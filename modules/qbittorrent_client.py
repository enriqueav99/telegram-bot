from __future__ import annotations

import os
from dataclasses import dataclass

import aiohttp

_STATE_ICONS = {
    "downloading": "⬇️",
    "forcedDL": "⬇️",
    "uploading": "⬆️",
    "forcedUP": "⬆️",
    "stalledUP": "💤",
    "stalledDL": "⏳",
    "pausedDL": "⏸",
    "pausedUP": "✅",
    "queuedDL": "📋",
    "queuedUP": "📋",
    "checkingDL": "🔍",
    "checkingUP": "🔍",
    "checkingResumeData": "🔍",
    "metaDL": "📡",
    "allocating": "💿",
    "error": "❌",
    "missingFiles": "❌",
    "moving": "🚚",
}


@dataclass
class Torrent:
    hash: str
    name: str
    state: str
    progress: float
    size: int
    dlspeed: int
    upspeed: int

    @property
    def icon(self) -> str:
        return _STATE_ICONS.get(self.state, "❓")

    @property
    def short_hash(self) -> str:
        return self.hash[:8]

    @property
    def size_str(self) -> str:
        gb = self.size / 1024**3
        if gb >= 1:
            return f"{gb:.1f} GB"
        mb = self.size / 1024**2
        return f"{mb:.0f} MB"

    @property
    def progress_str(self) -> str:
        return f"{self.progress * 100:.0f}%"

    def short_name(self, max_len: int = 40) -> str:
        return self.name if len(self.name) <= max_len else self.name[: max_len - 1] + "…"


class QBittorrentClient:
    def __init__(self) -> None:
        self.base = (os.getenv("QBITTORRENT_URL") or "").rstrip("/")
        self.username = os.getenv("QBITTORRENT_USER", "admin")
        self.password = os.getenv("QBITTORRENT_PASSWORD", "")
        self._session: aiohttp.ClientSession | None = None

    @property
    def available(self) -> bool:
        return bool(self.base)

    async def _session_(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(cookie_jar=aiohttp.CookieJar())
        return self._session

    async def login(self) -> bool:
        s = await self._session_()
        async with s.post(
            f"{self.base}/api/v2/auth/login",
            data={"username": self.username, "password": self.password},
        ) as resp:
            return (await resp.text()).strip() == "Ok."

    async def _get(self, path: str, **params) -> list | dict:
        s = await self._session_()
        async with s.get(f"{self.base}{path}", params=params) as resp:
            if resp.status == 403:
                await self.login()
                async with s.get(f"{self.base}{path}", params=params) as r2:
                    return await r2.json()
            return await resp.json()

    async def _post(self, path: str, data: dict) -> int:
        s = await self._session_()
        async with s.post(f"{self.base}{path}", data=data) as resp:
            if resp.status == 403:
                await self.login()
                async with s.post(f"{self.base}{path}", data=data) as r2:
                    return r2.status
            return resp.status

    async def torrents(self) -> list[Torrent]:
        raw = await self._get("/api/v2/torrents/info")
        return [
            Torrent(
                hash=t["hash"],
                name=t["name"],
                state=t["state"],
                progress=t["progress"],
                size=t["size"],
                dlspeed=t["dlspeed"],
                upspeed=t["upspeed"],
            )
            for t in (raw if isinstance(raw, list) else [])
        ]

    async def add(self, urls: str) -> bool:
        return (await self._post("/api/v2/torrents/add", {"urls": urls})) == 200

    async def pause(self, hash_: str) -> None:
        await self._post("/api/v2/torrents/pause", {"hashes": hash_})

    async def resume(self, hash_: str) -> None:
        await self._post("/api/v2/torrents/resume", {"hashes": hash_})

    async def delete(self, hash_: str, delete_files: bool = False) -> None:
        await self._post(
            "/api/v2/torrents/delete",
            {"hashes": hash_, "deleteFiles": "true" if delete_files else "false"},
        )
