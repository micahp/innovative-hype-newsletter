# 2026-08-31 - Innovative Hype news engine

Written 2026-08-31, covering 08-28 through 08-31. No code changed in this
window (last code commit is 08-27's `f6dc810` docs; before that `b802d21`/
`6ff949a`). Read `CONTEXT-2026-08-27-SUMMARY.md` first: the grader rules, the
gnews/sitemap surfaces, and the standing reds below all come from there.

## THE DAY'S ONE SHAPE

**Every cron tick since 08-27 logs `last_status: error`, and every one of
them is the known standing reds, not a failure.** cron_news.py exits 1 if ANY
stage exits non-zero; the acceptance fixture exits 1 while fewer than 8/8
named stories reach the desk, and gates.py exits 1 while G2/G10 sit in the
spec unimplemented. So the badge is red by construction on every tick.

That is fail-loudly turned inside out: **a signal that never clears stops
being a signal.** The next genuinely broken tick is indistinguishable from
these 28 healthy-but-red ones. Before trusting the badge again: either
implement/strike G2 and G10, and make the fixture's known-unreachable
stories a reported WARN rather than the exit code, or accept that the Hermes
cron status is noise and the real instruments are the per-tick output files.

## 1. Three days of unattended cron with the new surfaces

28+ ticks, all stages rc=0 except the two standing reds:
- feeds_ok stable at 50-52/66 (recovered from 46 the night the gnews feeds
  landed; the 2h cron retries brought Wired, CoinDesk, HN feeds back).
- ZERO ticks with Reuters/AP/CNN/Axios/Bloomberg FAILED. The valid-empty
  Google News response seen once on 08-27 has not recurred; if it does, it
  reads as a loud FAILED feed and the cron retries, as designed.
- Gated outlets accumulate in the pool (72h retention, ~20 rows/run/feed):
  Reuters 204, AP 476, CNN 116, Axios 58, Bloomberg 132.

## 2. The grader is running in production and reads like the rubric

All 27 brief cards carry a quality grade: **A:1, B:10, C:10, D:3, F:3.**
The F notes are the 08-27 rules firing verbatim:
- "Thesis contradicts the paragraph's own facts" (Anthropic watermarking,
  the internal-contradiction rule)
- "the cited sources are about..." (mismatched context caught, not graded
  through it)
- "thesis mischaracterizes the story" (Cameron Brink/Enes Kanter card)

Grades still do not move rank and do not feed the desk prompt (log +
display only, per Micah's standing rule).

## 3. Observation worth a look next session

Two Anthropic watermarking cards sit in the same brief: one graded F for
contradiction, one graded F because its context resolved elsewhere. That
reads as duplicate variant cards on one cluster. Worth checking whether the
dedupe/same-shape gate should have caught the second.

## 4. Acceptance fixture: 1/8 to 3/8, still red by design

Flock cameras, Data centers/Texas, and Longhorns vs Texas State now reach
the desk. Kanye fireworks, NBA-to-WNBA draft, and Sophie Cunningham are
absent from the pool (older than the window or no live feed carries them);
Marijuana Texas and 40-yr NCAAF are time-window drops. Same time-based
shape as 08-27, not a regression.

## 5. Housekeeping in this commit

Regenerated artifacts (corpus pulls, web/*, runs/latest) committed with
this doc. Untracked by design: `cards.jsonl` (the card store,
`card_store.STORE_PATH`), `runs/*` (per-run artifacts), `web/assets/`,
`docs/SELF-HOST-NITTER-DESKTOP.md`.

## Next

- Decide the standing-red policy (see THE DAY'S ONE SHAPE): the badge must
  be able to go green, or it cannot tell you anything.
- The duplicate Anthropic watermarking cards.
- WSJ Markets feed is still configured but frozen at Jan 2025.
