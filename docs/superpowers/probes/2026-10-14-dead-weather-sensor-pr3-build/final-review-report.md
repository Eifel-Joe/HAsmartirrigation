# Abschluss-Review `feat/pause-silent-sensor-hourly-live` (6fa424e8..e62b046f)

Geprüft gegen die Spec PR 3 (bindend), den Plan (Global Constraints, Review Focus, Rahmen, Selbstprüfung mit den vier
Abweichungen, Wortlaute) und dort, wo nötig, die PR-2-Spec. Code nur aus Git-Objekten gelesen (`git show e62b046f:…`,
`git diff 6fa424e8 e62b046f`). Tests nicht gelaufen; Suite- und Lint-Belege kommen vom Controller. Zeilenangaben
beziehen sich auf `e62b046f`, Pfade relativ zu `custom_components/irrigation_plus/`, sofern nicht `tests/` davorsteht.

## Stärken

- **Eine Quelle für die Sperren.** `zone_blocked_spans` (sensor_liveness.py:238-268) ist frei. Der Commit holt sie
  einmal (`_blocked_spans_for_zone` ist nur noch eine Hülle, calculation.py:431-444), die Live-Schätzung einmal je
  Neuberechnung (live_estimate.py:1488) und die Hochrechnung einmal für sich (:2020). Die Tests zählen die Aufrufe und
  prüfen `(start, end)`.
- **Gruppen auf *behalten* bleiben byte-identisch, und das ist belegbar.** Jeder neue Zweig hängt an
  `blocked`/`spans`/`mask`/`booked`; mit `None` laufen die alten Tabellen. Die Zeile `coverage <= 0` war schon vorher
  unerreichbar (weather_aggregate.py:1286-1291), `_books_nothing` greift also nur unter Sperren. Mit `booked is None` ist
  `measured == dt` Element für Element, deshalb sind `_weights_from_hourly_et` und beide Rückfälle für *behalten*
  unverändert. `_daily_mirror_et` ohne Sperren ist genau das alte `_mirror_blend` (`_daily_form_applies` →
  `_commit_forecast`). Die `==`-Tests auf Zeilen, Teilschritten und Live-Ergebnis halten das fest.
- **Die Maskierung ist sauber gebaut.** In `_masked_hold_table` (weather_aggregate.py:803-848) ist jede Ablesung und
  jede Spannengrenze ein Schnittpunkt, so gilt pro Stück genau ein Wert und genau ein Zustand. Halboffen über
  `_blocked_at`; die Ablesung bei der Rückkehr zählt. Nach der Sperre gilt der Wert von davor, und es gilt dieselbe
  Rückfüll-Regel wie bei `_held` und `_hold_integral_table`. `_valid_segments` verträgt sortierte, überlappende Spannen
  (der Cursor läuft mit `max`).
- **G4 ist sauber umgesetzt.** „Nie gelesen“ führt weiter zu `None` und damit zur Tagesform; „gesperrt“ ergibt Zeilen mit
  Gewicht 0. Eine leere Zeile wird nie bepreist (et_estimate.py:132-134), und `hourly_et` behält jede Stunde, so dass die
  Teilschritte nicht still auf Einmal-Buchung fallen.
- **G7 ist genauer als die Spec.** Ein Regenraten-Zuwachs wird an den Spannengrenzen geteilt und landet am Ende seines
  gemessenen Teils (weather_aggregate.py:918-932). Rechnerisch ist das dieselbe Trapezregel wie `_riemann_over`, nur
  anders zusammengefasst. Der Abgleich hält (1e-6 relativ). Regen direkt vor einer Sperre ist getestet.
- **Der Übertrags-Schlüssel ist richtig gewählt.** Schlüssel ist der Ausfall-Eintrag, nicht die zugeschnittene Spanne;
  bei *behalten* ist er leer (live_estimate.py:224-235). Damit gilt: Öffnen, Schließen, das Kürzen nach 7 Tagen und ein
  Wechsel *behalten*↔*pausieren* verwerfen den Übertrag. Ein offener Ausfall verwirft ihn dagegen nicht jede Minute.
  Abgeschlossene Stunden ändern sich bei offener Sperre nicht, der Schlüssel ist also auch korrekt.
- **Beide Fix-Runden halten.** `08728aa7`: Der Anteil kommt nach `_daily_form_applies` und vor der Prognose. Das gilt
  sonst nur bei Anteil 0 (Test mit `forecast_days = 2`). Ein Teilanteil ohne Prognose geht weiter den alten Weg.
  `e62b046f`: Der gedrosselte Aufruf hat ein eigenes Double, und `assert_not_awaited` hält die freigegebene Abweichung
  fest.
- **Die vier freigegebenen Abweichungen sind umgesetzt.**
  1. Ungedrosselte Auffrischung (sensor_liveness.py:522-536).
  2. Leere Zeilen; ihre Leser sind vollständig `eto_hourly_series` und `_ratio_hold_solar`, alle anderen lesen nur
     `hour_start`. Per `git grep` geprüft.
  3. Regen wird an den Grenzen geteilt.
  4. `zone_blocked_spans` prüft nur `None`; ein verkehrtes Fenster ist getestet.
- **Die Einheit aus Spec §1 hält über alle Commits.** Bei `d72c05d1` und `1160abc5` lehnt der Gate die Stundenrechnung
  noch ab. Gate, Texte, Panel-Hilfe und Doku fallen gemeinsam in `60ac780b`. Die Doku bei `60ac780b` sagt korrekt, dass
  die Live-Schätzung noch nicht schneidet; erst `2c374da9` ändert diesen Satz.
- **Kein neues Store-Feld, keine neuen Übersetzungsschlüssel.** Die Panel-Hilfe verliert genau den letzten Satz, in allen
  8 Sprachen.
- **Die Doku folgt Wort für Wort dem freigegebenen deutschen Wortlaut** (Zeile 59 und Absatz 62).
- **Keine Eigenbezüge.** Im Diff (ohne `dist`) und in allen 11 Commit-Messages findet sich kein `Eifel-Joe#`, `JustChr#`,
  `#N`, `G1`–`G12`, `F2`, `Task N` oder `PR 2/3`.

## Issues

### Critical

Keine.

### Important

**I1 — Die Spec verlangt zwei Tests, die nur teilweise da sind: „Sperren … an allen Lesern angekommen“ und
„Pflichtmenge je Form“. Vier Verdrahtungen hat kein Test.**

Betroffene Stellen:
- calculation.py:1424-1425 (`blocked=`, `required=required or ()` → `_substeps_for_zone`)
- live_estimate.py:1680-1688 (`blocked=`, `required=required_sensor_fields(…, hourly=buffer_et is not None)` →
  `_buffer_water_steps`)
- live_estimate.py:1220 und :2042 (`blocked=` → `_composed_day_et`), weiter über :1072 nach `_projected_extremes` und :992
  nach `_latest_temperature`
- live_estimate.py:1570-1572 und :1627-1629 (Niederschlag auf den Pfaden `hourly` und `proxy`)

*Warum es zählt:* Die Spec ist bindend. Unter *Tests/Teil B* verlangt sie „Sperren einmal gerechnet, an allen Lesern
angekommen“ und ausdrücklich `_latest_temperature`; unter *Mutationen* „Pflichtmenge je Form“. Getestet ist heute nur
Folgendes: dass einmal gerechnet wird; die Stundenquelle; das Aggregat; der Regen der Stundenquelle (Mutation 36);
`_latest_temperature` als Einzelfunktion; der Spiegel ohne Stundenschalter, also mit pauschaler Bilanz. Fällt eine der
Stellen oben weg, merkt das kein Test und keine Mutation. Die Folgen wären still:
- Ohne `required` legt die nachgespielte Bilanz die ET in die stumme Zeit. Das trifft genau die Konfiguration
  „Stundenschalter an, geschätzte Sonne, kein Sonnensensor“: Tagesform plus nachgespielte Bilanz. Für diese Konfiguration
  gibt es überhaupt keinen Test mit Ausfall (Task 7 ⚠️).
- Ohne `blocked` in `_buffer_water_steps` fällt die Live-Bilanz bei einer gesperrten Regenrate auf die pauschale Form,
  weil der Abgleich die geschnittene Summe gegen die ungeschnittenen Schritte prüft.
- Ohne `blocked` in `_composed_day_et` verankert die Selbstrechner-Stufe die Restkurve am eingefrorenen Wert des toten
  Sensors (Spec §3.3).
- Ohne `blocked` an den zwei Regen-Stellen veröffentlicht die Schätzung bei Passthrough-Zonen Regen aus der stummen
  Zeit, den der Commit nicht bucht. Spec §3.5 nennt genau diesen Fall: „geschnitten wird dort nur eine gesperrte
  Regenrate“.

*Fix (nur Tests, kein Produktionscode):*
- **A-Commit**, `tests/test_silent_sensor_hourly_commit.py::TestTheReplayedBalance::test_the_daily_form_places_no_et_in_silent_time`
  - Aufbau: `_zone(…, solrad="1")` mit Messwerten **ohne** Sonnenfeld, also geschätzte Sonne ohne Sensor, unter dem
    Stundenschalter.
  - Ein Spion um `calculation.build_substeps`, der die zurückgegebenen Schritte festhält.
  - Temperatur gesperrt 10–12: Jeder Schritt in `[10:00, 12:00)` hat `et_weight == 0`, die Summe ist 1, und
    „Number of steps:“ steht in der Erklärung.
  - Feuchte gesperrt 10–12: Die Schritte sind `==` denen eines ungesperrten Commits, denn die Tagesform braucht keine
    Feuchte.
  - Fängt: `required=()`, ein vertauschtes `hourly=` und `weight = dt_hours` im Zweig `table is None`
    (weather_aggregate.py:1559-1562; damit ist auch der Task-3-Punkt dazu erledigt).
- **A-Live**, `tests/test_live_estimate_silent_sensor.py::TestTheReplayUnderTheHourlySwitch::test_a_daily_mirror_zone_replays_its_measured_time`
  - Aufbau: `make_coordinator(hass)` (Stundenschalter an) und `_estimating_zone`, Temperatur-Ausfall innerhalb des
    Fensters, ein Spion um `live_estimate.build_substeps`.
  - Erwartet: `method == "daily_mirror"`, `balance_form == "replayed"`, Schritte in der Sperre mit Gewicht 0,
    `live_deficit ≈ round(Commit-Eimer, 2)`.
  - Fängt `required`/`hourly=` an live_estimate.py:1683-1688 und schließt die Lücke aus Task 7 ⚠️.
- **B**: In `test_a_blocked_rain_rate_is_published_as_the_commit_books_it` (tests/test_live_estimate_silent_sensor.py:101)
  zusätzlich `assert est["balance_form"] == "replayed"`, für `uncut` genauso. Fällt `blocked=` an :1680 weg, ergibt sich
  `lumped`.
- **C**, `tests/test_live_estimate_silent_sensor_daily.py::TestTheProjectionToTheDecisionPoint::test_a_temperature_silent_now_anchors_no_remainder`
  - Aufbau: `_frozen_zone`, aber `inputs` **ohne** Stundenprognose-Stufe und mit gespeicherten
    `MAPPING_TEMPERATURE_AMPLITUDES`, damit die Selbstrechner-Stufe tatsächlich greift.
  - *behalten*: `estimate["forecast_tier"] == "self_contained"` und
    `_carry_estimate_to(…)["projection_tier"] == "self_contained"`.
  - Offener Ausfall (`_silent(store, zone, 4)`): beide `== "observed"`.
  - Fängt die Kette :1220/:2042 → :1072 → :992.
- **D** (fix if cheap), `tests/test_live_estimate_silent_sensor.py::TestTheRainItPublishes::test_a_blocked_rain_rate_is_cut_on_every_source`
  - Parametrisiert über `hourly` (Zeilen eines Anbieters) und `proxy` (nur Prognose).
  - Eine Passthrough-Zone mit Regenrate und Niederschlags-Ausfall; erwartet `est["method"]`, und `precip_since` ist
    gleich dem Niederschlag des geschnittenen Commit-Aggregats und kleiner als ungeschnitten.

### Minor

- **M1** sensor_liveness.py:191-193. Der Docstring von `cuts_field` nennt noch „The commit's gate
  (calculation._blocked_spans_for_zone)“. Heute fragt `zone_blocked_spans` (für Commit und Live) und der Hinweis.
  *Fix:* den Satz auf `zone_blocked_spans` umstellen.
- **M2** live_estimate.py:1195-1199. Der Kommentar sagt, der Commit frage „neither the equation nor the forecast“.
  Tatsächlich holt der Commit die Prognose im Pfad „alle Zonen“ vorher (calculation.py:575-580), bucht sie bei Anteil 0
  nur nicht. Dazu :1182-1184: Bei „With none, nothing is booked“ fehlt das Bezugswort. *Fix:* „…which books 0 whatever
  the forecast“ bzw. „With no measured time, nothing is booked“. Die Commit-Message von `08728aa7` bleibt; JustChr
  squasht beim Merge.
- **M3** weather_aggregate.py:1584-1586. „No measured time at all: nothing is booked, so the ET to place is 0“ stimmt
  nicht für die **Tagesform**, wenn nur die Sonne das ganze Fenster stumm war. Die Sonne ist dort keine Pflichtgröße
  (Anteil 1, ET wird gebucht), steht aber in der Maske, also wird die ET flach verteilt. Das Verhalten ist vertretbar, es
  entspricht dem Rückfall „keine Strahlung“. Nur der Kommentar ist falsch. *Fix:* „No measured time to place it in:
  spread it flat, as for a window without radiation, so the rain still replays.“
- **M4** weather_aggregate.py:1354 und :1376-1382. `_weights_from_hourly_et` bekommt in `dt_hours` jetzt die gemessenen
  Stunden. Der Kommentar spricht noch von „elapsed time WITHIN the hour“, und `hour_seconds` enthält Stunden. *Fix:*
  Parameter `measured_hours` nennen und Kommentar „measured time within the hour“.
- **M5** weather_aggregate.py:666-667. Der Docstring von `_valid_segments` verlangt „sorted, merged“, zwei Aufrufer
  übergeben nur sortiert, mit Überlappung (:1258, :1517); funktioniert. Dass dort `sorted` gebraucht wird, hält kein Test
  fest: Bei :1517 iteriert `sorted` über eine Menge, bei :1258 hängt die Reihenfolge an der Feldreihenfolge. *Fix:*
  Docstring „sorted (overlaps allowed)“. Dazu ein Test in tests/test_hourly_rows_blocked.py mit einer
  Sonnen-Spanne 08–10 und einer Temperatur-Spanne 12–14 (spätes Feld, frühe Spanne): Gewicht 0 genau in 8, 9, 12, 13.
- **M6** calculation.py:88. „its daily form the fields above“ zeigt auf einen Kommentar. *Fix:*
  `` ``_REQUIRED_SENSOR_FIELDS`` `` nennen.
- **M7** tests/test_silent_sensor_commit.py:437/467. Der umgedrehte Test steht in
  `TestAGroupThatIsNotCutCalculatesAsBefore` und prüft das Gegenteil des Klassennamens. *Fix:* in eine eigene Klasse
  verschieben, z. B. `TestTheHourlySwitchDoesNotDecide`. Der Testname ist im Branch ohnehin schon neu, der
  Namensvergleich ändert sich also nicht.
- **M8** tests/test_sensor_liveness_coordinator.py:1285-1291. `test_a_refresh_that_fails_leaves_the_check_intact`
  bliebe grün, wenn gar nicht aufgefrischt würde. *Fix:* `coord.async_refresh_zone_estimates.assert_awaited_once()`.
  Außerdem gibt `_coord` (:213-231) keine Auffrisch-Attrappe vor. Die älteren `_pausing`-Tests rufen deshalb die echte
  `async_refresh_zone_estimates` gegen einen Mock-`hass` auf, und die Ausnahme verschwindet im DEBUG-Log. *Fix:*
  `coord.async_refresh_zone_estimates = AsyncMock()` als Standard in `_coord`.
- **M9** tests/test_silent_sensor_hourly_commit.py:203. Eine Taupunkt-Spanne lässt in der Stundenform `booked = None`;
  das Delta ist also bit-gleich. Die Global Constraints verlangen `==`. *Fix:* `==` statt `pytest.approx`.
- **M10** tests/test_live_estimate_silent_sensor.py:80-88. `test_an_open_outage_cuts_up_to_now` vergleicht nur Live mit
  Commit. Würden beide gar nicht schneiden, bliebe er grün. *Fix:* einen ungeschnittenen Lauf dazunehmen und
  `uncut > cut` prüfen. Außerdem nennt tests/test_live_estimate_silent_sensor_daily.py:151-155 (`_frozen_zone`) „silent
  from 7 h“; stumm ab +4 h, gesperrt ab +7 h wäre richtig.
- **M11** Die Testliste der Spec (Teil B) nennt „Live-Mixin allein ohne Querruf“. Alle neuen Tests laufen auf dem echten
  Koordinator; einen Querruf ins Rechen-Mixin würden sie nicht bemerken. *Fix:* eine pausierende Gruppe über
  `_Coord(LiveEstimateMixin)` (tests/test_live_estimate_from_buffer.py:153), dann `available` und ein geschnittenes
  `et_since`.
- **M12** Die Entscheidung aus G11, dass der Ausfall-Eintrag den Schlüssel bildet und nicht die zugeschnittene Spanne,
  hält kein Test fest. Ein Schlüssel aus den Spannen würde den Übertrag jede Minute verwerfen; das Ergebnis bliebe
  richtig, nur der Cache wäre nutzlos. *Fix:* In `TestTheCarryFollowsTheOutages` zwei Neuberechnungen bei offenem
  Ausfall (`LATE`, `LATE + 2 min`); dabei prüfen, dass der Eintrag in `_hourly_carry()` bleibt bzw. dass
  `hourly_eto_priced` ab `carry.boundary` rechnet.
- **M13** weather_aggregate.py:1044-1046. Der Satz „carries no reading to take a ratio from“ stimmt nur, wenn die Sonne
  selbst gesperrt ist. Ist nur ein anderes Feld gesperrt, gibt es Sonnenproben. Sie werden übersprungen, weil der leeren
  Zeile Temperatur und Feuchte für Rso fehlen. Das ist die Folge der freigegebenen Abweichung „leere Zeilen“; Wirkung
  praktisch null. *Fix:* „…has no air state to take a ratio against“.

## Triage der zurückgestellten Liste (55 Punkte)

Legende: **must** = vor dem PR · **cheap** = fix if cheap · **leave** = bleibt (mit „erledigt“, wenn am Kopf bestätigt)

| # | Punkt | Urteil | Grund (eine Zeile) |
|---|---|---|---|
| 1 | T1 ⚠️ Docstrings live_estimate/sensor_liveness | leave (erledigt) | am Kopf korrekt (sensor_liveness.py:12-14, live_estimate.py:628-629) |
| 2 | T1 Offset-Test ohne `hass` in UTC | leave | belegt wird „wirft nicht“; die Offset-Rechnung ist Vertrag von `coerce_stamp`, Ausfallstempel werden schon in `Outage.from_store` gewandelt |
| 3 | T1 Docstring `cuts_field` | cheap | M1 |
| 4 | T1 `is not None` statt Spannen | leave | geprüft wird „kein Gate“; die Spannen halten die Nachbartests fest |
| 5 | T1 „kein Anfang“ nur `None` | leave | unlesbare Strings sind Sache von `coerce_stamp` |
| 6 | T2 ⚠️ Aufrufer reichen `blocked` | leave (erledigt) | am Kopf alle verdrahtet (siehe I1 zu den ungetesteten) |
| 7 | T2 M1 Randprobe in `solar_samples` | leave | Ruling trägt; nur die erste Teilstunde, Commit und Live gleich |
| 8 | T2 `sorted(required_spans)` ungetestet | cheap | M5 |
| 9 | T2 Regen in buchungsloser Stunde ungetestet | leave | kein Produktivleser liest `row["precipitation"]` (per `git grep` geprüft) |
| 10 | T2 Aufbewahrungsregel viermal | leave | reine Refaktorierung, ohne Risiko |
| 11 | T2 `_precip_increments(spans)` ohne `start/end` | leave | kein Aufrufer; beide echten übergeben sie |
| 12 | T2 kleine Testlücken | leave | Randfälle ohne eigenes Risiko |
| 13 | T3 ⚠️ `required` am Aufrufer, `<2` → None | leave (erledigt) | verdrahtet; `<2` gleich wie im Aggregat |
| 14 | T3 Zweig Maske ohne Sonne → `measured_hours` | **must** | in Test A-Commit (ohne Sonnensensor) mit erledigt |
| 15 | T3 Sonnenproben nur durch eigene Spannen verworfen | leave | Docstring nennt es; Lage-Effekt minimal |
| 16 | T3 Test 4 / Test 7 | leave | Redundanz ohne Schaden |
| 17 | T3 Parametername `dt_hours` | cheap | M4 |
| 18 | T3 Standard `required=()` | leave | A-Commit/A-Live halten beide echten Aufrufer fest |
| 19 | T3 `_valid_segments` „merged“ | cheap | M5 |
| 20 | T3 Rückfall `list(measured)` | leave | nur bei ET 0 erreichbar, Ergebnis gleich |
| 21 | T4 ⚠️ Gate-Docstring / Suite | leave (erledigt) | Docstring ersetzt (calculation.py:432-440), Suite gelaufen |
| 22 | T4 M1 `required` in den Commit-Replay | **must** | I1, Test A-Commit |
| 23 | T4 `approx` statt `==` (Taupunkt) | cheap | M9 |
| 24 | T4 „nie gelesen“ auf Commit-Ebene | leave | Zeilentest deckt es; Commit-Glue ist Basis-Code |
| 25 | T4 Docstring „fields above“ | cheap | M6 |
| 26 | T5 ⚠️ Vorwärtsverweise, Interims-Satz | leave (erledigt) | am Kopf wahr; Doku-Satz ersetzt |
| 27 | T5 M1 Klassenname | cheap | M7 |
| 28 | T5 Stundenform über `async_calculate_zone` | leave | `_committed` der Live-Tests fährt dieselbe Kette in der Stundenform |
| 29 | T5 M3 `_group_cuts` Einzeiler | leave | harmlos |
| 30 | T6 ⚠️ (inkl. Live-`now` für den Regen bei *behalten*) | leave | Spec §3.1 verlangt es; vorher wurde bis zur Uhr gerechnet, jetzt bis zum `now` der ET – konsistenter |
| 31 | T6 M1a `blocked`/`required` an `_buffer_water_steps` | **must** | I1, Tests A-Live und B |
| 32 | T6 M1b zwei der drei Regen-Aufrufstellen | cheap | I1, Test D (Passthrough-Fall aus §3.5) |
| 33 | T6 M1c Kette Spiegel → `_latest_temperature` | **must** | I1, Test C |
| 34 | T6 Übertrag bei stabilem offenem Ausfall | cheap | M12, Spec-Entscheidung G11 |
| 35 | T6 offener Ausfall ohne Vergleich ungeschnitten | cheap | M10 |
| 36 | T6 Live-Test mit Offset-Stempeln | leave | `zone_blocked_spans` wandelt an der Eingangstür; dort getestet |
| 37 | T6 Modulname im Keyword-Argument | leave | kosmetisch, plan-diktiert |
| 38 | T7 Ruling Important (Anteil vor Prognose) | leave (erledigt) | `08728aa7` geprüft, Logik und Test tragen |
| 39 | T7 Kommentar/Commit-Message zum Fix | cheap | Kommentar M2; Message bleibt (Squash-Merge) |
| 40 | T7 Reihenfolge `_daily_form_applies` vor Anteil | leave | nur für Zonen ohne Spiegel relevant, dort heutiger Weg |
| 41 | T7 Tagesmenge nur über T/RH | leave | `required_sensor_fields` ist für Commit und Live dieselbe Funktion |
| 42 | T7 Modulname zweimal / toter Zweig | leave | kosmetisch |
| 43 | T7 Docstring „With none“ | cheap | M2 |
| 44 | T7 ⚠️ Stundenschalter + geschätzte Sonne ungetestet | **must** | I1, Test A-Live |
| 45 | T8 M1 `blocked=` an `_composed_day_et` (Hochrechnung) | **must** | I1, Test C |
| 46 | T8 nur Richtung / Grenzfälle | leave | Kernaussage gedeckt |
| 47 | T8 Docstring `_frozen_zone` | cheap | M10 |
| 48 | T8 ⚠️ `_projected_radiation` skaliert geschnittenes Mittel | leave | trifft am Fensterende das Commit-Mittel; G10 verlangt nichts anderes |
| 49 | T9 Ruling Important (ungedrosselt im Test) | leave (erledigt) | `e62b046f` geprüft, `assert_not_awaited` hält es fest |
| 50 | T9 ⚠️ Spec nennt noch `_throttled` | leave | freigegebene Abweichung steht im Plan; im Bauprotokoll vermerken |
| 51 | T9 `group_pauses` statt `_group_cuts` | leave | heute identisch |
| 52 | T9 Wächter `refresh is None` | leave | Abwehr für das Mixin ohne Koordinator |
| 53 | T9 Fehlschlag-Test ohne `assert_awaited_once` | cheap | M8 |
| 54 | T9 Ausnahme nach Store-Schreiben verliert Flag | leave | Issue-Registry müsste werfen; die nächste Abfrage frischt auf |
| 55 | T9 `_pausing`-Tests rufen echte Auffrischung | cheap | M8 |

Summe: **6 must** (14, 22, 31, 33, 44, 45; alle über die vier Tests A-Commit, A-Live, B und C) · **15 cheap** · **34
leave**, davon 7 am Kopf als erledigt bestätigt.

**Welche Pin-Kandidaten einen Test verdienen:** alle fünf.
- `required=` im Commit-Replay → A-Commit.
- `required=` und `blocked=` an `_buffer_water_steps` → A-Live und B.
- `blocked=` an `_composed_day_et`, für Spiegel und Hochrechnung → C.
- Die zwei Live-Regen-Stellen → D. D nur „cheap“: Der Leser `_observed_precip_since_mm` ist schon an der dritten Stelle
  gepinnt, und die zwei anderen Stellen sind derselbe Ausdruck.

## Declined to judge

- **Ergebnis der 37 Mutationen:** lief beim Review noch; das Urteil oben unterstellt keinen Ausgang.
- **Suite und Lint:** nicht selbst gelaufen; die Zahlen des Controllers sind plausibel (+1 passed/+1 error gegenüber der
  Probe = der Test aus `08728aa7`).
- **Minifizierte `dist`-Bundles:** nicht im Paket; Gleichheit mit dem Probe-Build angenommen.
- **Ende-zu-Ende-Kriterium auf HA-Test (Task 11)** und **Umsetzen auf den gemergten upstream-Stand (Task 12):** außerhalb
  dieses Reviews.
- **PR-2-Code, den PR 3 nicht anfasst:** `_aggregate_blocked`, Erkennung und Ausfall-Liste, Hinweistexte,
  `_silent_sensor_explanation`. Gilt aus dem PR-2-Review.
- **Fensteranfang:** Live-Anker (`max(last_calculated, Wasserzeichen)`) gegen Commit-Wasserzeichen, `_as_datetime` gegen
  `coerce_stamp`. Liegt so in der Basis.
- **Pfad „alle Zonen“ mit `forecast_days > 0` ohne Wetterdienst:** überspringt die Zone ganz
  (calculation.py:582-587). Das ist Basisverhalten und keine Folge von PR 3.
- **Teilanteil plus fehlende Prognose → Wetterdienst** (Task-7-Ruling): Die Kette rutscht dort wegen der Prognose, nicht
  wegen der Sperre. Die Spec-Grenze „nie wegen einer Sperre“ hält.
- **Konstruierter Fall „Pflichtfeld nur innerhalb der Sperre gelesen, ohne Randzeile“:** `_masked_hold_table` gibt
  `None`, damit `booked = []` und ET 0, die Erklärung nennt aber den Zeitanteil. Im Betrieb nicht erreichbar, denn der
  Beginn eines Ausfalls ist selbst eine Ablesung vor der Sperre.
- **Tagesform, nur die Sonne gesperrt:** Die gebuchte ET landet nur außerhalb der Sonnen-Sperre, im Extremfall in der
  Nacht. Das ist G6 wörtlich und betrifft nur die Lage.
- **Klarheitsquote, wenn nur ein anderes Feld gesperrt ist:** Die Sonnenprobe dieser Stunde liefert keine Quote (M13).
  Folge der freigegebenen leeren Zeilen, praktisch ohne Wirkung.
- **Laufzeitkosten** der maskierten Tabellen im Minutentakt: nicht gemessen; der Übertrag begrenzt das Fenster.
- **Ob die Auffrischung bei abgeschalteter Live-Schätzung Wetterdaten holt:** `async_get_zone_estimates` rechnet heute
  immer. Die zusätzliche Auffrischung kommt höchstens einmal je Öffnen oder Schließen; nicht weiter bewertet.

## Assessment

**Bereit für den PR: mit Fixes.**
- Die Logik ist korrekt. Commit und Live laufen gleich, *behalten* ist byte-identisch, es gibt kein neues Store-Feld.
  Doku und Panel-Hilfe stimmen, Eigenbezüge fehlen.
- Vor dem PR fehlen die Tests aus I1 (A-Commit, A-Live, B, C; D nach Aufwand), weil die Spec sie als Testpflicht nennt.
  Dazu die billigen Kommentar- und Testkorrekturen M1–M13. Produktionslogik muss sich nicht ändern; die geänderten
  Zeilen im Produktionscode sind nur Kommentare und Docstrings (M1–M6, M13).
