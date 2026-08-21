#!/usr/bin/env python3
"""
pull_corpus.py — collect a month of @Polymarket and @Kalshi posts via nitter.

nitter.net RSS caps at 20 posts (a few hours), and its HTML is bot-blocked.
This script uses the tiekoetter.com nitter instance, which serves full
timelines with cursor pagination behind an Anubis SHA-256 proof-of-work
challenge. We solve the PoW in-process (difficulty 4 = 2 zero bytes = ~16
bits, ~0.06s) to earn a session cookie, then page back through the cursor.

Output (written next to this script, configurable via --out-dir):
  polymarket.jsonl   all @Polymarket posts in the window
  kalshi.jsonl       all @Kalshi posts in the window
  justin.jsonl       the subset whose text starts with "JUST IN:"

Usage:
  python3 pull_corpus.py --days 31
  python3 pull_corpus.py --accounts Polymarket,Kalshi --out-dir /root/innovative-hype-newsletter/corpus
"""
import argparse
import gzip
import hashlib
import html as H
import http.cookiejar
import json
import re
import ssl
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
BASE = "https://nitter.tiekoetter.com"

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
        "User-Agent": UA, "Accept": "text/html,*/*", "Accept-Encoding": "gzip"})
    with _opener.open(req, timeout=30) as r:
        raw = r.read()
        if r.headers.get("Content-Encoding") == "gzip":
            raw = gzip.decompress(raw)
        return raw


def _solve_anubis(html):
    """Solve the Anubis PoW if the page is a challenge. No-op otherwise."""
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
    params = urllib.parse.urlencode({
        "id": ch["id"], "response": found, "nonce": nonce,
        "redir": "/", "elapsedTime": "500"})
    _get(BASE + "/.within.website/x/cmd/anubis/api/pass-challenge?" + params)


def _clean(t):
    return " ".join(H.unescape(re.sub(r"<[^>]+>", " ", t)).split())


def _parse_page(html):
    out = []
    for block in re.split(r'<div class="timeline-item', html)[1:]:
        text_m = re.search(r'class="tweet-content media-body" dir="auto">(.*?)</div>', block, re.S)
        date_m = re.search(r'class="tweet-date"><a href="([^"]+)" title="([^"]+)"', block)
        status_m = re.search(r'/status/(\d+)', block)
        if not text_m:
            continue
        out.append({
            "text": _clean(text_m.group(1)),
            "date": date_m.group(2) if date_m else None,
            "id": status_m.group(1) if status_m else None,
        })
    return out


def _parse_dt(s):
    if not s:
        return None
    try:
        # "Aug 17, 2026 · 1:18 PM UTC"
        s = s.split(" · ")[0].strip()
        return datetime.strptime(s, "%b %d, %Y").replace(tzinfo=timezone.utc)
    except Exception:
        return None


def collect(account, cutoff_dt, max_pages=400, delay=0.25):
    tweets, seen = [], set()
    url = BASE + "/" + account
    page = 0
    while page < max_pages:
        raw = _get(url).decode("utf-8", "replace")
        _solve_anubis(raw)
        raw = _get(url).decode("utf-8", "replace")
        page_items = _parse_page(raw)
        if not page_items:
            print("  [%s] empty page at %d — stopping" % (account, page))
            break
        added = 0
        for t in page_items:
            if t["id"] and t["id"] in seen:
                continue
            seen.add(t["id"])
            tweets.append(t)
            added += 1
        oldest = min((_parse_dt(t["date"]) for t in page_items if _parse_dt(t["date"])), default=None)
        print("  [%s] page %d: +%d (total %d) oldest=%s" %
              (account, page, added, len(tweets), oldest.strftime("%Y-%m-%d") if oldest else "?"))
        if oldest and oldest < cutoff_dt:
            print("  [%s] reached cutoff" % account)
            break
        m = re.search(r'class="show-more"><a href="([^"]+)"', raw)
        if not m:
            print("  [%s] no more cursor — done" % account)
            break
        url = BASE + "/" + account + m.group(1)
        page += 1
        time.sleep(delay)
    return tweets


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=31)
    ap.add_argument("--accounts", default="Polymarket,Kalshi")
    ap.add_argument("--out-dir", default="corpus")
    args = ap.parse_args()

    cutoff = datetime.now(timezone.utc) - timedelta(days=args.days)
    print("Cutoff: %s (%d days back)" % (cutoff.strftime("%Y-%m-%d"), args.days))

    import os
    os.makedirs(args.out_dir, exist_ok=True)

    all_posts = []
    for acc in [a.strip() for a in args.accounts.split(",")]:
        print("Collecting @%s ..." % acc)
        posts = collect(acc, cutoff)
        path = os.path.join(args.out_dir, acc.lower() + ".jsonl")
        with open(path, "w") as f:
            for p in posts:
                f.write(json.dumps(p) + "\n")
        print("  wrote %d posts to %s" % (len(posts), path))
        for p in posts:
            p["account"] = acc
        all_posts.extend(posts)

    justin = [p for p in all_posts if p["text"].upper().startswith("JUST IN")]
    jp = os.path.join(args.out_dir, "justin.jsonl")
    with open(jp, "w") as f:
        for p in justin:
            f.write(json.dumps(p) + "\n")
    print("\nTOTAL: %d posts, %d JUST IN" % (len(all_posts), len(justin)))
    print("Wrote justin.jsonl -> %s" % jp)


if __name__ == "__main__":
    main()
