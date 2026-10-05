# Live-Test PR 1 „stummer Wettersensor“ auf HA-Test — 2026-10-04

Plan: `docs/superpowers/plans/2026-10-03-dead-weather-sensor-common.md`, Task 15 (Variante 1, YAML-MQTT unter
`hasi_livetest/`, ohne Discovery), mit der freigegebenen Ergänzung „Verbrauchszähler an Gerät C“. Alle Zeiten UTC,
sofern nicht anders vermerkt. Keine IP, keine Schlüssel.

## Version und Installation

- Pre-Release **v2026.10.04b2** (Fork-Release, Tag → `d8c74317`, production = `d8c74317`); ZIP aus dem SHA, Download
  byte-gleich mit dem lokalen ZIP.
- HA-Test: HA **2026.9.3**. HACS `update_information` + `download v2026.10.04b2`; HACS meldet installiert
  `v2026.10.04b2`; `custom_components/irrigation_plus/sensor_liveness.py` vorhanden (Zeitstempel der Installation).
- Neustart HA-Test ~17:10 (angekündigt, freigegeben). Danach: Integration `loaded`, Repairs 0; System-Log zu
  `irrigation_plus` nur die bekannte Deprecation-Warnung `via_device` (Upstream-Code), kein Fehler.
- Bestehende Sensorgruppen auf HA-Test (id 0, 1): nur Wetterdienst-Felder → von der Prüfung nicht betroffen; beide tragen
  nach dem Laden `sensor_outages: []`, `sensor_last_seen: {}`.

## Aufbau (17:12–17:20)

- `configuration.yaml`: Schlüssel `mqtt` per `ha_config_set_yaml` (Vorschau, dann Token; `config_check: ok`), danach
  `mqtt.reload`. Nebenwirkung des Werkzeugs: eine Leerzeile am Dateianfang entfernt (kosmetisch).
- Entitäten (IDs per `ha_search` bestätigt; der Gerätename steht davor, anders als im Plan angenommen):
  - A: `sensor.hasi_livetest_a_livetest_a_temperature` (Gerät „HASI Livetest A“)
  - B: `sensor.hasi_livetest_b_livetest_b_temperature` (Gerät „HASI Livetest B“)
  - C: `sensor.hasi_livetest_c_livetest_c_temperature`, `sensor.hasi_livetest_c_livetest_c_humidity`
    (Gerät „HASI Livetest C“, `4a47c18f…`, Besitzer = MQTT-Entry `01KWE5TY…`)
- Automationen: `automation.hasi_livetest_a`/`_b`/`_c` (`time_pattern` jede Minute, `mqtt.publish` 18.5 / 17.0 /
  16.0), `automation.hasi_livetest_event` (Event `irrigation_plus_weather_stale` → `system_log.write`, Logger
  `hasi_livetest`, Modus `queued`, damit zwei Events derselben Prüfung beide ankommen).
- Retained: `hasi_livetest/c/humidity` = `80` (einmalig).
- **Ergänzung:** Verbrauchszähler (UI-Helfer, `utility_meter`, ohne Zyklus) „Livetest C Meter“ auf C-Temperatur →
  `sensor.hasi_livetest_c_livetest_c_meter`: `device_id` = Gerät C, `config_entry_id` = eigenes Entry
  `01M43YGV…`; Gerät C `config_entries` = nur MQTT. **`device_attr(Gerät C, 'config_entry_id')` = MQTT-Entry** → der
  `config_entry_id`-Zweig von `_entities_of_device` läuft hier (HA 2026.9.3). Der Zähler schreibt nur bei Änderung
  der Quelle; die Quelle bleibt 16.0 → sein Wert bleibt 0, sein `last_reported` steht.
- Sensorgruppen per `api_post("/irrigation_plus/mappings", …)` aus der Sandbox des HA-MCP-Servers (dieselbe HTTP-View
  wie das Panel; Anmeldung im Browser war nicht möglich, Passwort wird nicht eingegeben; der Server stellt mit seiner
  eigenen Anmeldung zu): **A = id 2** (Temperatur), **B = id 3** (Temperatur), **C = id 4** (Temperatur, Feuchte,
  Niederschlag = Zähler, `delta`).
- Stand 17:14 (Berlin 19:14): temp C 16.0, Feuchte 80, Zähler 0, A 18.5, B 17.0.

## Befund beim Aufbau: MQTT schreibt unveränderte Werte nicht (17:27)

- Sender A lief jede Minute (`last_triggered` 19:26:00 Berlin), aber `last_reported` aller MQTT-Sensoren stand seit
  19:14:00 Berlin (per `ha_eval_template`). Ein YAML-MQTT-Sensor schreibt auf HA 2026.9.3 einen unveränderten Wert
  NICHT neu (nur mit `force_update: true`). Die Annahme des Plans (Task 15, Schritt 3: „MQTT schreibt bei jeder
  Nachricht, `last_reported` rückt vor“) ist falsch; mit dem ersten Aufbau wäre nach 3 h auch C stumm gewesen und A/B
  ab 19:14 statt ab t1. Am Code ist das kein Fehler: es ist der Fall „schreibt nur bei Änderung“, den die Prüfung über
  das Gerät abfängt — nur ändert eine echte Station ihre Werte laufend.
- **Umbau (17:28, gleiche Variante 1, nur HA-Test):** A, B und C-Temperatur mit `force_update: true` (Schreibweise 1:
  schreibt bei jedem Update); neues **Gerät D** (`sensor.hasi_livetest_d_livetest_d_temperature` ohne
  `force_update`, Automation `automation.hasi_livetest_d` sendet abwechselnd 15.0/15.1 jede Minute; Feuchte
  `…_d_humidity` retained `70`, ruhig) = Schreibweise 2: schreibt nur bei Änderung, alle Felder bis auf eines ruhig;
  **Gruppe D = id 5** (Temperatur, Feuchte). Zähler-Quelle per Optionsfluss auf die ruhige **C-Feuchte** umgehängt (an
  der Temperatur mit `force_update` hätte der Zähler bei jedem Update selbst geschrieben und keinen Bürgen gebraucht);
  Zähler weiter an Gerät C, eigenes Entry.

## Erwartung

| Schritt | Erwartung |
|---|---|
| 1 | Ab t1 schweigen A und B; C meldet weiter, Feuchte und Zähler ruhig. |
| 2 | t1 + 3 h (+ ≤ 5 min): Hinweise für „Livetest A“ und „Livetest B“, keiner für „Livetest C“; zwei Events `stale: true` mit `since` = letzter Report (mit Offset); WARNING der Integration; zwei offene Einträge; `calculate_all_zones` ohne Fehler. |
| 3 | Neustart t1 + 3 h 10 min: Hinweise gleich wieder da, `since` unverändert; C ohne Hinweis. |
| 4 | A ein (t1 + 3 h 30 min): ≤ 5 min nach der ersten Meldung Hinweis A weg, Event `stale: false` mit `until` = erste Meldung, Eintrag geschlossen. |
| 5 | Gruppe B löschen: Hinweis B weg, Event `stale: false`. |
| — | Gruppe C hat über den ganzen Test keinen Hinweis (Feuchte und Zähler ruhig; der Zähler gedeckt über den Besitzer-Zweig). |
| — | Gruppe D hat über den ganzen Test keinen Hinweis (Temperatur ändert sich, Feuchte ruhig). |

## Ablauf

- **17:31 Stand vor t1** (Prüfung 17:30): A/B/C-Temperatur schreiben jede Minute (`force_update`, zuletzt 19:31:00
  Berlin), D-Temperatur wechselt jede Minute, C-/D-Feuchte und Zähler ruhig (19:28 Berlin). Alle vier Gruppen ohne
  Ausfall; `sensor_last_seen` aller Felder ≈ 19:30:00 Berlin — die ruhigen Felder über ihr Gerät gedeckt (C-Feuchte
  und Zähler = 19:30:00.412239 wie C-Temperatur; D-Feuchte = D-Temperatur 19:30:00.503607).
- **t1 = 17:31:52** (19:31:52+02:00): `automation.turn_off` A und B. Letzte Meldung A `2026-10-04T19:31:00.352353+02:00`,
  B `2026-10-04T19:31:00.148197+02:00`. Erwartet: Ausfälle öffnen bei der ersten Prüfung nach 20:31:00 UTC.
- **18:31 (t1 + 1 h):** A/B `sensor_last_seen` unverändert 19:31:00 (Berlin), keine Ausfälle; C (Temperatur, Feuchte,
  Zähler) alle 20:30:00.412815, D beide 20:30:00.502198 — Feuchten und Zähler seit 19:28 ruhig, über ihr Gerät gedeckt.
  Repairs 0; System-Log ohne Eintrag zu „liveness“.
- **19:31 (t1 + 2 h):** unverändert — A/B 19:31:00, keine Ausfälle; C alle 21:30:00.412519, D beide 21:30:00.503696;
  C-/D-Feuchte und Zähler seit über 2 h ohne Meldung, weiter gedeckt. Repairs 0.
- **Schritt 2 — 20:35:46 (t1 + 3 h 3 min 54 s, erste Prüfung nach 20:31:00): ✅**
  - Repairs 2: `weather_sensor_stale_2` (Livetest A), `weather_sensor_stale_3` (Livetest B), erstellt 20:35:46.476;
    Platzhalter `group` = Gruppenname, `entities` = `sensor.hasi_livetest_a_livetest_a_temperature (Temperature)` bzw.
    B, `since` = `2026-10-04 19:31`. Kein Hinweis für C und D.
  - `sensor_outages`: A `start 2026-10-04T19:31:00.352353, end null`; B `start …19:31:00.148197, end null` — Beginn =
    letzte Meldung exakt. C/D ohne Ausfall, alle Felder `last_seen` 22:35:00 (Berlin), auch die seit 19:28 ruhigen
    Feuchten und der Zähler (Besitzer-Zweig).
  - Events (Logger `hasi_livetest`, beide angekommen, `queued`): `{"device_id": "1b1c7c44…", "entity_id":
    "sensor.hasi_livetest_a_livetest_a_temperature", "fields": ["Temperature"], "mapping": "Livetest A",
    "mapping_id": 2, "since": "2026-10-04T19:31:00.352353+02:00", "stale": true, "until": null}`; B entsprechend
    (`since` `…19:31:00.148197+02:00`).
  - WARNING `custom_components.irrigation_plus.sensor_liveness`: „Sensor group Livetest A:
    sensor.hasi_livetest_a_livetest_a_temperature (Temperature) has not reported since 2026-10-04 19:31:00.352353;
    its last value is still used“ (B entsprechend).
  - `irrigation_plus.calculate_all_zones` (≈ 20:37): keine neue Log-Zeile von `irrigation_plus`.
  - Nebenbei (HA-Kern, nicht die Integration): Warnungen des Test-Zählers (Zustandsklasse `total` bei geerbter
    Geräteklasse Temperatur; ein `unknown` der Quelle beim MQTT-Neuladen).
- **Schritt 3 — Neustart HA-Test ≈ 20:37 (angekündigt), wieder oben 20:37:10: ✅ (Teil 1, vor der Karenz)**
  - 20:38:55, Karenz läuft: beide Hinweise aktiv, Platzhalter unverändert (`since` `2026-10-04 19:31`).
  - `sensor_outages` nach dem Laden unverändert (A `19:31:00.352353`, B `19:31:00.148197`, `end null`) — über die echte
    Abschaltfolge geschrieben; `sensor_last_seen` der letzten Prüfung vor dem Neustart (22:35:00 Berlin) ebenfalls da.
  - A/B nach dem Start `unknown` (kein retained, Sender aus) → weiter stumm; C-/D-Feuchte 22:37:12 (retained beim
    Start zugestellt), Zähler 22:37:10 (wiederhergestellt), C-/D-Temperatur ab 22:39:00.
- **Schritt 3, Teil 2 — erste Prüfung nach der Karenz 20:47:00: ✅** A/B-Ausfälle unverändert (gleicher Beginn,
  `end null`), Repairs weiter genau 2 (A, B; `created` 20:35:46 wie vorher); C/D ohne Ausfall und ohne Hinweis, alle
  Felder `last_seen` 22:47:00 (Berlin). Seit dem Neustart kein Event im System-Log (das Wiederanzeigen beim Setup sendet
  keins; nichts hat sich geändert).
- **Schritt 4 — A ein um 21:01:40 (t1 + 3 h 29 min 48 s): ✅** Erste Meldung 23:02:00.492 (Berlin, `unknown` → 18.5);
  die Prüfung um 23:02:10 (Takt ab dem Start 22:37:10) schließt den Ausfall: `start 19:31:00.352353, end
  2026-10-04T23:02:00.492071` = die eigene Rückkehr des Feldes (D3). Event `{"…": …, "mapping": "Livetest A",
  "since": "2026-10-04T19:31:00.352353+02:00", "stale": false, "until": "2026-10-04T23:02:00.492071+02:00"}`. Hinweis A
  weg (Repairs 1: nur B). Die INFO-Zeile beim Schließen ist bei Log-Stufe WARNING nicht sichtbar (durch Tests belegt).
- **Schritt 5 — Gruppe B gelöscht um 21:08:16 (`api_post`, `{"id": 3, "remove": true}`): ✅** Event `{"…": …,
  "mapping": "Livetest B", "mapping_id": 3, "since": "2026-10-04T19:31:00.148197+02:00", "stale": false, "until":
  "2026-10-04T23:08:16.194409+02:00"}` (`until` = Zeitpunkt des Löschens). Repairs 0.
- **Über den ganzen Test:** Gruppen C und D nie mit Ausfall oder Hinweis — C-/D-Feuchte und Zähler von 19:28 bis
  23:08 (Berlin, 3 h 40 min) ohne eigene Meldung, durchgehend über ihr Gerät gedeckt; der Zähler (eigenes Entry, Gerät
  einer anderen Integration) über den `config_entry_id`-Zweig auf HA 2026.9.3.

## Aufräumen (21:08–21:12)

- Sender A, C, D aus; retained `hasi_livetest/c/humidity` und `hasi_livetest/d/humidity` mit leerer Nutzlast und
  `retain: true` geleert.
- Gruppen 2, 4, 5 per `api_post … remove` gelöscht (B war Schritt 5); übrig nur die ursprünglichen Gruppen 0 und 1.
- Automationen `hasi_livetest_a/_b/_c/_d/_event` gelöscht; Zähler-Helfer (Config-Entry `01M43YGV…`) gelöscht.
- `mqtt`-Schlüssel aus `configuration.yaml` entfernt (Vorschau + Token, `config_check: ok`), `mqtt.reload`; die sechs
  verwaisten MQTT-Entitäten aus der Registry entfernt; die vier Geräte „HASI Livetest A–D“ entfernt.
- Gespeichertes Sandbox-Werkzeug `livetest_liveness_fields` gelöscht.
- Kontrolle: `ha_search livetest` → nichts; Geräte mit „livetest“ → keine; Repairs `irrigation_plus` → keine.
- Bleibt: die beim ersten YAML-Edit entfernte Leerzeile am Dateianfang (kosmetisch).

## Ergebnis

Alle fünf Schritte des Ende-zu-Ende-Kriteriums (Spec, *PR 1, HA-Test*) erfüllt, beide Schreibweisen abgedeckt
(Schreibweise 1: C-Temperatur mit `force_update`; Schreibweise 2: D, nur bei Änderung, alle Felder bis auf eines ruhig),
dazu der Besitzer-Zweig live. Kein Fehler der Integration im Log.
