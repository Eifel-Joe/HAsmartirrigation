# Task 8 — Bericht: Die Hochrechnung rechnet aus der gemessenen Zeit

Status: DONE
Commit: `ca0955f854d58a725f5a27be5da9b273bb947914` (`ca0955f8`) auf `feat/pause-silent-sensor-hourly-live`, Vorgänger `08728aa7`.
Worktree: `D:\Entwicklung\HASI\issue8-pr3-work\wt`.

## Umgesetzt

- `tests/test_live_estimate_silent_sensor_daily.py`: Import `live_estimate as live_estimate_module` und Klasse
  `TestTheProjectionToTheDecisionPoint` (zwei Tests, Hilfen `_frozen_zone`, `_projected`) hinter
  `TestNothingMeasuredIsNothingBooked` — also hinter dem durch die Fix-Runde `08728aa7` hinzugekommenen Test
  (`test_a_zone_that_averages_forecast_days_in_needs_no_forecast_for_it`), an der Stelle, die der Plan-Diff zeigt.
- `custom_components/irrigation_plus/live_estimate.py`, `_carry_estimate_to`: `blocked = zone_blocked_spans(self.store, zone, anchor, now_local)`
  einmal vor dem Aggregat; `_aggregate_live_window(..., blocked=blocked)` und `_composed_day_et(..., blocked=blocked)`.
  Die Zeilennummern im Plan (`@@ -2007`) waren durch frühere Tasks verschoben (hier `@@ -2014`); Anker per Text gefunden.
- Wörtlichkeit maschinell geprüft: die `+`/`-`-Zeilen der beiden Plan-Diffs (63 bzw. 9 Zeilen) stimmen mit meinem
  `git diff --unified=0` Zeichen für Zeichen überein (`want == got` → True für beide Dateien).

## RED (Step 2)

Befehl (aus `wt`, Temp auf D:):
`TZ=UTC /d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests/test_live_estimate_silent_sensor_daily.py -p _local_socket_unblock -q -k Projection`
Rohausgabe: `D:\Entwicklung\HASI\issue8-pr3-work\task-8-red.txt`

```
    assert paused["projected_et"] < kept["projected_et"]
E   assert 1.6405 < 1.6405
    assert len(calls) == 1
E   assert 0 == 1
E    +  where 0 = len([])
FAILED ...::TestTheProjectionToTheDecisionPoint::test_it_is_priced_from_the_cut_window
FAILED ...::TestTheProjectionToTheDecisionPoint::test_it_asks_for_its_spans_once
ERROR  ...::test_it_is_priced_from_the_cut_window      (Lingering timer, Teardown)
ERROR  ...::test_it_asks_for_its_spans_once            (Lingering timer, Teardown)
================== 2 failed, 4 deselected, 2 errors in 2.00s ==================
```

Erwartet und gemessen im Probelauf: `2 failed` mit `1.6405 < 1.6405` (Hochrechnung bleibt ungeschnitten) und
`0 == 1` (keine Sperren erfragt). Einziger Unterschied zur Messung im Brief: `4 deselected` statt `3 deselected`,
weil die Datei durch die Fix-Runde `08728aa7` einen Test mehr hat — wie vom Controller angekündigt.

## GREEN (Step 4)

Befehl: wie oben ohne `-k`. Rohausgabe: `D:\Entwicklung\HASI\issue8-pr3-work\task-8-green.txt`

```
========================= 6 passed, 6 errors in 3.74s =========================
```

`6 passed` (statt `5 passed` im Plan: der Fix-Runden-Test), 6 ERROR = alle `Failed: Lingering timer after test`
(`grep` auf die `E`-Zeilen: 6 × „Lingering timer after test“, sonst nichts).

## Lint (Step 5)

```
$ uvx black custom_components/irrigation_plus/
All done! ... 70 files left unchanged.
$ uvx ruff@0.16.10 check custom_components/irrigation_plus/
All checks passed!
```

Hinweis: Der erste `uvx black`-Aufruf scheiterte mit `os error 112` (kein Speicherplatz, uv-Cache auf C:, C: war bei 0 B frei).
Ich habe denselben kanonischen Befehl unverändert wiederholt; er lief dann durch (C: hatte kurzzeitig 62 MB frei). Kein Workaround,
keine Umleitung des Caches. C: ist weiterhin zu 100 % belegt — künftige `uvx`-Aufrufe können wieder daran scheitern.

## `../task_compare.sh t8 $(ls tests/test_live_estimate*.py tests/test_silent_sensor*.py tests/test_next_irrigation*.py)` (12 Dateien)

Ausgabe (die Konsolenausgabe ging teilweise verloren, weil mein `| tee` an „No space left on device“ auf C: scheiterte;
die Zeilen unten stammen aus dem Lauf selbst, die Rohausgabe des pytest-Laufs liegt vollständig in
`D:\Entwicklung\HASI\issue8-pr3-work\task-t8.txt`, die Namenslisten in `task-t8-names.txt` / `task-t8-base.txt`,
die Skriptausgabe in `task-8-compare.txt`):

```
baseline names missing now: 2
ERROR tests/test_silent_sensor_commit.py::TestAGroupThatIsNotCutCalculatesAsBefore::test_a_pausing_group_under_the_hourly_calculation_matches_too
ERROR tests/test_silent_sensor_commit.py::TestTheGate::test_with_the_hourly_calculation_nothing_is_cut
new FAILED: 0
new ERROR per file:
      8 ERROR tests/test_live_estimate_silent_sensor.py
      6 ERROR tests/test_live_estimate_silent_sensor_daily.py
      2 ERROR tests/test_silent_sensor_commit.py
      8 ERROR tests/test_silent_sensor_hourly_commit.py
=========== 1 failed, 348 passed, 270 errors in 64.39s (0:01:04) ===========
```

Einordnung gegen die Erwartung im Brief („es entfallen nur die zwei in Task 5 umbenannten Namen; keine neuen FAILED; neue ERROR nur aus
den neuen Dateien mit echtem Koordinator, alle ‚Lingering timer‘“):
- Die 2 entfallenen Namen sind die beiden in Task 5 umbenannten `test_silent_sensor_commit`-Tests (die Namen
  `…_hourly_switch_is_cut_too` / `…_hourly_calculation_is_cut_the_same` stehen unter den neuen ERROR). Sonst nichts entfallen.
- 0 neue FAILED. Das eine `1 failed` ist `tests/test_next_irrigation_sensor.py::TestSetupAnnouncesSchedules::test_setup_entry_announces_after_loading_schedules`
  (Vorbestand, in der Baseline; `winloop`/`aiodns`-Windows-Fehler — wie in den Berichten zu Task 6 und 7).
- Neue ERROR: 24 (8 + 6 + 2 + 8), nur aus den vier neuen Testdateien (`test_live_estimate_silent_sensor.py`,
  `test_live_estimate_silent_sensor_daily.py`, `test_silent_sensor_commit.py`, `test_silent_sensor_hourly_commit.py`).
  Alle 270 ERROR im Lauf sind `Lingering timer after test` (270 Treffer); die zwei weiteren `E`-Zeilen (`winloop`/`aiodns`)
  gehören zum FAILED-Vorbestandstest (Zeilen 5055/5091 der Ausgabe, im Abschnitt dieses Tests).

## Eigener Diff

- `git diff --stat` vor dem Commit: `live_estimate.py | 9 +++-` (8 +, 1 −), Testdatei `| 63 ++`; nur diese zwei Dateien.
- Zeilenenden: beide Dateien rein CRLF (2113/2113 bzw. 203/203, 0 nackte LF).
- Keine verbotenen Verweise (Task-/Spec-/Issue-Kürzel) in den hinzugefügten Zeilen (Wortlaut ist der des Plans, der keine enthält).
- Nach dem Commit: `git status --short` leer.

## Abweichungen vom Plan

Keine am Code oder an den Tests. Beobachtbare Unterschiede, alle erklärt: `4 deselected`/`6 passed` statt `3 deselected`/`5 passed`
(Fix-Runden-Test aus `08728aa7`); Diff-Zeilennummer im Plan (`-2007`) gegen Ist (`-2014`) verschoben. Probe-Commit `76de3372`
wurde nicht benutzt (kein Schiedsrichterfall).

## Bedenken

Keine zum Code. Betrieblich: C: ist voll (0–62 MB frei) — `uvx` (Cache auf C:) und `tee` auf die Tool-Pipe können dadurch sporadisch
mit `os error 112` / „No space left on device“ scheitern.
