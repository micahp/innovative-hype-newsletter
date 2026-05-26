# Market Research — 2026 rebuild
_Last rewritten 2026-05-25. Supersedes the framing in `01`–`08` (astrology-only) and reorganizes the agent-landscape work in `AGENT-*` / `AI-AGENT-LIKES.md` around the verticals Micah actually wants to pursue._

Grounded in 19 primary sources Micah curated (see `_notes/source-notes.md` for the full distillation, read from the screenshots in `innovative-hype-newsletter/scraped-links/` since the long-form X Articles are login-gated). Source citations below use the `[NN author]` keys from that notes file.

---

## 0. The filter (Micah's operating constraints)
Every idea below is judged against these — they are non-negotiable and kill otherwise-good ideas:

- **$0 upfront.** No ad spend, no paid creators, no inventory, no commercial licenses until the thing funds itself. Only free inputs: Micah's batched time + algorithms/Google/open-source.
- **Mostly hands-off.** Build-once-sell-forever beats anything needing daily manual labor. Automation and "self-improving" loops are the goal, not employees.
- **Solo operator.** One person, deep technical skill (ships Next.js on a Contabo VPS, has a desktop GPU box, runs agents).
- **No fabricated personas; faceless is fine.** (Established prior constraint.)
- **Low legal/regulatory risk.** No health/medical claims; be deliberate about anything touching securities, gambling, or money transmission.
- **Worldview fit:** AI-forward, sovereignty-centered (money, data, civil liberties). Finance + AI are his highest-conviction, highest-energy domains — and, conveniently, the highest-RPM content niches `[12 winkle]`.

**The single most important finding across all 19 sources:** the durable 2026 edge is not "have a model" — models are commoditized and cheap `[04 DeepSeek]`. The edge is **distribution you control + a self-improving system + a structural data/market inefficiency.** Hold every vertical to that bar.

---

## 1. The verticals, ranked

Ranked by **(opportunity × fit-with-constraints), not by Micah's listed order.** Reasoning for the ranking is in §3.

| Rank | Vertical | Why it ranks here | Hands-off? | $0? | Capital at risk? |
|---|---|---|---|---|---|
| **A** | Faceless AI media (high-RPM) | Proven unit economics, ~5h/wk, compounds, synergizes w/ newsletter, highest-RPM niches = his expertise | ✅ high | ✅ | none |
| **B** | Apps & games | Proven $0-distribution playbook, he has the build skill, subscription = passive | ⚠️ needs content cadence | ✅ | none |
| **C** | Prediction-market trading bot | Only *proven, live, self-improving* automated money-edge in the set; $0-ish | ✅ once built | ⚠️ ~$50–100 seed | ✅ yes |
| **D** | Sports prediction ("Legendary Picks") | $0 free data, buildable on his stack; monetization is the hard part | ✅ once built | ✅ | depends on model |
| **E** | Virtual influencer | $0 tooling now exists, but audience-building is slow + brand risk | ❌ slow build | ✅ | reputational |
| **F** | Music + code | Identity-driven; overlaps faceless media; gen-music tooling now $0-ish; his failed social-music app to revisit | ⚠️ varies | ✅ | none |

---

### A. Faceless AI media (newsletter → faceless video → high-RPM niches)
**The bet:** Run informational content channels where AI does the production, in the niches that pay the most per view, and let ad revenue + affiliate + digital products compound.

**Evidence:**
- `[12 winkle]` — a faceless AI YouTube channel ramped **$1.2k → $4.3k → $7.1k → $11.7k** over 4 months on **~5 hrs/week**. Stack = **Claude (scripts) + ElevenLabs (voice) + CapCut (assembly).** Concrete RPM table: **Finance/Investing $15–50, Tech/AI $12–30**, Health $10–25, True Crime $5–15, General $3–8. A finance channel at 500k monthly views ≈ $10k/mo from AdSense alone; sponsors/products 2–3×. Uses Claude as a niche-research analyst and a structured scriptwriting prompt (full prompts captured in notes).
- `[03 Seth Fowler]` — long-form (1hr+) video earns **$20+ RPM** if it has a narrative backbone (mission, payoffs, foreshadowing). Confirms long-form informational/gaming content monetizes well now.
- `[17 Sukh/Flow]` — the production-tooling moat is gone: a €3.5M Blender film beat Pixar's $200M. **$0 open-source tools now produce broadcast-quality media.**
- `[01 Aden Libin]` — one 30-min short-form video can carry a product for 6 months. Distribution is a *format*, not a budget.

**$0 / hands-off build path on his stack:** He already has the newsletter pipeline (`research.py` → digest → draft) and a voice/worldview profile. Extend it: newsletter issue → Claude reformats into a video script (winkle's prompt) → ElevenLabs voice → auto-assemble → publish to YouTube/Shorts/TikTok. **Niche = AI/finance/sovereignty** (his expertise *and* the top-RPM bands). Faceless, so no persona problem.

**Monetization:** AdSense (highest in his niches) → affiliate (AI tools, brokerages, hardware) → his own digital products (the planner-PDF muscle from the astrology work transfers). All zero-COGS.

**Risks / caveats:** YouTube faceless-AI saturation is real; the moat is *niche authority + script quality + consistency*, not the tooling. `[18 Andon Labs]` is the cautionary bound: fully-autonomous, no-human-in-loop media produces garbage and ~$0 — keep Micah's editorial judgment in the loop (he reviews, AI produces).

**Verdict & first step:** **Highest-fit vertical.** First step: wire the existing newsletter content into one faceless YouTube/Shorts channel in the AI/finance niche; run winkle's niche-analysis prompt to pick the exact sub-niche before producing.

---

### B. Apps & games
**The bet:** Ship small B2C apps (and eventually games) fast with AI, monetize with a subscription paywall, distribute for free via organic short-form video.

**Evidence:**
- `[02 Ernesto]` — **10 apps in 10 months, $800k/yr.** Replicable playbook, fully captured: (1) pick a **"painkiller" niche** from his 34-niche list (quit-habit / self-improvement / health-tracker apps); validate via App Store revenue + existing creator content. (2) Build in **3–7 days** with **Rork + Cursor + ChatGPT**, monetize with **Superwall** paywall. **Onboarding is 70% of the app** — copy the *structure* of the best competitor's onboarding (Goal→Results→Symptoms→How-it-helps→Reviews→Features→Custom Plan→Paywall→Discounted Paywall). (3) Distribute via one of 4 free channels: influencers, **faceless slideshows**, UGC, paid. Ernesto also builds **games with Rork** and runs **Arcads** for AI-influencer ad creative — directly relevant to Micah's "advertising component / AI images & videos."
- `[01 Aden Libin]` — $0-spend short-form video → $2k/mo app. The distribution half of the same playbook.
- **Games specifically** `[15 AlbyHojel]` — Micah's instinct that **Roblox/Fortnite is "a massive cliff" is correct.** Even Roblox's own team can't make AI *generate* a playable game; the frontier still pairs a real engine + a 14B video world-model + a VLM harness ("Cartridge"). Near-term reality: **build games IN the engine (Roblox Studio / UEFN / Rork for mobile) with AI assist** — don't wait for AI to generate them. Watch world models (Dreamer4, Genie-style) but don't bet the venture on them.

**$0 / hands-off build path:** He has the engineering chops; Rork/Cursor collapse build time to days. The recurring labor is *content for distribution* — which **shares infrastructure with Vertical A** (the same faceless-video engine markets the apps). Subscription paywall = passive once acquired.

**Monetization:** subscription (Superwall/RevenueCat) for apps; for games, in-game purchases / Roblox economy. Zero marginal cost.

**Risks/caveats:** App Store competition is brutal; the win is *niche + onboarding + distribution*, not the code. "Painkiller" niches (quit-porn, anxiety, etc.) brush wellness claims — keep copy testimonial-free and avoid medical claims (same discipline as the astrology work). Games are higher-value-per-hour-spent (Micah's correct framing) but the Roblox/Fortnite learning curve is a multi-month investment, not a weekend.

**Verdict & first step:** **Strong second.** First step: pick ONE painkiller niche where a competitor clears $100k/mo, ship an MVP in a week with Rork, A/B the onboarding, and feed it with the Vertical-A video engine. Treat games as a deliberate later bet, starting with one small Roblox/UEFN experiment, not a from-scratch AAA attempt.

---

### C. Prediction-market trading bot (the realistic "automated trading" play)
**The bet:** Run a self-improving statistical-arbitrage agent on prediction markets (Polymarket BTC up/down), where a measurable, mechanical edge exists.

**Evidence:**
- `[10 0xRicker]` — a complete, **<$10/mo, no-code-required** build for a **self-learning BTC trading agent**: claims $60M+ in 2025 across the segment; example live bots showing $570k–$797k P/L. The edge = **Markov-chain analysis of BTC price states** on Polymarket's **1-minute up/down market**: enter only when persistence probability `p(j,j) ≥ 0.87` and the model–market gap `≥ 5%`; size with **Kelly**; **win rate 63–72%.** Stack = Claude Opus 4.7 + the open-source **Hermes** agent (NousResearch) run via **Atomic** + cheap VPS + Telegram; **Claude reads the trade journal nightly and rewrites the rules** (the self-improving loop). Recommended open-source repos given.
- `[14 Roan]` — frames **prediction markets as the new accessible quant edge** ("quant trading is about math, not opinions; bet where implied probability deviates measurably from the data"). Confirms the category; the rest is a quant skills/career roadmap + comp benchmarks ($300k base, researcher $350–650k).
- `[13 Avi Chawla]` — the cheap form of "self-improving agent" is **prompt/rule iteration (system-prompt learning), not retraining** — exactly what `[10]`'s nightly loop does.

**Honest read on Micah's stated strategy (important):** Micah's plan — *a golden cross on the Welles Wilder 26-period MA across hourly/daily/weekly/monthly + sentiment analysis* — is a **widely-known classical trend-following system.** On liquid assets (spot BTC, large-cap stocks) these signals are heavily arbitraged and rarely a durable automated edge; they're better as a **discretionary confirmation overlay** than as the core of an automated money-maker. The sources show the *defensible* automated edge in 2026 is **structural inefficiency in a less-efficient venue** (Polymarket's emotion-priced short-interval markets), not TA on efficient markets. **Recommendation:** if he wants automated trading, point it at prediction-market stat-arb (where `[10]` shows a real edge) and use his Wilder-MA/sentiment ideas as *features* feeding the probability model, not as the strategy itself.

**On "build a fund like Aschenbrenner / copy-trade him" (corrected per Micah):** Copy-trading **is** possible via 13F filings. Any manager with **>$100M in 13F-reportable US equity AUM must file a Form 13F quarterly** — and **Aschenbrenner's Situation Awareness LP is large enough (reported ~$1.5B+) that it must disclose**, same as Buffett. So his US long-equity positions are public on a **~45-day lag**. Congress (Pelosi et al.) discloses under the **STOCK Act**. So all three are trackable.
- **Caveats of 13F copy-trading:** it shows only **long US equity + some options — not shorts, not cash, not non-US, not intra-quarter exits**, and the **45-day lag** means you're trading behind the manager. For a concentrated, slow-moving book (Buffett, a thesis fund like Aschenbrenner's) that lag matters less; for a high-turnover book it's near-useless.
- **The build:** a **copy-trading tool** is a real **Vertical-B app** (data is free: SEC EDGAR 13F + Senate/House disclosures). But it's a **crowded space** (Autopilot, Quiver Quantitative, Unusual Whales). Differentiate with his AI edge: an agent that *explains/contextualizes* each disclosed trade in real time, scores conviction, and bundles 13F + Congress + sentiment into one narrative — not just a mirror of positions.

**Risks/caveats:** **Real capital at risk** (violates the spirit of "$0" — cap the seed at what he'll lose). **Legal/geo:** Polymarket access is restricted for US persons; understand the rules before funding. Prediction-market BTC up/down ≠ spot BTC. Backtests lie — the source itself mandates a 24h dry-run; demand months of paper-trading before real money.

**Verdict & first step:** **Promising but capital-gated and legally caveated** — third, not first. First step (zero-risk): stand up `[10]`'s stack in **DRY_RUN** on his VPS, paper-trade for weeks, and verify the Markov edge holds on current data *before* a dollar moves. In parallel, scope the Buffett/Pelosi tracker as an app concept.

---

### D. Sports prediction — "Legendary Picks"
**The bet:** An AI/ML system that predicts game winners and player props for the big leagues, more accurately than the market.

**Evidence:**
- `[16 zostaff]` — a full, buildable **NBA prediction architecture**: free **`nba_api`** (box scores, play-by-play, tracking, 40+ yrs, no auth) + public **Polymarket Gamma API** → **ML ensemble (LogReg + Random Forest + XGBoost)** → fuse **3 probability sources (sportsbook lines + Polymarket + model)** → **Claude** for explanation + **divergence analysis**. NBA is the ideal ML target: 1,230 games/yr, clean binary outcomes, stable patterns (top teams win 68–72%). The real edge framing = **where the model disagrees with the market**, not raw "who wins." Player props = the same method on player box-score stats (covers Micah's "hit their prop").

**$0 / hands-off build path:** Entirely on his existing Python + Claude stack; data is free. Shares the **prediction-market + Claude-explanation infrastructure with Vertical C** — build once, two products.

**Monetization (the hard part):**
1. **Trade it yourself** on prediction markets/sportsbooks (merges with Vertical C; same capital/legal caveats).
2. **Sell picks / a subscription** (Vertical-A/B media + product) — but the "picks-seller" space is trust-poor, seasonal, and adjacent to gambling-promotion rules. Requires honest track-record transparency to stand out.

**Risks/caveats:** Sports modeling is seasonal and competitive against sharp books; "beating the closing line" is a high bar. Selling betting picks carries reputational + possible promotional-compliance issues. Best treated as **a data/AI showcase that feeds the trading or media verticals**, not a standalone get-rich product.

**Verdict & first step:** **Fourth — strong tech, weak standalone monetization.** First step: build the NBA model as a portfolio/credibility piece and a feature source for Vertical C; decide on monetization only after it demonstrably beats the market on out-of-sample games.

---

### E. Virtual influencer
**The bet:** An AI-generated on-camera persona that builds an audience and monetizes via brand/affiliate/products.

**Evidence:**
- `[09 Victor M]` — **LongCat**, an **open-source MIT talking-avatar model** with a free HF Space, makes a believable talking head at ~$0. Pair with ElevenLabs voice + Claude scripts (Vertical A) → a faced channel, AI tutors, dubbing, "Claude Code with a face," NPC dialogue.

**$0 / hands-off path:** Tooling is now free. But this is the **slowest** to monetize — audience-building takes months, and a *persona* (even AI) reintroduces the brand-risk and consistency burden that "faceless" avoids.

**Risks/caveats:** Brand/reputational risk (`[18 Andon Labs]` shows how fast autonomous AI media goes off the rails). Audience-building is not hands-off. Crowded.

**Verdict & first step:** **Lowest priority — an optional upgrade to Vertical A**, not its own venture. If Vertical A's faceless channel gains traction, *then* test adding a LongCat avatar to one format and measure lift. Don't start here.

---

### F. Music + code (Micah's identity vertical)
**The bet:** Music is core to Micah's identity, so the long-run play is something at the intersection of **music + code** — and it overlaps Vertical A (a faceless music/AI channel is still faceless media). He previously built a **social music app that failed** and has been waiting to return to it. Adjacent themes he cares about: **nostalgia** and **tech detox**.

**Honest status — this is NOT in the 19-source evidence base.** None of the curated sources are about music; this vertical comes from Micah's identity and intent, so treat the below as direction-setting, not validated research. Worth its own dedicated research pass.

**What's true in 2026 that makes it cheaper than when his app failed:**
- **Generative music is now ~$0 to produce** (Suno, Udio, open models) — raw content for a faceless music channel or in-app soundscapes costs nothing.
- The same **faceless-distribution engine (Vertical A)** works for music content (lo-fi/focus/nostalgia mixes are a proven high-retention YouTube format), and a music brand can carry merch/affiliate/products.
- A talking/animated avatar `[09 LongCat]` could front a music persona if he ever wants a face on it.

**Where "nostalgia" and "tech detox" fit:** these are *positioning angles*, and they're counter-cultural to the AI-maximalist crowd — which can be a differentiator. Possible shapes: a tech-detox / focus app (music + intentional friction; "painkiller" niche per `[02 Ernesto]` — Focus & Deep Work, Stress Relief are on his niche list); a nostalgia-driven music experience (retro UI, no infinite feed); the social-music app reimagined around small-group/anti-algorithm intimacy rather than scale.

**Why his social-music app failed (the question to answer before rebuilding):** social apps die on the **cold-start / network-effect** problem — they need users to have value, and have no value until they have users. That's the opposite of "$0 + hands-off + solo." Before rebuilding, decide: does v2 still need network effects (hard, slow, capital-hungry), or can it deliver **single-player value first** (works for one user with zero friends) and grow social later? The latter fits his constraints; the former probably doesn't.

**Risks/caveats:** music **licensing/copyright** is a minefield — stick to AI-generated or properly-licensed audio, never rip tracks. Social = cold-start trap (above). AI-music platform terms of service vary on commercial use — check before monetizing.

**Verdict & first step:** **A genuine long-term vertical, but under-researched and (if social) constraint-violating in its old form.** Cheapest first step that honors his constraints: a **faceless music/nostalgia channel** under Vertical A (single-player value, $0, compounds) — which doubles as audience + validation for an eventual app reboot. Hold the social-app rebuild until there's an audience to seed it. **Action: schedule a dedicated research pass on music+code (gen-music tooling, faceless-music-channel economics, tech-detox app market, the cold-start fix).**

---

## 2. Cross-cutting capability layer (powers all six)
These aren't verticals — they're the toolkit. Adopt selectively.

- **Cheap, commoditized models** `[04 DeepSeek]` — open-weight efficiency (GRPO, RLVR, MLA, MoE load-balancing) keeps collapsing cost. Good for $0 builders; don't over-invest in any one model. Sovereignty angle fits Micah's worldview.
- **Agent harnesses / skills** `[11 ECC]` — "Everything Claude Code" (38 agents, 156 skills, AgentShield's 1,282 security tests, continuous-learning layer). Useful patterns, but heed the critics: bloat, context-waste, drift within ~6 months, "Claude Code already does most of this." **Adopt à la carte (security scan, planning, memory via claude-mem), don't cargo-cult the whole thing.**
- **Massively parallel agents** `[06 Kimi swarm]` — 300 sub-agents in parallel for research-style fan-out tasks. Relevant to his research-dashboard/newsletter ambitions (parallelize source analysis).
- **Self-improvement = prompt/rule iteration** `[13 Avi Chawla]` — the accessible "self-learning" loop (used by `[10]`) is rewriting rules from a journal, not fine-tuning. Cheap and effective.
- **Edge AI** `[07 leopardracer]` — on-chip inference ($40 box, no cloud bill) is starting to "eat usage-based B2B SaaS." A future cost-lever and a possible product angle.
- **Upskilling** `[05 CJ Zafir]` fine-tuning curriculum + `[08 Avid]` the canonical 2026 agent-engineering reading list (~90 links) — bookmark both; `[05]` directly supports the **twitterGPT** finetune.

---

## 3. Why this ranking (the synthesis)
1. **Shared infrastructure is the real strategy.** A/B/C/D/E are not five separate bets — they're **one engine reused**: (a) a *faceless content/distribution machine* (Claude + ElevenLabs + CapCut) markets everything; (b) a *prediction-market + Claude-explanation backend* serves both trading (C) and sports (D); (c) a *Rork/Cursor app factory* ships apps, games, and the copy-trading tool. **Build the two shared engines first, and three verticals fall out of them.**
2. **Lead with the no-capital, compounding, hands-off vertical (A).** It funds the rest without risking money and exercises the exact muscles the others need.
3. **C is the highest-upside but the only one risking capital and carrying legal caveats** — gate it behind a dry-run and a hard loss cap.
4. **Respect the cliffs Micah already senses:** Roblox/Fortnite games `[15]` and a from-scratch fund `[14]`/Aschenbrenner copy-trading are real but slow/blocked — sequence them late, and reshape "copy-trading" into an app `[B]` rather than a trading strategy.
5. **Keep a human in the loop on anything public-facing** `[18]` — full autonomy still means ~$0 revenue and brand risk.

**Recommended 90-day sequence:**
1. **Weeks 1–4:** Vertical A — one faceless AI channel in the AI/finance niche, fed by the existing newsletter pipeline. (Funds everything; $0; reuses what exists.)
2. **Weeks 3–8 (parallel):** Vertical B — ship one painkiller app with Rork + Superwall, marketed by the A engine.
3. **Weeks 4–12 (parallel, zero-risk):** Vertical C in DRY_RUN — stand up the `[10]` Polymarket stack and paper-trade; build the NBA model `[16]` as the shared analytics backend (feeds D).
4. **Later / conditional:** virtual-influencer upgrade to A (E); a deliberate first Roblox/UEFN game experiment; the Buffett/Pelosi tracker app — only with a differentiator.

---

## 4. Source index (all 19)
**Financial:** `[10]` 0xRicker — Hermes+Polymarket self-learning BTC agent · `[14]` Roan — quant/prediction-market roadmap.
**Sports:** `[16]` zostaff — AI NBA prediction system.
**Apps/Games:** `[02]` Ernesto — 10 apps, $800k/yr playbook · `[01]` Aden Libin — 30-min video → $2k/mo app · `[15]` AlbyHojel — world-model harness for gaming (Roblox "Cartridge").
**Media:** `[12]` winkle — faceless AI channel $12k/mo · `[03]` Seth Fowler — $20 RPM long-form gaming video · `[17]` Sukh — Flow/Blender beats Pixar · `[09]` Victor M — LongCat open talking-avatar.
**Capability/meta:** `[11]` ECC (Affaan, Reddit) · `[06]` Kimi 300-agent swarm · `[13]` Avi Chawla — RL/system-prompt-learning agents · `[04]` GDP — DeepSeek $10T strategy · `[08]` Avid — AI-engineer roadmap · `[05]` CJ Zafir — fine-tuning curriculum · `[07]` leopardracer — solar edge-AI camera · `[18]` Andon Labs — AI-run radio (cautionary).

Full per-source detail and exact prompts/numbers: `_notes/source-notes.md`.
