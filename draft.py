#!/usr/bin/env python3
"""
Innovative Hype — Stage 2: Newsletter Draft Generator
======================================================
Reads digest.json and outputs a structured prompt for newsletter generation.
The actual LLM drafting is done by Hermes (in cron mode) or via an external
API if configured.

Usage:
    python3 draft.py                           # outputs prompt.md
    python3 draft.py --config config.local.yaml
    python3 draft.py --output newsletter.md    # custom output path
"""

import json
import sys
import os
from pathlib import Path
from datetime import datetime, timezone


def load_config(config_path="config.yaml"):
    path = Path(config_path)
    if not path.exists():
        print(f"ERROR: Config file not found: {config_path}")
        sys.exit(1)

    try:
        import yaml
        with open(path) as f:
            return yaml.safe_load(f)
    except ImportError:
        with open(path) as f:
            return json.load(f)


def build_prompt(digest, config):
    """Build a structured newsletter prompt from the digest."""
    newsletter_cfg = config.get("newsletter", {})
    pub_name = newsletter_cfg.get("publication_name", "Innovative Hype")
    story_count = newsletter_cfg.get("story_count", 5)
    sponsor = newsletter_cfg.get("sponsor_placeholder", "")

    articles = digest.get("articles", [])[:story_count]

    sections = []
    sections.append(f"# {pub_name} — AI News Roundup")
    sections.append(f"*{datetime.now().strftime('%B %d, %Y')}*")
    sections.append("")

    # Source articles
    sections.append("## Source Articles")
    sections.append("")
    for i, art in enumerate(articles, 1):
        sections.append(f"### {i}. {art['title']}")
        sections.append(f"- **Source:** {art['source']}")
        sections.append(f"- **Link:** {art['link']}")
        sections.append(f"- **Published:** {art.get('published', 'unknown')}")
        sections.append("")
        sections.append(f"{art['summary']}")
        sections.append("")

    # Prompt instructions
    sections.append("---")
    sections.append("")
    sections.append("## Writing Instructions for the AI Agent")
    sections.append("")
    sections.append("You are writing for **Innovative Hype**, a Substack newsletter by Micah Peoples")
    sections.append("that curates and analyzes the most important AI and tech news with a")
    sections.append("conversational, opinionated voice.")
    sections.append("")
    sections.append("### Brand Voice")
    sections.append("- Conversational and first-person (use 'I' occasionally)")
    sections.append("- Opinionated but thoughtful — don't just report, analyze")
    sections.append("- Cross-domain: connect AI stories to culture, business, and society")
    sections.append("- Texas/Austin flavor is welcome but don't force it")
    sections.append("- No corporate jargon, no clickbait")
    sections.append("")
    sections.append("### Structure")
    sections.append("1. **Opening hook** — 2-3 sentences that grab attention")
    sections.append("2. **Top Story** — the biggest AI news, ~200 words with analysis")
    sections.append(f"3. **{story_count - 1} More Stories** — each ~100-150 words with commentary")
    sections.append("4. **Quick Hits** — 2-3 one-liner stories with links")
    sections.append("5. **The Bottom Line** — wrap-up and CTA")
    sections.append("")
    sections.append("### Formatting")
    sections.append("- Write in Markdown (H1 title, H2 for sections, bold for emphasis)")
    sections.append("- Include links to sources")
    sections.append("- Total length: 800-1200 words")
    sections.append("- End with a CTA: 'Subscribe at innovativehype.substack.com'")
    sections.append("")
    if sponsor:
        sections.append(f"> {sponsor}")
        sections.append("")

    return "\n".join(sections)


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Generate newsletter draft prompt from digest"
    )
    parser.add_argument("--config", default="config.yaml", help="Config file path")
    parser.add_argument("--digest", default="digest.json", help="Input digest file")
    parser.add_argument("--output", default="newsletter.md", help="Output path")
    args = parser.parse_args()

    config = load_config(args.config)
    out_path = args.output

    # Load digest
    digest_path = Path(args.digest)
    if not digest_path.exists():
        print(f"ERROR: Digest file not found: {args.digest}")
        print("Run research.py first to generate the digest.")
        sys.exit(1)

    with open(digest_path) as f:
        digest = json.load(f)

    if not digest.get("articles"):
        print("WARNING: Digest is empty — no articles to draft from.")
        print("         Check your RSS feeds and filter settings.")
        # Still output a template
        prompt = "No articles available for this edition. Check feed sources."
    else:
        prompt = build_prompt(digest, config)

    # Write output
    with open(out_path, "w") as f:
        f.write(prompt)

    article_count = len(digest.get("articles", []))
    print(f"✅ Draft prompt written to {out_path}")
    print(f"   {article_count} source articles included")
    print(f"   {len(prompt)} characters total")
    print()
    print(f"Next steps:")
    print(f"  1. The Hermes cron agent will read this file and generate the final newsletter")
    print(f"  2. Or manually edit {out_path} and run: python3 publish.py {out_path}")


if __name__ == "__main__":
    main()
