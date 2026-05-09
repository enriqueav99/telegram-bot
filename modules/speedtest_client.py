from __future__ import annotations

from dataclasses import dataclass


@dataclass
class SpeedResult:
    download_mbps: float
    upload_mbps: float
    ping_ms: float
    server_name: str
    server_country: str

    def format(self) -> str:
        return (
            "🌐 *Speedtest*\n\n"
            f"⬇️ Bajada: *{self.download_mbps:.1f} Mbps*\n"
            f"⬆️ Subida: *{self.upload_mbps:.1f} Mbps*\n"
            f"📡 Ping: *{self.ping_ms:.0f} ms*\n"
            f"🏠 Servidor: {self.server_name}, {self.server_country}"
        )


def run() -> SpeedResult:
    import speedtest  # noqa: PLC0415 — lazy import, this call blocks ~30s

    s = speedtest.Speedtest(secure=True)
    s.get_best_server()
    download = s.download() / 1_000_000
    upload = s.upload() / 1_000_000
    server = s.results.server
    return SpeedResult(
        download_mbps=download,
        upload_mbps=upload,
        ping_ms=s.results.ping,
        server_name=server.get("name", "?"),
        server_country=server.get("country", "?"),
    )
