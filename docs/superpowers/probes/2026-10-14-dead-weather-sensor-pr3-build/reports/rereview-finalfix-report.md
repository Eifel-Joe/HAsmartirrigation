# Nach-Review der Abschluss-Fix-Welle `e62b046f..c21478c8`

Geprüft gegen `final-review-report.md` (I1: A-Commit, A-Live, B, C, D; M1-M13) und `final-fix-brief.md`. Gelesen: die Diff-Datei
`review-finalfix.diff` einmal ganz; Code und Tests nur aus Git-Objekten (`git show c21478c8:<pfad>`, `git grep c21478c8`); die Rohausgaben
unter `sdd\fix\` (RED/GREEN je Pin) und `final-fix-report.md`. Keine Tests gelaufen, nichts im Worktree verändert. Zeilenangaben beziehen
sich auf `c21478c8`, Pfade relativ zum Worktree.

## Ergebnis in Zahlen

- Verdikte: **18 von 18 ADDRESSED, 0 NOT ADDRESSED** (I1 = 5 Teil-Pins A-Commit, A-Live, B, C, D; dazu M1-M13).
- Neue Brüche im Fix-Diff: **Critical 0, Important 0, Minor 4** (siehe unten; keiner blockiert).
- Zusatztest (Punkt 2): auf dem richtigen Code deterministisch grün; behalten, optional mit einer gespiegelten Zuordnung deterministisch rot machen.

## Verdikte je Befund

### I1 — Verdrahtungs-Pins (Commit `08fed661`)

| Befund | Verdikt | Beleg |
|---|---|---|
| A-Commit | ADDRESSED | `tests/test_silent_sensor_hourly_commit.py:253` `test_the_daily_form_places_no_et_in_silent_time` (Helfer `_recording_substeps` :133, `_inside` :147). Aufbau wie verlangt: `solrad="1"`, Messwerte ohne Sonnenfeld, Stundenschalter an (Fixture), Spion um `calculation.build_substeps`. Feuchte gesperrt: Schritte `==` ungesperrt; Temperatur gesperrt: Gewicht 0 in `[10:00,12:00)`, Summe 1, „Number of steps:“ in der Erklärung. Alle drei vom Review genannten Mutationen belegt: `required=required or ()` -> `required=()` (`a-commit-red-required.txt`, `E assert False`); `weight = measured_hours` (weather_aggregate.py:1568) -> `dt_hours` (`a-commit-red-flat.txt`, gleiche Zusicherung); `hourly=hourly is not None` -> `is None` (`a-commit-red-hourly.txt`, `seen[-1] == plain_steps` im Feuchte-Zweig; das beweist zugleich, dass der Feuchte-Commit `build_substeps` wirklich aufruft, der Vergleich also nicht leer ist). |
| A-Live | ADDRESSED | `tests/test_live_estimate_silent_sensor.py:140` Klasse, `:154` `test_a_daily_mirror_zone_replays_its_measured_time[with_sun\|without_sun]`, `:188` `test_a_field_the_daily_form_does_without_places_its_et_as_before`. Fixture `coordinator` = `make_coordinator(hass)` mit `hourly_calculation=True` als Vorgabe (test_live_estimate_replayed_balance.py:131). Erwartet `method == "daily_mirror"`, `balance_form == "replayed"` (:177), Gewicht 0 in `BLOCKED = (T0+9h, T0+16h)` (ab `ANCHOR` gezählt, `ANCHOR = T0+2h`), Summe 1, `live_deficit ≈ round(Commit-Eimer, 2)`, zusätzlich Schritte `==` denen des Commits. RED: `required=() and required_sensor_fields(` beide Varianten rot (`alive-red-required.txt`); `hourly=buffer_et is None` nur der Feuchte-Test rot (`alive-red-hourly.txt`; der Temperatur-Test kann das nicht fangen, weil Temperatur in beiden Feldmengen steht, deshalb der zweite Test: sauber begründet); `blocked=None` am Aufruf `_buffer_water_steps` beide Varianten rot (`alive-b-red-blocked.txt`). Die Sonnenfeld-Variante ist ein Zusatz und schließt die Konfiguration „geschätzte Sonne, kein Sonnensensor“. |
| B | ADDRESSED | `tests/test_live_estimate_silent_sensor.py:234-235`: `uncut["balance_form"] == "replayed"` und `est["balance_form"] == "replayed"`. RED unter `blocked=None` am `_buffer_water_steps`-Aufruf: `AssertionError: assert 'lumped' == 'replayed'` (`alive-b-red-blocked.txt`). |
| C | ADDRESSED | `tests/test_live_estimate_silent_sensor_daily.py:195` `test_a_temperature_silent_now_anchors_no_remainder`; `_frozen_zone` :151 mit neuem Schlüsselwort `service_forecast=False` (ohne Stundenprognose-Stufe), gespeicherte `MAPPING_TEMPERATURE_AMPLITUDES`. *behalten*: `forecast_tier` und `projection_tier` je `self_contained`; offener Ausfall (`_silent(store, zone, 4)`): beide `observed`. Alle vier Glieder der Kette einzeln belegt: `_daily_mirror_et` (:1220) `c-red-1220.txt`; `_carry_estimate_to` (:2042) `c-red-2042.txt` (dort rot an `projection_tier`, `forecast_tier` bleibt richtig, also trennt der Test die beiden Aufrufer); `_composed_day_et` -> `_projected_extremes` (:1072) `c-red-1072.txt`; `_projected_extremes` -> `_latest_temperature` (:992) `c-red-992.txt`. |
| D | ADDRESSED | `tests/test_live_estimate_silent_sensor.py:238` `test_a_blocked_rain_rate_is_cut_on_every_source[hourly\|proxy]`; Passthrough-Zone, Regenrate, Niederschlags-Ausfall; `est["method"] == uncut["method"] == source`, `precip_since ≈` Niederschlag des geschnittenen Commit-Aggregats und `< uncut - 1.0`. RED je Pfad getrennt: `d-red-hourly.txt` (nur `[hourly]` rot, `5.0 == 1.0 ± 1e-3`), `d-red-proxy.txt` (nur `[proxy]` rot). Die dritte Stelle (Puffer-Quelle) bleibt durch die bestehende Mutation 36 gedeckt. |

Bemerkung zu A-Commit/A-Live: Der Review nennt unter „Betroffene Stellen“ auch `blocked=blocked` an `calculation.py:1424` (Aufruf von `_substeps_for_zone`). Dafür liegt keine eigene
RED-Probe vor; sie ist nicht verlangt (die „Fängt“-Liste des Reviews nennt sie nicht). Nach Lesen der Kette ist sie durch A-Commit gedeckt: ohne `blocked` ist die Maske leer,
`table is None`, Gewicht = `dt_hours`, und `all(steps[i].et_weight == 0.0 ...)` wird falsch. Kein Mangel, nur nicht belegt.

### Minor

| Befund | Verdikt | Beleg |
|---|---|---|
| M1 | ADDRESSED | `sensor_liveness.py:191` nennt `zone_blocked_spans`, „the one gate of the commit and the live estimate“. |
| M2 | ADDRESSED | `live_estimate.py:1182` „With no measured time, nothing is booked“; Kommentar :1197 „…whatever the forecast says, and the equation is not asked for it“. Die Aussage „Gleichung nicht gefragt“ stimmt: `calculation.py` überspringt `modinst.calculate` bei `share == 0` (Kommentar dort, Zeilen um 1315). Gleicher Fehler im Test-Docstring `test_live_estimate_silent_sensor_daily.py:124` mitberichtigt. Commit-Message `08728aa7` unberührt. |
| M3 | ADDRESSED | `weather_aggregate.py:1591`: „No measured time to place it in: spread it flat, as for a window without radiation, so the rain still replays.“ (Wortlaut des Reviews). |
| M4 | ADDRESSED | `weather_aggregate.py:1358` `_weights_from_hourly_et(weights, hours, measured_hours, hourly_et)`; einziger Aufrufer :1580 positional, kein Schlüsselwort-Aufrufer im Repo (`git grep dt_hours=` trifft nur `WaterStep(dt_hours=…)` in test_lumped_credit_drainage.py, ein anderes Feld). Lokale Namen `dt`/`hour_seconds` -> `measured`/`hour_measured`; Rechnung Zeichen für Zeichen gleich (`m for h, m in zip(hours, measured_hours, strict=True) if h == hour`, `fraction = measured / hour_measured if hour_measured > 0 else 0.0`). Kommentar „measured time WITHIN the hour“ :1384. Reine Umbenennung, kein Verhaltenswechsel. |
| M5 | ADDRESSED | Test `tests/test_hourly_rows_blocked.py:221` (Sonnen-Spanne 08-10, Temperatur-Spanne 12-14; `coverage_h == 0.0` genau in 8, 9, 12, 13, sonst 1.0). Docstring `weather_aggregate.py:666` „sorted (overlaps allowed)“. RED siehe Punkt 3. Zusatz `tests/test_substeps_blocked.py:104` siehe Punkt 2. Beide `sorted`-Stellen (:1262 und :1523) haben damit einen Test. |
| M6 | ADDRESSED | `calculation.py:88` nennt ``_REQUIRED_SENSOR_FIELDS``. |
| M7 | ADDRESSED | `tests/test_silent_sensor_commit.py:471` `TestTheHourlySwitchDoesNotDecide`; Testname unverändert; `_RESULT_FIELDS` :437 und `_results` :445 auf Modulebene, beide Klassen rufen sie (kein Rest von `self._results` oder `.FIELDS`, per Grep). |
| M8 | ADDRESSED | `tests/test_sensor_liveness_coordinator.py:224` `coord.async_refresh_zone_estimates = AsyncMock()` als Standard in `_coord`; `:1295` `assert_awaited_once()`. RED: `refresh = None` macht den Fehlschlag-Test und vier weitere Zähl-Tests rot (`m8-red.txt`). Vorher-Beleg `m8-before-real-refresh.txt`: die echte Auffrischung scheiterte still an `'_FakeStore' object has no attribute 'config'`. |
| M9 | ADDRESSED | `tests/test_silent_sensor_hourly_commit.py:229` `==` statt `approx`. Keine RED-Probe nötig (Verschärfung ohne Verdrahtung). |
| M10 | ADDRESSED | `tests/test_live_estimate_silent_sensor.py:114-128`: ungeschnittener Lauf (Live und Commit) vor `_silent`, dann `est["et_since"] < uncut["et_since"] - 0.1` (:127) und `data[BUCKET] > uncut_data[BUCKET] + 0.1` (:128). RED: `zone_blocked_spans` -> `return None`: `assert 6.03 < (6.03 - 0.1)` (`m10-red.txt`), die alte Live==Commit-Zusicherung blieb dabei grün, wie der Review vorhersagte. `_frozen_zone`-Docstring (`..._daily.py:151`): stumm ab +4 h, gesperrt ab +7 h. |
| M11 | ADDRESSED | `tests/test_live_estimate_from_buffer.py:340` `TestAPausingGroupWithTheMixinAlone` über `_Coord(LiveEstimateMixin)`; `_expected_et_mm` :202 mit optionalem `blocked=None`. RED 1 (unbedingter Querruf) trifft auch drei ältere Tests; RED 2 (Querruf nur im pausierenden Zweig, `m11-red-pausing-only.txt`): nur der neue Test rot, 27 grün. Das ist genau die Lücke, die der Review meint. |
| M12 | ADDRESSED | `tests/test_live_estimate_silent_sensor.py:326-353`: offener Ausfall, `LATE` und `LATE + 2 min`; Spion um `hourly_eto_priced`: Wasserzeichen `== carry.boundary` (23:00), `carry.outages` unverändert. RED: Schlüssel aus den zugeschnittenen Spannen -> Wasserzeichen 22.05. 00:00 statt 23:00 (`m12-red.txt`); die zwei älteren Carry-Tests bleiben grün, also trennt der Test genau die Cache-Eigenschaft. Die Spion-Variante statt „Eintrag bleibt in `_hourly_carry()`“ ist begründet (der Eintrag würde nach einem Verwerfen neu geschrieben). |
| M13 | ADDRESSED | `weather_aggregate.py:1049` „…has no air state to take a ratio against…“. |

## Neue Brüche im Fix-Diff

**Critical: keine. Important: keine.** Produktionscode: nur Docstrings/Kommentare und die M4-Umbenennung, jede Zeile im Diff gelesen; kein Ausdruck außerhalb davon geändert.

Minor (alle ohne Folge für Korrektheit, keiner blockiert den PR):

1. **M5-Pin der Stundenzeilen hängt an der Feldreihenfolge von `HOURLY_ROW_REQUIRED`.** Der Test setzt die Sonnen-Spanne früh und die Temperatur-Spanne spät; die Falle
   greift nur, solange im Tupel (`weather_aggregate.py:71`) Temperatur vor der Sonne steht (so entsteht `required_spans` in der Reihenfolge Temperatur, Sonne, siehe :1255-1257).
   Wird das Tupel einmal umgestellt, bleibt der Test still grün und verliert seine Kante. Billige Abhilfe: dieselbe Zuordnung gespiegelt (Sonne 12-14, Temperatur 08-10) als zweiter Parameter.
2. **Zusatztest in `test_substeps_blocked.py` ist nur mit Wahrscheinlichkeit rot** (Punkt 2); nie falsch rot.
3. **Dreifach vorhandener Hilfs-Code** in den Tests: `_inside` (hourly_commit :147 und live_estimate_silent_sensor, je mit anderem Startparameter), `_span_of` (substeps) und zwei verschieden
   signierte `_recording_substeps` (hourly_commit: `(monkeypatch)`, live: `(monkeypatch, module)`). Gleicher Name, andere Signatur, in zwei Dateien: kann beim späteren Zusammenlegen verwirren, funktional ohne Wirkung.
4. **Restlücke zu M8:** Der Standard-Attrappe in `_coord` entgehen die Tests, die die zweite Harness `_mock_store_coord` (`tests/test_sensor_liveness_coordinator.py:765`) benutzen. Vier davon sind
   pausierend (`_pausing(_sensor_group_zero(...))`, c21478c8-Zeilen 1024, 1065, 1077, 1088) und rufen weiter die echte `async_refresh_zone_estimates` gegen einen `Mock`-Store. Der Befund M8 nannte
   nur `_coord`, daher kein NOT ADDRESSED. Ob die echte Auffrischung dort still scheitert oder über Mocks läuft, habe ich nicht geprüft (keine Tests gelaufen).

## Antworten zu den Punkten 2-5

### Punkt 2 — Zusatztest `test_the_spans_of_several_fields_are_taken_in_time_order` (`tests/test_substeps_blocked.py:104`)

**Auf dem richtigen Code deterministisch grün, unabhängig von `PYTHONHASHSEED`.** Begründung aus dem Code (`weather_aggregate.py:1523-1530`): Die Hash-Abhängigkeit
steckt allein in der Iteration über `{*required, const.MAPPING_SOLRAD}` (Menge von Strings). Der gesunde Code reiht daraus *alle* Spannen und sortiert sie (`sorted` über Tupel von `datetime`,
paarweise verschieden, also vollständige Ordnung ohne Gleichstände); das Ergebnis hängt nur noch von den Spannen ab, nicht von der Mengenreihenfolge. `booked = _valid_segments(spans, start, end)` ist
damit fest, die Gewichte (`weight = measured_hours`, weil kein Sonnenfeld im Puffer) ebenso. Sonst hängt in dem Pfad nichts an Hash oder Mengenordnung (`blocked` ist ein Dict mit Einfügereihenfolge, `required` ein Tupel).
Belege des Implementers passen dazu: grün unter Seed 0 und 3 (`m5b-green2-s0/-s3.txt`: 28 passed), rot unter Seeds 0 bis 5 bei der Mutation `spans = sorted(` -> `list(` (`m5b-red-s0..s5.txt`, alle an
`test_substeps_blocked.py:124`).

**Wirkung unter der Mutation:** Rot, sobald die Mengenreihenfolge nicht genau der Zeitreihenfolge entspricht. Jede nicht aufsteigende Reihenfolge disjunkter Spannen verschluckt mindestens eine Spanne
(sie liegt in der Lücke, die der Cursor vor einem späteren Eintrag schon als „gemessen“ gebucht hat), also wird in einer stummen Stunde Gewicht gebucht und die Zusicherung bricht. Bei fünf Feldern
trifft die Reihenfolge den Zeitverlauf in etwa 1 von 120 Prozessen: die Mutation überlebt dort. Das ist ein Verlust an Fangquote (etwa 0,8 % je Lauf), kein Fehlalarm.

**Ist er als Test akzeptabel?** Ja, behalten. Gründe:
- Er schließt einen Teil von M5 selbst: Der Review-Text nennt beide Aufrufer („:1517 iteriert `sorted` über eine Menge, bei :1258 hängt die Reihenfolge an der Feldreihenfolge“) und führt
  die Triage-Zeile 8 „`sorted(required_spans)` ungetestet“. Vorgeschlagen war nur ein Test für die Zeilen; der zweite Aufrufer blieb sonst ohne Pin. Es ist also keine Zufallserweiterung.
- Die Konfiguration, die er trifft (kein Sonnenfeld, mehrere stumme Tagesform-Felder), ist die Betriebskonfiguration „geschätzte Sonne, kein Sonnensensor“. Mit Sonnenfeld wäre `booked` für die Gewichte
  bedeutungslos (der Implementer hat das beim ersten Entwurf selbst gemerkt und geschärft).
- Keine der Mutationsdateien (`mutations-final/-pr3/-r2/-wt.json`) enthält `sorted`; die Hash-Abhängigkeit kann das Ergebnis des 37er-Mutationslaufs also nicht verschieben.

**Empfohlene Schärfung (optional, drei bis vier Zeilen):** parametrisiere über die Zuordnung der Spannen zu den Feldern, vorwärts und gespiegelt, etwa
`@pytest.mark.parametrize("flip", [False, True])` und je Feld `index = 4 - i if flip else i` für `(T0 + (2 + 2*index)*H, T0 + (3 + 2*index)*H)`. Die Mengenreihenfolge ist im selben Prozess für beide
Läufe dieselbe; ist sie unter der einen Zuordnung aufsteigend, ist sie unter der gespiegelten absteigend, also unsortiert. Damit ist mindestens ein Lauf je Prozess rot, die Mutation wird zu 100 % gefangen,
auf dem gesunden Code bleiben beide grün. Ohne diese Schärfung ist der Test annehmbar; sie ist kein Merge-Blocker. Heraus muss er nicht.

### Punkt 3 — M5-Pin der Stundenzeilen rot mit `KeyError: 'Solar Radiation'`

**Als Pin ausreichend.**
- *Deterministisch:* `HOURLY_ROW_REQUIRED` ist ein Tupel (Temperatur, Feuchte, Wind, Sonne), `required_spans` (weather_aggregate.py:1255-1257) entsteht daher immer als Temperatur-Spanne 12-14, dann Sonnen-Spanne 08-10.
  Ohne `sorted` ergibt `_valid_segments` aus `[(12,14),(8,10)]` die gebuchten Segmente `(0,12)` und `(14,24)` (die zweite Spanne liegt unterm Cursor 14 und wird verschluckt). Die Stunden 8 und 9 gelten
  damit als gebucht, obwohl die Sonne dort keine gültige Zeit hat; `_masked_mean` liefert für die Sonne `None`, und `row["solar_mj_h"] = means[const.MAPPING_SOLRAD]` (weather_aggregate.py:1337)
  wirft. Kein Zufall, keine Umgebungsabhängigkeit; `m5-red-rows.txt` zeigt genau diesen Pfad.
- *Es ist die reale Folge des Fehlers:* Ohne Sortierung bräche die Zeilenbildung in Produktion mit derselben Ausnahme ab; die Ausnahme ist stärker als eine falsche Zahl, nicht schwächer.
- *Netz dahinter:* Fiele die Absicherung `means[SOLRAD]` einmal weg (etwa `.get`), finge `silent == {8, 9, 12, 13}` die falsche Abdeckung weiterhin.
- Einziger Vorbehalt ist Minor 1 oben (Abhängigkeit von der Tupel-Reihenfolge); mit einer gespiegelten Zuordnung wäre auch das gelöst.

### Punkt 4 — Kleine Zusätze

Keine neuen Fehler.
- `_expected_et_mm(..., blocked=None)` (test_live_estimate_from_buffer.py:202): letztes Schlüsselwort mit Vorgabe `None`, durchgereicht an `build_hourly_rows(..., blocked=None)`, dessen Vorgabe ebenfalls `None` ist
  (weather_aggregate.py:1138). Alle Altaufrufer rechnen unverändert; nur der neue Test setzt es.
- `_frozen_zone(..., *, service_forecast=True)` (…_daily.py:151): Vorgabe `True` reproduziert exakt das alte `forecast=_hourly_forecast()`; die beiden Altaufrufer (:187, :218) sind unverändert; nur der neue
  Test (:202) setzt `False`. `_estimating_inputs(..., forecast=None)` ist ein vorgesehener Aufruf (`hourly_forecast_tier` fällt dann auf `None`).
- Lokale Umbenennungen in `_weights_from_hourly_et`: äquivalent (siehe M4). Namensüberlappung: Im Aufrufer `build_substeps` heißt eine Schleifenvariable ebenfalls `measured_hours` (ein Skalar je Schritt,
  schon vorher so), in `_weights_from_hourly_et` heißt nun der Listen-Parameter so. Getrennte Gültigkeitsbereiche, nur Lesbarkeit.
- Es gibt keine Rückgriffe aus anderen Testdateien auf die geänderten Helfer (`git grep` nach `from tests.test_… import` ergibt für alle sechs betroffenen Module nichts).

### Punkt 5 — Bleibt jede bestehende Testaussage erhalten?

**Ja, keine Aussage geschwächt.** Alle entfernten oder geänderten Zeilen in den Testdateien des Diffs:
- M7: `FIELDS` und `_results` wandern von der Klasse auf Modulebene (`_RESULT_FIELDS`, `_results`, Inhalt gleich); `test_keep_with_outages_and_pause_without_one_match_a_plain_group` behält Namen, Klasse und
  Zusicherungen (`keep == plain`, `quiet == plain`); der umgedrehte Test steht unverändert in seiner neuen Klasse (`plain` -4,0; `paused` `-4.0 * 19 / 24`; „booked for 79 % of the period“). Die Verschiebung ändert nur die Knoten-ID
  (`task_compare`: beim Namensvergleich als „neuer Name“ zu lesen, der alte stand nicht in der Baseline).
- M8: Die Attrappe ersetzt eine Auffrischung, die gegen `_FakeStore` sofort an `.config` scheiterte und nichts Beobachtbares tat (`m8-before-real-refresh.txt`). Die Tests der Klasse `TestTheEstimateFollowsTheRecord`
  setzen ihre eigene Attrappe (c21478c8 :1239, :1293) und sind im Verhalten unverändert; niemand patcht die Methode auf Klassenebene (Grep), die Instanz-Attrappe schattiert also nichts. Die Prüfung „eine Auffrischung, die
  scheitert, lässt die Prüfung heil“ gewinnt `assert_awaited_once()` dazu (Verschärfung).
- M9: `approx` -> `==` (Verschärfung). M10: `test_an_open_outage_cuts_up_to_now` behält die alte Zusicherung `live_deficit ≈ round(Commit-Eimer, 2)` und bekommt zwei strengere dazu; die zusätzlich vorgeschalteten
  Läufe ohne Sperre nutzen dasselbe Muster wie `test_the_hourly_source_agrees_with_the_commit` (gleiche Datei), und beim Wechsel auf einen offenen Ausfall wird der Übertrag über den neuen Schlüssel verworfen.
- Rest: Docstrings und die beiden optionalen Parameter (Punkt 4). `task_compare` (`sdd\fix\task-compare-tfix.out`): `new FAILED: 0`, die zwei fehlenden Baseline-Namen sind die zwei bekannten, das eine `failed`
  (`test_next_irrigation_sensor.py::…test_setup_entry_announces_after_loading_schedules`) steht laut Implementer schon in der Baseline. Die 37 Anker stehen je einmal (`anchors-after.txt`).

## Out-of-scope observations

- `git status --short` im Worktree war während meiner Prüfung kurz nicht leer (vier Produktionsdateien und eine Testdatei als geändert), bei der nächsten Abfrage wieder leer. Vermutlich der laufende Mutations-/Suite-Lauf des
  Controllers. Ich habe deshalb nur Git-Objekte gelesen; die Urteile beziehen sich ausschließlich auf `c21478c8`.
- Der Implementer nutzt als Trailer `Claude Opus 5.5`, wie im Auftrag verlangt; das ist eine Controller-Entscheidung und keine Beanstandung.
- Die Raw-Belege zeigen bei den Läufen weiter die bekannten Teardown-ERRORs „Lingering timer“ (Vorbestand); alle neuen Tests sind `passed`.
- Nicht geprüft: Laufzeit der neuen Tests auf CI (Linux), Gleitkomma-Gleichheit `steps == booked[-1]` in A-Live über Plattformen hinweg (beide Seiten rufen dieselbe Funktion mit denselben Eingaben; sollte
  gleich bleiben, ist aber nur lokal unter Windows belegt).
