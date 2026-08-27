#!/usr/bin/env python3
"""build_voice_profile.py — extract Micah's PERSPECTIVES from the corpus.

The unigram lift layer (seeds) holds the topic but drops the stance: a seed
like "flock" ranks a Flock story up while the sarcasm in "yum authoritarianism
tastes so good" never reaches the model that writes the card. This script
recovers the missing half. One DeepSeek pass over the recent corpus produces
voice_profile.json:

  entries: [{topic, stance, tone, exemplars, categories}]

  topic      2-5 words, what the thread of thought is about
  stance     his actual position, in his register
  tone       sarcastic / matter-of-fact / hype / ...
  exemplars  VERBATIM tweet texts (validated character-for-character against
             the corpus below; a fabricated quote is dropped, an entry with
             zero verbatim exemplars is dropped entirely)
  categories which narrative signatures (scripts/brief.py) it colors

narrative_desk.py injects matching entries into the desk prompt so cards are
written in his perspective, not just on his topics.

Usage:
  python3 scripts/build_voice_profile.py            # last 14 days
  IH_VOICE_DAYS=30 python3 scripts/build_voice_profile.py
"""
import json
import os
import sys
from datetime import datetime, timezone

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "scripts"))
OUT = os.path.join(REPO, "voice_profile.json")

DAYS = int(os.environ.get("IH_VOICE_DAYS", "14"))
MAX_POSTS = int(os.environ.get("IH_VOICE_MAX_POSTS", "500"))
MIN_LEN = int(os.environ.get("IH_VOICE_MIN_LEN", "12"))


def corpus_posts():
    """Recent rows from the two voice handles, oldest first."""
    import brief
    from poll_social import parse_date
    rows = []
    for handle in ("geoppls", "innovativehype"):
        path = os.path.join(REPO, "corpus", handle + ".jsonl")
        for line in open(path):
            try:
                r = json.loads(line)
            except ValueError:
                continue
            d = parse_date(r.get("date"))
            if d:
                rows.append({"handle": handle, "dt": d,
                             "text": (r.get("text") or "").strip()})
    rows.sort(key=lambda r: r["dt"])
    cutoff = datetime.now(timezone.utc).toordinal() - DAYS
    rows = [r for r in rows if r["dt"].toordinal() >= cutoff
            and len(r["text"]) >= MIN_LEN][-MAX_POSTS:]
    return rows


def main():
    import brief
    import narrative_desk

    posts = corpus_posts()
    if len(posts) < 20:
        raise SystemExit(f"only {len(posts)} recent posts; refusing to "
                         "profile a corpus this thin")
    categories = [s["name"] for s in brief.NARRATIVE_SIGNATURES]
    blob = "\n".join(f"{i}. @{r['handle']}: {r['text']}"
                     for i, r in enumerate(posts, 1))

    system = (
        "You distill an editorial voice. Input: recent tweets from Micah's two "
        "accounts (@geoppls personal, @innovativehype brand). Extract the "
        "distinct recurring PERSPECTIVES: a topic plus HIS actual stance on it, "
        "which is usually sarcastic, contrarian or hype rather than neutral. "
        "The stance is the point; the topic alone is worthless. Return STRICT "
        "JSON: {\"entries\": [{\"topic\": str (2-5 words), \"stance\": str (one "
        "sentence, his position in his register), \"tone\": str, \"exemplars\": "
        "[3 tweet texts copied CHARACTER-FOR-CHARACTER from the input, never "
        "paraphrased], \"categories\": [1-3 from the list below]}]}. Categories "
        "list: " + " | ".join(categories) +
        ". Cover every distinct perspective you can support with verbatim "
        "exemplars; 5 to 12 entries."
    )
    user = "TWEETS:\n" + blob

    raw = narrative_desk.call_llm(system, user, max_tokens=4000)
    data = json.loads(raw)
    entries = []
    corpus_texts = {r["text"] for r in posts}
    dropped = 0
    for e in data.get("entries", []):
        ex = [x for x in (e.get("exemplars") or []) if x in corpus_texts]
        if not ex:
            dropped += 1
            continue
        e["exemplars"] = ex[:3]
        e["categories"] = [c for c in (e.get("categories") or [])
                           if c in categories]
        entries.append(e)

    out = {
        "built": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "window_days": DAYS,
        "n_posts": len(posts),
        "source": {h: sum(1 for r in posts if r["handle"] == h)
                   for h in ("geoppls", "innovativehype")},
        "corpus_newest": posts[-1]["dt"].strftime("%Y-%m-%d %H:%M UTC"),
        "entries": entries,
    }
    with open(OUT, "w") as f:
        json.dump(out, f, indent=1, ensure_ascii=False)
    print(f"wrote {OUT}: {len(entries)} perspective entries from "
          f"{len(posts)} posts ({out['source']}, newest {out['corpus_newest']}); "
          f"{dropped} entries dropped for fabricated exemplars")
    for e in entries:
        print(f"  - {e['topic']}: {e['stance'][:90]}")


if __name__ == "__main__":
    main()
