from __future__ import annotations

from unittest.mock import MagicMock, patch

from modules.docker_client import STATUS_EMOJI, DockerClient


def _make_client(containers: list | None = None, ping_ok: bool = True) -> DockerClient:
    """Devuelve un DockerClient con Docker SDK mockeado."""
    mock_sdk = MagicMock()
    if ping_ok:
        mock_sdk.ping.return_value = True
    else:
        mock_sdk.ping.side_effect = Exception("no socket")

    if containers is not None:
        mock_sdk.containers.list.return_value = containers

    with patch("modules.docker_client.docker") as mock_docker_mod:
        mock_docker_mod.from_env.return_value = mock_sdk
        client = DockerClient()
    client._client = mock_sdk if ping_ok else None
    return client


def _make_container(name: str, status: str = "running", tags: list[str] | None = None):
    c = MagicMock()
    c.name = name
    c.status = status
    c.image.tags = tags or [f"image/{name}:latest"]
    c.image.short_id = f"sha256:{name[:6]}"
    return c


# ── available ─────────────────────────────────────────────────────────────────


def test_available_when_ping_succeeds():
    client = _make_client(ping_ok=True)
    assert client.available is True


def test_unavailable_when_ping_fails():
    client = _make_client(ping_ok=False)
    assert client.available is False


# ── list_containers ───────────────────────────────────────────────────────────


def test_list_containers_empty():
    client = _make_client(containers=[])
    assert client.list_containers() == []


def test_list_containers_returns_info():
    c = _make_container("plex", "running")
    client = _make_client(containers=[c])
    result = client.list_containers()
    assert len(result) == 1
    assert result[0].name == "plex"
    assert result[0].status == "running"
    assert result[0].emoji == STATUS_EMOJI["running"]


def test_list_containers_sorted_by_name():
    cs = [_make_container("zebra"), _make_container("alpha"), _make_container("mango")]
    client = _make_client(containers=cs)
    names = [c.name for c in client.list_containers()]
    assert names == sorted(names)


def test_list_containers_unknown_status_emoji():
    c = _make_container("weird", status="unknown_status")
    client = _make_client(containers=[c])
    result = client.list_containers()
    assert result[0].emoji == "❓"


def test_list_containers_returns_empty_when_unavailable():
    client = _make_client(ping_ok=False)
    assert client.list_containers() == []


# ── running_count ─────────────────────────────────────────────────────────────


def test_running_count_mixed():
    cs = [
        _make_container("a", "running"),
        _make_container("b", "exited"),
        _make_container("c", "running"),
    ]
    client = _make_client(containers=cs)
    running, total = client.running_count()
    assert running == 2
    assert total == 3


def test_running_count_all_stopped():
    cs = [_make_container("a", "exited"), _make_container("b", "exited")]
    client = _make_client(containers=cs)
    running, total = client.running_count()
    assert running == 0
    assert total == 2


# ── start / stop / restart ────────────────────────────────────────────────────


def test_start_calls_container_start():
    c = _make_container("nginx", "exited")
    client = _make_client()
    client._client.containers.get.return_value = c
    result = client.start("nginx")
    c.start.assert_called_once()
    assert "nginx" in result
    assert "✅" in result


def test_stop_calls_container_stop():
    c = _make_container("nginx", "running")
    client = _make_client()
    client._client.containers.get.return_value = c
    result = client.stop("nginx")
    c.stop.assert_called_once()
    assert "⏹️" in result


def test_restart_calls_container_restart():
    c = _make_container("nginx", "running")
    client = _make_client()
    client._client.containers.get.return_value = c
    result = client.restart("nginx")
    c.restart.assert_called_once()
    assert "🔄" in result


def test_start_not_found_returns_error():
    client = _make_client()
    client._client.containers.get.return_value = None
    result = client.start("nonexistent")
    assert "❌" in result
    assert "nonexistent" in result


def test_stop_docker_error_returns_error():
    c = _make_container("nginx", "running")
    c.stop.side_effect = Exception("timeout")
    client = _make_client()
    client._client.containers.get.return_value = c
    result = client.stop("nginx")
    assert "❌" in result


# ── logs ──────────────────────────────────────────────────────────────────────


def test_logs_returns_decoded_text():
    c = _make_container("app")
    c.logs.return_value = b"line1\nline2\nline3"
    client = _make_client()
    client._client.containers.get.return_value = c
    result = client.logs("app", lines=10)
    assert "line1" in result
    assert "line2" in result


def test_logs_not_found_returns_error():
    client = _make_client()
    client._client.containers.get.return_value = None
    result = client.logs("missing")
    assert "❌" in result


def test_logs_empty_shows_placeholder():
    c = _make_container("app")
    c.logs.return_value = b""
    client = _make_client()
    client._client.containers.get.return_value = c
    result = client.logs("app")
    assert result == "(sin logs)"
