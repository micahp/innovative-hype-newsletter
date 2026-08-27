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
import urllib.request
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
    "cluster. There is no cap on the number of cards: write one for every "
    "cluster that earns it and decline the rest.\n"
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
    "== STEP 2: THE ANGLE ==\n"
    "EVERY CARD MUST REPORT angle_id, and it is never omitted. Its value is "
    "either one of the angle ids offered on that cluster or the string "
    '"none". A card without angle_id is a failed card.\n'
    "Each cluster lists the angles legal for it. Those are positions the author "
    "actually holds, and the list is the ONLY place an opinion may come from. "
    "Pick at most one, and only if it genuinely fits this story. Report the "
    "one you used as angle_id. If none of the listed angles fits, or the "
    "cluster says no angle is in scope, then report the story straight with no "
    "editorial turn, or decline it. Never import an opinion that is not on the "
    "list for this cluster: an angle about housing does not belong on a story "
    "about chip financing no matter how strongly the author feels about "
    "housing.\n"
    "== FIND THE POWER ANGLE ==\n"
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
    "EVERY CARD MUST NAME ITS CLUSTER. Include cluster_index, the number "
    "printed on the CLUSTER line it was written from. Without it the card gets "
    "matched to the wrong cluster and cited to the wrong publishers.\n"
    "Output STRICT JSON only: "
    '{"cards": [{"cluster_index": 0, "angle_id": "..." or null, '
    '"narrative": "...", "paragraph": "...", '
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
    ("CONTRAST", "Two halves joined by 'while' or 'but'. THE SECOND HALF "
                 "MUST BE ABOUT AN ACTOR DOING AN OBSERVABLE THING, never "
                 "about a concept. Test the SUBJECT of that clause: if it is "
                 "a person, a company or a group, keep it; if it is value, "
                 "dynamics, implications, the real story, the true anything, "
                 "cut the clause and stop after the first half. The paragraph "
                 "adds the taste; the headline does not. "
                 "GOOD: 'Good Good Golf deletes a violent ad while Callaway "
                 "stays silent on its involvement.' "
                 "GOOD: 'Mark Zuckerberg buys a castle while nobody on his "
                 "app can afford a house.' "
                 "BAD: '...while the true power dynamics behind creator-brand "
                 "partnerships remain hidden.' "
                 "BAD: '...while the value flows to incumbents.' "
                 "Both BAD lines look concrete and obey the shape. They fail "
                 "because a concept is doing the acting."),
    ("QUESTION", "A direct question the card then answers in the paragraph. "
                 "Example: 'Who actually owns the Lakers now?'"),
    ("FACT", "A single startling fact stated bare, with the number in it and "
             "no commentary at all. Example: 'In the US you can get a felony "
             "and six years in prison for sleeping in your car.'"),
    ("NAMED", "A named person or company on the hook for something. Example: "
              "'Palantir wants zero data retention for everyone except "
              "Palantir.'"),
]


# === THE TYPE GATE ===
#
# Micah, 2026-08-21: "how many cards are we just gonna be talking about how
# womens sports has good players and there playing well??? thats like 4 cards".
# The prompt has told the model to decline these since that day and it declines
# unreliably: on 2026-08-23 it still carded Angel Reese's 31 points and
# Alabama's quarterback competition. Third time learning the same thing, so it
# is written down here instead of in another prompt sentence: A NEGATIVE
# INSTRUCTION IS NOT A GATE.
#
# The test is two-sided on purpose, because a one-sided keyword ban would kill
# the stories he most wants. "Sophie Cunningham says the WNBA commissioner
# should be fired" is a WNBA story full of performance vocabulary and it is
# exactly the kind of card the brief exists for. So:
#
#   DECLINE only when the card is about someone doing their job well
#   (_PERFORMANCE) AND carries no money, power, law or rule angle (_POWER).
#
# The power list wins ties. A false keep costs one mediocre card; a false
# decline throws away the story he asked for.
_PERFORMANCE = (
    "career-high", "career high", "season-high", "points", "rebounds",
    "assists", "yards", "touchdown", "home run", "goals", "hat trick",
    "scoring record", "single-game", "triple-double", "double-double",
    "starting quarterback", "named starter", "starting job", "depth chart",
    "player of the week", "player of the month", "mvp race", "rookie of the",
    "breakout", "meteoric rise", "is becoming a star", "leads the league",
    "big game", "stat line", "all-star selection", "lineup", "roster move",
    "quarterback battle", "quarterback competition", "wins the job",
    # The adjacent no-story type: a routine roster or showcase event. Same
    # verdict, same veto. "Basketball Without Borders brings 40 top
    # high-school players to Chicago" carded on 2026-08-23 and is a calendar
    # entry, not a story.
    # Abbreviations. "starting quarterback" was a marker; "starting QB" was not,
    # and publishers write the short form. Same for the award acronyms.
    "starting qb", "qb battle", "qb competition", "qb1", "starting rb",
    "starting job", "dpoy", "poy", "all-american", "all-conference",
    "five-star", "four-star", "recruit", "signee", "snaps in",
    "starting point guard", "new starting", "who will start", "starting lineup",
    "players from", "has not beaten", "winless", "losing streak", "power rankings",
    "preseason rankings", "brings sun belt", "transfer portal move",
    "commit to", "commits to", "committed to", "commitment", "decommit",
    "transfer portal", "enters the portal", "signs with", "signing with",
    "poaching", "reuniting with", "football program", "basketball program",
    "leaves the program", "leaves the team", "joins the program",
    "steps down", "hired as", "named head coach", "walk-on",
    "fifth year of eligibility", "redshirt", "depth chart", "starting job",
    "high-school players", "top players", "showcase", "all-star weekend",
    "training camp opens", "schedule released", "lineup announced",
    "roster announced", "draft class", "recruiting class", "signing day",
)
_POWER = (
    # money and ownership
    "sells", "sold", "sale", "buys", "acquisition", "valuation", "stake",
    "owner", "ownership", "investor", "private equity", "billion", "million",
    "revenue", "media deal", "rights deal", "sponsorship", "payroll", "salary cap",
    # law, rule and governance
    "lawsuit", "sues", "sued", "judge", "court", "ruling", "rules that",
    "settlement", "arrested", "banned", "suspended", "investigation",
    "eligibility", "age limit", "rule change", "commissioner", "fired",
    "union", "strike", "collective bargaining", "antitrust", "congress",
    "regulator", "subpoena", "fine", "violation", "protest", "boycott",
    # someone with a platform saying something contestable
    "should be fired", "called out", "accused", "criticized", "slammed",
    "demanded", "walked out", "refused",
)


def performance_only(text):
    """True when this is 'an athlete did their job well' and nothing more."""
    low = (text or "").lower()
    if not any(k in low for k in _PERFORMANCE):
        return False
    return not any(k in low for k in _POWER)


def _lead_source_text(card, cluster):
    """Title (+ short summary) of the article this card is actually built on.

    Stable across runs. The generated headline is not: the desk rewrites it
    every two hours, so the same story arrives as "Angel Reese's career-high 31
    points" on one run and "Angel Reese's 31-point night makes Dream history"
    on the next. A keyword gate over regenerated text leaks on rephrasings, and
    it leaked twice on 2026-08-23 while I topped the vocabulary up. The
    publisher's headline does not move.
    """
    for srec in (card.get("_sources") or []):
        if srec.get("headline"):
            return srec["headline"]
    if cluster:
        for item in cluster.get("items", []):
            a = item.get("article", {})
            t = a.get("title", "")
            if t:
                return t + " " + (a.get("summary") or "")[:300]
    return ""


def card_is_performance_only(card, cluster):
    """Decline 'someone did their job well' / roster churn, judged on SOURCE.

    Two-sided as always: performance or roster markers present AND no money,
    ownership, law, rule or someone-said-something angle. The power side wins
    ties, because a false keep costs one mediocre card and a false decline
    loses a story Micah asked for.

    The generated headline is still consulted as a SECOND route in, so a card
    that invents roster framing the source did not have is still caught. But
    the source alone can decline, and that is what makes the verdict stable.
    """
    src = _lead_source_text(card, cluster).lower()
    head = (card.get("narrative") or "").lower()
    for text in (src, head):
        if not text:
            continue
        if any(k in text for k in _PERFORMANCE) and not any(k in text for k in _POWER):
            return True
    return False


    # huge transfer portal move" kept passing because its paragraph said
    # "million". The headline is the thing being judged, and the paragraph is
    # where the taste lives by design, so the gate reads the headline.
    own = card.get("narrative") or ""
    if not any(k in own.lower() for k in _PERFORMANCE):
        return False
    return not any(k in own.lower() for k in _POWER)


# === THE ANGLE INVENTORY ===
#
# 2026-08-23. A card read "Nvidia is turning compute into an asset class while
# the average person can't afford a home." No affordability claim was in the
# grounding. That was not a hallucination: it was a REAL position of Micah's,
# correctly retrieved, welded onto the wrong subject.
#
# The obvious fix (reject any clause not present in the article) is wrong. His
# right angle for that piece, that you will rent compute forever and never run
# local inference, is not in the article either. A presence check kills both.
#
# The distinction is SUBJECT SCOPE. An angle fires only on a story that is
# about the thing the angle is about. Housing cannot attach to a GPU financing
# story because it is out of scope, not because the words are missing.
#
# Scope is matched against TITLES and mined data points, never bodies. A body
# mentions everything; a title states the subject. Matching on bodies is how a
# housing angle finds a chip story in the first place.
ANGLES_PATH = os.path.join(REPO, "angles.yaml")


def load_angles():
    """The enabled angles from angles.yaml.

    This used to return [] on a missing yaml module, a missing file, or an
    unreadable one, and the desk would run "angle-free" while every card
    reported angle_id none. That is indistinguishable from a healthy run in
    which nothing happened to be eligible, which is exactly the state that hid
    the inventory being the rejected v1 for a day. It raises now.
    """
    import yaml
    if not os.path.exists(ANGLES_PATH):
        raise FileNotFoundError(
            "angles.yaml is missing at %s. Without it every card is written "
            "with no position and the brief still looks finished, so this "
            "raises rather than running angle-free." % ANGLES_PATH)
    doc = yaml.safe_load(open(ANGLES_PATH)) or {}
    rows = doc.get("angles", [])
    out, disabled, malformed = [], 0, 0
    for a in rows:
        if not a.get("enabled", True):
            disabled += 1
            continue
        scope = [str(x).lower().strip() for x in (a.get("scope") or []) if str(x).strip()]
        if a.get("id") and a.get("claim") and scope:
            out.append({"id": a["id"], "claim": a["claim"],
                        "subject": (a.get("subject") or "").strip(),
                        "scope": scope})
        else:
            malformed += 1
    if not out:
        raise RuntimeError(
            "angles.yaml parsed to 0 usable angles (%d rows, %d disabled, %d "
            "malformed). Every card would be written position-free."
            % (len(rows), disabled, malformed))
    return out


def cluster_subject_text(cl):
    """What the cluster is ABOUT: titles and data points only."""
    bits = []
    for item in cl.get("items", []):
        bits.append(item["article"].get("title", ""))
        bits.extend(item.get("points", []) or [])
    return " ".join(bits).lower()


# Cosine floor for an angle to be OFFERED on a cluster. Measured 2026-08-24 on
# the three stories that broke:
#
#   Marc Lore sells the Timberwolves for $4.5bn -> sports valuations 0.456,
#                                                  rent-vs-own compute  0.109
#   Nvidia turns compute into an asset class    -> rent-vs-own compute  0.427
#   Blue Origin's $674M factory in Williamson   -> housing              0.174
#
# The keyword version offered the housing angle on that last one, because the
# housing signature and the housing scope both contained the word `texas`.
# 0.30 sits above every wrong pair measured and below every right one. It is a
# tuned constant, not a law: scripts/calibrate_angles.py re-measures it against
# the current pool and prints what moves.
ANGLE_SIM_FLOOR = float(os.environ.get("IH_ANGLE_FLOOR", "0.30"))
ANGLE_MAX_OFFERED = 2


def angle_probe_text(a):
    """What an angle looks like to the embedding model.

    The claim alone is a sentence in his voice and embeds toward its rhetoric;
    the scope alone is a bag of nouns. Together with the extrapolated subject
    line they describe the CATEGORY the position is about, which is the thing
    a story has to be about for the position to be legal.
    """
    parts = [a["claim"]]
    if a.get("subject"):
        parts.append(a["subject"])
    parts.append("Subjects this covers: " + ", ".join(a["scope"]) + ".")
    return " ".join(parts)


def eligible_angles(cl, angles):
    """Angles whose SUBJECT covers this cluster's subject, by meaning.

    This was substring matching against a hand-written scope list until
    2026-08-24. Two failures, one mechanism: a scope wide enough to catch the
    right story caught every story (the housing angle fired on a rocket factory
    because both mention Texas), and a scope narrow enough to be safe caught
    nothing (53 of 62 angles were never once eligible across 758 cards).

    A word is not a subject. Similarity is computed between the cluster's
    titles and mined data points and the angle's claim + subject + scope, so a
    story about hyperscaler leasing can reach a position about renting your
    compute with no shared vocabulary at all.
    """
    if not cl or not angles:
        return []
    subject = cluster_subject_text(cl).strip()
    if not subject:
        # A cluster with no titles and no data points is an upstream failure.
        # Scoring it against everything would return whatever is nearest to
        # empty text, so it gets no angle and says so.
        print("  angle-match: cluster '%s' has no subject text; no angle offered"
              % (cl.get("sig", {}) or {}).get("name", "?"))
        return []
    import embed
    sims = embed.similarity([subject], [angle_probe_text(a) for a in angles])[0]
    hits = [(float(sc), a) for sc, a in zip(sims, angles) if sc >= ANGLE_SIM_FLOOR]
    hits.sort(key=lambda x: -x[0])
    return [(a, sc) for sc, a in hits[:ANGLE_MAX_OFFERED]]


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
    text, _cut = trim_interpretive_tail(text)
    while ",," in text:
        text = text.replace(",,", ",")
    while "  " in text:
        text = text.replace("  ", " ")
    text = text.replace(" ,", ",").strip()
    return text, (original if text != original else None)


# === THE RUNNING FEED ===
#
# Micah, 2026-08-23: "it's kinda more like the legendary picks one where I just
# want it to be timestamped... we don't have to be saying the same exact thing
# every single day and just adding to it, but every single day there is a new
# thing to talk about."
#
# So the brief stops being a digest that is thrown away and rebuilt every two
# hours, and becomes an accumulating feed. A card is identified by the set of
# article links behind it. First time that story set produces a card it enters
# the feed with a first_seen stamp. On later runs the same story set updates
# its text in place and KEEPS its original first_seen, so the feed reads as
# "this appeared at 2pm" rather than re-dating yesterday's story to now.
FEED_PATH = os.path.join(WEB, "brief-feed.json")
_LAST_DECLINES = []
FEED_MAX_AGE_H = float(os.environ.get("IH_FEED_MAX_AGE_H", "72"))


def load_feed():
    try:
        return json.load(open(FEED_PATH)).get("cards", [])
    except Exception:
        return []


def merge_into_feed(new_cards):
    """Add/refresh cards in the running feed. Returns the feed, newest first."""
    from datetime import datetime as _dt, timezone as _tz, timedelta as _td
    now = _dt.now(_tz.utc)
    existing = {c.get("story_key"): c for c in load_feed() if c.get("story_key")}
    for c in new_cards:
        k = c.get("story_key")
        if not k:
            continue
        prev = existing.get(k)
        if prev:
            # Keep the original first_seen; the story did not just happen.
            c["first_seen"] = prev.get("first_seen") or now.isoformat()
            c["updated"] = now.isoformat()
        else:
            c["first_seen"] = now.isoformat()
            c["updated"] = now.isoformat()
        existing[k] = c
    # A card the gates decline NOW must leave the feed, not linger for 72h
    # because an earlier run let it through. Measured 2026-08-23: the type gate
    # correctly declined "Why is Tennessee left out of ESPN's preseason power
    # rankings?" and it stayed on the page anyway, carried by the accumulating
    # store from a run twenty minutes earlier. Evict by headline subject, the
    # same identity the deduper uses, because the story key changes with the
    # source set.
    declined_subjects = {_headline_subject(d.get("headline"))
                         for d in _LAST_DECLINES
                         if d.get("headline")
                         and d.get("verdict") != "demoted_type_gate"}
    # Also evict on the SOURCE headline. The generated one is rewritten every
    # run, so matching only on it lets a card the gate just declined survive in
    # the feed under a different phrasing.
    declined_subjects |= {_headline_subject(d.get("source_headline"))
                          for d in _LAST_DECLINES
                          if d.get("source_headline")
                          and d.get("verdict") != "demoted_type_gate"}
    declined_subjects.discard(())
    evicted_keys = set()
    for k in [k for k, c in existing.items()
              if _headline_subject(c.get("narrative")) in declined_subjects
              or _headline_subject((c.get("sources") or [{}])[0].get("headline"))
              in declined_subjects]:
        print(f"  EVICTED (now declined): {existing[k].get('narrative','')[:64]}")
        # PHASE 2 (2026-08-27): eviction is a STATE, not a deletion. The card
        # stops rendering, but its row survives in cards.jsonl with state
        # "evicted" so nothing is ever thrown away by this path again.
        evicted_keys.add(k)

    cutoff = now - _td(hours=FEED_MAX_AGE_H)
    out = []
    aged_keys = set()
    for k, c in existing.items():
        # Evicted cards do NOT render again, ever — the eviction stands, the
        # row survives only in the store.
        if k in evicted_keys:
            continue
        try:
            seen = _dt.fromisoformat(c.get("first_seen"))
        except Exception:
            continue
        if seen >= cutoff:
            out.append(c)
        else:
            # PHASE 2: aging out is recorded, not applied by absence.
            aged_keys.add(k)
    if aged_keys:
        print(f"  FEED aged_out {len(aged_keys)} card(s) past the "
              f"{FEED_MAX_AGE_H:g}h window (recorded in cards.jsonl)")
    out.sort(key=feed_rank, reverse=True)

    # --- DURABLE STORE WRITE-THROUGH (Phase 2) ---
    # Every run writes every card it processed into cards.jsonl: still
    # rendering as "live", evictions as "evicted", fallen out of the window
    # as "aged_out" — nothing is dropped on the floor anymore. If anything
    # here breaks, the run fails loudly rather than rendering a brief over a
    # silent hole in the record.
    import card_store as _store
    _overrides = {k: "evicted" for k in evicted_keys}
    _overrides.update({k: "aged_out" for k in aged_keys})
    _store.record_run(list(existing.values()),
                      state_overrides=_overrides,
                      run_ts=now.isoformat())

    return out


# Micah, 2026-08-23: "i also dont think we necessarily need to gate that out.
# it more so shouldnt be the highest ranking thing. like why is this the first
# card?"
#
# Right, and the answer was embarrassing: the feed sorted by first_seen. There
# was no editorial rank in it at all, so card #1 was whichever story happened
# to land most recently. Everything I had built to that point was a GATE (keep
# or delete) when the actual complaint was ORDER.
#
# So the performance/roster signal stops deleting cards and becomes a heavy
# demotion. The card stays, he can see it, and it sits where it belongs.
FEED_RECENCY_HALFLIFE_H = float(os.environ.get("IH_FEED_HALFLIFE_H", "18"))
SOFT_PENALTY = float(os.environ.get("IH_SOFT_PENALTY", "4.0"))


def feed_rank(card):
    """Editorial rank for one feed card. Higher sorts first."""
    from datetime import datetime as _dt, timezone as _tz
    score = float(card.get("lead_score") or 0)
    score *= float(card.get("voice_weight") or 0.5) + 0.5   # 0.5x .. 1.5x
    try:
        age_h = (_dt.now(_tz.utc) - _dt.fromisoformat(
            card.get("first_seen") or "")).total_seconds() / 3600.0
    except Exception:
        age_h = 0.0
    score += 2.0 * (0.5 ** (max(age_h, 0) / FEED_RECENCY_HALFLIFE_H))
    score -= SOFT_PENALTY * float(card.get("soft_penalty") or 0)
    return score


def rel_time(iso):
    from datetime import datetime as _dt, timezone as _tz
    try:
        t = _dt.fromisoformat(iso)
    except Exception:
        return ""
    mins = int((_dt.now(_tz.utc) - t).total_seconds() // 60)
    if mins < 1:
        return "just now"
    if mins < 60:
        return f"{mins}m ago"
    if mins < 48 * 60:
        return f"{mins // 60}h ago"
    return f"{mins // 1440}d ago"


# The last subtle thing, Micah 2026-08-23, comparing two cards on one story:
#
#   GOOD "Good Good Golf deletes a violent ad while Callaway stays silent on
#         its involvement."
#   BAD  "Good Good Golf removes a controversial ad featuring a man shoving a
#         woman, while the true power dynamics behind creator-brand
#         partnerships remain hidden."
#   BAD  "Nvidia is turning compute into an asset class with $500 billion in
#         financing, while the value flows to incumbents."
#
# "just leave off the 'while value flows to the incumbents', the paragraph does
# the work of adding our taste."
#
# Both bad clauses LOOK concrete and both obey the CONTRAST shape. The
# difference is one word wide: what the clause is ABOUT. "Callaway" is an actor
# doing an observable thing (staying silent). "the value" and "the true power
# dynamics" are concepts, and a concept as the subject means the sentence has
# stopped reporting and started interpreting. Interpretation is the paragraph's
# job.
#
# So the test is on the clause's SUBJECT, not on whether it sounds specific.
# These survive, because their subjects are actors:
#   "while the county gives up the tax base"
#   "while nobody on his app can afford a house"
#   "while ByteDance keeps collecting data on kids"
_ABSTRACT_SUBJECTS = {
    "value", "values", "dynamic", "dynamics", "implication", "implications",
    "tension", "tensions", "reality", "truth", "story", "question",
    "questions", "cost", "costs", "stake", "stakes", "incentive", "incentives",
    "structure", "system", "balance", "gap", "divide", "future", "landscape",
    "picture", "trend", "trends", "shift", "pattern", "patterns", "force",
    "forces", "control", "influence", "access", "transparency",
    "accountability", "consequence", "consequences", "impact", "impacts",
    "issue", "issues", "problem", "irony", "contrast", "difference",
    "meaning", "significance", "risk", "risks", "danger", "point",
}
_ABSTRACT_LEADINS = ("the true ", "the real ", "the broader ", "the deeper ",
                     "the underlying ", "the bigger ", "the wider ")
_CONNECTORS = (", while ", ", but ", ", and ", ", as ", " while ")

# Same interpretive move, participial form, which the connector list cannot see:
# "...without a name or license plate, raising privacy concerns". There is no
# subject at all, which is exactly the tell. The clause is the writer telling
# you how to feel about the fact they just reported.
_PARTICIPIAL_TAILS = (
    ", raising ", ", sparking ", ", highlighting ", ", underscoring ",
    ", signaling ", ", signalling ", ", marking ", ", fueling ", ", fuelling ",
    ", prompting questions", ", drawing scrutiny", ", reflecting ",
    ", suggesting ", ", leaving questions", ", adding to concerns",
)


def _clause_subject(clause):
    """Head noun of the clause's subject, lowercased."""
    words = re.findall(r"[A-Za-z'-]+", clause)
    skip = {"the", "a", "an", "its", "their", "his", "her", "our", "this",
            "that", "these", "those", "true", "real", "broader", "deeper",
            "underlying", "bigger", "wider", "actual", "whole"}
    for w in words:
        if w[0].isupper():
            return None  # a named actor; not abstract
        if w.lower() in skip:
            continue
        return w.lower()
    return None


def trim_interpretive_tail(text):
    """Cut a trailing clause whose SUBJECT is a concept rather than an actor."""
    if not text:
        return text, None
    for tail in _PARTICIPIAL_TAILS:
        i = text.lower().find(tail)
        if i > 0:
            return text[:i].rstrip(" ,;") + ".", text[i:]
    for conn in _CONNECTORS:
        i = text.lower().rfind(conn)
        if i <= 0:
            continue
        head, clause = text[:i], text[i + len(conn):]
        if any(clause.lower().startswith(p) for p in _ABSTRACT_LEADINS):
            return head.rstrip(" ,;") + ".", clause
        subj = _clause_subject(clause)
        if subj and subj in _ABSTRACT_SUBJECTS:
            return head.rstrip(" ,;") + ".", clause
        return text, None
    return text, None


def _headline_tokens(text):
    stop = {"the", "and", "for", "with", "that", "this", "from", "into", "over",
            "while", "after", "about", "than", "they", "their", "have", "has"}
    return {t for t in re.findall(r"[a-z']{4,}", (text or "").lower())
            if t not in stop}


def _headline_subject(text):
    """The first few significant tokens: who or what the card is about."""
    toks = [t for t in re.findall(r"[a-z0-9']{3,}", (text or "").lower())
            if t not in {"the", "and", "for", "why", "who", "how", "did", "has"}]
    return tuple(toks[:3])


def dedupe_feed(cards, threshold=0.45):
    """Drop cards that retell a story already in the feed.

    The feed key is a hash of source URLs, so the same event covered by two
    publishers produces two keys and two cards. Two Good Good Golf ad cards
    shipped together on 2026-08-23. Similarity is judged on the HEADLINE,
    which is the only thing that actually says what the card is about.
    Earlier cards win: the feed is newest-first, so the survivor is the one
    that has been on the page longest and the reader has already seen.
    """
    kept, dropped = [], []
    for c in cards:
        toks = _headline_tokens(c.get("narrative"))
        subj = _headline_subject(c.get("narrative"))
        # Source identity is stable where the generated headline is not: two
        # runs phrase the same story differently and would stop deduping.
        srcs = {x.get("url") for x in (c.get("sources") or []) if x.get("url")}
        ssubj = _headline_subject((c.get("sources") or [{}])[0].get("headline"))
        dup = None
        for k in kept:
            ktoks = _headline_tokens(k.get("narrative"))
            ksrcs = {x.get("url") for x in (k.get("sources") or []) if x.get("url")}
            if srcs and ksrcs and srcs & ksrcs:
                dup = k
                break
            if ssubj and ssubj == _headline_subject(
                    (k.get("sources") or [{}])[0].get("headline")):
                dup = k
                break
            # Same subject is enough on its own: two cards that open on the
            # same entity are the same story told twice.
            if subj and subj == _headline_subject(k.get("narrative")):
                dup = k
                break
            if not toks or not ktoks:
                continue
            if len(toks & ktoks) / float(min(len(toks), len(ktoks))) >= threshold:
                dup = k
                break
        if dup is None:
            kept.append(c)
        else:
            dropped.append((c.get("narrative", "")[:70], dup.get("narrative", "")[:70]))
    for new, old in dropped:
        print(f"  DEDUPE dropped: {new}\n            same as: {old}")
    return kept


def render_brief_html(clusters, parsed, run_dir):
    """Render the LLM cards into web/brief.html with article links resolved
    from source_ids (indexes into each cluster's item list)."""
    from datetime import datetime, timezone as _tz
    import html as _html

    cards_html = []
    json_cards = []
    _max = int(os.environ.get("IH_MAX_CARDS", "0")) or 10**6
    _shown = 0
    for ci, card in enumerate(parsed.get("cards", [])):
        if not card.get("narrative"):
            continue  # declined cluster
        if _shown >= _max:
            continue
        _shown += 1
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
                sources.append({"source": a.get("source", ""),
                                "url": a.get("link", "#"),
                                "headline": a.get("title", "")})
        if not sources and cl["items"]:
            # Fallback: lead article of the cluster
            a = cl["items"][0]["article"]
            sources.append({"source": a.get("source", ""),
                            "url": a.get("link", "#"),
                            "headline": a.get("title", "")})
        # LP news-card shape (components/News/LeagueSection.tsx
        # AiNarrativeCard): kicker, narrative, paragraph, then a compact row of
        # publisher NAMES. Micah, 2026-08-23: "that pull quote below the
        # headline isnt necessary. and the sources should be shown as a list
        # like that." So data_point is no longer rendered as its own line; it
        # still rides in the JSON because ranking and grounding use it, and the
        # prompt already requires the paragraph to lead with the concrete fact.
        # LP's kicker is a TOPIC label, not a headline. A one-off cluster's
        # sig name is just the article's own title, which would print the
        # headline twice, so those fall back to the article category.
        _sig_name = (cl.get("sig", {}) or {}).get("name", "") or ""
        if _sig_name.startswith("One-off"):
            _lead = cl["items"][0]["article"] if cl.get("items") else {}
            kicker = (_lead.get("category") or "").title() or "What everyone's talking about"
        else:
            kicker = _sig_name or "What everyone's talking about"
        para_html = (f'<p class="brief-para">{_html.escape(card.get("paragraph",""))}</p>'
                     if card.get("paragraph") else "")
        _seen, _uniq = set(), []
        for srec in sources:
            if srec["source"] in _seen:
                continue
            _seen.add(srec["source"])
            _uniq.append(srec)
        sources = _uniq
        src_bits = []
        for i, srec in enumerate(sources[:3]):
            sep = '<span class="src-dot">·</span>' if i else ""
            src_bits.append(
                f'{sep}<a href="{srec["url"]}" target="_blank" rel="noopener" '
                f'title="{_html.escape(srec["headline"])}">{_html.escape(srec["source"])}</a>')
        more = '<span class="src-more">and more</span>' if len(sources) > 3 else ""
        cards_html.append(f"""
    <article class="brief-card">
      <p class="brief-kicker">{_html.escape(kicker)}</p>
      <h3 class="brief-title">{_html.escape(card.get("narrative",""))}</h3>
      {para_html}
      <div class="brief-sources">{''.join(src_bits)}{more}</div>
    </article>""")
        json_cards.append({
            "story_key": hashlib.sha256(
                "|".join(sorted(x["url"] for x in sources)).encode()).hexdigest()[:16],
            "kicker": kicker,
            "narrative": card.get("narrative", ""),
            "paragraph": card.get("paragraph", ""),
            "data_point": card.get("data_point", ""),
            "sources": sources[:3],
            "source_count": len(sources),
            # The lead article's editorial score, so the feed can be ORDERED.
            # Without this the feed sorted by first_seen and a golf ad ended up
            # as card #1 purely because of when it landed.
            "lead_score": max(
                [it["article"].get("_score", 0) for it in (cl["items"] if cl else [])] or [0]),
            "voice_weight": (cl.get("sig", {}) or {}).get("voice_weight", 0.5) if cl else 0.5,
            "soft_penalty": 1.0 if card.get("_soft_penalty") else 0.0,
        })

    # The page renders the RUNNING FEED, not just this run's cards. A story that
    # first appeared yesterday keeps yesterday's stamp and stays visible; a new
    # story lands on top. Nothing is capped: Micah is still exploring and wants
    # to see the lower-ranked cards so he can cut from the full picture himself.
    # RE-GATE THE WHOLE FEED, not just this run's cards. The feed accumulates,
    # so a card admitted by an older run was never judged again: four roster
    # cards sat in the feed on 2026-08-23 carrying obvious markers while the
    # run reported zero declines, because the gate only ever saw new cards.
    # The feed is the artifact, so the gate has to run over the feed.
    feed = merge_into_feed(json_cards)
    _kept, _demoted = [], 0
    for _c in feed:
        _probe = {"narrative": _c.get("narrative"),
                  "_sources": _c.get("sources") or []}
        _pen = 1.0 if card_is_performance_only(_probe, None) else 0.0
        if _pen and not _c.get("soft_penalty"):
            _demoted += 1
        _c["soft_penalty"] = _pen
        _kept.append(_c)
    if _demoted:
        print(f"  RE-RANK demoted {_demoted} card(s) already in the feed")
    feed = dedupe_feed(_kept)
    cards_html = []
    for c in feed:
        src_bits = []
        for i, srec in enumerate(c.get("sources", [])[:3]):
            sep = '<span class="src-dot">·</span>' if i else ""
            src_bits.append(
                f'{sep}<a href="{srec["url"]}" target="_blank" rel="noopener" '
                f'title="{_html.escape(srec.get("headline",""))}">'
                f'{_html.escape(srec.get("source",""))}</a>')
        more = ('<span class="src-more">and more</span>'
                if c.get("source_count", 0) > 3 else "")
        para = (f'<p class="brief-para">{_html.escape(c.get("paragraph",""))}</p>'
                if c.get("paragraph") else "")
        cards_html.append(f"""
    <article class="brief-card">
      <p class="brief-kicker">{_html.escape(c.get("kicker",""))}<span class="brief-age">{rel_time(c.get("first_seen",""))}</span></p>
      <h3 class="brief-title">{_html.escape(c.get("narrative",""))}</h3>
      {para}
      <div class="brief-sources">{''.join(src_bits)}{more}</div>
    </article>""")

    with open(FEED_PATH, "w") as f:
        json.dump({"updated": datetime.now(_tz.utc).isoformat(),
                   "cards": feed}, f, indent=2)

    # What the gates dropped, shown so he can disagree with a decline instead of
    # never learning it happened.
    declined_html = ""
    if _LAST_DECLINES:
        rows = "".join(
            f'<li><span class="dq-why">{_html.escape(d.get("reason") or d.get("verdict",""))}</span>'
            f'{_html.escape((d.get("headline") or "")[:130])}</li>'
            for d in _LAST_DECLINES)
        declined_html = (f'<details class="declined"><summary>Declined this run '
                         f'({len(_LAST_DECLINES)})</summary><ul>{rows}</ul></details>')

    # Displayed in LOCAL time. The stored timestamps stay UTC; see
    # brief.local_ts() for why the conversion happens at the edge.
    import brief as _brief
    ts = _brief.local_ts()
    meta = json.load(open(os.path.join(run_dir, "meta.json"))) if os.path.exists(os.path.join(run_dir, "meta.json")) else {}
    run_ts = _brief.local_ts(meta["timestamp"]) if meta.get("timestamp") else ts
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
  .brief-kicker {{ font-size:.68rem; font-weight:600; text-transform:uppercase; letter-spacing:.08em; color:var(--ink-muted); margin-bottom:.35rem; }}
  .brief-sources {{ display:flex; flex-wrap:wrap; align-items:center; gap:.35rem; margin-top:.7rem; font-size:.72rem; }}
  .brief-sources a {{ color:var(--ink-muted); text-decoration:none; text-transform:uppercase; letter-spacing:.04em; }}
  .brief-sources a:hover {{ color:var(--gold-dark); }}
  .src-dot {{ color:var(--border); margin:0 .1rem; }}
  .src-more {{ color:var(--ink-muted); opacity:.7; }}
  .brief-age {{ float:right; text-transform:none; letter-spacing:0; opacity:.75; }}
  .declined {{ margin-top:2rem; border-top:1px solid var(--border); padding-top:1rem; }}
  .declined summary {{ font-size:.75rem; text-transform:uppercase; letter-spacing:.08em; color:var(--ink-muted); cursor:pointer; }}
  .declined ul {{ list-style:none; padding:.6rem 0 0; }}
  .declined li {{ font-size:.8rem; line-height:1.5; color:var(--ink-muted); padding:.2rem 0; }}
  .dq-why {{ display:inline-block; min-width:11rem; font-size:.68rem; text-transform:uppercase; letter-spacing:.05em; color:var(--gold-dark); }}
  .back {{ display:inline-block; margin-top:2rem; font-family:'Oswald',sans-serif; font-size:.8rem; text-transform:uppercase; letter-spacing:.05em; color:var(--ink); text-decoration:none; border-bottom:2px solid var(--gold); padding-bottom:2px; }}
</style>
</head>
<body>
<div class="wrap">
  <h1 class="page-title">Innovative Hype — Brief</h1>
  <div class="page-meta">Narrative brief · LLM desk · run {meta.get('code_version','?')} · {run_ts} · updated {ts}</div>
  {''.join(cards_html)}
  {declined_html}
  <a class="back" href="index.html">← Back to feed</a>
</div>
</body>
</html>
"""
    with open(os.path.join(WEB, "brief.html"), "w") as f:
        f.write(html)
    with open(os.path.join(WEB, "brief-cards.json"), "w") as f:
        json.dump({"updated": datetime.now(_tz.utc).isoformat(),
                   "run": meta.get("code_version", "?"),
                   "cards": feed}, f, indent=2)
    print(f"Rendered web/brief.html + brief-cards.json with {len(cards_html)} cards")


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
    import embed
    # Embed the whole pool in batches before clustering it. signature_for()
    # embeds one story at a time, so without this a 2,000-article pool is 2,000
    # sequential round trips.
    _points = {id(a): brief.mine_data_points(a) for a in scored}
    brief.warm_signatures([(a, _points[id(a)]) for a in scored])
    print("  " + embed.stats_line())
    enriched = []
    for a in scored:
        points = _points[id(a)]
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
    _keep_n = int(os.environ.get("IH_ONE_OFFS", "12"))
    kept_one_offs = seeded[:_keep_n] + unseeded[: max(0, _keep_n - len(seeded[:_keep_n]))]
    print(f"  {len(one_off_clusters)} one-offs ({len(seeded)} seeded), keeping {_keep_n} (seeded first)")
    all_clusters = sig_clusters + kept_one_offs

    all_clusters.sort(key=cluster_score, reverse=True)
    # Keep the strongest 14 for the desk (12 signature clusters + top 2-6
    # one-offs), balanced so a single huge cluster doesn't crowd the field
    return all_clusters[:14]


def _api_key():
    """NOUS_PORTAL_KEY. The DEEPSEEK_API_KEY in config is dead/out of funds
    (measured 2026-08-21: 401 on chat, portal key returns 200)."""
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
    return key


_VOICE_PROFILE_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "voice_profile.json")
_VOICE_PROFILE_CACHE = None


def _load_voice_profile():
    """Perspective entries extracted from the corpus by
    scripts/build_voice_profile.py. The unigram seeds carry the topic; these
    carry the stance. Missing or corrupt file = empty list, reported loudly
    in the run log, never a crash: the desk renders without perspective
    rather than not at all."""
    global _VOICE_PROFILE_CACHE
    if _VOICE_PROFILE_CACHE is None:
        try:
            with open(_VOICE_PROFILE_PATH) as f:
                _VOICE_PROFILE_CACHE = json.load(f).get("entries", [])
        except Exception:
            _VOICE_PROFILE_CACHE = []
    return _VOICE_PROFILE_CACHE


def _voice_entries_for(cl):
    """Profile entries that color this cluster: category-name match first,
    else topic terms all present in the cluster name or item titles."""
    name = (cl.get("sig") or {}).get("name", "")
    hay = " ".join(
        [name] + [(i.get("title") or "") for i in (cl.get("items") or [])[:20]]
    ).lower()
    out = []
    for e in _load_voice_profile():
        if name in (e.get("categories") or []):
            out.append(e)
            continue
        twords = [w for w in re.split(r"\W+", (e.get("topic") or "").lower())
                  if len(w) > 3]
        if twords and all(w in hay for w in twords):
            out.append(e)
    return out[:2]


def call_model(clusters):
    """Call the LLM with the cluster material. Returns raw JSON string."""
    import urllib.request  # noqa: F401  (call_llm uses it)

    key = _api_key()

    _angles = load_angles()
    print(f"  angle inventory: {len(_angles)} enabled")
    _vp = _load_voice_profile()
    _vpc = sum(1 for _c in clusters if _voice_entries_for(_c))
    print(f"  voice profile: {len(_vp)} entries; perspective injected into "
          f"{_vpc}/{len(clusters)} clusters"
          + ("" if _vp else " (empty; run scripts/build_voice_profile.py)"))
    import embed as _embed
    _embed.warm([cluster_subject_text(c) for c in clusters]
                + [angle_probe_text(a) for a in _angles])
    print("  " + _embed.stats_line())
    prompt_lines = ["Today's date: %s" % datetime.now(timezone.utc).strftime("%Y-%m-%d"), ""]
    for ci, cl in enumerate(clusters):
        _shape_name, _shape_rule = _SHAPES[ci % len(_SHAPES)]
        prompt_lines.append(f"CLUSTER {ci}: {cl['sig']['name']} (voice_weight {cl['sig'].get('voice_weight','?')})")
        # Perspective injection: the stance and verbatim exemplars behind the
        # seed hits, so the card lands in his register, not just on his topic.
        for _pe in _voice_entries_for(cl):
            prompt_lines.append(
                f"  HOW MICAH TALKS ABOUT THIS: on {_pe['topic']}, his stance "
                f"is: {_pe['stance']} (tone: {_pe['tone']})")
            for _ex in _pe.get("exemplars", [])[:2]:
                prompt_lines.append(f'    his exact words: "{_ex}"')
        prompt_lines.append(f"  REQUIRED HEADLINE SHAPE = {_shape_name}. {_shape_rule}")
        _elig = eligible_angles(cl, _angles)
        if _elig:
            _ids = ", ".join(f'"{_a["id"]}"' for _a, _ in _elig)
            prompt_lines.append(f'  angle_id MUST be one of {_ids} or "none":')
            for _a, _m in _elig:
                prompt_lines.append(f"    [{_a['id']}] {_a['claim']}")
        else:
            prompt_lines.append('  angle_id MUST be "none". No angle is in '
                                "scope for this cluster: report it straight or "
                                "decline it, and do not supply an opinion from "
                                "somewhere else.")
        # THE REAL STARVATION POINT. This loop used to hand the model 300
        # characters of each article. Measured 2026-08-23 on The Verge's
        # "Nvidia's new financial strategy does not compute": 300 chars is the
        # piece's opening corncob joke and a Napoleon gag, and none of its
        # argument. The desk could not pick an angle because it had never been
        # shown one, and it filled the gap with an unrelated housing take.
        # Micah could not pick the angle from the excerpt either, which is the
        # whole point: this was never a model-capability problem.
        #
        # Budget: the LEAD articles of a cluster are what a card gets written
        # from, so they get real text. The tail is there for context and stays
        # short, which keeps the whole prompt sane across ~13 clusters.
        for _i, item in enumerate(cl["items"]):
            a = item["article"]
            prompt_lines.append(f"  {item['points'][0][:200] if item['points'] else 'no data point'}")
            prompt_lines.append(f"  {a.get('title','')} ({a.get('source','')})")
            _cap = 1800 if _i < 3 else 400
            body = (a.get("_body", "") or "")[:_cap]
            if body:
                prompt_lines.append(f"    {body}")
        prompt_lines.append("")

    return call_llm(_SYSTEM, "\n".join(prompt_lines), max_tokens=3000, key=key)


def call_llm(system, user, max_tokens=3000, key=None):
    """One strict-JSON chat completion. Shared by the desk and by
    extract_angles.py so there is exactly one place that knows the auth, the
    User-Agent and the reasoning flag."""
    if key is None:
        key = _api_key()
    body = json.dumps({
        "model": MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": 0.7,
        "max_tokens": max_tokens,
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
    with urllib.request.urlopen(req, timeout=180) as resp:
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
                                "body_excerpt": (item["article"].get("_body") or "")[:2500],
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
        # The model now names its own cluster. Trust it when it is in range and
        # unclaimed: it knows which block it wrote from, and no similarity
        # heuristic can beat that.
        # A model-declared index is a CLAIM, not a fact, and I shipped it as a
        # fact. Measured 2026-08-23: once the prompt grew (real article bodies
        # instead of 300-char stubs) the model started numbering its cards
        # 0..N sequentially regardless of which cluster it wrote from, and
        # every kicker went wrong at once: the Flock card filed under "The AI
        # data gold rush", a Timberwolves sale under "AI trust and
        # accountability". Trust it only when the content agrees.
        declared = card.get("cluster_index")
        best_ci = None
        best_score = 0.0
        tokens = set(re.findall(r"[a-z']{4,}", card_text))
        for ci, cl in enumerate(clusters):
            if ci in used_clusters:
                continue
            cl_tokens = set()
            for item in cl["items"]:
                cl_tokens |= set(re.findall(
                    r"[a-z']{4,}", item["article"].get("title", "").lower()))
            if not cl_tokens or not tokens:
                continue
            # NORMALISE. The old score was a raw count of card tokens appearing
            # anywhere in the cluster's concatenated titles, so the BIGGEST
            # cluster won every card by having more text to hit. Measured
            # 2026-08-23: a Blue Origin card landed in "Sports money keeps
            # inflating" and was cited to On3, a college sports site, and a
            # Timberwolves sale landed in "Crypto's leverage problem" cited to
            # Bitcoin Magazine. Jaccard removes the size advantage.
            overlap = len(tokens & cl_tokens) / float(len(tokens | cl_tokens))
            if overlap > best_score:
                best_score = overlap
                best_ci = ci
        # Accept the declared index when it is in range, unclaimed, and its
        # own content score is at least as good as the best free cluster's.
        # Otherwise the content wins, because the kicker and the source chips
        # both come from this decision and a wrong one cites the card to a
        # publisher that never covered it.
        if isinstance(declared, int) and 0 <= declared < len(clusters) \
                and declared not in used_clusters:
            dcl_tokens = set()
            for item in clusters[declared]["items"]:
                dcl_tokens |= set(re.findall(
                    r"[a-z']{4,}", item["article"].get("title", "").lower()))
            dscore = (len(tokens & dcl_tokens) / float(len(tokens | dcl_tokens))
                      if tokens and dcl_tokens else 0.0)
            if dscore >= best_score * 0.9:
                best_ci, best_score = declared, dscore
            else:
                print(f"  ALIGN: model said cluster {declared} "
                      f"(score {dscore:.3f}) but content says {best_ci} "
                      f"(score {best_score:.3f}); using content")
        if best_ci is not None and best_score > 0:
            used_clusters.add(best_ci)
            card["_cluster_idx"] = best_ci
        aligned.append(card)
    parsed["cards"] = aligned

    with open(os.path.join(run_dir, "cards.json"), "w") as f:
        json.dump(parsed, f, indent=2)

    # Render the cards into brief.html (resolving source_ids → article links)
    # Micah, 2026-08-23: "do we have that stuff being saved to a file whenever
    # it does like this decline and keep?" It did not; the verdicts only went
    # to stdout and the cron log rotates. Every verdict is now written twice:
    # runs/<ts>/decisions.json for this run, and an append-only
    # runs/decisions.jsonl so the record survives and can be read back. A gate
    # you cannot audit after the fact is a gate you cannot tune.
    _angles_used = load_angles()
    _decisions = []
    _typed_out = 0
    for _ci, _card in enumerate(parsed.get("cards", [])):
        _headline = _card.get("narrative")
        if not _headline:
            _decisions.append({"cluster": _ci, "verdict": "declined_by_model",
                               "headline": None})
            continue
        _cl = clusters[_ci] if _ci < len(clusters) else None
        _kicker = ((_cl or {}).get("sig", {}) or {}).get("name", "")
        # An angle_id the model reports is a CLAIM. Check it against the angles
        # that were actually offered for THIS cluster. A card built on an
        # out-of-scope angle is the housing-on-a-GPU-story failure, and the
        # only safe verdict is to drop it: the opinion in it was never legal
        # for this subject, so the sentence cannot be repaired by trimming.
        _aid = _card.get("angle_id")
        if isinstance(_aid, str) and _aid.strip().lower() in ("none", "null", ""):
            _aid = None  # "none" is the legal way to say no angle, not an id
        # The model reports "none" even when it plainly used one (measured
        # 2026-08-23: a card that restated the prediction-markets-weak claim
        # almost verbatim still said none). A self-reported field is a claim,
        # so the record keeps what was OFFERED and what the text actually
        # resembles, both of which are checkable, alongside what it said.
        if _cl and not _card.get("_sources"):
            _card["_sources"] = [
                {"headline": it["article"].get("title", ""),
                 "url": it["article"].get("link", "")}
                for it in _cl.get("items", [])[:3]]
        _elig = eligible_angles(_cl, _angles_used) if _cl else []
        _offered = [a["id"] for a, _ in _elig]
        _offered_scores = {a["id"]: round(sc, 3) for a, sc in _elig}
        _inferred, _inferred_score = None, 0.0
        if _elig:
            # The model reports "none" even when it plainly used one (measured
            # 2026-08-23: a card restating the prediction-markets claim almost
            # verbatim still said none). This was word overlap between the card
            # and the claim, which only caught a card that reused his nouns. It
            # is the same similarity the offer used, so a card that argues the
            # position in different words is still recognised as having used
            # it.
            import embed as _embed
            _ctext = (_headline + " " + (_card.get("paragraph") or "")).strip()
            _sims = _embed.similarity([_ctext],
                                      [_a["claim"] for _a, _ in _elig])[0]
            for (_a, _), _sc in zip(_elig, _sims):
                if float(_sc) > _inferred_score:
                    _inferred, _inferred_score = _a["id"], float(_sc)
            if _inferred_score < 0.45:
                _inferred, _inferred_score = None, 0.0
        if _aid and _cl is not None:
            _legal = set(_offered)
            if _aid not in _legal:
                print(f"  ANGLE-GATE declined (angle '{_aid}' not in scope for "
                      f"this cluster): {_headline[:60]}")
                _decisions.append({"cluster": _ci, "verdict": "declined_angle_gate",
                                   "reason": "angle_out_of_scope", "angle": _aid,
                                   "cluster_name": _kicker, "headline": _headline})
                _card["narrative"] = None
                continue
        if card_is_performance_only(_card, _cl):
            # DEMOTE, do not delete. The card stays visible and sinks. Deleting
            # it was me making his cut for him, and he is still exploring.
            _card["_soft_penalty"] = True
            print(f"  DEMOTED (performance only): {_headline[:70]}")
            _decisions.append({"cluster": _ci, "verdict": "demoted_type_gate",
                               "reason": "performance_only", "angle": _aid,
                               "source_headline": _lead_source_text(_card, _cl)[:160],
                               "cluster_name": _kicker, "headline": _headline})
            _typed_out += 1
            continue
        if False:
            _decisions.append({"cluster": _ci, "verdict": "declined_type_gate",
                               "reason": "performance_only", "angle": _aid,
                               "source_headline": _lead_source_text(_card, _cl)[:160],
                               "angle_offered": _offered,
                               "angle_offered_scores": _offered_scores,
                               "angle_inferred": _inferred,
                               "angle_inferred_score": round(_inferred_score, 3),
                               "cluster_name": _kicker, "headline": _headline})
            _card["narrative"] = None
            _typed_out += 1
        else:
            _decisions.append({"cluster": _ci, "verdict": "kept", "angle": _aid,
                               "angle_offered": _offered,
                               "angle_offered_scores": _offered_scores,
                               "angle_inferred": _inferred,
                               "angle_inferred_score": round(_inferred_score, 3),
                               "cluster_name": _kicker, "headline": _headline})
    if _typed_out:
        print(f"  DEMOTED {_typed_out} card(s) to the bottom of the feed")

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
    _max = int(os.environ.get("IH_MAX_CARDS", "0")) or 10**6
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

    _now = datetime.now(timezone.utc).isoformat()
    with open(os.path.join(run_dir, "decisions.json"), "w") as _f:
        json.dump({"timestamp": _now, "run": os.path.basename(run_dir),
                   "kept": sum(1 for d in _decisions if d["verdict"] == "kept"),
                   "declined_type_gate": _typed_out,
                   "decisions": _decisions}, _f, indent=2)
    with open(os.path.join(RUNS, "decisions.jsonl"), "a") as _f:
        for _d in _decisions:
            _f.write(json.dumps(dict(_d, timestamp=_now,
                                     run=os.path.basename(run_dir))) + "\n")
    print(f"  decisions -> {os.path.join(run_dir, 'decisions.json')} "
          f"and runs/decisions.jsonl")

    with open(os.path.join(run_dir, "meta.json"), "w") as _f:
        json.dump({"timestamp": datetime.now(timezone.utc).isoformat(),
                   "code_version": git_sha(), "model": MODEL,
                   "pool_key": pool_key(clusters)}, _f, indent=2)

    globals()["_LAST_DECLINES"] = [d for d in _decisions
                                   if d["verdict"].startswith("declined")
                                   and d.get("headline")]

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
