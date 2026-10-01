"""The forecast weighting on the live-estimate path (#159, second half).

``live_deficit`` is a pure actuals balance and stays one. What the weighting
changes is the SIZING: a zone the live path sizes (no flow sensor) waters for
``min(0, live_deficit + forecast_rain)``, exactly as the daily path sizes from
``effective_bucket`` while leaving the true deficit in the bucket. The window
comes from ``forecast_weighting_credit`` -- the one method the daily balance asks
too -- so the two cannot measure from different moments.

Worked figure from the issue: 10 L/min over 10 m^2 is 60 mm/h; a 10 mm deficit
with 4 mm forecast is a 6 mm run = 360 s, not the 600 s the unweighted live path
watered.
"""

import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from homeassistant.util.unit_system import METRIC_SYSTEM

from custom_components.irrigation_plus import SmartIrrigationCoordinator, const

UTC = datetime.timezone.utc
# Derived, not literal: every forecast entry below hangs off NOW, so no date in
# this module can rot (see test_experimental_features for the failure it avoids).
NOW = datetime.datetime(2026, 9, 26, 21, 0, tzinfo=UTC)


@pytest.fixture(autouse=True)
def _pin_the_clock(monkeypatch):
    import homeassistant.util.dt as dt_util

    monkeypatch.setattr(dt_util, "utcnow", lambda: NOW)


def _days(*mm):
    out = []
    for i in range(max(7, len(mm))):
        start = NOW + datetime.timedelta(days=i)
        out.append(
            {
                const.MAPPING_PRECIPITATION: mm[i] if i < len(mm) else 0.0,
                const.FORECAST_DAY_START: start,
                const.FORECAST_DAY_END: start + datetime.timedelta(days=1),
            }
        )
    return out


def _coordinator(*, forecast=None, weighting=True, deficit=-10.0, client_raises=False):
    coord = SmartIrrigationCoordinator.__new__(SmartIrrigationCoordinator)
    hass = Mock()
    hass.config = Mock()
    hass.config.units = METRIC_SYSTEM

    async def run_executor(func, *args):
        return func(*args)

    hass.async_add_executor_job = run_executor
    coord.hass = hass
    coord.store = Mock()
    coord.store.config = SimpleNamespace(
        live_estimate_enabled=True, forecast_weighting_enabled=weighting
    )
    coord.store.async_get_config = AsyncMock(
        return_value={const.CONF_PRECIPITATION_FORECAST_DAYS: 1}
    )
    coord.use_weather_service = True

    def get_forecast_data():
        if client_raises:
            raise RuntimeError("forecast unreachable")
        return forecast

    coord._WeatherServiceClient = SimpleNamespace(get_forecast_data=get_forecast_data)
    coord.recurring_schedule_manager = SimpleNamespace(
        async_next_run_start_for_zone=AsyncMock(return_value=NOW)
    )
    coord.async_refresh_zone_estimates = AsyncMock(
        return_value={"1": {"live_deficit": deficit}}
    )
    return coord


def _zone(**overrides):
    zone = {
        const.ZONE_ID: 1,
        const.ZONE_THROUGHPUT: 10.0,
        const.ZONE_SIZE: 10.0,  # 60 mm/h
        const.ZONE_MULTIPLIER: 1.0,
        const.ZONE_MAXIMUM_DURATION: 36000,
        const.ZONE_LEAD_TIME: 0,
        const.ZONE_DURATION: 300,
        const.ZONE_BUCKET: -5.0,
    }
    zone.update(overrides)
    return zone


async def test_the_forecast_shortens_a_live_sized_run():
    """The issue's table: 10 mm deficit, 4 mm forecast -> 360 s, not 600 s."""
    coord = _coordinator(forecast=_days(4.0))
    out = await coord._apply_live_durations([_zone()])
    assert out[0][const.ZONE_DURATION] == 360
    assert coord._live_run_zones == {1}


async def test_without_the_weighting_the_live_run_is_unchanged():
    coord = _coordinator(forecast=_days(4.0), weighting=False)
    out = await coord._apply_live_durations([_zone()])
    assert out[0][const.ZONE_DURATION] == 600


async def test_a_forecast_that_covers_the_deficit_drops_the_zone():
    coord = _coordinator(forecast=_days(12.0))
    assert await coord._apply_live_durations([_zone()]) == []
    assert coord._live_run_zones == set()


async def test_the_decision_keeps_the_true_deficit():
    """The credit shortens the sizing only; the deficit the run reports (and the
    ranking and the log read) is still the actuals balance."""
    coord = _coordinator(forecast=_days(4.0))
    decision = coord._zone_run_decision(
        _zone(), {"1": {"live_deficit": -10.0}}, True, credit=4.0
    )
    assert decision.duration == 360
    assert decision.deficit == -10.0


async def test_rain_does_not_move_the_trigger():
    """The gate reads the true deficit: a credit never turns a zone that has not
    crossed its threshold into one that waters."""
    coord = _coordinator(forecast=_days(4.0), deficit=2.0)
    assert await coord._apply_live_durations([_zone()]) == []


async def test_a_flow_zone_keeps_the_daily_duration():
    """It already carries the weighting through ZONE_DURATION; weighting it again
    here would count the same rain twice."""
    coord = _coordinator(forecast=_days(4.0))
    zone = _zone(**{const.ZONE_FLOW_SENSOR: "sensor.flow"})
    out = await coord._apply_live_durations([zone])
    assert out[0] is zone


async def test_an_unreadable_forecast_waters_as_before_rather_than_aborting():
    coord = _coordinator(client_raises=True)
    out = await coord._apply_live_durations([_zone()])
    assert out[0][const.ZONE_DURATION] == 600


async def test_the_live_path_asks_the_same_rule_the_daily_balance_does():
    """One window rule: the credit the live run takes is the credit
    ``forecast_weighting_credit`` reports, from the run's own start."""
    coord = _coordinator(forecast=_days(4.0))
    assert await coord.forecast_weighting_credit(_zone(), run_start=NOW) == 4.0
    # A run a day later no longer sees the first day's rain.
    later = NOW + datetime.timedelta(days=1)
    assert await coord.forecast_weighting_credit(_zone(), run_start=later) == 0.0


async def test_the_panel_quotes_the_duration_the_run_will_use():
    """No-drift guard: the published live_duration is the dispatched one."""
    coord = _coordinator(forecast=_days(4.0))
    estimates = {"1": {"live_deficit": -10.0, "live_duration": 600}}
    await coord._credit_forecast_to_estimates([_zone()], estimates)
    run = await coord._apply_live_durations([_zone()])
    assert estimates["1"]["live_duration"] == run[0][const.ZONE_DURATION] == 360
    assert estimates["1"]["forecast_credit"] == 4.0
    # and the deficit itself is untouched
    assert estimates["1"]["live_deficit"] == -10.0


async def test_the_panel_figure_is_unweighted_when_the_setting_is_off():
    coord = _coordinator(forecast=_days(4.0), weighting=False)
    estimates = {"1": {"live_deficit": -10.0, "live_duration": 600}}
    await coord._credit_forecast_to_estimates([_zone()], estimates)
    assert estimates["1"]["live_duration"] == 600
    assert "forecast_credit" not in estimates["1"]


async def test_a_queued_zone_is_repriced_with_the_credit():
    """The mid-run re-price is the fourth reader of the decision; without the
    credit it would stretch a run the dispatch had shortened (it only ever
    shortens, so it would be left alone -- but it must still DROP a zone the
    forecast now covers)."""
    coord = _coordinator(forecast=_days(12.0))
    coord.store.get_zone = Mock(return_value=_zone())
    coord.async_refresh_zone_estimates_throttled = AsyncMock()
    coord.async_get_cached_zone_estimates = AsyncMock(
        return_value={"1": {"live_deficit": -10.0}}
    )
    assert await coord._resize_queued_zone(_zone(), True) is None


async def test_a_queued_zone_is_shortened_by_the_credit():
    coord = _coordinator(forecast=_days(4.0))
    coord.store.get_zone = Mock(return_value=_zone())
    coord.async_refresh_zone_estimates_throttled = AsyncMock()
    coord.async_get_cached_zone_estimates = AsyncMock(
        return_value={"1": {"live_deficit": -10.0}}
    )
    out = await coord._resize_queued_zone(_zone(**{const.ZONE_DURATION: 600}), True)
    assert out[const.ZONE_DURATION] == 360


async def test_a_flow_zone_is_not_even_asked_for_a_credit():
    """The decision would ignore it anyway; what this pins is that a flow zone
    costs no forecast read on every refresh."""
    coord = _coordinator(forecast=_days(4.0))
    coord.forecast_weighting_credit = AsyncMock(return_value=4.0)
    zone = _zone(**{const.ZONE_FLOW_SENSOR: "sensor.flow"})
    assert await coord._live_forecast_credits([zone], run_start=NOW) == {}
    coord.forecast_weighting_credit.assert_not_awaited()
