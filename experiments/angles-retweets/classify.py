"""Quality filter on retweets. No comparison with Micah's own posts.

A model labels every retweet (60+ characters, as the extractor reads them):
  view      someone states an opinion or a claim a person could hold
  news      a report of a fact or event, with no stance
  promo     an ad, giveaway, mint, airdrop, contest, sale, event or course pitch,
            "follow and RT", a project shilling itself
  chatter   personal updates, thanks, greetings, jokes, memes, reactions
  fragment  too cut off or too vague to read as anything
Keep = view. Retweets of his own accounts (geoppls, micahppls, innovativehype)
are his words and are always kept.

  classify.py OUT.json
"""
import json, os, re, sys
from concurrent.futures import ThreadPoolExecutor
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "scripts"))
import narrative_desk as nd
import extract_angles as ea

OWN = {"geoppls", "micahppls", "innovativehype"}
PER_CALL = 50
LABELS = ("view", "news", "promo", "chatter", "fragment")
SYSTEM = (
    "Label each numbered tweet with exactly one label:\n"
    "  view     - states an opinion or a claim a person could hold and defend\n"
    "  news     - reports a fact or event with no stance\n"
    "  promo    - an ad, giveaway, mint, airdrop, whitelist spot, contest, sale, "
    "event, course or newsletter pitch, 'follow and RT', a project promoting itself\n"
    "  chatter  - personal update, thanks, greeting, joke, meme, reaction\n"
    "  fragment - too cut off or too vague to read as anything\n"
    'Output STRICT JSON: {"labels": [{"n": 1, "label": "view"}]} with every number.'
)

rows = []
for p in json.load(open(ea.ARCHIVE_JSON)):
    if not p.get("is_rt") or p.get("is_reply"):
        continue
    m = re.match(r"RT @(\w+):\s*", p.get("text") or "")
    text = (p["text"][m.end():] if m else p["text"]).strip()
    if len(text) < 60:
        continue
    rows.append({"id": p["id"], "handle": m.group(1).lower() if m else "", "text": text})
print("retweets to label:", len(rows), flush=True)

def ask(start):
    chunk = rows[start:start + PER_CALL]
    user = "\n".join("%d. %s" % (i + 1, r["text"][:300].replace("\n", " ")) for i, r in enumerate(chunk))
    try:
        got = json.loads(nd.call_llm(SYSTEM, user, max_tokens=3000)).get("labels", [])
        return start, {int(g["n"]): g.get("label") for g in got if "n" in g}
    except Exception as e:
        print("  batch at %d failed: %s" % (start, e), flush=True)
        return start, {}

with ThreadPoolExecutor(4) as ex:
    for start, got in ex.map(ask, range(0, len(rows), PER_CALL)):
        for i in range(min(PER_CALL, len(rows) - start)):
            lab = got.get(i + 1)
            rows[start + i]["label"] = lab if lab in LABELS else "unlabeled"
for r in rows:
    r["keep"] = r["handle"] in OWN or r["label"] == "view"
json.dump(rows, open(sys.argv[1], "w"), indent=1, ensure_ascii=False)
from collections import Counter
print("labels:", Counter(r["label"] for r in rows).most_common())
print("own-account retweets:", sum(r["handle"] in OWN for r in rows), "| keep:", sum(r["keep"] for r in rows), "of", len(rows))
