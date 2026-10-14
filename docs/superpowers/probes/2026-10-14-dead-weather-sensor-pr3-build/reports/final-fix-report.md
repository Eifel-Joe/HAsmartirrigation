# Abschluss-Fix-Welle — Bericht

Branch `feat/pause-silent-sensor-hourly-live`, Worktree `D:\Entwicklung\HASI\issue8-pr3-work\wt`.
Start `e62b046f`, Ende `c21478c8`. Alle Befunde I1-A-Commit, I1-A-Live, I1-B, I1-C, I1-D und M1-M13 sind erledigt;
keiner ist offen. Produktionslogik unverändert: im Produktionscode stehen nur Kommentare, Docstrings und die M4-Umbenennung
(`git diff e62b046f HEAD --numstat -- custom_components`: 28 Zeilen hinzu, 21 weg, nur diese).

Rohausgaben aller Läufe: `D:\Entwicklung\HASI\issue8-pr3-work\sdd\fix\` (je Probe eine Datei, Namen unten in Klammern),
Laufnotizen `sdd\fix\progress.txt`, Läufer `sdd\fix\run.sh`.

Verfahren je Pin: Test schreiben, grün auf dem jetzigen Code, Probe-Mutation per Edit setzen, derselbe Test rot, Mutation per
Edit exakt zurück, `git diff --quiet -- custom_components && echo restored` (jedes Mal `restored`), nach jeder Gruppe
`sha256sum -c sdd/fix/sha-before.txt` (calculation, weather_aggregate, live_estimate, sensor_liveness: je `OK`).
Alle Tests liefen mit `TZ=UTC`, Temp auf D:. „Teardown-ERROR“ = Vorbestand „Lingering timer“, steht bei jedem Test mit echtem Koordinator
dabei; entscheidend sind `passed`/`failed`.

## Commits

| SHA | Message (Betreff) |
|---|---|
| `08fed661` | `test(silent-sensor): pin the field sets and spans each reader of a pausing group is handed` |
| `1b0dfee0` | `test(silent-sensor): sharpen the remaining checks of the pausing-group tests` |
| `c21478c8` | `docs(silent-sensor): correct comments and docstrings, name measured hours as such` |

Letzte Zeile jeder Message: `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>` (wie im Auftrag verlangt; die Harness-Vorgabe nennt
Sonnet 5.5, der Auftrag hat Vorrang). Keine Verweise auf Fork-Issues, Upstream-Nummern, Spec-/Plan-Kürzel (per `grep` über
`e62b046f..HEAD` geprüft). `git status --short` leer. Kein Push, kein amend.

## I1 — Verdrahtungs-Pins (Commit `08fed661`)

### I1-A-Commit
- Test: `tests/test_silent_sensor_hourly_commit.py::TestTheReplayedBalance::test_the_daily_form_places_no_et_in_silent_time`
  (Hilfen `_recording_substeps`, `_inside`).
- Aufbau wie im Bericht: `_zone(…, solrad="1")`, Messwerte ohne Sonnenfeld, Stundenschalter an, Spion um `calculation.build_substeps`.
  Feuchte 10-12 gesperrt: Schritte `==` denen des ungesperrten Commits. Temperatur 10-12 gesperrt: alle Schritte in `[10:00, 12:00)` mit
  `et_weight == 0.0`, Summe 1, „Number of steps:“ in der Erklärung. Vorbedingung `plain_steps` nicht leer (kein leeres `==`).
- GREEN: 3 passed (`a-commit-green.txt`).
- RED 1, `calculation.py` `required=required or (),` -> `required=(),`: `assert all(steps[i].et_weight == 0.0 for i in inside)` / `E assert False`
  (`a-commit-red-required.txt`).
- RED 2, `weather_aggregate.py` Zweig `table is None`: `weight = measured_hours` -> `weight = dt_hours`: dieselbe Zusicherung
  (`a-commit-red-flat.txt`). Damit ist auch der Task-3-Punkt (Zweig Maske ohne Sonne) belegt.
- RED 3, `calculation.py` `hourly=hourly is not None` -> `hourly=hourly is None`: `assert seen[-1] == plain_steps` (Feuchte-Fall)
  (`a-commit-red-hourly.txt`). Der Temperatur-Teil allein bleibt hier grün, weil Temperatur in beiden Feldmengen steht.
- Abweichung: keine.

### I1-A-Live
- Tests: `tests/test_live_estimate_silent_sensor.py::TestTheReplayUnderTheHourlySwitch`
  - `test_a_daily_mirror_zone_replays_its_measured_time[with_sun|without_sun]` (parametrisiert: mit Sonnenfeld im Puffer und ohne, das
    ist die Konfiguration „geschätzte Sonne, kein Sonnensensor“).
  - `test_a_field_the_daily_form_does_without_places_its_et_as_before` (Feuchte-Ausfall ändert die Schritte nicht).
- Aufbau: `make_coordinator(hass)` (Stundenschalter an), `_estimating_zone`, Temperatur-Ausfall `_record(6, 16)` (gesperrt 09:00-16:00),
  Spione um `live_estimate.build_substeps` und `calculation.build_substeps`. Erwartet: `method == "daily_mirror"`,
  `balance_form == "replayed"`, Schritte in der Sperre Gewicht 0, Summe 1, **Schritte des Live == Schritte des Commits**,
  `live_deficit ≈ round(Commit-Eimer, 2)`.
- GREEN: `live-green-1.txt` (13 passed in der Datei).
- RED L1, `live_estimate.py` `required=required_sensor_fields(` -> `required=() and required_sensor_fields(`: beide Varianten
  `all(steps[i].et_weight == 0.0 …)` `E assert False` (`alive-red-required.txt`).
- RED L2, `hourly=buffer_et is not None,` -> `hourly=buffer_et is None,`: `test_a_field_the_daily_form_does_without_…`:
  `assert live[-1] == live[0]` (`alive-red-hourly.txt`). Der Temperatur-Test bleibt hier grün (siehe A-Commit RED 3); den vertauschten
  Schalter fängt erst der Feuchte-Test. Deshalb gibt es ihn als zweiten Test.
- RED L3, `blocked=blocked,` -> `blocked=None,` am Aufruf `_buffer_water_steps` (live_estimate ~1680): beide A-Live-Varianten rot
  (`assert False`) und B rot (`alive-b-red-blocked.txt`).
- Abweichung: Sonnenfeld-Variante und Feuchte-Test sind Zusatz zur Skizze; Ziel und Erwartung des Berichts sind erfüllt.

### I1-B
- Test: `test_a_blocked_rain_rate_is_published_as_the_commit_books_it` um `assert uncut["balance_form"] == "replayed"` und
  `assert est["balance_form"] == "replayed"` ergänzt.
- GREEN: `live-green-1.txt`.
- RED, dieselbe Mutation wie L3: `tests\test_live_estimate_silent_sensor.py:229: assert est["balance_form"] == "replayed"` /
  `AssertionError: assert 'lumped' == 'replayed'` (`alive-b-red-blocked.txt`).

### I1-C
- Test: `tests/test_live_estimate_silent_sensor_daily.py::TestTheProjectionToTheDecisionPoint::test_a_temperature_silent_now_anchors_no_remainder`.
  `_frozen_zone` bekam das Schlüsselwort `service_forecast=True`; mit `False` gehen `inputs` ohne Stundenprognose-Stufe in
  `_estimating_inputs(…, forecast=None)`. Gespeicherte `MAPPING_TEMPERATURE_AMPLITUDES` `[["2026-05-21", 14.0]]`.
  *behalten*: `forecast_tier` und `projection_tier` je `"self_contained"`. Offener Ausfall `_silent(store, zone, 4)`: beide `"observed"`.
- GREEN: `c-green.txt` (7 passed).
- RED C1, `live_estimate.py` `_daily_mirror_et` -> `_composed_day_et` ohne `blocked=blocked` (:1220): `assert paused["forecast_tier"] == "observed"` /
  `'self_contained' == 'observed'` (`c-red-1220.txt`).
- RED C2, `_carry_estimate_to` -> `_composed_day_et` ohne `blocked=blocked` (:2042): `assert paused["projection_tier"] == "observed"`
  (`c-red-2042.txt`); `forecast_tier` bleibt dort richtig.
- RED C3, `_composed_day_et` -> `_projected_extremes` ohne `blocked=blocked` (:1072): `forecast_tier` (`c-red-1072.txt`).
- RED C4, `_projected_extremes` -> `_latest_temperature(zone, agg)` statt `(zone, agg, blocked=blocked, now=now)` (:992): `forecast_tier`
  (`c-red-992.txt`). Alle vier Stellen der Kette einzeln belegt.

### I1-D
- Test: `tests/test_live_estimate_silent_sensor.py::TestTheRainItPublishes::test_a_blocked_rain_rate_is_cut_on_every_source[hourly|proxy]`.
  Passthrough-Zone (`module_name="Passthrough"`), Regenrate `{10: 2.0, 11: 2.0, 15: 1.0}`, Niederschlags-Ausfall 06-12.
  `hourly` über `_client_inputs(_provider_rows(0.0))`, `proxy` über `_proxy_inputs()`. Erwartet `method == source`,
  `precip_since ≈ Niederschlag des geschnittenen Commit-Aggregats` und `< ungeschnitten - 1.0`.
- GREEN: `live-green-1.txt`.
- RED D1, Pfad `hourly` (`_observed_precip_since_mm(… blocked=blocked)` -> ohne `blocked`): `[hourly]` rot `assert 5.0 == 0.9999999999999999 ± 1.0e-03`,
  `[proxy]` grün (`d-red-hourly.txt`).
- RED D2, Pfad `proxy` ebenso: `[proxy]` rot, `[hourly]` grün (`d-red-proxy.txt`).
- Die dritte Stelle (Buffer-Quelle) ist durch die bestehende Mutation 36 gepinnt.

## Übrige Befunde

### M5 (Test in Commit `1b0dfee0`, Docstring in `c21478c8`)
- Test: `tests/test_hourly_rows_blocked.py::TestSpansOfDifferentFieldsAreTakenInTimeOrder::test_a_late_field_with_an_early_span_is_not_overlooked`
  (Sonnen-Spanne 08-10, Temperatur-Spanne 12-14; `coverage_h == 0.0` genau in 8, 9, 12, 13, sonst 1.0). GREEN: 18 passed (`m5-green.txt`).
- RED: `weather_aggregate.py` `_valid_segments(sorted(required_spans), start, end)` -> `_valid_segments(required_spans, start, end)`: FAILED, aber mit
  `KeyError: 'Solar Radiation'` statt einer Zusicherung (Stunden 8, 9 würden gebucht, die Sonne hat dort keine gültige Zeit, die Invariante des
  Zeilenbauers bricht) (`m5-red-rows.txt`). Der Test ist rot, nur die Fehlerart ist eine andere als im Bericht skizziert.
- Zusatz (nicht im Bericht): `tests/test_substeps_blocked.py::TestTheEtLandsInMeasuredTime::test_the_spans_of_several_fields_are_taken_in_time_order`
  für die zweite `sorted`-Stelle (`build_substeps`, :1517). Fünf Felder mit je einer Stunde Ausfall, Messwerte ohne Sonnenfeld. Erste Fassung (mit Sonnenfeld)
  blieb unter der Mutation **grün**, weil `booked` dann die Gewichte nicht bestimmt; deshalb geschärft. RED: `spans = sorted(` -> `spans = list(`:
  `assert all(cut[i].et_weight == 0.0 for i in inside)` / `E assert False`, unter `PYTHONHASHSEED` 0 bis 5 jeweils rot (`m5b-red-s0..s5.txt`); wiederhergestellt
  unter Seed 0 und 3 grün (28 passed, beide Dateien). Hinweis: die Feldreihenfolge kommt aus einer Menge, ist also hash-abhängig; unter der Mutation ist der Test
  mit Wahrscheinlichkeit 119/120 je Prozess rot, am gesunden Code immer grün.
- Docstring `_valid_segments`: „sorted (overlaps allowed)“ mit Folgesatz.

### M7 (Commit `1b0dfee0`)
`test_a_pausing_group_under_the_hourly_switch_is_cut_too` zog in `TestTheHourlySwitchDoesNotDecide`; `FIELDS`/`_results` wurden dafür auf Modulebene gehoben
(`_RESULT_FIELDS`, `_results`), beide Klassen rufen sie. Testfunktionsname unverändert. `m7-green.txt`: 37 passed (Datei).

### M8 (Commit `1b0dfee0`)
`_coord` setzt `coord.async_refresh_zone_estimates = AsyncMock()` als Standard; `test_a_refresh_that_fails_leaves_the_check_intact` prüft
`assert_awaited_once()`.
- Vorher (Beleg `m8-before-real-refresh.txt`): die älteren `_pausing`-Tests rufen die echte Auffrischung; im DEBUG-Log steht
  `AttributeError: '_FakeStore' object has no attribute 'config'`. Nachher: 0 Treffer.
- GREEN: `m8-green.txt` 55 passed.
- RED: `sensor_liveness.py` `refresh = getattr(self, "async_refresh_zone_estimates", None)` -> `refresh = None`:
  `tests\test_sensor_liveness_coordinator.py:1295 … AssertionError: Expected mock to have been awaited once. Awaited 0 times.` (auch die vier anderen
  Tests der Klasse, die Awaits zählen) (`m8-red.txt`).

### M9 (Commit `1b0dfee0`)
`test_dewpoint_does_not`: `==` statt `pytest.approx`. GREEN (1 passed). Keine Mutation vorgesehen.

### M10 (Test in Commit `1b0dfee0`, Docstring in `c21478c8`)
- `test_an_open_outage_cuts_up_to_now` hat nun einen ungeschnittenen Lauf (Live und Commit) und prüft `est["et_since"] < uncut["et_since"] - 0.1` und
  `data[BUCKET] > uncut_data[BUCKET] + 0.1`. GREEN (`m10-green.txt`).
- RED: `sensor_liveness.py` `zone_blocked_spans` `return blocked or None` -> `return None` (keiner schneidet): `assert 6.03 < (6.03 - 0.1)`
  (`m10-red.txt`); die alte Zusicherung Live == Commit blieb dabei grün, wie der Bericht sagt.
- Docstring `_frozen_zone`: stumm ab +4 h, gesperrt ab +7 h.

### M11 (Commit `1b0dfee0`)
- Test: `tests/test_live_estimate_from_buffer.py::TestAPausingGroupWithTheMixinAlone::test_it_cuts_the_silent_time_without_the_calculation_mixin`
  (`_Coord(LiveEstimateMixin)`, Temperatur ab 09:00 stumm, gesperrt 12:00-14:30; `available`, `method == "hourly_sensor"`, `et_since ≈` Zeilenbauer mit
  denselben Sperren, `< plain - 0.1`). `_expected_et_mm` bekam das optionale `blocked=None`. GREEN 28 passed (`m11-green.txt`).
- RED 1: `live_estimate.py` (`_intraday_for_zone`) `blocked = zone_blocked_spans(self.store, zone, anchor, now_local)` -> `self._blocked_spans_for_zone(zone, now=now_local)`:
  der neue Test rot (`assert False is True` bei `available`). **Aber auch drei ältere Sensor-only-Tests** rot, weil der Aufruf unbedingt ist (`m11-red.txt`).
- RED 2 (trennscharf): derselbe Querruf nur `if group_pauses(…) else None`: **nur** der neue Test rot, 27 andere grün (`m11-red-pausing-only.txt`).
  Das ist die Lücke, die der Test schließt.

### M12 (Commit `1b0dfee0`)
- Test: `TestTheCarryFollowsTheOutages::test_an_open_outage_keeps_the_carried_hours_from_one_minute_to_the_next`: offener Ausfall, `LATE` und `LATE + 2 min`; Spion um
  `hourly_eto_priced`: Wasserzeichen `== carry.boundary` (23:00), `carry.outages` unverändert. GREEN 3 passed (`m12-green.txt`).
- RED: `_buffer_hourly_et` `outages = _carried_outages(mapping)` -> `tuple(sorted((blocked or {}).items()))` (Schlüssel aus den zugeschnittenen Spannen):
  `assert priced_from == [carried.boundary]` (Wasserzeichen 22.05. 00:00 statt 23:00); die zwei älteren Carry-Tests bleiben grün, das Ergebnis wäre also
  richtig und nur der Cache nutzlos, wie der Bericht sagt (`m12-red.txt`).
- Hinweis: „Eintrag bleibt in `_hourly_carry()`“ allein trennt nicht (der Eintrag wird auch nach einem Verwerfen neu geschrieben); deshalb die Spion-Variante.

### Nur Kommentar/Docstring/Umbenennung (Commit `c21478c8`)
- **M1** `sensor_liveness.py` `cuts_field`: nennt `zone_blocked_spans`.
- **M2** `live_estimate.py` `_daily_mirror_et`: Kommentar „whatever the forecast says, and the equation is not asked for it“; Docstring „With no measured time, nothing is booked“.
  Gleicher Fehler im Docstring des Tests `test_a_zone_that_averages_forecast_days_in_needs_no_forecast_for_it` („books 0 without asking for a forecast“) -> „books 0 whatever the forecast“.
  Commit-Message von `08728aa7` unberührt.
- **M3** `weather_aggregate.py` `build_substeps`: „No measured time to place it in: spread it flat, as for a window without radiation, so the rain still replays.“
- **M4** `_weights_from_hourly_et(weights, hours, measured_hours, hourly_et)`; einziger Aufrufer (`build_substeps`, positional) unverändert. Lokale Namen `dt` -> `measured`,
  `hour_seconds` -> `hour_measured` (enthielt Stunden); Kommentar „measured time WITHIN the hour“ (das `WITHIN` bleibt wie im Original); der Docstring bekam einen Satz zu
  `measured_hours`. Läufe um die Umbenennung: `test_substeps_blocked`, `test_water_balance_substeps`, `test_weather_aggregate*`, `test_summed_hourly_eto`: 110 passed (`rename-check.txt`).
- **M5-Docstring** siehe oben. **M6** `calculation.py` `required_sensor_fields`: nennt `_REQUIRED_SENSOR_FIELDS`, neu umbrochen.
- **M13** `weather_aggregate.py` `_ratio_hold_solar`: „has no air state to take a ratio against“. **M10-Docstring** siehe oben.

## Lint

Im selben Befehlsblock `UV_CACHE_DIR=D:/Entwicklung/HASI/issue8-pr3-work/uv-cache`:
- `uvx black custom_components/irrigation_plus/`: `70 files left unchanged.` Vor/nach dem Lauf identischer `git status` (`status-before-black.txt`): black hat keine Datei außerhalb meiner Änderungen angefasst.
- `uvx ruff@0.16.10 check custom_components/irrigation_plus/`: `All checks passed!`
- Zusätzlich auf den geänderten Testdateien: `black --check` und `ruff check` sauber.

## Anker-Check

`MUT_CHECK=1 … mutate-pr3.py wt mutations-check.json | grep -c "anchor count 1 "` -> **37** vor den Änderungen (`anchors-before.txt`), 37 nach den Änderungen und noch einmal nach dem letzten Commit
(`anchors-after.txt`).

## task_compare

`../task_compare.sh tfix $(ls tests/test_live_estimate*.py tests/test_silent_sensor*.py tests/test_sensor_liveness*.py tests/test_hourly_rows_blocked.py tests/test_substeps_blocked.py tests/test_next_irrigation*.py)`
(`task-compare-tfix.out`):

```
baseline names missing now: 2
ERROR tests/test_silent_sensor_commit.py::TestAGroupThatIsNotCutCalculatesAsBefore::test_a_pausing_group_under_the_hourly_calculation_matches_too
ERROR tests/test_silent_sensor_commit.py::TestTheGate::test_with_the_hourly_calculation_nothing_is_cut
new FAILED: 0
new ERROR per file:
14 ERROR tests/test_live_estimate_silent_sensor.py
7 ERROR tests/test_live_estimate_silent_sensor_daily.py
2 ERROR tests/test_silent_sensor_commit.py
9 ERROR tests/test_silent_sensor_hourly_commit.py
============ 1 failed, 544 passed, 278 errors in 110.42s (0:01:50) ============
```

- Die zwei fehlenden Baseline-Namen sind die zwei bekannten (im Branch umbenannt bzw. entfernt).
- Das eine `failed` ist Vorbestand: `tests/test_next_irrigation_sensor.py::TestSetupAnnouncesSchedules::test_setup_entry_announces_after_loading_schedules` steht in `task-tfix-base.txt`.
- Die „new ERROR“ sind ausschließlich Teardown-Fehler „Lingering timer“ neuer bzw. verschobener Tests (die neuen Tests dieser Welle laufen alle `passed`).
- Durch M7 verschoben: `ERROR …::TestAGroupThatIsNotCutCalculatesAsBefore::test_a_pausing_group_under_the_hourly_switch_is_cut_too` (Stand `e62b046f`, Teardown-Fehler) ist weg, dafür steht
  `ERROR …::TestTheHourlySwitchDoesNotDecide::test_a_pausing_group_under_the_hourly_switch_is_cut_too` da. Er stand nicht in der Baseline (der Name ist im Branch neu), zählt also unter den 2 neuen ERRORs der Datei.
- Mit dieser Welle mehr: in den drei Dateien des ersten Commits 31 statt 24 passed (Dateiebene, vor dem Rest), im Gesamtlauf 544 passed.

## Abweichungen und Bedenken

1. **M5 hourly rows:** rot mit `KeyError: 'Solar Radiation'` statt mit einer Zusicherung (siehe oben). Ein Pin, aber nicht die erwartete Fehlerart.
2. **Zusatztest `test_the_spans_of_several_fields_are_taken_in_time_order`** (zweite `sorted`-Stelle): nicht im Bericht verlangt. Unter der Mutation hash-abhängig rot (Seeds 0-5 alle rot).
   Wenn der Controller keinen Zusatz will, ist er in `1b0dfee0` sauber herauszunehmen (eigene Hunk-Gruppe in `tests/test_substeps_blocked.py`).
3. **M11 RED 1:** die naheliegende Mutation fängt auch ältere Tests; erst die auf den pausierenden Pfad beschränkte Variante trennt den neuen Test ab (belegt, siehe oben).
4. **Kleine Zusätze außerhalb der Liste, alle ohne Verhaltenswirkung:** gleicher Fehler im Docstring eines Daily-Tests (M2); Satz zu `measured_hours` im Docstring von `_weights_from_hourly_et`;
   lokale Namen in `_weights_from_hourly_et` mitumbenannt; optionales `blocked=None` an `_expected_et_mm`; Schlüsselwort `service_forecast` an `_frozen_zone`.
5. **Zeilenenden:** Dateien wurden mit dem Edit-Werkzeug bearbeitet, CRLF bleibt erhalten (Bytezählung `CRLF == LF` je Datei); `tests/test_hourly_rows_blocked.py` war und ist LF im Arbeitsbaum (Index LF, `core.autocrlf=true`).
6. Lokal nur die betroffenen Testdateien und die Umbenennungs-Nachbarn gelaufen, keine volle Suite.
7. Co-Authored-By nach Auftrag (Opus 5.5); die Harness-Vorgabe nennt Sonnet 5.5. Bei Bedarf ist das eine Entscheidung des Controllers.
