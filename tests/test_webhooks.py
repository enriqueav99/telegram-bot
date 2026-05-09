"""Tests for webhook handlers."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from config import BotConfig, FeatureFlags
from handlers import webhooks

# ── helpers ───────────────────────────────────────────────────────────────────


def _bot_data(tmp_path, monkeypatch, features_on: list[str] = (), chat_id: int | None = 999):
    monkeypatch.setattr("config.FEATURES_FILE", tmp_path / "features.json")
    config = BotConfig(
        token="tok",
        allowed_users=frozenset(),
        alerts_port=9091,
        alerts_chat_id=chat_id,
        log_level="DEBUG",
    )
    flags = FeatureFlags()
    for f in features_on:
        if not flags.is_enabled(f):
            flags.toggle(f)
    bot = AsyncMock()
    bot.send_message = AsyncMock()
    return {"config": config, "features": flags, "bot": bot}, bot


def _req(body: dict, data: dict) -> MagicMock:
    r = MagicMock()
    r.app = {"bot_data": data}
    r.json = AsyncMock(return_value=body)
    return r


def _req_bad_json(data: dict) -> MagicMock:
    r = MagicMock()
    r.app = {"bot_data": data}
    r.json = AsyncMock(side_effect=ValueError("bad json"))
    return r


# ── alertmanager ──────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_alertmanager_disabled_returns_200_no_message(tmp_path, monkeypatch):
    data, bot = _bot_data(tmp_path, monkeypatch)  # alerts is False by default
    resp = await webhooks.alertmanager(_req({"alerts": []}, data))
    assert resp.status == 200
    bot.send_message.assert_not_called()


@pytest.mark.asyncio
async def test_alertmanager_no_chat_id_returns_200(tmp_path, monkeypatch):
    data, bot = _bot_data(tmp_path, monkeypatch, features_on=["alerts"], chat_id=None)
    resp = await webhooks.alertmanager(_req({"alerts": []}, data))
    assert resp.status == 200
    bot.send_message.assert_not_called()


@pytest.mark.asyncio
async def test_alertmanager_invalid_json_returns_400(tmp_path, monkeypatch):
    data, bot = _bot_data(tmp_path, monkeypatch, features_on=["alerts"])
    resp = await webhooks.alertmanager(_req_bad_json(data))
    assert resp.status == 400


@pytest.mark.asyncio
async def test_alertmanager_firing_sends_message(tmp_path, monkeypatch):
    data, bot = _bot_data(tmp_path, monkeypatch, features_on=["alerts"])
    payload = {
        "alerts": [
            {
                "status": "firing",
                "labels": {"alertname": "DiskFull", "severity": "critical"},
                "annotations": {"summary": "Disco lleno", "description": "Queda 1% libre"},
            }
        ]
    }
    resp = await webhooks.alertmanager(_req(payload, data))
    assert resp.status == 200
    bot.send_message.assert_awaited_once()
    text = bot.send_message.call_args.kwargs["text"]
    assert "DiskFull" in text
    assert "🔴" in text


@pytest.mark.asyncio
async def test_alertmanager_resolved_uses_green_icon(tmp_path, monkeypatch):
    data, bot = _bot_data(tmp_path, monkeypatch, features_on=["alerts"])
    payload = {
        "alerts": [{"status": "resolved", "labels": {"alertname": "Test"}, "annotations": {}}]
    }
    await webhooks.alertmanager(_req(payload, data))
    text = bot.send_message.call_args.kwargs["text"]
    assert "🟢" in text


# ── grafana ───────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_grafana_disabled_returns_200_no_message(tmp_path, monkeypatch):
    data, bot = _bot_data(tmp_path, monkeypatch)
    resp = await webhooks.grafana(_req({}, data))
    assert resp.status == 200
    bot.send_message.assert_not_called()


@pytest.mark.asyncio
async def test_grafana_unified_alerting_format(tmp_path, monkeypatch):
    data, bot = _bot_data(tmp_path, monkeypatch, features_on=["grafana"])
    payload = {
        "alerts": [
            {
                "status": "firing",
                "labels": {"alertname": "HighCPU", "severity": "warning"},
                "annotations": {"summary": "CPU al 95%"},
            }
        ]
    }
    resp = await webhooks.grafana(_req(payload, data))
    assert resp.status == 200
    text = bot.send_message.call_args.kwargs["text"]
    assert "📈" in text
    assert "HighCPU" in text


@pytest.mark.asyncio
async def test_grafana_legacy_format(tmp_path, monkeypatch):
    data, bot = _bot_data(tmp_path, monkeypatch, features_on=["grafana"])
    payload = {"title": "[FIRING] HighCPU", "state": "alerting", "message": "CPU above threshold"}
    resp = await webhooks.grafana(_req(payload, data))
    assert resp.status == 200
    text = bot.send_message.call_args.kwargs["text"]
    assert "📈" in text
    assert "🔴" in text


@pytest.mark.asyncio
async def test_grafana_invalid_json_returns_400(tmp_path, monkeypatch):
    data, _ = _bot_data(tmp_path, monkeypatch, features_on=["grafana"])
    resp = await webhooks.grafana(_req_bad_json(data))
    assert resp.status == 400


# ── radarr ────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_radarr_disabled_returns_200_no_message(tmp_path, monkeypatch):
    data, bot = _bot_data(tmp_path, monkeypatch)
    resp = await webhooks.radarr(_req({"eventType": "Grab"}, data))
    assert resp.status == 200
    bot.send_message.assert_not_called()


@pytest.mark.asyncio
async def test_radarr_test_event(tmp_path, monkeypatch):
    data, bot = _bot_data(tmp_path, monkeypatch, features_on=["radarr"])
    resp = await webhooks.radarr(_req({"eventType": "Test"}, data))
    assert resp.status == 200
    text = bot.send_message.call_args.kwargs["text"]
    assert "Radarr" in text


@pytest.mark.asyncio
async def test_radarr_grab_event(tmp_path, monkeypatch):
    data, bot = _bot_data(tmp_path, monkeypatch, features_on=["radarr"])
    payload = {
        "eventType": "Grab",
        "movie": {"title": "Inception", "year": 2010},
        "release": {"quality": "Bluray-1080p"},
    }
    resp = await webhooks.radarr(_req(payload, data))
    assert resp.status == 200
    text = bot.send_message.call_args.kwargs["text"]
    assert "Inception" in text
    assert "Bluray-1080p" in text


@pytest.mark.asyncio
async def test_radarr_download_event(tmp_path, monkeypatch):
    data, bot = _bot_data(tmp_path, monkeypatch, features_on=["radarr"])
    payload = {
        "eventType": "Download",
        "movie": {"title": "The Matrix", "year": 1999},
        "movieFile": {"quality": "Remux-1080p"},
        "isUpgrade": False,
    }
    resp = await webhooks.radarr(_req(payload, data))
    assert resp.status == 200
    text = bot.send_message.call_args.kwargs["text"]
    assert "Matrix" in text
    assert "✅" in text


@pytest.mark.asyncio
async def test_radarr_download_upgrade(tmp_path, monkeypatch):
    data, bot = _bot_data(tmp_path, monkeypatch, features_on=["radarr"])
    payload = {
        "eventType": "Download",
        "movie": {"title": "Dune", "year": 2021},
        "movieFile": {"quality": "Remux-2160p"},
        "isUpgrade": True,
    }
    await webhooks.radarr(_req(payload, data))
    text = bot.send_message.call_args.kwargs["text"]
    assert "⬆️" in text


@pytest.mark.asyncio
async def test_radarr_unknown_event_no_message(tmp_path, monkeypatch):
    data, bot = _bot_data(tmp_path, monkeypatch, features_on=["radarr"])
    resp = await webhooks.radarr(_req({"eventType": "HealthCheck"}, data))
    assert resp.status == 200
    bot.send_message.assert_not_called()


# ── sonarr ────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_sonarr_disabled_returns_200_no_message(tmp_path, monkeypatch):
    data, bot = _bot_data(tmp_path, monkeypatch)
    resp = await webhooks.sonarr(_req({"eventType": "Grab"}, data))
    assert resp.status == 200
    bot.send_message.assert_not_called()


@pytest.mark.asyncio
async def test_sonarr_test_event(tmp_path, monkeypatch):
    data, bot = _bot_data(tmp_path, monkeypatch, features_on=["sonarr"])
    resp = await webhooks.sonarr(_req({"eventType": "Test"}, data))
    assert resp.status == 200
    text = bot.send_message.call_args.kwargs["text"]
    assert "Sonarr" in text


@pytest.mark.asyncio
async def test_sonarr_grab_with_episode(tmp_path, monkeypatch):
    data, bot = _bot_data(tmp_path, monkeypatch, features_on=["sonarr"])
    payload = {
        "eventType": "Grab",
        "series": {"title": "Breaking Bad"},
        "episodes": [{"seasonNumber": 3, "episodeNumber": 7, "title": "One Minute"}],
        "release": {"quality": "HDTV-1080p"},
    }
    resp = await webhooks.sonarr(_req(payload, data))
    assert resp.status == 200
    text = bot.send_message.call_args.kwargs["text"]
    assert "Breaking Bad" in text
    assert "S03E07" in text


@pytest.mark.asyncio
async def test_sonarr_download_upgrade(tmp_path, monkeypatch):
    data, bot = _bot_data(tmp_path, monkeypatch, features_on=["sonarr"])
    payload = {
        "eventType": "Download",
        "series": {"title": "The Wire"},
        "episodes": [{"seasonNumber": 1, "episodeNumber": 1, "title": "The Target"}],
        "episodeFile": {"quality": "Bluray-1080p"},
        "isUpgrade": True,
    }
    await webhooks.sonarr(_req(payload, data))
    text = bot.send_message.call_args.kwargs["text"]
    assert "⬆️" in text
    assert "The Wire" in text


@pytest.mark.asyncio
async def test_sonarr_series_add(tmp_path, monkeypatch):
    data, bot = _bot_data(tmp_path, monkeypatch, features_on=["sonarr"])
    payload = {"eventType": "SeriesAdd", "series": {"title": "Chernobyl"}}
    await webhooks.sonarr(_req(payload, data))
    text = bot.send_message.call_args.kwargs["text"]
    assert "Chernobyl" in text


# ── crowdsec ──────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_crowdsec_disabled_returns_200_no_message(tmp_path, monkeypatch):
    data, bot = _bot_data(tmp_path, monkeypatch)
    resp = await webhooks.crowdsec(_req([], data))
    assert resp.status == 200
    bot.send_message.assert_not_called()


@pytest.mark.asyncio
async def test_crowdsec_list_format(tmp_path, monkeypatch):
    data, bot = _bot_data(tmp_path, monkeypatch, features_on=["crowdsec"])
    payload = [
        {
            "scenario": "crowdsecurity/ssh-bf",
            "source": {"ip": "1.2.3.4", "as_name": "Evil Corp"},
            "decisions": [{"type": "ban", "duration": "4h"}],
        }
    ]
    resp = await webhooks.crowdsec(_req(payload, data))
    assert resp.status == 200
    text = bot.send_message.call_args.kwargs["text"]
    assert "1.2.3.4" in text
    assert "ssh-bf" in text
    assert "ban" in text


@pytest.mark.asyncio
async def test_crowdsec_dict_format(tmp_path, monkeypatch):
    data, bot = _bot_data(tmp_path, monkeypatch, features_on=["crowdsec"])
    payload = {
        "alerts": [
            {
                "scenario": "crowdsecurity/http-crawl-non_statics",
                "source": {"ip": "5.6.7.8"},
                "decisions": [{"type": "ban", "duration": "24h"}],
            }
        ]
    }
    resp = await webhooks.crowdsec(_req(payload, data))
    assert resp.status == 200
    text = bot.send_message.call_args.kwargs["text"]
    assert "5.6.7.8" in text


@pytest.mark.asyncio
async def test_crowdsec_invalid_json_returns_400(tmp_path, monkeypatch):
    data, _ = _bot_data(tmp_path, monkeypatch, features_on=["crowdsec"])
    resp = await webhooks.crowdsec(_req_bad_json(data))
    assert resp.status == 400


@pytest.mark.asyncio
async def test_crowdsec_limits_flood_to_10(tmp_path, monkeypatch):
    data, bot = _bot_data(tmp_path, monkeypatch, features_on=["crowdsec"])
    payload = [
        {"scenario": "test/scenario", "source": {"ip": f"1.2.3.{i}"}, "decisions": []}
        for i in range(20)
    ]
    await webhooks.crowdsec(_req(payload, data))
    assert bot.send_message.await_count == 10
