"""Cliente HTTP para la API de Prometheus."""

from __future__ import annotations

import logging

import aiohttp

log = logging.getLogger(__name__)

_TIMEOUT = aiohttp.ClientTimeout(total=10)


class PrometheusClient:
    def __init__(self, url: str) -> None:
        self._url = url.rstrip("/")
        self.available = bool(url)

    async def query(self, promql: str) -> float | None:
        """Instant query → primer valor escalar, o None si falla o no hay datos."""
        if not self.available:
            return None
        try:
            async with (
                aiohttp.ClientSession(timeout=_TIMEOUT) as session,
                session.get(
                    f"{self._url}/api/v1/query",
                    params={"query": promql},
                ) as resp,
            ):
                data = await resp.json(content_type=None)
                result = data.get("data", {}).get("result", [])
                if result:
                    return float(result[0]["value"][1])
        except Exception as exc:
            log.debug("Prometheus query error (%s…): %s", promql[:50], exc)
        return None
