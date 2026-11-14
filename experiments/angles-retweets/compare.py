"""Which retweet positions are already in angles.yaml, and which are new.

  compare.py CURRENT_angles.yaml RETWEET_angles.yaml OUT.json

Same test consolidate_angles.py uses for "same position": cosine >= 0.66 between
the probe texts (claim + subject + scope).
"""
import json, os, sys
import numpy as np
import yaml
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "scripts"))
import consolidate_angles as ca
import embed

cur = [a for a in yaml.safe_load(open(sys.argv[1]))["angles"] if a.get("enabled", True)]
rt = yaml.safe_load(open(sys.argv[2]))["angles"]
C = np.vstack(embed.embed([ca.probe(a) for a in cur]))
R = np.vstack(embed.embed([ca.probe(a) for a in rt]))
S = R @ C.T
rows = []
for i, a in enumerate(rt):
    j = int(np.argmax(S[i]))
    rows.append({"id": a["id"], "claim": a["claim"], "subject": a.get("subject", ""),
                 "evidence": a.get("evidence", []), "nearest_id": cur[j]["id"],
                 "nearest_claim": cur[j]["claim"], "cos": round(float(S[i, j]), 3),
                 "new": bool(S[i, j] < ca.SAME_POSITION)})
rows.sort(key=lambda r: r["cos"])
json.dump(rows, open(sys.argv[3], "w"), indent=1, ensure_ascii=False)
new = [r for r in rows if r["new"]]
print("current angles %d | retweet positions %d | already covered %d | new %d"
      % (len(cur), len(rt), len(rt) - len(new), len(new)))
print("cos to nearest current angle: p25 %.2f  p50 %.2f  p75 %.2f"
      % tuple(np.percentile([r["cos"] for r in rows], [25, 50, 75])))
print(embed.stats_line())
