from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path

COMMANDS_FILE = Path("data/ssh_commands.json")
SHELL_TIMEOUT = 30

log = logging.getLogger(__name__)


def load_commands() -> dict[str, str]:
    if not COMMANDS_FILE.exists():
        return {}
    return json.loads(COMMANDS_FILE.read_text())


def save_commands(commands: dict[str, str]) -> None:
    COMMANDS_FILE.parent.mkdir(parents=True, exist_ok=True)
    COMMANDS_FILE.write_text(json.dumps(commands, indent=2, ensure_ascii=False))


def add_command(alias: str, command: str) -> None:
    commands = load_commands()
    commands[alias] = command
    save_commands(commands)


def remove_command(alias: str) -> bool:
    commands = load_commands()
    if alias not in commands:
        return False
    del commands[alias]
    save_commands(commands)
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
