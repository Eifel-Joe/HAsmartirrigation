# Bericht Task 7 — Der Tagesform-Spiegel bucht den Anteil des Commits

Status: **DONE**
Commit: `2c374da9` (`feat(live): the daily mirror books the share the commit books`) auf `feat/pause-silent-sensor-hourly-live`, Vorgänger `f1b9a87d`. Nicht gepusht.

## Umgesetzt

- `custom_components/irrigation_plus/live_estimate.py`: Import `valid_share` (Klammer-Import in der Plan-Form); `_daily_mirror_et`: Docstring-Halbsatz „(a pausing sensor group's silent time aside; see ``_aggregate_live_window``)“ ersetzt und der neue Absatz zu `blocked` eingefügt; bei `blocked` wird die Pflichtmenge der Tagesform per `required_sensor_fields(module name)` geholt, `valid_share(blocked, fields, anchor, now)` gebildet, bei Anteil 0 kommt `_DayTotal(0.0, TIER_OBSERVED)` zurück, sonst wird `total_mm` mit dem Anteil multipliziert.
- `docs/configuration-sensor-groups.md` Zeile 62: der Satz zur Live-Schätzung durch den freigegebenen englischen Wortlaut ersetzt.
- Neu `tests/test_live_estimate_silent_sensor_daily.py` (Klassen `TestTheMirrorBooksTheShare`, `TestNothingMeasuredIsNothingBooked`), wörtlich aus dem Plan.

Die Blöcke wurden Zeichen für Zeichen übernommen. Die `Modify`-Diffs per Python-Skript (bytegenau, CRLF-erhaltend, jeder Anker genau einmal gefunden); `git diff` zeigt exakt die Plan-Indexzeilen `10122244..7bfc4141` (live_estimate.py) und `42f7f1cf..2d8bc77c` (Doku).

## RED (Step 2)

Befehl: `TZ=UTC /d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests/test_live_estimate_silent_sensor_daily.py -p _local_socket_unblock -q --no-header -rfE`

```
tests\test_live_estimate_silent_sensor_daily.py FE.EFE                   [100%]
FAILED tests/test_live_estimate_silent_sensor_daily.py::TestTheMirrorBooksTheShare::test_it_lands_on_the_cut_bucket
FAILED tests/test_live_estimate_silent_sensor_daily.py::TestNothingMeasuredIsNothingBooked::test_it_does_not_fall_back_to_a_weather_service
ERROR (x3, alle Teardown "Lingering timer after test")
==================== 2 failed, 1 passed, 3 errors in 3.28s ====================
```

- `test_it_lands_on_the_cut_bucket`: `assert -2.61 == -1.65 ± 1.0e-02` (Live-Eimer ohne Anteil verfehlt den gebuchten).
- `test_it_does_not_fall_back_to_a_weather_service`: `AssertionError: assert 'hourly' == 'daily_mirror'` (die Kette rutscht zur Stundenreihe des Wetterdienstes).
- `test_a_field_the_daily_form_does_without_changes_nothing` besteht (erwartet: ohne Code schon gleich).

Entspricht dem Plan (`2 failed, 1 passed`) und der gemessenen Probe (`2 failed, 1 passed, 3 errors`).

## GREEN (Step 4)

Gleicher Befehl:

```
tests\test_live_estimate_silent_sensor_daily.py .E.E.E                   [100%]
ERROR (x3: je "Lingering timer after test", lokaler Vorbestand)
========================= 3 passed, 3 errors in 3.39s =========================
```

## Lint (Step 5)

```
$ uvx black custom_components/irrigation_plus/
All done! ... 70 files left unchanged.
$ uvx ruff@0.16.10 check custom_components/irrigation_plus/
All checks passed!
```

## task_compare (Step 5)

`../task_compare.sh t7 $(ls tests/test_live_estimate*.py tests/test_silent_sensor*.py tests/test_next_irrigation*.py)`

```
baseline names missing now: 2
ERROR tests/test_silent_sensor_commit.py::TestAGroupThatIsNotCutCalculatesAsBefore::test_a_pausing_group_under_the_hourly_calculation_matches_too
ERROR tests/test_silent_sensor_commit.py::TestTheGate::test_with_the_hourly_calculation_nothing_is_cut
new FAILED: 0
new ERROR per file:
      8 ERROR tests/test_live_estimate_silent_sensor.py
      3 ERROR tests/test_live_estimate_silent_sensor_daily.py
      2 ERROR tests/test_silent_sensor_commit.py
      8 ERROR tests/test_silent_sensor_hourly_commit.py
============ 1 failed, 345 passed, 267 errors in 61.09s (0:01:01) =============
```

Einordnung (nachgeprüft):
- Die 2 entfallenen Namen sind genau die in Task 5 umbenannten (`…_under_the_hourly_switch_is_cut_too`, `…_the_hourly_calculation_is_cut_the_same` tauchen als die 2 neuen ERROR in `test_silent_sensor_commit.py` auf).
- „1 failed“ ist `tests/test_next_irrigation_sensor.py::TestSetupAnnouncesSchedules::test_setup_entry_announces_after_loading_schedules`, Vorbestand (steht in der Baseline; `winloop`/`aiodns`-Windows-Fehler). Keine neuen FAILED.
- Alle 267 ERROR sind `Lingering timer after test` (267 Treffer in der Ausgabe); die zwei weiteren `E`-Zeilen (`winloop` / `aiodns`) gehören zum FAILED-Vorbestandstest.
- Gegenüber dem Lauf von Task 6 (`task-t6-names.txt`) kommen exakt 3 neue Namen hinzu (die drei ERROR der neuen Datei), nichts entfällt.

## Eigener Diff (Selbstprüfung)

- `git diff b36bc93d HEAD -- live_estimate.py docs/configuration-sensor-groups.md tests/test_live_estimate_silent_sensor_daily.py` ist leer (`git diff --quiet` -> identisch zum Probe-Commit). Probe-Commit nur lesend als Vergleich genutzt, nicht für die Umsetzung (die Blöcke kamen aus dem Plan).
- Commit enthält nur die drei Task-Dateien (`3 files changed, 149 insertions(+), 7 deletions(-)`); `git status --short` danach leer.
- Zeilenenden: Arbeitskopie CRLF (live_estimate.py, Doku, auch die neue Testdatei auf CRLF gebracht wie die Nachbarn); Blobs im Index 0 CR. `git diff --stat` zählte vor dem Commit nur 28+/7- bzw. 1/1 Zeilen.
- Keine Verweise auf Fork-/Upstream-Issues, Task-/Spec-Kürzel oder „PR 2/3“ im Commit (grep: none). Letzte Commit-Zeile exakt `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## Abweichungen vom Plan

Keine. (Nur Handwerkliches: Edits per Python-Skript statt Edit-Tool wegen CRLF; die neue Testdatei zusätzlich auf CRLF konvertiert. Der Index ist davon unberührt.)

## Bedenken

Keine. Hinweis ohne Handlungsbedarf: black/ruff laufen laut Brief nur auf `custom_components/irrigation_plus/`, die Testdatei ist daher wörtlich aus dem Plan und nicht von black geprüft.

---

# Fix-Runde 1

Status: **DONE**
Commit: `08728aa7` (`fix(live): a silent window books nothing even without a forecast to mirror`), neuer Commit auf `2c374da9`, kein amend. Nicht gepusht. `git status --short` danach leer.

## Befund

Die 0-Abkürzung in `_daily_mirror_et` saß hinter `_mirror_blend(...)`. Eine Zone mit `forecast_days > 0` ohne verwertbare Tagesprognose lieferte `None`, bevor der Anteil 0 gebildet wurde, und die Quellenkette rutschte zur Stundenreihe des Wetterdienstes. Der Commit bucht dort 0 und fragt weder Gleichung noch Prognose.

## Test (zuerst)

`tests/test_live_estimate_silent_sensor_daily.py`, Klasse `TestNothingMeasuredIsNothingBooked`, neu:
`test_a_zone_that_averages_forecast_days_in_needs_no_forecast_for_it`. Aufbau wie `test_it_does_not_fall_back_to_a_weather_service`, plus `instance.forecast_days = 2` (Muster `_forecasting_zone` in `test_live_estimate_replayed_balance.py:1516`, hier inline gesetzt, kein neuer Import); keine Tagesprognose (`_estimating_inputs` setzt `forecast=None` per Default), Temperatur ab 4 h vor dem Anker offen stumm (`_silent(store, zone, -4)`), Stundenreihe des Wetterdienstes `_provider_rows(0.0)` vorhanden. Erwartet: `method == "daily_mirror"`, `et_since == 0.0` und Live-Eimer == gebuchter Eimer des Commits (wie im Schwestertest).

## RED

`TZ=UTC .../python.exe -m pytest tests/test_live_estimate_silent_sensor_daily.py -k test_a_zone_that_averages_forecast_days_in_needs_no_forecast_for_it -p _local_socket_unblock -q --no-header -rfE`

```
E   AssertionError: assert 'hourly' == 'daily_mirror'
FAILED tests/test_live_estimate_silent_sensor_daily.py::TestNothingMeasuredIsNothingBooked::test_a_zone_that_averages_forecast_days_in_needs_no_forecast_for_it
ERROR (Teardown, Lingering timer)
================== 1 failed, 3 deselected, 1 error in 2.18s ===================
```

Erwartet, weil der Spiegel vor dem Anteil `None` zurückgab und die Kette zur Stundenreihe rutschte (genau der Befund).

## Code

`custom_components/irrigation_plus/live_estimate.py`, `_daily_mirror_et` (+9/-2): Reihenfolge jetzt
`_daily_form_applies` (sonst `return None`) -> Anteil (`share == 0` -> `_DayTotal(0.0, TIER_OBSERVED)`) -> erst dann `_commit_forecast` (`None` -> `return None`). Davor ein knapper englischer Kommentar, warum der Anteil vor der Prognose kommt.

- `_mirror_blend` selbst unverändert: es hat einen zweiten Aufrufer (`_intraday_for_zone`, ca. Zeile 2016), der die Prognose-Prüfung und `_daily_form_applies` weiter zusammen braucht. Der Spiegel ruft stattdessen `_daily_form_applies` und `_commit_forecast` einzeln (kleinste Umstellung; `_commit_forecast` ist ein `staticmethod`, in einem Test direkt aufgerufen, unverändert).
- Docstring-Absatz „A pausing sensor group's commit books only the part …“ bleibt wahr und unverändert.
- Teilanteil (0 < Anteil < 1) ohne Prognose: unverändert `None` -> heutiger Weg.

Anker-Zeilen (je genau einmal, unverändert):

```
$ grep -c "^                    return _DayTotal(0.0, TIER_OBSERVED)" custom_components/irrigation_plus/live_estimate.py
1
$ grep -c "^            total \*= share" custom_components/irrigation_plus/live_estimate.py
1
```

## GREEN

Gleicher Befehl ohne `-k` (ganze Datei):

```
tests\test_live_estimate_silent_sensor_daily.py .E.E.E.E                 [100%]
========================= 4 passed, 4 errors in 3.73s =========================
```

(4 errors = Teardown „Lingering timer“.)

## Lint

```
$ uvx black custom_components/irrigation_plus/   -> All done! ... 70 files left unchanged.
$ uvx ruff@0.16.10 check custom_components/irrigation_plus/   -> All checks passed!
```

## task_compare t7f1

`../task_compare.sh t7f1 $(ls tests/test_live_estimate*.py tests/test_silent_sensor*.py tests/test_next_irrigation*.py)`

```
baseline names missing now: 2          (die zwei in Task 5 umbenannten Namen, wie bei t7)
new FAILED: 0
new ERROR per file:
      8 ERROR tests/test_live_estimate_silent_sensor.py
      4 ERROR tests/test_live_estimate_silent_sensor_daily.py
      2 ERROR tests/test_silent_sensor_commit.py
      8 ERROR tests/test_silent_sensor_hourly_commit.py
============ 1 failed, 346 passed, 268 errors in 61.42s (0:01:01) =============
```

Gegenüber t7 (345 passed / 267 errors): genau +1 passed und +1 ERROR (der neue Test, Teardown). Namensliste gegen t7: einzige Abweichung ist `ERROR …::test_a_zone_that_averages_forecast_days_in_needs_no_forecast_for_it`; nichts entfällt. Das eine FAILED ist der Vorbestand `test_next_irrigation_sensor::…announces_after_loading_schedules` (in der Baseline). Alle 268 ERROR sind `E   Failed: Lingering timer after test` (268 Treffer).

## Selbstprüfung

Commit enthält nur `live_estimate.py` (+9/-2) und die Testdatei (+19); Blobs 0 CR, Arbeitskopie CRLF erhalten; keine Issue-/Task-/Spec-/PR-Verweise in Diff und Message; letzte Commit-Zeile exakt `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`; Commit-Message wörtlich nach Brief.

## Abweichungen / Bedenken

Keine inhaltlichen. Umgebung: Laufwerk `C:` meldet 100 % (0 frei, `df -h /`); ein einzelner Bash-Aufruf mit Pipe scheiterte einmal mit `No space left on device` und lief beim Wiederholen durch. Ich habe deshalb die Lauf-Ausgaben dieser Runde nach `D:` umgeleitet (`issue8-pr3-work\t7f1-red.txt`, `t7f1-green.txt`, `t7f1-compare.txt`). Nichts von mir auf `C:` aufgeräumt; falls weitere Läufe scheitern, zuerst `C:` prüfen.
