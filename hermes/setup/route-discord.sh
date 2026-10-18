#!/bin/bash
# Route your #faceless Discord channel to fm-lead (hermes/SETUP.md, part 3).
#   hermes/setup/route-discord.sh <channel id> [--no-restart]
set -euo pipefail
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
exec "$REPO/.venv/bin/python" "$REPO/hermes/setup/route_discord.py" "$@"
