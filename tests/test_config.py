from __future__ import annotations

import json

import pytest

from config import DEFAULT_FEATURES, BotConfig, FeatureFlags

# ── BotConfig ──────────────────────────────────────────────────────────────────


def test_config_loads_from_env(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "tok123")
    monkeypatch.setenv("ALLOWED_USERS", "111,222")
    monkeypatch.setenv("ALERTS_PORT", "9999")
    monkeypatch.setenv("ALERTS_CHAT_ID", "555")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")

    cfg = BotConfig.load()

    assert cfg.token == "tok123"
    assert cfg.allowed_users == frozenset([111, 222])
    assert cfg.alerts_port == 9999
    assert cfg.alerts_chat_id == 555
    assert cfg.log_level == "DEBUG"


def test_config_missing_token_raises(monkeypatch):
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    with pytest.raises(RuntimeError, match="TELEGRAM_BOT_TOKEN"):
        BotConfig.load()


def test_config_empty_allowed_users(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "tok")
    monkeypatch.setenv("ALLOWED_USERS", "")
    cfg = BotConfig.load()
    assert cfg.allowed_users == frozenset()


def test_config_allowed_users_strips_whitespace(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "tok")
    monkeypatch.setenv("ALLOWED_USERS", " 1 , 2 , 3 ")
    cfg = BotConfig.load()
    assert cfg.allowed_users == frozenset([1, 2, 3])


def test_config_alerts_chat_id_optional(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "tok")
    monkeypatch.delenv("ALERTS_CHAT_ID", raising=False)
    cfg = BotConfig.load()
    assert cfg.alerts_chat_id is None


def test_config_default_alerts_port(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "tok")
    monkeypatch.delenv("ALERTS_PORT", raising=False)
    cfg = BotConfig.load()
    assert cfg.alerts_port == 9091


# ── FeatureFlags ───────────────────────────────────────────────────────────────


def test_feature_flags_start_with_defaults(tmp_path, monkeypatch):
    monkeypatch.setattr("config.FEATURES_FILE", tmp_path / "features.json")
    flags = FeatureFlags()
    assert flags.all() == DEFAULT_FEATURES


def test_feature_flags_toggle_changes_state(tmp_path, monkeypatch):
    monkeypatch.setattr("config.FEATURES_FILE", tmp_path / "features.json")
    flags = FeatureFlags()
    original = flags.is_enabled("docker")
    new = flags.toggle("docker")
    assert new != original
    assert flags.is_enabled("docker") == new


def test_feature_flags_persists_to_disk(tmp_path, monkeypatch):
    path = tmp_path / "features.json"
    monkeypatch.setattr("config.FEATURES_FILE", path)
    flags = FeatureFlags()
    flags.toggle("alerts")
    saved = json.loads(path.read_text())
    assert saved["alerts"] == flags.is_enabled("alerts")


def test_feature_flags_loads_from_existing_file(tmp_path, monkeypatch):
    path = tmp_path / "features.json"
    path.write_text(json.dumps({"docker": False, "system": True, "alerts": True}))
    monkeypatch.setattr("config.FEATURES_FILE", path)
    flags = FeatureFlags()
    assert flags.is_enabled("docker") is False
    assert flags.is_enabled("alerts") is True


def test_feature_flags_merges_missing_defaults(tmp_path, monkeypatch):
    """Un archivo con solo algunas features no pierde las que faltan."""
    path = tmp_path / "features.json"
    path.write_text(json.dumps({"docker": False}))
    monkeypatch.setattr("config.FEATURES_FILE", path)
    flags = FeatureFlags()
    assert "system" in flags.all()
    assert "alerts" in flags.all()


def test_feature_flags_toggle_unknown_raises(tmp_path, monkeypatch):
    monkeypatch.setattr("config.FEATURES_FILE", tmp_path / "features.json")
    flags = FeatureFlags()
    with pytest.raises(ValueError, match="desconocida"):
        flags.toggle("nonexistent")
