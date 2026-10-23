"""Every fetch point of the four weather clients, one table, one door.

``CASES`` names each of the seven places where a client goes to the network:
how to build the client, which call reaches the fetch point, a body the fetch
point accepts, and the attribute that holds the time of the last good fetch.
The tests below run over that table.
"""

import dataclasses
import json
import pathlib
from collections.abc import Callable
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
import requests

from custom_components.irrigation_plus.weathermodules.MetOfficeClient import (
    MetOfficeClient,
)
from custom_components.irrigation_plus.weathermodules.OpenMeteoClient import (
    OpenMeteoClient,
)
from custom_components.irrigation_plus.weathermodules.OWMClient import OWMClient
from custom_components.irrigation_plus.weathermodules.PirateWeatherClient import (
    PirateWeatherClient,
)

from . import test_weather_modules as twm

M = "custom_components.irrigation_plus.weathermodules."

_PIRATE_FIXTURE = (
    pathlib.Path(__file__).parent / "fixtures" / "pirate_weather_berlin.json"
)


@dataclasses.dataclass(frozen=True)
class GateCase:
    """One fetch point of one client."""

    id: str
    patch: str  # the session call the fetch point makes
    make: Callable[[], Any]  # a fresh client
    call: Callable[[Any], Any]  # the public call that reaches the fetch point
    ok_body: dict  # a body the fetch point accepts
    stamp: str  # attribute holding the time of the last good fetch
    failed_attempts: int  # requests one failed run makes with status 500


def _ok(body):
    """A 200 response carrying ``body``."""
    response = MagicMock()
    response.status_code = 200
    response.text = json.dumps(body)
    response.headers = {}
    return response


def _failing(status, headers=None):
    """A response with ``status`` whose ``raise_for_status`` raises ``HTTPError``."""
    response = MagicMock()
    response.status_code = status
    response.text = "{}"
    response.headers = {} if headers is None else headers
    response.raise_for_status.side_effect = requests.HTTPError(
        str(status), response=response
    )
    return response


def _owm():
    return OWMClient(api_key="k", latitude=1.0, longitude=2.0, elevation=0)


def _pirate():
    return PirateWeatherClient("key", "1", 52.0, 5.0, 0)


def _open_meteo():
    return OpenMeteoClient(latitude=1.0, longitude=2.0)


def _met_office():
    return MetOfficeClient(api_key="k", latitude=1.0, longitude=2.0)


_PIRATE_BODY = json.loads(_PIRATE_FIXTURE.read_text(encoding="utf-8"))

CASES: list[GateCase] = [
    GateCase(
        "owm_data",
        M + "OWMClient._SESSION.get",
        _owm,
        lambda c: c.get_data(),
        twm.TestOWMClientCaching._CURRENT_BODY,
        "_cached_data_at",
        1,
    ),
    GateCase(
        "owm_forecast",
        M + "OWMClient._SESSION.get",
        _owm,
        lambda c: c.get_forecast_data(),
        twm.TestOWMClientGetForecastData()._forecast_body(),
        "_cached_forecast_at",
        1,
    ),
    GateCase(
        "pirate_data",
        M + "PirateWeatherClient._SESSION.get",
        _pirate,
        lambda c: c.get_data(),
        _PIRATE_BODY,
        "_cached_data_at",
        3,
    ),
    GateCase(
        "pirate_forecast",
        M + "PirateWeatherClient._SESSION.get",
        _pirate,
        lambda c: c.get_forecast_data(),
        _PIRATE_BODY,
        "_cached_forecast_at",
        3,
    ),
    GateCase(
        "openmeteo_doc",
        M + "OpenMeteoClient._SESSION.get",
        _open_meteo,
        lambda c: c.get_forecast_data(),
        {"hourly": {"time": []}, "daily": {"time": []}},
        "_cached_doc_at",
        1,
    ),
    GateCase(
        "met_hourly",
        M + "MetOfficeClient._SESSION.get",
        _met_office,
        lambda c: c.get_data(),
        twm._met_doc([]),
        "_cached_hourly_at",
        1,
    ),
    GateCase(
        "met_three_hourly",
        M + "MetOfficeClient._SESSION.get",
        _met_office,
        lambda c: c.get_forecast_data(),
        twm._met_doc([]),
        "_cached_three_hourly_at",
        1,
    ),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
def test_every_client_asks_the_shared_freshness_check(case):
    client = case.make()
    get = MagicMock(return_value=_ok(case.ok_body))
    with patch(case.patch, get), patch(M + "fetch_gate.is_fresh", return_value=False):
        case.call(client)
        case.call(client)
    # Without the shared check the second call is a cache hit.
    assert get.call_count == 2
