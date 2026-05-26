# Source notes — from screenshots in innovative-hype-newsletter/scraped-links
(Captured 2026-05-25. Replies ignored per Micah. Bodies read from PNG screenshots since X Articles are login-gated.)

Page layout of each capture: tweet/thread preview first, then the full "Article" reader repeating the body.

---

## [10] 0xRicker — "Hermes + Polymarket: build an AI for a self-learning BTC trading agent, $100→$10,000" (2026-05-22)
**Vertical: FINANCIAL (BTC trading) — bullseye on Micah's idea.**
- Claim: trading bots generated **$60M+ profit on Polymarket in 2025–26**; 77% of that from the **Crypto UP/DOWN market**, driven by structural inefficiencies.
- Market = **BTC 5-minute Up/Down** prediction market on Polymarket. Crowd prices directional moves on *emotion* (news, social, gut). Edge = the gap between math and crowd price. "Repeatable, scalable, automatable."
- Stats: 288 windows/day per asset; 1 trade every 81 sec; edge window 5–15% avg gap; **win rate 63–72% at p≥0.87**.
- Example live bots (Polymarket P/L): Bonereaper $745,700 (High-Confidence Spread Capture); 0xe1D6b514 $797,185 (Dual-Mode Expected Value); 0xB27BC932 $569,134 (Multi-Asset Variance Reduction). Combined **$2,112,019** — three bots, one market segment, same math.
- **The math = Markov Chain analysis of BTC price states.** Price moves aren't random; in a committed directional state, P(continuation) measurably >50%. "The math knows before the crowd does."
- Entry: Δ = p̂ − q ≥ ε → ENTER. p̂=model prob, q=market price, ε=5% min gap. Payoff r=(1−q)/q (q=0.647→+54.5%; q=0.441→+126.7%). **Only trades when p(j*,j*) ≥ 0.87** (Markov persistence threshold) — below that, no trade. That filter (not directional prediction) is why win rate stays high.
- Sizing: **Kelly** f*=p−(1−p)/b; f*=0.71 at p=0.87, b=0.647.
- Stack (open-source, no coding, **<$10/mo**): Claude Opus 4.7 (model) + **Hermes agent** (open-source agent framework by **NousResearch**, Paradigm-backed $70M; by Apr 2026 surpassed Claude Code in GitHub stars) run via **Atomic** (atomicbot.ai; 100+ integrations, persistent memory, run local Mac or "Run in Cloud") + cheap VPS (Hetzner) + Telegram gateway. $10 min → $50 rec → 2 POL gas (~$1) → ~30 min setup.
- Setup: (1) install Atomic, pick Hermes agent; (2) connect model API = Claude Opus 4.7 (alt OpenRouter / OpenAI Codex free via ChatGPT Pro); (3) connect Telegram via BotFather.
- Trading logic = feed Hermes a "BUILD LOGIC" prompt pointing at an existing GitHub repo and adapt to Polymarket **CLOB v2**. Recommended repos: `aulekar/polymarket-BTC-15-Minute-Trading-Bot` (Grafana/Redis, SL/TP, Markov + Kelly), `JLowo/gengar-polymarket-bot` (Brownian motion, calibrated vol, conservative), `dijenno/Polymarket-bot` (arbitrage+momentum, auto-optimization). Use py_clob_client v2, SAFE_ADDRESS proxy wallets, USDC collateral, KEEP_DRY_RUN by default, never expose keys.
- Wallet: approve CTF Exchange, Neg Risk CTF Exchange, Neg Risk Adapter.
- **Run DRY_RUN 24h first.** env: DRY_RUN=true, MIN_EDGE=0.05, MIN_PROB=0.87, MIN_BET=1, MAX_BET=50, BANKROLL=100.
- **Self-learning loop**: Claude Opus 4.7 reads the execution journal nightly and rewrites the trading rules based on what worked. This is the "self-improving" part.
- Monetization tells: referral links to Polymarket profiles + `predictparity.com?code=ricky` (affiliate). The article is itself lead-gen.
- ⚠️ For Micah: this is *prediction-market* trading, not his TA golden-cross idea — but it's the closest live, $0-ish, hands-off, self-improving BTC-agent blueprint, and it bridges his trading + sentiment goals. Polymarket BTC up/down ≠ spot BTC; legal/geo caveats (US Polymarket access).

---

## [14] Roan / RohOnChain — "The Exact Blueprint To Make $650,000/Year (Quant Roadmap)" / "How to Become a Quant for Prediction Markets (Complete Roadmap)" (2026-02-24)
**Vertical: FINANCIAL (the fund / quant skills path) — relevant to Micah's "build a fund like Aschenbrenner."**
- Author = backend dev working on system design + HFT-style execution + quant trading systems; focuses on how prediction markets behave under load. Writes specific strategy pieces (e.g. the Polymarket arbitrage math one).
- Core thesis: **"Quant trading is not about opinions about markets. It is about MATH."** Find markets where implied probability deviates measurably from what the underlying data supports; bet on the gap; repeat across hundreds of independent events (casino model — small edge, many bets, law of large numbers). **Same framework applies identically to prediction markets** (elections, econ, sports, geopolitics) as to equities/derivatives.
- Myth-busting: you do NOT need a finance background or Ivy League. Jane Street job posts say finance knowledge "not expected or required"; 2/3 of interns studied CS or math. Base salary ~$300k.
- Comp benchmarks (the hook): Citadel entry quant researcher $336k–$642k total out of college; Jane Street avg $1.4M (H1 2025); IMC interns ~$240k annualized; 5-yr survivors at top prop shops $800k–$1.2M/yr. Roles: Researcher ($350–650k, highest paid), Trader ($200–400k, uncapped), Developer ($200–350k; C++/Rust/Python infra), Risk Quant (lower ceiling, more stability). **Fastest-growing role = AI/ML systems quant** (ML models in live trading; intersection of quant research + ML eng; most 2025–26 hiring).
- The roadmap = 5 math layers, each prerequisite for the next: **(1) Probability** (Bayes, conditional thinking, P(A|B), posterior = likelihood×prior/evidence, expected value + variance — "the two numbers you think about for the rest of your career"); (2) Statistics ("listen to data… most of what looks like signal is noise"; backtest properly — is 15% annual real edge or luck?); then stochastic processes, linear algebra, optimization/ML (later layers, not fully read).
- Nature of the doc: **mostly an educational curriculum + career roadmap + comp-porn hook**, NOT a turnkey bot. It's lead-gen for his strategy content. Value to Micah = the skill tree + the "prediction markets = accessible quant edge" framing, which pairs with [10].

---

## [16] zostaff — "WHEN DATA OUTWEIGHS INTUITION: AN AI SYSTEM FOR NBA PREDICTIONS" (2026-04-20)
**Vertical: SPORTS PREDICTION — this IS the "Legendary Picks" architecture, spelled out.**
- Full technical build guide. **Pipeline / architecture (5 layers):**
  1. **Data + feature layer** — Claude API for feature generation, context analysis, stats interpretation.
  2. **Probability fusion** — merge **3 probability sources**: sportsbook lines + Polymarket prices + ML model.
  3. **Model layer** — Logistic Regression | Random Forest | XGBoost, combined via Ensemble (voting/stacking).
  4. **Interpretation layer** — Claude generates natural-language prediction explanations, confidence assessment, and **divergence analysis between sportsbook / Polymarket / ML** (the edge = where they disagree).
  5. **Output layer** — matplotlib visualizations, JSON reports, Telegram bot.
- **Why NBA is the best ML playground:** 82 games × 30 teams = 1,230 games/season, each with deep stats; binary outcome (Win/Loss, no draws) → clean binary classification; patterns stable & modelable; best teams win **68–72%** (predictable); ~240 possessions & 80+ shots/game; data free.
- **Data is free + no auth:** `nba_api` (open-source wrapper over NBA.com API — box scores, play-by-play, player tracking, shot charts, 40+ yrs) + Polymarket **Gamma API** (public). Dependencies: anthropic, nba_api, pandas, numpy, scikit-learn, xgboost, matplotlib, seaborn, requests, python-dotenv, schedule.
- Rest of article = implementation code (NBADataLoader, feature engineering, model training, edge/bet sizing). Not fully read — heavy code, lots of whitespace.
- ⚠️ For Micah: confirms the sports-prediction vertical is buildable on **$0 free data** + his existing Python/Claude stack. The real edge framing = **disagreement between the ML model and the market (sportsbook/Polymarket) prices**, not just "predict the winner." Same prediction-market backbone as [10]/[14] → trading + sports verticals share infrastructure. Player-prop prediction (Micah's "hit their prop") is the same method applied to player box-score stats.

---

## [02] Ernesto Lopez — "I built 10 apps in 10 months and make $800,000/yr (full guide)" (2026-01-21)
**Vertical: APPS/GAMES — the cornerstone B2C app-factory playbook.**
- Story: first app "Snapout" (a quit-porn app), 0 experience, **$20,000 in first 30 days from 2 viral videos**. Went broke-19yo → retired mom + fiancé at 21, Miami. Came from SMMA (was trading time for money). Thesis: **"B2C apps are the only business that generates passive income — build once, sell forever, no calls/meetings, subscription-based."** Believes apps will mint more millionaires than ecom did, next 5 yrs. Limited spots → first movers win.
- **Step 1 — App-idea validation (the most important step):**
  - (a) Find a **"painkiller"** problem people struggle with *daily*. Shared a list of **"34+ $100k/mo painkiller app niches"**: Quit Porn / Vaping / Smoking / Alcohol / Weed / Caffeine / Overspending / Social Media, Addiction counter, Detox, Fasting, Build Discipline, Anxiety/Stress Relief, Procrastination, Ranked Gym, Pregnancy Tracker, Weight Loss, Muscle Gain, Healthy Eating, Testo-maxing, Men's Mental Health, Daily Motivation, Morning/Night Routine, Study Habits, Mindfulness & Meditation, Gratitude Journal, Self-Love & Confidence, Relationship, Focus & Deep Work. (Pattern = quit-a-habit + self-improvement + tracking.)
  - (b) Check App Store: confirm people already pay; a few apps doing $100k/mo = good sign.
  - (c) Download top competitors; screenshot their onboarding + core loop in detail.
  - (d) Check TikTok/IG growth strategy. Always one of **4 channels**: 1) Influencers, 2) **Faceless slideshows**, 3) UGC creators, 4) Paid ads. Proof = competitors making money + creators posting in the niche → validated.
- **Step 2 — Build + tool stack (3–7 days, "building an app in 2026 is a joke"):**
  - Stack: **Rork & Cursor** (AI app coding), **ChatGPT** (write prompts), **Superwall** (paywall — used on every app), **Firebase** (DB, optional), **Pinterest & Dribbble** (design inspo), **Xcode** (launch).
  - Flow: grab UI inspo → feed screenshots to ChatGPT with a "senior mobile app designer/engineer" meta-prompt → it outputs a build prompt for Rork/Cursor (+ reference images) → recreate UI as functional app.
  - **Monetization = "rip the onboarding & pricing."** Onboarding is **70% of the app** — it's what converts downloads to paying subs. Copy the *structure* (not literally) of the best competitor. The **"$100k onboarding structure that converts"**: Goal → Results → Symptoms → How App Can Help → Reviews → App Features → Custom Plan → **Paywall → Discounted Paywall**. Force users to pay upfront or start a free trial. Use Superwall/RevenueCat.
- Distribution is the $0 engine: **organic short-form video** (esp. faceless slideshows) drives installs; subscription paywall monetizes. Matches [01] Aden Libin ("one 30-min TikTok → $2k/mo app").
- (Ernesto's wider known playbook, from search: builds games 100% with **Rork**; runs an "OpenClaw" agent named "Eddie"; uses **Arcads** for AI-influencer ad creative — "plug-and-play AI influencers." Relevant to Micah's "advertising component / AI-generated images & videos.")
- ⚠️ For Micah: this is the most directly actionable apps-vertical blueprint — niche list + tool stack + onboarding-as-monetization + free short-form distribution. Cross-checks his "games are even more valuable" instinct (Rork builds games too).

---

## [15] Alberto Hojel — "In Search for the World Model Harness for Gaming" (2026-05-20)
**Vertical: GAMES (the Roblox/Fortnite cliff) — frontier reality-check, not a money playbook.**
- A research/build report (Roblox-affiliated work). **World models** = action-conditioned video models that predict pixels from state+action ("world model boom"). Question: can video-based world models actually make playable games?
- What they did: trained an **action-conditioned 14B Text-Image-to-Video (TI2V) world model running at 24fps**, handed it to Roblox game devs. Built a lightweight harness called **"Cartridge"** that couples the **Roblox engine** with a **real-time Vision Language Model (VLM) observer** — engine manages abstract game state, video model generates the world. Conclusion: **world models will need programmable harnesses (engine + VLM) to be usable for games.**
- Games impose 3 control levers a model must satisfy: **Movement** (locomotion rig: 1st/3rd person, jump/sprint/swim, vehicles), **Interactions** (tools, equip/use items, responsive NPCs/environment), **Scene control** (composition edits, non-trivial NPC behavior, physics like gravity/underwater). Text conditioning alone is insufficient; control decomposes into **Actions / World / Character / Dynamics.**
- Demos: cycle 7 prompts swapping environments + rigs (NYC avenue → warehouse → frog → camel caravan → firefighter → Himalayan backpacker → underwater diver); player acts as puppeteer/dungeon-master scheduling prompts.
- ⚠️ For Micah: confirms his instinct that **Roblox/Fortnite-grade games are a "massive cliff."** AI can't yet *generate* a playable game end-to-end — the frontier still pairs a real game engine + a model + a harness. Realistic near-term path = build IN Roblox Studio / UEFN with AI assist (Rork-style for mobile games), not AI-generates-the-whole-game. Watch world models (Dreamer4, Genie-style) but don't bet the venture on them yet.

---

## [12] winkle. — "How I Made an AI Channel That Generated $12,000 in One Month" (2026-05-12)
**Vertical: MEDIA CREATION — faceless AI YouTube channel playbook.**
- Revenue ramp: M1 $1,241 → M2 $4,310 → M3 $7,062 → **M4 $11,701.** Stack: **Claude** (scripts) + **ElevenLabs** (voice) + **CapCut** (assembly). Claude generated every video, ElevenLabs voiced every word, CapCut assembled every clip. **~5 hrs/week to maintain; runs while you sleep.**
- **YouTube RPM by niche (per 1,000 views):** Finance/Investing **$15–50**, Technology/AI **$12–30**, Health/Wellness $10–25, True Crime/Stories $5–15, General/Entertainment $3–8. A finance channel at 500k monthly views → ~$10k/mo from AdSense alone at $20 RPM; sponsorships/products → 2–3×. "Views are the engine. Niches are the fuel."
- **Part 1 — niche selection, Claude as market analyst.** Don't pick what you like; pick on demand + RPM + repeatability + ease of consistent production. Prompt: "Act as a YouTube channel strategist… analyze these 5 niches: for each give estimated RPM range, competition level, content repeatability (1–10), audience size potential, monetization beyond AdSense, one untapped content angle nobody uses. Final rec: which to start and why." Replaces a $300–500 niche-research consultant.
- **Part 2 — script system (prevents writer's block).** Script > visuals. Prompt: "You are a senior YouTube scriptwriter for faceless educational channels… Hook in first 30s = pattern interrupt; NO 'hey guys welcome back' intro; open-loop technique; tease payoff early; spoken English not essay English; [PAUSE] markers; [VISUAL: …] tags every scene; soft CTA that doesn't sound like begging."
- ⚠️ For Micah: maps onto his media vertical (newsletter/podcast). **Finance + Tech/AI = highest RPM**, which aligns perfectly with his AI-forward / money / sovereignty worldview. This is the Prayer-Lock pattern (faceless AI video) applied to high-RPM informational niches, with explicit unit economics. Could repurpose newsletter content → faceless YouTube/Shorts at near-$0 marginal cost.

---

## CAPABILITY / META layer (cross-cutting — power all four verticals)

### [06] Kirill — "Kimi Agent Swarm: How China Built a 300-Agent Parallel System" (2026-05-21)
- **Kimi K2.6 coordinates up to 300 sub-agents in parallel**, up to 4,000 coordinated steps, on one task. Coordinator decomposes → parallel subtasks → synthesizes into one deliverable. E.g. literature review = 40 parallel paper analyses; market-research report = 30 parallel source investigations. "Hours serially → minutes in parallel." Try: kimi.com/agent-swarm. (Affiliate links to ishosting in post.) → Meta-trend: **massively parallel agent orchestration** is now consumer-accessible.

### [13] Avi Chawla — "How top AI labs are building RL agents in 2026 (Karpathy's system-prompt-learning idea)" (2026-04-28)
- Teaches RL for agents: trajectory = (S,A,R,S′) transitions; RLHF lineage (InstructGPT 2022 → reward model → PPO). Modern shift toward **system-prompt learning** — agents improve by rewriting their own rules/prompt rather than retraining weights. Links **OpenPipe/ART**. → Connects to the "self-learning loop" in [10] and ECC's continuous-learning layer in [11]: the cheap, accessible form of "self-improving agent" is prompt/rule iteration, not fine-tuning.

### [04] GDP / bookwormengr — "DeepSeek's $10 Trillion Grand Strategy" / "Revisiting DeepSeek's Hero's Journey" (2026-05-22)
- Deep technical + geopolitical analysis. DeepSeek's efficiency innovations: **GRPO** (replaced PPO for RL), **RLVR** (RL w/ Verified Rewards), Multi-Token Prediction + speculative decoding, "ZERO bubble" pipelines, Wide-Expert-Parallel MoE load balancing, MLA/DSA to shrink KV cache, mHC for stable scaling. Framed as China's play to bootstrap a **$10T domestic AI hardware ecosystem** and wean off Western chips. Links DeepSeek-V4 paper, arXiv, AMD/OpenAI deal. → Meta-trend: **cheap, efficient, open-weight (often Chinese) models keep collapsing the cost curve** — good for $0-budget builders, and a sovereignty theme that fits Micah's worldview.

---

## Already-textual sources (from scraped .md; confirm/augment via media)
- **[01] Aden Libin** — one 30-min TikTok (3.7M views) → app **$2k/mo for 6 months, $0 spent**. "Steal this format." UGC = the entire distribution engine for a B2C app. (Pairs with [02].)
- **[03] Seth Fowler** — **$20+ RPM on 1hr+ gaming YouTube.** Long-form gaming video now needs a narrative backbone: clear mission/north-star, ups & downs, payoffs, foreshadowing — not aimless playthroughs. Plugs retti.ai (retention tool). → Games + media monetization overlap.
- **[05] CJ Zafir** — a copy-paste **mega-prompt to self-teach LLM fine-tuning** beginner→advanced (full curriculum: tokens→transformers→LoRA/QLoRA/DPO/RLHF→inference→local stack→RAG→agents→eval). → Upskilling resource; directly useful for Micah's twitterGPT finetune.
- **[07] leopardracer** — **Edge AI**: Pi Zero 2W + IMX500 camera + solar → on-chip bird-species ID, **no cloud / no latency / no monthly bill**, open-source code + free 3D files; beats paid wildlife-monitoring SaaS. Key insight (a reply): "a $40 edge box can replace a whole row of usage-based line items" → edge inference eats usage-based B2B SaaS.
- **[09] Victor M (HuggingFace)** — **LongCat** open-source **MIT talking-avatar model** (SOTA), free HF Space demo. Build: AI tutors with a face, dubbing pipelines, talking-head coding agents ("Claude Code with a face"), NPC dialogue. → Open-source path to a **virtual influencer / avatar** vertical at ~$0.
- **[11] Reddit / Affaan Mustafa — "Everything Claude Code" (ECC)** — won Anthropic hackathon solo (Claude Code, 8 hrs, $15k in credits), open-sourced: **38 agents, 156 skills, 72 commands, AgentShield (1,282 security tests; --opus red-team = attacker/defender/auditor), continuous-learning layer** (confidence grows across sessions), + claude-mem (cross-session memory) + superpowers (forced planning). Caveats from comments (worth heeding): bloat, context-waste loading all skills, "Claude Code already does most of this," will drift/break within ~6 months, expensive in tokens. → The agent-harness/skills tooling layer Micah's own builds sit on; adopt selectively, don't cargo-cult.
- **[17] Sukh — Flow beat Pixar with Blender** — Latvian indie, €3.5M vs Disney's $200M, won Best Animated Feature (97th Oscars), 100% **Blender (free, GPL-3.0)**. Full Blender capability list (modeling, VFX, sim, video edit, Python API). Netflix/Epic fund it; Pixar uses it. Caveat: steep learning curve. → Free open-source tooling now beats incumbents in media production. The animation/media vertical has $0 tooling.
- **[18] Andon Labs — four AI agents run radio stations** — same agent harness as their "SAOs" (semi-autonomous orgs); seed funding to buy songs, must get entrepreneurial; listeners call/tweet/send money. **Revenue terrible**, content chaotic (Gemini paired tragedies w/ pop songs; Grok incoherent; "DJ Claude" told ICE agents to refuse orders). → **Cautionary tale**: fully-autonomous agent-run media = ~$0 revenue + reputational/brand risk. Keep a human in the loop on anything public-facing.
- **[08] Avid — "How to Become an AI Engineer in 2026 (Builder's Roadmap)"** — a massive curated reading list (~90 links): Anthropic engineering blog (effective agents, context engineering, harnesses, skills, sandboxing, evals), LangChain blog/LangGraph, OpenAI/Anthropic cookbooks, Karpathy/Lex/Yannic, eval tooling (Inspect, Braintrust, tau2-bench), infra (Modal, e2b, Temporal, Inngest), memory (Letta, mem0), ECC. → The canonical 2026 agent-engineering curriculum; bookmark as Micah's reference index.
