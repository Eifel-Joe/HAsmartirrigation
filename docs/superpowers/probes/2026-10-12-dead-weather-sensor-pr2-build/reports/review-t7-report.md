### Spec Compliance
- ✅ Spec compliant. Verglichen mit dem Brief (Steps 3–6) ist nichts ausgelassen, nichts Zusätzliches drin, nichts missverstanden.
  - Step 3: `_group_cuts`, `_stale_issue_key`, `async_resync_stale_issue` (sensor_liveness.py:568/580/587) und `translation_key=self._stale_issue_key(mapping_id)` (:564).
  - Step 4: Log-Fallunterscheidung (:513-526).
  - Step 5: beide Hooks in `__init__.py` (:1246-1250, :1844-1846).
  - Step 6: 8 Sprachen, Block direkt nach `weather_sensor_stale`.
  - Tests: 6 neue Fälle, `TestThePausedNotice` ab tests/test_sensor_liveness_coordinator.py:981.
- Benannte Checks:
  - **keep / Stundenrechnung = bisheriger Hinweis.**
    - `_stale_issue_key` liefert `ISSUE_WEATHER_SENSOR_STALE` genau dann, wenn `group_pauses` falsch ist oder `hourly_calculation_enabled` wahr ist. Issue-Id ist unverändert `f"{ISSUE_WEATHER_SENSOR_STALE}_{mapping_id}"` (:553, ebenso in `_retire_outages` :631), also unabhängig von der Variante.
    - Der `else`-Zweig des Logs ist Zeichen für Zeichen der alte Text. Der implizite String-Concat bindet vor dem Ternary, also korrekt; beide Zweige haben 4 `%s`.
    - Die Platzhalter kommen weiter aus `stale_issue_placeholders`.
    - Der bestehende Test tests/test_sensor_liveness_coordinator.py:265 pinnt den keep-Fall (Gruppe ohne Einstellung bekommt `ISSUE_WEATHER_SENSOR_STALE`).
  - **Umschalten schreibt den Hinweis in place um.**
    - Gleiche Id, nur `translation_key` wechselt; es bleibt kein zweiter Eintrag unter dem anderen Schlüssel.
    - Ein variantenabhängiger Id-Aufbau würde in den Tests als `KeyError` auf `weather_sensor_stale_0` auffallen.
    - Der Hook läuft nach `await self.store.async_update_config(data)` bzw. `await self.store.async_update_mapping(...)`, liest also den Zustand nach dem Schreiben.
  - **Re-Sync nur bei offenem Ausfall.** `async_resync_stale_issue` kehrt bei `not mapping` und bei `not any(o.end is None)` zurück, bevor `_sync_stale_issue` oder die Registry berührt wird. Test :1054 nutzt eine Registry, die bei Berührung `AssertionError` wirft, einmal mit `CLOSED_RECORD` und einmal mit `None`. Entfernte man einen der beiden Guards, wäre der Test rot.
  - **Quellenwechsel + Einstellung im selben Payload.** `_retire_outages(before)` leert vorher Record und Hinweis. Der Re-Sync findet dann keinen offenen Ausfall und legt nichts neu an.
  - **Umbenennen.**
    - Ein reines Umbenennen (ohne `on_silent_sensor` im Payload) berührt den Hinweis nicht. Das pinnen Test :1024 und der bestehende Test :843, und es ist unverändert zur Basis.
    - Kommt `on_silent_sensor` im selben Payload mit, übernimmt der Re-Sync den aktuellen Namen.
    - Die Aufgabenformulierung „Umbenennen aktualisiert den Hinweis“ widerspricht dem Plantest „a rename leaves the notice alone“. Gebaut ist der Plantest (siehe ⚠️).
  - **Log unterscheidet die Varianten:** Tests :981ff (pause → „no longer used“ und nicht „still used“; pause + Stundenrechnung → „still used“).
  - **Bestehender `_sync_stale_issue`-Wrapper** (`boom(mapping_id, name, outages)`, tests :641-648): Signatur unverändert, die Methode liest die Einstellung aus dem Store. `_FakeStore.get_mapping` existiert; `hourly_calculation_enabled` ist per `getattr(..., None)` robust gegen fehlendes `config`. Einzige Aufrufer von `_sync_stale_issue` sind in sensor_liveness.py (:418, :531), also keine weiteren Testdoppel betroffen.
  - **Übersetzungen** (per Skript gegen die Dateien geprüft, nicht nur aus dem Diff gelesen):
    - Alle 8 JSON laden.
    - Titel von `weather_sensor_stale_paused` ist in jeder Sprache identisch mit dem von `weather_sensor_stale`.
    - Platzhalter sind pro Sprache gleich: Titel `{group}`, Beschreibung `{entities}`, `{since}`, jeweils wie beim Schwesterblock.
    - Je 2 Absatztrenner; der neue Block steht direkt nach `weather_sensor_stale`.
    - Der Text stimmt mit dem Brief überein.
    - `tests/test_i18n_completeness.py` prüft den `issues`-Block (:257).
  - **Hooks in `__init__.py` im Speicherpfad:** siehe Minor 1.
- ⚠️ Nicht aus dem Diff prüfbar:
  - Die Optionsnamen im Hinweis („Keep the last value“ / „Letzten Wert behalten“ usw.) müssen den Panel-Beschriftungen aus Task 8 entsprechen.
  - Das Schema von `SmartIrrigationMappingView` (websockets.py:229ff, ohne `extra=ALLOW_EXTRA`) kennt `on_silent_sensor` noch nicht; das kommt laut Plan in Task 8. Bis dahin ist der Mapping-Hook über die HTTP-Route nicht erreichbar. Das ist Absicht, aber der Controller sollte nach Task 8 einmal Ende-zu-Ende prüfen.
  - Falls mit „Umbenennen aktualisiert den Hinweis“ gemeint war, dass `{group}` im offenen Hinweis nach einer Umbenennung nachzieht: das gibt es weder in der Basis noch hier.

### Strengths
- Der Hinweis-Schlüssel wird an einer Stelle (`_stale_issue_key`) aus dem Store gelesen. Der Startpfad (:418), der periodische Check (:531) und der Re-Sync laufen dadurch alle durch dieselbe Wahl, und die Signatur von `_sync_stale_issue` bleibt stabil.
- Die Bedingung `group_pauses(...) and not hourly_calculation_enabled(...)` spiegelt `_blocked_spans_for_zone` (calculation.py:~433-436) exakt, einschließlich striktem Identitätsvergleich der Stundenrechnung.
- Die Tests gehen durch die echten Einstiegspunkte (`async_update_mapping_config`, `async_update_config`, `async_check_sensor_liveness`) und nicht durch die Hilfsmethoden. Der `{}`-Marker in `_mock_store_coord` macht „unberührt“ prüfbar. Der Stundenrechnungs-Test deckt beide Richtungen ab.
- Gruppen auf keep bleiben byte-identisch: derselbe Log-Text, dieselbe Id, derselbe Schlüssel. Es kommt nur ein zusätzlicher Store-Lesezugriff pro `_sync_stale_issue` dazu.
- Der Diff ist sauber (180+/3−, keine CRLF-Rauschzeilen, keine Fork- oder Plan-Kürzel).

### Issues
#### Critical (Must Fix)
Keine.

#### Important (Should Fix)
Keine.

#### Minor (Nice to Have)
1. **Die zwei Re-Sync-Hooks sind ungeschützt** (`__init__.py:1246-1250`, `:1844-1846`).
   - `async_setup_sensor_liveness` (sensor_liveness.py:414-426) und der Check (:456-463) kapseln dieselbe Arbeit in `try/except` mit der Begründung „only a notice“. Die neuen Hooks laufen nach dem Schreiben und vor `async_dispatcher_send(..._config_updated)`.
   - Ein Fehler dort würde die Speicherung nicht zurückrollen (Store ist schon geschrieben), aber den Dispatch überspringen und die HTTP-Route mit 500 beenden: `SmartIrrigationConfigView` fängt nur `ValueError`, `SmartIrrigationMappingView` gar nichts.
   - Reale Fehlerquellen sind kaum erkennbar: `outages_of` wirft nie, `MAPPING_ID` ist immer da, `async_create_issue` ist Core. Im selben Zweig ruft die Basis `_retire_outages` ebenfalls ungeschützt auf. Deshalb Minor (planverbindlich).
   - Zur Härtung: Hook in `try/except Exception` mit `_LOGGER.exception(...)` wie im Setup, oder die Schleife in `async_resync_stale_issue` selbst kapseln.
2. **Die Hook-Tests pinnen die Reihenfolge nicht.**
   - `_mock_store_coord.get_mapping` liefert ein festes Mapping, und `store.config` wird vor dem Aufruf gesetzt (Tests :1012, :1032-1050). Verschöbe man den Hook vor das Schreiben, bliebe die Mutation unbemerkt.
   - Der Mapping-Test ändert nichts: die Gruppe ist schon `pause`. Er unterscheidet daher „Einstellung geändert“ nicht von „Schlüssel im Payload“ und prüft nur die Richtung zur Pause-Variante.
   - Ein Test mit dem echten `_FakeStore` (Einstellung keep → pause per `async_update_mapping`) würde beides pinnen.
3. **Kein Test, dass ein Config-Speichern ohne `CONF_HOURLY_CALCULATION` nicht neu synchronisiert.** Ein `if True` wäre unbemerkt. Folgenlos, weil idempotent, aber ungepinnt.
4. **`async_resync_stale_issue` ohne `@callback`.** Das Schwestermethoden-Muster (`async_teardown_sensor_liveness`, :435) und die HA-Konvention für synchrone `async_*`-Methoden im Loop verlangen es. Der Plan-Snippet hat es nicht.
5. **Doppelte Logik:**
   - Der Körper von `async_resync_stale_issue` wiederholt die Setup-Schleife (:414-421), und `name = mapping.get(MAPPING_NAME) or str(mapping_id)` steht jetzt viermal da.
   - `_group_cuts` und `_blocked_spans_for_zone` halten denselben Wahrheitswert nur per Docstring-Verweis zusammen. Ein Test, der beide für dieselbe Konstellation vergleicht, würde Drift verhindern.
6. **Wortlaut des Hinweises** („diese Werte werden nicht mehr verwendet“): Ein kumulativer Regenmesser (`DELTA`) wird von `_blocked_spans_for_zone` nie gesperrt (calculation.py:~449, `effective_aggregate != DELTA`). Für ihn stimmt die Aussage nicht ganz. Konservativ, planverbindlicher Text; nur zur Kenntnis.

### Assessment
**Task quality:** Approved
**Reasoning:** Alle Anforderungen sind umgesetzt und belegt. keep- und Stundenrechnungs-Gruppen behalten Id, Schlüssel, Platzhalter und Log-Text. Umschalten schreibt den Hinweis in place um, und ohne offenen Ausfall wird weder ein Hinweis angelegt noch die Registry berührt. Offen bleiben nur Härtungs- und Test-Stärke-Punkte (v. a. Minor 1 und 2).