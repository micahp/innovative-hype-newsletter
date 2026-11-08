#!/usr/bin/env python3
"""build_substack_page.py - write web/newsletter.html from the Substack corpus.

Reads corpus/substack_posts.jsonl (written by pull_substack.py) and lists the
newsletter posts and the podcast episodes. Each entry links to its post on
Substack; the page does not republish post bodies.

Fails loudly: exits non-zero if the corpus is missing or empty, so the page is
never overwritten with an empty list.

    python3 scripts/build_substack_page.py
"""
import html
import json
import os
import re
import sys
from datetime import datetime

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(REPO, "corpus", "substack_posts.jsonl")
OUT = os.path.join(REPO, "web", "newsletter.html")
SPOTIFY_SHOW = "https://open.spotify.com/show/4BOYK9pMvz8X4jq1Pk3ML7"
EPISODE_RE = re.compile(r"^The Innovative Hype Podcast (\d{3}):\s*(.*)$")
DEK_CHARS = 220


def load():
    if not os.path.exists(SRC):
        sys.exit("missing %s; run pull_substack.py first" % SRC)
    with open(SRC, encoding="utf-8") as f:
        rows = [json.loads(line) for line in f if line.strip()]
    if not rows:
        sys.exit("%s is empty; page not written" % SRC)
    for r in rows:
        r["when"] = datetime.fromisoformat(r["date"].replace("Z", "+00:00"))
        m = EPISODE_RE.match(r["title"])
        r["episode"] = m.group(1) if m else None
    rows.sort(key=lambda r: r["when"], reverse=True)
    return rows


def dek(text):
    plain = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", text or "")).strip()
    if len(plain) <= DEK_CHARS:
        return plain
    return plain[:DEK_CHARS].rsplit(" ", 1)[0] + "…"


def row(r):
    when = r["when"].strftime("%b %d, %Y").lower()
    tag = '<span class="ep">episode %s</span> ' % r["episode"] if r["episode"] else ""
    return (
        '<li><div class="when">%s%s</div>'
        '<h2><a href="%s">%s</a></h2>'
        '<p>%s</p></li>'
    ) % (tag, html.escape(when), html.escape(r["link"]),
         html.escape(r["title"]), html.escape(dek(r["text"])))


def page(posts, episodes):
    posts_html = "\n".join(row(r) for r in posts)
    episodes_html = "\n".join(row(r) for r in episodes)
    return """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>newsletter and podcast · innovative hype</title>
<meta name="description" content="Innovative Hype newsletter posts and podcast episodes.">
<meta property="og:type" content="website">
<meta property="og:site_name" content="Innovative Hype">
<meta property="og:title" content="Newsletter and podcast · Innovative Hype">
<meta property="og:description" content="Innovative Hype newsletter posts and podcast episodes.">
<meta property="og:url" content="https://innovativehype.xyz/newsletter.html">
<meta property="og:image" content="https://innovativehype.xyz/og-image.png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="Newsletter and podcast · Innovative Hype">
<meta name="twitter:description" content="Innovative Hype newsletter posts and podcast episodes.">
<meta name="twitter:image" content="https://innovativehype.xyz/og-image.png">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Jost:wght@400;500;700;900&family=Space+Mono:wght@400;700&display=swap" rel="stylesheet">
<style>
  :root { --paper:#f3f0e7; --ink:#1a1a1a; --red:#e2231a; --blue:#21409a; --yellow:#f4c300; --rule:5px; --hair:2px; --pad:clamp(20px,5vw,64px); }
  :root[data-theme="dark"] { --paper:#15140f; --ink:#f3f0e7; }
  @media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) { --paper:#15140f; --ink:#f3f0e7; } }
  *{box-sizing:border-box;margin:0;padding:0}
  body{background:var(--paper);color:var(--ink);font-family:"Jost",system-ui,sans-serif;line-height:1.45;-webkit-font-smoothing:antialiased}
  a{color:inherit}
  .wrap{max-width:900px;margin:0 auto;padding:0 var(--pad)}
  header{display:flex;align-items:center;justify-content:space-between;gap:16px;padding:24px 0;border-bottom:var(--rule) solid var(--ink);flex-wrap:wrap}
  .brand{font-weight:900;font-size:21px;letter-spacing:-.01em;text-decoration:none}
  nav{display:flex;gap:22px;flex-wrap:wrap}
  nav a{text-decoration:none;font-family:"Space Mono",monospace;font-size:12px;font-weight:700;letter-spacing:.12em;text-transform:uppercase}
  nav a:hover{color:var(--blue)}
  h1{font-weight:900;font-size:clamp(44px,10vw,88px);line-height:.92;letter-spacing:-.035em;margin:56px 0 18px}
  .lede{font-size:clamp(18px,2.4vw,22px);max-width:640px;margin-bottom:48px}
  .section{margin-top:64px}
  .eyebrow{font-family:"Space Mono",monospace;font-size:12px;font-weight:700;letter-spacing:.14em;text-transform:uppercase;display:flex;align-items:center;gap:10px;opacity:.75;margin-bottom:14px}
  .eyebrow:before{content:"";width:22px;height:var(--hair);background:currentColor}
  ul.list{list-style:none;border-top:var(--hair) solid var(--ink)}
  ul.list li{padding:26px 0;border-bottom:var(--hair) solid var(--ink)}
  .when{font-family:"Space Mono",monospace;font-size:12px;font-weight:700;letter-spacing:.12em;text-transform:uppercase;opacity:.7}
  .ep{color:var(--red);margin-right:8px}
  ul.list h2{font-weight:700;font-size:clamp(22px,3vw,30px);line-height:1.15;margin:8px 0;letter-spacing:-.01em}
  ul.list h2 a{text-decoration:none}
  ul.list h2 a:hover{color:var(--blue);text-decoration:underline}
  ul.list p{opacity:.85;max-width:680px}
  footer{margin:64px 0 48px;padding-top:20px;border-top:var(--rule) solid var(--ink);font-family:"Space Mono",monospace;font-size:12px;letter-spacing:.12em;text-transform:uppercase}
  footer a{margin-right:18px}
</style>
</head>
<body>
<div class="wrap">
<header>
  <a class="brand" href="index.html">innovative hype</a>
  <nav>
    <a href="#newsletter">newsletter</a>
    <a href="#podcast">podcast</a>
    <a href="https://innovativehype.substack.com/">substack</a>
  </nav>
</header>

<h1>newsletter &amp; podcast</h1>
<p class="lede">essays and roundups, and the podcast episodes. each entry opens the full post on substack.</p>

<section class="section" id="newsletter">
  <div class="eyebrow">newsletter</div>
  <ul class="list">
%(posts)s
  </ul>
</section>

<section class="section" id="podcast">
  <div class="eyebrow">podcast</div>
  <p class="lede">listen on <a href="%(spotify)s">spotify</a>. episode notes are on substack.</p>
  <ul class="list">
%(episodes)s
  </ul>
</section>

<footer>
  <a href="https://innovativehype.substack.com/">substack</a>
  <a href="%(spotify)s">spotify</a>
  <a href="index.html">home</a>
</footer>
</div>
</body>
</html>
""" % {"posts": posts_html, "episodes": episodes_html, "spotify": SPOTIFY_SHOW}


def main():
    rows = load()
    episodes = [r for r in rows if r["episode"]]
    posts = [r for r in rows if not r["episode"]]
    if not posts:
        sys.exit("no newsletter posts found in corpus; page not written")
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(page(posts, episodes))
    print("wrote %s: %d posts, %d episodes" % (OUT, len(posts), len(episodes)))


if __name__ == "__main__":
    main()
