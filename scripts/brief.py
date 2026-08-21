#!/usr/bin/env python3
"""brief.py — generate a LinkedIn-style news brief from web/articles.json.

Reads the scored articles, buckets them by theme, picks leads per bucket,
and renders a brief. v2 (2026-08-21): buckets carry multi-story coverage and
per-bucket commentary hooks written in the Innovative Hype voice. Still
deterministic (no LLM) so it's cron-safe.

Output: web/brief.md (markdown, human-readable)
"""

import json
import os
import re
from collections import OrderedDict
from datetime import datetime, timezone

WEB = os.path.join(os.path.dirname(__file__), "..", "web")


def _md_escape(text):
    """Escape HTML special chars so titles with quotes/ampersands render."""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _md_inline(text):
    """Convert **bold** and _italic_ to HTML."""
    text = _md_escape(text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"_(.+?)_", r"<em>\1</em>", text)
    return text


# === Bucket definitions ===
# Each bucket has a display name, an emoji, keyword rules, and a hook
# template. The hook is a short editorial line that frames the theme —
# written once per bucket, applied to the lead story.
BUCKETS = [
    {
        "name": "Startups & Venture",
        "emoji": "🚀",
        "hook": "Capital is flowing to whoever builds the picks-and-shovels. The founders who win aren't selling dreams — they're selling infrastructure.",
        "keywords": ["startup", "venture", "vc", "funding", "raises", "seed", "series", "ipo", "unicorn", "founder", "acquisition", "acquires", "million", "billion", "gross run rate", "investor"],
    },
    {
        "name": "AI & Models",
        "emoji": "🤖",
        "hook": "The model wars are the new space race. Every release resets the bar — and the money follows the compute.",
        "keywords": ["ai", "artificial intelligence", "llm", "gpt", "claude", "gemini", "openai", "anthropic", "deepseek", "mistral", "model release", "machine learning", "neural network", "ai model", "ai training", "training data", "inference", "ai agent", "robot", "robotics", "generative", "chatbot"],
    },
    {
        "name": "Crypto & Markets",
        "emoji": "📈",
        "hook": "Markets are a rumor mill with a scoreboard. The signal is where the money moves — and where it doesn't.",
        "keywords": ["bitcoin", "crypto", "ethereum", "solana", "nft", "blockchain", "coin", "token", "defi", "web3", "prediction market", "kalshi", "polymarket", "stock", "market", "fed", "inflation", "rate"],
        # Security/scam stories that merely mention crypto are NOT market stories
        "not": ["hacker", "malware", "scam", "phishing", "ransomware", "lure", "security researcher", "exploit", "breach", "attack"],
    },
    {
        "name": "Sports & Business",
        "emoji": "🏀",
        "hook": "Sports is becoming the most watched business in America. The athletes have the leverage now — and the owners know it.",
        "keywords": ["nfl", "nba", "mlb", "nhl", "wnba", "ufc", "soccer", "football", "tennis", "us open", "prize money", "player", "college", "draft", "league", "stadium", "athlete", "training camp", "merchandise", "tickets"],
    },
    {
        "name": "Big Tech & Policy",
        "emoji": "🏛️",
        "hook": "The platforms write the rules until someone writes them for them. Every hearing, every ban, every lawsuit is a renegotiation of power.",
        "keywords": ["google", "meta", "facebook", "apple", "amazon", "microsoft", "nvidia", "tesla", "antitrust", "regulation", "ban", "lawsuit", "sues", "senate", "congress", "ftc", "doj", "eu", "supreme court", "judge"],
    },
    {
        "name": "Culture & Music",
        "emoji": "🎬",
        "hook": "Culture is the last uncommodified asset — until someone commodifies it. Watch the creators, the drops, the moments.",
        "keywords": ["music", "album", "song", "artist", "band", "festival", "tour", "concert", "film", "movie", "hollywood", "show", "streaming", "netflix", "hip-hop", "rap", "fashion", "streetwear", "sneaker", "lineup"],
    },
    {
        "name": "Other",
        "emoji": "🗞️",
        "hook": "",
        "keywords": [],
    },
]


def strip_html(s):
    if not s:
        return ""
    return re.sub(r"<[^>]+>", " ", s)


def bucket_for(article):
    # Use title + summary + full body (when present) for theming.
    text = f"{article.get('title','')} {article.get('summary','')} {article.get('_body','')}".lower()
    text = strip_html(text)
    for bucket in BUCKETS:
        if not bucket["keywords"]:
            continue
        # 'not' keywords veto a match
        if any(_kw_match(nk, text) for nk in bucket.get("not", [])):
            continue
        if any(_kw_match(kw, text) for kw in bucket["keywords"]):
            return bucket
    return BUCKETS[-1]


def _kw_match(keyword, text):
    """Word-boundary keyword match. 'ban' matches 'ban' but not 'band'."""
    return re.search(rf"\b{re.escape(keyword)}\b", text) is not None


def title_clean(title):
    return strip_html(title or "").strip()


def _detail_from_body(body, max_chars=220):
    """Pull the strongest single sentence from an article body:
    1) a sentence with a hard number ($, %, millions, stats)
    2) otherwise a quote (someone saying something)
    3) otherwise the first substantive sentence."""
    if not body:
        return ""
    # Clean entities & split into sentences
    clean = strip_html(body)
    clean = clean.replace("&#8217;", "'").replace("&#8220;", '"').replace("&#8221;", '"')
    clean = clean.replace("&#8230;", "...").replace("&amp;", "&")
    sents = re.split(r"(?<=[.!?])\s+", clean)

    # Pass 1: number-bearing sentence (concrete fact)
    for s in sents:
        if re.search(r"\$\s?\d|million|billion|\d+%|percent|\d+(\.\d+)?\s?(bn|m)\b", s):
            s = s.strip()
            if 40 <= len(s) <= max_chars:
                return s
    # Pass 2: a quote
    for s in sents:
        if '"' in s or "“" in s or "said" in s or "told" in s:
            s = s.strip()
            if 40 <= len(s) <= max_chars:
                return s
    # Pass 3: first long sentence
    for s in sents:
        s = s.strip()
        if 60 <= len(s) <= max_chars:
            return s
    return ""


def make_brief(articles, top_n=16, buckets_per_brief=5, stories_per_bucket=2):
    scored = [a for a in articles if not a.get("_noise")]
    scored.sort(key=lambda x: -x.get("_score", 0))

    # Bucket the whole scored set first, then take the top story per bucket
    # so every theme gets represented (not just AI/startup-heavy scores).
    all_bucketed = OrderedDict()
    for a in scored:
        b = bucket_for(a)
        all_bucketed.setdefault(b["name"], {"bucket": b, "articles": []})
        all_bucketed[b["name"]]["articles"].append(a)

    # Rank buckets by their lead story's score, drop Other, cap count
    ranked = []
    for name, entry in all_bucketed.items():
        if name == "Other":
            continue
        lead = max(entry["articles"], key=lambda a: a.get("_score", 0))
        ranked.append((name, entry, lead))
    ranked.sort(key=lambda x: -x[2].get("_score", 0))
    ranked = ranked[:buckets_per_brief]

    lines = []
    for name, entry, lead in ranked:
        b = entry["bucket"]
        emoji = b["emoji"]
        hook = b["hook"]

        lead_line = title_clean(lead.get("title", ""))
        lead_src = lead.get("source", "")
        lines.append(f"{emoji} **{name}** — {lead_line} ({lead_src})")
        if hook:
            lines.append(f"   _{hook}_")

        # When we have full article text, add the strongest fact/quote.
        detail = _detail_from_body(lead.get("_body", ""))
        if detail:
            lines.append(f"   ▸ {detail}")

        others = [a for a in entry["articles"] if a is not lead]
        for a in others[:stories_per_bucket - 1]:
            lines.append(f"   · {title_clean(a.get('title',''))} ({a.get('source','')})")
        lines.append("")

    return "\n".join(lines).strip()


def main():
    with open(os.path.join(WEB, "articles.json")) as f:
        data = json.load(f)
    brief = make_brief(data["articles"])

    header = (
        "# INNOVATIVE HYPE — BRIEF\n"
        f"_Generated {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')} · "
        f"{data.get('feeds_ok',0)}/{data.get('feeds_total',0)} feeds · "
        f"{len(data['articles'])} articles_\n\n"
    )
    out = header + brief + "\n"

    out_path = os.path.join(WEB, "brief.md")
    with open(out_path, "w") as f:
        f.write(out)
    print(out)

    # Also emit a standalone brief.html (self-contained, links to stories)
    html = _render_html(out, data)
    html_path = os.path.join(WEB, "brief.html")
    with open(html_path, "w") as f:
        f.write(html)
    print(f"\nWrote {out_path} and {html_path}")


def _render_html(md, data):
    """Render the markdown brief into a self-contained HTML page."""
    # Parse the markdown: each bucket block starts with emoji **Name** — line,
    # then _hook_ italic, then · bullets.
    blocks = []
    for raw_block in md.strip().split("\n\n"):
        lines = raw_block.strip().split("\n")
        if not lines:
            continue
        # Skip the title line (starts with #) and the italic _Generated_ header
        if lines[0].startswith("#"):
            continue
        if lines[0].startswith("_Generated"):
            continue
        lead_match = re.match(r"^(?P<emoji>\S+)\s+\*\*(?P<name>.+?)\*\*\s+—\s+(?P<title>.+?)\s+\((?P<src>.+?)\)$", lines[0])
        if not lead_match:
            continue
        g = lead_match.groupdict()
        hook = ""
        detail = ""
        bullets = []
        for line in lines[1:]:
            s = line.strip()
            if s.startswith("_") and s.endswith("_") and not hook:
                hook = s[1:-1]
            elif s.startswith("▸") and not detail:
                detail = s[1:].strip()
            elif s.startswith("·"):
                bullets.append(s[1:].strip())
        blocks.append((g["emoji"], g["name"], g["title"], g["src"], hook, detail, bullets))

    # Need links: look up title → link from articles
    title_to_link = {a.get("title", ""): a.get("link", "#") for a in data["articles"]}

    cards = []
    for emoji, name, title, src, hook, detail, bullets in blocks:
        link = title_to_link.get(title, "#")
        bullets_html = "".join(
            f'<li><a href="{title_to_link.get(_extract_title(b), "#")}" target="_blank" rel="noopener">{_md_inline(_extract_title(b))}</a></li>'
            for b in bullets
        )
        hook_html = f'<p class="brief-hook">{_md_inline(hook)}</p>' if hook else ""
        detail_html = f'<p class="brief-detail">▸ {_md_inline(detail)}</p>' if detail else ""
        cards.append(f"""
    <article class="brief-card">
      <div class="brief-head"><span class="brief-emoji">{emoji}</span><h3 class="brief-name">{_md_inline(name)}</h3></div>
      <h4 class="brief-lead"><a href="{link}" target="_blank" rel="noopener">{_md_inline(title)}</a></h4>
      <div class="brief-src">{_md_inline(src)}</div>
      {hook_html}
      {detail_html}
      <ul class="brief-list">{bullets_html}</ul>
    </article>""")

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>INNOVATIVE HYPE — BRIEF</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Oswald:wght@400;500;600;700&family=DM+Sans:wght@300;400;500;600&display=swap" rel="stylesheet">
<style>
  :root {{ --white:#fff; --off-white:#f8f8f8; --ink:#0a0a0a; --ink-light:#3a3a3a; --ink-muted:#888; --gold:#d4af37; --gold-dark:#b8860b; --border:#e8e8e8; }}
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{ font-family:'DM Sans',system-ui,sans-serif; background:var(--white); color:var(--ink); -webkit-font-smoothing:antialiased; }}
  .wrap {{ max-width:760px; margin:0 auto; padding:2.5rem 1.5rem; }}
  .brief-title {{ font-family:'Oswald',sans-serif; font-weight:700; font-size:2rem; text-transform:uppercase; letter-spacing:-0.02em; margin-bottom:.25rem; }}
  .brief-meta {{ font-size:.75rem; color:var(--ink-muted); text-transform:uppercase; letter-spacing:.05em; margin-bottom:2rem; }}
  .brief-card {{ background:var(--off-white); border:1px solid var(--border); border-top:3px solid var(--gold); padding:1.25rem 1.5rem; margin-bottom:1.25rem; }}
  .brief-head {{ display:flex; align-items:center; gap:.5rem; margin-bottom:.4rem; }}
  .brief-emoji {{ font-size:1.1rem; }}
  .brief-name {{ font-family:'Oswald',sans-serif; font-weight:600; font-size:1rem; text-transform:uppercase; letter-spacing:.04em; color:var(--gold-dark); }}
  .brief-lead {{ font-family:'Oswald',sans-serif; font-weight:600; font-size:1.2rem; line-height:1.25; margin-bottom:.25rem; }}
  .brief-lead a {{ color:var(--ink); text-decoration:none; }}
  .brief-lead a:hover {{ color:var(--gold-dark); }}
  .brief-src {{ font-size:.7rem; color:var(--ink-muted); text-transform:uppercase; letter-spacing:.04em; margin-bottom:.5rem; }}
  .brief-hook {{ font-size:.9rem; line-height:1.5; color:var(--ink-light); font-style:italic; margin-bottom:.5rem; }}
  .brief-detail {{ font-size:.85rem; line-height:1.5; color:var(--ink); margin-bottom:.5rem; padding-left:.9rem; border-left:2px solid var(--gold); }}
  .brief-list {{ list-style:none; padding-left:0; margin-top:.25rem; }}
  .brief-list li {{ font-size:.85rem; line-height:1.5; color:var(--ink-light); padding:.15rem 0 .15rem 1.1rem; position:relative; }}
  .brief-list li::before {{ content:'·'; position:absolute; left:0; color:var(--gold-dark); }}
  .brief-list a {{ color:var(--ink-light); text-decoration:none; }}
  .brief-list a:hover {{ color:var(--gold-dark); }}
  .back {{ display:inline-block; margin-top:2rem; font-family:'Oswald',sans-serif; font-size:.8rem; text-transform:uppercase; letter-spacing:.05em; color:var(--ink); text-decoration:none; border-bottom:2px solid var(--gold); padding-bottom:2px; }}
</style>
</head>
<body>
<div class="wrap">
  <h1 class="brief-title">Innovative Hype — Brief</h1>
  <div class="brief-meta">_Generated {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}_</div>
  {''.join(cards)}
  <a class="back" href="index.html">← Back to feed</a>
</div>
</body>
</html>
"""


def _extract_title(bullet):
    """Bullets are plain 'title (source)' strings — return just the title."""
    m = re.match(r"^(.*?)\s*\([^)]*\)$", bullet)
    return m.group(1).strip() if m else bullet


if __name__ == "__main__":
    main()
