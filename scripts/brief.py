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
# Theme signatures. `subject` is what decides membership (see _sig_probe_text);
# `keywords` is documentation only and is read by nothing.
# An article joins a
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
# `name` is the INTERNAL clustering identity — it is the dict key for
# clusters, the string gates.py and voice_profile.json match on, and the
# label carried in runs/grades.jsonl. It reads like an analyst's note
# because that is what it is.
#
# `label` is what the READER sees on the card. Micah, 2026-09-02: the
# internal names were being printed as public section kickers — "Media
# power and who owns it" is an analytic frame, not a section; "Creator
# economy consolidation" over-specifies a beat that is just Creator
# Economy; "The AI data gold rush" is a hot take wearing a category's
# clothes. Publications print short, stable, boring section names. Keep
# the two apart: rename a label freely, never a name.
NARRATIVE_SIGNATURES = [
    {
        "name": "The AI data gold rush",
        "label": "AI Infrastructure",
        "subject": 'The buildout underneath AI and who is getting paid for it: training data and the people who label it, GPUs and chip supply, data centres and the power and land they need, cloud capacity deals, and the money being raised against all of it.',
        "voice_weight": 1.0,
        "keywords": ["training data", "data labeling", "data center", "gross run rate", "ai training", "compute", "gpu", "data infra"],
    },
    {
        "name": "AI trust and accountability",
        "label": "AI Safety",
        "subject": 'Whether AI systems can be trusted and who is answerable when they are not: models that deceive or hallucinate, safety and alignment work, red teaming, audits, regulation, liability, and what happens to the people affected.',
        "voice_weight": 1.0,
        "keywords": ["zero data retention", "safety", "oversight", "national security", "lie", "cheat", "hallucinat", "alignment", "guardrail", "red team", "ai agents"],
    },
    {
        "name": "Media power and who owns it",
        "label": "Media",
        "subject": 'Who controls what gets published and seen: ownership of newsrooms and studios, consolidation and acquisitions, the platforms that distribute news, editorial independence, and antitrust pressure on any of it.',
        "voice_weight": 1.0,
        "keywords": ["zuckerberg", "media ownership", "newsroom", "journalism", "platform power", "antitrust media", "who owns", "masthead"],
    },
    {
        "name": "Creator economy consolidation",
        "label": "Creator Economy",
        "subject": 'Independent creators and the businesses forming around them: the platforms they publish on, revenue splits and royalties, deals with studios and labels, and the consolidation that turns independence back into employment.',
        "voice_weight": 1.0,
        "keywords": ["creator", "influencer", "studio", "tiktok", "youtube", "substack", "content deal", "royalt", "creator economy"],
    },
    {
        "name": "Sports money keeps inflating",
        "label": "Sports Business",
        "subject": 'The economics of professional sport rather than the games: franchise valuations and team sales, broadcast and streaming rights, stadium finance, player pay and revenue sharing, sponsorship, and betting money entering the sport.',
        "voice_weight": 0.7,
        "keywords": ["prize money", "valuation", "stadium", "media deal", "broadcast", "rights deal", "nfl", "nba", "mlb", "premier league", "franchise", "revenue share", "team sale"],
    },
    {
        "name": "Prediction markets go mainstream",
        "label": "Prediction Markets",
        "subject": 'Markets where people trade on the probability of real events: prediction and event contract exchanges, their regulators, election and sports odds, and the argument about whether their prices actually forecast anything.',
        "voice_weight": 0.7,
        "keywords": ["kalshi", "polymarket", "prediction market", "cftc", "election odds", "probability", "market contract"],
    },
    {
        "name": "Crypto's leverage problem",
        "label": "Crypto Markets",
        "subject": 'Borrowed money inside crypto markets: leveraged positions, liquidations and short squeezes, lending against tokens, ETF and fund flows, and the collapses that follow when the borrowing unwinds.',
        "voice_weight": 0.7,
        "keywords": ["short squeeze", "liquidation", "leverage", "borrow", "etf flow", "plung", "xrp", "bitcoin", "token"],
    },
    {
        "name": "AI surveillance creep",
        "label": "Surveillance",
        "subject": 'Automated watching of ordinary people: cameras and licence plate readers, facial recognition, phone and location tracking, always-on recording devices, police and employer use of it, and the privacy law around it.',
        "voice_weight": 0.7,
        "keywords": ["surveillance", "glasses", "recording", "police", "track", "camera", "privacy", "facial", "driver"],
    },
    {
        "name": "Energy and climate thresholds",
        "label": "Energy & Climate",
        "subject": 'How energy gets produced and what the climate does in response: grid capacity and demand, solar, geothermal, nuclear and hydrogen, emissions and carbon accounting, and the floods, heat and storms already arriving.',
        "voice_weight": 0.4,
        "keywords": ["hydrogen", "geothermal", "solar", "grid", "emission", "climate", "flood", "space mirror", "temperature", "carbon"],
    },
    {
        "name": "Cities, housing and where America lives",
        "label": "Housing",
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
    prose, the same thing angles.yaml now carries.

    The `keywords` lists are kept as human documentation of what each theme is
    meant to hold, and they DECIDE NOTHING: nothing in the pipeline reads them
    any more. Do not add a keyword expecting it to change what clusters.
    """
    subject = (sig.get("subject") or "").strip()
    if not subject:
        raise RuntimeError(
            "signature %r has no subject sentence. Falling back to its keyword "
            "list would silently reintroduce the place-name bias this replaced."
            % sig.get("name"))
    return "%s. %s" % (sig["name"], subject)


def local_ts(when=None, fmt="%Y-%m-%d %H:%M %Z"):
    """Format a moment in the box's LOCAL timezone, for DISPLAY only.

    Micah, 2026-08-25, reading the brief footer: "everything should be in local
    time on the webpage." The footer said "2026-08-25 00:29 UTC", which is
    19:29 CDT the previous evening, and it read as a run from earlier today
    when it was nineteen hours stale. A timestamp whose job is to tell you how
    fresh the page is must not need arithmetic first.

    Storage stays UTC on purpose: run directory names, meta.json timestamps and
    each card's first_seen are keys and comparisons, and a local-time key
    repeats itself for an hour every autumn. This converts at the edge.

    Accepts a datetime, an ISO string, or None for now. A naive datetime is
    assumed to be UTC, which is what every stored timestamp in this pipeline
    is.
    """
    from datetime import datetime as _d, timezone as _tzz
    if when is None:
        when = _d.now(_tzz.utc)
    elif isinstance(when, str):
        try:
            when = _d.fromisoformat(when)
        except ValueError:
            return when  # unparseable: show it as stored rather than guessing
    if when.tzinfo is None:
        when = when.replace(tzinfo=_tzz.utc)
    return when.astimezone().strftime(fmt)


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

    # Embed the whole pool in ONE batched pass before clustering it.
    # signature_for() embeds one article at a time, so without this a 2,580
    # article pool is 2,580 sequential provider round trips. Measured
    # 2026-08-25: that ran past 400s and the cron's 900s per-script timeout was
    # the only thing standing between it and running forever. load_clusters()
    # in narrative_desk.py already warmed; this loop did not, and it is the one
    # the cron reaches first.
    _points = {id(a): mine_data_points(a) for a in scored}
    warm_signatures([(a, _points[id(a)]) for a in scored])
    import embed as _embed
    print("  " + _embed.stats_line())

    # Enrich every eligible article — no gate
    enriched = []
    for a in scored:
        points = _points[id(a)]
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
#
# A seed hit is not a tiebreaker. At narrative_desk.py:1144 it is what lets a
# quote/moment story become a card at all, so this list decides which of
# Micah's subjects can reach the brief.
#
# There are TWO sources and they are ADDITIVE, per Micah 2026-08-26: "the
# hardcoded seeds and the live ones too".
#
#   PINNED   the list below. Things he named directly in conversation. These
#            are standing instructions and never expire.
#   LIVE     derived from corpus/*.jsonl on every run, weighted to the last
#            few weeks. See _live_seeds().
#
# Until 2026-08-26 only the pinned list existed, and its own comment admitted
# what that meant: the seeds came "from the 2026-08-21 spec conversation".
# Grepping every consumer of corpus/*.jsonl found exactly one, extract_angles.py,
# a manual dev tool run twice in its life. So poll_social.py had been appending
# his tweets to a corpus that NOTHING in the ranking path read. Micah, correctly:
# "it's like it's only incorporated if i say it in the chat." It was.
_PINNED_SEEDS = [
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

# How far back a tweet still counts as "what he is on about lately".
LIVE_SEED_DAYS = int(os.environ.get("IH_LIVE_SEED_DAYS", "14"))
# A term must appear in at least this many DISTINCT posts. One mention is a
# passing reference; two is a subject.
LIVE_SEED_MIN_POSTS = int(os.environ.get("IH_LIVE_SEED_MIN_POSTS", "3"))
LIVE_SEED_MAX = int(os.environ.get("IH_LIVE_SEED_MAX", "30"))
# Loud if the corpus has not moved in this long. The poller died on 2026-08-24
# and nothing noticed for days, because a frozen corpus and a quiet week look
# identical from in here.
LIVE_SEED_STALE_H = float(os.environ.get("IH_LIVE_SEED_STALE_H", "48"))

_STOP = set("""
a an the and or but if then than that this these those there here it its it's
is are was were be been being am do does did doing have has had having will
would can could should may might must shall
i me my we us our you your he him his she her they them their what which who
whom when where why how all any both each few more most other some such no nor
not only own same so too very just now also into onto from with without within
about above below over under again further once because as at by for of on to
in out up down off over under s t don ve ll re m d
new news good great best big get got go going make made like really much many
one two three first last next time day week month year today tomorrow
via rt amp http https com www co org net
people thing things way lot going know think want need see look
please everybody tired similar setting picked scored throw career estimated
bench aug toward step leaders fields open close start stop keep put
""".split())
# Every word on the two lines above was observed in a live-seed run on
# 2026-08-26 and removed for being English rather than a subject. Curate this
# from MEASURED output, never from a guess about what Micah cares about: the
# whole point of live seeds is that the corpus decides, not the author of this
# file.

_LIVE_CACHE = {}


LIVE_SEED_MAX_POOL_RATE = float(os.environ.get("IH_LIVE_SEED_MAX_POOL_RATE", "0.02"))


def _drop_indiscriminate(seeds, pool_limit=1200):
    """Remove live seeds that match too much of the current article pool.

    Returns seeds unchanged if the pool cannot be read: this is a refinement,
    and failing to refine must not empty the list. The count is printed either
    way so a silent no-op is visible."""
    path = os.path.join(WEB, "articles.json")
    if not seeds or not os.path.exists(path):
        print("  seed discrimination: SKIPPED (no pool at %s)" % path)
        return seeds
    try:
        arts = json.load(open(path)).get("articles", [])[:pool_limit]
    except Exception as exc:
        print("  seed discrimination: SKIPPED (%s)" % exc)
        return seeds
    if not arts:
        print("  seed discrimination: SKIPPED (pool is empty)")
        return seeds
    texts = [(a.get("title", "") + " " + a.get("summary", "")).lower() for a in arts]
    kept, dropped = [], []
    for t in seeds:
        n = sum(1 for x in texts if t in x)
        (dropped if n / float(len(texts)) > LIVE_SEED_MAX_POOL_RATE
         else kept).append((t, n))
    if dropped:
        print("  seed discrimination: dropped %d of %d for matching >%.0f%% of "
              "the pool: %s" % (len(dropped), len(seeds),
                                LIVE_SEED_MAX_POOL_RATE * 100,
                                ", ".join("%s(%d)" % d for d in dropped[:10])))
    else:
        print("  seed discrimination: 0 of %d dropped" % len(seeds))
    return [t for t, _ in kept]


def _tweet_terms(text, caps_out=None):
    """Candidate subject terms from one post: unigrams and bigrams.

    If `caps_out` is a set, terms that appeared Capitalised mid-sentence are
    added to it. That is a cheap proper-noun signal, and it is what separates
    `Galveston` and `Yeezy` from `setting` and `picked`, which lift alone
    ranked side by side."""
    t = text.lower()
    t = re.sub(r"https?://\S+", " ", t)
    t = re.sub(r"[@#]\w+", " ", t)
    t = re.sub(r"[^a-z0-9' ]+", " ", t)
    toks = [w for w in t.split() if len(w) >= 3 and w not in _STOP and not w.isdigit()]
    out = set(toks)
    out |= {"%s %s" % (a, b) for a, b in zip(toks, toks[1:])}
    if caps_out is not None:
        raw = re.sub(r"https?://\S+", " ", text)
        raw = re.sub(r"[@#]\w+", " ", raw)
        words = re.findall(r"[A-Za-z][A-Za-z']+", raw)
        # Skip index 0: a sentence-initial capital says nothing.
        for i, w in enumerate(words):
            if i and w[0].isupper() and not w.isupper():
                caps_out.add(w.lower())
    return out


def _live_seeds():
    """Subjects Micah has actually posted about lately, from corpus/*.jsonl.

    Additive to _PINNED_SEEDS, never a replacement. Raises if the corpus is
    missing: these files are a pipeline input, and returning [] would silently
    drop every recent subject while the brief still rendered.
    """
    if "seeds" in _LIVE_CACHE:
        return _LIVE_CACHE["seeds"]
    import datetime as _dtm
    now = _dtm.datetime.now(_dtm.timezone.utc)

    def _parse(v):
        v = (v or "").replace("·", "").replace("  ", " ").strip()
        for f in ("%b %d, %Y %I:%M %p UTC", "%a %b %d %H:%M:%S %z %Y"):
            try:
                d = _dtm.datetime.strptime(v, f)
                return d if d.tzinfo else d.replace(tzinfo=_dtm.timezone.utc)
            except ValueError:
                pass
        return None

    # A term is a SUBJECT when it is elevated against his own baseline, not
    # when it is common. Measured 2026-08-26: ranking the last 14 days by raw
    # frequency returned "years, open, after, back, better, every, still" from
    # 418 posts. Those are English, not subjects.
    #
    # So score by LIFT: a term's rate in the recent window against its rate in
    # everything older. That is also the honest reading of what Micah asked
    # for, which was what he has been tweeting about LATELY, not what he says
    # most often in general.
    recent_counts, old_counts, caps = {}, {}, {}
    recent = old_n = 0
    newest = None
    for name in ("innovativehype.jsonl", "geoppls.jsonl"):
        path = os.path.join(os.path.dirname(__file__), "..", "corpus", name)
        if not os.path.exists(path):
            raise FileNotFoundError(
                "%s is missing. It is a ranking input: every subject Micah has "
                "posted about recently would silently stop mattering while the "
                "brief still rendered. Run scripts/poll_social.py."
                % os.path.abspath(path))
        for line in open(path):
            try:
                row = json.loads(line)
            except ValueError:
                continue
            d = _parse(row.get("date"))
            if not d:
                continue
            if newest is None or d > newest:
                newest = d
            seen_caps = set()
            terms = _tweet_terms(row.get("text") or "", seen_caps)
            if (now - d).days <= LIVE_SEED_DAYS:
                recent += 1
                for t in terms:
                    recent_counts[t] = recent_counts.get(t, 0) + 1
                for w in seen_caps:
                    caps[w] = caps.get(w, 0) + 1
            else:
                old_n += 1
                for t in terms:
                    old_counts[t] = old_counts.get(t, 0) + 1

    pinned = set(_PINNED_SEEDS)
    scored = []
    for t, c in recent_counts.items():
        if c < LIVE_SEED_MIN_POSTS or t in pinned:
            continue
        recent_rate = c / float(max(recent, 1))
        # +1 smoothing so a term that is genuinely new is not divided by zero
        # into infinity, and one that is merely common does not win.
        base_rate = (old_counts.get(t, 0) + 1) / float(max(old_n, 1) + 1)
        lift = recent_rate / base_rate
        # A unigram that is never capitalised in his own posts is almost always
        # a verb or a filler noun. Require it to clear a higher bar than a
        # proper noun or a bigram does.
        if " " not in t:
            cap_share = caps.get(t, 0) / float(c)
            if cap_share < 0.5:
                lift *= 0.35
        scored.append((lift, c, t))
    ranked = [(c, t) for _lift, c, t in
              sorted(scored, key=lambda x: (-x[0], -x[1], x[2]))]

    # A bigram implies its parts. Keep the bigram, drop a unigram that only
    # ever appears inside one, so "prediction market" does not also seed every
    # article containing "market".
    bigrams = [t for _, t in ranked if " " in t]
    seeds, seen = [], set()
    for c, t in ranked:
        if " " not in t and any(t in b.split() for b in bigrams) and c <= LIVE_SEED_MIN_POSTS:
            continue
        if t in seen:
            continue
        seen.add(t)
        seeds.append(t)
        if len(seeds) >= LIVE_SEED_MAX:
            break

    # A seed must DISCRIMINATE. Measured 2026-08-26: lift plus a proper-noun
    # signal still promoted `nfl`, `justin` and `basketball`, which between
    # them admitted 202 extra articles that were almost entirely NFL. A term
    # frequent in his tweets AND frequent in the pool admits everything, which
    # makes the sports skew he complained about WORSE. Micah asked for more
    # variety; a seed matching a tenth of the pool delivers the opposite.
    #
    # So drop any live seed that matches more than LIVE_SEED_MAX_POOL_RATE of
    # the current pool. Pinned seeds are exempt: those are standing
    # instructions and he is entitled to a broad one.
    # "justin" and "justin bieber" both surface; the bare first name then
    # matches every Justin in the news (measured: it admitted an Eagles story
    # about Jalen Hurts). If we kept the bigram, the unigram is redundant and
    # strictly more dangerous.
    _bg_parts = {w for t in seeds if " " in t for w in t.split()}
    seeds = [t for t in seeds if " " in t or t not in _bg_parts]
    seeds = _drop_indiscriminate(seeds)

    age_h = (now - newest).total_seconds() / 3600.0 if newest else None
    # Say the counts every run, healthy or not.
    print("  live seeds: %d from %d posts in the last %dd (corpus newest %s)"
          % (len(seeds), recent, LIVE_SEED_DAYS,
             ("%.1fh ago" % age_h) if age_h is not None else "UNKNOWN"))
    if age_h is not None and age_h > LIVE_SEED_STALE_H:
        print("  WARNING: corpus is %.1fh stale (limit %.0fh). Recent tweets are "
              "NOT ranking anything. Check the social-corpus-poll cron job."
              % (age_h, LIVE_SEED_STALE_H))
    if not seeds:
        print("  WARNING: 0 live seeds. Either nothing was posted in %dd or the "
              "corpus is not updating. Only the %d pinned seeds are active."
              % (LIVE_SEED_DAYS, len(_PINNED_SEEDS)))
    _LIVE_CACHE["seeds"] = seeds
    return seeds


def all_seeds():
    """Pinned plus live. The order is pinned-first so a pinned term always
    matches even if the live pass is empty."""
    return list(_PINNED_SEEDS) + _live_seeds()


_LIVE_RE = {}


def _seed_match(article):
    """Count seeds present in the article (title+body). Pinned AND live.

    Pinned seeds match as SUBSTRINGS, deliberately: the list contains stems
    like `royalt` that are meant to catch royalty/royalties, and it is
    hand-written so its author owns the consequences.

    Live seeds match on WORD BOUNDARIES. They are derived automatically, and
    on 2026-08-26 substring matching let `russ` hit Russia/Brussels and `baby`
    hit a Dolly Parton story. An auto-generated term has nobody to own a
    false positive, so it gets the stricter rule.
    """
    text = f"{article.get('title','')} {article.get('summary','')} {article.get('_body','')[:1500]}".lower()
    n = sum(1 for seed in _PINNED_SEEDS if seed in text)
    for seed in _live_seeds():
        rx = _LIVE_RE.get(seed)
        if rx is None:
            rx = _LIVE_RE[seed] = re.compile(r"\b" + re.escape(seed) + r"\b")
        if rx.search(text):
            n += 1
    return n


def main():
    with open(os.path.join(WEB, "articles.json")) as f:
        data = json.load(f)
    md, cards = make_brief(data["articles"])

    header = (
        "# INNOVATIVE HYPE — BRIEF\n"
        f"_Generated {local_ts()} · "
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
  <div class="page-meta">Narrative brief · data-point anchored · updated {local_ts()}</div>
  {''.join(card_html)}
  <a class="back" href="index.html">← Back to feed</a>
</div>
</body>
</html>
"""


if __name__ == "__main__":
    main()
