#!/bin/bash
# serve.sh — serve web/ + the manual card-verdict API (scripts/serve.py)
# Usage: bash scripts/serve.sh [port]
PORT="${1:-8099}"
cd "$(dirname "$0")/.."
echo "Serving on http://localhost:$PORT"
exec python3 scripts/serve.py "$PORT"
