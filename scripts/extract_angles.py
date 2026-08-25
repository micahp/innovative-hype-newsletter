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

    python scripts/extract_angles.py            # write angles.candidates.yaml
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
OUT = os.path.join(REPO, "angles.candidates.yaml")

_SYSTEM = (
    "You are reading one person's social posts to extract the POSITIONS they "
    "hold. A position is an opinion they would defend, not a topic they "
    "mention. 'Cities' is a topic. 'If I'm not passing a cemetery, the city is "
    "too big' is a position.\n"
    "For each position give:\n"
    "  id      — short kebab-case slug\n"
    "  claim   — ONE sentence in their voice stating the position\n"
    "  subject — ONE plain-English sentence naming the CATEGORY this position "
    "is about, written so it stays true when the subject turns up under names "
    "he never used. Not the words in the post: the thing behind them. A post "
    "complaining that Nvidia rents you compute is not about the word "
    "'compute', it is about renting versus owning the infrastructure you "
    "depend on, which also covers hyperscaler leasing, inference pricing and "
    "on-device models. Write the category, not the vocabulary.\n"
    "  scope   — 6 to 12 lowercase terms naming things that BELONG TO that "
    "category, including ones the post never used. These are read by an "
    "embedding model, not matched as substrings, so they exist to pin the "
    "category down, not to be found verbatim in a headline. Extrapolate: if "
    "the category is renting versus owning infrastructure, the scope includes "
    "cloud lock-in and on-device inference even though he never typed them. "
    "Never put a place name in scope unless the position is genuinely about "
    "that place; 'texas' is where he lives, not what he is talking about.\n"
    "  evidence — 1 to 3 short quotes from the posts that show the position\n"
    "RULES: Extract at most 20. Merge near-duplicates. Skip one-off jokes and "
    "anything you cannot state as a defendable claim. State the position at the "
    "level he would defend it, which is usually one level above the story that "
    "provoked it: 'the housing market in Galveston is oversupplied' is an "
    "observation about one town and is worthless next week, while the position "
    "underneath it applies to any market. Do NOT widen the SUBJECT to "
    "compensate. A position about who captures new asset classes is about "
    "ownership and access, not about 'the economy'.\n"
    'Output STRICT JSON: {"angles": [{"id": "...", "claim": "...", '
    '"subject": "...", "scope": ["..."], "evidence": ["..."]}]}'
)


# year -> fraction of that year's originals to read. A worldview moves: 2021-22
# is the volume peak but 2025-26 is what he believes now, so recent years are
# taken whole and older years sampled. A position he held in 2021 and still
# posts about survives the sampling by repetition, which is the point.
_YEAR_WEIGHT = {"2026": 1.0, "2025": 1.0, "2024": 0.6, "2023": 0.5,
                "2022": 0.35, "2021": 0.35}
_YEAR_WEIGHT_DEFAULT = 0.25

# In the repo, never in /tmp. This file IS the specification for the voice
# profile (VOICE-AND-WORLDVIEW.md was mined from it).
ARCHIVE_JSON = os.environ.get(
    "IH_ARCHIVE_JSON", os.path.join(CORPUS, "x_archive_all_tweets.json"))


def load_archive_originals(min_len=60):
    """His own declarative posts from the official X export, weighted recent.

    ORIGINALS ONLY. Replies are conversation and retweets are endorsement.
    Neither is a stated position in his own words, and mixing them in is how
    the first pass asserted things he had quoted rather than claimed.
    """
    import random
    if not os.path.exists(ARCHIVE_JSON):
        raise FileNotFoundError(
            "the X archive is missing at %s. It is the largest voice source "
            "here and every position extracted from it would silently vanish, "
            "so this raises. Set IH_ARCHIVE_JSON to point at it." % ARCHIVE_JSON)
    posts = json.load(open(ARCHIVE_JSON))
    by_year = {}
    for p in posts:
        if p.get("is_reply") or p.get("is_rt"):
            continue
        text = (p.get("text") or "").strip()
        if len(text) < min_len:
            continue
        by_year.setdefault((p.get("date") or "").split()[-1], []).append(text)
    random.seed(7)
    out = []
    for year, items in sorted(by_year.items()):
        frac = _YEAR_WEIGHT.get(year, _YEAR_WEIGHT_DEFAULT)
        take = max(1, int(len(items) * frac))
        out.extend(random.sample(items, min(take, len(items))))
    if not out:
        raise RuntimeError(
            "%d tweets in the archive and 0 usable originals after filtering "
            "replies, retweets and posts under %d chars. That is a parse "
            "failure, not an empty corpus." % (len(posts), min_len))
    return out


def load_jsonl(name, min_len):
    path = os.path.join(CORPUS, name)
    if not os.path.exists(path):
        raise FileNotFoundError(
            "%s is missing. A voice source that silently disappears takes its "
            "positions with it and the extractor still completes, so this "
            "raises. Run scripts/pull_substack.py or scripts/pull_corpus.py."
            % path)
    out = []
    for line in open(path):
        try:
            row = json.loads(line)
        except Exception:
            continue
        text = (row.get("text") or "").strip()
        if len(text) >= min_len:
            out.append(text)
    return out


def load_posts(min_len=70):
    """Every voice source, not one of them.

    Until 2026-08-24 this read two nitter scrapes and nothing else.
    load_archive_originals() was defined BELOW the __main__ guard, so the
    33,143-tweet official export had never once been read, and the Substack
    posts were not on the box at all. The inventory that shipped was therefore
    built from ~260 scraped posts, came back article-shaped, and was rejected:
    "it's not generic enough. it's too specific to the articles."
    """
    sources = []
    sources.append(("x-archive (originals, weighted recent)",
                    load_archive_originals()))
    for name in ("geoppls.jsonl", "innovativehype.jsonl"):
        sources.append((name, load_jsonl(name, min_len)))
    # Substack posts are 1,500-2,500-word arguments. Splitting on blank lines
    # keeps each paragraph inside the model's window while keeping the
    # long-form reasoning that tweets do not carry.
    longform = []
    for post in load_jsonl("substack_posts.jsonl", 400):
        for para in post.split("\n\n"):
            para = para.strip()
            if len(para) >= 200:
                longform.append(para)
    sources.append(("substack_posts.jsonl (paragraphs)", longform))

    seen, out = set(), []
    for label, texts in sources:
        kept = 0
        for t in texts:
            t = t.replace("\n", " ").strip()
            if len(t) < min_len or t in seen:
                continue
            seen.add(t)
            out.append(t)
            kept += 1
        # Say the zero. A source contributing nothing must look different from
        # a source that is absent, and both must look different from a healthy
        # run. This is the whole reason the archive went unread for a day.
        print("  %-42s %6d read, %6d kept" % (label, len(texts), kept))
        if kept == 0:
            raise RuntimeError(
                "%s contributed 0 posts. Every position it carries is missing "
                "from the inventory, and the run would still have finished."
                % label)
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
             "subject": a.get("subject", ""),
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
                           "subject": a.get("subject", ""),
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
    print("These are RAW candidates, one pass over the corpus in batches, so "
          "near-duplicates are expected. Run scripts/consolidate_angles.py to "
          "merge them into angles.yaml.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
