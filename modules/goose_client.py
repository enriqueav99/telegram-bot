from __future__ import annotations

import asyncio
import contextlib
import logging
import re
import shutil

log = logging.getLogger(__name__)

_ANSI_RE = re.compile(r"\x1b\[[0-9;]*[mK]")
_MAX_MSG = 4000


def _strip_ansi(text: str) -> str:
    return _ANSI_RE.sub("", text)


def _split(text: str, size: int = _MAX_MSG) -> list[str]:
    if len(text) <= size:
        return [text]
    chunks: list[str] = []
    while text:
        if len(text) <= size:
            chunks.append(text)
            break
        cut = text.rfind("\n", 0, size)
        if cut == -1:
            cut = size
        chunks.append(text[:cut])
        text = text[cut:].lstrip("\n")
    return chunks


def available() -> bool:
    return shutil.which("goose") is not None


async def run(prompt: str, timeout: int = 120) -> str:
    if not available():
        return "❌ `goose` no está instalado en este servidor."
    try:
        proc = await asyncio.create_subprocess_exec(
            "goose",
            "run",
            "--text",
            prompt,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        output = _strip_ansi(stdout.decode("utf-8", errors="replace")).strip()
        if not output:
            output = _strip_ansi(stderr.decode("utf-8", errors="replace")).strip()
        return output or "(sin respuesta)"
    except TimeoutError:
        with contextlib.suppress(Exception):
            proc.kill()
        return f"⏱️ Goose no respondió en {timeout}s."
    except Exception as e:
        log.error("Error ejecutando goose: %s", e)
        return f"❌ Error: {e}"
