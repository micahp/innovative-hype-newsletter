# 2026-08-23 — Innovative Hype news engine

## WHY WE ARE DOING THIS AT ALL

Read this part first. Every failure below is a failure to serve it.

Innovative Hype is Micah's Substack. The bottleneck has never been writing, it
is **finding what to write about**. The north star doc
(`market-research/00-INFRASTRUCTURE-NORTH-STAR.md`) names three pillars, and
this is pillar two: *a research and insights dashboard ranked by the voice
profile*. Not a news reader. Not a feed. A machine that reads the day and hands
back the four or five stories **he would have found himself**, with the angle he
would have taken, so his time goes into writing instead of hunting.

That is why the tweet corpus exists. `corpus/geoppls.jsonl` and
`corpus/innovativehype.jsonl` are not decoration and not training data, they are
the specification. `VOICE-AND-WORLDVIEW.md` was mined from ~33K of his tweets.
The brief is correct when a story in it makes him say "yes, that one", and wrong
when he has to say "what happened to Flock". The test is not whether the prose
is clean. It is whether the selection matches the person.

Two consequences that keep getting forgotten:

- **A well-written card about a story he does not care about is a failure.** It
  costs him the same attention as a bad one and teaches the engine nothing.
- **The engine is allowed to return fewer things.** Six honest cards beat
  thirteen padded ones. Filler is the specific thing that makes him stop
  trusting it, and once he stops opening it the whole project is dead weight.

Where it has drifted: three rebuilds in a row optimized the *writing* when the
complaint was about the *selection*. That is the recurring mistake, and it is
recorded in `NEWS-ENGINE-SPEC.md` §7 as the thing not to do again.

## WHAT HAPPENED TODAY

### 1. He was not looking at the brief

The single biggest finding. `web/brief.html` was being written by **two**
scripts: `brief.py:393` and `narrative_desk.py`. `cron_news.py` runs brief.py
first and the desk second, so the desk normally wins. The 15:54 UTC run failed
before producing cards (`runs/20260823_155424/` has only `input.json`), so
brief.py's page stayed live, with a fresh timestamp on it.

That page was the **deterministic v1 he rejected on 2026-08-21** ("i dont like
this brief. at all."). Its five headlines were the hardcoded signature names:

```
Cities, housing and where America lives
Can we trust the machines we're building?
The creator economy is consolidating
The AI data layer is printing money
Media power and who owns it
```

So "it still feels off" was literal. Two days of desk work had never been on
screen. Fixed: brief.py now writes `brief-clusters.html`, the desk owns
`brief.html` alone (`dc856bb`).

Compounding it, the page provenance line had read `run ?` since the render step
was added, because `render_brief_html` loads `meta.json` and `main()` wrote it
afterwards. Not being able to tell which run made the page is exactly what let
this sit for two days. Fixed (`ae6eed0`).

### 2. Eight headlines, one sentence

The desk output that *did* generate had a real defect. From the 13:52 UTC run,
the clause after the turn in each of the eight headlines:

```
while  the county gives up the tax base.
but    the real cost is to children's privacy.
but    the real story is the transfer portal's impact.
but    who benefits?
but    the safeguards leave users exposed.
and    the NBA's ownership shuffle continues.
and    that's the point.
but    the real winners are the leveraged traders who got out in time.
```

Eight of eight in one mold. My fault from the 08-21 pass: I banned the abstract
second clause and handed the model exactly one approved replacement (the
concrete contrast, with the Zuckerberg castle line as the example), so it used
that template eight times. The prompt before mine produced thirteen of thirteen
as subject-verb-object. **A rule phrased as a constraint on a shape teaches
that shape.** Same lesson as `feedback_the_outlet_is_not_the_story.md`.

Three symptoms fell out of the one cause:

- **One posture.** Every card was the debunker: official story X, real story Y.
  His voice also does flat enthusiasm and bare shocking facts.
- **Half the turns said nothing.** "but who benefits?", "and that's the point",
  "and the NBA's ownership shuffle continues" are the banned abstractions in a
  concrete costume, and `repair_narrative()` missed all of them because it only
  knew the "is a reminder that" phrasing.
- **The paragraph restated the headline.** Card 1 said 26 football fields in the
  headline, 26 football fields and 1.3M sq ft in the data point, 1.3M sq ft and
  $650M in the paragraph. One fact three times, which is why a card reads thin
  even when the story is good. The LP rule for this is already in the skill and
  every card broke it.

Fixed: headline shapes are now **assigned per cluster and rotated**
(FLAT / CONTRAST / QUESTION / FACT / NAMED) rather than requested, and a card in
the wrong shape is a failed card. `repair_narrative()` learned that the
disguised abstractions are **cut, not pivoted**: "X is a reminder that Y" keeps
Y because Y is the claim, but "X, but the real story is Y" keeps X, because
there Y is the shrug. Keeping the far side of the latter produced fragments
like "The transfer portal impact."

Current output, one run, no cherry-picking:

```
Jeff Bezos' Blue Origin is set to build a 26-football-field plant in Hutto,
  Texas, while the county gives up the tax base.
TikTok pays a $400 million fine for children's privacy violations while
  ByteDance keeps collecting data on kids.
Who will be Alabama's starting quarterback this season?
Angel Reese's career-high 31 points also made Dream history.
Binance opens the door to AI agents that can trade crypto for you, while users
  shoulder the oversight.
The AI data gold rush is on, as Micro1 hits $500M gross run rate while Nvidia's
  compute-as-an-asset-class strategy raises eyebrows.
Who actually owns the Timberwolves now?
Flock's new AI police tool can track drivers without a name or license plate,
  putting surveillance power in the hands of law enforcement.
```

Shapes vary now. Selection still has the open defect below.

## STILL OPEN

- **The type gate.** "Who will be Alabama's starting quarterback this season?"
  and "Angel Reese's career-high 31 points" are the athlete-doing-their-job type
  the prompt tells the model to decline. It declines unreliably. This needs a
  deterministic classifier the way the headline bans did, not another prompt
  sentence. Same lesson, third time: **a negative instruction is not a gate.**
- **The paragraph still restates the headline.** Not addressed today.
- **Feed coverage.** 17 of 48 feeds dead as of 08-21, including ESPN, The
  Athletic, Bleacher Report and Sports Business Journal, which is why sports can
  only be seen as money. Six of the eight stories in the acceptance fixture are
  still `ABSENT_FROM_FEED`.

## NOTES FOR NEXT SESSION

- `cron_news.py` runs the **repo** scripts (`/root/innovative-hype-newsletter/scripts`),
  not the copies in `~/.hermes/scripts/`. The copies are vestigial. The skill
  still says to sync them; that instruction is stale for this pipeline.
- The news pane agent is on **ox-alpha** now, not deepseek.
- `NEWS-ENGINE-SPEC.md` is the doctrine doc, pointer at `SKILL.md:159`.
- `/root/TASK-llm-model-fallback.md` is written and unstarted: model fallback
  chain for every LLM cron, ox-alpha primary. Blocking finding in it: ox-alpha
  has mandatory reasoning, so LP's `reasoning_effort: none` default is a hard
  400 on every call.

## COMMITS

```
dc856bb  Stop brief.py overwriting the live page; assign headline shapes
ae6eed0  Write run meta before rendering, enforce the card cap in the renderer
```

---

# PASS 2 (afternoon/evening 2026-08-23)

The morning pass is above and still accurate. This is what happened after it.
The §WHY section at the top is unchanged and still the thing to read first.

## THE ONE FINDING THAT MATTERS: it is the RANKING, not the sourcing

Micah asked it directly: "is our rankings for stories in innovative hype off or
are we not sourcing the right stuff yet". Measured against the live
`articles.json`, seven of the eight topics he named on 08-21 are in the feed
right now. Here is where they rank out of 1,512 scored articles:

```
TOPIC                            IN FEED   BEST RANK
Flock / surveillance cams              5      #14
Data centers                          15      #18
Elon + Cursor                         11      #21
Lakers / Kushner                      20      #38
Zuckerberg                             5      #62
Palantir / zero data retention         3     #520   <- named by hand, buried
Texas weed / THC ban                  11     #391   <- named by hand, buried
Enhanced Games                         0       -    genuinely absent
```

His own read from 08-21 was right: "we had good enough articles in the corpus
to have a better brief."

**Mechanism.** `score_article()` is `source_tier + recency_decay + pillar_fit`.
`feed_aggregator.py` imports `CORPUS` on line 34 and never uses it in scoring.
The tweet corpus only becomes *bucket voice weights* inside `brief.py`, applied
after clustering, to buckets that already exist. So his voice has zero
influence on which articles rank, and by the time it gets a vote the buried
stories are already gone. This is also why a TechCrunch Disrupt ticket ad could
be TOP 1: nothing in the score asks whether he would care.

**The fix is the fourth score term**, and it is what the angle inventory is
for. Not built yet.

## THE CORPUS WAS NOT BEING COLLECTED

Two bugs that hid each other for six days:

1. The cron runs `~/.hermes/scripts/poll_social.py`, a COPY that had drifted.
   Its account list was hardcoded `["Polymarket", "Kalshi"]`. The repo version
   has `ACCOUNTS = ["Polymarket", "Kalshi", "geoppls", "innovativehype"]`. His
   own two accounts were never in the cron's list.
2. `CORPUS` defaults to `dirname(__file__)/../corpus`, which from there is
   `/root/.hermes/corpus` — a directory nothing reads. The pipeline reads
   `/root/innovative-hype-newsletter/corpus`. Six days of Polymarket/Kalshi
   posts landed where no consumer opens them, and the job reported `ok` on all
   74 runs.

Fixed: `~/.hermes/scripts/poll_social.py` is now a shim that execs the repo
script with `LP_CORPUS` pinned to the repo. A copy of a script is a second
source of truth that nothing compares.

**Correction to a claim I made mid-pass:** I reported `geoppls.jsonl` ended at
Jun 4 2025. That was a string `max()` over unparsed dates, which sorts "Nov"
above "Jun". Parsed properly the file spans 2020-08-01 to 2026-08-23. The two
bugs above are real and were read off the code; the staleness number was not.

## THE ARCHIVE WAS ON THE BOX THE WHOLE TIME

```
/root/Downloads/E:\Users\micah\Downloads\twitter-2026-05-17-*.zip   (9.8 GB)
  data/tweets.js -> 33,143 tweets, 2016 .. 2026-05-17
                    5,517 original | 19,590 replies | 8,036 retweets
```

This is what `market-research/VOICE-AND-WORLDVIEW.md` was mined from. Extract
`data/tweets.js` only; the rest of the zip is media. Parsed copy lives in the
session scratchpad; `extract_angles.py` reads it via `IH_ARCHIVE_JSON`.

Nitter backfill merged on top: geoppls 529 -> 600, innovativehype 163 -> 835.
geoppls hits the nitter cache wall around 241 pages back, which does not matter
because the archive covers everything before May 2026.

## ANGLE INVENTORY

v1 was extracted from ~260 nitter posts and came back **article-shaped**: 62
rows, most of them a fact about one story ("The housing market in Galveston TX
is in oversupply") rather than a position applicable to next week's news.
Micah: "it's not generic enough, it's too specific to the articles."

The rebuild reads the archive with two rules, both in `extract_angles.py`:
**originals only** (replies are conversation, retweets are endorsement, neither
is a stated position in his own words — mixing them in is how v1 ended up
asserting things he had quoted), and **weighted to recent** (2025-26 taken
whole, older years sampled; a position he held in 2021 and still posts about
survives by repetition).

Still open: the final list needs his cut, and then the wiring into
`score_article()`.

## THE BRIEF IS NOW A RUNNING FEED

Micah: "it's kinda more like the legendary picks one where I just want it to be
timestamped... let's not limit the number of cards. I really just wanna see
what we got. and then I should cut from that."

Cards are keyed by their source-link set. First appearance stamps `first_seen`;
later runs update the text in place and keep the original stamp, so the feed
reads "18h ago" instead of re-dating yesterday to now. 72h expiry, newest
first. Three caps removed: the renderer's 8, the prompt's "no more than 8 cards
total", and the one-off keep which was taking **3 of 163** seeded one-offs (now
12). One run went 7 cards to 15. The page also shows what the gates DECLINED,
with reasons, because he can only cut from what he can see.

## OTHER FIXES THIS PASS

- **Starvation.** The desk was handed **300 characters** of each article. For
  The Verge's Nvidia piece that is a corncob joke and a Napoleon gag and none
  of the argument. Leads now get 1800, tail 400. Separately
  `feed_aggregator.py` skipped its full-text fetch at 400+ chars of body, and
  partial `content:encoded` feeds clear that; threshold is 2500 and it keeps
  the longer of feed and fetch.
- **Wrong angle is not hallucination.** "Nvidia... while the average person
  can't afford a home" was a real position of his welded to the wrong subject.
  The obvious grounding check would have killed the *right* angle too, since
  "you'll rent compute forever" is not in the article either. Scope, not
  presence. Given 4000 chars of the real article the desk declines rather than
  inventing.
- **cluster_index is a claim.** Trusted on sight, it filed Flock surveillance
  under "The AI data gold rush" once the prompt grew. Now accepted only when
  its content score agrees.
- **Roster churn + duplicates** (`82dae32`). Recruiting/transfer/staff-move
  vocabulary added to the type gate, power veto still winning. Same-story
  duplicates collapse on headline SUBJECT, because two Good Good Golf
  paraphrases shared only "good" and "golf" out of seven tokens each.

## LEGENDARY PICKS, FOUND WHILE STEERING CODEX

Codex had ended its session; it never started `/root/TASK-llm-model-fallback.md`.
It was tracing World Cup commit provenance instead. Re-steered onto RotoWire.

**Props ingest is parked and nothing says so.** `legendarypicks-props.timer` and
`-prod.timer` are active+enabled with `next=n/a`, last fired 2026-08-21 11:08,
services inactive and not hung. `monitor_props_freshness` reports dev 18.8h and
prod 42.6h stale every 30 min and exits non-zero. Commit `43791af` deliberately
removed the self-healer citing "while scheduled props work is disabled", but no
handoff records that decision. Nobody can tell from the system whether props is
intentionally off or quietly broken. Untouched: restarting prod is Micah's call.

## OPEN AT END OF PASS 2

- Angle list needs his cut, then wire it into `score_article()` as the fourth
  term. **This is the highest-leverage item on the project** and it is what
  moves the Texas hemp lawsuit off rank 391.
- The paragraph still restates the headline.
- Six of eight acceptance-fixture stories still `ABSENT_FROM_FEED`; 17 of 48
  feeds dead including ESPN, The Athletic, Bleacher Report, SBJ.
- LP props: decide and record whether it is off on purpose.

## COMMITS, PASS 2

```
dc856bb  Stop brief.py overwriting the live page; assign headline shapes
ae6eed0  Write run meta before rendering, enforce the card cap in the renderer
2949cae  Type gate: decline performance-only cards in code, not in the prompt
716fd3f  LP card shape; Brief above Top News; gate verdicts persist
282d91d  Feed the desk the actual article; verify the model's cluster claim
757d868  Angle inventory: opinions come from an enumerated, scoped list
1ca9a8c  Brief becomes a running timestamped feed, uncapped
82dae32  Close the two feed defects: roster churn and same-story duplicates
```

Pushed through `757d868`; `1ca9a8c` and `82dae32` are local.
