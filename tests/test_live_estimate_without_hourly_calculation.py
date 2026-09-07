"""A zone whose install leaves ``hourlycalculation`` off still gets a live bucket.

``hourlycalculation`` ships off. ``live_estimate_enabled`` is an independent
setting, so an operator could turn live-estimate watering on and have it do
nothing: ``_daily_form_applies`` asked ``replayed_balance_applies``, that
predicate answers False whenever the switch is off, and the mirrored daily
equation was refused to the whole shipped-default population. On a sensor-only
install there is no other source, so the estimate was simply absent and the
sensor read ``unknown`` with nothing saying why.

The two questions are on different axes and only one of them involves the switch:

* which EQUATION the zone's commit runs. For a PyETO zone estimating solar
  radiation from the day's temperature range that is the daily FAO-56 equation,
  and it is the daily equation whether ``hourlycalculation`` is on or off. So the
  mirror applies either way, which is what this module pins;
* which FORM the water balance takes, replayed or lumped. That one is the
  switch's own, deliberately, because replaying moves the stored bucket. It is
  untouched here, and pinned untouched: opening the ET source must not change a
  single number the commit writes.

Asserted against a run of the real ``calculate_module`` rather than a
hand-computed figure, for the reason the sibling module gives: a
reimplementation of the equation in the test would agree with itself however far
the two paths had drifted.
"""

from unittest.mock import Mock

import pytest
from homeassistant.util.unit_system import METRIC_SYSTEM

from custom_components.irrigation_plus import SmartIrrigationCoordinator, const
from custom_components.irrigation_plus.calcmodules.pyeto import SOLRAD_behavior
from custom_components.irrigation_plus.live_estimate import (
    REASON_NEVER_CALCULATED,
    REASON_NO_ET_SOURCE,
)
from custom_components.irrigation_plus.store import SmartIrrigationStorage
from tests.test_live_estimate_replayed_balance import (
    ELEV,
    LAT,
    LON,
    WINDOW_END,
    _committed,
    _estimating_inputs,
    _estimating_zone,
    _hourly_forecast,
    _inputs,
    _zone,
)


@pytest.fixture
async def coordinator(hass):
    """A real coordinator over a real in-memory store, hourly form left OFF.

    The sibling module's fixture opts the hourly form IN, which is the one thing
    every case here has to vary, so this is its own fixture rather than an import
    the cases would immediately override.
    """
    hass.data[const.DOMAIN] = {
        const.CONF_USE_WEATHER_SERVICE: False,
        const.CONF_WEATHER_SERVICE: None,
    }
    hass.config.units = METRIC_SYSTEM
    hass.config.language = "en"
    store = SmartIrrigationStorage(hass)
    await store.async_load()
    await store.async_update_config(
        {const.CONF_CONTINUOUS_UPDATES: True, const.CONF_HOURLY_CALCULATION: False}
    )
    entry = Mock()
    entry.unique_id = "t"
    entry.data = {}
    entry.options = {}
    c = SmartIrrigationCoordinator(hass, None, entry, store)
    c.store = store
    # Both halves resolve the site from these, so pinning them here is what makes
    # the two priced windows comparable at all.
    c._effective_latitude = LAT
    c._effective_longitude = LON
    c._effective_elevation = ELEV
    return c, store


class TestTheMirrorAppliesWithTheSwitchOff:
    """The claim: the commit's own equation, offered on the population that ships."""

    async def test_a_sensor_only_zone_gets_a_live_bucket_at_all(self, coordinator):
        """The bug, stated as the behaviour that was missing.

        No weather client and no forecast, which is the sensor-only install the
        feature was inert on: with the mirror refused there was no source left
        and the estimate was absent entirely.
        """
        c, store = coordinator
        zone, module, instance = await _estimating_zone(
            c, store, 2.0, rain_at={20: 14.0}
        )

        est = c._intraday_for_zone(zone, _estimating_inputs(instance, module))

        assert est["available"] is True
        assert est["method"] == "daily_mirror"
        assert est["unavailable_reason"] is None

    async def test_the_live_bucket_lands_on_the_committed_bucket(self, coordinator):
        """And the number is the right one, not merely present.

        The equality is the point of mirroring the equation: an estimate that
        appeared but disagreed with the ledger would be worse than none, because
        with ``live_estimate_enabled`` on it both triggers and sizes real runs.
        """
        c, store = coordinator
        zone, module, instance = await _estimating_zone(
            c, store, 2.0, rain_at={20: 14.0}
        )

        est = c._intraday_for_zone(
            zone, _estimating_inputs(instance, module, forecast=_hourly_forecast())
        )
        data = await _committed(c, zone, now=WINDOW_END)

        assert est["live_deficit"] == pytest.approx(
            round(data[const.ZONE_BUCKET], 2), abs=0.01
        )

    async def test_the_switch_makes_no_difference_to_the_equation(self, coordinator):
        """Same zone, same window, both settings of the switch: one ET.

        The tightest statement of the axis separation. If the switch ever leaks
        back into the source gate this diverges, whatever else still passes.
        """
        c, store = coordinator
        zone, module, instance = await _estimating_zone(
            c, store, 2.0, rain_at={20: 14.0}
        )

        off = c._intraday_for_zone(zone, _estimating_inputs(instance, module))
        await store.async_update_config({const.CONF_HOURLY_CALCULATION: True})
        on = c._intraday_for_zone(zone, _estimating_inputs(instance, module))

        assert off["method"] == on["method"] == "daily_mirror"
        assert off["et_since"] == pytest.approx(on["et_since"])

    async def test_a_module_that_does_not_model_weather_is_still_refused(
        self, coordinator
    ):
        """The half of the old gate that stays.

        Static and Passthrough hand back a number the install supplied, so there
        is no equation to mirror. Dropping the whole predicate rather than its
        ``hourlycalculation`` half would have offered them one.
        """
        c, store = coordinator
        zone = await _zone(
            c,
            store,
            2.0,
            solrad=SOLRAD_behavior.EstimateFromTemp.value,
            module_name="Static",
        )
        module = store.get_module(zone[const.ZONE_MODULE])
        instance = Mock()
        instance._solrad_behavior = SOLRAD_behavior.EstimateFromTemp.value
        instance.forecast_days = 0

        assert c._daily_form_applies(zone, instance) is False
        est = c._intraday_for_zone(zone, _estimating_inputs(instance, module))
        assert est["available"] is False


class TestTheStoredBucketIsUntouched:
    """The blast radius the switch guards is the BALANCE FORM, and it is unmoved."""

    @pytest.mark.parametrize("hourly_calculation", [False, True])
    async def test_the_balance_form_still_follows_the_switch(
        self, coordinator, hourly_calculation
    ):
        c, store = coordinator
        await store.async_update_config(
            {const.CONF_HOURLY_CALCULATION: hourly_calculation}
        )
        zone, module, instance = await _estimating_zone(
            c, store, 2.0, rain_at={20: 14.0}
        )

        est = c._intraday_for_zone(zone, _estimating_inputs(instance, module))
        booked = est["precip_since"]
        commit_replays = c._substeps_for_zone(zone, booked, now=WINDOW_END) is not None

        assert est["available"] is True
        assert (est["balance_form"] == "replayed") is commit_replays
        assert commit_replays is hourly_calculation


class TestAZoneWithNoEstimateSaysWhy:
    """The other half: what an operator reads when there is still nothing to show.

    Every exit names its own missing precondition, so an empty sensor is a
    diagnosis rather than a guess between six of them.
    """

    async def test_a_never_calculated_zone_names_that(self, coordinator):
        c, store = coordinator
        zone, module, instance = await _estimating_zone(c, store, 2.0)
        zone = dict(zone)
        zone[const.ZONE_LAST_CALCULATED] = None

        est = c._intraday_for_zone(zone, _estimating_inputs(instance, module))

        assert est["available"] is False
        assert est["unavailable_reason"] == REASON_NEVER_CALCULATED

    async def test_a_zone_with_no_source_left_names_that(self, coordinator):
        """A measured-radiation zone on a sensor-only install with the switch off.

        Both forms decline: the hourly one because the commit is not summing
        hourly ETo, the daily mirror because the commit is not estimating
        radiation either. That zone is still outside this change's population,
        and now it says so instead of publishing nothing.
        """
        c, store = coordinator
        zone = await _zone(
            c, store, 2.0, solrad=SOLRAD_behavior.DontEstimate.value, rain_at={20: 14.0}
        )

        est = c._intraday_for_zone(zone, _inputs())

        assert est["available"] is False
        assert est["unavailable_reason"] == REASON_NO_ET_SOURCE

    async def test_the_reason_reaches_the_coordinator_and_clears(self, coordinator):
        """Published from a cache of its own, so the payload the panel and the
        runner read still holds only zones that carry a number."""
        c, store = coordinator
        zone = await _zone(
            c, store, 2.0, solrad=SOLRAD_behavior.DontEstimate.value, rain_at={20: 14.0}
        )
        c._fetch_intraday_inputs = _returns(_inputs())
        c._resolve_zone_modules = _returns({})

        estimates = await c.async_get_zone_estimates()
        zone_id = str(zone[const.ZONE_ID])

        assert zone_id not in estimates
        assert c._zone_estimate_reasons[zone_id] == REASON_NO_ET_SOURCE

    async def test_the_warning_is_only_for_an_install_that_waters_on_it(
        self, coordinator, caplog
    ):
        """With the feature off the absence costs nothing -- the runner was never
        going to read the estimate -- so warning about it would be noise on every
        install that has never turned it on.
        """
        c, store = coordinator
        await _zone(
            c, store, 2.0, solrad=SOLRAD_behavior.DontEstimate.value, rain_at={20: 14.0}
        )
        c._fetch_intraday_inputs = _returns(_inputs())
        c._resolve_zone_modules = _returns({})

        caplog.clear()
        await c.async_get_zone_estimates()
        assert "no live estimate" not in caplog.text

        await store.async_update_config({const.CONF_LIVE_ESTIMATE_ENABLED: True})
        caplog.clear()
        await c.async_get_zone_estimates()
        assert REASON_NO_ET_SOURCE in caplog.text

        # Same reason on the next cycle: said once, not once a minute forever.
        caplog.clear()
        await c.async_get_zone_estimates()
        assert "no live estimate" not in caplog.text


def _returns(value):
    """An async stand-in for one of the estimate's input fetches."""

    async def _fetch(*args, **kwargs):
        return dict(value) if isinstance(value, dict) else value

    return _fetch
