"""System statistics collector using psutil."""
import os
import time
import psutil
from collections import deque
from dataclasses import dataclass
from typing import List, Tuple

# Minimalny odstęp między skanami listy procesów (kosztowne przy 0.5 s odświeżania)
TOP_PROCS_MIN_INTERVAL = 1.5


@dataclass
class CPUStats:
    percent: float = 0.0
    freq_str: str = "N/A"
    cores_logical: int = 1
    cores_physical: int = 1
    load_avg: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    max_core_percent: float = 0.0
    top_proc: Tuple[str, float] = ("-", 0.0)


@dataclass
class RAMStats:
    percent: float = 0.0
    used_gb: float = 0.0
    total_gb: float = 0.0
    avail_gb: float = 0.0
    swap_percent: float = 0.0
    swap_used_gb: float = 0.0
    swap_total_gb: float = 0.0
    top_proc: Tuple[str, str] = ("-", "0 MB")


@dataclass
class SwapStats:
    percent: float = 0.0
    used_gb: float = 0.0
    total_gb: float = 0.0
    free_gb: float = 0.0
    sin_mb: float = 0.0
    sout_mb: float = 0.0


@dataclass
class DiskStats:
    mountpoint: str = "/"
    device: str = "-"
    fstype: str = ""
    percent: float = 0.0
    used_bytes: int = 0
    total_bytes: int = 0
    free_bytes: int = 0
    read_bps: float = 0.0
    write_bps: float = 0.0
    busy_percent: float = 0.0


def format_bytes(num: float) -> str:
    """Format a byte count as MB / GB / TB."""
    if num >= 1024**4:
        return f"{num / 1024**4:.2f} TB"
    if num >= 1024**3:
        return f"{num / 1024**3:.1f} GB"
    return f"{num / 1024**2:.0f} MB"


def format_rate(bps: float) -> str:
    """Format a transfer rate in bytes/second."""
    if bps >= 1024**3:
        return f"{bps / 1024**3:.1f} GB/s"
    if bps >= 1024**2:
        return f"{bps / 1024**2:.1f} MB/s"
    return f"{bps / 1024:.0f} KB/s"


def list_disk_partitions() -> List[Tuple[str, str, str]]:
    """Return (mountpoint, device, fstype) for real, mounted partitions."""
    result = []
    seen = set()
    try:
        parts = psutil.disk_partitions(all=False)
    except Exception:
        return [("/", "-", "")]
    for p in parts:
        dev_name = os.path.basename(p.device)
        if dev_name.startswith("loop") or p.mountpoint.startswith("/snap"):
            continue
        if p.mountpoint in seen:
            continue
        seen.add(p.mountpoint)
        result.append((p.mountpoint, p.device, p.fstype))
    if not any(m == "/" for m, _, _ in result):
        result.insert(0, ("/", "-", ""))
    return result


class SystemStatsCollector:
    def __init__(self, history_len: int = 35, disk_path: str = "/"):
        self.history_len = history_len
        self.cpu_history = deque([0.0] * history_len, maxlen=history_len)
        self.ram_history = deque([0.0] * history_len, maxlen=history_len)
        self.swap_history = deque([0.0] * history_len, maxlen=history_len)
        self.disk_history = deque([0.0] * history_len, maxlen=history_len)

        # Initial non-blocking seed
        psutil.cpu_percent(interval=None)
        psutil.cpu_percent(interval=None, percpu=True)
        self.cores_logical = psutil.cpu_count(logical=True) or 1
        self.cores_physical = psutil.cpu_count(logical=False) or self.cores_logical

        self._last_procs_time = 0.0
        self._top_cpu = ("-", 0.0)
        self._top_ram = ("-", "0 MB")

        self.set_disk_path(disk_path)

    def set_disk_path(self, path: str):
        """Select the mountpoint whose usage and I/O is reported."""
        self.disk_path = path if os.path.isdir(path) else "/"
        self.disk_device = "-"
        self.disk_fstype = ""
        for mount, device, fstype in list_disk_partitions():
            if mount == self.disk_path:
                self.disk_device, self.disk_fstype = device, fstype
                break
        # Klucz w /proc/diskstats (np. nvme0n1p2, dm-0 dla /dev/mapper/*)
        self._io_key = None
        if self.disk_device.startswith("/dev/"):
            self._io_key = os.path.basename(os.path.realpath(self.disk_device))
        self._last_io = None
        self._last_io_time = None
        self.disk_history.extend([0.0] * self.history_len)

    def _read_io(self):
        try:
            if self._io_key:
                per_disk = psutil.disk_io_counters(perdisk=True) or {}
                if self._io_key in per_disk:
                    return per_disk[self._io_key]
            return psutil.disk_io_counters(perdisk=False)
        except Exception:
            return None

    def _update_top_procs(self):
        now = time.monotonic()
        if now - self._last_procs_time < TOP_PROCS_MIN_INTERVAL:
            return
        self._last_procs_time = now
        try:
            procs = []
            for p in psutil.process_iter(['name', 'cpu_percent', 'memory_info']):
                try:
                    procs.append(p.info)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            if not procs:
                return

            best_cpu = max(procs, key=lambda x: x.get('cpu_percent') or 0.0)
            self._top_cpu = ((best_cpu.get('name') or "brak")[:12], best_cpu.get('cpu_percent') or 0.0)

            best_ram = max(procs, key=lambda x: (x.get('memory_info').rss if x.get('memory_info') else 0))
            if best_ram.get('memory_info'):
                rss = best_ram['memory_info'].rss
                self._top_ram = ((best_ram.get('name') or "brak")[:12], format_bytes(rss))
        except Exception:
            pass

    def update_disk(self) -> DiskStats:
        stats = DiskStats(mountpoint=self.disk_path, device=self.disk_device, fstype=self.disk_fstype)
        try:
            du = psutil.disk_usage(self.disk_path)
            stats.percent = du.percent
            stats.used_bytes = du.used
            stats.total_bytes = du.total
            stats.free_bytes = du.free
        except OSError:
            pass

        now = time.monotonic()
        io = self._read_io()
        if io is not None and self._last_io is not None:
            dt = now - self._last_io_time
            if dt > 0:
                stats.read_bps = max(0, io.read_bytes - self._last_io.read_bytes) / dt
                stats.write_bps = max(0, io.write_bytes - self._last_io.write_bytes) / dt
                busy_ms = getattr(io, "busy_time", None)
                prev_busy_ms = getattr(self._last_io, "busy_time", None)
                if busy_ms is not None and prev_busy_ms is not None:
                    stats.busy_percent = min(100.0, max(0.0, (busy_ms - prev_busy_ms) / (dt * 1000.0) * 100.0))
        self._last_io = io
        self._last_io_time = now

        # Wykres dysku pokazuje aktywność I/O (zajętość miejsca zmienia się zbyt wolno)
        self.disk_history.append(stats.busy_percent)
        return stats

    def update(self, include_top_procs: bool = True) -> Tuple[CPUStats, RAMStats, SwapStats, DiskStats]:
        # 1. CPU Usage
        cpu_pct = psutil.cpu_percent(interval=None)
        self.cpu_history.append(cpu_pct)
        per_core = psutil.cpu_percent(interval=None, percpu=True)
        max_core = max(per_core) if per_core else 0.0

        # Frequency
        freq = psutil.cpu_freq()
        if freq and freq.current > 0:
            if freq.current >= 1000:
                freq_str = f"{freq.current / 1000.0:.2f} GHz"
            else:
                freq_str = f"{int(freq.current)} MHz"
        else:
            freq_str = "N/A"

        # Load Average
        try:
            load = os.getloadavg()
        except (AttributeError, OSError):
            load = (0.0, 0.0, 0.0)

        # Top processes
        if include_top_procs:
            self._update_top_procs()
            top_cpu, top_ram = self._top_cpu, self._top_ram
        else:
            top_cpu, top_ram = ("-", 0.0), ("-", "0 MB")

        cpu_stats = CPUStats(
            percent=cpu_pct,
            freq_str=freq_str,
            cores_logical=self.cores_logical,
            cores_physical=self.cores_physical,
            load_avg=load,
            max_core_percent=max_core,
            top_proc=top_cpu
        )

        # 2. RAM Usage
        vm = psutil.virtual_memory()
        self.ram_history.append(vm.percent)

        sm = psutil.swap_memory()
        self.swap_history.append(sm.percent)

        ram_stats = RAMStats(
            percent=vm.percent,
            used_gb=vm.used / (1024**3),
            total_gb=vm.total / (1024**3),
            avail_gb=vm.available / (1024**3),
            swap_percent=sm.percent,
            swap_used_gb=sm.used / (1024**3),
            swap_total_gb=sm.total / (1024**3),
            top_proc=top_ram
        )

        swap_stats = SwapStats(
            percent=sm.percent,
            used_gb=sm.used / (1024**3),
            total_gb=sm.total / (1024**3),
            free_gb=sm.free / (1024**3),
            sin_mb=sm.sin / (1024**2),
            sout_mb=sm.sout / (1024**2)
        )

        # 3. Disk
        disk_stats = self.update_disk()

        return cpu_stats, ram_stats, swap_stats, disk_stats
