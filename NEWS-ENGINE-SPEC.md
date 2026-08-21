# News engine spec: why the brief misses what matters, and what to build

Status: written 2026-08-21 after Micah rejected the LLM narrative desk output.
Read this before touching `scripts/brief.py` or `scripts/narrative_desk.py`.

This doc exists because the engine has now been rebuilt three times (category
buckets, narrative signatures, LLM desk) and each version failed the same way.
The failure is not the prompt. Everything below is measured against
`web/articles.json` as of the 2026-08-21T17:14 run (474 articles).

---

## 1. The verdict Micah gave

> "does this brief sound like what I would be writing as a headline or focusing
> on as a narrative?"

Then, when told no:

> "whathappened to flock? data centers? marijuana becoming illegal in texas?
> texas longhorns vs texas state? kanye west fireworks for all of the lights?
> X NBA players declaring for the WNBA draft? 40 year-old people playing in NCAA
> football? Sophie Cunningham saying that the WNBA commissioner should be fired
> next year? These are the things that I care about these are the things that
> our engine should be able to pull out as narratives and write a paragraph
> about. Why are we missing what matters? How do we get the pipeline on point?
> Without having me have to fine-tune an LLM on my tweets?"

That list is the spec. It is also the acceptance fixture (section 6).

## 2. The answer to "why are we missing what matters"

**Not because the stories are absent from the feed.** That was the assumed
answer and it is wrong for most of the list. Measured:

| Story Micah named | In `articles.json`? | What the pipeline did |
|---|---|---|
| Flock cameras | YES: "WPD won't replace stolen Flock cameras, citing public trust" (HN General) | dropped: no signature, no data point |
| WNBA | YES: "Newest WNBA Dildo Thrower Arrested and Banned" (Front Office Sports, 2,026 char body) | dropped: no signature, no data point |
| 40-year-olds in NCAAF | YES: "College Football Landscape Fueled by New Off-Field Drama" (FOS, 6,000 char body, **3 data points mined**) | dropped: no signature |
| NFL back to college | YES: "Judge Rules Players Can Go From NFL Training Camp Back to College" (FOS, 4,848 char body) | dropped: no signature, no data point |
| Data centers / Texas | YES: "Williamson County Greenlights $674M Blue Origin Development Deal" (Connect CRE Austin) | **mis-filed into "Creator economy consolidation"** |
| Sophie Cunningham | NO | genuinely absent, see 2.4 |
| Kanye fireworks | NO | genuinely absent, see 2.4 |
| Texas marijuana | NO | genuinely absent, see 2.4 |

Five of eight were in the pool and the pipeline threw them away. Fix the
selection before adding feeds.

### 2.1 The hard gate: 11% of the feed ever reaches the LLM

`scripts/brief.py` line ~236:

```python
if sig and points:
    enriched.append(...)
```

An article must match one of ten hardcoded signatures **and** yield a mined
data point, or it is discarded before the LLM sees anything. Measured on the
current feed:

```
total articles      474
noise-capped         14
eligible            460
has a data point     83
has a signature      89
BOTH (survives)      54   = 11%
```

89% of the feed is invisible to the narrative desk. The desk is not choosing
badly. It is choosing from 54 articles, and it never learns what it was denied.

### 2.2 The signature list is a topic allowlist

`brief.py:120-172` hardcodes ten signatures. The output can only ever be about
those ten things. There is no signature for a surveillance-vs-citizens story, a
college-eligibility story, a WNBA story, a music-moment story, or a
state-law story. Those narratives cannot be produced, at any prompt quality.

This is the same defect shape as a trust list keyed on a name: the allowlist
silently decides the answer, and nothing reports what it excluded.

### 2.3 Word-boundary matching silently drops every plural

`_kw_match` compiles `\bKEYWORD\b`. Verified:

```
_kw_match("camera", "stolen flock cameras")        -> False
_kw_match("track",  "license plate tracking")      -> False
```

The Flock story contains the exact concept the "AI surveillance creep"
signature was written for and scores zero hits on it. Word-boundary matching
was correctly adopted to stop "ban" matching "band"; the plural case was never
handled. Every singular noun in every keyword list has this hole.

Compounding it, generic keywords win ties. For the Blue Origin / Williamson
County story the signature hits are:

```
Creator economy consolidation    ['deal']       <- wins, +1 from the data-point boost
Prediction markets go mainstream ['odds']
Cities, housing and where America lives ['texas'] <- the correct bucket, loses
```

An Austin real-estate story lands in "Creator economy" on the word "deal".
`"deal"`, `"agent"`, `"contract"`, `"revenue"`, `"billion"`, `"platform"` and
`"media"` are all in the keyword lists and all match almost anything.

### 2.4 Four sports and culture feeds are dead, and nobody noticed

`articles.json` reports `feeds_ok: 31, feeds_fail: 17`. Among the failures:

```
ESPN
The Athletic
Bleacher Report
Sports Business Journal
Hacker News (AI)
Wired
Hypebeast, Complex, The FADER
```

Every general sports feed is down. The only surviving sports source is Front
Office Sports, which covers the *business* of sports. That is exactly why the
engine can talk about a $9.6B Seahawks sale but not about Sophie Cunningham
calling for the commissioner's job, or Longhorns vs Texas State. Same for
culture: Hypebeast, Complex and The FADER are down, so a Kanye fireworks
moment has no path in.

`feeds_fail` is written to the JSON and read by nobody. A 35% feed failure rate
is reported as a number in a file, never as a failure.

Also correct the record: the session notes claim Connect CRE Austin/Texas
failed. They did not. The latest run has Connect CRE Austin 10 articles and
Connect CRE Texas 8. Only Indie Hackers failed of the six additions.

### 2.5 A per-feed cap of 20 flattens beat coverage

Every feed contributes at most ~20 items. A dedicated beat feed cannot supply
depth, so a real thread on one beat never accumulates enough articles to
cluster. Combined with the "at least 2 keyword hits" purity gate, a genuine
one-off moment can never form a card by design.

### 2.6 The prompt is a sports-desk register, applied to a voice newsletter

`narrative_desk.py:_SYSTEM` was copied from the Legendary Picks narrative desk:

> "PLAIN NEWS LANGUAGE. Subject, plain verb, object. No idioms, no puns, no
> metaphors."

That rule exists in LP to *remove* an author's voice from sports cards. Applied
to Innovative Hype it removes Micah's. The result reads like a wire service:
"The creator economy is consolidating as startups raise big rounds."

This is real, and it is the *last* thing to fix. Rewriting the prompt against
an 11% sample of the wrong 54 articles just produces better-written cards about
the same ten topics.

---

## 3. What the engine is supposed to do

From Micah, across the session, in his words:

- "we pick out narratives and use articles to support that. and that's what the
  bucketing is for us to see if there's a recurring theme"
- "narrative focused. thats what theme means. not category focused."
- "a data point can tell a story on its own. But you have to ask a question
  what does that data point tell a story about."
- "you have to use kalshi and polymarkets just in as examples because not every
  datapoint matters. i'm sure with ranking it'll work out"
- "These are the things that I care about ... our engine should be able to pull
  out as narratives and write a paragraph about"
- "Without having me have to fine-tune an LLM on my tweets"

The last line is a constraint on the solution, not a complaint. The corpus at
`corpus/geoppls.jsonl` + `corpus/innovativehype.jsonl` is already the voice
signal. It should be used as **ranking and seed input**, not as training data.

## 4. The rules to build to

**R1. Nothing is excluded before the LLM sees it.** Delete the `if sig and
points` gate. The deterministic layer's job is to **rank**, not to **admit**.
Every eligible article enters the pool with a score; the desk chooses from the
top of a wide pool.

**R2. A signature is a boost, never a filter.** Keep the ten signatures as
weights. An article matching none of them keeps its base score. The set of
narratives the engine can produce must not be enumerable in advance.

**R3. Three ways to qualify, not one.** A story earns a card if it has any of:
- a **data point** that crosses a threshold (record, first, multi-year level,
  market-implied probability, structural imbalance, big directional money) —
  the existing JUST IN test, keep it
- a **quote**: a named person saying something contestable. "Sophie Cunningham
  says the commissioner should be fired" is a story with no number in it.
- a **moment**: a symbol, a first, a rule bent, a thing that is weird or local.
  The Flock camera draped in a flag is this. So is a 40-year-old playing NCAAF.

A number is one route in. It is currently the only route in, and that is why
every card is a funding round.

**R4. The tweet corpus is the seed list.** This is the answer to "without
fine-tuning". Legendary Picks already works this way: seeds are human-dictated,
adjacent queries derived. Extract entities and recurring subjects from
`corpus/*.jsonl` (Flock, Kalshi, Texas, Austin, WNBA, TikTok, oatmeal,
promotion and relegation) and use them as a **match-and-boost list** against
every incoming article. An article that touches something Micah has actually
posted about outranks one that does not. No training, no fine-tune, and it
updates itself every 2h because `poll_social.py` already runs on a cron.

**R5. Substring or stemmed matching, or an explicit plural list.** Whatever
form it takes, `camera` must match `cameras` and `track` must match `tracking`,
while `ban` must not match `band`. Add a regression test for both directions
before changing the matcher.

**R6. Kill generic keywords.** `deal`, `agent`, `contract`, `revenue`,
`billion`, `platform`, `media`, `network` match everything and decide ties.
Either remove them or weight them at a fraction of a specific term.

**R7. Feed failure is a failure.** `feeds_fail: 17` must break the run loudly,
not sit in a JSON field. Print the failing feed names to the cron log and fail
the acceptance check below when a named beat source is down. Fix ESPN, The
Athletic, Bleacher Report and Sports Business Journal, or replace them, before
claiming sports coverage exists.

**R8. Rewrite the prompt last, and rewrite it for his voice.** When the pool is
right, replace the LP sports register. The desk should be told the voice rules
that are actually observable in `newsletter.md` and the tweet corpus:
first-person and opinionated, power-and-ownership framing (who controls this),
urgency, contrarian angle, Texas and local flavor, no corporate neutrality.
"You write like Micah", not "you write like ESPN". Do not touch this before
R1 through R4 land, or you will be tuning prose about the wrong 54 articles.

## 5. Order of work

1. R7 (feed failures visible, sports and culture feeds restored)
2. R5 + R6 (matcher correctness, keyword hygiene)
3. R1 + R2 (delete the admission gate, signatures become boosts)
4. R3 (quote and moment qualifiers alongside data points)
5. R4 (tweet-corpus seed matching and boost)
6. R8 (voice prompt rewrite)

Do not skip to 6. Every prior rebuild skipped to 6.

## 6. The acceptance fixture

Commit these expected values before changing code, so a weakened check shows up
in git. Each of Micah's eight named stories, with the required outcome:

| # | Story | Required outcome |
|---|---|---|
| 1 | Flock cameras (surveillance vs citizens) | reaches the desk; produces a card or is declined *by the model*, never by a gate |
| 2 | Data centers | reaches the desk under a cities/infrastructure or AI-infra thread |
| 3 | Marijuana becoming illegal in Texas | present in the feed (needs a source, see R7) and reaches the desk |
| 4 | Texas Longhorns vs Texas State | present in the feed (needs a live sports feed) and reaches the desk |
| 5 | Kanye fireworks for All of the Lights | present in the feed (needs a live culture feed) and reaches the desk |
| 6 | NBA players declaring for the WNBA draft | present and reaches the desk |
| 7 | 40-year-olds playing NCAA football | already in the feed; must reach the desk (currently dropped despite 3 mined data points) |
| 8 | Sophie Cunningham on the WNBA commissioner | present (needs a live sports feed); qualifies via the **quote** route, not a number |

Report the fixture as a table on every run: for each item, one of
`ABSENT_FROM_FEED` / `DROPPED_BY_<gate name>` / `REACHED_DESK` / `CARDED`.
"Absent" and "dropped" are both failures, and they have different fixes. Today
the table reads five `DROPPED` and three `ABSENT`, and nothing reports it.

## 7. What not to do again

- Do not report "the desk works" from a run whose input was 11% of the feed.
  A clean run over a gated pool is a claim about the gate, not about the feed.
- Do not rewrite the prompt when the complaint is about *which stories*
  appeared. Prompt quality and story selection are different failures.
- Do not report a feed as failed without re-checking the latest run. Connect
  CRE was reported dead and has been supplying 18 articles.
- Do not use `git add -A` in this repo while another agent is working.
