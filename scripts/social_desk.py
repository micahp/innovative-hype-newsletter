#!/usr/bin/env python3
"""social_desk.py — turn traceable brief cards into postable social copy.

Reads web/brief-cards.json, and for each card:
  1. refuses it unless the card can be traced to a real article
  2. pulls the article's own photo (og:image, or the feed's media tag)
  3. renders both branded card images
  4. writes the 200-250 word Instagram/X post in Micah's register

Output: web/social.json + web/social.html, a page with the image, the
copy, and a copy button per post.

The post is written from the card's PARAGRAPH and DATA POINT only. The
voice profile supplies register, never facts — that distinction is the
whole reason the desk was inventing AT&T statistics.

Usage:
  python3 scripts/social_desk.py            # top 8 cards
  IH_SOCIAL_N=20 python3 scripts/social_desk.py
"""
import html as _html
import json
import os
import re
import sys
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import make_card_image
import narrative_desk

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEB = os.path.join(REPO, "web")
IMG_DIR = os.path.join(WEB, "social")
N = int(os.environ.get("IH_SOCIAL_N", "8"))

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/125.0 Safari/537.36")


def og_image(url):
    """The article's own social photo. Publishers all set this because it
    is what their own share cards use, which makes it the one image we can
    expect to exist for an arbitrary story."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        raw = urllib.request.urlopen(req, timeout=12).read()
        page = raw.decode("utf-8", "ignore")[:250000]
    except Exception as e:
        return None, f"{type(e).__name__}"
    for pat in (r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)',
                r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image["\']',
                r'<meta[^>]+name=["\']twitter:image["\'][^>]+content=["\']([^"\']+)'):
        m = re.search(pat, page)
        if m:
            return _html.unescape(m.group(1)), None
    return None, "no og:image"


def fetch(url, dest):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        data = urllib.request.urlopen(req, timeout=20).read()
        if len(data) < 5000:
            return False
        with open(dest, "wb") as f:
            f.write(data)
        return True
    except Exception:
        return False


POST_SYSTEM = (
    "You write Instagram and X posts for Innovative Hype, Micah's tech and "
    "culture publication. Given ONE story and the register the author writes "
    "in, produce a post of 200 to 250 words. This length is a requirement, "
    "not a target: under 200 words will be rejected. Get there with analysis "
    "and consequence, never with padding or invented detail.\n\n"
    "HARD RULES:\n"
    "- Every fact, number, company and name must come from the STORY block. "
    "The voice samples show TONE ONLY. Never take a fact from them.\n"
    "- Never invent a statistic. If the story has one number, use that one.\n"
    "- Open with the concrete fact, not a throat-clear.\n"
    "- Short declarative sentences. Lowercase is fine mid-post. No hashtags, "
    "no emoji, no 'in today's world', no calls to action.\n"
    "- Land on the implication, the part a reader would not get from the "
    "headline alone.\n"
    "- NEVER use em dashes.\n\n"
    'Return STRICT JSON: {"post": str}'
)


def write_post(card, voice_entries):
    story = (
        f"HEADLINE: {card.get('narrative','')}\n"
        f"STORY: {card.get('paragraph','')}\n"
        f"KEY DATA POINT: {card.get('data_point','')}\n"
        f"SOURCES: " + ", ".join(
            f"{s.get('source','')} ({s.get('headline','')})"
            for s in card.get("sources", [])[:3])
    )
    voice = ""
    for e in voice_entries[:2]:
        voice += (f"\nOn {e.get('topic')}, his stance: {e.get('stance')} "
                  f"(tone: {e.get('tone')})")
        for ex in (e.get("exemplars") or [])[:1]:
            voice += f'\n  register sample (TONE ONLY, not a source): "{ex}"'
    user = f"STORY:\n{story}\n\nHOW HE WRITES:{voice or ' (no profile entry; use a plain analytical register)'}"
    # Asking for "200-250 words" once reliably produced 74-158. The length
    # is part of the spec (it is what fits an IG caption and reads as a
    # real post rather than a tweet), so it gets checked and retried
    # instead of hoped for.
    for attempt in range(3):
        u = user if attempt == 0 else (
            user + f"\n\nYour previous attempt was {last} words. That is too "
            "short. Write 200-250 words. Add analysis and consequence, never "
            "invented facts.")
        raw = narrative_desk.call_llm(POST_SYSTEM, u, max_tokens=1400)
        try:
            post = json.loads(raw or "").get("post", "").strip()
        except (ValueError, TypeError):
            post = ""
        last = len(post.split())
        if 190 <= last <= 275:
            return post
        if attempt == 2:
            return post  # take the best we got rather than dropping the card
    return ""


def page(posts, updated):
    rows = []
    for i, p in enumerate(posts):
        imgs = "".join(
            f'<a href="{u}" target="_blank"><img src="{u}"></a>'
            for u in p["images"])
        srcs = " · ".join(
            f'<a href="{_html.escape(s["url"])}" target="_blank">{_html.escape(s["source"])}</a>'
            for s in p["sources"])
        rows.append(f"""
  <article class="post">
    <div class="imgs">{imgs or '<div class="noimg">no photo available</div>'}</div>
    <div class="body">
      <p class="kicker">{_html.escape(p['kicker'])}</p>
      <h2>{_html.escape(p['narrative'])}</h2>
      <textarea id="t{i}" readonly>{_html.escape(p['post'])}</textarea>
      <div class="row">
        <button onclick="cp({i},this)">copy post</button>
        <span class="wc">{p['words']} words</span>
        <span class="src">{srcs}</span>
      </div>
      <p class="prov">based on {p['source_count']} article(s) ·
         {p['provenance']} matching terms</p>
    </div>
  </article>""")

    return f"""<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>IH Social Desk</title>
<link href="https://fonts.googleapis.com/css2?family=Jost:wght@300;400;500;700;900&family=Space+Mono:wght@400;700&display=swap" rel="stylesheet">
<style>
:root{{--bg:#15140f;--fg:#f3f0e7;--dim:#8b877c;--line:#2e2c26;--red:#e2231a}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--bg);color:var(--fg);font-family:Jost,system-ui,sans-serif}}
header{{padding:2rem 1.5rem 1rem;border-bottom:1px solid var(--line)}}
h1{{font-size:1.5rem;font-weight:500;margin:0;letter-spacing:-.01em}}
header p{{color:var(--dim);font-family:'Space Mono',monospace;font-size:.75rem;margin:.4rem 0 0}}
main{{max-width:1100px;margin:0 auto;padding:1.5rem}}
.post{{display:grid;grid-template-columns:300px 1fr;gap:1.5rem;padding:1.75rem 0;border-bottom:1px solid var(--line)}}
@media(max-width:760px){{.post{{grid-template-columns:1fr}}}}
.imgs{{display:flex;flex-direction:column;gap:.5rem}}
.imgs img{{width:100%;border:1px solid var(--line)}}
.noimg{{color:var(--dim);font-family:'Space Mono',monospace;font-size:.7rem;padding:2rem 0;text-align:center;border:1px dashed var(--line)}}
.kicker{{font-family:'Space Mono',monospace;font-size:.65rem;letter-spacing:.12em;color:var(--red);margin:0 0 .4rem;text-transform:uppercase}}
h2{{font-size:1.15rem;font-weight:500;margin:0 0 .75rem;line-height:1.3}}
textarea{{width:100%;height:230px;background:#0e0d0a;color:var(--fg);border:1px solid var(--line);
 padding:.9rem;font-family:Jost,sans-serif;font-size:.95rem;line-height:1.55;resize:vertical}}
.row{{display:flex;align-items:center;gap:1rem;margin-top:.6rem;flex-wrap:wrap}}
button{{background:var(--fg);color:var(--bg);border:0;padding:.5rem 1rem;font-family:'Space Mono',monospace;
 font-size:.7rem;cursor:pointer;letter-spacing:.05em}}
button:hover{{background:var(--red);color:#fff}}
.wc,.src,.prov{{font-family:'Space Mono',monospace;font-size:.68rem;color:var(--dim)}}
.src a{{color:var(--dim)}}
.prov{{margin:.5rem 0 0}}
a{{color:var(--fg)}}
</style></head><body>
<header>
  <h1>Social desk</h1>
  <p>{len(posts)} posts ready · generated {updated} · every post traced to a real article</p>
</header>
<main>{''.join(rows)}</main>
<script>
function cp(i,b){{const t=document.getElementById('t'+i);t.select();
document.execCommand('copy');const o=b.textContent;b.textContent='copied';
setTimeout(()=>b.textContent=o,1200);}}
</script>
</body></html>"""


def main():
    from datetime import datetime, timezone
    os.makedirs(IMG_DIR, exist_ok=True)

    cards = json.load(open(os.path.join(WEB, "brief-cards.json")))["cards"]
    cards = [c for c in cards if c.get("sources")]
    cards.sort(key=lambda c: -c.get("lead_score", 0))
    cards = cards[:N]
    print(f"{len(cards)} cards selected")

    vp = narrative_desk._load_voice_profile()
    posts = []
    for i, c in enumerate(cards):
        key = c.get("story_key", str(i))
        src = c["sources"][0]
        print(f"[{i+1}/{len(cards)}] {c.get('narrative','')[:58]}")

        images = []
        img_url, err = og_image(src["url"])
        photo = os.path.join(IMG_DIR, f"{key}_photo.jpg")
        if img_url and fetch(img_url, photo):
            for style in ("mono", "bauhaus"):
                out = os.path.join(IMG_DIR, f"{key}_{style}.jpg")
                try:
                    make_card_image.build(photo, out, c.get("kicker", "News"),
                                          c.get("narrative", ""),
                                          src.get("source", ""), style)
                    images.append(f"social/{os.path.basename(out)}")
                except Exception as e:
                    print(f"    image {style} failed: {e}")
            os.remove(photo)
        else:
            print(f"    no photo ({err or 'download failed'})")

        # Voice entries whose categories touch this card's signature.
        ve = [e for e in vp if not e.get("categories")
              or any(c.get("kicker", "").lower() in cat.lower()
                     or cat.lower() in c.get("kicker", "").lower()
                     for cat in e.get("categories", []))] or vp

        post = write_post(c, ve)
        if not post:
            print("    post generation failed, skipping")
            continue
        posts.append({
            "story_key": key,
            "kicker": c.get("kicker", ""),
            "narrative": c.get("narrative", ""),
            "post": post,
            "words": len(post.split()),
            "images": images,
            "sources": c.get("sources", [])[:3],
            "source_count": c.get("source_count", len(c.get("sources", []))),
            "provenance": (c.get("provenance") or {}).get("distinctive_hits", "n/a"),
        })
        print(f"    {len(post.split())} words, {len(images)} images")

    updated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    json.dump({"updated": updated, "posts": posts},
              open(os.path.join(WEB, "social.json"), "w"),
              ensure_ascii=False, indent=2)
    with open(os.path.join(WEB, "social.html"), "w") as f:
        f.write(page(posts, updated))
    print(f"\nwrote web/social.html with {len(posts)} posts")


if __name__ == "__main__":
    main()
