#!/usr/bin/env bash
#
# Odinstalowanie skrótów i autostartu
#

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APPS_FILE="$HOME/.local/share/applications/zorin-monitor.desktop"
AUTOSTART_FILE="$HOME/.config/autostart/zorin-monitor.desktop"

"${SCRIPT_DIR}/stop.sh"

rm -f "$APPS_FILE"
rm -f "$AUTOSTART_FILE"
rm -f "$HOME/Desktop/zorin-monitor.desktop" 2>/dev/null
rm -f "$HOME/Pulpit/zorin-monitor.desktop" 2>/dev/null

echo "[ZorinMonitor] Odinstalowano skróty oraz autostart."
