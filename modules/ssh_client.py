from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

COMMANDS_FILE = Path("data/ssh_commands.json")


@dataclass
class SSHConfig:
    host: str
    user: str
    key_path: str | None

    @classmethod
    def load(cls) -> SSHConfig:
        return cls(
            host=os.getenv("SSH_HOST", ""),
            user=os.getenv("SSH_USER", "root"),
            key_path=os.getenv("SSH_KEY_PATH"),
        )

    @property
    def available(self) -> bool:
        return bool(self.host)


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


async def run(config: SSHConfig, command: str) -> tuple[str, str, int]:
    import asyncssh  # noqa: PLC0415

    keys = [config.key_path] if config.key_path else ()
    async with asyncssh.connect(
        config.host,
        username=config.user,
        client_keys=keys,
        known_hosts=None,
    ) as conn:
        result = await conn.run(command, check=False)
        return result.stdout or "", result.stderr or "", result.exit_status or 0
