#!/usr/bin/env python3
"""narrative_desk.py — LLM narrative desk for the Innovative Hype brief.

Takes the deterministic clusters + mined data points from brief.py and runs
an LLM pass (the same pattern as Legendary Picks' ingest_league_narratives)
to write narrative cards:

  narrative  — one-sentence title naming the CONVERSATION (the story the
               data point tells), plain news language, no outlet-name
  paragraph  — 2-4 sentences of body prose: what's happening, who it
               affects, concrete names/numbers, the data point grounded
  source_ids — which articles this card actually grounds in

VERSIONED RUNS (Micah, 2026-08-21): every run writes a snapshot to
  runs/<timestamp>/
    input.json      — the clusters + data points fed to the model
    output.json     — the raw model response (strict JSON)
    cards.json      — the parsed cards, ready for brief.html
    meta.json       — code version (git SHA), model, prompt hash, timestamp
So every generation can be diffed and compared, exactly like LP's
news_narratives_runs table.

POOL-KEY DEDUP: if the input pool (cluster membership + data points) hasn't
changed since the last run, skip regeneration unless --force is passed.
"""

import argparse
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEB = os.path.join(REPO, "web")
RUNS = os.path.join(REPO, "runs")

# Model: same provider/family LP uses for its narrative desk.
MODEL = "deepseek/deepseek-v4-flash-0731"
PROVIDER_BASE = "https://inference-api.nousresearch.com/v1"

_SYSTEM = (
    "You are the narrative desk for Innovative Hype, a news briefing. "
    "You are given clusters of articles — each cluster is a recurring theme "
    "with mined data points from the article bodies. Write ONE card per "
    "cluster.\n"
    "THE DATA POINT IS THE HOOK. Each cluster carries data points (a "
    "dollar figure, a percentage, a threshold crossed, a market-implied "
    "probability). The card leads with the strongest one — this is the "
    "JUST IN material: 'US strategic petroleum reserve falls below 300M "
    "barrels for the first time in 40+ years'. Not every number matters; "
    "the one that crosses a meaningful threshold does.\n"
    "ASK THE QUESTION: what does this data point tell a story about? The "
    "answer is the narrative.\n"
    "THE OUTLET IS NOT THE STORY. Never write 'TechCrunch reported X'. "
    "Write the FACT as the subject: 'The AI data layer is printing money'. "
    "Name a masthead only when who reported it is itself the fact (an "
    "exclusive nobody else matched).\n"
    "ONE TOPIC PER CARD. A card covers exactly the cluster's theme. If an "
    "article in the cluster is off-theme, LEAVE IT OUT and don't cite it in "
    "source_ids.\n"
    "THE STORY IS ALWAYS ABOUT PEOPLE. Every data point lands on someone: "
    "who does it happen to, what changes for them.\n"
    "PLAIN NEWS LANGUAGE. Subject, plain verb, object. No idioms, no puns, "
    "no metaphors. Spell out jargon. Concrete names and numbers from the "
    "articles.\n"
    "DECLINE WEAK CLUSTERS. If a cluster has no shared theme worth a card, "
    'output {"narrative": null} for it.\n'
    "Output STRICT JSON only: "
    '{"cards": [{"narrative": "...", "paragraph": "...", '
    '"data_point": "...", "source_ids": [0, 2]}]} where source_ids are the '
    "indexes of the articles in that cluster's list that the card grounds in."
)


def render_brief_html(clusters, parsed, run_dir):
    """Render the LLM cards into web/brief.html with article links resolved
    from source_ids (indexes into each cluster's item list)."""
    from datetime import datetime, timezone as _tz
    import html as _html

    cards_html = []
    for ci, card in enumerate(parsed.get("cards", [])):
        if not card.get("narrative"):
            continue  # declined cluster
        cl = clusters[ci] if ci < len(clusters) else None
        sources = []
        for sid in card.get("source_ids", []):
            if cl and sid < len(cl["items"]):
                a = cl["items"][sid]["article"]
                sources.append(
                    f'<li><a href="{a.get("link","#")}" target="_blank" rel="noopener">{_html.escape(a.get("title",""))} <span class="src">({a.get("source","")})</span></a></li>'
                )
        if not sources:
            continue  # card with no real articles = no receipts, skip
        dp_html = f'<p class="brief-dp">▸ {_html.escape(card.get("data_point",""))}</p>' if card.get("data_point") else ""
        para_html = f'<p class="brief-para">{_html.escape(card.get("paragraph",""))}</p>' if card.get("paragraph") else ""
        cards_html.append(f"""
    <article class="brief-card">
      <h3 class="brief-title">{_html.escape(card.get("narrative",""))}</h3>
      {dp_html}
      {para_html}
      <ul class="brief-list">{''.join(sources)}</ul>
    </article>""")

    ts = datetime.now(_tz.utc).strftime("%Y-%m-%d %H:%M UTC")
    meta = json.load(open(os.path.join(run_dir, "meta.json"))) if os.path.exists(os.path.join(run_dir, "meta.json")) else {}
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>INNOVATIVE HYPE — BRIEF</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Oswald:wght@400;500;600;700&family=DM+Sans:wght@300;400;500;600&display=swap" rel="stylesheet">
<style>
  :root {{ --white:#fff; --off-white:#f8f8f8; --ink:#0a0a0a; --ink-light:#3a3a3a; --ink-muted:#888; --gold:#d4af37; --gold-dark:#b8860b; --border:#e8e8e8; }}
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{ font-family:'DM Sans',system-ui,sans-serif; background:var(--white); color:var(--ink); -webkit-font-smoothing:antialiased; }}
  .wrap {{ max-width:760px; margin:0 auto; padding:2.5rem 1.5rem; }}
  .page-title {{ font-family:'Oswald',sans-serif; font-weight:700; font-size:2rem; text-transform:uppercase; letter-spacing:-0.02em; margin-bottom:.25rem; }}
  .page-meta {{ font-size:.75rem; color:var(--ink-muted); text-transform:uppercase; letter-spacing:.05em; margin-bottom:2rem; }}
  .brief-card {{ background:var(--off-white); border:1px solid var(--border); border-top:3px solid var(--gold); padding:1.25rem 1.5rem; margin-bottom:1.25rem; }}
  .brief-title {{ font-family:'Oswald',sans-serif; font-weight:600; font-size:1.15rem; line-height:1.25; margin-bottom:.5rem; }}
  .brief-dp {{ font-size:.9rem; line-height:1.5; color:var(--ink); margin-bottom:.6rem; padding-left:.9rem; border-left:2px solid var(--gold); font-style:italic; }}
  .brief-para {{ font-size:.9rem; line-height:1.55; color:var(--ink-light); margin-bottom:.6rem; }}
  .brief-list {{ list-style:none; padding-left:0; }}
  .brief-list li {{ font-size:.85rem; line-height:1.5; color:var(--ink-light); padding:.15rem 0 .15rem 1.1rem; position:relative; }}
  .brief-list li::before {{ content:'·'; position:absolute; left:0; color:var(--gold-dark); }}
  .brief-list a {{ color:var(--ink-light); text-decoration:none; }}
  .brief-list a:hover {{ color:var(--gold-dark); }}
  .brief-list .src {{ color:var(--ink-muted); font-size:.7rem; text-transform:uppercase; letter-spacing:.03em; }}
  .back {{ display:inline-block; margin-top:2rem; font-family:'Oswald',sans-serif; font-size:.8rem; text-transform:uppercase; letter-spacing:.05em; color:var(--ink); text-decoration:none; border-bottom:2px solid var(--gold); padding-bottom:2px; }}
</style>
</head>
<body>
<div class="wrap">
  <h1 class="page-title">Innovative Hype — Brief</h1>
  <div class="page-meta">Narrative brief · LLM desk · run {meta.get('code_version','?')} · {ts}</div>
  {''.join(cards_html)}
  <a class="back" href="index.html">← Back to feed</a>
</div>
</body>
</html>
"""
    with open(os.path.join(WEB, "brief.html"), "w") as f:
        f.write(html)
    print(f"Rendered web/brief.html with {len(cards_html)} cards")


def git_sha():
    try:
        out = subprocess.run(
            ["git", "-C", REPO, "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, timeout=10,
        )
        return out.stdout.strip() or "unknown"
    except Exception:
        return "unknown"


def pool_key(clusters):
    """Hash of cluster membership + data points — used for dedup."""
    material = []
    for cl in clusters:
        material.append(cl["sig"]["name"])
        for item in cl["items"]:
            material.append(item["article"].get("title", ""))
            material.append(item["article"].get("link", ""))
            material.extend(item["points"])
    return hashlib.sha256("\n".join(material).encode()).hexdigest()[:16]


def load_clusters():
    """Load clusters from the deterministic brief pipeline."""
    sys.path.insert(0, os.path.join(REPO, "scripts"))
    import brief
    with open(os.path.join(WEB, "articles.json")) as f:
        data = json.load(f)
    md, cards = brief.make_brief(data["articles"])
    # Rebuild the enriched clusters the same way make_brief does
    scored = [a for a in data["articles"] if not a.get("_noise")]
    scored.sort(key=lambda x: -x.get("_score", 0))
    enriched = []
    for a in scored:
        points = brief.mine_data_points(a)
        sig, hits = brief.signature_for(a, points)
        if sig and points:
            enriched.append({"article": a, "points": points, "sig": sig, "hits": hits})
    from collections import OrderedDict
    clusters = OrderedDict()
    for e in enriched:
        name = e["sig"]["name"]
        clusters.setdefault(name, {"sig": e["sig"], "items": []})
        clusters[name]["items"].append(e)
    return list(clusters.values())


def call_model(clusters):
    """Call the LLM with the cluster material. Returns raw JSON string."""
    import urllib.request

    # Use NOUS_PORTAL_KEY — the DEEPSEEK_API_KEY in config is dead/out of funds
    # (measured 2026-08-21: 401 on chat, portal key returns 200).
    key = os.environ.get("NOUS_PORTAL_KEY", "")
    if not key:
        env_path = "/root/.hermes/.env"
        if os.path.exists(env_path):
            for line in open(env_path):
                if line.startswith("NOUS_PORTAL_KEY="):
                    key = line.strip().split("=", 1)[1].strip('"').strip("'")
                    break
    if not key:
        raise RuntimeError("No NOUS_PORTAL_KEY found in /root/.hermes/.env")

    prompt_lines = ["Today's date: %s" % datetime.now(timezone.utc).strftime("%Y-%m-%d"), ""]
    for ci, cl in enumerate(clusters):
        prompt_lines.append(f"CLUSTER {ci}: {cl['sig']['name']} (voice_weight {cl['sig'].get('voice_weight','?')})")
        for item in cl["items"]:
            a = item["article"]
            prompt_lines.append(f"  {item['points'][0][:200] if item['points'] else 'no data point'}")
            prompt_lines.append(f"  {a.get('title','')} ({a.get('source','')})")
            body = (a.get("_body", "") or "")[:600]
            if body:
                prompt_lines.append(f"    {body[:300]}")
        prompt_lines.append("")

    body = json.dumps({
        "model": MODEL,
        "messages": [
            {"role": "system", "content": _SYSTEM},
            {"role": "user", "content": "\n".join(prompt_lines)},
        ],
        "temperature": 0.7,
        "max_tokens": 3000,
        "reasoning": {"enabled": False},  # we want content, not a thinking dump
        "response_format": {"type": "json_object"},
    }).encode()

    req = urllib.request.Request(
        PROVIDER_BASE + "/chat/completions",
        data=body,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {key}",
            # urllib sends 'Python-urllib/3.8' by default; some gateways 403 it
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) narrative-desk/1.0",
        },
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = json.loads(resp.read().decode())
    return data["choices"][0]["message"]["content"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true", help="regenerate even if pool unchanged")
    args = ap.parse_args()

    clusters = load_clusters()
    key = pool_key(clusters)
    os.makedirs(RUNS, exist_ok=True)

    # Pool-key dedup: skip if the last run used the same material
    meta_path = os.path.join(RUNS, "latest", "meta.json")
    if os.path.exists(meta_path) and not args.force:
        with open(meta_path) as f:
            last = json.load(f)
        if last.get("pool_key") == key:
            print(f"Pool unchanged ({key}) — skipping. Use --force to regenerate.")
            return 0

    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    run_dir = os.path.join(RUNS, ts)
    os.makedirs(run_dir, exist_ok=True)
    # Keep a stable 'latest' pointer
    latest = os.path.join(RUNS, "latest")
    if os.path.islink(latest):
        os.remove(latest)
    elif os.path.exists(latest):
        import shutil
        shutil.rmtree(latest)
    os.symlink(run_dir, latest)

    with open(os.path.join(run_dir, "input.json"), "w") as f:
        json.dump(
            {
                "clusters": [
                    {
                        "name": cl["sig"]["name"],
                        "voice_weight": cl["sig"].get("voice_weight"),
                        "items": [
                            {
                                "title": item["article"].get("title"),
                                "source": item["article"].get("source"),
                                "link": item["article"].get("link"),
                                "points": item["points"],
                                "body_excerpt": (item["article"].get("_body") or "")[:600],
                            }
                            for item in cl["items"]
                        ],
                    }
                    for cl in clusters
                ]
            },
            f, indent=2,
        )

    print(f"Calling {MODEL} with {len(clusters)} clusters...")
    raw = call_model(clusters)
    with open(os.path.join(run_dir, "output.json"), "w") as f:
        f.write(raw)

    parsed = json.loads(raw)
    with open(os.path.join(run_dir, "cards.json"), "w") as f:
        json.dump(parsed, f, indent=2)

    # Render the cards into brief.html (resolving source_ids → article links)
    render_brief_html(clusters, parsed, run_dir)

    meta = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "code_version": git_sha(),
        "model": MODEL,
        "pool_key": key,
        "n_clusters": len(clusters),
        "prompt_hash": hashlib.sha256(_SYSTEM.encode()).hexdigest()[:12],
    }
    with open(os.path.join(run_dir, "meta.json"), "w") as f:
        json.dump(meta, f, indent=2)

    print(f"Wrote run {ts} ({key})")
    for card in parsed.get("cards", []):
        if card.get("narrative"):
            print(f"  - {card['narrative'][:80]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
