# TASK: recurring desktop pull of @geoppls + @innovativehype

**The standing spec.** Runs unattended on Micah's home PC (residential IP) via a
Windows Scheduled Task. This is the single authoritative version: it supersedes
and replaces both `TASK-desktop-pull-2026-08-27.md` (the first hand-run, dated
pull) and `TASK-desktop-pull-recurring.md`, which were written four minutes
apart on 2026-09-05 by two sessions that did not know about each other. Two
specs for one job is how a scraper ends up following the one without the media
section. Both are deleted; this file is the only one.

## Why it runs there and not on the server

The server's datacenter IP is burned with X: 429 on syndication, every public
nitter mirror dead since the 2026-08-24 cease-and-desist. Measured server-side
2026-09-05: `@Kalshi` and `@Polymarket` still return same-day posts through
syndication, but `@geoppls` is frozen 427 days back and `@innovativehype`
returns an empty page. A logged-in browser on a residential IP is the only
surface that reaches those two.

`SELF-HOST-NITTER-DESKTOP.md` proposed a self-hosted nitter behind a tunnel.
**It was rejected** — an outward-facing service on the home PC is a last resort.
This outbound git pull is the answer instead: nothing listens on that machine,
every drop is an auditable commit, and if the PC is off the pipeline goes quiet
rather than silently reading a dead endpoint.

**The server CAN still reach X's media CDN.** Verified 2026-09-05:
`pbs.twimg.com` returns 200 at `name=orig` and `video.twimg.com` serves a 1080p
HLS playlist, both while the tweet surface is blocked. So you never download
media. You capture URLs; `scripts/fetch_media.py` pulls the bytes server-side.

## Scope lock

- Write ONLY `corpus/desktop/<today>/geoppls.jsonl` and
  `corpus/desktop/<today>/innovativehype.jsonl`, `<today>` as `YYYY-MM-DD`.
- One commit, and only when at least one handle produced new rows.
- FORBIDDEN: edits elsewhere in the repo, any X API call, any third-party
  scraper service, any tunnel or inbound service, and any destructive git
  operation (`push --force`, `reset --hard`, amending prior commits).
- Browser only, on `x.com/<handle>`. Never `x.com/home`.
- Never store credentials in the repo.
- `git pull --rebase origin main` before pushing. The server commits its own
  work to this repo independently and this job must not clobber it.

## Step 1: compute the cutoff, per handle

**Not hardcoded.** For each handle, read every row across
`corpus/<handle>.jsonl` and every `corpus/desktop/*/<handle>.jsonl`, and take
the **numerically largest `id`**. Tweet ids are Snowflake ids: a larger id
strictly means newer. Do not trust the `date` field or file order for this.
Collect strictly after that id.

## Step 2: scrape

1. Log into x.com. (The 09-05 run used @geoppls, Micah's real account, rather
   than the defi_kallen throwaway. Either works; say which in your report.)
2. Open `https://x.com/<handle>`, profile tab, and scroll past the cutoff at
   human pace, one handle at a time.
3. **Exclude the pinned tweet.** @geoppls pins a Jun 2025 post that the profile
   injects at the top, out of order. It falsely trips cutoff detection on first
   load. Detect it by the "Pinned" social-context label.
4. **`id` is REQUIRED and must be a JSON STRING.** Ids exceed 2^53, so a
   number-typed id is silently corrupted by a JSON round-trip. The ingest
   rejects and counts non-string ids. An early run shipped 117 rows with no ids
   and every one was unusable.
5. If a row's author is not that profile, drop it. An early attempt shipped
   home-feed rows into the geoppls file.
6. Skip ad slots, "Who to follow", promoted cards, poll fragments.

### Media

- **Photos:** the post's `<img>` `src`, e.g.
  `https://pbs.twimg.com/media/G4s2zvbXEAAReuB?format=jpg&name=small`. Take it
  verbatim including `name=small`; the server rewrites to `name=orig`. On the
  pinned-tweet image that is 173,798 bytes at 1179x1259 rather than 75,116 at
  637x680.
- **Video and GIFs:** the poster/thumbnail `img src` goes in `url`. If you can
  reach the `video.twimg.com` playlist or mp4, put it in `video_url`; if not,
  omit the field and still emit the row. A thumbnail alone beats nothing and a
  missing field is honest.
- **Only `pbs.twimg.com` and `video.twimg.com`.** Anything else is rejected by
  the ingest and counted by host. Never substitute a proxy or cached copy.
- **Do not download media.** URLs only.

### Links

X renders links broken across lines, so the visible text is not a usable link.
The corpus literally holds
`'whose ready? watch it here\n\n\nhttps://\nlegendarypicks.xyz/esports'`.
Read the anchor's `href` and put real URLs in a `urls` array. Leave `text` as
the rendered text; do not repair it.

## Output

```
corpus/desktop/<YYYY-MM-DD>/geoppls.jsonl
corpus/desktop/<YYYY-MM-DD>/innovativehype.jsonl
```

One JSON object per line, UTF-8, no blank lines. `id`, `date`, `text` required;
`media` and `urls` optional and omitted entirely when empty.

```json
{"id": "2094917087898595500",
 "date": "2026-09-05T14:07:33.000Z",
 "text": "whose ready? watch it here",
 "media": [{"type": "photo", "url": "https://pbs.twimg.com/media/G4s2zvbXEAAReuB?format=jpg&name=small"}],
 "urls": ["https://legendarypicks.xyz/esports"]}
```

- `date`: **ISO 8601 UTC preferred.** X's display format
  (`Aug 24, 2026 · 6:16 PM UTC`) still parses; the server normalizes on ingest.
- `type`: `photo`, `video` or `gif`.
- **A media-only post still gets a row**, `text` as `""`. There are 9 such rows
  already in the corpus with no content at all. Killing those blanks is the
  entire point of the `media` field.
- Rows need not be sorted. Overlap is harmless; the server dedupes by id.

Self-check before committing (must print `0 bad`):

```bash
python3 - <<'PY'
import json,glob,sys
bad=0
for f in glob.glob(f'corpus/desktop/{sys.argv[1] if len(sys.argv)>1 else ""}/*.jsonl'):
    for n,l in enumerate(open(f,encoding='utf-8'),1):
        if not l.strip(): continue
        try: r=json.loads(l)
        except Exception: print(f,n,'not json'); bad+=1; continue
        if not isinstance(r.get('id'),str) or not r['id'].isdigit(): print(f,n,'bad id'); bad+=1
        if 'text' not in r: print(f,n,'no text'); bad+=1
        for m in r.get('media',[]):
            if not str(m.get('url','')).startswith(('https://pbs.twimg.com','https://video.twimg.com')):
                print(f,n,'bad media host'); bad+=1
print(bad,'bad')
PY
```

## Nothing new: no commit

If both handles produce zero new rows, **do not commit and do not create empty
files.** A daily empty commit is noise.

This is safe only because the server watches independently: `poll_social.py
--check-only` runs on cron at 13:00 daily, reads local corpus files with no
network, and exits 1 naming any handle whose newest post is older than 48h. So
"the PC stopped pulling" is caught server-side rather than inferred from an
absent commit. **If that alarm is ever removed, this rule has to change back to
always writing a file**, because otherwise a dead job and a quiet week look
identical.

## Report back

Rows per handle, oldest and newest date per handle, how many rows carry media,
how many carry urls, which login you used, and anything that looked wrong.

## What the server does next (not your job)

```bash
git pull
python3 scripts/ingest_desktop.py            # dry run, prints every count
python3 scripts/ingest_desktop.py --apply    # merge
python3 scripts/fetch_media.py --apply       # pull bytes from the CDN
```

## Known limit, not a failure

@geoppls' tweets after 2026-08-24 were deleted at X itself. If the profile shows
nothing after the cutoff, **that is the answer** — say so in the report. Their
media is almost certainly gone with them.

## Related: the same mechanism serves Legendary Picks

LP's league-news X lane (`legendarypicks-news-x.service`) died the same way and
has contributed no rows since 2026-08-20. It needs 17 sports handles rather than
these two. See `/root/legendarypicks/docs/TASK-desktop-pull-x-news.md`. Same
architecture, different repo and different handle list; do not mix the two
drops.
