### Task 1: Gemeinsame Frische-Prüfung (`Eifel-Joe#20`, keine Verhaltensänderung)

**Files:**
- Create: `custom_components/irrigation_plus/weathermodules/fetch_gate.py`
- Modify: `OWMClient.py:32-37` (Konstante), `:85-90` (`_is_fresh` weg), `:106`, `:247`;
  `PirateWeatherClient.py:39`, `:138-143`, `:235`, `:341`; `OpenMeteoClient.py:33-39`, `:96-102`;
  `MetOfficeClient.py:62`, `:129-134`, `:231`, `:239`, `:321-323`
- Test: `tests/test_weather_fetch_gate.py`, `tests/test_weather_clients_fetch_gate.py`

**Interfaces:**
- Produces: `MIN_CACHE_SECONDS: int = 60`; `cache_lifetime(cache_seconds: float) -> float`;
  `is_fresh(fetched_at: datetime.datetime | None, cache_seconds: float, override_cache: bool) -> bool` (Semantik wie das
  heutige `_is_fresh`: `None` oder `override_cache` → False, sonst `now < fetched_at + cache_lifetime`).
- Produces (Testdatei): in `tests/test_weather_clients_fetch_gate.py` die Tabelle `CASES` (siehe Step 1), die Tasks 2–6
  nutzen.

- [ ] **Step 1: Testtabelle und Tests schreiben**

`tests/test_weather_clients_fetch_gate.py` bekommt `CASES: list[GateCase]` (frozen dataclass mit `id`, `patch`,
`make`, `call`, `ok_body`, `stamp`, `failed_attempts`) und die Helfer `_ok(body)` und
`_failing(status, headers=None)`: MagicMock mit `status_code`, `text`, `headers` (echtes `dict`) und
`raise_for_status.side_effect = requests.HTTPError(str(status), response=<derselbe Mock>)`. `M` = 
`"custom_components.irrigation_plus.weathermodules."`, `twm` = `tests.test_weather_modules` als Modul.

| `id` | `patch` | `make()` | `call(c)` | `ok_body` | `stamp` | `failed_attempts` (Status 500) |
|---|---|---|---|---|---|---|
| `owm_data` | `M+"OWMClient._SESSION.get"` | `OWMClient(api_key="k", latitude=1.0, longitude=2.0, elevation=0)` | `c.get_data()` | `twm.TestOWMClientCaching._CURRENT_BODY` | `_cached_data_at` | 1 |
| `owm_forecast` | dito | dito | `c.get_forecast_data()` | `twm.TestOWMClientGetForecastData()._forecast_body()` | `_cached_forecast_at` | 1 |
| `pirate_data` | `M+"PirateWeatherClient._SESSION.get"` | `PirateWeatherClient("key", "1", 52.0, 5.0, 0)` | `c.get_data()` | `json.loads(tests/fixtures/pirate_weather_berlin.json)` | `_cached_data_at` | 3 |
| `pirate_forecast` | dito | dito | `c.get_forecast_data()` | dito | `_cached_forecast_at` | 3 |
| `openmeteo_doc` | `M+"OpenMeteoClient._SESSION.get"` | `OpenMeteoClient(latitude=1.0, longitude=2.0)` | `c.get_forecast_data()` | `{"hourly": {"time": []}, "daily": {"time": []}}` | `_cached_doc_at` | 1 |
| `met_hourly` | `M+"MetOfficeClient._SESSION.get"` | `MetOfficeClient(api_key="k", latitude=1.0, longitude=2.0)` | `c.get_data()` | `twm._met_doc([])` | `_cached_hourly_at` | 1 |
| `met_three_hourly` | dito | dito | `c.get_forecast_data()` | `twm._met_doc([])` | `_cached_three_hourly_at` | 1 |

Probe vom 2026-10-23 auf `c46c41fc` (`issue89-work\probe\probe_cases.py`): alle sieben `ok_body` setzen den Zeitstempel;
Status 500 → OWM wirft `OSError`, Pirate gibt `None` nach 3 Versuchen, Open-Meteo/Met Office geben am Zugriff `None`
(Ausnahme im `_fetch*`); `requests.ConnectionError` → OWM `get_data` und Pirate `get_data` werfen, die übrigen geben `None`.

Tests:

```python
# tests/test_weather_fetch_gate.py
def test_cache_lifetime_has_a_floor_of_sixty_seconds():
    assert cache_lifetime(0) == 60 and cache_lifetime(59) == 60 and cache_lifetime(599) == 599

@freeze_time("2026-10-23 12:00:00")
def test_is_fresh_matches_the_clients_old_rule():
    now = datetime.datetime.now()
    assert is_fresh(None, 599, False) is False
    assert is_fresh(now, 599, True) is False                      # override_cache
    assert is_fresh(now - timedelta(seconds=598), 599, False) is True
    assert is_fresh(now - timedelta(seconds=599), 599, False) is False
    assert is_fresh(now - timedelta(seconds=59), 0, False) is True  # floor

# tests/test_weather_clients_fetch_gate.py
@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
def test_every_client_asks_the_shared_freshness_check(case):
    client = case.make()
    get = MagicMock(return_value=_ok(case.ok_body))
    with patch(case.patch, get), patch(M + "fetch_gate.is_fresh", return_value=False):
        case.call(client); case.call(client)
    assert get.call_count == 2            # without the shared check the second call is a cache hit
```

- [ ] **Step 2: Rot sehen** — `TZ=UTC $PY -m pytest tests/test_weather_fetch_gate.py tests/test_weather_clients_fetch_gate.py -p _local_socket_unblock -q --no-header`
  Erwartet: `test_weather_fetch_gate.py` bricht beim Sammeln mit `ModuleNotFoundError: …weathermodules.fetch_gate`
  ab; in `test_weather_clients_fetch_gate.py` scheitern alle sieben Fälle am Patch-Ziel `…fetch_gate.is_fresh`.
- [ ] **Step 3: `fetch_gate.py` anlegen und die vier Clients umstellen.** Die Clients rufen
  `fetch_gate.is_fresh(...)` über das **Modul** (`from . import fetch_gate`), damit der Patch im Test greift; die drei
  `_is_fresh`-Methoden und die vier `_MIN_CACHE_SECONDS` entfallen; Open-Meteo `_fetch` prüft per `is_fresh`;
  `_forecast_document` nimmt `cache_lifetime(self.cache_seconds)`. Den Kommentar `OWMClient.py:32-36` an die Konstante
  in `fetch_gate.py` mitnehmen.
- [ ] **Step 4: Grün sehen** — dieselben zwei Dateien plus `tests/test_weather_modules.py tests/test_pirateweather_daily.py
  tests/test_met_office_forecast_document.py tests/test_precipitation_guard_real_clients.py`. Erwartet: alles grün.
- [ ] **Step 5: Commit** — `refactor(weather): one freshness check shared by the four weather clients` (Body: die
  Prüfung war dreimal byte-gleich und einmal inline; die Lebensdauer wurde zweimal gerechnet; keine Verhaltensänderung).

---

