## Teil A — Commit

### Task 1: Die Sperren eines Fensters als freie Funktion

**Files:**
- Modify: `custom_components/irrigation_plus/sensor_liveness.py` (neue Funktion nach `valid_share`, `:223-235`)
- Modify: `custom_components/irrigation_plus/calculation.py` (Importe `:44-50`, `_blocked_spans_for_zone` `:420-453`)
- Test: `tests/test_sensor_liveness_blocked.py`

**Interfaces:**
- Produces: `zone_blocked_spans(store, zone: dict, start, end) -> dict | None` in `sensor_liveness.py` — `None` für eine
  Gruppe auf *behalten*, ohne Gruppe, ohne Anfang/Ende oder ohne verbleibende Sperre; sonst `{feld: ((von, bis), …)}`
  ohne Regenzähler. `CalculationMixin._blocked_spans_for_zone(zone, *, now)` bleibt mit gleicher Signatur und ruft die
  Funktion; das Gate auf die Stundenrechnung bleibt bis Task 5.

- [ ] **Step 1: Tests schreiben**

@@TEST T1@@

- [ ] **Step 2: RED**

Run: `TZ=UTC /d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests/test_sensor_liveness_blocked.py -p _local_socket_unblock -q`
Expected: Sammelfehler `ImportError: cannot import name 'zone_blocked_spans'`.

- [ ] **Step 3: Implementierung**

@@CODE T1@@

- [ ] **Step 4: GREEN**

Run: wie Step 2. Expected: `@@COUNT T1@@ passed`.

- [ ] **Step 5: Prüfen**

```bash
cd /d/Entwicklung/HASI/issue8-pr3-work/wt
uvx black custom_components/irrigation_plus/ && uvx ruff@0.16.10 check custom_components/irrigation_plus/
../task_compare.sh t1 tests/test_sensor_liveness_blocked.py tests/test_silent_sensor_commit.py
```

Expected: kein Baseline-Name entfällt, keine neuen FAILED, keine neuen ERROR.

- [ ] **Step 6: Commit**

```bash
git add custom_components/irrigation_plus/sensor_liveness.py custom_components/irrigation_plus/calculation.py tests/test_sensor_liveness_blocked.py
git commit -F - <<'EOF'
refactor(liveness): one function cuts a zone's window for every caller

The commit's gate method computed the blocked spans itself. The live
estimate needs the same spans for its own window, and its mixin cannot
call the calculation's: it runs alone in its tests, where a cross-mixin
call raises and is swallowed as a failed estimate. zone_blocked_spans
takes the store, the zone and the window explicitly; the commit's method
wraps it and still declines under the hourly calculation for now.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
```

### Task 2: Stundenzeilen buchen nur gemessene Zeit

**Files:**
- Modify: `custom_components/irrigation_plus/weather_aggregate.py` (`_HOURLY_ROW_REQUIRED` `:71` → öffentlich; neue
  Helfer nach `_hold_integral_upto` `:793-800`; `_precip_increments` `:803`; `_books_nothing` vor `_ratio_hold_solar`
  `:909`; `build_hourly_rows` `:1007-1174`)
- Modify: `custom_components/irrigation_plus/et_estimate.py` (`eto_hourly_series` `:103-145`, `hourly_eto_priced`
  `:148-191`)
- Test: neu `tests/test_hourly_rows_blocked.py`

**Interfaces:**
- Produces: `HOURLY_ROW_REQUIRED` (bisher `_HOURLY_ROW_REQUIRED`; kein Test nutzt den alten Namen);
  `build_hourly_rows(…, blocked=None)`; `hourly_eto_priced(…, blocked=None)`;
  `_precip_increments(samples, aggregate, *, spans=None, start=None, end=None)` (alte Aufrufe bleiben gültig);
  `_masked_hold_table(samples, spans, start, end, *, mask=None)`, `_masked_upto(table, t)`, `_masked_mean(table, a, b)`,
  `_overlap_hours(segments, a, b)`, `_books_nothing(row)`. Eine gesperrte Stunde ist eine Zeile mit `coverage_h == 0.0`
  ohne Messfelder; `eto_hourly_series` gibt für sie `0.0`.

- [ ] **Step 1: Tests schreiben**

@@TEST T2@@

- [ ] **Step 2: RED**

Run: `TZ=UTC /d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests/test_hourly_rows_blocked.py -p _local_socket_unblock -q`
Expected: Sammelfehler `ImportError: cannot import name 'HOURLY_ROW_REQUIRED'`.

- [ ] **Step 3: Implementierung** (der Diff enthält auch die Umbenennung `_HOURLY_ROW_REQUIRED` → `HOURLY_ROW_REQUIRED`,
  drei Stellen)

@@CODE T2@@

- [ ] **Step 4: GREEN**

Run: wie Step 2. Expected: `@@COUNT T2@@ passed`.

- [ ] **Step 5: Prüfen**

```bash
uvx black custom_components/irrigation_plus/ && uvx ruff@0.16.10 check custom_components/irrigation_plus/
../task_compare.sh t2 tests/test_hourly_rows_blocked.py tests/test_summed_hourly_eto.py tests/test_solar_ratio_hold.py tests/test_cumulative_delta.py tests/test_hourly_rows_dst.py tests/test_water_balance_substeps.py tests/test_weather_aggregate_blocked.py tests/test_et_hourly.py tests/test_live_estimate_from_buffer.py
```

Expected: kein Baseline-Name entfällt, keine neuen FAILED oder ERROR.

- [ ] **Step 6: Commit**

```bash
git add custom_components/irrigation_plus/weather_aggregate.py custom_components/irrigation_plus/et_estimate.py tests/test_hourly_rows_blocked.py
git commit -F - <<'EOF'
feat(weather): hourly rows charge each hour only for its measured time

A pausing sensor group's blocked field is averaged over its own valid
time in each hour, never held into a span, and after one the value from
before holds again. The hour is charged only for the time in which
temperature, humidity, wind and the sun were all measured; an hour
without any stays a row without readings and without ET, so the per-hour
series stays complete and a silent sensor never sends the window to the
daily form. Readings stamped inside a span neither count for their hour
nor feed the clearness ratio, and a blocked rain rate adds only its
measured part, landing at the end of it. Without spans every row is what
it was.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
```

### Task 3: Die nachgespielte Bilanz legt ET nur in gemessene Zeit

**Files:**
- Modify: `custom_components/irrigation_plus/weather_aggregate.py` (`build_substeps` `:1211-1361`)
- Test: neu `tests/test_substeps_blocked.py`

**Interfaces:**
- Consumes: `_masked_hold_table`, `_masked_upto`, `_overlap_hours`, `_precip_increments(…, spans=, start=, end=)` aus
  Task 2.
- Produces: `build_substeps(…, blocked=None, required=())` — `required` = Pflichtmenge der Form, die der Commit rechnet.

- [ ] **Step 1: Tests schreiben**

@@TEST T3@@

- [ ] **Step 2: RED**

Run: `TZ=UTC /d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests/test_substeps_blocked.py -p _local_socket_unblock -q`
Expected: `9 failed`, jeweils `TypeError: build_substeps() got an unexpected keyword argument 'blocked'`.

- [ ] **Step 3: Implementierung**

@@CODE T3@@

- [ ] **Step 4: GREEN**

Run: wie Step 2. Expected: `@@COUNT T3@@ passed`.

- [ ] **Step 5: Prüfen**

```bash
uvx black custom_components/irrigation_plus/ && uvx ruff@0.16.10 check custom_components/irrigation_plus/
../task_compare.sh t3 tests/test_substeps_blocked.py tests/test_water_balance_substeps.py tests/test_summed_hourly_eto.py tests/test_live_estimate_replayed_balance.py
```

Expected: kein Baseline-Name entfällt, keine neuen FAILED oder ERROR.

- [ ] **Step 6: Commit**

```bash
git add custom_components/irrigation_plus/weather_aggregate.py tests/test_substeps_blocked.py
git commit -F - <<'EOF'
feat(weather): the replayed balance places a pausing group's ET in measured time

The sub-steps spread the window's ET by measured sun. Where a field the
zone's form needs was silent nothing is booked, so nothing is placed
there either; the sun's own silent time weighs nothing, its frozen value
being no measurement, and a dark hour spreads its share over its
measured part. A blocked rain rate adds only its measured rain, so the
steps still reconcile with the aggregate. Only the placement moves.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
```

### Task 4: Der Commit bucht die Stundenform, Anteil nach der Form, die lief

**Files:**
- Modify: `custom_components/irrigation_plus/calculation.py` (Importe `:51-57`; Kommentar `_REQUIRED_SENSOR_FIELDS`
  `:65-82` und neue Funktion danach; `_hourly_et_for_zone` `:945-1049`; `_substeps_for_zone` `:1051-1101`;
  `calculate_module`: Anteil `:1256-1268` hinter die Formwahl `:1293-1297`, Teilschritt-Aufruf `:1405-1407`)
- Test: neu `tests/test_silent_sensor_hourly_commit.py`

**Interfaces:**
- Consumes: `HOURLY_ROW_REQUIRED` (Task 2), `hourly_eto_priced(…, blocked=)` (Task 2), `build_substeps(…, blocked=,
  required=)` (Task 3).
- Produces: `required_sensor_fields(module_name, *, hourly=False)` (öffentlich in `calculation.py`, auch für die
  Live-Schätzung); `_hourly_et_for_zone(…, blocked=None)`; `_substeps_for_zone(…, blocked=None, required=())`.
- Das Gate steht noch: Im Betrieb erreicht die Stundenform bis Task 5 keine Sperre; die Tests rufen `calculate_module`
  direkt mit Sperren.

- [ ] **Step 1: Tests schreiben**

@@TEST T4@@

- [ ] **Step 2: RED**

Run: `TZ=UTC /d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests/test_silent_sensor_hourly_commit.py -p _local_socket_unblock -q`
Expected: Sammelfehler `ImportError: cannot import name 'required_sensor_fields'`.

- [ ] **Step 3: Implementierung**

@@CODE T4@@

- [ ] **Step 4: GREEN**

Run: wie Step 2. Expected: `@@COUNT T4@@ passed`, dazu 8 Teardown-ERROR „Lingering timer“.

- [ ] **Step 5: Prüfen**

```bash
uvx black custom_components/irrigation_plus/ && uvx ruff@0.16.10 check custom_components/irrigation_plus/
../task_compare.sh t4 tests/test_silent_sensor_hourly_commit.py tests/test_silent_sensor_commit.py tests/test_summed_hourly_eto.py tests/test_water_balance_substeps.py tests/test_live_estimate_replayed_balance.py tests/test_live_estimate_without_hourly_calculation.py
```

Expected: kein Baseline-Name entfällt; keine neuen FAILED; neue ERROR nur 8 in `test_silent_sensor_hourly_commit.py`.

- [ ] **Step 6: Commit**

```bash
git add custom_components/irrigation_plus/calculation.py tests/test_silent_sensor_hourly_commit.py
git commit -F - <<'EOF'
feat(calculation): the hourly form books a pausing group's measured time

The commit hands the blocked spans to the hourly rows and to the replayed
balance, and takes the share once the form is known: the hourly form
needs temperature, humidity, wind and the sun, the daily form its own
fields (required_sensor_fields, shared with the live estimate). The
hourly total already holds the measured part and is not scaled again;
the explanation names the time share. Nothing reaches this in operation
while the gate still declines the hourly calculation.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
```

### Task 5: Das Gate fällt — Hinweis, Log, Panel-Hilfe, Doku

**Files:**
- Modify: `custom_components/irrigation_plus/calculation.py` (`_blocked_spans_for_zone`)
- Modify: `custom_components/irrigation_plus/sensor_liveness.py` (Moduldocstring `:11-14`, `_group_cuts` `:585-595`,
  `async_resync_stale_issue` Docstring)
- Modify: `custom_components/irrigation_plus/__init__.py` (`:1246-1250` entfällt)
- Modify: `custom_components/irrigation_plus/const.py` (Kommentar `:715-718`)
- Modify: `custom_components/irrigation_plus/weather_aggregate.py` (Docstring `aggregate_window` `:346-350`)
- Modify: `custom_components/irrigation_plus/frontend/localize/languages/*.json` (8) und 2 Bundles in `dist/`
- Modify: `docs/configuration-sensor-groups.md` (Zeile 59 und 62, Wortlaut nach Freigabe)
- Test: `tests/test_silent_sensor_commit.py`, `tests/test_sensor_liveness_coordinator.py` (je 2 Tests umgedreht)

**Interfaces:** keine neuen Namen.

- [ ] **Step 1: Die vier Tests des Zwischenstands umdrehen**

@@TEST T5@@

- [ ] **Step 2: RED**

```bash
K="test_the_hourly_calculation_is_cut_the_same or test_a_pausing_group_under_the_hourly_switch_is_cut_too or test_under_the_hourly_calculation_too_they_are_no_longer_used or test_switching_the_hourly_calculation_leaves_the_notice_alone"
TZ=UTC /d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests/test_silent_sensor_commit.py tests/test_sensor_liveness_coordinator.py -p _local_socket_unblock -q -k "$K"
```

Expected: `4 failed` (im Probelauf gegen den Stand von Task 4 gemessen).

- [ ] **Step 3: Implementierung (Python, Kommentare)**

@@CODE T5@@

- [ ] **Step 4: Panel-Hilfe in 8 Sprachen** — Skript nach `D:\Entwicklung\HASI\issue8-pr3-work\strip_help.py` legen
  (per Write-Werkzeug, die englische Zeile enthält `\"`) und ausführen:

```python
@@STRIP_HELP@@
```

```bash
/d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -I ../strip_help.py custom_components/irrigation_plus/frontend/localize/languages
```

Expected: 8 × `removed`; `git diff --stat` 8 Dateien, je 1 Zeile.

- [ ] **Step 5: Doku** — nach der Freigabe des Wortlauts (Abschnitt *Wortlaute*); der Block zeigt die englische Fassung
  des Probelaufs:

@@DOCS T5@@

- [ ] **Step 6: Bundles bauen**

```bash
cd custom_components/irrigation_plus/frontend && npm ci && npm run build && cd -
git status --short -- custom_components/irrigation_plus/frontend/dist
git checkout -- custom_components/irrigation_plus/frontend/dist/irrigation-plus-card.js custom_components/irrigation_plus/frontend/dist/irrigation-plus-card-legacy.js
for f in custom_components/irrigation_plus/frontend/dist/*.js; do echo "$f $(grep -c 'Applies only while' $f)"; done
```

Expected: nur `irrigation-plus.js` und `irrigation-plus-card-impl.js` geändert (die anderen zwei nur im Zeilenende); in
keinem Bundle mehr „Applies only while“.

- [ ] **Step 7: GREEN**

Run: wie Step 2. Expected: `4 passed` (dazu 2 Teardown-ERROR).

- [ ] **Step 8: Prüfen**

```bash
uvx black custom_components/irrigation_plus/ && uvx ruff@0.16.10 check custom_components/irrigation_plus/
../task_compare.sh t5 tests/test_silent_sensor_commit.py tests/test_sensor_liveness_coordinator.py tests/test_sensor_liveness_blocked.py tests/test_i18n_completeness.py tests/test_silent_sensor_hourly_commit.py tests/test_silent_sensor_setting.py tests/test_sensor_liveness_repair.py
```

Expected: es entfallen genau die zwei alten Namen `test_with_the_hourly_calculation_nothing_is_cut` und
`test_a_pausing_group_under_the_hourly_calculation_matches_too`; keine neuen FAILED; neue ERROR nur 2 in
`test_silent_sensor_commit.py` (die umbenannten) und 8 in `test_silent_sensor_hourly_commit.py`.

- [ ] **Step 9: Commit**

```bash
git add custom_components/irrigation_plus/calculation.py custom_components/irrigation_plus/sensor_liveness.py custom_components/irrigation_plus/__init__.py custom_components/irrigation_plus/const.py custom_components/irrigation_plus/weather_aggregate.py custom_components/irrigation_plus/frontend/localize/languages/ docs/configuration-sensor-groups.md tests/test_silent_sensor_commit.py tests/test_sensor_liveness_coordinator.py
git add -f custom_components/irrigation_plus/frontend/dist/
git diff --cached --name-only | wc -l    # 18
git commit -F - <<'EOF'
feat(liveness): a pausing group is cut under the hourly calculation too

Only the daily form cut, because the replayed balance checks itself
against the aggregate's rain and the hourly rows were not cut. Both are
now, so the commit's spans no longer depend on the switch: the notice and
the log say a group's values are left out wherever it pauses, switching
the hourly calculation no longer rewrites open notices, and the panel
help drops its "only while hourly is off" sentence (bundles rebuilt).
The docs name the fields each form needs and what the hourly form does
with a partly measured hour.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
```

## Teil B — Live-Schätzung

### Task 6: Die Live-Schätzung schneidet dieselben Sperren

**Files:**
- Modify: `custom_components/irrigation_plus/live_estimate.py` (Moduldocstring `:21-22`; Importe `:78-112`;
  `_HourlyCarry` `:182-206` und neue `_carried_outages`; `_aggregate_live_window` `:590-636`;
  `_observed_precip_since_mm` `:638-660`; `_buffer_hourly_et` `:718-793`; `_latest_temperature` `:888-908`;
  `_projected_extremes` `:910-965`; `_composed_day_et` `:967-1065`; `_daily_mirror_et` `:1104-1145` (nur
  durchreichen); `_buffer_water_steps` `:1147-1207`; `_intraday_for_zone` `:1305-1644`)
- Modify: `custom_components/irrigation_plus/weather_aggregate.py` (Docstring `aggregate_window`)
- Test: neu `tests/test_live_estimate_silent_sensor.py`; `tests/test_live_estimate_replayed_balance.py` (`:536`, ein
  Test-Double)

**Interfaces:**
- Consumes: `zone_blocked_spans` (Task 1), `required_sensor_fields` (Task 4), `hourly_eto_priced(…, blocked=)` (Task 2),
  `build_substeps(…, blocked=, required=)` (Task 3).
- Produces: `_HourlyCarry.outages` (Standard `()`), `_carried_outages(mapping) -> tuple`,
  `_aggregate_live_window(zone, anchor, *, now=None, blocked=None)`,
  `_observed_precip_since_mm(zone, anchor, *, now=None, blocked=None)`, `_buffer_hourly_et(…, blocked=None)`,
  `_latest_temperature(zone, agg, *, blocked=None, now=None)`, `_projected_extremes(…, blocked=None)`,
  `_composed_day_et(…, blocked=None)`, `_daily_mirror_et(…, blocked=None)`, `_buffer_water_steps(…, blocked=None,
  required=())`.

- [ ] **Step 1: Tests schreiben** (und das Test-Double anpassen, das die neuen Schlüsselwörter sonst mit `TypeError`
  ablehnt — die Schätzung gälte dann als fehlgeschlagen)

@@TEST T6@@

- [ ] **Step 2: RED**

Run: `TZ=UTC /d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests/test_live_estimate_silent_sensor.py -p _local_socket_unblock -q`
Expected: alle bis auf `test_a_group_that_keeps_is_estimated_as_before` rot — `AttributeError: module
'custom_components.irrigation_plus.live_estimate' has no attribute 'zone_blocked_spans'`, `TypeError: … _latest_temperature()
got an unexpected keyword argument 'blocked'`, Live-Eimer ≠ Commit-Eimer, kein Unterschied im Niederschlag/Übertrag.

- [ ] **Step 3: Implementierung**

@@CODE T6@@

- [ ] **Step 4: GREEN**

Run: wie Step 2. Expected: `@@COUNT T6@@ passed`, dazu Teardown-ERROR.

- [ ] **Step 5: Prüfen**

```bash
uvx black custom_components/irrigation_plus/ && uvx ruff@0.16.10 check custom_components/irrigation_plus/
../task_compare.sh t6 $(ls tests/test_live_estimate*.py tests/test_silent_sensor*.py tests/test_next_irrigation*.py)
```

Expected: es entfallen nur die zwei in Task 5 umbenannten Namen; keine neuen FAILED; neue ERROR nur aus den neuen Dateien
und den zwei umbenannten Tests.

- [ ] **Step 6: Commit**

```bash
git add custom_components/irrigation_plus/live_estimate.py custom_components/irrigation_plus/weather_aggregate.py tests/test_live_estimate_silent_sensor.py tests/test_live_estimate_replayed_balance.py
git commit -F - <<'EOF'
feat(live): the live estimate leaves out a pausing group's silent time

The estimate exists to show the path the stored bucket takes, so it now
cuts the spans the commit will: computed once per refresh from its own
anchor to its now and handed to every reader of the buffer -- the
aggregate and its rain, the hourly rows, the replayed balance, and the
current temperature, which is not read from a sensor silent right now.
The completed-hour carry is keyed on the group's outage record and
setting as well: an outage opens on the next check and closes at a
return that can lie before the last refresh, so a carried hour can
change after it closed. A group that keeps is estimated as before.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
```

### Task 7: Der Tagesform-Spiegel bucht den Anteil des Commits

**Files:**
- Modify: `custom_components/irrigation_plus/live_estimate.py` (Import `valid_share`; `_daily_mirror_et`)
- Modify: `docs/configuration-sensor-groups.md` (Satz zur Live-Schätzung in Zeile 62)
- Test: neu `tests/test_live_estimate_silent_sensor_daily.py` (erste zwei Klassen)

**Interfaces:**
- Consumes: `required_sensor_fields` (Task 4), `valid_share` (PR 2), `_daily_mirror_et(…, blocked=)` (Task 6).
- Produces: `_daily_mirror_et` gibt bei Anteil 0 `_DayTotal(0.0, TIER_OBSERVED)` statt `None`.

- [ ] **Step 1: Tests schreiben**

@@TEST T7@@

- [ ] **Step 2: RED**

Run: `TZ=UTC /d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests/test_live_estimate_silent_sensor_daily.py -p _local_socket_unblock -q`
Expected: `2 failed, 1 passed` — der Live-Eimer verfehlt den gebuchten (ohne Anteil), und
`AssertionError: assert 'hourly' == 'daily_mirror'` (die Kette rutscht zur Stundenreihe des Wetterdienstes).

- [ ] **Step 3: Implementierung**

@@CODE T7@@

Doku (Wortlaut nach Freigabe; englische Fassung des Probelaufs):

@@DOCS T7@@

- [ ] **Step 4: GREEN**

Run: wie Step 2. Expected: `3 passed`, dazu Teardown-ERROR.

- [ ] **Step 5: Prüfen**

```bash
uvx black custom_components/irrigation_plus/ && uvx ruff@0.16.10 check custom_components/irrigation_plus/
../task_compare.sh t7 $(ls tests/test_live_estimate*.py tests/test_silent_sensor*.py tests/test_next_irrigation*.py)
```

- [ ] **Step 6: Commit**

```bash
git add custom_components/irrigation_plus/live_estimate.py docs/configuration-sensor-groups.md tests/test_live_estimate_silent_sensor_daily.py
git commit -F - <<'EOF'
feat(live): the daily mirror books the share the commit books

A zone whose commit runs the daily equation is estimated by that
equation over the elapsed window; for a pausing group the commit books
only the part in which every field of the daily form was measured, so
the mirror books that part too. A field silent throughout now answers 0
instead of None: None sent the source chain on to a weather service's
hourly series, a source the commit never books from. The docs say the
live estimate leaves out the same time.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
```

### Task 8: Die Hochrechnung rechnet aus der gemessenen Zeit

**Files:**
- Modify: `custom_components/irrigation_plus/live_estimate.py` (`_carry_estimate_to` `:1828-1982`)
- Test: `tests/test_live_estimate_silent_sensor_daily.py` (Klasse `TestTheProjectionToTheDecisionPoint`)

**Interfaces:**
- Consumes: `zone_blocked_spans` (Task 1), `_aggregate_live_window(…, blocked=)` und `_composed_day_et(…, blocked=)`
  (Task 6).

- [ ] **Step 1: Tests schreiben**

@@TEST T8@@

- [ ] **Step 2: RED**

Run: `TZ=UTC /d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests/test_live_estimate_silent_sensor_daily.py -p _local_socket_unblock -q -k Projection`
Expected: `2 failed` — `assert 1.6405 < 1.6405` (die Hochrechnung bleibt ungeschnitten) und `assert 0 == 1` (keine
Sperren erfragt).

- [ ] **Step 3: Implementierung**

@@CODE T8@@

- [ ] **Step 4: GREEN**

Run: `… -m pytest tests/test_live_estimate_silent_sensor_daily.py …`. Expected: `5 passed`, dazu Teardown-ERROR.

- [ ] **Step 5: Prüfen**

```bash
uvx black custom_components/irrigation_plus/ && uvx ruff@0.16.10 check custom_components/irrigation_plus/
../task_compare.sh t8 $(ls tests/test_live_estimate*.py tests/test_silent_sensor*.py tests/test_next_irrigation*.py)
```

- [ ] **Step 6: Commit**

```bash
git add custom_components/irrigation_plus/live_estimate.py tests/test_live_estimate_silent_sensor_daily.py
git commit -F - <<'EOF'
feat(live): the projection to the decision point is priced off measured time

The projection books nothing, but it composes the day from the window's
observed part, and a dead sensor's frozen value is no observation. It
takes the group's spans once, from the same anchor and now, and composes
the day from the cut aggregate; whether the sensor will return is not
assumed either way.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
```

### Task 9: Ein Ausfall frischt die Live-Schätzung auf

**Files:**
- Modify: `custom_components/irrigation_plus/sensor_liveness.py` (`async_check_sensor_liveness` `:465-484`, neue
  `_refresh_estimates_after_outage_change`, `_async_check_mapping_liveness` gibt `bool` zurück)
- Test: `tests/test_sensor_liveness_coordinator.py` (neue Klasse `TestTheEstimateFollowsTheRecord`)

**Interfaces:**
- Consumes: `LiveEstimateMixin.async_refresh_zone_estimates` (vorhanden, über `getattr`, weil Test-Doubles der Prüfung
  ohne ihn laufen).
- Produces: `_async_check_mapping_liveness(…) -> bool` — wahr, wenn bei einer pausierenden Gruppe ein Ausfall geöffnet
  oder geschlossen wurde.

- [ ] **Step 1: Tests schreiben**

@@TEST T9@@

- [ ] **Step 2: RED**

Run: `TZ=UTC /d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests/test_sensor_liveness_coordinator.py -p _local_socket_unblock -q -k TestTheEstimateFollowsTheRecord`
Expected: `4 failed, 2 passed` (`Expected mock to have been awaited once. Awaited 0 times.`; die zwei grünen sind die
Wächter „behalten“ und „Fehler bleibt folgenlos“).

- [ ] **Step 3: Implementierung**

@@CODE T9@@

- [ ] **Step 4: GREEN**

Run: wie Step 2. Expected: `6 passed`.

- [ ] **Step 5: Prüfen**

```bash
uvx black custom_components/irrigation_plus/ && uvx ruff@0.16.10 check custom_components/irrigation_plus/
../task_compare.sh t9 $(ls tests/test_live_estimate*.py tests/test_silent_sensor*.py tests/test_sensor_liveness*.py tests/test_next_irrigation*.py)
```

- [ ] **Step 6: Commit**

```bash
git add custom_components/irrigation_plus/sensor_liveness.py tests/test_sensor_liveness_coordinator.py
git commit -F - <<'EOF'
feat(liveness): an outage of a pausing group refreshes the live estimate

A silent station writes no rows, so the ingestion that normally
refreshes the estimates stays quiet until the next poll, commit or run,
and the panel kept showing ET for a sensor that is no longer counted.
The check refreshes them once when an outage of a pausing group opens or
closes -- unthrottled, since a reading in the last minute would
otherwise swallow it. A failing refresh is logged and leaves the check
intact.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
```

