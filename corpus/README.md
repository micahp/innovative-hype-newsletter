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
