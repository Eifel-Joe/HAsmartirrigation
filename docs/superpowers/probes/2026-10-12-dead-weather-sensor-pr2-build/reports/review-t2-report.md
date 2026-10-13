### Spec Compliance
- ✅ Spec compliant. Der Diff enthält genau Step 3-5 und Step 1, nichts darüber hinaus. Kein Missing, kein Extra, kein Misunderstood.
  - Import: `store.py:134` (`MAPPING_ON_SILENT_SENSOR` nach `MAPPING_NAME`), `store.py:150-152` (die drei `ON_SILENT_SENSOR_*` zwischen `MODULE_SCHEMA` und `RETRIEVED_AT`). Reihenfolge stimmt auch für ruff `I`.
  - Feld `MappingEntry.on_silent_sensor`, Standard `ON_SILENT_SENSOR_PAUSE`: `store.py:391`.
  - Coercion `_as_on_silent_sensor`: `store.py:~983-992`. Sie ist im Lade-Pfad eingehängt (`store.py:1424-1426`).
  - Kein Store-Versionssprung: `STORAGE_VERSION = 14` (`store.py:211`) und `STORAGE_MINOR_VERSION = 2` (`store.py:214`) stehen unverändert und sind nicht im Diff.
- Benannte Risiken, je ein Check:
  - Bestehende gespeicherte Gruppen laden als `keep`.
    - Es gibt genau eine Stelle, die ein `MappingEntry` aus gespeicherten Daten baut (`store.py:1403`), und dort läuft das Feld durch `_as_on_silent_sensor`.
    - Fehlt der Schlüssel, liefert `mapping.get(...)` `None`. `None in ("keep","pause")` ist False, also `keep`.
    - Der Attribut-Standard `pause` greift im Lade-Pfad nie, weil der Wert immer explizit übergeben wird.
  - Nur neu angelegte Gruppen starten mit `pause`. Das sind genau zwei `MappingEntry(...)`-Stellen ohne das Feld.
    - `set_up_factory_defaults`, `store.py:1589`. Der Test dazu ist `test_the_group_of_the_first_setup_pauses`.
    - `async_create_mapping`, `store.py:2217`, erreichbar nur über `__init__.py:1844`. Der Test dazu ist `test_a_group_created_now_pauses`.
    - Es gibt keine weitere Stelle (`grep "MappingEntry("` liefert 3 Treffer, die genannten zwei plus den Lade-Pfad).
  - Ungültige gespeicherte Werte fallen auf `keep`.
    - `ON_SILENT_SENSOR_OPTIONS` ist ein Tuple (`const.py:725`). Die Mitgliedschaft prüft damit per `==` und wirft bei unhashbaren Werten (`["pause"]`) keinen `TypeError`. Bei einem `set`/`frozenset` würde sie das tun.
    - Der Test `["pause"]` pinnt das (`test_silent_sensor_setting.py:~48`).
    - `"sometimes"`, `1` und `None` sind ebenfalls parametrisiert.
    - Falsche Schreibweise (`"Pause"`, `"PAUSE"`) ist im Lade-Pfad nicht getestet (siehe Minor 1). Der Code behandelt sie korrekt, denn `"PAUSE" in ("keep","pause")` ist False, also `keep`.
  - Domain-Migration und Kopierpfade.
    - `migrate_domain.py` baut kein `MappingEntry`. Es kopiert die Datei byte-genau.
    - `MigratableStore._async_migrate_major` fasst in `store.py:760-970` keine Mapping-Records an (kein Treffer für "mapping" in diesem Bereich).
    - Der gespeicherte Mapping-Record läuft also unverändert in den Lade-Pfad und wird dort zu `keep`.
    - Der im Test zitierte `test_migrate_domain::test_imports_the_legacy_store_verbatim` existiert (`tests/test_migrate_domain.py:59`).
  - Rollback nach unten ist gutmütig: der alte Lade-Pfad liest Felder einzeln per `.get` und ignoriert den unbekannten Schlüssel.
  - Lesepfade tragen den Schlüssel: Diagnose (`diagnostics.py:79`), `websocket_get_mappings` (`websockets.py:557`) und `get_mapping` laufen alle über `attr.asdict`. Das deckt den Satz im Interfaces-Block.
  - Gruppen ohne Nutzung der Einstellung bleiben byte-identisch. In diesem Task liest nichts außer `group_pauses` (`sensor_liveness.py:182`, aus Task 1) das Feld, und `group_pauses` vergleicht strikt mit `== "pause"`.
- ⚠️ Cannot verify from diff (liegt in späteren Tasks, bitte prüfen): `SmartIrrigationMappingView` (`websockets.py:~235-247`) kennt `on_silent_sensor` noch nicht im `vol.Schema`. Das Panel kann die Einstellung bis dahin also nicht per HTTP setzen. Der Schlüssel sollte dort mit `vol.In(ON_SILENT_SENSOR_OPTIONS)` validiert werden, weil der Store beim Schreiben nicht prüft (siehe Minor 3).

### Strengths
- Die Coercion ist eine Zeile und fehlersicher: unbekannt, falscher Typ oder fehlend ergibt `keep`. Ein Fehler kann in Richtung "nichts ändern" nur falsch liegen. Das passt zu `group_pauses` (`== pause`) und gibt Lade- und Laufzeitpfad dieselbe Semantik.
- Die Tests prüfen echtes Verhalten gegen den echten Store. Die Datei wird per `hass_storage` mutiert und über eine frische `SmartIrrigationStorage`-Instanz neu geladen. Dass die Mutation wirklich gelesen wird, zeigt der `"sometimes"`-Fall: andernfalls käme `pause` heraus.
- Mutationsprüfung am Code (gedanklich):
  - Lade-Aufruf entfernt: die Keep-Tests fallen.
  - `else KEEP` zu `else PAUSE`: fällt.
  - `in OPTIONS` zu `isinstance(str)`: der `"sometimes"`-Fall fällt.
  - Standard `pause` zu `keep`: die beiden Pause-Tests fallen.
- `test_a_save_without_the_setting_leaves_it_alone` setzt vorher bewusst den Nicht-Standardwert `keep`. Es würde also fallen, wenn ein Update auf `pause` zurückfiele.
- Reload wird für beide Werte getestet, `keep` und `pause`.
- Reiner Store-Eingriff: 21 Zeilen, kein neuer Zustand, keine Änderung an Pfaden anderer Felder. Die Commit-Message nennt die Semantik (WAS und WARUM).

### Issues
#### Critical (Must Fix)
Keine.

#### Important (Should Fix)
Keine.

#### Minor (Nice to Have)
1. `tests/test_silent_sensor_setting.py:~44` (Parametrisierung `[None, "sometimes", 1, ["pause"]]`): Die Schreibweise-Variante fehlt im Lade-Pfad. Ein späteres `.lower()` in `_as_on_silent_sensor` würde `"PAUSE"` zu `pause` machen und kein Test dieses Tasks würde es merken. `test_sensor_liveness_blocked.py:110` pinnt nur `group_pauses`, nicht den Lade-Pfad. Fix: `"PAUSE"` (oder `"Pause"`) in die Liste aufnehmen. Der Plan schreibt den Test wörtlich vor, daher ist das nur ein Hinweis.
2. `tests/test_silent_sensor_setting.py:~58-70` (`test_a_group_carried_over_from_smart_irrigation_keeps`) ist weitgehend redundant zum `stored=None`-Fall. Das Entfernen von `sensor_outages` und `sensor_last_seen` ändert am Ergebnis nichts, denn beide haben eigene Fallbacks. Es testet auch nicht die Migration selbst, sondern simuliert nur ihr Ergebnis. Der Docstring-Verweis hat zudem nicht die echte Test-ID (`test_migrate_domain.py::TestStorageImport::test_imports_the_legacy_store_verbatim`). Das ist plan-diktiert und harmlos.
3. `store.py:2217` und `store.py:2248` (`async_create_mapping` und `async_update_mapping`): Der Store prüft den Wert beim Schreiben nicht. Ein `"garbage"` oder `None` landet im Speicher und in `get_mapping`. Laufzeit und Neustart verhalten sich trotzdem gleich (beide `keep`, über `group_pauses` und `_as_on_silent_sensor`), es gibt also keinen Fehler. Die Validierung gehört in das Schema des Schreibpfads (siehe ⚠️ oben). Ein Test, der `async_create_mapping` mit explizitem `keep` aufruft, fehlt ebenfalls.

### Assessment
**Task quality:** Approved
**Reasoning:** Die Änderung ist klein, wörtlich nach Plan umgesetzt und fehlersicher. Alle benannten Risiken (Bestand lädt als `keep`, nur neue Gruppen `pause`, ungültige Werte, keine Versionserhöhung, Migration und Kopierpfade) sind am Code belegt, und die Tests pinnen die tragenden Entscheidungen. Offen sind nur kleine Lücken in der Testabdeckung und die Schreib-Validierung, die zu einem späteren Task gehört.