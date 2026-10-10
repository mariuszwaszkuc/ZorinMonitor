"""Main application window and logic for Zorin Desktop Monitor."""
import sys
from pathlib import Path
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GLib
import cairo

from zorin_monitor.config import load_config, save_config, TILE_KEYS
from zorin_monitor.stats import SystemStatsCollector, format_bytes, format_rate, list_disk_partitions
from zorin_monitor.widgets import TileCard

AUTOSTART_DIR = Path.home() / ".config" / "autostart"
AUTOSTART_FILE = AUTOSTART_DIR / "zorin-monitor.desktop"

TILE_WIDTH = 280
TILE_SPACING = 14
POSITION_SAVE_DELAY_MS = 600

# key -> (tytuł, plik ikony, kolor, [(klucz wiersza, etykieta), ...], nazwa w menu)
TILE_SPECS = {
    "cpu": ("CPU KPI", "cpu.svg", "#38bdf8", [
        ("cores", "Rdzenie / wątki:"),
        ("maxcore", "Najbardziej obciążony rdzeń:"),
        ("load", "Średnie obciążenie:"),
        ("top", "Główny proces:"),
    ], "Procesor (CPU)"),
    "ram": ("RAM KPI", "ram.svg", "#c084fc", [
        ("usage", "Użyte / Całkowite:"),
        ("avail", "Dostępna pamięć:"),
        ("swap", "Pamięć Swap:"),
        ("top", "Główny proces:"),
    ], "Pamięć RAM"),
    "swap": ("SWAP KPI", "swap.svg", "#f59e0b", [
        ("usage", "Użyte / Całkowite:"),
        ("avail", "Wolny Swap:"),
        ("activity", "Zapisano (Out):"),
        ("status", "Status pamięci:"),
    ], "Pamięć wymiany (SWAP)"),
    "disk": ("DISK KPI", "disk.svg", "#34d399", [
        ("usage", "Użyte / Całkowite:"),
        ("free", "Wolne miejsce:"),
        ("io", "Odczyt / Zapis:"),
        ("device", "Partycja:"),
    ], "Dysk"),
}


class ZorinDesktopMonitor(Gtk.Window):
    def __init__(self, assets_dir: Path):
        super().__init__(type=Gtk.WindowType.TOPLEVEL)
        self.assets_dir = assets_dir
        self.base_dir = assets_dir.parent
        self.config = load_config()
        self.stats_collector = SystemStatsCollector(history_len=35, disk_path=self.config.get("disk_path", "/"))
        self.timer_id = None
        self.save_pos_id = None
        self.positioned = False
        self.css_provider = Gtk.CssProvider()
        Gtk.StyleContext.add_provider_for_screen(
            self.get_screen(),
            self.css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

        # Setup Window Properties for Desktop Widget
        self.set_title("Zorin Desktop Monitor")
        self.set_decorated(False)
        self.set_resizable(False)
        self.set_app_paintable(True)
        self.set_skip_taskbar_hint(True)
        self.set_skip_pager_hint(True)
        self.set_type_hint(Gdk.WindowTypeHint.NORMAL)
        self.stick() # Sticky across all virtual desktops/workspaces
        self.add_events(Gdk.EventMask.BUTTON_PRESS_MASK | Gdk.EventMask.BUTTON_RELEASE_MASK)

        if self.config.get("keep_below", False):
            self.set_keep_below(True)

        # RGBA Screen Visual for transparency
        screen = self.get_screen()
        visual = screen.get_rgba_visual()
        if visual and screen.is_composited():
            self.set_visual(visual)

        # Connect events
        self.connect("draw", self.on_draw_background)
        self.connect("destroy", self.on_destroy)
        self.connect("button-press-event", self.on_button_press)
        self.connect("button-release-event", self.on_button_release)
        self.connect("configure-event", self.on_configure)

        # Main Layout Container (renamed to main_box to avoid conflict with GtkContainer internal field)
        self.main_box = Gtk.Box(spacing=TILE_SPACING)
        self.main_box.get_style_context().add_class("monitor-container")
        self.add(self.main_box)

        # Tiles
        self.tiles = {}
        self.tile_eboxes = {}
        for key in TILE_KEYS:
            self._create_tile(key)

        # Apply Orientation from config
        self._apply_orientation(self.config.get("orientation", "horizontal"))

        # Apply Graph visibility & tile visibility from config
        self._apply_graphs_visibility(self.config.get("show_graphs", True))
        self._apply_tiles_visibility()

        # Apply CSS styling
        self.apply_styles()

        # Position Window
        self.connect("realize", self.on_realize)
        self.connect("map-event", lambda w, e: self.on_realize(w))

        # Start periodic update timer
        interval = self.config.get("refresh_interval", 1000)
        self.timer_id = GLib.timeout_add(interval, self.on_update_tick)

        # Perform initial tick immediately
        self.on_update_tick()

    def _create_tile(self, key: str):
        title, svg_name, color, rows, _ = TILE_SPECS[key]
        tile = TileCard(title=title, svg_path=str(self.assets_dir / svg_name), base_color=color)
        for idx, (row_key, label) in enumerate(rows):
            tile.add_detail_row(idx, row_key, label)

        ebox = Gtk.EventBox()
        ebox.set_visible_window(False)
        ebox.set_above_child(True)
        ebox.add(tile)
        ebox.connect("button-press-event", self.on_button_press)
        ebox.connect("button-release-event", self.on_button_release)
        self.main_box.pack_start(ebox, True, True, 0)

        # Widoczność kafelków i wykresów sterujemy ręcznie - show_all() z main.py
        # nie może ich ponownie odkrywać
        tile.show_all()
        ebox.show()
        ebox.set_no_show_all(True)

        self.tiles[key] = tile
        self.tile_eboxes[key] = ebox

    def _visible_tile_count(self) -> int:
        return sum(1 for key in TILE_KEYS if self.config["tiles"].get(key, True))

    def _apply_orientation(self, orient: str):
        if orient == "vertical":
            self.main_box.set_orientation(Gtk.Orientation.VERTICAL)
        else:
            self.main_box.set_orientation(Gtk.Orientation.HORIZONTAL)

    def _apply_graphs_visibility(self, visible: bool):
        for tile in self.tiles.values():
            tile.set_graph_visible(visible)

    def _apply_tiles_visibility(self):
        for key, ebox in self.tile_eboxes.items():
            ebox.set_visible(self.config["tiles"].get(key, True))

    def apply_styles(self):
        opacity = self.config.get("opacity", 0.85)
        # Background alpha
        bg_alpha = f"{opacity:.2f}"

        css = f"""
        window {{
            background-color: transparent;
        }}
        .monitor-container {{
            background-color: transparent;
            padding: 4px;
        }}
        .tile-card {{
            background-color: rgba(18, 24, 38, {bg_alpha});
            border-radius: 18px;
            border: 1px solid rgba(255, 255, 255, 0.10);
            padding: 14px 16px;
            /* Zewnętrzny cień na przezroczystym oknie (XWayland) kumuluje się
               przy częściowym odświeżaniu i tworzy szare tło - tylko cień wewnętrzny */
            box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.06);
        }}
        .tile-title {{
            font-size: 11.5px;
            font-weight: 800;
            letter-spacing: 1.2px;
            color: rgba(255, 255, 255, 0.88);
        }}
        .tile-badge {{
            font-size: 10px;
            font-weight: 700;
            background-color: rgba(255, 255, 255, 0.08);
            border-radius: 6px;
            padding: 2px 7px;
            color: rgba(255, 255, 255, 0.72);
        }}
        .metric-percent {{
            font-size: 26px;
            font-weight: 900;
            font-feature-settings: "tnum";
        }}
        .metric-sub {{
            font-size: 12px;
            font-weight: 700;
            color: rgba(255, 255, 255, 0.85);
        }}
        .kpi-pill {{
            font-size: 9px;
            font-weight: 800;
            letter-spacing: 0.8px;
            border-radius: 4px;
            padding: 2px 6px;
        }}
        .pill-ok {{
            background-color: rgba(16, 185, 129, 0.20);
            color: #34d399;
            border: 1px solid rgba(16, 185, 129, 0.35);
        }}
        .pill-warn {{
            background-color: rgba(245, 158, 11, 0.20);
            color: #fbbf24;
            border: 1px solid rgba(245, 158, 11, 0.35);
        }}
        .pill-crit {{
            background-color: rgba(244, 63, 94, 0.25);
            color: #fda4af;
            border: 1px solid rgba(244, 63, 94, 0.45);
        }}
        .tile-separator {{
            background-color: rgba(255, 255, 255, 0.08);
            margin-top: 4px;
            margin-bottom: 4px;
        }}
        .detail-name {{
            font-size: 10.5px;
            color: rgba(255, 255, 255, 0.50);
        }}
        .detail-value {{
            font-size: 10.5px;
            font-weight: 600;
            color: rgba(255, 255, 255, 0.90);
        }}
        """

        self.css_provider.load_from_data(css.encode("utf-8"))

    def on_draw_background(self, widget, cr):
        # Okno jest app_paintable - bez czyszczenia po zmianie rozmiaru zostaje
        # w nim stara zawartość (szare półprzezroczyste tło za kafelkami)
        cr.save()
        cr.set_source_rgba(0, 0, 0, 0)
        cr.set_operator(cairo.OPERATOR_SOURCE)
        cr.paint()
        cr.restore()
        return False

    def _default_position(self):
        """Top-right corner of the primary monitor."""
        display = Gdk.Display.get_default()
        monitor = None
        if display:
            monitor = display.get_primary_monitor() or (
                display.get_monitor(0) if display.get_n_monitors() > 0 else None)
        if monitor:
            geom = monitor.get_geometry()
        else:
            geom = Gdk.Rectangle()
            geom.x, geom.y, geom.width, geom.height = 0, 0, 1920, 1080

        num_tiles = max(1, self._visible_tile_count())
        if self.config.get("orientation") != "vertical":
            win_w = num_tiles * TILE_WIDTH + (num_tiles - 1) * TILE_SPACING + 16
        else:
            win_w = TILE_WIDTH + 10
        return max(10, geom.x + geom.width - win_w - 24), geom.y + 24

    def _move_to(self, x: int, y: int, save: bool = True):
        self.move(x, y)
        self.config["x"] = x
        self.config["y"] = y
        if save:
            save_config(self.config)

    def on_realize(self, widget):
        # Pozycję ustawiamy tylko przy pierwszym pokazaniu okna - kolejne map-event
        # (np. zmiana obszaru roboczego) nie mogą cofać widgetu na starą pozycję
        if self.positioned:
            return
        if widget.get_mapped():
            self.positioned = True

        x = self.config.get("x", -1)
        y = self.config.get("y", -1)
        if x == -1 or y == -1:
            self._move_to(*self._default_position())
        else:
            self.move(x, y)

    def on_update_tick(self) -> bool:
        try:
            include_procs = self.config.get("show_top_procs", True)
            cpu, ram, swap, disk = self.stats_collector.update(include_top_procs=include_procs)
            visible = self.config["tiles"]

            # Update CPU Tile
            if visible.get("cpu", True):
                tile = self.tiles["cpu"]
                tile.set_badge(f"{cpu.cores_logical} wątków")
                tile.set_percent(cpu.percent)
                tile.set_sub_metric(cpu.freq_str)
                tile.set_graph_data(self.stats_collector.cpu_history)

                tile.set_detail_value("cores", f"{cpu.cores_physical} / {cpu.cores_logical}")
                tile.set_detail_value("maxcore", f"{cpu.max_core_percent:.0f}%")
                tile.set_detail_value("load", f"{cpu.load_avg[0]:.2f}, {cpu.load_avg[1]:.2f}, {cpu.load_avg[2]:.2f}")
                if include_procs and cpu.top_proc[0] != "-":
                    tile.set_detail_value("top", f"{cpu.top_proc[0]} ({cpu.top_proc[1]:.1f}%)")
                else:
                    tile.set_detail_value("top", "-")

            # Update RAM Tile
            if visible.get("ram", True):
                tile = self.tiles["ram"]
                tile.set_badge(f"{ram.total_gb:.1f} GB")
                tile.set_percent(ram.percent)
                tile.set_sub_metric(f"{ram.used_gb:.1f} / {ram.total_gb:.1f} GB")
                tile.set_graph_data(self.stats_collector.ram_history)

                tile.set_detail_value("usage", f"{ram.used_gb:.1f} z {ram.total_gb:.1f} GB")
                tile.set_detail_value("avail", f"{ram.avail_gb:.1f} GB wolnej")
                tile.set_detail_value("swap", f"{ram.swap_used_gb:.1f} / {ram.swap_total_gb:.1f} GB ({ram.swap_percent:.0f}%)")
                if include_procs and ram.top_proc[0] != "-":
                    tile.set_detail_value("top", f"{ram.top_proc[0]} ({ram.top_proc[1]})")
                else:
                    tile.set_detail_value("top", "-")

            # Update SWAP Tile
            if visible.get("swap", True):
                tile = self.tiles["swap"]
                tile.set_badge(f"{swap.total_gb:.1f} GB")
                tile.set_percent(swap.percent)
                tile.set_sub_metric(f"{swap.used_gb:.1f} / {swap.total_gb:.1f} GB")
                tile.set_graph_data(self.stats_collector.swap_history)

                tile.set_detail_value("usage", f"{swap.used_gb:.1f} z {swap.total_gb:.1f} GB")
                tile.set_detail_value("avail", f"{swap.free_gb:.1f} GB wolnej")
                if swap.sout_mb >= 1024:
                    tile.set_detail_value("activity", f"{swap.sout_mb / 1024.0:.1f} GB zapis.")
                else:
                    tile.set_detail_value("activity", f"{swap.sout_mb:.0f} MB zapis.")

                if swap.total_gb == 0:
                    tile.set_detail_value("status", "Brak pamięci Swap")
                elif swap.percent >= 75:
                    tile.set_detail_value("status", "Wysokie zużycie")
                else:
                    tile.set_detail_value("status", "Aktywny / W normie")

            # Update DISK Tile
            if visible.get("disk", True):
                tile = self.tiles["disk"]
                tile.set_badge(disk.mountpoint)
                tile.set_percent(disk.percent)
                tile.set_sub_metric(f"{format_bytes(disk.used_bytes)} / {format_bytes(disk.total_bytes)}")
                tile.set_graph_data(self.stats_collector.disk_history)

                tile.set_detail_value("usage", f"{format_bytes(disk.used_bytes)} z {format_bytes(disk.total_bytes)}")
                tile.set_detail_value("free", f"{format_bytes(disk.free_bytes)} wolnego")
                tile.set_detail_value("io", f"{format_rate(disk.read_bps)} / {format_rate(disk.write_bps)}")
                device = Path(disk.device).name if disk.device != "-" else "-"
                tile.set_detail_value("device", f"{device} ({disk.fstype})" if disk.fstype else device)

        except Exception as e:
            print(f"[ZorinMonitor] Update error: {e}", file=sys.stderr)

        return True # Continue GLib timer

    def on_button_press(self, widget, event: Gdk.EventButton):
        if event.type != Gdk.EventType.BUTTON_PRESS:
            return False
        if event.button == 1: # Left Click: Drag window if unlocked
            if not self.config.get("locked", False):
                self.begin_move_drag(
                    event.button,
                    int(event.x_root),
                    int(event.y_root),
                    event.time
                )
                return True
        elif event.button == 3: # Right Click: Context Menu
            tile_key = next((k for k, eb in self.tile_eboxes.items() if eb is widget), None)
            self.show_context_menu(event, tile_key)
            return True
        return False

    def on_button_release(self, widget, event: Gdk.EventButton):
        if event.button == 1:
            self._schedule_position_save()
        return False

    def on_configure(self, widget, event):
        # Pozycja zmienia się też przy przeciąganiu przez menedżer okien, który
        # przejmuje zdarzenia myszy - dlatego zapis następuje tutaj (z opóźnieniem)
        if not self.positioned:
            return False
        pos = self.get_position()
        if pos[0] >= 0 and pos[1] >= 0 and (pos[0], pos[1]) != (self.config.get("x"), self.config.get("y")):
            self.config["x"] = pos[0]
            self.config["y"] = pos[1]
            self._schedule_position_save()
        return False

    def _schedule_position_save(self):
        if self.save_pos_id:
            GLib.source_remove(self.save_pos_id)
        self.save_pos_id = GLib.timeout_add(POSITION_SAVE_DELAY_MS, self._save_position_now)

    def _save_position_now(self) -> bool:
        self.save_pos_id = None
        save_config(self.config)
        return False

    def show_context_menu(self, event=None, tile_key=None):
        self.context_menu = Gtk.Menu()
        menu = self.context_menu

        # 0. Hide the clicked tile
        if tile_key and self._visible_tile_count() > 1:
            hide_item = Gtk.MenuItem(label=f"🙈 Ukryj kafelek: {TILE_SPECS[tile_key][4]}")
            hide_item.connect("activate", lambda _w, k=tile_key: self.set_tile_visible(k, False))
            menu.append(hide_item)
            menu.append(Gtk.SeparatorMenuItem())

        # 1. Visible tiles submenu
        tiles_menu = Gtk.Menu()
        tiles_item = Gtk.MenuItem(label="👁 Widoczne kafelki")
        tiles_item.set_submenu(tiles_menu)
        for key in TILE_KEYS:
            check = Gtk.CheckMenuItem(label=TILE_SPECS[key][4])
            check.set_active(self.config["tiles"].get(key, True))
            check.connect("toggled", self.on_toggle_tile, key)
            tiles_menu.append(check)
        tiles_menu.append(Gtk.SeparatorMenuItem())
        show_all_item = Gtk.MenuItem(label="Pokaż wszystkie kafelki")
        show_all_item.connect("activate", self.on_show_all_tiles)
        tiles_menu.append(show_all_item)
        menu.append(tiles_item)

        # 2. Disk selection submenu
        disk_menu = Gtk.Menu()
        disk_item = Gtk.MenuItem(label="💽 Monitorowany dysk")
        disk_item.set_submenu(disk_menu)
        curr_disk = self.stats_collector.disk_path
        group = None
        for mount, device, fstype in list_disk_partitions():
            dev_name = Path(device).name if device != "-" else ""
            label = f"{mount}  ({dev_name})" if dev_name else mount
            radio = Gtk.RadioMenuItem(group=group, label=label)
            group = group or radio
            radio.set_active(mount == curr_disk)
            radio.connect("toggled", lambda w, m=mount: self.on_change_disk(m) if w.get_active() else None)
            disk_menu.append(radio)
        menu.append(disk_item)

        menu.append(Gtk.SeparatorMenuItem())

        # 3. Lock position toggle
        lock_item = Gtk.CheckMenuItem(label="🔒 Zablokuj pozycję na pulpicie")
        lock_item.set_active(self.config.get("locked", False))
        lock_item.connect("toggled", self.on_toggle_locked)
        menu.append(lock_item)

        # 4. Keep Below toggle (desktop layer)
        below_item = Gtk.CheckMenuItem(label="📌 Zawsze na spodzie (pod oknami)")
        below_item.set_active(self.config.get("keep_below", False))
        below_item.connect("toggled", self.on_toggle_keep_below)
        menu.append(below_item)

        # 5. Show Graphs toggle
        graphs_item = Gtk.CheckMenuItem(label="📈 Pokaż wykresy obciążenia (Sparkline)")
        graphs_item.set_active(self.config.get("show_graphs", True))
        graphs_item.connect("toggled", self.on_toggle_graphs)
        menu.append(graphs_item)

        menu.append(Gtk.SeparatorMenuItem())

        # 6. Orientation submenu
        orient_menu = Gtk.Menu()
        orient_item = Gtk.MenuItem(label="↔ Układ kafelków")
        orient_item.set_submenu(orient_menu)

        curr_orient = self.config.get("orientation", "horizontal")
        radio_h = Gtk.RadioMenuItem(label="Poziomo (obok siebie)")
        radio_h.set_active(curr_orient == "horizontal")
        radio_h.connect("activate", lambda w: self.on_change_orientation("horizontal") if w.get_active() else None)
        orient_menu.append(radio_h)

        radio_v = Gtk.RadioMenuItem(group=radio_h, label="Pionowo (jeden pod drugim)")
        radio_v.set_active(curr_orient == "vertical")
        radio_v.connect("activate", lambda w: self.on_change_orientation("vertical") if w.get_active() else None)
        orient_menu.append(radio_v)
        menu.append(orient_item)

        # 7. Opacity submenu
        opacity_menu = Gtk.Menu()
        opacity_item = Gtk.MenuItem(label="🎨 Przezroczystość tła")
        opacity_item.set_submenu(opacity_menu)

        for label, val in [("95% (Ciemne)", 0.95), ("85% (Zalecane)", 0.85), ("70% (Przejrzyste)", 0.70), ("50% (Szkliste)", 0.50)]:
            sub = Gtk.MenuItem(label=label)
            sub.connect("activate", lambda w, v=val: self.on_change_opacity(v))
            opacity_menu.append(sub)
        menu.append(opacity_item)

        # 8. Refresh interval submenu
        interval_menu = Gtk.Menu()
        interval_item = Gtk.MenuItem(label="⏱ Częstotliwość odświeżania")
        interval_item.set_submenu(interval_menu)

        for label, val in [("0.5 sekundy (Płynne)", 500), ("1.0 sekunda (Standard)", 1000), ("2.0 sekundy (Oszczędne)", 2000)]:
            sub = Gtk.MenuItem(label=label)
            sub.connect("activate", lambda w, v=val: self.on_change_interval(v))
            interval_menu.append(sub)
        menu.append(interval_item)

        menu.append(Gtk.SeparatorMenuItem())

        # 9. Autostart toggle
        autostart_item = Gtk.CheckMenuItem(label="🚀 Uruchamiaj przy starcie systemu")
        autostart_item.set_active(AUTOSTART_FILE.exists())
        autostart_item.connect("toggled", self.on_toggle_autostart)
        menu.append(autostart_item)

        # 10. Reset position
        reset_item = Gtk.MenuItem(label="🔄 Przywróć domyślną pozycję")
        reset_item.connect("activate", self.on_reset_position)
        menu.append(reset_item)

        menu.append(Gtk.SeparatorMenuItem())

        # 11. Quit (destroy -> on_destroy zapisuje konfigurację)
        quit_item = Gtk.MenuItem(label="❌ Zamknij monitor")
        quit_item.connect("activate", lambda _: self.destroy())
        menu.append(quit_item)

        menu.show_all()
        if event is not None:
            try:
                menu.popup_at_pointer(event)
            except Exception:
                menu.popup(None, None, None, None, event.button, event.time)
        else:
            menu.popup_at_widget(self, Gdk.Gravity.SOUTH_WEST, Gdk.Gravity.NORTH_WEST, None)

    def set_tile_visible(self, key: str, visible: bool) -> bool:
        """Show or hide a tile. Refuses to hide the last visible tile."""
        if not visible and self.config["tiles"].get(key, True) and self._visible_tile_count() <= 1:
            return False
        self.config["tiles"][key] = visible
        self.tile_eboxes[key].set_visible(visible)
        if visible:
            self.on_update_tick()
        self.resize(1, 1) # Auto-shrink window
        save_config(self.config)
        return True

    def on_toggle_tile(self, widget, key: str):
        if not self.set_tile_visible(key, widget.get_active()):
            widget.set_active(True)

    def on_show_all_tiles(self, widget):
        for key in TILE_KEYS:
            self.config["tiles"][key] = True
        self._apply_tiles_visibility()
        self.on_update_tick()
        self.resize(1, 1)
        save_config(self.config)

    def on_change_disk(self, path: str):
        self.config["disk_path"] = path
        self.stats_collector.set_disk_path(path)
        self.on_update_tick()
        save_config(self.config)

    def on_toggle_locked(self, widget):
        self.config["locked"] = widget.get_active()
        save_config(self.config)

    def on_toggle_keep_below(self, widget):
        val = widget.get_active()
        if val and not self._confirm_keep_below():
            widget.set_active(False)
            return
        self.config["keep_below"] = val
        self.set_keep_below(val)
        save_config(self.config)

    def _confirm_keep_below(self) -> bool:
        # Okno ikon pulpitu (np. zorin-desktop-icons) leży nad oknami "na spodzie"
        # i przejmuje wszystkie kliknięcia - widget stanie się nieklikalny
        dialog = Gtk.MessageDialog(
            transient_for=self,
            modal=True,
            message_type=Gtk.MessageType.WARNING,
            buttons=Gtk.ButtonsType.OK_CANCEL,
            text="Włączyć tryb „Zawsze na spodzie”?",
        )
        dialog.format_secondary_text(
            "Przy włączonych ikonach pulpitu kafelki przestaną reagować na mysz "
            "(przeciąganie i menu pod prawym przyciskiem).\n\n"
            "Aby później wyłączyć ten tryb, uruchom w terminalu:\n"
            f"{self.base_dir / 'run.sh'} --restart --reset-below"
        )
        response = dialog.run()
        dialog.destroy()
        return response == Gtk.ResponseType.OK

    def on_toggle_graphs(self, widget):
        val = widget.get_active()
        self.config["show_graphs"] = val
        self._apply_graphs_visibility(val)
        self.resize(1, 1) # Auto-shrink window
        save_config(self.config)

    def on_change_orientation(self, orient: str):
        self.config["orientation"] = orient
        self._apply_orientation(orient)
        self.resize(1, 1)
        save_config(self.config)

    def on_change_opacity(self, opacity: float):
        self.config["opacity"] = opacity
        self.apply_styles()
        save_config(self.config)

    def on_change_interval(self, interval_ms: int):
        self.config["refresh_interval"] = interval_ms
        if self.timer_id:
            GLib.source_remove(self.timer_id)
        self.timer_id = GLib.timeout_add(interval_ms, self.on_update_tick)
        save_config(self.config)

    def on_toggle_autostart(self, widget):
        active = widget.get_active()
        try:
            if active:
                AUTOSTART_DIR.mkdir(parents=True, exist_ok=True)
                desktop_content = f"""[Desktop Entry]
Type=Application
Name=Zorin Desktop Monitor
Comment=Monitor zasobów CPU, RAM i dysku w postaci kafelków na pulpicie
Exec="{self.base_dir / 'run.sh'}" --daemon
Icon={self.assets_dir / 'icon.svg'}
Terminal=false
Categories=System;Monitor;
X-GNOME-Autostart-enabled=true
"""
                with open(AUTOSTART_FILE, "w", encoding="utf-8") as f:
                    f.write(desktop_content)
                AUTOSTART_FILE.chmod(0o755)
            else:
                if AUTOSTART_FILE.exists():
                    AUTOSTART_FILE.unlink()
        except Exception as e:
            print(f"[ZorinMonitor] Autostart error: {e}", file=sys.stderr)

    def on_reset_position(self, widget):
        self._move_to(*self._default_position())

    def on_destroy(self, widget):
        # Pozycja jest na bieżąco aktualizowana w on_configure
        save_config(self.config)
        for source_id in (self.timer_id, self.save_pos_id):
            if source_id:
                GLib.source_remove(source_id)
        self.timer_id = self.save_pos_id = None
        Gtk.main_quit()
