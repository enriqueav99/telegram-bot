"""Fixtures compartidos para todos los tests."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from config import BotConfig, FeatureFlags


@pytest.fixture()
def bot_config() -> BotConfig:
    return BotConfig(
        token="test-token",
        allowed_users=frozenset([111, 222]),
        alerts_port=9091,
        alerts_chat_id=None,
        log_level="DEBUG",
    )


@pytest.fixture()
def feature_flags(tmp_path, monkeypatch) -> FeatureFlags:
    monkeypatch.setattr("config.FEATURES_FILE", tmp_path / "features.json")
    return FeatureFlags()


@pytest.fixture()
def mock_update() -> MagicMock:
    update = MagicMock()
    update.effective_user.id = 111
    update.effective_user.first_name = "Test"
    update.effective_message.reply_text = AsyncMock()
    update.message = update.effective_message
    return update


@pytest.fixture()
def mock_context(bot_config, feature_flags) -> MagicMock:
    context = MagicMock()
    context.bot_data = {
        "config": bot_config,
        "features": feature_flags,
    }
    return context
