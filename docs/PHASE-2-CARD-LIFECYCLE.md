# Phase 2: cards graduate, they do not expire

Written 2026-08-26. Status: LANDED 2026-08-27 (store live, G12 in gates.py and
§6b; digest/topics/social/feedback UI remain Phase 3). Read
`CONTEXT-2026-08-26-SUMMARY.md` for the state this builds on.

## 1. The problem, measured

Micah, 2026-08-26:

> "the cadence of how the cards fall matters too....right now it's just a brief
> that gets regenerated every day with enough cards to be a site. but then they
> go stale and go away forever. that's not what i want"

Measured against the live run the same day:

```
693  distinct cards written across all runs
 35  live on the page
658  have fallen off and exist nowhere on the site
```

Live set by age: 22 cards from today, 12 from two days ago, 1 at 72.5 hours and
about to vanish.

The mechanism is `narrative_desk.py:610`, in `feed()`:

```python
cutoff = now - _td(hours=FEED_MAX_AGE_H)   # 72
out = []
for c in existing.values():
    seen = _dt.fromisoformat(c.get("first_seen"))
    if seen >= cutoff:
        out.append(c)
```

Everything older is not archived, not marked, not counted. It is simply not
copied into `out`. The text survives in `runs/<ts>/cards.json`, so it is
technically recoverable, but no stage of the pipeline and nothing on the site
ever reads it again.

**The brief is not a publication. It is a 72-hour sliding window that happens to
render.** At roughly 40 cards a day that is the rate at which written, ranked,
angle-checked work is being thrown away.

## 2. The lever

**A card should graduate, not expire.**

This is one change, and the four things Micah asked for on 2026-08-26 fall out of
it rather than being four separate builds:

| ask | what it becomes |
|---|---|
| daily digest | a query on the store: what entered today |
| topic-based articles | a query on the store: every card on a subject over weeks |
| X and Instagram | posts from the fresh end, with the store recording what went out so nothing posts twice |
| up/down/remove + run feedback | judgments that attach to a card which still exists tomorrow |

That last one is the reason this document exists and the interface does not. An
interface was about to be built against run output. Every judgment entered into
it would have evaporated on the same 72-hour clock, because the object being
judged does not survive. **Ranking feedback on an object with a 72-hour life is
theatre.** Build the store first.

### Cadence becomes expressible

Micah named cadence specifically. Today "how the cards fall" is a single
constant, `FEED_MAX_AGE_H=72`, applied uniformly to everything. There is no way
to say:

- hold this card longer, the story is still developing
- retire this one early, I marked it down
- let this slow-burn topic accumulate cards until it is worth an article
- this card was posted to X, do not surface it again as new

None of those are expressible against a window. All of them are trivial against
a store with per-card state.

## 3. What Phase 2 is NOT

Scope discipline, because Micah said "i don't want to overdo it":

- **Not** the digest, the topic articles, or the social publishing. Those are
  Phase 3 and each needs its own decision about voice and format.
- **Not** the feedback UI. Phase 2 makes it worth building; it does not build it.
- **Not** a database. A JSONL store with a derived index is enough at 693 cards
  and will be enough at 20,000.
- **Not** a change to what renders. The 72-hour window still governs the live
  brief. Phase 2 only stops the discarded cards from ceasing to exist.

If Phase 2 lands and nothing visible changes on the page, it worked.

---

# TASK: the durable card store

## Goal

`feed()` writes through to a durable store on every run. The live brief becomes
a VIEW over that store rather than the only copy of a card. No card is ever
deleted by the pipeline.

## Files you may touch

```
scripts/card_store.py       NEW: the store, its schema, its queries
scripts/narrative_desk.py   feed() writes through; nothing else changes
scripts/gates.py            one new gate, see Acceptance
NEWS-ENGINE-SPEC.md         the new gate's spec entry in §6b
docs/PHASE-2-CARD-LIFECYCLE.md   mark sections done as you land them
```

**Do not touch** `brief.py`, `feed_aggregator.py`, `embed.py`, `angles.yaml`,
`voice_terms.txt`, `web/index.html`, or anything under `/root/.hermes/`.

## Schema

`cards.jsonl`, append-only, one JSON object per line, at the repo root.

Every card the desk writes gets a row on every run in which it appears. The
store is the log; the current state of a card is the newest row bearing its
`story_key`.

```
story_key     stable id already present on every card
run           the run ts that produced this row
first_seen    carried forward, never rewritten
last_seen     the run ts of the newest row
state         live | aged_out | evicted | removed
narrative     card text, current
paragraph     card text, current
kicker        cluster name
sources       list, as the card carries it
angle_id      what the desk claimed, null if none
angle_offered what was legal for its cluster
lead_score    the ranking number at the time
```

`state` transitions, all of them recorded rather than applied by deletion:

- `live` while inside the window
- `aged_out` when it passes `FEED_MAX_AGE_H`. **This replaces dropping it.**
- `evicted` when the type gate or angle gate rejects it on a later run. The
  existing eviction path at `narrative_desk.py:607` already prints this and
  then discards; it should record instead.
- `removed` reserved for the Phase 3 interface. Nothing writes it yet. Define
  it now so the interface does not have to migrate the schema.

## Rules

1. **Nothing in the pipeline deletes a row.** Not aging, not eviction, not a
   pool change. If a card stops rendering, that is a state, not an absence.
2. **`first_seen` is never rewritten.** It already has a bug history here: see
   `narrative_desk.py:577`, where the feed sorted by `first_seen` and a golf ad
   reached #1.
3. **The store is derived and rebuildable.** `runs/*/cards.json` holds every
   card ever written. Ship a `--rebuild` that reconstructs `cards.jsonl` from
   those runs, and use it to backfill the 658 lost cards on first run.
4. **Fail loudly.** Load `.claude/skills/fail-loudly/SKILL.md` before writing a
   line of this. A store that silently returns zero rows makes the live brief
   look exactly like a healthy one with a small pool. Specifically: an
   unreadable `cards.jsonl` raises rather than starting empty, and a run that
   would write zero rows against a non-empty store raises.
5. **Say the counts every run.** `N live, N aged_out this run, N total in
   store`. A count that only appears on failure cannot tell "clean" from "never
   ran".

## Acceptance

Concrete, and written before the code per `feedback_fix_gates_before_the_code`:

1. `python3 scripts/card_store.py --rebuild` reconstructs from `runs/*/cards.json`
   and reports **at least 693 rows**, the count measured on 2026-08-26.
2. After one full pipeline run, `cards.jsonl` contains every `story_key` in
   `web/brief-cards.json`, and every one of them is `state: live`.
3. A card older than `FEED_MAX_AGE_H` is present in the store as `aged_out` and
   absent from `web/brief-cards.json`. **Both halves must be asserted.**
4. `web/brief-cards.json` is byte-identical in structure to what it renders
   today. If the page changes, the scope was exceeded.
5. New gate **G12 no-card-deleted**: the store's row count is monotonic across
   runs. It reads the previous count from the store itself, not from a fixture.
   Add it to `SPEC_GATES` in `gates.py` AND to §6b of `NEWS-ENGINE-SPEC.md` in
   the same commit, since a gate in one and not the other is the G2/G10 failure
   that has been open since 08-24.

## Verification, and read this part

Today's incident is the reason this section is explicit.

- **Run every check with the interpreter the cron uses**, not the one on your
  PATH: `/usr/local/lib/hermes-agent/venv/bin/python3`. On 2026-08-24 a numpy
  import worked under `/usr/bin/python3` (3.8) and failed under the venv (3.11),
  and the desk was dark for 19 hours while `articles.json` stayed fresh and the
  page served stale cards. An import smoke test under your own shell proves
  nothing.
- **After landing, check the job actually ran.** Read
  `/root/.hermes/cron/jobs.json` for `feed-aggregator` and confirm
  `last_status` and `last_error`. The pipeline's real external surface is a
  hermes cron job, and a green local run says nothing about it. See
  `feedback_a_split_breaks_things_outside_the_repo`.
- **Do not modify the cron, the venv, or anything under `/root/.hermes/`.** If
  the task appears to need that, stop and say so.
- A non-zero exit from `cron_news.py` usually means a gate found something
  rather than that the pipeline broke. Read which stage.

## Out of scope, explicitly

Digest generation, topic articles, social publishing, the feedback UI, changing
`FEED_MAX_AGE_H`, changing what renders, per-card cadence rules. Phase 2 is the
store and only the store. Per-card cadence is the first thing the store makes
possible and the first thing Phase 3 should take up.
