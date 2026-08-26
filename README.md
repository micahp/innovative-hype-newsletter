# Innovative Hype news engine

Builds the narrative brief at `web/brief.html` for the **Innovative Hype**
Substack (Micah Peoples). Reads ~55 RSS feeds, ranks the pool against a mined
voice profile, clusters what is left by subject, and has an LLM desk write at
most one card per cluster, taking only positions Micah actually holds.

The engine is judged on **whether the selection matches the person**, not on
whether the prose is clean. See `docs/CONTEXT-2026-08-23-SUMMARY.md` §WHY.

Current release: **v0.1.0**.

## How it works

```
feed_aggregator.py ─► web/articles.json ─► brief.py ─► web/brief.md
   (~55 RSS feeds,      (scored pool,        (clusters   brief-clusters.html
    scored + deduped)    ~3,000 articles)     by subject)
                                                  │
                                                  ▼
                                          narrative_desk.py ─► web/brief.html
                                          (LLM cards, one per      runs/<ts>/
                                           cluster, angle-gated)
                                                  │
                          acceptance_fixture.py ──┴── gates.py, test_type_gate.py
                          (8 named stories)           (NEWS-ENGINE-SPEC §6b)
```

`/root/.hermes/scripts/cron_news.py` runs all six in order every 120 minutes as
the hermes cron job `feed-aggregator`, and **exits non-zero if any stage or gate
fails**. The last two stages report problems loudly, so a non-zero exit usually
means a gate is red rather than the pipeline being broken. Check which.

### Selection matches on meaning, not on words

Clustering and angle eligibility used to count substring hits against
hand-written keyword lists. That put a Padres roster story and a WNBA
championship story into *Cities, housing and where America lives*, because that
list contained `texas`. Broadening such a list attaches everything; narrowing it
attaches nothing. A word is not a subject.

Signatures (`brief.NARRATIVE_SIGNATURES`) and angles (`angles.yaml`) each carry
a prose `subject` sentence naming the category, and matching is embedding cosine
via `scripts/embed.py`. Their `keywords` lists are documentation now and are read
by nothing.

### The voice profile

`angles.yaml` holds the positions the desk may take. An angle fires only on a
cluster whose subject matches it, and a card claiming an out-of-scope angle is
dropped. Built in two passes from `corpus/`:

```
scripts/extract_angles.py     4 sources, 2,772 posts -> angles.candidates.yaml
scripts/consolidate_angles.py 487 candidates -> 378 positions -> angles.yaml
scripts/angle_coverage.py     which of those can ever fire, against the live pool
```

Sources are the official X archive (originals only, weighted recent), two nitter
scrapes, and the 15 Substack posts. **These are developer tools. Nothing
schedules them**, and `pull_substack.py` in particular should stay manual.

## Files

| Path | Role |
|---|---|
| `scripts/feed_aggregator.py` | Fetch + score ~55 feeds → `web/articles.json` |
| `scripts/brief.py` | Deterministic layer: mine data points, cluster by subject |
| `scripts/narrative_desk.py` | LLM desk → `web/brief.html`, `runs/<ts>/` |
| `scripts/embed.py` | Embedding + cosine primitive, disk-cached |
| `scripts/gates.py` | The 11 gates in `NEWS-ENGINE-SPEC.md` §6b |
| `scripts/acceptance_fixture.py` | Micah's 8 named stories, reported loudly |
| `angles.yaml` | The position inventory. **Hand-edit this.** |
| `voice_terms.txt` | 59 subjects that boost an article's rank |
| `config.yaml` | Feeds and filters. Secrets in `config.local.yaml` (gitignored) |
| `corpus/` | Voice sources. `INDEX.md` and `README.md` describe each |
| `web/index.html` | The feed page. **Hand-maintained; no script writes it** |
| `docs/CONTEXT-*.md` | Day summaries. Newest first, read before changing anything |
| `.claude/skills/fail-loudly/` | Load before touching any pipeline input |

## Running

```bash
python3 scripts/feed_aggregator.py    # refresh the pool
python3 scripts/brief.py              # cluster it (~80s on ~3,000 articles)
python3 scripts/narrative_desk.py     # write the cards
python3 scripts/gates.py              # 11 gates; exits 1 if any fail
```

**Use the same interpreter the cron uses.** `cron_news.py` invokes each script
with `sys.executable`, the hermes venv at Python 3.11:

```bash
/usr/local/lib/hermes-agent/venv/bin/python3 scripts/brief.py
```

A package present on your PATH's Python says nothing about that one. numpy was
installed in one and not the other on 2026-08-24, and `brief.py` and
`narrative_desk.py` exited 1 every two hours for 19 hours while
`feed_aggregator.py` kept returning 0. `web/articles.json` stayed fresh, the desk
went dark, and the page went on serving its last good cards. Nothing looked
broken from outside.

## State as of v0.1.0

- **Gates 7 of 11.** G2 (boost-not-filter) and G10 (keep-cards) are specified and
  not implemented, and report FAIL rather than nothing. G6 is red on generic
  terms (`revenue`, `platform`, `media`) in the new angle scopes. G7 is red on
  17 of 55 feeds being down.
- **Acceptance fixture 2 of 8 reach the desk.** 4 more are in the pool but rank
  below the cutoff, and 2 are absent from every feed. That reframes the work
  from "find a feed" to "fix ranking".
- **`angles.yaml` has 378 positions and needs a human cut.** 213 can reach a
  story in the current pool; 165 cannot, most of them 2021-22 NFT-era and
  politics positions the feed structurally cannot serve. Prefer
  `enabled: false` to deleting rows: adding a source wakes them.
- **The paragraph still restates the headline.**
- **The brief page has never been inspected in a browser** at any viewport.

## Legacy: the Substack newsletter path

`research.py`, `draft.py`, `publish.py` and `pipeline.sh` are the original
2026-06 pipeline that drafted a newsletter and emailed it to Substack. They are
**not part of the news engine and nothing runs them here**: `pipeline.sh`
hardcodes macOS paths under `/Users/micah`. Kept because `publish.py` is still
the only route to Substack if the brief ever becomes an edition.
