"""Weather-sensor liveness in the coordinator: states, registry, ledger, notice, event."""

import ast
import copy
import pathlib
from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import pytest
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.irrigation_plus import (
    SmartIrrigationCoordinator,
    const,
    sensor_liveness,
)
from custom_components.irrigation_plus.sensor_liveness import (
    Outage,
    _entities_of_device,
    seen_from_state,
)

T0 = datetime(2026, 7, 1, 12, 0, 0)  # naive, on HA's clock


def _aware(local_naive):
    """A naive HA-local wall time as Home Assistant stamps states: aware, in UTC."""
    return dt_util.as_utc(local_naive.replace(tzinfo=dt_util.get_default_time_zone()))


def _state(entity_id, value, reported, changed=None):
    return SimpleNamespace(
        entity_id=entity_id,
        state=value,
        last_reported=_aware(reported),
        last_changed=_aware(changed if changed is not None else reported),
    )


class TestSeenFromState:
    def test_state_stamps_land_on_has_clock(self):
        # Tripwire: the scene only proves the conversion if UTC differs from HA's
        # zone here (the autouse hass fixture puts HA on US/Pacific).
        assert _aware(T0).replace(tzinfo=None) != T0
        seen = seen_from_state(
            _state("sensor.t", "21.5", T0, changed=T0 - timedelta(hours=1))
        )
        assert seen.reported == T0
        assert seen.changed == T0 - timedelta(hours=1)
        assert seen.valid is True

    @pytest.mark.parametrize("value", ["unavailable", "unknown"])
    def test_unavailable_and_unknown_are_not_valid(self, value):
        assert seen_from_state(_state("sensor.t", value, T0)).valid is False

    def test_no_state_is_no_snapshot(self):
        assert seen_from_state(None) is None


async def test_the_device_is_read_from_the_entity_registry(hass):
    entry = MockConfigEntry(domain="test")
    entry.add_to_hass(hass)
    device = dr.async_get(hass).async_get_or_create(
        config_entry_id=entry.entry_id, identifiers={("test", "station")}
    )
    registry = er.async_get(hass)
    temp = registry.async_get_or_create(
        "sensor", "test", "temp", device_id=device.id, config_entry=entry
    )
    rain = registry.async_get_or_create(
        "sensor", "test", "rain", device_id=device.id, config_entry=entry
    )
    loose = registry.async_get_or_create("sensor", "test", "loose", config_entry=entry)

    assert _entities_of_device(hass, temp.entity_id) == (device.id, [rain.entity_id])
    assert _entities_of_device(hass, loose.entity_id) == (None, [])
    assert _entities_of_device(hass, "sensor.not_registered") == (None, [])
