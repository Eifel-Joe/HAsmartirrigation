# Live-Test Geräte-Registry (Plan Task 7) — HA-Test

Instanz: **HA-Test** (MCP-Präfix `mcp__HA-Test__`), Core **2026.9.4** (Spec nannte 2026.9.3 — inzwischen aktualisiert),
Config-Entry `01M20AD0AWZJ15ZXSF1ECVJZN3`.

## Schritt 1 — RED auf dem installierten Pre-Release v2026.10.05b2 (2026-10-06, ~14:45 Ortszeit)

**Registry direkt** (`config/device_registry/list`, gefiltert auf den Entry; nicht über Entities):

| Gerät | Geräte-ID | Kennung | `via_device_id` |
|---|---|---|---|
| Irrigation Plus (Hub) | `7d8d4b6a91c3cbf05d3ee3a279d44463` | `Irrigation Plus` | — |
| Kirschlorbeer | `fb27ba09f82bd120803acf9a16255c92` | `Irrigation Plus_zone_0` | Hub |
| Beet | `b2d30aa9730e1c29cdcf4641a1257f23` | `Irrigation Plus_zone_1` | Hub |
| Test1 | `4a3b714b555acc05e86f66155c63436c` | `Irrigation Plus_zone_2` | Hub |
| Test2 | `130d59f8a1fd629e9ee54305358550e4` | `Irrigation Plus_zone_3` | Hub |
| Test3 | `692ce34d29a0f55417790edcdd062c1d` | `Irrigation Plus_zone_4` | Hub |
| Test4 | `1dba72f7a445fa648b4d9ddbc45ef5d6` | `Irrigation Plus_zone_5` | Hub |
| Test5 | `8b1d0e5677d826d8649ad3fe4c87ed61` | `Irrigation Plus_zone_6` | Hub |
| Test6 | `ad6d8930e70219d1dcd2e91382befd1b` | `Irrigation Plus_zone_7` | Hub |
| Grace Test | `b517f6afd36cbb993c4af850cc72b093` | `Irrigation Plus_zone_8` | Hub |
| Gardena1 | `94c7b88d9e8f19ddd4981a93721a9a01` | `Irrigation Plus_distributor_0` | Hub |

- 11 Geräte, ein einziges Hub-Gerät; Instanzname „Irrigation Plus“ nicht leer → Vorbedingung M6 erfüllt (Hub aus dem
  Setup == Hub der globalen Entities).
- Entity-Registry des Entries: **181** Einträge, davon **37** `unavailable`/ohne Zustand (je Zone `last_calculated`,
  `last_updated`, `data_points`, `current_drainage` × 9 = 36, dazu `button.irrigation_plus_distributor_gardena1_test_run`).
- System-Log (`source=system`): `via_device`-Warnung von `irrigation_plus` an `binary_sensor.py:73`, `button.py:54`,
  `sensor.py:147`, `binary_sensor.py:97`, `button.py:78` (Zähler 7 vor den Wegwerf-Objekten).
- **Wegwerf-Zone** „LT Wegwerf-Zone“ (deaktiviert; über `api_post /irrigation_plus/zones`): id 9, Gerät
  `7e3d79629fea54977e10db8837784804`, `via_device_id` = Hub. Gelöscht (`{id: 9, remove: true}`): Gerät weg, Log neu:
  `async_get_device` … `__init__.py, line 2218` … „stop working in Home Assistant 2027.8.0“.
- **Wegwerf-Verteiler** „LT Wegwerf-Verteiler“ (nur Name): id 1, Gerät `fe39150ca89f1f3ffd78583628c38228`,
  `via_device_id` = Hub. Gelöscht: Gerät weg, Log neu: `async_get_device` … `distributor.py, line 2126`.
- Hinweis: Die Sandbox (`ha_manage_custom_tool`) kennt kein `asyncio.sleep`; der Zonen-View hat kein GET (Liste über das
  Websocket-Kommando `irrigation_plus/zones` bzw. `irrigation_plus/distributors`).

## Schritt 2/3 — Pre-Release und Update (2026-10-06)

- production `fa31c31a` (= `7001c754` + Branding + upstream PR 191 + die fünf Commits + Build), gepusht mit Lease
  (vorher `31cd812b`, lokal gesichert als `backup/production-pre-v2026.10.06b1`). Pre-Release **v2026.10.06b1**
  (Titel/Text wie freigegeben, zurückgelesen gleich), ZIP aus dem SHA: 205 Einträge, sha256 `59a4dd3a…`, Download
  HTTP 200 und sha256-gleich; Tag remote/lokal `fa31c31a`; Fork-CI (hassfest, HACS, Pages) grün.
- HA-Test: HACS `update_information` + `download v2026.10.06b1`; `entity.py` auf der Instanz = neuer Stand (gelesen);
  Neustart 14:53 (angekündigt).

## Schritt 4 — GREEN (v2026.10.06b1)

- Hub-Gerät `sw_version` = v2026.10.06b1 (Setup des neuen Codes gelaufen); System-Log frisch, **keine** Meldung von
  `irrigation_plus`; Roh-Log nach dem Start (14:53:53) ohne `via_device`/`async_get_device`; kein „Not adding entity
  with invalid device info“, kein „Error adding entity“ (letzte 2000 Zeilen).
- Registry: dieselben **11 Geräte**, dieselben IDs, alle zehn mit `via_device_id` = Hub `7d8d4b6a…`; **181** Entities,
  dieselben **37** `unavailable` wie vorher (keins verworfen).
- Diagnostics `data.hub_link` = `{"via_device_id": "7d8d4b6a91c3cbf05d3ee3a279d44463"}` = Hub-Geräte-ID (Id-Form aktiv,
  Vorbedingung M6 erfüllt).
- Wegwerf-Zone (id 9): Gerät `7e3d7962…` (HA vergibt die ID des in RED gelöschten Geräts wieder), `via_device_id` = Hub,
  18 Entities angelegt; gelöscht → Gerät weg, **keine** Warnung.
- Wegwerf-Verteiler (id 1): Gerät `fe39150c…`, `via_device_id` = Hub, 4 Entities; gelöscht → Gerät weg, **keine**
  Warnung.

## Schritt 5 — Reload

- Eintrag per `POST /api/config/config_entries/entry/<id>/reload` neu geladen (`loaded`); `data.hub_link` unverändert;
  neue Wegwerf-Zone nach dem Reload: am Hub, 18 Entities, gelöscht → Gerät weg, keine Warnung.
- **Befund am Rande (vorbestehend upstream, nicht von diesem Fix):** Nach dem Reload blieben die 9 Entities des
  bestehenden Verteilers „Gardena1“ (`current_outlet`, `outlet_1…6_zone`, `commissioned`, `watering_now`)
  `unavailable` (seit 12:56:37 UTC = Reload). Ursache im Code: `async_unload` leert nur die Zonen-Tracker in
  `hass.data[DOMAIN]` (Kommentar dort: issue #36), nicht `distributor_sensors` (`sensor.py:132`) und
  `distributor_buttons` (`button.py:67`) samt den Binärsensoren — nach dem Reload hält `async_add_distributor_sensors`
  die Entities für vorhanden und legt sie nicht neu an. Der Branch berührt weder die Plattform-Dateien noch
  `async_unload` (Diff leer). Kein Upstream-/Fork-Issue dazu gefunden. HA-Test danach neu gestartet (angekündigt).
- Nach dem zweiten Neustart: 11 Geräte, ein Elternteil (Hub), Hub `sw_version` v2026.10.06b1, 181 Entities, wieder
  **37** `unavailable` (Ausgangsstand), „Gardena1“ zurück (`current_outlet` 1, `watering_now` off, `commissioned` on),
  System-Log ohne `irrigation_plus` — auch der zweite Start ohne Abkündigungs-Warnung.

## Ergebnis

Ende-zu-Ende-Kriterium der Spec erfüllt: RED (beide Warnungen auf v2026.10.05b2) → GREEN (keine Warnung, gleiche
Eltern-IDs, Diagnostics Id-Form, Wegwerf-Zone und -Verteiler hängen am Hub und verschwinden beim Löschen ohne Warnung,
kein Entity verworfen), Reload ohne Folgen für den Fix. HA-Prod unberührt (v2026.10.05b1, Feldtest des Wettersensors).
