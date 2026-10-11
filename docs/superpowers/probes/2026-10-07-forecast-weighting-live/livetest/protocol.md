# Live-Protokoll Eifel-Joe#61 (HA-Test)
Spec: docs/superpowers/specs/2026-10-07-forecast-weighting-live-verification-design.md
Plan: docs/superpowers/plans/2026-10-07-forecast-weighting-live-verification.md
Quellstand: `upstream/master` = `6a40e083` (geprüft 2026-10-11 07:00 UTC, unverändert seit 06.10.)
Offset HA-Test: +02:00 (Europe/Berlin; `ha_eval_template` 2026-10-11 07:01:18 UTC = 09:01:18 Ortszeit)

| Kriterium | Zeit (UTC) | Rohzitat / Wert | O1 | O2 | Urteil |
|---|---|---|---|---|---|

## Task 1 — Orakel `o1.py` (2026-10-11, lokal)

- `o1_test.py` und `o1.py` = Plan-Codeblöcke 0/1 byte-gleich (`cmp` gegen `plan-probe/`).
- RED: `ModuleNotFoundError: No module named 'o1'` (Collection-Fehler).
- GREEN: `7 passed in 0.68s`.
- Mutationen (je eigener Ordner, Ersetzung trifft genau einmal):
  - (a) Stunde ab Stempel → `1 failed, 6 passed`, FAILED `test_a_rate_covers_the_hour_ending_at_its_stamp_pro_rata`
  - (b) kein Abschneiden vor der Auswertung → `1 failed, 6 passed`, FAILED `test_the_part_before_the_evaluation_is_cut_off`
  - (c) keine Lochprüfung → `1 failed, 6 passed`, FAILED `test_a_hole_inside_the_window_is_refused_and_one_outside_is_not`
  - Original danach: `7 passed`.

## E3 — Imperial-Probetest (2026-10-11 07:04 UTC, lokal gegen `src-6a40e083`)

`imperial_probe_test.py` = Plan-Codeblock 2 byte-gleich. Volle Ausgabe: `livetest/e3-imperial-probe.out`.

```
.FF
FAILED imperial_probe_test.py::test_imperial_panel_credits_the_forecast_in_the_deficits_unit
  AssertionError: assert 0 == 112
FAILED imperial_probe_test.py::test_imperial_run_credits_the_forecast_in_the_deficits_unit
  AssertionError: zone dropped: the mm credit covered the inch deficit
2 failed, 1 passed
```

- Kontrolle metrisch (`test_control_metric_panel_and_run_agree_with_the_mm_credit`): PASS — der Prüfaufbau trägt.
- Panel imperial: `_live_run_duration(zone, -0.5 in, metric=False, credit=5.08 mm)` = 0 s statt 112 s.
- Lauf imperial: `_zone_run_decision(...)` = `None` — die Zone fällt weg.

**Urteil: Verdacht E3 bestätigt.** Der Live-Pfad addiert die mm-Gutschrift auf das Defizit in Anzeige-Einheiten
(Zoll). Ende-zu-Ende auf einer echten imperialen Installation nicht gemessen (Spec §7).

## Blocker vor Task 3 (2026-10-11)

- WS `irrigation_plus/weather_forecast` (HA-Test, 07:01 UTC): `{"available": false, "days": []}`.
- Systemlog HA-Test: `PirateWeather API returned error status code: 429`, erstmals 2026-10-09 09:16:15 UTC,
  zuletzt 2026-10-11 07:01:21 UTC; Zähler 5466 (`PirateWeatherClient.py:243`, `get_forecast_data`) bzw. 550
  (`:351`, `get_data`); dazu WARNING `[async_update_all] No weather data to parse for sensor group 0/1` (550).
- Spec §6 Probe 0 und Task 4 brauchen einen echten Abruf mit Rohdokument → nicht möglich. Rücksprache.
- **User-Entscheidung (Chat):** neuer Pirate-Schlüssel (User trägt ihn im Panel ein); Nebenbefund erst messen, dann Issue.

## Nach dem Schlüsselwechsel (2026-10-11)

- Letzte 429-Zeile 09:10:43.205 Ortszeit; danach keine WARNING+ mehr. WS `weather_forecast` 07:13 UTC:
  `available: true`, 6 Tage 12.–17.10., `precipitation` je **0**.
- `config-before.json` gesichert 07:14 UTC (Werte wie Plan Task 3 Step 2 erwartet; kein Schlüsselfeld).
- Log-Pegel vorher (Plan Task 3 Step 3): `irrigation_plus` = WARNING (30). DEBUG nur auf
  `…weathermodules.PirateWeatherClient` von 09:13:45 bis 09:27:34 Ortszeit, danach `warning`.

### Abrufrate im Normalbetrieb (ein Zyklus, 09:20:42.554–09:20:43.326 Ortszeit)

| Art | Anzahl |
|---|---|
| echter Abruf `get_data` | 1 (09:20:42.554) |
| echter Abruf `get_forecast_data` | **18** (18 verschiedene SyncWorker, 09:20:42.748–43.321) |
| „Returning cached PirateWeather forecastdata“ | 19 |
| „Returning cached PirateWeather data“ | 1 |
| WARNING `urllib3.connectionpool` „Connection pool is full … size: 10“ | 8 |

→ 19 echte Anfragen je 10-Minuten-Zyklus bei gültigem Schlüssel (rechnerisch 19 × 144 = 2736 je Tag).
Mechanismus (Code `src-6a40e083`): ein geteiltes Client-Objekt (`helpers.py:877`), Frische-Prüfung ohne Sperre
(`PirateWeatherClient.py:139-143`), Zeitstempel nur bei Erfolg (`:322-323`), bei Fehler `RETRY_TIMES = 3` Versuche ohne
Pause (`:71`, `:237-247`). OWM/Open-Meteo/MetOffice: dieselbe Struktur ohne Sperre. HA-Prod-Systemlog 07:28 UTC: kein
`irrigation_plus`-Eintrag; Prod-Abrufrate nicht gemessen. Aufrufer der 18: Inventur läuft (Code-Lese-Agent).

### Probe 0 (a): Rohdokument im Log zerlegt

- Jede Abruf-Zeile ist 16379 Zeichen (+ 5 Byte Farbcode = 16384) und endet mitten in einem Eintrag; gefiltert gelesen
  (`search`) nur 31 von 168 Stundenwerten, kein `daily`.
- Ungefiltert gelesen: die Fortsetzung steht in 5 direkt folgenden Zeilen OHNE Zeitstempel (16384, 16384, 16384, 16384,
  11042 Zeichen), die letzte mit `'daily':`; `precipIntensity`-Zähler 32+34+33+33+33+12 = 177 = 1 currently + 168 hourly
  + 8 daily. → Dokument vollständig, aber nur durch Zusammensetzen lesbar; Plan Task 4 Step 3 (Suchfilter) sieht nur
  das erste Stück → Plan-Nachtrag nötig.

### Regenverteilung (E1)

- Stundenwerte 11.10. 07:00 UTC bis 12.10. 13:00 UTC (31 Werte, erstes Stück des Abrufs 09:20:42): alle `0`.
- Tagessummen 12.–17.10.: alle 0 mm. → **E1 trägt nicht** (kein Fenster mit Regen in Sicht). Rücksprache.

## Rev. 2 — Task 3 Step 5, Task 3a (2026-10-11)

- `coords-before.json` (09:18 UTC): `manual_coordinates_enabled` false, `manual_*` null; `grep -c "ha_"` = 0.
- Task 3a: `scout_test.py`/`scout.py` = Plan-Blöcke (byte-gleich mit `plan-probe-rev2/`). RED
  `No module named 'scout'`; GREEN `6 passed`; Mutationen (a) ohne `abs` 1 failed, (b) ohne Mindestregen 3 failed,
  (c) ohne T1 1 failed — alle getötet; lokale Suite `13 passed`.
- Rangliste `scout-0919.txt` (now 09:19 UTC, rows 96, 11.10. 00:00 bis 14.10. 23:00 UTC):
  Rang 1 **Brest** 48.39 / -4.49, elev 47, Reserve 2.68 (r_now 5.74, T1-Bestwert 12.10. 04:04 UTC);
  Rang 2 **Rostock** 54.09 / 12.10, elev 17, Reserve 2.17; Rang 3 Goeteborg 0.42; übrige 24 `ok=False`.

## Rev. 2 — Task 4R: Ersatzort Brest + Probe 0 (2026-10-11)

- Step 1: DEBUG `…PirateWeatherClient` (11:20 Ortszeit, vor dem Koordinatenwechsel).
- Step 2: `CUTOFF` 2026-10-11 11:20:11 Ortszeit; `coordinates_save` Brest **48.39 / -4.49, elev 47** →
  `{"success": true}`; Rücklesen `manual_coordinates_enabled` true, 48.39, -4.49, 47.
- Step 3: Eintrag `state: loaded`; Systemlog ohne neuen `irrigation_plus`-Eintrag nach `CUTOFF` (jüngster alter Eintrag
  07:10:43 UTC).
- Step 4, erster Versuch Baustein X: `SANDBOX_LIMIT_EXCEEDED` (10486116 > 10485760 Bytes). Ursache gemessen: Fenster
  500 Zeilen = 4 382 545 Bytes, 47 Abruf-Köpfe (19 um 09:20:42, 28 beim Neuladen 11:20:16), 282 Zeilen > 10 KB.
  User-Entscheidung: sparsame Variante → Plan Revision 2a (Baustein X′).
- Step 4 mit Baustein X′ (3 Seiten, `window_first` 09:20:43.326): **28 Dokumente** 11:20:15.839–11:20:16.387
  (1 `get_data`, 27 `get_forecast_data`), jedes `chunks` 6, `n_hourly` 168, `steps_ok`, `has_daily`, `n_precip` 177,
  `masked` true, `key_pattern` false; **eine** Stundenreihe für alle 28. **Probe 0 bestanden.**
  Maßgeblich: 11:20:16.387 `get_forecast_data` → `doc-112016.series.json`; Prüfsumme lokal `[168, 301057646400, 14.0]`
  = Sandbox `[168, 301057646400, 14]`; grep Koordinaten/Schlüssel 0.
  Reihe: erster Stempel 11.10. 09:00 UTC; Regen 11.10. 14:00 UTC bis 12.10. 10:00 UTC (21 Werte, 12.3 mm),
  13.10. 09:00 UTC 1.7 mm; sonst 0.
- Step 5: `scout.py check` mit NOW 2026-10-11T11:23:54+02:00 → `ok=True reserve=8.10 r_now=11.88
  worst=11.10 17:23Z t1=12.10 05:23Z`. Kein Ortswechsel nötig (Step 6 entfällt).
- **Testort: Brest (FR), 48.39 / -4.49, Höhe 47 m.** Reserve Open-Meteo 2.68, Pirate 8.10.

## Rev. 2 — Task 5R: Aufbau (2026-10-11, HA-Test)

- Step 1: `input_boolean.hasi61_a` / `_b` angelegt (`off`).
- Step 6R (vorgezogen): Pegel calculation/irrigation/live_estimate/skip_conditions `debug`, `irrigation_plus`/scheduler/
  auto_calc `info`; PirateWeatherClient bleibt `debug`.
- Step 2: Zonen **A = 9** „HASI61 A“, **B = 10** „HASI61 B“: `classic`, `linked_entity` `input_boolean.hasi61_a`/`_b`,
  Modul 0, Sensorgruppe 0, `flow_sensor`/`distributor_id` null, Größe 1, Durchsatz 3 → **180 mm/h, 1 mm = 20 s**.
  `SENSOR_A` = `sensor.irrigation_plus_lt_wegwerf_zone` (HA hat die Entitäts-ID der früher gelöschten Zone 9
  wiederverwendet; Attribut `id` = 9 per Template geprüft), `SENSOR_B` = `sensor.irrigation_plus_hasi61_b` (`id` 10).
- Step 3R: Konfiguration `forecast_weighting_enabled` true, `precipitation_threshold_mm` 100,
  `skip_irrigation_on_precipitation` true, `fixed_time`, Live aus, `precipitation_forecast_days` 1,
  `autoupdateinterval` "10"; INFO 11:24:49.440 „Scheduled auto update time interval for each 0:10:00“.
- Steps 4–5: `schedule_ec886994`, `schedule_1fac4605` `enabled: false`; **P61 = `schedule_be72fcbe`** „HASI61“,
  täglich, Start 04:00 (vorläufig), Anker Start, `zones` "9".

## Task 6 — Phase 1a (B1, B2a, B2b), 2026-10-11

- Vorbedingung: jüngste Wetterzeile `retrieved` 11:24:49.698 > `last_consumed_at` A/B 11:24:32 (Vergleich über
  `retrieved`, `calculation.py:406-411`, `const.py:777`).
- Kein echter Abruf zwischen 11:24:40 und 11:26 (Update 11:24:49 aus dem Zwischenspeicher) → Dokument weiter
  `doc-112016`.
- Step 1: E = 11:29:00+02:00 (09:29 UTC); `o1.py scan` (15 min, E+1 h bis E+20 h): O1(E) = 11.9383; früheste passende
  Zeile **T1 = 14:44 UTC = 16:44 Ortszeit**: O1(T1) = 11.3333, |O1(T1) − O1(E)| = 0.605, O1(T1+24h) = 1.7
  (Abstand 9.63); 57 passende Zeilen.
- Step 2: P61 `start_time` 16:44 (`success: true`). D = −(⌈11.9383⌉ + 15) = **−27 mm**.
  `set_bucket` erster Aufruf HTTP 500 — Bedienfehler: das MCP-Werkzeug reichte „a,b“ als EINE Entitäts-ID weiter
  (Systemlog `services.py:168` „No state found for entity sensor.…_zone,sensor.…_hasi61_b“); Eimer blieben 0.
  Zweiter Aufruf mit Liste in `data` → A/B `bucket` −27.
- **Ausführungshinweis (Reihenfolge):** `set_bucket` rückt `last_consumed_at` vor (A 11:24:32 → 11:26:45.695,
  B → 11:26:45.704). Danach muss erst eine neue Wetterzeile kommen, sonst rechnet die Zone still nicht. Reihenfolge
  daher in Task 6–9: `set_bucket` → neue Wetterzeile abwarten → rechnen (der Plan nennt Warten vor `set_bucket`).
- Outlook: `upcoming_runs` = nur P61, `next_run_utc` 2026-10-11T14:44:00+00:00 ✓.
  O2 vorher (Dokument 11:20:16): `checks[precipitation].observed` **11.33**, `threshold` 100, `would_skip` false.
- Step 3: O2 vorher 11.33; neue Wetterzeile `retrieved` 11:34:49.920 > Wassermarke 11:26:45 ✓; `calculate_zone`
  A+B (Liste in `data`); O2 nachher **11.33**.
- Step 4 Belege (Log, Ortszeit):
  - `11:35:52.846 … [calculate-module]: forecast weighting 11.33 mm rain → effective bucket -15.67 (true -27.01)` (A)
  - `11:35:52.881 … [calculate-module]: no scheduled run resolves for zone 10, so the forecast weighting measures
    from this calculation` (nur B)
  - `11:35:52.882 … [calculate-module]: forecast weighting 12.02 mm rain → effective bucket -14.99 (true -27.01)` (B)
  - WS zones A: `bucket` -27.005050056488447, `duration` 313, `irrigation_target_bucket` -11.333333333333336,
    `last_calculated` 2026-10-11T11:35:52.841956; B: -27.005050309329615, 300, -12.018615829916671,
    11:35:52.878785. Erklärung (de, Schlüssel `module.calculation.explanation.forecast-weighting-applied`,
    `calculation.py:1624`): A „… reduziert (-27.01 → -15.67)“, B „… (-27.01 → -14.99)“.
  - Maßgebliches Dokument: Schub 11:34:49.666–11:34:50.534 (1 `get_data` + 22 `get_forecast_data`), alle 23
    vollständig, **eine** Reihe (= Reihe von 11:20:16, Prüfsumme gleich) → letztes vor 11:35:52.846:
    **11:34:50.534** → `doc-113450.series.json` (Prüfsumme `[168, 301057646400, 14.0]`, grep 0).
  - Systemlog seit 11:34: nur „Connection pool is full“ (Abruf-Schub) und der eigene `set_bucket`-Bedienfehler
    11:26:33; kein `irrigation_plus`-Fehler, kein „[async_update_zone_config] … no sensor data“, keine 429.

| Kriterium | Zeit (UTC) | Rohzitat / Wert | O1 | O2 | Urteil |
|---|---|---|---|---|---|
| B1 | 09:35:52 | Rohdokument 11:34:50.534 vor der Rechnung; Gutschrift-Zeilen A/B; kein Fehler | — | — | **bestanden** |
| B2a | 09:35:52.846 | A: 11.33 (Log) / 11.333333 (Zone) | O1(T1=14:44Z, E) = 11.3333 | 11.33 | **bestanden** (|O1(T1) − O1(E)| = 0.6853 ≥ 0.5) |
| B2b | 09:35:52.881 | Fallback-Zeile nur Zone 10; B: 12.02 / 12.018616 | O1(E, E) = 12.0186 | — | **bestanden** |
| A/B Dauer + Ziel | 09:35:52 | A 313 = 15.6717·20 = 313.43; Ziel -11.3333 = Z − Y. B 300 = 14.9864·20 = 299.73; Ziel -12.0186 = Z − Y | — | — | **bestanden** |

## Task 7 — Phase 1b (B3), 2026-10-11

- `set_bucket` A = −27 (11:37:22; Wassermarke → 11:37:22.644); neue Wetterzeile `retrieved` 11:44:50.053 ✓.
- **Ausführungsfehler (vor jeder B3-Auswertung):** `calculate_zone` A um 11:45:45.491 lief, während P61 noch auf T1
  (16:44) stand — der Plan setzt P61 = T3 VOR der Rechnung. Ergebnis dieser Rechnung (Resolver-Anker T1):
  `11:45:45.493 … forecast weighting 11.33 mm rain → effective bucket -15.67 (true -27.00)`, `duration` 313,
  `irrigation_target_bucket` -11.3333 — bestätigt B2a ein zweites Mal (= O1(T1)), zählt aber nicht für B3.
  Korrektur: nächste Wetterzeile abwarten → P61 = T3 → sofort rechnen; kein erneutes `set_bucket` (Wassermarke).
  Korrekte Reihenfolge für Task 7–9: `set_bucket` → neue Wetterzeile → P61-Zeit setzen → rechnen.
- Neue Wetterzeile `retrieved` 11:54:49.919 ✓; HA-Zeit 11:55:25 → **T3 = 12:02 Ortszeit (10:02 UTC)**; P61
  `start_time` 12:02 und sofort `calculate_zone` A.
- Rechnung 11:55:30.806: `11:55:30.808 … forecast weighting 12.30 mm rain → effective bucket -14.71 (true -27.01)`;
  Zone A `bucket` Z₃ = -27.010456978401862, **d₃ = 294**, **g₃ = -12.300000000000004**.
- Maßgebliches Dokument: Schub 11:54:49.666–11:54:50.361 (23, alle vollständig, eine Reihe = bisherige Reihe) →
  **11:54:50.361** → `doc-115450.series.json` (Prüfsumme gleich). O1(T3, 11:55:30.806) = **12.3000** = X(A) 12.30 ✓.
- Sicherheits-Rücklesen vor T3: nur P61 aktiv, `zones` "9", `next_run_utc` 10:02 UTC; Zone 9 `classic`,
  `linked_entity` `input_boolean.hasi61_a`, `automatic` ✓. Erwartung ohne Gutschrift: |Z₃|·20 = 540 s.
- Belege nach dem Lauf (Log, Ortszeit): `12:02:00.113 INFO … scheduler: Executing recurring schedule: HASI61`;
  `12:02:05.120 … Parallel irrigation: zone 9 (timed)`; `12:02:05.121 … Metered (timed) irrigation: zone 9 for 294s
  @ 3.00 L/min` (5 s = Pumpen-Vorlauf `master_settle_seconds` 5); `12:06:59.237 … Metered irrigation: zone 9 done —
  14.70 L in 294s`. Suche „Committing the pre-run“: **leer** (unter `fixed_time` keine Vorabrechnung) ✓.
  Logbuch `input_boolean.hasi61_a`: on 12:02:05.121565, off 12:06:59.226433 (294.1 s).
  WS A: `run_log[0]` = {ts 12:06:59.237758+02:00, trigger schedule, planned_s 294, actual_s 294, volume_l 14.7,
  result completed}; `bucket` -12.310456978401863; `water_used_total` 14.7.

| Kriterium | Zeit (UTC) | Rohzitat / Wert | O1 | O2 | Urteil |
|---|---|---|---|---|---|
| B3 | 10:02:00–10:06:59 | planned_s 294 = d₃; 294 < 540 (Dauer aus wahrem Eimer); completed; Eimer -12.3105 vs g₃ -12.3 (Δ 0.0105 ≤ 0.05) | X(A) 12.30 = O1(T3) 12.3000 | — | **bestanden** |

## Task 8 — Phase 2 (B4, `before_run`), 2026-10-11

- Step 1: `autocalcmode` → `before_run` (`success`); `12:08:53.011 INFO … Automatic calculation runs before each
  irrigation run; no fixed-time calculation scheduled`. `set_bucket` A = −27 (Wassermarke 12:08:53.026).
- Neue Wetterzeile `retrieved` 12:14:49.924 ✓. **Neuer Pirate-Modelllauf** im Abruf 12:14:49.745 (`get_data`):
  erster Stempel 10:00 UTC, Regen ab 09–10 UTC, Summe 16.2 → `doc-121449.series.json` (Prüfsumme
  `[168, 301058251200, 16.2]`). In diesem Zyklus nur 1 echter Abruf.
- Step 3: jetzt 12:15:38; `o1.py scan` (1 min, +6…+60 min): **T4 = 12:22 Ortszeit (10:22 UTC)**, O1(T4) 14.2167,
  O1(T4+24h) 1.7. P61 `start_time` 12:22; Sicherheits-Rücklesen: nur P61, `zones` "9", `next_run_utc` 10:22 UTC,
  Zone 9 `classic` auf `input_boolean.hasi61_a`, `before_run` ✓.
- **Nebenbefund (Abrufrate):** das Speichern von P61 um ≈ 12:16 löste einen Schub von **30 echten
  `get_forecast_data`-Abrufen** aus (12:16:05.966–12:16:06.761) — Zeitplan-Änderung → Projektionen → Wächter-Vorschau.
- Step 4 Logkette (Ortszeit): `12:22:00.489 INFO … scheduler: Executing recurring schedule: HASI61` →
  `12:22:00.489 INFO … auto_calc: Committing the pre-run calculation for zones: 9` → `12:22:00.489 INFO …
  Calculating zone 9` → `12:22:00.493 DEBUG … [calculate-module]: forecast weighting 14.22 mm rain → effective
  bucket -12.77 (true -26.99)`; Vorhersage beim Dispatch nur „Returning cached“ (kein echter Abruf).
  `12:22:05.533 … Metered (timed) irrigation: zone 9 for 255s @ 3.00 L/min`.
  WS A: `last_calculated` 2026-10-11T12:22:00.490199 (= T4), `duration` d₄ = 255, `irrigation_target_bucket`
  g₄ = -14.216598371805553. Outlook `last_skip_evaluation`: `timestamp` 2026-10-11T10:22:00.530021+00:00,
  `checks[precipitation].observed` **14.22**.
  Maßgebliches Dokument: letzter echter Abruf vor 12:22:00.493 = **12:16:06.761** (Schub 12:16:05.966–06.761,
  30 Dokumente + 12:14:49.745, alle vollständig, eine Reihe = `doc-121449`) → `doc-121606.series.json`.
  O1(T4, T4) = **14.2166**; O1(T4+24h) = 1.7000.
- Step 5 nach dem Lauf: `12:26:20.621 … Metered irrigation: zone 9 done`; `run_log[0]` = {ts 12:26:20.621134+02:00,
  trigger schedule, planned_s 255, actual_s 255, volume_l 12.75, result completed}; `bucket` -14.241244820027482.
  Keine 429 seit 09:10:43 (Ortszeit).

| Kriterium | Zeit (UTC) | Rohzitat / Wert | O1 | O2 | Urteil |
|---|---|---|---|---|---|
| B4 | 10:22:00.489 | Kette Executing → Committing pre-run (zones: 9) → Calculating zone 9 in derselben Sekunde; `last_calculated` = T4; X₄ 14.22 / 14.216598; planned_s 255 = d₄; Eimer -14.2412 vs g₄ -14.2166 (Δ 0.025) | O1(T4,T4) 14.2166; O1(T4+24h) 1.7 (Abstand 12.52) | 14.22 | **bestanden** |

## Task 9 — Phase 3 (B5, Live-Schätzung), 2026-10-11

- Step 1: `autocalcmode` `fixed_time`, `live_estimate_enabled` true (zurückgelesen; Gewichtung an, Intervall "10").
  `set_bucket` A = −27 (Wassermarke 12:27:59.277).
- Step 2 Probe: erste Lesung (as_of 12:24:49, vor dem Einschalten) `live_deficit` -20.98 ohne `forecast_credit` →
  ein Update abgewartet; zweite Lesung 12:35:29: `available` true, `method` daily_mirror, `live_deficit` **-26.97**,
  `live_duration` 505, `forecast_credit` **1.7**, `as_of` 12:34:50.031. Die 1.7 = Gutschrift für den NÄCHSTEN
  P61-Lauf (P61 noch 12:22 → morgen 10:22 UTC; Fenster enthält die 1.7 mm vom 13.10. 08–09 UTC); 505 =
  (26.97 − 1.7)·20 = 505.4 ✓ — Live-Pfad verankert am Resolver.
- **Ausführungshinweis T5:** Das Outlook liefert die zwischengespeicherte Schätzung (Erneuerung im Zyklus,
  `live_estimate.py:1769-1782`); der Dispatch rechnet frisch mit `run_start=utcnow()` (`irrigation.py:2352-2354`).
  Damit C₅ (gelesen bei T5 − 90 s) denselben Anker hat wie der Dispatch, muss zwischen P61-Änderung und Lesen ein
  Zyklus liegen → **T5 = 12:47 Ortszeit (10:47 UTC)** statt 12:42 (Plan: nächste volle Minute ≥ jetzt + 6 min;
  „≥ jetzt + 6 min“ erfüllt). Beleg: nach dem Speichern (12:36:12) zeigte das Outlook weiter `forecast_credit` 1.7.
- Step 3: P61 `start_time` 12:47 (`success`); Sicherheits-Rücklesen: nur P61, `zones` "9", `next_run_utc`
  10:47 UTC, Zone 9 `classic` auf `input_boolean.hasi61_a` ✓.
- Step 4 (12:45:34.163, T5 − 86 s): Outlook `zone_estimates["9"]`: `live_deficit` **D₅ = -26.92**,
  `forecast_credit` **C₅ = 14.008333333333331**, `live_duration` **L₅ = 258**, `as_of` 12:44:49.974,
  `precip_since` 0.0948, `et_since` 0.0186. `upcoming_runs`: P61 10:47 UTC.
  Dokument: Schub 12:44:49.651–12:44:50.507 (21, alle vollständig, eine Reihe = `doc-121449`) →
  `doc-124450.series.json` (Prüfsumme `[168, 301058251200, 16.2]`). O1(T5, 12:45:34) = **14.0083**.
  Nachrechnung: |D₅ + C₅|·20 = 258.23 → 258 = L₅; |D₅|·20 = 538.4.
- Step 5 Belege (Ortszeit): `12:47:00.053 INFO … Executing recurring schedule: HASI61`;
  `12:47:00.069–.078 DEBUG … no scheduled run resolves for zone 0…7, 10` (frische Schätzung aller Zonen beim
  Dispatch, `irrigation.py:2352`; für Zone 9 keine Zeile — P61 löst auf); `12:47:00.336 INFO … Live-estimate
  watering: zone 9 255s → 258.0s (live deficit -26.93)`; `12:47:05.337 … Metered (timed) irrigation: zone 9 for 258s`;
  `12:51:23.422 … zone 9 done — 12.90 L in 258s`. `run_log[0]` = {ts 12:51:23.422762+02:00, trigger schedule,
  planned_s 258, actual_s 258, volume_l 12.9, result completed}.

| Kriterium | Zeit (UTC) | Rohzitat / Wert | O1 | O2 | Urteil |
|---|---|---|---|---|---|
| B5 | 10:45:34 / 10:47:00.336 | C₅ 14.008333; L₅ 258 < 538 (D₅ allein); Y 258 = planned_s = L₅; mit D′ -26.93: |D′ + C₅|·20 = 258.43 → 258 | O1(T5, Lesezeit) 14.0083 | — | **bestanden** |
| (i) Regen außerhalb zählt nicht | — | B2a: Regen vor T1 nicht in der Gutschrift (11.3333 statt O1(E) 12.0186, Abstand 0.685); B4: Regen nach T4+24h (1.7) nicht enthalten (Abstand 12.52); B2b umgekehrt mit Fallback-Anker | — | — | **bestanden** |

## Task 10R — Rückbau (2026-10-11, HA-Test)

- Step 1 (≈ 12:53): P61 `schedule_be72fcbe` gelöscht; `schedule_ec886994` / `schedule_1fac4605` `enabled: true`;
  Zonen 9/10 entfernt (Zonenliste 0–8); Konfiguration: Gewichtung aus, Schwelle 2, `fixed_time`, Live aus,
  Intervall "60" (vier Felder) — alle `success`.
- Step 2: `input_boolean.hasi61_a` / `_b` gelöscht.
- Step 3: `coordinates_save` `manual_coordinates_enabled: false` → Rücklesen `manual_*` false/null →
  `coords-after.json`; Eintrag `loaded`; INFO `12:53:06.406` und `12:53:13.045` „Scheduled auto update time interval
  for each 1:00:00“ (Konfiguration bzw. Neuladen).
- Step 4: alle Test-Logger und `PirateWeatherClient` → `warning`.
- Step 5: Vergleich → `{'days_since_last_irrigation': (1, 0), 'autoupdateinterval': ('10', '60')}`, Zeitpläne
  `True`, Zonen `True`, Koordinaten `True`. `autoupdateinterval` = erwartete Abweichung (E6).
  `days_since_last_irrigation` = Laufzeitzähler, von den Testläufen zurückgesetzt (`12:22:05.547 DEBUG …
  skip_conditions: Reset days since last irrigation to 0`), wirkungslos bei `days_between_irrigation` 0 — nicht
  künstlich zurückgesetzt (wäre gefälschter Zustand).
- Step 6: HA-Test-Neustart angekündigt und ausgelöst (≈ 12:56 Ortszeit).
- Nach dem Neustart (12:57 Ortszeit): Verteiler-Entitäten wieder verfügbar (`binary_sensor.…gardena1_commissioned`
  on, `sensor.…gardena1_current_outlet` 1, Ausgangs-Sensoren Test1–4; nur `button.…test_run` `unavailable` = Gate
  bei `commissioned` an, b9); Pegel `irrigation_plus` WARNING; WS config `autoupdateinterval` "60", Gewichtung aus,
  `manual_coordinates_enabled` false; Eintrag `loaded`; Vorhersage am Heimatort wieder `available`, 12.–14.10. 0 mm.

## Ende-zu-Ende-Kriterium (Spec §9, Rev. 2)

1. B1–B5 und (i) bestanden — Tabellenzeilen in Task 6 (B1, B2a, B2b, Dauer/Ziel), Task 7 (B3), Task 8 (B4),
   Task 9 (B5, (i)). ✓
2. Rückbau-Vergleich: einzige Konfig-Abweichungen `autoupdateinterval` "10" → "60" (E6, erwartet) und
   `days_since_last_irrigation` 1 → 0 (Laufzeitzähler, begründet in Task 10R); Zeitpläne, Zonen, Koordinaten gleich. ✓
3. Imperial-Probetest gelaufen, Verdacht E3 **bestätigt** (Abschnitt E3). ✓

Nicht beobachtet (für den Abschluss-Kommentar): `precipitation_forecast_days` > 1, `hourlycalculation: true`,
Verteiler-Mitglieder, imperial live; (ii) Lauf mit Gutschrift 0 trotz Regen in der Vorhersage nicht gefahren.
Der Test lief am Ersatzort Brest (manuelle Koordinaten), nicht am Standort von HA-Test.
