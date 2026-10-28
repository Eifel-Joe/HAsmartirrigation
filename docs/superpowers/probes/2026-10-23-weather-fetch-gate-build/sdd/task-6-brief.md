### Task 6: Pirate Weather — Pausen zwischen den Versuchen, Abbruch bei `429`/`Retry-After` (C8)

**Files:** Modify `PirateWeatherClient.py` (`import time`; `RETRY_PAUSES_SECONDS = (1, 2)`; neue Methode; beide
Schleifen `:237-247` und `:343-353`). Test: `tests/test_weather_clients_fetch_gate.py`.

**Interfaces:**
- Consumes: `retry_after_seconds`, `FetchGate.note_response` (Task 5).
- Produces: `PirateWeatherClient._get_with_retries(self, gate: FetchGate) -> requests.Response` — bis zu
  `RETRY_TIMES` Versuche; nach jedem `gate.note_response(req)`; Abbruch bei 200, bei 429 oder wenn
  `retry_after_seconds(req) is not None`; zwischen zwei Versuchen `time.sleep(RETRY_PAUSES_SECONDS[i])`, nach dem letzten
  keiner; Netz-Ausnahmen laufen wie heute ungefangen heraus. Beide Bodies rufen sie statt ihrer Schleife; der tote
  Ausdruck `i = i + 1` entfällt.

- [ ] **Step 1: Tests schreiben** — in der Datei eine autouse-Fixture, die `M + "PirateWeatherClient.time.sleep"` durch
  einen `MagicMock` ersetzt (`sleep`), für beide Pirate-Zugriffe parametrisiert:
  - `test_pirate_pauses_one_then_two_seconds_between_retries` — `_failing(500)`: `get.call_count == 3`,
    `sleep.call_args_list == [call(1), call(2)]`.
  - `test_pirate_stops_retrying_on_429` — `_failing(429)`: `call_count == 1`, `sleep` nicht gerufen.
  - `test_pirate_stops_retrying_when_told_when_to_come_back` — `_failing(503, {"Retry-After": "120"})`: `call_count == 1`.
  - `test_pirate_does_not_retry_a_network_error` — `side_effect=requests.ConnectionError`: `call_count == 1` (wie heute).
- [ ] **Step 2: Rot sehen** — Erwartet: `AttributeError` (Modul hat kein `time`), danach FAILED (`call_count == 3`
  bei 429, `sleep` nie gerufen).
- [ ] **Step 3:** `_get_with_retries` einbauen; Kommentar nach `code-doku` (Wurzel: drei Versuche ohne Pause, 429 heißt
  Monatskontingent; NOT-TO-DO: nicht `Retry-After` in der Schleife abwarten — das ist die Pause des Tors).
- [ ] **Step 4: Grün sehen** — beide neuen Dateien plus `tests/test_pirateweather_daily.py
  tests/test_precipitation_guard_real_clients.py`. Erwartet: grün; die Laufzeit dieser Dateien steigt nicht merklich
  (sonst schläft irgendwo ein echter `sleep`).
- [ ] **Step 5: Commit** — `fix(weather): Pirate Weather pauses between retries and stops on 429`.

---

