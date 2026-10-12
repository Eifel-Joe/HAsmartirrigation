# DEBUG-Messung OWM-Client auf HA-Prod, 2026-10-11 (Eifel-Joe#89)

Freigabe: User im Chat („B ja“). Nur gelesen bis auf zwei `logger.set_level`-Aufrufe.

- Setzen: `logger.set_level {"custom_components.irrigation_plus.weathermodules.OWMClient": "debug"}` —
  Aufruf kurz vor 14:21:09 UTC (die erste DEBUG-Zeile liegt vor 16:21:09 Ortszeit; `date` lief erst nach der
  Tool-Antwort).
- Rückbau: derselbe Aufruf mit `"warning"` um 14:46:20 UTC. Beleg: letzte DEBUG-Zeile 16:46:12.410 Ortszeit,
  bis 16:47:06 keine weitere, obwohl Schübe alle 10–30 s kommen. Der Kind-Logger behält den Eintrag WARNING bis
  zum nächsten HA-Neustart (wirksamer Pegel wie vorher über `irrigation_plus` = WARNING).
- Aufbau HA-Prod (Diagnostics `data.store.config`): OWM, `autoupdateinterval` 10 min → `cache_seconds` 599,
  3 Zonen, 1 aktiver Zeitplan „Sunrise“ (alle Zonen), Regen-Wächter an (2 mm, 1 Tag), Live-Schätzung an,
  `continuousupdates` an, Sensorgruppe rein Sensor.
- Auswertung: Sandbox `ha_manage_custom_tool`, Skript `owm_count_sandbox.py` (Liste per `sorted()` auf
  Strings — Monty kann Listen von Listen nicht sortieren). Nur Kopf (Zeitstempel, Pegel, Thread, Art), keine
  URL, kein Dokument.

## Ergebnis (Fenster 16:21:09–16:46:20 Ortszeit)

| Art | Anzahl |
|---|---|
| echter Abruf `get_forecast_data` | 4: 16:28:12.840 (SyncWorker_58); 16:38:12.349 / .362 / .373 (SyncWorker_53, _46, _27) |
| echter Abruf `get_data` | 0 |
| „Returning cached OWM forecastdata“ | 537, Schübe von 6–7 alle 10–30 s |
| „Connection pool is full“, OWM-Fehler | 0 (auch Systemlog seit Neustart 08:48 UTC) |

Cache-Ablauf: Abruf 16:28:12.84 + 599 s = 16:38:11.84 → der Schub um 16:38:12.3 lief mit drei Workern in den
abgelaufenen Cache. Hochgerechnet höchstens rund 430 echte Anfragen am Tag (OWM frei: 60/min, 1 Mio./Monat).
Herkunft der 6–7er-Schübe nicht zugeordnet.

Folgen: Kommentare auf Eifel-Joe#89 (`6110244016` Messung + `schwere:niedrig`, `6110265016` Korrektur
`helpers.py:877` → `__init__.py:624-660`, `6110295807` gemeldet), Upstream `JustChr#196`.
