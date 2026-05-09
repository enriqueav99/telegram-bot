from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass

log = logging.getLogger(__name__)

CONTAINER = "wireguard"
CONNECTED_THRESHOLD = 180  # seconds — WireGuard re-handshakes every ~3min


@dataclass
class WgPeer:
    public_key: str
    endpoint: str
    allowed_ips: str
    last_handshake: int  # unix timestamp, 0 = never
    rx_bytes: int
    tx_bytes: int

    @property
    def connected(self) -> bool:
        return self.last_handshake > 0 and (time.time() - self.last_handshake) < CONNECTED_THRESHOLD

    @property
    def short_key(self) -> str:
        return self.public_key[:12] + "..."

    @property
    def handshake_str(self) -> str:
        if self.last_handshake == 0:
            return "Nunca"
        delta = int(time.time() - self.last_handshake)
        if delta < 60:
            return f"hace {delta}s"
        if delta < 3600:
            return f"hace {delta // 60}m {delta % 60}s"
        return f"hace {delta // 3600}h {(delta % 3600) // 60}m"

    @property
    def transfer_str(self) -> str:
        def fmt(b: int) -> str:
            if b < 1024:
                return f"{b} B"
            if b < 1024**2:
                return f"{b / 1024:.1f} KB"
            return f"{b / 1024**2:.1f} MB"

        return f"↓{fmt(self.rx_bytes)} ↑{fmt(self.tx_bytes)}"


def _parse_dump(output: str) -> list[WgPeer]:
    """Parse output of `wg show all dump` (tab-separated, 9 fields = peer line)."""
    peers = []
    for line in output.strip().splitlines():
        fields = line.split("\t")
        if len(fields) != 9:
            continue
        try:
            peers.append(
                WgPeer(
                    public_key=fields[1],
                    endpoint=fields[3] if fields[3] != "(none)" else "—",
                    allowed_ips=fields[4],
                    last_handshake=int(fields[5]),
                    rx_bytes=int(fields[6]),
                    tx_bytes=int(fields[7]),
                )
            )
        except (ValueError, IndexError):
            continue
    return peers


async def get_peers(docker_client) -> list[WgPeer] | None:
    """Returns peer list, or None if the wireguard container is unavailable."""

    def _run() -> str | None:
        container = docker_client.get_container(CONTAINER)
        if not container:
            return None
        result = container.exec_run("wg show all dump")
        if result.exit_code != 0:
            log.warning("wg show exited with code %d", result.exit_code)
            return None
        return result.output.decode("utf-8", errors="replace")

    try:
        output = await asyncio.to_thread(_run)
    except Exception:
        log.exception("Error ejecutando wg show en contenedor %s", CONTAINER)
        return None

    if output is None:
        return None
    return _parse_dump(output)
