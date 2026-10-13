# Live-Test PR 2 „stummer Wettersensor — pausieren“ auf HA-Test — 2026-10-13

Plan: `docs/superpowers/plans/2026-10-12-dead-weather-sensor-pr2.md`, Task 11 (+ Kriterium 5 aus E1, im Chat
vorgeschlagen und mit „Weiter mit Task 11“ freigegeben). Zeiten Ortszeit HA-Test (Europe/Berlin, UTC+2), sofern nicht
anders vermerkt. Keine IP, keine Schlüssel. HA-Prod unberührt.

## Version und Installation

- HA-Test: **core-2026.10.0**, HA OS, Python 3.14.6 (gelesen 13.10. ~21:20 per `ha_get_system_health`).

- Pre-Release **v2026.10.13b1** (Tag → `77f041d2`, production = `77f041d2`, 0 behind / 19 ahead); ZIP aus dem SHA,
  Download sha256 `6072861c…` gleich, HTTP 200.
- HA-Test: HACS `update_information` + `download v2026.10.13b1` (17:11); `const.py` auf HA-Test: `VERSION =
  "v2026.10.13b1"`, geändert 17:11:21. Neustart HA-Test (angekündigt) ≈ 17:11. Danach: Integration `loaded`, Hub
  `sw_version` `v2026.10.13b1`; System-Log ohne Eintrag von `irrigation_plus`.
- Bestand nach dem Update: Gruppen 0 („Standard Sensorgruppe“) und 1 („My Sensor Group“) `on_silent_sensor: keep`.
- Konfiguration HA-Test (nur gelesen): `hourlycalculation: false`, `calctime 23:00` (`fixed_time`), Auto-Update alle 60 min.

## Aufbau (17:14–17:16)

- `configuration.yaml`: Schlüssel `mqtt` per `ha_config_set_yaml` (Vorschau + Token, `config_check: ok`), `mqtt.reload`.
  Alle Sensoren `force_update: true`.
  - Gerät „HASI Livetest A“: `sensor.hasi_livetest_a_livetest_a_temperature` (°C), `…_dewpoint` (°C), `…_wind`
    (m/s gesendet, HA zeigt km/h: 2,0 → 7,2), `…_pressure` (hPa).
  - Gerät „HASI Livetest B“: `sensor.hasi_livetest_b_livetest_b_rain` (mm, `total_increasing`).
- Gruppen per `api_post("/irrigation_plus/mappings")` (HTTP-View des Panels):
  - **2 „Livetest Pause“** (`pause`): Temperatur, Taupunkt, Wind (km/h), Druck von A; Rest `none`.
  - **3 „Livetest Keep“** (`keep`): dieselben Felder.
  - **4 „Livetest Rain“** (`pause`): nur Niederschlag = B (Sensor → Aggregat `delta`); Rest `none`.
- Zonen per `api_post("/irrigation_plus/zones")`, PyETO (Modul 0), 10 m², 10 l/min, `automatic`:
  **9 „Livetest Pause Zone“** (Gruppe 2), **10 „Livetest Pause Zone 2“** (Gruppe 2, für Kriterium 4),
  **11 „Livetest Keep Zone“** (Gruppe 3).
  - Befund beim Aufbau: `calculate` → HTTP 500, `TypeError … NoneType + float` in `calculation.py:1836`
    (`zone.get(ZONE_LEAD_TIME)` = None), weil die Zonen ohne die Standardwerte des Panels angelegt waren
    (Bestandscode, nicht PR 2). Nachgetragen wie `handleAddZone`: `duration 0, bucket 0, delta 0, explanation "",
    multiplier 1, lead_time 0, current_drainage 0`; danach rechnen alle drei.
- Werte: A 18,5 °C / 12,0 °C / 2,0 m/s / 1013,0 hPa, B 5,0 mm, einmal 17:14:50 (vor den Gruppen) und erneut
  **17:15:27,5** (letzte Meldung = t0), nicht retained, kein Sender danach.
- `update` + `calculate` der Zonen 9–11 → Wasserzeichen **W9 17:16:00.893525**, **W10 17:16:01.082159**,
  **W11 17:16:01.235715**; Erklärung ohne neuen Satz.

## Erwartung

| # | Erwartung |
|---|---|
| 1 | Nach der Rückkehr: Erklärung Zone 9 nennt Taupunkt, Luftdruck, Temperatur, Windgeschwindigkeit von t0 + 3 h bis zur ersten Meldung; Satz 2 = vorab gerechneter Anteil (ganze Prozent, 1…99). |
| 2 | Zone 11 (behalten): kein neuer Satz. |
| 3 | Offener Ausfall: Hinweis Gruppe 2 = `weather_sensor_stale_paused`, Gruppe 3 = `weather_sensor_stale`; Stundenrechnung an → Gruppe 2 `weather_sensor_stale`; wieder aus → `_paused`. |
| 4 | Stundenrechnung an, Rechnung Zone 10: kein neuer Satz. |
| 5 | Gruppe 4 (pausieren, nur Regenzähler stumm): Hinweis `weather_sensor_stale` (nicht `_paused`), WARNING „its last value is still used“. |

## Ablauf
- **17:23** erste Prüfung erfasst die Gruppen: `sensor_last_seen` A-Felder 17:15:27.531578, B 17:15:27.536757.
- **Unterbrechung:** Die HA-Test-MCP-Verbindung der Sitzung fiel weg (vor 20:50); weiter über den eigenen Client
  `tools\mcp_test.py` (nur HA-Test, Endpunkt aus `secrets\`, nie ausgegeben) mit `livetest\run_code.py`.
- **20:17:09 (t0 + 3 h 1 min 42 s): Ausfälle offen** — Gruppen 2 und 3 je vier Einträge (Temperatur, Taupunkt, Wind,
  Druck; `start 17:15:27.531578`, `end null`), Gruppe 4 einer (Niederschlag, `start 17:15:27.536757`).
  Hinweise (`repairs/list_issues`, erstellt 18:17:09 UTC):
  - `weather_sensor_stale_2` (Livetest Pause) → **`weather_sensor_stale_paused`** ✅
  - `weather_sensor_stale_3` (Livetest Keep) → `weather_sensor_stale` ✅
  - `weather_sensor_stale_4` (Livetest Rain, pausiert, nur Regenzähler) → **`weather_sensor_stale`** ✅ (Kriterium 5)
  WARNINGs 20:17:09.142 (Roh-Log): Pause viermal „… its values are no longer used, and where the calculation cannot do
  without them no evapotranspiration is booked while it is silent“; Keep viermal und Rain einmal „… its last value is
  still used“ ✅ (Kriterium 5, Log).
- **20:51:2x Kriterium 3:** Stundenrechnung per Konfig-View ein → Hinweis 2 = `weather_sensor_stale`, 3/4 unverändert;
  aus → Hinweis 2 = `weather_sensor_stale_paused` ✅. `hourlycalculation` danach `false` (= Stand vor dem Test).
- **20:51:50 Kriterium 4:** Stundenrechnung ein, Zone 10 rechnen (Wasserzeichen 17:16:01.08 → 20:51:50.03, Sperre im
  Fenster), Erklärung ohne „(Sensor stumm)“ und ohne Anteilssatz ✅; Stundenrechnung wieder aus (`false`).
- **20:52:00 Rückkehr:** A und B veröffentlichen dieselben Werte; `last_reported` Temperatur .184966, Taupunkt
  .190707, Wind .197112, Druck .203012, Regen .208408 (je eigene Meldung, ms auseinander).
- **20:57:09 Prüfung:** alle Ausfälle geschlossen, `end` = eigene Rückkehr je Feld (Temperatur 20:52:00.184966, Taupunkt
  .190707, Wind .197112, Druck .203012; Regen .208408); keine Hinweise mehr.
- **Vorab gerechnet (Zone 9):** Fenster W9 17:16:00.893525 → Commit 20:58:00.630741 = 13 319,74 s; Sperre (Vereinigung
  der Pflichtfelder) 20:15:27.531578 → 20:52:00.203012 = 2 192,67 s; Anteil 0,83538 → **84 %**.
- **20:58:00 Zonen 9 und 11 gerechnet** (Konfig-View `calculate`; die Konsolen-Ausgabe scheiterte an cp1252, gelesen
  danach ohne erneute Rechnung):
  - Zone 9: „… Keine Werte von Temperatur von 2026-10-13 20:15 bis 2026-10-13 20:52 (Sensor stumm). Keine Werte von
    Taupunkt von … (Sensor stumm). Keine Werte von Windgeschwindigkeit von … (Sensor stumm). Keine Werte von Luftdruck
    von … (Sensor stumm). Verdunstung für 84 % des Zeitraums gebucht.“ → **Anteil ✅ (84 % = Soll)**, Satz 1 inhaltlich
    richtig, aber **vier Sätze statt einem ❌** (Befund L1).
  - Zone 11 (behalten): kein neuer Satz ✅ (Kriterium 2). Zone 10 weiter ohne Satz.
  - Gebucht: Zone 9 Δ −0,21941, Zone 11 Δ −0,26264; Verhältnis 0,8354 = Anteil (gleiche Werte, gleiches Fenster ±0,4 s).
  - „gebucht.Der alte Vorrat“: das bekannte fehlende Leerzeichen (Bestand, nicht dieser PR). „SÃ¤ttigung“ in der
    Lesung = Dekodierung meines Clients (UTF-8 als Latin-1), nicht im Produkt.

## Befund L1 — ein Satz je Feld statt je Sperre

`_silent_sensor_explanation` gruppiert Felder nach der exakten Sperre `(start, end)`. Der Beginn ist für alle Felder
eines Geräts gleich (letztes Lebenszeichen), das Ende ist die eigene Rückkehr jedes Feldes; eine Station meldet ihre
Felder nacheinander, Millisekunden auseinander. Damit bekommt jedes Feld eine eigene Gruppe, und die minutengenaue
Anzeige macht die Sätze gleich. Kein Unit-Test hatte Enden mit verschiedenen Mikrosekunden. Korrektur: nach der Sperre
gruppieren, wie der Satz sie zeigt (`%Y-%m-%d %H:%M`), Felder als Menge.

**Korrektur im Branch (nicht in v2026.10.13b1):** `fa701bcd` „fix(calculation): fields back milliseconds apart share one
silent-time sentence“ (Gruppierung nach `(start.strftime(fmt), end.strftime(fmt))`, Felder als Menge) + `6fa424e8`
(Reihenfolge-Pin, Gegenprobe „Rückkehr eine Stunde später“, getauschter Sensor statt unmöglicher Eingabe). RED: 4 == 1 /
2 == 1; Review + Re-Review ohne offene Befunde; Suite 7/3925/9/466 (Namen sauber). Live noch nicht nachgeprüft.

## Ergebnis

| # | Ergebnis |
|---|---|
| 1 | Anteil 84 % = vorab gerechnet ✅; Satz 1 inhaltlich richtig, Form ❌ (vier Sätze) → Befund L1, im Branch behoben |
| 2 | ✅ |
| 3 | ✅ |
| 4 | ✅ |
| 5 | ✅ (Hinweis und WARNING) |

Aufräumen (Step 6): offen — Entscheidung, ob L1 live nachgeprüft wird (dann wird der Aufbau weiterverwendet).
