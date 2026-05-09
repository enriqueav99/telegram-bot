from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime

import aiohttp

log = logging.getLogger(__name__)

_STATUS_EMOJI = {
    "queued": "⏳",
    "in_progress": "🔄",
    "completed": "✅",
}

_CONCLUSION_EMOJI = {
    "success": "✅",
    "failure": "❌",
    "cancelled": "🚫",
    "timed_out": "⏱️",
    "skipped": "⏭️",
    "neutral": "⬜",
    "action_required": "⚠️",
}


@dataclass
class WorkflowRun:
    id: int
    run_number: int
    name: str
    status: str
    conclusion: str | None
    branch: str
    event: str
    created_at: str

    @property
    def emoji(self) -> str:
        if self.status == "completed":
            return _CONCLUSION_EMOJI.get(self.conclusion or "", "❓")
        return _STATUS_EMOJI.get(self.status, "❓")

    @property
    def status_str(self) -> str:
        if self.status == "completed":
            return self.conclusion or "completed"
        return self.status

    @property
    def age_str(self) -> str:
        try:
            dt = datetime.fromisoformat(self.created_at.replace("Z", "+00:00"))
            delta = datetime.now(UTC) - dt
            secs = int(delta.total_seconds())
            if secs < 60:
                return f"hace {secs}s"
            if secs < 3600:
                return f"hace {secs // 60}m"
            if secs < 86400:
                return f"hace {secs // 3600}h"
            return f"hace {secs // 86400}d"
        except Exception:
            return self.created_at


class GitHubClient:
    _BASE = "https://api.github.com"

    def __init__(self, token: str, repo: str) -> None:
        self._token = token
        self._repo = repo  # "owner/repo"

    @property
    def available(self) -> bool:
        return bool(self._token and self._repo)

    @property
    def repo(self) -> str:
        return self._repo

    async def get_runs(self, limit: int = 10) -> list[WorkflowRun] | None:
        if not self.available:
            return None
        headers = {
            "Authorization": f"Bearer {self._token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        url = f"{self._BASE}/repos/{self._repo}/actions/runs?per_page={limit}"
        try:
            timeout = aiohttp.ClientTimeout(total=10)
            async with (
                aiohttp.ClientSession(timeout=timeout) as session,
                session.get(url, headers=headers) as resp,
            ):
                if resp.status != 200:
                    log.error("GitHub API devolvió %d para %s", resp.status, self._repo)
                    return None
                data = await resp.json()
        except Exception:
            log.exception("Error consultando GitHub Actions")
            return None

        return [
            WorkflowRun(
                id=r["id"],
                run_number=r["run_number"],
                name=r["name"],
                status=r["status"],
                conclusion=r.get("conclusion"),
                branch=r.get("head_branch", "—"),
                event=r.get("event", "—"),
                created_at=r["created_at"],
            )
            for r in data.get("workflow_runs", [])
        ]
