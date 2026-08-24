#!/usr/bin/env python3
"""extract_angles.py — build the angle inventory from Micah's own posts.

WHY THIS EXISTS (2026-08-23)
A card read "Nvidia is turning compute into an asset class while the average
person can't afford a home." No affordability claim was anywhere in the
grounding. That was NOT a hallucination: it is a real position of Micah's,
correctly retrieved, attached to the wrong subject. The desk reached into his
voice signal, grabbed the nearest thing, and welded it on.

The fix is not "reject clauses absent from the article". His RIGHT angle for
that piece (you will never run local inference, you will rent compute forever)
is not literally in the article either. A text-presence check kills both.

The distinction is SUBJECT SCOPE. An angle may only fire on a story that is
about the thing the angle is about. Housing can never attach to a GPU financing
story, not because the words are missing but because it is out of scope.

So: positions are enumerated in angles.yaml, each with the subjects it may fire
on and the posts it came from. Micah edits that file directly. This is the
answer to "without having me fine-tune an LLM on my tweets" — the corpus seeds
the inventory, but the inventory is text he owns and corrects, not weights.

    python scripts/extract_angles.py            # write angles.yaml (candidates)
    python scripts/extract_angles.py --dry-run  # print, don't write

Nothing schedules this. It is a developer tool: re-run it when the corpus has
grown enough to be worth re-reading, then hand-edit the result.
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import narrative_desk as nd  # noqa: E402  (reuse its provider + auth path)

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CORPUS = os.path.join(REPO, "corpus")
OUT = os.path.join(REPO, "angles.yaml")

_SYSTEM = (
    "You are reading one person's social posts to extract the POSITIONS they "
    "hold. A position is an opinion they would defend, not a topic they "
    "mention. 'Cities' is a topic. 'If I'm not passing a cemetery, the city is "
    "too big' is a position.\n"
    "For each position give:\n"
    "  id      — short kebab-case slug\n"
    "  claim   — ONE sentence in their voice stating the position\n"
    "  scope   — 4 to 10 lowercase SUBJECT terms. A story must be ABOUT one of "
    "these for the position to be allowed to apply. Be strict and concrete: "
    "the scope for a housing-affordability position is housing, rent, "
    "mortgage, home prices, zoning, landlord. It is NOT 'money' or 'the "
    "economy', because those would let it attach to anything.\n"
    "  evidence — 1 to 3 short quotes from the posts that show the position\n"
    "RULES: Extract at most 20. Merge near-duplicates. Skip one-off jokes and "
    "anything you cannot state as a defendable claim. A position with a vague "
    "scope is worse than no position, because it will attach to stories it has "
    "nothing to do with.\n"
    'Output STRICT JSON: {"angles": [{"id": "...", "claim": "...", '
    '"scope": ["..."], "evidence": ["..."]}]}'
)


def load_posts(min_len=70):
    posts = []
    for name in ("geoppls.jsonl", "innovativehype.jsonl"):
        path = os.path.join(CORPUS, name)
        if not os.path.exists(path):
            continue
        for line in open(path):
            try:
                p = json.loads(line)
            except Exception:
                continue
            text = (p.get("text") or "").strip()
            if len(text) >= min_len:
                posts.append(text.replace("\n", " "))
    # newest first is not meaningful here; dedupe and keep order
    seen, out = set(), []
    for t in posts:
        if t not in seen:
            seen.add(t)
            out.append(t)
    return out


def to_yaml(angles):
    import yaml
    doc = {
        "_readme": (
            "The angle inventory. An angle may only be applied to a story whose "
            "SUBJECT is in its scope. Edit freely: delete positions that are not "
            "yours, tighten a scope that is catching the wrong stories, set "
            "enabled: false to retire one without losing it. narrative_desk.py "
            "reads this file and records which angle each card used, so when a "
            "card picks badly you can point at the row."
        ),
        "angles": [
            {"id": a.get("id", ""), "enabled": True,
             "claim": a.get("claim", ""),
             "scope": [s.lower().strip() for s in a.get("scope", []) if s],
             "evidence": a.get("evidence", [])[:3]}
            for a in angles if a.get("id") and a.get("scope")
        ],
    }
    return yaml.safe_dump(doc, sort_keys=False, allow_unicode=True, width=88)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--batch", type=int, default=120,
                    help="posts per model call")
    args = ap.parse_args()

    posts = load_posts()
    print(f"{len(posts)} substantive posts")

    collected = []
    for i in range(0, len(posts), args.batch):
        chunk = posts[i:i + args.batch]
        user = "POSTS:\n" + "\n".join("- " + t[:400] for t in chunk)
        print(f"  reading posts {i}-{i + len(chunk)}...")
        raw = nd.call_llm(_SYSTEM, user, max_tokens=6000)
        try:
            got = json.loads(raw).get("angles", [])
        except Exception as exc:
            print(f"  parse failed: {exc}")
            continue
        print(f"    {len(got)} positions")
        collected.extend(got)

    # Merge by id across batches; first definition wins, scopes union.
    merged = {}
    for a in collected:
        aid = (a.get("id") or "").strip().lower()
        if not aid:
            continue
        if aid in merged:
            merged[aid]["scope"] = sorted(
                set(merged[aid]["scope"]) | set(s.lower() for s in a.get("scope", [])))
            merged[aid]["evidence"] = (merged[aid]["evidence"] + a.get("evidence", []))[:3]
        else:
            merged[aid] = {"id": aid, "claim": a.get("claim", ""),
                           "scope": [s.lower() for s in a.get("scope", [])],
                           "evidence": a.get("evidence", [])[:3]}

    out = to_yaml(list(merged.values()))
    print(f"\n{len(merged)} positions after merge")
    if args.dry_run:
        print(out)
        return 0
    with open(OUT, "w") as f:
        f.write(out)
    print(f"wrote {OUT}")
    print("EDIT IT. These are candidates read off the corpus, not your ruling.")
    return 0


if __name__ == "__main__":
    sys.exit(main())


# === ARCHIVE MODE (2026-08-23) ===
#
# The first inventory was read off ~260 nitter-scraped posts and came back
# article-shaped: 62 rows, most of them a FACT about one story ("The housing
# market in Galveston TX is in oversupply") rather than a position that can be
# applied to next week's news. Micah: "it's not generic enough. it's too
# specific to the articles."
#
# The real corpus was on the box the whole time: the official X export at
# /root/Downloads/twitter-2026-05-17-*.zip, 33,143 tweets from 2016 to
# 2026-05-17. That is what VOICE-AND-WORLDVIEW.md was mined from.
#
# Two choices that matter:
#
#   ORIGINALS ONLY. Replies (19,590) are conversation, retweets (8,036) are
#   endorsement. Neither is a stated position in his own words, and mixing them
#   in is how the first pass ended up asserting things he had quoted rather
#   than claimed.
#
#   WEIGHTED TO RECENT. A worldview moves. 2021-2022 is the volume peak (1,601
#   originals) but 2025-2026 is what he believes now, so recent years are taken
#   whole and older years are sampled. A position he held in 2021 and still
#   posts about survives the sampling by repetition, which is the point.
# In the repo, not in /tmp. This file IS the specification for the voice
# profile (VOICE-AND-WORLDVIEW.md was mined from it), and it spent a day
# living in a session scratchpad that gets cleaned, where a missing file made
# load_archive_originals() return [] with nothing to say about it.
ARCHIVE_JSON = os.environ.get(
    "IH_ARCHIVE_JSON",
    os.path.join(os.path.dirname(__file__), "..", "corpus", "x_archive_all_tweets.json"))

# year -> fraction of that year's originals to read
_YEAR_WEIGHT = {"2026": 1.0, "2025": 1.0, "2024": 0.6, "2023": 0.5,
                "2022": 0.35, "2021": 0.35}
_YEAR_WEIGHT_DEFAULT = 0.25


def load_archive_originals(min_len=60):
    """His own declarative posts, weighted toward the present."""
    import random
    if not os.path.exists(ARCHIVE_JSON):
        raise FileNotFoundError(
            "the X archive is missing at %s. Every position extracted from it "
            "silently disappears if this returns empty, so it raises instead. "
            "Set IH_ARCHIVE_JSON to point at it." % ARCHIVE_JSON)
    posts = json.load(open(ARCHIVE_JSON))
    by_year = {}
    for p in posts:
        if p.get("is_reply") or p.get("is_rt"):
            continue
        text = (p.get("text") or "").strip()
        if len(text) < min_len:
            continue
        year = (p.get("date") or "").split()[-1]
        by_year.setdefault(year, []).append((year, text))
    random.seed(7)
    out = []
    for year, items in sorted(by_year.items()):
        frac = _YEAR_WEIGHT.get(year, _YEAR_WEIGHT_DEFAULT)
        take = max(1, int(len(items) * frac))
        out.extend(random.sample(items, min(take, len(items))))
    out.sort(key=lambda x: x[0], reverse=True)  # newest years first
    return out
