### Task 3: Pause nach dem Fehlschlag (C3, C4 Rückgabe, C5, C7, C10, C11)

**Files:** Modify `fetch_gate.py`; Test: beide Testdateien.

**Interfaces:**
- Produces: `FIRST_PAUSE_SECONDS = 60`; `is_replay(exc: BaseException) -> bool` (liest das Merkmal
  `_fetch_gate_replay`); `FetchGate` hält `_failures: int`, `_failed_at: float | None` (monoton), `_outcome`
  (`(raised: bool, value)`), `_retry_after: float = 0.0` (bleibt bis Task 5 null).

- [ ] **Step 1: Tests schreiben**

Einheit (`tests/test_weather_fetch_gate.py`, Schein-Besitzer, `freeze_time` + `tick`):

- `test_a_failure_is_replayed_without_a_fetch_during_the_pause` — `fetch_none`: 1. Aufruf `calls == 1`, Rückgabe
  `None`; nach `tick(59)` Rückgabe `None`, `calls == 1`; nach `tick(2)` `calls == 2`.
- `test_a_raised_failure_is_replayed_with_its_type_and_message` — `fetch_raise` (`OSError("down")`): in der Pause
  `pytest.raises(OSError, match="down")`, `is_replay(exc)` True, `exc is not` die erste Instanz, `calls == 1`.
- `test_consecutive_failures_double_the_pause_up_to_the_cache_lifetime` — `cache_seconds=599`: Abstände der echten
  Aufrufe 60, 120, 240, 480, 599, 599.
- `test_without_auto_update_the_pause_stays_at_sixty_seconds` — `cache_seconds=0`: 60, 60, 60.
- `test_a_success_resets_the_backoff` — zwei Fehlschläge, Erfolg, Zeitstempel altern lassen, Fehlschlag → nächste
  Pause wieder 60 s.
- `test_override_cache_bypasses_the_pause` — `override_cache=True`: jeder Aufruf ruft ab (C10).
- `test_waiters_served_from_cache_do_not_count_as_failures` — zwei Threads, der erste holt erfolgreich; danach
  `_failed_at is None` und `_failures == 0`.
- Review Focus 2 `test_a_shorter_update_interval_shortens_a_running_pause` — `cache_seconds=3599`, drei Fehlschläge
  (Pause 240), `cache_seconds = 0` → nach `tick(61)` ruft der nächste Aufruf ab.
- Review Focus 3 `test_replay_of_an_uncopyable_exception_keeps_its_type` — `class _Picky(Exception): __init__(self, a, *, b)`;
  in der Pause `pytest.raises(_Picky)`.
- Review Focus 4 `test_the_pause_runs_on_the_monotonic_clock` — ohne freezegun; `time.monotonic` per `patch` auf eine
  steuerbare Uhr: +59 → Wiedergabe, +61 → Abruf.

Sieben Tore (`tests/test_weather_clients_fetch_gate.py`, `freeze_time`):

- `test_a_failed_fetch_pauses_its_gate` (parametrisiert) — `_failing(500)`: Ergebnis des 1. Aufrufs merken
  (`("returned", v)` oder `("raised", type, str)`); `get.call_count == case.failed_attempts`; nach `tick(30)` gleiches
  Ergebnis, Zahl unverändert; nach `tick(31)` wieder `+ failed_attempts`.
- Review Focus 1 `test_concurrent_callers_during_an_outage_share_one_failed_run` (parametrisiert) — wie der
  Gleichzeitigkeitstest aus Task 2, aber `_failing(500)`: `get.call_count == case.failed_attempts`, alle fünf
  Ergebnisse gleich.
- `test_a_paused_forecast_does_not_hold_up_current_conditions` — OWM und Met Office: Vorhersage-Tor in Pause,
  `get_data()` ruft ab.
- Review Focus 5 `test_validate_key_ignores_a_running_pause` — OWM `get_data` in Pause; `validate_key()` mit
  `_ok({"cod": 200})` → `get.call_count` steigt um 1.

- [ ] **Step 2: Rot sehen** — Erwartet: die Pausen-Tests FAILED (`calls == 2` statt 1 bzw. `call_count` zu hoch);
  `test_override_cache_bypasses_the_pause`, `test_validate_key_ignores_a_running_pause` und
  `test_a_paused_forecast_does_not_hold_up_current_conditions` dürfen schon grün sein (Pins).
- [ ] **Step 3: `FetchGate.run` um die Pause erweitern.** Kern (Reihenfolge ist die Entscheidung, der Rest ist frei):

```python
def run(self, fetch):
    with self._lock:
        owner = self._owner
        before = getattr(owner, self._stamp_attr)
        was_fresh = is_fresh(before, owner.cache_seconds, owner.override_cache)
        if not was_fresh and not owner.override_cache and self._in_pause():
            return self._replay()                    # no request; DEBUG line with seconds left
        try:
            result = fetch()
        except Exception as exc:
            self._settle(before, was_fresh, raised=True, value=exc)
            raise
        self._settle(before, was_fresh, raised=False, value=result)
        return result
```

  `_settle`: neuer Zeitstempel (`!= before`) → Erfolg, `_failures = 0`, `_failed_at = None`, `_outcome = None`; sonst,
  wenn `not was_fresh` → Fehlschlag: `_failures += 1`, `_failed_at = time.monotonic()`, `_outcome` merken; sonst (aus dem
  Zwischenspeicher bedient) nichts. `_in_pause()` rechnet die Pause **bei jeder Prüfung neu**:
  `min(FIRST_PAUSE_SECONDS * 2 ** min(_failures - 1, 16), cache_lifetime(owner.cache_seconds))`; damit folgt sie einer
  Intervall-Änderung sofort (Review Focus 2). `_replay()`: Rückgabe → derselbe Wert; Ausnahme → `copy.copy(exc)` mit
  `_fetch_gate_replay = True` werfen; scheitert die Kopie, die Original-Instanz markieren und mit
  `with_traceback(None)` werfen. Kommentare an C3, C5, C7 nach `code-doku`.
- [ ] **Step 4: Grün sehen** — beide neuen Dateien plus die vier Client-Testdateien. Erwartet: grün.
- [ ] **Step 5: Commit** — `fix(weather): a failed fetch pauses that document instead of being retried at once`
  (Body: Pause 60 s, verdoppelt, gedeckelt auf das Cache-Fenster; Wiedergabe statt alter Werte; Begründung Kontingente).

---

