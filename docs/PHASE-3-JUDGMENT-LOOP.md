# Phase 3: the judgment loop

Written 2026-08-26. Status: PROPOSAL, not built. Depends on Phase 2
(`PHASE-2-CARD-LIFECYCLE.md`), which must land first.

## 1. Correction to Phase 2's closing line

`PHASE-2-CARD-LIFECYCLE.md` ends by saying per-card cadence is "the first thing
Phase 3 should take up." **That is wrong and this file supersedes it.**

Cadence rules without a feedback signal are more constants for an assistant to
guess. Today there is exactly one, `FEED_MAX_AGE_H=72`. Replacing it with five
tunables picked by whoever writes the code is not progress, it is four more
numbers nobody measured. **Cadence is the consumer of Micah's judgments, not the
first thing built on an empty store.**

Order below is: make the list worth ruling on, collect the rulings, then let
cadence spend them.

## 2. The ladder

```
3a  event-level dedupe        make the list worth ruling on
3b  the feedback interface    collect the rulings
3c  cadence, driven by 3b     spend them
3d  the outputs               digest, then topic articles, then X + Instagram
```

Each is its own task file with its own scope lock. Only 3a is specified here.
Writing 3b before 3a lands would repeat the Phase 2 mistake of specifying a
consumer before its input exists.

### Why 3a is first

Measured 2026-08-26 on the live page, 35 cards:

- **Seven** are the same Enes Kanter / WNBA incident.
- Two are the same YouTube Pedro Pina quote.
- Two are the same Texas football off-field story.
- 14 of 35 are Sports, on a tech, business and culture brief.

A feedback interface built before this asks Micah to rule on the Kanter story
**seven times**. The first thing his attention meets would be the thing the
system is worst at. Fix the list, then ask.

### Why the outputs are last

A daily digest, a topic article and an X post are each a query on the store plus
a decision about voice and format. They inherit whatever quality the list has.
Shipping them over a list with seven duplicate cards publishes seven duplicate
posts, and it does it in public.

## 3. Two live bugs that sit outside this ladder

Neither should wait for Phase 2 or 3.

- **`social-corpus-poll` is failing.** `/root/.hermes/cron/jobs.json`, job
  `social-corpus-poll`, `last_status: error`:
  `{"error": "auth failed: HTTP Error 429: Too Many Requests"}` from nitter.
  `corpus/innovativehype.jsonl` and `corpus/geoppls.jsonl` are frozen at
  **2026-08-24**. That corpus feeds `brief._seed_match()`, one of the three ways
  an article qualifies for the desk and the entire subject of gate G4. So
  anything Micah has tweeted since 08-24 is not a ranking signal. **This is the
  direct cause of "i've been tweeting some stuff that i havent' seen on the
  list."** Do not retry nitter in a loop; `corpus/README.md` already records
  most instances as dead or challenge-gated, and hammering a 429 is how this box
  got IP-blocked by Liquipedia on 08-10.
- **`voice_terms.txt` is the third keyword layer and was never converted.**
  Clustering and angle eligibility moved to embeddings on 08-24. Ranking did
  not. It still scores by substring and still contains `texas`, the term that
  took 55 of 150 hits and put a WNBA story in the housing cluster.

---

# TASK 3a: event-level dedupe

## Goal

Cards about the same real-world event collapse into one card carrying all of its
sources, instead of appearing as N separate cards.

## The measurement that defines the problem

Text similarity does not solve this, and the numbers say why. Cosine over the 35
current card texts finds **4 pairs at >= 0.60**:

```
0.740  "The WNBA bans a provocateur for wearing a shirt..."
    vs "A man gets ejected from a WNBA game for a shirt..."
0.683  "Sky coach Tyler Marsh defended Natasha Cloud after the Kanter incident."
    vs "Natasha Cloud confronted Enes Kanter while the Sky were on the brink..."
0.681  the two Texas football off-field cards
0.618  the two YouTube / Pedro Pina cards
```

It misses the rest of the Kanter pile-up entirely. "Caitlin Clark missed the
Kanter-Cloud fight because she was in the huddle" and "Enes Kanter plans to
attend the Fever-Sky game after declaring for the WNBA Draft" are the same
event and share almost no vocabulary.

**Sentence similarity measures how alike two sentences are. The question here is
whether two cards are about the same happening.** Those are different questions,
and the second one is answered by shared entities plus proximity in time, not by
cosine over prose.

## Approach

Group by **shared named entities within a time window**, then use cosine only as
a secondary signal.

1. Extract entities per card from `narrative` + `data_point` + source headlines.
   People, orgs, teams. `brief._clean_entities()` already exists; read it before
   writing anything new.
2. Two cards are the same event when they share **2 or more** distinct entities
   AND their `first_seen` are within a window (start at 48h, tune with the
   numbers below).
3. Merge: keep the highest `lead_score` card's text, union the `sources`, keep
   the earliest `first_seen`, record the merged `story_key`s.
4. **Record the merge in the store as a state, do not delete the losers.** Phase
   2's rule 1 is that nothing in the pipeline deletes a row. Add
   `state: merged_into` with the surviving `story_key`. A merge that turns out
   wrong must be reversible, and the Phase 3b interface will need to show what
   was folded together.

## Rules

1. **Load `.claude/skills/fail-loudly/SKILL.md` first.** A dedupe that silently
   over-merges produces a shorter, cleaner-looking brief that is missing real
   stories, and there is no way to see that from the page.
2. **Print the merges every run.** `N cards, M merged into K groups`, and the
   headline of each group with its members. Say the zero: "0 merged" must look
   different from a healthy run.
3. **Never merge across kickers without agreement.** Two cards in different
   clusters sharing two entities are more likely a coincidence than one event.
   Require either the same kicker or cosine >= 0.55.
4. **The union of sources is the point.** One card with seven sources is a
   stronger card than seven weak ones. Do not just drop six.

## Acceptance

1. The seven Kanter cards on the 2026-08-26 pool collapse to **one** card
   carrying at least 5 sources.
2. The YouTube/Pina pair and the Texas football pair each collapse to one.
3. **No merge crosses subject.** Assert specifically that no AI card merges with
   a sports card on the current pool. Over-merging is the failure mode that
   looks like success.
4. Card count on the page drops and **no `story_key` disappears from the
   store**. Both halves asserted, per Phase 2 gate G12.
5. New gate **G13 no-duplicate-events**: no two rendered cards share 2+ entities
   within the window. Added to `gates.py` AND to `NEWS-ENGINE-SPEC.md` §6b **in
   the same commit**, since a gate in one and not the other is the G2/G10 defect
   open since 08-24.

## Files you may touch

```
scripts/dedupe_events.py    NEW: entity extraction, grouping, merge
scripts/narrative_desk.py   feed() calls it; nothing else changes
scripts/gates.py            G13
NEWS-ENGINE-SPEC.md         G13's §6b entry
```

**Do not touch** `brief.py`, `feed_aggregator.py`, `embed.py`, `angles.yaml`,
`voice_terms.txt`, `web/index.html`, `web/brief.html`, `web/brief-cards.json`,
`render_brief_html()`, or anything under `/root/.hermes/`.

## Verification

Same two rules as Phase 2, for the same reason.

- **Run every check with `/usr/local/lib/hermes-agent/venv/bin/python3`**, not
  the `python3` on your PATH. On 2026-08-24 numpy existed in one and not the
  other, the desk was dark for 19 hours, `articles.json` stayed fresh and the
  page served stale cards throughout. An import smoke test under your own shell
  proves nothing.
- **After landing, read `/root/.hermes/cron/jobs.json`** for the
  `feed-aggregator` job and confirm `last_status` and `last_error`. The real
  external surface of this pipeline is a hermes cron job. A green local run says
  nothing about it.
- A non-zero exit from `cron_news.py` usually means a gate found something, not
  that the pipeline broke. Read which stage.

## Out of scope

The feedback interface, cadence rules, the digest, topic articles, social
publishing, and both live bugs in section 3. Task 3a is dedupe and only dedupe.
