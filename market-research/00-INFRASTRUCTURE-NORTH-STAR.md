# Innovative Hype — Operating Infrastructure (North Star)

_Created 2026-05-25. This reframes the market-research effort: it's no longer a
one-off study, it's the planning hub for how Innovative Hype operates._

## One-liner
An integrated system where an **autonomous AI research lab** feeds a
**voice-aware insights dashboard**, which powers **article/newsletter writing** in
your worldview — all tracked in **cloud project management**.

## Reality check (what already exists)
A working **v1 of pillars 2 + 3 already ships**: the `innovative-hype-newsletter`
repo scrapes news, drafts, and publishes to Substack on a Hermes cron. The job
now is mostly **evolution, not greenfield** — wire in the voice/worldview brain,
broaden beyond generic AI-news, and add a dashboard + real PM.

---

## The three pillars

### Pillar 1 — Ops & Project Management *(adopt: Plane, open source)*
Tracks every project Innovative Hype is building; doubles as the **newsletter
pipeline** (idea → draft → review → scheduled → published).
- **Decision:** use **Plane** (self-hosted via Docker — same pattern as
  InnovativeHypeChat). Don't build this.
- **Status:** not started. Greenfield (adopt + configure).

### Pillar 2 — Research & Insights Dashboard *(evolve existing + build UI)*
A dedicated view of news/research, **ranked and framed by the voice-and-worldview
profile**, that tells you *what to write about and the angle* — then assists the draft.
- **Already exists (engine):** `innovative-hype-newsletter` — `research.py`
  (17 RSS feeds → filter → dedup → `digest.json`), `draft.py` (digest → prompt
  template `newsletter.md`), `pipeline.sh`, Substack publish. One edition live.
- **The gap to close:**
  1. **Voice/worldview not wired in.** `draft.py` hardcodes a generic
     "conversational AI-news" brand voice. Replace with the mined profile
     ([`VOICE-AND-WORLDVIEW.md`](VOICE-AND-WORLDVIEW.md)).
  2. **Sources are AI-only.** `config.yaml` keywords/feeds cover AI/ML. The
     profile's beats are broader — web3/creator ownership, sovereignty/sound
     money, decentralized social, Texas, sports-business. Expand feeds + keywords
     from profile §5.
  3. **Ranking is keyword-match + recency.** Add **thesis-aware scoring**: rank up
     items touching your §3 theses and amplified-accounts seed list.
  4. **No dashboard UI.** Today output is `digest.json` + a draft prompt. Build a
     view that surfaces "what to write + your angle" cards.
- **Lives in:** the `innovative-hype-newsletter` repo.

### Pillar 3 — Automated AI Research Lab *(evolve existing; → desktop)*
"The AI does the research itself," Anthropic-style.
- **Already started:** the Hermes-cron `--cron-research` flow IS the v1 lab
  (RSS scrape → digest → agent drafts → publish).
- **Evolution:** more agentic (follow links, read full articles, cross-reference,
  synthesize a POV — not just RSS summaries), and **move to the desktop** (2x RTX
  2060, 32 GB) so it can run heavier local models + the twitterGPT voice model.
- Can reuse InnovativeHypeChat's Ollama RAG + OpenRouter for the LLM layer.

---

## The shared "brain"
Both the dashboard's ranking and the draft-writing pull from one editorial layer:
- **Voice & Worldview profile** ([`VOICE-AND-WORLDVIEW.md`](VOICE-AND-WORLDVIEW.md))
  — topics, stances, theses, tone, source heuristics. *This is the missing input
  to the existing pipeline.*
- **twitterGPT voice model** (optional) — finetuned style for first-draft phrasing.
- Division of labor: dashboard/brain decides *what + why + angle*; voice layer
  decides *how it sounds*.

---

## Assets already in place (reuse, don't rebuild)
| Asset | What it gives us |
|---|---|
| **innovative-hype-newsletter** (research.py / draft.py / pipeline.sh, Substack, Hermes cron) | Working pillar 2+3 v1 — the engine to evolve |
| **InnovativeHypeChat** (LibreChat + OpenRouter + Ollama RAG, Dockerized) | LLM access + RAG + deploy pattern for lab/dashboard backend |
| **Voice & Worldview profile** (this folder) | The editorial brain / ranking config — *not yet wired into the pipeline* |
| **twitterGPT** (`/root/twittergpt`) | voice mining + finetuning + data tooling |
| **market-research corpus** (01–08) | audience/market knowledge for who the newsletter serves |
| **gppls-daily** | content assets (images, songs) |
| **Desktop GPUs** | runs the research lab + finetuning off-cloud |

---

## Data flow (target state)
```
Pillar 3 (research lab, desktop) ── scrape + read + synthesize ──►
        │   (sources seeded from VOICE profile §5: feeds, accounts, keywords)
        ▼
Pillar 2 (insights dashboard) ── score by thesis/worldview, frame angle ──►
        │   "Here's what to write about, and your take on it"
        ▼
   assisted draft (voice model + brand voice) ──►
        ▼
Pillar 1 (Plane) ── editorial calendar: draft → review → schedule → publish (Substack)
```

---

## Decisions locked
- **No new repo** — work in **market-research** (planning + brain) and
  **innovative-hype-newsletter** (engine + dashboard).
- **Plane** for project management (open source, self-hosted).
- **Hybrid:** adopt for ops/PM; evolve/build the research + dashboard + voice
  integration custom.
- Voice/worldview profile is the ranking + drafting brain; lives in `market-research/`.

---

## Open questions
1. ~~Where is the newsletter repo?~~ **Resolved:** `innovative-hype-newsletter`
   (cloned to `/root`).
2. **Research lab:** is the Hermes-cron pipeline what you meant by "already
   started," and do you want it moved to the desktop now or after the voice
   integration?
3. **Voice reconciliation:** the live newsletter voice (`draft.py`) is
   mainstream-conversational "Micah Peoples / AI news." The mined profile is
   broader/edgier (sovereignty, web3, civil liberties). How much of the mined
   worldview do you want injected — full send, or a dial? And **one voice vs.
   personal (geo ppls) + brand split?**
4. **Scope of the newsletter:** stay AI-news-focused, or broaden to the full beat
   list from the profile (web3, sovereignty, creator economy, Texas, sports-biz)?
5. **Hosting** for Plane + dashboard: same host as InnovativeHypeChat, separate
   VPS, or desktop-exposed?

---

## Phased roadmap (proposed)
- **Phase 0 — Align (now):** this doc; confirm the open questions above.
- **Phase 1 — Wire the brain (highest leverage):** inject `VOICE-AND-WORLDVIEW.md`
  into `draft.py`; expand `config.yaml` feeds + keywords from profile §5; add
  thesis/account-aware ranking to `research.py`. *Upgrades the live pipeline
  immediately, no new infra.*
- **Phase 2 — Insights dashboard UI:** a view over the scored digest — "what to
  write + angle" cards, with one-click draft.
- **Phase 3 — Ops:** stand up Plane; model projects + the newsletter editorial
  calendar.
- **Phase 4 — Lab to desktop + more agentic:** move research to the desktop, make
  it read full articles + synthesize a POV; integrate the twitterGPT voice model
  for on-brand drafting.
```
