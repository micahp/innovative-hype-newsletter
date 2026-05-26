# Context Summary — 2026-05-25

Snapshot of where everything stands across the session, so we can resume cleanly
after the pause. Three intertwined work streams: **twitterGPT**, **Innovative Hype
infrastructure / newsletter**, and **market research (AI-agent landscape)**.

---

## 1. Source data
- Micah's X archive: `/root/Downloads/E:\Users\micah\Downloads\twitter-2026-05-17-...zip`
  (9.85 GB). Account `@geoppls` ("geo ppls").
- Key contents: 33,143 tweets (8,036 RTs, 19,747 replies, 5,360 originals);
  56,691 **likes** (used as de-facto bookmarks — X doesn't export real bookmarks);
  `article.js` is **empty** (Micah has authored no X Articles).
- Parsing/analysis scripts live in `/root/Downloads/`:
  `prepare_dataset.py`, `train_qlora.py`, `generate.py`, `resolve_links.py`,
  `enrich_quotes.py`. Link-resolution caches: `tco_cache.json`, `oembed_cache.json`.

---

## 2. twitterGPT  (repo: https://github.com/micahp/twittergpt, public)
Web app to finetune an LLM on a user's tweets and generate tweets in their voice.
- **M0 data pipeline** ✅ done — `prepare_dataset.py` → 19,744 clean training
  examples (`dataset_out/`, gitignored).
- **M1 local finetune kit** ✅ written, ⏳ not yet run — needs Micah's desktop GPU
  (2x RTX 2060). See `M1-SETUP.md`. QLoRA via Unsloth, Qwen2.5-3B.
- **M3 web app skeleton** ✅ done — FastAPI backend + Next.js frontend +
  `ComputeBackend` abstraction (local/Daytona). Non-GPU paths verified.
- **M2 Daytona** ⏳ stub. **M4 multi-user** ⏳ deferred.
- **Next action:** run M1 on the desktop, paste sample tweets to judge voice.

## 3. Innovative Hype infrastructure + newsletter
- **North-star plan:** `00-INFRASTRUCTURE-NORTH-STAR.md` (this folder). Three
  pillars: (1) Ops/PM via **Plane** (open-source, adopt), (2) Research & insights
  dashboard (build, voice-powered), (3) Automated AI research lab (desktop; partly
  exists). Decisions: no new repo; Plane for PM; voice/worldview profile = the brain.
- **Newsletter repo** (https://github.com/micahp/innovative-hype-newsletter, public):
  working v1 — `research.py` (17 RSS feeds → digest), `draft.py` (prompt template),
  `pipeline.sh`, `publish.py`, Hermes cron, Substack. Added README + `.gitignore`
  this session; `config.local.yaml` untracked (its committed values were
  placeholders, **not** real secrets — I raised a false alarm and corrected it).
  Gap: not yet powered by the voice/worldview profile; AI-news-only.
- **Note:** Micah does **not** want me publishing directly to Substack.

## 4. Market research (the active stream)
Folder `/root/market-research/` (numbered docs `01`–`08` = earlier "make money on
the internet, mostly hands-off" research). New this session:
- **`VOICE-AND-WORLDVIEW.md`** — Micah's editorial voice + worldview, mined from
  originals + replies + retweets. Headline: live worldview is **AI-forward +
  sovereignty-centered** (money/data/civil liberties), broader than the 2021–23
  NFT-heavy originals. (Built for voice/article drafting + source selection.)
- **`AI-AGENT-LIKES.md`** — 325 AI-agent likes, tiered (🔁 27 retweeted →
  📄 article/thread → other), with t.co links resolved (19 external 🔗 + 6 X
  Articles 📰) and 43 quote-tweets expanded via oembed.
- **`AGENT-MONEY-LIKES.md`** — 58 monetization-tagged subset (kept per request).
- **`AGENT-TOOLS-AND-STRATEGIES.md`** — the synthesis: the agent **tool landscape**
  (coding agents/IDEs, frameworks, models, browser/voice/gen-media, payment rails)
  and the **money playbooks** (AI-agency-for-local-biz, vertical micro-SaaS,
  sell-the-agent, UGC ad factories, build-and-flip, sell-the-playbook, tooling,
  crypto) + meta-trends + risks + sources.
- **Purpose (clarified by Micah):** this agent mining is **market research** to
  understand the tools and strategies people use to build agents and make money —
  **not** newsletter material.

---

## Open threads / where to resume
1. **Pressure-test** the top agent money-strategies against Micah's constraints,
   tying into `08-synthesis-and-recommendations.md` (offered, not yet done).
2. Optionally resolve remaining quote/X-article links to deepen a specific strategy.
3. twitterGPT **M1 finetune run** on the desktop (the quality gate).
4. Wire the voice/worldview profile into the newsletter pipeline (north-star Phase 1)
   — separate from the market-research thread.

## Working preferences (persisted to memory)
- **No Co-Authored-By / AI-attribution trailers** on commits or PRs, ever.
- Verify before alarming (the secret false-alarm lesson).
- `gh` CLI installed + authenticated as `micahp` on this box.
