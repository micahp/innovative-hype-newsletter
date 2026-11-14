"""Whitelist test: does Micah say a retweet position in his OWN posts?

His own words are every original post (X archive originals, all years, no
replies or retweets; geoppls; innovativehype; Substack paragraphs). For each
position, support = how many of his own posts sit within cosine T of the
position's probe text (claim + subject + scope, as consolidate_angles.py).

T is not hand-picked. The current 378 angles were extracted from his own
posts, so their support is what "his position" looks like. T is set so that
90% of current angles have at least MIN_SUPPORT own posts at T or above.

  support.py CURRENT_angles.yaml RETWEET_compare.json OUT.json
"""
import json, os, re, sys
import numpy as np
import yaml
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "scripts"))
import consolidate_angles as ca
import embed
import extract_angles as ea

MIN_SUPPORT = 2
KEEP_FRAC = 0.90


def own_posts():
    out = []
    for p in json.load(open(ea.ARCHIVE_JSON)):
        if p.get("is_reply") or p.get("is_rt"):
            continue
        out.append((p.get("text") or "").strip())
    for name in ("geoppls.jsonl", "innovativehype.jsonl"):
        out += ea.load_jsonl(name, 0)
    for post in ea.load_jsonl("substack_posts.jsonl", 0):
        out += [x.strip() for x in post.split("\n\n")]
    seen, keep = set(), []
    for t in out:
        t = re.sub(r"https?://\S+", "", t.replace("\n", " ")).strip()
        if len(t) >= 40 and t not in seen:
            seen.add(t)
            keep.append(t)
    return keep


cur = [a for a in yaml.safe_load(open(sys.argv[1]))["angles"] if a.get("enabled", True)]
rt = json.load(open(sys.argv[2]))
posts = own_posts()
print("own posts:", len(posts))
P = np.vstack(embed.embed(posts))
rt_probe = [ca.probe({"claim": r["claim"], "subject": r["subject"], "scope": []}) for r in rt]
# The compare file has no scope, so probe the current angles the same way.
Cs = np.vstack(embed.embed([ca.probe({"claim": a["claim"], "subject": a.get("subject", ""), "scope": []})
                            for a in cur])) @ P.T
Rs = np.vstack(embed.embed(rt_probe)) @ P.T

def kth(S, k):
    return np.sort(S, axis=1)[:, -k]

cur_k = kth(Cs, MIN_SUPPORT)
T = float(np.quantile(cur_k, 1 - KEEP_FRAC))
rt_k = kth(Rs, MIN_SUPPORT)
print("T = %.3f (90%% of current angles have >= %d own posts at T)" % (T, MIN_SUPPORT))
print("current angles: own-post cos (2nd best) p10 %.2f p50 %.2f p90 %.2f" % tuple(np.quantile(cur_k, [.1, .5, .9])))
print("retweet angles: own-post cos (2nd best) p10 %.2f p50 %.2f p90 %.2f" % tuple(np.quantile(rt_k, [.1, .5, .9])))
rows = []
for i, r in enumerate(rt):
    top = np.argsort(Rs[i])[::-1][:3]
    rows.append({**r, "own_cos2": round(float(rt_k[i]), 3), "own_support": int((Rs[i] >= T).sum()),
                 "keep": bool(rt_k[i] >= T),
                 "own_posts": [{"cos": round(float(Rs[i, j]), 3), "text": posts[j][:220]} for j in top]})
json.dump({"T": T, "min_support": MIN_SUPPORT, "rows": rows}, open(sys.argv[3], "w"), indent=1, ensure_ascii=False)
k = [r for r in rows if r["keep"]]
print("retweet positions %d | kept %d (new %d, covered %d) | dropped %d (new %d, covered %d)" % (
    len(rows), len(k), sum(r["new"] for r in k), sum(not r["new"] for r in k),
    len(rows) - len(k), sum(r["new"] for r in rows if not r["keep"]), sum(not r["new"] for r in rows if not r["keep"])))
print(embed.stats_line())
