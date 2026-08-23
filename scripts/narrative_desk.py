#!/usr/bin/env python3
"""narrative_desk.py — LLM narrative desk for the Innovative Hype brief.

Takes the deterministic clusters + mined data points from brief.py and runs
an LLM pass (the same pattern as Legendary Picks' ingest_league_narratives)
to write narrative cards:

  narrative  — one-sentence title naming the CONVERSATION (the story the
               data point tells), plain news language, no outlet-name
  paragraph  — 2-4 sentences of body prose: what's happening, who it
               affects, concrete names/numbers, the data point grounded
  source_ids — which articles this card actually grounds in

VERSIONED RUNS (Micah, 2026-08-21): every run writes a snapshot to
  runs/<timestamp>/
    input.json      — the clusters + data points fed to the model
    output.json     — the raw model response (strict JSON)
    cards.json      — the parsed cards, ready for brief.html
    meta.json       — code version (git SHA), model, prompt hash, timestamp
So every generation can be diffed and compared, exactly like LP's
news_narratives_runs table.

POOL-KEY DEDUP: if the input pool (cluster membership + data points) hasn't
changed since the last run, skip regeneration unless --force is passed.
"""

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEB = os.path.join(REPO, "web")
RUNS = os.path.join(REPO, "runs")

# Model: same provider/family LP uses for its narrative desk.
MODEL = "deepseek/deepseek-v4-flash-0731"
PROVIDER_BASE = "https://inference-api.nousresearch.com/v1"

_SYSTEM = (
    "You are the narrative desk for Innovative Hype, a Substack newsletter by "
    "Micah Peoples covering tech, business, sports and culture with an "
    "opinionated, cross-domain voice. You are given clusters of articles, each "
    "with mined data points, quotes and moments. Write AT MOST ONE card per "
    "cluster, and no more than 8 cards total.\n"
    "\n"
    "== STEP 1: DOES THIS DESERVE A CARD? ==\n"
    "Default to NO. Most clusters are not stories. Card it only if you can "
    "finish this sentence with something a reader would argue about: 'the "
    "reason this matters is ___'. If the honest answer is 'a thing happened' "
    'or \'someone did their job well\', output {"narrative": null}.\n'
    "NEVER card these, no matter how well sourced:\n"
    "  - an athlete or performer being good at their job (scored 53, had a "
    "big game, is a rising star, brings top players to an event)\n"
    "  - a scheduled or routine announcement (a launch, a lineup, a camp, a "
    "prize increase, a person describing a stadium)\n"
    "  - an event with no disclosed detail (someone was hospitalized, an "
    "incident is under investigation)\n"
    "  - a press release wearing a headline\n"
    "Six honest cards beat thirteen padded ones. An empty slot is a correct "
    "answer; a filler card is not.\n"
    "\n"
    "== STEP 2: FIND THE POWER ANGLE ==\n"
    "Every story lands on someone. Before writing, answer: who controls this, "
    "who profits, who pays, who is not being asked about it. That answer is "
    "usually the story, and it is usually the part a wire report leaves out.\n"
    "When a story has a buyer, an owner, or a name behind the money, NAME "
    "THEM. A franchise sale is about who is buying it, not the price. If the "
    "cluster names an owner, an investor or a political figure, that name "
    "belongs in the card, and leaving it out is the single worst mistake you "
    "can make on that card.\n"
    "If a story has no power angle and no contest, go back to step 1 and "
    "decline it.\n"
    "\n"
    "== STEP 3: WRITE THE HEADLINE ==\n"
    "Name the CONVERSATION, not the event. 'Marc Lore sells the Timberwolves "
    "for $4.5 billion' is an event. 'Another NBA franchise changes hands to a "
    "buyer nobody voted for' is a conversation.\n"
    "EACH CLUSTER CARRIES A REQUIRED HEADLINE SHAPE, written on the cluster "
    "as 'REQUIRED HEADLINE SHAPE = ...'. Obey it exactly. It is not a "
    "suggestion. A card whose headline is in the wrong shape is a failed card "
    "even when every fact in it is right. If the assigned shape genuinely "
    "cannot carry the story, decline the cluster rather than writing it in a "
    "different shape.\n"
    "\n"
    "== WHAT A SECOND CLAUSE MAY AND MAY NOT DO ==\n"
    "This is the rule people get backwards, so read it twice.\n"
    "ALLOWED, and often the whole point: a second clause carrying a CONCRETE "
    "contrast or consequence. 'Zuckerberg buys a castle while nobody on his "
    "app can afford a house.' 'Blue Origin gets 26 football fields in Hutto "
    "while the county gives up the tax base.' These are specific, checkable, "
    "and they carry the opinion.\n"
    "BANNED: a second clause that LABELS the meaning in the abstract. Never "
    "write 'is a David-vs-Goliath fight', 'is a test of state versus federal "
    "power', 'is a stark reminder that', 'shows the tension between', 'marks "
    "a turning point for'. That is a critic summarizing a story instead of "
    "telling one.\n"
    "Test: if the clause names PEOPLE, MONEY or a THING, keep it. If it names "
    "an abstraction (a fight, a tension, a reminder, an era), cut it.\n"
    "Use full names on first mention (Greg Abbott, not Abbott) and keep the "
    "concrete subject (the Venezuelan man, the hemp industry).\n"
    "\n"
    "== THE PUSH-QUOTE (data_point) ==\n"
    "One hook that reads as a pull-quote under the headline: a number that "
    "crosses a real threshold ('US strategic petroleum reserve falls below "
    "300M barrels for the first time in 40+ years'), a named person saying "
    "something contestable ('Sophie Cunningham says the commissioner should "
    "be fired'), or a moment that is weird, local or a symbol (a Flock camera "
    "stolen while draped in an American flag). Not every number is a hook. A "
    "story with no number can still be a card when the quote or the moment "
    "carries it.\n"
    "\n"
    "== THE PARAGRAPH ==\n"
    "One to three sentences. Lead with the concrete fact: who, what, how "
    "much. Then the observation that the headline earned. Then stop.\n"
    "You may hold a position. You may not moralize. Banned constructions: "
    "'it is not just about X, it is about Y', 'this is a reminder that', "
    "'that is what matters', 'only time will tell', 'the implications are "
    "significant'. If a sentence would survive being pasted into any other "
    "story, delete it.\n"
    "\n"
    "== STANDING RULES ==\n"
    "THE OUTLET IS NOT THE STORY. Never write 'TechCrunch reported X'. The "
    "fact is the subject. Name a masthead only when who reported it is itself "
    "the fact.\n"
    "ONE TOPIC PER CARD. If an article in the cluster is off-theme, leave it "
    "out and do not cite it.\n"
    "NO TWO CARDS ON THE SAME SHAPE. If several clusters are all 'this player "
    "is good' or 'this team is rising', card the strongest and decline the "
    "rest.\n"
    "PLAIN AND SPECIFIC. Concrete names and numbers from the articles, no "
    "puns, no metaphors, no jargon. Plain is not the same as neutral: a plain "
    "sentence can carry an opinion, and here it should.\n"
    "SOURCE IDS ARE PER-CLUSTER. Each cluster's article list starts at 0. "
    "source_ids must be the LOCAL indexes within THAT cluster's list, never a "
    "global count across clusters. If you cite only the first article of "
    'cluster 2, source_ids is [0], not [2].\n'
    "\n"
    "Output STRICT JSON only: "
    '{"cards": [{"narrative": "...", "paragraph": "...", '
    '"data_point": "...", "source_ids": [0, 2]}]} where source_ids are the '
    "LOCAL indexes of the articles in that cluster's list that the card "
    "grounds in. A declined cluster is "
    '{"narrative": null} and still occupies its position in the list.'
)


# The model will not reliably honor a negative instruction. Measured
# 2026-08-21: with "is a reminder that" explicitly banned in the prompt, two of
# eight headlines came back carrying it, plus four moralizing tails after an em
# dash. So the ban is enforced here, in code, where it cannot be ignored.
#
# Two repairs, both deterministic:
#   TAIL   "...buying in - but the math may not add up."   -> drop the tail.
#          The sentence before the dash is already complete; the tail is a
#          critic summarizing the story instead of telling it.
#   PIVOT  "X is a reminder that Y" / "X shows that Y"     -> keep Y.
#          Y is the actual claim; X is throat-clearing. Truncating before the
#          pivot would leave a fragment, so we keep the far side instead.
# A trailing conjunction clause after a dash is always the critic's tail.
_TAIL_CONJUNCTIONS = ("and", "but", "so", "yet", "which")
_DASHES = ("\u2014", "\u2013")

_PIVOTS = (
    " is a reminder that ", " is a stark reminder that ", " shows that ",
    " is a test of ", " marks a turning point for ", " highlights that ",
    " underscores that ", " signals that ", " is proof that ",
)

# Turns that answer nothing. A headline ending in one of these is a shrug and
# the card reads as formula. Cut the clause; the first half stands alone.
# The same abstraction wearing a concrete costume. Measured 2026-08-23: four
# of eight headlines used one of these. They are CUT, not pivoted: the claim
# is the half before the turn, and the half after is the shrug.
_EMPTY_TURNS = (
    ", but the real story is", ", but the real cost is",
    ", but the real issue is", ", and the real story is",
    ", but the real question is", ", but the real winners are",
    ", and the nba's ownership shuffle continues",
    ", but who benefits?", ", and that's the point.", ", but at what cost?",
    ", and that's the problem.", ", but the story continues.",
    ", and the shuffle continues.", ", but it's complicated.",
    ", and the nba's ownership shuffle continues.",
)


# Measured 2026-08-23: telling the model to "vary the shape" does not vary the
# shape. Given one approved example (the concrete contrast clause), it wrote
# eight of eight headlines as "[fact], but [the real thing]". The previous
# prompt produced thirteen of thirteen as subject-verb-object. A rule phrased
# as a constraint on a shape teaches that shape, so the shape is now ASSIGNED
# per cluster and rotated, not requested.
_SHAPES = [
    ("FLAT", "One flat declarative sentence stating the claim. No second "
             "clause, no conjunction, no question. Example: 'Texas is "
             "becoming a company town for rockets.'"),
    ("CONTRAST", "Two concrete halves joined by 'while' or 'but', where "
                 "the second half names people, money or a thing, never an "
                 "abstraction. Example: 'Mark Zuckerberg buys a castle while "
                 "nobody on his app can afford a house.'"),
    ("QUESTION", "A direct question the card then answers in the paragraph. "
                 "Example: 'Who actually owns the Lakers now?'"),
    ("FACT", "A single startling fact stated bare, with the number in it and "
             "no commentary at all. Example: 'In the US you can get a felony "
             "and six years in prison for sleeping in your car.'"),
    ("NAMED", "A named person or company on the hook for something. Example: "
              "'Palantir wants zero data retention for everyone except "
              "Palantir.'"),
]


def repair_narrative(text):
    """Strip the abstraction the prompt bans. Returns (text, note or None)."""
    if not text:
        return text, None
    original = text
    for pivot in _PIVOTS:
        i = text.lower().find(pivot)
        if i > 0:
            text = text[i + len(pivot):].strip()
            text = text[:1].upper() + text[1:]
            break
    low0 = text.lower()
    for turn in _EMPTY_TURNS:
        i = low0.find(turn.lower())
        if i > 0:
            text = text[:i].rstrip(" ,;") + "."
            break
    for dash in _DASHES:
        i = text.find(dash)
        if i > 0 and text[i + 1:].lstrip().split(" ")[0].lower().strip(",") in _TAIL_CONJUNCTIONS:
            text = text[:i].rstrip(" ,;")
            if not text.endswith("."):
                text += "."
            break
    # Micah does not use em dashes anywhere, and this is his copy.
    text = text.replace("\u2014", ", ").replace(" ,", ",")
    while ",," in text:
        text = text.replace(",,", ",")
    while "  " in text:
        text = text.replace("  ", " ")
    text = text.replace(" ,", ",").strip()
    return text, (original if text != original else None)


def render_brief_html(clusters, parsed, run_dir):
    """Render the LLM cards into web/brief.html with article links resolved
    from source_ids (indexes into each cluster's item list)."""
    from datetime import datetime, timezone as _tz
    import html as _html

    cards_html = []
    for ci, card in enumerate(parsed.get("cards", [])):
        if not card.get("narrative"):
            continue  # declined cluster
        # Use the content-aligned cluster index when present
        cluster_idx = card.get("_cluster_idx", ci)
        cl = clusters[cluster_idx] if cluster_idx < len(clusters) else None
        if not cl:
            continue
        sources = []
        # Don't trust model source_ids (they drift after re-alignment) —
        # match the card text against each article in the cluster to find
        # which ones the card actually cites.
        card_text = f"{card.get('narrative','')} {card.get('paragraph','')}".lower()
        card_tokens = set(re.findall(r"[a-z']{4,}", card_text))
        # Strongly prefer articles whose title shares multiple card tokens
        scored_items = []
        for sid, item in enumerate(cl["items"]):
            a = item["article"]
            title = a.get("title", "").lower()
            title_tokens = set(re.findall(r"[a-z']{4,}", title))
            overlap = len(card_tokens & title_tokens)
            scored_items.append((overlap, sid, a))
        scored_items.sort(key=lambda x: -x[0])
        for overlap, sid, a in scored_items[:3]:
            if overlap >= 2:
                sources.append(
                    f'<li><a href="{a.get("link","#")}" target="_blank" rel="noopener">{_html.escape(a.get("title",""))} <span class="src">({a.get("source","")})</span></a></li>'
                )
        if not sources and cl["items"]:
            # Fallback: lead article of the cluster
            a = cl["items"][0]["article"]
            sources.append(
                f'<li><a href="{a.get("link","#")}" target="_blank" rel="noopener">{_html.escape(a.get("title",""))} <span class="src">({a.get("source","")})</span></a></li>'
            )
        dp_html = f'<p class="brief-dp">▸ {_html.escape(card.get("data_point",""))}</p>' if card.get("data_point") else ""
        para_html = f'<p class="brief-para">{_html.escape(card.get("paragraph",""))}</p>' if card.get("paragraph") else ""
        cards_html.append(f"""
    <article class="brief-card">
      <h3 class="brief-title">{_html.escape(card.get("narrative",""))}</h3>
      {dp_html}
      {para_html}
      <ul class="brief-list">{''.join(sources)}</ul>
    </article>""")

    ts = datetime.now(_tz.utc).strftime("%Y-%m-%d %H:%M UTC")
    meta = json.load(open(os.path.join(run_dir, "meta.json"))) if os.path.exists(os.path.join(run_dir, "meta.json")) else {}
    run_ts = (meta.get("timestamp") or ts)[:19].replace("T", " ")
    html = f"""<!DOCTYPE html>
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
  .brief-para {{ font-size:.9rem; line-height:1.55; color:var(--ink-light); margin-bottom:.6rem; }}
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
  <div class="page-meta">Narrative brief · LLM desk · run {meta.get('code_version','?')} · {run_ts} · updated {ts}</div>
  {''.join(cards_html)}
  <a class="back" href="index.html">← Back to feed</a>
</div>
</body>
</html>
"""
    with open(os.path.join(WEB, "brief.html"), "w") as f:
        f.write(html)
    print(f"Rendered web/brief.html with {len(cards_html)} cards")


def git_sha():
    try:
        out = subprocess.run(
            ["git", "-C", REPO, "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, timeout=10,
        )
        return out.stdout.strip() or "unknown"
    except Exception:
        return "unknown"


def pool_key(clusters):
    """Hash of the STORY IDENTITY — sorted article titles+links across all
    clusters. Excludes cluster order, one-off names, and anything volatile,
    so an unchanged set of stories never regenerates (fixes the 'good
    headline became bad' regression: same stories, different hash, bad rerun).
    """
    stories = set()
    for cl in clusters:
        for item in cl["items"]:
            a = item["article"]
            stories.add(a.get("link", "") or a.get("title", ""))
    material = sorted(stories)
    return hashlib.sha256("\n".join(material).encode()).hexdigest()[:16]


def load_clusters():
    """Load clusters + one-off qualifiers from the deterministic layer.

    v4 (NEWS-ENGINE-SPEC.md R1/R3): no admission gate — the desk sees
    signature clusters PLUS quote/moment stories that don't cluster."""
    sys.path.insert(0, os.path.join(REPO, "scripts"))
    import brief
    with open(os.path.join(WEB, "articles.json")) as f:
        data = json.load(f)

    scored = [a for a in data["articles"] if not a.get("_noise")]
    scored.sort(key=lambda x: -x.get("_score", 0))

    from collections import OrderedDict
    enriched = []
    for a in scored:
        points = brief.mine_data_points(a)
        sig, hits = brief.signature_for(a, points)
        quote = brief._quote_from_article(a)
        moment = brief._moment_from_article(a)
        seed_hits = brief._seed_match(a)
        enriched.append({
            "article": a, "points": points, "sig": sig, "hits": hits,
            "quote": quote, "moment": moment, "seed_hits": seed_hits,
        })

    # Signature clusters
    clusters = OrderedDict()
    for e in enriched:
        if e["sig"]:
            name = e["sig"]["name"]
            clusters.setdefault(name, {"sig": e["sig"], "items": []})
            clusters[name]["items"].append(e)

    # One-off qualifiers: quote or moment stories with no signature, but
    # with a tweet-seed hit (the voice cares). These get their own cluster
    # so the desk can card them individually.
    one_offs = OrderedDict()
    for e in enriched:
        if e["sig"]:
            continue
        if (e["quote"] or e["moment"]) and e["seed_hits"] > 0:
            name = e["article"].get("title", "")[:50]
            one_offs.setdefault(name, {"sig": {"name": "One-off: " + name[:40], "voice_weight": 1.0}, "items": []})
            one_offs[name]["items"].append(e)

    all_clusters = list(clusters.values()) + list(one_offs.values())

    # Dedup same-shape one-offs (NEWS-ENGINE-SPEC: no four 'player is good'
    # cards). If multiple one-off clusters match the same story-shape regex,
    # keep only the highest-scored one and drop the rest. This collapses
    # 'Marina Mabrey is good', 'Kaitlyn Chen is good', 'Megan DiLeo is
    # good' into one slot so the brief has room for actual narratives.
    _PLAYER_GOOD = re.compile(
        r"(meteoric rise|leading by example|is (?:a|the) (?:star|reason|key|face)"
        r"|growth and success|elevating|championship|newest star"
        r"|finding (?:their|its) (?:identity|gems|way)|rise in|is (?:putting|taking)"
        r"|meteoric|has been (?:a|the) (?:revelation|breakout)|is thriving|is finding)",
        re.I,
    )
    seen_shape = {}
    deduped = []
    for cl in all_clusters:
        if not cl["sig"]["name"].startswith("One-off"):
            deduped.append(cl)
            continue
        title = cl["sig"]["name"]
        shape = "player_good" if _PLAYER_GOOD.search(title) else "other"
        if shape == "player_good":
            if shape in seen_shape:
                print(f"  DROPPED same-shape one-off: {title[:60]}")
                continue  # already have one 'player is good' card
            seen_shape[shape] = True
        deduped.append(cl)
    all_clusters = deduped

    # Rank clusters by voice weight × (seed boost + size) × lead score, cap
    # the desk input so it doesn't drown in one-offs. Seed hits are the
    # voice's own priorities — they outrank generic volume. One-offs with a
    # seed hit get a strong priority so a Flock/WNBA story isn't crowded
    # out by a 14-article macro cluster.
    def cluster_score(cl):
        sig = cl["sig"]
        vw = sig.get("voice_weight", 0.5)
        items = cl["items"]
        total_seed = sum(i.get("seed_hits", 0) for i in items)
        lead_score = items[0]["article"].get("_score", 0)
        is_one_off = sig.get("name", "").startswith("One-off")
        # One-offs with seed hits punch above their size
        if is_one_off:
            return (vw, total_seed * 3, len(items), lead_score)
        return (vw, total_seed, len(items), lead_score)

    # Hard cap on one-offs: keep at most 3 one-off clusters (the strongest
    # by seed+score) so single stories can't crowd the real narratives.
    # A brief should be themes first, one-offs as spice. Signature clusters
    # are unaffected. (NEWS-ENGINE-SPEC R3: one-offs qualify, they don't
    # dominate — Micah: 'how many f*cking cards are we gonna be talking
    # about how womens sports has good players'.)
    # Seed-matched one-offs (stories Micah explicitly posts about) get FIRST
    # dibs on the slots — a 40-yr NCAAF or NBA->WNBA story must not lose a
    # slot to a generic player story on raw score. (Measured: College
    # Football Landscape, seed=1, 3 data points, was ranked out.)
    one_off_clusters = [c for c in all_clusters if c["sig"]["name"].startswith("One-off")]
    sig_clusters = [c for c in all_clusters if not c["sig"]["name"].startswith("One-off")]

    seeded = [c for c in one_off_clusters if sum(i.get("seed_hits", 0) for i in c["items"]) > 0]
    unseeded = [c for c in one_off_clusters if sum(i.get("seed_hits", 0) for i in c["items"]) == 0]
    seeded.sort(key=cluster_score, reverse=True)
    unseeded.sort(key=cluster_score, reverse=True)
    # Seeded one-offs fill the cap first, then unseeded by score.
    kept_one_offs = seeded[:3] + unseeded[: max(0, 3 - len(seeded[:3]))]
    print(f"  {len(one_off_clusters)} one-offs ({len(seeded)} seeded), keeping 3 (seeded first)")
    all_clusters = sig_clusters + kept_one_offs

    all_clusters.sort(key=cluster_score, reverse=True)
    # Keep the strongest 14 for the desk (12 signature clusters + top 2-6
    # one-offs), balanced so a single huge cluster doesn't crowd the field
    return all_clusters[:14]


def call_model(clusters):
    """Call the LLM with the cluster material. Returns raw JSON string."""
    import urllib.request

    # Use NOUS_PORTAL_KEY — the DEEPSEEK_API_KEY in config is dead/out of funds
    # (measured 2026-08-21: 401 on chat, portal key returns 200).
    key = os.environ.get("NOUS_PORTAL_KEY", "")
    if not key:
        env_path = "/root/.hermes/.env"
        if os.path.exists(env_path):
            for line in open(env_path):
                if line.startswith("NOUS_PORTAL_KEY="):
                    key = line.strip().split("=", 1)[1].strip('"').strip("'")
                    break
    if not key:
        raise RuntimeError("No NOUS_PORTAL_KEY found in /root/.hermes/.env")

    prompt_lines = ["Today's date: %s" % datetime.now(timezone.utc).strftime("%Y-%m-%d"), ""]
    for ci, cl in enumerate(clusters):
        _shape_name, _shape_rule = _SHAPES[ci % len(_SHAPES)]
        prompt_lines.append(f"CLUSTER {ci}: {cl['sig']['name']} (voice_weight {cl['sig'].get('voice_weight','?')})")
        prompt_lines.append(f"  REQUIRED HEADLINE SHAPE = {_shape_name}. {_shape_rule}")
        for item in cl["items"]:
            a = item["article"]
            prompt_lines.append(f"  {item['points'][0][:200] if item['points'] else 'no data point'}")
            prompt_lines.append(f"  {a.get('title','')} ({a.get('source','')})")
            body = (a.get("_body", "") or "")[:600]
            if body:
                prompt_lines.append(f"    {body[:300]}")
        prompt_lines.append("")

    body = json.dumps({
        "model": MODEL,
        "messages": [
            {"role": "system", "content": _SYSTEM},
            {"role": "user", "content": "\n".join(prompt_lines)},
        ],
        "temperature": 0.7,
        "max_tokens": 3000,
        "reasoning": {"enabled": False},  # we want content, not a thinking dump
        "response_format": {"type": "json_object"},
    }).encode()

    req = urllib.request.Request(
        PROVIDER_BASE + "/chat/completions",
        data=body,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {key}",
            # urllib sends 'Python-urllib/3.8' by default; some gateways 403 it
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) narrative-desk/1.0",
        },
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = json.loads(resp.read().decode())
    return data["choices"][0]["message"]["content"]


def _prev_cards_by_story():
    """Map story-link → existing card from the latest run, for keep-good-cards."""
    latest = os.path.join(RUNS, "latest")
    cards_path = os.path.join(latest, "cards.json")
    inp_path = os.path.join(latest, "input.json")
    if not (os.path.exists(cards_path) and os.path.exists(inp_path)):
        return {}
    try:
        cards = json.load(open(cards_path)).get("cards", [])
        inp = json.load(open(inp_path)).get("clusters", [])
    except Exception:
        return {}
    result = {}
    for ci, card in enumerate(cards):
        if not card.get("narrative"):
            continue
        cl = inp[ci] if ci < len(inp) else None
        if not cl:
            continue
        # The cluster's story set = its article links
        links = frozenset(it.get("link", "") for it in cl.get("items", []))
        if links:
            result[links] = card
    return result


def _cluster_links(cl):
    return frozenset(
        item["article"].get("link", "") or item["article"].get("title", "")
        for item in cl["items"]
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true", help="regenerate even if pool unchanged")
    args = ap.parse_args()

    clusters = load_clusters()
    key = pool_key(clusters)
    os.makedirs(RUNS, exist_ok=True)

    # Pool-key dedup: skip if the last run used the same material
    meta_path = os.path.join(RUNS, "latest", "meta.json")
    if os.path.exists(meta_path) and not args.force:
        with open(meta_path) as f:
            last = json.load(f)
        if last.get("pool_key") == key:
            print(f"Pool unchanged ({key}) — skipping. Use --force to regenerate.")
            return 0

    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    run_dir = os.path.join(RUNS, ts)
    os.makedirs(run_dir, exist_ok=True)
    # Keep a stable 'latest' pointer
    latest = os.path.join(RUNS, "latest")
    if os.path.islink(latest):
        os.remove(latest)
    elif os.path.exists(latest):
        import shutil
        shutil.rmtree(latest)
    os.symlink(run_dir, latest)

    with open(os.path.join(run_dir, "input.json"), "w") as f:
        json.dump(
            {
                "clusters": [
                    {
                        "name": cl["sig"]["name"],
                        "voice_weight": cl["sig"].get("voice_weight"),
                        "items": [
                            {
                                "title": item["article"].get("title"),
                                "source": item["article"].get("source"),
                                "link": item["article"].get("link"),
                                "points": item["points"],
                                "body_excerpt": (item["article"].get("_body") or "")[:600],
                            }
                            for item in cl["items"]
                        ],
                    }
                    for cl in clusters
                ]
            },
            f, indent=2,
        )

    print(f"Calling {MODEL} with {len(clusters)} clusters...")
    raw = call_model(clusters)
    with open(os.path.join(run_dir, "output.json"), "w") as f:
        f.write(raw)

    parsed = json.loads(raw)

    # Keep-good-cards: if a cluster's story set was already carded in the
    # previous run, prefer that card over a fresh (possibly worse) generation.
    # This stops a good headline from degrading when the pool shifts and
    # forces a rerun of everything. (Measured 2026-08-21: same Minnesota
    # story, two runs, good headline → vague headline.)
    prev_cards = _prev_cards_by_story()
    kept = 0
    new_cards = []
    for ci, card in enumerate(parsed.get("cards", [])):
        if not card.get("narrative"):
            new_cards.append(card)
            continue
        cl = clusters[ci] if ci < len(clusters) else None
        if cl is None:
            new_cards.append(card)
            continue
        links = _cluster_links(cl)
        prev = prev_cards.get(links)
        if prev and prev.get("narrative"):
            kept += 1
            new_cards.append(prev)  # keep the old, known-good card
        else:
            new_cards.append(card)
    if kept:
        print(f"Kept {kept} existing cards (unchanged story sets)")
    parsed["cards"] = new_cards

    # === FIX CARD-CLUSTER ALIGNMENT (measured 2026-08-21) ===
    # The model sometimes returns cards out of order or skips a cluster, so
    # positional mapping (cards[i] -> clusters[i]) attaches the wrong sources.
    # Re-align content-based: find each card's best-matching cluster by
    # keyword overlap between the card text and the cluster's article titles.
    aligned = []
    used_clusters = set()
    for card in parsed.get("cards", []):
        if not card.get("narrative"):
            aligned.append(card)  # declined — keep placeholder
            continue
        card_text = f"{card.get('narrative','')} {card.get('paragraph','')}".lower()
        best_ci = None
        best_score = 0
        for ci, cl in enumerate(clusters):
            if ci in used_clusters:
                continue
            cl_text = " ".join(
                item["article"].get("title", "") for item in cl["items"]
            ).lower()
            # Count shared meaningful tokens
            tokens = set(re.findall(r"[a-z']{4,}", card_text))
            overlap = sum(1 for t in tokens if t in cl_text)
            if overlap > best_score:
                best_score = overlap
                best_ci = ci
        if best_ci is not None and best_score > 0:
            used_clusters.add(best_ci)
            card["_cluster_idx"] = best_ci
        aligned.append(card)
    parsed["cards"] = aligned

    with open(os.path.join(run_dir, "cards.json"), "w") as f:
        json.dump(parsed, f, indent=2)

    # Render the cards into brief.html (resolving source_ids → article links)
    for _card in parsed.get("cards", []):
        _fixed, _was = repair_narrative(_card.get("narrative"))
        if _was:
            print(f"  REPAIRED headline: {_was}")
            print(f"                 -> {_fixed}")
            _card["narrative"] = _fixed
        _p, _pw = repair_narrative(_card.get("paragraph"))
        if _pw:
            _card["paragraph"] = _p

    # The prompt asks for at most 8 cards and the model does not reliably
    # obey it (measured 2026-08-21: 8 cards on one run, 12 on the next from the
    # same pool). Clusters reach the model already sorted by cluster_score, so
    # the cap is just "keep the top N that were not declined". Micah's
    # complaint was volume of filler, and a cap is the only thing that
    # guarantees it.
    _max = int(os.environ.get("IH_MAX_CARDS", "8"))
    _kept, _dropped = [], 0
    for _card in parsed.get("cards", []):
        if not _card.get("narrative"):
            _kept.append(_card)
            continue
        if len([c for c in _kept if c.get("narrative")]) >= _max:
            _card["narrative"] = None
            _dropped += 1
        _kept.append(_card)
    if _dropped:
        print(f"  CAPPED at {_max} cards; dropped {_dropped} lower-ranked")
    parsed["cards"] = _kept

    render_brief_html(clusters, parsed, run_dir)

    meta = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "code_version": git_sha(),
        "model": MODEL,
        "pool_key": key,
        "n_clusters": len(clusters),
        "prompt_hash": hashlib.sha256(_SYSTEM.encode()).hexdigest()[:12],
    }
    with open(os.path.join(run_dir, "meta.json"), "w") as f:
        json.dump(meta, f, indent=2)

    print(f"Wrote run {ts} ({key})")
    for card in parsed.get("cards", []):
        if card.get("narrative"):
            print(f"  - {card['narrative'][:80]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
