from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from modules.system_client import SystemSnapshot, _bar, snapshot

# ── _bar ───────────────────────────────────────────────────────────────────────


def test_bar_zero_percent():
    assert _bar(0) == "░" * 10


def test_bar_full_percent():
    assert _bar(100) == "█" * 10


def test_bar_half():
    result = _bar(50)
    assert result.count("█") == 5
    assert result.count("░") == 5


def test_bar_custom_length():
    assert len(_bar(50, length=20)) == 20


# ── SystemSnapshot.uptime_str ──────────────────────────────────────────────────


def test_uptime_only_minutes():
    snap = _snap(uptime=300)
    assert snap.uptime_str() == "5m"


def test_uptime_hours_and_minutes():
    snap = _snap(uptime=3600 + 30 * 60)
    assert snap.uptime_str() == "1h 30m"


def test_uptime_days():
    snap = _snap(uptime=2 * 86400 + 3600)
    assert "2d" in snap.uptime_str()
    assert "1h" in snap.uptime_str()


def test_uptime_zero_minutes_shown():
    snap = _snap(uptime=3600)
    assert snap.uptime_str() == "1h 0m"


# ── SystemSnapshot.format ──────────────────────────────────────────────────────


def test_format_contains_cpu_section():
    assert "CPU" in _snap().format()


def test_format_contains_ram_section():
    assert "RAM" in _snap().format()


def test_format_contains_disk_section():
    assert "Disco" in _snap().format()


def test_format_contains_uptime():
    assert "Uptime" in _snap().format()


def test_format_shows_values():
    snap = _snap(cpu=42.5, ram_used=2.0, ram_total=8.0)
    text = snap.format()
    assert "42.5" in text
    assert "2.0" in text
    assert "8.0" in text


# ── snapshot() integration (mocked psutil) ────────────────────────────────────


@pytest.mark.asyncio
async def test_snapshot_returns_system_snapshot():
    with _mock_psutil():
        result = await snapshot()
    assert isinstance(result, SystemSnapshot)
    assert result.cpu_percent == 25.0
    assert result.ram_total_gb == pytest.approx(8.0, rel=0.01)


@pytest.mark.asyncio
async def test_snapshot_disk_values():
    with _mock_psutil():
        result = await snapshot()
    assert result.disk_total_gb > 0
    assert 0 <= result.disk_percent <= 100


# ── helpers ───────────────────────────────────────────────────────────────────


def _snap(
    cpu: float = 10.0,
    ram_used: float = 1.0,
    ram_total: float = 8.0,
    disk_used: float = 50.0,
    disk_total: float = 200.0,
    uptime: float = 3600.0,
    net_sent_mb: float = 100.0,
    net_recv_mb: float = 200.0,
) -> SystemSnapshot:
    ram_pct = ram_used / ram_total * 100
    disk_pct = disk_used / disk_total * 100
    return SystemSnapshot(
        cpu_percent=cpu,
        ram_used_gb=ram_used,
        ram_total_gb=ram_total,
        ram_percent=ram_pct,
        disk_used_gb=disk_used,
        disk_total_gb=disk_total,
        disk_percent=disk_pct,
        uptime_seconds=uptime,
        load_avg=(0.5, 0.4, 0.3),
        net_sent_mb=net_sent_mb,
        net_recv_mb=net_recv_mb,
    )


def _mock_psutil():
    GB = 1024**3
    vm = MagicMock()
    vm.used = 2 * GB
    vm.total = 8 * GB
    vm.percent = 25.0

    disk = MagicMock()
    disk.used = 50 * GB
    disk.total = 200 * GB
    disk.percent = 25.0

    net = MagicMock()
    net.bytes_sent = 100 * 1024**2
    net.bytes_recv = 200 * 1024**2

    return patch.multiple(
        "modules.system_client.psutil",
        cpu_percent=MagicMock(return_value=25.0),
        virtual_memory=MagicMock(return_value=vm),
        disk_usage=MagicMock(return_value=disk),
        boot_time=MagicMock(return_value=0.0),
        getloadavg=MagicMock(return_value=(0.5, 0.4, 0.3)),
        net_io_counters=MagicMock(return_value=net),
    )
