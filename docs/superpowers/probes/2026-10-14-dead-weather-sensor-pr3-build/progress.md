# SDD ledger — plan: D:/Entwicklung/HASI/HAsmartirrigation/docs/superpowers/plans/2026-10-14-dead-weather-sensor-pr3.md

Spec: docs/superpowers/specs/2026-10-14-dead-weather-sensor-pr3-design.md (freigegeben 2026-10-14), dazu PR-2-Spec und Rev. 3.
Worktree: D:/Entwicklung/HASI/issue8-pr3-work/wt, Branch feat/pause-silent-sensor-hourly-live (no tracking, NICHT pushen vor Task 12), Basis 6fa424e8.
Session 2026-10-14 (Nachmittag), Controller Opus 5.5.

## Task 0

- Step 1 (13:59 UTC): origin/feat/pause-silent-weather-sensor = 6fa424e8; JustChr#197 OPEN, mergedAt null, 18 Commits, 1 Kommentar (unser CI-Hinweis), 0 Reviews, keine Checks; upstream/master 6a40e083. Upstream-Runde ab 13:56 UTC leer (Issues/PRs, Issue-Kommentare, Review-Kommentare, Releases; neuestes Release v2026.10.05).
- Step 2: Worktree angelegt, HEAD 6fa424e8, `_local_socket_unblock.py` kopiert.
- Step 3: Baseline `../suite-base-wt.txt`: 7 failed, 3925 passed, 9 skipped, 466 errors (7:33 min); `names-base-wt.txt` 473 Namen, identisch mit der Probe-Baseline `names-baseline.txt` (diff leer).
- Step 4: task_compare.sh per Write-Tool (Backslash-Falle), Bytes geprüft (einzelne Backslashes, kein CR).

## Rulings (Setup)

- Ruling: Workspace in `issue8-pr3-work/sdd/` statt `<repo>/.superpowers/sdd/` — wie PR 2, User-Regel „Agenten-Ablagen unter …-work“ — kostet nichts.
- Ruling: Spec-Check = `sdd/spec_check.py N BASE HEAD`: Task-Diff je Datei gleich dem Diff des Probe-Commits P[N-1]..P[N] (Kette d4817574 9233cf6b 71276b0d 27e7b551 3333f841 c7677cf1 b36bc93d 76de3372 8bd004a9; Range-Diff 6fa424e8..8bd004a9 == probe-2026-10-14.patch, cmp gleich), erster Subject = Plan-Message, Trailer Opus 5.5, keine Eigenbezüge. Selbsttest gegen die Kette: Inhalt+Baum je Task gleich, nur Subject/Trailer der Probe-Commits weichen ab — wenn falsch: ein Review-Fix verschiebt spätere Probe-Zeilen → FAIL, dann von Hand interdiff.
- Ruling: Plan (15:56) ist nach dem letzten Probe-Stand (Commits 14:58–14:59) erzeugt → Blöcke = finale Kette; kein Abgleich Block↔Patch vorab, der Spec-Check fängt jede Abweichung — kostet: Abweichung erst nach dem Implementer sichtbar.
- Ruling: Je Task prüft der Implementer mit `task_compare.sh` (Plan-Step „Prüfen“, User-Vorgabe); der Controller liest dessen Ergebnisdateien und fährt die volle Suite mit Namensvergleich (`sdd/suite_compare.sh`) nach Task 5 (Ende Teil A), in Task 10 und sofort bei jedem Task, dessen Baum von der Probe abweicht — Abweichung von PR 2 (dort volle Suite je Task) — Grund: Bäume = Probe, deren volle Suite gemessen ist; spart ~7 min je Task — kostet, wenn falsch: Regression in einer fremden Testdatei erst nach T5/T10 sichtbar (Fix-Runde später).
- Ruling: Implementer Sonnet (User), Task-Reviewer Sonnet (lesen, Memory agent-model-tiering), Abschluss-Review Opus (Plan).
- Ruling: Soll-Endstand volle Suite = 7/3989/9/487 (Plan-Kopf, `plan-suite.md`, `suite-final-probe.txt` 14:30, User-Auftrag); Task 10 Step 2 nennt noch 3987/486 und „silent_sensor.py (7)“ — das ist `suite-probe.txt` 13:51 vor den Test-Verschärfungen nach dem ersten Mutationslauf, Plantext veraltet — kostet nichts (Messung entscheidet).
- Ruling: Plan-Rahmen „Quell- und Testdateien liegen im Worktree mit LF“ stimmt nicht: Arbeitskopie CRLF, Index LF (`git ls-files --eol`), genau wie im Probe-Worktree — keine Folge, Header-Regel 8 wie PR 2.
- Ruling: Englischer Doku-Wortlaut der Blöcke T5/T7 deckt sich Satz für Satz mit dem freigegebenen deutschen (geprüft am Probe-Diff) → wörtlich übernehmen, dem User im Chat gezeigt (Memory language-german: „dann englisch zeigen“) — kostet, wenn er anders will: ein Doku-Fix-Commit.
- Ruling: Header-Regel 7 verbietet `git checkout <sha> -- …`; das plan-diktierte `git checkout -- <2 Bundles>` (T5 Step 6, ohne SHA, verwirft nur Zeilenende) ist ausdrücklich erlaubt (notes/t5.md).

## Konflikt-Scan (vor Task 1)

Geprüft gegen den Probelauf (Tasks 1–9 in Reihenfolge, RED je Task mechanisch gemessen `red-check.txt`, GREEN laut Plan), die Dateilisten der Probe-Commits und die Files-Abschnitte des Plans.

| Paar / Task | geteilte Datei / Schnittstelle | Erzeugt → verbraucht | Befund |
|---|---|---|---|
| T1 ↔ T4 ↔ T5 | calculation.py | T1 Importe + Hülle `_blocked_spans_for_zone` (Gate bleibt) → T4 `required_sensor_fields`, Sperren an Stundenzeilen/Teilschritte → T5 Gate fällt | Reihenfolge erfüllt „Einheit“ (Gate erst nach T4); Probe grün |
| T1 ↔ T5 ↔ T9 | sensor_liveness.py | T1 `zone_blocked_spans` → T5 Hinweis/Log ohne Stundenbedingung → T9 Neuberechnung | Probe grün |
| T1 → T6 | `zone_blocked_spans(store, zone, start, end)` | T1 → Live-Schätzung | Probe grün |
| T2 ↔ T3 ↔ T5 ↔ T6 | weather_aggregate.py | T2 `HOURLY_ROW_REQUIRED` öffentlich + maskierte Tabelle → T3 `build_substeps(blocked=)` → T5/T6 Docstring `aggregate_window` | Probe grün |
| T2 → T4/T6 | `hourly_eto_priced(…, blocked=)`, `build_hourly_rows(blocked=)` | T2 → Commit (T4), Live (T6) | Probe grün |
| T3 → T4/T6 | `build_substeps(…, blocked=)` | T3 → Commit, Live | Probe grün |
| T4 → T6/T7 | `required_sensor_fields(module, *, hourly)` | T4 → Live-Anteil/Spiegel | Probe grün |
| T4 ↔ T5 | tests/test_silent_sensor_hourly_commit.py (T4 legt an, T5 läuft sie mit) | — | Probe grün |
| T5 ↔ T7 | docs/configuration-sensor-groups.md | T5 Zeile 59 + Absatz 62 → T7 Live-Satz in 62 | Probe-Diff = freigegebener Wortlaut |
| T5 ↔ T9 | tests/test_sensor_liveness_coordinator.py | T5 dreht 2 Tests um → T9 neue Klasse | Probe grün |
| T6 ↔ T7 ↔ T8 | live_estimate.py | T6 Sperren an alle Leser, Übertrags-Schlüssel → T7 Spiegel × Anteil → T8 Hochrechnung | Probe grün |
| T7 ↔ T8 | tests/test_live_estimate_silent_sensor_daily.py | T7 legt an (2 Klassen) → T8 Klasse Projection | Probe grün |

| Task | Selbstkonsistenz (Tests ↔ Code, Files ↔ spätere Nutzung) |
|---|---|
| T0 | Werkzeuge task_compare.sh (Write-Tool), Baseline auf 6fa424e8 — konsistent |
| T1 | Files = Probe-Commit (3); RED ImportError gemessen, GREEN 25 |
| T2 | Files = Probe (3); RED ImportError, GREEN 17; Umbenennung im Diff enthalten |
| T3 | Files = Probe (2); RED 9 failed TypeError, GREEN 9 |
| T4 | Files = Probe (2); RED ImportError, GREEN 10 + 8 Teardown |
| T5 | Files = Probe (18 inkl. 8 json + 2 dist); RED 4 failed (-k), GREEN 4 + 2 Teardown; `git diff --cached` = 18 im Plan |
| T6 | Files = Probe (4); RED 7 failed 1 passed, GREEN 8 |
| T7 | Files = Probe (3); RED 2 failed 1 passed, GREEN 3 |
| T8 | Files = Probe (2); RED 2 failed (-k Projection), GREEN 5 |
| T9 | Files = Probe (2); RED 4 failed 2 passed (-k), GREEN 6 |
| T10 | Erwartungszahlen veraltet → Ruling oben (3989/487) |
| Rubrik | kein plan-diktierter Rubrik-Defekt gefunden (Tests asserten Werte; keine wörtliche Logik-Dopplung bekannt) |

## Tasks
Task 1: BASE 6fa424e8, Implementer a4185bd49fff715fe (Sonnet), Commit d72c05d1; spec_check PASS (Baum = Probe T1); task_compare t1: 0 fehlend, 0 neue FAILED/ERROR, 62 passed 36 errors (= Baseline-Namen).
Task 1: review (Sonnet afc671e617d6606ff): Spec ✅, Approved, 0 C / 0 I / 4 M. ⚠️ live_estimate-Docstring + sensor_liveness-Moduldocstring: am Probe-Ende (8bd004a9) nachgezogen (live_estimate:629, sensor_liveness:12-14) → erledigt.
Task 1: minor (deferred): Offset-Test `test_sensor_liveness_blocked.py:202-210` läuft ohne `hass` in UTC (as_local = Identität), nur `end` aware.
Task 1: minor (deferred): Docstring `cuts_field` (`sensor_liveness.py` ~190-193) nennt noch „The commit's gate (calculation._blocked_spans_for_zone) … asks here“ — fragt seit T1 über `zone_blocked_spans`; am Probe-Ende unverändert.
Task 1: minor (deferred): `test_sensor_liveness_blocked.py:165-169` `is not None` statt erwarteter Spannen.
Task 1: minor (deferred): `test_sensor_liveness_blocked.py:179-185` „kein Anfang“ nur mit `None`, nicht mit unlesbarem String.
Task 1: complete (commits 6fa424e8..d72c05d1, review clean)
Task 2: BASE d72c05d1, Implementer ab0341aba3bd48a51 (Sonnet), Commit 0d976997; spec_check PASS (Baum = Probe T2); task_compare t2: 0 fehlend, 0 neu, 177 passed 15 errors (= Baseline-Namen). Notiz t2 nannte die Umbenennung fälschlich auch in et_estimate.py (stand nur in weather_aggregate.py) — Controller-Fehler, folgenlos.
Task 2: review (Sonnet a56aa3461bdf05a74): Spec ✅, Approved, 0 C / 0 I / 6 M. ⚠️ (calculation/live reichen `blocked` noch nicht; `build_substeps` → `_precip_increments` ohne `spans`; `mask` unbenutzt) am Probe-Ende geprüft: weather_aggregate:1465-1468 spans, :1541 mask, calculation:446-1030 und live_estimate:619-1023 blocked= → erledigt durch T3/T4/T6.
Task 2: minor M1 (plan-vorgegeben, Spec G5): Randprobe `t <= start` bleibt in `solar_samples`, auch wenn das Fenster in einer Sperre beginnt — Ruling: Code bleibt — die Randprobe ist der „Wert von davor“ (F2) und nach der Sperre die „Quote von davor“ (G5); innerhalb der Sperre hat die Stunde keine gebuchte Zeit (leere Zeile, `_ratio_hold_solar` überspringt sie); Plan-Review-Focus „Fenster beginnt in einer Sperre“ will genau das — kostet, wenn falsch: die erste Stunde eines solchen Fensters nimmt ihre Quote vom eingefrorenen Randwert, eine andere Quelle gibt es im Fenster nicht.
Task 2: minor (deferred): `sorted(required_spans)` (`weather_aggregate.py:1258`) tragend, keine Mutation/Test mit umgekehrter oder überlappender Feldreihenfolge.
Task 2: minor (deferred): Regenzuweisung in buchungsloser Stunde (`:1316-1317`) ungetestet (gesperrtes Pflichtfeld + Regenfeld).
Task 2: minor (deferred): Aufbewahrungsregel `t <= start or not _blocked_at(…)` viermal (`:632`, `:822`, `:909`, `:1236`); Helfer denkbar.
Task 2: minor (deferred): `_precip_increments(spans=…)` ohne `start`/`end` → TypeError (kein heutiger Aufrufer).
Task 2: minor (deferred): kleine Testlücken (Fenster nicht auf voller Stunde mit `booked`, `tz` auf leerer Zeile, `len(kept) < 2` bei Regenrate, `mask=`).
Task 2: complete (commits d72c05d1..0d976997, review clean)
Task 3: BASE 0d976997, Implementer af7e6426d9e801044 (Sonnet), Commit 74d7192a; spec_check PASS (Baum = Probe T3); task_compare t3: 0 fehlend, 0 neu, 213 passed 168 errors (= Baseline-Namen).
Task 3: review (Sonnet a81975d7453ecaa95): Spec ✅, Approved, 0 C / 0 I / 7 M. ⚠️ Aufrufer reichen `blocked`/`required` noch nicht; `required` muss der Form entsprechen → am Probe-Ende geprüft: calculation:1299 `required = required_sensor_fields(…)` → `_substeps_for_zone(…, blocked=, required=)` :1418-1425; live_estimate:1662-1680 `required=required_sensor_fields(…, hourly=buffer_et is not None)` → erledigt durch T4/T6. ⚠️ `_precip_increments` < 2 Proben → None = Einmal-Buchung wie Aggregat: zur Kenntnis, ins Abschluss-Review.
Task 3: minor (deferred): Zweig „Maske aktiv, nur Nacht gültig → Gewicht = gemessene Zeit“ (`weather_aggregate.py:1562`) ungepinnt (Test 6 prüft nur Summe).
Task 3: minor (deferred): Sonnenproben nur durch eigene Sperren verworfen (`:1536-1542`) ungepinnt; Spanende in Tests auf Sonnenraster.
Task 3: minor (deferred): Test 4 (`test_substeps_blocked.py:111-129`) prüft nur Gewicht 0 des stummen Schritts; Test 7 doppelt Assertion von Test 1.
Task 3: minor (deferred): `_weights_from_hourly_et` Parameter heißt `dt_hours`, bekommt gemessene Stunden (`:1354`).
Task 3: minor (deferred): Default `required=()` (`:1397`) macht vergessenes `required` bei gesetztem `blocked` unsichtbar.
Task 3: minor (deferred): `_valid_segments`-Docstring „merged spans“, `build_substeps` gibt nur sortierte (funktioniert laut Reviewer).
Task 3: minor (deferred): Rückfallstufe `weights = list(measured)` nur bei 0-ET-Fenstern, von keinem Test unterscheidbar erreicht.
Task 3: complete (commits 0d976997..74d7192a, review clean)
Task 4: BASE 74d7192a, Implementer aa144e25035b299c4 (Sonnet), Commit 1160abc5; spec_check PASS (Baum = Probe T4); task_compare t4: 0 fehlend, 0 neue FAILED, 8 neue ERROR test_silent_sensor_hourly_commit.py (classify: UNEXPECTED 0), 274 passed 235 errors.
Task 4: review (Sonnet a771015768f967470): Spec ✅, Approved, 0 C / 0 I / 4 M. ⚠️ Gate-Docstring `_blocked_spans_for_zone` „Only in the daily form for now“ → in Probe T5 (3333f841, calculation:431-441) ersetzt → in T5 prüfen (Spec-Check). ⚠️ Volle Suite → Controller nach T5 (Ruling Setup).
Task 4: minor M1 (vom Reviewer „plan-mandated“): Verdrahtung `required=required or ()` in den Replay (calculation.py ~1100/~1428) ungepinnt; Mutation `required=()` laut Reviewer grün (unbestätigt: nicht gelaufen); auch nicht unter den 37 Mutationen (14 deckt nur `blocked=`) — Ruling: kein Fix-Loop (Minor, wirkt nur auf die Lage der ET, Summe gleich; sichtbar nur bei Eimer-Kappung), aber Pin-Kandidat fürs Abschluss-Review zusammen mit den Live-`required` (live_estimate ~1662-1680) — kostet, wenn falsch: eine falsch verdrahtete Pflichtmenge fiele erst im Feld auf.
Task 4: minor (deferred): `test_dewpoint_does_not` prüft „wie bisher“ mit `pytest.approx` statt `==` (Global Constraint nennt `==`; plan-diktiert).
Task 4: minor (deferred): Rückfall „Pflichtfeld nie gelesen“ → Tagesform auf Commit-Ebene nicht eigens getestet.
Task 4: minor (deferred): Docstring `required_sensor_fields` verweist mit „fields above“ auf einen Kommentar statt `_REQUIRED_SENSOR_FIELDS` (plan-diktiert).
Task 4: complete (commits 74d7192a..1160abc5, review clean)
Task 5: BASE 1160abc5, Implementer a8189ffba4fba6f9f (Sonnet), Commit 60ac780b; spec_check PASS (Baum = Probe T5, inkl. 2 Bundles byte-gleich), 18 Dateien; task_compare t5: entfallen genau die 2 umbenannten, 0 neue FAILED, neue ERROR 2 + 8 (classify UNEXPECTED 0), 204 passed 44 errors. strip_help.py == Plan-Block (cmp).
Task 5: review (Sonnet ab75b4a0dc1c7676a, Paket ohne Bundle-Diffs): Spec ✅, Approved, 0 C / 0 I / 3 M. ⚠️ Vorwärtsverweise (sensor_liveness:13-14, calculation:435-436) und Interims-Satz Doku:62 → am Probe-Ende wahr bzw. ersetzt (live_estimate:629 + zone_blocked_spans-Aufrufe :1481/:2013; Doku-Diff 6fa424e8..8bd004a9) → erledigt durch T6/T7, im Spec-Check von T6/T7 erneut.
Task 5: minor M1 (plan-mandated): umgedrehter Test `test_silent_sensor_commit.py:467` steht in Klasse `TestAGroupThatIsNotCutCalculatesAsBefore` (:437), deren Name jetzt das Gegenteil sagt — Ruling: bleibt im Bau (Plan/Probe/Mutations-Killer gleich), Kandidat fürs Abschluss-Review (Umbenennen ändert Testnamen gegen den Namensvergleich) — kostet: ein irreführender Klassenname im PR.
Task 5: minor (deferred): kein Test fährt die echte Stundenform über `async_calculate_zone` ohne Gate (T4-Tests direkt `calculate_module(blocked=…)`, T5-Test über Tagesform-Rückfall).
Task 5: minor M3 (plan-mandated): `_group_cuts` (`sensor_liveness.py:618-626`) ist jetzt Einzeiler `group_pauses(mapping)` ohne `self` — Ruling: bleibt (plan-diktiert, harmlos) — kostet nichts.
Task 5: complete (commits 1160abc5..60ac780b, review clean)
Upstream-Runde 15:02 UTC (Fenster ab 13:56): leer; #197 0 Reviews; master 6a40e083; letzter Workflow-Lauf weiter 2026-10-08 05:41.
Volle Suite nach T5 (60ac780b, sdd/compare-t5.txt): 7 failed, 3970 passed, 9 skipped, 474 errors; +45 passed = 9+17+9+10; entfallen nur die 2 umbenannten; FAILED gleich; neu 2 + 8 ERROR, classify UNEXPECTED 0; Lingering timer 932 → 948.
Task 6: BASE 60ac780b, Implementer afd30b3dcc29926c9 (Sonnet), Commit f1b9a87d, DONE_WITH_CONCERNS (Docstring `_daily_mirror_et` ~1168 „silent time aside“ jetzt falsch) → in Probe T7 b36bc93d und am Probe-Ende 0 Treffer, T7 ändert die Methode → erledigt durch T7 (im T7-Spec-Check). spec_check PASS (Baum = Probe T6); task_compare t6: entfallen nur die 2 umbenannten, 0 neue FAILED (1 failed = Baseline next_irrigation aiodns), neue ERROR 8 + 2 + 8 (classify UNEXPECTED 0), 342 passed 264 errors.
Task 6: review (Sonnet aec1698d9c6771ef0): Spec ✅, Approved, 0 C / 0 I / 5 M. ⚠️ `_carry_estimate_to` ungeschnitten → T8 (Mutation 37); Spiegel ohne Anteil/0-Regel → T7 (Mutationen 34, 35); Docstring → T7. ⚠️ `_observed_precip_since_mm` bekommt bei *behalten* `now_local` statt Uhr-Rückfall — Ruling: bleibt — Spec §3.1 verlangt Live-`now` für den Niederschlag, Unterschied Sekunden — kostet, wenn falsch: keine Byte-Gleichheit der Regenspur bei *behalten* im Sekundenbereich.
Task 6: minor M1 (deferred, Pin-Kandidat): Durchreichungen ungepinnt — `blocked`/`required` an `_buffer_water_steps` (:1641-1665; Regenraten-Test prüft `balance_form` nicht), zwei der drei Regen-Aufrufstellen (:1542, :1599), Kette Spiegel → `_composed_day_et` → `_projected_extremes` → `_latest_temperature`. Mutationen 30/31/36 decken nur Stundenquelle/Aggregat/Regen der Stundenquelle. Zusammen mit Task 4 M1 ins Abschluss-Review.
Task 6: minor (deferred): kein Test, dass ein stabiler offener Ausfall den Übertrag wiederverwendet (Schlüssel aus zugeschnittenen Spans würde jede Minute verwerfen; Korrektheit gleich, nur Cache).
Task 6: minor (deferred): `test_an_open_outage_cuts_up_to_now` (:907-915) ohne Vergleich mit ungeschnittenem Lauf.
Task 6: minor (deferred): kein Live-Pfad-Test mit Offset-Stempeln (T1-Test deckt `zone_blocked_spans`; nach `coerce_stamp` unbedenklich).
Task 6: minor (deferred, plan-diktiert): Modulname verschachtelt im Keyword-Argument gebaut (:1655-1662).
Task 6: complete (commits 60ac780b..f1b9a87d, review clean)
Task 7: BASE f1b9a87d, Implementer a50ccd3a17847c9d1 (Sonnet), Commit 2c374da9; spec_check PASS (Baum = Probe T7); „silent time aside“ 0 Treffer; task_compare t7: entfallen nur die 2 umbenannten, 0 neue FAILED, neue ERROR 8+3+2+8 (classify UNEXPECTED 0), 345 passed 267 errors.
Task 7: review (Sonnet ad17445199ab29331): Spec ✅ (Plantext 1:1), Needs fixes: 0 C / 1 I / 3 M.
Task 7: Ruling: Important 1 (plan-diktierter Code: Anteil-0-Abkürzung in `_daily_mirror_et` sitzt hinter `_mirror_blend`/`_commit_forecast`; bei `forecast_days > 0` ohne spiegelbare Prognose kommt `None`, die Kette fällt zum Wetterdienst, obwohl der Commit 0 bucht — am Code bestätigt: calculation.py:1311-1316 fragt die Gleichung bei share 0 nicht, live_estimate.py:876-880/:1193-1203) → FIX — Spec G9 „bei Anteil 0 → 0 statt `None`“ und §3.5 Gleichlauf binden, der Plan deckt den Unterfall nicht; Anteil nach `_daily_form_applies`, vor der Prognose; Teilanteil mit fehlender Prognose bleibt heutiger Weg — kostet: ein Commit über die Probe hinaus (Spec-Check ab hier per Datei-Diff, Baum ≠ Probe), Mutationsanker 35 muss weiter genau einmal passen; wenn falsch: nichts außer einem Commit.
Task 7: fix round 1/5 (1 addressed, 0 open — Anteil vor Prognose in `_daily_mirror_et`; commits 2c374da9..08728aa7). Fix-Brief sdd/task-7-fix1-brief.md; RED `assert 'hourly' == 'daily_mirror'`, GREEN 4 passed; Anker 34/35 je 1; task_compare t7f1: +1 passed, +1 Teardown-ERROR, nichts entfallen. Re-Review (Sonnet a8e80d60d96b17297): ADDRESSED, neue Brüche 0 C / 0 I / 2 M.
Task 7: minor (deferred): Kommentar am Fix (und Commit-Message 08728aa7, Controller-Wortlaut) sagt, der Commit frage bei Anteil 0 „weder Gleichung noch Prognose“ — er holt die Prognose für PyETO mit forecast_days > 0 vorher (calculation.py:570-583), nutzt sie nur nicht → Kommentar im Abschluss-Fix berichtigen.
Task 7: minor (deferred): Reihenfolge `_daily_form_applies` vor Anteil ungepinnt (Anteil 0 + Stundenform-Zone).
Task 7: minor (deferred): Tagesmenge nur über Temperatur (+) und Feuchte (−) gepinnt; Taupunkt/Wind/Druck in keinem Test (Mutation `fields=(T,)` überlebt laut Reviewer, unbestätigt).
Task 7: minor (deferred): Modulnamen-Auflösung zweimal (live_estimate ~1198 und ~1676); Zweig `fields is not None` für den Spiegel unerreichbar.
Task 7: minor (deferred): Docstring-Satz „With none, nothing is booked“ (~1180-1184) ohne klaren Bezug.
Task 7: ⚠️ Stundenschalter an + geschätzte Strahlung (Spiegel + gespielte Bilanz) mit Ausfall ohne eigenen Test → ins Abschluss-Review.
Task 7: complete (commits f1b9a87d..08728aa7, 1 fix round, review clean)
Umgebung 2026-10-14 ~18:00 lokal: C: 0 Byte frei (df). User-Rüge „wieder auf C:“ → TEMP/TMP/TMPDIR in task_compare.sh, suite_compare.sh, header.md (Briefs 8/9 neu gebaut) auf issue8-pr3-work/tmp; Beleg tempfile.gettempdir() = D:\…\tmp. Memory temp-files-on-drive-d ergänzt.
Lint: UV_CACHE_DIR=issue8-pr3-work/uv-cache (C: wieder 0 frei, uvx os error 112 beim T8-Implementer); belegt: black 26.10.1 / ruff 0.16.10 laufen, Baum sauber. header.md Regel 4 ergänzt, Brief 9 neu.
Task 8: BASE 08728aa7, Implementer a3e7fec5d5e67eb3e (Sonnet), Commit ca0955f8; spec_check PASS (Datei-Diffs gleich Probe T8; Baum ≠ Probe nur um die T7-Fix-Runde, +28/−2); RED `-k Projection` 2 failed (1.6405 < 1.6405; 0 == 1), GREEN 6 passed; task_compare t8: entfallen nur die 2 umbenannten, 0 neue FAILED, neue ERROR 8+6+2+8, 348 passed 270 errors.
Task 8: review (Sonnet a06b81f98fd2ffbe0): Spec ✅, Approved, 0 C / 0 I / 3 M.
Task 8: minor M1 (plan-mandated, Pin-Kandidat): `blocked=blocked` an `_composed_day_et` in der Hochrechnung (live_estimate ~2042) von keinem Test bemerkt (Test 1 nutzt Stundenprognose, Stufe `service`; `_latest_temperature`-Zweig läuft nie); Mutation 37 deckt nur das Aggregat — Ruling: kein Fix-Loop (Minor), mit T4 M1 / T6 M1 ins Abschluss-Review als Pin-Paket — kostet, wenn falsch: Hochrechnung ohne Wetterdienst ankert am eingefrorenen Wert, bis ein Feldfall es zeigt.
Task 8: minor (deferred): `paused < kept` (Testdatei ~184) nur Richtung; Halboffen-Grenze am Ende, ganztägig gesperrte Temperatur, `==` für *behalten*, `own_equation=False` ungeprüft.
Task 8: minor (deferred, plantreu): Docstring `_frozen_zone` (~152) ungenau (stumm ab +4 h, Sperre ab +7 h).
Task 8: ⚠️ zur Kenntnis: `_projected_radiation` (~1140) skaliert den geschnittenen Mittelwert mit der ganzen verstrichenen Zeit (G10 verlangt nichts anderes) → Abschluss-Review.
Task 8: complete (commits 08728aa7..ca0955f8, review clean)
Task 9: BASE ca0955f8, Implementer a3bec3d47f55b3b16 (Sonnet), Commit e5d184e3; spec_check PASS (Baum = Probe-Ende 8bd004a9 bis auf die T7-Fix-Runde, +28/−2); RED 4 failed 2 passed, GREEN 6 passed; task_compare t9: entfallen nur die 2 umbenannten, 0 neue FAILED, classify UNEXPECTED 0, 507 passed 270 errors.
Task 9: review (Sonnet a1881087160628c42): Spec ✅, Needs fixes: 0 C / 1 I / 5 M.
Task 9: Ruling: Important (plan-mandated Testlücke: „ungedrosselt“ `sensor_liveness.py:530` von keinem Test gehalten; `_throttled` ruft am `__new__`-Koordinator durch zum Mock) → FIX nur im Test (eigenes Double für `_throttled` + `assert_not_awaited`, RED per Probe-Mutation, zurückgenommen) — die Abweichung ist eine User-Entscheidung, die ein Test halten muss — kostet: ein Test-Commit über die Probe hinaus.
Task 9: ⚠️ Spec §3.4 (:195-196) und G11-Zeile (:41) nennen noch `_throttled` — Ruling: Spec bleibt unverändert, die freigegebene Abweichung steht in der Selbstprüfung des Plans; im Bauprotokoll (Task 10 Step 5) vermerken — kostet: ein Leser der Spec allein sieht die Abweichung nicht.
Task 9: minor (deferred): `:603` fragt `group_pauses` statt `_group_cuts`; Ausfall nur eines ungeschnittenen Felds (Regenzähler) frischt trotzdem auf (harmlos).
Task 9: minor (deferred): Wächter `if refresh is None` (`:531-532`) unerreicht.
Task 9: minor (deferred): `test_a_refresh_that_fails…` ohne `assert_awaited_once()` — wäre leer, wenn nie aufgefrischt würde (Kandidat fürs Abschluss-Fix-Paket).
Task 9: minor (deferred): wirft nach dem Store-Schreiben etwas in der Gruppe (`_fire_weather_stale`, `_sync_stale_issue`), geht das Auffrisch-Flag verloren.
Task 9: minor (deferred): bestehende `_pausing`-Tests (`:1004-1100`) rufen über `_coord` jetzt die echte `async_refresh_zone_estimates` gegen Mock-`hass` (verschluckter DEBUG-Pfad); Standard-`AsyncMock` in `_coord` würde das abschirmen.
Task 9: fix round 1/5 (1 addressed, 0 open — Double für `_throttled` + assert_not_awaited; commits e5d184e3..e62b046f). RED unter Probe-Mutation 4 failed, zurückgenommen (`restored`), GREEN 6 passed, task_compare t9f1 = t9. Re-Review (Sonnet a737f52854a5bc804): ADDRESSED, neue Brüche 0; 2 Nits: Double ohne Kommentar; `test_a_group_that_keeps_does_not` prüft nur das ungedrosselte Double.
Task 9: complete (commits ca0955f8..e62b046f, 1 fix round, review clean)
Task 10 Step 1: black/ruff@0.16.10 sauber (UV_CACHE_DIR D:), drei Eigenbezug-Greps leer, 11 Commits 6fa424e8..e62b046f.
Task 10 Step 2 (sdd/compare-t10.txt): 7 failed, 3990 passed, 9 skipped, 488 errors = Probe-Ende 3989/487 + 1 Test der T7-Fix-Runde (+1 Teardown); gegen names-final-probe nur dieser Name neu, keiner fehlt; FAILED gleich; UNEXPECTED 0; Lingering 932 → 976.
Task 10 Step 3: Anker-Check 37/37 je genau einmal (mutate-wt-check.txt); Lauf gestartet (mutate-wt.txt).
Upstream-Runde 16:47 UTC (Fenster ab 15:00): leer; #197 offen, Kopf 6fa424e8, 0 Reviews; master 6a40e083; kein neues Release, letzter Workflow-Lauf 2026-10-08.
Final review (Opus a9db385745d89b877, sdd/final-review-report.md): „bereit mit Fixes“ — 0 C / 1 I / 13 M; Triage 55 Punkte: 6 must (alle über Tests A-Commit, A-Live, B, C), 15 cheap, 34 leave (7 davon am Kopf erledigt). Logik korrekt, Live = Commit, *behalten* byte-identisch, kein Store-Feld, Doku = Wortlaut, keine Eigenbezüge; 4 Abweichungen + 2 Fix-Runden halten.
Final review: Ruling: EINE Fix-Welle mit I1 (A-Commit, A-Live, B, C, D) + M1–M13 komplett (auch „cheap“; M11/M12 halten Spec-Vorgaben „Live-Mixin allein“ und G11) — Produktionslogik unverändert, nur Tests, Kommentare/Docstrings und Umbenennung `dt_hours` → `measured_hours` (kein Mutationsanker enthält `dt_hours`); jeder Pin mit RED unter Probe-Mutation; Implementer Sonnet; Brief sdd/final-fix-brief.md — kostet, wenn falsch: mehr Diff im PR (Kommentare/Tests), keine Verhaltensänderung.
Task 10 Step 3 (mutate-wt.txt, mutations-wt.json) auf e62b046f: 37 killed / 37 applied, jede vom erwarteten Killer (37/37), alle Quellen sha256-gleich zurück, git diff --quiet HEAD: True; unmutiert 167 passed 58 errors.
Final fix wave (Sonnet abe065ef8a6babfce, sdd/final-fix-report.md): DONE_WITH_CONCERNS, 14/14 Befunde erledigt; Commits 08fed661 (Pins I1 A–D), 1b0dfee0 (M5-Test, M7, M8, M9, M10, M11, M12 + nicht verlangter Zusatztest zweite `sorted`-Stelle in build_substeps), c21478c8 (Kommentare/Docstrings, M4 `measured_hours`). Jeder Pin rot unter seiner Mutation, zurückgenommen (restored + sha256). task_compare tfix: 0 neue FAILED, 544 passed. Controller: Lint sauber, Eigenbezug-Greps (inkl. I1/M-Kürzel) leer, Trailer 3/3, Anker 37/37; Prod-Diff nur Docstrings/Kommentare + Umbenennung.
Final fix wave: Bedenken des Implementers: (1) M5-Pin rot per KeyError statt Assertion; (2) Zusatztest hängt unter Mutation an Hash-Reihenfolge (~119/120 rot); (3) Zusätze ohne Verhaltenswirkung (lokale Namen, Test-Helfer-Kwargs) → an die Nach-Review gegeben.
Volle Suite nach Fix-Welle (sdd/compare-t10f.txt, c21478c8): 7 failed, 4001 passed, 9 skipped, 496 errors; +11 passed = neue Tests der Welle; FAILED gleich; UNEXPECTED 0; Lingering 976 → 992; gegen t10 nur neue Testnamen + M7-Umzug. Zweiter Mutationslauf auf c21478c8 gestartet (mutate-final-wt.txt).
Final fix wave: re-review (Sonnet af1d7b7df3d92adbd, sdd/rereview-finalfix-report.md): 18/18 ADDRESSED (I1 A–D, M1–M13), neue Brüche 0 C / 0 I / 4 M. Zusatztest `test_the_spans_of_several_fields_are_taken_in_time_order`: auf richtigem Code deterministisch grün (sorted über paarweise verschiedene Spannen), unter Mutation ~119/120 rot.
Final fix wave: parked — Zusatztest fängt die `sorted`-Mutation nur mit Wahrscheinlichkeit — Ruling: bleibt (nie Fehlalarm, M5 nennt beide `sorted`-Stellen; gespiegelte Zuordnung als zweiter Parameter wäre die deterministische Fassung) — kostet: ~0,8 % Fangverlust je Lauf.
Final fix wave: parked — M5-Pin der Stundenzeilen hängt an der Feldreihenfolge von `HOURLY_ROW_REQUIRED` (Temperatur vor Sonne) — Ruling: bleibt, real und nachrangig — kostet: bei umgestelltem Tupel verliert der Pin still seine Wirkung.
Final fix wave: parked — Testhelfer `_inside`/`_recording_substeps` doppelt (teils andere Signatur) — Ruling: bleibt, ohne Wirkung — kostet: Pflege an zwei Stellen.
Final fix wave: parked — vier pausierende `_mock_store_coord`-Tests (test_sensor_liveness_coordinator.py) rufen weiter die echte Auffrischung (M8 nannte nur `_coord`) — Ruling: bleibt, außerhalb des M8-Auftrags; die Prüfung schluckt den Fehler absichtlich (Task-9-Test) — kostet: verschluckte DEBUG-Ausnahme in vier Tests.
Task 10 Step 5 (User-Freigabe „Archiv pushen“, Upstream-Runde 18:04 UTC leer): archive/design-history add8be59..d8deb5f8 gepusht, remote = lokal; Plan abgehakt (65 Schritte) + probes/2026-10-14-dead-weather-sensor-pr3-build/ (55 Dateien, Scan auf IP/Schlüssel/Mail leer). Offen: Ergebnis des zweiten Mutationslaufs auf c21478c8 → nächster Archiv-Stand. Ruling: SDD-Workspace issue8-pr3-work/sdd bleibt bis Task 12 (Skripte für Rebase-Neubeleg) — kostet nichts, Kopie im Archiv.
Task 10 Step 3 Endstand (mutate-final-wt.txt, mutations-final-wt.json) auf c21478c8: 37 killed / 37 applied, erwarteter Killer 37/37, sha256 zurück, git diff --quiet HEAD True. Noch nicht im Archiv (nächster Stand, Freigabe).
