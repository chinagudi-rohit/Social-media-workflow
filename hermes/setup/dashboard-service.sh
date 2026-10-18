#!/bin/bash
# Keep the Creator Earnings dashboard running at http://127.0.0.1:8765 (a macOS LaunchAgent).
#   hermes/setup/dashboard-service.sh install     start now and at every login
#   hermes/setup/dashboard-service.sh uninstall   stop and remove it
set -euo pipefail
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
LABEL="ai.faceless.dashboard"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"

case "${1:-}" in
  install)
    mkdir -p "$HOME/Library/LaunchAgents" "$REPO/data/logs"
    cat > "$PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>$LABEL</string>
  <key>ProgramArguments</key><array>
    <string>$REPO/fm</string><string>dashboard</string><string>serve</string>
  </array>
  <key>EnvironmentVariables</key><dict>
    <key>PATH</key><string>$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin</string>
  </dict>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
  <key>StandardOutPath</key><string>$REPO/data/logs/dashboard.log</string>
  <key>StandardErrorPath</key><string>$REPO/data/logs/dashboard.log</string>
</dict></plist>
EOF
    launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
    launchctl bootstrap "gui/$(id -u)" "$PLIST"
    echo "Dashboard: http://127.0.0.1:8765 (starts at login)"
    ;;
  uninstall)
    launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
    rm -f "$PLIST"
    echo "Dashboard service removed"
    ;;
  *)
    echo "usage: $0 install|uninstall"; exit 2
    ;;
esac
