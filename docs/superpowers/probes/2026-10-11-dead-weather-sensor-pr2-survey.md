# Faktensammlung für die Spec von PR 2 (stummer Wettersensor, "der Schnitt im Tagespfad")

Stand: 2026-10-11. Nur gelesen: kein Code geändert, kein Git-Schreibzugriff, keine HA-Aufrufe. Alle Code-Zeilen
beziehen sich auf `upstream/master` = `6a40e083` (Release v2026.10.05, enthält PR 1 als `7001c754`) und
`custom_components/irrigation_plus/`, sofern nicht anders genannt (Tests `tests/`, Docs `docs/`). Gelesen per
`git archive 6a40e083` in ein Wegwerf-Verzeichnis; Nachprüfen mit `git show 6a40e083:<pfad>`. "Spec" =
`docs/superpowers/specs/2026-10-03-dead-weather-sensor-design.md` (Revision 3), Angaben als `Spec:<zeile>`.
Markierung: **[Zusammenfassung]** = von mir zusammengefasst, nicht wörtlich.

---

## 1. Anforderungen an PR 2 aus der Spec

**Anforderungen (Spec, Abschnitt *Anforderungen*, `Spec:105-124`)**
- R4 (`Spec:114-115`): Einstellung je Sensorgruppe *pausieren* / *letzten Wert behalten*. Bestand: behalten, Rechnung und
  Erklärung byte-identisch. Neue Gruppen: pausieren.
- R5 (`Spec:116-118`): Pausieren = was nicht gemessen ist, wird nicht gebucht. Von Beginn + 3 h bis Ende zählen die Werte
  des Feldes nicht. Regenzähler (Aggregat `delta`) ausgenommen: Stand nach der Rückkehr ist eine Messung, nur spät übertragen.
- R6 (`Spec:119-120`): Melden für jede Einstellung; bei pausierenden Gruppen zusätzlich ein Satz in der Berechnungs-Erklärung.
- R7 (`Spec:121`): nur Sensorfelder; Dienst-Felder und statische Werte unverändert.
- R8 (`Spec:122-123`): PR 2 schneidet nur, wo die Stundenrechnung aus ist.
- R9 (`Spec:124`): der Schnitt kommt erst nach dem Feldtest von PR 1 (JustChrs Bedingung).

**Entscheidungen**
- Entscheidung 1 (`Spec:132`): Verhalten bei Ausfall = Einstellung *pausieren*; verworfen: Weiterrechnen, Ersatzwert/Wetterdienst-Rückfall.
- Entscheidung 8 (`Spec:154`, User 2026-10-04): Die Masken sind ein Parameter von `aggregate_window`; in PR 2 übergibt ihn
  nur der Commit bei ausgeschalteter Stundenrechnung. Grund: Das Aggregat liefert im Stundenbetrieb den Niederschlag,
  die nachgespielte Bilanz gleicht sich damit ab; geschnittene Regenrate gegen ungeschnittene Stundenzeilen --> Abgleich
  scheitert, still Einmal-Buchung.
- Entscheidung 9 (`Spec:155`, User 2026-10-04): neue Gruppen *pausieren*, Bestand *behalten*. Ausweg im Hinweistext pausierender
  Gruppen und in der Doku (Integration aktualisiert nur alle paar Stunden --> *behalten*). Bekannter Preis: 6-h-Takt verliert bei
  *pausieren* in jedem Zyklus die halbe Zeit.
- J1 (`Spec:144`): Einstellung je Gruppe, Bestand byte-identisch. J2 (`Spec:145`): Design 2 (Masken je Feld). J3 (`Spec:146`):
  drei PRs, Schnitt erst nach Feldtest. J4 (`Spec:147`): Hinweis-Tests (PR 1, erledigt). J5 (`Spec:148`): fest 3 h + Doku-Satz zum 6-h-Fehlalarm.

**Design für PR 2**
- *Einstellung je Sensorgruppe* (`Spec:226-241`): Feld `MappingEntry.on_silent_sensor` (`keep`/`pause`), ohne Store-Versionssprung;
  Lade-Pfad setzt `keep`, wo der Schlüssel fehlt; Attribut-Standard `pause`; Erst-Einrichtung und jede über Panel/Assistent angelegte
  Gruppe pausiert; **der Plan von PR 2 prüft per Test, ob die Domain-Migration Gruppen über den Lade-Pfad übernimmt (`keep`)**
  (`Spec:233-234`). View-Schema nimmt den Schlüssel an, Panel zeigt eine Auswahl in der Gruppenkarte, schickt ihn beim Speichern mit,
  Beschriftungen in 8 Sprachen, dist neu bauen. Wirkung: Liste unabhängig von der Einstellung; jeder Commit wendet die *aktuelle*
  Einstellung auf alle Ausfälle an, die sein Fenster berühren (Wechsel auf *pausieren* gilt rückwirkend im nächsten Fenster);
  Wechsel bei offenem Ausfall gleicht den Hinweistext sofort an.
- *Gemeinsame Schnittregeln* (`Spec:243-252`): Gesperrte Zeit eines Eintrags = `start`+3 h bis `end` (offen: bis jetzt); die ersten
  3 h werden mit dem letzten Wert überbrückt. Gesperrte Zeit eines Feldes = Vereinigung seiner Einträge. Regenzähler (Precipitation
  mit Aggregat `delta`) nie gesperrt; Regenraten (`riemannsum`/`sum`) und alle Pegelwerte gesperrt; Current Precipitation wird
  gesperrt, wird aber von keiner Rechnung gelesen. *behalten* bekommt keine Masken (selber Code-Pfad, byte-identisch).
- *Tagespfad* (`Spec:254-277`): Gate = Gruppe pausiert UND `hourly_calculation_enabled(store)` falsch; nur der Commit übergibt die
  Masken (Live-Schätzung und Stundenpfad nicht). Aggregation je Feld nur in gültiger Zeit: Wert wird bis zur nächsten Messung
  gehalten, aber nie in eine Sperre hinein; Zeilen in einer Sperre fallen weg (trifft eingefrorene, frisch gestempelte Poll-Werte);
  Mittel (zeitgewichtet wie einfach), Tmin/Tmax, Einzelwert-Zweig und `last_entry`-Auffüllung nur für die gültige Zeit; Feld ohne
  gültige Zeit fehlt; das Ergebnis meldet je Feld seine gesperrten Abschnitte im Fenster.
- *Buchen* (`Spec:267-273`): PyETO-Tagesform bucht ET nur für den Anteil des Fensters, in dem *alle* Pflichtfelder zugleich gültig
  sind (Schnittmenge, nicht Minimum der Einzelanteile; Pflichtfelder Taupunkt, Temperatur, Wind, Druck; fehlt nur die Sonne, schätzt
  PyETO sie wie heute); Passthrough: gültiger Anteil des ET-Feldes; Regenrate: nur über die gültige Zeit integriert.
- *Aufzeichnungen* (`Spec:274-276`): `_record_window_radiation` und `_record_window_amplitude` zeichnen kein Fenster auf, in dem Sonne
  bzw. Temperatur gesperrt war.
- *Melden* (`Spec:336-356`): Hinweis-Variante für pausierende Gruppen (zweiter Übersetzungsschlüssel, gleicher Titel, Wortlaut
  "wird mit dem Plan von PR 2 freigegeben", Entwurf `Spec:336-341`); wählt nach Einstellung und, bis PR 3, nach der Stundenrechnung
  (mit Stundenrechnung: Text von PR 1). Log-WARNING nennt ab PR 2 den Schnitt, wo geschnitten wird (`Spec:347-348`). Erklärungssatz
  `module.calculation.explanation.sensor-outage` (`Spec:349-352`), je Sperre, die das Fenster berührt; *behalten* bekommt keinen.
  Übersetzungen in 8 Sprachen: Hinweis in `translations/*.json`, Erklärungssatz + Auswahl-Beschriftungen in
  `frontend/localize/languages/*.json`; `en.json` des Frontends ist ins Bundle importiert --> dist neu bauen (`Spec:353-356`).
- *Doku* (`Spec:416-419`): Abschnitt "When a sensor goes silent" um die Einstellung erweitern (was *pausieren* tut, Standardwerte,
  Rat *behalten* bei seltenen Updates, "Mit der stündlichen Berechnung wird der letzte Wert weiter verwendet").
- *Betroffene Stellen PR 2* (`Spec:433-439`): `store.py`, `websockets.py`, `const.py`; `frontend/src/views/mappings/view-mappings.ts`,
  `frontend/localize/languages/*.json`; `weather_aggregate.py` (Masken); `sensor_liveness.py` (gesperrte Zeit je Feld, Hinweis-Variante);
  `calculation.py` (Gate, Masken an den Commit, Aufzeichnungen überspringen, Erklärungssatz); `calcmodules/pyeto/__init__.py`,
  `calcmodules/passthrough/` (Buchungsanteil); `translations/*.json`, Doku.
- *Zwischenstand nach PR 2* (`Spec:297-300`): mit Stundenrechnung schneidet auch eine pausierende Gruppe nicht und bekommt den
  *behalten*-Hinweistext; ohne Stundenrechnung schneidet der Commit, die Live-Schätzung nicht ("bei Live-Schätzungs-Bewässerung kann ein
  Lauf während eines Ausfalls mehr ET bemessen, als der Commit danach bucht").
- *Tests PR 2* (`Spec:578-588`): Einstellung (Bestand lädt `keep`, Erst-Einrichtung/neue Gruppe `pause`, Domain-Migration behält `keep`,
  Schema/Panel tragen den Schlüssel, Wechsel gleicht den Hinweis an); Byte-Identität für *behalten* mit Ausfällen in der Liste; Gate;
  Sperren in der Aggregation (zeitgewichtet, einfaches Mittel, Einzelwert, Tmin/Tmax, `last_entry`, Regenzähler ausgenommen,
  eingefrorene Poll-Zeilen fallen weg, Feld ohne gültige Zeit fehlt); Buchen (Schnittmenge Pflichtfelder, Sonnenschätzung, Passthrough,
  Regenrate); Aufzeichnungen; Melden (Erklärungssatz, Hinweis-Variante, i18n). Jeder PR: volle Suite mit Namensvergleich gegen Baseline,
  Mutationen auf die Wächter, RED vor GREEN (`Spec:551`, `Spec:594`).
- *Ende-zu-Ende PR 2* (`Spec:620-622`): HA-Test mit ausgeschalteter Stundenrechnung: pausierende Gruppe schweigt 3,5 h --> Erklärung nennt
  die Sperre, ET nur für den gültigen Teil; Gruppe auf *behalten* rechnet wie vorher; mit Stundenrechnung schneidet nichts. Mittel aus
  PR 1: MQTT-Sensoren per YAML unter eigenem Topic-Präfix, ohne Discovery (`Spec:598-602`).
- *Lieferung* (`Spec:635`): eigener Plan, frühestens nach dem Merge von PR 1, gepostet nach dem Feldtest (R9); P1 (Archiv) nach jeder Freigabe.
- *Ausdrücklich nicht* (`Spec:527-539`): Dienst-Felder (`Eifel-Joe#74`), einstellbare Grenze/Abschalten des Hinweises, Zustands-Entität,
  Ersatzwerte/Wetterdienst-Rückfall, HAs eigene Ausfallzeit, Satz in der Erklärung für *behalten*; blinde Flecken: toter Untersensor
  an lebendem Gerät mit behaltenem Zahlenwert, Integrationen, die denselben Cloud-Wert weiter melden.
- Schwester-Pfade, die PR 2 abdeckt (`Spec:509-525`): Poll-Schreiber mit eingefrorenem Zahlenwert; `last_entry` auch bei abgeschaltetem
  `continuousupdates` gelesen (`calculation.py:420`); Kalibrier-/Amplituden-Aufzeichnung. Für PR 3 vorgemerkt: Stundenzeilen aus `last_entry`,
  Temperatur-Anker, `_effective_series`, Abgleich Aggregat/Teilschritte.

---

## 2. JustChrs Aussagen zu PR 2

Quelle: `gh api` lesend, nur das Konto `JustChr` zählt (der Bot `watchtower-justchr[bot]` ist ungeprüft, hier nicht aufgetreten).
- Issue 188, Kommentar `5972596286`, 2026-10-03 19:13 UTC, https://github.com/JustChr/HAsmartirrigation/issues/188#issuecomment-5972596286
  **[Zusammenfassung]** Punkt 1: "Not booked" nach 3 h ja, aber nicht still für Bestandsinstallationen: Einstellung je Gruppe
  "on a silent sensor: pause / keep last value", für bestehende Gruppen Standard *keep last value and notify* (byte-identisch), für neue
  darf *pause* Standard sein; Erkennung, Ausfall-Liste und Hinweis zuerst, "the cut rule follows once it has been field-tested".
  Punkt 2: Design 2; Aufteilung in drei PRs, "(2) the cut in the daily path; (3) the hourly path and live estimate". Punkt 3: Tests für
  den Hinweis (PR 1, erledigt). Kleinkram: fest 3 h für die erste Fassung ok, 6-h-Cloud-Fehlalarm in die Doku. Abschluss: "Go ahead and build it".
- PR 190, Kommentar `5997966126`, 2026-10-05 15:48 UTC, https://github.com/JustChr/HAsmartirrigation/pull/190#issuecomment-5997966126
  **[Zusammenfassung]** Gemergt als `7001c754`; er hat das Liveness-Modul Zeile für Zeile gelesen und auf aktuellem `master` probe-gemergt
  (3790 passed, 9 skipped); zwei eigene Mutationen (strikte 3-h-Grenze; ein `update`-Entity bürgt) wurden von den Tests gefangen.
  Wörtlich: "Parts 2 and 3 of #188 can follow whenever you are ready." --> er wiederholt die Feldtest-Bedingung nicht, hebt sie aber
  auch nicht auf (siehe Abschnitt 4, Frage 1).
- PR 190: keine Review-Kommentare und keine Reviews (beide Abfragen leer); es gibt nur zwei Issue-Kommentare, der erste ist von Eifel-Joe (Codecov-Fehlschlag), der zweite ist der oben zitierte von JustChr.
- Doppelarbeit geprüft: `gh pr list --search "sensor silent OR stale OR liveness OR outage"` zeigt außer #190 nichts Einschlägiges; seit
  2026-10-05 15:48 UTC kommen Issue-Kommentare nur zu #190, #191, #192 (JustChr).

---

## 3. Code-Fakten auf `6a40e083`

### 3.1 Liveness-Modul `sensor_liveness.py` (neu in PR 1, 531 Zeilen)
- Öffentliche reine Funktionen: `sensor_fields_by_entity(mappings_config)` (`:38-57`, nur `source: sensor` mit gesetzter Entität, `input_number`
  ausgenommen, Dienst-/Static-Felder fehlen von Natur aus); `last_sign_of_life` (`:70-87`); `first_report_after` (`:90-107`);
  `advance_outages` (`:184-235`); `stale_issue_placeholders` (`:238-249`); `outage_event_payload` (`:252-269`); `seen_from_state` (`:277-286`).
- Datenstruktur `Outage` (`:110-163`, frozen dataclass): `entity_id`, `device_id`, `fields: tuple[str,...]`, `start: datetime`,
  `end: datetime | None`. Ein Ausfall gehört einer **Entität**, nicht einem Feld; `fields` nennt die Felder, die die Entität beim Öffnen
  speiste. `to_store`/`from_store` (`:126-163`): ISO-Strings; unlesbare Einträge werden verworfen, nie geworfen.
- Uhr: Alle Stempel **naiv auf HAs Uhr** (`_on_has_clock` `:272-274`, `local_naive_now()`), derselbe Rahmen wie Puffer-Stempel, Zonen-Wasserzeichen
  und das `now` der Rechnung. `start` = letztes Lebenszeichen (nicht Beginn+3 h); die Sperre beginnt also bei `start + STALE_AFTER`
  (`STALE_AFTER` `:34`, `const.SENSOR_STALE_AFTER_SECONDS = 3*3600` `const.py:696`). `end` = Rückkehr des Feldes (D3), oder "jetzt", wenn die Gruppe
  die Entität nicht mehr liest (`:213-217`).
- Ablage je Sensorgruppe: `MappingEntry.sensor_outages` (Liste von Dicts, `store.py:379`) und `sensor_last_seen` (`store.py:383`); Schlüssel
  `const.MAPPING_SENSOR_OUTAGES`/`MAPPING_SENSOR_LAST_SEEN` (`const.py:711-712`). Leser: `outages_of(mapping)` (`:166-171`, wirft nie).
- Aufbewahrung: geschlossene Einträge fallen 7 Tage nach `end` weg (`advance_outages` `:209-212`, `const.SENSOR_OUTAGE_RETENTION_DAYS` `const.py:703`);
  offene bleiben, egal wie alt (`:203`). Prüfung alle 300 s (`const.py:699`), erste Prüfung 600 s nach Setup (`const.py:700`, `sensor_liveness.py:350-352`, `:384-388`).
- **Kein Hook für PR 2 vorhanden:** keine Funktion, die "gesperrte Zeit je Feld" liefert; das Modul sagt ausdrücklich "Nothing here changes a
  calculation" (`:11-12`). Einziger Rechen-Bezug im Code: der Docstring von `_prune_mapping_buffer` verweist auf die Liste (`calculation.py:441-447`). Die
  Suche nach "PR 2"/"later PR" im Paket fand nichts.
- Hinweis/Event: `_sync_stale_issue(mapping_id, name, outages)` (`:484-500`; Issue-ID `weather_sensor_stale_<mapping_id>`, `translation_key =
  const.ISSUE_WEATHER_SENSOR_STALE`, Warnstufe, nicht fixierbar); aufgerufen **nur** bei Öffnen/Schließen (`:464-465`) und im Setup für offene Einträge
  (`:353-369`); `_retire_outages` (`:502-531`) beendet offene Einträge bei Quellwechsel/Löschen/Reset. Log-WARNING beim Öffnen `:454-462`
  ("... has not reported since ...; its last value is still used"), INFO beim Schließen `:445-452`.
- Aufrufer: `__init__.py:798` (`async_setup_sensor_liveness`), `:1778` (Löschen), `:1816` (Quellwechsel), `calculation.py:367-370` (Reset).

### 3.2 Store, Laden, Standardwerte
- `STORAGE_VERSION = 14`, `STORAGE_MINOR_VERSION = 2` (`store.py:207-210`); Minor-Sprung nur für die Stempel-Hebung (`_lift_legacy_stamps` `store.py:627-672`). PR 1 hat
  seine zwei Felder **ohne** Versionssprung ergänzt; `MigratableStore._async_migrate_func` (`store.py:675-689`) bleibt unberührt. Begründung im Code: seit HA 2026.3 sperrt
  ein Major-Sprung den Rollback (Docstring von `_lift_legacy_stamps`, `store.py:627-650`).
- `MappingEntry` (`store.py:351-383`, `attr.s(slots=True, frozen=True)`): Felder `id, name, mappings, data_last_updated, data_last_entry,
  data_last_calculation, temperature_amplitudes, radiation_calibration, sensor_outages, sensor_last_seen`. Vorbild für ein "optionales Feld":
  `radiation_calibration = attr.ib(type=list, factory=list)` (`:374`).
- **Laden:** `store.py:1367-1405`: `MappingEntry(...)` mit `mapping.get(KEY) or []` bzw. `_as_last_seen(...)` je Feld (`:1402-1405`). Hier käme
  `on_silent_sensor=mapping.get(KEY, "keep")` hin (Bestand = `keep`).
- **Neu-Anlage mit Attribut-Standard:** (a) `async_create_mapping` (`store.py:2191-2205`: `MappingEntry(**data)`), erreicht über
  `coordinator.async_update_mapping_config` (`__init__.py:1844`), einziger Aufrufer ist der HTTP-View (`websockets.py:268`); das Panel schickt
  beim Neuanlegen nur `{name, mappings}` (`view-mappings.ts:203-207`, `:380`); (b) Erst-Einrichtung `async_factory_default_mappings` (`store.py:1534-1581`,
  `MappingEntry(**{id:0,...})` `:1568`), aufgerufen aus `set_up_factory_defaults` (`store.py:1480-1486`) **immer wenn `self.mappings` leer ist**, also auch bei
  einem Bestand, der alle Gruppen gelöscht hat (neue Gruppe, `pause` ist dort richtig).
- Update: `async_update_mapping` (`store.py:2219-2253`) macht `attr.evolve(old, **changes)`; ein Panel-Speichern ohne den Schlüssel lässt ihn stehen.
  Test-Vorbild: `tests/test_sensor_liveness_store.py` (u. a. `test_a_document_written_before_these_fields_still_loads` :78,
  `test_a_panel_save_leaves_the_outages_alone` :95).
- **Domain-Migration:** `migrate_domain.async_import_legacy_store` kopiert die rohen Bytes der alten `smart_irrigation.storage` auf den neuen Schlüssel
  (`migrate_domain.py:492-540`, Docstring `:497-501`: "keeps this module out of the business of knowing anything about the schema"); gelesen wird
  danach über den normalen Lade-Pfad. Folge (Code-Lektüre, noch kein Test): übernommene Gruppen haben den Schlüssel nicht --> `keep`. Test-Vorbild:
  `tests/test_migrate_domain.py:59` (`test_imports_the_legacy_store_verbatim`).
- Rollback-Verhalten (Code-Lektüre): Ein PR-1-Build lädt nur die Schlüssel, die er kennt, und schreibt sie ohne `on_silent_sensor` zurück --> nach erneutem
  Upgrade stünde die Gruppe auf `keep` (harmlos, aber eine gesetzte `pause` ginge verloren).

### 3.3 Aggregation `weather_aggregate.py` (Datei unverändert seit `e9c79ec4`, Spec-Zeilen gelten dort noch)
- `aggregate_window(readings, watermark, mappings_config, *, now=None, last_entry=None, time_weighted=False)` (`:321-409`). **Aufrufer genau zwei:**
  `calculation.py:409` (Commit) und `live_estimate.py:607` (Live), dazu Tests (`tests/test_weather_aggregate.py` ruft sie 20-mal auf, weitere Dateien
  siehe 3.9). Rückgabe: flaches Dict `{Feld: Zahl, MAX/MIN-Temp, data_multiplier}` oder `None` (`:359-361`).
- Ablauf: `select_window` (`:137-180`) trennt Randzeile und Fenster; die Randzeile trägt je Feld den neuesten Wert ≤ Wasserzeichen, **die Einzelstempel gehen
  verloren** (`:178`), nur der Stempel der neuesten Zeile bleibt (`:179`). Randzeile wird auf das Wasserzeichen umgestempelt (`:365-368`). `_group_by_sensor` (`:183-207`)
  macht `{Feld: [(stempel, wert)]}` (Stempel kann `None` sein, wenn unlesbar). `last_entry`-Auffüllung `:371-396` (ungestempelt, `[(None, val)]`; Integral-Aggregate
  ausgenommen; Delta aufgefüllt). `data_multiplier` = `_hour_multiplier` (`:304-318`, Fensterlänge als Tagesanteil, gerechnet aus Wasserzeichen und `now`, nicht aus den Daten).
  Fenstergrenzen `_window_bounds` (`:210-227`: Start = Wasserzeichen oder frühester Stempel, Ende = `max(now, Stempel)`).
- `_aggregate` (`:501-575`): Tmax/Tmin aus **allen** Proben des Feldes Temperature vor jedem Aggregat-Zweig (`:516-518`); `delta` --> `cumulative_delta_total` (`:521-522`);
  `len(d) < 2` --> Einzelwert verbatim, bei Temperatur auch Tmax/Tmin (`:523-527`); `average` --> `_time_weighted_mean` nur mit `time_weighted`, sonst `statistics.mean` (`:528-542`);
  first/last/max/min/median/sum (`:543-554`); `riemannsum` trapezweise je Paar aufeinanderfolgender Proben, ohne Verlängerung bis zum Fensterende, bei fehlendem Stempel dt = 1 h (`:555-575`).
- `_time_weighted_mean` (`:256-301`): erste Probe wird rückwärts bis Fensterstart gehalten (`:282-288`), letzte vorwärts bis Fensterende (`:298-300`) --> beides müsste an Sperren enden.
  `time_weighted` kommt nur aus `continuousupdates is True` (`calculation.py:425-432`, `live_estimate.py:620-627`); im Poll-Betrieb (Standard) gilt das einfache Mittel über Zeilen.
- Regenzähler-Ausnahme: `effective_aggregate(key, mappings_config)` (`:412-439`) ist die einzige Wahrheit für das Aggregat (Precipitation: Wetterdienst --> `riemannsum`, sonst
  Standard `delta`, Override per Feld-Konfiguration). Eine Maske gibt es nur für Sensorfelder (siehe 3.1), also wird ein Dienst-Regenfeld nie maskiert.
- Für PR 3 (Abgrenzung): `_effective_series` (`:703-719`, stempelt ebenfalls um `:714`), `build_hourly_rows` (`:854`, `last_entry`-Probe `:936`), `build_substeps` (`:1058`, nutzt `_group_by_sensor` `:1109`).

### 3.4 Commit-Pfad `calculation.py`
- `hourly_calculation_enabled(store)` `:87-102` (freie Funktion, strikter `is True`-Test, auch für Test-Doubles sicher); `replayed_balance_applies` `:123-150` (verlangt Stundenrechnung
  UND PyETO); `zone_module_models_weather` `:105-120`; Methode `_hourly_calculation_enabled` `:846-860`.
- `_aggregate_for_zone(self, zone, *, now)` `:393-434`: holt Mapping, Puffer, Wasserzeichen (`:403-407`), zählt Zeilen (`:408`), ruft `aggregate_window` `:409-433` (mit
  `last_entry` `:420`, `time_weighted` `:425-432`), gibt `(weatherdata, len(window))` zurück. **Einziger Produktions-Aufrufer:** `async_calculate_zone` `:606`; Tests rufen es oft direkt
  (`tests/test_live_estimate_replayed_balance.py` u. a.), `tests/test_coordinator_mixins.py:39` führt es in der Mixin-Methodenliste.
- `async_calculate_zone` `:560-642`: Fenster verbrauchen, `calculate_module` `:614`, dann `_record_window_amplitude` `:625` und `_record_window_radiation` `:626`, Wasserzeichen vor (`:631`).
  Liefert `calculate_module` `None`, gibt die Funktion mit ERROR auf **ohne das Wasserzeichen zu bewegen** (`:617-623`).
- `_record_window_amplitude` `:644-692` (Tmin/Tmax aus dem Aggregat, überspringt Fenster kürzer als `TEMPERATURE_AMPLITUDE_MIN_MULTIPLIER`); `_record_window_radiation` `:694-752`
  (Sonnen-Mittel aus dem Aggregat; überspringt kurze/gestockte Fenster `:704-712`). Beide nehmen das Aggregat, kennen keine Masken.
- `calculate_module` `:1140-1776`: PyETO-Tagesform `modinst.calculate(weather_data=weatherdata, ...)` `:1204-1216` (nur wenn `_hourly_et_for_zone` `None` liefert, `:1195-1199`);
  `precip = weatherdata.get(Precipitation, 0)` `:1218`; Passthrough `:1222-1232` (**fehlt `Evapotranspiration` im Aggregat: ERROR und `return None`**); `hour_multiplier` `:1241`;
  **ET-Buchung `et_delta = delta * kc * hour_multiplier` `:1255`** (Stundenform `:1251-1252`); `delta = et_delta + precip` `:1256`; `elapsed_hours = hour_multiplier * 24` `:1271` (Drainage-Dauer,
  nicht ET); Replay `:1294-1297`; Erklärung beginnt `:1405-1418` (HTML mit `<br/>`; Schlüssel unter `module.calculation.explanation.*`).
- Abgleich Replay/Aggregat: `_substeps_for_zone` `:968-1018`: Gate `replayed_balance_applies` `:986`; `build_substeps` `:998-1005`; `stepped = sum(...)` `:1008`; Vergleich mit `precip_total` `:1009-1017`
  (bei Abweichung `None` = Einmal-Buchung). **Mit ausgeschalteter Stundenrechnung liefert `replayed_balance_applies` False (`:148-149`) und der Abgleich entfällt** --> das ist der Grund für das Gate.
- `_hourly_et_for_zone` `:862-966` (Gates `:894-905`, `hourly_eto_priced` `:941`); fällt es auf `None` zurück, rechnet der Commit die Tagesform auf dem Aggregat.
- `_prune_mapping_buffer` `:436-...`: Randzeile je Feld ohne Altersprüfung (Docstring in PR 1 berichtigt `:438-447`); Retention `BUFFER_RETENTION = timedelta(days=7)` `:55`.
- Reset: `_async_clear_all_weatherdata` `:329-391` leert Liste (`:367`) und beendet offene Ausfälle (`:370`); Lebenszeichen bleiben.
- PyETO `calcmodules/pyeto/__init__.py`: `DAILY_FORM_FIELDS = (Dewpoint, Min-/Max-Temp, Windspeed, Pressure)` `:114-120` (Min/Max-Temp sind abgeleitet aus dem Feld Temperature, nie gemappt);
  `calculate` `:209-270` (Mittel aus Wetter-Tag und `forecast_days` Prognose-Tagen, `:246-268`); `calculate_et_for_day` `:272-462`: Pflichtfelder-Test `:303`, Sonne fehlt/`DontEstimate` anders --> Sonnenstunden-Schätzung
  `:324-364` (`:325-326`), fehlt ein Pflichtfeld: WARNING je Feld `:438-461` und Rückgabe 0 (`:462`) --> bei PyETO **rückt das Wasserzeichen vor, es wird 0 gebucht**.
  Passthrough: `calcmodules/passthrough/__init__.py` (`calculate(et_data)` gibt den Wert unverändert zurück; wird in `calculate_module` mit `hour_multiplier` skaliert).

### 3.5 Live-Schätzung (nur Abgrenzung; PR 2 ändert sie nicht)
- `_aggregate_live_window` `live_estimate.py:589-628` ruft `aggregate_window` `:607`; Docstring/Kommentar verlangen, dass es "exactly as `_aggregate_for_zone`" reduziert (`:590-596`, `:617-620`) --> PR 2 bricht diese
  Gleichheit absichtlich (Spec-Zwischenstand). Verbraucher: `_observed_precip_since_mm` `:630-652`, `_daily_mirror_et` `:1095-1134`, `_latest_temperature` `:880-900` (liest `last_entry[Temperature]` als "aktuell"),
  `_buffer_hourly_et` `:710-785`, `_buffer_water_steps` `:1136-1196`.

### 3.6 Schema, View, Panel, i18n
- HTTP-View `SmartIrrigationMappingView` `websockets.py:229-273`, Schema `:235-250`: `vol.Schema({...})` ohne `extra=ALLOW`, erlaubt `id`, `name`, `mappings` (`:240`), `remove` und vier Server-Felder (`:244-247`) --> **jeder
  neue Schlüssel muss ins Schema, sonst 400**. WS-Lesepfad `websocket_get_mappings` `:553-558` liefert `attr.asdict` (der neue Schlüssel erscheint von selbst, ebenso in `diagnostics.py`).
- Panel: `frontend/src/views/mappings/view-mappings.ts` (1131 Zeilen). Gruppenkarte `renderMappingCard` `:1008-1066` (Name-Zeile `:1027-1045`, danach `renderMappingSettings` `:1046`, Löschen `:1047-1062`) --> natürlicher Ort
  der Auswahl zwischen `:1045` und `:1046`. Neuanlage `handleAddMapping` `:184-231` (`newMapping = {name, mappings}` ohne Schlüssel, `:203-207`). Bearbeiten `handleEditMapping` `:277-327` (hält je Gruppe die letzte Kopie, speichert nach
  500 ms debounced). **Speichern `saveToHA` (`:329-381`): `const { id, name, mappings } = mapping; saveMapping(hass, { id, name, mappings })` `:379-380`** --> hier muss `on_silent_sensor` mit. Der Kommentar `:376-378` begründet, dass Server-Felder
  abgelehnt würden. TS-Typ `SmartIrrigationMapping` `frontend/src/types.ts:421-432` (`id, name, mappings, data`). Frontend-Test: `view-mappings-save.test.ts` (7 Tests, u. a. "saves every group edited inside one debounce window").
  `saveMapping` `frontend/src/data/websockets.ts:146-151` (POST `/api/irrigation_plus/mappings`, `Partial<SmartIrrigationMapping>`).
- Bestehende `<select>`-Muster im Panel: `renderUnitSelect` `:630-656`, `renderPressureTypeSelect` `:658-685`, `renderAggregateSelect` `:687-719`.
- i18n: Frontend/Backend-Texte in `frontend/localize/languages/{de,en,es,fr,it,nl,no,sk}.json` (8 Sprachen, `SUPPORTED_LANGUAGES` `const.py:29`); Panel-Block `panels.mappings.cards.mapping.*` (`en.json:436-483`,
  z. B. `sources` `:477-482`, `labels.mapping-name` `:486-488`); Berechnungs-Erklärung `module.calculation.explanation.*` (`en.json:65-67ff`, kebab-case; der Schlüssel `sensor-outage` existiert nicht). Backend-Lookup `localize()`
  (`localize.py:14`). **`frontend/localize/localize.ts:1` importiert `en.json` fest ins Bundle** --> dist neu bauen; getrackte Bundles (4): `frontend/dist/irrigation-plus.js`, `-card.js`, `-card-legacy.js`, `-card-impl.js`
  (`git ls-tree`), mit `git add -f` stagen (Projekt-CLAUDE.md). Versionen: `manifest.json` `v2026.10.05` / `package.json` `2026.10.05`; HA-Untergrenze `hacs.json` 2025.5.0.
- Completeness-Test: `tests/test_i18n_completeness.py` prüft beide Kataloge (Platzhalter-Gleichheit je Sprache `:175-208`, hassfest-Regeln für `issues` `:237-261`: keine URLs, `description` oder Fix-Flow).

### 3.7 Reparaturhinweis `weather_sensor_stale` (Wortlaut PR 1)
- Übersetzungen `translations/{de,en,es,fr,it,nl,no,sk}.json`, Block `issues`, Schlüssel `weather_sensor_stale` jeweils ab Zeile 456 (`"issues": {` Zeile 455); Platzhalter `{group}`, `{entities}`, `{since}`.
- en (`translations/en.json:457-458`): Titel "A weather sensor of {group} has stopped reporting"; Inhalt: nichts gehört seit `{since}` von `{entities}`; "The last reported values are still used as if they were current, so zones that depend
  on them are calculated with those values until new ones arrive."; Hinweis zu Gerätetausch und "Static value"; "If the integration only updates every few hours, this notice appears between its updates and does not mean the sensor has failed."; "This notice clears itself when the sensor reports again."
- de (`translations/de.json:457-458`): Titel "Ein Wettersensor von {group} meldet nicht mehr"; "Die zuletzt gemeldeten Werte werden weiter verwendet, als wären sie aktuell; ..." (sonst analog).
- Das Issue nutzt `translation_key=const.ISSUE_WEATHER_SENSOR_STALE` (`sensor_liveness.py:498`, `const.py:714`); eine Variante bräuchte einen zweiten Schlüssel (Spec) und müsste in allen 8 Dateien stehen.

### 3.8 Dokumentation
- `docs/configuration-sensor-groups.md:54-61`: Abschnitt "## When a sensor goes silent" (4 Absätze: Geräte-Regel; 3 h + Event + "Meanwhile the calculation keeps using the sensor's last value." `:57`; fest 3 h / 6-h-Cloud `:59`;
  Sensor ohne Gerät `:61`); darauf folgt "## Deleting a sensor group" `:63`. `docs/usage-events.md:21`: Zeile zum Event `irrigation_plus_weather_stale` (Felder, `stale`, Quellwechsel-Ende).
  Nach Lage der Dinge muss der Satz `:57` für PR 2 umformuliert werden ("keeps using" gilt nur noch für *behalten* und für die Stundenrechnung).

### 3.9 Tests und Infrastruktur
- PR-1-Tests (Muster für PR 2): `tests/test_sensor_liveness.py` (488 Zeilen, rein), `..._coordinator.py` (969), `..._repair.py` (165, echte Registry + `freezer`), `..._store.py` (170, echter Store).
  Test-Zone: HAs Zone US/Pacific (autouse `hass`), Prozess `TZ=UTC`. `aggregate_window` wird in 9 Testdateien benutzt (`test_weather_aggregate.py`, `test_aggregate_time_weighting_is_opt_in.py`, `test_continuous_update.py`,
  `test_live_estimate*.py`, `test_mapping_source_change.py`, `test_prune_delta_baseline.py`, `test_water_balance_substeps.py`, `test_weather_buffer_one_frame.py`). Test-Doubles geben Mapping-Dicts ohne neue Schlüssel
  und Stores ohne `config` --> der Lesepfad im Commit muss `.get(KEY, "keep")` und `hourly_calculation_enabled` (getattr-sicher) nutzen.
- Plan PR 1 (`docs/superpowers/plans/2026-10-03-dead-weather-sensor-common.md`, 2867 Zeilen): Kopf (Ziel/Architektur/Tech-Stack/Spec-Revision/Freigabe/Probelauf), `## Rahmen` (Zeilen 63-85), `## Dateien`-Tabelle (86-102), dann
  `### Task 0` (Worktree von `upstream/master` mit `--no-track`, Baseline der vollen Suite + Namensliste) bis `### Task 16`; Task 14 = Lint + volle Suite mit `diff` der FAILED/ERROR-Namen + Mutationstabelle + Review;
  Task 15 = Pre-Release/Live-Test; Task 16 = PR + Nachlauf; am Ende `## Selbstprüfung gegen die Spec`. Tasks nach der Methode RED --> GREEN --> Commit, Checkboxen `- [ ]`. Testbefehl:
  `TZ=UTC /d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest <pfad> -p _local_socket_unblock -q`; Lint `uvx black` + `uvx ruff check` auf `custom_components/irrigation_plus/`. Der PR-1-Plan nennt
  Basis-Messwerte (7 failed / 3618 passed / 9 skipped / 415 errors auf `e9c79ec4`); auf `6a40e083` neu messen (Memory `rebaseline-when-the-base-moves`). Laut JustChr: 3790 passed, 9 skipped auf aktuellem `master`.
- Faktensammlung `issue8-work/context-2026-10-03.md`: gilt noch (Stand `e9c79ec4`); `weather_aggregate.py` ist seither unverändert, `calculation.py` nur um PR-1-Zeilen verschoben (siehe unten).

### 3.10 Umrechnung Spec-Zeilen (`e9c79ec4`) --> `6a40e083`
| Spec nennt | jetzt |
|---|---|
| `calculation.py:388-429` `_aggregate_for_zone` | `:393-434` |
| `calculation.py:635` / `:685` `_record_window_*` | `:644` / `:694` |
| `calculation.py:999-1008` Abgleich Aggregat/Teilschritte | `:1008-1017` (`build_substeps`-Aufruf `:998-1005`) |
| `calculation.py:329-386` Reset | `:329-391` |
| `store.py:372` `radiation_calibration` | `:374` |
| `store.py:1361` Lade-Pfad (Mapping) | `:1385-1405` |
| `store.py:1539` Erst-Einrichtung | `:1568` |
| `__init__.py:1820` Mapping anlegen | `:1844` |
| `websockets.py:236-241` Schema | `:235-250` (Zeilen unverändert, nur genauer) |
| `view-mappings.ts:379-380` | unverändert `:379-380` |
| `live_estimate.py:607`, `:880`; `weather_aggregate.py:*` | unverändert |
Nur diese Dateien (außer PR-1-Dateien) änderten sich zwischen `e9c79ec4` und `6a40e083`: `__init__.py`, `calculation.py` (13 Zeilen), `const.py`, `store.py`, `entity.py`, `distributor.py`, `master.py`, `run_chain.py`, `self_closing.py`, `watering_calendar.py`, Übersetzungen.

---

## 4. Offene Fragen / Entscheidungen, die die Spec von PR 2 treffen muss

1. **Feldtest-Bedingung (R9).** JustChr 188: Schnitt "once it has been field-tested"; PR 190: "Parts 2 and 3 ... whenever you are ready". Gilt R9 weiter wie in der Spec (Posten erst nach Feldtest auf HA-Prod)?
   Laut Memory-Index läuft der Feldtest von PR 1 auf HA-Prod (b1) noch (nicht von mir geprüft). Wann ist er "bestanden" (Dauer, Kriterien)?
2. **Rückgabe-Form der Masken und Sperren.** Das Aggregat ist ein flaches Dict `Feld --> Zahl`, das auch ans Rechenmodul geht (`calculation.py:1204`). Wohin mit "gesperrte Abschnitte je Feld" und "gültiger Anteil"? Optionen: Zusatz-Schlüssel nur
   bei übergebenen Masken (hält die Byte-Identität für alle anderen Aufrufer), zweiter Rückgabewert (ändert die Signatur für 2 Produktions- und ~20+ Test-Aufrufer), eigene Struktur neben `weatherdata`. Entscheiden und Name festlegen.
3. **Wer rechnet die gesperrte Zeit?** Neue reine Funktion in `sensor_liveness.py` (`blocked_spans(outages, now, fields) --> {Feld: [(von, bis)]}`) und deren Randfälle: offener Eintrag bis `now` des Commits (nicht Uhr);
   Sperre = `[start + STALE_AFTER, end]`, leer wenn `end < start + 3 h` (kurzer Ausfall, nie gesperrt); Vereinigung überlappender Einträge je Feld; Zuschneiden aufs Fenster `(Wasserzeichen, now]`; Feldzuordnung über `Outage.fields`
   (Snapshot beim Öffnen); Derselbe Wert für alle Zonen einer Gruppe (Gruppe, nicht Zone, trägt die Einstellung).
4. **Randzeile (Boundary).** `select_window` verwirft die Einzelstempel (`weather_aggregate.py:178`). Maskieren über das Wasserzeichen (Randwert gilt nur, wenn das Wasserzeichen außerhalb der Sperre liegt) oder über den echten Stempel
   (verlangt eine Änderung an `select_window`/`merge_latest_per_field`; dann ist die Byte-Identität der übrigen Aufrufer zu belegen)? Und: Was gilt nach dem Ende einer Sperre, wenn keine neue Zeile kommt (Ereignis-Pfad mit Totband schreibt nach der Rückkehr nichts,
   `context-2026-10-03.md` B.4)? Wird der Vor-Sperren-Wert wieder gehalten, oder ist das Feld bis zur nächsten Zeile gültig-ohne-Wert? Das legt das Verhalten für den häufigsten Fall (Ausfall endet, Sensor meldet gleichen Wert) fest.
5. **Mittel über einen Teil des Tages.** Das Tagesform-Mittel über nur den gültigen Teil verzerrt tageszeitabhängige Felder (Sonne, Temperatur, Tmax/Tmin) abhängig davon, WELCHER Teil gesperrt ist; der Buchungsanteil korrigiert nur die Menge, nicht die Form.
   Soll die Spec das als bekannte Grenze benennen (PR 3 behebt es für die Stundenrechnung) oder für Sonne/Temperatur ab einem Mindestanteil "fehlt" erklären?
6. **Buchungsanteil im Detail.** (a) Wo wird skaliert: `calculation.py:1255` (`et_delta = delta * kc * hour_multiplier * anteil`), nicht `elapsed_hours`/Drainage (`:1271`); (b) Mit `forecast_days > 0` ist `delta` das Mittel aus Wetter-Tag und Prognose-Tagen
   (`pyeto:246-268`): Wird nur der Wetter-Tag-Anteil skaliert oder das Mittel? (c) Wie kommt der Anteil zum Commit (Modul-API: `calculate(...)` hat heute keinen Parameter; die Spec nennt `calcmodules/pyeto` und `passthrough` als betroffen)?
   (d) Pflichtfelder-Liste: `DAILY_FORM_FIELDS` nutzt Min/Max-Temp (abgeleitet), die Masken kennen aber nur das Feld `Temperature`; Übersetzung festlegen. Humidity ist nicht Pflicht der Tagesform; Pressure schon.
7. **Passthrough und leeres ET-Feld.** Ein Feld ohne gültige Zeit "fehlt" (Spec) --> `calculate_module` liefert `None` (`calculation.py:1222-1232`) --> ERROR-Log, Wasserzeichen bewegt sich nicht (`:617-623`), das Fenster wächst, der 24-h-Wächter
   (`auto_calc.py:76-111`) kann zusätzlich committen. PyETO dagegen: WARNING + 0 gebucht, Wasserzeichen rückt vor. Soll Passthrough wie PyETO "Fenster verbrauchen, 0 buchen" oder bewusst anders behandelt werden?
8. **Wasserzeichen und volle Sperre.** Liegt das ganze Fenster in einer Sperre: Wasserzeichen vorrücken und 0 buchen (R5 sagt "nicht gebucht"), oder liegen lassen? (Verknüpft mit 7; und mit dem Erklärungssatz.)
9. **Hinweis-Variante.** Wortlaut (Spec nennt nur Entwurf, `Spec:336-341`, Freigabe "mit dem Plan"); Schlüsselname; wann wird neu synchronisiert: bei Ausfall-Öffnen/-Schließen (heute), **bei Wechsel von `on_silent_sensor`** (neuer Aufruf in `async_update_mapping_config`, `__init__.py:1814`) und
   **bei Wechsel der globalen Stundenrechnung** (`websockets.py:154`, Config-Pfad), sowie im Setup (`sensor_liveness.py:353-369`). Log-WARNING-Text je Fall.
10. **Erklärungssatz.** Schlüssel `module.calculation.explanation.sensor-outage`, Platzhalter ({fields}, {start}, {end}), Einfügestelle in der Erklärung (nach `:1417-1418`?), Zeitzonen-/Formatregel (naiv, HAs Uhr), Anzahl der Sätze bei mehreren Sperren/Feldern;
    8 Sprachen. Keine Sätze für *behalten* und (laut Spec) nicht bei eingeschalteter Stundenrechnung, da nichts geschnitten wird.
11. **Aufzeichnungen überspringen.** Kriterium für "Sonne bzw. Temperatur gesperrt": jede Überlappung oder ein Mindestanteil? (`_record_window_radiation` hat schon eigene Mindestlängen `:704-712`.)
12. **Unbekannter/ungültiger Wert des neuen Felds** beim Laden (von Hand editiert): Rückfall `keep`? Gültige Werte als Konstanten (`const.py`), Schema `vol.In([...])`.
13. **Domain-Migration:** Test wie von der Spec verlangt (`Spec:233-234`); Vorbild `tests/test_migrate_domain.py:59`.
14. **Live-Schätzung und Zwischenstand.** Spec nimmt hin, dass sie nach PR 2 nicht schneidet (`Spec:297-300`). Die Spec von PR 2 sollte den Satz im Hinweis/der Doku festlegen und die Kommentare an `live_estimate.py:590-596`, `:617-620` ("exactly as")
    anpassen, damit der Code nicht das Gegenteil behauptet.
15. **Doku-Fassung** (deutsch zur Freigabe, dann englisch): Erweiterung von `docs/configuration-sensor-groups.md:54-61` und Anpassung von `:57`; die Warnung für 6-h-Integrationen mit Ausweg *behalten* (Entscheidung 9).
16. **Lieferung/Release:** Branch von `upstream/master` (`6a40e083` oder neuer; vor Baubeginn Upstream-Runde und `git rev-list`), Version-Bump nicht im Feature-PR; dist neu bauen und mit `git add -f` stagen; PR-Text erst deutsch zur Freigabe,
    keine Verweise auf unsere Issues in Code/Commits/Doku (Memory `no-own-issue-refs-upstream`); `production` bekommt PR 2 sofort (User-Regel aus der Spec); Archivierung nach `archive/design-history` (P1).
17. **Live-Test auf HA-Test** (Wegwerf, Stundenrechnung aus): Mittel wie PR 1 (MQTT-YAML-Geräte unter eigenem Topic-Präfix); Kriterium laut Spec: Erklärung nennt die Sperre, ET nur für den gültigen Teil, *behalten*-Gruppe unverändert, mit Stundenrechnung kein Schnitt.
    Vorab zu benennen: welche Zahl wird mit welchem Soll verglichen (Anteil x ET).

---

## 5. Risiken und Fallen

- **Byte-Identität (R4):** Der neue Parameter von `aggregate_window` muss Standard `None` haben und den alten Pfad Zeile für Zeile erhalten; Zusatzschlüssel im Ergebnis nur bei übergebenen Masken. Für *behalten*-Gruppen darf der Commit die Ausfall-Liste
  nicht einmal lesen/parsen (billiger Vorab-Test auf die Einstellung). Test-Doubles ohne Schlüssel müssen `keep` ergeben.
- **Gate falsch herum:** `hourly_calculation_enabled(store)` ist strikt `is True` (`calculation.py:99-102`); die Spec verlangt "falsch" für den Schnitt. Test-Doubles ohne `config` lesen als "aus" und würden SCHNEIDEN, falls die Gruppe pausiert. Für die Masken-Fälle der Tests
  die Einstellung ausdrücklich setzen.
- **Eingefrorene Poll-Zeilen vor der Erkennung:** Zeilen innerhalb der ersten 3 h Stille (und bis zu 5 min Erkennungs-Latenz, plus 10 min Karenz nach HA-Start, `const.py:699-700`) sind nicht gesperrt; das ist gewollt (Überbrückung), aber ein Commit kann eine noch nicht eingetragene Sperre nicht sehen.
  Offener Eintrag bis `now` wird nur beim nächsten 5-min-Tick fortgeschrieben, nicht beim Commit.
- **Rückwirkung und Wechsel:** Die Liste gilt rückwirkend (R3, 7 Tage); ein Wechsel auf *pausieren* sperrt im nächsten Fenster auch Ausfälle, die bereits in einem früheren (anders gerechneten) Fenster lagen, soweit sie noch ins aktuelle Fenster ragen. Quellwechsel/Reset leeren die Liste:
  danach kann ein noch stummer Sensor erst nach der nächsten Prüfung wieder sperren (Latenz bis 5 min, Beginn aus `sensor_last_seen`).
- **Mischzustand mit Stundenrechnung:** Ist die Stundenrechnung an, schneidet PR 2 nicht; fällt `_hourly_et_for_zone` auf die Tagesform zurück (`calculation.py:894-905`, `:952-953`), rechnet diese auf dem **ungeschnittenen** Aggregat. Das ist gewollt, muss aber in Doku/Hinweis stehen.
  HA-Prod rechnet in der Stundenform: PR 2 ändert dort nichts (Spec: Gruppe "Greimerath" bleibt auf *behalten*).
- **Live-Schätzung weicht vom Commit ab** (siehe 3.5/Frage 14): bei ausgeschalteter Stundenrechnung und eingeschalteter Live-Schätzung zeigt die Live-Bilanz ungeschnittene ET, der Commit schneidet. Bestehende Tests, die Live und Commit vergleichen,
  laufen mit *behalten*-Gruppen unverändert; neue Tests dürfen sie nicht mit *pausieren* mischen.
- **Passthrough-Fall** (Frage 7): stilles Nicht-Verbrauchen des Fensters mit ERROR bei jedem Lauf, wenn das ET-Feld komplett gesperrt ist; PyETO verbraucht dagegen. Spiegel-Pfad nach Schwester-Pfad-Regel: beide Zweige im selben Fix klären.
- **Panel-Falle:** `saveToHA` schickt nur `{id, name, mappings}` (`view-mappings.ts:379-380`), das View-Schema lehnt Unbekanntes ab (`websockets.py:235-250`). Ein Frontend ohne den Schlüssel (alter Cache, Strg+F5-Drill) lässt die Einstellung unverändert; ein neues
  Frontend gegen ein altes Backend scheitert mit 400. Die optimistische Kopie einer neu angelegten Gruppe hat den Schlüssel erst nach `_fetchData`.
- **Bundle:** `en.json` ist im Bundle (`localize.ts:1`), die 4 Bundles sind getrackt und brauchen `git add -f` (Projekt-CLAUDE.md: ohne `-f` scheitert `git add` still, ein `&&`-Commit wird verschluckt); danach Dateizahl prüfen.
- **i18n-Aufwand:** Erklärungssatz + Auswahl (Titel, zwei Optionen, ggf. Hilfetext) in 8 Frontend-Dateien, Hinweis-Variante in 8 `translations/*.json`; `test_i18n_completeness` prüft Platzhalter-Gleichheit (`{group}`, `{entities}`, `{since}` müssen je Sprache gleich bleiben, `tests/test_i18n_completeness.py:175-208`).
- **Zeitumstellung/naiver Rahmen:** Sperren vergleichen naive HA-Zeit mit naiven Puffer-Stempeln; die Grenzen der Zeitumstellung gelten unverändert (`Spec:189-193`). `now` des Commits ist ebenfalls naiv (`calculation.py:577-578`).
- **Rollback:** Nach einem Rückbau auf PR 1 geht eine gesetzte *pause* verloren (Schlüssel wird beim Speichern verworfen); Wiederaufstieg liest `keep`. Kein Datenverlust, aber Verhalten ändert sich lautlos zu "behalten".
- **`Outage.fields` ist ein Snapshot** beim Öffnen (`sensor_liveness.py:232`); die Zuordnung Feld --> Entität darf sich laut Quellwechsel-Regel nur ändern, wenn die Liste geleert wird (`__init__.py:1804-1816`). Ein Test sollte zeigen, dass die Maske keine Felder erfindet, die der
  Ausfall nicht kannte.
- **Regenzähler-Ausnahme hängt am Aggregat zur Rechenzeit:** wer `Precipitation` auf `sum`/`riemannsum`/`average` stellt, bekommt die Sperre (Spec: Regenraten gesperrt). Das Aggregat wird über `effective_aggregate` aufgelöst (`weather_aggregate.py:412-439`); die Ausnahme darf nicht an
  der Quelle (Sensor) hängen, sondern am Aggregat `delta`.
- **Zeilenzahl `n_points`** (`calculation.py:408`, `:632`) zählt weiterhin eingefrorene Zeilen; die Zonen-Diagnose "Weather data points" ändert sich nicht. Nur anmerken, nicht beheben.
