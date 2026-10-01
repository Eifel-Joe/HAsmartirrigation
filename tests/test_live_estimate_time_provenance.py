"""Which zone the live estimate reads each kind of naive timestamp in.

Two kinds reach it:

- **stored** stamps (`last_calculated`, `last_consumed_at`) are written on HA's clock
  (``local_naive_now()``), and the store's 14.2 migration moved the ones older
  releases wrote on the PROCESS's clock;
- **client** rows (the hourly forecast series) are site-local clock times off a
  weather API, so naive means HA's configured zone, and always did.

Both therefore read in HA's zone. The stored half used to be wrong: a bare
``datetime.now()`` wrote the process's clock, and on a container without ``TZ=`` this
reader was the whole UTC offset off.
"""

import datetime
import zoneinfo
from unittest.mock import AsyncMock, Mock

import pytest
from homeassistant.util import dt as dt_util

from custom_components.irrigation_plus import helpers, live_estimate

UTC = datetime.timezone.utc
BERLIN = zoneinfo.ZoneInfo("Europe/Berlin")


@pytest.fixture
def split_zones(monkeypatch):
    """Container at UTC, user at Europe/Berlin: the process's clock is not HA's.

    HA's own setter is used and the zone is restored to UTC rather than to whatever
    was found: the test plugin's cleanup asserts UTC at teardown.
    """
    monkeypatch.setattr(helpers, "_process_timezone", lambda: UTC)
    dt_util.set_default_time_zone(BERLIN)
    yield
    dt_util.set_default_time_zone(UTC)


def test_a_client_forecast_row_is_read_in_ha_local(split_zones):
    """An aware forecast row lands on HA's clock, which is correct and stays.

    A weather API answers in the site's own local time. 10:00 UTC is 12:00 for a user
    in Berlin, and 12:00 is the hour their zone is being priced for.
    """
    aware = datetime.datetime(2026, 9, 21, 10, 0, tzinfo=UTC)

    got = helpers.coerce_stamp(aware, helpers.STAMP_FROM_CLIENT)

    assert got == datetime.datetime(2026, 9, 21, 12, 0)


def test_a_stored_stamp_is_read_on_has_clock(split_zones):
    """The store now holds what this reader always assumed.

    ``_parse_stored_as_ha_local`` reads a stored stamp as HA-local: an aware value
    through ``dt_util.as_local``, a naive one as it is. Stamps used to be written on the
    process's clock, so on a container without ``TZ=`` that was the whole UTC offset
    off. Written on HA's clock now, and migrated there at 14.2, the reading is right --
    and the store provenance gives the same answer.
    """
    aware = datetime.datetime(2026, 9, 21, 10, 0, tzinfo=UTC)

    got = live_estimate._parse_stored_as_ha_local(aware)

    assert got == datetime.datetime(2026, 9, 21, 12, 0)
    assert helpers.coerce_stamp(aware, helpers.STAMP_FROM_STORE) == got


def test_a_naive_stored_stamp_passes_through_either_way(split_zones):
    """Every stored stamp is naive, and a naive value is already in the frame.

    Both rules leave it alone. What put a naive stamp in the right frame is the write
    side and the store migration, not this reader -- which is why the defect was
    invisible here while it lasted.
    """
    naive = datetime.datetime(2026, 9, 21, 10, 0)

    assert live_estimate._parse_stored_as_ha_local(naive) == naive
    assert helpers.coerce_stamp(naive, helpers.STAMP_FROM_STORE) == naive
    assert helpers.coerce_stamp(naive, helpers.STAMP_FROM_CLIENT) == naive


def test_a_stored_stamp_beyond_the_datetime_range_is_no_stamp(split_zones):
    """An aware stamp at the edge of the range has no local form: no stamp, no raise.

    Raised, it would reach the live estimate's blanket ``except`` and switch the
    estimate off.
    """
    edge = "9999-12-31T23:59:59+00:00"

    assert live_estimate._parse_stored_as_ha_local(edge) is None
    assert helpers.coerce_stamp(edge, helpers.STAMP_FROM_STORE) is None


class TestTheForecastReadersUseTheClientRule:
    """The three row conversions, exercised THROUGH the functions that hold them.

    They sit behind ``if when.tzinfo is not None``, so only an aware forecast row
    reaches them, and no other fixture in this file supplies one. An aware row lands on
    HA's clock, the hour the zone is priced for. Both provenances read an aware stamp
    alike since that branch moved to HA's clock, so what these pin is the reading at
    the three call sites, not the name they pass.
    """

    @staticmethod
    def _client(method, rows):
        client = type("FakeClient", (), {})()
        setattr(client, method, lambda: rows)
        return client

    def test_the_precipitation_reader_localises_to_ha(self, split_zones):
        rows = [(datetime.datetime(2026, 9, 21, 10, 0, tzinfo=UTC), 1.5)]
        client = self._client("get_hourly_precipitation_forecast", rows)

        out = live_estimate.LiveEstimateMixin._hourly_forecast_precipitation(client)

        assert out == [(datetime.datetime(2026, 9, 21, 12, 0), 1.5)]

    def test_the_temperature_reader_localises_to_ha(self, split_zones):
        rows = [(datetime.datetime(2026, 9, 21, 10, 0, tzinfo=UTC), 17.0)]
        client = self._client("get_hourly_temperature_forecast", rows)

        out = live_estimate.LiveEstimateMixin._hourly_forecast_temperatures(client)

        assert out == [(datetime.datetime(2026, 9, 21, 12, 0), 17.0)]

    async def test_the_weather_entity_reader_localises_to_ha(self, split_zones):
        """The third site: the rows ``weather.get_forecasts`` returns, as ISO strings."""
        entries = [
            {"datetime": "2026-09-21T10:00:00+00:00", "temperature": 17.0},
            {"datetime": "2026-09-21T11:00:00+00:00", "temperature": 18.0},
        ]
        hass = Mock()
        hass.states.get = Mock(return_value=Mock(attributes={}))
        hass.services.async_call = AsyncMock(
            return_value={"weather.home": {"forecast": entries}}
        )
        host = type("Host", (), {"hass": hass})()

        out = await live_estimate.LiveEstimateMixin._read_hourly_forecast(
            host, "weather.home"
        )

        assert out == [
            (datetime.datetime(2026, 9, 21, 12, 0), 17.0),
            (datetime.datetime(2026, 9, 21, 13, 0), 18.0),
        ]

    def test_a_naive_forecast_row_is_left_alone(self, split_zones):
        """The branch is guarded on ``tzinfo``, so a naive row never reaches it.

        A naive row is already in the frame every reader shares, HA's wall clock, so
        nothing may shift it.
        """
        naive = datetime.datetime(2026, 9, 21, 12, 0)
        client = self._client("get_hourly_precipitation_forecast", [(naive, 1.5)])

        out = live_estimate.LiveEstimateMixin._hourly_forecast_precipitation(client)

        assert out == [(naive, 1.5)]
