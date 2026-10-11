# Live-Verifikation der Vorhersage-Gewichtung (Eifel-Joe#61) — Design

Stand: 2026-10-07, Entscheidungen E1–E3 und Abschnitte 1–3 im Chat vom User freigegeben.
**Revision 2 (2026-10-11):** Nachtrag §10 (E4–E6) — Ersatzort per manuellen Koordinaten, Rohdokument aus
Log-Stücken, Intervall-Drosselung; Abschnitte 1–3 des Nachtrags im Chat vom User freigegeben. Revision 1 liegt in
`archive/design-history` (`ec898135`).
Art: **Verifikation, keine Codeänderung.** Code-Fakten mit Fundstellen: `D:\Entwicklung\HASI\issue61-work\code-facts.md`
(gelesen auf `upstream/master` `6a40e083`; Zitate unten verweisen auf dessen Abschnitte Q1–Q10).

## 1. Problem

Die Vorhersage-Gewichtung (`forecast_weighting_enabled`) wurde nie auf einer laufenden Instanz beobachtet — weder der
Tagespfad (upstream PR 172, Eifel-Joe#61 Body) noch der Live-Estimate-Pfad, den JustChr selbst gebaut hat (`faa05b0b`,
Beta v2026.10.02; Kommentar auf #61 vom 2026-10-03). Belegt sind beide nur durch Tests. Das Issue nennt fünf
Beobachtungen, die es schließen:

| # | Beobachtung | Quelle |
|---|---|---|
| B1 | ein antwortender Wetter-Client | Body 1 |
| B2 | eine Zone **mit** Zeitplan (Resolver-Anker) und eine **ohne** (Fallback-Anker = Rechenzeitpunkt) | Body 2 |
| B3 | ein Lauf mit Regen im Fenster und einer mit Regen außerhalb; verkürzte Dauer + `irrigation_target_bucket` | Body 3 |
| B4 | eine Berechnung unter `autocalcmode: before_run` **aus einem Dispatch heraus** | Body 4 |
| B5 | Zone ohne Durchflusssensor unter Live-Estimate, Regen in der Vorausschau, Lauf kürzer als das Live-Defizit allein, Zonenkarte = Laufdauer | Kommentar 03.10. |

## 2. Ausgangslage (geprüft 2026-10-06 21:36–22:10 UTC, nur lesend)

- **Blocker „PirateWeather 429 auf HA-Test“ ist weg.** Rechnung um 21:00 UTC (23:00 Ortszeit): Zonen 2–8 (PyETO,
  Sensorgruppe 0 = alle Felder `weather_service`) `last_calculated` 23:00:00, Delta −1,546 mm aus 5 Datenpunkten;
  Systemlog ohne `irrigation_plus`-Eintrag; Pirate-Abrufe im Log.
- **Code auf HA-Test = `upstream/master`.** HA-Test hat v2026.10.06b1 = production `fa31c31a`; dessen `.py`-Dateien
  unterscheiden sich von `6a40e083` nur in `const.py` (Version).
- **HA-Test-Konfiguration (Auszug):** Pirate Weather, metrisch, `autocalcmode: fixed_time` 23:00,
  `hourlycalculation: false`, `precipitation_forecast_days: 1`, Regen-Wächter an (Schwelle 2 mm),
  `zone_sequencing: parallel`, `forecast_weighting_enabled: false`, `live_estimate_enabled: false`. Zeitpläne: „all“
  (täglich, Ende-Anker 20:27 Ortszeit) und „TEST B2 scheduler dispatch“ (Zone 2, Start 08:54).
- **Vorhersage HA-Test** (WS `irrigation_plus/weather_forecast`, Tagessummen): 07.10. 3,4 · 08.10. 15,9 · 09.10. 3,6 ·
  10.10. 7,5 · 11.10. 0,6 · 12.10. 0 mm. Der Wächter würde derzeit jeden Plan-Lauf ganz überspringen (`observed`
  16,84 mm ≥ 2).
- **Ventile der vorhandenen Zonen:** Zonen 0/1 (Kirschlorbeer, Beet) sind `classic` und schalten nur ihre
  `linked_entity` `input_boolean.test_ventil2/3` (`irrigation.py:893`, `:1113`, `:3226`, `:3375`). Ihre hinterlegten
  `run_service`-Skripte senden nach `zigbee2mqtt/Wasser vorne/set` bzw. `…/Wasser Beet/set` über den Broker von HA-Prod,
  werden aber nur von den selbstschließenden Modi gelesen (`self_closing.py:91-103`). **Würde jemand eine der beiden
  Zonen auf `service` stellen, schaltete HA-Test echte Ventile.** Test1–6: Verteiler „Gardena1“ auf Emulator; Grace Test:
  Emulator mit Durchflusssensor.

## 3. Entscheidungen

**E1 — Regen ins Fenster: echte Vorhersage am HA-Test-Standort** (Variante 1 von 3). Zeitpläne wenige Minuten voraus,
Zeitpunkte nach dem Stundendokument gewählt. Verworfen: (2) manuelle Koordinaten auf einen Ort mit passendem Regen —
verschiebt Standort, Sonnenstand und PyETO für alle HA-Test-Rechnungen und zieht einen Pfad mehr in den Test; bleibt
Ausweichweg, falls die Regenverteilung zum Testzeitpunkt nicht trägt (dann neue Freigabe). (3) Open-Meteo als zweiter
Client — seit Pirate antwortet unnötig; prüfte einen Client, den keine unserer Installationen für die Vorhersage nutzt.

**E2 — Regen-Wächter: an lassen, Schwelle für die Testdauer 2 → 100 mm** (Variante 1 von 3). Er überspringt dann
nichts, rechnet aber weiter; sein `observed` ist die zweite Gegenprobe (O2). Verworfen: (2) abschalten — `observed`
verschwindet (Q6, `skip_conditions.py:212-213`); (3) nur Fenster < 2 mm — Gutschriften im Rundungsrauschen, bei der
Wetterlage kaum verfügbar.

**E3 — Imperiale Einheiten: aus dem Live-Test heraus, getrennt per lokalem pytest belegen** (Variante 1 von 3).
Verdacht aus dem Code (abgeleitet, nicht gemessen): die Gutschrift ist immer mm (`rain.mm`), der Live-Pfad addiert sie
auf `live_deficit` in **Anzeige-Einheiten** — Lauf `irrigation.py:2501-2502` (`min(0.0, deficit + credit)`), Panel
`live_estimate.py:1742-1744` → `_live_run_duration`, dessen Docstring „in the same unit as deficit“ verlangt;
`live_deficit` ist `from_mm(...)` (`live_estimate.py:1353`, `:1607-1614`). Auf imperial würden 5 mm als 5 Zoll
gutgeschrieben. Der Tagespfad ist nicht betroffen (`calculate_module` rechnet den Eimer vorher in mm um). Verworfen:
(2) HA-Test auf US-Einheiten umstellen — Nebenwirkung auf jede Integration und Statistik; (3) nur vermerken.

## 4. Aufbau (HA-Test)

**Testzonen** (Sandbox `api_post("/irrigation_plus/zones", …)`):

| Zone | Zweck | Aufbau |
|---|---|---|
| **61-A** | B2a, B3, B4, B5 | `classic`, `linked_entity` = neues `input_boolean.hasi61_a`, Modul 0 (PyETO), Sensorgruppe 0, kein `flow_sensor`, kein Verteiler, `bucket_threshold` 0 |
| **61-B** | B2b | wie 61-A, `input_boolean.hasi61_b`; **in keinem aktiven Zeitplan** |

Größe/Durchsatz so, dass 1 mm ≥ 10 s Laufzeit ergibt und ein Lauf wenige Minuten dauert (Rate = Durchsatz × 60 /
Größe mm/h; Dauer = |Eimer| / Rate × 3600 s). Eimer per `irrigation_plus.set_bucket` so tief, dass die erwartete
Gutschrift den Lauf **verkürzt**, aber nicht wegfallen lässt (Gutschrift ≥ Defizit ⇒ Zone fällt weg,
`calculation.py:1396`).

**Konfiguration für die Testdauer** (Originale vorher gesichert, `issue61-work\livetest\config-before.json`):

- `forecast_weighting_enabled` → `true`; `precipitation_threshold_mm` 2 → 100 (E2).
- Zeitpläne „all“ und „TEST B2 scheduler dispatch“ → `enabled: false` (sonst nimmt „all“ die Testzonen mit, und 61-B
  hätte doch einen Plan, Q3: „all“ prüft den Zonenzustand nicht).
- Neuer Zeitplan **P61**: täglich, Start-Anker, `start_time` je Phase gesetzt, `zones` = nur 61-A.
- `autocalcmode` → `before_run` nur in Phase 2; `live_estimate_enabled` → `true` nur in Phase 3.
- Log-Pegel per `logger.set_level` → `debug`: `custom_components.irrigation_plus.calculation`, `….irrigation`,
  `….live_estimate`, `….skip_conditions`, `….weathermodules.PirateWeatherClient` (Rohdokument, Q1/Q8);
  `info` für `custom_components.irrigation_plus`, `….scheduler`, `….auto_calc`.

**Sicherheit.** Jeder Lauf schaltet nur `input_boolean.hasi61_a`/`_b`. Vor jedem Schaltlauf: P61 zurücklesen (welche
Zonen) und deren `linked_entity`/`watering_mode`. Zonen 0/1 bleiben unverändert. Kein MQTT, keine Discovery, kein
HA-Test-Neustart (alles per Dienst/WS/HTTP-View). Unter `before_run` berechnet der Dispatch alle automatischen Zonen,
wenn der Plan „all“ nennt — P61 nennt nur 61-A, also nur deren Neuberechnung und Dispatch (Q4).

**Rückbau.** P61, 61-A/-B und die beiden `input_boolean`s löschen; Konfiguration und Log-Pegel zurück; danach
Konfiguration auslesen (`config-after.json`) und mit der Sicherung vergleichen — Abweichung muss leer sein.

## 5. Orakel

Für ein Fenster `[s, s + 24 h)` (`precipitation_forecast_days` = 1, Q2):

- **O1 — Rohdokument.** Der Pirate-Client schreibt bei DEBUG bei jedem echten Abruf das ganze Dokument ins Log
  (`get_forecast_data` und `get_data`, Q1). Maßgeblich ist der **letzte echte Abruf vor der Auswertung** (Cache-Treffer
  loggen „Returning cached …“). Eigenes Skript `issue61-work\o1.py` — importiert **nicht** `forecast_window` —
  integriert `precipIntensity` (mm/h) sekundengenau über das Fenster, mit der Stempel-Konvention des Clients (Wert gilt
  für die Stunde, die am Stempel endet, Q1/Q2) und dem Abschnitt vor dem Auswertungszeitpunkt abgeschnitten.
- **O2 — Regen-Wächter.** `observed` aus `irrigation_outlook.skip_preview` bzw. der INFO-Zeile des Wächters beim
  Dispatch: dieselbe `expected_rain`-Regel, aber ein anderer Weg zum Anker (Wächter: nächster Lauf aus `upcoming` bzw.
  „jetzt“ beim Dispatch; Gewichtung: `async_next_run_start_for_zone` bzw. übergebener `run_start`).

**Toleranz** ±0,01 mm (Log-Format `%.2f`, Wächter rundet auf 2 Stellen). **Trennschärfe:** Zeitpunkte so gewählt,
dass richtiges und falsches Fenster laut O1 um **≥ 0,5 mm** auseinanderliegen — sonst beweist Gleichheit nichts.

## 6. Ablauf und Prüfkriterien

**Probe 0** (vor allem anderen): (a) Rohdokument vollständig aus dem Log lesbar (`ha_get_logs`), JSON parsebar,
`hourly.data` mit `time`/`precipIntensity`; (b) es enthält den API-Schlüssel nicht (grep vor jedem Ablegen).
Scheitert (a): **anhalten, Rücksprache** — nicht improvisieren.

**Phase 1** — `fixed_time`, Gewichtung an, Live-Estimate aus:

- **B1:** Rohdokument im Log, Gutschrift-Zeile „forecast weighting X mm rain → effective bucket …“, kein Fehler.
- **B2a (Resolver-Anker):** P61-Start T1 kurz voraus, dann `irrigation_plus.calculate_zone` für 61-A (Dienst übergibt
  `run_start=None` ⇒ Resolver, Q3/Q4). **Bestanden:** Gutschrift = O1(T1) = O2 (Outlook mit P61 als einzigem Plan),
  je ±0,01; und |O1(T1) − O1(Rechenzeitpunkt)| ≥ 0,5.
- **B2b (Fallback-Anker):** `calculate_zone` für 61-B. **Bestanden:** DEBUG „no scheduled run resolves for zone <61-B>“
  und Gutschrift = O1(Rechenzeitpunkt) ±0,01.
- **Für 61-A und 61-B:** Erklärung enthält „forecast-weighting-applied“ mit `(wahr → effektiv)`; `duration` =
  |effektiv| / Rate × 3600 (nachgerechnet); `irrigation_target_bucket` = wahr − effektiv.
- **B3 (Lauf mit Regen im Fenster):** P61 feuert bei T1. **Bestanden:** `input_boolean.hasi61_a` an/aus;
  `run_log[0].planned_s` = gespeicherte (verkürzte) Dauer < Dauer aus dem wahren Eimer; Eimer nach dem Lauf =
  `irrigation_target_bucket` (nicht 0; genauer `max(Ziel, Eimer vor dem Lauf)`, Q7).

**Phase 2** — `before_run`:

- **B4:** Eimer von 61-A neu setzen; P61-Start T2 kurz voraus, T2 so gewählt, dass |O1(T2) − O1(T2 + 24 h)| ≥ 0,5
  (Falle „+1 Tag“, Q4). **Bestanden:** Logkette „Executing recurring schedule“ → „Committing the pre-run calculation
  for zones: …“ → „Calculating zone …“ in derselben Sekunde; `last_calculated` = Dispatch-Zeit; Gutschrift = O1(T2) =
  Wächter-`observed` beim Dispatch, je ±0,01; Lauf nutzt die eben berechnete Dauer (`planned_s`).

**Phase 3** — `fixed_time`, Live-Estimate an:

- **Probe:** bekommt 61-A ein `live_deficit` (`irrigation_outlook.zone_estimates`)? Ohne Schätzung fällt der Pfad
  still auf den Tagespfad zurück (Q5) — dann **anhalten, Rücksprache**.
- **B5:** P61-Start T3 kurz voraus; kurz vor dem Dispatch `zone_estimates[61-A]` lesen: `live_deficit` D,
  `forecast_credit` C, `live_duration` L. **Bestanden:** C = O1(T3) ±0,01; L < Dauer aus D allein (nachgerechnet);
  beim Dispatch INFO „Live-estimate watering: zone … → Y s (live deficit D′)“ mit Y = L und `run_log[0].planned_s` = Y
  (ändert sich D zwischen Lesen und Dispatch: mit D′ nachrechnen). Die Zonenkarte zeigt denselben WS-Wert
  (`view-zones.ts:549-566`); ein Blick ins Panel durch den User ist optional.

**Regen außerhalb des Fensters** (Body 3, zweiter Teil):

- **(i) Pflicht:** Regen außerhalb zählt nicht — belegt durch B2a/B2b/B4: der Regen vor T bzw. nach T + 24 h liegt mit
  ≥ 0,5 mm Abstand nachweislich nicht in der Gutschrift.
- **(ii) Gelegentlich:** ein Lauf mit Gutschrift 0 trotz Regen in der Vorhersage braucht ein trockenes 24-h-Fenster
  (frühestens 11./12.10. laut Vorhersage). Wird mitgenommen, falls eines kommt, solange #61 offen ist; **keine
  Bedingung zum Schließen** (Gutschrift 0 ist der schlichte Zweig `if forecast_precip > 0`).

**Imperial (E3):** lokaler pytest gegen `upstream/master` im Arbeitsordner (nicht im Repo, kein Produktionscode):
`_zone_run_decision` bzw. `_live_run_duration` mit `metric=False`, Defizit in Zoll, Gutschrift in mm. Ergebnis
bestätigt oder widerlegt den Verdacht aus E3.

## 7. Ausdrücklich nicht dabei

- **Codeänderungen.** Ein gefundener Defekt wird ein eigenes Issue mit eigener Spec.
- **HA-Prod.** Dort `forecast_weighting_enabled: false` — keine Änderung.
- **Imperial live** (E3).
- **Semantik der Pirate-Stundenstempel** (im Client als „ASSUMED“ markiert): O1 übernimmt die Konvention; geprüft
  werden Anker und Durchreichung, nicht die Bedeutung beim Anbieter.
- **`precipitation_forecast_days` > 1, `hourlycalculation: true`, Verteiler-Mitglieder.** HA-Prod nutzt die letzten
  beiden; keine der fünf Beobachtungen verlangt sie. Im Abschluss-Kommentar als „nicht beobachtet“ genannt.

## 8. Belege und Ablage

`D:\Entwicklung\HASI\issue61-work\`: `livetest\protocol.md` (je Kriterium Rohzitat aus Log/WS, O1-/O2-Wert, Urteil),
`o1.py`, `livetest\config-before.json` / `config-after.json`, Rohdokumente der Auswertungen. Zeiten nur aus HA-eigener
Quelle (Log-Stempel, `ha_eval_template`); Zonen-Attributzeiten nie aus `ha_get_history` (rechnet sie um). Der
Wetter-API-Schlüssel (steht in `ha_get_integration`-Optionen) gelangt in keine Datei; vor jedem Ablegen grep.

## 9. Ende-zu-Ende-Kriterium

1. B1–B5 und (i) bestanden, je mit Beleg im Protokoll;
2. Rückbau-Vergleich der Konfiguration ohne Abweichung; **Rev. 2:** außer `autoupdateinterval` = `"60"` (E6), und
   Koordinaten-Vergleich ohne Abweichung (§10.4);
3. Imperial-Probetest gelaufen, Ergebnis festgestellt.

Danach P2: Ergebnis-Kommentar auf Eifel-Joe#61 (EN + DE, Freigabe vorher), #61 schließen, `Eifel-Joe#42` nachziehen,
Imperial-Befund ggf. als neues Fork-Issue mit Label im selben Zug; Spec, Plan und Belege nach
`archive/design-history`.

**Abbruch:** fällt ein Kriterium durch → kein zweiter Versuch mit umgebautem Aufbau, sondern
`superpowers:systematic-debugging` und Rücksprache. Ein Durchfaller kann ein echter Defekt sein.

## 10. Nachtrag Revision 2 (2026-10-11)

### 10.1 Anlass (gemessen 2026-10-11, Protokoll `issue61-work\livetest\protocol.md`)

- **Blocker 429:** HA-Test bekam von Pirate Weather seit 2026-10-09 09:16 UTC nur noch HTTP 429 (5466 + 550 Fehler).
  User-Entscheidung: neuer Schlüssel (vom User im Panel eingetragen); seit 09:10:43 Ortszeit keine 429 mehr.
- **E1 trägt nicht:** am HA-Test-Standort Stundenwerte 11.10. 07:00 bis 12.10. 13:00 UTC alle 0, Tagessummen
  12.–17.10. alle 0 mm. User-Entscheidung: Ausweichweg E1 (2), manuelle Koordinaten (E4).
- **Rohdokument zerlegt:** jede Abruf-Zeile wird nach 16384 Byte abgeschnitten (16379 Zeichen + Farbcode); die
  Fortsetzung steht in 5 direkt folgenden Zeilen ohne Zeitstempel. Eine gefilterte Suche sieht nur 31 von 168
  Stundenwerten (E5).
- **Abrufrate:** ein Zyklus 09:20:42.554–43.326 Ortszeit = 1 `get_data` + 18 `get_forecast_data` echte Abrufe
  (parallel, ohne Sperre im Client) + 20 Cache-Treffer. User-Entscheidung: Intervall 10 → 60 min bis zum Test, und
  nach dem Test bleibt 60 (E6). Seit 2026-10-11 10:45:01 Ortszeit belegt („Scheduled auto update time interval for
  each 1:00:00“).

### 10.2 E4 — Ersatzort per manuellen Koordinaten

- **Suche** (User-Wahl Variante 1 von 3; verworfen: (2) Suche direkt mit Pirate über den Mess-Schlüssel — kostet
  dessen Kontingent, Zustand des Schlüssels unbekannt; (3) Ort vom User — nicht nachvollziehbar gewählt): lokales
  Skript `issue61-work\scout.py` fragt Open-Meteo mit dem GFS-Modell (`hourly=precipitation`, Zeitbasis UTC, ohne
  Schlüssel) für eine feste Liste von Orten in derselben UTC-Verschiebung wie HA-Test ab (DE, NL, BE, FR, DK, NO, SE,
  CH, AT, PL, CZ, IT, ES). Gleiche Verschiebung hält Pirates Tagesblöcke deckungsgleich mit HA-Tests Uhr.
- **Kriterium** (R = Regen in mm laut Reihe, Fenster halboffen, Startpunkte in 15-Minuten-Schritten, Regen innerhalb
  einer Stunde gleichverteilt): für jeden Startpunkt t in [jetzt, jetzt + 8 h] gilt
  R(t, t + 24 h) ≥ 2 mm **und** |R(t, t + 24 h) − R(t + 24 h, t + 48 h)| ≥ 0,5 mm; außerdem existiert T1 in
  [jetzt + 1 h, jetzt + 20 h] mit |R(T1, T1 + 24 h) − R(jetzt, jetzt + 24 h)| ≥ 0,5 mm. Rangfolge nach der Reserve
  (kleinster Abstand zur jeweiligen Schwelle über alle t).
- **Setzen:** WS `irrigation_plus/coordinates_save` mit Breite, Länge und der Gitterhöhe aus der Open-Meteo-Antwort.
  Der Eintrag lädt neu (`websockets.py:1070-1101`: die Koordinaten sind beim Setup in die Wetter-Clients gebacken).
  Folgen: sofortiger Abruf-Schub; Verteiler-Entitäten bis zum nächsten Neustart `unavailable` (vorbestehend, für
  #61 ohne Belang).
- **Bestätigen:** das erste vollständige Pirate-Dokument am Ort (E5) muss mit `o1.py scan` dasselbe Kriterium
  erfüllen. Sonst **einmal** Wechsel auf Rang 2 (User-Wahl); trägt auch dieser nicht → Stopp, Rücksprache.
  Das ist Aufbau, kein Prüfkriterium.
- **Reihenfolge:** Koordinaten vor Zonen, Zeitplan und Log-Pegeln; kein Neuladen innerhalb einer Phase; zurück erst
  nach dem Löschen von P61.
- **Datenschutz:** Der Testort ist ein öffentlicher Ort und darf mit Namen und auf 2 Stellen gerundeten Koordinaten
  ins Protokoll. HA-Tests eigene Koordinaten nie: WS `irrigation_plus/coordinates` liefert sie als `ha_latitude`,
  `ha_longitude`, `ha_elevation` mit (`websockets.py:1062-1064`) — die Sandbox filtert sie, bevor etwas zurückkommt.

### 10.3 E5 — Rohdokument aus Log-Stücken

- **Zusammensetzen** in der Sandbox: `error_log` ungefiltert lesen (Fenster 2000 Zeilen, bei Bedarf `offset`),
  chronologisch ordnen; ab jeder Zeile `PirateWeatherClient get_(forecast_data|data) called API` alle folgenden
  Zeilen ohne Zeitstempel ohne Trenner anhängen, Farbcodes je Stück entfernt.
- **Vollständig** (ersetzt Probe 0 (a)) heißt: 168 Stundenwerte in lückenlosen 3600-s-Schritten, nach dem
  Stundenblock folgt `'daily':`, `precipIntensity`-Zähler = 177 (1 currently + 168 hourly + 8 daily). Sonst Probe 0
  gescheitert → Stopp, Rücksprache. Probe 0 (b): die URL im Dokument trägt `***`, kein Schlüsselmuster.
- **Ablage** unverändert: nur die Zahlenreihe nach `doc-HHMMSS.series.json`; die Sandbox gibt nie Rohtext zurück.
- **Maßgebliches Dokument:** Die Gutschrift liest nur `_cached_doc` und fragt nie selbst ab
  (`PirateWeatherClient.py:210-215`); jeder echte Abruf überschreibt es (`:249` `get_forecast_data`, `:357`
  `get_data`), unmittelbar vor seiner Log-Zeile. Maßgeblich ist daher der letzte echte Abruf mit Log-Stempel vor der
  Gutschrift-Zeile, gleich welche Methode. Zusätzlich müssen **alle Dokumente dieses Schubs dieselbe Stundenreihe**
  haben (verglichen werden nur die Paare `(time, precipIntensity)`; `currently` darf abweichen). Weichen sie ab →
  Stopp, Rücksprache — kein nachträgliches Auswählen des passenden Dokuments.
- **Zeitpunkt:** Extraktion unmittelbar nach jeder Auswertung, im selben Zyklus.

### 10.4 E6 — Intervall, Eimer-Marge, Rückbau

- **Intervall:** Task 5 setzt 10 min (alle vier Felder `autoupdateenabled`, `…schedule`, `…interval`, `…delay`
  zusammen; nur dann plant `__init__.py:1243-1244` neu), Beleg INFO „… for each 0:10:00“. Der Rückbau setzt 60 min,
  Beleg „… for each 1:00:00“. Eine 429 während der Phasen ist ein Umgebungsabbruch, kein Durchfaller → Stopp,
  Rücksprache.
- **Eimer-Marge 8 → 15 mm:** Sensorgruppe 0 bezieht alle Felder vom Wetterdienst; gemessener Regen am Ersatzort hebt
  den Eimer bei der Rechnung an. D = −(⌈max(O1(T1), O1(E))⌉ + 15) mm (Läufe etwa 5–8 min bei 180 mm/h). Fällt eine
  Zone trotzdem weg (wahrer Eimer + Gutschrift ≥ 0), ist die Phase nicht auswertbar → Stopp, Rücksprache, kein
  Nachsetzen.
- **Testzonen nach dem Koordinatenwechsel anlegen:** ihr `last_consumed_at` beginnt am neuen Ort; keine Mischung von
  Wetterzeilen beider Orte in ihren Rechnungen.
- **Rückbau-Reihenfolge:** P61 löschen → Zonen 61-A/-B und Helfer löschen → Konfiguration zurück (Intervall 60) →
  `coordinates_save` mit `manual_coordinates_enabled: false` (Neuladen) → Log-Pegel WARNING.
- **Vergleich:** gegen `config-before.json` mit genau einer erwarteten Abweichung `autoupdateinterval` = `"60"`;
  `coords-before.json` / `coords-after.json` (nur die `manual_*`-Felder, in der Sandbox gefiltert) ohne Abweichung.
- **Danach:** HA-Test-Neustart, angekündigt, damit die Verteiler-Entitäten zurückkommen.

### 10.5 Ausdrücklich nicht dabei (Ergänzung zu §7)

- Die Abrufrate selbst (19 echte Abrufe je Zyklus, keine Sperre, Fehler ungecacht, drei Versuche ohne Pause): eigenes
  Fork-Issue, Text zur Freigabe nach diesem Nachtrag. Offen bleibt, ob HA-Prod (OWM) ebenfalls mehrfach je Zyklus
  abruft — nicht gemessen.
- Die Gutschrift am Ersatzort prüft Anker und Durchreichung wie am Heimatort; Sonnenstand und PyETO am Ersatzort sind
  für B1–B5 ohne Belang (Eimer werden gesetzt, geprüft wird die Differenz wahr → effektiv).
