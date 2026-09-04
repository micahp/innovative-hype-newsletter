#!/usr/bin/env python3
"""make_card_image.py — branded Instagram image for a brief card.

The text is NOT generated. It is composited with Pillow at exact pixel
positions, so a headline renders identically every run and costs nothing.
Diffusion models still fumble long strings and cannot be made deterministic,
which is the wrong trade for a publication that posts its own headlines.

Brand comes from the live site (/var/www/ih-src/v3.html) and logo.svg:
  Bauhaus primaries red/yellow/blue, paper #f3f0e7, ink #15140f,
  Jost for display, Space Mono for meta, white triangle in the corner.

Usage: make_card_image.py PHOTO OUT --kicker K --headline H --source S
"""
import argparse
import os

from PIL import Image, ImageDraw, ImageFont

W, H = 1080, 1350  # 4:5, Instagram portrait

PAPER = (243, 240, 231)
INK = (21, 20, 15)
RED = (226, 35, 26)
YELLOW = (244, 195, 0)
BLUE = (33, 64, 154)

FONTS = os.path.join(os.path.dirname(__file__), "..", "assets", "fonts")


def font(name, size, weight=None):
    f = ImageFont.truetype(os.path.join(FONTS, name), size)
    if weight is not None:
        try:
            f.set_variation_by_axes([weight])
        except Exception:
            pass
    return f


def fit_photo(path, box_w, box_h):
    """Cover-crop the photo to fill the box without distorting it."""
    im = Image.open(path).convert("RGB")
    scale = max(box_w / im.width, box_h / im.height)
    im = im.resize((round(im.width * scale), round(im.height * scale)), Image.LANCZOS)
    left = (im.width - box_w) // 2
    top = (im.height - box_h) // 2
    return im.crop((left, top, left + box_w, top + box_h))


def draw_tracked(draw, xy, text, fnt, fill, tracking):
    """Letterspacing by explicit per-glyph advance. A joined space between
    letters is far too wide for a kicker; a few px of tracking is the look."""
    x, y = xy
    for ch in text:
        draw.text((x, y), ch, font=fnt, fill=fill)
        x += draw.textlength(ch, font=fnt) + tracking
    return x


def wrap(draw, text, fnt, max_w):
    words, lines, cur = text.split(), [], ""
    for w in words:
        trial = f"{cur} {w}".strip()
        if draw.textlength(trial, font=fnt) <= max_w:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def build_bauhaus(photo, out, kicker, headline, source):
    canvas = Image.new("RGB", (W, H), PAPER)
    draw = ImageDraw.Draw(canvas)

    photo_h = 760
    canvas.paste(fit_photo(photo, W, photo_h), (0, 0))

    # Bauhaus rule under the photo: the three primaries, red widest.
    y = photo_h
    draw.rectangle([0, y, 560, y + 14], fill=RED)
    draw.rectangle([560, y, 820, y + 14], fill=YELLOW)
    draw.rectangle([820, y, W, y + 14], fill=BLUE)

    pad = 64
    cursor = y + 14 + 52

    kfont = font("SpaceMono-Bold.ttf", 26)
    ktext = kicker.upper()
    kw = draw.textlength(ktext, font=kfont)
    draw.rectangle([pad, cursor - 10, pad + kw + 28, cursor + 40], fill=RED)
    draw.text((pad + 14, cursor - 4), ktext, font=kfont, fill=PAPER)
    cursor += 76

    # Same headline face and weight as the mono style, which is the
    # podcast cover's: open counters, 500 not 800.
    for size in (76, 70, 64, 58, 52, 46):
        hfont = font("Jost.ttf", size, weight=500)
        lines = wrap(draw, headline, hfont, W - pad * 2)
        line_h = round(size * 1.16)
        if cursor + len(lines) * line_h < H - 150:
            break
    for ln in lines:
        draw.text((pad, cursor), ln, font=hfont, fill=INK)
        cursor += line_h

    sfont = font("SpaceMono-Regular.ttf", 24)
    draw.text((pad, H - 108), f"via {source}", font=sfont, fill=(110, 106, 96))

    lfont = font("Jost.ttf", 30, weight=900)
    lock = "innovative hype"
    lw = draw.textlength(lock, font=lfont)
    bx0, by0 = W - pad - lw - 92, H - 118
    draw.rectangle([bx0, by0, W - pad, by0 + 62], fill=INK)
    draw.polygon([(W - pad - 30, by0 + 62), (W - pad, by0 + 32), (W - pad, by0 + 62)], fill=PAPER)
    draw.text((bx0 + 20, by0 + 14), lock, font=lfont, fill=PAPER)

    canvas.save(out, quality=94)
    return out


def build_mono(photo, out, kicker, headline, source):
    """The podcast cover's identity: pure black, white lowercase geometric
    sans, and the big white corner wedge. The layout is monochrome; the
    photo keeps its own colour, which is the only colour on the card.

    Headline weight is 500, not 800. The cover's letterforms are open and
    wide; heavy Jost closes the counters and is what made the first pass
    hard to read at thumbnail size.
    """
    BLACK, WHITE = (0, 0, 0), (255, 255, 255)
    canvas = Image.new("RGB", (W, H), BLACK)
    draw = ImageDraw.Draw(canvas)

    photo_h = 700
    canvas.paste(fit_photo(photo, W, photo_h), (0, 0))

    pad = 72
    cursor = photo_h + 64

    # Kicker: mono, lightly tracked over a hairline rule, no fill chip.
    kfont = font("SpaceMono-Bold.ttf", 24)
    draw_tracked(draw, (pad, cursor), kicker.upper(), kfont, WHITE, 4)
    cursor += 46
    draw.rectangle([pad, cursor, W - pad, cursor + 2], fill=(70, 70, 70))
    cursor += 44

    for size in (76, 70, 64, 58, 52, 46):
        hfont = font("Jost.ttf", size, weight=500)
        lines = wrap(draw, headline, hfont, W - pad * 2)
        line_h = round(size * 1.16)
        if cursor + len(lines) * line_h < H - 170:
            break
    for ln in lines:
        draw.text((pad, cursor), ln, font=hfont, fill=WHITE)
        cursor += line_h

    # The wedge: a corner mark, not a design element. At cover scale it
    # dominates a photo card, so it stays small enough to read as a nod.
    wedge = 104
    draw.polygon([(W - wedge, H), (W, H - wedge), (W, H)], fill=WHITE)

    sfont = font("SpaceMono-Regular.ttf", 22)
    draw.text((pad, H - 112), f"via {source}", font=sfont, fill=(150, 150, 150))

    lfont = font("Jost.ttf", 34, weight=500)
    draw.text((pad, H - 74), "innovative hype", font=lfont, fill=WHITE)

    canvas.save(out, quality=94)
    return out


STYLES = {"bauhaus": build_bauhaus, "mono": build_mono}


def build(photo, out, kicker, headline, source, style="mono"):
    return STYLES[style](photo, out, kicker, headline, source)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("photo")
    p.add_argument("out")
    p.add_argument("--kicker", required=True)
    p.add_argument("--headline", required=True)
    p.add_argument("--source", required=True)
    p.add_argument("--style", default="mono", choices=sorted(STYLES))
    a = p.parse_args()
    print(build(a.photo, a.out, a.kicker, a.headline, a.source, a.style))
