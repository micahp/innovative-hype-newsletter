# Scraped content

**Source:** https://www.reddit.com/r/AIAgentsInAction/comments/1t84rlc/this_guy_won_the_anthropic_hackathon_solo_then_he/
**Title:** This guy Won the Anthropic Hackathon Solo. Then He Open-Sourced the Stack includes: 38 Agents, 156 Skills, 1,282 Security Tests : r/AIAgentsInAction

**Screenshot:** [11-reddit-post-1t84rlc.png](./11-reddit-post-1t84rlc.png)
**Scraped at:** 2026-05-26T00:02:07.763Z

## Post

This guy Won the Anthropic Hackathon Solo. Then He Open-Sourced the Stack includes: 38 Agents, 156 Skills, 1,282 Security Tests

A solo dev won the Anthropic hackathon by shipping a product in eight hours with Claude Code. Prize: $15,000. He open-sourced the repo and it sits at 153,000+ stars on GitHub.

The repo is Everything Claude Code (ECC). Claude Code with 38 specialized agents, 156 skills, 72 commands, and a security scanner with 1,282 tests.

Install selectively

# Plugin install
/plugin marketplace add affaan-m/everything-claude-code
/plugin install everything-claude-code@everything-claude-code

# Or pick what you need
ecc install --profile developer \
  --with lang:typescript \
  --with agent:security-reviewer \
  --without skill:continuous-learning

Loading all 156 skills wastes context. Pick your stack, drop the rest.

Agents that do one job

planner             → breaks down task, delegates to specialists
security-reviewer   → scans for vulnerabilities pre-ship
typescript-reviewer → catches TS antipatterns
code-reviewer       → 5 parallel checks
debugger            → root-cause analysis

Coverage spans 12 language ecosystems. The planner agent handles orchestration: hand it a ticket, it decomposes the work and routes to specialists.

Skills load on demand

/plan          → structured task planning
/tdd           → test-driven workflow
/security-scan → AgentShield audit
/quality-gate  → ship-readiness check
/simplify      → refactor for readability

Stack-specific ones too: nextjs-turbopack, bun-runtime, pytorch-patterns, mcp-server-patterns.

AgentShield

This is the part most people skip and where ECC pays for itself.

# Quick scan, no install
npx ecc-agentshield scan

# Auto-fix safe issues
npx ecc-agentshield scan --fix

# Three Opus 4.6 agents in red-team pipeline
npx ecc-agentshield scan --opus --stream

The --opus flag runs three Claude Opus 4.6 agents:

Attacker  → looks for exploit chains
Defender  → evaluates defenses
Auditor   → synthesizes a prioritized risk report

What gets scanned:

CLAUDE.md     → hardcoded secrets, injection vectors
settings.json → misconfigured permissions
MCP configs   → server risks (25+ known CVEs)
Hooks         → injection analysis
Agents        → prompt injection, privilege escalation
Skills        → supply chain verification

Sample output:

Grade: B+
Critical: 0 | High: 2 | Medium: 5 | Low: 3

❌ HIGH: Hardcoded API key in CLAUDE.md:15
   Fix: Move to environment variable

Drops into continuous integration so any pull request changing an agent config gets audited.

The learning layer

Stock Claude Code starts each session blank. ECC's continuous learning watches your sessions and builds patterns:

Session 1:  you fix an async error pattern    (confidence: 0.3)
Session 5:  same pattern, refined             (confidence: 0.6)
Session 10: stable, applied automatically     (confidence: 0.9)

A knowledge layer that persists across sessions, sharpens with use. After two or three weeks, Claude writes in your conventions instead of generic large language model defaults.

Three repos that close ECC's gaps

claude-mem for cross-session memory (github.com/thedotmack/claude-mem). Five lifecycle hooks, SQLite storage, web viewer at localhost:37777.

/plugin marketplace add thedotmack/claude-mem
/plugin install claude-mem

Superpowers for forced planning (github.com/obra/superpowers). ECC's agents will write 400 lines without a plan. Superpowers makes them think first.

/plugin marketplace add obra/superpowers
/plugin install superpowers

CLAUDE.md rules for predictable agent behavior. All 38 agents read the file. Drop in:

- Run tests before marking task complete
- Never create files outside the project directory
- Ask before deleting any file
- Explain reasoning before writing code
- If unsure, ask. Don't guess.

Easy setup

# 1. Install ECC for your stack
/plugin install everything-claude-code@everything-claude-code

# 2. Memory
/plugin install claude-mem

# 3. Planning discipline
/plugin install superpowers

# 4. Security scan
npx ecc-agentshield scan --fix

# 5. Drop behavior rules into CLAUDE.md

## Comments

### Anonymous

AutoModerator
•
16d ago

### Anonymous

Do you think it would be useful to link the github repo?

### Anonymous

https://github.com/affaan-m/everything-claude-code

### Anonymous

I had the same thought. Get the bottom of the write-up and the biggest question: Someone sat down and wrote all of this, but didn't think it was worth taking 2 seconds to link to the repo they just spent all this time writing about?!? 🤨

### Anonymous

I mean Claude clearly wrote this, but I’m fine with that as it’s clearly based off some really good base data the poster absolutely wrote up.

Claude just helped make it presentable and easy to read.

Saving this shit for sure

### Anonymous

Your instinct is correct and you were right to push back on this. I owe you a link to the GitHub repository.

### Anonymous

Now get some rest. It’s been a long day

### Anonymous

this entire combobulation will become irrelevant and incompatible with Claude itself in like 6 months

if you need 156 skills and 38 agents and 17 layers of review and containment, the complexity of rapid drift at the frontier will just swallow you whole

### Anonymous

Also probably costs like $400 per prompt and $2000 to run for 12 seconds.

### Anonymous

Also this: “if unsure, ask, don’t guess”

Who in their right mind believes this does anything? 😂

### Anonymous

It already is. Lot of this is built into Claude Code already. This is quite old.

### Anonymous

Prize: $15,000.

Job as a key AI developer at Anthropic or other LLM, priceless. (Or maybe just high 6 figs)

### Anonymous

Probably cost the same in opus tokens making the readme.md file

### Anonymous

I applied a couple years ago and they were offering $400k/yr cash. So, yeah.

### Anonymous

What does it do?

### Anonymous

[deleted]
•
15d ago

### Anonymous

burns token.

### Anonymous

Just heard of it. Sounds interesting!

### Anonymous

Jack_smith33
•
16d ago

### Anonymous

What product did he build?

### Anonymous

Debt generator with an optimal pain-reward ratio

### Anonymous

A todo list app

### Anonymous

I am surprised that people didn’t know about it. It’s old news. And claude always tells me I don’t need to use it y🤣

### Anonymous

Or you can just ask Claude to do it without skills. A lot of this stuff is actually harmful now.

### Anonymous

Is anyyone not usign everything-claude already? I mean...it's not new....

### Anonymous

This is awesome

### Anonymous

Has anyone else found that claude-mem uses heaps of API tokens? Way more than expected.

### Anonymous

Finally some real agent systems.

### Anonymous

The 1282 security tests are InsAIts tests FROM MY fork into ECC. He didn't want to recognize the InsAIts value and the fact that improve Claude work and make the session longer and instead he renamed ny fork and took the credit for what InsAIts do. Bellow my discussion with Affan. https://github.com/Nomadu27/InsAIts-public *

### Anonymous

YUYbox
•
15d ago
1 more reply

### Anonymous

To be fair the prize was paid out in Anthropic credits

### Anonymous

Fake money but real (tech) debt.

### Anonymous

Theres a few decent one off items but overall it’s just someone else’s harness setup. A lot of overlap.

### Anonymous

lol.

### Anonymous

1282 security tests is the right impulse and the bit that gets missed is how unmaintainable that count gets the moment the agent's skill or tool surface changes. hand-written tests at that volume turn into a graveyard within a quarter. the move that actually scales is generating the test bodies from a traversal of the agent's capability tree, so when a tool changes the test rewrites itself instead of failing silently. otherwise you end up with 1282 tests and only the loudest fifty still mean anything. written with ai

## Media

- https://styles.redditmedia.com/t5_fd586i/styles/communityIcon_uihtizy80esg1.png?width=96&height=96&frame=1&auto=webp&crop=96%3A96%2Csmart&s=c9f7bbe9dd52d206801d0013201f5bffb1ef4d32
- https://preview.redd.it/i39jfyhd1izg1.png?auto=webp&s=1228cbd2b5d2e7493b04670194aa20280cb9ed74
- https://styles.redditmedia.com/t5_1yz875/styles/profileIcon_klqlly9fc4l41.png?width=64&height=64&frame=1&auto=webp&crop=64%3A64%2Csmart&s=4cd002de4de73dc33950158eb385a54026d627e1
- https://styles.redditmedia.com/t5_21mxoz/styles/profileIcon_6vdizl7sbsn31.png?width=64&height=64&frame=1&auto=webp&crop=64%3A64%2Csmart&s=906bcfa4ea31e0d3b95743be2356a6f4456406f5
- https://styles.redditmedia.com/t5_et0q8/styles/profileIcon_txtk9ldnpk4a1.jpg?width=64&height=64&frame=1&auto=webp&crop=64%3A64%2Csmart&s=7620b166daacb1f775b8d3c55845d4b6c4990ded
- https://styles.redditmedia.com/t5_pceuh/styles/profileIcon_re50n8n463ob1.png?width=48&height=48&frame=1&auto=webp&crop=48%3A48%2Csmart&s=d9c7c554bf0d8c69402093071554e2b95e774500
- https://preview.redd.it/5yha9sw3oazg1.png?width=640&crop=smart&auto=webp&s=da44db839e277d3d0a51d4b62c8a0253a2d072b3
- https://preview.redd.it/chfz1kx3oazg1.png?width=640&crop=smart&auto=webp&s=8ba2a636201fb8fd1462032fa1dabd65e40f0fd9
- https://preview.redd.it/x0z0vzx3oazg1.png?width=640&crop=smart&auto=webp&s=77580a131a6bcfa51b3e2af0cbd5302539c9afdc
- https://preview.redd.it/sgjuyky3oazg1.png?width=640&crop=smart&auto=webp&s=3ead6ff51eccbf9893e8abdd397dea19c2d70809
- https://preview.redd.it/lmjtnyy3oazg1.jpg?width=640&crop=smart&auto=webp&s=291fa12eabcf5a1fdc6a466c1f255d3a00fd595b
- https://styles.redditmedia.com/t5_aor7ef/styles/profileIcon_vhx0shyf5ttc1.jpeg?width=64&height=64&frame=1&auto=webp&crop=64%3A64%2Csmart&s=4439920bc53193458f974f29cf77a7a2cc4b95a8
- https://styles.redditmedia.com/t5_e2atnn/styles/profileIcon_uuvs8a9ea1se1.png?width=64&height=64&frame=1&auto=webp&crop=64%3A64%2Csmart&s=88b4a32e45b7aacbd80eaf26cdb9422f72dd7585
- https://preview.redd.it/zkepwca1s4og1.png?auto=webp&s=54a75df92e5fb4bba9f32a145e70ebd30047b92a
- https://styles.redditmedia.com/t5_d6br6/styles/profileIcon_06emvbudndj71.png?width=64&height=64&frame=1&auto=webp&crop=64%3A64%2Csmart&s=665fd860d65913cf892c45a63a2e1d72dfd76163
- https://styles.redditmedia.com/t5_cmgsn/styles/profileIcon_v69hcz1q8nab1.jpg?width=64&height=64&frame=1&auto=webp&crop=64%3A64%2Csmart&s=541218c7ddf473d509ed09df71dc5c0c07525363
- https://preview.redd.it/this-guy-won-the-anthropic-hackathon-solo-then-he-open-v0-aejj8laofb0h1.jpeg?width=1080&format=pjpg&auto=webp&s=43905132395e93fa63ccb0284764543d2f40ace9
- https://styles.redditmedia.com/t5_5wa5ww/styles/communityIcon_wyopomb2xb0a1.png?width=48&height=48&frame=1&auto=webp&crop=48%3A48%2Csmart&s=993cee5fff1a15460b937e402b9397420f150b5a
- https://styles.redditmedia.com/t5_d5w4yc/styles/profileIcon_yz8831kuzyge1.jpg?width=48&height=48&frame=1&auto=webp&crop=48%3A48%2Csmart&s=dd3d834b78867ca3800ed6d10b25a4daab6dbeff
- https://external-preview.redd.it/153T5oINSGAU9Lnv2bO-MH5p_4vdxbsN6jEscM1q7BY.png?width=108&crop=smart&format=pjpg&auto=webp&s=b38beb27de152fc82e298677920bf534576f794e
- https://styles.redditmedia.com/t5_81eyvm/styles/communityIcon_cumnsvx9kzma1.png?width=48&height=48&frame=1&auto=webp&crop=48%3A48%2Csmart&s=a65b055886461d9f520fb038a7ab11356a72b896
- https://styles.redditmedia.com/t5_5nsj5k/styles/communityIcon_nrzwex66tmjb1.png?width=48&height=48&frame=1&auto=webp&crop=48%3A48%2Csmart&s=d2eba576be00986f38d02af68f4ed2ffdbc25ca6
- https://b.thumbs.redditmedia.com/SNHPOt67Y9JQ1Aflh5fnm5xzvPjSfD1X_YMPcIkcx6c.jpg
- https://styles.redditmedia.com/t5_dp6k3k/styles/communityIcon_g3ehwz8f4sbf1.jpg?width=48&height=48&frame=1&auto=webp&crop=48%3A48%2Csmart&s=3078fec0c87d7b6f9bfe74b2932791ef497eaffb
- https://preview.redd.it/rgwzo56tlxxg1.jpeg?width=140&height=140&crop=1%3A1%2Csmart&auto=webp&s=942af516c37e0f1e9952c3a0b951ffdab8c867f5
- https://styles.redditmedia.com/t5_e2rxrm/styles/communityIcon_c4b81khvimyg1.png?width=48&height=48&frame=1&auto=webp&crop=48%3A48%2Csmart&s=81ef40f18874cc9855342c0fa6ca8df6f53d0d3c
- https://preview.redd.it/mvbyrznehdog1.png?width=140&height=140&crop=1%3A1%2Csmart&auto=webp&s=88e1d700929a02e839f5f4fceb6fe3054615cac2
- https://styles.redditmedia.com/t5_ev2z02/styles/communityIcon_0mrio0jnb6bf1.jpg?width=48&height=48&frame=1&auto=webp&crop=48%3A48%2Csmart&s=e4fe928419103b7d8bb5f774342ecfd05ccc2eb9
- https://preview.redd.it/df3ydzqwbelg1.png?width=140&height=140&crop=1%3A1%2Csmart&auto=webp&s=e1d8b8c4750eff07868eee9ebdaf666ec511c1dd
- https://styles.redditmedia.com/t5_7tpn6r/styles/communityIcon_vw08a423ptxa1.png?width=48&height=48&frame=1&auto=webp&crop=48%3A48%2Csmart&s=860301d17bf9fdde358e2d2490bbb192d141f397
- https://preview.redd.it/2m53eiaq8pkg1.png?width=140&height=140&crop=1%3A1%2Csmart&auto=webp&s=9b62cc23681f9d48c25379dc97ca6462c3641194
- https://styles.redditmedia.com/t5_2y46a/styles/communityIcon_qoggx8r4r8m31.png?width=48&height=48&frame=1&auto=webp&crop=48%3A48%2Csmart&s=709e7429a1de4851591bc1a4dec1c9dcb20e01c0
- https://external-preview.redd.it/d3oPtTiU-SbRBlF-kR2cJykQNHqwVkuuyJhFDcaPPxQ.jpeg?width=140&height=93&auto=webp&s=830849891d4074522fc384a422389d537ec304fd
- https://styles.redditmedia.com/t5_8f6xyy/styles/communityIcon_cifdzj1blbsc1.png?width=48&height=48&frame=1&auto=webp&crop=48%3A48%2Csmart&s=bbb77ca62d2240146be91bd43257c521a96152d3
- https://preview.redd.it/25btz09yv5yg1.png?width=140&height=140&crop=1%3A1%2Csmart&auto=webp&s=1d2ffbf8f0950761b54826779c93b59d4d02fcc1
- https://styles.redditmedia.com/t5_95egkp/styles/communityIcon_tg782nsbpdjb1.png?width=48&height=48&frame=1&auto=webp&crop=48%3A48%2Csmart&s=4cf913125e1a09e4733b014e89e9b635a2d3a13f
- https://styles.redditmedia.com/t5_7t8hvt/styles/communityIcon_97yk0vsmp4cf1.png?width=48&height=48&frame=1&auto=webp&crop=48%3A48%2Csmart&s=553dec879c203855da3925cf00c120b370bb0ca0
- https://styles.redditmedia.com/t5_fgw1tz/styles/communityIcon_l23h7m9g2o3g1.png?width=48&height=48&frame=1&auto=webp&crop=48%3A48%2Csmart&s=981e81893b3a88e8d5f54547e5e7a8a8f3c1098c
- https://external-preview.redd.it/J63qmtHViaiBwDQri96M7SrbtJPnMpdMt_TVlRiQUYQ.jpeg?width=140&height=73&auto=webp&s=2f369df1a8d5498296fbf9a10cf21dbb40076d46
- https://styles.redditmedia.com/t5_zb6bc/styles/communityIcon_cwit35unflwc1.png?width=48&height=48&frame=1&auto=webp&crop=48%3A48%2Csmart&s=6b277a896f788209d4d258693266e440cdd674ef
- https://styles.redditmedia.com/t5_fxg7lp/styles/communityIcon_y6zf5lo8w02g1.png?width=48&height=48&frame=1&auto=webp&crop=48%3A48%2Csmart&s=dd7af082667ec76670fe2587e3890dca219bcb54
- https://styles.redditmedia.com/t5_88cu6z/styles/communityIcon_eb9g26zoi7qe1.png?width=48&height=48&frame=1&auto=webp&crop=48%3A48%2Csmart&s=2a3e4cb72d0abd13b6cb50ba51042461061feaa9
- https://styles.redditmedia.com/t5_64hpn8/styles/communityIcon_aqqdq8z6q5t81.jpg?width=48&height=48&frame=1&auto=webp&crop=48%3A48%2Csmart&s=810de4fea7897225c748942084544745b8f74fdc
- https://styles.redditmedia.com/t5_gb11mn/styles/communityIcon_qhrjttsmufgg1.png?width=48&height=48&frame=1&auto=webp&crop=48%3A48%2Csmart&s=b6da426a0c73f5ef184816ce44faa91a95a2c9c1
- https://styles.redditmedia.com/t5_fxhgvo/styles/communityIcon_gzfsk8pic12g1.png?width=48&height=48&frame=1&auto=webp&crop=48%3A48%2Csmart&s=0f982495f2263bc19f3610b0a2c3bde3988239e9
- https://styles.redditmedia.com/t5_emk2pb/styles/communityIcon_6gi1cclb0cyf1.png?width=48&height=48&frame=1&auto=webp&crop=48%3A48%2Csmart&s=0b1fb7cd799d349cf5ff46fc753d9bd59058b3ba
- https://id.rlcdn.com/472486.gif
