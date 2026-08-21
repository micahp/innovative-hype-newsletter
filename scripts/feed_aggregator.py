#!/usr/bin/env python3
"""feed_aggregator.py — fetch all 42 RSS feeds, output JSON for the web page.

Handles blocking: rotates User-Agent, short timeout, per-feed isolation,
RSSHub fallbacks for blocked sources. Failed feeds are logged and skipped.

Ranking: every article gets a weighted editorial score
  score = source_tier + recency_decay + pillar_fit
with a listicle/opinion noise penalty. The top N are flagged `top: true`
and rendered in the TOP NEWS section. See OPTIONS discussion (2026-08-20):
option 2 (weighted editorial score) + option 3 (LP-style noise filter) as
a negative modifier. Deterministic, no LLM, reruns every 2h via cron.

Output: web/articles.json = {"updated": ISO, "feeds_ok": N, "feeds_fail": N, "articles": [...]}
"""

import feedparser
import json
import os
import re
import ssl
import time
import urllib.request
import urllib.error

# Optional: full-article fetch for teaser-only feeds. Imported lazily so the
# aggregator still works if trafilatura isn't installed.
try:
    import trafilatura
except ImportError:
    trafilatura = None
from datetime import datetime, timezone

CORPUS = os.path.join(os.path.dirname(__file__), "..", "corpus")
WEB = os.path.join(os.path.dirname(__file__), "..", "web")

# Ensure SSL works for all feeds
ssl_context = ssl.create_default_context()

UA_ROTATE = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "feedparser/6.0.11 +https://github.com/kurtmckee/feedparser",
]

FEEDS = [
    # TECHNOLOGY
    {"name": "TechCrunch AI", "url": "https://techcrunch.com/category/artificial-intelligence/feed/", "category": "technology"},
    {"name": "The Verge AI", "url": "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml", "category": "technology"},
    {"name": "VentureBeat AI", "url": "https://venturebeat.com/category/ai/feed/", "category": "technology"},
    {"name": "MIT Technology Review", "url": "https://www.technologyreview.com/feed/", "category": "technology"},
    {"name": "Wired", "url": "https://www.wired.com/feed/latest/rss", "category": "technology", "fallback": "https://rsshub.app/wired"},
    {"name": "Ars Technica", "url": "https://feeds.arstechnica.com/arstechnica/index", "category": "technology"},
    {"name": "The Defiant", "url": "https://newsletter.thedefiant.io/feed", "category": "technology"},
    {"name": "Decrypt", "url": "https://decrypt.co/feed", "category": "technology"},
    {"name": "CoinDesk", "url": "https://www.coindesk.com/arc/outboundfeeds/rss/", "category": "technology"},
    {"name": "Google AI Blog", "url": "https://blog.research.google/feeds/posts/default", "category": "technology"},
    {"name": "OpenAI Blog", "url": "https://openai.com/blog/rss.xml", "category": "technology"},
    {"name": "DeepMind Blog", "url": "https://deepmind.google/discover/blog/feed.xml", "category": "technology", "fallback": "https://rsshub.app/google/deepmind"},
    {"name": "Anthropic Research", "url": "https://www.anthropic.com/research/feed", "category": "technology", "fallback": "https://rsshub.app/anthropic"},
    {"name": "Meta AI Blog", "url": "https://ai.meta.com/blog/feed/", "category": "technology", "fallback": "https://rsshub.app/meta-ai"},
    {"name": "Import AI", "url": "https://importai.substack.com/feed", "category": "technology"},
    {"name": "Hacker News (AI)", "url": "https://hnrss.org/frontpage?q=AI+OR+ML+OR+LLM+OR+GPT+OR+Claude+OR+Gemini", "category": "technology", "fallback": "https://rsshub.app/hacker-news/top"},
    # BUSINESS
    {"name": "CNBC", "url": "https://www.cnbc.com/id/100003114/device/rss/rss.html", "category": "business"},
    {"name": "Reuters Business", "url": "https://www.rss.reuters.com/news/business", "category": "business", "fallback": "https://rsshub.app/reuters"},
    {"name": "Economist", "url": "https://www.economist.com/business/rss.xml", "category": "business"},
    {"name": "HN (Business)", "url": "https://hnrss.org/frontpage?q=business+OR+startup+OR+IPO+OR+acquisition", "category": "business", "fallback": "https://rsshub.app/hacker-news/top"},
    {"name": "TechCrunch", "url": "https://techcrunch.com/feed/", "category": "business"},
    {"name": "Bitcoin Magazine", "url": "https://bitcoinmagazine.com/feed", "category": "business"},
    {"name": "CoinDesk Markets", "url": "https://www.coindesk.com/markets/feed/", "category": "business", "fallback": "https://rsshub.app/coindesk/news"},
    # SPORTS
    {"name": "ESPN", "url": "https://www.espn.com/espn/rss/news", "category": "sports", "fallback": "https://rsshub.app/espn"},
    {"name": "Sports Business Journal", "url": "https://www.sbj.com/feed/", "category": "sports", "fallback": "https://rsshub.app/sbj"},
    {"name": "The Athletic", "url": "https://theathletic.com/rss/", "category": "sports", "fallback": "https://rsshub.app/the-athletic"},
    {"name": "Bleacher Report", "url": "https://bleacherreport.com/articles/feed", "category": "sports", "fallback": "https://rsshub.app/bleacher-report"},
    {"name": "Front Office Sports", "url": "https://frontofficesports.com/feed/", "category": "sports"},
    {"name": "HN (Sports)", "url": "https://hnrss.org/frontpage?q=sports+OR+NBA+OR+NFL+OR+MLB+OR+UFC", "category": "sports", "fallback": "https://rsshub.app/hacker-news/top"},
    # CULTURE
    {"name": "Highsnobiety", "url": "https://www.highsnobiety.com/feed/", "category": "culture"},
    {"name": "Hypebeast", "url": "https://hypebeast.com/feed", "category": "culture", "fallback": "https://rsshub.app/hypebeast"},
    {"name": "Complex", "url": "https://www.complex.com/feed", "category": "culture", "fallback": "https://rsshub.app/complex"},
    {"name": "Billboard", "url": "https://www.billboard.com/feed/", "category": "culture"},
    {"name": "Rolling Stone", "url": "https://www.rollingstone.com/feed/", "category": "culture"},
    {"name": "Pitchfork", "url": "https://pitchfork.com/rss/news/", "category": "culture"},
    {"name": "Stereogum", "url": "https://www.stereogum.com/feed/", "category": "culture"},
    {"name": "The FADER", "url": "https://www.thefader.com/feed/rss", "category": "culture", "fallback": "https://rsshub.app/the-fader"},
    {"name": "XXL", "url": "https://www.xxlmag.com/feed/", "category": "culture"},
    {"name": "Deadline", "url": "https://deadline.com/feed/", "category": "culture"},
    {"name": "Variety", "url": "https://variety.com/feed/", "category": "culture"},
    {"name": "Hollywood Reporter", "url": "https://www.hollywoodreporter.com/feed/", "category": "culture"},
    # CROSS
    {"name": "HN (General)", "url": "https://hnrss.org/frontpage", "category": "technology", "fallback": "https://rsshub.app/hacker-news/frontpage"},
    # GAP-CLOSING FEEDS (2026-08-21, from FEED-GAP-MAP.md)
    # AI tools/building — the voice is a builder, feed barely covers dev tools
    {"name": "HN (Show)", "url": "https://hnrss.org/show", "category": "technology", "fallback": "https://rsshub.app/hacker-news/show"},
    {"name": "Indie Hackers", "url": "https://www.indiehackers.com/feed", "category": "technology"},
    # Cities/urbanism — the #1 voice theme, half-covered
    {"name": "Connect CRE Austin", "url": "https://www.connectcre.com/feed?story-market=austin", "category": "business"},
    {"name": "Connect CRE Texas", "url": "https://www.connectcre.com/feed?story-market=texas", "category": "business"},
    {"name": "HousingWire", "url": "https://www.housingwire.com/category/real-estate/feed", "category": "business"},
    # Media/platform power — who owns the platforms
    {"name": "Platformer", "url": "https://www.platformer.news/feed", "category": "culture"},
]

# === RANKING: source tiers ===
# T1 = flagship editorial / wire-grade (can anchor TOP NEWS)
# T2 = strong beat coverage (solid, worth a top slot on a good story)
# T3 = niche / secondary (still valuable, rarely the lead)
# T4 = aggregator / generic (HN frontpage: signal but not authority)
SOURCE_TIERS = {
    # TECHNOLOGY
    "MIT Technology Review": 1,
    "Ars Technica": 1,
    "TechCrunch AI": 2,
    "The Verge AI": 2,
    "VentureBeat AI": 2,
    "The Defiant": 2,
    "Decrypt": 2,
    "OpenAI Blog": 1,
    "Google AI Blog": 2,
    "Import AI": 2,
    "Wired": 1,
    "DeepMind Blog": 2,
    "Anthropic Research": 2,
    "Meta AI Blog": 3,
    "Hacker News (AI)": 3,
    "CoinDesk": 2,
    # BUSINESS
    "CNBC": 1,
    "Economist": 1,
    "Reuters Business": 1,
    "TechCrunch": 1,
    "Bitcoin Magazine": 2,
    "HN (Business)": 3,
    "CoinDesk Markets": 2,
    # SPORTS
    "ESPN": 1,
    "Front Office Sports": 1,
    "Sports Business Journal": 1,
    "The Athletic": 1,
    "Bleacher Report": 2,
    "HN (Sports)": 3,
    # CULTURE — entertainment trade press is NOT the Innovative Hype culture
    # beat (streetwear, music, creator economy). Demoted to T2 so a celebrity
    # spat can't anchor TOP NEWS; Highsnobiety/Pitchfork/FADER (the actual
    # culture-beat press) stay T2 but their stories fit the pillars better.
    "Highsnobiety": 2,
    "Hypebeast": 2,
    "Complex": 2,
    "Billboard": 2,
    "Rolling Stone": 2,
    "Pitchfork": 2,
    "Stereogum": 2,
    "The FADER": 2,
    "XXL": 2,
    "Deadline": 2,
    "Variety": 2,
    "Hollywood Reporter": 2,
    # CROSS
    "HN (General)": 4,
    # GAP-CLOSING (2026-08-21)
    "HN (Show)": 2,
    "Indie Hackers": 2,
    "Connect CRE Austin": 2,
    "Connect CRE Texas": 2,
    "HousingWire": 2,
    "Platformer": 1,
}

# Negative markers — LP-style news-vs-noise filter. Any hit hard-caps the score.
NOISE_PATTERNS = [
    r"\b(listicle|roundup|recap|best of|top \d+|n best|ways to)\b",
    r"\b(review|reviewed|hands-?on|we tried|i tried)\b",
    r"\b(opinion|op-?ed|column|hot take|take:)\b",
    r"\b(how to|guide|tutorial|explainer|cheat sheet|primer)\b",
    r"\b(5 |10 |25 |50 |100 )(things|reasons|ways|signs|lessons)\b",
    r"\b(q&a|podcast episode|newsletter)\b",
    # Entertainment chatter — interview/recap/breakdowns are texture, not top news
    r"\b(interview|interviews|break down|breaks down|recap|watch now|first look|trailer)\b",
    # Celebrity/personality drama — gossip is not Innovative Hype culture
    r"\b(says he refused|says she refused|weighs in|opens up|reveals|dishes on|slams|rips|blasts|feud)\b",
    r"\b(remembers|tribute|honors|memorializes)\b",
]

# Pillar keywords from EDITORIAL_MAP.md (title+summary match, word-boundary).
# Each entry maps a pillar to the keyword list that signals it.
PILLAR_KEYWORDS = {
    "sovereignty": ["sovereignty", "self-custody", "self custody", "de-dollarization", "de-dollarisation", "sound money", "censorship", "surveillance", "data privacy", "financial freedom", "sanctions"],
    "ownership": ["ownership", "creator", "creators", "royalt", "rent-seeking", "middleman", "middlemen", "platform fee", "take rate", "commission", "upside"],
    "ai-defining": ["ai", "artificial intelligence", "llm", "gpt", "claude", "gemini", "sora", "agent", "model release", "open source model", "deepseek", "mistral", "openai", "anthropic", "machine learning", "robotics", "automation", "agi"],
    "build-consume": ["build", "builder", "making", "maker", "creators", "startup", "founder", "founders", "entrepreneur", "side project", "indie", "open source", "diy"],
    "community-moat": ["community", "network effect", "creators", "fans", "fandom", "audience", "subscribers", "members", "guild", "co-op", "cooperative"],
    "culture-onchain": ["nft", "on-chain", "onchain", "web3", "blockchain", "ethereum", "solana", "base", "token", "tokenization", "digital art", "metaverse", "crypto"],
    "tech-optimism": ["future", "breakthrough", "next generation", "frontier", "innovation", "disrupt", "pioneer", "milestone", "record"],
    "self-mastery": ["discipline", "consistency", "training", "workout", "stoic", "mindset", "compounding", "grind", "hustle", "routine", "longevity", "peak performance"],
    "access-uplift": ["democrati", "access", "opportunity", "generation", "uplift", "inclusive", "financial inclusion", "financial literacy", "learn", "education"],
}

# How long until a story is half as relevant (hours). 36h keeps a morning
# briefing story viable into the evening without drowning in old news.
RECENCY_HALF_LIFE_HOURS = 36

# How many top stories to flag.
TOP_N = 7

# How many top-scored stories get full-text fetched (teaser-only feeds).
FETCH_BODY_TOP_N = 15

def _match_count(text, patterns):
    """Count distinct patterns found in text (word-boundary regex)."""
    low = text.lower()
    found = set()
    for pat in patterns:
        try:
            if re.search(pat, low):
                found.add(pat)
        except re.error:
            continue
    return len(found)

def _pillar_hits(title, summary):
    """Return set of pillar names matched in title+summary."""
    haystack = f"{title} {summary}".lower()
    hits = set()
    for pillar, kws in PILLAR_KEYWORDS.items():
        for kw in kws:
            if re.search(rf"\b{re.escape(kw)}\b", haystack):
                hits.add(pillar)
                break
    return hits

def score_article(article):
    """Weighted editorial score for one article dict. Adds _score, _pillars,
    _noise to the dict in place. score = source_tier + recency_decay + pillar_fit
    - noise penalty (hard cap).

    Weights (v1, tuned 2026-08-20):
      source_tier: T1=3, T2=2, T3=1, T4=0.5  (authority helps, doesn't dominate)
      recency:     2.0 * 0.5^(age/36h)       (half-life 36h, max 2.0)
      pillar_fit:  +1.5 per pillar, cap +4.5 (editorial fit is the strongest signal)
    Max ~9.5, floor ~2.5. A T1 zero-pillar story (~5.5) still loses to a T2
    three-pillar story (~8.5), which is the intended bias: fit > brand."""
    # Source tier (lower tier number = better)
    tier = SOURCE_TIERS.get(article.get("source"), 3)
    source_score = {1: 3.0, 2: 2.0, 3: 1.0, 4: 0.5}.get(tier, 1.0)

    # Recency: exponential decay with 36h half-life
    now = time.time()
    ts = article.get("_ts", 0)
    age_h = (now - ts) / 3600.0 if ts else 24 * 30  # no date = very old
    recency = 2.0 * (0.5 ** (age_h / RECENCY_HALF_LIFE_HOURS))

    # Pillar fit: +1.5 per pillar, cap at +4.5 (3 pillars)
    pillars = _pillar_hits(article.get("title", ""), article.get("summary", ""))
    pillar_score = min(len(pillars) * 1.5, 4.5)

    # Noise penalty: listicle/opinion/guide/review → hard cap at 2.5
    title = article.get("title", "")
    noise = _match_count(title, NOISE_PATTERNS)
    if noise > 0:
        source_score = min(source_score, 0)
        pillar_score = min(pillar_score, 1.5)

    score = source_score + recency + pillar_score
    article["_score"] = round(score, 3)
    article["_pillars"] = sorted(pillars)
    article["_noise"] = bool(noise)
    return article

def fetch_feed(feed_config, ua_index=0):
    """Try to fetch a single feed, with RSSHub fallback. Returns list of articles or []."""
    url = feed_config["url"]
    fallback = feed_config.get("fallback")
    ua = UA_ROTATE[ua_index % len(UA_ROTATE)]
    
    # Try primary URL
    parsed = feedparser.parse(url, agent=ua, request_headers={
        "Accept": "application/rss+xml, application/xml, text/xml, */*",
        "Accept-Language": "en-US,en;q=0.9",
        "Connection": "close",
    })
    if parsed.entries:
        return _to_articles(parsed.entries, feed_config)
    
    # Try RSSHub fallback if provided
    if fallback:
        parsed = feedparser.parse(fallback, agent=ua, request_headers={
            "Accept": "application/rss+xml, application/xml, text/xml, */*",
            "Accept-Language": "en-US,en;q=0.9",
            "Connection": "close",
        })
        if parsed.entries:
            return _to_articles(parsed.entries, feed_config)
    
    return []


def _to_articles(entries, feed_config):
    """Convert feed entries to our article dict format."""
    articles = []
    for entry in entries[:20]:
        title = entry.get("title", "").strip()
        if not title:
            continue
        link = entry.get("link", "#")
        summary = entry.get("summary", "")[:300]
        published = entry.get("published", "")
        # Full text from content:encoded when the feed ships it (MIT TR,
        # Front Office Sports, Ars Technica, Verge). Stored as _body for
        # theming/briefs; stripped of HTML, capped at 6000 chars.
        body = _extract_body(entry)
        articles.append({
            "title": title,
            "link": link,
            "summary": summary,
            "source": feed_config["name"],
            "category": feed_config["category"],
            "published": published,
            "_body": body,
        })
    return articles


def _extract_body(entry):
    """Pull full text from feedparser content fields, strip HTML, cap size."""
    html = ""
    for c in entry.get("content", []):
        v = c.get("value", "")
        if len(v) > len(html):
            html = v
    if not html:
        html = entry.get("summary", "")
    text = re.sub(r"<[^>]+>", " ", html)
    text = re.sub(r"<script.*?</script>", " ", text, flags=re.S | re.I)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:6000]


def main():
    all_articles = []
    feeds_ok = 0
    feeds_fail = 0
    fail_log = []

    for i, feed in enumerate(FEEDS):
        articles = fetch_feed(feed, ua_index=i)
        if articles:
            feeds_ok += 1
            all_articles.extend(articles)
            print(f"  OK  {feed['name']}: {len(articles)} articles")
        else:
            feeds_fail += 1
            fail_log.append(feed["name"])
            print(f"  XX  {feed['name']} — FAILED")
        # Be polite — short sleep between feeds
        time.sleep(0.3)

    # Sort: articles with a parseable date first, then by source
    for a in all_articles:
        try:
            dt = datetime.strptime(a["published"], "%a, %d %b %Y %H:%M:%S %z")
            a["_ts"] = dt.timestamp()
        except:
            a["_ts"] = 0

    # Dedupe by normalized title (keep the highest-tier source for dupes).
    # Same story hits multiple feeds (TechCrunch + TechCrunch AI); a dupe
    # must never eat two TOP NEWS slots.
    seen_titles = {}
    deduped = []
    for a in all_articles:
        norm = re.sub(r"[^a-z0-9]+", " ", a["title"].lower()).strip()
        if not norm:
            continue
        tier = SOURCE_TIERS.get(a.get("source"), 3)
        if norm not in seen_titles:
            seen_titles[norm] = a
            deduped.append(a)
        elif tier < SOURCE_TIERS.get(seen_titles[norm].get("source"), 3):
            # Better source for the same story — swap it in
            old = seen_titles[norm]
            deduped.remove(old)
            seen_titles[norm] = a
            deduped.append(a)
    all_articles = deduped

    all_articles.sort(key=lambda x: -x["_ts"])

    # Score every article, then flag the top N (skipping noise-capped ones).
    for a in all_articles:
        score_article(a)

    # Top stories: highest score, exclude noise-capped items (they can still
    # show in the feed below, just never as TOP NEWS).
    # Diversity constraints: max 2 per source, max 2 per category in top N —
    # one vendor (OpenAI Blog) or one beat (all business) must not own the
    # top shelf.
    scored = [a for a in all_articles if not a["_noise"]]
    scored.sort(key=lambda x: -x["_score"])
    top_ids = set()
    src_count = {}
    cat_count = {}
    for a in scored:
        if len(top_ids) >= TOP_N:
            break
        src = a.get("source", "")
        cat = a.get("category", "")
        if src_count.get(src, 0) >= 2 or cat_count.get(cat, 0) >= 2:
            continue
        top_ids.add(id(a))
        src_count[src] = src_count.get(src, 0) + 1
        cat_count[cat] = cat_count.get(cat, 0) + 1
    for a in all_articles:
        a["top"] = id(a) in top_ids

    # === Full article text for the top stories ===
    # Feeds with content:encoded already have _body. For teaser-only feeds
    # (TechCrunch, CNBC, OpenAI, Economist, etc.) fetch the page via
    # trafilatura — only for the top-scored stories, throttled, so we don't
    # hammer every source on every run.
    if trafilatura is not None:
        top_candidates = [a for a in all_articles if not a["_noise"]]
        top_candidates.sort(key=lambda x: -x.get("_score", 0))
        fetched = 0
        for a in top_candidates[:FETCH_BODY_TOP_N]:
            # Skip stories that already have real body text
            if len(a.get("_body", "").strip()) >= 400:
                continue
            link = a.get("link", "")
            if not link or link == "#":
                continue
            try:
                dl = trafilatura.fetch_url(link)
                txt = trafilatura.extract(dl) if dl else None
                if txt and len(txt.strip()) >= 200:
                    a["_body"] = re.sub(r"\s+", " ", txt).strip()[:6000]
                    fetched += 1
                    print(f"  BODY {a['source']}: {a['title'][:50]}... ({len(a['_body'])} chars)")
            except Exception as e:
                print(f"  SKIP {a['source']}: {e}")
            time.sleep(0.5)  # polite throttle
        print(f"Fetched full text for {fetched} top stories")

    output = {
        "updated": datetime.now(timezone.utc).isoformat(),
        "feeds_ok": feeds_ok,
        "feeds_fail": feeds_fail,
        "feeds_total": len(FEEDS),
        "feed_failures": fail_log,
        "ranking": {
            "name": "weighted_editorial_v1",
            "source_tiers": "T1=4,T2=3,T3=2,T4=1",
            "recency_half_life_hours": RECENCY_HALF_LIFE_HOURS,
            "pillar_cap": 3,
            "noise_penalty": "hard_cap",
            "top_n": TOP_N,
        },
        "articles": all_articles,
    }

    os.makedirs(WEB, exist_ok=True)
    out_path = os.path.join(WEB, "articles.json")
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2)

    print(f"\n=== DONE: {feeds_ok}/{len(FEEDS)} feeds OK, {len(all_articles)} articles total ===")
    if fail_log:
        print(f"Failed feeds: {', '.join(fail_log)}")


if __name__ == "__main__":
    main()
