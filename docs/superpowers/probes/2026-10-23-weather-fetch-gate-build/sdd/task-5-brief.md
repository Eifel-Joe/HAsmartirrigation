### Task 5: `Retry-After` (C6)

**Files:** Modify `fetch_gate.py`; `OWMClient.py` (`_fetch_data`, `_fetch_forecast`: nach `_SESSION.get`);
`PirateWeatherClient.py` (beide Schleifen: nach `_SESSION.get`). Test: beide Testdateien.

**Interfaces:**
- Produces: `MAX_RETRY_AFTER_SECONDS = 86400`; `retry_after_seconds(response: Any) -> float | None` — liest
  `response.headers.get("Retry-After")`; nur ein `str` zählt (MagicMock-Köpfe in vorhandenen Tests → `None`);
  Ganzzahl-Sekunden ≥ 0 oder HTTP-Datum (`email.utils.parsedate_to_datetime`, Abstand zu
  `datetime.datetime.now(datetime.UTC)`); ≤ 0, unlesbar, fehlend → `None`.
  `FetchGate.note_response(self, response: Any) -> None` — merkt die Antwort des laufenden Versuchs (innerhalb der Sperre,
  also ohne Thread-Lokales). `run` setzt sie vor `fetch()` zurück; `_settle` liest bei einem Fehlschlag
  `retry_after_seconds(gemerkte Antwort)` oder, bei einer Ausnahme, `retry_after_seconds(exc.response)`, wo vorhanden.
  Pause = `max(Backoff aus Task 3, min(retry_after, MAX_RETRY_AFTER_SECONDS))`.

- [ ] **Step 1: Tests schreiben**

```python
# tests/test_weather_fetch_gate.py
@freeze_time("2026-10-23 12:00:00")
def test_retry_after_is_read_as_seconds_or_http_date():
    assert retry_after_seconds(_resp({"Retry-After": "120"})) == 120
    assert retry_after_seconds(_resp({"Retry-After": "Fri, 23 Oct 2026 12:05:00 GMT"})) == 300
    for bad in ("", "soon", "-5", "Fri, 23 Oct 2026 11:00:00 GMT"):
        assert retry_after_seconds(_resp({"Retry-After": bad})) is None
    assert retry_after_seconds(_resp({})) is None
    assert retry_after_seconds(MagicMock()) is None          # non-str header value
```

- `test_a_longer_retry_after_wins_over_the_backoff` — `Retry-After: 900`, `cache_seconds=599`: Wiedergabe bis 899 s,
  Abruf bei 901 s.
- `test_a_shorter_retry_after_keeps_the_backoff` — `Retry-After: 10`: Wiedergabe bei 30 s, Abruf bei 61 s.
- `test_retry_after_is_capped_at_a_day` — `Retry-After: 999999`: Abruf bei 86 401 s.
- Sieben Tore: `test_retry_after_reaches_the_gate` für `owm_data` (Antwort-Kopf, `cod` 429), `pirate_forecast`
  (Status 429, Kopf) und `openmeteo_doc` (über `HTTPError.response`): `_failing(429, {"Retry-After": "900"})` → nach
  `tick(600)` keine neue Anfrage, nach `tick(301)` mindestens eine. Die Zahl je Lauf nicht festnageln: Pirate macht bei
  `429` bis Task 6 drei Versuche, danach einen.

- [ ] **Step 2: Rot sehen** — Erwartet: `ImportError` für `retry_after_seconds`, danach FAILED (Abruf schon bei 61 s).
- [ ] **Step 3:** `retry_after_seconds`, `note_response` und die Einbindung in `_settle`; `self._data_gate.note_response(req)`
  bzw. `self._forecast_gate.note_response(req)` direkt nach jedem `_SESSION.get` in OWM und Pirate.
- [ ] **Step 4: Grün sehen** — beide neuen Dateien plus die vier Client-Testdateien. Erwartet: grün.
- [ ] **Step 5: Commit** — `fix(weather): the pause after a failure honours Retry-After`.

---

