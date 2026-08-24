# 2026-08-24 - Innovative Hype news engine

Written 16:1x CDT. The §WHY at the top of `CONTEXT-2026-08-23-SUMMARY.md` is
unchanged and is still the thing to read first. This pass did not touch
selection quality. It touched whether we can TELL when selection quality has
silently gone to zero.

## THE DAY'S ONE SHAPE

**The fourth ranking term, the highest-leverage thing on the project, was in a
state where it could have been contributing nothing and every instrument would
still have reported a healthy run.**

Same shape as the 08-24 Legendary Picks day, arrived at independently. It is
now written down as a loadable skill rather than a lesson.

## 1. The audit

Eight findings against the live `web/articles.json`, 2,022 articles, 52 voice
terms. Three were fixed on request, the rest are open and listed in §4.

1. `_load_voice_terms()` swallowed every exception and returned `[]` at import
   time. A renamed or broken `voice_terms.txt` turns the fourth score term off
   and every article ranks exactly as it did before the term existed, which is
   the state that produced a golf ad at #1. FIXED.
2. Nothing measured which terms fired. **24 of 52 fired zero times**, including
   `palantir`, `thc`, `hemp`, `marijuana`, `deepseek`, `cursor`, `elon musk`,
   `zuckerberg`, `polymarket`, `substack`, `license plate`, `facial
   recognition`. Those are the subjects the term was added to rescue, and
   `907d85e` cites "Texas THC lawsuit #419 to #1" as its evidence. FIXED
   (per-term hit table + dead list in the meta, printed every run).
3. `articles.json` still declared `weighted_editorial_v1` with three terms and
   no mention of the boost. A stored file could not say which scorer made it.
   FIXED, now `weighted_editorial_v2_voice` with the term path, loaded/fired/
   dead counts, boost, cap and load error.
4. `texas` alone took **55 of 150 hits**, next is `wnba` at 20. It is a
   geography, not a subject. OPEN.
5. Generic single nouns match phrasing, not subject. `platform` put "WildBrain
   Acquires Kid Safe Generative-AI Platform Personality AI" at #6.
   `data center` + `platform` put a Paxton chatbot-ban headline at #2. OPEN.
6. Magnitude: max base score (source + recency + pillar) across the pool is
   **7.89, mean 3.10**, against a voice cap of **6.0**. Three generic hits beat
   a T1 source on breaking news. Only 1 article of 2,022 reaches the cap, so the
   cap is not what constrains anything; the 2.0-per-hit slope is. OPEN.
7. `extract_angles.py` defaulted `ARCHIVE_JSON` to a path inside another Claude
   session's `/tmp` scratchpad, and returned `[]` when it was gone. That file is
   the specification for the whole voice profile. FIXED, now
   `corpus/x_archive_all_tweets.json`, 33,143 tweets, 1,993 weighted originals,
   and a missing archive raises.
8. `gates.py` dead locals and unused imports. OPEN, cosmetic.

Feed health at audit time: **`feeds_ok 37, feeds_fail 18, feeds_total 55`**.
The 08-23 summary recorded 17 of 48. It has not improved.

## 2. The gates were lying in two ways

- **G7 is named `feeds-loud`** and the spec says it passes when a dead feed
  causes a visible failure. What it asserted was
  `"feeds_fail" in feed and "feed_failures" in feed`, a presence check on a JSON
  key. Green with 18 of 55 dead, green on 08-21 with 17 of 48 dead. It now fails
  and names them: ESPN, The Athletic, Bleacher Report and Sports Business
  Journal among the 18.
- **§6b lists 11 gates; the runner implemented 9** and printed `8/9 gates
  passed`, a denominator that redefined itself to whatever had been written.
  **G2 (boost-not-filter) and G10 (keep-cards) have never existed.** They now
  report FAIL from a `SPEC_GATES` roster.

Honest result: **7 of 11, exit 1**. It read 8 of 9, exit 1, before. Two of the
three new reds were always true and had nowhere to appear.

Correction for the record: I reported mid-session that `gates.py` exits 0 on a
FAIL. It exits 1 and always did. I had read `tail`'s status through a pipe.

## 3. The repo had no skills at all

`/root/innovative-hype-newsletter` had no `.claude/` directory, so every one of
these defects was written in a repo where the doctrine that covers them was not
loadable. It lived only in `legendarypicks`. A skill that exists in one repo is
not a skill the next repo has.

`.claude/skills/fail-loudly/SKILL.md` now carries the same governing principle
with THIS pipeline's measured cases, and a description keyed to what actually
gets touched here: `score_article()`, `gates.py`, `voice_terms.txt`,
`angles.yaml`, the corpus, anything writing `web/articles.json`.

## 4. STILL OPEN

Carried from 08-23 and untouched today:

- **The angle list still needs his cut**, then the generic entries come out of
  `voice_terms.txt`. Items 4, 5 and 6 above are all one decision: the term file
  currently mixes subjects (`flock`, `palantir`) with geography (`texas`) and
  stopword-grade nouns (`platform`, `compute`, `lawsuit`, `jury`). The new
  per-term hit table is the instrument for making that cut with numbers.
- **The paragraph still restates the headline.**
- **Six of eight acceptance-fixture stories are still `ABSENT_FROM_FEED`**, and
  18 of 55 feeds are dead. Sports can still only be seen as money.
- **G2 and G10 need writing**, now that they report FAIL instead of nothing.
- **G6 hygiene should extend to `voice_terms.txt`.** G6 bans `platform` from
  signatures by name; the voice file does the same job and contains it.

New today:

- **The brief page has never been inspected in a browser.** I ran a 63-load
  responsive sweep this session and pointed it at the Legendary Picks dev tunnel
  on `:3096`, not at `web/` on `:8099`, which is the surface this session was
  about. That sweep found real LP defects and answered a question nobody asked.
  The IH brief page is unexamined at every viewport.

## 5. Repo state

**`main` is 11 commits ahead of `origin/main`, unpushed.** Six of those predate
today (through `907d85e`, the fourth ranking term itself).

Dirty and deliberately left alone: all five `corpus/*.jsonl`, `runs/latest`,
`web/articles.json`, `web/brief.html`, `web/brief.md`, and ~30 untracked
`runs/2026082*/` directories. These are pipeline output, still being written.
Latest run `20260824_202517`.

## 6. COMMITS

```
03fc026  Move the news-engine context summaries into the repo
63a4107  The voice term reports its own coverage, and fails loud
7579d50  The X archive moves into the repo; a missing one raises
4d7462a  A fail-loudly skill for this repo, which had no skills at all
450f446  G7 checks the number, and a gate missing from the runner is a FAIL
```

The 08-21 and 08-23 summaries were moved into `docs/` from `/root` in the first
of those, along with 57 Legendary Picks handoffs into that repo's `docs/`. All
MEMORY.md pointers and doc cross-references were rewritten and every linked path
verified against disk.
