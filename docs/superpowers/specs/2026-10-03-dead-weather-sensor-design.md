# Ein stummer Wettersensor wird nicht endlos weiterverwendet

Design für `Eifel-Joe#8`. Basis: `upstream/master` = `e9c79ec4` (Beta v2026.10.03). Alle Zeilenangaben
beziehen sich auf diesen Commit und auf `custom_components/irrigation_plus/`, sofern nicht anders
angegeben. Faktensammlung: `D:\Entwicklung\HASI\issue8-work\context-2026-10-03.md`, im Archiv als
`docs/superpowers/probes/2026-10-03-dead-weather-sensor-survey.md` (Agent; die tragenden Aussagen am 2026-10-03
selbst nachgelesen, Zeilen per `grep -n` bestätigt). Vorschlag an JustChr: `JustChr#188`.

**Status:** Verhalten mit dem User am 2026-10-03 entschieden (sieben Fragen, vier Design-Abschnitte; siehe
*Entscheidungen*). **Mit JustChr noch nicht abgestimmt:** Der Vorschlag geht zuerst als Issue auf sein Repo,
gebaut wird nach seiner Antwort. Die Feinheit des Schnitts (Design 1 oder Design 2) soll er wählen; unsere
Präferenz ist Design 2.

## Der Defekt

Liefert ein Sensor einer Sensorgruppe nichts mehr, rechnet die Integration mit seinem letzten Wert weiter,
zeitlich unbegrenzt und ohne dass es irgendwo sichtbar wird. Drei Träger:

1. **Die Grenzzeile je Feld überlebt jedes Ausdünnen.** `_prune_mapping_buffer` behält je Feld die letzte
   Zeile vor dem Schnitt, ohne auf ihr Alter zu sehen (`calculation.py:458-481`). `BUFFER_RETENTION`
   (7 Tage) verschiebt nur den Schnitt. Der Docstring behauptet das Gegenteil (`calculation.py:436-437`:
   „hard-drops anything older than the retention cap“).
2. **Ihr Alter wird unsichtbar.** `select_window` verwirft die Einzelstempel der Grenzwerte
   (`weather_aggregate.py:178`), `aggregate_window` stempelt die Grenzzeile auf das Watermark um (`:367`),
   der Wert wird bis zum Fensterende gehalten (`:217-224`), und ein Einzelwert geht unverändert als Ergebnis
   durch (`:523`). Dasselbe Umstempeln in `_effective_series` (`:714`), dem Einstieg von Stundenzeilen und
   nachgespielter Bilanz.
3. **`last_entry` füllt ungestempelt auf.** Fehlt ein Feld im Fenster, nimmt die Aggregation den letzten
   Ereigniswert ohne Zeitstempel (`weather_aggregate.py:371-396`); ebenso die Stundenzeilen (`:936`) und
   der Temperatur-Anker des Live-Estimate (`live_estimate.py:880`).

Dazu im Poll-Betrieb: Ein toter Sensor, der seinen Zahlenwert behält, wird bei jedem Poll mit frischem
Stempel neu geschrieben (`build_sensor_values_for_mapping`, `__init__.py:1871`) und sieht lebendig aus.

Synthetisch nachgemessen (Agent, gegen `e9c79ec4`): Ein 30 Tage alter Temperaturwert übersteht das
Ausdünnen (160 → 2 Zeilen) und kommt als Temperatur = Tmax = Tmin zurück, zeitgewichtet wie ungewichtet.
Seit der letzten Nachprüfung (2026-09-29, `1876aa03`) unverändert: `a503dc40`, `faa05b0b` und `98859077`
berühren die beiden Dateien, aber keinen der drei Träger.

## Wie ein toter Sensor in HA aussieht (je nach Integration)

Das Design darf nicht an einer Station hängen (User, 2026-10-03: „Ich habe Ecowitt. Andere Nutzer haben
andere Stationen.“). Drei Erscheinungsformen, für die Integration heute alle mit demselben Ergebnis:

- **Die Entität geht auf `unavailable`/`unknown`** (etwa MQTT-Sensoren mit `expire_after`, ESPHome bei
  abgerissener Verbindung). Ereignis-Pfad und Poll verwerfen solche Zustände (`continuous_update.py:359`,
  `__init__.py:1871`ff.); das Feld bekommt keine Zeilen mehr, der letzte Wert wird weitergetragen.
- **Die Entität behält ihren letzten Wert und schreibt nicht mehr** (Push-Integrationen wie `ecowitt`;
  Integrationen, die nur bei Änderung schreiben). Ereignis-Pfad: keine Zeilen. Poll: der eingefrorene Wert
  wird bei jedem Poll frisch gestempelt.
- **Die Entität meldet weiter denselben Wert, obwohl die Station schweigt** (Integrationen, die die letzte
  Beobachtung eines Cloud-Dienstes abholen). `last_reported` rückt vor; ohne die Beobachtungszeit des
  Dienstes ist das nicht erkennbar → blinder Fleck, siehe *Ausdrücklich nicht in dieser Arbeit*.

Integrationen unterscheiden sich außerdem darin, ob sie unveränderte Werte schreiben: Manche rücken
`last_reported` bei jedem Update vor (wie `ecowitt`), andere nur bei einer Änderung. Deshalb misst die
Erkennung am **Gerät**: An einer lebenden Station meldet oder ändert sich innerhalb von 3 h immer irgendein
Wert, außer womöglich dem Regen.

## Warum es auf HA-Prod scharf ist

- Die Sensorgruppe „Greimerath“ ist eine **reine Sensorgruppe**: alle belegten Felder `source: sensor`
  (Evapotranspiration hat keine Quelle), eine EcoWitt-Station über die Core-Integration `ecowitt` (Local
  Push). Mit `continuousupdates` überspringt der
  Poll sie (`__init__.py:1559-1584`); Zeilen entstehen nur, wenn sich ein Wert ändert.
- `ecowitt`-Entitäten schreiben nur beim Push (`should_poll = False`), und `available` wird nur beim
  Schreiben ausgewertet (`homeassistant/components/ecowitt/entity.py`; gelesen in der lokalen HA 2024.12.5
  und am 2026-10-03 auf `home-assistant/core` `dev` bestätigt, dort zuletzt am 2026-06-22 nur kosmetisch
  geändert). **Fällt die Station aus, bleibt der letzte Zahlenwert als
  „verfügbar“ stehen**; erst ein HA-Neustart macht die Entitäten `unavailable`. Das einzige Zeichen ist das
  alternde `last_reported`. Gemessen am 2026-10-03: `last_reported` aller acht Entitäten 12 s alt, auch bei
  Luftfeuchte und Tagesregen, deren Wert seit 3,5 h gleich war.
- Folge eines Ausfalls heute: Nächtliche Rechnung (Stundenform) und Live-Estimate, das auf Prod echte Läufe
  bemisst, rechnen mit dem eingefrorenen Wert. Nachts eingefroren (99 % Feuchte, 10 °C) wird kaum ET
  gebucht, mittags eingefroren dauerhaft zu viel. Kein Hinweis.

## Anforderungen

- **R1 Erkennung je Gerät.** Ein Sensorfeld lebt, solange irgendeine Entität seines HA-Geräts innerhalb der
  Grenze gemeldet hat. Ohne Gerät zählt die eigene Entität. Steht die eigene Entität auf
  `unavailable`/`unknown`, gilt das Feld als stumm. `input_number` wird nie als ausgefallen gewertet.
- **R2 Grenze fest 3 h.** Schweigen bis 3 h wird überbrückt wie heute.
- **R3 Ausfälle werden mitgeschrieben** (Beginn = letztes Lebenszeichen, Ende = erste neue Meldung) und
  wirken rückwirkend auf jedes Fenster, das sie berühren, auch wenn das Gerät längst wieder meldet.
- **R4 Was nicht gemessen ist, wird nicht gebucht.** Von Beginn + 3 h bis zum Ende zählen die Werte des
  Feldes nicht. **Regenzähler (Aggregat `delta`) sind ausgenommen:** Ihr Stand nach der Rückkehr ist eine
  Messung, nur spät übertragen.
- **R5 Melden:** Reparaturhinweis je Sensorgruppe, Bus-Event bei Beginn und Ende, ein Satz in der
  Berechnungs-Erklärung, Log.
- **R6 Nur Sensorfelder.** Felder aus einem Wetterdienst und statische Werte bleiben unverändert.
- **R7 Erst der Vorschlag an JustChr,** dann der Bau.

## Entscheidungen (User, 2026-10-03)

| # | Frage | Entscheidung | Verworfen, weil |
|---|---|---|---|
| 1 | Was passiert bei einem Ausfall? | Nach der Grenze verwerfen, nichts buchen; die Bewässerung pausiert, bis der Sensor wieder liefert | Weiterrechnen: Menge ist Zufall des Ausfallzeitpunkts. Ersatzwert aus den letzten Tagen bzw. Wetterdienst-Rückfall: eigene Features; der Rückfall kehrt JustChrs Entscheidung aus `JustChr#149` um |
| 2 | Woran erkennen? | Je Gerät. User: an einer lebenden Station ändert sich immer etwas, außer der Regenrate | Je Entität: Fehlalarm bei Integrationen, die nur bei Wertänderung schreiben. Zeilenalter: braucht feldweise Grenzen und sieht eingefrorene Poll-Werte nicht |
| 3 | Laufende oder auch beendete Ausfälle? | Mitschreiben, rückwirkend | Nur laufende: ließe den häufigsten Fall (Ausfall endet vor der nächsten Rechnung) ungelöst |
| 4 | Grenze | Fest 3 h | 1 h: knapp für langsame Integrationen und Nebelnächte. 6 h: zu lange eingefrorene Werte. Einstellbar: Umfang ohne Anlass |
| 5 | Melden | Reparaturhinweis + Bus-Event | Nur Hinweis: kein Push möglich. Neuer Binärsensor: neue Entität, nachrüstbar. Die Problem-Sensoren passen nicht: ein Platz je Zone, ein guter Lauf löscht ihn (`irrigation.py:589-630`) |
| 6 | Welche Quellen? | Nur Sensorfelder | Dienst-Felder brauchen eine eigene Regel (Abfragetakt bis „täglich“, Mischgruppen) → eigenes Issue |
| 7 | Weg zu JustChr | Vorschlag zuerst, Plan in der Wartezeit | Erst bauen: Risiko eines dauerhaften Fork-Deltas bei abweichender Produktentscheidung |
| — | Feinheit des Schnitts | Design 1 (je Rolle) und Design 2 (je Feld) zur Wahl für JustChr, unsere Präferenz Design 2 | User: „Warum soll man lebende Entitäten verwerfen, nur weil eine vom selben Gerät tot ist.“ |

## Das Design

### Erkennung

- Neues Modul (Arbeitsname `sensor_liveness.py`). Eine Prüfung alle 5 min (`async_track_time_interval`,
  beim Entladen abgemeldet), die erste 10 min nach `EVENT_HOMEASSISTANT_STARTED`, damit Integrationen ihre
  Entitäten erst anlegen können.
- Je Sensorgruppe, je Feld mit `source: sensor` und gesetzter Entität:
  - **Gerät** über die Entity-Registry. Lebenszeichen = jüngstes `last_reported` über alle Entitäten dieses
    Geräts, deren Zustand nicht `unavailable`/`unknown` ist; Batterie- oder Signal-Entitäten zählen mit.
  - **Ohne Gerät:** das eigene `last_reported`.
  - **Eigene Entität `unavailable`/`unknown` oder fehlend:** stumm, egal was das Gerät tut. Lebenszeichen ist
    das letzte vorher gesehene.
  - **Domäne `input_number`:** nie ausgefallen (von Hand gesetzter Wert, kein Lebenszeichen zu erwarten).
- Das Lebenszeichen je Entität wird bei jeder Prüfung mitgespeichert. Hat eine Entität seit dem HA-Start noch
  nicht gemeldet, gilt das gespeicherte. So beginnt ein Ausfall, der über einen Neustart reicht, vor dem
  Neustart. HAs eigene Ausfallzeit ist dagegen kein Sensorausfall: Meldet das Gerät innerhalb der Karenz nach
  dem Start, entsteht kein Eintrag.
- **Uhr:** Alle Stempel im Rahmen des Puffers, also HAs Uhr, naiv (`local_naive_now`; die UTC-Zeiten der
  Zustände werden umgerechnet). Damit erbt die Liste die bekannte Einschränkung des Puffers zur
  Rückstell-Stunde, mehr nicht.
- Verbleibendes Fehlalarm-Risiko: ein Template-Sensor ohne Gerät mit konstantem Wert. Der Hinweistext nennt
  dafür die Quelle „statisch“.

### Ausfall-Liste

- Zwei neue Felder an `MappingEntry`, gespeichert wie `radiation_calibration` (`store.py:372`): begrenzt, in
  der normalen Speicherung, **ohne Store-Versionssprung**. Ältere Versionen lesen beim Laden nur die
  Schlüssel, die sie kennen; ein Rollback bleibt gutmütig.
  - `sensor_outages`: Einträge `{entity_id, device_id oder null, fields, start, end oder null}`.
  - `sensor_last_seen`: `{entity_id: Stempel}`.
- **Öffnen:** Lebenszeichen älter als 3 h, kein offener Eintrag für die Entität.
- **Schließen:** Lebenszeichen nach `start`. `end` = erste neue Meldung, auf die Prüfperiode genau
  (frühestes `last_changed` einer Geräte-Entität nach `start`, sonst das neue Lebenszeichen).
- **Kürzen:** Einträge, deren `end` älter als 7 Tage ist (`BUFFER_RETENTION`), fallen weg.
- **Leeren:** Ein Quellwechsel eines Feldes leert dessen Einträge, wie heute Puffer und `last_entry`
  (`__init__.py:1783-1790`); „Wetterdaten zurücksetzen“ (`calculation.py:329-386`) leert die Liste der Gruppe.
- **Schutz:** Beide Schlüssel kommen auf die Streichliste der server-berechneten Felder
  (`websockets.py:242-267`, wie `data_last_entry`), damit Speichern im Panel sie nicht überschreibt.
- Die Diagnose zeigt beide Felder über `async_get_mappings` ohne Zusatzarbeit.

### Schneiden: gemeinsame Regeln

- Gesperrte Zeit eines Eintrags: von `start` + 3 h bis `end`, bei offenem Eintrag bis jetzt. Die ersten 3 h
  werden mit dem letzten Wert überbrückt.
- Gesperrte Zeit eines Feldes: die Vereinigung über seine Einträge.
- **Regenzähler** (Precipitation mit Aggregat `delta`) werden nie gesperrt. Regenraten (`riemannsum`/`sum`)
  und alle Pegelwerte werden gesperrt. Current Precipitation wird gesperrt wie jeder Pegelwert, liest aber
  keine Rechnung.

### Design 1: Löcher je Rolle (Alternative)

- Zwei Lückenlisten je Sensorgruppe: das **ET-Loch** (Vereinigung der Sperren aller Einträge mit einem
  ET-Eingang: Temperatur, Taupunkt, Feuchte, Druck, Wind, Sonne, ET) und das **Regen-Loch** (Sperren der
  Einträge mit einer Regenrate).
- Im ET-Loch wird keine ET gebucht (Tagesform: Anteil des Fensters ohne Loch; Stundenform: Stunden im Loch
  entfallen), im Regen-Loch kein Regen. Die Module brauchen keine Pflichtfeld-Logik; weniger Code.
- **Unterschied zu Design 2:** Fällt nur ein Teil der ET-Eingänge aus (ein separater Sensor oder eine
  einzelne `unavailable`-Entität an einem lebenden Gerät), setzt Design 1 die ET für die Lücke ganz aus;
  Design 2 rechnet mit den lebenden Feldern weiter, wo das Modul es kann (in der Tagesform z. B. mit
  geschätzter Sonne). Für eine Gruppe aus einem Gerät, wie auf HA-Prod, sind beide gleich.

### Design 2: Masken je Feld (bevorzugt)

- `aggregate_window`, `_effective_series`, `build_hourly_rows`, `build_substeps` und die Einstiege des
  Live-Estimate erhalten die gesperrte Zeit je Feld.
- **Aggregation**, jedes Feld nur in seiner gültigen Zeit:
  - Ein Wert wird bis zur nächsten Messung gehalten, aber nie in eine Sperre hinein.
  - Zeilen innerhalb einer Sperre fallen weg (das trifft eingefrorene, frisch gestempelte Poll-Werte).
  - Mittel (zeitgewichtet wie einfach), Tmin/Tmax, Einzelwert-Zweig (`weather_aggregate.py:523`) und
    `last_entry`-Auffüllung (`:371-396`, `:936`) gelten nur für die gültige Zeit.
  - Hat ein Feld im Fenster keine gültige Zeit, fehlt es.
  - Das Ergebnis meldet je Feld seine gesperrten Abschnitte im Fenster.
- **Buchen entscheidet das Modul anhand seiner Pflichtfelder:**
  - **PyETO, Tagesform:** ET wird nur für den Anteil des Fensters gebucht, in dem *alle* Pflichtfelder
    zugleich gültig sind (Taupunkt, Temperatur, Wind, Druck; Schnittmenge der gültigen Zeiten, nicht das
    Minimum der Einzelanteile). Fehlt nur die Sonne, schätzt PyETO sie wie heute
    (`calcmodules/pyeto/__init__.py:324-364`).
  - **PyETO, Stundenform** (HA-Prod): Eine Stunde zählt mit dem Anteil, in dem Temperatur, Feuchte, Wind und
    Sonne zugleich gültig sind. Fehlt nur der Druck, wird er wie heute aus der Höhe abgeleitet. Die gehaltene
    Klarheitsquote der Sonne (`weather_aggregate.py:757`) überbrückt keine Sperre, weil sie vom toten Sensor
    stammt.
  - **Passthrough:** der gültige Anteil des ET-Feldes.
  - **Regenrate:** integriert nur über die gültige Zeit; in der Sperre wird kein Regen gebucht.
- **Weitere Leser:**
  - **Live-Estimate** schneidet gleich, bei offenem Eintrag bis jetzt. `_latest_temperature`
    (`live_estimate.py:880`) nimmt `last_entry` nicht als aktuell, solange die Temperatur gesperrt ist.
  - `_record_window_radiation` (`calculation.py:685`) und `_record_window_amplitude` (`calculation.py:635`)
    zeichnen kein Fenster auf, in dem Sonne bzw. Temperatur gesperrt war, damit kein Teiltag als ganzer Tag
    in die 7-Tage-Reihen geht.
  - **Nachgespielte Bilanz** (`build_substeps`): In gesperrten Stunden wird nach Zeit statt nach Sonne
    verteilt (vorhandener Rückfall ohne Sonne).

### Melden

- **Reparaturhinweis** `weather_sensor_stale_<mapping_id>`, einer je Sensorgruppe; Warnstufe, ohne
  Reparatur-Dialog (also mit `description`, `repairs.py:50-52`).
  - Erscheint, sobald der erste Eintrag der Gruppe öffnet; wird aktualisiert, wenn sich die Menge der
    stummen Entitäten ändert; verschwindet, wenn kein Eintrag mehr offen ist.
  - Beim HA-Start aus der gespeicherten Liste wiederhergestellt; er übersteht einen Neustart. Neu ist, dass
    die Integration einen Reparaturhinweis zur Laufzeit führt; heute entstehen sie nur beim Setup
    (`__init__.py:327`).
  - Platzhalter: Gruppe, stumme Entitäten mit ihren Feldern, Beginn.
  - Textentwurf (EN): Titel „A weather sensor of {group} has stopped reporting“. Inhalt sinngemäß:
    „Irrigation Plus has not heard from {entities} since {since}. After three hours of silence its readings
    are no longer used and nothing is booked for that time, so zones depending on it water less or not at
    all until it reports again. Check the device and its integration. If the value is meant to be fixed, use
    the "static" source instead. This notice clears itself when the sensor reports again.“
- **Bus-Event `irrigation_plus_weather_stale`** bei Beginn und Ende jedes Eintrags. Inhalt: `mapping_id`,
  `mapping` (Name), `entity_id`, `device_id` (oder null), `fields`, `since`, `until` (null beim Beginn),
  `stale` (true/false). Derselbe Automations-Haken wie das vorhandene `irrigation_plus_zone_problem`.
- **Satz in der Berechnungs-Erklärung** der Zone, je Sperre, die das Fenster berührt; neuer Schlüssel
  `module.calculation.explanation.sensor-outage`, etwa: „Sensordaten für {fields} fehlten von {start} bis
  {end} (Gerät stumm); für diese Zeit wurde nichts gebucht.“
- **Log:** WARNING beim Öffnen, INFO beim Schließen.
- **Übersetzungen** in allen 8 Sprachen: Hinweis in `translations/*.json` (Block `issues`), Erklärungssatz in
  `frontend/localize/languages/*.json`. `test_i18n_completeness` prüft beides. **`en.json` ist fest ins
  Bundle importiert** (`frontend/localize/localize.ts:1`) → dist neu bauen.

### Dokumentation

- `docs/configuration-sensor-groups.md`: neuer Abschnitt „Wenn ein Sensor schweigt“ (Regel, 3 h,
  Regenzähler-Ausnahme, `input_number`, Template-Hinweis, was in der Pause passiert).
- `docs/usage-events.md`: das neue Event mit Beispiel-Automation (Push aufs Handy).
- Docstring von `_prune_mapping_buffer` (`calculation.py:432-446`) berichtigt: Die Grenzzeile je Feld
  überlebt die Frist absichtlich als Delta-Basis; gegen veraltete Werte wirkt die Ausfall-Liste.

### Betroffene Stellen (Überblick für den Plan)

| Datei | Änderung |
|---|---|
| neu: `sensor_liveness.py` | Prüfung, Liste, Hinweis, Event |
| `__init__.py` | Timer an- und abmelden; Liste beim Quellwechsel leeren |
| `store.py` | zwei Felder an `MappingEntry`, Laden und Speichern |
| `websockets.py` | Streichliste der server-berechneten Felder |
| `calculation.py` | Sperren an die Aggregation, Buchungsanteil, Erklärungssatz, Aufzeichnungen überspringen, Reset leert die Liste, Docstring |
| `weather_aggregate.py` | Sperren in `aggregate_window`, `_effective_series`, `build_hourly_rows`, `build_substeps` |
| `calcmodules/pyeto/__init__.py` | nur Design 2: Buchungsanteil aus den Pflichtfeldern |
| `live_estimate.py` | Sperren, Temperatur-Anker |
| `repairs.py` | Hinweis zur Laufzeit |
| `const.py` | Konstanten (3 h, 5 min, 10 min, Event-Name, Schlüssel) |
| `translations/*.json` (8) | Hinweis |
| `frontend/localize/languages/*.json` (8) | Erklärungssatz; dist neu bauen |
| `docs/configuration-sensor-groups.md`, `docs/usage-events.md` | siehe *Dokumentation* |

## Schwester-Pfade geprüft

- **Poll-Schreiber mit eingefrorenem Zahlenwert:** abgedeckt; seine Zeilen liegen in der Sperre und fallen weg.
- **`last_entry` auch bei abgeschaltetem `continuousupdates`** gelesen (`calculation.py:415`): abgedeckt, weil
  die Auffüllung nur in gültiger Zeit gilt.
- **Stundenzeilen aus `last_entry`** (`weather_aggregate.py:936`), **Temperatur-Anker**
  (`live_estimate.py:880`), **Kalibrier- und Amplituden-Aufzeichnung:** abgedeckt (siehe Design 2).
- **`_effective_series`** stempelt ebenfalls um (`weather_aggregate.py:714`): bekommt dieselben Sperren.
- **Zeilen-Obergrenze im Ereignis-Pfad** (`continuous_update.py:558-589`): unberührt; sie behält nur die
  älteste Zeile und ändert an Sperren nichts.
- **Ereignis-Pfad und Start-Saat ignorieren `unavailable`/`unknown`** (`continuous_update.py:264`, `:359`):
  unverändert; ein solcher Zustand wird jetzt zusätzlich als Ausfall erkannt.
- **Nur-Stempel-Zeilen** einer ganz unlesbaren Gruppe zählen weiter als Datenpunkt (Faktensammlung G.6):
  bemerkt, nicht Teil dieser Arbeit.

## Ausdrücklich nicht in dieser Arbeit

- Felder aus einem Wetterdienst (eigenes Issue, Text vorher zur Freigabe).
- Eine einstellbare Grenze.
- Eine Zustands-Entität „Wetterdaten veraltet“.
- Ersatzwerte oder ein Rückfall auf den Wetterdienst während eines Ausfalls.
- HAs eigene Ausfallzeit.
- Ein toter Untersensor an einem lebenden Gerät, der seinen Zahlenwert behält (blinder Fleck aus Frage 2;
  wird er `unavailable`, ist er erfasst).
- Integrationen, die die letzte Beobachtung eines Cloud-Dienstes weiterreichen und dabei denselben Wert
  weiter melden, obwohl die Station schweigt (zweiter blinder Fleck; bräuchte die Beobachtungszeit des
  Dienstes, die jede Integration anders oder gar nicht liefert).

## Tests

Jeweils RED vor GREEN.

- **Erkennung:** Geräte-Maximum; eigene Entität `unavailable`; Entität ohne Gerät; `input_number`;
  Start-Karenz; Lebenszeichen über einen Neustart; Stempel im Rahmen des Puffers.
- **Liste:** Öffnen nach 3 h, nicht vorher; Schließen bei der ersten Meldung mit richtigem Ende;
  7-Tage-Kürzung; Leeren bei Quellwechsel und Reset; Speichern im Panel lässt die Liste stehen;
  Store-Rundlauf (beide Felder überleben Speichern und Laden, ein Store ohne sie lädt).
- **Sperren in der Aggregation:** zeitgewichtet; einfaches Mittel; Einzelwert; Tmin/Tmax; `last_entry`;
  Regenzähler ausgenommen; eingefrorene Poll-Zeilen fallen weg; Feld ohne gültige Zeit fehlt.
- **Buchen:** Schnittmenge der Pflichtfelder in der Tagesform; Sonnenschätzung; Stundenanteil;
  Klarheitsquote ohne Brücke; Passthrough; Regenrate.
- **Weitere Leser:** Live-Estimate samt Temperatur-Anker; keine Kalibrier- oder Amplituden-Aufzeichnung über
  eine Sperre.
- **Melden:** Lebenszyklus des Hinweises samt Neustart; Event-Inhalt bei Beginn und Ende; Erklärungssatz;
  i18n-Vollständigkeit.
- Mutationen auf die tragenden Wächter (Regenzähler-Ausnahme, 3-h-Brücke, Geräte-Maximum, eigene
  `unavailable`-Entität, `input_number`, Start-Karenz, Schnittmenge, Stundenanteil, Klarheitsquote,
  Aufzeichnungs-Sperre); volle Suite mit Namensvergleich gegen die Baseline.

## Ende-zu-Ende-Kriterium

**HA-Test**, eine Sensorgruppe aus Entitäten eines Geräts, das wir steuern (etwa ein MQTT-Gerät mit
minütlichem Senden, falls auf HA-Test ein Broker läuft, sonst Template-Helfer mit Gerät; das Mittel klärt der
Plan):

1. Das Gerät meldet 3,5 h lang **unveränderte** Werte → es entsteht kein Ausfall. Für beide Schreibweisen:
   ein Gerät, das bei jedem Update schreibt (`last_reported` rückt vor), und eines, das nur bei Änderung
   schreibt und dessen Felder bis auf eines ruhig bleiben.
2. Dann 3,5 h Stille → der Hinweis erscheint rund 3 h nach der letzten Meldung, das Event kommt an, und eine
   Berechnung nennt die Sperre in ihrer Erklärung und bucht ET nur für den gültigen Teil.
3. Das Gerät meldet wieder → der Hinweis verschwindet, das Erholungs-Event kommt an, und der Eintrag schließt
   mit dem richtigen Ende.
4. Ein HA-Neustart mitten im Ausfall lässt Beginn und Hinweis unverändert.

**HA-Prod**, passiv nach dem Update: In den ersten Tagen entsteht kein Fehlalarm, auch nicht in
Nebelnächten mit 99 % Feuchte.

## Lieferung

1. **Issue an JustChr** (englisch; Text vorher zur Freigabe; keine Verweise auf unsere Issues): Befund mit
   Datei:Zeile auf seinem aktuellen `master`, Folgen, Vorschlag, Design 1 und Design 2 in dieser Reihenfolge
   mit Design 2 als unserer Präferenz, Abgrenzung, Testplan. Ausdrücklich gefragt: die Pause-Regel, die Design-Wahl, der neue Hinweis
   samt Event. Danach P2: `upstream:gemeldet` auf Eifel-Joe#8, Kommentar mit Link, #42 nachziehen.
2. **Plan:** der gemeinsame Teil (Erkennung, Liste, Melden, Doku, Docstring) in der Wartezeit, der
   Schnitt-Teil nach seiner Wahl.
3. **Bau** nach seiner Antwort: Branch von `upstream/master`, PR nur Fix und Test, dist neu wegen `en.json`;
   Rezept: Memory `hasi-pr-build-recipe`.
4. **production** bekommt den Fix nach dem Bau sofort (User-Regel), auch vor dem Merge.
5. **Eigenes Issue für die Dienst-Felder** (Text vorher zur Freigabe).
6. **P1:** Spec und Plan beim Abschluss nach `archive/design-history`.
