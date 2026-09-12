"""The finish anchor prices a self-closing zone at the window its valve runs.

The series this closes moved the self-closing RUN onto ``hardware_window``: a
minutes-unit valve told "5 minutes" for a 263 s price really runs 300 s, and
``async_run_self_closing`` now books that 300 -- including the chain advance,
which is armed on exactly that number (``_sc_schedule_cleanup(zone_id,
planned_seconds)``, released by ``_sc_finish_run`` -> ``_chain_advance_for_run``,
with ``run_chain.async_dispatch_chained_zones`` holding the remaining zones
until then).

The finish anchor did not move with it. It prices through
``irrigation.async_plan_zone_runs`` and ``run_window.nominal_zone_duration``,
both of which stopped at the unrounded seconds, so the model and the run
disagreed by one rounding PER ZONE on every chained sequencing -- the anchor
said 526 s for a pair the chain really takes 600 s over. Under ``parallel`` the
track is a max rather than a sum, so the same disagreement costs one rounding
there, as it did before the series too.

Every number below is the real chain end, derived from the hardware window,
not from the priced seconds.
"""

from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from homeassistant.util.unit_system import METRIC_SYSTEM

from custom_components.irrigation_plus import SmartIrrigationCoordinator, const
from custom_components.irrigation_plus.run_window import (
    hardware_priced_seconds,
    nominal_zone_duration,
)

SEQUENTIAL = const.CONF_ZONE_SEQUENCING_SEQUENTIAL
PARALLEL = const.CONF_ZONE_SEQUENCING_PARALLEL
ROTATING = const.CONF_ZONE_SEQUENCING_ROTATING

# 263 s priced -> 5 whole minutes told -> 300 s the valve really runs. Chosen
# because the rounding is large (37 s) and 263 is a minute multiple in neither
# direction, so an accidental floor and an accidental ceil give different
# numbers and cannot both pass.
PRICED = 263.0
WINDOW = 300.0


def _zone(zone_id, *, mode, unit=const.DURATION_UNIT_MINUTES, duration=PRICED):
    """A zone that is due and priced at ``duration`` seconds.

    No throughput/size, so ``_zone_run_decision`` falls through to the daily
    ledger and the decision duration IS ``ZONE_DURATION`` -- what is under test
    is the conversion applied to it, not the deficit math that produced it.

    No ``confirm_entity`` and no ``linked_entity``: both buy a zone 30 s of
    ``zone_confirm_seconds`` on top of its water, which is real but is not this
    fix, and would put a second moving part into every expected number.
    """
    return {
        const.ZONE_ID: zone_id,
        const.ZONE_NAME: f"Zone {zone_id}",
        const.ZONE_STATE: const.ZONE_STATE_AUTOMATIC,
        const.ZONE_WATERING_MODE: mode,
        const.ZONE_DURATION_UNIT: unit,
        const.ZONE_DURATION: duration,
        const.ZONE_BUCKET: -5.0,
        const.ZONE_BUCKET_THRESHOLD: -1.0,
    }


def _nominal_zone(zone_id, *, mode, unit=const.DURATION_UNIT_MINUTES):
    """Same zone, configured so ``nominal_zone_duration`` prices it at 263 s.

    10 l/min over 10 m2 is 60 mm/h, so a threshold of -(263/3600)*60 mm prices
    to 263/3600*3600 = 263.0 s.
    """
    z = _zone(zone_id, mode=mode, unit=unit)
    z.update(
        {
            const.ZONE_BUCKET_THRESHOLD: -(PRICED / 3600.0) * 60.0,
            const.ZONE_THROUGHPUT: 10.0,
            const.ZONE_SIZE: 10.0,
            const.ZONE_MULTIPLIER: 1.0,
            const.ZONE_MAXIMUM_DURATION: 36000,
            const.ZONE_LEAD_TIME: 0,
        }
    )
    return z


def _coord(zones, *, sequencing=SEQUENTIAL, slot_minutes=5, absorption_minutes=0):
    """A coordinator built by ``__new__``, as test_nominal_demand_projection does.

    Not the real constructor: it arms ``async_track_time_change`` trackers that
    nothing here cancels, and the harness fails such a test in teardown on the
    lingering timer. Both methods under test are read-only projections and need
    nothing __init__ builds.
    """
    c = SmartIrrigationCoordinator.__new__(SmartIrrigationCoordinator)
    hass = Mock()
    hass.config = Mock()
    hass.config.units = METRIC_SYSTEM
    # No station entity is registered, so station_facts answers "the controller
    # did not answer" and the station track is priced as a chain -- which is
    # all the OpenSprinkler guard below needs it to do.
    hass.states.get = Mock(return_value=None)
    hass.states.async_all = Mock(return_value=[])
    c.hass = hass
    c.store = Mock()
    c.store.config = SimpleNamespace(
        zone_sequencing=sequencing,
        # sequencing_timing reads both as MINUTES and returns seconds.
        zone_sequencing_max_consecutive_duration=slot_minutes,
        zone_sequencing_min_absorption_time=absorption_minutes,
        live_estimate_enabled=False,
    )
    c.store.async_get_zones = AsyncMock(side_effect=lambda: [dict(z) for z in zones])
    c.store.async_get_distributors = AsyncMock(return_value=[])
    return c


class TestTheAnchorCoversTheChain:
    """The test that matters: the anchor against the end the chain really has.

    All three sequencings are pinned, because the shortfall's SIZE is a
    property of the reduction: parallel takes a max and pays one rounding,
    sequential sums and pays one per zone, rotating replays the ring and pays
    one per zone too. The conversion itself is orthogonal to all of that — it
    is applied per zone in the two pricing functions, so what
    ``concurrent_wall_clock`` receives is already the effective budget and the
    reduction never sees the priced number. That is why the rotating case needs
    no separate argument about pauses: ``test_run_window.py`` owns the pause
    model, and this file only has to show the converted budget reaching it.
    """

    @pytest.mark.asyncio
    async def test_a_sequential_pair_of_minute_zones_is_anchored_at_the_real_end(
        self,
    ):
        # Two minutes-unit self-closing zones, each priced 263 s and each
        # really running 300 s. Under sequential the chain holds zone 2 until
        # zone 1's cleanup fires -- and that cleanup is armed on 300, not 263.
        # So the run ends 600 s after it starts.
        #
        # The anchor said 526 and started the run 74 s too late. Before the
        # series it also said 526, but against a real end of 563 (zone 1's
        # chain advance fired on the booked 263, zone 2 then really ran 300),
        # so it was 37 s late: ONE rounding, however many zones were chained.
        # Arming the chain on the effective number without moving the anchor
        # turned that single rounding into one PER ZONE -- 74 s for two, 111 s
        # for three, and so on -- which is the half of this bug the series
        # introduced itself.
        coord = _coord(
            [
                _zone(1, mode=const.WATERING_MODE_SERVICE),
                _zone(2, mode=const.WATERING_MODE_SERVICE),
            ],
            sequencing=SEQUENTIAL,
        )
        assert await coord.get_total_irrigation_duration() == 600

    @pytest.mark.asyncio
    async def test_parallel_pays_one_rounding_not_one_per_zone(self):
        # The guard on the REDUCTION: this fix re-prices each zone, it does not
        # turn a max into a sum. Both valves are opened together and both close
        # at +300, so the track is 300 -- never 526 and never 600.
        coord = _coord(
            [
                _zone(1, mode=const.WATERING_MODE_SERVICE),
                _zone(2, mode=const.WATERING_MODE_SERVICE),
            ],
            sequencing=PARALLEL,
        )
        assert await coord.get_total_irrigation_duration() == 300

    @pytest.mark.asyncio
    async def test_rotating_replays_the_ring_on_the_effective_budget(self):
        # The third reduction, and the other chained one.
        #
        # An absorption pause is configured on purpose. With absorption at 0
        # and no confirms the replay degenerates to sum(budgets) -- 600 at
        # every slot length, which is the number the sequential test above
        # already asserts by identical arithmetic, so such a pin would be blind
        # to both the slot and the replay. At 5 minutes of absorption the
        # pauses bite and the answer moves with the slot: 1020 at a 2-minute
        # slot, 780 at 3, 600 at 5 (one slot per zone, no pause charged).
        #
        # Hand-replayed from simulate_wall_clock's loop, slot 120 s,
        # absorption 300 s, budgets 300/300, confirms 0:
        #   A 0-120, B 120-240
        #   A waits to 420 (300 - 120 elapsed), runs to 540
        #   B needs no wait (300 elapsed exactly), runs to 660
        #   A waits to 840, runs its last 60 to 900
        #   B waits to 960, runs its last 60 to 1020.
        # Priced unconverted (263/263) the same replay gives 983.
        coord = _coord(
            [
                _zone(1, mode=const.WATERING_MODE_SERVICE),
                _zone(2, mode=const.WATERING_MODE_SERVICE),
            ],
            sequencing=ROTATING,
            slot_minutes=2,
            absorption_minutes=5,
        )
        assert await coord.get_total_irrigation_duration() == 1020


class TestThePlanPricesTheSameWindowTheRunBooks:
    """``async_plan_zone_runs`` is where the anchor's live durations are made."""

    async def _durations(self, zones):
        planned = await _coord(zones).async_plan_zone_runs()
        return [p.duration for p in planned]

    @pytest.mark.asyncio
    async def test_a_self_closing_minute_zone_is_planned_at_its_window(self):
        zones = [_zone(1, mode=const.WATERING_MODE_SERVICE)]
        assert await self._durations(zones) == [WINDOW]

    @pytest.mark.asyncio
    async def test_a_classic_zone_carrying_a_minutes_unit_is_not_converted(self):
        # Mode, not unit. A classic zone is timed by Irrigation Plus -- it
        # sleeps the priced seconds and closes the valve itself, whatever
        # duration_unit says -- and the field survives on a zone switched back
        # to classic. Keying on the unit would reserve 300 s for a 263 s run.
        zones = [_zone(1, mode=const.WATERING_MODE_CLASSIC)]
        assert await self._durations(zones) == [PRICED]

    @pytest.mark.asyncio
    async def test_an_opensprinkler_station_is_not_converted(self):
        # run_station takes whole seconds and nothing else; the duration unit
        # belongs to a user's own run_service script, not to that API.
        # hardware_window's own docstring says not to wire this path.
        zones = [_zone(1, mode=const.WATERING_MODE_OPENSPRINKLER)]
        assert await self._durations(zones) == [PRICED]


class TestHardwarePricedSeconds:
    """The shared rule, exercised directly."""

    def test_a_minutes_self_closing_zone_is_priced_at_its_window(self):
        zone = _zone(1, mode=const.WATERING_MODE_SERVICE)
        assert hardware_priced_seconds(zone, PRICED) == WINDOW

    def test_a_seconds_self_closing_zone_rounds_to_the_whole_second(self):
        zone = _zone(
            1, mode=const.WATERING_MODE_SERVICE, unit=const.DURATION_UNIT_SECONDS
        )
        assert hardware_priced_seconds(zone, 263.4) == 263.0

    def test_a_batch_zone_converts_too(self):
        # batch.py prices its queue entries through hardware_window as well
        # (8464b3b0), so the batch track has to be re-priced on the same terms.
        zone = _zone(1, mode=const.WATERING_MODE_BATCH)
        assert hardware_priced_seconds(zone, PRICED) == WINDOW

    def test_a_classic_zone_is_never_converted(self):
        zone = _zone(1, mode=const.WATERING_MODE_CLASSIC)
        assert hardware_priced_seconds(zone, PRICED) == PRICED

    def test_an_opensprinkler_zone_is_never_converted(self):
        zone = _zone(1, mode=const.WATERING_MODE_OPENSPRINKLER)
        assert hardware_priced_seconds(zone, PRICED) == PRICED

    def test_nothing_is_conjured_out_of_a_zero(self):
        # A zone priced at 0 must reserve 0, never the one-minute floor of
        # hardware_window's minutes branch -- async_plan_zone_runs produces
        # such a zone on purpose under ignore_demand. hardware_window's own
        # non-positive clamp is what holds this; hardware_priced_seconds adds
        # no guard of its own, because one was added there and measured dead.
        # Pinned from this side anyway: the invariant belongs to the caller's
        # contract, whichever layer happens to hold it.
        zone = _zone(1, mode=const.WATERING_MODE_SERVICE)
        assert hardware_priced_seconds(zone, 0.0) == 0.0


class TestNominalZoneDuration:
    """The other anchor entry point: the steady projection the dial draws."""

    def test_a_minutes_self_closing_zone_prices_at_its_window(self):
        zone = _nominal_zone(1, mode=const.WATERING_MODE_SERVICE)
        assert nominal_zone_duration(zone, metric=True) == WINDOW

    def test_a_classic_zone_with_a_minutes_unit_prices_at_the_priced_seconds(self):
        zone = _nominal_zone(1, mode=const.WATERING_MODE_CLASSIC)
        assert nominal_zone_duration(zone, metric=True) == PRICED

    def test_an_opensprinkler_zone_prices_at_the_priced_seconds(self):
        zone = _nominal_zone(1, mode=const.WATERING_MODE_OPENSPRINKLER)
        assert nominal_zone_duration(zone, metric=True) == PRICED

    def test_a_calibrated_flow_zone_is_converted_after_it_is_rescaled(self):
        """The ORDER, which both call sites forbid getting wrong and nothing
        else in the repo exercises: every other zone in this file has no
        calibration samples, so hoisting the conversion above the rescale
        leaves them all green.

        The zone measured 5 l/min where 10 is configured, so
        ``calibrated_flow_seconds`` doubles the watering. Convert LAST (right):
        263 * 2 = 526 s, which is 9 whole minutes of hardware time = 540.
        Convert FIRST (wrong): 263 -> 5 min = 300, then 300 * 2 = 600 -- a
        60 s over-reservation, and a number that is neither the priced
        duration nor any window the valve can actually be told.
        """
        zone = _nominal_zone(1, mode=const.WATERING_MODE_SERVICE)
        zone[const.ZONE_FLOW_SENSOR] = "sensor.flow"
        zone[const.ZONE_FLOW_CAL_SAMPLES] = [5.0] * const.FLOW_CAL_MIN_SAMPLES
        assert nominal_zone_duration(zone, metric=True) == 540.0
