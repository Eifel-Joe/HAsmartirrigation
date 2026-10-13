# SDD ledger — plan: D:/Entwicklung/HASI/HAsmartirrigation/docs/superpowers/plans/2026-10-12-dead-weather-sensor-pr2.md

Spec: docs/superpowers/specs/2026-10-11-dead-weather-sensor-pr2-design.md (+ Rev. 3 2026-10-03-dead-weather-sensor-design.md)
Worktree: D:/Entwicklung/HASI/issue8-pr2-work/wt, Branch feat/pause-silent-weather-sensor (no tracking), Basis 6a40e083
Session 2026-10-12, Controller Opus 5.5.

## Rulings (Setup)

- Ruling: Workspace in `issue8-pr2-work/sdd/` statt `<repo>/.superpowers/sdd/` — User-Regel „Agenten-Ablagen unter …-work“ — kostet nichts.
- Ruling: Spec-Check = `sdd/spec_check.py N BASE HEAD`: Task-Diff je Datei gleich dem Diff des Probe-Commits P[N-1]..P[N] (Probe-Kette 3426f5f0…dfd5c9a8, Range-Diff == probe-2026-10-12.patch byte-gleich, cmp belegt), Subject wie Probe, Trailer Opus 5.5, keine Eigenbezüge — der User erklärt den Patch zum Schiedsrichter — wenn falsch: ein Review-Fix in einem früheren Task, der eine spätere Probe-Zeile verschiebt, meldet FAIL, dann von Hand interdiff prüfen.
- Ruling: Volle Suite + dreiteiliger Namensvergleich je Task fährt der Controller (`sdd/suite_compare.sh tN`, Klassifizierer `classify_new_errors.py`), nicht der Implementer — vermeidet parallele pytest-Läufe (WinError 10055) und 6-min-Läufe im Agenten — kostet: Regression wird erst nach dem Commit gesehen (Fix-Runde statt Vorab-Korrektur).
- Ruling: Implementer Sonnet (User), Task-Reviewer Sonnet (lesen = Sonnet, Memory agent-model-tiering), Abschluss-Review Opus (User/Plan).
- Ruling: Implementer bekommen die Probe-SHA ihres Tasks nur als Schiedsrichter bei scheiterndem Snippet, Cherry-pick/Checkout verboten — wenn falsch: TDD-RED übersprungen; Bericht muss RED-Ausgabe zeigen.
- Ruling: Task 6 Methode `_silent_sensor_explanation` am Dateiende (Probe D5: `calculate_module` ist auf 6a40e083 das letzte Mitglied) — inhaltlich gleich.
- Ruling: Baseline trotz unveränderter Basis neu gemessen (Plan Task 0 Step 3) — kostet 6 min.

## Konflikt-Scan (vor Task 1)

Geprüft gegen den Probelauf (Tasks 1–9 wörtlich in Reihenfolge, jede RED/GREEN traf, steps.md/deviations.md) und die
Dateilisten der Probe-Commits.

| Paar / Task | geteilte Datei / Schnittstelle | Erzeugt → verbraucht | Befund |
|---|---|---|---|
| T1 ↔ T7 | sensor_liveness.py | T1 reine Funktionen + Konstanten → T7 Hinweis-Variante nutzt `group_pauses` | Probe: T7 auf T1 grün; kein Konflikt |
| T1 → T4/T5 | `blocked_spans`, `valid_share`, `group_pauses` | T1 → Gate (T4), Anteil (T5) | Probe grün |
| T2 ↔ T8 | tests/test_silent_sensor_setting.py, `MappingEntry.on_silent_sensor` | T2 Feld + Store → T8 View-Schema/Panel | Probe grün |
| T2 → T4/T7 | `on_silent_sensor` am Mapping | T2 → Gate / Hinweis | Probe grün |
| T3 → T4 | `aggregate_window(…, blocked=)` | T3 → T4 Transport | Probe grün |
| T4 ↔ T5 ↔ T6 | calculation.py, tests/test_silent_sensor_commit.py | T4 Gate/Testdatei → T5 Anteil → T6 Erklärung | Probe grün; T6 Einfügestelle = Dateiende (D5, Ruling oben) |
| T6 ↔ T8 | frontend/localize/languages/*.json (8) | T6 Erklärungsschlüssel, T8 Panel-Schlüssel | verschiedene Schlüssel; Probe grün |
| T4 ↔ tests/test_run_in_flight.py | Fake-Store `get_mapping` | T4 | Probe grün |
| T1 | Text in sich | — | ok (Probe) |
| T2 | RED-Beschreibung | — | im Plan nach D3 berichtigt |
| T3 | Text in sich | — | ok |
| T4 | neue Tests haben Teardown „Lingering timer“ | — | D4; Vergleich per Klassifizierer |
| T5 | Text in sich | — | ok |
| T6 | Einfügestelle | — | D5, Ruling |
| T7 | Text in sich | — | ok |
| T8 | prettier-Zeile, Bundle-Zahl | — | im Plan nach D6a/D6b berichtigt (Soll 2) |
| T9 | Kriterium `pausing` | — | im Plan nach D7 berichtigt |
| alle | ruff 0.17.0 UP017 ×20 in fremden Dateien | — | D1; `grep -v UP017` |

## Fortschritt

Task 0: Worktree angelegt (HEAD 6a40e083, kein Upstream), Baseline läuft
Task 0: complete — Baseline 6a40e083: `7 failed, 3819 passed, 9 skipped, 11 warnings, 430 errors in 382.00s`, names-baseline.txt 437 Namen == probe/names-baseline.txt (diff leer); npm ci ok, vitest view-mappings-save 7 passed; wt clean.
Task 1: implementer done (aad419a9), spec_check PASS (tree == probe 3426f5f0), suite t1 + review laufen
Task 1: review (Sonnet) Spec ✅, quality Approved, 0 Critical/Important
Task 1: minor (deferred): valid_share schneidet übergebene Spannen nicht auf [start,end) zu — Vertrag nur implizit im Aufrufer (gleiches watermark..now), kein Test (sensor_liveness.py:207-219)
Task 1: minor (deferred): berührende Spannen (Ende == Anfang) + Ausfall mit end < start ungetestet; Mutation `<=`→`<` in _merged (:226) überlebte laut Reviewer
Task 1: minor (deferred): outage.start + STALE_AFTER kann bei Jahr-9999-Stempel OverflowError werfen (:198), from_store härtet, blocked_spans nicht
Task 1: minor (deferred): plan-diktierte Kommentare mit Vorwärtsverweisen/holpriger Grammatik (const.py:714-725, group_pauses-Docstring :177)
Task 1: minor (deferred): `blocked: dict`, `fields` lose getypt (:207)
Task 1: suite t1: 7 failed / 3834 passed (+15) / 9 skipped / 430 errors; (1) 0 entfallen, (2) FAILED gleich, (3) keine neuen Namen
Task 1: complete (commits 6a40e083..aad419a9, review clean)
Task 2: implementer done (e30e0602), spec_check PASS (tree == probe 21cd6cdd), suite t2 + review laufen
Task 2: review (Sonnet) Spec ✅, quality Approved, 0 Critical/Important; ⚠️ View-Schema validiert on_silent_sensor noch nicht → gehört zu Task 8 (MAPPING_VIEW_SCHEMA mit vol.In, Mutation 22) — geprüft im Plantext, kein Gap
Task 2: minor (deferred): Lade-Pfad-Parametrisierung ohne Groß/Klein-Variante ("PAUSE") — ein späteres .lower() bliebe unbemerkt (test_silent_sensor_setting.py ~44)
Task 2: minor (deferred): test_a_group_carried_over_from_smart_irrigation_keeps weitgehend redundant zu stored=None; Docstring-Test-ID ohne Klasse (TestStorageImport)
Task 2: minor (deferred): Store prüft on_silent_sensor beim Schreiben nicht (async_create_mapping/async_update_mapping); Laufzeit + Neustart behandeln Müll als keep; Validierung im View-Schema (Task 8)
Task 2: suite t2: 7 failed / 3844 passed (+25) / 9 skipped / 430 errors; (1) 0, (2) FAILED gleich, (3) keine neuen Namen
Task 2: complete (commits aad419a9..e30e0602, review clean)
Task 3: implementer done (373f85f2), spec_check PASS (tree == probe 55339274), suite t3 + review laufen; Implementer verglich nach dem Commit mit dem Probe-Commit (nur diff --stat, gemeldet)
Task 3: review (Sonnet) Spec ✅, quality Approved, 0 Critical/Important; ⚠️ gleiches `end` für blocked_spans/valid_share → geprüft: Gate (T4 Plantext :296) und Anteil (T5 :334) beide watermark..now; Zeit hinter now zählt als gültig = Review Focus der Spec
Task 3: minor (deferred): test_a_field_blocked_throughout_is_left_out_and_not_filled — last_entry wirkungslos (Fixture liefert T-Zeilen), Carry-forward-Fall nicht gepinnt (test :126-130)
Task 3: minor (deferred): unerreichbare Zweige `... if values else held[0]` / `elif not values` (weather_aggregate.py:647, :650-651), plan-diktiert
Task 3: minor (deferred): Testlücken: ≥2 Spans an einem Feld; Riemann mit gesperrtem Fensterstart/-ende; time_weighted mit Span am Ende
Task 3: minor (deferred): offener Span bis now + Zeile hinter now: Segment (now, window_end) gültig im Aggregat, nicht in valid_share (Uhrversatz, vernachlässigbar)
Task 3: minor (deferred): Riemann-Feld mit einer behaltenen Zeile bucht Rate als mm (spiegelt Bestand _aggregate :551-555)
Task 3: suite t3: 7 failed / 3867 passed (+48) / 9 skipped / 430 errors; (1) 0, (2) FAILED gleich, (3) keine neuen Namen
Task 3: complete (commits e30e0602..373f85f2, review clean)
Task 4: implementer done (d31311ed), spec_check PASS (tree == probe 6035e583), suite t4 + review laufen
Task 4: Plan-Mangel: Step 5 „im Docstring nach dem ersten Absatz ergänzen“ doppeldeutig (Titelzeile vs. Absatz); Implementer las den Probe-Commit (Regel 9) und setzte den Absatz direkt nach die Titelzeile → im Plan berichtigen (P1-Nachlauf)
Task 4: review (Sonnet) Spec ✅, quality Approved, 0 Critical/Important; ⚠️ calculate_module bekommt blocked erst in T5 (Plan) und live_estimate-Kommentare sind bis T9 für pausierende Gruppen unwahr (T9 Step 2) → beide im Plan, kein Gap
Task 4: minor (deferred): kein Gate-Test mit offenem Ausfall (end=None) — Fensterende = now des Commits ungepinnt (Mutation auf anderes Ende überlebte)
Task 4: minor (deferred): Offset-Test nutzt HAs eigene Zone → unterscheidet „auf HAs Uhr umrechnen“ nicht von „tzinfo abschneiden“; aware watermark/now durchs Gate ungetestet (test :452-464)
Task 4: minor (deferred): Gate-Docstring (plan-diktiert) „that form cuts together with the live estimate“ liest sich als Ist-Zustand (calculation.py:401-403)
Task 4: minor (deferred): `watermark >= now` redundant zu blocked_spans (äquivalente Mutation) (calculation.py:418)
Task 4: suite t4: 7 failed / 3879 passed (+60) / 9 skipped / 442 errors (+12); (1) 0, (2) FAILED gleich, (3) 12 neue ERROR test_silent_sensor_commit.py, alle Teardown Lingering timer (UNEXPECTED 0)
Task 4: complete (commits 373f85f2..d31311ed, review clean)
Task 5: implementer done (4c74320e), spec_check PASS (tree == probe 1fc1412b), suite t5 + review laufen; Scratch-Datei des Implementers nicht im wt (status --ignored nur Caches + socket-Plugin)
Task 5: review (Sonnet) Spec ✅, quality Approved, 0 Critical/Important
Task 5: minor (deferred): test_with_forecast_days_the_whole_mean_is_scaled testet keine Prognosetage (Stub konstant, Tagespfad liest forecast_days nicht) (test :309)
Task 5: minor (deferred): test_a_pausing_group_under_the_hourly_calculation_matches_too läuft nicht durch den Stunden-Zweig (Mock ohne DontEstimate) (test :456)
Task 5: minor (deferred): ungetestet: Anteil knapp über 0 (Gleichung wird gefragt); Regen bei 0<share<1 (precip unskaliert)
Task 5: minor (deferred): Fenster (watermark, now) doppelt hergeleitet (Gate :437-439 und calculate_module :1255-1263), plan-diktiert; Guard watermark is not None über den Koordinator unerreichbar
Task 5: minor (deferred): et_term im Kc-Satz unskaliert (calculation.py:1353) — Task-6-Review auf Kohärenz der Erklärung mit Kc≠1 hinweisen
Task 5: suite t5: 7 failed / 3891 passed (+72) / 9 skipped / 453 errors (+23); (1) 0, (2) FAILED gleich, (3) 23 neue ERROR test_silent_sensor_commit.py, alle Teardown Lingering timer (UNEXPECTED 0)
Task 5: complete (commits d31311ed..4c74320e, review clean)
Task 6: implementer done (d2913ab2), spec_check PASS (tree == probe c5f36693), suite t6 + review laufen (Review mit Hinweis auf et_term/Kc aus T5)
Task 6: review (Sonnet) Spec ✅, quality Approved, 0 Critical/Important; ⚠️ dist erst in T8 (Plan), Stundenrechnung → kein Satz (gewollt, gepinnt)
Task 6: minor (deferred, User-Entscheidung): Rundung „100 %“ bei kurzer Sperre (<~7 min in 24 h) direkt hinter „No values from … (sensor silent)“, „0 %“ bei 0<share<0,005 (calculation.py:1912-1916, Format plan-diktiert)
Task 6: minor (deferred): Erklärungszweig share == 0 („booked for 0 %“) ungepinnt (Mutant `0 < share < 1` überlebte)
Task 6: minor (deferred): Reihenfolge mehrerer Sätze (sorted(fields_by_span)) ungepinnt (:1900)
Task 6: minor (deferred): Kc≠1 mit Teilanteil ungetestet; et_term im Kc-Satz unskaliert, Satzfolge lesbar (calculation.py:1531)
Task 6: minor (deferred): vorbestehend: kein Leerzeichen vor „Bucket was“ (nicht in diesem PR beheben, SESSION-STAND 2026-10-12)
Task 6: minor (deferred): Satz 1 auch für Zonen, deren Modul das Feld nicht nutzt (Static), plan-diktiert
Task 6: suite t6: 7 failed / 3896 passed (+77) / 9 skipped / 458 errors (+28); (1) 0, (2) FAILED gleich, (3) 28 neue ERROR test_silent_sensor_commit.py, alle Teardown Lingering timer (UNEXPECTED 0)
Task 6: complete (commits 4c74320e..d2913ab2, review clean)
Task 7: implementer done (a0efb498), spec_check PASS (tree == probe 146d306e), suite t7 + review laufen
Task 7: review (Sonnet) Spec ✅, quality Approved, 0 Critical/Important; ⚠️ „Umbenennen aktualisiert Hinweis“ war MEIN Fehler im Review-Prompt — Plan-Test pinnt „a rename leaves the notice alone“, gebaut nach Plan, kein Gap; ⚠️ Optionsnamen im Hinweis == Panel-Beschriftungen (T8) → in T8-Review prüfen; ⚠️ View-Schema erst T8, E2E im Live-Test T11
Task 7: minor (deferred): Re-Sync-Hooks in __init__.py ungeschützt (:1246-1250, :1844-1846) — Fehler würde Dispatch überspringen + HTTP 500; Setup/Check kapseln dieselbe Arbeit in try/except; Basis-_retire_outages ebenso ungeschützt
Task 7: minor (deferred): Hook-Tests pinnen Reihenfolge (nach dem Schreiben) nicht; Mapping-Test ändert nichts (schon pause)
Task 7: minor (deferred): kein Test, dass Config-Speichern ohne CONF_HOURLY_CALCULATION nicht re-synct
Task 7: minor (deferred): async_resync_stale_issue ohne @callback (Schwester async_teardown_sensor_liveness hat es)
Task 7: minor (deferred): Doppelte Logik: Re-Sync-Schleife == Setup-Schleife; name-Fallback 4×; _group_cuts ↔ _blocked_spans_for_zone nur per Docstring gekoppelt
Task 7: minor (deferred): Hinweistext „values are no longer used“ gilt nicht für Regenzähler (DELTA nie gesperrt), plan-diktiert
Task 7: suite t7: 7 failed / 3902 passed (+83) / 9 skipped / 458 errors; (1) 0, (2) FAILED gleich, (3) weiter nur die 28 Teardown-ERROR aus T4–T6 (UNEXPECTED 0)
Task 7: complete (commits d2913ab2..a0efb498, review clean)
Task 8: implementer done (2621a230), spec_check PASS (tree == probe acb8409c, inkl. 2 Bundles), Bundles im Commit: 2; Review-Paket ohne dist (review-t8.diff), suite t8 + review laufen
Task 8: review (Sonnet) Spec ✅, quality Approved, 0 Critical/Important; Optionsnamen Panel == Zitate im Hinweis (alle 8 Sprachen, per Skript); mein Prompt-Satz „the vitest pins both“ war überzogen (vitest pinnt nur das Speichern)
Task 8: minor (deferred, plan-mandated): Anzeige ungepinnt (`?? "pause"`, ?selected, @change) — Mutant `?? "keep"` überlebt (view-mappings.ts:1085, :1109)
Task 8: minor (deferred, plan-mandated): Schema-Test prüft nicht, dass Weglassen weggelassen bleibt — Mutant `vol.Optional(KEY, default="pause")` überlebt und würde bei jedem Speichern eines alten Panels keep überschreiben (test_silent_sensor_setting.py:105-111)
Task 8: minor (deferred): "keep"/"pause" als lose String-Literale in TS, Typ nur string (types.ts:426)
Task 8: suite t8: 7 failed / 3903 passed (+84) / 9 skipped / 458 errors; (1) 0, (2) FAILED gleich, (3) nur die 28 Teardown-ERROR (UNEXPECTED 0) == Probelauf-Endstand
Task 8: complete (commits a0efb498..2621a230, review clean)
Ruling: Die volle Suite nach Task 9 (nur Doku + Kommentare) gilt zugleich als Task 10 Step 2, weil HEAD dann der Endstand ist — spart einen 6-min-Lauf — wenn falsch: kein Risiko, derselbe Commit
Task 9: implementer done (a9708bec), spec_check PASS (tree == probe dfd5c9a8 == Probe-Endstand), suite t9 (= T10 Step 2) + review laufen
Task 10 Step 1 (Lint, HEAD a9708bec): black 26.10.1 + black 26.10.0 (CI 06.10.) `70 files would be left unchanged`; 6 Testdateien unverändert; ruff 0.16.10 (CI-Version JustChr master 06.10., Run 37516590024) `All checks passed!` auf custom_components/irrigation_plus/; ruff 0.17.0 (PyPI latest, upload 2026-10-09T19:46) nur auf den 8 vom Branch geänderten .py `All checks passed!`, auf dem Paket 20× UP017 in forecast_window.py + 4 weathermodules/*Client.py (vom Branch unberührt)
BEFUND (User-Entscheidung): CI installiert ruff ungepinnt (`pip install ruff black isort`, pytest.yml:91) → nächster Lauf mit 0.17.0 wird im Lint-Job rot, unabhängig von PR 2; Optionen: im PR-Text erwähnen / eigener kleiner Upstream-PR (UP017-Fix oder Pin) / nichts
Task 9: review (Sonnet) Spec ✅, quality Approved, 0 Critical/Important; jede Doku-Aussage am Branch-Code belegt
Task 9: minor (deferred, User-Wortlaut): Doku :59 „values are no longer used … books no evapotranspiration for that time“ gilt nur für Pflichtfelder (_REQUIRED_SENSOR_FIELDS); stumme Sonne/Feuchte → volles ET
Task 9: minor (deferred, plan-mandated): live_estimate.py :590/:594-596 „reduced exactly as …“/„agree by construction“ bleiben unqualifiziert; ähnliche Sätze :15-21, :912-915, :1108
Task 9: minor (deferred, User-Wortlaut): „the hourly calculation“ ist nicht der UI-Name (Einstellung „Hourly evapotranspiration“/„Sum evapotranspiration hour by hour“) — Doku :62 + Panel-Hilfe en.json:470
Task 9: minor (deferred, User-Wortlaut): Doku :64 „With **Pause**, set such a sensor group to **Keep the last value**“ liest sich widersprüchlich
Task 9: minor (deferred): Doku :59 „the sensor's last report“ — Ausfallbeginn ist das letzte Lebenszeichen des Geräts
Task 9: minor (deferred): = T4-Minor Gate-Docstring calculation.py:423-424 „that form cuts together with the live estimate“
Task 10 Step 4 vorbereitet: sdd/mutate-pr2.py (= probe/mutate-pr2.py, nur WT/OUT/PROBE-Pfade, diff belegt), MUT_CHECK: 22/22 Anker genau einmal auf a9708bec
Task 9: suite t9: 7 failed / 3903 passed (+84) / 9 skipped / 458 errors; (1) 0, (2) FAILED gleich, (3) 28 Teardown-ERROR (UNEXPECTED 0); names-t9 == probe/names-pr2 (diff leer)
Task 9: complete (commits 2621a230..a9708bec, review clean)
Task 10 Step 2: = suite t9 (Ruling oben), Erwartung Plan: passed = Baseline + 84 (3819 → 3903) ✓, failed wie Baseline ✓, neue Namen nur 28 Teardown aus test_silent_sensor_commit.py ✓
Task 10 Step 3: vitest 27 files / 661 passed; npm run build ok; danach alle 4 Bundles git diff --quiet (unverändert), git status leer
Task 10 Step 6: Diff-Grep (Plan-Muster) 0 Treffer, Commit-Messages Eifel-Joe#/JustChr# 0, Zusatzmuster (Rev. 3|F1-4|#188|#190|#8|PR 2|Part 2|…) 0, git grep Eifel-Joe# HEAD 0; 9 Commits, alle Trailer Opus 5.5
Task 10 Step 4: Mutationen 22 killed / 22 applied / 22 total, expected killer among killers 22/22, Vorlauf unmutiert 121 passed, 28 errors (nur Teardown); sha256 restore True, git diff --quiet HEAD True (sdd/mutate-pr2.txt, sdd/mutations-pr2.json)
Task 10 Step 5: Abschluss-Review (Opus) „With fixes“: 0 Critical, 2 Important, 7 Minor (+ Triage der 43 deferred minors) → final-review-report.md
  Important 1 (Hinweis/Log melden Schnitt, den die Rechnung nicht macht: nur-Regenzähler-Ausfall → paused-Text; Nicht-Pflichtfelder → „no ET booked“ falsch) — vom Controller nachgeprüft: Code folgt Spec §5 wörtlich (Variante = pause UND nicht Stundenrechnung, ohne Feldbezug) → Spec-Lücke, kein Umsetzungsfehler; Probe des Reviewers sdd/probe_rain_notice.py
  Important 2 (Standard pause + gerätelose Template-Sensoren wie `wind_at_2m` aus der Doku :43-49 → windstille Nacht = Ausfall → Wind (Pflichtfeld) gesperrt → ~29 % ET weg) — nachgeprüft: Doku :66 nennt gerätelose Template-/Utility-Meter-Sensoren selbst als „looks silent“; Rev. 3 nahm nur den Fehlalarm hin
Ruling: STOP vor der Fix-Welle — beide Important berühren Spec §5 und vom User freigegebene Wortlaute (Hinweis, Doku, Panel-Hilfe) bzw. die Standard-Entscheidung 9 → User-Entscheidung; die reinen Test-Pins/Kommentare bündle ich danach in EINE Fix-Welle — kostet: Wartezeit bis zur Antwort
Archiv: 342be9e1 gepusht (4abd4c7a..342be9e1, origin == lokal 0/0); Upstream-Runde 19:05 UTC leer (6a40e083). Entscheidungsfragen E1–E4 an den User gestellt; Fix-Welle wartet.
User 2026-10-13: E1=2, E2=2, E3=Ok, E4=3; Wortlaute de/en freigegeben („Texte freigegeben“)
Spec-Nachtrag 2026-10-13 + Plan Task 10b (C1–C6) geschrieben (Hauptbaum, ungetrackt)
Ruling: die zwei „unerreichbaren“ Zweige in _aggregate_blocked bleiben und werden gepinnt statt entfernt — über den Commit unerreichbar (Gate nur mit Wasserzeichen, dann ≤1 Zeile ≤ start), ohne Wasserzeichen aber erreichbar, ohne sie würfe statistics.mean([]) — kostet: ein Test mit konstruiertem Eingang
Ruling: Fix-Welle als eigene Commits C1–C6 auf a9708bec (kein Falten jetzt); ob gefaltet wird, entscheidet der User vor dem PR (wie bei PR 1) — kostet: a9708bec-Message behauptet Kommentare „qualified“, erst C5 macht es wahr
Ruling: Fix-Implementer Opus (mehrere Dateien, 6 Übersetzungen, Handrechnungen) — kostet mehr Token als Sonnet
Task 10b: BASE a9708bec, Implementer (Opus) dispatcht
Task 10b: implementer DONE_WITH_CONCERNS, 6 Commits 720b9e84..549d5e2e; 12/12 freigegebene Wortlaute per Skript wörtlich; Eigenbezug-Greps leer; Trailer 6× Opus; Bedenken: Mock-Store-Anpassung in test_a_source_change_empties_the_record_and_drops_the_notice (keine Assertion geändert), 2 Bundles statt 1 (irrigation-plus.js bettet en.json auch ein), sk 'vôbec'→'vôbec nie'
Task 10b: mutate-pr2b.py vorbereitet (make_mutate_b.py): M12/M20 neu verankert, M23–M33 neu (Schema-default, _merged <=, Gate-now, Hinweis/Log ohne cuts_field, Re-Sync ohne mappings, 2 Prozent-Klammern, 2 Rückfall-Zweige, cuts_field=True); MUT_CHECK 33/33 Anker genau einmal auf 549d5e2e
Task 10b: suite t10b: 7 failed / 3920 passed (+17 = neue Fälle inkl. Parametrisierung) / 9 skipped / 462 errors (+4 Teardown der neuen Koordinator-Tests); (1) 0, (2) FAILED gleich, (3) 32 Teardown-ERROR test_silent_sensor_commit.py, UNEXPECTED 0
Task 10b: Re-Review (Sonnet): alle Befunde 1–8g ADDRESSED, keine neue Critical/Important; Mock-Anpassung = getreues Double (Produktionspfad durch test_sensor_liveness_repair.py::test_the_notice_goes_when_its_sensor_is_replaced gedeckt); 6 Übersetzungen per Skript geprüft (keep-Label, Name der Einstellung, Platzhalter, Anführungszeichen)
Task 10b: minor (Re-Review): `if outage.end is None` in _stale_issue_key (sensor_liveness.py:608) ungepinnt
Ruling: diesen einen Pin noch ergänzen (ein Test, Sonnet) statt parken — der Maintainer fährt eigene Mutationen, und ein überlebender Mutant verdächtigt den Test (Memory) — kostet einen kleinen Dispatch außerhalb der „einen Fix-Welle“
Task 10b: out-of-scope (deferred): weather_aggregate.py:525 wiederholt die delta-Ausnahme inline (Import-Richtung); live_estimate.py:596 „agree by construction“ ohne Zusatz (durch erste Zeile + letzten Absatz gedeckt)
Task 10b: Pin 030e12a3 „test: a closed outage does not decide the paused notice“ (Sonnet): grün 49 passed, unter Mutation (Zeile 608 entfernt) rot `'weather_sensor_stale_paused' == 'weather_sensor_stale'`, Datei per cmp zurück
Task 10b: M34 (Filter `if outage.end is None` entfernt) in mutate-pr2b.py, 34/34 Anker; Frontend auf 030e12a3: vitest 661 passed, Build lässt dist unverändert, git status leer, tsc ohne Ausgabe
Task 10b: Suite t10c + Mutationen 1–34 laufen (nacheinander, Hintergrund)
Task 10b: suite t10c (HEAD 030e12a3): 7 failed / 3921 passed (+1 Pin) / 9 skipped / 462 errors; (1) 0, (2) FAILED gleich, (3) 32 Teardown, UNEXPECTED 0
Task 10b: Mutationen 34 killed / 34 applied / 34 total, expected killer 34/34, sha256 restore True, git diff --quiet HEAD True (mutate-pr2b.txt, mutations-pr2b.json)
Task 10b: Lint auf 030e12a3: black 70+6 unverändert, ruff 0.16.10 Paket „All checks passed!“, ruff 0.17.0 geänderte .py „All checks passed!“; Eigenbezüge Diff 0 / Messages 0; 16 Commits, 0 behind
Task 10b: complete (commits a9708bec..030e12a3, re-review clean, 1 Pin nachgezogen)
Task 10: complete (Steps 1–6 auf a9708bec, Fix-Welle 10b auf 030e12a3)
