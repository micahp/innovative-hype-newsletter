"""Agreement test: do Micah's own posts AGREE with a retweet position?

support.py found his 5 own posts nearest to each position by embedding. That
measures topic: "Giveaways build NFT community" matched his posts about
community. Here a model reads the position and those posts and says whether
the posts state or clearly imply the same position (agree), oppose it
(disagree), or only share the topic (topic_only). Keep = agree.

  stance.py rt_support.json OUT.json
"""
import json, os, sys
from concurrent.futures import ThreadPoolExecutor
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "scripts"))
import narrative_desk as nd
import numpy as np

PER_CALL = 12
SYSTEM = (
    "You check whether one person actually holds a position. For each ITEM you "
    "get a POSITION and up to 5 of the person's OWN posts on a related topic. "
    "Answer from the posts only.\n"
    "  agree      - at least one post states the same position or clearly implies it\n"
    "  disagree   - a post states the opposite position\n"
    "  topic_only - the posts are about the same topic but do not take this position\n"
    "Sharing a topic is NOT agreement. Be strict.\n"
    'Output STRICT JSON: {"items": [{"n": 1, "stance": "agree|disagree|topic_only", '
    '"post": 0, "why": "one short sentence"}]} where post is the number of the '
    "deciding post (0 if none)."
)

src = json.load(open(sys.argv[1]))
rows = src["rows"]
# support.py kept the top 3 own posts per row; widen to 5 is not needed for a
# first pass, so the 3 nearest are what the model reads.
def ask(start):
    chunk = rows[start:start + PER_CALL]
    lines = []
    for n, r in enumerate(chunk, 1):
        lines.append("ITEM %d\nPOSITION: %s" % (n, r["claim"]))
        for k, p in enumerate(r["own_posts"], 1):
            lines.append("  post %d: %s" % (k, p["text"]))
    got = json.loads(nd.call_llm(SYSTEM, "\n".join(lines), max_tokens=4000)).get("items", [])
    return start, {int(g["n"]): g for g in got if "n" in g}

with ThreadPoolExecutor(4) as ex:
    res = list(ex.map(ask, range(0, len(rows), PER_CALL)))
missing = 0
for start, got in res:
    for n in range(1, min(PER_CALL, len(rows) - start) + 1):
        g = got.get(n)
        r = rows[start + n - 1]
        if not g or g.get("stance") not in ("agree", "disagree", "topic_only"):
            r["stance"], missing = "unjudged", missing + 1
            continue
        r["stance"], r["stance_post"], r["stance_why"] = g["stance"], int(g.get("post") or 0), g.get("why", "")
json.dump(src, open(sys.argv[2], "w"), indent=1, ensure_ascii=False)
from collections import Counter
print("stance:", Counter(r["stance"] for r in rows).most_common(), "| unjudged", missing)
for s in ("agree", "disagree", "topic_only"):
    sub = [r for r in rows if r["stance"] == s]
    print("  %-10s %3d  (new %d, covered %d; embedding keep %d)" % (
        s, len(sub), sum(r["new"] for r in sub), sum(not r["new"] for r in sub), sum(r["keep"] for r in sub)))
