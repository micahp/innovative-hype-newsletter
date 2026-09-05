#!/usr/bin/env python3
"""ingest_desktop.py — merge a desktop tweet drop into the account corpora.

WHY THIS EXISTS
---------------
X rate-limits by IP and this box is a datacenter address. On 2026-08-24 X Corp's
cease-and-desist killed every public nitter instance, so `poll_social.py`'s
transports went dead and the X lane froze on 2026-08-27.

The working path is Micah's home PC on a residential IP: it pulls the accounts,
writes `corpus/desktop/<YYYY-MM-DD>/<account>.jsonl`, and pushes. What did NOT
exist was anything on this side that reads the drop, so the 08-27 merge was done
by hand. This is that missing half.

THE DROP FORMAT
---------------
One JSON object per line. `id`, `date`, `text` are required; `media` and `urls`
are optional and new as of 2026-09-05.

    {"id": "2094917087898595500",
     "date": "2026-09-05T14:07:33.000Z",
     "text": "whose ready? watch it here",
     "media": [{"type": "photo",
                "url": "https://pbs.twimg.com/media/G4s2zvbXEAAReuB?format=jpg&name=small"}],
     "urls": ["https://legendarypicks.xyz/esports"]}

ISO on the wire is deliberate: unambiguous, keeps seconds, sorts as a string.
The corpus stores nitter's render format because `poll_social.py` writes that,
so conversion happens on the way IN, at exactly one place, here.

WHY MEDIA IS A URL AND NOT BYTES
--------------------------------
Verified 2026-09-05: pbs.twimg.com and video.twimg.com serve THIS datacenter IP
without auth (HTTP 200 for a photo at name=orig, and for a 1080p HLS playlist)
while the tweet surface itself is blocked. So only the URL has to cross from the
residential machine; the bytes are fetched here by `fetch_media.py`. Hosts other
than those two are rejected and counted: this box runs live trading and does not
blindly fetch arbitrary links scraped from a web page on another machine.

DEDUPE IS BY ID, NEVER BY TEXT OR DATE
--------------------------------------
Tweet id is the publisher's own key and is stable. Text is not unique (this
corpus holds "wow" and "motivation" as whole tweets) and the corpus date format
loses seconds, so @innovativehype's two identical posts 46 seconds apart would
collide. Matching on either would silently eat real rows.

FAILING LOUDLY
--------------
Per .claude/skills/fail-loudly: every count prints every run, including zeros
and dead categories, and nothing is discarded without being counted. A drop that
merges 0 rows must not look like a drop that was never read.
"""
import argparse
import collections
import json
import os
import pathlib
import re
import sys
from datetime import datetime, timezone

HERE = pathlib.Path(__file__).resolve().parent.parent
CORPUS = HERE / "corpus"
DROPS = CORPUS / "desktop"

# The only hosts fetch_media.py will ever be pointed at. Verified reachable from
# this IP on 2026-09-05 while the tweet surface was not.
CDN_HOSTS = ("pbs.twimg.com", "video.twimg.com")

_NITTER_RE = re.compile(
    r"([A-Z][a-z]{2}) (\d{1,2}), (\d{4}) · (\d{1,2}):(\d{2}) ([AP]M) UTC")
_MONTHS = "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split()


def parse_any(s):
    """-> aware datetime, from either the ISO drop format or the corpus format."""
    s = str(s or "").strip()
    if not s:
        return None
    m = _NITTER_RE.match(s)
    if m:
        hour = int(m.group(4)) % 12 + (12 if m.group(6) == "PM" else 0)
        return datetime(int(m.group(3)), _MONTHS.index(m.group(1)) + 1,
                        int(m.group(2)), hour, int(m.group(5)), tzinfo=timezone.utc)
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return None
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None \
        else dt.astimezone(timezone.utc)


def fmt_corpus(dt):
    """The exact format poll_social.py writes, so one file never mixes two."""
    return "%s %d, %d · %d:%02d %s UTC" % (
        _MONTHS[dt.month - 1], dt.day, dt.year,
        dt.hour % 12 or 12, dt.minute, "AM" if dt.hour < 12 else "PM")


def clean_media(raw, rej):
    """-> validated media list. Every rejection is counted into `rej`.

    This is untrusted input: another machine scraped it off a web page. Only
    x.com's own CDN is kept, and a rejected item is a COUNT, never a silent drop
    -- a scraper that starts emitting the wrong host would otherwise look
    identical to a tweet with no media.
    """
    out = []
    if raw is None:
        return out
    if not isinstance(raw, list):
        rej["media_not_a_list"] += 1
        return out
    for m in raw:
        if not isinstance(m, dict):
            rej["media_item_not_object"] += 1
            continue
        url = str(m.get("url") or "").strip()
        if not url.startswith("https://"):
            rej["media_url_not_https"] += 1
            continue
        try:
            host = url.split("/")[2].split("?")[0]
        except IndexError:
            rej["media_url_unparseable"] += 1
            continue
        if host not in CDN_HOSTS:
            rej["media_host_%s" % host] += 1
            continue
        item = {"type": str(m.get("type") or "photo"), "url": url}
        vid = str(m.get("video_url") or "").strip()
        if vid:
            if vid.startswith("https://") and vid.split("/")[2] in CDN_HOSTS:
                item["video_url"] = vid
            else:
                rej["video_url_rejected"] += 1
        out.append(item)
    return out


def clean_urls(raw, rej):
    """-> outbound links, deduped. Recorded only; this script never fetches them.

    X renders a link broken across lines ('https://\\nlegendarypicks.xyz/esports'),
    so scraped TEXT is useless as a link. The scraper reads the anchor href.
    """
    out, seen = [], set()
    if raw is None:
        return out
    if not isinstance(raw, list):
        rej["urls_not_a_list"] += 1
        return out
    for u in raw:
        u = str(u or "").strip()
        if not u.startswith(("http://", "https://")):
            rej["url_not_http"] += 1
            continue
        if u in seen:
            continue
        seen.add(u)
        out.append(u)
    return out


def read_jsonl(path, rej=None):
    """-> list of rows. A line that will not parse is COUNTED, never swallowed.

    The previous version did `except json.JSONDecodeError: pass`, which is the
    exact shape .claude/skills/fail-loudly exists to prevent: a truncated drop
    file would ingest its readable prefix and report success.
    """
    rows = []
    if not path.exists():
        if rej is not None:
            rej["file_missing"] += 1
        return rows
    for n, line in enumerate(path.read_text().splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError as e:
            if rej is not None:
                rej["unparseable_line"] += 1
            print("    !! %s line %d is not valid JSON: %s" % (path.name, n, e))
    return rows


def merge_account(account, drop_path, apply):
    """-> a stats dict for one account. Nothing is dropped without a count."""
    rej = collections.Counter()
    target = CORPUS / ("%s.jsonl" % account)
    existing = read_jsonl(target, rej)
    have = {r.get("id") for r in existing}

    added, dup = [], 0
    n_media, n_urls, rows_with_media = 0, 0, 0
    for r in read_jsonl(drop_path, rej):
        rid = r.get("id")
        if not rid:
            rej["no_id"] += 1
            continue
        if not isinstance(rid, str):
            # Tweet ids exceed 2^53. A number-typed id is already corrupted by
            # the time we see it, so it is rejected rather than coerced.
            rej["id_not_a_string"] += 1
            continue
        if rid in have:
            dup += 1
            continue
        dt = parse_any(r.get("date"))
        if dt is None:
            rej["undateable"] += 1
            continue
        row = {"id": rid, "date": fmt_corpus(dt), "text": r.get("text", "")}
        media = clean_media(r.get("media"), rej)
        urls = clean_urls(r.get("urls"), rej)
        if media:
            row["media"] = media
            n_media += len(media)
            rows_with_media += 1
        if urls:
            row["urls"] = urls
            n_urls += len(urls)
        have.add(rid)
        added.append(row)

    merged = existing + added
    merged.sort(key=lambda p: (parse_any(p.get("date")) is not None,
                               parse_any(p.get("date"))
                               or datetime.min.replace(tzinfo=timezone.utc)))
    dated = [parse_any(p.get("date")) for p in merged]
    newest = max((d for d in dated if d), default=None)

    if apply and added:
        tmp = target.with_suffix(".jsonl.tmp")
        tmp.write_text("".join(json.dumps(p) + "\n" for p in merged))
        os.replace(tmp, target)   # atomic: a crash never truncates the corpus

    return {"added": len(added), "dup": dup, "rej": rej, "newest": newest,
            "media": n_media, "rows_with_media": rows_with_media,
            "urls": n_urls, "total": len(merged)}


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--date", help="drop folder to ingest (default: all)")
    ap.add_argument("--apply", action="store_true",
                    help="write the corpus (default is a dry run)")
    a = ap.parse_args()

    if not DROPS.exists():
        print("FAIL: no drop directory at %s" % DROPS)
        return 1
    folders = sorted(d for d in DROPS.iterdir() if d.is_dir())
    if a.date:
        folders = [d for d in folders if d.name == a.date]
        if not folders:
            print("FAIL: no drop folder named %s" % a.date)
            return 1
    if not folders:
        print("FAIL: no drops found in %s" % DROPS)
        return 1

    total_added, total_rej = 0, collections.Counter()
    for folder in folders:
        drops = sorted(folder.glob("*.jsonl"))
        print("%s  (%d file%s)" % (folder.name, len(drops), "" if len(drops) == 1 else "s"))
        if not drops:
            print("  !! folder is empty. A pull that found nothing should still "
                  "write an empty FILE per handle, so 'we looked' is recorded.")
            continue
        for path in drops:
            s = merge_account(path.stem, path, a.apply)
            total_added += s["added"]
            total_rej.update(s["rej"])
            # Every count, every run, including the zeros. A drop with no media
            # must read differently from a drop we never checked for media.
            print("  %-16s +%-4d new  %4d held  |  media %d in %d rows  |  urls %d  "
                  "|  newest %s  |  corpus %d"
                  % (path.stem, s["added"], s["dup"], s["media"],
                     s["rows_with_media"], s["urls"],
                     s["newest"].strftime("%Y-%m-%d %H:%M") if s["newest"] else "NONE",
                     s["total"]))
            if s["rej"]:
                print("     rejected: " + ", ".join("%s=%d" % kv
                                                    for kv in sorted(s["rej"].items())))
            else:
                print("     rejected: none")

    if total_rej:
        print("\nREJECTED ACROSS ALL FILES: " +
              ", ".join("%s=%d" % kv for kv in sorted(total_rej.items())))
        print("Every rejected row is a post we know exists and did not store.")

    if not a.apply:
        print("\nDRY RUN. Nothing written. Re-run with --apply to merge.")
        return 0
    print("\nMerged %d new post%s." % (total_added, "" if total_added == 1 else "s"))
    # Zero is a finding, not a success. An --apply that merged nothing is either
    # "already up to date" or "the drop was empty/broken", and the counts above
    # are what distinguish them.
    return 0


if __name__ == "__main__":
    sys.exit(main())
