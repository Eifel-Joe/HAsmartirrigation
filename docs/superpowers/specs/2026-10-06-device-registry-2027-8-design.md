# Geräte-Registry: vor HA 2027.8 von `via_device` und `async_get_device` lösen

- **Issue:** Eifel-Joe#11 (Arbeitsreihenfolge `Eifel-Joe#42`, Punkt 12), `schwere:mittel`, `prod-scharf`
- **Stand:** Spec; Entwurf Teil 1 (Aufbau, Verhalten) und Teil 2 (Tests, Live-Test, Abgrenzung) am 2026-10-06 im Chat
  freigegeben
- **Basis:** `upstream/master` = `7001c754`. `entity.py` Blob `1925bba0` (unverändert seit `83eb8488`, 2026-09-04),
  `__init__.py` Blob `28eeded7`, `distributor.py` Blob `68aa2d4a`. Zeilenangaben beziehen sich auf diesen Stand.
- **HA-Quellen:** `homeassistant/helpers/device_registry.py` der Tags 2025.5.0, 2025.12.0, 2026.2.3, 2026.6.0, 2026.7.0,
  2026.8.0, 2026.9.0, 2026.9.4 und `entity_platform.py` von 2025.5.0 und 2026.9.4, gelesen über die GitHub-API
  (`gh api "repos/home-assistant/core/contents/homeassistant/helpers/<datei>.py?ref=<tag>" --jq .content | base64 -d`;
  lokale Kopien: `D:\Entwicklung\HASI\issue11-work\ha-src\ha-<tag>-<datei>.py`).

## Der Defekt

Zwei Aufrufe an HAs Geräte-Registry sind abgekündigt, beide mit der Frist **HA 2027.8.0**.

1. **`via_device`** in `zone_device_info` (`entity.py:49`) und `distributor_device_info` (`entity.py:63`). Damit hängt
   jedes Zonen- und Verteiler-Gerät am Hub, angegeben als Kennung des Hubs `(DOMAIN, cid)`. HA reicht das
   `device_info` jedes Entities an `async_get_or_create` weiter. Seit 2026.8 heißt der Ersatz `via_device_id` (die
   Registry-ID des Hubs); seit 2026.9.0 steht die Entfernung in `_DEPRECATED_DEVICE_INFO_PARAMETERS`
   (`"via_device": ("2027.8.0", "via_device_id")`).
2. **`async_get_device(identifiers=…)`** beim Löschen einer Zone (`__init__.py:2217-2222`) und eines Verteilers
   (`distributor.py:2125-2129`), jeweils um das leere Gerät mitzunehmen. Seit 2026.9.0 gemeldet („device identifiers
   and connections are no longer unique across config entries“, `breaks_in_ha_version="2027.8.0"`); Ersatz
   `async_get_device_by_identifier(identifier, config_entry_id)`, den es seit 2026.8.0 gibt.

**Live belegt (2026-10-05/06):** HA-Prod (2026.9.4, Zähler 10) und HA-Test (2026.9.3, Zähler 7) melden (1) für
`irrigation_plus`. Die genannten Stellen (`binary_sensor.py:73`, `button.py:54`, `sensor.py:147` …) sind HAs
Stack-Zuordnung zum `async_add_entities`-Aufruf; die Wurzel ist `entity.py`. (2) läuft nur beim Löschen und steht
deshalb in keinem der beiden Logs.

## Warum nicht einfach ersetzen

| HA | `DeviceInfo` | `async_get_or_create` | Suche nach Kennung |
|---|---|---|---|
| 2025.5.0 — JustChrs Untergrenze (`hacs.json`, CI-Job `test-ha-floor`) | nur `via_device` | feste Schlüsselwort-Signatur, kein `via_device_id`, kein `**kwargs` | nur `async_get_device` |
| 2026.2.3 — JustChrs CI-Hauptjob (Python 3.13) | nur `via_device` | wie 2025.5.0 | nur `async_get_device` |
| 2026.7.0 (auch 2025.12.0, 2026.6.0 geprüft) | nur `via_device` | wie 2025.5.0 | nur `async_get_device` |
| 2026.8.0 | `via_device` und `via_device_id` | `via_device_id` neu; `via_device` als abgekündigt kommentiert (Z. 1766) | `async_get_device_by_identifier` neu |
| 2026.9.0 / 2026.9.4 | nur `via_device_id` | `via_device` nur noch über `**kwargs`, gemeldet, Frist 2027.8.0 | `async_get_device` gemeldet, Frist 2027.8.0 |

Folgen:

- **`via_device_id` ohne Weiche** wirft unter 2026.8 einen `TypeError` in `async_get_or_create`. Die Entity-Plattform
  fängt nur `DeviceInfoError` (2025.5.0 `entity_platform.py:828-843`), also würde kein Zonen-Entity mehr angelegt —
  auch nicht in JustChrs beiden CI-Jobs.
- **Ab 2026.8 muss die ID stimmen:** Ein `via_device_id`, das kein registriertes Gerät ist, endet in `DeviceInfoError`
  (2026.9.4 `device_registry.py:2404-2421`), und HA verwirft das Entity. Es muss die echte Registry-ID des Hubs sein.
- **Ein fehlender Eltern-Schlüssel ändert nichts:** `via_device_id` bleibt `UNDEFINED` und wird so an
  `_async_update_device` gereicht. Nur ein ausdrückliches `via_device=None` löst den Elternteil.

## Entscheidungen (User, 2026-10-06, im Chat)

- **E1 Variante 1:** Weiche; JustChrs Untergrenze 2025.5.0 bleibt.
- **E2:** `async_get_device` kommt in denselben PR (gleiche Ursache, gleiche Frist, gleiche Weiche; Regel „Spiegel-Bugs
  in denselben Fix“).
- **E3:** Direkt als PR an JustChr, ohne Vorab-Frage. Der PR-Text bietet die Alternative an (Untergrenze auf 2026.8 oder
  höher, Weichen weg).

## Das Design

### Grundsatz

Beide Weichen fragen HAs Registry selbst, statt eine Versionsnummer zu vergleichen — JustChrs Muster in
`migrate_domain.all_registry_devices` (`08de2eb5`, 2026-09-05: „Detect rather than branch on a version string“).
Gefragt wird an der **Klasse** der Registry, nicht an der Instanz: Ein `Mock()` beantwortet jede Attributfrage mit
Ja, und die bestehenden Lösch-Tests bauen die Registry als `Mock()` (`test_distributor_entities.py:120`, `:285`,
`test_distributor_integration.py:194`).

### (a) Eltern-Verweis

- **`entity.hub_link_for(registry, hub_device_id, cid) -> dict`:** Steht `via_device_id` in der Signatur von
  `type(registry).async_get_or_create`, lautet der Verweis `{"via_device_id": hub_device_id}`. Sonst — auch wenn die
  Methode fehlt oder ihre Signatur nicht lesbar ist — `{"via_device": (const.DOMAIN, cid)}`.
- **`async_setup_entry`** (`__init__.py:208-216`): Die Registrierung des Hubs bleibt, ihr Rückgabewert wird genommen,
  und `hass.data[DOMAIN]["hub_link"] = hub_link_for(device_registry, hub.id, coordinator.id)` steht fest, bevor die
  Plattformen geladen werden.
- **`entity.hub_link(hass) -> dict`:** der abgelegte Verweis. Ohne Eintrag (ein Entity ohne Setup) die alte Form
  `{"via_device": (const.DOMAIN, coordinator_id(hass))}`, mit derselben Fehlertoleranz wie `coordinator_id`.
- **`zone_device_info`, `distributor_device_info`:** `**hub_link(hass)` statt des festen `via_device`. Modul- und
  Funktions-Docstrings nennen beide Formen.

### (b) Gerät suchen

- **`entity.find_device(registry, identifier, config_entry_id)`:** Hat `type(registry)` die Methode
  `async_get_device_by_identifier`, wird sie mit `(identifier, config_entry_id)` gerufen; sonst
  `registry.async_get_device(identifiers={identifier})` wie heute.
- **Zone löschen** (`async_remove_entity`, `__init__.py:2217-2222`) und **Verteiler löschen**
  (`distributor.py:2125-2129`) rufen `find_device` mit der Entry-ID des Coordinators (`self.entry`, gesetzt in
  `__init__.py:569`).
- **Die Entry-ID wird tolerant gelesen** (`getattr(getattr(self, "entry", None), "entry_id", None)`): Die Test-Hosts der
  bestehenden Verteiler-Lösch-Tests tragen kein `entry` (`_DistHost` aus `tests/test_distributor.py:45`;
  `_upsert_coord()` baut den Coordinator per `__new__`, `tests/test_distributor_integration.py:153`). Der alte Weg
  braucht die ID nicht; im Betrieb ist sie immer gesetzt. `async_remove_entity` hatte bis dahin keinen Test (seit
  Task 4/4b: Treffer, Fehlschlag, alte Bauart ohne `entry`).

### Verhalten je Version

- **HA unter 2026.8** (Untergrenze 2025.5, JustChrs CI 2025.5.0 und 2026.2.3): dieselben Aufrufe wie heute.
- **HA ab 2026.8** (HA-Prod 2026.9.4, HA-Test 2026.9.3): die neuen Aufrufe; beide Warnungen verschwinden. Bestehende
  Zonen- und Verteiler-Geräte behalten denselben Hub als Elternteil — gleiche ID, HA schreibt nichts um.

### Rückbau

Hebt JustChr die Untergrenze auf 2026.8 oder höher, liefert `hub_link_for` immer `via_device_id` und `find_device`
immer den neuen Aufruf; die Weichen fallen ersatzlos weg. Der Kommentar an beiden Stellen sagt das. Dazu (Nachtrag
aus der Umsetzung): die zwei toleranten Lesestellen der Entry-ID (Zone `__init__.py`, Verteiler `distributor.py`)
werden strikt `self.entry.entry_id`, und die drei bestehenden Lösch-Tests mit `Mock()`-Registry, die
`async_get_device` namentlich binden (`tests/test_distributor_entities.py`, `tests/test_distributor_integration.py`),
ziehen mit um; die Kompatibilitäts-Tests der alten Bauart fallen weg.

### Betroffene Stellen

- `entity.py`: drei neue Helfer (`hub_link_for`, `hub_link`, `find_device`), zwei geänderte (`zone_device_info`,
  `distributor_device_info`), Modul-Docstring
- `__init__.py`: Setup legt den Verweis ab; Zone löschen über `find_device`
- `distributor.py`: Verteiler löschen über `find_device`
- neue Testdatei `tests/test_device_registry_compat.py`; bestehende Tests unverändert

## Schwester-Pfade geprüft

- **`migrate_domain.all_registry_devices`:** `registry.devices` als Mapping (gemeldet seit 2026.9.0, Frist 2027.9.0) —
  von JustChr bereits gelöst.
- **`sensor_liveness.py:304-319`:** `dr.async_get(hass).async_get(device_id)` sucht über die Geräte-ID; in 2026.9.4
  ohne Meldung (`device_registry.py:1883` ff.). Unberührt.
- **`migrate_domain.async_migrate_device_areas`:** `async_update_device(device_id, area_id=…)` über die Geräte-ID —
  nicht abgekündigt.
- **`_validate_str`** (2026.9.4 `device_registry.py:290-303`, Frist 2026.12.0, meldet Nicht-String-Werte): Hersteller,
  Modell und Version sind bei uns String-Konstanten (`entity.py`, `__init__.py:209-216`) — nicht betroffen.
- **Weitere abgekündigte Schlüssel** (`default_*`, `created_at`, `modified_at`): nicht benutzt (`git grep` leer).

## Ausdrücklich nicht in dieser Arbeit

- Untergrenze anheben oder Weichen weglassen — JustChrs Entscheidung, im PR-Text angeboten.
- Frontend, Übersetzungen, `dist`; kein Versions-Bump im PR.
- `sensor_liveness.py`.
- Kind-Geräte (`parent_device_id`, seit 2026.9) — nicht nötig.

## Verworfen

- **Variante 2** (Elternteil nachträglich per `async_update_device(via_device_id=…)`): braucht einen Eingriff an jeder
  Stelle, an der ein Gerät entsteht (Setup, neue Zone, neuer Verteiler), und eine feste Reihenfolge mit der
  Entity-Plattform.
- **Variante 3** (Untergrenze 2026.8, nur neue Aufrufe): JustChrs Entscheidung; schließt HA 2025.5 bis 2026.7 aus; seine
  CI (Python 3.13 → HA 2026.2.3, Floor-Job 2025.5.0) könnte die Integration nicht mehr testen.
- **Versionsvergleich** (`MAJOR_VERSION`/`MINOR_VERSION`): JustChr fragt lieber die API selbst.
- **Frage an der Instanz** (`hasattr(registry, …)`): Jeder `Mock()` sagt Ja.
- **Ohne Setup-Eintrag gar kein Verweis:** Die bestehenden Pins erwarten das Tupel, die alte Form nimmt jede Version
  bis 2027.8 an, und im Betrieb gibt es den Eintrag immer.

## Tests

Alle als pytest (der PR ändert nur Python).

1. **`hub_link_for`:** Fake-Klasse mit `via_device_id` in der Signatur → `{"via_device_id": <Hub-ID>}`; Fake-Klasse
   ohne → `{"via_device": (DOMAIN, cid)}`; `Mock()` → alte Form.
2. **`hub_link`:** abgelegter Verweis wird geliefert; ohne Eintrag die alte Form (die bestehenden Pins
   `test_sensor.py:127` und `test_distributor_entities.py:39` bleiben unverändert).
3. **`zone_device_info`, `distributor_device_info`** mit abgelegter neuer Form: `via_device_id` vorhanden, `via_device`
   nicht.
4. **`find_device`:** Fake-Klasse mit `async_get_device_by_identifier` → genau diese mit Kennung und Entry-ID,
   `async_get_device` nicht gerufen; `Mock()` → `async_get_device(identifiers={…})` wie heute (die bestehenden
   Lösch-Tests bleiben unverändert).
5. **Zone und Verteiler löschen** über den neuen Weg: Gerät gefunden und entfernt.
6. **Setup mit echter Registry**, im Stil von `tests/test_init.py::test_async_setup_entry_success` (echtes `hass`,
   echte Geräte-Registry, Store und Plattformen gepatcht): Nach `async_setup_entry` steht der Verweis in `hass.data`;
   ein Gerät, das mit `zone_device_info` angelegt wird, trägt die ID des Hubs als `via_device_id`. In JustChrs CI ist das
   der alte Weg auf echtem HA — der Beleg, dass die Hierarchie dort unberührt bleibt.
7. **Mutationen:** Weiche immer an / immer aus; Verweis nicht abgelegt; Suchreihenfolge vertauscht; Entry-ID nicht
   weitergereicht. Jede macht mindestens einen Test rot.

RED auf `7001c754`: 1, 3–6 scheitern (Helfer fehlen bzw. alter Weg fest verdrahtet), bei 2 die neue Hälfte. Die
übrige Suite bleibt namensgleich mit der Baseline auf derselben Basis.

## Ende-zu-Ende-Kriterium (HA-Test, 2026.9.3)

1. **RED auf dem heutigen Stand (Pre-Release v2026.10.05b2):** Das System-Log zeigt die `via_device`-Warnung von
   `irrigation_plus`; das Löschen einer Wegwerf-Zone erzeugt die `async_get_device`-Warnung; die Eltern-Verweise aller
   Geräte der Integration werden notiert.
2. **Pre-Release** aus production (upstream + Branding + der offene Fix aus `JustChr#191` + dieser Fix), auf HA-Test
   per HACS; Neustart vorher angekündigt.
3. **GREEN:** keine der beiden Warnungen von `irrigation_plus`; jedes Gerät hat denselben Eltern-Verweis wie in
   Schritt 1; eine neue Wegwerf-Zone und ein neuer Wegwerf-Verteiler hängen am Hub, nach dem Löschen ist ihr Gerät weg,
   ohne Warnung.

Beleg der Eltern-Verweise per Template (vorher und nachher), Log per `ha_get_logs(source="system")`:

```jinja
{% for d in integration_entities('irrigation_plus') | map('device_id') | reject('none') | unique %}
{{ d }} | {{ device_attr(d, 'name') }} | {{ device_attr(d, 'via_device_id') }}
{% endfor %}
```

HA-Prod bleibt auf v2026.10.05b1 (Feldtest Eifel-Joe#8); ein Update nur auf Zuruf.

## Präzisierungen aus der Planung (2026-10-06)

- **Zweiter Setup-Test mit einer Registry neuer Bauart:** Auf altem HA (lokal, JustChrs CI) liefert `hub_link_for` die
  Kennungs-Form, gleich welche ID das Setup übergibt. Reichte das Setup die Coordinator-ID statt der Hub-ID weiter,
  bliebe das dort unbemerkt und verwürfe ab 2026.8 jedes Zonen-Entity. Der Test ersetzt `dr.async_get` durch eine
  Fake-Registry, deren `async_get_or_create` `via_device_id` kennt, und erwartet `{"via_device_id": <Hub-ID>}`.
- **Die Setup-Tests ersetzen auch `async_get_clientsession`:** Lokal scheitert das Setup sonst an „aiodns needs a
  SelectorEventLoop on Windows“; so stehen `test_init.py::…::test_async_setup_entry_success` und
  `…_with_weather_service` in der Baseline auf `7001c754`.
- **Lokale teardown-ERRORs:** Die zwei Setup-Tests enden lokal mit „Lingering timer“ (300-s-Takt der
  Sensor-Lebendprüfung), wie andere Coordinator-Tests der Baseline; RED und GREEN zählen in der Testphase.
- **Diagnostics:** `async_get_config_entry_diagnostics` kopiert `hass.data[DOMAIN]`, also erscheint `hub_link` künftig
  dort — ohne Geheimnis, und im Live-Test der Beleg, welcher Weg aktiv ist.
- **Umfang der Tests:** zwölf Tests in fünf Tasks, 16 Mutationen (Plan
  `docs/superpowers/plans/2026-10-06-device-registry-2027-8.md`, Probelauf dort).

## Nachtrag aus der Umsetzung (2026-10-06, nicht Teil der Freigabe)

Aus den Quality-Reviews kamen Nachträge dazu, je ein eigener Commit (Begründung und Belege im Plan unter Task 1b–5b).
Task 1b (Review von Task 1):

- **Die Erkennung darf das Setup nie stoppen.** HA braucht seit 2026.3 Python 3.14, und seit 2026.6 verzichtet
  `device_registry.py` auf `from __future__ import annotations`; damit wertet `inspect.signature` die Annotationen aus,
  und ein Name, den die Registry nur unter `TYPE_CHECKING` importiert, würfe `NameError`. `hub_link_for` fängt deshalb
  jeden Fehler beim Lesen der Signatur und bleibt dann bei der Kennungs-Form. Heute latent (alle Namen der Signatur sind
  in 2026.6.0–2026.9.4 zur Laufzeit gebunden).
- **Drei Bauarten statt zwei:** 2026.8.0 selbst nennt beide Schlüssel und hat noch kein `**kwargs`; ein eigener Test
  pinnt, dass die Regel auf den neuen Namen schaut (nicht auf `**kwargs`, nicht auf das Fehlen des alten).
- **`hub_link` gepinnt:** alles außer einem abgelegten Verweis (leer, kein Dict, `hass` ohne `data`, `MagicMock`) ergibt
  die Kennungs-Form; der Verweis wird als Kopie herausgegeben.
- **Docstrings:** neu in 2026.8 ist der Parameter bzw. Device-Info-Schlüssel `via_device_id` (`DeviceEntry.via_device_id`
  gibt es lange vorher); ab 2026.9 meldet HA das alte `via_device`.
- **Task 2b:** ein Fehlschlag von `find_device` ergibt `None` und fragt nie den alten Lookup (mit Entry-ID und mit
  `None`); Docstring: ab 2026.8 findet eine Entry-ID `None` nichts, ein `Mock` nimmt auch mit `spec` den alten Weg.
- **Task 3b:** belegt, dass der Verweis vor dem Laden der Plattformen steht und ein alter Verweis (Reload)
  überschrieben wird; dazu das Lesen der Id-Form über `zone_device_info`.
- **Task 4b / 5b (Schwester-Pfade):** beide Löschpfade gepinnt für Fehlschlag (kein Rückfall auf den alten Lookup, das
  Löschen läuft weiter) und für die alte Bauart ohne `entry`; ein gleichlautender Kommentar an beiden Stellen, warum
  die Entry-ID tolerant gelesen wird; der Verteiler-Kommentar verwies auf ein nie vorhandenes `async_remove_zone`.
- **Umfang jetzt:** zweiundzwanzig Tests, 36 Mutationen (M17–M36 aus den Nachträgen), Probe-Endstand
  `issue11-work\probe-2026-10-06-5b.patch`. Lokal enden die drei Setup-Tests zusätzlich mit dem teardown-ERROR
  „Lingering timer“.

## Lieferung

- Worktree `D:\Entwicklung\HASI\issue11-work\wt`, Branch `fix/device-registry-2027-8` von `upstream/master`, danach
  `--unset-upstream`.
- Nur Fix und Tests; `black` und `ruff` vor jedem Push; kein `dist`.
- production: Pre-Release mit der Kalender-Version des Bautags, Live-Test auf HA-Test nach dem Ende-zu-Ende-Kriterium.
- P2: Kommentar auf Eifel-Joe#11 mit dem Schwester-Befund vor dem Bau; nach dem PR Label `upstream:gemeldet` und
  `#42` Punkt 12.
- PR-Text erst deutsch, dann englisch zur Freigabe; keine Verweise auf unsere Issues oder Dokumente.
- P1: Spec, Plan und Belege ins Archiv `archive/design-history`.
