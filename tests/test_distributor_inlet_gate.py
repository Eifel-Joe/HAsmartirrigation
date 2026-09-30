"""A distributor cycle never starts while its inlet reports open (#181).

Measured on a test instance in count watch mode: a cycle claimed while a foreign
run held the inlet open watered over it. Opening an inlet that is already open
makes no edge, so the ring did not index; the leg was credited to the next member,
the member whose outlet had the water got nothing, and the stored position ended
one ahead while it still read synced. These tests pin the gate in the claim, what
a refused cycle leaves behind, and the grace after the integration's own close.
"""

import asyncio
import json
import logging
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from homeassistant.exceptions import ServiceNotFound

from custom_components.irrigation_plus import const
from tests.test_distributor import _dist, _host
from tests.test_distributor_cycle import _dist_cfg, _loop_host, _mem
from tests.test_distributor_integration import _call


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


_NOTICE = "Distributor 'Garten' did not start a watering cycle: its inlet switch.inlet was open."


async def test_a_refusal_is_logged_and_notified(caplog):
    c = _gate_host(inlet_state="on")

    with caplog.at_level(logging.WARNING):
        await c.async_run_distributor_cycle(_gated_cfg())

    assert (
        "Distributor 'Garten' did not start a cycle: inlet switch.inlet is on"
        in caplog.text
    )
    c.hass.services.async_call.assert_any_await(
        "persistent_notification",
        "create",
        {
            "title": "Irrigation Plus",
            "message": _NOTICE,
            "notification_id": f"{const.DOMAIN}_distributor_0",
        },
    )


async def test_a_refusal_is_forwarded_to_the_notify_target():
    c = _gate_host(inlet_state="on")

    await c.async_run_distributor_cycle(_gated_cfg(notify_target="notify.phone"))

    c.hass.services.async_call.assert_any_await("notify", "phone", {"message": _NOTICE})


async def test_a_refusal_records_every_member_as_an_explicit_list():
    c = _gate_host(inlet_state="on")

    await c.async_run_distributor_cycle(_gated_cfg())

    c._record_skipped_run.assert_awaited_once_with(
        [1, 2, 3], const.SKIP_REASON_INLET_OPEN, trigger="schedule"
    )
    c._dist_members.assert_awaited_once_with(0)


async def test_a_refusal_records_only_the_targeted_members():
    # The dispatcher hands the claim the schedule's whole target, direct zones
    # included: zone 9 is not a member and must get no entry.
    c = _gate_host(inlet_state="on")

    await c.async_run_distributor_cycle(_gated_cfg(), only_zone_ids=[2, 9])

    c._record_skipped_run.assert_awaited_once_with(
        [2], const.SKIP_REASON_INLET_OPEN, trigger="schedule"
    )


async def test_a_refusal_records_nothing_when_no_member_was_targeted():
    c = _gate_host(inlet_state="on")

    await c.async_run_distributor_cycle(_gated_cfg(), only_zone_ids=[9])

    c._record_skipped_run.assert_not_awaited()


async def test_a_refused_test_run_records_no_history():
    c = _gate_host(inlet_state="on")

    assert await c.async_run_distributor_cycle(_gated_cfg(), test_run=True) is False

    c._record_skipped_run.assert_not_awaited()
    c.hass.services.async_call.assert_awaited_once()  # the notification still goes out


async def test_a_refused_forced_member_run_is_recorded_as_manual():
    c = _gate_host(inlet_state="on")

    await c.async_run_distributor_cycle(
        _gated_cfg(), only_zone_ids=[2], force_water=True
    )

    c._record_skipped_run.assert_awaited_once_with(
        [2], const.SKIP_REASON_INLET_OPEN, trigger="manual"
    )


async def test_a_distributor_in_flight_is_not_reported_as_an_open_inlet(caplog):
    # The integration's own sweep holds the inlet open: the in-flight guard must
    # answer first, with no notification and no history entry.
    c = _gate_host(inlet_state="on")
    c._dist_inflight_ids().add(0)

    with caplog.at_level(logging.WARNING):
        assert await c.async_run_distributor_cycle(_gated_cfg()) is False

    c.hass.services.async_call.assert_not_awaited()
    c._record_skipped_run.assert_not_awaited()
    assert "did not start a cycle" not in caplog.text


async def test_a_broken_notify_target_does_not_stop_the_history(caplog):
    # A stale notify target raises ServiceNotFound. The refusal must still
    # return False and record the history instead of raising into the
    # dispatcher, which would stop the other distributors.
    c = _gate_host(inlet_state="on")

    async def _service_call(domain, service, data=None, **kwargs):
        if domain == "notify":
            raise ServiceNotFound(domain, service)

    c.hass.services.async_call = AsyncMock(side_effect=_service_call)

    with caplog.at_level(logging.ERROR):
        refused = await c.async_run_distributor_cycle(
            _gated_cfg(notify_target="notify.gone")
        )

    assert refused is False
    c._record_skipped_run.assert_awaited_once_with(
        [1, 2, 3], const.SKIP_REASON_INLET_OPEN, trigger="schedule"
    )
    assert "could not forward the notification to notify.gone" in caplog.text


async def test_a_refusal_is_notified_in_the_users_language():
    c = _gate_host(inlet_state="on")
    c.hass.config.language = "de"

    await c.async_run_distributor_cycle(_gated_cfg())

    c.hass.services.async_call.assert_awaited_once_with(
        "persistent_notification",
        "create",
        {
            "title": "Irrigation Plus",
            "message": "Verteiler 'Garten' hat einen Bewässerungszyklus nicht "
            "gestartet: sein Einlass switch.inlet war offen.",
            "notification_id": f"{const.DOMAIN}_distributor_0",
        },
    )


async def test_a_refusal_with_an_empty_target_records_nothing():
    # An empty target means "no member", as in the sweep, not "every member".
    c = _gate_host(inlet_state="on")

    await c.async_run_distributor_cycle(_gated_cfg(), only_zone_ids=[])

    c._record_skipped_run.assert_not_awaited()


def test_the_skip_reason_is_a_key_every_language_localizes():
    # The history renders a skip code through panels.zones.outlook.checks.<code>;
    # a code without a key there shows up raw.
    languages = Path(const.__file__).parent / const.LANGUAGE_FILES_DIR
    files = sorted(languages.glob("*.json"))
    assert len(files) == 8
    for path in files:
        data = json.loads(path.read_text(encoding="utf-8"))
        checks = data["panels"]["zones"]["outlook"]["checks"]
        assert const.SKIP_REASON_INLET_OPEN in checks, path.name


def _grace_host(inlet_state="on"):
    """A gate host with the REAL _dist_close_inlet (which stamps the close).

    _loop_host stubs _dist_close_inlet as an instance attribute; deleting it
    restores the method. The actuation underneath is stubbed instead, so the
    classic close sends nothing real. The clock starts at 1000.0.
    """
    c = _gate_host(inlet_state=inlet_state, now=1000.0)
    del c._dist_close_inlet
    c._dist_domain_turn = AsyncMock()
    return c


@pytest.mark.parametrize("state", ["on", "closing"])
async def test_the_next_cycle_runs_within_the_grace_after_our_own_close(state):
    # The inlet still reports open, or not closed yet, after our own close.
    c = _grace_host(inlet_state=state)
    cfg = _gated_cfg()
    await c._dist_close_inlet(cfg)

    c.hass.loop.time.return_value = 1029.0
    assert await c.async_run_distributor_cycle(cfg) is True

    c._dist_domain_turn.assert_awaited_once_with("switch.inlet", False)


async def test_the_grace_runs_out_after_thirty_seconds():
    c = _grace_host()
    cfg = _gated_cfg()
    await c._dist_close_inlet(cfg)

    c.hass.loop.time.return_value = 1031.0
    assert await c.async_run_distributor_cycle(cfg) is False


async def test_a_stop_service_close_starts_the_grace():
    c = _grace_host()
    cfg = _gated_cfg(
        watering_mode=const.WATERING_MODE_SERVICE, stop_service="script.dist_stop"
    )
    await c._dist_close_inlet(cfg)

    c.hass.loop.time.return_value = 1029.0
    assert await c.async_run_distributor_cycle(cfg) is True

    c.hass.services.async_call.assert_any_await(
        "script", "dist_stop", {"distributor_id": 0}
    )


async def test_a_service_distributor_without_stop_service_gets_no_grace():
    # Nothing is sent, so nothing proves the valve closed: a start over a
    # still-open self-closing valve is the defect the gate exists for.
    c = _grace_host()
    cfg = _gated_cfg(watering_mode=const.WATERING_MODE_SERVICE, stop_service=None)
    await c._dist_close_inlet(cfg)

    c.hass.loop.time.return_value = 1001.0
    assert await c.async_run_distributor_cycle(cfg) is False


async def test_the_grace_belongs_to_the_distributor_that_closed():
    c = _grace_host()
    await c._dist_close_inlet(_gated_cfg(id=0))

    c.hass.loop.time.return_value = 1001.0
    assert await c.async_run_distributor_cycle(_gated_cfg(id=1)) is False


async def test_a_close_that_raised_starts_no_grace():
    c = _grace_host()
    c._dist_domain_turn = AsyncMock(side_effect=RuntimeError("inlet unreachable"))
    cfg = _gated_cfg()
    with pytest.raises(RuntimeError):
        await c._dist_close_inlet(cfg)

    c.hass.loop.time.return_value = 1001.0
    assert await c.async_run_distributor_cycle(cfg) is False


async def test_a_stop_service_that_raised_starts_no_grace():
    # A stale stop_service raises ServiceNotFound at once: nothing was sent, so
    # nothing shows the valve closed (the service twin of the classic case above).
    c = _grace_host()

    async def _service_call(domain, service, data=None, **kwargs):
        if domain == "script":
            raise ServiceNotFound(domain, service)

    c.hass.services.async_call = AsyncMock(side_effect=_service_call)
    cfg = _gated_cfg(
        watering_mode=const.WATERING_MODE_SERVICE, stop_service="script.dist_stop"
    )
    with pytest.raises(ServiceNotFound):
        await c._dist_close_inlet(cfg)

    c.hass.loop.time.return_value = 1001.0
    assert await c.async_run_distributor_cycle(cfg) is False


async def test_a_later_close_restarts_the_grace():
    # Every own close counts: the last one decides, not the first.
    c = _grace_host()
    cfg = _gated_cfg()
    await c._dist_close_inlet(cfg)

    c.hass.loop.time.return_value = 1500.0
    await c._dist_close_inlet(cfg)

    c.hass.loop.time.return_value = 1529.0
    assert await c.async_run_distributor_cycle(cfg) is True


async def test_the_grace_is_over_at_exactly_thirty_seconds():
    c = _grace_host()
    cfg = _gated_cfg()
    await c._dist_close_inlet(cfg)

    c.hass.loop.time.return_value = 1030.0
    assert await c.async_run_distributor_cycle(cfg) is False


async def test_the_grace_runs_for_a_distributor_that_is_not_number_zero():
    # Every other positive test uses id 0, the one id that is also falsy.
    c = _grace_host()
    cfg = _gated_cfg(id=3)
    await c._dist_close_inlet(cfg)

    c.hass.loop.time.return_value = 1029.0
    assert await c.async_run_distributor_cycle(cfg) is True


_MEMBER = {
    "id": 7,
    "distributor_id": 0,
    "outlet_number": 1,
    "duration": 30,
    "bucket": -1,
    "bucket_threshold": 0,
    "state": "automatic",
}


def _entry_host(inlet_state="on"):
    """The full distributor host with the REAL dispatcher and claim.

    Distributor 0 (``_dist``: classic, inlet ``switch.inlet``, synced, confirmed) has
    one due member, zone 7. Only the sweep, the history writer and the store's reads
    are stubbed, so a call through any entry meets the gate as it would in the
    coordinator.
    """
    c = _host()
    c.hass.config.language = "en"
    c.hass.states.get = Mock(return_value=SimpleNamespace(state=inlet_state))
    c.store.config.zone_sequencing = const.CONF_ZONE_SEQUENCING_SEQUENTIAL
    c._master_off_deadline = None
    c._rain_delay_active = Mock(return_value=False)
    c._sc_is_self_closing = Mock(return_value=False)
    c.store.async_get_zones = AsyncMock(return_value=[dict(_MEMBER)])
    c.store.get_zone = Mock(return_value=dict(_MEMBER))
    c.store.async_get_distributors = AsyncMock(return_value=[_dist(id=0)])
    c.store.get_distributor = Mock(return_value=_dist(id=0, active_cycle=None))
    c._dist_members = AsyncMock(return_value=[dict(_MEMBER)])
    c._dist_needs_water = Mock(return_value=True)
    c._dist_run_sweep = AsyncMock(return_value=True)
    c._record_skipped_run = AsyncMock()
    return c


def _assert_refused(c, trigger="schedule"):
    c._dist_run_sweep.assert_not_awaited()
    assert 0 not in c._dist_inflight_ids()
    c._record_skipped_run.assert_awaited_once_with(
        [7], const.SKIP_REASON_INLET_OPEN, trigger=trigger
    )


async def test_a_scheduled_dispatch_meets_the_gate():
    c = _entry_host()

    assert await c._dispatch_distributor_cycles("all") is False

    _assert_refused(c)


async def test_water_all_zones_meets_the_gate():
    c = _entry_host()

    await c.async_irrigate_now()

    _assert_refused(c)


async def test_irrigate_now_on_a_member_meets_the_gate():
    c = _entry_host()

    await c.async_irrigate_now("7")

    _assert_refused(c)


async def test_a_member_run_with_a_duration_meets_the_gate():
    # A forced run bypasses the rain delay and the demand gate, but not this one.
    c = _entry_host()

    await c.async_run_zone(7, 2)

    _assert_refused(c, trigger="manual")


async def test_distributor_run_now_meets_the_gate():
    c = _entry_host()

    await c.handle_distributor_run_now(_call(**{const.ATTR_DISTRIBUTOR_ID: 0}))

    _assert_refused(c)


async def test_the_test_run_meets_the_gate():
    c = _entry_host()

    assert await c.async_run_distributor_test(_dist(id=0)) is False

    c._dist_run_sweep.assert_not_awaited()
    c._record_skipped_run.assert_not_awaited()


async def test_the_finish_anchor_estimate_does_not_read_the_inlet():
    c = _entry_host(inlet_state="off")
    closed = await c.get_total_irrigation_duration("all")

    c.hass.states.get = Mock(return_value=SimpleNamespace(state="on"))
    opened = await c.get_total_irrigation_duration("all")

    assert closed > 0
    assert opened == closed


async def test_two_claims_scheduled_together_start_exactly_one_sweep():
    # The gate sits between the in-flight check and inflight.add; an await there
    # would let a second claim through while the first one is past its check.
    c = _gate_host(inlet_state="off")
    starts = []

    async def slow_sweep(*args, **kwargs):
        starts.append(1)
        await asyncio.sleep(0.01)  # long enough for the second claim to run
        return True

    c._dist_run_sweep = slow_sweep

    first, second = await asyncio.gather(
        c.async_run_distributor_cycle(_gated_cfg()),
        c.async_run_distributor_cycle(_gated_cfg()),
    )

    assert (first, second) == (True, False)
    assert len(starts) == 1
