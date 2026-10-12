# Probelauf Plan PR 2 -- Schritte (RED/GREEN)

Worktree: D:\Entwicklung\HASI\issue8-pr2-work\probe-wt, Branch probe/pr2-plan, Basis upstream/master 6a40e083.

## Task 0

- Step 1: `git rev-parse --short=8 upstream/master` = `6a40e083` (wie erwartet).
- Step 2: Worktree `probe-wt`, Branch `probe/pr2-plan` (no-track) von upstream/master, `_local_socket_unblock.py` kopiert. HEAD 6a40e083.
- Step 3: Baseline volle Suite: `7 failed, 3819 passed, 9 skipped, 11 warnings, 430 errors in 359.62s (0:05:59)`, 3835 gesammelt.
  Namensliste `names-baseline.txt` (437 Zeilen: 7 FAILED, 430 ERROR). Die ERRORs sind Teardown "Lingering timer after test"
  (`_reset_event_fired_today`, an test_window_amplitude geprueft): der Test selbst zaehlt als passed, das Teardown schlaegt zusaetzlich fehl
  (Vorbestand, Windows). FAILED: test_init (2), test_next_irrigation_sensor (1), test_opensprinkler_teardown (3), test_panel (1).
- Step 4: `npm ci` ok (Node v24.15.0), `npx vitest run src/views/mappings/view-mappings-save.test.ts` -> `7 passed (7)` wie erwartet.

## Task 1 (Commit 3426f5f0)

- Step 2 RED: `ImportError: cannot import name 'blocked_spans'` beim Sammeln (1 error, 0 collected) -- wie erwartet.
- Step 6 GREEN: `80 passed` = 15 neue (`--co`: 15 tests collected) + 65 aus test_sensor_liveness.py -- wie erwartet (15 neue).
- Step 7: black `71 files left unchanged`; ruff: 20 Befunde UP017, alle in Dateien, die der Plan nicht anfasst (siehe deviations.md D1). Commit ok.

## Task 2 (Commit 21cd6cdd)

- Step 2 RED: `10 failed in 2.81s`. Plan erwartete "FAIL mit KeyError: 'on_silent_sensor'": tatsaechlich `KeyError: 'on_silent_sensor'` (u.a. first_setup, keeps[None|sometimes|1|stored3], carried_over)
  und 3 x `TypeError: MappingEntry.__init__() got an unexpected keyword argument 'on_silent_sensor'` (`test_a_stored_setting_survives_a_reload[keep|pause]`, `test_a_save_without_the_setting_leaves_it_alone`; Kopf der Ausgabe nicht mitgeschnitten) -- Zahl (10) stimmt, Fehlertext nur teilweise (D3).
- Step 6 GREEN: `35 passed` = 10 neue + 10 (test_sensor_liveness_store) + 15 (test_store) -- wie erwartet (10 neue).
- Step 7: black unveraendert, ruff nur die 20 UP017 (D1). Commit ok.

## Task 3 (weather_aggregate; Commit siehe git log)

- Step 2 RED: `23 failed in 3.32s`, alle `TypeError: aggregate_window() got an unexpected keyword argument 'blocked'` -- wie erwartet; `--co`: 23 Tests.
- Step 7 GREEN: `113 passed` = 23 neue + 32 (test_weather_aggregate) + 5 (opt_in) + 53 (test_continuous_update) -- wie erwartet (23 neue), im ersten Anlauf, ohne Korrektur am Snippet.
- Step 8: black formatierte die neue Testdatei um (`1 file reformatted`), Produktionscode unveraendert; ruff nur UP017 (D1).

## Task 4 (Gate und Transport)

- Step 2 RED: `12 failed, 12 errors in 4.04s` (12 neue Tests; die 12 errors sind Teardown "Lingering timer", siehe D4). Fehler: `AttributeError ... _blocked_spans_for_zone`,
  `TypeError: ... unexpected keyword argument 'blocked'`, ausserdem `KeyError: 'blocked'` (Plan nannte nur AttributeError/TypeError) -- Zahl 12 stimmt.
- Step 8 Beleg: ohne den Fake-Store-Zusatz scheitert `tests/test_run_in_flight.py::test_calculation_runs_normally_with_no_run_in_flight`
  (`AttributeError: '_FakeStore' object has no attribute 'get_mapping'`, `1 failed, 30 passed`) -- der Zusatz ist noetig, wie im Plan.
- Step 9 GREEN: `99 passed, 57 errors in 12.35s`; alle 12 neuen Tests passed. Die 57 errors = Teardown "Lingering timer" (45 Vorbestand der Nachbardateien
  laut Baseline: per_zone 3 + window_amplitude 7 + live_estimate_measured_radiation 35, plus 12 NEUE, jeweils der Test passed). Plan: "alle gruen (12 neue Faelle)" -- passed stimmt, die Teardown-ERRORs der neuen Tests stehen nicht im Plan (D4).
- Step 10: black formatierte nur die neue Testdatei um; ruff nur UP017. Commit ok. Snippets von Task 4 liefen im ersten Anlauf ohne Korrektur.

## Task 5 (Buchen nur fuer den gemessenen Anteil; Commit 1fc1412b)

- Step 2 RED: `7 failed, 17 passed, 23 errors` (errors = Teardown "Lingering timer", D4). Die 7 Fehler: `KeyError: 'blocked'` (module_is_handed_the_spans),
  `ImportError ... _REQUIRED_SENSOR_FIELDS`, 3 x Buchung `-4.0` statt `-3.1666...` (pyeto share, forecast_days, passthrough share),
  PyETO ruft das Modul trotz ganz gesperrtem Taupunkt (`Called 1 times`), Passthrough: Wasserzeichen `2026-07-01` statt `2026-07-02` (Fenster nicht verbraucht, wegen ERROR).
  Die 17 gruenen = 12 aus Task 4 + die im Plan genannten 5 (zwei Byte-Identitaets-Tests, Static, field_pyeto_does_without, passthrough_for_another_reason) -- genau wie im Plan.
- Step 7 GREEN: `83 passed, 42 errors` (alle 12 neuen passed; 42 errors = 23 aus test_silent_sensor_commit + 19 Vorbestand-Teardown der Nachbardateien: manual_bucket 5, mid_window 4, summed_hourly 10 -- identisch zur Baseline). Plan: "12 neue Faelle" stimmt.
- Step 8: black ("1 file reformatted"), ruff nur UP017. Snippets liefen ohne Korrektur.

## Task 6 (Erklaerungssaetze; Commit siehe git log)

- Step 2 RED: `4 failed, 1 passed, 24 deselected, 5 errors` -- 4 x `assert '... (sensor silent).' in '...'` (bzw. `assert 0 == 2`), `test_a_group_that_keeps_gets_no_sentence` gruen -- wie im Plan.
- Step 5 GREEN: `96 passed, 28 errors` (test_silent_sensor_commit 29 Tests, davon 28 mit Teardown-ERROR, D4; test_i18n_completeness 67 gruen). Alle 5 neuen gruen.
- Anker: `calculate_module` ist das LETZTE Mitglied der Klasse/Datei (`return data` am Dateiende) -- "direkt nach calculate_module" heisst also: ans Dateiende angehaengt (D5, kein Eingriff).
- Beobachtung (kosmetisch, vorbestehend): die Erklaerung hat kein Leerzeichen vor "Bucket was" ("... of -1.58." + "Bucket was" auch vorher); mit den neuen Saetzen: `...Evapotranspiration booked for 79 % of the period.Bucket was 0.00.` Die neuen Saetze setzen ein Leerzeichen davor, aber keines danach.
- Plan-Snippets liefen ohne Korrektur.

## Task 7 (Hinweis-Variante; Commit 146d306e)

- Step 2 RED: `4 failed, 2 passed, 37 deselected`: falscher `translation_key` (`'weather_sensor_stale' == 'weather_sensor_stale_paused'`),
  2 x `KeyError: 'translation_key'` (Re-Sync fehlt), `AttributeError: ... 'async_resync_stale_issue'`. Schon gruen: `test_under_the_hourly_calculation...` und `test_a_rename...` -- genau wie im Plan.
  Der Plan-Satz "fehlender Log-Text" wurde im ersten Test nicht erreicht, weil die Key-Assertion davor scheitert.
- Step 6: Beschreibungstexte der 8 Sprachen programmatisch aus dem Plan (Task 7 Step 6) in `translations/*.json` uebernommen (JSON-escaped, `json.loads` ok, Titel == Titel von `weather_sensor_stale`);
  die Task-6-Tabelle gegen `frontend/localize/languages/*.json` byte-genau verglichen: `rows 8 mismatches 0`.
- Step 7 GREEN: `185 passed` (6 neue in test_sensor_liveness_coordinator; kein Teardown-ERROR in diesen Dateien) -- wie erwartet.
- Plan-Snippets liefen ohne Korrektur. Anker-Hinweis: Zeilenangaben des Plans (`:454-462`, `:1245`, `:1842-1844`) stimmten nach den vorherigen Tasks nicht mehr (Verschiebung), die Textanker passten; `async_dispatcher_send(...)` steht im Code dreizeilig (nicht einzeilig wie im Plan zitiert).

## Task 8 (View-Schema, Panel, Bundle; Commit siehe git log)

- Step 2 RED: pytest `1 failed, 10 passed` (`ImportError: cannot import name 'MAPPING_VIEW_SCHEMA'`); vitest `1 failed | 8 passed (9)`
  (`saves the setting for a silent sensor with the group` fehlt `on_silent_sensor: "keep"` im gesendeten Koerper; `sends no setting...` schon gruen) -- wie im Plan.
- Step 8 GREEN: pytest `78 passed` (11 test_silent_sensor_setting inkl. 1 neuer + 67 i18n); vitest gesamt `27 files, 661 tests passed` (2 neue in view-mappings-save.test.ts -> Datei jetzt 9 Tests).
- Step 9 `npm run build`: SCHEITERT zuerst am Lint (prettier) in der Plan-Testzeile (D6a), nach Korrektur `created dist` fuer alle 4 Bundles. `git status` zeigt danach 4 Bundles " M".
- Step 10: `git diff --cached --name-only | grep -c "frontend/dist/"` = **2**, nicht 4 (D6b). Staged: irrigation-plus.js (+909/-890) und irrigation-plus-card-impl.js (1 Zeile);
  irrigation-plus-card.js und -card-legacy.js sind nach dem Bau byte-identisch mit HEAD (sha256 verglichen), "M" in git status war nur Stat-Dirty durch das Neuschreiben.
- black: unveraendert; ruff nur UP017.

## Task 9 (Doku, Live-Schaetzung-Kommentare; Commit siehe git log)

- Kein automatischer Test. Kriterium Step 3 geprueft: `grep -c "Meanwhile the calculation keeps using" docs/configuration-sensor-groups.md` = **0**;
  `grep -n "Keep the last value"` -> Zeilen 60 (Liste) und 64 (letzter Satz des Absatzes zu den festen drei Stunden); `grep -n "pausing" live_estimate.py` -> Zeilen 598 und 625 (beide Stellen).
- Der Plan-Satz "`grep -n "exactly" ... zeigt an beiden Stellen den Zusatz`" (Kriterium vorab) trifft nicht zu: der Zusatz enthaelt das Wort "exactly" nicht; `grep -n "pausing"` (Step 3) ist das taugliche Kriterium (D7, kosmetisch).
- Der englische Doku-Block wurde programmatisch aus dem Plan uebernommen (4 Absaetze; Absatz 2 -> :57, Absatz 4 ersetzt den bestehenden Absatz :59). Die Zeilenangabe `:54-61` stimmte.

## Task 10 (Steps 1-4 und 6; Step 5 Review laut Auftrag nicht ausgefuehrt)

- Step 1 Lint: `black --check custom_components/irrigation_plus/` -> `70 files would be left unchanged`; `black --check` der 6 Testdateien -> `6 files would be left unchanged`;
  `ruff check custom_components/irrigation_plus/` -> `Found 20 errors` (alle UP017 in Dateien, die der Branch nicht anfasst, D1); `ruff check` nur auf den vom Branch geaenderten .py-Dateien -> `All checks passed!`.
- Step 2 Volle Suite (suite-pr2.txt): `7 failed, 3903 passed, 9 skipped, 11 warnings, 458 errors in 350.76s (0:05:50)`.
  Baseline (suite-baseline.txt): `7 failed, 3819 passed, 9 skipped, 11 warnings, 430 errors in 359.62s`.
  - passed: 3903 - 3819 = **+84** = berechnete 84 (15 + 11 + 23 + 29 + 6); `--co`: test_sensor_liveness_blocked 15, test_silent_sensor_setting 11, test_weather_aggregate_blocked 23, test_silent_sensor_commit 29, TestThePausedNotice 6.
  - Gesamt gesammelt: 3835 -> 3919 (= 7 + 3903 + 9).
  - failed: 7 = 7, die FAILED-Namen sind identisch (`diff` der FAILED-Zeilen leer).
  - errors: 458 - 430 = **+28**. Namensvergleich `diff names-baseline.txt names-pr2.txt`: 0 Namen entfallen, **28 hinzugekommen, alle `ERROR tests/test_silent_sensor_commit.py::...`** (Teardown "Lingering timer", der Test selbst passed; D4).
    "Namen gleich" aus dem Plan ist daher woertlich NICHT erfuellt; die Abweichung ist vollstaendig durch die neuen Tests erklaert.
- Step 3 Frontend: `npx vitest run` -> `27 passed (27)` Dateien, `661 passed (661)` Tests; `npm run build` Exit 0, 4 Bundles erzeugt; danach `git status --short` leer und `git diff --quiet HEAD -- dist/` -> dist == HEAD (der committete Stand ist der gebaute) -- wie erwartet.
- Step 4 Mutationen (mutate-pr2.py, mutate-pr2.txt, mutations-pr2.json): Vorlauf unmutiert `121 passed, 28 errors` (nur Teardown-ERRORs, keine FAILED); **22 killed / 22 applied / 22 total**,
  keine SURVIVED, keine HANG, keine BROKEN, keine NOT APPLIED. Bei allen 22 ist der im Plan genannte Killer unter den toeten Tests (`expected_killer_among_killers` = true fuer alle).
  Rueckgesetzt: sha256 jeder der 6 Quelldateien nach jedem Lauf und am Ende gleich dem Original, `git diff --quiet HEAD` ok, `git status --short` im Worktree danach leer.
  Zusaetzliche Killer jenseits der genannten (z.B. M1 15 Tests, M5 10 Tests) stehen in mutate-pr2.txt.
- Step 6 Eigene Bezuege: beide Greps des Plans leer (`Eifel-Joe|spec D[0-9]|spec §|Task [0-9]|PR [123]\b|PR [A-T]\b` auf den hinzugefuegten Zeilen; `Eifel-Joe#|JustChr#` in den Commit-Messages);
  zusaetzlich geprueft auf `Rev. 3|F1-F4|Entscheidung|Faktensammlung|#188|#190|#8|issue 8|PR 2|Part 2`: leer.
- Patch/Commits: probe-2026-10-12.patch (`git diff upstream/master..HEAD`, 969692 Byte), commits.txt (9 Commits). Diffstat: 36 Dateien, +2612/-935.

