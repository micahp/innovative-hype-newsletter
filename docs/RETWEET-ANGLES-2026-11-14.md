# Retweet angles: analysis and one-week trial (2026-11-14)

Branch `ih/angles-retweets`. `angles.yaml` on `main` is not changed.

## Question

Does it improve the angle list if the extractor also reads Micah's retweets?
Until now, `scripts/extract_angles.py` read original posts only.

## Source data

- `corpus/x_archive_all_tweets.json` is the official X export of **@geoppls**
  (from `account.js` in the export zip): 33,143 tweets, 8,036 retweets.
- The retweets come from 3,582 accounts. 601 are retweets of Micah's own
  accounts: @geoppls 394, @micahppls 130, @innovativehype 77. These are his
  own words.
- 6,919 retweets have 60 or more characters after the `RT @handle:` prefix.
  The export cuts most retweets at 140 characters.

## Steps and results

1. **No filter.** Extract from retweets only (3,728 after the same year
   weighting the extractor uses), then `consolidate_angles.py`:
   617 raw positions, 418 after merge, 35 dropped as "no news can trigger".
   Against the 378 current angles (consolidate same-position cut, cosine
   0.66): 78 already in the list, **340 new**.
   Many are other people's words stated as his position, for example
   "Trading is trading on emotions" from a trading-course ad.

2. **Own-words test, embedding only** (`support.py`). Keep a position if his own
   posts are near it. Rejected: it measures topic, not agreement. Current
   angles and retweet angles had almost the same scores (median 0.49 vs 0.47).
   It kept "giveaways build NFT community" because he posts about community.

3. **Own-words test, model** (`stance.py`). A model reads each position and the
   3 nearest own posts: agree 201, disagree 39, topic only 178. It drops good
   positions he never wrote about, for example "ads in AI answers are not
   acceptable". Micah: "i knew my words as the whitelist would cut good stuff".

4. **Quality filter** (`classify.py`), the chosen option. A model labels every
   retweet: view 2,063, news 1,610, promo 1,658, chatter 1,524, fragment 64.
   Keep = view, plus every retweet of his own accounts. 2,399 of 6,919 kept.
   No comparison with his own posts.

## Comparison on the same 418 positions

Each position is traced to the retweets its evidence quotes come from (409 of
418 traced). The quality filter keeps a position if any source retweet is kept.

| | Quality filter | Own-words test (model) |
|---|---|---|
| Positions kept | 280 (9 not traced) | 201 |
| New angles kept | 234 | 150 |
| Trading-course ad | dropped | dropped |
| NFT giveaway | dropped | dropped |
| Ads in AI answers | kept | dropped |
| US drone industry | kept | dropped |

Both keep 133. Only the quality filter keeps 147. Only the own-words test
keeps 66. Both drop 63.

## Known gap: news retweets (open, for later)

Of the 66 positions only the own-words test keeps, the source retweets are
news 62, chatter 17, promo 8 (a position can have more than one source).
A news retweet often shows agreement, for example a Meta age-check lobbying
report became "tech companies push surveillance through lobbying". The filter
drops all news. Keeping news adds these, and also adds noise, for example
"Google's quantum chip proves multiple universes".

Next step when this is picked up: label news retweets as "news with a stance"
or "plain news", or keep news only when the position also passes the
own-words test.

## Other notes

- `qf.*` files: a full extraction again from only the filtered retweets gave
  170 positions, but 1 of its 12 batches failed to parse. The trial does not
  use it. The trial uses the traced quality-filter set from step 4.
- The page that shows all of this is built by `build_page.py` from
  `page.html` and the JSON files. It was served on the dev tunnel as
  `angles-retweets.html`. Quick-tunnel URLs change on restart.

## Files on the branch

`experiments/angles-retweets/`:

| File | What |
|---|---|
| `extract_parallel.py` | `extract_angles.py` main with 4 model calls at a time |
| `rt.candidates.yaml`, `rt.angles.yaml` | no-filter raw and merged positions |
| `compare.py`, `rt_compare.json` | new or already in the list |
| `support.py`, `rt_support.json` | own-words test, embedding (rejected) |
| `stance.py`, `rt_stance.json` | own-words test, model |
| `classify.py`, `rt_labels.json`, `rt_keep_ids.json` | quality filter labels |
| `qf.*` | extraction again from filtered retweets (1 batch failed) |
| `build_page.py`, `page.html` | the comparison page |
| `trial/trial.angles.yaml` | the trial angle list (378 + 234 = 612) |
| `trial/trial_tick.sh` | the trial runner |

Script changes: `extract_angles.py` takes `--retweets {no,also,only}`
(default `no`), `--out`, and the `IH_RT_KEEP` list of retweet ids.
`consolidate_angles.py` reads `IH_ANGLE_CANDIDATES` and `IH_ANGLE_OUT`.

## One-week trial (started 2026-11-14)

Goal: see the full page fed by the new angles, and check its quality day by
day.

- Folder `/root/ih-angles-trial`: a real copy of this branch (`git archive`,
  no run history, empty card store). Its `angles.yaml` is
  `trial/trial.angles.yaml`, with 234 new angles. Their ids start with `rt-`
  and they have `origin: retweets, quality filter (2026-11-14)`.
- Each tick copies production `web/articles.json` (read only), then runs
  `brief.py` and `narrative_desk.py` in the trial folder. Top News and the
  story pool are the same as live. Only the angle list is different.
  Embeddings go to `/root/ih-angles-trial/.embed-cache`.
- The card feed starts empty, and it is full after 72 hours
  (`IH_FEED_MAX_AGE_H`). Compare with live from 2026-11-17.
- Crontab (system):
  - `50 * * * *` tick. It skips when production has no new articles.
  - `35 7 * * *` snapshot to `/root/ih-angles-trial/daily/<date>/{trial,live}/`.
    `live` is copied from `/var/www/html` after the 07:30 deploy.
- Log: `/root/ih-angles-trial/logs/tick.log`.
- Page: `trial/index.html` on the dev tunnel (a symlink to
  `/root/ih-angles-trial/web`).
- To stop: remove the two crontab lines under the "IH retweet-angles trial"
  comment. There is no automatic end date.
- First run: 11 cards, 1 with an `rt-` angle
  (`rt-hollywood-corporate-soullessness` on a music-industry story).
