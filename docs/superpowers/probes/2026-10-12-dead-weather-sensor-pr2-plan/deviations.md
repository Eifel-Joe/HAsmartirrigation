# Abweichungen vom Plan

Je Abweichung: Task/Step, Plan, was passierte, Korrektur, Grund.

## D1 -- Umgebung: ruff 0.17.0 meldet 20 vorbestehende UP017 (Task 1 Step 7, gilt fuer alle Tasks)
- Plan: `uvx ruff check custom_components/irrigation_plus/` "sauber".
- Passiert: `uvx` zieht ruff 0.17.0; es meldet `UP017 Use datetime.UTC alias` in forecast_window.py und weathermodules/*Client.py
  (20 Stellen), alles Dateien, die der Plan nicht anfasst, schon auf upstream/master 6a40e083. Keine Befunde in den vom Plan geaenderten Dateien.
- Behandlung: nicht angefasst. Pruefung je Task: `ruff check ... --output-format concise | grep -v UP017` muss leer sein (Befunde in Plan-Dateien sonst Abweichung).
- Hinweis fuer Plan/Task 10 Step 1 "alles sauber": mit dieser ruff-Version nicht erreichbar; die CI-Version ist vermutlich aelter (nicht geprueft).

## D2 -- Commit-Trailer (alle Commits)
- Plan: `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- Passiert: Der Probelauf laeuft als Sonnet 5.5; der Trailer nennt in den Probe-Commits `Claude Sonnet 5.5` (Vorgabe der Sitzung), nicht Opus 5.5.
  Rein kosmetisch fuer Wegwerf-Commits; fuer den echten Lauf bleibt die Zeile des Plans.

## D3 -- Task 2 Step 2, RED-Beschreibung ungenau (kein Eingriff)
- Plan: "FAIL mit `KeyError: 'on_silent_sensor'`". Tatsaechlich 10 FAIL, davon (sichtbar) 3 `TypeError: MappingEntry.__init__() got an unexpected keyword argument 'on_silent_sensor'`
  (`async_update_mapping` ruft `attr.evolve` mit dem unbekannten Feld). Zahl stimmt, Ursache dieselbe (Feld fehlt). Keine Korrektur noetig; nur die Erwartung im Plan praezisieren.

## D4 -- Task 4 Step 9 (und alle Tasks mit echtem Koordinator): Teardown-ERROR "Lingering timer" bei den NEUEN Tests
- Plan: "alle gruen"; Task 10 Step 2 erwartet `Namen gleich` (FAILED/ERROR-Namensliste = Baseline).
- Passiert: Jeder neue Test in `tests/test_silent_sensor_commit.py`, der den `coord`-Fixture (echter `SmartIrrigationCoordinator`) nutzt, endet mit
  `ERROR at teardown ... Failed: Lingering timer after test <TimerHandle ... _reset_event_fired_today>`; der Test selbst ist passed. Dasselbe Muster
  haben auf der Baseline 430 vorhandene Tests (Vorbestand, Windows/HA-Version, Memory hasi-local-test-env-rebuild).
  Folge: In Task 10 enthaelt `names-pr2.txt` zusaetzliche ERROR-Namen aus den neuen Dateien (alle in tests/test_silent_sensor_commit.py und evtl. test_sensor_liveness_coordinator.py).
- Behandlung: nicht korrigiert (kein Planfehler im Code; Fixture-Konstruktion wie in tests/test_window_amplitude.py). Vergleich in Task 10: Namen der Baseline muessen alle
  unveraendert da sein, neue Namen duerfen NUR aus neuen Tests stammen.

## D5 -- Task 6 Step 3: Einfuegestelle der Methode
- Plan: "direkt nach `calculate_module` die Methode `_silent_sensor_explanation`". Auf 6a40e083 ist `calculate_module` das letzte Mitglied der Datei; die Methode steht daher am Dateiende. Keine inhaltliche Abweichung.

## D6a -- Task 8 Step 1/9: Plan-Testzeile besteht prettier nicht, `npm run build` scheitert
- Plan (Step 1, vitest): `el.handleEditMapping(0, { ...group(1, "Garden"), on_silent_sensor: "keep" });` (eine Zeile, 83 Zeichen).
- Passiert: `npm run build` -> `npm run lint` -> `view-mappings-save.test.ts 137:30 error Replace ... prettier/prettier`; Build bricht vor Rollup ab.
- Korrektur: `npx eslint --fix src/views/mappings/view-mappings-save.test.ts` -> der Aufruf wird dreizeilig (`el.handleEditMapping(0, {` / `...group(1, "Garden"),` / `on_silent_sensor: "keep",` / `});`). Reine Formatierung, Test unveraendert; vitest danach weiter `661 passed`.
- Plan-Korrektur: Die Zeile im Plan so umbrechen.

## D6b -- Task 8 Step 9/10: nur 2 von 4 Bundles aendern sich, Erwartung "4" falsch
- Plan: "git status zeigt die 4 Bundles als geaendert" und `git diff --cached --name-only | grep -c "frontend/dist/"` -> "Expected: 4".
- Passiert: `git status` zeigt nach dem Bau 4 Bundles " M" (alle vier neu geschrieben), nach `git add -f` stehen aber nur 2 im Index (`irrigation-plus.js`, `irrigation-plus-card-impl.js`);
  `irrigation-plus-card.js` (1668 B) und `irrigation-plus-card-legacy.js` (2017 B) sind byte-identisch mit HEAD (sha256 55aefaf17f25 / aa09a91dffdb).
- Korrektur: keine am Code; die Zahl im Plan ist auf `2` zu setzen (die Panel-Aenderung betrifft nur das Panel-Bundle und das Card-Impl-Bundle). Die Dateizahl-Pruefung hier hat den falschen Alarm erzeugt, den der Plan vermeiden wollte; im echten Lauf nicht auf 4 "nachstagen".
- card-impl.js aendert sich um genau 1 Zeile (+437 Byte): dort steht der englische Text `"on-silent-sensor":{title:"When a sensor goes silent", ...}` (en.json ist in dieses Bundle eingebaut).

## D7 -- Task 9, Kriterium vorab (kosmetisch)
- Plan: `grep -n "exactly" custom_components/irrigation_plus/live_estimate.py` soll "an beiden Stellen den Zusatz" zeigen. Der eingefuegte Zusatz enthaelt "exactly" nicht; die Stellen sind per `grep -n "pausing"` (Step 3) zu finden. Nur das Kriterium im Plan umformulieren.

## D4 (Nachtrag, Task 10 Step 2) -- "Namen gleich" nicht woertlich erfuellt
- Ergebnis: 0 Baseline-Namen entfallen, 28 neue `ERROR tests/test_silent_sensor_commit.py::...` (Teardown "Lingering timer", Test selbst passed). FAILED-Mengen identisch. passed +84 wie berechnet.
- Im Plan zu praezisieren: Task 10 Step 2 vergleicht "Namen der Baseline sind alle noch da, neue Namen nur aus den neuen Tests" (`comm -23` leer) statt `diff` gleich; oder die Fixture so bauen, dass sie keinen Timer hinterlaesst (nicht untersucht).

