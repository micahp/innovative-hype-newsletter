#!/usr/bin/env python3
"""poll_social.py — incremental poll of social accounts into corpus/*.jsonl.

HISTORY / WHY THIS WAS REWRITTEN (2026-08-27):
The original polled ONLY nitter.tiekoetter.com, fetching /<account> HTML
twice per run (once in _auth(), again in poll_account()) behind an Anubis
PoW gate. When tiekoetter began answering 429 Too Many Requests on the
account surfaces (while still serving its own front page 200), every run
died at _auth() printing a single terse JSON error into a cron log nobody
read — while corpus/innovativehype.jsonl and corpus/geoppls.jsonl froze at
2026-08-24 for 2+ days. The failure was invisible because nothing in the
run ever reported HOW STALE the data had become.

WHAT CHANGED:
1. Multi-transport fallback: nitter RSS endpoints are tried ONE time each,
   in order, no internal retries — the 2h cron cadence provides the retry
   spacing. Hammering a rate limit is how this box got IP-blocked by
   Liquipedia on 2026-08-10; that mistake is not repeated here. Current
   transports, most-preferred first:
     - nitter.tiekoetter.com/<acct>/rss   (historical home; presently 429)
     - nitter.net/<acct>/rss              (works per corpus/README.md;
                                          timeline caps around 20 posts,
                                          which is enough for incrementals)
     - xcancel.com/<acct>/rss             (public mirror, not previously
                                          catalogued in corpus/README.md)
     - twiiit.com/<acct>/rss              (rotator over live instances)
2. LOUD STALENESS REPORTING (the required part): EVERY run prints, per
   account, the age in hours of the newest post on disk — BEFORE polling
   (pre-flight truth) and AFTER (result). Any account whose newest post is
   older than STALE_EXIT_H (default 48) — or whose file is missing/empty/
   unparsable, or whose fetch failed this run — exits NON-ZERO. Silence is
   not healthy; healthy runs say their counts out loud.
3. Row schema is unchanged: {"id", "date", "text"} per account file;
   dedupe stays by tweet id; justin.jsonl is still rebuilt as the JUST IN
   union across accounts. Dates emitted match the historical nitter render
   ("Aug 24, 2026 · 6:16 PM UTC") so consumers and lexicographic sorts see
   one uniform format across old and new rows.

Captcha paths: deliberately NONE. No service solves challenges here; an
endpoint that demands one is skipped, not beaten.

Run summary shape:
{"transport": "...", "accounts": {"<name>": {"new": N, "page": M,
  "newest_post_age_h": X.X, "error": null|str}}, "stale_accounts": [...],
  "ts": "..."}  →  printed on stdout ALWAYS, plus human-readable lines.
"""

import email.utils
import gzip
import json
import os
import re
import ssl
import sys
import urllib.request
from datetime import datetime, timezone

UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
CORPUS = os.environ.get("LP_CORPUS",
                        os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                     "..", "corpus"))
os.makedirs(CORPUS, exist_ok=True)

ACCOUNTS = ["Polymarket", "Kalshi", "geoppls", "innovativehype"]
STALE_EXIT_H = float(os.environ.get("IH_SOCIAL_STALE_H", "48"))
# One attempt per host per run. Never loop, never retry inside a run: the
# cron fires every 120 minutes and THAT is the retry policy.
TRANSPORTS = [
    "https://nitter.tiekoetter.com",
    "https://nitter.net",
    "https://xcancel.com",
    "https://twiiit.com",
]
TIMEOUT_S = 30

_ctx = ssl.create_default_context()
_ctx.check_hostname = False
_ctx.verify_mode = ssl.CERT_NONE


# ------------------------------------------------------------------ fetch

def _get(url):
    req = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "Accept": "application/rss+xml, application/xml, text/xml, */*",
        "Accept-Encoding": "gzip",
    })
    with urllib.request.urlopen(req, timeout=TIMEOUT_S, context=_ctx) as r:
        raw = r.read()
        if r.headers.get("Content-Encoding") == "gzip":
            raw = gzip.decompress(raw)
        return raw


# ------------------------------------------------------------------ parse

_DATE_RE = re.compile(
    r"^([A-Z][a-z]{2}) (\d{1,2}), (\d{4}) · (\d{1,2}):(\d{2}) (AM|PM) UTC$")


def parse_date(s):
    """Parse any date form found in the corpus into aware UTC datetime.

    Handles the historical nitter render ('Aug 24, 2026 · 6:16 PM UTC'),
    RFC 822 (RSS pubDate), and ISO 8601. Returns None when unparsable so
    the caller can count it loudly instead of guessing."""
    if not s:
        return None
    s = str(s).strip()
    m = _DATE_RE.match(s)
    if m:
        mon, d, y, hh, mm, ap = m.groups()
        months = {name: i for i, name in enumerate(
            ("Jan", "Feb", "Mar", "Apr", "May", "Jun",
             "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"), 1)}
        h = int(hh) % 12 + (12 if ap == "PM" else 0)
        try:
            return datetime(int(y), months[mon], int(d), h, int(mm),
                            tzinfo=timezone.utc)
        except (ValueError, KeyError):
            return None
    try:
        dt = email.utils.parsedate_to_datetime(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except (TypeError, ValueError):
        pass
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return None


def fmt_date(dt):
    """Emit dates in the exact historical corpus format."""
    return dt.strftime("%b %d, %Y · %-I:%M %p UTC")


_TAG_RE = re.compile(r"<[^>]+>")


def _clean(html):
    txt = re.sub(r"<br\s*/?>", "\n", html or "")
    txt = _TAG_RE.sub("", txt)
    txt = (txt.replace("&amp;", "&").replace("&lt;", "<")
              .replace("&gt;", ">").replace("&quot;", '"')
              .replace("&#39;", "'").replace("&apos;", "'"))
    txt = re.sub(r"[ \t]+", " ", txt)
    return "\n".join(part.strip() for part in txt.split("\n")
                     if part.strip())


_ITEM_RE = re.compile(r"<item>(.*?)</item>", re.S)


def parse_rss(xml_bytes):
    """Extract {id, date(datetime), text} from a nitter-style RSS feed."""
    xml = xml_bytes.decode("utf-8", "replace")
    posts = []
    for item in _ITEM_RE.findall(xml):
        m_guid = re.search(r"<guid>(.*?)</guid>", item, re.S)
        m_id = None
        if m_guid:
            m_id = re.search(r"/status/(\d+)", m_guid.group(1))
        if not m_id:
            m_id = re.search(r"/status/(\d+)", item)
        if not m_id:
            continue
        m_date = re.search(r"<pubDate>(.*?)</pubDate>", item, re.S)
        dt = parse_date(m_date.group(1)) if m_date else None
        m_desc = re.search(r"<description>(.*?)</description>", item, re.S)
        m_title = re.search(r"<title>(.*?)</title>", item, re.S)
        body = ""
        # Prefer the description (full text) over the title (truncated).
        raw_desc = m_desc.group(1) if m_desc else ""
        if "&lt;" in raw_desc or "<" in raw_desc:
            body = _clean(raw_desc)
        elif m_title:
            body = _clean(m_title.group(1))
        if not body:
            body = _clean(m_title.group(1)) if m_title else ""
        if not body:
            continue
        posts.append({"id": m_id.group(1),
                      "date": fmt_date(dt) if dt else "",
                      "_dt": dt,
                      "text": body})
    return posts


# ------------------------------------------------------------------ store

def corpus_path(screen):
    return os.path.join(CORPUS, f"{screen.lower()}.jsonl")


def load_rows(path):
    rows = []
    if not os.path.exists(path):
        return rows
    with open(path) as f:
        for ln, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as e:
                # Fail loudly on corruption: silently skipping rows is how
                # this corpus's quality guarantees rot away unnoticed.
                raise RuntimeError(f"{path} line {ln} corrupt: {e}") from e
    return rows


def append_rows(path, posts):
    if not posts:
        return 0
    with open(path, "a") as f:
        for p in posts:
            f.write(json.dumps(p, sort_keys=True) + "\n")
    return len(posts)


def newest_age_h(rows, now=None):
    """Age in hours of the newest post in rows; None when unknowable."""
    now = now or datetime.now(timezone.utc)
    best = None
    for r in rows:
        dt = parse_date(r.get("date", ""))
        if dt and (best is None or dt > best):
            best = dt
    if best is None:
        return None
    return (now - best).total_seconds() / 3600.0


# ------------------------------------------------------------------ poll

def pick_transport():
    """Try each transport host ONCE with a cheap probe on the first account.
    Returns (base_url, None) or (None, reason)."""
    probe_acct = ACCOUNTS[0]
    reasons = []
    for base in TRANSPORTS:
        url = f"{base}/{probe_acct}/rss"
        try:
            raw = _get(url)
            posts = parse_rss(raw)
            if posts:
                return base, None
            reasons.append(f"{base}: 200 but 0 items parsed")
        except Exception as e:
            reasons.append(f"{base}: {getattr(e, 'code', '')} {repr(e)[:80]}")
    return None, "; ".join(reasons)


def poll_account(base, screen):
    """Fetch the latest RSS page for one account, append only new rows.
    Returns dict(new=, page=, error=, rows_after=)."""
    path = corpus_path(screen)
    existing = {r.get("id") for r in load_rows(path)}
    try:
        posts = parse_rss(_get(f"{base}/{screen}/rss"))
    except Exception as e:
        return {"new": 0, "page": 0,
                "error": f"{getattr(e, 'code', '')} {repr(e)[:100]}"}
    fresh = [p for p in posts if p["id"] not in existing]
    fresh.sort(key=lambda p: (p["_dt"] or datetime.min.replace(
        tzinfo=timezone.utc)).timestamp())
    for p in fresh:
        p.pop("_dt", None)
    append_rows(path, fresh)
    return {"new": len(fresh), "page": len(posts), "error": None}


# ------------------------------------------------------------------ main

def main():
    ts = datetime.now(timezone.utc).isoformat()
    now = datetime.now(timezone.utc)

    # ---- PRE-FLIGHT: say the staleness truth BEFORE touching the network.
    preflight = {}
    for screen in ACCOUNTS:
        path = corpus_path(screen)
        try:
            rows = load_rows(path)
        except RuntimeError as e:
            preflight[screen] = {"age_h": None, "rows": 0, "error": str(e)[:90]}
            continue
        preflight[screen] = {"age_h": newest_age_h(rows, now),
                             "rows": len(rows)}
    print("== social corpus freshness (pre-flight) ==")
    for screen, pf in preflight.items():
        age = pf["age_h"]
        shown = f"{age:.1f}h" if age is not None else "UNKNOWN"
        warn = " << STALE" if (age is None or age > STALE_EXIT_H) else ""
        print(f"  {screen:<16} rows={pf['rows']:<5} newest={shown}{warn}")

    # ---- POLL: one transport chosen per run, one request per account.
    base, why_not = pick_transport()
    results, stale = {}, []
    if base is None:
        print(f"!! no reachable RSS transport this run: {why_not}")
        for screen in ACCOUNTS:
            results[screen.lower()] = {
                "new": 0, "page": 0, "error": "no_transport: " + (why_not or "")[:120],
                "newest_post_age_h": preflight[screen]["age_h"]}
            stale.append(screen)
    else:
        for i, screen in enumerate(ACCOUNTS):
            res = poll_account(base, screen)
            rows_after = load_rows(corpus_path(screen))
            age = newest_age_h(rows_after, now)
            res["newest_post_age_h"] = age
            results[screen.lower()] = res
            if res["error"] or age is None or age > STALE_EXIT_H:
                stale.append(screen)
            if i < len(ACCOUNTS) - 1:
                import time as _t
                _t.sleep(0.5)

    # ---- POST-FLIGHT report: the counts and the ages, every run.
    print("== poll result ==")
    if base:
        print(f"  transport: {base}")
    for screen, res in results.items():
        age = res.get("newest_post_age_h")
        shown = f"{age:.1f}h" if age is not None else "UNKNOWN"
        flag = ""
        if res.get("error"):
            flag = f" ERROR {res['error']}"
        elif age is None or age > STALE_EXIT_H:
            flag = f" << STALE (> {STALE_EXIT_H:g}h)"
        print(f"  {screen:<16} new={res['new']:<4} page={res['page']:<3} "
              f"age={shown}{flag}")

    # ---- JUST IN union rebuild (unchanged behaviour, all account files).
    seen_ids = set()
    justin_posts = []
    for screen in ACCOUNTS:
        fp = corpus_path(screen)
        if not os.path.exists(fp):
            continue
        for line in open(fp):
            line = line.strip()
            if not line:
                continue
            p = json.loads(line)
            if p.get("text", "").upper().startswith("JUST IN:") \
                    and p["id"] not in seen_ids:
                seen_ids.add(p["id"])
                justin_posts.append({**p, "account": screen})
    with open(os.path.join(CORPUS, "justin.jsonl"), "w") as f:
        for p in sorted(justin_posts, key=lambda x: x.get("date", "")):
            f.write(json.dumps(p) + "\n")

    summary = {
        "transport": base,
        "accounts": results,
        "stale_accounts": [s.lower() for s in stale],
        "justin_total": len(justin_posts),
        "ts": ts,
    }
    print(json.dumps(summary))

    if stale:
        print(f"EXIT 1: {len(stale)} account(s) stale or unfetched: "
              f"{', '.join(stale)}")
        return 1
    print("EXIT 0: all accounts fresh")
    return 0


if __name__ == "__main__":
    sys.exit(main())
