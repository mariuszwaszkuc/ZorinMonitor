"""Custom GTK & Cairo widgets for Zorin Desktop Monitor."""
import math
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GdkPixbuf, Gio
import cairo
from typing import Tuple, Sequence, Optional


def hex_to_rgba(hex_color: str, alpha: float = 1.0) -> Tuple[float, float, float, float]:
    """Convert hex string (e.g. '#38bdf8') to Cairo RGBA tuple (0.0 to 1.0)."""
    hex_color = hex_color.lstrip('#')
    if len(hex_color) == 6:
        r = int(hex_color[0:2], 16) / 255.0
        g = int(hex_color[2:4], 16) / 255.0
        b = int(hex_color[4:6], 16) / 255.0
        return (r, g, b, alpha)
    return (1.0, 1.0, 1.0, alpha)


# Wspólne progi dla koloru wskaźników i etykiety statusu
WARN_THRESHOLD = 70.0
CRIT_THRESHOLD = 85.0


def get_color_for_percent(percent: float, base_hex: str) -> str:
    """Returns color based on load percentage."""
    if percent >= CRIT_THRESHOLD:
        return "#f43f5e" # Rose / Red (Critical)
    elif percent >= WARN_THRESHOLD:
        return "#f59e0b" # Amber / Yellow (High)
    return base_hex      # Normal theme accent


class SparklineGraph(Gtk.DrawingArea):
    """Real-time smooth historical sparkline chart drawn via Cairo."""
    def __init__(self, base_color: str = "#38bdf8", height: int = 54):
        super().__init__()
        self.set_size_request(-1, height)
        self.base_color = base_color
        self.history: Sequence[float] = [0.0] * 35
        self.connect("draw", self.on_draw)

    def set_data(self, history: Sequence[float]):
        self.history = history
        self.queue_draw()

    def on_draw(self, widget, cr: cairo.Context):
        width = widget.get_allocated_width()
        height = widget.get_allocated_height()

        if width <= 0 or height <= 0:
            return False

        # Background container for graph with rounded corners
        radius = 8.0
        self._rounded_rect(cr, 0, 0, width, height, radius)
        cr.set_source_rgba(0.06, 0.08, 0.12, 0.45)
        cr.fill()

        # Faint grid lines at 50%
        cr.set_line_width(1.0)
        cr.set_source_rgba(1.0, 1.0, 1.0, 0.07)
        cr.move_to(0, height * 0.5)
        cr.line_to(width, height * 0.5)
        cr.stroke()

        if not self.history or len(self.history) < 2:
            return False

        latest_pct = self.history[-1] if self.history else 0.0
        line_color_hex = get_color_for_percent(latest_pct, self.base_color)
        r, g, b, _ = hex_to_rgba(line_color_hex, 1.0)

        # Padding
        pad_x = 4.0
        pad_y = 6.0
        usable_w = width - (2 * pad_x)
        usable_h = height - (2 * pad_y)

        n = len(self.history)
        step_x = usable_w / (n - 1)

        # Calculate coordinates
        points = []
        for i, val in enumerate(self.history):
            clamped = max(0.0, min(100.0, float(val)))
            x = pad_x + (i * step_x)
            y = (height - pad_y) - ((clamped / 100.0) * usable_h)
            points.append((x, y))

        # 1. Fill gradient area under the line
        cr.save()
        self._rounded_rect(cr, 0, 0, width, height, radius)
        cr.clip()

        cr.move_to(points[0][0], height)
        cr.line_to(points[0][0], points[0][1])
        for x, y in points[1:]:
            cr.line_to(x, y)
        cr.line_to(points[-1][0], height)
        cr.close_path()

        grad = cairo.LinearGradient(0, 0, 0, height)
        grad.add_color_stop_rgba(0.0, r, g, b, 0.35)
        grad.add_color_stop_rgba(0.7, r, g, b, 0.10)
        grad.add_color_stop_rgba(1.0, r, g, b, 0.01)
        cr.set_source(grad)
        cr.fill()
        cr.restore()

        # 2. Stroke the trendline
        cr.save()
        self._rounded_rect(cr, 0, 0, width, height, radius)
        cr.clip()

        cr.set_line_width(2.2)
        cr.set_line_join(cairo.LINE_JOIN_ROUND)
        cr.set_line_cap(cairo.LINE_CAP_ROUND)
        cr.set_source_rgba(r, g, b, 0.95)

        cr.move_to(points[0][0], points[0][1])
        for x, y in points[1:]:
            cr.line_to(x, y)
        cr.stroke()

        # 3. Glowing point at the last value
        last_x, last_y = points[-1]
        # Glow ring
        cr.set_source_rgba(r, g, b, 0.30)
        cr.arc(last_x, last_y, 4.5, 0, 2 * math.pi)
        cr.fill()
        # Solid center dot
        cr.set_source_rgba(1.0, 1.0, 1.0, 0.95)
        cr.arc(last_x, last_y, 2.2, 0, 2 * math.pi)
        cr.fill()

        cr.restore()
        return False

    def _rounded_rect(self, cr: cairo.Context, x: float, y: float, w: float, h: float, r: float):
        r = min(r, w / 2, h / 2)
        cr.new_sub_path()
        cr.arc(x + w - r, y + r, r, -math.pi / 2, 0)
        cr.arc(x + w - r, y + h - r, r, 0, math.pi / 2)
        cr.arc(x + r, y + h - r, r, math.pi / 2, math.pi)
        cr.arc(x + r, y + r, r, math.pi, 3 * math.pi / 2)
        cr.close_path()


class CapsuleProgressBar(Gtk.DrawingArea):
    """Custom sleek horizontal capsule progress bar."""
    def __init__(self, base_color: str = "#38bdf8", height: int = 8):
        super().__init__()
        self.set_size_request(-1, height)
        self.base_color = base_color
        self.percent: float = 0.0
        self.connect("draw", self.on_draw)

    def set_percent(self, pct: float):
        self.percent = max(0.0, min(100.0, pct))
        self.queue_draw()

    def on_draw(self, widget, cr: cairo.Context):
        width = widget.get_allocated_width()
        height = widget.get_allocated_height()
        if width <= 0 or height <= 0:
            return False

        radius = height / 2.0

        # Background track
        self._rounded_rect(cr, 0, 0, width, height, radius)
        cr.set_source_rgba(1.0, 1.0, 1.0, 0.10)
        cr.fill()

        # Filled bar
        fill_width = (self.percent / 100.0) * width
        if fill_width > 2.0:
            color_hex = get_color_for_percent(self.percent, self.base_color)
            r, g, b, _ = hex_to_rgba(color_hex, 1.0)

            self._rounded_rect(cr, 0, 0, fill_width, height, radius)
            grad = cairo.LinearGradient(0, 0, fill_width, 0)
            grad.add_color_stop_rgba(0.0, r * 0.9, g * 0.9, b * 0.9, 0.9)
            grad.add_color_stop_rgba(1.0, r, g, b, 1.0)
            cr.set_source(grad)
            cr.fill()

        return False

    def _rounded_rect(self, cr: cairo.Context, x: float, y: float, w: float, h: float, r: float):
        r = min(r, w / 2, h / 2)
        cr.new_sub_path()
        cr.arc(x + w - r, y + r, r, -math.pi / 2, 0)
        cr.arc(x + w - r, y + h - r, r, 0, math.pi / 2)
        cr.arc(x + r, y + h - r, r, math.pi / 2, math.pi)
        cr.arc(x + r, y + r, r, math.pi, 3 * math.pi / 2)
        cr.close_path()


class TileCard(Gtk.Box):
    """
    Desktop widget tile representing CPU, RAM, SWAP or disk.
    Displays percentage, quantities, progress bar, sparkline, and detail rows.
    """
    def __init__(self, title: str, svg_path: str, base_color: str = "#38bdf8"):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.base_color = base_color
        self.get_style_context().add_class("tile-card")
        self.set_size_request(270, -1)

        # 1. Header (Icon + Title + Badge)
        header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        header_box.set_valign(Gtk.Align.CENTER)

        # SVG Icon
        try:
            pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(svg_path, 22, 22, True)
            icon = Gtk.Image.new_from_pixbuf(pixbuf)
        except Exception:
            icon = Gtk.Image.new_from_icon_name("utilities-system-monitor", Gtk.IconSize.MENU)
        header_box.pack_start(icon, False, False, 0)

        # Title Label
        title_label = Gtk.Label(label=title)
        title_label.get_style_context().add_class("tile-title")
        title_label.set_xalign(0.0)
        header_box.pack_start(title_label, True, True, 0)

        # KPI Status Pill
        self.status_pill = Gtk.Label(label="NORMA")
        self.status_pill.get_style_context().add_class("kpi-pill")
        self.status_pill.get_style_context().add_class("pill-ok")
        header_box.pack_end(self.status_pill, False, False, 0)

        # Badge Label (e.g. "18 wątków" / "15.0 GB")
        self.badge_label = Gtk.Label(label="")
        self.badge_label.get_style_context().add_class("tile-badge")
        header_box.pack_end(self.badge_label, False, False, 4)

        self.pack_start(header_box, False, False, 0)

        # 2. Main Metric Row (Large Percentage + Secondary quantity)
        metric_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        metric_box.set_valign(Gtk.Align.BASELINE)

        self.percent_label = Gtk.Label()
        self.percent_label.get_style_context().add_class("metric-percent")
        self.percent_label.set_xalign(0.0)
        metric_box.pack_start(self.percent_label, False, False, 0)

        self.sub_metric_label = Gtk.Label()
        self.sub_metric_label.get_style_context().add_class("metric-sub")
        self.sub_metric_label.set_xalign(1.0)
        metric_box.pack_end(self.sub_metric_label, True, True, 0)

        self.pack_start(metric_box, False, False, 0)

        # 3. Progress Bar
        self.progress_bar = CapsuleProgressBar(base_color=self.base_color, height=8)
        self.pack_start(self.progress_bar, False, False, 2)

        # 4. Sparkline Graph
        self.sparkline = SparklineGraph(base_color=self.base_color, height=52)
        self.pack_start(self.sparkline, False, False, 4)

        # Separator line
        sep = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        sep.get_style_context().add_class("tile-separator")
        self.pack_start(sep, False, False, 2)

        # 5. Quantitative Details Grid
        self.details_grid = Gtk.Grid()
        self.details_grid.set_column_spacing(12)
        self.details_grid.set_row_spacing(4)
        self.details_grid.set_hexpand(True)

        self.detail_labels = {}
        self.pack_start(self.details_grid, False, False, 0)

    def add_detail_row(self, row_idx: int, key: str, label_text: str):
        lbl = Gtk.Label(label=label_text)
        lbl.get_style_context().add_class("detail-name")
        lbl.set_xalign(0.0)
        self.details_grid.attach(lbl, 0, row_idx, 1, 1)

        val = Gtk.Label(label="-")
        val.get_style_context().add_class("detail-value")
        val.set_xalign(1.0)
        val.set_hexpand(True)
        self.details_grid.attach(val, 1, row_idx, 1, 1)

        self.detail_labels[key] = val

    def set_detail_value(self, key: str, value: str):
        if key in self.detail_labels:
            self.detail_labels[key].set_text(value)

    def set_badge(self, text: str):
        self.badge_label.set_text(text)

    def set_percent(self, percent: float, formatted_text: Optional[str] = None):
        text = formatted_text if formatted_text else f"{percent:.1f}%"
        self.percent_label.set_markup(f"<b>{text}</b>")
        self.progress_bar.set_percent(percent)

        # Update KPI Status Pill
        style_ctx = self.status_pill.get_style_context()
        style_ctx.remove_class("pill-ok")
        style_ctx.remove_class("pill-warn")
        style_ctx.remove_class("pill-crit")

        if percent >= CRIT_THRESHOLD:
            self.status_pill.set_text("ALERT")
            style_ctx.add_class("pill-crit")
        elif percent >= WARN_THRESHOLD:
            self.status_pill.set_text("UWAGA")
            style_ctx.add_class("pill-warn")
        else:
            self.status_pill.set_text("NORMA")
            style_ctx.add_class("pill-ok")

        # Set dynamic color style on percent label
        color = get_color_for_percent(percent, self.base_color)
        self.percent_label.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(*hex_to_rgba(color)))

    def set_sub_metric(self, text: str):
        self.sub_metric_label.set_text(text)

    def set_graph_data(self, history: Sequence[float]):
        self.sparkline.set_data(history)

    def set_graph_visible(self, visible: bool):
        self.sparkline.set_visible(visible)
