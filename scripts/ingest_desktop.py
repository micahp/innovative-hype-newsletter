#!/usr/bin/env python3
"""ingest_desktop.py — merge a desktop tweet drop into the account corpora.

WHY THIS EXISTS
---------------
X rate-limits by IP and this box is a datacenter address. On 2026-08-24 X Corp's
cease-and-desist killed every public nitter instance, so `poll_social.py`'s
three transports all went dead and the X lane has been frozen since 2026-08-27.

The working path is Micah's home PC on a residential IP: it pulls the accounts,
writes `corpus/desktop/<YYYY-MM-DD>/<account>.jsonl`, and pushes. That happened
on 2026-08-27 and it worked. What did NOT exist was anything on this side that
reads the drop: the merge that day was done by hand, so a new drop would sit in
the directory untouched. This is that missing half.

THE DROP FORMAT
---------------
One JSON object per line, ISO 8601 UTC:

    {"id": "2092038806132146257", "date": "2026-08-24T23:58:14.000Z", "text": "..."}

ISO on the wire is deliberate. It is unambiguous, keeps seconds, and sorts
chronologically as a plain string. The corpus stores nitter's render format
('Aug 24, 2026 · 11:58 PM UTC') because `poll_social.py` writes that and 1,569
existing rows use it, so this converts on the way IN. One format per file, and
the conversion happens at exactly one place: here.

DEDUPE IS BY ID, NEVER BY TEXT OR DATE
--------------------------------------
Tweet id is the publisher's own key and it is stable. Text is not unique (this
corpus contains 'wow' and 'motivation' as whole tweets) and the date loses
seconds in the corpus format, so two posts in the same minute would collide.
Matching on either would silently drop real rows.
"""
import argparse
import json
import os
import pathlib
import re
import sys
from datetime import datetime, timezone

HERE = pathlib.Path(__file__).resolve().parent.parent
CORPUS = HERE / "corpus"
DROPS = CORPUS / "desktop"

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


def read_jsonl(path):
    rows = []
    if not path.exists():
        return rows
    for line in path.read_text().splitlines():
        line = line.strip()
        if line:
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return rows


def merge_account(account, drop_path, apply):
    """-> (added, duplicate, unparseable, newest_after) for one account."""
    target = CORPUS / ("%s.jsonl" % account)
    existing = read_jsonl(target)
    have = {r.get("id") for r in existing}

    added, dup, bad = [], 0, 0
    for r in read_jsonl(drop_path):
        rid = r.get("id")
        if not rid:
            bad += 1
            continue
        if rid in have:
            dup += 1
            continue
        dt = parse_any(r.get("date"))
        if dt is None:
            # Never invent a timestamp. A row we cannot date is reported and
            # skipped, because a wrong date here becomes a wrong date forever.
            bad += 1
            continue
        have.add(rid)
        added.append({**r, "date": fmt_corpus(dt)})

    merged = existing + added
    # Chronological, oldest first, matching what poll_social.py now writes.
    merged.sort(key=lambda p: (parse_any(p.get("date")) is not None,
                               parse_any(p.get("date"))
                               or datetime.min.replace(tzinfo=timezone.utc)))
    newest = max((parse_any(p.get("date")) for p in merged
                  if parse_any(p.get("date"))), default=None)

    if apply and added:
        tmp = target.with_suffix(".jsonl.tmp")
        tmp.write_text("".join(json.dumps(p) + "\n" for p in merged))
        os.replace(tmp, target)   # atomic: a crash never truncates the corpus
    return len(added), dup, bad, newest


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--date", help="drop folder to ingest (default: all unmerged)")
    ap.add_argument("--apply", action="store_true",
                    help="write the corpus (default is a dry run)")
    a = ap.parse_args()

    if not DROPS.exists():
        print("No drop directory at %s" % DROPS)
        return 1
    folders = sorted(d for d in DROPS.iterdir() if d.is_dir())
    if a.date:
        folders = [d for d in folders if d.name == a.date]
        if not folders:
            print("No drop folder named %s" % a.date)
            return 1
    if not folders:
        print("No drops found in %s" % DROPS)
        return 0

    total = 0
    for folder in folders:
        drops = sorted(folder.glob("*.jsonl"))
        if not drops:
            continue
        print("%s" % folder.name)
        for path in drops:
            account = path.stem
            added, dup, bad, newest = merge_account(account, path, a.apply)
            total += added
            print("  %-18s +%-4d new  %4d already held  %2d unusable   newest now %s"
                  % (account, added, dup, bad,
                     newest.strftime("%Y-%m-%d %H:%M") if newest else "none"))

    if not a.apply:
        print("\nDRY RUN. Nothing written. Re-run with --apply to merge.")
    elif total:
        print("\nMerged %d new posts." % total)
    else:
        print("\nNothing new to merge.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
