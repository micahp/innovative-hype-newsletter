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
