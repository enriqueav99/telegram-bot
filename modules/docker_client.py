from __future__ import annotations

import logging
from dataclasses import dataclass

log = logging.getLogger(__name__)

try:
    import docker
    from docker.errors import DockerException, NotFound, APIError

    _DOCKER_AVAILABLE = True
except ImportError:
    _DOCKER_AVAILABLE = False


STATUS_EMOJI = {
    "running": "🟢",
    "exited": "🔴",
    "paused": "🟡",
    "restarting": "🔄",
    "dead": "💀",
    "created": "🔵",
}


@dataclass
class ContainerInfo:
    name: str
    status: str
    image: str
    emoji: str


class DockerClient:
    def __init__(self) -> None:
        self._client: docker.DockerClient | None = None
        if _DOCKER_AVAILABLE:
            try:
                self._client = docker.from_env()
                self._client.ping()
                log.info("Conexión con Docker establecida")
            except Exception as e:
                log.warning("No se pudo conectar con Docker: %s", e)
                self._client = None

    @property
    def available(self) -> bool:
        return self._client is not None

    def list_containers(self, all: bool = True) -> list[ContainerInfo]:
        if not self._client:
            return []
        try:
            containers = self._client.containers.list(all=all)
            return [
                ContainerInfo(
                    name=c.name,
                    status=c.status,
                    image=c.image.tags[0] if c.image.tags else c.image.short_id,
                    emoji=STATUS_EMOJI.get(c.status, "❓"),
                )
                for c in sorted(containers, key=lambda c: c.name)
            ]
        except Exception as e:
            log.error("Error listando contenedores: %s", e)
            return []

    def get_container(self, name: str):
        if not self._client:
            return None
        try:
            return self._client.containers.get(name)
        except Exception:
            return None

    def start(self, name: str) -> str:
        c = self.get_container(name)
        if not c:
            return f"❌ Contenedor `{name}` no encontrado"
        try:
            c.start()
            return f"✅ `{name}` iniciado"
        except Exception as e:
            return f"❌ Error al iniciar `{name}`: {e}"

    def stop(self, name: str) -> str:
        c = self.get_container(name)
        if not c:
            return f"❌ Contenedor `{name}` no encontrado"
        try:
            c.stop(timeout=10)
            return f"⏹️ `{name}` detenido"
        except Exception as e:
            return f"❌ Error al detener `{name}`: {e}"

    def restart(self, name: str) -> str:
        c = self.get_container(name)
        if not c:
            return f"❌ Contenedor `{name}` no encontrado"
        try:
            c.restart(timeout=10)
            return f"🔄 `{name}` reiniciado"
        except Exception as e:
            return f"❌ Error al reiniciar `{name}`: {e}"

    def logs(self, name: str, lines: int = 30) -> str:
        c = self.get_container(name)
        if not c:
            return f"❌ Contenedor `{name}` no encontrado"
        try:
            raw = c.logs(tail=lines, timestamps=True).decode("utf-8", errors="replace")
            return raw.strip() or "(sin logs)"
        except Exception as e:
            return f"❌ Error obteniendo logs de `{name}`: {e}"

    def running_count(self) -> tuple[int, int]:
        """Returns (running, total)."""
        containers = self.list_containers(all=True)
        running = sum(1 for c in containers if c.status == "running")
        return running, len(containers)
