"""The live estimate's daily mirror of a pausing sensor group books what the commit does.

A zone whose commit runs the daily equation is estimated by that same equation
over the elapsed window. For a pausing group the commit books only the share of
the window in which every field of the daily form was measured, so the mirror
books that share too. A field silent for the whole window leaves nothing to book
-- which is an answer, not a reason to price the window from a weather service.
"""

from datetime import timedelta

import pytest

from custom_components.irrigation_plus import const
from custom_components.irrigation_plus.sensor_liveness import Outage
from tests.test_live_estimate_replayed_balance import (
    ANCHOR,
    WINDOW_END,
    _estimating_inputs,
    _estimating_zone,
    _hourly_forecast,
    _provider_rows,
    make_coordinator,
)

H = timedelta(hours=1)
T = const.MAPPING_TEMPERATURE


@pytest.fixture
async def coordinator(hass):
    """The shipped default: the hourly calculation off, the daily form runs."""
    return await make_coordinator(hass, hourly_calculation=False)


async def _silent(store, zone, start_h, end_h=None, fields=(T,)):
    await store.async_update_mapping(
        zone[const.ZONE_MAPPING],
        {
            const.MAPPING_ON_SILENT_SENSOR: const.ON_SILENT_SENSOR_PAUSE,
            const.MAPPING_SENSOR_OUTAGES: [
                Outage(
                    "sensor.t",
                    "dev1",
                    tuple(fields),
                    ANCHOR + start_h * H,
                    None if end_h is None else ANCHOR + end_h * H,
                ).to_store()
            ],
        },
    )


async def _committed(c, store, zone, now=WINDOW_END):
    zone = store.get_zone(zone[const.ZONE_ID])
    blocked = c._blocked_spans_for_zone(zone, now=now)
    weatherdata, _ = await c._aggregate_for_zone(zone, now=now, blocked=blocked)
    return await c.calculate_module(zone, weatherdata, None, now=now, blocked=blocked)


def _estimate(c, store, zone, instance, module, **inputs_kw):
    inputs = _estimating_inputs(instance, module, forecast=_hourly_forecast())
    inputs.update(inputs_kw)
    return c._intraday_for_zone(store.get_zone(zone[const.ZONE_ID]), inputs)


class TestTheMirrorBooksTheShare:
    async def test_it_lands_on_the_cut_bucket(self, coordinator):
        """Temperature silent from 4 h to 12 h after the anchor, frozen at 40 °C
        and stamped fresh by the poll: 7-12 h blocked."""
        c, store = coordinator
        zone, module, instance = await _estimating_zone(c, store, 2.0)
        store.set_mapping_buffer(
            zone[const.ZONE_MAPPING],
            [
                (
                    {**row, T: 40.0}
                    if ANCHOR + 7 * H <= row[const.RETRIEVED_AT] < ANCHOR + 12 * H
                    else row
                )
                for row in store.get_mapping_buffer(zone[const.ZONE_MAPPING])
            ],
        )
        uncut = await _committed(c, store, zone)
        await _silent(store, zone, 4, 12)

        est = _estimate(c, store, zone, instance, module)
        data = await _committed(c, store, zone)

        assert est["method"] == "daily_mirror"
        assert est["live_deficit"] == pytest.approx(
            round(data[const.ZONE_BUCKET], 2), abs=0.01
        )
        assert data[const.ZONE_BUCKET] > uncut[const.ZONE_BUCKET] + 0.3

    async def test_a_field_the_daily_form_does_without_changes_nothing(
        self, coordinator
    ):
        c, store = coordinator
        zone, module, instance = await _estimating_zone(c, store, 2.0)
        plain = _estimate(c, store, zone, instance, module)
        await _silent(store, zone, 4, 12, fields=(const.MAPPING_HUMIDITY,))
        assert _estimate(c, store, zone, instance, module) == plain


class TestNothingMeasuredIsNothingBooked:
    async def test_it_does_not_fall_back_to_a_weather_service(self, coordinator):
        """A client's hourly series is at hand, and would be the next source."""
        c, store = coordinator
        zone, module, instance = await _estimating_zone(c, store, 2.0)
        rows = _provider_rows(0.0)
        await _silent(store, zone, -4)

        est = _estimate(c, store, zone, instance, module, rows=rows, tz=0.0)
        data = await _committed(c, store, zone)

        assert est["method"] == "daily_mirror"
        assert est["et_since"] == 0.0
        assert est["live_deficit"] == pytest.approx(
            round(data[const.ZONE_BUCKET], 2), abs=0.01
        )

    async def test_a_zone_that_averages_forecast_days_in_needs_no_forecast_for_it(
        self, coordinator
    ):
        """The commit books 0 without asking for a forecast, so the mirror does too."""
        c, store = coordinator
        zone, module, instance = await _estimating_zone(c, store, 2.0)
        instance.forecast_days = 2
        rows = _provider_rows(0.0)
        await _silent(store, zone, -4)

        est = _estimate(c, store, zone, instance, module, rows=rows, tz=0.0)
        data = await _committed(c, store, zone)

        assert est["method"] == "daily_mirror"
        assert est["et_since"] == 0.0
        assert est["live_deficit"] == pytest.approx(
            round(data[const.ZONE_BUCKET], 2), abs=0.01
        )
