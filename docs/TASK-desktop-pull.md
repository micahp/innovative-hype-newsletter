# TASK: desktop pull of @geoppls + @innovativehype, with media

**Run this on Micah's home machine (residential IP).** This supersedes
`docs/TASK-desktop-pull-2026-08-27.md`, which was written for a single run and
had no media. Everything here is the standing procedure; re-read it each run
because the cutoffs move.

## Why a residential IP

X rate-limits by IP. The server is a datacenter address and is burned: 429 on
syndication, and every public nitter mirror died with the 2026-08-24
cease-and-desist. Measured on the server 2026-09-05: `@Kalshi` and `@Polymarket`
still come back through syndication with same-day posts, but `@geoppls` is
frozen 427 days back and `@innovativehype` returns an empty page. A logged-in
browser on a residential IP is the only surface that reaches those two.

**The server can still fetch MEDIA.** `pbs.twimg.com` and `video.twimg.com`
serve it fine (verified: HTTP 200 for a photo at `name=orig`, and for a 1080p
HLS playlist). So you do **not** download images or video. You capture the URLs
and the server pulls the bytes with `scripts/fetch_media.py`. Only the URL has
to cross.

## Scope lock

- Write ONLY the two files named under Output. One commit. Push to `origin main`.
- FORBIDDEN: edits elsewhere in the repo, `/etc` changes, systemd or cron
  install, new global packages, any X API call, any third-party scraper service,
  any tunnel or inbound service. Browser only.
- Never put credentials in the repo.
- `git pull --rebase` before you push.

## Cutoffs

Collect everything **strictly after** the newest post already held per handle.
Derive them yourself rather than trusting this file, because it goes stale:

```bash
python3 - <<'PY'
import json,sys; sys.path.insert(0,'scripts')
from ingest_desktop import parse_any
for a in ('geoppls','innovativehype'):
    rows=[json.loads(l) for l in open(f'corpus/{a}.jsonl') if l.strip()]
    d=[(parse_any(r['date']),r['id']) for r in rows]
    d=[x for x in d if x[0]]
    print(a, max(d))
PY
```

As of 2026-09-05 that is `geoppls` 2026-09-04 16:37 and `innovativehype`
2026-09-03 14:54. **The corpus is now chronologically sorted, but do not rely on
the last line being newest** — take the max by parsed date, as above.

## How

1. Log into x.com in the browser. (The 09-05 run used @geoppls, Micah's real
   account, rather than the defi_kallen throwaway. Either works; note which in
   your report.)
2. Open `https://x.com/<handle>` and scroll past the cutoff at human pace, one
   handle at a time.
3. **Profile page only.** Never `x.com/home`: an early attempt shipped
   home-feed rows into the geoppls file. If a row's author is not that profile,
   drop it.
4. **Exclude the pinned tweet.** `@geoppls` pins a Jun 2025 post which the
   profile injects at the top, out of order. It falsely trips cutoff detection
   on first load. Detect it by the "Pinned" social-context label.
5. **`id` is REQUIRED and must be a JSON STRING.** Ids exceed 2^53, so a
   number-typed id is silently corrupted by a JSON round-trip. The ingest
   rejects and counts non-string ids; an earlier run shipped 117 rows with no
   ids and every one was unusable.
6. Skip ad slots, "Who to follow", promoted cards, poll fragments.

### Media (new)

For every post, capture what is actually in the DOM:

- **Photos:** the `<img>` `src` on the post, which looks like
  `https://pbs.twimg.com/media/G4s2zvbXEAAReuB?format=jpg&name=small`. Take it
  verbatim, including `name=small`. The server rewrites it to `name=orig` and
  gets the full-size original; on the pinned-tweet image that is 173,798 bytes
  at 1179x1259 instead of 75,116 at 637x680.
- **Video and GIFs:** the poster/thumbnail `img src` goes in `url`. If you can
  reach the `video.twimg.com` playlist or mp4 URL, put it in `video_url`. If you
  cannot, omit `video_url` and still emit the row: the thumbnail alone is worth
  more than nothing, and a missing field is honest.
- **Only `pbs.twimg.com` and `video.twimg.com` are accepted.** Anything else is
  rejected by the ingest and counted by host. Do not substitute a proxy or a
  cached copy.
- **Do not download the media.** URLs only.

### Links

X renders links broken across lines, so the visible text is useless as a link.
The corpus holds exactly this, which is not clickable:

```
'whose ready? watch it here\n\n\nhttps://\nlegendarypicks.xyz/esports'
```

Read the anchor's `href` instead and put the real URLs in a `urls` array. Leave
`text` as the rendered text; do not repair it.

## Output (exact)

```
corpus/desktop/<YYYY-MM-DD>/geoppls.jsonl
corpus/desktop/<YYYY-MM-DD>/innovativehype.jsonl
```

One JSON object per line, UTF-8, no blank lines. `id`, `date`, `text` required;
`media` and `urls` optional, omitted entirely when empty.

```json
{"id": "2094917087898595500",
 "date": "2026-09-05T14:07:33.000Z",
 "text": "whose ready? watch it here",
 "media": [{"type": "photo", "url": "https://pbs.twimg.com/media/G4s2zvbXEAAReuB?format=jpg&name=small"}],
 "urls": ["https://legendarypicks.xyz/esports"]}
```

- `date`: **ISO 8601 UTC preferred.** X's display format
  (`Aug 24, 2026 · 6:16 PM UTC`) still parses. The server normalizes on ingest.
- `type`: `photo`, `video` or `gif`.
- **A media-only post still gets a row**, with `text` as `""`. There are already
  9 such rows in the corpus with no content at all; the whole point of `media`
  is that those stop being blanks.
- Rows need not be sorted. Overlap with what the server holds is harmless: it
  dedupes by id. Do not emit rows at or before the cutoff.
- A handle with zero new posts **still gets its file, empty**. An empty file
  means "we looked and X had nothing", which is a finding. No file means nobody
  ran, which is a different thing, and the two must not look alike.

Self-check before committing (must print `0 bad`):

```bash
python3 - <<'PY'
import json,glob
bad=0
for f in glob.glob('corpus/desktop/<YYYY-MM-DD>/*.jsonl'):
    for n,l in enumerate(open(f),1):
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

## Commit + push

```bash
git pull --rebase
git add corpus/desktop/<YYYY-MM-DD>/
git commit -m "desktop pull: geoppls + innovativehype thru <YYYY-MM-DD>"
git push origin main
```

## Report back

Rows per handle, oldest and newest date per handle, how many rows carry media,
how many carry urls, which login you used, and anything that looked wrong.

## What the server does next (not your job)

```bash
git pull
python3 scripts/ingest_desktop.py                 # dry run, prints every count
python3 scripts/ingest_desktop.py --apply         # merge
python3 scripts/fetch_media.py --apply            # pull the bytes from the CDN
```

## Known limit, not a failure

`@geoppls`' tweets after 2026-08-24 were deleted at X itself. If the profile
shows nothing after the cutoff, **that is the answer.** Commit the empty file
and say so. Their media is almost certainly gone with them.
