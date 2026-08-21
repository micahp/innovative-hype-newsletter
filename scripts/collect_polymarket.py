#!/usr/bin/env python3
"""Collect Polymarket tweets from nitter with proper 429 handling.

Two prongs:
  - /Polymarket          : full timeline (~21 posts/page)
  - /search?q=from:Polymarket+JUST+IN : JUST IN subset (~20 posts/page)

Incremental: resumes from existing polymarket.jsonl / justin.jsonl in corpus/.
Stops when oldest post date <= 2026-07-17 or no next cursor.
"""

import urllib.request, urllib.parse, gzip, ssl, re, json, hashlib, http.cookiejar, base64, time, os, sys
from datetime import datetime, timezone

UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE
BASE = "https://nitter.tiekoetter.com"

CORPUS = os.path.join(os.path.dirname(__file__), "..", "corpus")
POLY_FILE = os.path.join(CORPUS, "polymarket.jsonl")
JUSTIN_FILE = os.path.join(CORPUS, "justin.jsonl")
TARGET_DATE = datetime(2026, 7, 17, tzinfo=timezone.utc)

cj = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(
    urllib.request.HTTPCookieProcessor(cj),
    urllib.request.HTTPSHandler(context=ctx)
)

def get(url):
    req = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "Accept": "text/html,*/*",
        "Accept-Encoding": "gzip"
    })
    with opener.open(req, timeout=30) as r:
        raw = r.read()
        if r.headers.get("Content-Encoding") == "gzip":
            raw = gzip.decompress(raw)
        return raw

def solve(html):
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
        "id": ch["id"],
        "response": found,
        "nonce": nonce,
        "redir": "/",
        "elapsedTime": "500"
    })
    get(BASE + "/.within.website/x/cmd/anubis/api/pass-challenge?" + p)

def get_authenticated():
    h = get(BASE + "/Polymarket").decode("utf-8", "replace")
    solve(h)
    return get(BASE + "/Polymarket").decode("utf-8", "replace")

def get_with_retry(url, max_429_retries=5):
    """GET with exponential backoff on 429. Returns (html, status_code)."""
    for attempt in range(max_429_retries + 1):
        try:
            raw = get(url)
            return raw.decode("utf-8", "replace"), 200
        except Exception as e:
            if "429" in str(e) and attempt < max_429_retries:
                wait = 15 * (2 ** attempt)  # 15, 30, 60, 120, 240s
                print(f"    429 -> waiting {wait}s (attempt {attempt+1})", flush=True)
                time.sleep(wait)
                # re-auth in case cookie expired
                get_authenticated()
                continue
            raise
    return None, 429

def extract_posts(html):
    """Extract posts from a nitter timeline/search page. Returns list of {id, date, text}."""
    posts = []
    # Each tweet is an <article> containing a <div dir="auto"> for text
    # and a timestamp in title="..." on the <time> or a[data-timestamp]
    # More robust: use the data-testid="tweet" structure
    # Nitter's HTML: each timeline-item has a data-tweet-id or the link /status/ID
    # Let's find all status links and the nearest text block
    blocks = re.findall(
        r'<a href="(/Polymarket/status/(\d+))"[^>]*>.*?</a>.*?<div[^>]*dir="auto"[^>]*>(.*?)</div>',
        html, re.S
    )
    # Simpler: split on timeline-items
    items = re.findall(r'class="timeline-item[^"]*"(.*?)(?=class="timeline-item|class="show-more|$)', html, re.S)
    if not items:
        items = [html]

    for item in items:
        # tweet id
        m_id = re.search(r'/status/(\d+)', item)
        if not m_id:
            continue
        tid = m_id.group(1)
        # date: title="Aug 5, 2026 · 12:34 PM UTC"
        m_date = re.search(r'title="([A-Z][a-z]{2} \d+, \d{4} · [^"]+)"', item)
        date_str = m_date.group(1) if m_date else ""
        # text
        m_text = re.search(r'dir="auto"[^>]*>(.*?)</div>', item, re.S)
        text = m_text.group(1) if m_text else ""
        text = re.sub(r'<[^>]+>', ' ', text)
        text = re.sub(r'\s+', ' ', text).strip()
        if text and tid:
            posts.append({"id": tid, "date": date_str, "text": text})
    return posts

def parse_date(s):
    """Parse 'Aug 5, 2026 · 12:34 PM UTC' -> datetime or None."""
    try:
        return datetime.strptime(s, "%b %d, %Y · %I:%M %p UTC").replace(tzinfo=timezone.utc)
    except:
        return None

def load_existing(path):
    """Load existing jsonl, return list of dicts."""
    if not os.path.exists(path):
        return []
    out = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out

def save_post(path, post):
    with open(path, "a") as f:
        f.write(json.dumps(post) + "\n")

def page_timeline(cursor=None):
    url = BASE + "/Polymarket"
    if cursor:
        url += "?cursor=" + urllib.parse.quote(cursor)
    html, status = get_with_retry(url)
    if status != 200:
        return [], None, html
    posts = extract_posts(html)
    m = re.search(r'class="show-more"><a href="([^"]+)"', html)
    next_c = urllib.parse.unquote(m.group(1)).split("cursor=")[1] if m else None
    return posts, next_c, html

def page_search(cursor=None):
    url = BASE + "/search?f=tweets&q=from%3APolymarket+JUST+IN&since=2026-07-01&near="
    if cursor:
        url += "&cursor=" + urllib.parse.quote(cursor)
    html, status = get_with_retry(url)
    if status != 200:
        return [], None, html
    posts = extract_posts(html)
    m = re.search(r'class="show-more"><a href="([^"]+)"', html)
    next_c = urllib.parse.unquote(m.group(1)).split("cursor=")[1] if m else None
    return posts, next_c, html

def dedup(posts, existing_ids):
    return [p for p in posts if p["id"] not in existing_ids]

def oldest_date(posts):
    ds = [parse_date(p["date"]) for p in posts if p.get("date")]
    return min(ds) if ds else None

def main():
    os.makedirs(CORPUS, exist_ok=True)
    existing_poly = load_existing(POLY_FILE)
    existing_justin = load_existing(JUSTIN_FILE)
    poly_ids = {p["id"] for p in existing_poly}
    justin_ids = {p["id"] for p in existing_justin}
    print(f"Existing: {len(existing_poly)} poly, {len(existing_justin)} justin", flush=True)

    # --- Prong 1: full timeline ---
    print("\n=== Prong 1: /Polymarket timeline ===", flush=True)
    get_authenticated()
    cursor = None
    page_num = 0
    new_poly = 0
    stop = False
    while not stop:
        page_num += 1
        try:
            posts, next_c, raw = page_timeline(cursor)
        except Exception as e:
            print(f"  page {page_num} FAIL: {e}", flush=True)
            break
        fresh = dedup(posts, poly_ids)
        for p in fresh:
            save_post(POLY_FILE, p)
            poly_ids.add(p["id"])
            new_poly += 1
        od = oldest_date(posts)
        print(f"  page {page_num}: {len(posts)} items, {len(fresh)} new, oldest={od.strftime('%b %d %H:%M') if od else '?'}", flush=True)
        if not next_c:
            print("  no next cursor -> timeline cap reached", flush=True)
            break
        if od and od <= TARGET_DATE:
            print("  reached target date -> stop", flush=True)
            break
        cursor = next_c
        time.sleep(0.3)

    # --- Prong 2: JUST IN search ---
    print("\n=== Prong 2: /search?q=from:Polymarket JUST IN ===", flush=True)
    get_authenticated()
    cursor = None
    page_num = 0
    new_justin = 0
    stop = False
    while not stop:
        page_num += 1
        try:
            posts, next_c, raw = page_search(cursor)
        except Exception as e:
            print(f"  page {page_num} FAIL: {e}", flush=True)
            break
        fresh = dedup(posts, justin_ids)
        for p in fresh:
            save_post(JUSTIN_FILE, p)
            justin_ids.add(p["id"])
            new_justin += 1
        od = oldest_date(posts)
        print(f"  page {page_num}: {len(posts)} items, {len(fresh)} new, oldest={od.strftime('%b %d %H:%M') if od else '?'}", flush=True)
        if not next_c:
            print("  no next cursor -> search cap reached", flush=True)
            break
        if od and od <= TARGET_DATE:
            print("  reached target date -> stop", flush=True)
            break
        cursor = next_c
        time.sleep(0.6)  # search is heavier, be polite

    # final summary
    final_poly = load_existing(POLY_FILE)
    final_justin = load_existing(JUSTIN_FILE)
    print(f"\n=== DONE ===")
    print(f"Polymarket: {len(final_poly)} total ({new_poly} new)")
    print(f"Justin:     {len(final_justin)} total ({new_justin} new)")

if __name__ == "__main__":
    main()
