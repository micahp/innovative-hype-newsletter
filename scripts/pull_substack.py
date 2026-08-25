#!/usr/bin/env python3
"""pull_substack.py - pull the Innovative Hype Substack archive into the corpus.

The Substack posts are the longest-form, most-defended statements of Micah's
positions. Until 2026-08-24 they were the one voice source that had never been
on this box at all: extract_angles.py read two nitter scrapes and nothing else,
so seven years of 1,500-to-2,500-word argument were absent from the angle
inventory.

Two endpoints, and it needs both:

  /api/v1/archive  enumerates every post (id, title, slug, post_date). This is
                   the AUTHORITY on how many posts exist. Measured 2026-08-24:
                   15 posts, offset=15 and offset=30 both return 0.
  /feed            carries the full body in <content:encoded>. Measured the
                   same day: all 15 posts present, bodies 8,387 to 29,415
                   chars.

The feed happening to hold the whole archive is a fact about a publication that
has posted 15 times in seven years, not a property of Substack RSS. So the
archive count is fetched separately and any post the feed does not carry is
named and counted, rather than quietly missing.

    python3 scripts/pull_substack.py
    python3 scripts/pull_substack.py --dry-run
"""
import argparse
import html
import json
import os
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(REPO, "corpus", "substack_posts.jsonl")

PUB = os.environ.get("IH_SUBSTACK", "https://innovativehype.substack.com")
ARCHIVE = PUB + "/api/v1/archive?sort=new&search=&offset=%d&limit=50"
FEED = PUB + "/feed"
UA = "Mozilla/5.0 (compatible; innovative-hype-newsletter/1.0)"


def _get(url, timeout=30):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def fetch_archive_index():
    """Every post the publication says it has. Raises rather than returning a
    short list: a truncated index would silently shrink the corpus and the
    extractor would still complete."""
    posts, offset = [], 0
    while True:
        raw = _get(ARCHIVE % offset)
        page = json.loads(raw)
        if not page:
            break
        posts.extend(page)
        offset += len(page)
        if len(page) < 50:
            break
    if not posts:
        raise RuntimeError(
            "the Substack archive index at %s came back empty. These posts are "
            "the longest-form source for the angle inventory, so an empty "
            "index raises instead of writing a corpus that is missing them."
            % (ARCHIVE % 0))
    return posts


def strip_html(s):
    s = re.sub(r"(?is)<(script|style).*?</\1>", " ", s or "")
    s = re.sub(r"(?i)</(p|div|h[1-6]|li|blockquote)>", "\n\n", s)
    s = re.sub(r"(?i)<br\s*/?>", "\n", s)
    s = re.sub(r"<[^>]+>", " ", s)
    s = html.unescape(s)
    s = re.sub(r"[ \t]+", " ", s)
    return re.sub(r"\n{3,}", "\n\n", s).strip()


def fetch_feed_bodies():
    """slug/link -> (title, pubdate, body text) from <content:encoded>."""
    root = ET.fromstring(_get(FEED))
    out = {}
    for item in root.findall(".//item"):
        link = (item.findtext("link") or "").strip()
        body = ""
        for child in item:
            if child.tag.endswith("encoded") and child.text:
                body = child.text
                break
        if not body:
            body = item.findtext("description") or ""
        slug = link.rstrip("/").split("/")[-1]
        out[slug] = {
            "title": (item.findtext("title") or "").strip(),
            "date": (item.findtext("pubDate") or "").strip(),
            "link": link,
            "text": strip_html(body),
        }
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--min-len", type=int, default=400,
                    help="a post shorter than this is a stub, not an argument")
    args = ap.parse_args()

    index = fetch_archive_index()
    print("archive index: %d posts" % len(index))

    bodies = fetch_feed_bodies()
    print("feed carries:  %d bodies" % len(bodies))

    rows, missing, stubs = [], [], []
    for p in index:
        slug = p.get("slug") or ""
        b = bodies.get(slug)
        if not b:
            missing.append("%s (%s)" % (p.get("title", "?")[:60], slug))
            continue
        text = b["text"]
        if len(text) < args.min_len:
            stubs.append("%s (%d chars)" % (p.get("title", "?")[:60], len(text)))
            continue
        rows.append({
            "id": str(p.get("id")),
            "slug": slug,
            "date": p.get("post_date") or b["date"],
            "title": p.get("title") or b["title"],
            "link": b["link"],
            "text": text,
        })

    # Say the zero, and say it per-category. "15 posts" and "15 posts of which
    # 9 had no body" look identical downstream otherwise.
    print("usable posts:  %d" % len(rows))
    print("total chars:   %d" % sum(len(r["text"]) for r in rows))
    if missing:
        print("NOT IN FEED (%d) - the archive lists these and the feed does "
              "not carry them, so their argument is absent from the corpus:"
              % len(missing))
        for m in missing:
            print("   - " + m)
    else:
        print("NOT IN FEED: 0 - the feed covers the whole archive")
    if stubs:
        print("TOO SHORT (%d, under %d chars):" % (len(stubs), args.min_len))
        for s in stubs:
            print("   - " + s)

    if not rows:
        raise RuntimeError(
            "0 usable posts. The index reported %d. Writing an empty corpus "
            "here would silently drop the longest-form voice source, so this "
            "raises." % len(index))

    if args.dry_run:
        for r in rows:
            print("  %s  %-58s %6d chars" % (r["date"][:10], r["title"][:58],
                                             len(r["text"])))
        return 0

    with open(OUT, "w") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print("wrote %s" % OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
