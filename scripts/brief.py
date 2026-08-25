#!/usr/bin/env python3
"""brief.py — narrative news brief for the Innovative Hype site.

The pipeline (v3, narrative-focused, modeled on the LP news desk + the
Polymarket/Kalshi JUST IN corpus):

  1. MINE data points from article bodies — dollar figures, percentages,
     ratios, market-implied probabilities.
  2. FILTER for "moment-ness" — a data point makes the brief only when it
     crosses a meaningful threshold: a record, a first, a multi-year level,
     a market-implied probability, a structural imbalance. (This is the
     JUST IN lesson: not every number matters.)
  3. CLUSTER articles that share a recurring theme (narrative buckets, NOT
     category buckets).
  4. ASK the story question — what does this data point tell a story about?
     The answer becomes the narrative title.
  5. RENDER narrative cards: narrative title (the conversation) + the data
     point as the hook + supporting articles as receipts.

Deterministic (no LLM) in v3: moment detection + narrative templates are
rule-based. An LLM desk pass can replace step 4 later (LP does exactly this
with a DeepSeek call).

Output: web/brief.md + web/brief.html
"""

import json
import os
import re
from collections import OrderedDict
from datetime import datetime, timezone

WEB = os.path.join(os.path.dirname(__file__), "..", "web")


def _md_escape(text):
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _md_inline(text):
    text = _md_escape(text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"_(.+?)_", r"<em>\1</em>", text)
    return text


def strip_html(s):
    if not s:
        return ""
    return re.sub(r"<[^>]+>", " ", s)


def _clean_entities(s):
    return (s.replace("&#8217;", "'").replace("&#8220;", '"').replace("&#8221;", '"')
             .replace("&#8230;", "...").replace("&amp;", "&").replace("&#8211;", "-")
             .replace("&#8212;", "—"))


# === 1. DATA MINING ===
# Patterns for dollar figures, percentages, and large counts.
_NUM_PAT = re.compile(
    r"\$\s?\d[\d,]*(?:\.\d+)?\s?(million|billion|bn|m|k)?"
    r"|\d+(?:\.\d+)?%"
    r"|\d[\d,]*\s*(million|billion|trillion)\b"
    r"|\d+(?:\.\d+)?\s?(?:x|fold)\b",
    re.I,
)

# === 2. MOMENT FILTER ===
# A data point matters when it crosses a meaningful threshold. This is the
# JUST IN lesson: records, firsts, multi-year levels, market-implied
# probabilities, structural imbalances.
_MOMENT_PAT = re.compile(
    r"first\s+time|ever\s+record|highest\s+(?:level|since|ever|grossing)"
    r"|lowest\s+(?:level|since|ever)|record\s+(?:high|low|prize|amount|purse)"
    r"|largest|biggest|fastest|most\s+ever|since\s+19\d\d|since\s+20\d\d"
    r"|in\s+40\s+years|in\s+\d+\s+years|first\s+(?:country|company|team|player|city|state)"
    r"|officially|%\s+chance|chance\s+of|crosses?|surpasses?|plunges?\s+to"
    r"|hits?\s+(?:a\s+)?record|clears?\s+\$|exceeds?\s+\$|topped\s+\$"
    r"|\$[\d.,]+[mb]\s+(?:valuation|deal|acquisition|investment)"
    r"|one\s+of\s+the\s+(?:first|largest|biggest|only)",
    re.I,
)


def mine_data_points(article):
    """Return a list of (data_point) sentences from the article body.

    v3 fix: don't require a moment marker — a striking number itself is the
    hook (JUST IN: '$500M gross run rate', '80-90% margins'). Moment phrases
    (record/first/highest) are a BOOST for ranking, not a gate."""
    body = _clean_entities(article.get("_body", "") or "")
    if len(body) < 200:
        return []
    sents = re.split(r"(?<=[.!?])\s+", body)
    points = []
    for s in sents:
        nums = _NUM_PAT.findall(s)
        if not nums:
            continue
        s_clean = s.strip()
        if 30 <= len(s_clean) <= 260:
            points.append(s_clean)
    return points[:3]


# === 3. NARRATIVE CLUSTERING ===
# Theme signatures: (name, keywords, voice_weight). An article joins a
# narrative bucket when it matches the theme AND carries a moment-worthy
# data point (or is a high-score anchor).
#
# voice_weight comes from cross-referencing the @geoppls + @innovativehype
# tweet corpora (the Innovative Hype voice) against the article feed:
#   1.0 = the voice talks about this theme a lot (AI/tools 145, media 58,
#         cities 52, creator 43) — buckets get priority
#   0.7 = moderate voice interest (crypto/markets 34, sports 28,
#         prediction markets 25, sovereignty 25)
#   0.4 = feed pushes it but the voice is lukewarm — can still surface
#         when the data point is strong, but doesn't dominate
NARRATIVE_SIGNATURES = [
    {
        "name": "The AI data gold rush",
        "subject": 'The buildout underneath AI and who is getting paid for it: training data and the people who label it, GPUs and chip supply, data centres and the power and land they need, cloud capacity deals, and the money being raised against all of it.',
        "voice_weight": 1.0,
        "keywords": ["training data", "data labeling", "data center", "gross run rate", "ai training", "compute", "gpu", "data infra"],
    },
    {
        "name": "AI trust and accountability",
        "subject": 'Whether AI systems can be trusted and who is answerable when they are not: models that deceive or hallucinate, safety and alignment work, red teaming, audits, regulation, liability, and what happens to the people affected.',
        "voice_weight": 1.0,
        "keywords": ["zero data retention", "safety", "oversight", "national security", "lie", "cheat", "hallucinat", "alignment", "guardrail", "red team", "ai agents"],
    },
    {
        "name": "Media power and who owns it",
        "subject": 'Who controls what gets published and seen: ownership of newsrooms and studios, consolidation and acquisitions, the platforms that distribute news, editorial independence, and antitrust pressure on any of it.',
        "voice_weight": 1.0,
        "keywords": ["zuckerberg", "media ownership", "newsroom", "journalism", "platform power", "antitrust media", "who owns", "masthead"],
    },
    {
        "name": "Creator economy consolidation",
        "subject": 'Independent creators and the businesses forming around them: the platforms they publish on, revenue splits and royalties, deals with studios and labels, and the consolidation that turns independence back into employment.',
        "voice_weight": 1.0,
        "keywords": ["creator", "influencer", "studio", "tiktok", "youtube", "substack", "content deal", "royalt", "creator economy"],
    },
    {
        "name": "Sports money keeps inflating",
        "subject": 'The economics of professional sport rather than the games: franchise valuations and team sales, broadcast and streaming rights, stadium finance, player pay and revenue sharing, sponsorship, and betting money entering the sport.',
        "voice_weight": 0.7,
        "keywords": ["prize money", "valuation", "stadium", "media deal", "broadcast", "rights deal", "nfl", "nba", "mlb", "premier league", "franchise", "revenue share", "team sale"],
    },
    {
        "name": "Prediction markets go mainstream",
        "subject": 'Markets where people trade on the probability of real events: prediction and event contract exchanges, their regulators, election and sports odds, and the argument about whether their prices actually forecast anything.',
        "voice_weight": 0.7,
        "keywords": ["kalshi", "polymarket", "prediction market", "cftc", "election odds", "probability", "market contract"],
    },
    {
        "name": "Crypto's leverage problem",
        "subject": 'Borrowed money inside crypto markets: leveraged positions, liquidations and short squeezes, lending against tokens, ETF and fund flows, and the collapses that follow when the borrowing unwinds.',
        "voice_weight": 0.7,
        "keywords": ["short squeeze", "liquidation", "leverage", "borrow", "etf flow", "plung", "xrp", "bitcoin", "token"],
    },
    {
        "name": "AI surveillance creep",
        "subject": 'Automated watching of ordinary people: cameras and licence plate readers, facial recognition, phone and location tracking, always-on recording devices, police and employer use of it, and the privacy law around it.',
        "voice_weight": 0.7,
        "keywords": ["surveillance", "glasses", "recording", "police", "track", "camera", "privacy", "facial", "driver"],
    },
    {
        "name": "Energy and climate thresholds",
        "subject": 'How energy gets produced and what the climate does in response: grid capacity and demand, solar, geothermal, nuclear and hydrogen, emissions and carbon accounting, and the floods, heat and storms already arriving.',
        "voice_weight": 0.4,
        "keywords": ["hydrogen", "geothermal", "solar", "grid", "emission", "climate", "flood", "space mirror", "temperature", "carbon"],
    },
    {
        "name": "Cities, housing and where America lives",
        "subject": 'Where people can afford to live and what that does to a place: home prices and rents, supply and construction, zoning and permitting, landlords and investor ownership, cost of living, and the migration between cities and regions that follows.',
        "voice_weight": 1.0,
        "keywords": ["texas", "austin", "housing", "rent", "suburb", "relocation", "move to", "real estate", "zoning", "migration", "cost of living", "neighborhood"],
    },
]


def _kw_match(keyword, text):
    """Word-boundary keyword match, plural-aware (NEWS-ENGINE-SPEC.md R5).

    'camera' matches 'cameras' and 'track' matches 'tracking', but 'ban'
    must NOT match 'band'. Strategy: match the keyword, its plural (s/es),
    and its -ing form at word boundaries — never a raw substring."""
    kw = re.escape(keyword)
    pattern = rf"\b{kw}(?:s|es|ing|'s)?\b"
    return re.search(pattern, text) is not None


# Cosine floor for a story to JOIN a signature cluster, calibrated 2026-08-24
# against a 400-article slice of the live pool. Against the prose subject
# probes:
#
#   Padres roster moves            housing 0.031   (the OLD rule clustered it
#   Mystics WNBA championship      housing 0.038    into housing, on `texas`)
#   Texas A&M fall camp            housing 0.065
#   First-time buyers priced out   housing 0.264
#   Austin rents fall 12%          housing 0.274
#
# 0.26 is the widest gap in that ordering. It also keeps out "Texans' 53-man
# roster prediction" (0.254 against prediction markets, matched on the word
# prediction). Known cost at this floor: "Oceans hit highest temperature on
# record" scores 0.252 against energy and climate and stays unclustered.
#
# Known cost at this floor, beyond the oceans story: two genuine housing items
# ("W Properties Mixing BTR and Garden-Style Apartments" 0.214, "VIC Partners
# Obtains Construction Loan for a 268-Unit Workforce Rental Community" 0.231)
# rank housing FIRST and still miss. Terse trade-press headlines carry little
# text to embed.
#
# A confidence clause was tried to recover them: admit anything above 0.21 that
# beats its runner-up by 0.08. It recovered both, and readmitted eleven others,
# including "Brenda Song Loves the Los Angeles Rams" into sports money and a
# Notre Dame recruiting page into the AI data gold rush. Rejected: the margin
# is high on short headlines because there is not enough text for a second
# theme to score at all, so it measures brevity rather than confidence.
#
# The margin rule that remains is separate: the best signature must beat the
# runner-up by SIG_SIM_MARGIN, so a story equally near two themes joins neither
# rather than joining whichever won by a hair.
SIG_SIM_FLOOR = float(os.environ.get("IH_SIG_FLOOR", "0.26"))
SIG_SIM_MARGIN = float(os.environ.get("IH_SIG_MARGIN", "0.02"))


def _sig_probe_text(sig):
    """What a signature looks like to the embedding model.

    Not the keyword list. The keywords were written to be FOUND in text, so
    they carry the vocabulary's accidents: `texas` and `austin` sat in the
    housing list because that is where he lives, and feeding them to an
    embedding pulls the whole vector toward Texas. Measured 2026-08-24, a
    Texas A&M fall-camp story scored 0.148 against the keyword probe and 0.054
    once the place names came out.

    Stripping them is not enough either, because a bare noun list is a thin
    description of a category: it also dropped a real story ("Austin rents
    fall 12% as new apartments finish") from 0.360 to 0.279, under the floor.

    So each signature carries a `subject` sentence describing the CATEGORY in
    prose, the same thing angles.yaml now carries. Keywords stay for the
    non-semantic uses elsewhere in this file.
    """
    subject = (sig.get("subject") or "").strip()
    if not subject:
        raise RuntimeError(
            "signature %r has no subject sentence. Falling back to its keyword "
            "list would silently reintroduce the place-name bias this replaced."
            % sig.get("name"))
    return "%s. %s" % (sig["name"], subject)


def signature_subject_text(article, data_points):
    """What a story is ABOUT, for matching: its title and its mined data
    points. Never the body. A body mentions everything; a title states the
    subject, and matching on bodies is how a housing theme finds a chip story
    in the first place."""
    title = strip_html(article.get("title", "") or "").strip()
    return " ".join([title] + list(data_points or [])).strip()


def warm_signatures(pairs):
    """Batch-embed a whole pool before clustering it.

    signature_for() embeds one article at a time, so without this a 400-article
    pool is 400 sequential provider round trips. Pass [(article, points), ...]
    and every later signature_for() call is a cache hit.
    """
    import embed
    texts = [_sig_probe_text(x) for x in NARRATIVE_SIGNATURES]
    texts += [signature_subject_text(a, p) for a, p in pairs]
    embed.warm(texts)


def signature_for(article, data_points):
    """Assign an article to a narrative signature (theme), if any.

    Until 2026-08-24 this counted substring hits from the signature's keyword
    list and required 2. That is how `texas`, sitting in the housing
    signature's keywords, put a Blue Origin rocket factory in "Cities, housing
    and where America lives" and let the desk offer it a housing angle. The
    same list has `valuation` and `broadcast` under sports and `compute` under
    the AI data gold rush, so a team sale and a compute-financing story land
    next to each other on generic finance nouns.

    Broadening the list attaches everything and narrowing it attaches nothing.
    Both are the same defect, which is that a word is not a subject. Matching
    is on meaning now: the article's title and mined data points against the
    signature's theme and its keywords-as-examples. Returns (signature, score)
    where score is the cosine, kept in the second slot so existing callers that
    treat it as a strength number still work.
    """
    import embed
    subject = signature_subject_text(article, data_points)
    if not subject:
        # No title and no mined points is an upstream failure, not a story that
        # belongs to no theme. Say it rather than silently returning None.
        print("  signature: article has no title or data points; unclustered")
        return None, 0.0

    sims = embed.similarity([subject], [_sig_probe_text(x)
                                        for x in NARRATIVE_SIGNATURES])[0]
    order = sorted(zip(sims, NARRATIVE_SIGNATURES), key=lambda t: -t[0])
    best_score, best = float(order[0][0]), order[0][1]
    runner = float(order[1][0]) if len(order) > 1 else 0.0

    if best_score < SIG_SIM_FLOOR:
        return None, 0.0
    if best_score - runner < SIG_SIM_MARGIN:
        # Equally near two themes means the subject is not one of them.
        return None, 0.0
    return best, best_score


def _narrative_title(sig_name, lead, data_point):
    """Rule-based narrative title: the story the data point tells, not the
    category. Uses the strongest moment phrasing from the article."""
    # Common shapes
    if "Sports money" in sig_name:
        return f"{lead.get('source','')}: the money keeps inflating"
    if "AI data gold rush" in sig_name:
        return "The AI data layer is printing money"
    if "AI trust" in sig_name:
        return "Can we trust the machines we're building?"
    if "Prediction markets" in sig_name:
        return "Prediction markets are becoming the newsroom"
    if "AI surveillance" in sig_name:
        return "AI watches everyone now"
    if "Creator economy" in sig_name:
        return "The creator economy is consolidating"
    if "Crypto's leverage" in sig_name:
        return "Crypto's rally is running on borrowed money"
    if "Energy and climate" in sig_name:
        return "The energy transition is hitting thresholds"
    return sig_name


# === 4. THE BRIEF BUILDER ===
def make_brief(articles, max_cards=5, stories_per_card=3):
    """Build the deterministic layer for the narrative desk.

    v4 (NEWS-ENGINE-SPEC.md R1/R2/R3): NO admission gate. Every eligible
    article enters the pool with a score. Signatures are boosts, not
    filters. An article qualifies for the desk via ANY of:
      - a data point (number crossing a threshold)
      - a quote (named person saying something contestable)
      - a moment (weird/local/symbolic/first/rule-bent)
    The deterministic layer RANKS, it does not admit."""
    scored = [a for a in articles if not a.get("_noise")]
    scored.sort(key=lambda x: -x.get("_score", 0))

    # Enrich every eligible article — no gate
    enriched = []
    for a in scored:
        points = mine_data_points(a)
        sig, hits = signature_for(a, points)
        quote = _quote_from_article(a)
        moment = _moment_from_article(a)
        # Boost: tweet-corpus seed match (R4)
        seed_hits = _seed_match(a)
        enriched.append({
            "article": a,
            "points": points,
            "sig": sig,
            "hits": hits,
            "quote": quote,
            "moment": moment,
            "seed_hits": seed_hits,
        })

    # Build clusters from signature matches (loose), plus one-off cards
    # from quote/moment stories that don't cluster.
    clusters = OrderedDict()
    for e in enriched:
        if e["sig"]:
            name = e["sig"]["name"]
            clusters.setdefault(name, {"sig": e["sig"], "items": []})
            clusters[name]["items"].append(e)

    # Rank clusters: voice weight × size × lead score (seed boost included)
    ranked = []
    for name, cl in clusters.items():
        strength = len(cl["items"])
        lead = cl["items"][0]
        vw = cl["sig"].get("voice_weight", 0.5)
        ranked.append((name, cl, lead, strength, vw))
    ranked.sort(key=lambda x: (-x[4], -x[3], -x[2]["article"].get("_score", 0)))
    ranked = ranked[:max_cards]

    lines = []
    cards = []
    for name, cl, lead, strength, vw in ranked:
        sig = cl["sig"]
        lead_article = lead["article"]
        data_point = lead["points"][0] if lead["points"] else ""
        title = _narrative_title(sig["name"], lead_article, data_point)

        lines.append(f"## {title}")
        lines.append(f"_{data_point}_" if data_point else "")
        lines.append("")
        for item in cl["items"][:stories_per_card]:
            a = item["article"]
            lines.append(f"- {a.get('title','')} ({a.get('source','')})")
        lines.append("")

        cards.append({
            "title": title,
            "data_point": data_point,
            "stories": [(i["article"].get("title",""), i["article"].get("source",""), i["article"].get("link","#")) for i in cl["items"][:stories_per_card]],
        })

    return "\n".join(lines).strip(), cards


def _quote_from_article(article):
    """Find a quotable sentence: a named person saying something contestable.
    Returns (speaker, quote) or None."""
    body = _clean_entities(article.get("_body", "") or "")
    if len(body) < 150:
        return None
    sents = re.split(r"(?<=[.!?])\s+", body)
    for s in sents:
        m = re.search(r'["“](.+?)["”]', s)
        if m and re.search(r"\b(said|says|told|argued|claimed|warned|called|urged)\b", s, re.I):
            quote = m.group(1)
            if 15 <= len(quote) <= 250:
                return quote
    return None


def _moment_from_article(article):
    """Moment test: a symbol, a first, a rule bent, something weird/local.
    Returns the matching phrase or None."""
    title = article.get("title", "")
    body = (article.get("_body", "") or "")[:2000]
    text = f"{title} {body}".lower()
    for pat in [
        r"\bfirst\s+(?:time|ever|player|woman|man|team|city)\b",
        r"\bbanned\b|\barrested\b|\bfired\b|\bquits\b|\bwalked\s+off\b",
        r"\b(?:40|50|60|70)-year-old\b",
        r"\bstolen\b|\btheft\b",
        r"\bdraped\s+in\b|\bamerican\s+flag\b",
        r"\bsurveillance\b|\bprivacy\b",
        r"\btexas\b|\baustin\b",
        r"\bfireworks\b|\bconcert\b|\bfestival\b",
    ]:
        if re.search(pat, text):
            return pat
    return None


# === TWEET-CORPUS SEED MATCHING (R4) ===
# Entities and recurring subjects from the @geoppls + @innovativehype tweet
# corpora. An article touching one of these gets a boost — the voice is
# the seed list, exactly like LP's human-dictated conversation seeds.
_TWEET_SEEDS = [
    # Micah's explicit named stories (from the 2026-08-21 spec conversation)
    # — these get a boost whenever they appear, because he asked for them
    # directly. 'college football', 'wnba draft', '40-year-old', 'all of the
    # lights', 'commissioner' are his own words.
    "flock", "kalshi", "polymarket", "prediction market", "texas", "austin",
    "wnba", "nba", "ncaa", "college football", "longhorns", "messi", "soccer",
    "promotion", "relegation", "oatmeal", "zuckerberg", "castle", "meta",
    "tiktok", "marijuana", "cannabis", "surveillance", "privacy", "sovereignty",
    "media", "ownership", "creator", "royalt", "fireworks", "kanye",
    "all of the lights", "wnba draft", "commissioner", "40-year-old",
    "data center", "kushner", "palantir", "elon", "cursor", "blue origin",
]


def _seed_match(article):
    """Count tweet-corpus seeds present in the article (title+body)."""
    text = f"{article.get('title','')} {article.get('summary','')} {article.get('_body','')[:1500]}".lower()
    return sum(1 for seed in _TWEET_SEEDS if seed in text)


def main():
    with open(os.path.join(WEB, "articles.json")) as f:
        data = json.load(f)
    md, cards = make_brief(data["articles"])

    header = (
        "# INNOVATIVE HYPE — BRIEF\n"
        f"_Generated {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')} · "
        f"{data.get('feeds_ok',0)}/{data.get('feeds_total',0)} feeds · "
        f"{len(data['articles'])} articles_\n\n"
    )
    out = header + md + "\n"

    out_path = os.path.join(WEB, "brief.md")
    with open(out_path, "w") as f:
        f.write(out)
    print(out)

    # NOT brief.html. brief.py and narrative_desk.py both used to write that
    # one filename, and cron_news.py runs brief.py FIRST. So on any run where
    # the desk failed, brief.py's deterministic page silently became the live
    # brief, under a fresh timestamp, and it is the version Micah rejected on
    # 2026-08-21 ("i dont like this brief. at all."). That happened on the
    # 15:54 UTC run of 2026-08-23 and went unnoticed because the page looked
    # freshly updated. The desk owns brief.html; this file is the debug view of
    # the deterministic layer that feeds it.
    html = _render_html(cards)
    html_path = os.path.join(WEB, "brief-clusters.html")
    with open(html_path, "w") as f:
        f.write(html)
    print(f"\nWrote {out_path} and {html_path}")


def _render_html(cards):
    card_html = []
    for c in cards:
        stories = "".join(
            f'<li><a href="{link}" target="_blank" rel="noopener">{_md_inline(title)} <span class="src">({src})</span></a></li>'
            for title, src, link in c["stories"]
        )
        dp_html = f'<p class="brief-dp">▸ {_md_inline(c["data_point"])}</p>' if c["data_point"] else ""
        card_html.append(f"""
    <article class="brief-card">
      <h3 class="brief-title">{_md_inline(c["title"])}</h3>
      {dp_html}
      <ul class="brief-list">{stories}</ul>
    </article>""")

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>INNOVATIVE HYPE — BRIEF</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Oswald:wght@400;500;600;700&family=DM+Sans:wght@300;400;500;600&display=swap" rel="stylesheet">
<style>
  :root {{ --white:#fff; --off-white:#f8f8f8; --ink:#0a0a0a; --ink-light:#3a3a3a; --ink-muted:#888; --gold:#d4af37; --gold-dark:#b8860b; --border:#e8e8e8; }}
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{ font-family:'DM Sans',system-ui,sans-serif; background:var(--white); color:var(--ink); -webkit-font-smoothing:antialiased; }}
  .wrap {{ max-width:760px; margin:0 auto; padding:2.5rem 1.5rem; }}
  .page-title {{ font-family:'Oswald',sans-serif; font-weight:700; font-size:2rem; text-transform:uppercase; letter-spacing:-0.02em; margin-bottom:.25rem; }}
  .page-meta {{ font-size:.75rem; color:var(--ink-muted); text-transform:uppercase; letter-spacing:.05em; margin-bottom:2rem; }}
  .brief-card {{ background:var(--off-white); border:1px solid var(--border); border-top:3px solid var(--gold); padding:1.25rem 1.5rem; margin-bottom:1.25rem; }}
  .brief-title {{ font-family:'Oswald',sans-serif; font-weight:600; font-size:1.15rem; line-height:1.25; margin-bottom:.5rem; }}
  .brief-dp {{ font-size:.9rem; line-height:1.5; color:var(--ink); margin-bottom:.6rem; padding-left:.9rem; border-left:2px solid var(--gold); font-style:italic; }}
  .brief-list {{ list-style:none; padding-left:0; }}
  .brief-list li {{ font-size:.85rem; line-height:1.5; color:var(--ink-light); padding:.15rem 0 .15rem 1.1rem; position:relative; }}
  .brief-list li::before {{ content:'·'; position:absolute; left:0; color:var(--gold-dark); }}
  .brief-list a {{ color:var(--ink-light); text-decoration:none; }}
  .brief-list a:hover {{ color:var(--gold-dark); }}
  .brief-list .src {{ color:var(--ink-muted); font-size:.7rem; text-transform:uppercase; letter-spacing:.03em; }}
  .back {{ display:inline-block; margin-top:2rem; font-family:'Oswald',sans-serif; font-size:.8rem; text-transform:uppercase; letter-spacing:.05em; color:var(--ink); text-decoration:none; border-bottom:2px solid var(--gold); padding-bottom:2px; }}
</style>
</head>
<body>
<div class="wrap">
  <h1 class="page-title">Innovative Hype — Brief</h1>
  <div class="page-meta">Narrative brief · data-point anchored · updated {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}</div>
  {''.join(card_html)}
  <a class="back" href="index.html">← Back to feed</a>
</div>
</body>
</html>
"""


if __name__ == "__main__":
    main()
