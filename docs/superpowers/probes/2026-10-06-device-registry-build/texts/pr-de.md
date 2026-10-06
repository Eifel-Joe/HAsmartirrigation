Titel (englisch, wird mit der EN-Fassung freigegeben): fix(devices): use the device registry's 2026.8 calls where offered, keep the 2025.5 floor

## Problem

Zwei Aufrufe an HAs Geräte-Registry sind abgekündigt und fallen in HA 2027.8.0 weg:

1. **`via_device`** im `device_info` der Zonen- und Verteiler-Geräte (`entity.py`), mit dem jedes dieser Geräte am
   Hub hängt. HA 2026.9 meldet beim Start: „calls `device_registry.async_get_or_create` with a deprecated `via_device`
   parameter; use `via_device_id` instead … This will stop working in Home Assistant 2027.8.0“.
2. **`device_registry.async_get_device(identifiers=…)`** beim Löschen einer Zone (`async_remove_entity`) und eines
   Verteilers (Löschzweig von `async_upsert_distributor`). HA 2026.9 meldet: „deprecated because device identifiers and
   connections are no longer unique across config entries; use `async_get_device_by_identifier` …“.

Einfach ersetzen geht nicht, weil die Integration ab HA 2025.5 laufen soll (`hacs.json`, CI-Job `test-ha-floor`):

| HA | `via_device_id` | `async_get_device_by_identifier` |
|---|---|---|
| 2025.5 – 2026.7 (Untergrenze; CI-Hauptjob 2026.2.3) | gibt es nicht: `async_get_or_create` hat eine feste Signatur, ein unbekannter Parameter wäre ein `TypeError`, und jedes Zonen- und Verteiler-Entity fiele weg | gibt es nicht |
| 2026.8 | neu (neben `via_device`) | neu |
| 2026.9 | einziger benannter Parameter; `via_device` nur noch über `**kwargs`, gemeldet | Ersatz für das gemeldete `async_get_device` |

## Fix

- `entity.hub_link_for` fragt die **Klasse** der Registry, ob `async_get_or_create` einen Parameter `via_device_id`
  hat — Erkennen statt Versionsvergleich, wie in `migrate_domain.all_registry_devices`. Wenn ja, lautet der
  Eltern-Verweis `{"via_device_id": <Registry-ID des Hubs>}`, sonst wie bisher `{"via_device": (DOMAIN, <Kennung>)}`.
  Gefragt wird die Klasse, weil ein `Mock()` jede Attributfrage an der Instanz bejaht und die bestehenden Lösch-Tests
  die Registry als `Mock()` bauen.
- `async_setup_entry` nimmt den Rückgabewert der bestehenden Hub-Registrierung und legt die Antwort einmal in
  `hass.data[DOMAIN]["hub_link"]` ab — vor dem Laden der Plattformen und bei jedem Setup neu, weil `hass.data` einen
  Reload überlebt. `zone_device_info` und `distributor_device_info` tragen `**hub_link(hass)`; ohne Eintrag bleibt die
  alte Form.
- `entity.find_device` nutzt `async_get_device_by_identifier(identifier, config_entry_id)`, wo die Klasse ihn hat,
  sonst wie bisher `async_get_device`. Beide Löschpfade gehen darüber, mit der Entry-ID des Coordinators. Sie wird
  tolerant gelesen (der alte Lookup braucht sie nicht, Test-Hosts ohne `__init__` haben keine); ein Fehlschlag ergibt
  `None` und fällt nie auf den abgekündigten Aufruf zurück.
- **Python 3.14:** Seit 2026.6 hat HAs `device_registry.py` kein `from __future__ import annotations` mehr. Unter
  Python 3.14, das HA seit 2026.3 verlangt, wertet `inspect.signature` die Annotationen dann aus; ein Name, den die
  Registry nur für die Typprüfung importiert, würfe `NameError` und bräche das Setup ab. Jeder Fehler beim Lesen der
  Signatur lässt deshalb die Kennungs-Form stehen. Heute nur vorbeugend: in 2026.6 bis 2026.9.4 sind alle Namen der
  Signatur zur Laufzeit gebunden.
- Bestehende Geräte behalten denselben Hub als Elternteil (dieselbe ID, HA schreibt nichts um): keine Migration, eine
  Rückkehr auf eine ältere Version hat keine Folgen. `hub_link` erscheint künftig in den Diagnostics.
- Nebenbei: Der Kommentar über dem Verteiler-Löschzweig verwies auf eine Funktion `async_remove_zone`, die es nicht
  gibt; er nennt jetzt `async_remove_entity`.

**Alternative**, falls dir das lieber ist: die Untergrenze auf 2026.8 oder höher anheben und die Weichen streichen.
Dann fallen weg: beide Weichen und `import inspect`; die tolerante Entry-ID an beiden Löschpfaden (wird strikt
`self.entry.entry_id`); der Rückfall in `hub_link` samt seiner zwei bestehenden Pins
(`test_sensor.py::TestSmartIrrigationZoneEntity::test_device_info`,
`test_distributor_entities.py::test_distributor_device_info_identifiers_and_via_device`); die Tests der alten Bauart;
und die drei Lösch-Tests mit `Mock()`-Registry, die `async_get_device` namentlich binden, ziehen um. Sag Bescheid, dann
baue ich das so um.

## Testing

- Neue Datei `tests/test_device_registry_compat.py`, 22 Tests. Die CI läuft auf 2026.2.3 und 2025.5.0 und kennt die
  neuen Aufrufe nicht; deshalb prüfen Stand-in-Registrys die drei Bauarten (vor 2026.8, 2026.8.0 selbst, ab 2026.9).
  Dazu ein Setup-Test gegen die installierte Registry (in beiden CI-Jobs der alte Weg auf echtem HA), an beiden
  Löschpfaden Treffer, Fehlschlag und die alte Bauart ohne Entry, die Reihenfolge vor dem Laden der Plattformen, das
  Überschreiben nach einem Reload und die unlesbare Signatur. Bestehende Tests unverändert.
- Volle Suite lokal (Python 3.12, HA 2024.12.5): außer den neuen Tests unverändert. (Lokal enden die drei neuen
  Setup-Tests, wie die vorhandenen Coordinator-Tests, mit einem „Lingering timer“ beim Aufräumen — eine Eigenheit
  dieser Windows-Umgebung.) black und ruff sauber.
- 36 Mutationen der geänderten Zeilen, alle von der neuen Datei getötet.
- Live auf einer Testinstanz mit HA 2026.9.4: Vorher meldete HA beide Abkündigungen (beim Start und beim Löschen einer
  Zone und eines Verteilers). Nachher keine; alle bestehenden Zonen- und Verteiler-Geräte hängen mit derselben ID am
  Hub, kein Entity wurde verworfen, `hub_link` steht in den Diagnostics mit der Registry-ID des Hubs, und eine neu
  angelegte Zone sowie ein neuer Verteiler hängen am Hub und verschwinden beim Löschen samt Gerät — auch nach einem
  Reload.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
