#!/usr/bin/env bash
# ==========================================================================
# Innovative Hype — Newsletter Pipeline
# ==========================================================================
# End-to-end automation: research → draft → publish
#
# Usage:
#   ./pipeline.sh                     # Full run (research + draft prompt)
#   ./pipeline.sh --dry-run           # Research only, no publish
#   ./pipeline.sh --publish           # Full run + publish to Substack
#   ./pipeline.sh --config config.local.yaml
#
# Cron mode (for Hermes cron job):
#   The cron agent runs research.py first, then the agent itself reads
#   newsletter.md and generates the final draft using its LLM, then
#   calls publish.py to send it. The --cron-research flag outputs
#   JSON digest only for chaining.
# ==========================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

CONFIG="${HERMES_CONFIG:-config.yaml}"
MODE="full"
TIMESTAMP="$(date -u '+%Y-%m-%d %H:%M UTC')"

# ── Parse args ─────────────────────────────────────────────────────────────

for arg in "$@"; do
    case "$arg" in
        --dry-run)       MODE="dry-run" ;;
        --publish)       MODE="publish" ;;
        --cron-research) MODE="cron-research" ;;
        --config)        CONFIG="${2:-config.yaml}"; shift ;;
        --help|-h)
            echo "Innovative Hype Newsletter Pipeline"
            echo ""
            echo "Usage: ./pipeline.sh [flags]"
            echo ""
            echo "Flags:"
            echo "  --dry-run         Research only, outputs digest + draft prompt"
            echo "  --publish         Full pipeline including Substack publish"
            echo "  --cron-research   Research-only mode for Hermes cron (outputs JSON)"
            echo "  --config PATH     Use custom config file"
            exit 0
            ;;
    esac
    shift 2>/dev/null || true
done

# ── Logging ────────────────────────────────────────────────────────────────

log() { echo "[$(date '+%H:%M:%S')] $*"; }
banner() { echo ""; echo "══════════════════════════════════════════════════"; echo "  $*"; echo "══════════════════════════════════════════════════"; }

# ── Stage 1: Research ─────────────────────────────────────────────────────

banner "STAGE 1: AI News Research — $TIMESTAMP"
log "Config: $CONFIG"
log "Researching AI news from RSS feeds..."

python3 research.py --config "$CONFIG" --output digest.json 2>&1 | while IFS= read -r line; do
    log "$line"
done

if [ ! -s digest.json ]; then
    log "ERROR: digest.json is empty — no news stories found."
    exit 1
fi

ARTICLE_COUNT=$(python3 -c "import json; print(len(json.load(open('digest.json'))['articles']))" 2>/dev/null || echo "0")
log "Digest ready: $ARTICLE_COUNT articles"

# ── Cron-Research Mode: stop here ─────────────────────────────────────────

if [ "$MODE" = "cron-research" ]; then
    log "Cron research mode — stopping after Stage 1."
    exit 0
fi

# ── Stage 2: Draft ────────────────────────────────────────────────────────

banner "STAGE 2: Newsletter Draft"
log "Generating draft prompt from digest..."

python3 draft.py --config "$CONFIG" --digest digest.json --output newsletter.md

if [ ! -s newsletter.md ]; then
    log "ERROR: newsletter.md is empty — draft generation failed."
    exit 1
fi

DRAFT_CHARS=$(wc -c < newsletter.md | tr -d ' ')
log "Draft prompt written: $DRAFT_CHARS chars"
log ""
log "⚠️  NOTE: newsletter.md is a PROMPT TEMPLATE, not the final newsletter."
log "    The Hermes cron agent will read it and generate the final text."
log "    To manually publish: edit newsletter.md, then run:"
log "      python3 publish.py newsletter.md"

# ── Stage 3: Publish ──────────────────────────────────────────────────────

if [ "$MODE" = "publish" ]; then
    banner "STAGE 3: Substack Publish"
    log "Sending newsletter to Substack..."

    python3 publish.py newsletter.md --config "$CONFIG"

    log "Pipeline complete! Check innovativehype.substack.com."
elif [ "$MODE" = "dry-run" ]; then
    log ""
    log "✅ Dry run complete. Digest and draft prompt are ready."
    log "   digest.json    — raw news stories"
    log "   newsletter.md  — draft prompt (edit + publish manually)"
fi

# ── Summary ───────────────────────────────────────────────────────────────

echo ""
echo "──────────────────────────────────────────────────"
echo "  Pipeline Summary"
echo "──────────────────────────────────────────────────"
echo "  Mode:      $MODE"
echo "  Articles:  $ARTICLE_COUNT"
echo "  Digest:    $(du -h digest.json 2>/dev/null | cut -f1 || echo '0B')"
echo "  Draft:     $(du -h newsletter.md 2>/dev/null | cut -f1 || echo 'N/A')"
echo "──────────────────────────────────────────────────"
