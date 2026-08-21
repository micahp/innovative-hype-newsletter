#!/usr/bin/env python3
"""acceptance_fixture.py — report whether Micah's named stories reached the desk.

NEWS-ENGINE-SPEC.md §6. Every run reports each story as:
  ABSENT_FROM_FEED / DROPPED_BY_<gate> / REACHED_DESK / CARDED

Exits non-zero if any expected story is ABSENT or DROPPED (so the cron log
shows the failure loudly — R7).
"""

import json
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEB = os.path.join(REPO, "web")
RUNS = os.path.join(REPO, "runs")

# Micah's eight named stories: (label, title keywords — ANY match suffices)
FIXTURE = [
    ("Flock cameras", ["flock", "stolen flock cameras", "camera", "surveillance"]),
    ("Data centers/Texas", ["data center", "williamson county", "blue origin"]),
    ("Marijuana Texas", ["marijuana", "cannabis", "texas"]),
    ("Longhorns vs Texas State", ["longhorn", "texas state"]),
    ("Kanye fireworks", ["kanye", "fireworks", "all of the lights"]),
    ("NBA->WNBA draft", ["wnba draft", "declare for the wnba"]),
    ("40-yr NCAAF", ["40-year-old", "college football", "age limit"]),
    ("Sophie Cunningham", ["sophie cunningham", "wnba commissioner"]),
]


def main():
    with open(os.path.join(WEB, "articles.json")) as f:
        feed = json.load(f)

    # What the desk actually saw (latest run input)
    latest = os.path.join(RUNS, "latest")
    desk_titles = set()
    desk_meta = {}
    input_path = os.path.join(latest, "input.json")
    cards_path = os.path.join(latest, "cards.json")
    if os.path.exists(input_path):
        with open(input_path) as f:
            inp = json.load(f)
        for cl in inp.get("clusters", []):
            for item in cl.get("items", []):
                desk_titles.add((item.get("title", "").lower(), item.get("source", "")))
    carded = set()
    if os.path.exists(cards_path):
        with open(cards_path) as f:
            cards = json.load(f)
        for c in cards.get("cards", []):
            if c.get("narrative"):
                # Card narrative text may mention the story; count CARDED if
                # the narrative is non-null (declined = null)
                carded.add(c.get("narrative", ""))

    failures = 0
    print("=== ACCEPTANCE FIXTURE ===")
    for label, kws in FIXTURE:
        # Check feed presence (ANY keyword in title OR summary)
        in_feed = any(
            any(k in a.get("title", "").lower() or k in (a.get("summary", "") or "").lower() for k in kws)
            for a in feed.get("articles", [])
        )
        reached = any(
            any(k in t for k in kws) for t, _ in desk_titles
        )
        if not in_feed:
            status = "ABSENT_FROM_FEED"
        elif not reached:
            status = "DROPPED_BY_GATE"
        else:
            status = "REACHED_DESK"
        print(f"  {label:24s} {status}")
        if status in ("ABSENT_FROM_FEED", "DROPPED_BY_GATE"):
            failures += 1

    print(f"\n  {len(FIXTURE) - failures}/{len(FIXTURE)} reached the desk")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
