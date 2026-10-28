### Task 2: Ein Abruf je Tor (C1, C2)

**Files:**
- Modify: `fetch_gate.py`; `OWMClient.py:104`, `:240`, `__init__`; `PirateWeatherClient.py:233`, `:339`, `__init__`;
  `OpenMeteoClient.py:88`, `__init__`; `MetOfficeClient.py:230`, `:238`, `__init__`
- Test: beide Testdateien

**Interfaces:**
- Consumes: `is_fresh`, `cache_lifetime` (Task 1).
- Produces: `class FetchGate: __init__(self, owner: Any, stamp_attr: str) -> None`, `run(self, fetch: Callable[[], T]) -> T`.
  Tore als Attribute am Ende jedes `__init__`: OWM/Pirate `_data_gate = FetchGate(self, "_cached_data_at")`,
  `_forecast_gate = FetchGate(self, "_cached_forecast_at")`; Open-Meteo `_doc_gate = FetchGate(self, "_cached_doc_at")`;
  Met Office `_hourly_gate = FetchGate(self, "_cached_hourly_at")`, `_three_hourly_gate = FetchGate(self, "_cached_three_hourly_at")`.
  Bodies (heutiger Methodeninhalt, unverändert, nur umbenannt): OWM/Pirate `_fetch_data`, `_fetch_forecast`;
  Open-Meteo `_fetch_doc`; Met Office `_fetch_hourly_doc`, `_fetch_three_hourly_doc`. Die alten Namen bleiben als
  Einzeiler mit ihrem Docstring: `return self._data_gate.run(self._fetch_data)` usw.

- [ ] **Step 1: Tests schreiben**

```python
# tests/test_weather_clients_fetch_gate.py
@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
def test_concurrent_callers_make_one_request(case):
    # get blocks on `release` (Event); 5 threads call case.call(client); main waits until
    # get.call_count >= 1, sleeps 0.2 s, sets `release`, joins all (timeout 5, none alive)
    assert get.call_count == 1
    assert getattr(client, case.stamp) is not None
    assert len({repr(r) for r in results}) == 1           # everyone got the same answer

# tests/test_weather_fetch_gate.py — fake owner: cache_seconds, override_cache, stamp, and
# fetch_ok/fetch_none/fetch_raise that serve their cache when is_fresh(stamp, …), else count a call
def test_run_serialises_two_threads_onto_one_fetch(): ...   # owner.calls == 1
```

- [ ] **Step 2: Rot sehen** — Erwartet: `test_concurrent_callers_make_one_request` FAILED in allen sieben Fällen mit
  `assert 5 == 1` (Pirate/OWM/Open-Meteo/Met Office gleich), der Einheitstest mit `AttributeError`/`ImportError`.
- [ ] **Step 3: `FetchGate` mit `threading.Lock` und `run` = Sperre um `fetch()`; die sieben Stellen umstellen.** Die
  Frische-Prüfung im Body läuft damit innerhalb der Sperre: Wer wartet, findet danach den frischen Eintrag (C2).
  Code-doku-Kommentar an der Sperre (Wurzel: 19 Abrufe in 0,6 s; Fix-Logik; NOT-TO-DO: keine `asyncio`-Sperre, keine
  Sperre nur um die Anfrage).
- [ ] **Step 4: Grün sehen** — beide neuen Dateien plus die vier Client-Testdateien aus Task 1 Step 4. Erwartet: grün.
- [ ] **Step 5: Commit** — `fix(weather): concurrent callers wait for one fetch instead of each fetching`.

---

