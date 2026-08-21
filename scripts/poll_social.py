#!/usr/bin/env python3
"""poll_social.py — quick incremental poll of social accounts.

Pulls the latest page from nitter (tiekoetter instance), appends only new
posts to corpus/{account}.jsonl. Deduped by tweet ID.

Accounts: Polymarket, Kalshi, geoppls, innovativehype

Designed to run on a cron every ~1-2 hours. Each run is fast: solves
one Anubis PoW, fetches one page per account, writes deltas only.

Returns JSON summary: {"polymarket": N_new, "kalshi": N_new, "geoppls": N_new, "innovativehype": N_new, "justin": N_total, "ts": ...}
"""

import gzip, hashlib, http.cookiejar, json, os, re, ssl, sys, time, urllib.parse, urllib.request
from datetime import datetime, timezone

UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
BASE = "https://nitter.tiekoetter.com"
CORPUS = os.environ.get("LP_CORPUS", os.path.join(os.path.dirname(__file__), "..", "corpus"))
os.makedirs(CORPUS, exist_ok=True)

ACCOUNTS = ["Polymarket", "Kalshi", "geoppls", "innovativehype"]

_ctx = ssl.create_default_context()
_ctx.check_hostname = False
_ctx.verify_mode = ssl.CERT_NONE

_cj = http.cookiejar.CookieJar()
_opener = urllib.request.build_opener(
    urllib.request.HTTPCookieProcessor(_cj),
    urllib.request.HTTPSHandler(context=_ctx),
)


def _get(url):
    req = urllib.request.Request(url, headers={
        "User-Agent": UA, "Accept": "text/html,*/*", "Accept-Encoding": "gzip",
    })
    with _opener.open(req, timeout=30) as r:
        raw = r.read()
        if r.headers.get("Content-Encoding") == "gzip":
            raw = gzip.decompress(raw)
        return raw


def _solve(html):
    m = re.search(r'<script id="anubis_challenge" type="application/json">(.*?)</script>', html, re.S)
    if not m:
        return
    ch = json.loads(m.group(1))["challenge"]
    rd = ch["randomData"]
    nonce = 0
    while True:
        h = hashlib.sha256((rd + str(nonce)).encode()).digest()
        if h[0] == 0 and h[1] == 0:
            break
        nonce += 1
    found = hashlib.sha256((rd + str(nonce)).encode()).hexdigest()
    p = urllib.parse.urlencode({
        "id": ch["id"], "response": found, "nonce": nonce, "redir": "/", "elapsedTime": "500",
    })
    _get(BASE + "/.within.website/x/cmd/anubis/api/pass-challenge?" + p)


def _auth():
    h = _get(BASE + "/Polymarket").decode("utf-8", "replace")
    _solve(h)


def _extract(html):
    posts = []
    items = re.findall(r'class="timeline-item[^"]*"(.*?)(?=class="timeline-item|class="show-more|$)', html, re.S)
    for item in items:
        m_id = re.search(r'/status/(\d+)', item)
        if not m_id:
            continue
        m_date = re.search(r'title="([A-Z][a-z]{2} \d+, \d{4} · [^"]+)"', item)
        m_text = re.search(r'dir="auto"[^>]*>(.*?)</div>', item, re.S)
        text = re.sub(r'<[^>]+>', ' ', m_text.group(1)) if m_text else ""
        text = re.sub(r'\s+', ' ', text).strip()
        if text:
            posts.append({
                "id": m_id.group(1),
                "date": m_date.group(1) if m_date else "",
                "text": text,
            })
    return posts


def _load_ids(path):
    if not os.path.exists(path):
        return set()
    with open(path) as f:
        return {json.loads(l)["id"] for l in f if l.strip()}


def _append(path, posts):
    if not posts:
        return
    with open(path, "a") as f:
        for p in posts:
            f.write(json.dumps(p) + "\n")


def poll_account(screen):
    """Fetch one page of an account timeline, append new posts. Returns (#new, #total_page, error)."""
    path = os.path.join(CORPUS, f"{screen.lower()}.jsonl")
    existing = _load_ids(path)
    try:
        html = _get(BASE + f"/{screen}").decode("utf-8", "replace")
    except Exception as e:
        return 0, 0, str(e)[:80]
    posts = _extract(html)
    fresh = [p for p in posts if p["id"] not in existing]
    _append(path, fresh)
    return len(fresh), len(posts), None


def main():
    ts = datetime.now(timezone.utc).isoformat()
    try:
        _auth()
    except Exception as e:
        print(json.dumps({"error": f"auth failed: {e}", "ts": ts}))
        sys.exit(1)

    results = {}
    for screen in ACCOUNTS:
        new, total, err = poll_account(screen)
        results[screen.lower()] = {"new": new, "page_size": total, "error": err}
        time.sleep(0.3)

    # build the JUST IN union from ALL account files (geoppls + innovativehype + polymarket + kalshi)
    justin_ids = set()
    justin_posts = []
    for screen in ACCOUNTS:
        fp = os.path.join(CORPUS, f"{screen.lower()}.jsonl")
        if not os.path.exists(fp):
            continue
        for line in open(fp):
            line = line.strip()
            if not line:
                continue
            p = json.loads(line)
            if p.get("text","").upper().startswith("JUST IN:") and p["id"] not in justin_ids:
                justin_ids.add(p["id"])
                justin_posts.append({**p, "account": screen})
    justin_path = os.path.join(CORPUS, "justin.jsonl")
    with open(justin_path, "w") as f:
        for p in sorted(justin_posts, key=lambda x: x.get("date","")):
            f.write(json.dumps(p) + "\n")
    results["justin"] = {"total": len(justin_posts)}
    results["ts"] = ts

    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
