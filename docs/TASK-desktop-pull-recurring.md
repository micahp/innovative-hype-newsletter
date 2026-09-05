# TASK: recurring desktop pull of @geoppls + @innovativehype (generalized)

This is the standing spec for the automated daily desktop pull, run unattended
by a Windows Scheduled Task on Micah's home PC. It generalizes
`TASK-desktop-pull-2026-08-27.md` (the first, hand-run, dated pull): same
rules, but the cutoff is computed fresh each run instead of hardcoded, and the
job is a no-op (no commit) when there is nothing new.

## Why this exists, and why it runs here and not on the server

The server's datacenter IP is burned with X (429 on syndication, every public
nitter mirror dead since X's 2026-08-24 cease-and-desist). A residential IP
with a logged-in browser is the only working surface for the two personal
handles (`geoppls`, `innovativehype`); brand accounts still come through
server-side syndication fine. See `SELF-HOST-NITTER-DESKTOP.md` for the
self-hosted-nitter alternative that was proposed and explicitly rejected
(Micah: an outward-facing service on the home PC is a last resort) — this
outbound git-based pull is the answer instead: nothing listens on this
machine, every drop is an auditable commit, and if the PC is off or asleep the
pipeline just goes quiet rather than silently reading a dead endpoint.

## Scope lock

- Touch ONLY `corpus/desktop/<today>/geoppls.jsonl` and
  `corpus/desktop/<today>/innovativehype.jsonl`, where `<today>` is today's
  date in `YYYY-MM-DD`. Commit exactly one commit if (and only if) at least one
  handle produced new rows. Push to `origin main`.
- FORBIDDEN: edits outside this repo, any X API call, any third-party scraper
  service, any destructive git operation (`push --force`, `reset --hard`,
  amending prior commits). Browser only, on `x.com/<handle>` — never
  `x.com/home`.
- Do not store credentials anywhere in the repo.
- `git pull --rebase origin main` before pushing; the server merges its own
  work (e.g. `scripts/ingest_desktop.py`) independently and this job must not
  clobber it.

## Step 1: compute this run's cutoff, per handle

The cutoff is NOT hardcoded. For each handle, read every existing row across
`corpus/<handle>.jsonl` and any `corpus/desktop/*/<handle>.jsonl`, and take the
row with the numerically largest `id` (tweet ids are Snowflake ids — larger id
strictly means newer; do not trust the `date` field or file order, corpus
files are not date-sorted). That id is the cutoff. Collect strictly AFTER it.

## Step 2: scrape

1. Open `https://x.com/<handle>` (profile tab, not Replies/Reposts/Media).
   Never navigate to `x.com/home`.
2. For each rendered tweet, extract via the DOM (not OCR, not the hover
   tooltip): the id from the timestamp `<time>` element's enclosing permalink
   (`/status/<id>`), the ISO datetime from `<time datetime="...">`, and the
   text from the tweet-text node.
3. **Exclude the pinned tweet.** The profile page injects it out of
   chronological order at the top, and its `data-testid="socialContext"`
   label reads "Pinned". A stray old pinned tweet will otherwise falsely
   trip cutoff-detection on the very first load — this bit the first
   recurring run (2026-09-05) before the exclusion was added.
4. **Exclude tweets not authored by the target handle** — pure reposts of
   other accounts' tweets, where the author link inside the tweet resolves to
   someone else. Quote-tweets and replies authored by the handle stay in.
5. Drop rows with empty text (image/video-only posts with no caption).
6. Scroll and repeat until the oldest tweet id visible on the page is at or
   below the cutoff.

## Step 3: output

One JSON object per line, UTF-8, no blank lines, sorted ascending by id:

```json
{"id": "2093092494149906617", "date": "2026-08-27T21:45:13.000Z", "text": "..."}
```

- `id` is REQUIRED on every row and MUST be a JSON string — ids exceed 2^53
  and a number-typed id is silently corrupted by a JSON round-trip.
- `date`: ISO 8601 UTC (preferred; the server ingest accepts X's display
  format too, but ISO is what the `<time datetime>` attribute already gives
  you, so there's no reason to reach for anything else).
- A handle with zero new rows still gets checked, but does NOT get an empty
  file written for a routine daily run (unlike the one-time historical gap
  fill on 2026-08-27) — an empty file every day forever is noise, not signal.
  If BOTH handles have zero new rows, skip the commit entirely.

## Step 4: self-check (must print 0 bad rows before committing anything)

```bash
python3 -c "
import json, sys
for h in ['geoppls', 'innovativehype']:
    p = f'corpus/desktop/<today>/{h}.jsonl'
    import os
    if not os.path.exists(p): continue
    rows = [json.loads(l) for l in open(p, encoding='utf-8') if l.strip()]
    bad = sum(1 for r in rows if not isinstance(r.get('id'), str) or not r['id'].isdigit() or not r.get('text'))
    print(h, len(rows), 'bad:', bad)
"
```

## Step 5: commit + push (only if at least one file has new rows)

```bash
git add corpus/desktop/<today>/geoppls.jsonl corpus/desktop/<today>/innovativehype.jsonl
git commit -m "desktop pull: geoppls + innovativehype tweets thru <today> (auto)"
git pull --rebase origin main
git push origin main
```

## Report

End with a one-paragraph summary: rows per handle, oldest/newest date, commit
hash (or "nothing new, no commit"), and anything that looked wrong (a repeat
of the pinned-tweet issue, an author-mismatch row, a truncated scrape, X UI
changes that broke a selector). This is unattended — the report is written to
a log file, not read live by a person — so state findings plainly rather than
asking a question nothing will answer.
