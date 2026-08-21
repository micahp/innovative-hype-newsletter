# Feed Gap Map — voice vs. article coverage

Cross-reference of the @geoppls + @innovativehype tweet corpus (the
Innovative Hype voice) against the article feed (web/articles.json).

Generated 2026-08-21. Method: keyword-count tweets per topic vs. keyword-count
articles per topic.

## The gap table

| Topic | Tweets | Articles | Verdict |
|---|---|---|---|
| AI tools / building | 32 | 6 | **BIG GAP** — voice is a builder, feed barely covers dev tools |
| Cities / urbanism | 67 | 36 | **GAP** — the #1 voice theme, half-covered |
| Media / platform power | 61 | 18 | **GAP** — who owns the platforms, 3x under-covered |
| Prediction markets | 25 | 6 | **GAP** — the voice is ahead of the news on this |
| Family / kids | 63 | 37 | gap — partially covered |
| Creator / ownership | 46 | 25 | gap — partially covered |
| Sports | 26 | 31 | ok |
| Food / health | 9 | 13 | ok |
| Crypto / markets | 43 | 77 | over-covered — feed pushes it, voice lukewarm |
| Sovereignty / gov | 28 | 67 | over-covered |
| Entertainment | 21 | 47 | over-covered |

## What the voice actually is (from the tweets)

- **AI tools / building**: "Fable 5 planner + orchestrator", "Opus 5 builds
  Blender MCP", "Minimax-H3 Prompt Agent Skill", "will I now CTO Pirate
  Nation and take the open source material" — a BUILDER. Ships tools,
  agents, open-source. The feed's 6 dev-tool articles are nowhere near this.
- **Cities / urbanism**: "If I'm not passing by a cemetery, then the city is
  too big", "In one California town, Flock misread license plates 71% of the
  time" — Texas / anti-big-city / car-culture voice.
- **Media / platform power**: "tiktok is the craziest platform of all time...
  ai integration for videos, try on's in the shop" — platform-watcher energy.
- **Prediction markets**: Kalshi/Polymarket posts — the voice is ahead of
  the article feed here.

## Feed additions to close the gaps

### AI tools / building (biggest gap)
- Hacker News Show HN feed — `https://hnrss.org/show` (launches, dev tools)
- Indie Hackers — `https://www.indiehackers.com/feed`
- Product Hunt (via RSSHub) — `https://rsshub.app/product-hunt/today`

### Cities / urbanism
- Connect CRE Austin — `https://www.connectcre.com/feed?story-market=austin`
- Connect CRE Texas — `https://www.connectcre.com/feed?story-market=texas`
- HousingWire — `https://www.housingwire.com/category/real-estate/feed`
- Realtor.com news — `https://www.realtor.com/news/feed`

### Media / platform power
- Platformer — `https://www.platformer.news/` (Casey Newton, Substack RSS
  via `https://www.platformer.news/feed` if available)
- The Verge (already have AI feed; add main feed)

### Prediction markets
- Kalshi/Polymarket news via existing Decrypt/CoinDesk (partial) — plus
  poll_social.py already collects the accounts every 2h; the justin.jsonl
  corpus is the prediction-market signal. Consider wiring corpus → feed.

## Notes

- The `Cities, housing and where America lives` narrative signature exists
  in brief.py (voice_weight 1.0) but currently has no stories — the feed
  gap means it never fires. Add the feeds above and it will.
- Crypto over-coverage is a *weighting* issue, not a feed issue: the voice
  is selective about crypto (34/509 posts), so crypto stories shouldn't
  auto-dominate the brief. The voice_weight (0.7) handles this.
