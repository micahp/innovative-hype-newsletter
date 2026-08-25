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

---

# 2026-08-24, evening pass

Written 22:1x CDT. Everything above stands. The morning pass fixed whether we
can TELL when selection has gone wrong. This pass replaced the mechanism that
was making it go wrong.

## THE EVENING'S ONE SHAPE

**A word is not a subject.**

Three separate layers decided what a story was ABOUT by counting substring hits
from a hand-written keyword list, and all three failed the same way:

| layer | list | decides |
|---|---|---|
| `brief.NARRATIVE_SIGNATURES` | 10 lists of 8-13 keywords | which cluster a story joins |
| `voice_terms.txt` | 52 terms | the fourth ranking term |
| `angles.yaml` `scope` | 62 lists of 4-10 terms | which position the desk may take |

Broadening such a list attaches everything. Narrowing it attaches nothing. Both
are the same defect. §4 of the morning pass listed items 4, 5 and 6 as "one
decision" about `voice_terms.txt`; they were one decision about all three.

## 1. What he actually reported

"right now we have some sports narrative cards being tagged as affordability
and where people live lol. embarassing."

Confirmed on a 400-article slice of the live pool. The housing signature's
keyword list contains **`texas`**, so the old rule put these into
*Cities, housing and where America lives*:

- Padres make flurry of roster moves before Pirates series
- Mystics take big first step toward WNBA championship
- Texas Railroad Commission eliminates public comment period

Same `texas` that took 55 of 150 voice-term hits in the morning audit. Next
door, `Sports money keeps inflating` is keyed on `valuation`, `franchise` and
`broadcast`, generic finance nouns, which is why Brenda Song liking the Rams
was in it.

**The angle was never the root cause.** `eligible_angles()` matches scope
against the CLUSTER's text, so a wrong cluster guarantees a wrong angle offer.
Fixing angle scope alone would not have stopped the card he was embarrassed by.

## 2. Two things I got wrong and had to correct

**a. `angles.yaml` was never built from the X archive.** I said it was. In
fact `load_archive_originals()` and `ARCHIVE_JSON` were defined at lines 192
and 202 of `extract_angles.py`, **below** `if __name__ == "__main__"` at line
161. Nothing called them. `main()` called `load_posts()`, which read
`geoppls.jsonl` + `innovativehype.jsonl` and nothing else.

So the morning's finding #7, "FIXED, now `corpus/x_archive_all_tweets.json`",
corrected the default path of a function the program never reaches. The fix was
real and it changed nothing about what shipped.

**b. The file on disk was the version he already rejected.** The comment block
at line 165 says so outright: the first inventory came back "article-shaped:
62 rows", and *"it's not generic enough. it's too specific to the articles."*
`angles.yaml` had 62 rows and contained `galveston-housing-glut`. Archive mode
was written as the replacement and left below the exit line, so the rebuild
never ran. **Same shape as the 08-23 brief.py incident: two code paths, one
output filename, and the rejected version is the one that shipped.**

## 3. The Substack articles were never on this box

Seven years of 1,500-to-2,500-word argument, the longest-form statement of
every position, and `extract_angles.py` had never seen a word of it.
`publish.py` only pushes to Substack; nothing pulled back.

`scripts/pull_substack.py` fixes it. It hits `/api/v1/archive` for the
authoritative post list and `/feed` for the bodies, separately, so a post the
index lists and the feed does not carry gets named and counted.

```
archive index: 15 posts     (offset=15 and offset=30 both return 0)
feed carries:  15 bodies
usable posts:  15
total chars:   76035
NOT IN FEED: 0 - the feed covers the whole archive
```

I had warned there would be an archive gap. There is none: the publication has
posted 15 times in seven years, so the feed holds all of it. **This is a
one-shot developer tool. Nothing schedules it** (verified against root's
crontab, systemd timers, `/etc/cron*` and `pipeline.sh`), and it should stay
that way.

## 4. What replaced the keyword lists

`scripts/embed.py`, cosine similarity via `openai/text-embedding-3-small` on
the same Nous endpoint `call_llm` already uses. Disk cache keyed by
sha256(model + text). `warm()` batches a whole pool first, so 400 articles is
one round trip and 1.5s rather than 400 sequential ones. Every failure path
raises: a silently empty embedding layer would zero every similarity, no angle
would be eligible, and the brief would look healthy.

Probed against the three stories that broke:

```
Timberwolves sale      sports valuations 0.456   rent-vs-own compute 0.109
Nvidia compute-as-asset  rent-vs-own compute 0.427
Blue Origin $674M factory  housing 0.174
```

### The keyword list is not the probe

First attempt fed each signature's keyword list to the embedder. That carries
the vocabulary's accidents straight through: a Texas A&M story scored 0.148
against the housing probe, and 0.054 once `texas` and `austin` came out.

Stripping place names is not enough either. A bare noun list is a thin
description of a category and it dropped a REAL story, "Austin rents fall 12%",
from 0.360 to 0.279.

So each signature carries a `subject` sentence describing the category in
prose, the same field `angles.yaml` now carries. Against those probes:

```
Padres roster moves          housing 0.031     all three were clustered
Mystics WNBA championship    housing 0.038     INTO housing by the old rule
Texas A&M fall camp          housing 0.065
First-time buyers priced out housing 0.264
Austin rents fall 12%        housing 0.274
```

### Same ruler, before and after

```
old keyword rule   43 of 400 clustered (11%)
new cosine rule    61 of 400 clustered (15%)
330 agree, 1 moved, 35 dropped, 34 added
```

Dropped are the sports-in-housing cases. Added are "Data centers become killer
application for gas turbines" and "AI is hitting entry-level jobs hardest".

### Two costs, recorded beside the constant rather than buried

`SIG_SIM_FLOOR` 0.26 with a 0.02 margin. It misses "Oceans hit highest
temperature on record" (0.252) and two genuine housing items that rank housing
FIRST and still miss on short trade-press headlines.

A confidence clause was tried to recover them: admit anything above 0.21 that
beats its runner-up by 0.08. **Rejected**, and the reason is in the comment: it
recovered both and readmitted eleven wrong stories, because a high margin on a
short headline measures brevity, not confidence.

## 5. The corpus and the two-pass rebuild

`load_posts()` now reads every source, 897 posts to 2,772:

```
x-archive (originals, weighted recent)   1993 read,   1725 kept
geoppls.jsonl                             230 read,    229 kept
innovativehype.jsonl                      668 read,    667 kept
substack_posts.jsonl (paragraphs)         151 read,    151 kept
```

Each source prints read/kept and **a source contributing zero raises**.

The prompt's old scope rule was `"Be strict and concrete"`, which taught it to
copy vocabulary instead of naming subjects. It now asks for a `subject`
sentence naming the category and scope terms that BELONG TO it including ones
he never typed, since these are read by an embedding model rather than matched
as substrings. Place names are barred: **texas is where he lives, not what he
is talking about.**

24 batches produced **487 candidates**, and merging by exact id barely dedupes
(`you-will-never-own-your-compute` in one batch, `renting-your-compute` in the
next). `scripts/consolidate_angles.py` is the second pass he asked for:

1. **Group mechanically.** Nearest-neighbour cosine across the 487 is p50
   0.581, so most candidates genuinely have no duplicate and grouping alone can
   never do the reduction. At 0.86 it made 483 groups of 487. At 0.66 it makes
   424, and the merges are right: five Flock-camera statements become one.
2. **Merge by model**, one call per 20 groups.
3. **Drop what cannot fire**, via a `live` flag.

```
candidates 487 -> 424 groups -> round 2: 394 -> 378
kept 378 live, dropped 40 that no news story can trigger
```

## 6. 378 is not an editable inventory, so measure it

`scripts/angle_coverage.py` scores every angle against every article in the
live pool with the same cosine the desk uses. On a 600-article slice:

```
213 angles reach at least one story at cosine >= 0.30
165 reach nothing at all
```

| category | total | live | dead |
|---|---:|---:|---:|
| AI power, ownership and labour | 70 | **65** | 5 |
| Media, creators and platforms | 65 | 32 | 33 |
| Politics and geopolitics | 65 | 17 | **48** |
| Crypto and markets | 44 | 34 | 10 |
| NFTs, DAOs and web3 | 43 | 17 | 26 |
| Cities, housing and cost of living | 36 | 17 | 19 |
| Sports | 31 | 27 | 4 |
| Personal, health and relationships | 24 | 4 | **20** |
| **total** | **378** | **213** | **165** |

**AI is 93% live, by far the highest.** Politics is the single biggest block of
dead weight at 48 rows, 29% of the dead set, and I had wrongly called NFTs the
largest (26, third). Media splits almost evenly 32/33, which is the group that
needs reading rather than a rule.

**"Reach 0" is a fact about what the 55 feeds carry, not a verdict on the
position.** 18 of those feeds are dead. Prefer `enabled: false` to deleting
rows: adding a politics source would wake a chunk of the dead 165.

The single highest-reach position in the file is **rookie quarterbacks should
not be thrown into starting roles too quickly**, at 28 stories. Real position,
not what Innovative Hype is for. The numbers do not make the cut for him.

## 7. Gates

**6 of 11, down from 7.** The new red is correct.

- **G5 was asserting `brief._kw_match()` handles plurals. Nothing calls
  `_kw_match` any more.** A green assertion about a surface nothing reads is
  the skill's own §2e failure, created by this change. Rewritten as
  `G5 subject-match`: Padres and Mystics must NOT join housing, Austin rents
  must. Renamed because plural-match named a mechanism that is gone.
- **G6 checked signature keywords, which are now documentation and are read by
  nothing.** Extended to the three lists that do steer matching, and it bars
  place names by name. It is RED and naming real rows: `austin` and `texas` in
  two scopes, generic nouns (`revenue`, `platform`, `media`) in six more.
- **G3 was already failing before this work.** Verified by checking out the
  pre-change `brief.py` and `narrative_desk.py` against the SAME
  `web/articles.json`. It is a property of today's pool, not a regression. My
  first comparison used `git stash`, which also reverted `articles.json`, so it
  compared two different pools. Two numbers need the same ruler.
- G2 and G10 still do not exist. G7 still red, 18 of 55 feeds dead.

## 8. UI

`web/index.html:470`, `.brief-section` max-width 1280px to 1000px. The 1400px
values are site header and hero, left alone. **`web/index.html` is
hand-maintained: no script writes it**, the run only writes `brief.html` and
links back, so a pipeline run will not overwrite this.

## 9. The two orphaned repos: nothing to pull in

- `innovativehype-newsletter` (`9af9b01`, June 17) is the direct ancestor.
  `config.yaml`, `draft.py`, `research.py` are byte-identical; `publish.py`
  differs only by a refactor (`validate_config` + `build_email` + `send_email`
  became `send_email_publish`). The current repo is a strict superset.
- `innovativehype-discovery` (`12e8ff1`) is one file, `report.md`, 18KB, dated
  2026-05-14. No code, no corpus. Worth keeping for two things: a partial
  Substack archive index back to 2019, and a brand audit whose own conclusion
  is **"voice is the asset"**.

## 10. STILL OPEN

Carried and new:

- **The cut from 213 to an editable inventory is his.** Politics (48 dead) and
  personal (20 dead) are safe `enabled: false` sweeps. Media's 65 rows split
  32/33 and need reading.
- **G6 red**: two place-name scopes and six generic-noun scopes in the new file.
- **G2 and G10 need writing.** Still.
- **18 of 55 feeds dead**, so six of eight acceptance fixtures are still
  `ABSENT_FROM_FEED`. Unchanged since 08-21.
- **The paragraph still restates the headline.** Untouched since 08-23.
- **The IH brief page has still never been inspected in a browser** at any
  viewport. The width change above was made against the CSS, not against a
  render.
- `voice_terms.txt` is the third keyword layer and **was not converted**. It
  still scores by substring, and it still contains `texas`.

## 11. Repo state

**Pushed.** `757d868..b4cd59c` on `main`, 20 commits: the 9 below plus the 11
that had been unpushed since before this session, including `907d85e`.

```
8afeaa6  Semantic matching primitive, and the Substack archive joins the corpus
ce0016c  The angle extractor reads every voice source, and asks for the category
d160cb3  Clustering and angle eligibility match on meaning, not on words
46b070f  Signatures match on a prose subject, not on their keyword list
6a010ed  A second pass consolidates raw candidates into the inventory
add189e  G5 and G6 move onto the surfaces that now decide
2a25f05  Narrow the brief block on desktop from 1280px to 1000px
b4cd59c  The rebuilt inventory, and an instrument for cutting it
```

Dirty and deliberately left alone, unchanged from the morning: the five
`corpus/*.jsonl` scrapes, `runs/latest`, `web/articles.json`, `web/brief.html`,
`web/brief.md`, and the untracked `runs/2026082*/` directories. The `news` tmux
pane runs a hermes agent that is writing them.

**Note for whoever asks "what schedules the pipeline":** nothing in root's
crontab, no systemd timer, nothing in `/etc/cron*`. The `news` pane's hermes
agent is the only candidate. Killing that pane stops the engine and nothing
reports that it stopped.
