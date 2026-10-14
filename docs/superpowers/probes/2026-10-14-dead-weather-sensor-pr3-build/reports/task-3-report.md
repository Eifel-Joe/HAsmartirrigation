# Bericht Task 3 — Die nachgespielte Bilanz legt ET nur in gemessene Zeit

Status: **DONE**
Commit: `74d7192a` (Branch `feat/pause-silent-sensor-hourly-live`, Vorgänger `0d976997`)

## Umgesetzt

- Step 1: `tests/test_substeps_blocked.py` wörtlich aus dem Plan angelegt (9 Tests, 188 Zeilen; Arbeitskopie auf CRLF
  gebracht wie die übrigen Testdateien, Index LF).
- Step 3: `custom_components/irrigation_plus/weather_aggregate.py`, `build_substeps` — Diff aus dem Plan Hunk für Hunk
  übertragen (Signatur mit `blocked=None, required=()`, Docstring-Absatz, `spans=/start=/end=` an `_precip_increments`,
  `mask`/`booked`/`masked_sun`-Block, `measured`-Liste je Schritt, `_weights_from_hourly_et(weights, hours, measured, …)`,
  dreistufiger Rückfall bei `total <= 0`). Nur die Edit-Tools benutzt.
- Step 6: Commit mit der wörtlichen Message, gezielt gestaget (`weather_aggregate.py`, `tests/test_substeps_blocked.py`).

## RED (Step 2)

Befehl: `TZ=UTC /d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests/test_substeps_blocked.py -p _local_socket_unblock -q`

```
FAILED tests/test_substeps_blocked.py::TestWithoutSpans::test_no_spans_an_empty_dict_and_a_foreign_field_give_the_same_steps
FAILED ...::TestTheEtLandsInMeasuredTime::test_a_required_field_silent_places_no_et_there
FAILED ...::TestTheEtLandsInMeasuredTime::test_a_field_the_form_does_without_moves_nothing
FAILED ...::TestTheEtLandsInMeasuredTime::test_silent_sun_places_no_et_in_its_span_either
FAILED ...::TestTheEtLandsInMeasuredTime::test_inside_an_hour_the_quantum_goes_to_its_measured_part
FAILED ...::TestTheEtLandsInMeasuredTime::test_a_dark_hour_spreads_its_quantum_over_its_measured_time
FAILED ...::TestTheEtLandsInMeasuredTime::test_a_window_with_no_measured_time_still_steps
FAILED ...::TestTheRainStillReconciles::test_a_blocked_rain_rate_adds_only_its_measured_rain
FAILED ...::TestTheRainStillReconciles::test_rain_just_before_a_span_lands_before_it
============================== 9 failed in 2.34s ==============================
```

Jeder Fehler: `E   TypeError: build_substeps() got an unexpected keyword argument 'blocked'` (`tests\test_substeps_blocked.py:52`,
Aufruf in `_steps`). Erwartet, weil `build_substeps` den Parameter vor Step 3 nicht kennt. Deckt sich mit der gemessenen
Erwartung (`9 failed`, je dieser TypeError).

## GREEN (Step 4)

Befehl wie Step 2:

```
collected 9 items
tests\test_substeps_blocked.py .........                                 [100%]
============================== 9 passed in 1.11s ==============================
```

## Lint (Step 5)

```
$ uvx black custom_components/irrigation_plus/
All done! ... 70 files left unchanged.
$ uvx ruff@0.16.10 check custom_components/irrigation_plus/
All checks passed!
```

black änderte keine Datei (auch keine, die der Task nicht anfasst).

## `../task_compare.sh t3 tests/test_substeps_blocked.py tests/test_water_balance_substeps.py tests/test_summed_hourly_eto.py tests/test_live_estimate_replayed_balance.py`

```
baseline names missing now: 0
new FAILED: 0
new ERROR per file:
====================== 213 passed, 168 errors in 38.38s =======================
```

Die 168 Errors sind die Namen der Baseline (`task-t3-base.txt` 168 Zeilen = `task-t3-names.txt` 168 Zeilen) und
ausnahmslos `Failed: Lingering timer after test …` (168 Treffer, `_reset_event_fired_today` des
`SmartIrrigationCoordinator`) — der bekannte lokale Teardown-Vorbestand. Keine neuen FAILED, keine neuen ERROR.

## Nach dem Commit

- `git status --short`: leer.
- `git diff --stat` vor dem Commit: nur `weather_aggregate.py` (+70/−11) und die neue Testdatei (+188); Zeilenenden:
  Arbeitskopie CRLF (1597/1597 bzw. 188/188, keine einzelnen CR), Index LF (`git ls-files --eol`: `i/lf w/crlf`).
- Commit-Message wörtlich, letzte Zeile `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`; keine Verweise auf
  Issues, Spec-/Plan-Kürzel oder „PR 2/PR 3“ (`grep` über `git show` leer).
- Eigenen Diff gegen den Probe-Commit `71276b0d` verglichen (nur lesend, **erst nach** dem Commit, nicht zum Bauen
  benutzt): die `+`/`-`-Zeilen beider Dateien sind identisch (`diff` leer).

## Abweichungen vom Plan

Keine. Der Probe-Commit wurde nicht als Schiedsrichter gebraucht (kein Block scheiterte); die einzige Nutzung war der
nachträgliche Zeilenvergleich oben.

## Bedenken

Keine.
