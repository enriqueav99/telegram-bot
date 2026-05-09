from __future__ import annotations

import datetime
import logging
from dataclasses import dataclass

import psutil

log = logging.getLogger(__name__)


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

        return (
            "📊 *Métricas del sistema*\n\n"
            f"🖥️ *CPU*: {self.cpu_percent:.1f}%  {cpu_bar}\n"
            f"   Load avg: {self.load_avg[0]:.2f} · {self.load_avg[1]:.2f} · {self.load_avg[2]:.2f}\n\n"
            f"💾 *RAM*: {self.ram_used_gb:.1f} / {self.ram_total_gb:.1f} GB  ({self.ram_percent:.0f}%)  {ram_bar}\n\n"
            f"💿 *Disco*: {self.disk_used_gb:.1f} / {self.disk_total_gb:.1f} GB  ({self.disk_percent:.0f}%)  {disk_bar}\n\n"
            f"⏱️ *Uptime*: {self.uptime_str()}"
        )


def _bar(percent: float, length: int = 10) -> str:
    filled = round(percent / 100 * length)
    return "█" * filled + "░" * (length - filled)


def snapshot() -> SystemSnapshot:
    cpu = psutil.cpu_percent(interval=1)
    ram = psutil.virtual_memory()
    disk = psutil.disk_usage("/")
    boot_time = psutil.boot_time()
    uptime = datetime.datetime.now().timestamp() - boot_time

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
    )
