#!/bin/bash
# One-command install / update of the Hermes instance (hermes/SETUP.md, part 1).
#   hermes/setup/install.sh            install or update everything
#   hermes/setup/install.sh --dry-run  show what it would run
set -euo pipefail
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO"
command -v hermes >/dev/null || { echo "hermes is not on PATH"; exit 1; }

if [ ! -x .venv/bin/python ]; then
  if command -v uv >/dev/null; then uv venv --python 3.12 .venv; else python3 -m venv .venv; fi
fi
if command -v uv >/dev/null; then
  uv pip install --python .venv/bin/python -q -r requirements.txt pytest
else
  .venv/bin/python -m pip install -q -r requirements.txt pytest
fi
.venv/bin/python -m pytest -q
.venv/bin/python hermes/setup/install.py "$@"
