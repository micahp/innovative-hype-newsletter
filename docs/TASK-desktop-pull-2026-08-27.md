# TASK: desktop pull of @geoppls + @innovativehype tweets (2026-08-27)

Run this on Micah's local machine. The server's IP is rate-limited by X (429 on
syndication and burned on every nitter mirror); a residential IP with a logged-in
browser is the only working surface. Your job: collect every tweet we are missing
and push it to this repo so the server can ingest it.

## Scope lock

- Touch ONLY the two output files named below. Commit exactly one commit. Push to `origin main`.
- FORBIDDEN: edits outside this repo, /etc changes, systemd/cron install, new global packages,
  any X API call, any third-party scraper service. Browser only.
- Do not store credentials anywhere in the repo.

## What to collect

Two handles: `geoppls`, `innovativehype`.

Cutoffs (collect everything STRICTLY AFTER these, up to now). Derived from the corpus's
true newest rows by parsed date (the corpus file is not date-sorted; the last line is not
the newest row):

| handle         | corpus ends at              | what we are missing            |
|----------------|-----------------------------|--------------------------------|
| geoppls        | Aug 24, 2026 3:20 PM UTC (id 2091908436988436800) | ~3 days. NOTE: his post-Aug-24-2026 tweets are deleted at X; whatever the logged-in profile shows IS the truth. If you see nothing after the cutoff, that is the finding. |
| innovativehype | Aug 24, 2026 6:16 PM UTC (id 2091952898003390877) | ~3 days |

Include replies and retweets-as-displayed; do not filter. Scroll the profile until you
reach the cutoff date, at human pace, one handle at a time.

## How

1. Log into x.com in the browser (account: defi_kallen; credentials come from Micah's
   password manager, never from this repo).
2. Open `https://x.com/<handle>`, scroll past the cutoff, scrape from the DOM:
   tweet id (the big number in the status link / `data-tweet-id`), the visible date
   string, and the full text.
3. Treat tweet ids as STRINGS end to end. They exceed 2^53; a number-typed id is
   silently corrupted by JSON round-trips. `String(...)` or read them from URLs.

## Output (exact)

One JSON object per line, UTF-8, no blank lines:

```json
{"id": "2091952898003390877", "date": "Aug 24, 2026 · 6:16 PM UTC", "text": "full tweet text"}
```

- `date`: keep X's own display format, e.g. `Aug 24, 2026 · 6:16 PM UTC`. If your scraper
  only has ISO 8601, use it and say so in your report; the server normalizes on ingest.
- Rows need not be sorted. The server dedupes by `id` against its corpus; overlap is harmless,
  but do not emit rows at or before the cutoff.

Files:

```
corpus/desktop/2026-08-27/geoppls.jsonl
corpus/desktop/2026-08-27/innovativehype.jsonl
```

A handle with zero results still gets its file (empty file = "we looked, X has nothing").

## Commit + push

```
git add corpus/desktop/2026-08-27/geoppls.jsonl corpus/desktop/2026-08-27/innovativehype.jsonl
git commit -m "desktop pull: geoppls + innovativehype tweets thru 2026-08-27"
git push origin main
```

Done = push succeeds and both files exist on `origin/main`. Report: rows per handle,
oldest and newest date per handle, and anything that looked wrong.
