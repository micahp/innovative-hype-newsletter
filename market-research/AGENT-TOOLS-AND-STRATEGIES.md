# Market Research: AI Agents — Tools & Money Strategies

_Synthesized from 325 AI-agent tweets Micah saved/retweeted (2023–2026). Companion
to the raw data in `AI-AGENT-LIKES.md`. Generated 2026-05-25._

**What this is:** a read on *how people are actually building agents* (the tool
stack) and *how they're trying to make money with them* (the playbooks) — distilled
from the corpus, not the open web. It's a hype-weighted sample (X discourse), so
treat the strategies as "what's being promoted," validated against repetition.

---

## Part 1 — The tool landscape

### A. Coding agents / AI IDEs (the center of gravity)
The single most-saved category. Build software (or whole apps) by directing agents.
- **Leaders:** Cursor (the default; ~$10B valuation, ~$300M ARR), **Replit Agent**
  ($250M raise @ $3B; phone-to-App-Store), **Claude Code** (+ subagents — repeatedly
  called best-in-class for agentic coding), **OpenAI Codex**, **Devin** (Cognition),
  **Factory** (“droids”), **Windsurf**, **Bolt**, **v0**, **Lovable**, GitHub
  Copilot/Spark, **Cline**, Goose (Block/Jack Dorsey, open-source), Emergent, Manus.
- **Workflow patterns people swear by:** "vibe coding," **background/parallel agent
  fleets** (10–12 agents at once), **subagents** as a "startup team" (markdown
  personas: architect, frontend, security), and **PRD → atomic tasks → loop the
  agent** (the "Ralph Wiggum"/AI-Dev-Tasks method) to "ship while you sleep."

### B. Frameworks & orchestration
- **CrewAI**, **AutoGen** / **Magentic-One** (Microsoft), **LangGraph/LangChain**,
  **OpenAI Agents SDK**, **Google ADK**, **Pydantic AI**, **OpenAI Swarm**, **AWS
  Multi-Agent Orchestrator**, **Hermes Agent** (Nous), **Sim** (open-source n8n alt).
- **No-code/low-code:** **Lindy** (agent builder — "replace your PMs, accountants,
  IT"), **n8n** (the workhorse of the money plays — lead-gen, content autopilot).
- **Live debates worth noting:** multi-agent *vs* single (Cognition "don't build
  multi-agents" vs Anthropic's multi-agent research writeup); Cline's "3 mind
  viruses" (avoid multi-agent orchestration, RAG, instruction-overload); **context
  engineering** as the real skill (12-Factor Agents / dexhorthy); Noam Brown:
  "fancy scaffolds will be washed away by scale." Recurring line: **"building agents
  is 5% AI and 100% software engineering."**

### C. Models that power agents (cheap + open-source surging)
- Frontier: **Claude (Opus/Sonnet)** = top for agentic coding; GPT/Codex; **Gemini 3**; Grok.
- **The open-source/cheap wave** (heavily saved): **Kimi K2** (Moonshot — "8x cheaper,"
  long autonomous runs), **DeepSeek V4**, **MiniMax M2.7**, **Qwen3-Coder** (runs
  locally, 1M context), Ring-2.6-1T. Theme: **OSS closing the gap, running locally,
  collapsing cost.** "Your agent is only as good as the data nobody else has."

### D. Browser / computer-use agents
OpenAI **Operator / Agent Mode / CUA**, Anthropic **Computer Use**, Perplexity
**Comet**, **Browser Use**, **Fellou**, **flowithOS**, **Genspark**, **Runner H**
(H Company, $220M), **Proxy** (Convergence), Google's Chrome agent. The pitch:
agents that *do things* in Gmail/Calendar/the web, not just chat.

### E. Voice agents
**ElevenLabs** Conversational AI 2.0, **Vapi**, **Pine**, dental/sales voice agents.
a16z has a standing voice-agent thesis + market map.

### F. Gen-media agents (content/ad production)
**Sora 2, Veo 3, Nano Banana, Seedance 2, Higgsfield, Suno, ElevenLabs**, **glif/
heyglif**, **MakeUGC**, **Calico AI**, **fal** (genmedia CLI), **Muse** (music).
Used to spin up UGC/ads at cents-per-asset.

### G. Agent infra & rails
- **MCP** (Model Context Protocol) — the connective tissue, mentioned constantly;
  Firecrawl (scraping), Tavily (research), e2b (sandboxes), supermemory (memory, $3M),
  tmux-mcp, dedicated "agent computers" ($249).
- **Payments rails (emerging fast):** Google **AP2**, **Visa** agent tokens,
  Coinbase **x402/USDC**, Stripe, Coinbase **AgentKit**. Andreessen: "AI agents are
  going to need money." Onchain: Eigenlayer, Ethereum dAI team, ERC-8004, Farcaster
  wallets, Virtuals/aixbt.

---

## Part 2 — The money strategies (the playbooks)

Ranked roughly by how often they recur and how concrete they are.

1. **The "AI guy" / agency for local businesses** — highest-frequency play.
   Walk into a boring local biz (HVAC, plumbing, roofing, dental), find where they
   "leak money," build an after-hours **voice/call agent** or lead-gen agent. Chris
   Camillo's "$500k/yr" blueprint; the roofing-company hail-damage lead example; the
   $24k/yr dental voice agent. Plus the **productized agency** ("$10M exit in 2 years"
   — agents fix the "scaling humans is a nightmare" problem of 2022 agencies).

2. **Vertical AI-agent micro-SaaS** — pick a "boring, hated, expensive" niche and
   automate it: mortgage pre-approval/underwriting, loan apps, **debt collection**,
   insurance audits, customs/compliance paperwork, SEC-filing extraction, **document
   processing** ("replace a $150k consultant; agencies charge $3–8k/mo"). Explicit
   "build wealth with a vertical AI agent startup *without* VC" thread.

3. **Sell the agent / agent-as-a-service** — e.g. an **SDR agent sold for $7k upfront
   + 20% of revenue**; AI **ad agents** reportedly $122k→$830k/mo; "replace a $100k/yr
   growth manager"; resume-screening and B2B sales agents.

4. **Content / UGC "ad factories"** — agents generating 100s of ads/day (Nano Banana
   + Veo3 + MakeUGC), **clip factories** (1 long video → 8 platform shorts), faceless
   viral-video pipelines. Sells against "$10k/mo agencies" and "$300–800/video."

5. **Build-and-flip / one-person company** — "$100 + an audience > $1M"; clone a
   billion-$ SaaS (Figma/Slack/Airbnb/Netflix clones via Cursor); "build weird
   software that stops the scroll"; 1-person startups worth millions (Lindy framing).

6. **Sell the *playbook* (info products/courses)** — "20 agent ideas that make
   $10k–$1M/mo," "building agents = the hottest side hustle, $10k/mo," agents crash
   courses ($2,500 → free), free **n8n templates** as lead magnets, **in-person AI
   workshops for "corporate boomers"** ($500 × room = ~$10k/mo). Meta-play: monetize
   teaching the above.

7. **Sell tooling/infra to builders** — agent IDEs, MCP toolmakers, memory layers,
   "$249 agent computers," QA agents (TestDriver). Pick-and-shovel plays.

8. **Crypto/onchain agent plays** — launch agent tokens (fair-launch, Pump.fun;
   one $400k-mcap flip netted ~$1k), **trading swarms** + prediction-market arbitrage
   (Kalshi/Polymarket), onchain agent economies. Higher risk/degens.

---

## Part 3 — Meta-trends (where it's going)
- **Doing → managing.** The repeated thesis: everyone becomes a *manager of agent
  fleets* (Alexandr Wang "pod of 10," Amjad Masad "every dev a manager, 100x," Reid
  Hoffman, Kevin Weil "junior→senior architect in a year"). "AI org charts" with a
  chief agent routing to department-head agents.
- **Cost collapse + OSS parity.** Chinese/open models (Kimi, DeepSeek, Qwen, MiniMax)
  at a fraction of frontier cost, runnable locally — commoditizing the model layer.
- **Context engineering > prompting** as the core competency.
- **Agents need money → payment rails** (AP2, Visa, x402) + the "machine economy."
- **Data as the moat** once models commoditize.
- **AI is eating labor** (a16z); Morgan Stanley: ~$1T/yr potential S&P500 savings.

## Part 4 — The skeptic / risk column (don't ignore)
- **Security is a mess:** OpenClaw's 9 CVEs + 2,200 malicious add-ons; 44 agents
  attacked → 62k breaches; prompt-injection/data-exfil (Comet flaw, Copilot Studio
  hijack); a state actor using Claude Code to breach ~30 orgs.
- **Durability doubt:** "the agents everyone's building will be worthless in 18
  months — wrong layer"; "fancy scaffolds washed away by scale."
- **Reality check:** "5% AI, 100% software engineering"; mixed real-world results
  "unless aimed at the right problems."

## Part 5 — Highest-signal sources (who/what to follow)
- **Thesis/analysis:** a16z (voice agents, "AI eating labor," CUAs), Anthropic
  (multi-agent research writeup), OpenAI guides ("build agents from scratch"),
  Balaji, DeepMind ("Virtual Agent Economies" paper).
- **Builders/operators:** levelsio, Amjad Masad (Replit), Aravind Srinivas
  (Perplexity), CrewAI (João Moura), LangChain, Cline, Factory (Matan Grinberg),
  Lindy, dwr (Farcaster), Phil Chen.
- **Resolved standout resources** (full list in `AI-AGENT-LIKES.md`): Microsoft
  Research **Magentic-One**, **DeepCode** (HKUDS), **12-Factor Agents** (dexhorthy),
  Anthropic "How we built our multi-agent research system," fal **genmedia CLI**,
  **ai-dev-tasks** (snarktank), **TestDriver**, Google Cloud **AP2** announcement.

---

## Caveat
Single-timeline, hype-weighted sample — strong on what's *promoted* in AI-X circles,
weak on independent validation of the income claims (treat $ figures as marketing
until verified). Best used as a **map of the space and the prevailing playbooks**,
then pressure-test the 2–3 strategies that fit Micah's "mostly hands-off internet
income" goal (see `08-synthesis-and-recommendations.md`).
