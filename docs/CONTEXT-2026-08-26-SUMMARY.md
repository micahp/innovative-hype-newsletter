# 2026-08-26 - Innovative Hype news engine

Written 17:4x CDT, covering 08-25 and 08-26. Read
`CONTEXT-2026-08-24-SUMMARY.md` first: its evening pass is what this one is
mostly about the consequences of.

**v0.1.0 tagged**, the repo's first tag ever.

## THE DAY'S ONE SHAPE

**The desk was dark for 19 hours and every instrument a person would look at
said fine.**

The 08-24 evening pass replaced keyword matching with embeddings. Every commit
was tested by hand and passed. The pipeline then failed on its next scheduled
run and on the eight after that, and the failure was invisible because of how
the stages are wired:

```
feed_aggregator.py rc=0   -> web/articles.json kept refreshing every 2h
brief.py           rc=1   -> ModuleNotFoundError: No module named 'numpy'
narrative_desk.py  rc=1   -> load_clusters() never returned
```

`articles.json` stayed fresh. `web/brief.html` went on serving its last good
cards, because it is a running feed rather than one run's output. The page even
said `updated 2026-08-25 00:29 UTC`, which reads as "earlier today" and was
19:29 the previous evening.

Micah spotted it, not an instrument: *"so it was supposed to run but it never
did..."* and, looking at the page, *"tha'ts funny because whats currently on the
site is good."* It was good because it was old.

## 1. Two regressions, both mine

### 1a. Dev and cron are different interpreters

`/root/.hermes/scripts/cron_news.py` runs each stage with `sys.executable`,
which is the hermes venv at **Python 3.11**. Development here happens under
`/usr/bin/python3`, **3.8**, which had numpy. So `scripts/embed.py` imported
cleanly every single time I tested it and raised every single time the cron ran.

Fixed by installing numpy into that venv, and by making the import raise a
message that names the interpreter and says a package present in one says
nothing about the other.

> **A green run under your shell is a claim about YOUR interpreter.** This is
> `feedback_run_the_suite_against_both_dbs` wearing different clothes.

### 1b. I batched half the pipeline

Fixing numpy alone would not have brought it back. `warm_signatures()` was wired
into `narrative_desk.load_clusters()` and **not** into `brief.make_brief()`,
which is the stage the cron reaches first. That loop called `signature_for()`
per article, so a 2,580-article pool was 2,580 sequential single-item provider
calls. It ran past 400s and wrote nothing; the cron's 900s per-script timeout
was the only thing standing between it and running forever.

Batched, `brief.py` is **78.6s, rc=0**.

### The measurement mistake underneath both

I reported `load_clusters` at 64.5s as evidence the semantic path was
affordable. That was:

- the stage I had already batched, not the one the cron hits first,
- on a warm cache,
- under the wrong interpreter.

**Three ways of not measuring the thing that runs**, in a single number I
offered as reassurance.

## 2. I also said nothing schedules the pipeline

Asked what drove the 2-hourly runs, I checked root's crontab, systemd timers,
`/etc/cron*` and `pipeline.sh`, found nothing, and said so. Wrong.

**Hermes has its own cron at `/root/.hermes/cron`.** The job is `feed-aggregator`
(id `36748f1d747d`, `script: cron_news.py`, interval 120m), and its
`jobs.json` had carried `"last_status": "error"` with the full traceback in
`last_error` the whole time. The evidence was sitting in a file I had not
thought to look for because I had already concluded the file did not exist.

> **"I looked and found nothing" is a statement about where you looked.**

## 3. Timestamps are local now

Micah, reading the footer: *"everything should be in local time on the
webpage."* It said `2026-08-25 00:29 UTC`, which is 19:29 CDT the previous
evening, and the staleness was the one thing that stamp exists to convey.

Four display sites go through `brief.local_ts()` now. **Storage stays UTC on
purpose**: run directory names, `meta.json` timestamps and every card's
`first_seen` are keys and comparisons, and a local-time key repeats itself for
an hour every autumn. The conversion happens at the edge.

`web/index.html` needed nothing; it formats through `toLocaleDateString`, so the
feed cards already render in the viewer's own timezone.

Incidentally this is why the run directory names look like tomorrow:
`runs/20260825_002930` is a UTC name for a 19:29 CDT run.

## 4. Verified restored

The 16:23 run on 08-26, `code_version e575bb8`, is **the first brief ever
rendered by the semantic matcher**.

```
feed_aggregator.py    rc=0
brief.py              rc=0     <- was rc=1
narrative_desk.py     rc=0     <- was rc=1
acceptance_fixture.py rc=1     (by design: 2 stories ABSENT_FROM_FEED)
gates.py              rc=1     (by design: 7/11)
test_type_gate.py     rc=0
```

**A non-zero exit from `cron_news.py` usually means a gate found something, not
that the pipeline broke.** That distinction is now in the README, because it
cost a day to learn.

And the thing Micah reported on 08-24 is fixed. The housing cluster now holds:

- A new Texas law declaws neighborhood groups that oppose housing projects
- UMusic Unveils Plans for Austin Hotel & Residential Community
- Property taxes are the housing affordability crisis no one wants to touch

Two of those carry the place names that used to drag the Padres and the Mystics
in with them. They belong there on merit now.

## 5. Where the tests actually stand

**Gates 7 of 11. The same number as before the rebuild**, having gone 7 -> 6 ->
7. The count is flat and the meaning is not:

| gate | before | now |
|---|---|---|
| G3 three-ways-qualify | FAIL | PASS (pool-dependent, not from this work) |
| G5 | PASS, testing `_kw_match`, which nothing calls | PASS, testing the live matcher |
| G6 | PASS, checking dead keywords | FAIL, checking the lists that decide |

Two gates stopped being green about nothing. Still red: G6 (generic terms
`revenue`, `platform`, `media` in the new angle scopes), G7 (17 of 55 feeds
down), G2 and G10 (specified, never implemented).

**Acceptance fixture 2 of 8 reach the desk.** But `ABSENT_FROM_FEED` went from
**6 to 2**: four stories moved from "not in the pool at all" to "in the pool,
ranked below the cutoff". That reframes the work from *find a feed* to *fix
ranking*.

> **That improvement is NOT from this work.** It comes from the pool growing to
> ~3,000 articles and the `news` agent's persistence merge. The semantic
> rebuild changed clustering and angle eligibility, not feed coverage. Do not
> let the two get credited to each other.

## 6. v0.1.0

The repo had **no tags at all**, locally or on the remote, so nothing was
missing from GitHub; it had simply never been tagged. Unlike `legendarypicks`
there is no `scripts/release.sh` and no pre-push hook here, so it was cut by
hand as an annotated tag matching LP's `vX.Y.Z` format.

The tag was force-moved once, from `3601079` to `b2b6857`, to include the README
rewrite. It was minutes old and unfetched. Worth porting `release.sh` and the
pre-push hook if releases here should work like LP's.

## 7. The README described a pipeline that no longer exists

It documented only `research.py -> draft.py -> publish.py -> Substack`, the
2026-06 path. Nothing in it referred to `feed_aggregator`, `brief`,
`narrative_desk`, `gates`, `angles.yaml`, the corpus or `web/brief.html`. Its
"current limitations" section still listed *"ranking is keyword + recency, not
thesis/worldview-aware"* as future work, two rebuilds after that stopped being
true.

Rewritten around the six-stage flow, why matching is semantic, how the voice
profile is built, and the honest v0.1.0 state. The legacy path is documented as
legacy rather than deleted: `publish.py` is still the only route to Substack,
and `pipeline.sh` hardcodes macOS paths under `/Users/micah`.

## 8. STILL OPEN

- **`angles.yaml` has 378 positions and needs his cut.** 213 reach a story in
  the current pool, 165 cannot. By category the dead are politics 48, media 33,
  NFT-era 26, personal 20. Prefer `enabled: false` to deleting: adding a source
  wakes them.
- **G6 red** on generic scope terms in the new file.
- **G2 and G10 need writing.** Unchanged since 08-24.
- **17 of 55 feeds dead.** Unchanged since 08-21.
- **The paragraph still restates the headline.** Unchanged since 08-23.
- **The brief page has still never been inspected in a browser.** The 1280 ->
  1000 width change on 08-24 was made against the CSS, not against a render.
- **`voice_terms.txt` is the third keyword layer and was never converted.** It
  still scores by substring and still contains `texas`.
- **The interpreter-mismatch lesson is not in the `fail-loudly` skill.** It is
  exactly the shape that skill exists to catch.

## 8b. NEXT PHASE, written up and not built

Micah, on wanting social/digest/topic-articles plus a feedback interface:
*"i havent' found the right lever for this yet and i don't want to overdo it...
the cadence of how the cards fall matters too....right now it's just a brief
that gets regenerated every day with enough cards to be a site. but then they
go stale and go away forever."*

Measured: **693 distinct cards written, 35 live, 658 gone.** `feed()` at
`narrative_desk.py:610` keeps what is inside a 72h window and silently drops
the rest. No archive, no state, no count. The brief is a sliding window that
happens to render, discarding ~40 written and ranked cards a day.

The lever is that **cards should graduate, not expire**, and the digest, topic
articles, social posts and the feedback interface all fall out of that one
change. Notably it reorders the work: a feedback UI built against run output
would have every judgment evaporate on the same 72h clock, because the object
being judged does not survive.

Proposal and a scope-locked task in
[`PHASE-2-CARD-LIFECYCLE.md`](PHASE-2-CARD-LIFECYCLE.md). Not implemented.

## 9. COMMITS

```
e575bb8  Page timestamps render in local time, not UTC
3601079  Fix the two regressions that took the desk dark for 19 hours
b2b6857  README describes the news engine, which it never mentioned
```

Pushed. `v0.1.0` -> `b2b6857`.

Dirty and deliberately left alone: the five `corpus/*.jsonl` scrapes,
`runs/latest`, `web/articles.json`, `web/brief.html`, `web/brief.md` and the
untracked `runs/2026082*/` directories. The hermes cron writes them every 120
minutes.

MEMORY.md was trimmed from 26.5KB to 23.3KB, under its 24.4KB load limit, by
rewriting 43 over-long index hooks. No pointer or lesson was dropped.
