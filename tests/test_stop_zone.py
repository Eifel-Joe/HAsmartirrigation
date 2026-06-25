"""Tests for the Stop action (issue #36 follow-up).

``async_stop_zone`` interrupts an in-progress run immediately: it sets the run's
stop event (so the metered/rotating loop breaks, commits the water delivered so
far and logs a *partial* run) and turns the linked valve off directly as a
safety net. ``get_active_runs`` exposes the in-progress runs (with a countdown
end for time-bounded runs) so the dashboard can show a Stop control + countdown.

Coordinators are built with ``__new__`` so only the touched attributes are wired.
"""

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

from homeassistant.util.unit_system import METRIC_SYSTEM

from custom_components.smart_irrigation import SmartIrrigationCoordinator, const


class _FakeStore:
    def __init__(self, zones=None):
        self.zones = {int(z[const.ZONE_ID]): dict(z) for z in (zones or [])}
        self.config = SimpleNamespace(
            zone_sequencing=const.CONF_ZONE_SEQUENCING_PARALLEL
        )

    def get_zone(self, zone_id):
        z = self.zones.get(int(zone_id))
        return dict(z) if z is not None else None

    async def async_update_zone(self, zone_id, changes):
        self.zones.setdefault(int(zone_id), {const.ZONE_ID: int(zone_id)}).update(
            changes
        )
        return dict(self.zones[int(zone_id)])

    async def async_get_zones(self):
        return [dict(z) for z in self.zones.values()]


def _coord(monkeypatch, zones=None, units=METRIC_SYSTEM):
    monkeypatch.setattr(
        "custom_components.smart_irrigation.irrigation.async_dispatcher_send", Mock()
    )
    coord = SmartIrrigationCoordinator.__new__(SmartIrrigationCoordinator)
    hass = Mock()
    hass.config = Mock()
    hass.config.units = units
    hass.loop = asyncio.get_event_loop()
    hass.services = Mock()
    hass.services.async_call = AsyncMock()
    hass.states = Mock()
    coord.hass = hass
    coord.store = _FakeStore(zones)
    return coord


def _zone(**over):
    z = {
        const.ZONE_ID: 1,
        const.ZONE_NAME: "Lawn",
        const.ZONE_LINKED_ENTITY: "switch.valve",
        const.ZONE_STATE: const.ZONE_STATE_AUTOMATIC,
        const.ZONE_DURATION: 300,
        const.ZONE_BUCKET: -2.0,
        const.ZONE_RUN_LOG: [],
    }
    z.update(over)
    return z


# --------------------------------------------------------------------------- #
# active-run registry
# --------------------------------------------------------------------------- #
def test_register_active_run_exposes_countdown_end(monkeypatch):
    coord = _coord(monkeypatch, zones=[_zone()])
    coord._register_active_run(1, 600, has_end=True)
    runs = coord.get_active_runs()
    assert "1" in runs
    assert runs["1"]["ends_at"] is not None  # time-bounded → countdown
    assert runs["1"]["started_at"] is not None


def test_flow_run_has_no_countdown_end(monkeypatch):
    coord = _coord(monkeypatch, zones=[_zone()])
    coord._register_active_run(1, 0, has_end=False)
    assert coord.get_active_runs()["1"]["ends_at"] is None


def test_unregister_active_run_clears_marker(monkeypatch):
    coord = _coord(monkeypatch, zones=[_zone()])
    coord._register_active_run(1, 600, has_end=True)
    coord._unregister_active_run(1)
    assert coord.get_active_runs() == {}


# --------------------------------------------------------------------------- #
# async_stop_zone
# --------------------------------------------------------------------------- #
async def test_stop_zone_sets_event_and_turns_off(monkeypatch):
    coord = _coord(monkeypatch, zones=[_zone()])
    event = coord._register_active_run(1, 600, has_end=True)

    await coord.async_stop_zone(1)

    assert event.is_set()  # loop will notice and finish the run
    coord.hass.services.async_call.assert_awaited_once_with(
        "switch", "turn_off", {"entity_id": "switch.valve"}
    )


async def test_stop_zone_without_tracked_run_still_turns_off(monkeypatch):
    """Safety net: an untracked valve (e.g. opened pre-restart) is still closed."""
    coord = _coord(monkeypatch, zones=[_zone()])
    await coord.async_stop_zone(1)
    coord.hass.services.async_call.assert_awaited_once_with(
        "switch", "turn_off", {"entity_id": "switch.valve"}
    )


async def test_stop_all_zones_stops_each(monkeypatch):
    coord = _coord(
        monkeypatch,
        zones=[
            _zone(),
            _zone(**{const.ZONE_ID: 2, const.ZONE_LINKED_ENTITY: "switch.v2"}),
        ],
    )
    e1 = coord._register_active_run(1, 600, has_end=True)
    e2 = coord._register_active_run(2, 600, has_end=True)
    await coord.async_stop_all_zones()
    assert e1.is_set() and e2.is_set()


# --------------------------------------------------------------------------- #
# stopping interrupts a metered run → partial + delivered water credited
# --------------------------------------------------------------------------- #
async def test_metered_run_stops_early_records_partial(monkeypatch):
    zone = _zone(
        **{
            const.ZONE_BUCKET: -10.0,
            const.ZONE_SIZE: 10.0,
            const.ZONE_THROUGHPUT: 10.0,
            const.ZONE_MAXIMUM_BUCKET: 100.0,
            const.ZONE_DURATION: 600,
        }
    )
    coord = _coord(monkeypatch, zones=[zone])
    coord._confirm_valve_running = AsyncMock(return_value=True)
    monkeypatch.setattr(
        "custom_components.smart_irrigation.irrigation.asyncio.sleep", AsyncMock()
    )

    # Stop as soon as the run registers its marker: the first poll then reports
    # stopped and the loop breaks.
    orig_register = coord._register_active_run

    def _register_then_stop(zid, dur, *, has_end):
        ev = orig_register(zid, dur, has_end=has_end)
        ev.set()
        return ev

    coord._register_active_run = _register_then_stop

    await coord._run_valve_metered(dict(zone), "switch.valve", real_flow=False)

    # Run was logged as a partial with the "stopped" detail.
    log = coord.store.zones[1][const.ZONE_RUN_LOG]
    assert log[0]["result"] == const.RUN_RESULT_PARTIAL
    assert log[0]["detail"] == const.RUN_DETAIL_STOPPED
    # The in-progress marker is cleared once the run finishes.
    assert coord.get_active_runs() == {}
