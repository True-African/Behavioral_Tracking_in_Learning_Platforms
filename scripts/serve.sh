#!/usr/bin/env bash
set -euo pipefail

# Simple static server for the dashboard (serve repo root)
SCRIPT_DIR="$(cd -- "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd -P)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd -P)"
cd "$ROOT_DIR"

PORT="${PORT:-8000}"

if [ ! -f "index.html" ]; then
  echo "index.html not found in $ROOT_DIR" >&2
  exit 1
fi

echo "Serving $ROOT_DIR at http://localhost:${PORT}/index.html"

# Prefer the real Windows launcher first to avoid Microsoft Store aliases.
if [ -x "/c/Windows/py.exe" ]; then
  "/c/Windows/py.exe" -3 -m http.server "$PORT"
elif [ -x "/mnt/c/Windows/py.exe" ]; then
  "/mnt/c/Windows/py.exe" -3 -m http.server "$PORT"
elif command -v py >/dev/null 2>&1; then
  py -3 -m http.server "$PORT"
elif command -v python3 >/dev/null 2>&1 && ! command -v python3 | rg -i "WindowsApps" >/dev/null 2>&1; then
  python3 -m http.server "$PORT"
elif command -v python >/dev/null 2>&1 && ! command -v python | rg -i "WindowsApps" >/dev/null 2>&1; then
  python -m http.server "$PORT"
else
  echo "Python not found. Install Python 3, or ensure 'py'/'python' is on PATH." >&2
  exit 1
fi

