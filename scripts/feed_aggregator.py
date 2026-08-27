#!/usr/bin/env python3
"""feed_aggregator.py — fetch all RSS feeds (66 configured), output JSON for the web page.

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
    {"name": "Wired", "url": "https://www.wired.com/feed/rss", "category": "technology", "fallback": "https://rsshub.app/wired"},
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
    # "Reuters Business" (rss.reuters.com 404 + dead rsshub fallback) removed
    # 2026-08-27 evening — replaced by the Google News "Reuters" feed above.
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
    {"name": "The FADER", "url": "https://www.thefader.com/feed", "category": "culture", "fallback": "https://rsshub.app/the-fader"},
    {"name": "XXL", "url": "https://www.xxlmag.com/feed/", "category": "culture"},
    {"name": "Deadline", "url": "https://deadline.com/feed/", "category": "culture"},
    {"name": "Variety", "url": "https://variety.com/feed/", "category": "culture"},
    {"name": "Hollywood Reporter", "url": "https://www.hollywoodreporter.com/feed/", "category": "culture"},
    # CROSS
    {"name": "HN (General)", "url": "https://hnrss.org/frontpage", "category": "technology", "fallback": "https://rsshub.app/hacker-news/frontpage"},
    # JUST IN-OUTLET FEEDS (2026-08-27): the polymarket/kalshi corpus names
    # Bloomberg, Reuters, Axios, WSJ, CNN, AP, NYT as the desks' upstream.
    # Reuters/Axios/CNN/AP have no free RSS left (404/401/403, probed once
    # each 2026-08-27) and Bloomberg/FT never did; rsshub.app fallbacks are
    # 403-dead fleet-wide. NYT, WSJ (Dow Jones public host), Fox, Business
    # Insider and Fortune still publish free RSS. BI/Fortune also carry the
    # tech-nepotism beat ("nepotism in tech darlings", Micah 2026-08-27),
    # which no current feed covers at all.
    #
    # GATED OUTLETS VIA GOOGLE NEWS RSS (2026-08-27 evening, Micah's
    # "archive.ph or wayback machine" direction): archive.ph is 429 from this
    # box and Wayback only holds Reuters/Bloomberg's 401/403 GATE pages for
    # their section URLs — the archive carries the wall, not the paper. But
    # Google's index serves every gated outlet as an RSS search result:
    # site:<outlet> when:2d returns 100 fresh items each, one uniform surface.
    # Probed once per host, all 200 (items verified, not just headers). The
    # pubDate is RFC2822 with a "GMT" zone, which datetime.strptime's %z
    # rejects — the main() date parse carries a parsedate_to_datetime
    # fallback. Titles carry a " - Outlet" suffix, stripped in _to_articles
    # via the "gnews" flag.
    {"name": "Reuters", "url": "https://news.google.com/rss/search?q=site%3Areuters.com+when:2d&hl=en-US&gl=US&ceid=US:en", "category": "business", "gnews": True},
    # AP + CNN answer 200 from this box (only their RSS is gated), and both
    # publish Google news-format sitemaps: the publisher's own titles, real
    # article URLs, ISO publication dates. Verified 2026-08-27 (AP 627 URLs,
    # CNN 225). Real URLs mean the trafilatura top-15 body fetch can reach
    # their article pages, so AP/CNN enter the pool as full articles where
    # they rank — NOT headline-only like the gnews outlets. Replaces the
    # gnews AP/CNN feeds (same coverage, no Google dependency).
    {"name": "AP", "url": "https://apnews.com/news-sitemap-content.xml", "category": "business", "kind": "sitemap"},
    {"name": "CNN", "url": "https://www.cnn.com/sitemap/news.xml", "category": "business", "kind": "sitemap"},
    {"name": "Axios", "url": "https://news.google.com/rss/search?q=site%3Aaxios.com+when:2d&hl=en-US&gl=US&ceid=US:en", "category": "business", "gnews": True},
    {"name": "Bloomberg", "url": "https://news.google.com/rss/search?q=site%3Abloomberg.com+when:2d&hl=en-US&gl=US&ceid=US:en", "category": "business", "gnews": True},
    {"name": "NYT Business", "url": "https://rss.nytimes.com/services/xml/rss/nyt/Business.xml", "category": "business"},
    {"name": "WSJ Markets", "url": "https://feeds.a.dj.com/rss/RSSMarketsMain.xml", "category": "business"},
    {"name": "Fox Business", "url": "https://feeds.foxnews.com/foxnews/business", "category": "business"},
    {"name": "Business Insider", "url": "https://www.businessinsider.com/rss", "category": "business"},
    {"name": "Fortune", "url": "https://fortune.com/feed/", "category": "business"},
    # TOPIC-GAP FEEDS (2026-08-27, from the voice-coverage audit): Kanye/Yeezy
    # had ZERO pool coverage in 14d (8 tweets, no music feed carries the
    # tabloid beat) -> Vibe (HipHopDX's RSS is a frozen Apr-2026 archive,
    # hotnewhiphop 404). Houston Dynamo/MLS/Messi was thin (ESPN, Athletic,
    # Bleacher all dead) -> BBC Football.
    {"name": "Vibe", "url": "https://vibe.com/feed/", "category": "culture"},
    {"name": "BBC Football", "url": "https://feeds.bbci.co.uk/sport/football/rss.xml", "category": "sports"},
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
    # SPORTS FEED FIX (2026-08-21, NEWS-ENGINE-SPEC.md R7): ESPN/Athletic/
    # Bleacher/SBJ all dead. Winsidr + Swish Appeal cover WNBA (Sophie
    # Cunningham, NBA→WNBA draft), On3 + ClutchPoints cover college/Texas
    # (Longhorns, NCAAF age stories), Texas Monthly covers state politics
    # (marijuana law) + culture.
    {"name": "Winsidr", "url": "https://winsidr.com/feed/", "category": "sports"},
    {"name": "Swish Appeal", "url": "https://www.swishappeal.com/rss/index.xml", "category": "sports"},
    {"name": "On3", "url": "https://www.on3.com/feed/", "category": "sports"},
    {"name": "ClutchPoints", "url": "https://clutchpoints.com/feed", "category": "sports"},
    {"name": "Texas Monthly", "url": "https://www.texasmonthly.com/feed/", "category": "business"},
    {"name": "Texas Tribune", "url": "https://www.texastribune.org/feed/", "category": "business"},
    {"name": "Austin Chronicle", "url": "https://www.austinchronicle.com/feeds/news/", "category": "culture"},
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
    # VENDOR BLOGS demoted from T1 (2026-08-21): their announcements are
    # self-promotion, not reporting — "Offering Zero Data Retention" (undated,
    # 0 recency) sat on the Top shelf at 7.50 on tier+pillars alone.
    "OpenAI Blog": 4,
    "Google AI Blog": 3,
    "DeepMind Blog": 3,
    "Meta AI Blog": 4,
    "Anthropic Research": 3,
    "Hacker News (AI)": 3,
    "CoinDesk": 2,
    # BUSINESS
    "CNBC": 1,
    "Economist": 1,
    # WIRE-GRADE GATED OUTLETS (2026-08-27, Google News RSS surfaces): these
    # are the exact outlets the JUST IN desks crib from. T1 by definition.
    "Reuters": 1,
    "AP": 1,
    "CNN": 1,
    "Axios": 1,
    "Bloomberg": 1,
    "TechCrunch": 1,
    "NYT Business": 1,
    "WSJ Markets": 1,
    "Fortune": 2,
    "Business Insider": 3,
    "Fox Business": 3,
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
    "Vibe": 2,
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
    # SPORTS FEED FIX (2026-08-21)
    "Winsidr": 2,
    "Swish Appeal": 2,
    "On3": 2,
    "ClutchPoints": 2,
    "BBC Football": 2,
    "Texas Monthly": 1,
    "Texas Tribune": 1,
    "Austin Chronicle": 2,
}

# Negative markers — LP-style news-vs-noise filter. Any hit hard-caps the score.
NOISE_PATTERNS = [
    r"\b(listicle|roundup|recap|best of|top \d+|n best|ways to)\b",
    # "The 9 Best X of 2026, Tried and Tested" — number+Best and
    # tried/tested are the same review-register as the patterns above.
    # (Measured 2026-08-21: Rolling Stone earbuds roundup hit the Top shelf.)
    r"\b\d+ best\b",
    r"\b(tried and tested|tested and reviewed|hands-?on)\b",
    r"\b(review|reviewed|we tried|i tried)\b",
    r"\b(opinion|op-?ed|column|hot take|take:)\b",
    r"\b(how to|guide|tutorial|explainer|cheat sheet|primer)\b",
    r"\b(5 |10 |25 |50 |100 )(things|reasons|ways|signs|lessons)\b",
    r"\b(q&a|podcast episode|newsletter)\b",
    # Entertainment chatter — interview/recap/breakdowns are texture, not top news
    r"\b(interview|interviews|break down|breaks down|recap|watch now|first look|trailer)\b",
    # Celebrity/personality drama — gossip is not Innovative Hype culture
    r"\b(says he refused|says she refused|weighs in|opens up|reveals|dishes on|slams|rips|blasts|feud)\b",
    r"\b(remembers|tribute|honors|memorializes)\b",
    # Event/conference promo marketing — a source pushing its own tickets,
    # passes, discounts, or deadlines ("last chance") is an ad, not news.
    # (Measured 2026-08-21: TechCrunch "Last chance: Save up to $300 on your
    # Disrupt 2026 ticket" hit all 3 pillars and anchored Top News #1.)
    r"\b(last chance|early[- ]?bird|act now|limited time|don[’']t miss|dont miss)\b",
    r"\b(save up to|save \$\d+|\$\d+ off|discount|coupon|promo code|deal of the)\b",
    r"\b(register now|registration|reserve (your|my) (spot|seat|pass)|rsvp|sign[ -]?up)\b",
    r"\b(tickets? on sale|get your (ticket|pass)|buy (tickets|passes))\b",
    # Outlet self-promo — a publisher pushing its OWN event lineup or a
    # vendor's own partnership announcement. Same class as the Disrupt promo.
    # (Sweep 2026-08-21: Texas Tribune Festival lineup, OpenAI "Partnering
    # with CodeAI" — both LIVE at 3.41 / 7.50, neither is news.)
    r"\b(our (full )?lineup|our (annual )?(festival|summit|conference|event)|join us at|see you at|get your (ticket|pass) to)\b",
    r"\b(partnering with|partnership with|teaming up with)\b",
    # Podcast/media-player prefixes — "LISTEN:" is an episode, not a story.
    # (Measured 2026-08-21: "LISTEN: Amazon Courts Creators…" hit 8.38, #4 on
    # the Top shelf, on pillar keywords in its summary alone.)
    r"^listen:|^watch:|^read:|^stream:",
    r"\b(podcast|episode \d+|ep\. ?\d+)\b",
]

# Pillar keywords from EDITORIAL_MAP.md (title+summary match, word-boundary).
# Each entry maps a pillar to the keyword list that signals it.
PILLAR_KEYWORDS = {
    # CORRECTED 2026-08-21 evening: 'creator(s)' appeared in THREE lists
    # (ownership, build-consume, community-moat), so a single word bought
    # +4.5 pillar score and soft culture features out-ranked hard news
    # ("For Comedy Writers..." hit 3 pillars on creator/community/ownership).
    # Rule now: a keyword may belong to ONE pillar only — the most specific.
    # 'ai' also lived in ai-defining while 'agent' inflated every crypto story.
    "sovereignty": ["sovereignty", "self-custody", "self custody", "de-dollarization", "de-dollarisation", "sound money", "censorship", "surveillance", "data privacy", "financial freedom", "sanctions"],
    "ownership": ["ownership", "royalt", "rent-seeking", "middleman", "middlemen", "platform fee", "take rate"],
    "ai-defining": ["ai", "artificial intelligence", "llm", "gpt", "claude", "gemini", "sora", "model release", "deepseek", "mistral", "machine learning", "robotics", "agi"],
    "build-consume": ["build", "builder", "making", "maker", "startup", "founder", "founders", "entrepreneur", "side project", "indie", "diy"],
    "community-moat": ["community", "network effect", "fandom", "audience", "subscribers", "members", "guild", "co-op", "cooperative"],
    "culture-onchain": ["nft", "on-chain", "onchain", "web3", "blockchain", "ethereum", "solana", "tokenization", "digital art", "metaverse", "crypto"],
    "tech-optimism": ["breakthrough", "next generation", "innovation", "pioneer", "milestone"],
    "self-mastery": ["discipline", "consistency", "training", "workout", "stoic", "mindset", "compounding", "grind", "hustle", "routine", "longevity", "peak performance"],
    "access-uplift": ["democrati", "uplift", "inclusive", "financial inclusion", "financial literacy"],
}

# How long until a story is half as relevant (hours). 36h keeps a morning
# briefing story viable into the evening without drowning in old news.
RECENCY_HALF_LIFE_HOURS = 36

# How many top stories to flag.
TOP_N = 7

# How many top-scored stories get full-text fetched (teaser-only feeds).
FETCH_BODY_TOP_N = 15

# How much body text means "we plausibly have the whole article". A real news
# story is thousands of characters; anything under this is a teaser, a partial
# content:encoded payload, or an intro. See the 2026-08-23 note in the fetch
# loop for what a low bar cost us.
BODY_LOOKS_COMPLETE = int(os.environ.get("IH_BODY_COMPLETE", "2500"))

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

# === THE VOICE BOOST ===
#
# Micah, 2026-08-23, on why a golf ad was card #1: "it more so shouldnt be the
# highest ranking thing." The score was source_tier + recency + pillar_fit and
# none of those three terms knows what he cares about, so his own named topics
# sat at #419 (Texas THC lawsuit) and #553 (Palantir zero data retention) out
# of 1,512.
#
# The first attempt at fixing this was an LLM-extracted inventory of "positions"
# with subject scopes. He read it and said: "that sounds really complicated. is
# there a simpler way?" There is. This is it. A flat list of subjects in
# voice_terms.txt, one per line. An article whose TITLE mentions one gets a
# boost. Add a line, it ranks higher; delete a line, it stops mattering.
#
# TITLE ONLY, and word-boundary matched. A body mentions everything, and plain
# substring matching put "rent" inside "Inherent" and pushed an unrelated AI
# story to #2. Same lesson as the bucket keywords on 2026-08-21.
#
# Measured on the 474-article pool the moment it went in:
#   Texas THC lawsuit   #419 -> #1
#   Flock CEO           #15  -> #3
#   Data centers        #53  -> #5
#   Palantir / ZDR      #553 -> #100
VOICE_TERMS_PATH = os.path.join(os.path.dirname(__file__), "..", "voice_terms.txt")
VOICE_BOOST = float(os.environ.get("IH_VOICE_BOOST", "2.0"))
VOICE_BOOST_CAP = float(os.environ.get("IH_VOICE_BOOST_CAP", "6.0"))


# The term file failing to load is NOT a soft failure. If it comes back empty
# the fourth score term silently becomes zero and every article ranks exactly
# as it did before the boost existed, with no error anywhere. That is why the
# load error is kept and written into the run meta rather than swallowed.
_VOICE_LOAD_ERROR = None


def _load_voice_terms():
    global _VOICE_LOAD_ERROR
    try:
        out = []
        for line in open(VOICE_TERMS_PATH):
            line = line.strip().lower()
            if line and not line.startswith("#"):
                out.append((line, re.compile(r"\b" + re.escape(line) + r"\b")))
        if not out:
            _VOICE_LOAD_ERROR = "voice_terms.txt loaded but contains no terms"
            print("WARNING: " + _VOICE_LOAD_ERROR)
        return out
    except Exception as e:
        _VOICE_LOAD_ERROR = "%s: %s" % (type(e).__name__, e)
        print("WARNING: voice terms did not load (%s). The fourth score term "
              "is OFF for this run." % _VOICE_LOAD_ERROR)
        return []


_VOICE_TERMS = _load_voice_terms()


def voice_hits(title):
    """Subjects from voice_terms.txt present in this headline."""
    t = (title or "").lower()
    return [w for w, rx in _VOICE_TERMS if rx.search(t)]


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

    # The fourth term: does Micah actually care about this subject.
    vhits = voice_hits(title)
    voice = min(VOICE_BOOST * len(vhits), VOICE_BOOST_CAP)

    score = source_score + recency + pillar_score + voice
    article["_score"] = round(score, 3)
    article["_voice"] = vhits
    article["_pillars"] = sorted(pillars)
    article["_noise"] = bool(noise)
    return article

def fetch_feed(feed_config, ua_index=0):
    """Try to fetch a single feed, with RSSHub fallback. Returns list of articles or []."""
    if feed_config.get("kind") == "sitemap":
        return fetch_sitemap(feed_config, ua_index)
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


def _rfc2822_from_iso(v):
    """Sitemap publication_date is ISO 8601 (often 'Z'-suffixed); the pool
    stores RFC 2822. Normalize so main()'s date parse sees a known shape."""
    from email.utils import format_datetime
    try:
        dt = datetime.fromisoformat((v or "").replace("Z", "+00:00"))
        return format_datetime(dt)
    except ValueError:
        return ""


def fetch_sitemap(feed_config, ua_index=0):
    """Google news-format sitemap: <url> entries carrying <loc>, <news:title>,
    <news:publication_date>. Returns the same article dicts as fetch_feed.
    Titles and dates are the publisher's own; links are real article pages,
    so the trafilatura body fetch applies to them like any other source."""
    import xml.etree.ElementTree as ET
    url = feed_config["url"]
    ua = UA_ROTATE[ua_index % len(UA_ROTATE)]
    req = urllib.request.Request(url, headers={
        "User-Agent": ua,
        "Accept": "application/xml, text/xml, */*",
    })
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            data = r.read()
    except (urllib.error.URLError, OSError) as exc:
        print(f"  sitemap {feed_config['name']}: FETCH FAILED {exc}")
        return []
    try:
        root = ET.fromstring(data)
    except ET.ParseError as exc:
        print(f"  sitemap {feed_config['name']}: PARSE FAILED {exc}")
        return []
    ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9",
          "news": "http://www.google.com/schemas/sitemap-news/0.9"}
    rows = []
    for u in root.findall("sm:url", ns):
        n = u.find("news:news", ns)
        title_el = n.find("news:title", ns) if n is not None else None
        pd_el = n.find("news:publication_date", ns) if n is not None else None
        pub_el = n.find("news:publication", ns) if n is not None else None
        lang_el = pub_el.find("news:language", ns) if pub_el is not None else None
        loc_el = u.find("sm:loc", ns)
        title = (title_el.text or "").strip() if title_el is not None and title_el.text else ""
        pdate = (pd_el.text or "").strip() if pd_el is not None and pd_el.text else ""
        loc = (loc_el.text or "").strip() if loc_el is not None else ""
        lang = (lang_el.text or "").strip().lower() if lang_el is not None and lang_el.text else ""
        if not title or not loc:
            continue
        # video pages have no extractable article text
        if "/video/" in loc:
            continue
        # AP's news sitemap ships its Spanish edition (news:language "spa");
        # CNN's carries cnn-underscored commerce rows. Neither is the news
        # surface this desk reads.
        if lang and lang not in ("eng", "en"):
            continue
        if "cnn-underscored" in loc:
            continue
        # Parse for sorting: ISO strings with mixed offsets ("-04:00" vs "Z")
        # do not compare correctly as strings.
        try:
            dt = datetime.fromisoformat(pdate.replace("Z", "+00:00"))
        except ValueError:
            dt = datetime.min.replace(tzinfo=timezone.utc)
        rows.append((dt, pdate, title, loc))
    # A news sitemap's order is not guaranteed; take the 20 newest by date.
    # Rows with unparseable dates sort last and so effectively drop out.
    rows.sort(key=lambda r: r[0], reverse=True)
    articles = []
    for _dt, pdate, title, loc in rows[:20]:
        articles.append({
            "title": title,
            "link": loc,
            "summary": "",
            "kind": "sitemap",
            "source": feed_config["name"],
            "category": feed_config["category"],
            "published": _rfc2822_from_iso(pdate),
            "_body": "",
        })
    return articles


def _to_articles(entries, feed_config):
    """Convert feed entries to our article dict format."""
    # Google News search feeds stamp every title with " - <Outlet>" (the
    # <source> tag's name). Strip it so titles dedupe against the same story
    # from other feeds and read clean in the pool. Only strips the outlet
    # suffixes this file's gnews feeds can produce.
    _GNEWS_SUFFIXES = ("Reuters", "AP News", "CNN", "Axios", "Bloomberg.com")
    gnews = feed_config.get("gnews")
    articles = []
    for entry in entries[:20]:
        title = entry.get("title", "").strip()
        if gnews and title:
            for sfx in _GNEWS_SUFFIXES:
                if title.endswith(" - " + sfx):
                    title = title[: -len(" - " + sfx)].strip()
                    break
        if not title:
            continue
        # A Google News description is an HTML anchor to the news.google.com
        # redirect page, never editorial text — keep it out of the pool
        # rather than storing markup that reads like a summary.
        link = entry.get("link", "#")
        if gnews:
            summary = ""
            body = ""
        else:
            summary = entry.get("summary", "")[:300]
            # Full text from content:encoded when the feed ships it (MIT TR,
            # Front Office Sports, Ars Technica, Verge). Stored as _body for
            # theming/briefs; stripped of HTML, capped at 6000 chars.
            body = _extract_body(entry)
        published = entry.get("published", "")
        articles.append({
            "title": title,
            "link": link,
            "summary": summary,
            "gnews": bool(gnews),
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

    # Sort: articles with a parseable date first, then by source.
    # strptime's %z never accepts the "GMT" zone name (Google News pubDates,
    # among others), so fall back to the RFC2822 parser before calling a
    # date undated — an undated article silently sinks in every sort.
    from email.utils import parsedate_to_datetime
    for a in all_articles:
        try:
            dt = datetime.strptime(a["published"], "%a, %d %b %Y %H:%M:%S %z")
            a["_ts"] = dt.timestamp()
        except ValueError:
            try:
                a["_ts"] = parsedate_to_datetime(a["published"]).timestamp()
            except Exception:
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

    # === Story persistence (2026-08-21 evening) ===
    # The feed window (~20 items per feed) forgets stories within HOURS.
    # Measured: the Winona/Flock camera story was CARDED by the desk at 18:02
    # and the Texas THC-ban lawsuit in four consecutive runs (18:13→20:11),
    # then both silently vanished from the pool because newer posts pushed
    # them past entries[:20]. The desk can only card what the aggregator
    # keeps. Fix: merge back articles from the previous run that the fresh
    # fetch no longer carries, bounded by RETENTION_HOURS, so a story lives
    # for days instead of hours. Scores/flags are recomputed below with
    # current time, so decay stays honest.
    RETENTION_HOURS = 72
    prev_path = os.path.join(WEB, "articles.json")
    if os.path.exists(prev_path):
        try:
            with open(prev_path) as f:
                prev = json.load(f)
            now_ts = time.time()
            kept = 0
            for pa in prev.get("articles", []):
                ts = pa.get("_ts", 0)
                if not ts or now_ts - ts > RETENTION_HOURS * 3600:
                    continue
                pnorm = re.sub(r"[^a-z0-9]+", " ", pa["title"].lower()).strip()
                if pnorm and pnorm not in seen_titles:
                    seen_titles[pnorm] = pa
                    all_articles.append(pa)
                    kept += 1
            if kept:
                print(f"  PERSISTED {kept} stories carried over from the previous run (< {RETENTION_HOURS}h old)")
        except Exception as e:
            print(f"  persist merge skipped: {e}")

    all_articles.sort(key=lambda x: -x["_ts"])

    # Score every article, then flag the top N (skipping noise-capped ones).
    for a in all_articles:
        score_article(a)

    # Which voice terms actually fired. A term that matches nothing and a term
    # that is doing all the work look identical from outside the run, so both
    # the per-term counts and the dead list go into the meta. On 2026-08-24,
    # 24 of 52 terms fired zero times, including palantir, thc and deepseek,
    # the exact subjects the term was added to rescue.
    voice_counts = {}
    for a in all_articles:
        for t in a.get("_voice") or []:
            voice_counts[t] = voice_counts.get(t, 0) + 1
    voice_dead = sorted(t for t, _ in _VOICE_TERMS if t not in voice_counts)
    voice_hit_articles = sum(1 for a in all_articles if a.get("_voice"))
    print("Voice terms: %d loaded, %d fired, %d dead; %d/%d articles boosted"
          % (len(_VOICE_TERMS), len(voice_counts), len(voice_dead),
             voice_hit_articles, len(all_articles)))
    if voice_dead:
        print("  never fired: " + ", ".join(voice_dead))

    # Top stories: highest score, exclude noise-capped items (they can still
    # show in the feed below, just never as TOP NEWS).
    # Dated-only rule (2026-08-21): an article with no parseable date has
    # unknown freshness ("Offering Zero Data Retention" was undated, age=∞,
    # recency≈0, yet took a Top slot on tier+pillars). No date → never TOP.
    # Diversity constraints: max 2 per source, max 2 per category in top N —
    # one vendor (OpenAI Blog) or one beat (all business) must not own the
    # top shelf.
    scored = [a for a in all_articles if not a["_noise"] and a.get("_ts", 0) > 0]
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
        gnews_skipped = 0
        for a in top_candidates[:FETCH_BODY_TOP_N]:
            # Google News items link to news.google.com JS interstitials, and
            # their real article pages are the same 401/403 walls that gated
            # the RSS. A trafilatura hit there is Google boilerplate at best
            # and a wasted top-15 slot at worst — count them, don't fetch.
            if a.get("gnews"):
                gnews_skipped += 1
                continue
            # 400 was the old skip threshold and it was the wrong test.
            # Measured 2026-08-23: The Verge ships PARTIAL content:encoded.
            # "Nvidia's new financial strategy does not compute" arrived with
            # 854 chars, cleared 400, so the fetch never ran and 854 chars
            # counted as "we have the article". The desk then had to pick an
            # angle from an opening corncob joke and one financing sentence,
            # and it welded on an unrelated housing take because there was
            # nothing else in there to work with. A partial feed passing a low
            # bar is indistinguishable from a full one, so raise the bar and,
            # when we do fetch, KEEP THE LONGER of the two rather than
            # assuming either source wins.
            have = len(a.get("_body", "").strip())
            if have >= BODY_LOOKS_COMPLETE:
                a["_body_source"] = a.get("_body_source") or "feed"
                continue
            link = a.get("link", "")
            if not link or link == "#":
                continue
            try:
                dl = trafilatura.fetch_url(link)
                txt = trafilatura.extract(dl) if dl else None
                if txt and len(txt.strip()) >= 200:
                    cand = re.sub(r"\s+", " ", txt).strip()[:6000]
                    if len(cand) > have:
                        a["_body"] = cand
                        a["_body_source"] = "fetch"
                        fetched += 1
                        print(f"  BODY {a['source']}: {a['title'][:50]}... "
                              f"({have} -> {len(cand)} chars)")
                    else:
                        a["_body_source"] = a.get("_body_source") or "feed"
            except Exception as e:
                print(f"  SKIP {a['source']}: {e}")
            time.sleep(0.5)  # polite throttle
        print(f"Fetched full text for {fetched} top stories "
              f"({gnews_skipped} gnews items skipped, headline-only by design)")

    output = {
        "updated": datetime.now(timezone.utc).isoformat(),
        "feeds_ok": feeds_ok,
        "feeds_fail": feeds_fail,
        "feeds_total": len(FEEDS),
        "feed_failures": fail_log,
        "ranking": {
            # v2 = the fourth term. The name changes with the formula so a
            # stored articles.json says which scorer produced it.
            "name": "weighted_editorial_v2_voice",
            "source_tiers": "T1=4,T2=3,T3=2,T4=1",
            "recency_half_life_hours": RECENCY_HALF_LIFE_HOURS,
            "pillar_cap": 3,
            "noise_penalty": "hard_cap",
            "top_n": TOP_N,
            "voice_terms_path": os.path.relpath(
                VOICE_TERMS_PATH,
                os.path.join(os.path.dirname(__file__), "..")),
            "voice_terms_loaded": len(_VOICE_TERMS),
            "voice_terms_fired": len(voice_counts),
            "voice_terms_dead": voice_dead,
            "voice_term_hits": dict(sorted(voice_counts.items(),
                                           key=lambda kv: -kv[1])),
            "voice_articles_boosted": voice_hit_articles,
            "voice_boost_per_hit": VOICE_BOOST,
            "voice_boost_cap": VOICE_BOOST_CAP,
            "voice_load_error": _VOICE_LOAD_ERROR,
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
