"""A pausing sensor group's commit: the gate, the cut, the booking and its explanation."""

import datetime
from datetime import timedelta
from unittest.mock import AsyncMock, Mock

import pytest
from homeassistant.util import dt as dt_util

from custom_components.irrigation_plus import SmartIrrigationCoordinator, const
from custom_components.irrigation_plus.sensor_liveness import Outage
from custom_components.irrigation_plus.store import SmartIrrigationStorage

W = datetime.datetime(2026, 7, 1, 0, 0, 0)  # the zone's watermark, naive on HA's clock
NOW = W + timedelta(hours=24)
H = timedelta(hours=1)
T = const.MAPPING_TEMPERATURE
PRECIP = const.MAPPING_PRECIPITATION


def _sensor(entity, aggregate=None):
    field = {
        const.MAPPING_CONF_SOURCE: const.MAPPING_CONF_SOURCE_SENSOR,
        const.MAPPING_CONF_SENSOR: entity,
    }
    if aggregate is not None:
        field[const.MAPPING_CONF_AGGREGATE] = aggregate
    return field


def _outage(start_h, end_h=None, fields=(T,)):
    return Outage(
        "sensor.t",
        "dev1",
        tuple(fields),
        W + start_h * H,
        None if end_h is None else W + end_h * H,
    ).to_store()


@pytest.fixture
async def coord(hass):
    """A real coordinator and store; the module is stubbed unless a test wires one."""
    hass.data[const.DOMAIN] = {
        const.CONF_USE_WEATHER_SERVICE: False,
        const.CONF_WEATHER_SERVICE: None,
    }
    store = SmartIrrigationStorage(hass)
    await store.async_load()
    entry = Mock()
    entry.unique_id = "t"
    entry.data = {}
    entry.options = {}
    c = SmartIrrigationCoordinator(hass, None, entry, store)
    c.store = store
    c.calculate_module = AsyncMock(
        return_value={const.ZONE_BUCKET: -1.0, const.ZONE_DURATION: 0}
    )
    return c, store


async def _group(store, *, setting="pause", outages=(), mappings=None, readings=None):
    created = await store.async_create_mapping(
        {
            const.MAPPING_NAME: "Garden",
            const.MAPPING_MAPPINGS: (
                mappings if mappings is not None else {T: _sensor("sensor.t")}
            ),
            const.MAPPING_DATA: (
                readings
                if readings is not None
                else [{const.RETRIEVED_AT: W + h * H, T: float(h)} for h in range(24)]
            ),
            const.MAPPING_ON_SILENT_SENSOR: setting,
            const.MAPPING_SENSOR_OUTAGES: list(outages),
        }
    )
    return created[const.MAPPING_ID]


async def _zone(store, mapping_id, *, module_id=1, watermark=W):
    created = await store.async_create_zone(
        {
            const.ZONE_NAME: "z",
            const.ZONE_MAPPING: mapping_id,
            const.ZONE_MODULE: module_id,
            const.ZONE_STATE: const.ZONE_STATE_AUTOMATIC,
            const.ZONE_BUCKET: 0.0,
            const.ZONE_MAXIMUM_BUCKET: 50.0,
            const.ZONE_DRAINAGE_RATE: 0.0,
            const.ZONE_THROUGHPUT: 10.0,
            const.ZONE_SIZE: 10.0,
            const.ZONE_MULTIPLIER: 1.0,
            const.ZONE_MAXIMUM_DURATION: 3600,
            const.ZONE_LEAD_TIME: 0,
            const.ZONE_LAST_CONSUMED: watermark,
        }
    )
    return created[const.ZONE_ID]


def _gate(c, store, zone_id):
    return c._blocked_spans_for_zone(store.get_zone(zone_id), now=NOW)


class TestTheGate:
    async def test_a_pausing_group_is_cut_where_its_outage_blocks(self, coord):
        c, store = coord
        zone = await _zone(store, await _group(store, outages=[_outage(2, 10)]))
        assert _gate(c, store, zone) == {T: ((W + 5 * H, W + 10 * H),)}

    async def test_a_group_that_keeps_is_not_cut(self, coord):
        c, store = coord
        mid = await _group(store, setting="keep", outages=[_outage(2, 10)])
        assert _gate(c, store, await _zone(store, mid)) is None

    async def test_with_the_hourly_calculation_nothing_is_cut(self, coord):
        c, store = coord
        await store.async_update_config({const.CONF_HOURLY_CALCULATION: True})
        mid = await _group(store, outages=[_outage(2, 10)])
        assert _gate(c, store, await _zone(store, mid)) is None

    async def test_a_window_no_outage_reaches_is_not_cut(self, coord):
        c, store = coord
        mid = await _group(store, outages=[_outage(-30, -20), _outage(2, 4)])
        assert _gate(c, store, await _zone(store, mid)) is None

    async def test_a_zone_that_never_consumed_is_not_cut(self, coord):
        c, store = coord
        mid = await _group(store, outages=[_outage(2, 10)])
        assert _gate(c, store, await _zone(store, mid, watermark=None)) is None

    async def test_a_zone_without_its_group_is_not_cut(self, coord):
        c, store = coord
        assert _gate(c, store, await _zone(store, 99)) is None
        assert c._blocked_spans_for_zone({const.ZONE_MAPPING: None}, now=NOW) is None

    async def test_a_rain_gauge_is_never_cut_and_a_rain_rate_is(self, coord):
        c, store = coord
        both = (T, PRECIP)
        gauge = await _group(
            store,
            mappings={T: _sensor("sensor.t"), PRECIP: _sensor("sensor.rain")},
            outages=[_outage(2, 10, fields=both)],
        )
        rate = await _group(
            store,
            mappings={
                T: _sensor("sensor.t"),
                PRECIP: _sensor("sensor.rain", const.MAPPING_CONF_AGGREGATE_RIEMANNSUM),
            },
            outages=[_outage(2, 10, fields=both)],
        )
        assert set(_gate(c, store, await _zone(store, gauge))) == {T}
        assert set(_gate(c, store, await _zone(store, rate))) == {T, PRECIP}

    async def test_outage_stamps_with_an_offset_are_read_on_has_clock(self, coord):
        """A record edited by hand, or written by another build, may carry offsets."""
        c, store = coord
        local = W.replace(tzinfo=dt_util.get_default_time_zone())
        record = {
            "entity_id": "sensor.t",
            "device_id": "dev1",
            "fields": [T],
            "start": (local + 2 * H).isoformat(),
            "end": (local + 10 * H).isoformat(),
        }
        zone = await _zone(store, await _group(store, outages=[record]))
        assert _gate(c, store, zone) == {T: ((W + 5 * H, W + 10 * H),)}


class TestTheCommitCarriesTheSpans:
    async def test_the_aggregate_and_both_records_are_cut(self, coord):
        c, store = coord
        zone = await _zone(store, await _group(store, outages=[_outage(2, 10)]))
        c._record_window_amplitude = AsyncMock()
        c._record_window_radiation = AsyncMock()

        await c.async_calculate_zone(zone, now=NOW)

        expected = {T: ((W + 5 * H, W + 10 * H),)}
        assert c._record_window_amplitude.call_args.kwargs["blocked"] == expected
        assert c._record_window_radiation.call_args.kwargs["blocked"] == expected
        weatherdata = c.calculate_module.call_args.args[1]
        # 0..23 without the frozen rows of hours 5..9.
        assert weatherdata[T] == pytest.approx(
            (sum(range(24)) - sum(range(5, 10))) / 19
        )

    async def test_a_group_that_keeps_aggregates_as_before(self, coord):
        c, store = coord
        mid = await _group(store, setting="keep", outages=[_outage(2, 10)])
        c._record_window_amplitude = AsyncMock()

        await c.async_calculate_zone(await _zone(store, mid), now=NOW)

        assert c._record_window_amplitude.call_args.kwargs["blocked"] is None
        assert c.calculate_module.call_args.args[1][T] == 11.5


class TestTheRecordsSkipABlockedWindow:
    async def test_no_amplitude_is_recorded_when_the_temperature_was_blocked(
        self, coord
    ):
        c, store = coord
        mid = await _group(store)
        zone = store.get_zone(await _zone(store, mid))
        data = {
            const.MAPPING_DATA_MULTIPLIER: 1.0,
            const.MAPPING_MIN_TEMP: 5.0,
            const.MAPPING_MAX_TEMP: 15.0,
        }

        await c._record_window_amplitude(
            zone, data, now=NOW, blocked={T: ((W, W + H),)}
        )
        assert store.get_mapping(mid)[const.MAPPING_TEMPERATURE_AMPLITUDES] == []

        other = {const.MAPPING_DEWPOINT: ((W, W + H),)}
        await c._record_window_amplitude(zone, data, now=NOW, blocked=other)
        assert store.get_mapping(mid)[const.MAPPING_TEMPERATURE_AMPLITUDES] == [
            [NOW.date().isoformat(), 10.0]
        ]

    async def test_no_radiation_pair_is_recorded_when_the_sun_was_blocked(self, coord):
        c, store = coord
        mid = await _group(store)
        zone = store.get_zone(await _zone(store, mid))
        c._effective_latitude = 40.0
        c._effective_longitude = 0.0
        data = {const.MAPPING_SOLRAD: 15.0}
        sun = {const.MAPPING_SOLRAD: ((W, W + H),)}

        await c._record_window_radiation(zone, data, now=NOW, blocked=sun)
        assert store.get_mapping(mid)[const.MAPPING_RADIATION_CALIBRATION] == []

        await c._record_window_radiation(
            zone, data, now=NOW, blocked={T: ((W, W + H),)}
        )
        assert len(store.get_mapping(mid)[const.MAPPING_RADIATION_CALIBRATION]) == 1
