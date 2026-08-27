# Corpus — @Polymarket & @Kalshi "JUST IN" posts

Pulled 2026-08-17 via nitter (tiekoetter.com instance, Anubis PoW solved
in-process by `scripts/pull_corpus.py`).

## Files

| File | Account | Posts | Date range | Notes |
|---|---|---|---|---|
| `polymarket.jsonl` | @Polymarket | 784 | Aug 6 → Aug 17 2026 | ~8 days — instance cursor ends here (see below) |
| `kalshi.jsonl` | @Kalshi | 737 | Jul 17 → Aug 17 2026 | full 31 days |
| `justin.jsonl` | both | 1098 | Jul 17 → Aug 17 2026 | subset whose text starts with "JUST IN" |

Each line is JSON: `{"text", "date", "id", "account"}`. `id` is the tweet
status id (snowflake). `date` is the nitter-rendered absolute UTC timestamp.

## JUST IN breakdown

- Polymarket: 431 JUST IN posts (~8 days of coverage)
- Kalshi: 667 JUST IN posts (full month)
- 1098 total, 0 duplicates, 0 blank rows.

## Coverage caveat (important)

Kalshi pulled the full 31-day window. Polymarket stopped at ~Aug 9 because the
tiekoetter.com instance's timeline cache for @Polymarket ends after ~42 pages
(~780 posts). Polymarket posts ~100/day vs Kalshi's ~24/day, so the same
instance holds a much shallower window for the higher-volume account.

Other nitter instances were probed and are dead or challenge-gated:
nitter.net (HTML 0-byte blocked; RSS caps at 20 posts), privacyredirect
(timeout), poast.org / space / lightbrd / catsarch / kareem.one (403),
privacydev / kavin.rocks (502), 1d4.us / unixfox / mint.lgbt / bus-hit.me /
fdn.fr / ktachibana.party (NXDOMAIN), woodland.cafe (refused).

To backfill the missing ~3 weeks of Polymarket, the options are: a paid X API
(twitterapi.io, ~$0.15/1k reads), or poll nitter RSS every ~2h going forward
to accumulate (the approach the LP news engine already uses for its X feeds).

## Reverse-engineering notes (what these posts actually are)

- The "JUST IN:" prefix is the house style for a breaking-news aggregation
  desk, NOT original reporting and NOT market resolution.
- Only 14/1098 posts carry inline source attribution ("— Bloomberg",
  "— Reuters", "— Axios", "— WSJ", "— CNN"). The rest state the claim bare.
- Traced examples reveal the true sources are quote/clip surfaces: podcasts
  (Lex Fridman, Pomp), business TV (CNBC Squawk Box), earnings calls, official
  statements, and high-follower finance accounts — not news wires.
- A "JUST IN" post is typically a single provocative sentence about a named
  person/entity making a counterintuitive claim, reformatted with no link.

## Regenerate

```bash
cd /root/innovative-hype-newsletter
python3 scripts/pull_corpus.py --days 31 --out-dir corpus
```

## STATUS UPDATE 2026-08-27 — the free nitter fleet is dead or dying

The `social-corpus-poll` cron froze all four corpus files at **2026-08-24**
because tiekoetter began answering **HTTP 429** on every account surface
(`/<account>` HTML and `/<account>/rss`, both verified; its own front page
still served 200, proving the block is endpoint-scoped, not IP-wide).
Re-written `scripts/poll_social.py` probes transports ONE time each per run,
in this order, with no internal retries:

| Transport | Result on 2026-08-27 |
|---|---|
| nitter.tiekoetter.com | 429 on account pages AND rss (front page 200) |
| nitter.net | **410 Gone** — the instance died between Aug 17 and today |
| xcancel.com | RSS 400; root page displays X Corp **cease-and-desist notice dated Aug 24, 8PM EST** — service ending |
| twiiit.com | 421 Misdirected Request |

Conclusion: public free nitter access is being terminated (legal action by
X Corp), not merely rate-limited. Waiting will not recover it. The remaining
options, requiring a decision above this repo:

1. **Paid X data API** (e.g. twitterapi.io, ~$0.15/1k reads; polling these
   4 accounts every 2h ≈ 1.5k reads/month ≈ pennies, plus one backfill).
   NOT done automatically — costs money and needs signup, so it awaits
   approval.
2. Some other sanctioned source for these accounts' posts.

Until one lands, `poll_social.py` keeps trying the fleet each run (recovery
would be picked up automatically) and — the part that must never regress —
**prints per-account newest-post age on EVERY run and exits non-zero when
any account exceeds 48h stale**, so staleness can never again hide inside a
red cron dot nobody opens.
