#!/usr/bin/env python3
"""recover_lost_stories.py — one-time merge of stories lost to the feed-window bug.

The aggregator used to rebuild articles.json from scratch each run (~20 items
per feed), so stories aged out within HOURS even after the desk had carded
them. This script pulls every article from historical run inputs that is NOT
in the current feed and merges it back, with _ts = the last run that saw it
(honest freshness — these ran TODAY). Going forward, feed_aggregator's
persistence merge keeps stories alive <=72h so this never happens again.
"""
import json
import glob
import os
import re

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEB = os.path.join(REPO, "web")
RUNS = os.path.join(REPO, "runs")


def norm(title):
    return re.sub(r"[^a-z0-9]+", " ", title.lower()).strip()


feed_path = os.path.join(WEB, "articles.json")
with open(feed_path) as f:
    out = json.load(f)

seen = {}
for a in out["articles"]:
    n = norm(a.get("title", ""))
    if n:
        seen[n] = a

recovered = []
for path in sorted(glob.glob(os.path.join(RUNS, "2026*", "input.json"))):
    run_ts = 0
    meta_path = os.path.join(os.path.dirname(path), "meta.json")
    if os.path.exists(meta_path):
        try:
            import datetime
            meta = json.load(open(meta_path))
            ts_str = meta.get("timestamp", "")
            if ts_str:
                run_ts = datetime.datetime.fromisoformat(
                    ts_str.replace("Z", "+00:00")).timestamp()
        except Exception:
            pass
    try:
        inp = json.load(open(path))
    except Exception:
        continue
    for cl in inp.get("clusters", []):
        for item in cl.get("items", []):
            t = item.get("title", "")
            n = norm(t)
            if not n or n in seen:
                continue
            seen[n] = True
            recovered.append({
                "title": t,
                "link": item.get("link", "#"),
                "summary": "",
                "source": item.get("source", ""),
                "category": "news",
                "published": "",
                "_body": (item.get("body_excerpt", "") or "")[:6000],
                "_ts": run_ts,
            })

out["articles"].extend(recovered)
with open(feed_path, "w") as f:
    json.dump(out, f, indent=2)
print(f"Recovered {len(recovered)} lost stories into articles.json "
      f"(pool now {len(out['articles'])})")
