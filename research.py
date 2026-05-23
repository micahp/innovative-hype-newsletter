#!/usr/bin/env python3
"""
Innovative Hype — Stage 1: AI News Research
============================================
Scrapes 15+ RSS feeds, filters for AI/ML stories, deduplicates,
and outputs a structured JSON digest.

Usage:
    python3 research.py                          # uses config.yaml
    python3 research.py --config config.local.yaml
    python3 research.py --max-articles 10
"""

import json
import sys
import os
import re
import hashlib
from datetime import datetime, timedelta, timezone
from pathlib import Path

import feedparser

# ── Config loading ──────────────────────────────────────────────────────────

def load_config(config_path="config.yaml"):
    """Load YAML config. Falls back to json if PyYAML is unavailable."""
    path = Path(config_path)
    if not path.exists():
        print(f"ERROR: Config file not found: {config_path}")
        print("Copy config.yaml to config.local.yaml and fill in your settings.")
        sys.exit(1)

    # Try YAML first
    try:
        import yaml
        with open(path) as f:
            return yaml.safe_load(f)
    except ImportError:
        pass

    # Fallback: load as JSON (we ship config.yaml in YAML format, but this
    # handles the case where someone converted it)
    try:
        with open(path) as f:
            return json.load(f)
    except json.JSONDecodeError:
        print(f"ERROR: Cannot parse {config_path} — is it valid YAML/JSON?")
        sys.exit(1)


# ── Feed fetching ───────────────────────────────────────────────────────────

def fetch_feed(name, url, timeout=15):
    """Fetch and parse a single RSS feed. Returns list of article dicts."""
    try:
        parsed = feedparser.parse(url, agent="InnovativeHype/1.0")
    except Exception as e:
        print(f"  [SKIP] {name}: connection error — {e}")
        return []

    if parsed.bozo:
        bozo_msg = str(parsed.bozo_exception)[:120]
        print(f"  [WARN] {name}: parse warning — {bozo_msg}")

    articles = []
    for entry in parsed.entries:
        # Extract publish date
        published = None
        for date_field in ("published_parsed", "updated_parsed"):
            val = getattr(entry, date_field, None)
            if val:
                try:
                    published = datetime(*val[:6], tzinfo=timezone.utc)
                    break
                except (TypeError, ValueError):
                    continue

        title = getattr(entry, "title", "(no title)").strip()
        link = getattr(entry, "link", "")
        summary = getattr(entry, "summary", "") or getattr(entry, "description", "")

        # Clean HTML from summary
        summary = re.sub(r"<[^>]+>", " ", summary)
        summary = re.sub(r"\s+", " ", summary).strip()[:500]

        articles.append({
            "title": title,
            "link": link,
            "summary": summary,
            "source": name,
            "published": published.isoformat() if published else None,
        })

    return articles


# ── Filtering ───────────────────────────────────────────────────────────────

def matches_keywords(article, keywords):
    """Check if article title or summary contains any keyword (case-insensitive)."""
    text = (article["title"] + " " + article["summary"]).lower()
    return any(kw.lower() in text for kw in keywords)


def is_recent(article, max_age_hours):
    """Check if article is within the age limit. If no date, assume recent."""
    pub_str = article.get("published")
    if not pub_str:
        return True  # No date = assume recent
    try:
        pub = datetime.fromisoformat(pub_str)
        age = datetime.now(timezone.utc) - pub
        return age <= timedelta(hours=max_age_hours)
    except (ValueError, TypeError):
        return True


# ── Deduplication ───────────────────────────────────────────────────────────

def normalize(text):
    """Normalize text for dedup comparison."""
    return re.sub(r"[^a-z0-9]", "", text.lower())


def deduplicate(articles):
    """Remove duplicates by title similarity. Keeps first occurrence."""
    seen = set()
    unique = []
    for art in articles:
        key = normalize(art["title"])[:80]  # First 80 chars of normalized title
        # Also check summary hash for near-duplicates
        summary_key = hashlib.md5(normalize(art["summary"])[:200].encode()).hexdigest()
        fingerprint = (key, summary_key)

        if fingerprint not in seen:
            seen.add(fingerprint)
            unique.append(art)
    return unique


# ── Main ────────────────────────────────────────────────────────────────────

def main():
    import argparse

    parser = argparse.ArgumentParser(description="Aggregate AI news from RSS feeds")
    parser.add_argument("--config", default="config.yaml", help="Config file path")
    parser.add_argument("--max-articles", type=int, help="Override max_articles from config")
    parser.add_argument("--output", help="Override output path")
    args = parser.parse_args()

    # Load config
    config = load_config(args.config)

    feeds = config["rss_feeds"]
    keywords = config["filter"]["keywords"]
    max_age = config["filter"]["max_age_hours"]
    max_articles = args.max_articles or config["filter"]["max_articles"]
    out_path = args.output or config["output"]["digest"]

    print(f"=== AI News Research === {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"Feeds to scrape: {len(feeds)}")
    print(f"Max age: {max_age}h | Max articles: {max_articles}")

    # Fetch all feeds
    all_articles = []
    for feed in feeds:
        name = feed["name"]
        url = feed["url"]
        print(f"  Fetching {name}...")
        articles = fetch_feed(name, url)
        print(f"    → {len(articles)} raw articles")
        all_articles.extend(articles)

    print(f"\nTotal raw articles: {len(all_articles)}")

    # Filter by keywords
    filtered = [a for a in all_articles if matches_keywords(a, keywords)]
    print(f"After keyword filter: {len(filtered)}")

    # Filter by recency
    recent = [a for a in filtered if is_recent(a, max_age)]
    print(f"After recency filter ({max_age}h): {len(recent)}")

    # Deduplicate
    unique = deduplicate(recent)
    print(f"After dedup: {len(unique)}")

    # Trim to max
    final = unique[:max_articles]
    print(f"Final digest: {len(final)} articles")

    # Build output
    digest = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "article_count": len(final),
        "sources_scraped": len(feeds),
        "filters_applied": {
            "keywords": len(keywords),
            "max_age_hours": max_age,
        },
        "articles": final,
    }

    # Write output
    with open(out_path, "w") as f:
        json.dump(digest, f, indent=2, ensure_ascii=False)

    print(f"\n✅ Digest written to {out_path}")
    print(f"   {len(final)} stories from {len(set(a['source'] for a in final))} unique sources")

    # Print summary
    if final:
        print("\n── Top Stories ──")
        for i, art in enumerate(final[:10], 1):
            src = art["source"]
            title = art["title"][:90]
            print(f"  {i}. [{src}] {title}")


if __name__ == "__main__":
    main()
