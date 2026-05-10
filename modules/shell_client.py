"""Ejecución de comandos de shell registrados en el servidor."""

from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path

COMMANDS_FILE = Path("data/shell_commands.json")
_LEGACY_FILE = Path("data/ssh_commands.json")
SHELL_TIMEOUT = 30

log = logging.getLogger(__name__)


def _load_raw() -> dict[str, str]:
    if COMMANDS_FILE.exists():
        return json.loads(COMMANDS_FILE.read_text())
    if _LEGACY_FILE.exists():
        data = json.loads(_LEGACY_FILE.read_text())
        _save_raw(data)
        log.info("Migrado ssh_commands.json → shell_commands.json")
        return data
    return {}


def _save_raw(commands: dict[str, str]) -> None:
    COMMANDS_FILE.parent.mkdir(parents=True, exist_ok=True)
    COMMANDS_FILE.write_text(json.dumps(commands, indent=2, ensure_ascii=False))


def load_commands() -> dict[str, str]:
    return _load_raw()


def add_command(alias: str, command: str) -> None:
    commands = _load_raw()
    commands[alias] = command
    _save_raw(commands)


def remove_command(alias: str) -> bool:
    commands = _load_raw()
    if alias not in commands:
        return False
    del commands[alias]
    _save_raw(commands)
    return True


async def run(command: str) -> tuple[str, str, int]:
    proc = await asyncio.create_subprocess_shell(
        command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=SHELL_TIMEOUT)
    except TimeoutError:
        proc.kill()
        return "", f"Error: comando superó el límite de {SHELL_TIMEOUT}s", 1
    return stdout.decode(errors="replace"), stderr.decode(errors="replace"), proc.returncode or 0
