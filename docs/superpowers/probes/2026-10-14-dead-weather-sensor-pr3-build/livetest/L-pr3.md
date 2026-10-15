# Live-Test PR 3 „stummer Wettersensor — Stundenpfad und Live-Schätzung“ auf HA-Test

Plan: `docs/superpowers/plans/2026-10-14-dead-weather-sensor-pr3.md`, Task 11. Spec: `…/specs/2026-10-14-dead-weather-sensor-pr3-design.md`,
Abschnitt *Ende-zu-Ende-Kriterium (HA-Test)*. Zeiten Ortszeit HA-Test (Europe/Berlin, UTC+2), sofern nicht anders
vermerkt. Keine IP, keine Schlüssel (⚠️ `ha_get_integration` gibt in `options` den Pirate-Schlüssel aus — nie übernehmen).
HA-Prod unberührt.

## Version und Installation (2026-10-14 abends)

- Pre-Release **v2026.10.14b1** (Tag → `a50b74f9`, production = `a50b74f9`, 0 behind / 35 ahead = Branding + upstream
  PR 194 + PR 2 (18, inkl. L1-Fix) + PR 3 (14) + Build). ZIP aus dem SHA, 205 Einträge, Download sha256 `b2a9cc40…`
  gleich, HTTP 200; CI production + Tag grün.
- **Vorher** (Diagnostics `data.store.config`, 22:2x): installiert `v2026.10.13b1`, **`hourlycalculation: false`**,
  **`live_estimate_enabled: false`** → beim Aufräumen genau so zurück.
- HACS `update_information` + `download v2026.10.14b1` (22:31). Dateigrößen auf HA-Test vor dem Neustart = neues ZIP
  (`const.py` 73907, `sensor_liveness.py` 31741, `live_estimate.py` 106113; 13b1: 73942 / 29340 / 100880).
- Neustart HA-Test (angekündigt) 22:31:31. Danach: Geräte `sw_version` `v2026.10.14b1`, Eintrag `loaded`, System-Log
  frisch (ab 22:32), kein Eintrag von `irrigation_plus`.
- Keine `hasi_livetest`-Entitäten vorhanden (PR-2-Aufbau ist abgeräumt). Sonne 15.10.: Aufgang 07:51, Untergang 18:44.

## Aufbau (offen, 15.10. tagsüber)

Nach Spec: Stundenrechnung an, Live-Schätzung an, PyETO mit gemessener Sonne (`solrad_behavior = 3`),
`forecast_days = 0`, Koordinaten gesetzt; YAML-MQTT-Gerät unter `hasi_livetest/…` ohne Discovery (Broker = HA-Prod!),
`force_update: true`, Temperatur, Feuchte, Wind, Sonne; pausierende Gruppe + Vergleichsgruppe *behalten*; Wegwerf-Zonen
auf eigener Gruppe (Zonen 0/1 nie auf `service`). Skripte: `issue8-pr3-work\livetest\s_*.py` + `mqtt-e.yaml` (14.10.
nachts geschrieben, noch nicht gelaufen); Ausweich-Client bei MCP-Ausfall `issue8-pr2-work\livetest\run_code.py`.
Panel-Standardwerte beim Anlegen der Zone mitschicken (in `s_setup_zones.py`).

Zeitvorschlag: einmal senden ≈ 09:30 (= Ausfallbeginn T0), direkt danach `update` + `calculate`
(Wasserzeichen W), Sperre ab T0 + 3 h ≈ 12:30, Rückkehr ≈ 13:00, **Commit erst nach der schließenden Prüfung**
(Diagnostics: alle vier `end` gesetzt, Prüftakt 5 min). Live-ET zwischen 12:30 und 13:00 beobachten (Soll 2).

~~Soll 3 vorab: Anteil ≈ (T0 + 3 h − W) / (Commit − W)~~ — **falsch**, siehe Herleitung: Die Formel lässt die gültige
Zeit zwischen Rückkehr und Commit weg (Beispiel unten: 83 % statt 86 %).

## Herleitung Soll 3 (aus dem Code, 2026-10-14 22:5x, Worktree `issue8-pr3-work\wt` = `c21478c8`)

Pfade relativ zu `custom_components/irrigation_plus/`.

1. **Ausfall-Eintrag.** `advance_outages` (`sensor_liveness.py:292-343`) öffnet einen Eintrag, sobald
   `now − last > 3 h` (strikt), mit `start` = **letztes Lebenszeichen** (`:340`). Das letzte Lebenszeichen ist
   `max(eigenes last_reported, last_reported der Geschwister-Sensoren am selben Gerät)` (`last_sign_of_life`, `:73-90`;
   Geschwister = `sensor`/`binary_sensor` desselben Entries, `:397-433`). Liegen alle vier Sensoren an **einem**
   MQTT-Gerät, haben alle vier Einträge denselben `start` T0 = der späteste der vier Sende-Stempel.
   Geschlossen wird bei der ersten Prüfung nach der Rückkehr, mit `end` = `recovered` = eigenes `last_changed` des
   Feldes (`first_report_after`, `:93-110`; `:327-333`) → je Feld eine eigene Rückkehr R_p, ms auseinander (wie PR 2).
2. **Sperre.** `blocked_spans` (`:201-220`): je Feld `[max(start + 3 h, ws), min(end, we))`; ein offener Ausfall sperrt
   bis `we`. `zone_blocked_spans` (`:238-268`) mit ws = `last_consumed_at` der Zone (Wasserzeichen W), we = `now` des
   Commits (`calculation.py:432-445`, Aufruf `:666`); Regenzähler (`delta`) nie.
3. **Anteil.** Stundenform lief → Pflichtmenge `HOURLY_ROW_REQUIRED` = Temperatur, Feuchte, Wind, Sonne
   (`weather_aggregate.py:71-76`; Wahl `required_sensor_fields(…, hourly=True)`, `calculation.py:81-94`, `:1300-1302`).
   `share = valid_share(blocked, required, W, C)` (`calculation.py:1303-1311`) = Fensterlänge minus **Vereinigung** der
   Sperren dieser vier Felder, geteilt durch die Fensterlänge (`sensor_liveness.py:223-235`).
4. **Prozentwert.** `_silent_sensor_explanation` (`calculation.py:1910-1957`): `round(share × 100)` (Python: bei
   genau ,5 zur geraden Zahl), bei `share > 0` mindestens 1, höchstens 99. Satz 1 je Sperre, wie sie angezeigt wird
   (`%Y-%m-%d %H:%M`, abgeschnitten, nicht gerundet), Felder als Menge (L1-Fix aus PR 2) → **ein** Satz, wenn alle vier
   Rückkehren in dieselbe Minute fallen; damit wird L1 hier zugleich live nachgeprüft.
5. **Stundenform muss laufen**, sonst gilt die Tagesform-Pflichtmenge (Temperatur, Taupunkt, Wind, Druck) und Satz 3
   fehlt: `_hourly_et_for_zone` (`calculation.py:937-1047`) braucht `hourlycalculation` an, `solrad_behavior` = 3
   (`DontEstimate`), `forecast_days` = 0, Koordinaten, ein Fenster ≤ 168 h, jedes Pflichtfeld mindestens einmal gelesen.
   Satz `water-balance-substepped` (`:1620-1629`) nur mit Teilschritten: `replayed_balance_applies` (Stundenrechnung an +
   PyETO, `:162-189`) und Abgleich der Niederschläge (`:1100-1111`; ohne Niederschlagsfeld 0 = 0).

**Formel (Soll 3):**

```
Sperre  = [T0 + 3 h, max_p R_p)          p ∈ {Temperatur, Feuchte, Wind, Sonne}, alle aus Diagnostics
Anteil  = 1 − (max_p R_p − (T0 + 3 h)) / (C − W)
Prozent = round(100 × Anteil), gehalten auf 1 … 99
```

W = `last_consumed_at` der Zone vor dem Commit, C = `last_consumed_at` danach (`calculation.py:699` schreibt `now`).
C steht erst nach dem Commit fest → **vorab mit dem geplanten C rechnen** und eintragen; die Abhängigkeit ist klein
(Beispiel: 0,001 Prozentpunkte je Sekunde), entscheidend nur nahe einer ,5-Grenze — dann mit dem echten C nachrechnen und
beides notieren.

**Beispiel mit dem Zeitvorschlag:** T0 09:30:00, W 09:31:00, Sperre 12:30:00–13:00:00, C 13:06:00 → Fenster 215 min,
gesperrt 30 min, Anteil 185/215 = 0,8605 → **86 %**. (Alte Formel: 179/215 = 0,8326 → 83 %.)

**Fallen für den Ablauf:**
- Commit **vor** der schließenden Prüfung: der Ausfall ist noch offen, sperrt bis C, Satz 1 endet bei C, der Anteil
  fällt. Also nach der Rückkehr Diagnostics lesen, bis alle vier `end` gesetzt sind, dann erst `calculate`.
- Rückkehr nicht auf eine Minutengrenze legen (z. B. hh:mm:20 senden), sonst zwei Sätze mit verschiedenem Ende — das wäre
  korrekt, prüft L1 aber nicht.
- Alle vier Sensoren an EINEM Gerät; bei getrennten Geräten hätte jedes Feld ein eigenes T0, Sperrbeginn = frühestes.

## Soll (vorab rechnen und hier eintragen)

| # | Soll | Ist |
|---|---|---|
| 1 | Während der Sperre Hinweis-Variante „pausiert“, obwohl die Stundenrechnung an ist | ✅ |
| 2 | Live-ET seit dem Anker wächst ab T0 + 3 h nicht mehr (nur Drainage bewegt den Eimer); Methode `hourly_sensor`, keine Wetterdienst-Stufe | ✅ |
| 3 | Erklärung nach dem Commit: **ein** Satz „Keine Werte von Feuchtigkeit, Sonnenstrahlung, Temperatur, Windgeschwindigkeit von ‹T0 + 3 h› bis ‹max R_p› (Sensor stumm).“ (Reihenfolge = sortierte Feldschlüssel, `de.json`), Prozent = Formel oben (vorab mit geplantem C; Zeitvorschlag → 86 %), Satz `water-balance-substepped` | ✅ 56 % (Lauf mit verlängerter Sperre) |
| 4 | Live-Eimer direkt nach dem Commit = gebuchter Eimer (Toleranz Erkennungs-Latenz) | ✅ |
| 5 | Dieselbe Lage auf *behalten*: kein Satz, Hinweis im PR-1-Text | ✅ |

## Vorbereitung (14.10. ~22:50, HA-Test nur gelesen)

- Konfiguration: `hourlycalculation false`, `live_estimate_enabled false`, `continuousupdates false`, Auto-Update 60 min,
  Auto-Rechnung 23:00, Wetterdienst Pirate (Schlüssel nicht gelesen). Koordinaten: aus HA gesetzt, manuelle aus (Werte
  nicht ausgegeben).
- Module: 0 PyETO **ohne Konfiguration** (= Standard `solrad_behavior` 1, Schätzung aus Temperatur → Stundenform liefe
  NICHT), 1/2 Static. → eigenes Wegwerf-Modul PyETO mit `solrad_behavior "3"`, `forecast_days 0`.
- Gruppen 0/1 (*behalten*, nur Wetterdienst, keine Ausfälle); Zonen 0–8. Zeitpläne: „alle Zonen“ täglich mit Ende 20:27,
  „Zone 2“ 08:54 → keiner im Test-Fenster; Wegwerf-Zonen sind vor 20:27 wieder weg.
- Auffrischen der Live-Schätzung: `update_all_zones`, Commit und (neu PR 3) Öffnen/Schließen eines Ausfalls; ein
  Zonen-`update` frischt NICHT auf (`__init__.py:1466-1545` gegen `:1677-1680`). Zonen-`update` einer reinen
  Sensorgruppe ruft den Wetterdienst nicht; `update_all_zones` schon (ein Abruf für Gruppen 0/1).

## Ablauf 15.10. (Skripte in `livetest\`, Sandbox `ha_manage_custom_tool` auf **HA-Test**)

| Zeit | Schritt | Werkzeug |
|---|---|---|
| ~09:00 | Upstream-Runde | `gh` |
| ~09:05 | `mqtt`-Schlüssel = `mqtt-e.yaml` (Gerät „HASI Livetest E“, 4 Sensoren, `force_update`, kein `retain`, keine Discovery); Vorschau + Token (+ `BestPracticeKey`), `mqtt.reload`; Entitäts-IDs per `ha_search` bestätigen (erwartet `sensor.hasi_livetest_e_livetest_e_{temperature,humidity,wind,solar}`, sonst Skripte anpassen) | `ha_config_set_yaml` |
| ~09:10 | Modul, Gruppen *pausieren*/*behalten*, Zonen; danach Stundenrechnung + Live-Schätzung an | `s_setup_module.py`, `s_setup_groups.py`, `s_setup_zones.py`, `s_flags_on.py` |
| **09:30 T0** | einmal senden (15,0 °C / 70 % / 2,0 m/s / 350 W/m²) | `s_publish.py` |
| T0 + 1 min | Stempel lesen (T0 = spätester `last_reported`), dann Zonen-`update` + `calculate` → W | `s_state.py`, `s_anchor.py` |
| ~12:20 | **R1:** auffrischen, Live lesen (Methode, `et_since`, `as_of`) | `s_refresh.py`, `s_state.py` |
| 12:3x | erste Prüfung nach T0 + 3 h öffnet die Ausfälle → **Soll 1** (Hinweise P/K), **R2:** Live lesen OHNE eigenes Auffrischen (`as_of` nach dem Öffnen belegt G11) | `s_state.py` |
| ~12:55 | **R3:** auffrischen, Live lesen → **Soll 2** | `s_refresh.py`, `s_state.py` |
| **≈ 13:00:20** | Rückkehr: dieselben Werte senden (nicht auf eine Minutengrenze) | `s_publish.py` |
| 13:0x | Prüfung schließt → vier `end` je Gruppe; **Soll 3 vorab** mit geplantem C rechnen und hier eintragen | `s_state.py` |
| danach | auffrischen, Live lesen (L), sofort Commit beider Zonen → Erklärung, Eimer B, C → **Soll 3, 4, 5** | `s_refresh.py`, `s_state.py`, `s_commit.py` |
| danach | Aufräumen | `s_cleanup.py`, `ha_config_set_yaml remove`, `mqtt.reload`, `ha_remove_entity`, `ha_remove_device` |

**Soll 2 konkret:** P: Methode `hourly_sensor` in R1–R3; `et_since` R2 = R3 (die Stunde 12 bucht in beiden nur
12:00–12:30, Zeilen-Mittelpunkt = ganze Stunde, `weather_aggregate.py:1286-1308`; Abweichung nur im Fließkomma-Rest);
R1 kleiner als R2. Gegenprobe K: `et_since` wächst von R2 nach R3.
**Soll 4 konkret:** L (Live-Eimer P, aufgefrischt unmittelbar vor dem Commit, Ausfall da schon geschlossen) = B (Eimer P
nach dem Commit); Toleranz = ET zwischen `as_of` und C (wenige Sekunden, deutlich unter 0,01 mm). Dasselbe für K als
Gegenprobe. Ein Live-Eimer, der die Sperre nicht schneidet, läge um die ET von 12:30–13:00 daneben.

## Ablauf (Ist, 15.10.)

- **09:00 Upstream-Runde** (Fenster ab 14.10. 20:44 UTC): leer; #197 Kopf `6fa424e8`, 0 Reviews, 0 Checks;
  `upstream/master` `6a40e083`.
- HA-MCP der Sitzung weg (Prod + Test) → alles über `tools\mcp_test.py` + `run_code.py` bzw. `yaml_step.py` (nur
  HA-Test). Umlaute/„°“ im Client als Mojibake (Antwort als Latin-1 gelesen), gesendet wird JSON mit Escapes.
- **09:01:23** `mqtt`-Schlüssel (Vorschau, Diff nur der neue Block, Token, `config_check: ok`), `mqtt.reload` → Gerät
  „HASI Livetest E“ (`8d2701bf…`, MQTT-Entry `01KWE5TY…`) mit `sensor.hasi_livetest_e_livetest_e_{temperature,humidity,
  wind,solar}`, alle `unknown` (Wind zeigt km/h).
- Modul **3** PyETO `{"coastal": false, "solrad_behavior": "3", "forecast_days": 0}`; Gruppen **2** „Livetest PR3 Pause“
  (`pause`) und **3** „Livetest PR3 Keep“ (`keep`), je Temperatur/Feuchte/Wind/Sonne = E, Rest `none`; Zonen **9**
  (Gruppe 2) und **10** (Gruppe 3), Modul 3, 10 m², 10 l/min, `automatic`, Panel-Standardwerte.
- **09:01:59** `hourlycalculation true`, `live_estimate_enabled true` (Rest unverändert).
- 09:02:11 Stand: keine Ausfälle, keine Hinweise; Zonen tragen schon ein Wasserzeichen vom Anlegen (9: 09:01:53.272252,
  10: 09:01:53.293936), `last_calculated` leer. Live-Sensoren heißen nach gelöschten Zonen gleicher Nummer
  (`sensor.irrigation_plus_lt_wegwerf_zone_live_deficit` = Zone 9, `sensor.irrigation_plus_hasi61_b_live_deficit` =
  Zone 10; über `unique_id` `irrigation_plus_<id>_live_deficit` gefunden), `not_computed_yet`.
- **09:30:11 T0 gesendet** (15,0 °C / 70 % / 2,0 m/s → HA 7,2 km/h / 350 W/m², nicht retained). `last_reported`
  (UTC): Temperatur 07:30:11.730443, Feuchte .736421, Wind .739918, Sonne **.744301** → erwartetes T0 = 09:30:11.744301
  Ortszeit (spätester Stempel am Gerät; der Ausfall-Eintrag bestätigt es später).
- **09:30:25 Anker:** Zonen-`update` 9/10, `calculate` 9/10 → **W9 = 09:30:25.800856**, **W10 = 09:30:25.960304**;
  beide in der Stundenform („Summe der stündlichen FAO-56-et0“) mit Teilschritten (Satz `water-balance-substepped`,
  1 Schritt), Eimer 9 −0,067137, 10 −0,067142, keine Ausfall-Sätze. Rohausgabe `anchor-0930.json`.
- Erwartet: Sperre ab **12:30:11.744301**; die erste Prüfung danach (Takt 5 min) öffnet die Ausfälle.
- 09:30:4x Live noch `not_computed_yet` (die Einzelzonen-Rechnung frischt nicht auf). **09:31:02 Probe-Auffrischung**
  `update_all_zones` → beide Zonen `hourly_sensor`, `replayed`, `et_since` 0,0015, `live_deficit` −0,07, `as_of`
  09:31:03.073364. Der Weg funktioniert.
- **Auflösung:** Der Schätz-Cache rundet `live_deficit` auf 2, `et_since` auf 4 Nachkommastellen (WS
  `irrigation_outlook` = Sensor-Attribute). **Soll 4 daher zweifach:** grob `live_deficit` = round(B, 2); fein
  Eimer(W) − `et_since` (+ Niederschlag − Drainage, hier 0) = B auf ≈ 0,0002 mm (Rundung 0,00005 + ET der Sekunden
  zwischen `as_of` und C).
- ⚠️ **Zeitplan verpasst:** Der Hintergrund-Timer für R1 lief um 12:20:20 ab (Ausgabedatei), die Meldung erreichte die
  Sitzung nicht; nichts geschah bis zur Rückfrage des Users um 14:54. R1–R3 und die Rückkehr 13:00:20 entfielen. R1/R2
  aus dem Recorder nachgeholt (WS `history/history_during_period`, `history-live.json`).
- **12:32:06 Ausfälle geöffnet** (Prüfung; Hinweise erstellt 10:32:06.0179 UTC): Gruppen 2 und 3 je vier Einträge,
  alle `start` **09:30:11.744301** (= spätester Stempel am Gerät, wie hergeleitet), `end null`. Hinweise:
  `weather_sensor_stale_2` → **`weather_sensor_stale_paused`** (Stundenrechnung an), `weather_sensor_stale_3` →
  `weather_sensor_stale` (*behalten*, PR-1-Text); `since` „2026-10-15 09:30“.
- **Live-Verlauf** (Recorder, `et_since` / `as_of`), Zone 9 *pausieren* | Zone 10 *behalten*, durchgehend `hourly_sensor`,
  `replayed`:

  | `as_of` | Z9 `et_since` | Z10 `et_since` | Anlass |
  |---|---|---|---|
  | 09:31:03.07 | 0,0015 | 0,0015 | Probe `update_all_zones` |
  | 09:32:06.30 | 0,0040 | 0,0040 | stündliche Abfrage |
  | 10:32:06.33 | 0,1533 | 0,1533 | stündliche Abfrage |
  | 11:32:06.35 | 0,3314 | 0,3314 | stündliche Abfrage |
  | 12:32:06.018 | 0,5227 | 0,5294 | Öffnen der Ausfälle (G11-Auffrischung) |
  | 12:32:06.287 | 0,5128 | 0,5189 | stündliche Abfrage (neue Pufferzeile) |
  | 13:32:06.33 | 0,5128 | 0,7096 | stündliche Abfrage |
  | 14:32:06.30 | 0,5128 | 0,8994 | stündliche Abfrage |
  | 14:55:05.10 | 0,5128 | 0,9715 | eigenes `update_all_zones` |

- **Befund-Kandidat B1 (unbestätigt):** Zwischen 12:32:06.018 und .287 (0,27 s, einzige Änderung: Pufferzeile der
  stündlichen Abfrage mit denselben eingefrorenen Werten) fallen BEIDE Zonen um ≈ 0,01 mm (Z9 −0,0099, Z10 −0,0105).
  Für Z10 erklärbar (Stunde 12 bekommt eine Sonnen-Probe statt der Klarheitsquote). Für Z9 liegt die Zeile in der Sperre
  und dürfte nach G5 (Spec 2.3) weder als „gelesene Stunde“ noch als Quote zählen — die gleich große Änderung spricht
  dafür, dass sie es doch tut. Nach dem Test lokal mit diesem Puffer prüfen (mit/ohne Zeile), erst dann urteilen.
- **14:58:15 Rückkehr** (User-Entscheidung Option 1: jetzt zurück statt Neustart morgen; Abweichung von der Spec: Stille
  ≈ 5,5 h statt 3,5 h, Sperre ≈ 2,5 h statt 30 min, weiter bei Tageslicht). `last_reported` Ortszeit: Temperatur
  14:58:15.335651, Feuchte .339092, Wind .343499, Sonne **.347198**.
- **Soll 3 vorab (vor dem Commit eingetragen):** Sperre 12:30:11.744301 → 14:58:15.347198 = 2 h 28 min 3,6 s; W9
  09:30:25.800856. C = 15:03:00 → 55,48 % → 55; C = 15:03:30 → 55,55 % → 56 → **,5-Grenze bei ≈ 15:03:05**, daher
  Commit nach 15:04:00: **Soll 56 %** (15:04 → 55,61; 15:10 → 56,40). Satz 1 erwartet einmal: „… von 2026-10-15 12:30
  bis 2026-10-15 14:58 (Sensor stumm).“ — vorausgesetzt, die `end`-Stempel = obige `last_reported` (nach dem Schließen
  prüfen).
- **15:02:06 Prüfung schließt** (Monitor-Abfrage 15:02:22): beide Gruppen, alle acht Einträge `end` = eigene Rückkehr
  (Temperatur 14:58:15.335651, Feuchte .339092, Wind .343499, Sonne .347198) = `last_reported` oben; Hinweise danach
  leer.
- **15:04:07 Auffrischen** (`update_all_zones`), Live vor dem Commit (`as_of` 15:04:07.404123): Z9 `et_since` 0,5410,
  `live_deficit` −0,61; Z10 0,9993 / −1,07; beide `hourly_sensor`, `replayed`. Rohausgabe `pre-commit-*.json`.
- **15:04:09 Commit** Zonen 9/10 (Rohausgabe `commit.json`): **C9 = 15:04:09.808637**, C10 = 15:04:09.986161.
  - Z9: Δ −0,5410860, Eimer −0,6082228. Erklärung: „… von -0.54. **Keine Werte von Feuchtigkeit, Sonnenstrahlung,
    Temperatur, Windgeschwindigkeit von 2026-10-15 12:30 bis 2026-10-15 14:58 (Sensor stumm). Verdunstung für 56 % des
    Zeitraums gebucht.**Der alte Vorrat war -0.07. … **Die Wasserbilanz wurde über den Zeitraum nachgerechnet** …
    Anzahl der Schritte: 7.“ Nachgerechnet mit dem echten C: C − W = 20 024,008 s, Anteil 0,55635 → 56 %.
  - Z10: Δ −0,9994664, Eimer −1,0666086; Erklärung ohne Ausfall- und Anteilssatz, Teilschritte 7.
  - Soll 4 fein: Z9 Eimer(W) − `et_since` = −0,0671368 − 0,5410 = −0,6081368 gegen B −0,6082228 → **8,6·10⁻⁵ mm**; Z10
    −1,0664422 gegen −1,0666086 → **1,7·10⁻⁴ mm** (ET der 2,6 s bis C10 ≈ 1,3·10⁻⁴ + Rundung 5·10⁻⁵). Grob: round(B, 2)
    = `live_deficit` in beiden Zonen.
- Nach dem Commit: Puffer der Gruppen 2/3 bis auf die Randzeile 15:04:07 geleert (`records.json`; Sonne gespeichert als
  30,24 MJ/Tag/m² = 350 W/m² × 0,0864) → B1 lokal mit nachgebautem Puffer prüfen.

## Ergebnis

| # | Ergebnis |
|---|---|
| 1 | ✅ Hinweis Gruppe 2 = `weather_sensor_stale_paused` bei `hourlycalculation true` (erstellt 12:32:06) |
| 2 | ✅ Z9 `et_since` ab dem Öffnen 0,5128 bei 12:32:06.287, 13:32, 14:32, 14:55 (davor 0,0015 → 0,5227); Z10 wächst weiter (0,5189 → 0,9715); durchgehend `hourly_sensor`, keine Wetterdienst-Stufe. Lesungen R1/R2 aus dem Recorder statt live (Timer-Ausfall) |
| 3 | ✅ ein Satz 12:30 → 14:58, **56 % = Soll** (vorab mit geplantem C eingetragen, mit echtem C bestätigt), Satz `water-balance-substepped` (7 Schritte); L1 live bestätigt |
| 4 | ✅ Live-Eimer vor dem Commit = gebuchter Eimer (fein 8,6·10⁻⁵ mm; Gegenprobe Z10 1,7·10⁻⁴ mm) |
| 5 | ✅ Z10 (*behalten*) ohne Satz; Hinweis `weather_sensor_stale` (PR-1-Text) während des Ausfalls |

Abweichung von der Spec: Stille 5 h 28 min statt 3,5 h, Sperre 2 h 28 min statt 30 min (Timer-Ausfall, User-Entscheidung
„jetzt zurück“).

## B1 aufgeklärt (15:10–15:20): kein PR-3-Fehler, vorbestehend auf upstream/master

Probe `b1_probe.py` (PR-3-Code `c21478c8`) und `b1_probe_upstream.py` (`6a40e083`), Puffer aus den Live-Stempeln
nachgebaut (konstante Werte, Koordinaten genähert — qualitativ):

1. **G5 hält:** voller Zeilenbau `hourly_eto_priced` ab W, *pausieren*, mit/ohne die Zeile 12:32 in der Sperre → gleiche
   ET (Differenz 0,0). *behalten*: −0,01063 (Stunde 12 bekommt die Probe, Sonne 1,446 → 1,26 MJ/m²/h) = live −0,0105.
2. **Ursache des Z9-Sprungs ist der Übertrag `_HourlyCarry`:** nach der Auffrischung 12:32:06.018 (Übertrag wegen der
   neuen Ausfall-Einträge verworfen, voll gerechnet) rechnet die nächste nur ab der vollen Stunde 12:00 neu
   (`live_estimate.py:779-806`). Ab 12:00 zählt der fortgeschriebene Wert (Randzeile) als Probe der Stunde 12 → Sonne
   **gehalten** (1,26), während die volle Rechnung — und der Commit — eine Stunde ohne eigene gültige Probe aus der
   **Klarheitsquote** auffüllt (1,446). Probe: Stunde 12 voll 0,10579, ab 12:00 0,09580 → −0,00999 = live −0,0099.
3. **Vorbestehend:** ohne jede Sperre, Stunde ohne Sonnen-Probe → voll 0,11248, ab 12:00 0,10186, auf PR-3-Code UND auf
   `upstream/master` `6a40e083` identisch. Der Übertrag steht upstream mindestens seit `552dc4ae` (2026-09-04).
4. **Warum Soll 4 trotzdem stimmte:** Das Schließen der Ausfälle (15:02:06) änderte die Einträge → Übertrag verworfen
   (G11) → Stunde 12 wieder voll gerechnet. Recorder: Z9 0,5128 → 0,5344 (+0,0216 = ET 14:58:15–15:02:06 ≈ 0,012 +
   Rückkorrektur 0,0099); Z10 nur +0,0212 (ET). Ohne Anlass zum Verwerfen (Gruppe *behalten*, kein Ausfall) bleibt die
   Abweichung bis zum nächsten Commit stehen: Live-Eimer ≠ Commit in Stunden ohne eigene Sonnen-Probe (z. B. seltene
   Abfrage, Totband-Sensor, nachts egal, mittags bis ≈ 0,01 mm je Stunde).
5. Kein Issue dazu, weder `Eifel-Joe` noch `JustChr` (Suche „carry“, „clearness“, „partial hour“, „live estimate drift“).
   → Kandidat für ein neues Fork-Issue (Text zur Freigabe); nicht Teil von PR 3.

## Aufräumen (15.10. 15:05–15:07, erledigt)

- Zonen 9/10, Gruppen 2/3, Modul 3 per Konfig-Views `remove`; `hourlycalculation false`, `live_estimate_enabled
  false` (Rohausgabe `cleanup1.json`). Übrig: Zonen 0–8, Gruppen 0/1 (`keep`), Module 0–2.
- `mqtt`-Schlüssel entfernt (Vorschau, Diff nur der Block, Token, `config_check: ok`, Datei 264 Bytes, 15:05:44),
  `mqtt.reload`; vier Entitäten per `ha_remove_entity` (4/4), Gerät „HASI Livetest E“ per `ha_remove_device`.
  Nichts retained gesendet → nichts zu leeren.
- Kontrolle (`final-check.json`): keine Geräte/Entitäten/Zustände mit „livetest“, keine `irrigation_plus`-Hinweise,
  keine Registry-Einträge `irrigation_plus_9_*`/`_10_*` mehr (die vorher verwaisten Namen `lt_wegwerf_zone`/`hasi61_b`
  früherer Tests sind mit den Zonen gegangen); Konfiguration `hourlycalculation false`, `live_estimate_enabled false`,
  `continuousupdates false`, 60 min, 23:00, Pirate — wie vorher. Schlüssel nie gelesen.

## Aufräumen (Plan, vor dem Test)

Gerät, Gruppen, Zonen und `mqtt`-YAML entfernen, retained leeren (falls benutzt), Registry-Reste löschen;
`hourlycalculation` und `live_estimate_enabled` zurück auf `false`; 60-min-Intervall und Pirate-Schlüssel unberührt.
