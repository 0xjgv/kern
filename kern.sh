#!/usr/bin/env bash
set -euo pipefail

# Resolve symlinks to find actual script location (portable for macOS/Linux)
SOURCE="${BASH_SOURCE[0]}"
while [[ -L "$SOURCE" ]]; do
  DIR="$(cd "$(dirname "$SOURCE")" && pwd)"
  SOURCE="$(readlink "$SOURCE")"
  [[ "$SOURCE" != /* ]] && SOURCE="$DIR/$SOURCE"
done
SCRIPT_DIR="$(cd "$(dirname "$SOURCE")" && pwd)"

export PYTHONPATH="$SCRIPT_DIR/src${PYTHONPATH:+:$PYTHONPATH}"
PYTHON_BIN="$SCRIPT_DIR/.venv/bin/python"
if [[ -x "$PYTHON_BIN" ]]; then
  exec "$PYTHON_BIN" -m kern.cli "$@"
fi
exec python3 -m kern.cli "$@"
