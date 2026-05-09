from __future__ import annotations

import asyncio
from unittest.mock import MagicMock, patch

import pytest

from modules.goose_client import _split, _strip_ansi, available, run

# ── _strip_ansi ────────────────────────────────────────────────────────────────


def test_strip_ansi_removes_color_codes():
    assert _strip_ansi("\x1b[32mhello\x1b[0m") == "hello"


def test_strip_ansi_passthrough_plain():
    assert _strip_ansi("hello world") == "hello world"


def test_strip_ansi_removes_multiple_sequences():
    assert _strip_ansi("\x1b[1m\x1b[31mred bold\x1b[0m") == "red bold"


# ── _split ─────────────────────────────────────────────────────────────────────


def test_split_short_text_single_chunk():
    assert _split("hello", size=100) == ["hello"]


def test_split_long_text_breaks_at_newline():
    text = "line1\nline2\nline3"
    chunks = _split(text, size=12)
    assert len(chunks) > 1
    for chunk in chunks:
        assert len(chunk) <= 12


def test_split_no_newline_breaks_at_size():
    text = "a" * 20
    chunks = _split(text, size=10)
    for chunk in chunks:
        assert len(chunk) <= 10


def test_split_rejoins_to_original():
    text = "line1\nline2\nline3\nline4"
    chunks = _split(text, size=12)
    rejoined = "\n".join(chunks)
    assert "line1" in rejoined
    assert "line4" in rejoined


# ── available ──────────────────────────────────────────────────────────────────


def test_available_true_when_goose_in_path():
    with patch("modules.goose_client.shutil.which", return_value="/usr/bin/goose"):
        assert available() is True


def test_available_false_when_not_in_path():
    with patch("modules.goose_client.shutil.which", return_value=None):
        assert available() is False


# ── run ────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_run_returns_error_when_goose_missing():
    with patch("modules.goose_client.shutil.which", return_value=None):
        result = await run("hola")
    assert "❌" in result
    assert "goose" in result.lower()


@pytest.mark.asyncio
async def test_run_returns_stdout():
    with patch("modules.goose_client.shutil.which", return_value="/usr/bin/goose"):
        mock_proc = _mock_proc(stdout=b"respuesta de goose", stderr=b"")
        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            result = await run("hola")
    assert result == "respuesta de goose"


@pytest.mark.asyncio
async def test_run_falls_back_to_stderr_when_stdout_empty():
    with patch("modules.goose_client.shutil.which", return_value="/usr/bin/goose"):
        mock_proc = _mock_proc(stdout=b"", stderr=b"error info")
        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            result = await run("hola")
    assert result == "error info"


@pytest.mark.asyncio
async def test_run_strips_ansi_from_output():
    with patch("modules.goose_client.shutil.which", return_value="/usr/bin/goose"):
        mock_proc = _mock_proc(stdout=b"\x1b[32mok\x1b[0m", stderr=b"")
        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            result = await run("hola")
    assert result == "ok"


@pytest.mark.asyncio
async def test_run_returns_timeout_message():
    with patch("modules.goose_client.shutil.which", return_value="/usr/bin/goose"):
        mock_proc = _mock_proc(stdout=b"", stderr=b"", delay=10)
        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            result = await run("hola", timeout=0)
    assert "⏱️" in result


@pytest.mark.asyncio
async def test_run_returns_placeholder_when_no_output():
    with patch("modules.goose_client.shutil.which", return_value="/usr/bin/goose"):
        mock_proc = _mock_proc(stdout=b"", stderr=b"")
        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            result = await run("hola")
    assert result == "(sin respuesta)"


# ── helpers ───────────────────────────────────────────────────────────────────


def _mock_proc(stdout: bytes, stderr: bytes, delay: float = 0):
    proc = MagicMock()
    proc.kill = MagicMock()

    async def communicate():
        if delay:
            await asyncio.sleep(delay)
        return stdout, stderr

    proc.communicate = communicate
    return proc
