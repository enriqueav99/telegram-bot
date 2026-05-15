from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from config import BotConfig, FeatureFlags
from handlers.auth import require_auth, require_module

# ── helpers ───────────────────────────────────────────────────────────────────


def _update(user_id: int = 111) -> MagicMock:
    upd = MagicMock()
    upd.effective_user.id = user_id
    upd.effective_message.reply_text = AsyncMock()
    return upd


def _context(config: BotConfig, features: FeatureFlags | None = None) -> MagicMock:
    ctx = MagicMock()
    ctx.bot_data = {"config": config, "features": features}
    return ctx


def _config(allowed: frozenset[int] = frozenset([111])) -> BotConfig:
    return BotConfig(
        token="tok",
        allowed_users=allowed,
        alerts_port=9091,
        alerts_chat_id=None,
        log_level="DEBUG",
        github_token="",
        github_repo="",
        prometheus_url="",
    )


# ── require_auth ──────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_require_auth_allowed_user_passes():
    called = False

    @require_auth
    async def handler(update, context):
        nonlocal called
        called = True

    await handler(_update(111), _context(_config(frozenset([111]))))
    assert called


@pytest.mark.asyncio
async def test_require_auth_denied_user_blocked():
    called = False

    @require_auth
    async def handler(update, context):
        nonlocal called
        called = True

    upd = _update(999)
    await handler(upd, _context(_config(frozenset([111]))))
    assert not called
    upd.effective_message.reply_text.assert_awaited_once()
    msg = upd.effective_message.reply_text.call_args[0][0]
    assert "permiso" in msg.lower() or "⛔" in msg


@pytest.mark.asyncio
async def test_require_auth_empty_whitelist_allows_all():
    """Sin whitelist configurada cualquier usuario puede usar el bot."""
    called = False

    @require_auth
    async def handler(update, context):
        nonlocal called
        called = True

    await handler(_update(999), _context(_config(frozenset())))
    assert called


@pytest.mark.asyncio
async def test_require_auth_preserves_return_value():
    @require_auth
    async def handler(update, context):
        return 42

    result = await handler(_update(111), _context(_config()))
    assert result == 42


# ── require_module ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_require_module_enabled_passes(tmp_path, monkeypatch):
    monkeypatch.setattr("config.FEATURES_FILE", tmp_path / "f.json")
    features = FeatureFlags()
    called = False

    @require_module("docker")
    async def handler(update, context):
        nonlocal called
        called = True

    upd = _update(111)
    ctx = _context(_config(), features)
    await handler(upd, ctx)
    assert called


@pytest.mark.asyncio
async def test_require_module_disabled_blocks(tmp_path, monkeypatch):
    monkeypatch.setattr("config.FEATURES_FILE", tmp_path / "f.json")
    features = FeatureFlags()
    features.toggle("docker")  # docker arranca True, ahora False
    called = False

    @require_module("docker")
    async def handler(update, context):
        nonlocal called
        called = True

    upd = _update(111)
    ctx = _context(_config(), features)
    await handler(upd, ctx)
    assert not called
    upd.effective_message.reply_text.assert_awaited_once()


@pytest.mark.asyncio
async def test_require_module_disabled_message_mentions_panel(tmp_path, monkeypatch):
    monkeypatch.setattr("config.FEATURES_FILE", tmp_path / "f.json")
    features = FeatureFlags()
    features.toggle("system")  # system arranca True, ahora False

    @require_module("system")
    async def handler(update, context):
        pass

    upd = _update(111)
    ctx = _context(_config(), features)
    await handler(upd, ctx)
    msg = upd.effective_message.reply_text.call_args[0][0]
    assert "/panel" in msg
