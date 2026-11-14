#!/usr/bin/env bash
# Retweet-angles trial: the Innovative Hype desk with 612 angles (378 current
# + 234 new from @geoppls retweets after the quality filter). See
# docs/RETWEET-ANGLES-2026-11-14.md on branch ih/angles-retweets.
#
# Production is only READ: each tick copies the live pipeline's
# web/articles.json, so Top News and the story pool are the same as live and
# only the angle list differs. Everything is written under this folder.
#
#   trial_tick.sh            run brief.py + narrative_desk.py if prod has new articles
#   trial_tick.sh snapshot   save today's trial and live brief for the day-by-day review
#
# Runs until its crontab lines are removed. Fails loudly (non-zero exit).
set -euo pipefail

T=/root/ih-angles-trial
PROD=/root/innovative-hype-newsletter/web/articles.json
PY=/usr/local/lib/hermes-agent/venv/bin/python3
export IH_EMBED_CACHE="$T/.embed-cache"
cd "$T"

if [ "${1:-}" = "snapshot" ]; then
  D="$T/daily/$(date +%F)"
  mkdir -p "$D/trial" "$D/live"
  for f in brief-cards.json brief-feed.json articles.json; do
    cp -p "$T/web/$f" "$D/trial/$f"
    cp -p "/var/www/html/$f" "$D/live/$f"
  done
  echo "$(date -Is) snapshot -> $D"
  exit 0
fi

STATE="$T/.last_prod_mtime"
m=$(stat -c %Y "$PROD")
if [ -f "$STATE" ] && [ "$(cat "$STATE")" = "$m" ]; then
  echo "$(date -Is) prod articles.json unchanged since $(date -d @"$m" -Is), skip"
  exit 0
fi

cp -p "$PROD" "$T/web/articles.json.tmp"
"$PY" -c "import json,sys; d=json.load(open(sys.argv[1])); assert d['articles'], 'no articles'" "$T/web/articles.json.tmp"
mv "$T/web/articles.json.tmp" "$T/web/articles.json"

echo "$(date -Is) tick: prod articles.json of $(date -d @"$m" -Is)"
"$PY" scripts/brief.py > "$T/logs/brief-last.log" 2>&1 || { echo "brief.py failed"; tail -20 "$T/logs/brief-last.log"; exit 1; }
"$PY" scripts/narrative_desk.py
echo "$m" > "$STATE"
echo "$(date -Is) tick done"
