#!/usr/bin/env python3
"""fetch_media.py — pull tweet media onto this box from X's CDN.

THE ASYMMETRY THIS EXPLOITS
---------------------------
X blocks this datacenter IP on the TWEET surface: syndication returns 429, every
public nitter mirror died with the 2026-08-24 cease-and-desist, and
@innovativehype's syndication page comes back empty. But its MEDIA is on a
different CDN, and that CDN does not care. Verified 2026-09-05 from this box:

    pbs.twimg.com/media/<id>?name=small   HTTP 200    75,116B    637x680
    pbs.twimg.com/media/<id>?name=orig    HTTP 200   173,798B   1179x1259
    video.twimg.com/.../pl/<x>.m3u8       HTTP 200   master playlist
    .../pl/avc1/1920x1080/<x>.m3u8        HTTP 200   1080p variant

So only the URL has to cross from the residential machine. The bytes come from
here. The scraper hands us `name=small` because that is what the profile DOM
carries; this upgrades to `name=orig` and keeps the original.

WHAT IT WILL NOT DO
-------------------
Fetches ONLY pbs.twimg.com and video.twimg.com, the two hosts ingest_desktop
validates against. These URLs were scraped off a web page on another machine and
this box runs live trading; it does not follow arbitrary links. A URL that is
not on those hosts should never have reached the corpus, so finding one here is
reported as a defect in the ingest, not quietly skipped.

Video: saves the master .m3u8 only, not the segments. A playlist is 1.3KB and
records exactly what was available; pulling every segment is a different
decision about disk and about copyright, and it is not made silently here.
"""
import argparse
import collections
import json
import pathlib
import re
import sys
import time
import urllib.error
import urllib.request

HERE = pathlib.Path(__file__).resolve().parent.parent
CORPUS = HERE / "corpus"
MEDIA = CORPUS / "media"
CDN_HOSTS = ("pbs.twimg.com", "video.twimg.com")
UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/128.0 Safari/537.36")
GAP_S = 0.7          # one host, one process, a polite pace
TIMEOUT_S = 30
MAX_BYTES = 40 * 1024 * 1024


def upgrade(url):
    """pbs.twimg.com serves sizes via ?name=. Ask for the original.

    Only /media/ honours it. Video thumbnails ignore the parameter entirely
    (measured: small, large and orig all returned the same 18,642 bytes), so
    this rewrites the parameter and lets the CDN decide rather than assuming.
    """
    if "pbs.twimg.com" not in url:
        return url
    if "name=" in url:
        return re.sub(r"name=[a-z0-9]+", "name=orig", url)
    return url + ("&" if "?" in url else "?") + "name=orig"


def ext_for(url, ctype):
    ct = (ctype or "").split(";")[0].strip()
    return {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp",
            "image/gif": ".gif", "video/mp4": ".mp4",
            "application/x-mpegURL": ".m3u8",
            "application/vnd.apple.mpegurl": ".m3u8"}.get(
                ct, pathlib.Path(url.split("?")[0]).suffix or ".bin")


def fetch(url):
    """-> (bytes, content_type). Raises on anything that is not a clean 200."""
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=TIMEOUT_S) as r:
        data = r.read(MAX_BYTES + 1)
        if len(data) > MAX_BYTES:
            raise RuntimeError("exceeds %d byte cap" % MAX_BYTES)
        return data, r.headers.get("Content-Type", "")


def rows_with_media(accounts):
    for acct in accounts:
        path = CORPUS / ("%s.jsonl" % acct)
        if not path.exists():
            print("  !! no corpus file for %s" % acct)
            continue
        for line in path.read_text().splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                print("  !! unparseable row in %s" % path.name)
                continue
            if r.get("media"):
                yield acct, r


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--accounts", default="geoppls,innovativehype")
    ap.add_argument("--apply", action="store_true",
                    help="actually download (default is a dry run)")
    ap.add_argument("--limit", type=int, default=0, help="stop after N files")
    a = ap.parse_args()

    accounts = [s.strip() for s in a.accounts.split(",") if s.strip()]
    stats = collections.Counter()
    todo = []

    for acct, r in rows_with_media(accounts):
        for i, m in enumerate(r.get("media") or []):
            for key, tag in (("url", "img"), ("video_url", "vid")):
                url = m.get(key)
                if not url:
                    continue
                host = url.split("/")[2] if url.startswith("https://") else "?"
                if host not in CDN_HOSTS:
                    # Should be impossible: ingest_desktop validates this. If it
                    # happens the ingest let something through, which is a defect
                    # worth shouting about rather than skipping past.
                    stats["BAD_HOST_%s" % host] += 1
                    print("  !! %s carries a non-CDN url (%s). ingest_desktop "
                          "should have rejected it." % (r.get("id"), host))
                    continue
                todo.append((acct, r["id"], i, tag, upgrade(url) if tag == "img" else url))

    if not todo:
        # Zero is a finding. Distinguish "no media in the corpus yet" from a run
        # that failed to look, because they print identically otherwise.
        print("0 media references in the corpus for: %s" % ", ".join(accounts))
        print("That is expected until a drop carrying the new `media` field is "
              "ingested. It is NOT evidence that fetching works.")
        return 0

    print("%d media file(s) referenced across %s" % (len(todo), ", ".join(accounts)))
    got = skip = fail = 0
    for acct, tid, idx, tag, url in todo:
        if a.limit and (got + skip + fail) >= a.limit:
            break
        outdir = MEDIA / tid
        existing = list(outdir.glob("%s%d.*" % (tag, idx))) if outdir.exists() else []
        if existing:
            skip += 1
            continue
        if not a.apply:
            print("  would GET %s" % url[:110])
            got += 1
            continue
        try:
            time.sleep(GAP_S)
            data, ctype = fetch(url)
            outdir.mkdir(parents=True, exist_ok=True)
            dest = outdir / ("%s%d%s" % (tag, idx, ext_for(url, ctype)))
            dest.write_bytes(data)
            got += 1
            print("  %s  %7dB  %s" % (dest.relative_to(CORPUS), len(data), ctype.split(";")[0]))
        except (urllib.error.HTTPError, urllib.error.URLError, RuntimeError) as e:
            fail += 1
            code = getattr(e, "code", "")
            print("  FAIL %s %s  %s" % (tid, code, str(e)[:90]))
            stats["fail_%s" % (code or type(e).__name__)] += 1

    print("\nfetched %d, already held %d, failed %d" % (got, skip, fail))
    if stats:
        print("failures: " + ", ".join("%s=%d" % kv for kv in sorted(stats.items())))
    if not a.apply:
        print("DRY RUN. Nothing downloaded. Re-run with --apply.")
    # A failure is not a warning. Media the corpus claims exists and we could not
    # retrieve is a gap, and the caller should know without reading the log.
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
