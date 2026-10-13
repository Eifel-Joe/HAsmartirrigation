# Stummer Wettersensor, PR 2: der Schnitt im Tagespfad

Detail-Design für `Eifel-Joe#8`, Teil 2 der Aufteilung aus `JustChr#188` („(2) the cut in the daily path“).
**Ergänzt** die Spec `2026-10-03-dead-weather-sensor-design.md` (Revision 3, im Folgenden „Rev. 3“) und
entscheidet nur, was dort für PR 2 offen ist: die 17 Fragen aus §4 der Faktensammlung
`D:\Entwicklung\HASI\issue8-pr2-work\context-2026-10-11.md`. Alles, was hier nicht steht, gilt aus Rev. 3
(Abschnitte *Einstellung je Sensorgruppe*, *Schneiden: gemeinsame Regeln*, *Schnitt im Tagespfad*,
*Zwischenstände*, *Melden*).

Basis: `upstream/master` = `6a40e083` (Pre-Release v2026.10.05, enthält PR 1 als `7001c754`). Zeilenangaben
beziehen sich auf diesen Commit und auf `custom_components/irrigation_plus/`, sofern nicht anders angegeben; am
2026-10-12 per `git show 6a40e083:<pfad> | grep -n` bestätigt.

**Status: vom User freigegeben am 2026-10-12.** Die Entscheidungen F1–F4, der Ansatz und die Abschnitte 1–6 hat
der User am 2026-10-12 im Chat einzeln freigegeben, danach die schriftliche Fassung. Nächster Schritt: Plan für PR 2
(`superpowers:writing-plans`).

**Voraussetzung R9 erfüllt:** Feldtest von PR 1 auf HA-Prod (v2026.10.05b1, 2026-10-05 → 2026-10-12) ohne
Ausfall und ohne Fehlalarm bestanden, belegt in
<https://github.com/Eifel-Joe/HAsmartirrigation/issues/8#issuecomment-6121112008>. JustChrs Bedingung „the cut
rule follows once it has been field-tested“ (`JustChr#188`, Kommentar `5972596286`) ist damit erfüllt; nach dem
Merge von PR 1 schrieb er „Parts 2 and 3 of #188 can follow whenever you are ready“ (`JustChr#190`, Kommentar
`5997966126`).

## Ziel in einem Satz

Was nicht gemessen ist, wird nicht gebucht (R5) — für Sensorgruppen auf *pausieren*, nur ohne Stundenrechnung
(Entscheidung 8), im Commit des Tagespfads; Gruppen auf *behalten* rechnen und erklären byte-identisch wie heute
(R4).

Schreibweise: Fenster `[ws, we)` mit `ws` = Wasserzeichen der Zone (`last_consumed`), `we` = `now` des Commits.
Gültige Zeit eines Feldes `V` = Fenster minus seine Sperren. `s` = Buchungsanteil.

## Entscheidungen (User, 2026-10-12)

| # | Frage (§4) | Entscheidung | Grund | Verworfen |
|---|---|---|---|---|
| F1 | Feld ohne gültige Zeit (Fragen 7, 8) | **Angleichen:** Passthrough verbraucht das Fenster wie PyETO und bucht 0 ET, ohne ERROR; nur wenn das Feld *wegen einer Sperre* fehlt. Fehlt es aus anderem Grund, bleibt der heutige ERROR. | Beide Module folgen R5; die gebuchte ET-Summe ist in allen Varianten gleich, aber Liegenlassen friert Eimer, `last_calculated` und Drainage ein, weckt im Vor-Lauf-Modus jede Mitternacht den 24-h-Wächter (`auto_calc.py`, `async_guard_ledger_staleness`) und meldet einen Konfigurationsfehler, den es nicht gibt. | 2: wie heute liegen lassen (ERROR bei jedem Commit); 3: liegen lassen ohne ERROR |
| F2 | Wert nach Sperren-Ende ohne neue Zeile (Frage 4, zweite Hälfte) | **Der Wert von vor der Sperre gilt ab ihrem Ende wieder**, bis zur nächsten Zeile. `V` hängt nur an der Ausfall-Liste und den Fenstergrenzen. | Im Ereignis-Betrieb heißt „keine Zeile“ nach der Code-Logik „innerhalb des Totbands gleich dem letzten geschriebenen Wert“ (`continuous_update.py:93-101`, `:463-476`); eine Rückkehr mit gleichem Wert feuert nur `state_reported` und schreibt nichts. Im Poll-Betrieb unterscheiden sich die Varianten höchstens um einen Abruf. | 2: Feld ohne Wert bis zur nächsten Zeile (bestraft den häufigsten Fall mit zu wenig ET, im Extremfall bis Fensterende) |
| F3 | Mittel über einen Teiltag (Frage 5) | **Als bekannte Grenze benennen**, kein Mindestanteil. | Kürzere Fenster als 24 h rechnet der Commit heute schon genauso (Vor-Lauf-Modus, Neuberechnung von Hand); die Aufzeichnungen überspringen kurze Fenster bereits (`const.py:675`, `:682`). | 2: Mindestanteil (Temperatur ist Pflichtfeld → 0 ET für das ganze Fenster); 3: Anteil nach Sonnenstand gewichten (Aufwand für einen Zwischenstand, PR 3 ersetzt ihn) |
| F4 | Anteil bei `forecast_days > 0` (Frage 6b) | **Das ganze Mittel skalieren:** `delta × kc × hour_multiplier × s`. | Entspricht Rev. 3 wörtlich und Entscheidung 1 (kein Rückfall auf den Wetterdienst); kein neuer Modul-Parameter. Standard ist `forecast_days = 0` (`calcmodules/pyeto/__init__.py:56`). | 2: nur den Wetter-Tag im Mittel gewichten (Prognose bucht in der Sperre weiter) |
| A | Rückgabe der Masken (Fragen 2, 3) | **Ansatz 1: Sperren laufen neben dem Aggregat**, als optionales Schlüsselwort `blocked=`; das Aggregat bleibt das flache Dict. | Nach F2 braucht niemand eine Rückmeldung des Aggregats; keine Rückgabeform ändert sich (Test-Aufrufe: `aggregate_window` 36, `_aggregate_for_zone` 24, `calculate_module` 56; je 1–2 in Produktion). | 2: Zusatzschlüssel im Ergebnis (Metadaten im Messwert-Dict); 3: Ergebnis-Objekt (Signaturbruch) |

Nachtrag zu F1: „PyETO bucht 0“ gilt für den Standard `forecast_days = 0`. Mit Prognosetagen bucht PyETO heute bei
fehlendem Pflichtfeld `mean(0, Prognosen)` (`calcmodules/pyeto/__init__.py:246-268`, `:462`); nach F4 bucht der
Schnitt dann 0.

## 1. Sperren berechnen, Gate, Transport

- **Reine Funktion** `blocked_spans(outages, start, end) -> dict[str, tuple[tuple[datetime, datetime], ...]]` in
  `sensor_liveness.py`:
  - Sperre eines Eintrags = `[start + STALE_AFTER, end)`, **halboffen** — die Zeile der Rückkehr zählt als gültig.
    Ein offener Eintrag (`end is None`) läuft bis zum `end`-Argument (= `now` des Commits, nicht die Uhr).
  - Ein Eintrag mit `end ≤ start + STALE_AFTER` (Ausfall kürzer als 3 h) ergibt keine Sperre.
  - Felder aus `Outage.fields` (Schnappschuss beim Öffnen, `sensor_liveness.py:110-163`); die Funktion erfindet
    keine Felder.
  - Je Feld Vereinigung der Einträge, Zuschnitt auf `[start, end)`, sortiert; Felder ohne Rest fehlen im Ergebnis.
  - Kennt keine Aggregate und liest keine Uhr.
- **Gate und Regenzähler-Ausnahme** in einer neuen Methode `_blocked_spans_for_zone(zone, now)` im Rechen-Mixin.
  Sie liefert `None`, wenn
  - die Gruppe nicht auf `pause` steht (gelesen mit `.get(MAPPING_ON_SILENT_SENSOR, "keep")`, Test-Doubles ergeben
    `keep`), oder
  - `hourly_calculation_enabled(self.store)` wahr ist (`calculation.py:87`), oder
  - die Zone kein Wasserzeichen hat (nie verbrauchte Zone rechnet wie heute; ihr erster Commit verankert sie), oder
  - nach dem Filtern keine Sperre bleibt (eine pausierende Gruppe ohne Sperre im Fenster rechnet exakt wie heute).

  Sonst `blocked_spans(outages_of(mapping), watermark, now)`, ohne die Felder, deren
  `effective_aggregate(key, mappings_config)` (`weather_aggregate.py:412`) `delta` ist — die Regenzähler-Ausnahme
  hängt am Aggregat, nicht an der Quelle (Rev. 3).
- **Transport (Ansatz 1):** `async_calculate_zone` (`calculation.py:560`) ruft die Methode einmal und reicht das
  Ergebnis als `blocked=` (Standard `None`) an:
  `_aggregate_for_zone` (`:393`) → `aggregate_window` (`weather_aggregate.py:321`); `calculate_module`
  (`calculation.py:1140`); `_record_window_amplitude` (`:644`); `_record_window_radiation` (`:694`).
  Die Live-Schätzung (`live_estimate.py:607`) übergibt nichts.
- **Bewusst hingenommen:** Der Commit sieht eine Sperre erst, wenn die Prüfung (alle 300 s) den Eintrag geöffnet hat;
  ein offener Eintrag, dessen Sensor gerade zurückkam, sperrt bis zur nächsten Prüfung, also höchstens 5 min zu viel.
  Der Commit stößt **keine eigene Prüfung** an — die schreibt in den Store und feuert Events, das gehört nicht in den
  Rechenpfad.

## 2. Aggregation unter Masken (`aggregate_window(…, blocked=None)`)

- **Unverändert:** Mit `blocked=None` läuft kein neuer Code. Auch mit Masken gehen Felder **ohne** Eintrag in
  `blocked` durch den heutigen Zweig von `_aggregate` (`weather_aggregate.py:501`) — byte-identisch.
  `select_window` (`:137`) bleibt unangetastet.
- **Für ein gesperrtes Feld f:**
  - **`V` leer** → f fehlt im Ergebnis: kein `last_entry`-Auffüllen, bei Temperatur auch kein Tmin/Tmax.
  - **Proben** wie heute: Randzeile auf `ws` umgestempelt, Fensterzeilen, `last_entry` ungestempelt. Eine
    Fensterzeile mit Stempel in einer Sperre fällt weg (trifft eingefrorene, frisch gestempelte Poll-Zeilen). Die
    Randzeile bleibt immer als Wert erhalten, zählt als Probe aber nur, wenn `ws` in `V` liegt.
  - **Haltewert h(t):** Wert der letzten verbliebenen Probe mit Stempel ≤ t; vor der ersten die erste (wie heute,
    `_time_weighted_mean`, `:256`). Nach einer Sperre gilt damit wieder der Wert von davor (F2).
  - **`average`, zeitgewichtet:** ∫ h über `V` / |`V`|.
  - **`average`, einfach** (Poll-Standard): Mittel der Proben in `V`; keine Probe in `V` → h am Beginn des ersten
    gültigen Abschnitts.
  - **Tmin/Tmax:** Min/Max von h über `V` (= Proben in `V` plus Haltewert am Beginn jedes gültigen Abschnitts).
  - **`first`/`last`/`maximum`/`minimum`/`median`/`sum`:** über die Proben in `V`; keine → h als Einzelwert.
  - **Einzelwert-Zweig** und **`last_entry`-Auffüllung:** wie heute, nur wenn `V` nicht leer ist.
  - **`riemannsum`** (Regenrate): jedes Trapez zählt nur mit seinem Zeitanteil in `V`; über eine Sperre hinweg wird
    kein Regen interpoliert.
  - **`delta`** (Regenzähler) kommt nie gesperrt an (Abschnitt 1).
- **Prüfstein:** Ein Feld mit leer zugeschnittener Sperre und ein Feld ohne Eintrag ergeben dasselbe wie
  `blocked=None`. Für „Sperre am Fensterstart“, „am Fensterende“, „mitten drin“ je Aggregat ein von Hand gerechneter
  Sollwert.

## 3. Buchen (`calculate_module(…, blocked=None)`)

- **Anteil** `s = |⋂ V_p über die Pflichtfelder p| / |[ws, we)|`, neue reine Funktion
  `valid_share(blocked, fields, start, end)` neben `blocked_spans`. Ein Pflichtfeld ohne Eintrag in `blocked` gilt
  im ganzen Fenster.
  - **PyETO, Tagesform:** Pflichtfelder = `DAILY_FORM_FIELDS` (`calcmodules/pyeto/__init__.py:114-120`), Min-/Max-
    Temperatur abgebildet auf das gemappte Feld `Temperature` → Taupunkt, Temperatur, Wind, Druck. Sonne und Feuchte
    zählen nicht; fehlt die Sonne ganz, schätzt PyETO sie wie heute.
  - **Passthrough:** `Evapotranspiration`.
  - **Static:** kein Sensorfeld, unverändert.
- **Wo:** nur im Tagesform-Zweig, `et_delta = delta * kc * hour_multiplier * s` (`calculation.py:1255`), und nur bei
  `blocked is not None` — sonst bleibt der Ausdruck wörtlich der heutige. Der Stundenzweig (`:1251-1252`) wird unter
  Masken nie erreicht (Gate). Das Mittel aus Wetter- und Prognosetagen wird als Ganzes skaliert (F4).
- **`s = 0`** (ein Pflichtfeld ganz gesperrt oder keine gemeinsame gültige Zeit): Modul wird **nicht** aufgerufen,
  ET = 0 — keine PyETO-„missing“-WARNINGs (`calcmodules/pyeto/__init__.py:438-462`), kein Passthrough-ERROR
  (`calculation.py:1222-1232`). Das Fenster wird verbraucht, das Wasserzeichen rückt vor (§4 Frage 8). PyETO bucht
  weiter Regen (Zähler voll, Rate nur über ihre gültige Zeit). Die Erklärung nennt die Sperre (Abschnitt 5).
- **ET-Feld fehlt aus anderem Grund** (kein Eintrag in `blocked`): Passthrough-ERROR und `return None` wie heute
  (`:1222-1232`, `:617-623`).
- **Unverändert über das ganze Fenster:** Drainage (`elapsed_hours = hour_multiplier * 24`, `:1271` — physikalische
  Zeit, keine Messung), Wasserzeichen, `n_points`, Replay-Gate.
- **Bekannte Grenze (F3):** Die Tagesform-Mittel eines Teiltags hängen davon ab, welcher Teil gesperrt war (der
  Sonnen-Deckel von PyETO, die Tmin/Tmax-Spanne eines Teiltags). Spec und Doku nennen es; ohne Grenze ist die
  Stundenrechnung, die ab PR 3 ebenfalls schneidet.
- `calcmodules/pyeto` und `calcmodules/passthrough` bleiben **unverändert**; `DAILY_FORM_FIELDS` wird nur gelesen.

## 4. Einstellung je Sensorgruppe

Rev. 3 (*Einstellung je Sensorgruppe*) gilt; hier das bisher Offene.

- **Konstanten** in `const.py`: `MAPPING_ON_SILENT_SENSOR = "on_silent_sensor"`, Werte `keep` / `pause` (eigene
  Konstanten plus Tupel der gültigen Werte).
- **Feld** `MappingEntry.on_silent_sensor` (`store.py:352`), Attribut-Standard `pause`, ohne Store-Versionssprung.
- **Laden** (`store.py:1385-1405`): fehlender Schlüssel, `None` oder ein unbekannter Text → `keep` (§4 Frage 12). Ein
  von Hand verbogener Wert schneidet nie.
- **Neu angelegte Gruppen pausieren:** Panel/Assistent über `async_create_mapping` (`store.py:2191`,
  `MappingEntry(**data)` `:2196`) und die Erst-Einrichtung `async_factory_default_mappings` (`:1534`) — auch bei
  einem Bestand, der alle Gruppen gelöscht hat (die Ersatzgruppe ist neu).
- **Domain-Migration:** Test nach Vorbild `tests/test_migrate_domain.py:59` belegt, dass übernommene Gruppen `keep`
  laden (§4 Frage 13).
- **View-Schema** (`SmartIrrigationMappingView`, `websockets.py:229`, Schema um `:240`):
  `vol.Optional(MAPPING_ON_SILENT_SENSOR): vol.In([keep, pause])`; andere Werte → 400.
- **Panel** (`frontend/src/views/mappings/view-mappings.ts`): Auswahl in der Gruppenkarte zwischen Namenszeile und
  `renderMappingSettings` (`:1046`), Muster `renderAggregateSelect` (`:687`); `saveToHA` schickt
  `{id, name, mappings, on_silent_sensor}` (heute `:379-380`); TS-Typ `SmartIrrigationMapping`
  (`frontend/src/types.ts`) bekommt das Feld. Ein altes Frontend ohne den Schlüssel lässt die Einstellung stehen
  (`attr.evolve`). Beschriftungen in 8 Sprachen, `dist` neu bauen.
- **Wirkung eines Wechsels:** ab dem nächsten Commit für alle Ausfälle, die sein Fenster berühren (Rev. 3); der Hinweis
  wird sofort angeglichen (Abschnitt 5).
- **Rückbau auf einen PR-1-Build:** ein gesetztes `pause` geht verloren (der Build schreibt ohne den Schlüssel
  zurück), nach erneutem Upgrade `keep`. Kein Datenverlust; hingenommen, der PR-Text nennt es.

## 5. Melden

- **Hinweis-Variante:** `_sync_stale_issue` (`sensor_liveness.py:484`) wählt den Übersetzungsschlüssel selbst:
  `weather_sensor_stale_paused`, wenn die Gruppe pausiert **und** die Stundenrechnung aus ist, sonst wie bisher
  `weather_sensor_stale` (`const.py:714`). Gleiche Issue-ID, gleiche Platzhalter `{group}`, `{entities}`, `{since}`.
  **Neu synchronisiert** wird zusätzlich zu Öffnen/Schließen und Setup:
  - beim Wechsel von `on_silent_sensor` in `async_update_mapping_config` (`__init__.py:1751`), für diese Gruppe;
  - beim Umschalten der Stundenrechnung in `async_update_config` (`__init__.py:1168`), für alle Gruppen mit offenem
    Eintrag.
- **Log:** WARNING beim Öffnen nennt bei pausierender Gruppe ohne Stundenrechnung den Schnitt („… has not reported
  since …; its values are no longer used and no evapotranspiration is booked while it is silent“), sonst PR-1-Text.
  INFO beim Schließen unverändert. Ein Wechsel der Einstellung schreibt keine eigene Zeile.
- **Erklärung der Zone** (nur bei `blocked is not None`; *behalten* und Fenster ohne Sperre byte-identisch):
  - Satz 1 je Sperre, Felder mit gleicher Sperre zusammengefasst — `module.calculation.explanation.sensor-outage`:
    „Keine Werte von {fields} von {start} bis {end} (Sensor stumm).“ Feldnamen aus den Panel-Beschriftungen
    `panels.mappings.cards.mapping.items.*` (`frontend/localize/languages/en.json:454-464`); Zeiten
    `JJJJ-MM-TT HH:MM` auf HAs Uhr (der Rahmen der Puffer-Stempel).
  - Satz 2 nur bei `s < 1` — `module.calculation.explanation.sensor-outage-share`: „Verdunstung für {share} % des
    Zeitraums gebucht.“ (ganze Prozent). Ist nur Sonne oder Feuchte gesperrt, fehlt Satz 2 zu Recht.
  - Stelle: direkt nach dem ET-Satz (und ggf. dem Kc-Satz, `calculation.py:1405-1428`), vor „Eimer war“
    (`bucket-was`, `:1431`).
  - 8 Sprachen in `frontend/localize/languages/*.json`, `dist` neu bauen.

## 6. Aufzeichnungen, Live-Schätzung, Doku

- **Aufzeichnungen** (§4 Frage 11): `_record_window_radiation` lässt das Fenster aus, sobald `Solar Radiation` in
  `blocked` steht; `_record_window_amplitude` ebenso bei `Temperature`. Jede Überschneidung zählt, kein
  Mindestanteil.
- **Live-Schätzung** (§4 Frage 14) schneidet weiter nicht (Rev. 3, *Zwischenstände*). Die Kommentare „exactly as
  `_aggregate_for_zone`“ (`live_estimate.py:590-596`) und „Must match _aggregate_for_zone exactly“ (`:612-619`)
  bekommen den Zusatz, dass der Commit einer pausierenden Gruppe ohne Stundenrechnung Sperren anwendet und die
  Live-Schätzung noch nicht. Kein „PR 3“ im Code.
- **Doku** (§4 Frage 15) `docs/configuration-sensor-groups.md`, Abschnitt „When a sensor goes silent“ (`:54-61`):
  neuer Absatz zur Einstellung (was *pausieren* tut; Bestand behält, neue Gruppen pausieren; Rat *behalten* bei
  Integrationen, die nur alle paar Stunden aktualisieren; mit Stundenrechnung gilt der letzte Wert weiter; die Grenze
  aus F3; der Live-Schätzungs-Zwischenstand). Der Satz `:57` („Meanwhile the calculation keeps using the sensor's
  last value.“) wird auf *behalten* eingeschränkt.

## Tests

Die Liste aus Rev. 3 (*Tests*, PR 2) gilt; zusätzlich:

- `blocked_spans`: halboffen, Ausfall unter 3 h ergibt nichts, offen bis `end`, Vereinigung überlappender Einträge,
  Zuschnitt aufs Fenster, keine Felder außerhalb von `Outage.fields`.
- `valid_share`: Schnittmenge, nicht Minimum der Einzelanteile; Pflichtfeld ohne Sperre = ganzes Fenster.
- Gate: `keep`, Stundenrechnung an, kein Wasserzeichen, leere Sperren → `None`; Regenzähler (`delta`) nie gesperrt,
  Regenrate (`riemannsum`/`sum`) gesperrt.
- Aggregation je Aggregat mit Sollwerten von Hand (Sperre am Anfang, am Ende, mitten drin); ungesperrte Felder und
  leere Sperren gleich `blocked=None`; Rückkehr ohne neue Zeile hält den Wert von davor (F2).
- Buchen: Anteil an `:1255`; `s = 0` → PyETO nicht aufgerufen, Regen gebucht, Fenster verbraucht; Passthrough ohne
  ERROR, Fenster verbraucht; Passthrough ohne ET-Feld und ohne Sperre → ERROR wie heute; `forecast_days > 0` als
  Ganzes skaliert.
- Erklärungssätze (zusammengefasste Felder, Satz 2 nur bei `s < 1`, keiner bei *behalten*); Hinweis-Variante und
  beide neuen Auslöser; Log-Text.
- Laden mit ungültigem Wert, Domain-Migration, Schema, Panel-Speichern (vitest, `view-mappings-save.test.ts`),
  i18n-Completeness.
- Byte-Identität: *behalten* mit Ausfällen in der Liste, pausierend mit Stundenrechnung, pausierend ohne Sperre im
  Fenster — Ergebnis und Erklärung gleich wie ohne PR 2.
- Volle Suite mit Namensvergleich gegen eine **auf der Baubasis neu gemessene** Baseline; Mutationen auf Gate,
  Halboffenheit, Schnittmenge, `s = 0`, Regenzähler-Ausnahme; RED vor GREEN.

## Ende-zu-Ende-Kriterium (HA-Test)

HA-Test, Stundenrechnung aus, MQTT-YAML-Geräte unter eigenem Topic-Präfix wie bei PR 1. Ein Sensor einer
pausierenden Gruppe schweigt 3,5 h, danach Berechnung der Zone.

- **Soll, vorab gerechnet:** aus Wasserzeichen, `now` und dem Eintrag in den Diagnostics
  (`data.store.mappings[].sensor_outages`) der Anteil `(Fenster − Sperre) / Fenster` auf ganze Prozent; Satz 2 nennt
  genau diesen Wert, Satz 1 nennt `start + 3 h` bis `end`.
- Dieselbe Lage auf *behalten*: kein Satz, Rechnung wie vorher. Mit Stundenrechnung: kein Satz.
- Der Hinweistext wechselt beim Umschalten der Einstellung und der Stundenrechnung.
- Danach Stundenrechnung zurückstellen. Das 60-min-Intervall und der Pirate-Schlüssel auf HA-Test bleiben unberührt;
  die Zonen 0/1 kommen nie auf `service`.

## Lieferung

- Branch von dem `upstream/master`, der zum Baubeginn aktuell ist (vorher Upstream-Runde und
  `git rev-list --count HEAD..upstream/master`), im Worktree; kein Versionssprung im PR.
- `dist` neu bauen, mit `git add -f` stagen, Dateizahl prüfen (Projekt-`CLAUDE.md`).
- Diff und Commit-Messages auf eigene Bezüge greppen (Memory `no-own-issue-refs-upstream`); PR-Text erst deutsch zur
  Freigabe.
- Ablauf wie PR 1: Pre-Release → Live-Test HA-Test → PR. Auf HA-Prod ändert PR 2 nichts (Stundenrechnung, Gruppe
  „Greimerath“ auf *behalten*); ein Update dort nur auf Zuruf.
- Archiv nach P1 jeweils nach Freigabe von Spec und Plan.

## Ausdrücklich nicht in PR 2

- Schnitt im Stundenpfad und in der Live-Schätzung (PR 3).
- Dienst-Felder (`Eifel-Joe#74`), einstellbare Grenze, Abschalten des Hinweises (Rev. 3).
- Eine eigene Liveness-Prüfung im Commit (Abschnitt 1).
- Mindestanteil für Teiltage (F3); Rückfall auf die Prognose (F4).
- Masken für nie verbrauchte Zonen (Abschnitt 1).
- Änderungen an `select_window`, an `calcmodules/pyeto` und `calcmodules/passthrough`.

## Betroffene Stellen PR 2 (ersetzt die PR-2-Liste in Rev. 3)

`const.py`, `store.py`, `websockets.py`, `__init__.py` (zwei Re-Sync-Aufrufe), `sensor_liveness.py`
(`blocked_spans`, `valid_share`, Hinweis-Variante, Log-Text), `weather_aggregate.py` (Masken), `calculation.py`
(Gate-Methode, Transport, Anteil, `s = 0`, Aufzeichnungen, Erklärungssätze), `live_estimate.py` (nur Kommentare),
`translations/*.json` (Hinweis-Variante), `frontend/src/views/mappings/view-mappings.ts`, `frontend/src/types.ts`,
`frontend/localize/languages/*.json`, `frontend/dist/` (4 Bundles), `docs/configuration-sensor-groups.md`, Tests.

## Zuordnung der offenen Fragen (§4 der Faktensammlung)

| § 4 | Wo entschieden |
|---|---|
| 1 Feldtest-Bedingung | Kopf (*Voraussetzung R9 erfüllt*) |
| 2 Rückgabe-Form | Entscheidung A, Abschnitt 1 |
| 3 Wer rechnet die Sperren | Abschnitt 1 |
| 4 Randzeile / Wert nach Sperre | Abschnitt 2, F2 |
| 5 Mittel über Teiltag | F3, Abschnitt 3 |
| 6 Buchungsanteil (a–d) | Abschnitt 3, F4 |
| 7 Passthrough ohne ET | F1, Abschnitt 3 |
| 8 Wasserzeichen bei voller Sperre | F1, Abschnitt 3 |
| 9 Hinweis-Variante | Abschnitt 5 |
| 10 Erklärungssatz | Abschnitt 5 |
| 11 Aufzeichnungen | Abschnitt 6 |
| 12 Ungültiger Wert | Abschnitt 4 |
| 13 Domain-Migration | Abschnitt 4 |
| 14 Live-Schätzung | Abschnitt 6 |
| 15 Doku | Abschnitt 6 |
| 16 Lieferung | *Lieferung* |
| 17 Live-Test | *Ende-zu-Ende-Kriterium* |

## Wortlaute zur Freigabe mit dem Plan (Entwürfe, Deutsch)

- **Panel:** Titel „Wenn ein Sensor verstummt“; Optionen „Pausieren“ / „Letzten Wert behalten“; Hilfe „Pausieren:
  Nach 3 Stunden ohne Meldung werden die Werte des Sensors nicht mehr verwendet, und für diese Zeit wird keine
  Verdunstung gebucht. Gilt nur ohne stündliche Berechnung.“
- **Hinweis `weather_sensor_stale_paused`** (Titel wie PR 1): „Irrigation Plus hat seit {since} nichts mehr von
  {entities} gehört. Nach drei Stunden Stille werden diese Werte nicht mehr verwendet, und für die Zeit ohne Werte wird
  keine Verdunstung gebucht; Zonen, die davon abhängen, wässern deshalb weniger oder gar nicht, bis wieder Werte
  kommen. Prüfe das Gerät und seine Integration. Hast du das Gerät ersetzt, wähle seine neuen Entitäten in der
  Sensorgruppe. Soll der Wert fest sein, nutze stattdessen die Quelle „Fester Wert“. Aktualisiert die Integration nur
  alle paar Stunden, stelle die Sensorgruppe auf „Letzten Wert behalten“ — sonst fehlt bei jedem Update ein Teil der
  Zeit. Dieser Hinweis verschwindet von selbst, sobald der Sensor wieder meldet.“
- **Erklärung:** „Keine Werte von {fields} von {start} bis {end} (Sensor stumm).“ / „Verdunstung für {share} % des
  Zeitraums gebucht.“
- **Doku-Absatz:** Fassung folgt im Plan, deutsch zur Freigabe, dann englisch.

Die englischen und die übrigen sechs Fassungen folgen dem freigegebenen Deutsch; Quellen-Namen sind die
Panel-Beschriftungen.

## Nachtrag 2026-10-13 — nach der Abschluss-Review (User-Entscheidungen E1–E4)

Die Abschluss-Review (Opus, Bericht im Archiv `probes/2026-10-12-dead-weather-sensor-pr2-build/final-review-report.md`)
fand zwei Lücken dieser Spec; beide vom Controller am Code nachgeprüft. Entscheidungen des Users im Chat 2026-10-13:

- **E1 = 2 — Hinweis und Log nur, wo wirklich geschnitten wird, Wortlaut eingeschränkt.** §5 knüpfte die Variante
  `weather_sensor_stale_paused` nur an „pausiert und keine Stundenrechnung“. Fällt nur ein Regenzähler aus (Aggregat
  `delta`, nach §1 nie gesperrt), behauptete der Hinweis einen Schnitt, den die Rechnung nicht macht; für Feuchte oder
  Sonne allein stimmte „keine Verdunstung gebucht“ nicht (§3: nur Pflichtfelder zählen). Neu:
  - Ein gemeinsamer Helfer „wird dieses Feld geschnitten“ (jedes Feld außer `effective_aggregate == delta`) für das
    Gate (§1) und den Hinweis; die Variante und der Schnitt-Text im WARNING erscheinen nur, wenn die Gruppe schneidet
    **und** ein offener Ausfall (beim Log: dieser Ausfall) mindestens ein solches Feld hat. Sonst PR-1-Text.
  - Neu synchronisiert wird zusätzlich, wenn sich die Zuordnung der Gruppe (`mappings`) ändert.
  - Wortlaut von Hinweis, Log, Panel-Hilfe und Doku: „wo die Verdunstungsrechnung ohne einen davon nicht auskommt, wird
    … keine Verdunstung gebucht“; „ein Regenzähler zählt weiter“.
- **E2 = 2 — gerätelose Sensoren, die nur bei Wertänderung melden:** Doku und Hinweis sagen, dass *Pausieren* deren
  Werte bei langer Gleichheit (Wind-Template bei Windstille) auslässt, und raten zu *Letzten Wert behalten* oder einem
  UI-Template-Helfer am Gerät der Station. Kein Code; Rev. 3 nahm für diese Klasse nur den Fehlalarm hin, der Schnitt
  ist damit benannt.
- **E3 = freigegeben:** (a) Satz 2 der Erklärung zeigt höchstens 99 %, solange `share < 1`, und mindestens 1 %, solange
  `share > 0`; bei 0 bleibt 0 % (ersetzt „`f"{share * 100:.0f}"`“ aus den Global Constraints des Plans). (b) Panel-Hilfe
  und Doku nennen die Einstellung beim UI-Namen „Stündliche Verdunstung“ / „Hourly evapotranspiration“ (Experimentelle
  Funktionen). (c) Doku ohne relative Zeitangaben („from now on“, „existed before“), Satz zu seltenen Updates eindeutig.
- **E4 = 3:** ruff in der Upstream-CI ist ungepinnt (0.17.0 meldet 20 UP017 in Dateien, die dieser Branch nicht
  anfasst) — abwarten, vor dem PR nachsehen.

Freigegebene Wortlaute (de/en) stehen im Plan, Task 10b. Die übrigen sechs Sprachen folgen dem englischen Text.
