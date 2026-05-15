from __future__ import annotations

import asyncio
import contextlib
import datetime
import logging
from dataclasses import dataclass, field

import psutil

log = logging.getLogger(__name__)


@dataclass
class ProcessInfo:
    pid: int
    name: str
    cpu_percent: float
    mem_mb: float


@dataclass
class SystemSnapshot:
    cpu_percent: float
    ram_used_gb: float
    ram_total_gb: float
    ram_percent: float
    disk_used_gb: float
    disk_total_gb: float
    disk_percent: float
    uptime_seconds: float
    load_avg: tuple[float, float, float]
    net_sent_mb: float
    net_recv_mb: float
    net_is_rate: bool = field(default=False)

    def uptime_str(self) -> str:
        delta = datetime.timedelta(seconds=int(self.uptime_seconds))
        days = delta.days
        hours, remainder = divmod(delta.seconds, 3600)
        minutes, _ = divmod(remainder, 60)
        parts = []
        if days:
            parts.append(f"{days}d")
        if hours:
            parts.append(f"{hours}h")
        parts.append(f"{minutes}m")
        return " ".join(parts)

    def format(self) -> str:
        cpu_bar = _bar(self.cpu_percent)
        ram_bar = _bar(self.ram_percent)
        disk_bar = _bar(self.disk_percent)

        if self.net_is_rate:
            net_line = f"🌐 *Red*: ↑ {self.net_sent_mb:.2f} MB/s  ↓ {self.net_recv_mb:.2f} MB/s  (media 5m)\n\n"
        else:
            net_line = f"🌐 *Red*: ↑ {self.net_sent_mb:.1f} MB  ↓ {self.net_recv_mb:.1f} MB  (desde boot)\n\n"

        return (
            "📊 *Métricas del sistema*\n\n"
            f"🖥️ *CPU*: {self.cpu_percent:.1f}%  {cpu_bar}\n"
            f"   Load avg: {self.load_avg[0]:.2f} · {self.load_avg[1]:.2f} · {self.load_avg[2]:.2f}\n\n"
            f"💾 *RAM*: {self.ram_used_gb:.1f} / {self.ram_total_gb:.1f} GB  ({self.ram_percent:.0f}%)  {ram_bar}\n\n"
            f"💿 *Disco*: {self.disk_used_gb:.1f} / {self.disk_total_gb:.1f} GB  ({self.disk_percent:.0f}%)  {disk_bar}\n\n"
            f"{net_line}"
            f"⏱️ *Uptime*: {self.uptime_str()}"
        )


def _bar(percent: float, length: int = 10) -> str:
    filled = round(percent / 100 * length)
    return "█" * filled + "░" * (length - filled)


async def snapshot(prom=None) -> SystemSnapshot:
    """Returns a SystemSnapshot, preferring Prometheus data when available."""
    if prom is not None and prom.available:
        result = await _snapshot_from_prometheus(prom)
        if result is not None:
            return result
    return _snapshot_from_psutil()


async def _snapshot_from_prometheus(prom) -> SystemSnapshot | None:
    (
        cpu,
        ram_used_bytes,
        ram_total_bytes,
        disk_used_bytes,
        disk_total_bytes,
        uptime,
        load1,
        load5,
        load15,
        net_tx,
        net_rx,
    ) = await asyncio.gather(
        prom.query('100 - (avg(rate(node_cpu_seconds_total{mode="idle"}[2m])) * 100)'),
        prom.query("node_memory_MemTotal_bytes - node_memory_MemAvailable_bytes"),
        prom.query("node_memory_MemTotal_bytes"),
        prom.query(
            'node_filesystem_size_bytes{mountpoint="/",fstype!~"tmpfs|rootfs|overlay"}'
            ' - node_filesystem_avail_bytes{mountpoint="/",fstype!~"tmpfs|rootfs|overlay"}'
        ),
        prom.query('node_filesystem_size_bytes{mountpoint="/",fstype!~"tmpfs|rootfs|overlay"}'),
        prom.query("time() - node_boot_time_seconds"),
        prom.query("node_load1"),
        prom.query("node_load5"),
        prom.query("node_load15"),
        prom.query('sum(rate(node_network_transmit_bytes_total{device!="lo"}[5m]))'),
        prom.query('sum(rate(node_network_receive_bytes_total{device!="lo"}[5m]))'),
    )

    # Require the most critical metrics; fall back to psutil if missing
    if any(
        v is None for v in (cpu, ram_used_bytes, ram_total_bytes, disk_used_bytes, disk_total_bytes)
    ):
        return None

    ram_total = ram_total_bytes or 1.0
    disk_total = disk_total_bytes or 1.0

    return SystemSnapshot(
        cpu_percent=cpu,
        ram_used_gb=ram_used_bytes / 1024**3,
        ram_total_gb=ram_total / 1024**3,
        ram_percent=100 * ram_used_bytes / ram_total,
        disk_used_gb=(disk_used_bytes or 0) / 1024**3,
        disk_total_gb=disk_total / 1024**3,
        disk_percent=100 * (disk_used_bytes or 0) / disk_total,
        uptime_seconds=uptime or 0.0,
        load_avg=(load1 or 0.0, load5 or 0.0, load15 or 0.0),
        net_sent_mb=(net_tx or 0.0) / 1024**2,
        net_recv_mb=(net_rx or 0.0) / 1024**2,
        net_is_rate=True,
    )


def _snapshot_from_psutil() -> SystemSnapshot:
    cpu = psutil.cpu_percent(interval=1)
    ram = psutil.virtual_memory()
    disk = psutil.disk_usage("/")
    boot_time = psutil.boot_time()
    uptime = datetime.datetime.now().timestamp() - boot_time
    net = psutil.net_io_counters()

    try:
        load = psutil.getloadavg()
    except AttributeError:
        load = (0.0, 0.0, 0.0)

    return SystemSnapshot(
        cpu_percent=cpu,
        ram_used_gb=ram.used / 1024**3,
        ram_total_gb=ram.total / 1024**3,
        ram_percent=ram.percent,
        disk_used_gb=disk.used / 1024**3,
        disk_total_gb=disk.total / 1024**3,
        disk_percent=disk.percent,
        uptime_seconds=uptime,
        load_avg=(load[0], load[1], load[2]),
        net_sent_mb=net.bytes_sent / 1024**2,
        net_recv_mb=net.bytes_recv / 1024**2,
    )


def top_processes(n: int = 10) -> list[ProcessInfo]:
    procs = []
    for p in psutil.process_iter(["pid", "name", "cpu_percent", "memory_info"]):
        with contextlib.suppress(psutil.NoSuchProcess, psutil.AccessDenied):
            procs.append(
                ProcessInfo(
                    pid=p.info["pid"],
                    name=p.info["name"] or "?",
                    cpu_percent=p.info["cpu_percent"] or 0.0,
                    mem_mb=(p.info["memory_info"].rss if p.info["memory_info"] else 0) / 1024**2,
                )
            )
    return sorted(procs, key=lambda p: p.cpu_percent, reverse=True)[:n]
