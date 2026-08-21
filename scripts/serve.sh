#!/bin/bash
# serve.sh — quick static server for the web folder
# Usage: bash scripts/serve.sh [port]
PORT="${1:-8099}"
cd "$(dirname "$0")/../web"
echo "Serving on http://localhost:$PORT"
python3 -m http.server "$PORT" --bind 0.0.0.0
