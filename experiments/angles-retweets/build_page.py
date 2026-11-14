"""One page comparing the retweet options. Writes OUT.html with the data inline.

  build_page.py OUT.html
"""
import html, json, os, sys
from collections import Counter
import yaml
HERE = os.path.dirname(os.path.abspath(__file__))

J = lambda f: json.load(open(os.path.join(HERE, f)))
stance = J("rt_stance.json")["rows"]        # unfiltered positions + own-words verdict
labels = J("rt_labels.json")                 # every retweet with its label
cur_n = sum(1 for a in yaml.safe_load(open("/root/innovative-hype-newsletter/angles.yaml"))["angles"]
            if a.get("enabled", True))

# Trace each position to the retweets its evidence quotes come from. The
# quality filter keeps a position if any of its source retweets is kept.
import re
norm = lambda t: re.sub(r"[^a-z0-9]", "", t.lower())
T = [(norm(r["text"]), r) for r in labels]
for r in stance:
    src = []
    for ev in r.get("evidence") or []:
        e = norm(ev)
        if len(e) >= 15:
            src += [x for t, x in T if e[:60] in t]
    r["src"] = [{"h": x["handle"], "label": x["label"], "t": x["text"][:240]} for x in src]
    r["qf_kept"] = None if not src else any(x["keep"] for x in src)

lab_n = Counter(r["label"] for r in labels)
own_n = sum(r["handle"] in ("geoppls", "micahppls", "innovativehype") for r in labels)
st_n = Counter(r["stance"] for r in stance)
EX = ["Trading is essentially", "Giveaways are", "Advertising baked", "surveillance and age",
      "Programming is going", "drone industry", "top 1%"]
examples = []
for k in EX:
    r = next((r for r in stance if k in r["claim"]), None)
    if r:
        examples.append({"claim": r["claim"], "own": r["stance"], "qf": r["qf_kept"],
                         "src": [x["label"] for x in r["src"]]})
data = {
    "cur_n": cur_n, "rt_total": len(labels), "own_n": own_n, "lab_n": lab_n,
    "unf_n": len(stance), "unf_new": sum(r["new"] for r in stance), "st_n": st_n,
    "qf_kept_ids": sum(r["keep"] for r in labels),
    "qf_keep": sum(r["qf_kept"] is True for r in stance),
    "qf_untraced": sum(r["qf_kept"] is None for r in stance),
    "qf_keep_new": sum(r["qf_kept"] is True and r["new"] for r in stance),
    "own_keep_new": sum(r["stance"] == "agree" and r["new"] for r in stance),
    "both": sum(r["qf_kept"] is True and r["stance"] == "agree" for r in stance),
    "only_qf": sum(r["qf_kept"] is True and r["stance"] != "agree" for r in stance),
    "only_own": sum(r["qf_kept"] is False and r["stance"] == "agree" for r in stance),
    "neither": sum(r["qf_kept"] is False and r["stance"] != "agree" for r in stance),
    "examples": examples,
    "unf": [{"claim": r["claim"], "new": r["new"], "own": r["stance"], "why": r.get("stance_why", ""),
             "qf": r["qf_kept"], "src": r["src"][:3], "near": r["nearest_claim"], "cos": r["cos"]}
            for r in stance],
    "dropped": {lab: [{"h": r["handle"], "t": r["text"][:240]} for r in labels if r["label"] == lab][:60]
                for lab in ("promo", "chatter", "news", "fragment")},
    "kept": [{"h": r["handle"], "t": r["text"][:240]} for r in labels if r["keep"]][:60],
}
tpl = open(os.path.join(HERE, "page.html")).read()
open(sys.argv[1], "w").write(tpl.replace("/*DATA*/null", json.dumps(data, ensure_ascii=False).replace("</", "<\\/")))
print("wrote", sys.argv[1], "| quality filter keeps", data["qf_keep"], "untraced", data["qf_untraced"],
      "| own words keeps", st_n["agree"], "| both", data["both"], "only qf", data["only_qf"],
      "only own", data["only_own"], "neither", data["neither"])
