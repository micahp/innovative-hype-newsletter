# Innovative Hype — Newsletter Pipeline

Automated AI-news research → draft → publish pipeline for the **Innovative Hype**
Substack (by Micah Peoples). Scrapes RSS feeds, filters and dedupes the day's
stories into a digest, builds a writing prompt, and (via a Hermes cron agent)
generates and publishes the edition.

> **Architecture & roadmap** for how this fits the larger Innovative Hype
> operating infrastructure lives in the `market-research` repo
> (`00-INFRASTRUCTURE-NORTH-STAR.md`). This README covers just how to run the repo.

## How it works

```
research.py ──► digest.json ──► draft.py ──► newsletter.md ──► publish.py ──► Substack
  (scrape +      (top ~20        (prompt        (draft /          (email
   filter RSS)    stories)        template)      final text)       post)
        └────────────────── pipeline.sh orchestrates ──────────────────┘
```

1. **Research** (`research.py`) — fetches the RSS feeds in `config.yaml`
   (3 tiers: major AI news, research/labs, community), keyword-filters for AI/ML
   relevance, drops anything older than `max_age_hours`, deduplicates by
   title/summary, and writes the top `max_articles` to `digest.json`.
2. **Draft** (`draft.py`) — turns the digest into `newsletter.md`, a structured
   **prompt** (source articles + brand-voice + structure instructions). This is a
   prompt template, *not* the final copy.
3. **Generate + Publish** — the Hermes cron agent reads `newsletter.md`, writes
   the final edition with its LLM, and `publish.py` emails it to the Substack
   "post by email" address.

## Files
| File | Role |
|---|---|
| `config.yaml` | Feeds, keywords, filters, output paths, brand/template settings. **Secrets go in `config.local.yaml`** (gitignored). |
| `research.py` | Stage 1 — RSS scrape, filter, dedup → `digest.json` |
| `draft.py` | Stage 2 — digest → `newsletter.md` prompt template |
| `pipeline.sh` | Orchestrates stages; modes below |
| `publish.py` | Stage 3 — emails the edition to Substack _(referenced by `pipeline.sh`; add/restore before using `--publish`)_ |
| `digest.json` / `newsletter.md` | Latest run artifacts (checked in as examples) |

## Setup
```bash
pip install feedparser pyyaml
cp config.yaml config.local.yaml   # then fill in Substack address + SMTP creds
```
`config.local.yaml` holds the Substack posting address and SMTP credentials and
is gitignored — never commit it.

## Running
```bash
./pipeline.sh --dry-run     # research + draft only, no publish
./pipeline.sh               # research + draft (manual publish step)
./pipeline.sh --publish     # full run, publishes to Substack
./pipeline.sh --cron-research   # Stage 1 only (JSON digest) — used by Hermes cron

# or run stages directly:
python3 research.py --config config.local.yaml --output digest.json
python3 draft.py    --config config.local.yaml --digest digest.json --output newsletter.md
```

## Current limitations / next steps
- **Voice is generic.** `draft.py` hardcodes a mainstream "conversational AI-news"
  brand voice. Planned: drive it from the mined voice/worldview profile
  (`market-research/VOICE-AND-WORLDVIEW.md`).
- **AI-only sourcing.** Feeds/keywords cover AI/ML; the broader Innovative Hype
  beats (web3/creator ownership, sovereignty, decentralized social, Texas,
  sports-business) aren't yet represented.
- **Ranking is keyword + recency**, not thesis/worldview-aware.
- **No dashboard UI** — output is `digest.json` + a prompt; a "what to write +
  angle" view is planned.

See the north-star doc in `market-research` for the full plan.
