# Eifel-Joe#8 PR 1 — Abweichungen vom Plan beim Bau (2026-10-04)

Der Plan (Revision 2) ist der freigegebene, probegelaufene Stand; Endstand-Baum des Probelaufs `d668d93e`.
Hier steht jede Abweichung, die beim Bau dazukam, mit Grund und Beleg. Am Ende in den Plan übernehmen
(„Berichtigungen beim Bau“).

## Task 1 — Quality-Review (Sonnet), Befunde I-1 und M-1 übernommen, M-2 abgelehnt, M-3 zurückgestellt

- **I-1 übernommen — neuer Test `test_the_limits_are_the_documented_ones`** in `tests/test_sensor_liveness.py`:
  pinnt `SENSOR_STALE_AFTER_SECONDS == 3 * 3600`, `SENSOR_LIVENESS_INTERVAL_SECONDS == 5 * 60`,
  `SENSOR_LIVENESS_STARTUP_GRACE_SECONDS == 10 * 60`. Grund: Alle anderen Tests leiten ihre Zeiten aus den Konstanten
  ab; die Doku nennt die Werte. Vom Koordinator geprüft: Die Stille-Grenze ist durch vorhandene Tests nur auf
  (8 min, 5 h) eingegrenzt (`test_home_assistants_own_downtime_is_not_an_outage`: frischer Bericht 8 min;
  `test_an_outage_spanning_a_restart_keeps_its_start`: 5 h fest), Intervall und Karenz gar nicht. Das Szenario
  des Reviewers (6 h überlebt) stimmt so nicht — 6 h tötet der Neustart-Test. Präzedenz für Literal-Pins im Repo:
  `tests/test_namespace_isolation.py::TestDerivedNotRestated::test_value_follows_the_domain`.
  Folge: Zählungen für `tests/test_sensor_liveness.py` in Tasks 2–6 je +1; Gesamt 75 → 76.
  Neue Mutationen für Task 14: M21 `SENSOR_STALE_AFTER_SECONDS = 4 * 3600`, M22 Intervall `600`, M23 Karenz `300`.
- **M-1 übernommen — Begründung der Aufbewahrung:** `const.py` „…: no window reaches back further.“ →
  „…, so they cover the same days as the readings.“; Test-Docstring entsprechend. Grund: Ein Fenster beginnt
  ungeklemmt am Watermark der Zone (`calculation.py:402`), gekürzt wird nur nach einer Rechnung
  (`calculation.py:545/627`, `continuous_update.py:546`); steht die Rechnung > 7 Tage, reicht ein Fenster weiter
  zurück. **Für den Plan von PR 2 notieren:** Fall „Fenster älter als die Aufbewahrung“ entscheiden (hinnehmen und
  dokumentieren, oder geschlossene Ausfälle erst fallen lassen, wenn sie älter sind als die älteste Pufferzeile).
- **Re-Review (07809037) → zweite Korrektur:** (a) Docstring des Pins behauptete „every other test derives its
  times from these constants“ — falsch (5 h / 8 min / 4 h fest in zwei Koordinator-Tests) und las sich, als nenne
  die Doku die 10 min. (b) Mein Ersatztext „cover the same days as the readings“ / „kept exactly as long as the
  reading buffer keeps rows“ stimmt nur für die Obergrenze: `BUFFER_RETENTION` ist die Kappe
  (`calculation.py:53-55` „may linger“), auf täglich rechnenden Installationen kürzt `_prune_mapping_buffer` bis
  zum ältesten Watermark (`calculation.py:463`, vgl. `const.py:664-666`). Neu: „may keep rows (its cap, …)“;
  Testname `test_closed_outages_are_kept_as_long_as_the_buffer_may_keep_rows`; Task-5-Commit-Message
  „…as long as the reading buffer may keep rows…“.
  **Vor dem PR erwägen:** Review-Korrekturen in ihre Task-Commits falten (Baum identisch prüfen), damit keine
  Commit-Message mit überholter Aussage auf der PR-Seite steht (07809037-Body: „Every other test derives …“).
- **Zweites Re-Review (b9e47294):** Aufbewahrung OK. Pin-Docstring „Most tests derive …“ weiter unzutreffend (per
  Zählung 7 von 62 Testfunktionen) → Docstring sagt nur noch, was er pinnt (dritte, letzte Textkorrektur, mit
  Task-2-Korrektur zusammen gebaut). Nit im Commit-Body „at most“ bleibt (erledigt sich beim Falten).
- **M-2 abgelehnt** (Leerzeile nach dem Liveness-Block, Event-Gruppe): `const.py` hat keine Leerzeilen zwischen den
  Gruppen; der Strahlungsblock läuft genauso in den nächsten über.
- **M-3 zurückgestellt — „ledger“:** im Paket 45× für die Wasserbilanz der Zone (`auto_calc.py`, `live_estimate.py`,
  `async_guard_ledger_staleness`). Bei uns meist qualifiziert („outage ledger“, „sensor-liveness ledger“), aber auch
  nackt (Mixin-Docstring „the ledger“, Testnamen `…_empties_the_ledger…`). Umbenennen träfe Blöcke in 7 Tasks →
  dem User vor dem PR als Entscheidung vorlegen (Kandidat: „outage record“).

## Task 2 — Quality-Review (Sonnet): I1 + M4 übernommen (nur Tests), M1–M3/M5 nicht

- **I1 übernommen:** R7 (nur Sensorfelder) hing an einer ungetesteten Zeile — die Wetterdienst-/Statik-Felder des
  ersten Tests hatten keine Entität und fielen schon an `if not entity_id` heraus. Jetzt mit liegengebliebener
  Entität (`weather_service`, `static`, `none`) und einem Sensorfeld ohne Entitäts-Schlüssel (Setup-Wizard,
  `ip-setup-wizard.ts:265-267`). Mutation „Quellprüfung löschen“ muss rot werden.
- **M4 übernommen:** Gegenbeispiel `sensor.input_number_mirror` im zweiten Test (nur die Domain ist ausgenommen);
  Mutation „Teilstring statt Domain“ muss rot werden. Zählung bleibt (4 Tests in der Datei).
- **M1 (Leerraum-Entität `"   "`) abgelehnt:** Das Feld liest wirklich nichts; ein Hinweis darauf ist kein
  Fehlalarm. Produktionscode bleibt wie freigegeben.
- **Re-Review (6b11663a, dd82ac60): OK.** Offen als Text-Politur (mit der nächsten Korrektur-Runde bauen):
  P1 Testkommentar „A field switched away from a sensor can keep its old entity.“ → das Panel leert die Entität
  beim Quellwechsel (`view-mappings.ts:513-514`), nur andere Clients lassen sie stehen; P2 im Wizard-Fall
  `MAPPING_PRECIPITATION` statt `MAPPING_CURRENT_PRECIPITATION` (der Wizard bietet `sensor` für Temperatur, Feuchte,
  Niederschlag). Commit-Message-Nits (dd82ac60 „Only a few tests …“, 6b11663a „so it fails …“) erledigen sich
  beim Falten.
- **P1/P2 gebaut** als eigener Commit mit den Task-3-Korrekturen.
- **M2, M3 abgelehnt** (Nicht-String-Entität nur per HTTP-POST, je Gruppe in `try/except`; Groß-/Kleinschreibung nur
  per HTTP-POST). **M5** nicht jetzt; **für den Plan von PR 2 notieren:** „as before“ im Modul-Docstring
  (`sensor_liveness.py:11-12`) veraltet mit dem Schnitt.

## Task 3 — Quality-Review (Sonnet): I1, I2, M3, M4, M5b übernommen; M5a abgelehnt

- **I1:** `first_report_after` — Gültigkeit der Geschwister ungepinnt (nur `own` getestet). Szenario: Batterie-Entität
  geht per MQTT-`expire_after` mitten im Ausfall auf `unavailable` → Ausfall endet Stunden zu früh, falsches `until`.
  Test `test_an_unavailable_sibling_is_not_a_return`; Mutation M26.
- **I2:** `last_sign_of_life` — fehlende eigene Entität bei lebendem Gerät ungepinnt (Test übergab `[]`); Docstring
  ließ „missing“ aus. Szenario: Nutzer deaktiviert die gewählte Entität → Registry-Eintrag mit Gerät, Geschwister
  leben → Fehlimplementierung hielte das Feld für lebendig, Hinweis käme nie. Test
  `test_a_missing_entity_is_silent_whatever_its_device_does`; Docstring „missing, unavailable or unknown“; M27.
- **M3:** `changed == start` ist nicht „danach“ (`>=` überlebte) → Test `test_a_change_at_the_start_itself_is_not_after_it`; M28.
- **M4:** ohne Gerät markiert die Entität ihre eigene Rückkehr (auf Unit-Ebene ungepinnt, Task 9 tötet es später) →
  Test `test_without_a_device_the_entity_marks_its_own_return`; M29.
- **M5b:** Docstring `first_report_after` + „Unavailable or unknown states do not count“ und „This only dates a
  return; whether the outage has ended is ``last_sign_of_life``'s call.“
- **M5a abgelehnt:** „an outage that spans a restart keeps its start“ ist richtig — meldet die Entität nach dem
  Neustart frisch, überspannt der Ausfall den Neustart nicht (er schließt; Task-9-Test pinnt beide Seiten).
- Zählung `tests/test_sensor_liveness.py`: nach Task 3 **17**; Task 4 → 25, Task 5 → 33, Task 6 → 37, Task 12 → 45;
  vier Liveness-Dateien zusammen **80** statt 75. Mutationen jetzt M1–M29 (`probe_mutate3.py`).

## Task 4 — Quality-Review (Sonnet): I-1, I-2, M-1, M-2 übernommen (Härtung des Lesers); M-3 nicht

- **I-1 (Produktionscode, Abweichung vom Plan):** `Outage.from_store`/`outages_of` waren nicht total, obwohl der
  Docstring es verspricht: `fields=5`, `sensor_outages=5` → `TypeError`; `fields="Temperature"` → Einzelzeichen;
  `fields=[1, 2]` gelesen, dann wirft der Hinweistext (`", ".join`). Der Leser läuft in Task 10 im **Setup ohne
  try/except** → `async_setup_entry` scheitert bei jedem Neustart, danach liefen auch `async_resume_self_closing_runs`
  & Co. nicht. Realistischer Auslöser: production bekommt PR 1 vor dem Merge; ändert das Review die Datensatzform,
  liest der gemergte Code Altdatensätze. → `fields` muss Liste aus `str` sein, sonst verwerfen; Nicht-Liste in
  `outages_of` → `[]`; NOT-TO-DO-Absatz im Docstring (Hausstil wie `helpers.coerce_stamp`).
- **M-1:** vorhandener, aber unlesbarer `end` → Datensatz verwerfen (sonst kam ein geschlossener als offen zurück:
  falscher Hinweis bis zur ersten Prüfung, doppeltes End-Event).
- **I-2:** `outages_of` hatte keinen Test; 5 Fehlimplementierungen von `from_store` blieben grün. Neu: `_record`,
  fünf Parametrisierungsfälle, `test_a_record_without_its_optional_keys_still_reads`, Klasse `TestOutagesOf`
  (1 + 3 Fälle). Zählung Datei +10 → 35 nach Task 4; Task 5 → 43, Task 6 → 47, Task 12 → 55; Liveness gesamt **90**.
  Mutationen M30–M34.
- **M-2:** Klassen-Docstring von `Outage` sprach im Präsens von einem Vergleich mit Pufferzeilen (macht erst PR 2/3)
  → „One stretch in which …“ / „Stored as ISO strings on HA's clock: the frame the reading buffer's row stamps are in.“
- **Plan-Hinweis Task 10 übernommen:** Wiederherstellung je Gruppe in `async_setup_sensor_liveness` in
  `try/except Exception` + `_LOGGER.exception` (wie Task 9) — eine Meldefunktion darf das Setup einer
  Bewässerungssteuerung nicht kippen. Test „eine kaputte Gruppe stoppt das Setup nicht“. M18-Anker anpassen.
- **Plan-Hinweis Task 11 (offen, beim Bau entscheiden):** `_retire_outages(before)` steht im Quellwechsel vor der
  Neuverankerung der Zonen-Watermarks; mit dem totalen Leser praktisch nicht mehr werfend.
- **M-3 nicht** (Ausschmückung: `entity_id`/`device_id`-Typen, `__post_init__`, Log beim Verwerfen).
- **Dem User melden** (Abweichung im Produktionscode).
- **Re-Review (90be02bc): NEIN, nur Wortlaut** — „``fields`` that is not a list of strings“ stimmt nicht für falsy
  Werte (`None`, `0`, `""`, `{}` … → keine Felder, gewollt) → „(missing or empty means none)“. Dazu billige Pins:
  `_record(fields=["Temperature", 1])` (tötet `all`→`any`, M35), Optional-Keys-Test parametrisiert über `_record()`,
  `fields=None`, `fields=[]` (tötet `raw.get("fields", [])`, M36). Gebaut mit der Task-5-Korrektur-Runde.
  Zählung Datei +3. Vorgreifender Satz „The ledger is read in the setup and in the configuration paths“ stimmt erst
  ab Task 10/11 — bleibt (Modul-Docstring beschreibt durchgehend den Endstand); falls Task 11 anders entschieden
  wird, Satz anpassen.

## Task 5 — Quality-Review (Opus): Important 1 + Minor 2/3/4/6 übernommen; Minor 5 nicht

- **Important 1 (nur Tests):** drei plausible Mutanten überlebten die ganze geplante Suite (kein Test mit geschlossenem
  Eintrag derselben Entität): geschlossene Einträge in `still_open` (Sensor nach Erholung 7 Tage nicht meldbar),
  behaltene geschlossene zusätzlich in `closed` (End-Event alle 5 min), Schließen schon bei `recovered > start` ohne
  neueres Lebenszeichen (verletzt R1). Tests `test_a_sensor_that_recovered_can_fall_silent_again`,
  `test_a_change_elsewhere_on_the_device_does_not_end_a_silent_field`, dazu `test_a_late_check_closes_and_reopens_in_one_go`
  und voller Tupel-Vergleich im Aufbewahrungstest. M37–M39.
- **Minor 6:** Docstring `advance_outages` präzisiert (Rückfall-Ende, „without an open one“, „stays open“).
- **Minor 2/3/4 → Task 9:** Events `closed` vor `opened` (sonst letztes Event `stale: false` bei stummem Sensor nach
  Schließen+Wiederöffnen); Log-Zeile neutral („the outage of %s is over“ statt „reports again“ — auch für nicht mehr
  gelesene Entitäten); `last = open_start.get(entity_id, now)` (offener Ausfall ohne gemerktes Lebenszeichen endet
  nicht „jetzt“). Zwei Koordinator-Tests. Commit-Message Task 9 ergänzt (`overrides/t9-*`).
- **Task 10 (aus Task-4-Review):** `try/except` je Gruppe in `async_setup_sensor_liveness` + Test
  `test_one_broken_group_does_not_stop_the_setup` (`overrides/t10-*`).
- **Minor 5 nicht** (`end=max(now, start)` bei Uhrsprung > 3 h zurück: Ausschmückung).
- **Für PR 2 notieren:** `first_report_after` zählt Änderungen der Geschwister aus der Zeit, in der die eigene Entität
  noch `unavailable` war → bei einem R1-Ausfall kann das Ende vor der Rückkehr der eigenen Entität liegen
  (Schnittlänge).
- Zählungen: `test_sensor_liveness.py` 49 nach Task 5 → 53 (Task 6) → 61 (Task 12); Koordinator 19/24/29;
  Liveness gesamt **99**. Mutationen M1–M39 (+ M40/M41 bei Task 9/10).
- **Re-Review (42b1c92d, 49c13f1f): NEIN, nur Wortlaut** — (1) Docstring `advance_outages` „Opens an outage for an
  entity without an open one …“ widerspricht dem Schließen+Wiederöffnen-Test → umgeordnet nach dem Code (erst
  schließen/beenden, dann je Entität ohne offenen Ausfall öffnen; „so it does not stay open“); (2) „(missing or empty
  means none)“ stimmt nicht für `0`/`False` → „(a missing or falsy value means none)“; (3) Commit-Message 49c13f1f
  „an entity is opened only once“ falsch → beim Falten berichtigen; optional Testname → „…with_no_fields_and_no_device…“.
  Gebaut mit der Task-6-Korrektur-Runde.

## Task 6 — Quality-Review (Sonnet): I-1 (Variante A), I-2, M-1, M-2, M-4, M-5 übernommen; M-3 nicht

- **I-1 (Produktionscode, Event-Vertrag):** Event-Stempel `since`/`until` waren naiv; ein Verbraucher liest sie per
  `as_timestamp` in der Prozess-Zone (Docker ohne `TZ=`: still um den UTC-Offset falsch). Konvention im Repo:
  `irrigation_plus_recurring_schedule_triggered` sendet `dt_util.as_local(now).isoformat()` (begründet in
  `scheduler.py:2317-2325`). → `dt_util.as_local(...)` im Payload; Docstring nennt den Grund. Folgen: Task-9-Assertion
  `until == dt_util.as_local(back).isoformat()`; Event-Zeile der Doku (Task 13) „both in Home Assistant's time zone,
  with offset“. **Dem User melden** (öffentlicher Event-Vertrag gegenüber dem Plan geändert).
- **I-2:** Hinweis mit geschlossenen neben offenen Ausfällen (der echte Eingang aus Task 9) ungetestet →
  `test_closed_outages_do_not_shape_the_notice`. **M-1:** Gleichstand nach `entity_id` (tote Station: Normalfall) →
  `test_entities_that_fell_silent_together_are_listed_by_entity_id` (M41). **M-2:** End-Event voll gepinnt.
- **M-4 → Task 13:** Doku-Satz „It fires once per sensor entity …“. **M-5 → Task 12:** Platzhalter ⊆ {group,
  entities, since} (`import re`).
- **Fixture-Fund beim Bau:** `monkeypatch` auf `dt_util.DEFAULT_TIME_ZONE` erzeugte einen Teardown-Fehler im
  Folgetest (monkeypatch wird vor `hass` angelegt, erst nach `verify_cleanup` zurückgebaut) → Repo-Idiom
  `set_default_time_zone` mit Rückstellung (wie `tests/test_store_stamp_migration.py:36-44`).
- **M-3 nicht** (leere `fields` → „sensor.t ()“ nur bei beschädigtem Ledger). Ausschmückungen nicht.
- Zählung `test_sensor_liveness.py` 55 nach Task 6 → 63 (Task 12); gesamt **101**. Mutationen M40–M44 (M42–M44
  für Tasks 9/10), M9/M18 mit neuen Ankern.
- **Erwarteter Endbaum `33ae7dd0`:** alle bis hier beschlossenen Korrekturen eingerechnet (`apply_corrections.py`,
  Quellen = `overrides/t{9,10,12,13}-blocks.md`), nicht aus dem Gebauten abgeleitet.
- **Re-Review (d0a8fad7, b42e07a9): OK.** Nits für die nächste Text-Runde: (1) „a consumer would read a naive one in
  the process's zone“ → „may read“; (2) Modul-Docstring „pure functions“ → „plain functions“ (der Payload liest HAs
  Zeitzone); (3) `_record(fields="")` in die Optional-Keys-Parametrisierung (pinnt „falsy“ über None/[] hinaus;
  Zählung +1 → 56 nach Task 6, 64 nach Task 12, gesamt **102**). Plandatei am Ende berichtigen (Task 6/9/13-Blöcke).

## Task 7 — Quality-Review (Opus): I-1 übernommen (Produktionscode), M-1 + M-3 übernommen; M-2 nicht

- **I-1 (Produktionscode, Design-Lücke gegenüber R3 „Lebenszeichen über Neustart“):** Ein sauberer Neustart verlor
  das aufgefrischte Lebenszeichen. `_async_flush_on_stop` plant nur bei `_buffers_dirty` einen Save; HA schreibt beim
  Herunterfahren nur einen *anstehenden* Save (`helpers/storage.py`); der Setter plante nichts. Im Abfrage-Betrieb
  (Puffer meist sauber) bis zu ~1 h Lebenszeichen verloren → nach dem Neustart beginnt ein Ausfall zu früh (Start =
  veraltetes Lebenszeichen), bei täglicher Abfrage sofort nach der Karenz. Die Neustart-Tests rufen vorher selbst
  `async_save()` und sahen es nicht. Vom Reviewer mit echtem HA-Kern 2024.12.5 belegt; Koordinator: Stop-Listener ist
  immer scharf (`async_load` + jedes Setup), `_data_to_save` nur zur Schreibzeit gerufen.
  Fix: Merker `_last_seen_dirty` (Setter setzt ihn bei Änderung; Stop-Flush schreibt bei `_buffers_dirty or
  _last_seen_dirty`; Rücksetzen in `_data_to_save` und `async_delete`); bewusst NICHT im 10-min-Backstop → weiter kein
  Schreiben je Prüfung. Tests: Stop schreibt; unverändert → kein Stop-Write; gelöschte Konfiguration nicht
  zurückgeschrieben. Mutationen M45–M47. **Dem User melden.** Spec Präzisierung 3: Satz zum Mitschreiben beim
  sauberen Herunterfahren ergänzen.
- **M-1:** `sensor_last_seen`, das kein dict ist (Hand-Edit/anderer Build), lud ungeprüft → Task 9 `remembered.get`
  → `AttributeError` alle 5 min für die Gruppe. → `_as_last_seen` beim Laden (wie `_as_buffer`); Test; M48.
- **M-3:** Kommentare präzisiert („Bounded: at most one open outage per entity, closed ones go … after their end“;
  „a clean stop writes it too“; Setter: „Unlike data_last_entry nothing can rebuild it …“, „keeps a copy“).
- **M-2 nicht** (Testlücken ohne Folgen: `.get(KEY, [])`, unbekannte ID, Panel-Kürzen — das Schema sperrt ohnehin).
- Zählung Store-Tests 6 → **10**; gesamt **106** (64 + 10 + 29 + 3).
- **Re-Review (55c2c422): OK** — mit echtem HA-Kern 2024.12.5 geprobt (Backstop schreibt nicht; Stopp schreibt; unverändert
  kein Stopp-Write; nach Löschen nichts zurück; Zeilen bleiben). Text-Politur für später: Debug-Zeile in
  `_async_flush_on_stop` („buffered sensor readings“), Testname `…_not_a_mapping_…` → `…_not_a_dict_…` („mapping“ heißt
  hier Sensorgruppe); Commit-Message „up to an hour“ → „up to one polling interval“ (beim Falten).

## Task 8 — Quality-Review (Opus): plantreu, HA-API korrekt (2024.12.5 / Floor 2025.5.0 / dev); I-1 = ENTSCHEIDUNG USER

- Versionsboden ok (`last_reported` seit HA 2024.4.0; Floor 2025.5.0). Registry-Aufrufe korrekt; nur `last_reported`
  sieht unveränderte Pushes; `as_local` exakt; Test-Stolperdraht wirksam.
- **I-1 (Design R1, User entscheidet vor dem Pre-Release):** Geschwister = ALLE Entitäten des Geräts schließt Helfer
  ein, die HA automatisch ans Gerät der Quell-Entität hängt (`utility_meter`, `integration`, `statistics`,
  `derivative`, Templates) und die im eigenen Takt schreiben (Tageszähler-Reset 00:00 → jede Nacht Fehl-Entwarnung,
  zerstückelte Ausfälle); ESPHome-`update`-Entität (gleiches Entry, alle 5 min) → Deep-Sleep-Station nie erkannt.
  Vorschlag: Geschwister nur aus dem Config-Entry der gemappten Entität, zusätzlich nur `sensor`/`binary_sensor`;
  Signatur/Rückgabe gleich (Task 9 unberührt). **HA-Prod geprüft (lesend, 2026-10-04):** Gerät „WS2900_V2.01.18“ mit
  26 Entitäten, alle `ecowitt`, nur `sensor`/`binary_sensor`, keine fremden → für die eigene Anlage wirkungslos,
  für andere Nutzer verbreitet (Tageszähler am Regensensor). Empfehlung: übernehmen.
- **M-1 (Spec, nicht PR 1):** eigene Entität „gültig“ ist lockerer als der Lesepfad (Nicht-Zahlen wie „n/a“ bei
  Template/REST ohne Einheit) → für PR 2 notieren.
- **M-4 (Grenzen, intern dokumentieren):** Zeitumstellung (naiver Rahmen: Vorstell-Nacht öffnet 1 h zu früh,
  Rückstellung 1 h zu spät/mehrdeutig); MQTT-retained/Z2M-Republish beim Neustart beendet einen offenen Ausfall
  (Fehl-Entwarnung, Neuöffnung nach 3 h); Umbenennen/Icon/Bereich der stummen Entität schreibt den Zustand neu
  (Fehl-Entwarnung). → Spec „Grenzen“; ob in die Nutzer-Doku: User.
- M-2/M-3 nicht (optional).

## Task 9 — gebaut mit den Berichtigungen (a)–(d) (08ac0d33)

- **RED-Vorhersage des Plans ungenau:** 14 der 15 neuen Tests scheitern im Helfer `_coord` an
  `monkeypatch.setattr(sensor_liveness, "_issue_registry", …)` (Attribut existiert vor Step 3 nicht, `raising=True`),
  nicht an `async_check_sensor_liveness`; nur der Hinweis-Test zeigt die erwartete Zeile. Rot aus dem richtigen Grund
  (fehlende Implementierung) → Plantext berichtigen.
- GREEN Koordinator 19, Hinweis 1; Mutationen „last = now“ und „Schleifen vertauscht“ je genau ihr Test rot.

## Task 9 — Quality-Review (Opus): Ready to merge für Task 9; I1 = ENTSCHEIDUNG USER; M1/M2/M4/M6/M8a übernommen

- **I1 (Spec „Schließen“, User entscheidet vor dem Pre-Release):** `first_report_after` datiert das Ende auf die
  früheste Änderung IRGENDEINER Geräte-Entität nach `start`. Ist nur die eigene Entität ausgefallen (R1: `unavailable`,
  Gerät lebt), zieht eine Geschwister-Änderung während des Ausfalls das Ende nach vorn. Probe (voller Ablauf):
  `sensor.temp` unavailable ab 06:00, Batterie ändert sich 06:30, Start-Event 09:05, Rückkehr 11:58 → Liste
  `start 06:00, end 06:30`, End-Event `until 06:30` (vor dem Start-Event!). PR 1: falsches öffentliches `until`;
  Feldtest-Daten (R9) verfälscht; PR 2 schnitte nicht. (Opus-Review Task 5 hatte es für PR 2 angemerkt.)
  Vorschlag (a): eigene Änderung zuerst — `if own is not None and own.valid and own.changed > start: return own.changed`,
  sonst Geräte-Minimum (stilles Feld wie Regenmesser). Dreht `test_the_earliest_change_after_the_start_marks_the_return`
  um. Empfehlung: übernehmen (folgt R1s Grundsatz „eigene Entität stumm, egal was das Gerät tut“).
- **M1 (Test):** `test_one_broken_group_does_not_stop_the_others` prüfte Gruppe 1 nicht (stummes Schlucken bliebe grün)
  → Gruppe 1 unberührt, nur Gruppe 2 geschrieben, genau ein ERROR-Log.
- **M2 (Kommentar):** NOT-TO-DO an `async_check_sensor_liveness`: kein `await`, das die Loop abgibt, zwischen Lesen
  einer Gruppe und Zurückschreiben (sonst überschreibt die Prüfung eine vom Quellwechsel geleerte Liste).
- **M4 (Test):** Gruppe mit offenem Ausfall, aber ohne verbliebenes Sensorfeld → Ausfall endet, Hinweis weg.
- **M6 (Log):** `_retire_outages` beendet Ausfälle ohne Log-Zeile (R6: INFO beim Schließen) → INFO-Zeile.
- **M8a:** `now` keyword-only (`*, now=None`) — schützt davor, HAs aware-UTC-`now` positionell zu übergeben.
- Nicht: M3 (Hinweis bei jeder Prüfung abgleichen), M5 (Log-Flut-Drossel), M7 (DST → Spec „Grenzen“), M8 Rest.
- Gebaut nach Task 11 (gleiche Testdatei).

## USER-ENTSCHEIDUNGEN 2026-10-04 (im Chat, AskUserQuestion)

- **D1 Geschwister (R1):** „Gleiche Integration + sensor/binary_sensor“ — nur Entitäten desselben Geräts aus dem
  Config-Entry der gemappten Entität und nur `sensor`/`binary_sensor` bürgen (Helfer wie `utility_meter`, Updates
  nicht). Umsetzung F3 (`SENSOR_LIVENESS_SIBLING_DOMAINS` in `const.py`, `_entities_of_device`, Test). Doku Task 13:
  „any sensor of that device from the same integration“, „Helpers attached to the device, such as a utility meter, do
  not count.“ Spec R1 präzisieren.
- **D3 Ende (Spec „Schließen“):** „Eigene Rückkehr zuerst“ — `first_report_after`: hat sich die eigene Entität nach
  dem Beginn geändert, ist das das Ende; sonst (stilles Feld) die früheste Geräte-Änderung. Umsetzung F4.
- **D2 Benennung:** „ledger“ → „outage record“, ein Umbenennungs-Commit nach Task 13.

## Task 10 — Quality-Review (Sonnet): Important 1 + 2 übernommen (nur Tests) → F2

- Timer-Vertrag ungepinnt (Ziel, Intervall, Karenz scharf stellen, `now` nicht weiterreichen, zweites Setup ersetzt
  den Timer) — gemessen 5 Mutanten überlebten (u. a. Timer-Ziel = Check direkt → aware-UTC-`now` → TypeError je
  Gruppe, verschluckt → keine Erkennung). → zwei Tests. AST-Test zählte jeden Aufruf irgendwo in der Funktion (auch
  in `if`, ohne `await`) → `_own_statements_of` (nur Rumpf-Anweisungen, `await` geprüft).
- Minor 3–8 nicht (Karenz-Messkante 2./3. Tick, DST, Setup-Fehler nach Timern, Hinweis heilt nicht, Platzierung,
  `patch` ungenutzt).

## Task 11 — gebaut (95d20384): RED/GREEN wie Plan; Suite 3716, Namen identisch

## Task 11 — Quality-Review (Opus): I-1, I-2, M-1, M-3, M-4 übernommen (Runde B); M-2, M-6 nicht; M-5 offen

- **I-1 (Plan-Korrektur, Implementierungsdetail):** Reset und Quellwechsel leerten auch `sensor_last_seen`. Ein
  Sensor ohne gültigen Zustand (z. B. ESPHome setzt verlorene Geräte `unavailable`) galt danach als „nie gesehen“ →
  Hinweis 3 h weg, kam mit „Reset + 5 min“ als Beginn zurück (Probe A/F). Lebenszeichen beschreiben das Gerät, nicht
  die Messwerte → bleiben; die Prüfung schreibt sie ohnehin nur für die gelesenen Entitäten neu (ersetzter Sensor fällt
  binnen 5 min heraus). Ausfall-Liste wird weiter geleert (User-Entscheidung unberührt). Test: Reset bei stummem Sensor
  → nächste Prüfung öffnet mit echtem Beginn. **Dem User melden.**
- **I-2:** (a) Quellwechsel nur gegen Mock-Store getestet (Mutant „Store nach dem Schreiben neu lesen“ grün) → Test
  gegen echten Store in `test_sensor_liveness_repair.py`; (b) Reset-Test mit nur einer Gruppe (Mutant „Retire hinter
  die Schleife“ grün) → zwei Gruppen.
- **M-1:** Offen-Filter in `_retire_outages` ungepinnt → `test_only_open_outages_are_ended`,
  `test_closed_outages_alone_end_nothing`.
- **M-3:** Kommentare (`__init__.py` Quellwechsel, `calculation.py` Reset) und `_retire_outages`-Docstring präzisiert.
- **M-4:** Event-Doku (Task 13): „also false when its sensor group stops tracking the outage: … ; `until` is then the
  time of that change, and a sensor still silent after a reset starts a new outage“.
- **M-5 (offen, Folge-Issue):** Entfernen/Deaktivieren der Integration lässt offene Hinweise bis zum Neustart stehen,
  ohne End-Event (`async_remove_entry` ruft kein `_retire_outages`). Spec sagt „kein Hinweis überlebt die
  Konfiguration“. Nicht in PR 1; dem User nennen.
- M-2 (Hinweis behält alten Gruppennamen nach Umbenennen bis zum nächsten Übergang) und M-6 (try/except an den
  Aufrufstellen) nicht.
- Zählung nach Runde B: Koordinator 36, Hinweis 4; gesamt nach Task 12 **115** (65 + 10 + 36 + 4).

## Runde A (e9bcf4d6 … 3498b403) — Re-Reviews

- F1/F4 (Task-9-Reviewer): Code OK; I1-Szenario mit Probe gegen c1bef26c: Ende = eigene Rückkehr 11:58, `until` nach dem
  Start-Event; stilles Feld fällt auf früheste Geräte-Änderung zurück. NEIN nur Text: Docstring `advance_outages` nannte
  noch die alte Regel → Runde B, B3. Spec „Schließen“ präzisieren (P1).
- F2 (Task-10-Reviewer): OK; M1–M6 fallen an den neuen Tests, Verdrahtungstest tötet alle sechs Varianten.
- F3 (Task-8-Reviewer): **NEIN** — Filter verglich mit dem Entry der GEMAPPTEN Entität; ist diese selbst ein Helfer am
  Stationsgerät (Tageszähler, Template mit gewähltem Gerät), bürgte die Station nicht mehr → Fehlalarm an trockenen
  Tagen (mit echten Registries belegt). → Runde C, C1: bürgen dürfen das eigene Entry UND das Entry, dem das Gerät
  gehört (`config_entry_id` neuer, `primary_config_entry` älter, per `getattr`); Helfer bürgen weiter nicht für die
  Station. Texte: Template hängt am gewählten Gerät; Button hat keinen Takt. (Im Sinn der User-Entscheidung D1.)
- Suite nach Runde A: 7 / 3721 / 9 / 415, Namen identisch.
- Runde C, C2: Umbenennung „ledger“ → „outage record“ (16 Stellen + Task-13-Docstring/Message bereits in der
  Auftragsdatei berichtigt, `overrides/t13-*`).

## Runden B (4103c879, 2141d161, ee88cb75) und C (5672d552, b91d9a67, bae6a9d7) — gebaut, re-reviewt

- B1 Lebenszeichen bleiben bei Reset/Quellwechsel (RED 3, GREEN; Mutation „LAST_SEEN wieder leeren“ rot, zusätzlich
  der Reset-Test). B2 Echt-Store-Quellwechsel, Reset über zwei Gruppen, nur offene enden (Mutanten je rot; „Store neu
  lesen“ fängt NUR der Echt-Store-Test). B3 Docstring `advance_outages` (Ende = Rückkehr des Feldes).
- Re-Review B (Task-11-Reviewer, Probe A/F gegen 2141d161: Ausfall nach +5 min mit echtem Beginn wieder offen): NEIN nur
  wegen `_retire_outages`-Satz „a sensor that is still silent starts a new outage“ (gilt nur für noch gelesene
  Sensoren) → C3. Event-Doku Task 13 ergänzt: „…after a reset, or one a source change left in place, starts a new
  outage“.
- C1 gemappter Helfer (RED `[]`, GREEN; Mutationen „nur eigenes Entry“, „Domain-Zeile weg“ rot). C2 Umbenennung (16
  Stellen, `git grep -i ledger` leer). C3 Satz in `_retire_outages`.
- Re-Review C1 (Task-8-Reviewer, Registry-Probe 5 Fälle inkl. MQTT-Gerät von Shelly übernommen, Gerät ohne Besitzer,
  Helfer ohne Gerät): Code OK; `config_entry_id`-Zweig per Quelle in HA 2026.9.4 belegt (**berichtigt nach dem
  Abschluss-Review, M3: NICHT Haupt-CI** — die Haupt-CI läuft auf Python 3.13 und bekommt höchstens HA 2026.2.x, dort
  hat `DeviceEntry` nur `primary_config_entry`; der `config_entry_id`-Zweig läuft also nur live), Floor-Job nimmt
  `primary_config_entry`. NEIN nur Docstring-Begründung (Station bürgt, weil ihr Entry das Gerät BESITZT; eigenes Entry
  zählt, wo eine andere Integration besitzt/kein Besitzer) → C4 (mit Task 12 gebaut).
- Suite nach Runden B+C: 7 / 3725 / 9 / 415, 422 Namen identisch. Mutationsliste `probe_mutate4.py`: 59 Mutationen,
  alle Anker genau einmal (Stand bae6a9d7).

## Task 12 — Quality-Review (Sonnet): technisch sauber; zwei Ein-Wort-Korrekturen + Test-Härtung übernommen

- Alle 16 Strings mit der echten `intl-messageformat` 11.2.8 (Panel-Bibliothek) formatiert: parsen, alle drei Werte
  eingesetzt. Quellen-Namen in allen 8 Sprachen wörtlich wie `panels.mappings.cards.mapping.sources.static`.
- **es (Important):** „Este aviso desaparece solo cuando …“ liest sich als „nur wenn“ → „desaparece por sí solo cuando“
  (wie `panels.zones.help.update_all` „por sí solo“).
- **it (Minor):** „la sorgente «Valore statico»“ → „la fonte …“ (Panel-Begriff `Fonte`, „sorgente“ 0× in den
  it-Katalogen).
- **Test-Härtung:** in der Platzhalter-Schleife `assert not re.search(r"'[{}<>]", text)` (ASCII-Apostroph vor Klammer
  legt in ICU die Ersetzung still) und Klammern balanciert = Anzahl benannter Platzhalter.
- Beobachtung (nicht PR 1): no-Panel „sensorguppe“ (20×) Tippfehler — eigener Frontend-Commit irgendwann.

## Abschluss-Review (Opus, e9c79ec4..07576b78): „With fixes“, am Code kein Fehler — Bewertung

Volltext: `final-review-opus.txt`. Bewertet nach receiving-code-review, Belege je Punkt:

- **I1 Historie falten — übernommen, Zeitpunkt nach dem Live-Test, vor dem PR; Entscheidung USER.** Belegt per
  `git log`: eine Message kündigt an („the outage will be compared with“, Task 4) — das verletzt die Regel „kein Text
  von PR 1 verspricht einen Schnitt“; „ledger“ steht in sechs Messages; weitere beschreiben überholtes Verhalten.
  JustChr squasht, GitHubs Standard-Squash-Message hängt alle Messages an. Faltung mit identischem Baum
  (`git diff <alt> <neu>` leer); der Task-für-Task-Stand bleibt als lokaler Ref erhalten.
- **I2 PR-Text nennt die Abweichungen vom #188-Vorschlag (a–f) — übernommen**, Task 16.
- **M1 Neustart-Test über STOP/FINAL_WRITE — übernommen, Begründung des Reviewers aber widerlegt.** Probe
  (`m1probe_run.py`): Mit der Task-7-Mutation (Stopp-Flush nur bei `_buffers_dirty`) bleibt auch der neue Test GRÜN —
  der Ausfall-Schreibvorgang plant ein Speichern, das FINAL_WRITE samt Lebenszeichen schreibt. Den Task-7-Verlust
  hält `test_sensor_liveness_store.py` fest (unter der Mutation 1 failed). Was der Umbau wirklich bringt: geplantes
  Speichern abgeschaltet (`async_schedule_save` → `return`) → neuer Test ROT, alter (Speichern von Hand) GRÜN; ohne
  FINAL_WRITE → rot. → Commit E, Gegenprobe am Endstand (`probeE_s0.py`) rot/grün.
- **M2 Doku — übernommen** (gemappter Helfer wird vom Gerät gedeckt; YAML-`utility_meter` ohne Gerät wirkt an
  trockenen Tagen stumm, ein per UI angelegter hängt am Gerät der Quelle) → E.
- **M3 — übernommen:** Vermerk oben berichtigt; im PR-Text keine CI-Abdeckung für den `config_entry_id`-Zweig
  behaupten; Live-Test braucht ein Gerät mit Geschwister-Sensoren (Gerät C mit zwei Sensoren ist im Testplan).
  Fork-CI: `pytest.yml` läuft nur bei push auf main/master und bei pull_request auf main/master — ein Push des
  Feature-Branchs oder von `production` startet sie NICHT; nur ein PR im Fork täte es (nach außen, Freigabe) → als
  Option vorlegen.
- **M4 Outage-Docstring — übernommen** → E (2a). **M5 Banner — übernommen in der Variante des Reviewers** (Banner
  entfernt, Konstanten mit schlichten Kommentaren wie die Amplituden-/Strahlungsblöcke) → E (3).
- **Nits:** `first_report_after`-Docstring (2b) und „(MQTT ranks low)“ (2c) → E; Offset-Stellung in der Event-Tabelle
  → E (5). `learn_more_url` NICHT in PR 1 (neues Verhalten, URL zeigte auf Doku im Repo) → PR-2-Notiz.
- **P1:** Spec Revision 2 (Z. 156–157, 168, 180–181, 308–310) und Plan noch nicht berichtigt — vor „fertig“ und vor
  der Archivierung.
- Erwarteter Baum nach E: `c3980024` (`fixE.py`, aus derselben Ersetzungsliste wie der Auftrag); Probelauf am
  Endstand: 148 passed (4 Liveness-Dateien + `test_store_buffers.py`), black/ruff sauber.
- **Review-Aussage berichtigt (beim Entwurf des PR-Texts, gegen `sensor_liveness.py` gelesen):** „Die Prüfung schreibt
  nie“ (Strengths) und I2(e) „einzige Änderung an der Schreibhäufigkeit“ sind ungenau. `_async_check_mapping_liveness`
  ruft `async_update_mapping` (→ `async_schedule_save`), sobald sich die Ausfall-Liste ändert (`kept != outages`: ein
  Ausfall beginnt, endet oder fällt nach 7 Tagen weg). Nur das Auffrischen der Lebenszeichen plant nie ein Speichern.
  Spec Rev. 3 und PR-Text entsprechend formuliert.
- **Nach Commit E (`b321c0bb`, Baum `c3980024` = Sollbaum):** Suite 7/3733/9/415, 422 Namen identisch (`suite-E.txt`,
  `names-E.txt`); Mutationen 59/59 getötet gegen die Endstand-Kopie `probeE/` (inhaltsgleich mit dem Worktree, 447
  Dateien), Killer-Mengen je Mutation identisch mit `mutate-final.txt` (`mutate-E.txt`).
- **Rebuild v2026.10.04b2** (`prodrebuild-1004b2-work\wt`, Build-Commit `e031b6a6`): Liveness-Anteil per `git patch-id`
  gleich dem PR-Diff; Suite 7/3791/9/415, 422 Namen identisch; 3791 = 3667 (JustChr#189-Endstand) + 9
  (`test_brand_assets.py`, parametrisiert) + 115. 0 behind, en.json 0 URLs, black/ruff sauber, Bundles nur
  Versionsstring; ZIP aus dem SHA (Mixin 1×, Versionen v2026.10.04b2).

## Review Commit E (Sonnet): 0 Critical, 0 Important, 2 Minor, 2 Nit — Bewertung

- **F1 Doku übernommen** → Commit F. Beleg: Die Prüfung liest `last_reported`; ein Sensor ohne Gerät, der denselben
  Wert neu schreibt, rückt es vor und wirkt nie stumm. Der Satz gilt nur für Sensoren, die bei Änderung schreiben
  (Template: unverändertes Ergebnis wird übersprungen; `utility_meter` hört nur auf `state_changed`). Ein UI-Zähler
  hängt nur dann am Gerät der Quelle, wenn sie eins hat. Wortlaut des Reviewers übernommen; Spec Rev. 3 (Doku DE/EN,
  Fehlalarm-Zeile) nachgezogen.
- **F2 übernommen** → F: „a helper mapped from that device“ → „attached to“ (in dieser Integration heißt „mapped“
  einem Feld zugeordnet).
- **F3 übernommen** → F: Der Zweig „das Entry der gemappten Entität bürgt, wo eine andere Integration das Gerät
  besitzt“ war ungepinnt (Mutation überlebte mit 115 passed). Killer-Test des Reviewers, im Probelauf am Endstand
  geprüft (`probeF_m60.py`: unter der Mutation genau dieser Test rot, 1 failed / 115 passed; zurückgesetzt 116 passed).
  Mutation als **M60** in `probe_mutate5.py`.
- **F4 (Commit-Message E) zurückgestellt** → erledigt sich mit I1 (Falten); ohne Falten kein Amend.
- Erwarteter Baum nach F: `e9a98569` (`fixF.py`); Probelauf: 149 passed (+1), black/ruff sauber.
- **Nach Commit F (`6c9ba82a`, Baum `e9a98569` = Sollbaum):** Suite 7/3734/9/415, 422 Namen identisch
  (`suite-F.txt`); Mutationen **60/60** getötet (`probe_mutate5.py` gegen `probeF/`, `mutate-F.txt`): M60 von genau dem
  neuen Test, M52 zusätzlich von ihm, alle übrigen Killer-Mengen gleich `mutate-E.txt`.
- **Rebuild mit F** (Branch `rebuild/v2026.10.04b2-f`: `13cfcb11` + F + Build-Commit per Cherry-Pick, Message auf 41
  Commits berichtigt → `d8c74317`): Liveness-Anteil per `git patch-id` gleich `e9c79ec4..6c9ba82a`; frischer
  `npm run build` reproduziert die vier Bundles byte-gleich (das „M“ in `git status` war nur autocrlf: drei Bundles
  sind nicht auf `eol=lf` gepinnt); Suite 7/3792/9/415 = 3667 + 9 + 116, 422 Namen identisch; ZIP aus `d8c74317`
  (Mixin 1×, v2026.10.04b2, en.json 0 URLs). Der alte Rebuild `e031b6a6` ist überholt.

## Review Commit F (Sonnet): OK — 0 Critical, 0 Important; B1 Minor, B2/B3 Nit, H1/H2 Hinweise

- Neuer Test gilt auf 2024.12.5 (ausgeführt), 2025.5.0, 2026.2.3 (Quellen: `name` → Info-Typ „primary“ →
  `primary_config_entry` = Besitzer; Blöcke per diff identisch) und dev (`config_entry_id` Pflichtfeld, wird zuerst
  gelesen). `er.async_get_or_create` prüft nirgends die Zugehörigkeit des Entrys zum Gerät, nur Existenz.
- **B1/B2 (Message F) → mit I1** (Falten; sonst Amend des Spitzen-Commits). **B3** Kommentar zu `name=` in beiden
  Registry-Tests → kleiner Test-Commit vor dem PR (Kandidat). **H1** nicht übernommen (E-Review: Vereinfachung
  unschädlich, nur großzügig). **H2** (HA dev: Kind-Geräte, `async_entries_for_device` sieht nur das Kind) →
  PR-2-Notiz, unbelegt ob Wetterstationen das nutzen.

## 2026-10-05: Upstream v2026.10.04 (stabil, mit JustChr#189) — Rebase vor dem Push

- Upstream-Runde 05:46 UTC: JustChr#189 am 2026-10-04 21:49 UTC gemergt (Squash `ef8cceef`, inhaltsgleich mit
  `ab3eb45f`, ohne Kommentar/Review), danach Release-Commit `bbf2e151` = **v2026.10.04, stabil**. PR 1 lag 2 dahinter.
- **Rebase** des gefalteten, ungepushten Branches auf `bbf2e151` ohne Konflikt; PR-Diff per `git patch-id` identisch
  (`8bd5f99c…`). Vorher-Stand als lokaler Ref `archive/stale-weather-sensor-folded-e9c79ec4` (`1ebf4c0f`).
- **Neu belegt** (Task 14 Schritte 1–3): frische Baseline auf `bbf2e151` im Worktree `base-bbf2`: 7/3667/9/415, 422 Namen
  = alte Namen. Rebaster Stand: 7/3783/9/415 = 3667 + 116, Namen identisch; jeder der vier Commits für sich grün
  (43/108/149/149, black/ruff sauber); 60/60 Mutationen, Killer-Mengen gleich `mutate-F.txt` (`mutate-R.txt`).
- **Rebuild v2026.10.05b1** (`prodrebuild-1005-work\wt`, `5a780270`): `bbf2e151` + Branding (Message berichtigt, Patch-ID
  gleich `b4e1c92e`) + die vier PR-Commits (Patch-ID gleich) + Build; Suite 7/3792/9/415 = 3667 + 9 + 116, Namen identisch;
  ZIP aus dem SHA geprüft; Tag frei.
- PR-Text: nur die Suite-Zahlen geändert (3618 → 3734 wird 3667 → 3783).
