from __future__ import annotations

import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

HISTORY_FILE = Path("data/claude_history.json")
MAX_HISTORY = 20  # mensajes totales por chat (10 turnos aprox.)
SHELL_TIMEOUT = 30
SHELL_OUTPUT_LIMIT = 3500


class ClaudeClient:
    def __init__(self) -> None:
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if api_key:
            import anthropic

            self._client: anthropic.AsyncAnthropic | None = anthropic.AsyncAnthropic(
                api_key=api_key
            )
        else:
            self._client = None
        self._history: dict[str, list[dict]] = self._load()

    @property
    def available(self) -> bool:
        return self._client is not None

    def _load(self) -> dict[str, list[dict]]:
        HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
        if HISTORY_FILE.exists():
            try:
                return json.loads(HISTORY_FILE.read_text())
            except Exception:
                return {}
        return {}

    def _save(self) -> None:
        HISTORY_FILE.write_text(json.dumps(self._history, indent=2, ensure_ascii=False))

    def reset(self, chat_id: str) -> None:
        self._history.pop(chat_id, None)
        self._save()

    async def _run_shell(self, command: str) -> str:
        try:
            proc = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=SHELL_TIMEOUT)
            output = stdout.decode(errors="replace")
            if len(output) > SHELL_OUTPUT_LIMIT:
                output = output[:SHELL_OUTPUT_LIMIT] + "\n... (salida truncada)"
            return output or "(sin salida)"
        except TimeoutError:
            return f"Error: comando superó el límite de {SHELL_TIMEOUT}s"
        except Exception as e:
            return f"Error: {e}"

    def _serialize_content(self, content: Any) -> Any:
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            return [
                block.model_dump() if hasattr(block, "model_dump") else block for block in content
            ]
        return content

    async def chat(self, chat_id: str, message: str) -> str:
        if not self._client:
            return "❌ ANTHROPIC_API_KEY no está configurada."

        history = list(self._history.get(chat_id, []))
        history.append({"role": "user", "content": message})

        tools = [
            {
                "name": "shell",
                "description": (
                    "Ejecuta un comando bash en el servidor Linux del homelab. "
                    "Útil para consultar estado del sistema, archivos, procesos, logs, etc."
                ),
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "command": {"type": "string", "description": "Comando bash a ejecutar"}
                    },
                    "required": ["command"],
                },
            }
        ]

        try:
            while True:
                response = await self._client.messages.create(
                    model="claude-sonnet-4-6",
                    max_tokens=1024,
                    system=(
                        "Eres un asistente personal de homelab. "
                        "Tienes acceso a la herramienta shell para ejecutar comandos en el servidor Linux. "
                        "Úsala cuando el usuario te pida información del sistema o quiera ejecutar algo. "
                        "Responde siempre en el mismo idioma que el usuario. "
                        "Sé conciso."
                    ),
                    messages=history,
                    tools=tools,
                )

                history.append(
                    {"role": "assistant", "content": self._serialize_content(response.content)}
                )

                if response.stop_reason == "tool_use":
                    tool_results = []
                    for block in response.content:
                        if block.type == "tool_use":
                            log.info("Claude shell: %s", block.input.get("command", ""))
                            result = await self._run_shell(block.input["command"])
                            tool_results.append(
                                {
                                    "type": "tool_result",
                                    "tool_use_id": block.id,
                                    "content": result,
                                }
                            )
                    history.append({"role": "user", "content": tool_results})
                else:
                    break

        except Exception as e:
            log.exception("Error en Claude API")
            return f"❌ Error al contactar con Claude: {e}"

        if len(history) > MAX_HISTORY:
            history = history[-MAX_HISTORY:]

        self._history[chat_id] = history
        self._save()

        text_parts = [b.text for b in response.content if hasattr(b, "text") and b.text]
        return "\n".join(text_parts) or "_(sin respuesta)_"
