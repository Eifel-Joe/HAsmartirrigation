"""A distributor cycle never starts while its inlet reports open (#181).

Measured on a test instance in count watch mode: a cycle claimed while a foreign
run held the inlet open watered over it. Opening an inlet that is already open
makes no edge, so the ring did not index; the leg was credited to the next member,
the member whose outlet had the water got nothing, and the stored position ended
one ahead while it still read synced. These tests pin the gate in the claim, what
a refused cycle leaves behind, and the grace after the integration's own close.
"""

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from custom_components.irrigation_plus import const
from tests.test_distributor_cycle import _dist_cfg, _loop_host, _mem


def _gated_cfg(**kw):
    """A synced, confirmed distributor with an inlet entity."""
    d = _dist_cfg(inlet_entity="switch.inlet")
    d.update(kw)
    return d


def _gate_host(members=None, *, inlet_state="on", now=1000.0):
    """A cycle host whose inlet reports ``inlet_state`` and whose loop clock reads ``now``.

    ``inlet_state=None`` makes ``hass.states.get`` return None (the entity does not
    exist). The sweep is stubbed: these tests are about the claim's decision, and
    ``_dist_run_sweep`` returning True is what a delivered cycle looks like to it.
    ``_record_skipped_run`` is stubbed because the real one awaits the store.
    """
    c = _loop_host(
        members if members is not None else [_mem(1, 1), _mem(2, 2), _mem(3, 3)]
    )
    c.hass.config.language = "en"
    c.hass.states.get = Mock(
        return_value=None if inlet_state is None else SimpleNamespace(state=inlet_state)
    )
    c.hass.loop.time = Mock(return_value=now)
    c._dist_run_sweep = AsyncMock(return_value=True)
    c._record_skipped_run = AsyncMock()
    return c


def _evt(old, new):
    """A state-change event as the inlet handler reads it."""
    return SimpleNamespace(
        data={
            "old_state": SimpleNamespace(state=old),
            "new_state": SimpleNamespace(state=new),
        }
    )


async def test_a_foreign_open_keeps_its_credit_when_a_cycle_is_asked_for_meanwhile():
    c = _gate_host([_mem(1, 1), _mem(2, 2), _mem(3, 3)], now=100.0)
    c.hass.data = {}  # _dist_store_update fires the real dispatcher; short-circuit it
    c.store.config.observed_watering_enabled = True
    c.store.get_distributor = Mock(
        return_value=_gated_cfg(
            current_outlet=2,
            watch_mode=const.DISTRIBUTOR_WATCH_MODE_COUNT,
            skip_pulse_seconds=30,
            active_cycle={},
        )
    )
    tasks = []
    c.hass.async_create_task = Mock(
        side_effect=lambda coro: tasks.append(asyncio.ensure_future(coro))
    )
    handler = c._dist_inlet_state_handler(0)

    # The foreign open: count advances the stored position 2 -> 3 and stashes
    # outlet 2, the one that has the water.
    handler(_evt("off", "on"))
    await asyncio.gather(*tasks)
    tasks.clear()

    # A cycle is asked for while the inlet is still open.
    assert await c.async_run_distributor_cycle(_gated_cfg(current_outlet=3)) is False
    c._dist_run_sweep.assert_not_awaited()

    # The foreign run ends 300 s after it began: its member is credited.
    c.hass.loop.time.return_value = 400.0
    handler(_evt("on", "off"))
    await asyncio.gather(*tasks)

    zone, seconds = c._dist_credit_zone.await_args.args
    assert zone[const.ZONE_ID] == 2
    assert seconds == 300.0
    assert (
        c._dist_credit_zone.await_args.kwargs["trigger"] == const.RUN_TRIGGER_OBSERVED
    )
    # The only position write is the foreign open's own advance.
    c.store.async_update_distributor.assert_awaited_once_with(0, {"current_outlet": 3})


@pytest.mark.parametrize("state", ["on", "open", "opening", "closing"])
async def test_the_claim_refuses_while_the_inlet_reports_open(state):
    c = _gate_host(inlet_state=state)

    assert await c.async_run_distributor_cycle(_gated_cfg()) is False

    c._dist_run_sweep.assert_not_awaited()
    c._dist_persist_cycle.assert_not_awaited()  # no STARTING marker, no active_cycle
    c._dist_master_start.assert_not_awaited()
    c._dist_open_inlet.assert_not_awaited()  # a refusal actuates nothing
    c._dist_close_inlet.assert_not_awaited()
    assert 0 not in c._dist_inflight_ids()


@pytest.mark.parametrize("state", ["off", "closed", "unavailable", "unknown", "idle"])
async def test_the_claim_lets_a_cycle_through_when_the_inlet_is_not_open(state):
    c = _gate_host(inlet_state=state)

    assert await c.async_run_distributor_cycle(_gated_cfg()) is True

    c._dist_run_sweep.assert_awaited_once()


async def test_the_claim_lets_a_cycle_through_when_the_inlet_entity_does_not_exist():
    c = _gate_host(inlet_state=None)

    assert await c.async_run_distributor_cycle(_gated_cfg()) is True


@pytest.mark.parametrize("inlet", ["", None])
async def test_the_claim_lets_a_cycle_through_without_an_inlet_entity(inlet):
    c = _gate_host(inlet_state="on")

    assert await c.async_run_distributor_cycle(_gated_cfg(inlet_entity=inlet)) is True

    c.hass.states.get.assert_not_called()


@pytest.mark.parametrize(
    "watch_mode",
    [
        const.DISTRIBUTOR_WATCH_MODE_COUNT,
        const.DISTRIBUTOR_WATCH_MODE_WARN,
        const.DISTRIBUTOR_WATCH_MODE_IGNORE,
    ],
)
@pytest.mark.parametrize(
    "watering_mode", [const.WATERING_MODE_CLASSIC, const.WATERING_MODE_SERVICE]
)
async def test_the_claim_refuses_in_every_watch_and_watering_mode(
    watch_mode, watering_mode
):
    c = _gate_host(inlet_state="on")
    cfg = _gated_cfg(watch_mode=watch_mode, watering_mode=watering_mode)

    assert await c.async_run_distributor_cycle(cfg) is False

    c._dist_run_sweep.assert_not_awaited()
