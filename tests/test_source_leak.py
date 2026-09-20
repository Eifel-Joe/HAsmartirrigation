"""A field mapped to a sensor must never carry the weather service's value (#149).

Megalos reported a live bucket rising ~7.5 mm on a day with 4.3 mm of rain, from a
sensor they then showed to be strictly monotonic apart from its midnight reset. It
was: the *sensor* never dips, but the *series in the buffer* does.

The merged poll row starts as the weather service's full row and sensor values are
laid over it, so any poll that cannot read the sensor keeps the weather service's
value under the same key. For precipitation the two are not even the same quantity
-- Open-Meteo reports the past hour's rain, a daily gauge reports a running total --
so one leaked reading makes a monotonic counter appear to fall, and a leaked 0.0 in a
dry hour looks exactly like a midnight reset.
"""

import datetime

import pytest

from custom_components.irrigation_plus import const
from custom_components.irrigation_plus.calculation import CalculationMixin
from custom_components.irrigation_plus.weather_aggregate import _aggregate


class _Coord(CalculationMixin):
    """Only the two merge helpers are exercised; nothing else is touched."""

    def __init__(self):
        pass


def _mapping(**sources):
    return {
        const.MAPPING_MAPPINGS: {
            key: {const.MAPPING_CONF_SOURCE: src} for key, src in sources.items()
        }
    }


SENSOR = const.MAPPING_CONF_SOURCE_SENSOR
SERVICE = const.MAPPING_CONF_SOURCE_WEATHER_SERVICE
STATIC = const.MAPPING_CONF_SOURCE_STATIC_VALUE


class TestTheWeatherServicesCopyIsDropped:
    def test_a_sensor_mapped_field_loses_the_weather_service_value(self):
        """The reported defect: Open-Meteo's hourly rain in a daily gauge's slot."""
        wd = {const.MAPPING_PRECIPITATION: 0.0, const.MAPPING_TEMPERATURE: 14.0}
        out = _Coord().strip_foreign_source_values(
            wd,
            _mapping(
                **{
                    const.MAPPING_PRECIPITATION: SENSOR,
                    const.MAPPING_TEMPERATURE: SERVICE,
                }
            ),
        )
        assert const.MAPPING_PRECIPITATION not in out
        assert out[const.MAPPING_TEMPERATURE] == 14.0

    def test_a_static_mapped_field_loses_it_too(self):
        wd = {const.MAPPING_WINDSPEED: 3.0}
        out = _Coord().strip_foreign_source_values(
            wd, _mapping(**{const.MAPPING_WINDSPEED: STATIC})
        )
        assert const.MAPPING_WINDSPEED not in out

    def test_a_weather_service_field_is_untouched(self):
        wd = {const.MAPPING_PRECIPITATION: 0.8}
        out = _Coord().strip_foreign_source_values(
            wd, _mapping(**{const.MAPPING_PRECIPITATION: SERVICE})
        )
        assert out[const.MAPPING_PRECIPITATION] == 0.8

    def test_a_field_the_group_does_not_map_is_untouched(self):
        wd = {const.MAPPING_CURRENT_PRECIPITATION: 0.4}
        out = _Coord().strip_foreign_source_values(wd, _mapping())
        assert out[const.MAPPING_CURRENT_PRECIPITATION] == 0.4

    def test_a_legacy_bare_string_mapping_claims_nothing(self):
        """The old stored shape carries no source, so it cannot claim the field."""
        wd = {const.MAPPING_PRECIPITATION: 0.8}
        out = _Coord().strip_foreign_source_values(
            wd, {const.MAPPING_MAPPINGS: {const.MAPPING_PRECIPITATION: "legacy"}}
        )
        assert out[const.MAPPING_PRECIPITATION] == 0.8

    def test_no_weather_data_and_no_mapping_are_handled(self):
        assert _Coord().strip_foreign_source_values(None, _mapping()) is None
        assert _Coord().strip_foreign_source_values({}, None) == {}


class TestTheReadableSensorStillWins:
    """Stripping must not disturb the happy path it runs in front of."""

    async def test_a_readable_sensor_value_is_laid_on_top_as_before(self):
        coord = _Coord()
        mapping = _mapping(
            **{
                const.MAPPING_PRECIPITATION: SENSOR,
                const.MAPPING_TEMPERATURE: SERVICE,
            }
        )
        wd = {const.MAPPING_PRECIPITATION: 0.0, const.MAPPING_TEMPERATURE: 14.0}
        wd = coord.strip_foreign_source_values(wd, mapping)
        merged = await coord.merge_weatherdata_and_sensor_values(
            wd, {const.MAPPING_PRECIPITATION: 4.3}
        )
        assert merged[const.MAPPING_PRECIPITATION] == 4.3
        assert merged[const.MAPPING_TEMPERATURE] == 14.0

    async def test_an_unreadable_sensor_leaves_the_field_absent(self):
        coord = _Coord()
        mapping = _mapping(**{const.MAPPING_PRECIPITATION: SENSOR})
        wd = coord.strip_foreign_source_values(
            {const.MAPPING_PRECIPITATION: 0.0}, mapping
        )
        merged = await coord.merge_weatherdata_and_sensor_values(wd, {})
        assert const.MAPPING_PRECIPITATION not in merged


def _credit(values):
    """What the DELTA aggregate books for a precipitation series."""
    t0 = datetime.datetime(2026, 9, 20, 6, 0, tzinfo=datetime.timezone.utc)
    samples = [(t0 + datetime.timedelta(hours=i), v) for i, v in enumerate(values)]
    out = {}
    _aggregate(
        {const.MAPPING_PRECIPITATION: samples},
        {const.MAPPING_PRECIPITATION: {const.MAPPING_CONF_SOURCE: SENSOR}},
        out,
        samples[0][0],
        samples[-1][0],
    )
    return out[const.MAPPING_PRECIPITATION]


class TestWhatTheLeakCostWhenItReachedTheAggregate:
    """Why the fix belongs at the merge: once stored, the row cannot be told apart.

    These pin the damage a leaked value still does if one ever reaches the buffer,
    which is the argument for dropping it at the source rather than guessing later.
    """

    def test_a_clean_monotonic_day_books_its_own_total(self):
        assert _credit([0.0, 1.0, 2.5, 3.4, 4.3]) == pytest.approx(4.3)

    def test_a_leaked_zero_in_a_dry_hour_recredits_the_whole_day(self):
        """6.8 mm booked for 4.3 mm: the reported symptom, and unfixable later."""
        assert _credit([0.0, 1.0, 2.5, 0.0, 3.4, 4.3]) == pytest.approx(6.8)

    def test_a_leaked_hourly_amount_mid_rain_is_held_off_by_the_high_water_mark(self):
        """Above the restart threshold, so it reads as a revision and costs nothing."""
        assert _credit([0.0, 1.0, 2.5, 0.8, 3.4, 4.3]) == pytest.approx(4.3)
