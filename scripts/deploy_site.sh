#!/usr/bin/env bash
# Publish the Innovative Hype homepage and its data to a web root.
#
# Run after narrative_desk.py has written web/ (cron: 07:30 UTC, after the 07:00 desk run).
# Copies an explicit list of files, so dev-only pages (pipeline.html, social.html,
# tweets.html, samples/) never reach the public site. Never deletes anything at DEST.
# Before overwriting index.html, the current one is copied to BACKUP_DIR.
#
#   scripts/deploy_site.sh [DEST]          DEST defaults to /var/www/html (production)
#
# Fails loudly: exits non-zero if a source file is missing or the data is empty.

set -euo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
SRC="$REPO/web"
DEST="${1:-/var/www/html}"
BACKUP_DIR="${BACKUP_DIR:-/var/backups/ih-site}"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"

# Homepage served as index.html; everything else copied under its own name.
PAGES=(brief.html newsletter.html)
DATA=(articles.json brief-cards.json brief-feed.json)

for f in index.html "${PAGES[@]}" "${DATA[@]}"; do
  [ -s "$SRC/$f" ] || { echo "deploy: missing or empty $SRC/$f" >&2; exit 1; }
done
[ -d "$SRC/assets" ] || { echo "deploy: missing $SRC/assets" >&2; exit 1; }

python3 - "$SRC" <<'PY'
import json, sys
src = sys.argv[1]
arts = json.load(open(src + "/articles.json"))["articles"]
cards = json.load(open(src + "/brief-cards.json"))["cards"]
if not arts or not cards:
    sys.exit("deploy: articles.json or brief-cards.json has no entries")
PY

mkdir -p "$BACKUP_DIR"
if [ -f "$DEST/index.html" ]; then
  cp -p "$DEST/index.html" "$BACKUP_DIR/index-$STAMP.html"
  echo "backed up $DEST/index.html -> $BACKUP_DIR/index-$STAMP.html"
fi

cp -p "$SRC/index.html" "$DEST/index.html"
for f in "${PAGES[@]}" "${DATA[@]}"; do
  cp -p "$SRC/$f" "$DEST/$f"
done
rsync -a --exclude '.DS_Store' "$SRC/assets/" "$DEST/assets/"

echo "deployed to $DEST at $STAMP"
