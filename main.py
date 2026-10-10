#!/usr/bin/env python3
"""
Zorin Desktop Monitor
Monitor zasobów CPU i RAM w postaci kafelków na pulpicie dla Zorin OS / GNOME.
"""
import os
import sys
import signal
from pathlib import Path

# Ensure package import works
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

# Ensure GDK backend compatibility for Wayland / X11
if "GDK_BACKEND" not in os.environ:
    os.environ["GDK_BACKEND"] = "x11"

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib
from zorin_monitor.app import ZorinDesktopMonitor


def main():
    assets_dir = BASE_DIR / "assets"

    # Create App Window
    app = ZorinDesktopMonitor(assets_dir=assets_dir)
    app.show_all()

    # Ctrl+C / SIGTERM (stop.sh) - zamknij okno, aby zapisać konfigurację
    def on_signal():
        app.destroy()
        return GLib.SOURCE_REMOVE

    for sig in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
        GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, sig, on_signal)

    # Start GTK main loop
    Gtk.main()


if __name__ == "__main__":
    main()
