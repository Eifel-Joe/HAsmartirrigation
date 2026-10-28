### Task 4: Wiedergabe leise loggen (C4, Open-Meteo und Met Office)

**Files:** Modify `fetch_gate.py`; `OpenMeteoClient.py:201`, `:311`, `:478`; `MetOfficeClient.py:466`, `:569`.
Test: `tests/test_weather_clients_fetch_gate.py`.

**Interfaces:**
- Consumes: `is_replay` (Task 3).
- Produces: `failure_log_level(exc: BaseException) -> int` = `logging.DEBUG` für eine Wiedergabe, sonst `logging.ERROR`.

- [ ] **Step 1: Test schreiben**

```python
@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
def test_a_replayed_failure_logs_nothing_above_debug(case, caplog):
    # first call with _failing(500) (no assertion on its logs: OWM's forecast lets its OSError
    # out unlogged); caplog.clear(); second call inside the pause (tick(30)) → outcome as before, and
    assert not [r for r in caplog.records
                if r.name.startswith("custom_components.irrigation_plus.weathermodules") and r.levelno > logging.DEBUG]
```

- [ ] **Step 2: Rot sehen** — Erwartet: FAILED für `openmeteo_doc`, `met_hourly`, `met_three_hourly` (ERROR-Zeile
  „… error: 500“); grün für OWM und Pirate (deren Body läuft in der Pause nicht).
- [ ] **Step 3:** Die fünf Stellen auf `_LOGGER.log(failure_log_level(ex), "<unveränderte Meldung>", ex)` umstellen.
- [ ] **Step 4: Grün sehen** — beide neuen Dateien plus `tests/test_weather_modules.py`. Erwartet: grün.
- [ ] **Step 5: Commit** — `fix(weather): a replayed failure is logged at DEBUG, not as a fresh error`.

---

