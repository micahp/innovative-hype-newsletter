# 2026-08-21 DAY SUMMARY — Innovative Hype news engine

Previous: [2026-08-19 summary](/root/legendarypicks/docs/CONTEXT-2026-08-19-SUMMARY.md) (Legendary Picks day). This
summary covers the **Innovative Hype newsletter** (`/root/innovative-hype-newsletter`), where all
of today's work happened. Written so a killed session loses nothing: §A is what changed and is
live, §B is what is still open with acceptance criteria, §C is the honest scoreboard.

The engine was rebuilt end-to-end today: full-article layer → narrative desk (LLM) → R1-R8 spec
fixes → headline/stability fixes → gates → promo-class filter. All 9 commits landed on `main`,
**nothing pushed** (memory: no push unless asked).

---

## §A What shipped (9 commits on `main`, live in the cron)

All commits are on `main` (not pushed), newest first. The cron chain
(`~/.hermes/scripts/cron_news.py`) runs scripts straight from the repo, so these are **live next
tick** — no `cp` needed for the cron_news path.

| commit | what landed |
|---|---|
| `e1f0ffd` | Full-article text layer (`content:encoded` + trafilatura fetch for teaser feeds) + rank-true ordering everywhere (hero, category grids, Top News) |
| `1b128b5` | Voice-weighted narrative buckets + close feed gaps (sports/Texas feeds restored) |
| `c8acf6d` | LLM narrative desk (LP pattern): deterministic clusters + mined data points → ONE DeepSeek call → strict JSON cards → versioned runs |
| `e60525b` | R1-R8 pipeline fixes: admission gate removed, plural-aware matching, keyword hygiene, honest fixture |
| `a84fc6a` | Voice prompt (write like Micah), seed-boost, keyword hygiene — cards finally sound like him |
| `068370e` | Selection-first: theme-first desk, fixture honest to 3/8, one-off cap + same-shape dedup |
| `18e382f` | Card↔source alignment: content-based, never positional (model source_ids go stale after re-alignment) |
| `06f1630` | Gates (NEWS-ENGINE-SPEC §6b): 9/9 passing, wired into cron |
| `e668621` | **Promo/self-promo noise patterns** — event-ticket marketing, outlet self-promo, vendor partnership announces capped out of Top News + brief |

### The day's through-line (why the commits build on each other)

1. **Selection was broken before writing existed.** Deterministic layer admitted only 11% of the
   feed; five of the eight stories Micah named were in the feed and thrown away by a gate.
   `e60525b` opened the gate (signatures are boosts, never filters) — every non-noise article
   enters the pool, three ways to qualify (data point / quote / moment), tweet corpus is the seed
   list, `\bcamera\b` finally matches "cameras".
2. **Then the writing was wrong.** Micah: "does this brief sound like what I would be writing?"
   → no. `a84fc6a` + `068370e`: voice prompt rewritten (first-clause headlines, short punchy
   paragraphs, decline non-juicy, no same-shape cards), theme-first selection, one-off cap.
3. **Then regeneration was unstable** (good headline became bad): `pool_key` was hashing volatile
   identity; keep-good-cards + stable pool_key fixed it (`18e382f` also fixed wrong source links).
4. **Micah: "you added todos but instead there should be gates"** → `06f1630`: NEWS-ENGINE-SPEC
   §6b gate table (G1-G11) + `scripts/gates.py`, all wired into the cron, exit 0 only when all pass.
5. **Micah: "is this really top news? top 1?"** on the TechCrunch Disrupt promo → `e668621`.

### The promo-class fix (the last commit, today's final work)

A TechCrunch "Last chance: Save up to $300 on your Disrupt 2026 ticket" ad anchored Top News #1
(9.45) because promo copy hits the same pillar keywords as real news. Fix + full-class sweep:

| item | source | before | after |
|---|---|---|---|
| "Save up to $300… Disrupt 2026 ticket" | TechCrunch | 9.45, Top #1 | 3.44, NOISE |
| "Texas Tribune Festival 2026: Our full lineup" | Texas Tribune | 3.41, LIVE | 0.41, NOISE |
| "Partnering with CodeAI…" | OpenAI Blog | 7.50, LIVE | 1.50, NOISE |

New NOISE_PATTERNS: last chance/early bird/act now/limited time, save up to $N/discount/coupon/
promo code, register now/rsvp/ tickets on sale, "our full lineup"/"our annual festival"/
"join us at"/"see you at", "partnering with"/"partnership with"/"teaming up with". Each pattern
precision-scanned to exactly 1 genuine hit across all 500 articles before committing. One
false-positive caught and dropped during the sweep: bare `admission` (caught "shares honest
admission" — a confession, not event entry).

**Effect on the brief:** exactly one card changed — the "AI data layer is printing money" section
lost the Disrupt promo as lead + bullet, now leads with the real Micro1 $500M story. Other 4
sections byte-identical; Tribune Festival and CodeAI never appeared in any committed brief (verified
across git history).

## §B Still open

### B1 The 3 ABSENT stories need feeds (not prompts)
FIXTURE says ABSENT_FROM_FEED: **Kanye fireworks** (no music/culture feed), **Sophie Cunningham**
(no WNBA-quote feed), and Longhorns moved ABSENT → DROPPED_BY_GATE today (a Texas sports feed now
carries it but it ranks below the one-off cap). If Micah names a story and the fixture says ABSENT,
the fix is a feed, never the prompt. **Do not claim coverage the fixture doesn't show.**

### B2 The 2 DROPPED stories (ranked below one-off cap)
NBA→WNBA draft and 40-yr NCAAF are in the feed with seed hits + qualifiers but lose the 3-slot
one-off cap to higher-scoring WNBA stories. Seeded-first selection helped but all one-offs are
seeded now, so it falls to raw score. Accepted per Micah ("it's ok if there are a few narratives
left out") — but they're reported loudly, not silently.

### B3 Regeneration cost (2h cron = up to 12 LLM desk calls/day, ~$0.05 each)
Micah asked "how often is this regenerating?" — offer 6h/12h/manual; don't silently keep 2h.

### B4 Zuckerberg castle / Kushner-Lakers / Palantir / Elon-Cursor
In his tweets, partially in the feed, but the contrast framing (the actual story) drops out in
ranking or needs the right source. Kushner-as-buyer must be named in a Lakers card.

### B5 FEED-GAP-MAP.md is partially stale
Says Connect CRE failed (it's live now). Regenerate it against the current 55-feed pool + current
tweet corpus.

## §C Honest scoreboard (as of the last run, 2026-08-21 ~21:00 UTC)

- Fixture: **3/8 reached the desk** — Flock ✓, Data centers/Texas ✓, Marijuana/Texas ✓; Longhorns
  DROPPED, NBA→WNBA DROPPED, 40-yr NCAAF DROPPED, Kanye ABSENT, Sophie ABSENT.
- Gates: **9/9 passing** (`python3 scripts/gates.py`), wired into cron; fixture exits 1 on any
  ABSENT/DROPPED so failures are loud in the cron log.
- Feeds: 32 ok / 23 fail (normal now; failures are loud, not silent).
- Top News #1 is now Micro1's $500M AI data story (real news), shelf and brief free of promo
  language.
- Skill updated: `innovative-hype-newsletter` patched (promo-gap pitfall, three-artifact brief
  check, cron_news no-cp correction) + `references/ranking-promo-gap.md` written.

## Docs to load next session

- `NEWS-ENGINE-SPEC.md` — the spec + §6b gate table (the de-facto task doc, updated today)
- Skill `innovative-hype-newsletter` (v1.0.0, patched today with v4/v5/v6 + promo pitfalls)
- `FEED-GAP-MAP.md` (regenerate — stale)
