#!/usr/bin/env bash
# Backward-compatible Bash 3.2 wrapper for the PRO Python CLI.
# Usage: ./scripts/scrape.sh "<keyword>" <lat> <lon> [depth] [PRO options...]
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
if command -v python3 >/dev/null 2>&1; then
  PYTHON_BIN=python3
elif command -v python >/dev/null 2>&1; then
  PYTHON_BIN=python
else
  echo "Python 3.9+ is required. See SETUP.md." >&2
  exit 1
fi

if [ "$#" -lt 3 ]; then
  echo "Usage: $0 \"<keyword>\" <lat> <lon> [depth] [PRO options...]" >&2
  exit 1
fi

KEYWORD="$1"; LAT="$2"; LON="$3"
shift 3
DEPTH=5
if [ "$#" -gt 0 ] && [[ "$1" =~ ^[0-9]+$ ]]; then
  DEPTH="$1"
  shift
fi
exec "$PYTHON_BIN" "$SCRIPT_DIR/scrape.py" "$KEYWORD" "$LAT" "$LON" --depth "$DEPTH" "$@"
