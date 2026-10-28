"""Probe: success and failure outcome of each of the seven fetch points on c46c41fc."""
import json, pathlib, sys
from unittest.mock import MagicMock, patch
import requests

sys.path.insert(0, str(pathlib.Path.cwd()))
sys.path.insert(0, str(pathlib.Path.cwd() / "tests"))
from custom_components.irrigation_plus.weathermodules.OWMClient import OWMClient
from custom_components.irrigation_plus.weathermodules.PirateWeatherClient import PirateWeatherClient
from custom_components.irrigation_plus.weathermodules.OpenMeteoClient import OpenMeteoClient
from custom_components.irrigation_plus.weathermodules.MetOfficeClient import MetOfficeClient
from test_weather_modules import TestOWMClientCaching, TestOWMClientGetForecastData, _met_doc

M = "custom_components.irrigation_plus.weathermodules."
pirate_doc = json.loads((pathlib.Path("tests/fixtures/pirate_weather_berlin.json")).read_text())

def resp(status, body):
    m = MagicMock(); m.status_code = status; m.text = json.dumps(body); m.headers = {}
    if status != 200:
        m.raise_for_status.side_effect = requests.HTTPError(f"{status}", response=m)
    return m

cases = [
    ("owm_data", M+"OWMClient._SESSION.get", lambda: OWMClient(api_key="k", latitude=1.0, longitude=2.0, elevation=0), lambda c: c.get_data(), TestOWMClientCaching._CURRENT_BODY, "_cached_data_at"),
    ("owm_forecast", M+"OWMClient._SESSION.get", lambda: OWMClient(api_key="k", latitude=1.0, longitude=2.0, elevation=0), lambda c: c.get_forecast_data(), TestOWMClientGetForecastData()._forecast_body(), "_cached_forecast_at"),
    ("pirate_data", M+"PirateWeatherClient._SESSION.get", lambda: PirateWeatherClient("key", "1", 52.0, 5.0, 0), lambda c: c.get_data(), pirate_doc, "_cached_data_at"),
    ("pirate_forecast", M+"PirateWeatherClient._SESSION.get", lambda: PirateWeatherClient("key", "1", 52.0, 5.0, 0), lambda c: c.get_forecast_data(), pirate_doc, "_cached_forecast_at"),
    ("openmeteo_doc", M+"OpenMeteoClient._SESSION.get", lambda: OpenMeteoClient(latitude=1.0, longitude=2.0), lambda c: c.get_forecast_data(), {"hourly": {"time": []}, "daily": {"time": []}}, "_cached_doc_at"),
    ("met_hourly", M+"MetOfficeClient._SESSION.get", lambda: MetOfficeClient(api_key="k", latitude=1.0, longitude=2.0), lambda c: c.get_data(), _met_doc([]), "_cached_hourly_at"),
    ("met_three_hourly", M+"MetOfficeClient._SESSION.get", lambda: MetOfficeClient(api_key="k", latitude=1.0, longitude=2.0), lambda c: c.get_forecast_data(), _met_doc([]), "_cached_three_hourly_at"),
]

def outcome(fn):
    try:
        v = fn(); return ("returned", type(v).__name__, v if v is None else "…")
    except Exception as e:
        return ("raised", type(e).__name__, str(e)[:50])

for cid, target, make, call, ok, stamp in cases:
    c = make()
    with patch(target, MagicMock(return_value=resp(200, ok))) as g:
        o = outcome(lambda: call(c))
    print(f"{cid:17s} OK   stamp_set={getattr(c, stamp) is not None} calls={g.call_count} {o}")
    c = make()
    with patch(target, MagicMock(return_value=resp(500, {}))) as g:
        o = outcome(lambda: call(c))
    print(f"{cid:17s} 500  stamp_set={getattr(c, stamp) is not None} calls={g.call_count} {o}")
    c = make()
    with patch(target, MagicMock(side_effect=requests.ConnectionError("down"))) as g:
        o = outcome(lambda: call(c))
    print(f"{cid:17s} CONN stamp_set={getattr(c, stamp) is not None} calls={g.call_count} {o}")
