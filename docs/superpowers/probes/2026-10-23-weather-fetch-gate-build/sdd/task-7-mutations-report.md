# Task 7 Step 3: Mutationen gegen das Fetch-Tor

Worktree `D:/Entwicklung/HASI/issue89-work/wt`, Branch `fix/weather-client-fetch-gate`, HEAD `48945139` (unveraendert).
Nichts committet, nichts gestasht. Jede Mutation einzeln angewandt, danach `git checkout -- custom_components/`;
nach jeder Mutation war `git status --short` leer.

Befehl je Mutation (wie im Auftrag, `-x`):
`TZ=UTC timeout 300 .venv/Scripts/python.exe -m pytest tests/test_weather_fetch_gate.py tests/test_weather_clients_fetch_gate.py -p _local_socket_unblock -q --no-header -x`

Basislauf vor den Mutationen: `85 passed in 9.74s`. Jede Mutation: `collected 85 items` (gueltig). Kein Timeout, kein Hang.
Die Mutationen wurden per Skript (Bytes, CRLF erhalten, Muster muss genau einmal vorkommen) eingespielt:
`scratchpad/mutate.py`, `probe.sh`, `probe-full.sh` (Scratchpad der Sitzung, nicht im Repo).

## Ergebnis: 12 von 12 getoetet, keine Ueberlebenden

| # | Stelle (HEAD) | Aenderung | collected | getoetet | Killer (erster Fehlschlag mit `-x`) | Fehlschlaege ohne `-x` |
|---|---|---|---|---|---|---|
| M1 | fetch_gate.py:192 | `with self._lock:` -> `with contextlib.nullcontext():` (+ `import contextlib`) | 85 | ja | `test_weather_fetch_gate.py::test_run_serialises_two_threads_onto_one_fetch` (`assert 2 == 1`, Aufrufe des Fetch) | 16 |
| M2 | fetch_gate.py:195 | `was_fresh = is_fresh(...)` aus der Sperre vor `with self._lock:` verschoben (liest den Stempel dort selbst); `before` bleibt in der Sperre | 85 | ja | `test_weather_fetch_gate.py::test_waiters_served_from_cache_do_not_count_as_failures` (`_failed_at` ist gesetzt statt `None`) | 1 |
| M3 | fetch_gate.py:244 | `self._failed_at = time.monotonic()` -> `pass` | 85 | ja | `test_weather_fetch_gate.py::test_a_failure_is_replayed_without_a_fetch_during_the_pause` (`assert 2 == 1`) | 52 |
| M4 | fetch_gate.py:293 | `FIRST_PAUSE_SECONDS * 2 ** min(...)` -> `FIRST_PAUSE_SECONDS * 1` | 85 | ja | `test_weather_fetch_gate.py::test_consecutive_failures_double_the_pause_up_to_the_cache_lifetime` (`[60]*6 != [60,120,240,480,599,599]`) | 2 |
| M5 | fetch_gate.py:292-295 | `backoff = min(60 * 2**n, cache_lifetime(...))` -> `backoff = 60 * 2**n` (Deckel weg) | 85 | ja | `test_weather_fetch_gate.py::test_consecutive_failures_double_the_pause_up_to_the_cache_lifetime` (`[...,960,1920] != [...,599,599]`) | 3 |
| M6 | fetch_gate.py:311 | woertlich: aeusseres `max(backoff, min(retry_after, cap))` -> `min(backoff, min(retry_after, cap))` | 85 | ja | `test_weather_fetch_gate.py::test_a_failure_is_replayed_without_a_fetch_during_the_pause` (siehe Analyse: Beifang) | 38 |
| M6b | fetch_gate.py:311 | schaerfer: `min(backoff, min(retry_after, cap)) if retry_after > 0 else backoff` (Retry-After nur wo vorhanden als Obergrenze) | 85 | ja | `test_weather_fetch_gate.py::test_a_longer_retry_after_wins_over_the_backoff` (`assert 2 == 1`) | 11 |
| M7 | PirateWeatherClient.py:252 | Zeile `or req.status_code == 429` entfernt (200-Zweig und Retry-After-Zweig bleiben) | 85 | ja | `test_weather_clients_fetch_gate.py::test_pirate_stops_retrying_on_429[pirate_data]` (`assert 3 == 1`, `call_count`) | 2 (`[pirate_data]`, `[pirate_forecast]`) |
| M8 | fetch_gate.py:69 | `return logging.DEBUG if is_replay(exc) else logging.ERROR` -> `return logging.ERROR` | 85 | ja | `test_weather_fetch_gate.py::test_failure_log_level_is_debug_for_a_replay_and_error_otherwise` (`40 == 10`) | 7 |
| M9 | fetch_gate.py:198 | `if not was_fresh and not owner.override_cache:` -> `if not was_fresh:` | 85 | ja | `test_weather_fetch_gate.py::test_run_lets_an_exception_through_and_lets_the_next_caller_in` (`[ValueError('boom')] != ['document']`) | 2 (+ `test_override_cache_bypasses_the_pause`) |
| M10 | fetch_gate.py:228 | `self._failures = 0` im Erfolgszweig von `_settle` entfernt | 85 | ja | `test_weather_fetch_gate.py::test_a_success_resets_the_backoff` (`4 == 3 + 2`) | 1 |
| M11 | fetch_gate.py:198 | Pause vor/unabhaengig von der Frische geprueft: `if not was_fresh and not owner.override_cache:` -> `if not owner.override_cache:` | 85 | ja | `test_weather_fetch_gate.py::test_a_fresh_entry_is_served_even_during_a_pause` (`None != 'document'`) | 1 |
| M12 | PirateWeatherClient.py:249 | `gate.note_response(req)` hinter den Frueh-Ausstieg (`if ...: break`) verschoben, direkt vor `if attempt < RETRY_TIMES - 1:` | 85 | ja | `test_weather_clients_fetch_gate.py::test_retry_after_reaches_the_gate[pirate_data]` (`assert 2 == 1`, `call_count`) | 2 (`[pirate_data]`, `[pirate_forecast]`) |

Alle Fehlschlaege sind Assertions auf das erwartete Verhalten (keine Import-/Syntaxfehler); die `E`-Zeilen stehen oben.

## Abweichungen und Hinweise zur Anwendung

- Die Namen aus dem Plan stimmen nicht mehr; jede Stelle wurde nach Bedeutung gesucht (Tabelle). Alle zwoelf Edits waren
  moeglich, keine "nicht anwendbar".
- M2: `before` wird weiter in der Sperre gelesen. Nur die Frischeablesung (`was_fresh`) liegt davor. Genau dieser
  Abstand (Frische alt, Stempel neu) ist die Situation eines Wartenden.
- M6: Der woertliche Tausch `max` -> `min` macht die Pause ohne Retry-After-Header zu 0 s (`min(backoff, 0) = 0`).
  Er stirbt deshalb an fast jedem Test der Pause (38 Fehlschlaege): ein Beifang-Tod, keine gezielte Pruefung der
  Retry-After-Regel. Darum zusaetzlich M6b: Retry-After nur dort als Obergrenze, wo er vorhanden ist. M6b wird gezielt von
  den vier Retry-After-Tests in `test_weather_fetch_gate.py` und `test_retry_after_reaches_the_gate[*]` (alle 7 Faelle)
  getoetet. Die Regel "Header ist Untergrenze, kuerzt nie den Backoff" ist damit unabhaengig belegt.
- M7: Der Test nutzt `_failing(429)` ohne Header (`test_weather_clients_fetch_gate.py:412`). Ohne die 429-Bedingung laeuft
  die Schleife weiter (3 Aufrufe statt 1). Haette der Test-429 einen Retry-After-Header, truege der Retry-After-Zweig den
  Ausstieg und M7 wuerde ueberleben; so ist die 429-Bedingung einzeln gepinnt.
- M12: Ohne `-x` sterben beide Pirate-Faelle; die uebrigen fuenf Clients rufen `note_response` anderswo und bleiben gruen.

## Beobachtungen (keine Ueberlebenden, nichts zu schaerfen)

- Einzel-Killer (nur ein Test stirbt): M2, M10, M11. Sie sind je durch genau einen Test gepinnt:
  `test_waiters_served_from_cache_do_not_count_as_failures`, `test_a_success_resets_the_backoff`,
  `test_a_fresh_entry_is_served_even_during_a_pause`. Bei M2 stirbt nur der Baustein-Test, keiner der Client-Tests
  (`test_concurrent_callers_*` bleiben gruen; warum, wurde nicht untersucht). Gepinnt ist es, aber schmal.
- M8: nur Open-Meteo (3 Fehlerfaelle) und Met Office (2 Faelle) rufen `failure_log_level`; OWM/Pirate fangen nicht oberhalb
  des Tors und bleiben bei M8 gruen. Das ist korrekt (grep: `failure_log_level` nur in OpenMeteoClient.py:199/311/482 und
  MetOfficeClient.py:468/573), kein Testloch.
- M1 ist doppelt belegt: Baustein-Test (`test_run_serialises_two_threads_onto_one_fetch`) und alle sieben
  `test_concurrent_callers_make_one_request[*]`.

## Endzustand

`git status --short` ohne Ausgabe (nur das git-ignorierte `.superpowers/` existiert); `git rev-parse HEAD` =
`489451398c2fa39b80f18fe23674239a51096967`. Keine Zeile unter `custom_components/` geaendert.
