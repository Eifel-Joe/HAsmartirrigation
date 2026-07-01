"""Master switch / pump control."""

import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

from custom_components.smart_irrigation.master import MasterMixin
from custom_components.smart_irrigation.store import (
    STORAGE_VERSION,
    Config,
    async_get_registry,
)


class _MasterHost(MasterMixin):
    """Minimal host to unit-test the mixin in isolation."""


def _mcoord(**master_cfg):
    c = _MasterHost()
    c.hass = Mock()
    c.hass.services.async_call = AsyncMock()
    c.store = Mock()
    c.store.config = SimpleNamespace(
        master_entity=master_cfg.get("master_entity", "switch.pump"),
        master_settle_seconds=master_cfg.get("master_settle_seconds", 10),
        master_kick_enabled=master_cfg.get("master_kick_enabled", False),
        master_kick_pause_seconds=master_cfg.get("master_kick_pause_seconds", 1.0),
        master_off_after=master_cfg.get("master_off_after", False),
    )
    # Isolate the real sleep; record the requested delays instead.
    c._master_sleep = AsyncMock()
    return c


def test_storage_version_is_11():
    assert STORAGE_VERSION == 11


def test_config_has_master_defaults():
    c = Config()
    assert c.master_entity is None
    assert c.master_settle_seconds == 10
    assert c.master_kick_enabled is False
    assert c.master_kick_pause_seconds == 1.0
    assert c.master_off_after is False


async def test_migration_seeds_master_defaults(hass):
    reg = await async_get_registry(hass)
    data = {"config": {}, "zones": []}
    await reg._store._async_migrate_func(10, data)
    cfg = data["config"]
    assert cfg["master_entity"] is None
    assert cfg["master_settle_seconds"] == 10
    assert cfg["master_kick_enabled"] is False
    assert cfg["master_kick_pause_seconds"] == 1.0
    assert cfg["master_off_after"] is False


async def test_master_begin_turns_on_and_settles():
    c = _mcoord()
    await c.async_master_begin_cycle()
    c.hass.services.async_call.assert_awaited_once_with(
        "homeassistant", "turn_on", {"entity_id": "switch.pump"}
    )
    c._master_sleep.assert_awaited_once_with(10)
    assert c._master_on is True


async def test_master_kick_pulses_off_then_on():
    c = _mcoord(
        master_kick_enabled=True, master_kick_pause_seconds=1.0, master_settle_seconds=5
    )
    await c.async_master_begin_cycle()
    calls = [ck.args for ck in c.hass.services.async_call.await_args_list]
    assert calls[0] == ("homeassistant", "turn_off", {"entity_id": "switch.pump"})
    assert calls[1] == ("homeassistant", "turn_on", {"entity_id": "switch.pump"})
    sleeps = [s.args[0] for s in c._master_sleep.await_args_list]
    assert sleeps == [1.0, 5]  # kick pause, then settle


async def test_master_not_configured_is_noop():
    c = _mcoord(master_entity=None)
    await c.async_master_begin_cycle()
    c.hass.services.async_call.assert_not_awaited()


async def test_master_begin_idempotent_while_on():
    c = _mcoord()
    await c.async_master_begin_cycle()
    c.hass.services.async_call.reset_mock()
    c._master_sleep.reset_mock()
    await c.async_master_begin_cycle()  # already on
    c.hass.services.async_call.assert_not_awaited()
    c._master_sleep.assert_not_awaited()


def test_master_note_run_keeps_latest_deadline():
    c = _mcoord(master_off_after=True)
    t0 = datetime.datetime(2026, 7, 1, 8, 0, 0, tzinfo=datetime.timezone.utc)
    c._master_now = Mock(return_value=t0)
    c._master_note_run(60)
    c._master_note_run(600)
    c._master_note_run(120)  # shorter must not shrink the deadline
    assert c._master_off_deadline == t0 + datetime.timedelta(seconds=600)


async def test_master_off_disabled_never_arms(monkeypatch):
    c = _mcoord(master_off_after=False)
    armed = []
    monkeypatch.setattr(
        "custom_components.smart_irrigation.master.async_call_later",
        lambda *a, **k: armed.append(a) or Mock(),
    )
    c._master_note_run(60)
    await c.async_master_schedule_off()
    assert armed == []


async def test_master_off_enabled_arms_and_fires(monkeypatch):
    c = _mcoord(master_off_after=True)
    captured = {}

    def fake_later(hass, delay, cb):
        captured["delay"] = delay
        captured["cb"] = cb
        return Mock()

    monkeypatch.setattr(
        "custom_components.smart_irrigation.master.async_call_later", fake_later
    )
    t0 = datetime.datetime(2026, 7, 1, 8, 0, 0, tzinfo=datetime.timezone.utc)
    c._master_now = Mock(return_value=t0)
    c._master_on = True
    c._master_note_run(60)
    await c.async_master_schedule_off()
    assert 59 <= captured["delay"] <= 61

    # deadline passed -> firing turns the master off
    c._master_now = Mock(return_value=t0 + datetime.timedelta(seconds=61))
    await captured["cb"](None)
    c.hass.services.async_call.assert_awaited_with(
        "homeassistant", "turn_off", {"entity_id": "switch.pump"}
    )
    assert c._master_on is False
