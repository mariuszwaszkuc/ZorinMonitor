"""Configuration manager for Zorin Desktop Monitor."""
import os
import json
from pathlib import Path

# Kolejność kafelków na pulpicie
TILE_KEYS = ("cpu", "ram", "swap", "disk")

DEFAULT_CONFIG = {
    "x": -1,              # -1 means auto-position (top-right of primary monitor)
    "y": -1,
    "locked": False,      # Lock position to prevent accidental dragging
    "keep_below": False,  # Float on desktop without getting hidden by desktop icons extension
    "orientation": "horizontal", # "horizontal" or "vertical"
    "show_graphs": True,  # Show real-time sparkline graphs
    "tiles": {key: True for key in TILE_KEYS}, # Visibility of each tile
    "disk_path": "/",     # Mountpoint shown on the disk tile
    "show_top_procs": True, # Show top consuming process
    "opacity": 0.85,      # Background opacity (0.5 to 1.0)
    "refresh_interval": 1000, # In milliseconds (500, 1000, 2000)
}

CONFIG_DIR = Path.home() / ".config" / "zorin-monitor"
CONFIG_FILE = CONFIG_DIR / "config.json"


def load_config() -> dict:
    config = json.loads(json.dumps(DEFAULT_CONFIG))  # deep copy
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
            if isinstance(saved, dict):
                # Migracja ze starszej wersji (tylko przełącznik kafelka SWAP)
                if "show_swap_tile" in saved and "tiles" not in saved:
                    saved["tiles"] = {"swap": bool(saved["show_swap_tile"])}
                for old_key in ("show_swap_tile", "show_swap", "theme_accent"):
                    saved.pop(old_key, None)
                tiles = saved.pop("tiles", {})
                config.update(saved)
                if isinstance(tiles, dict):
                    for key in TILE_KEYS:
                        if key in tiles:
                            config["tiles"][key] = bool(tiles[key])
        except Exception as e:
            print(f"[ZorinMonitor] Błąd odczytu konfiguracji: {e}")
    if not any(config["tiles"].values()):
        config["tiles"]["cpu"] = True
    return config


def save_config(config: dict) -> bool:
    try:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        tmp_file = CONFIG_FILE.with_suffix(".json.tmp")
        with open(tmp_file, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4)
        os.replace(tmp_file, CONFIG_FILE)
        return True
    except Exception as e:
        print(f"[ZorinMonitor] Błąd zapisu konfiguracji: {e}")
        return False
