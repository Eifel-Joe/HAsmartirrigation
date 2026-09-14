"""PyETO prices each day's weather with the sun of that day.

Extraterrestrial and clear-sky radiation depend on the day of the year, and with
an estimated solar radiation so does the whole Penman-Monteith result. The day
comes from the caller, as the day the weather belongs to; only a call without a
day falls back to the clock.
"""

import datetime
from statistics import mean

import pytest
from freezegun import freeze_time

from custom_components.irrigation_plus.calcmodules.pyeto import (
    MAPPING_DEWPOINT,
    MAPPING_MAX_TEMP,
    MAPPING_MIN_TEMP,
    MAPPING_PRESSURE,
    MAPPING_WINDSPEED,
    PyETO,
    SOLRAD_behavior,
)
from custom_components.irrigation_plus.const import (
    CONF_PYETO_FORECAST_DAYS,
    CONF_PYETO_SOLRAD_BEHAVIOR,
)

SUMMER_SOLSTICE = datetime.date(2026, 6, 21)
WINTER_SOLSTICE = datetime.date(2026, 12, 21)
# Around an equinox the solar declination changes fastest, so neighbouring days
# price the same weather measurably differently.
SPRING_EQUINOX = datetime.date(2026, 3, 20)


def _module(hass, forecast_days=0):
    return PyETO(
        hass,
        description="",
        config={
            # Estimated radiation, so the day of the year reaches the result
            # through the extraterrestrial radiation.
            CONF_PYETO_SOLRAD_BEHAVIOR: SOLRAD_behavior.EstimateFromTemp.value,
            CONF_PYETO_FORECAST_DAYS: forecast_days,
        },
    )


def _weather():
    # Every reading calculate_et_for_day requires; the solar radiation is
    # estimated from the temperatures.
    return {
        MAPPING_DEWPOINT: 12.0,
        MAPPING_MIN_TEMP: 14.0,
        MAPPING_MAX_TEMP: 28.0,
        MAPPING_WINDSPEED: 1.5,
        MAPPING_PRESSURE: 977.0,
    }


def _forecast():
    return {
        MAPPING_DEWPOINT: 9.0,
        MAPPING_MIN_TEMP: 11.0,
        MAPPING_MAX_TEMP: 24.0,
        MAPPING_WINDSPEED: 3.0,
        MAPPING_PRESSURE: 1005.0,
    }


class TestTheDayOfTheWeather:
    def test_the_same_weather_evaporates_more_in_june_than_in_december(self, hass):
        modinst = _module(hass)

        june = modinst.calculate_et_for_day(_weather(), day=SUMMER_SOLSTICE)
        december = modinst.calculate_et_for_day(_weather(), day=WINTER_SOLSTICE)

        # The delta is the negative ET, so more evaporation is the lower value.
        assert june < december

    def test_a_given_day_prices_like_the_clock_on_that_day(self, hass):
        modinst = _module(hass)

        with freeze_time(WINTER_SOLSTICE):
            by_clock = modinst.calculate_et_for_day(_weather())
        by_day = modinst.calculate_et_for_day(_weather(), day=WINTER_SOLSTICE)

        assert by_day == by_clock


class TestTheForecastDays:
    def test_each_forecast_entry_is_priced_one_day_further_out(self, hass):
        modinst = _module(hass, forecast_days=2)
        day = SPRING_EQUINOX
        first = SPRING_EQUINOX + datetime.timedelta(days=3)

        combined = modinst.calculate(
            _weather(), [_forecast(), _forecast()], day=day, forecast_first_day=first
        )

        assert combined == pytest.approx(
            mean(
                [
                    modinst.calculate_et_for_day(_weather(), day=day),
                    modinst.calculate_et_for_day(_forecast(), day=first),
                    modinst.calculate_et_for_day(
                        _forecast(), day=first + datetime.timedelta(days=1)
                    ),
                ]
            )
        )

    def test_without_a_first_forecast_day_the_forecast_starts_the_day_after(self, hass):
        modinst = _module(hass, forecast_days=1)
        day = SPRING_EQUINOX

        combined = modinst.calculate(_weather(), [_forecast()], day=day)

        assert combined == pytest.approx(
            mean(
                [
                    modinst.calculate_et_for_day(_weather(), day=day),
                    modinst.calculate_et_for_day(
                        _forecast(), day=day + datetime.timedelta(days=1)
                    ),
                ]
            )
        )

    def test_without_any_day_the_forecast_starts_tomorrow(self, hass):
        modinst = _module(hass, forecast_days=1)

        with freeze_time(SPRING_EQUINOX):
            combined = modinst.calculate(_weather(), [_forecast()])

        assert combined == pytest.approx(
            mean(
                [
                    modinst.calculate_et_for_day(_weather(), day=SPRING_EQUINOX),
                    modinst.calculate_et_for_day(
                        _forecast(),
                        day=SPRING_EQUINOX + datetime.timedelta(days=1),
                    ),
                ]
            )
        )
