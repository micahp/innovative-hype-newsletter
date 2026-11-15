# Context summary: 2026-11-15

Covers the session from 2026-11-12 to 2026-11-15. Innovative Hype only.

## Live site now

- `main` = `origin/main` = `67eeeff`. The live homepage is that `web/index.html`.
- Top News on the live site is the old ranking (score order, top 5). No lead
  step, no Show more button, no age labels.
- The working tree is on `main` with about 619 uncommitted entries that were
  there before this session. Do not reset or check out over them.

## Top News: gated #1 (built, made live, rolled back)

- Branch `ih/top-news-outlet-count` (local, not pushed): `scripts/top_news_lead.py`
  plus page changes (lead at #1, Show more for slots 6 to 10, age labels).
- Rule: the event with the most distinct outlets takes #1 only if it has at
  least 10 outlets and at least 1.5x the next event. Everything else moves
  down one place.
- Made live on 2026-11-13 at about 19:39 UTC, then rolled back the same day.
  Micah: the old ranking already had Huang at #1, it "wasn't bad before",
  tweak the algorithm instead of forcing a #1.
- Rollback: old `index.html` copied back to `/var/www/html`, step removed from
  `/root/.hermes/scripts/cron_news.py`, local `main` reset to `67eeeff` (the
  merge was never pushed).

## How the live Top News ranks (for the next tweak)

`scripts/feed_aggregator.py`, `score_article()`. Each article is scored alone:

- outlet tier: T1 3, T2 2, T3 1, T4 0.5
- freshness: 2.0 x 0.5^(age / 36h)
- pillars (keyword groups from EDITORIAL_MAP): 1.5 each, max 4.5
- `voice_terms.txt` subjects in the title: 2 each, max 6

Top 7 by score are flagged `top`, at most 2 per source and 2 per category,
no noise matches, dated only. The page shows the first 5.

- It does not count outlets, so it does not know how big a story is.
- Micah on 2026-11-13: `voice_terms.txt` is NOT his voice. It is a list of
  subjects (nvidia is a subtopic of AI). Do not call it "his voice".
- Micah: several slots for one big story can be right, because each article
  is a different angle. Do not apply "one slot per story" to all days. Judge
  it by reading real days.
- Correction: "23 of 44 days" was from the backtest of the outlet-count list,
  not the live list. There is no measured repeat rate for the live list.

## Daily save of the live Top News (running)

- `scripts/save_top_news.py`, called at the end of `scripts/deploy_site.sh`.
  It writes `top-news-history/top-news-<stamp>.json`: the 5 cards shown, all
  7 flagged, the next 15, each with score, pillars, voice terms and age.
- It runs from UNCOMMITTED changes in the `main` working tree. The commit is
  on branch `ih/save-live-top-news` (`b580b04`, not pushed). If the working
  tree loses these two files, the save stops.
- Files so far: `top-news-20261113T204208Z.json` (manual),
  `top-news-20261114T133001Z.json` (07:30 deploy).
- Use: after about a week, read the days where one story has more than one
  slot, angle by angle, with Micah.

## Past Top News cannot be rebuilt

- The desk inputs (`runs/*/input.json`) keep title, source, link and an
  excerpt, but no publish time, and only about half of the articles.
- Measured on 2026-11-13: a rebuild matched 3 of the 5 live cards. On 11 older
  points with both files, 38 of 77 real top items were in the desk input.
- The score math itself matches (median difference 0.03).

## Retweet angles (branch `ih/angles-retweets`, pushed)

Full record: `docs/RETWEET-ANGLES-2026-11-14.md` on that branch.

- The X archive is the @geoppls export. 601 retweets are of his own accounts
  (@geoppls, @micahppls, @innovativehype).
- Chosen: a quality filter. A model labels each retweet (view, news, promo,
  chatter, fragment). It keeps views and own-account retweets.
- On the same 418 retweet positions: the quality filter keeps 280, and the
  own-words test keeps 201. Micah rejected own words as the whitelist because
  it cuts good positions.
- Open for later: news retweets. 62 of the 66 positions that only the
  own-words test keeps came from news retweets.

## One-week trial (running since 2026-11-14)

- Folder `/root/ih-angles-trial`, a copy of the branch with 612 angles
  (378 + 234 `rt-` angles). It reads production `web/articles.json` only.
- Crontab: `50 * * * *` tick (skips when prod articles are unchanged) and
  `35 7 * * *` snapshot to `daily/<date>/{trial,live}/`. No end date. To stop,
  remove the two lines under "IH retweet-angles trial".
- Page: `trial/index.html` on the dev tunnel (quick tunnel on port 8850,
  serving the session scratchpad `topevent/web`; the URL changes if it restarts).
- Status 2026-11-15 06:00 local: 13 ticks, 8 done, 4 failed on the model's
  JSON (`narrative_desk.py` line 2063). Production has the same failure: its
  desk returned rc=1 in 5 of its last 14 runs. Not caused by the trial.
- The trial feed started empty. Compare it with live from 2026-11-17.

## Disk (urgent, not this project)

- 2026-11-15: 572 MB free, 100% used (3.8 GB free on 2026-11-14).
- New large files: `/root/legendarypicks/backend/data/picks.db.bak-premigrate-ufc-timer-20261115-052431`
  (3.4 GB, 05:24 today, an LP migration backup) and a docker container log
  of 981 MB. Not touched. Deleting needs Micah's go.
- This project: trial folder 301 MB, repo `.embed-cache` 619 MB.

## Branches

| Branch | State |
|---|---|
| `ih/top-news-outlet-count` | gated #1, rolled back, local only |
| `ih/save-live-top-news` | daily save commit, local only; live via uncommitted files |
| `ih/angles-retweets` | analysis, doc, trial files; pushed |
| `ih/homepage-fixes-2026-11-10` | merged earlier |

## Open items

1. Disk at 100% (LP backup).
2. Desk fails on bad model JSON in about 1 of 3 runs, in prod and trial.
3. Top News tweak: read a week of saved lists first.
4. Trial review from 2026-11-17, day by day.
5. News retweets (see the retweet doc).
6. Older: card 4 wrong pair, `_body` in the public `articles.json`, cluster 0
   split paused, quality test item 16.
