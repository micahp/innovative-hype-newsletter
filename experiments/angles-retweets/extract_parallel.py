"""extract_angles.py main(), with the model calls 4 at a time. Same prompt,
same batches, same merge. Writes the candidates file given as argv[2].

  extract_parallel.py {no|also|only} OUT.yaml
"""
import json, os, sys
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "scripts"))
import extract_angles as ea

mode, out_path = sys.argv[1], sys.argv[2]
posts = ea.load_posts(retweets=mode)
print(f"{len(posts)} substantive posts", flush=True)
chunks = [posts[i:i + 120] for i in range(0, len(posts), 120)]

def read(chunk):
    raw = ea.nd.call_llm(ea._SYSTEM, "POSTS:\n" + "\n".join("- " + t[:400] for t in chunk), max_tokens=6000)
    return json.loads(raw).get("angles", [])

collected, failed = [], 0
with ThreadPoolExecutor(4) as ex:
    for i, fut in enumerate([ex.submit(read, c) for c in chunks]):
        try:
            got = fut.result()
            collected.extend(got)
            print(f"  batch {i}: {len(got)} positions", flush=True)
        except Exception as e:
            failed += 1
            print(f"  batch {i}: FAILED {e}", flush=True)

merged = {}
for a in collected:
    aid = (a.get("id") or "").strip().lower()
    if not aid:
        continue
    if aid in merged:
        merged[aid]["scope"] = sorted(set(merged[aid]["scope"]) | set(s.lower() for s in a.get("scope", [])))
        merged[aid]["evidence"] = (merged[aid]["evidence"] + a.get("evidence", []))[:3]
    else:
        merged[aid] = {"id": aid, "claim": a.get("claim", ""), "subject": a.get("subject", ""),
                       "scope": [s.lower() for s in a.get("scope", [])], "evidence": a.get("evidence", [])[:3]}
open(out_path, "w").write(ea.to_yaml(list(merged.values())))
print(f"{len(merged)} positions after merge, {failed} of {len(chunks)} batches failed -> {out_path}")
