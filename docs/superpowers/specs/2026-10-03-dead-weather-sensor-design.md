# Ein stummer Wettersensor wird nicht endlos weiterverwendet

Design für `Eifel-Joe#8`. Basis: `upstream/master` = `e9c79ec4` (Beta v2026.10.03). Alle Zeilenangaben
beziehen sich auf diesen Commit und auf `custom_components/irrigation_plus/`, sofern nicht anders
angegeben. Faktensammlung: `D:\Entwicklung\HASI\issue8-work\context-2026-10-03.md`, im Archiv als
`docs/superpowers/probes/2026-10-03-dead-weather-sensor-survey.md` (Agent; die tragenden Aussagen am 2026-10-03
selbst nachgelesen, Zeilen per `grep -n` bestätigt). Vorschlag an JustChr: `JustChr#188`.

**Status: Revision 2 (2026-10-04), angepasst an JustChrs Antwort.** Revision 1 (2026-10-03, Vorschlag mit
Design 1 und 2 zur Wahl) liegt unverändert in `archive/design-history` `1c197e36`. JustChr hat den Bau am
2026-10-03 um 19:13 UTC freigegeben (`JustChr#188`, Kommentar `5972596286`), mit Bedingungen (siehe *JustChrs
Antwort*). Mit dem User am 2026-10-04 entschieden: der Schnitt von PR 2 nur ohne Stundenrechnung, neue Gruppen
pausieren (Entscheidungen 8 und 9). **Revision 2 und der Plan für PR 1 vom User freigegeben am 2026-10-04**, Live-Test
mit Variante 1 (MQTT-YAML unter eigenem Topic-Präfix, siehe *Ende-zu-Ende-Kriterium*).

**Revision 3 (2026-10-04, nach dem Bau von PR 1).** Der Text beschreibt PR 1 jetzt so, wie er gebaut ist. Geändert
gegenüber Revision 2: drei User-Entscheidungen beim Bau (D1–D3, Tabelle *User, 2026-10-04, Bau*) und die Befunde der
Reviews (*Präzisierungen aus dem Bau*, 7–12); berührt sind R1, R3, *Erkennung*, *Ausfall-Liste*, das Event, die
Doku-Fassung und *Tests*. PR 2 und PR 3 sind unverändert. Revision 2 liegt unverändert in `archive/design-history`
`02d69eb0`; das Abweichungsprotokoll mit allen Belegen (`deviations.md`) im Archiv unter
`docs/superpowers/probes/2026-10-04-dead-weather-sensor-pr1/`.

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
   der Temperatur-Anker der Live-Schätzung (`live_estimate.py:880`).

Dazu im Poll-Betrieb: Ein toter Sensor, der seinen Zahlenwert behält, wird bei jedem Poll mit frischem
Stempel neu geschrieben (`build_sensor_values_for_mapping`, `__init__.py:1871`) und sieht lebendig aus.

Synthetisch nachgemessen (Agent, gegen `e9c79ec4`): Ein 30 Tage alter Temperaturwert übersteht das
Ausdünnen (160 → 2 Zeilen) und kommt als Temperatur = Tmax = Tmin zurück, zeitgewichtet wie ungewichtet.
JustChr hat den Kern am 2026-10-03 auf seinem `master` nachgeprüft (Grenzzeile ohne Altersprüfung, ungestempelte
`last_entry`-Auffüllung); Geräte-Lebendigkeit und das Neustempeln beim Poll hat er ausdrücklich noch nicht geprüft.

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
- Folge eines Ausfalls heute: Nächtliche Rechnung (Stundenform) und Live-Schätzung, die auf Prod echte Läufe
  bemisst, rechnen mit dem eingefrorenen Wert. Nachts eingefroren (99 % Feuchte, 10 °C) wird kaum ET
  gebucht, mittags eingefroren dauerhaft zu viel. Kein Hinweis.
- HA-Prod rechnet in der **Stundenform**: Den Hinweis bekommt es mit PR 1, den Schnitt erst mit PR 3
  (Entscheidung 8). Die Gruppe „Greimerath“ ist Bestand und steht nach PR 2 auf „letzten Wert behalten“; wer dort
  pausieren will, stellt es um.

## JustChrs Antwort (`JustChr#188`, 2026-10-03 19:13 UTC)

Bau freigegeben („Go ahead and build it when you're ready.“), mit diesen Bedingungen, sinngemäß:

1. **Einstellung je Sensorgruppe** „bei stummem Sensor: pausieren / letzten Wert behalten“. Bestehende Gruppen
   stehen auf *letzten Wert behalten und melden*, damit sie byte-identisch bleiben; für neue Gruppen darf
   *pausieren* der Standard sein. Erkennung, Ausfall-Liste und Hinweis dürfen zuerst kommen; die Schnitt-Regel
   folgt nach einem Feldtest („once it has been field-tested“; wir lesen: Feldtest von PR 1, R9).
2. **Design 2**, weil Design 1 die ET der ganzen Gruppe aussetzt, wenn ein Eingang stirbt; als größere Änderung
   aufgeteilt in **drei PRs**: (1) Erkennung, Ausfall-Liste, Reparaturhinweis und Event **ohne
   Verhaltensänderung**; (2) der Schnitt im Tagespfad; (3) Stundenpfad und Live-Schätzung.
3. **Reparaturhinweis und Event** passen ihm. Tests verlangt: der Hinweis verschwindet bei Erholung, übersteht
   einen Neustart mitten im Ausfall und fällt weg, wenn die Gruppe gelöscht wird.
4. **Fest 3 h** ist für eine erste Fassung in Ordnung; eine Cloud-Integration mit 6-h-Abfrage löst aber
   Fehlalarm aus, und das soll in der Doku stehen. Die Liste „nicht Teil davon“ hält er für vernünftig.

## Anforderungen

- **R1 Erkennung je Gerät.** Ein Sensorfeld lebt, solange irgendein Sensor seines HA-Geräts innerhalb der
  Grenze gemeldet hat; es zählen nur `sensor`/`binary_sensor` der Integration, der das Gerät gehört, oder der
  Integration der gemappten Entität (D1). Ohne Gerät zählt die eigene Entität. Steht die eigene Entität auf
  `unavailable`/`unknown`, gilt das Feld als stumm. `input_number` wird nie als ausgefallen gewertet.
- **R2 Grenze fest 3 h.** Schweigen bis 3 h wird überbrückt wie heute.
- **R3 Ausfälle werden mitgeschrieben** (Beginn = letztes Lebenszeichen, Ende = Rückkehr des Feldes, D3) und
  wirken rückwirkend auf jedes Fenster, das sie berühren, auch wenn das Gerät längst wieder meldet.
- **R4 Einstellung je Sensorgruppe:** *pausieren* oder *letzten Wert behalten*. Bestehende Gruppen: behalten,
  Rechnung und Erklärung byte-identisch. Neue Gruppen: pausieren.
- **R5 Pausieren heißt: Was nicht gemessen ist, wird nicht gebucht.** Von Beginn + 3 h bis zum Ende zählen die
  Werte des Feldes nicht. **Regenzähler (Aggregat `delta`) sind ausgenommen:** Ihr Stand nach der Rückkehr ist
  eine Messung, nur spät übertragen.
- **R6 Melden, für jede Einstellung:** Reparaturhinweis je Sensorgruppe, Bus-Event bei Beginn und Ende, Log;
  bei pausierenden Gruppen zusätzlich ein Satz in der Berechnungs-Erklärung.
- **R7 Nur Sensorfelder.** Felder aus einem Wetterdienst und statische Werte bleiben unverändert.
- **R8 Drei PRs, jeder für sich prüfbar.** PR 1 ändert keine Rechnung; PR 2 schneidet nur, wo die
  Stundenrechnung aus ist; PR 3 schneidet im Stundenpfad und in der Live-Schätzung.
- **R9 Der Schnitt kommt erst nach dem Feldtest** von PR 1 (JustChrs Bedingung).

## Entscheidungen

**User, 2026-10-03** (Vorschlag, Revision 1):

| # | Frage | Entscheidung | Verworfen, weil |
|---|---|---|---|
| 1 | Was passiert bei einem Ausfall? | Nach der Grenze verwerfen, nichts buchen; die Bewässerung pausiert, bis der Sensor wieder liefert. **Seit JustChrs Antwort:** das Verhalten der Einstellung *pausieren*, Standard für neue Gruppen (Entscheidung 9) | Weiterrechnen: Menge ist Zufall des Ausfallzeitpunkts. Ersatzwert aus den letzten Tagen bzw. Wetterdienst-Rückfall: eigene Features; der Rückfall kehrt JustChrs Entscheidung aus `JustChr#149` um |
| 2 | Woran erkennen? | Je Gerät. User: an einer lebenden Station ändert sich immer etwas, außer der Regenrate | Je Entität: Fehlalarm bei Integrationen, die nur bei Wertänderung schreiben. Zeilenalter: braucht feldweise Grenzen und sieht eingefrorene Poll-Werte nicht |
| 3 | Laufende oder auch beendete Ausfälle? | Mitschreiben, rückwirkend | Nur laufende: ließe den häufigsten Fall (Ausfall endet vor der nächsten Rechnung) ungelöst |
| 4 | Grenze | Fest 3 h | 1 h: knapp für langsame Integrationen und Nebelnächte. 6 h: zu lange eingefrorene Werte. Einstellbar: Umfang ohne Anlass |
| 5 | Melden | Reparaturhinweis + Bus-Event | Nur Hinweis: kein Push möglich. Neuer Binärsensor: neue Entität, nachrüstbar. Die Problem-Sensoren passen nicht: ein Platz je Zone, ein guter Lauf löscht ihn (`irrigation.py:589-630`) |
| 6 | Welche Quellen? | Nur Sensorfelder | Dienst-Felder brauchen eine eigene Regel (Abfragetakt bis „täglich“, Mischgruppen) → `Eifel-Joe#74` |
| 7 | Weg zu JustChr | Vorschlag zuerst, Plan in der Wartezeit | Erst bauen: Risiko eines dauerhaften Fork-Deltas bei abweichender Produktentscheidung |

**JustChr, 2026-10-03** (Antwort auf `JustChr#188`):

| # | Frage | Entscheidung | Verworfen, weil |
|---|---|---|---|
| J1 | Verhalten bei Ausfall | Einstellung je Gruppe; Bestand *behalten + melden* (byte-identisch), neu darf *pausieren* | Verhalten für alle ändern: bestehende Installationen änderten sich still |
| J2 | Feinheit des Schnitts | Design 2 (Masken je Feld) | Design 1 (Löcher je Rolle): setzt die ET der ganzen Gruppe aus, wenn ein Eingang stirbt |
| J3 | Lieferung | Drei PRs: Erkennung ohne Verhaltensänderung → Tagespfad → Stundenpfad + Live-Schätzung; Schnitt erst nach Feldtest | Ein PR: zu groß für ein Review |
| J4 | Tests | Hinweis: verschwindet bei Erholung, übersteht Neustart mitten im Ausfall, fällt beim Löschen der Gruppe weg | — |
| J5 | Grenze | Fest 3 h für die erste Fassung; die Doku nennt den Fehlalarm einer 6-h-Cloud-Abfrage | — |

**User, 2026-10-04** (Revision 2):

| # | Frage | Entscheidung | Verworfen, weil |
|---|---|---|---|
| 8 | Wo schneidet PR 2? | Nur wo die Stundenrechnung aus ist: Die Masken sind ein Parameter, und in PR 2 übergibt ihn nur der Commit bei ausgeschalteter Stundenrechnung. Stundenbetrieb bleibt bis PR 3 wie heute | Aggregat für jede Installation: Mischzustand im Stundenbetrieb. Das Aggregat liefert dort den Niederschlag, die nachgespielte Bilanz gleicht sich damit ab (`calculation.py:999-1008`); geschnittene Regenrate gegen ungeschnittene Stundenzeilen → Abgleich scheitert, still Einmal-Buchung |
| 9 | Standard neuer Gruppen | *Pausieren*; Bestand *behalten*. Ausweg im Hinweistext pausierender Gruppen und in der Doku: aktualisiert die Integration nur alle paar Stunden, auf *behalten* stellen | Alle behalten: das Verhalten aus Entscheidung 1 bekäme kaum jemand. Bekannter Preis: Eine Integration mit 6-h-Takt verliert bei *pausieren* in jedem Zyklus die halbe Zeit, bis der Nutzer umstellt |

**User, 2026-10-04, Bau** (Revision 3; gefragt nach den Reviews von Plan-Task 8 und 9 und vor der Umbenennung):

| # | Frage | Entscheidung | Verworfen, weil |
|---|---|---|---|
| D1 | Wer bürgt für ein Feld? | Sensoren desselben Geräts, nur `sensor`/`binary_sensor`, nur aus der Integration, der das Gerät gehört, oder aus der Integration der gemappten Entität | Alle Entitäten des Geräts (Revision 2): HA hängt Helfer wie `utility_meter` ans Gerät ihrer Quelle, und die schreiben im eigenen Takt (Tageszähler-Reset um Mitternacht → jede Nacht eine Fehl-Entwarnung); `update`-Entitäten laufen im eigenen Takt (ESPHome alle 5 min → eine Deep-Sleep-Station würde nie erkannt) |
| D2 | Name der Ausfall-Liste im Code | „outage record“, JustChrs eigenes Wort aus `JustChr#188` | „ledger“: so heißt in der Integration schon die Wasserbilanz einer Zone |
| D3 | Wann endet ein Ausfall? | Zuerst die eigene Rückkehr des Feldes, also die erste Änderung seiner Entität nach dem Beginn; nur ein Feld ohne eigene Änderung (Regenmesser bei 0) nimmt die früheste Änderung eines bürgenden Sensors | Früheste Änderung irgendeiner Geräte-Entität (Revision 2): Ist nur die eigene Entität ausgefallen, zieht eine Batterie-Änderung während des Ausfalls das Ende nach vorn, in der Probe sogar vor das Start-Event |

## Das Design

### Erkennung (PR 1)

- Neues Modul `sensor_liveness.py`. Eine Prüfung alle 5 min (`async_track_time_interval`, beim Entladen
  abgemeldet), die erste 10 min nach dem Setup, damit Integrationen ihre Entitäten erst anlegen können.
- Je Sensorgruppe, je Feld mit `source: sensor` und gesetzter Entität:
  - **Gerät** über die Entity-Registry. Lebenszeichen = jüngstes `last_reported` über die eigene Entität und die
    bürgenden Sensoren dieses Geräts, deren Zustand nicht `unavailable`/`unknown` ist. Bürgen dürfen nur
    `sensor`/`binary_sensor` aus der Integration, der das Gerät gehört (`config_entry_id` in neuerem HA,
    `primary_config_entry` davor), oder aus der Integration der gemappten Entität, die dort zählt, wo ein Gerät
    geteilt ist und eine andere Integration es besitzt (D1). Ein Helfer am Gerät (`utility_meter`, `integration`,
    Template mit gewähltem Gerät) bürgt nicht für die Station; ein gemappter Helfer wird dagegen von der Station
    gedeckt, weil ihr das Gerät gehört.
  - **Ohne Gerät:** das eigene `last_reported`.
  - **Eigene Entität `unavailable`/`unknown` oder fehlend:** stumm, egal was das Gerät tut. Lebenszeichen ist
    das letzte vorher gesehene.
  - **Domäne `input_number`:** nie ausgefallen (von Hand gesetzter Wert, kein Lebenszeichen zu erwarten).
- Das Lebenszeichen je Entität wird bei jeder Prüfung mitgespeichert. Hat eine Entität seit dem HA-Start noch
  nicht gemeldet, gilt das gespeicherte. So beginnt ein Ausfall, der über einen Neustart reicht, vor dem
  Neustart. HAs eigene Ausfallzeit ist dagegen kein Sensorausfall: Meldet das Gerät innerhalb der Karenz nach
  dem Start, entsteht kein Eintrag. Ein sauberes Herunterfahren schreibt geänderte Lebenszeichen mit
  (Präzisierung 7). Die Prüfung plant nur dann ein Speichern, wenn sich die Ausfall-Liste ändert (ein Ausfall
  beginnt, endet oder fällt nach 7 Tagen weg); die Lebenszeichen allein lösen keins aus.
- **Uhr:** Alle Stempel im Rahmen des Puffers, also HAs Uhr, naiv (`local_naive_now`; die UTC-Zeiten der
  Zustände werden umgerechnet). Damit erbt die Liste die Grenzen des naiven Rahmens bei der Zeitumstellung: In
  der Vorstell-Nacht öffnet ein Ausfall eine Stunde zu früh, in der Rückstell-Nacht eine Stunde zu spät, und
  Stempel der doppelten Stunde sind mehrdeutig. Nach außen (Event) gehen die Stempel mit HAs UTC-Offset
  (`dt_util.as_local`).
- Verbleibendes Fehlalarm-Risiko: ein Sensor ohne Gerät, der nur bei einer Wertänderung schreibt und dessen Wert
  3 h gleich bleibt (ein Template-Sensor, ein per YAML angelegter `utility_meter` auf einem Regenzähler an einem
  trockenen Tag; ein per UI angelegter hängt am Gerät seiner Quelle, wenn sie eins hat, und ist dann gedeckt; wer
  denselben Wert neu schreibt, rückt `last_reported` vor und wirkt nie stumm), und jede Integration, die seltener als
  alle 3 h aktualisiert (J5). Doku und Hinweistext nennen beides.

### Ausfall-Liste (PR 1)

- Zwei neue Felder an `MappingEntry`, gespeichert wie `radiation_calibration` (`store.py:372`): begrenzt, in
  der normalen Speicherung, **ohne Store-Versionssprung**. Ältere Versionen lesen beim Laden nur die
  Schlüssel, die sie kennen; ein Rollback bleibt gutmütig.
  - `sensor_outages`: Einträge `{entity_id, device_id oder null, fields, start, end oder null}`.
  - `sensor_last_seen`: `{entity_id: Stempel}`.
- **Öffnen:** Lebenszeichen älter als 3 h, kein offener Eintrag für die Entität.
- **Schließen:** Lebenszeichen nach `start`. `end` = Rückkehr des Feldes, auf die Prüfperiode genau (D3): das
  `last_changed` der eigenen Entität, wenn sie sich nach `start` geändert hat (eine Rückkehr aus `unavailable` ist
  eine Änderung); sonst, bei einem ruhigen Feld wie einem Regenmesser bei 0, das früheste `last_changed` eines
  bürgenden Sensors nach `start`; sonst das neue Lebenszeichen.
- **Nicht mehr gelesen:** Ein offener Eintrag einer Entität, die die Gruppe nicht mehr liest, endet bei der
  nächsten Prüfung mit `end` = jetzt (Präzisierung 6, *Selbstheilung*).
- **Kürzen:** Einträge, deren `end` älter als 7 Tage ist (`BUFFER_RETENTION`), fallen weg.
- **Leeren:** Ein Quellwechsel leert die Liste der ganzen Gruppe, wie heute Puffer und `last_entry`
  (`__init__.py:1768-1790`); ebenso „Wetterdaten zurücksetzen“ (`calculation.py:329-386`). Jeder offene Eintrag
  endet dabei mit seinem End-Event (Präzisierung 6). Die Lebenszeichen bleiben stehen (Präzisierung 8): Sie
  beschreiben das Gerät, nicht die Messwerte; ein weiter stummer Sensor, den die Gruppe noch liest, öffnet bei der
  nächsten Prüfung wieder, mit seinem echten Beginn. Wird eine Gruppe gelöscht, verschwindet ihr Hinweis.
- **Schutz:** Das Panel schickt beim Speichern nur `{id, name, mappings}`, und das Schema des Views lässt andere
  Schlüssel nicht zu; ein Test hält fest, dass Speichern die Liste stehen lässt (siehe *Präzisierungen*).
- Die Diagnose zeigt beide Felder über `async_get_mappings` ohne Zusatzarbeit.
- In PR 1 liest **keine Rechnung** die Liste. Sie ist Aufzeichnung und Grundlage des Hinweises; die Schnitte von
  PR 2 und PR 3 lesen sie später rückwirkend (R3).

### Einstellung je Sensorgruppe (PR 2)

- Neues Feld `MappingEntry.on_silent_sensor` mit den Werten `keep` und `pause`, **ohne Store-Versionssprung**:
  - Der Lade-Pfad (`store.py:1361`) setzt `keep`, wo der Schlüssel fehlt — **jede bestehende Gruppe** behält
    ihren letzten Wert.
  - Der Attribut-Standard ist `pause`. Damit pausieren die Gruppe der Erst-Einrichtung (`store.py:1539`) und jede
    über Panel oder Assistent angelegte Gruppe (`store.async_create_mapping`, `__init__.py:1820`).
  - Ob die Domain-Migration (`smart_irrigation` → `irrigation_plus`) Gruppen über den Lade-Pfad übernimmt und
    sie damit `keep` behalten, prüft der Plan von PR 2 per Test; übernommene Gruppen sind Bestand.
- Das View-Schema (`websockets.py:236-241`) nimmt den Schlüssel an; das Panel zeigt ihn als Auswahl in der Karte
  der Sensorgruppe und schickt ihn beim Speichern mit (heute `{id, name, mappings}`,
  `frontend/src/views/mappings/view-mappings.ts:379-380`). Beschriftungen in 8 Sprachen, dist neu bauen.
- **Wirkung:** Die Liste ist unabhängig von der Einstellung. Jeder Commit wendet die **aktuelle** Einstellung auf
  alle Ausfälle an, die sein Fenster berühren. Ein Wechsel auf *pausieren* gilt damit auch für schon
  aufgezeichnete Ausfälle im nächsten Fenster (R3); ein Wechsel auf *behalten* beendet das Schneiden. Ein
  Wechsel bei offenem Ausfall gleicht den Hinweistext sofort an.

### Schneiden: gemeinsame Regeln (PR 2 und PR 3, nur Gruppen auf *pausieren*)

- Gesperrte Zeit eines Eintrags: von `start` + 3 h bis `end`, bei offenem Eintrag bis jetzt. Die ersten 3 h
  werden mit dem letzten Wert überbrückt.
- Gesperrte Zeit eines Feldes: die Vereinigung über seine Einträge.
- **Regenzähler** (Precipitation mit Aggregat `delta`) werden nie gesperrt. Regenraten (`riemannsum`/`sum`)
  und alle Pegelwerte werden gesperrt. Current Precipitation wird gesperrt wie jeder Pegelwert, liest aber
  keine Rechnung.
- Gruppen auf *behalten* bekommen keine Masken: derselbe Code-Pfad wie heute, Ergebnis und Erklärung
  byte-identisch (R4).

### Schnitt im Tagespfad (PR 2)

- **Gate (Entscheidung 8):** Die gesperrte Zeit je Feld ist ein Parameter von `aggregate_window`. In PR 2 übergibt
  ihn nur der Commit (`_aggregate_for_zone`, `calculation.py:388-429`), und nur wenn die Gruppe pausiert **und**
  `hourly_calculation_enabled(store)` falsch ist. Live-Schätzung (`live_estimate.py:607`) und Stundenpfad
  übergeben nichts.
- **Aggregation**, jedes Feld nur in seiner gültigen Zeit:
  - Ein Wert wird bis zur nächsten Messung gehalten, aber nie in eine Sperre hinein.
  - Zeilen innerhalb einer Sperre fallen weg (das trifft eingefrorene, frisch gestempelte Poll-Werte).
  - Mittel (zeitgewichtet wie einfach), Tmin/Tmax, Einzelwert-Zweig (`weather_aggregate.py:523`) und
    `last_entry`-Auffüllung (`:371-396`) gelten nur für die gültige Zeit.
  - Hat ein Feld im Fenster keine gültige Zeit, fehlt es.
  - Das Ergebnis meldet je Feld seine gesperrten Abschnitte im Fenster.
- **Buchen entscheidet das Modul anhand seiner Pflichtfelder:**
  - **PyETO, Tagesform:** ET wird nur für den Anteil des Fensters gebucht, in dem *alle* Pflichtfelder
    zugleich gültig sind (Taupunkt, Temperatur, Wind, Druck; Schnittmenge der gültigen Zeiten, nicht das
    Minimum der Einzelanteile). Fehlt nur die Sonne, schätzt PyETO sie wie heute
    (`calcmodules/pyeto/__init__.py:324-364`).
  - **Passthrough:** der gültige Anteil des ET-Feldes.
  - **Regenrate:** integriert nur über die gültige Zeit; in der Sperre wird kein Regen gebucht.
- `_record_window_radiation` (`calculation.py:685`) und `_record_window_amplitude` (`calculation.py:635`)
  zeichnen kein Fenster auf, in dem Sonne bzw. Temperatur gesperrt war, damit kein Teiltag als ganzer Tag in die
  7-Tage-Reihen geht.
- **Satz in der Berechnungs-Erklärung** der Zone, je Sperre, die das Fenster berührt (siehe *Melden*).

### Schnitt im Stundenpfad und in der Live-Schätzung (PR 3)

- `build_hourly_rows`/`hourly_eto_priced`, `_effective_series` (`weather_aggregate.py:714`) und `build_substeps`
  erhalten die gesperrte Zeit je Feld; die Stundenzeilen aus `last_entry` (`:936`) gelten nur in gültiger Zeit.
- **PyETO, Stundenform** (HA-Prod): Eine Stunde zählt mit dem Anteil, in dem Temperatur, Feuchte, Wind und Sonne
  zugleich gültig sind. Fehlt nur der Druck, wird er wie heute aus der Höhe abgeleitet. Die gehaltene
  Klarheitsquote der Sonne (`weather_aggregate.py:757`) überbrückt keine Sperre, weil sie vom toten Sensor stammt.
- **Nachgespielte Bilanz** (`build_substeps`): In gesperrten Stunden wird nach Zeit statt nach Sonne verteilt
  (vorhandener Rückfall ohne Sonne). Weil Aggregat und Teilschritte dann dieselbe Sperre sehen, stimmt der Abgleich
  (`calculation.py:999-1008`) wieder.
- **Live-Schätzung** schneidet gleich, bei offenem Eintrag bis jetzt; ihr Aggregat-Aufruf (`live_estimate.py:607`)
  bekommt die Masken. `_latest_temperature` (`live_estimate.py:880`) nimmt `last_entry` nicht als aktuell,
  solange die Temperatur gesperrt ist.
- Das Gate aus PR 2 fällt weg: Pausierende Gruppen schneiden in jeder Rechenform.

### Zwischenstände, bewusst in Kauf genommen

- **Nach PR 1:** Jede Gruppe verhält sich wie *behalten + melden*; nichts wird geschnitten.
- **Nach PR 2:** Mit Stundenrechnung schneidet auch eine pausierende Gruppe noch nicht; sie bekommt den
  *behalten*-Hinweistext, weil der zutrifft, und die Doku sagt es. Ohne Stundenrechnung schneidet der Commit, die
  Live-Schätzung noch nicht: Bei Live-Schätzungs-Bewässerung kann ein Lauf während eines Ausfalls mehr ET bemessen,
  als der Commit danach bucht.
- **Nach PR 3:** keine Zwischenstände mehr.

### Melden

- **Reparaturhinweis** `weather_sensor_stale_<mapping_id>` (PR 1), einer je Sensorgruppe; Warnstufe, ohne
  Reparatur-Dialog (also mit `description`, `repairs.py:50-52`).
  - Erscheint, sobald der erste Eintrag der Gruppe öffnet; wird aktualisiert, wenn sich die Menge der
    stummen Entitäten ändert; verschwindet, wenn kein Eintrag mehr offen ist.
  - Beim HA-Start aus der gespeicherten Liste wiederhergestellt; er übersteht einen Neustart. Neu ist, dass
    die Integration einen Reparaturhinweis zur Laufzeit führt; heute entstehen sie nur beim Setup
    (`__init__.py:327`).
  - Platzhalter: Gruppe, stumme Entitäten mit ihren Feldern, Beginn.
  - **Text von PR 1 (behalten).** Verspricht keinen Schnitt. Freigabe-Fassung Deutsch:
    - Titel: „Ein Wettersensor von {group} meldet nicht mehr“
    - Inhalt: „Irrigation Plus hat seit {since} nichts mehr von {entities} gehört. Die zuletzt gemeldeten Werte
      werden weiter verwendet, als wären sie aktuell; Zonen, die davon abhängen, werden damit berechnet, bis wieder
      Werte kommen.
      Prüfe das Gerät und seine Integration. Hast du das Gerät ersetzt, wähle seine neuen Entitäten in der
      Sensorgruppe. Soll der Wert fest sein, nutze stattdessen die Quelle „Fester Wert“. Aktualisiert die
      Integration nur alle paar Stunden, erscheint dieser Hinweis zwischen ihren Updates und bedeutet keinen
      Ausfall.
      Dieser Hinweis verschwindet von selbst, sobald der Sensor wieder meldet.“

    Englisch:
    - Title: “A weather sensor of {group} has stopped reporting”
    - Description: “Irrigation Plus has not heard from {entities} since {since}. The last reported values are still
      used as if they were current, so zones that depend on them are calculated with those values until new ones
      arrive.
      Check the device and its integration. If you replaced the device, select its new entities in the sensor
      group. If the value is meant to be fixed, use the "Static value" source instead. If the integration only
      updates every few hours, this notice appears between its updates and does not mean the sensor has failed.
      This notice clears itself when the sensor reports again.”

    Die übrigen sechs Sprachen folgen dem englischen Text; die Quellen-Namen sind die Panel-Beschriftungen
    (`frontend/localize/languages/*.json` → `panels.mappings.cards.mapping.sources.static`).
  - **Variante für pausierende Gruppen (PR 2), Entwurf, Wortlaut wird mit dem Plan von PR 2 freigegeben:**
    zweiter Schlüssel, gleicher Titel. Inhalt sinngemäß: „Nach drei Stunden Stille werden diese Werte nicht mehr
    verwendet, und für diese Zeit wird nichts gebucht; Zonen, die davon abhängen, wässern deshalb weniger oder gar
    nicht, bis wieder Werte kommen. … Aktualisiert die Integration nur alle paar Stunden, stelle die Sensorgruppe
    auf „Letzten Wert behalten“ — sonst fehlt bei jedem Update ein Teil der Zeit.“ Der Hinweis wählt die Variante
    nach der Einstellung und, bis PR 3, nach der Stundenrechnung (mit Stundenrechnung: Text von PR 1).
- **Bus-Event `irrigation_plus_weather_stale`** (PR 1) bei Beginn und Ende jedes Eintrags. Inhalt: `mapping_id`,
  `mapping` (Name), `entity_id`, `device_id` (oder null), `fields`, `since`, `until` (null beim Beginn; beide in HAs
  Zeitzone mit Offset), `stale` (true/false). Derselbe Automations-Haken wie das vorhandene `irrigation_plus_zone_problem`. Jeder Start
  bekommt ein Ende, auch wenn die Gruppe den Sensor nicht mehr verfolgt (Präzisierung 6).
- **Log** (PR 1): WARNING beim Öffnen, ohne Schnitt-Versprechen („… has not reported since …; its last value is
  still used“), INFO beim Schließen. Ab PR 2 nennt die WARNING den Schnitt, wo geschnitten wird (pausierende
  Gruppe, bis PR 3 nur ohne Stundenrechnung).
- **Satz in der Berechnungs-Erklärung** (PR 2, nur pausierende Gruppen), je Sperre, die das Fenster berührt; neuer
  Schlüssel `module.calculation.explanation.sensor-outage`, etwa: „Sensordaten für {fields} fehlten von {start}
  bis {end} (Gerät stumm); für diese Zeit wurde nichts gebucht.“ Gruppen auf *behalten* bekommen keinen Satz
  (byte-identisch, R4).
- **Übersetzungen** in allen 8 Sprachen: Hinweis in `translations/*.json` (Block `issues`; PR 1, Variante PR 2).
  Erklärungssatz und Einstellungs-Beschriftungen in `frontend/localize/languages/*.json` (PR 2).
  `test_i18n_completeness` prüft beides. **`en.json` des Frontends ist fest ins Bundle importiert**
  (`frontend/localize/localize.ts:1`) → dist neu bauen, **erst in PR 2**; PR 1 ändert kein Frontend.

### Dokumentation

- **PR 1:** `docs/configuration-sensor-groups.md` bekommt vor *Deleting a sensor group* den Abschnitt „When a
  sensor goes silent“. Fassung wie gebaut (Revision 3). Gegenüber der Freigabe-Fassung von Revision 2 sind der
  erste und der letzte Absatz geändert: D1 (nur Sensoren der Integration des Geräts; Helfer am Gerät zählen nicht,
  gemappte Helfer sind gedeckt) und das Abschluss-Review (Fehlalarm auch bei Sensoren ohne Gerät mit ruhigem Wert,
  nicht nur bei Template-Sensoren). Deutsch:

  > **Wenn ein Sensor schweigt.** Irrigation Plus prüft alle fünf Minuten, ob die Sensoren einer Sensorgruppe noch
  > melden. Maßgeblich ist das Home-Assistant-Gerät eines Sensors: Solange irgendein Sensor dieses Geräts meldet,
  > gilt auch ein Wert als lebendig, der sich gerade nicht ändert, etwa ein Regenmesser an einem trockenen Tag. Es
  > zählen nur Sensoren der Integration, zu der das Gerät gehört: Ein Helfer am Gerät, etwa ein Verbrauchszähler,
  > hält das Gerät nicht am Leben; ein Helfer, den du selbst zuordnest, ist aber durch die Sensoren des Geräts
  > gedeckt. Ein Sensor ohne Gerät zählt für sich selbst. Steht ein Sensor auf `unavailable` oder `unknown`, gilt er
  > als stumm, egal was sein Gerät tut. Werte aus einem `input_number`-Helfer gelten nie als stumm.
  >
  > Hat ein Sensor drei Stunden lang nicht gemeldet, zeigt Irrigation Plus einen Reparaturhinweis für seine
  > Sensorgruppe und sendet das Event `irrigation_plus_weather_stale` (siehe Events). Meldet er wieder,
  > verschwindet der Hinweis von selbst, und ein zweites Event markiert das Ende. Die Berechnung verwendet in dieser
  > Zeit weiter den letzten Wert des Sensors.
  >
  > Die drei Stunden sind fest. Eine Integration, die seltener aktualisiert — etwa ein Cloud-Dienst, der nur alle
  > sechs Stunden abgefragt wird —, löst den Hinweis deshalb zwischen ihren Updates aus, obwohl nichts ausgefallen
  > ist.
  >
  > Auch ein Sensor ohne Gerät, der nur bei einer Änderung seines Werts meldet, etwa ein Template-Sensor oder ein per
  > YAML angelegter Verbrauchszähler, der Regen zählt, sieht wie ein stummer Sensor aus, sobald sein Wert drei
  > Stunden gleich geblieben ist, zum Beispiel an einem trockenen Tag. Ein in der Oberfläche angelegter
  > Verbrauchszähler gehört zum Gerät seiner Quelle, wenn sie eins hat, und ist durch es gedeckt. Soll ein Wert fest
  > sein, nutze die Quelle „Fester Wert“.

  Englisch:

  > **When a sensor goes silent.** Irrigation Plus checks every five minutes whether the sensors of a sensor group
  > still report. What counts is a sensor's Home Assistant device: as long as any sensor of that device reports, a
  > value that merely stays the same, such as a rain gauge on a dry day, counts as alive. Only sensors of the
  > device's own integration count: a helper attached to the device, such as a utility meter, does not keep the
  > device alive, but a helper you map yourself is covered by the device's sensors. A sensor without a device
  > counts for itself. A sensor whose state is `unavailable` or `unknown` counts as silent whatever its device
  > does. Values from an `input_number` helper never count as silent.
  >
  > Once a sensor has not reported for three hours, Irrigation Plus shows a repair notice for its sensor group and
  > fires the `irrigation_plus_weather_stale` event (see [Events](usage-events.md)). When the sensor reports again,
  > the notice clears itself and a second event marks the end. Meanwhile the calculation keeps using the sensor's
  > last value.
  >
  > The three hours are fixed. An integration that updates less often, such as a cloud service polled every six
  > hours, therefore raises the notice between its updates even though nothing has failed.
  >
  > A sensor without a device that reports only when its value changes, such as a template sensor or a utility
  > meter set up in YAML that counts rain, looks silent too once the value has stayed the same for three hours, on a
  > dry day for instance. A utility meter set up in the UI belongs to its source's device, if the source has one,
  > and is covered by it. If a value is meant to be fixed, use the "Static value" source instead.

- **PR 1:** `docs/usage-events.md`: das Event mit seinen Feldern (Zeile nach `irrigation_plus_zone_problem`),
  einschließlich des Endes, wenn die Gruppe den Ausfall nicht mehr verfolgt (Präzisierung 6), und der Offsets.
- **PR 1:** Docstring von `_prune_mapping_buffer` (`calculation.py:432-446`) berichtigt: Die Grenzzeile je Feld
  überlebt die Frist absichtlich als Delta-Basis; ob sie noch eine Messung ist, hält die Ausfall-Liste fest.
- **PR 2:** derselbe Abschnitt um die Einstellung erweitert: was *pausieren* tut (nach 3 h nichts gebucht,
  Regenzähler ausgenommen), die Standardwerte (bestehende Gruppen behalten, neue pausieren), der Rat für
  Integrationen mit seltenen Updates (*behalten*), und: „Mit der stündlichen Berechnung wird der letzte Wert weiter
  verwendet.“
- **PR 3:** dieser letzte Satz entfällt; der Abschnitt beschreibt den Schnitt für beide Rechenformen.

### Betroffene Stellen je PR

| PR | Datei | Änderung |
|---|---|---|
| 1 | neu: `sensor_liveness.py` | Prüfung, Liste, Hinweis, Event |
| 1 | `__init__.py` | Mixin; Timer an- und abmelden; Liste bei Quellwechsel leeren, Hinweis beim Löschen |
| 1 | `store.py` | zwei Felder an `MappingEntry`, Laden, Setter ohne Speichern |
| 1 | `calculation.py` | „Wetterdaten zurücksetzen“ leert die Liste; Docstring `_prune_mapping_buffer` |
| 1 | `const.py` | Grenzen (3 h, 5 min, 10 min, 7 Tage), Schlüssel, Event- und Hinweis-Name |
| 1 | `translations/*.json` (8) | Hinweis (Text von PR 1) |
| 1 | `docs/configuration-sensor-groups.md`, `docs/usage-events.md` | Abschnitt, Event |
| 2 | `store.py`, `websockets.py`, `const.py` | `on_silent_sensor`: Feld, Lade- und Attribut-Standard, Schema |
| 2 | `frontend/src/views/mappings/view-mappings.ts`, `frontend/localize/languages/*.json` (8) | Auswahl, Beschriftungen, Erklärungssatz; dist neu bauen |
| 2 | `weather_aggregate.py` | Masken in `aggregate_window` |
| 2 | `sensor_liveness.py` | gesperrte Zeit je Feld aus der Liste; Hinweis-Variante |
| 2 | `calculation.py` | Gate, Masken an den Commit, Aufzeichnungen überspringen, Erklärungssatz |
| 2 | `calcmodules/pyeto/__init__.py`, `calcmodules/passthrough/` | Buchungsanteil (Tagesform) |
| 2 | `translations/*.json` (8), Doku | Hinweis-Variante; Abschnitt erweitert |
| 3 | `weather_aggregate.py` | Masken in `build_hourly_rows`, `_effective_series`, `build_substeps`; Klarheitsquote |
| 3 | `calculation.py`, `live_estimate.py` | Masken im Stundenpfad und in der Live-Schätzung; Gate entfällt; Temperatur-Anker |
| 3 | `translations/*.json` (8), Doku | vereinheitlicht |

### Präzisierungen aus der Planung (2026-10-03)

Beim Schreiben des Plans von PR 1 gegen den Code gefunden; sie gehen dem Text oben vor:

1. **Keine Streichliste nötig.** Das Panel schickt beim Speichern nur `{id, name, mappings}`
   (`frontend/src/views/mappings/view-mappings.ts:379-380`), und das Schema des Mapping-Views lässt andere
   Schlüssel gar nicht zu (`websockets.py:235-250`). Stattdessen hält ein Test fest, dass ein Speichern die
   Ausfall-Liste stehen lässt. (PR 2 erweitert Panel und Schema um genau einen Schlüssel, `on_silent_sensor`.)
2. **Ein Quellwechsel leert die Liste der ganzen Gruppe**, so wie er heute Puffer und `last_entry` der ganzen
   Gruppe leert (`__init__.py:1768-1790`), nicht nur die Einträge des geänderten Feldes. Ebenso beim Löschen
   einer Gruppe: Ihr Hinweis verschwindet.
3. **Das Lebenszeichen fährt mit**, wie `data_last_entry`: Es wird bei jeder Prüfung erneuert, ohne eigenen
   Schreibvorgang, und geht mit dem nächsten Speichern auf die Platte. Ein Schreibvorgang alle 5 Minuten wäre
   ein ganzes Dokument für einen Wert, der nur über einen Neustart zählt.
4. **Eine nie gesehene Entität** (nicht vorhanden oder `unavailable`, nichts gespeichert) bekommt beim ersten
   Blick „jetzt“ als Lebenszeichen; die 3 h zählen ab da.
5. **Grenze:** Entitäten, die nach einem Neustart ihren letzten Zustand wiederherstellen, gelten zum HA-Start
   als lebendig; ein Ausfall über den Neustart beginnt bei ihnen erst mit dem Start.
6. **Gerätetausch darf zu keinen Fehlern führen** (User: „Es kann ja sein, dass Sensor-Entitäten ausgetauscht
   werden, weil ein neues Gerät beschafft wurde. Das darf nicht zu Fehlern führen.“):
   - *Neue Entitäten in der Gruppe* = Quellwechsel: Liste und Hinweis gehen, und **jeder offene Ausfall endet mit
     seinem End-Event** (`stale: false`, `until` = jetzt), damit eine Automation, die auf den Start reagiert hat,
     nicht hängen bleibt. Gleiches beim Löschen der Gruppe und bei „Wetterdaten zurücksetzen“.
   - *Neues Gerät unter denselben Entity-IDs*: Die Prüfung liest jedes Mal das aktuelle Gerät der Entität; meldet
     das neue, schließt der Ausfall regulär.
   - *Altes Gerät gelöscht, Gruppe noch nicht umgestellt*: Nach 3 h erscheint der Hinweis. Er sagt auch:
     „Hast du das Gerät ersetzt, wähle seine neuen Entitäten in der Sensorgruppe.“
   - *Selbstheilung*: Ein offener Ausfall einer Entität, die die Gruppe nicht mehr liest (Zuordnung auf anderem Weg
     geändert), endet bei der nächsten Prüfung mit End-Event; keine Liste und kein Hinweis überleben die
     Konfiguration.
   - Keine Ausnahme in diesen Fällen: fehlender Zustand, fehlender Registry-Eintrag und gelöschtes Gerät sind
     abgefangen; im Probelauf je ein Test.

### Präzisierungen aus dem Bau (2026-10-04)

Beim Bau von PR 1 aus Reviews und Proben gefunden; sie sind oben eingearbeitet und gehen Revision 2 vor. Belege im
Abweichungsprotokoll (`deviations.md`).

7. **Lebenszeichen beim Herunterfahren.** Präzisierung 3 trug nur halb: HA schreibt beim Herunterfahren nur ein
   *anstehendes* Speichern, und der Setter plante keins. Ein sauberer Neustart verlor deshalb bis zu einem
   Abfrage-Intervall Lebenszeichen, und ein Ausfall begann danach zu früh. Jetzt merkt sich der Store eine Änderung
   der Lebenszeichen, und sein Stopp-Listener plant dann ein Speichern, wie schon für den Puffer. Das Auffrischen
   der Lebenszeichen löst weiterhin kein Speichern aus.
8. **Reset und Quellwechsel lassen die Lebenszeichen stehen** (siehe *Leeren*). Sonst galt ein weiter stummer
   Sensor danach als „nie gesehen“ (Präzisierung 4): Der Hinweis verschwand für 3 h und kam mit falschem Beginn
   zurück.
9. **Eine kaputte Gruppe hält die anderen nicht auf.** Setup und Prüfung fangen Fehler je Gruppe ab und loggen sie.
10. **Leser werfen nie.** Ein unlesbarer Eintrag der Ausfall-Liste wird beim Lesen verworfen, ein
    `sensor_last_seen`, das kein Dictionary ist, beim Laden ersetzt; sonst würfe die Prüfung alle 5 min.
11. **Bekannte Grenzen von PR 1, hingenommen:**
    - Zeitumstellung (siehe *Uhr*).
    - Eine Integration, die beim Start ihren letzten Wert wiederherstellt oder neu zustellt (etwa ein retained
      MQTT-Topic oder ein Z2M-Republish), zählt als Meldung: Ein offener Ausfall endet beim Neustart und wird erst
      3 h später wieder gemeldet. Präzisierung 5 sah das für den Beginn vor; es gilt auch für das Ende. JustChrs
      Neustart-Test deckt den Fall ab, dass die Entität nach dem Start `unavailable` ist.
    - Umbenennen, neues Icon oder neuer Bereich der stummen Entität schreiben ihren Zustand neu und beenden den
      Ausfall (Fehl-Entwarnung).
    - Werte wie `n/a` gelten als gültige Meldung der eigenen Entität; das ist lockerer als der Lesepfad (PR 2).
    - Wird die Integration entfernt oder deaktiviert, bleiben offene Hinweise bis zum HA-Neustart stehen, ohne
      End-Event; der Entlade-Pfad beendet keine Ausfälle. Für diesen einen Weg gilt Präzisierung 6 („keine Liste und
      kein Hinweis überleben die Konfiguration“) also nicht → eigenes Issue.
12. **Der `config_entry_id`-Zweig** (neueres HA) läuft in keiner CI: Die Haupt-CI bekommt mit Python 3.13 höchstens
    HA 2026.2.x, und dort hat `DeviceEntry` nur `primary_config_entry`. Er läuft nur im Live-Test
    (*Ende-zu-Ende-Kriterium*, Punkt 1); der PR-Text behauptet keine CI-Abdeckung dafür.

## Schwester-Pfade geprüft

- **Poll-Schreiber mit eingefrorenem Zahlenwert:** abgedeckt (pausierende Gruppen); seine Zeilen liegen in der Sperre
  und fallen weg.
- **`last_entry` auch bei abgeschaltetem `continuousupdates`** gelesen (`calculation.py:415`): abgedeckt, weil
  die Auffüllung nur in gültiger Zeit gilt.
- **Stundenzeilen aus `last_entry`** (`weather_aggregate.py:936`), **Temperatur-Anker**
  (`live_estimate.py:880`), **Kalibrier- und Amplituden-Aufzeichnung:** abgedeckt (PR 2 bzw. PR 3).
- **`_effective_series`** stempelt ebenfalls um (`weather_aggregate.py:714`): bekommt in PR 3 dieselben Sperren.
- **Aggregat und nachgespielte Bilanz** müssen dieselbe Regensumme sehen (`calculation.py:999-1008`): Grund für das
  Gate von PR 2 (Entscheidung 8); ab PR 3 sehen beide dieselbe Sperre.
- **Zeilen-Obergrenze im Ereignis-Pfad** (`continuous_update.py:558-589`): unberührt; sie behält nur die
  älteste Zeile und ändert an Sperren nichts.
- **Ereignis-Pfad und Start-Saat ignorieren `unavailable`/`unknown`** (`continuous_update.py:264`, `:359`):
  unverändert; ein solcher Zustand wird jetzt zusätzlich als Ausfall erkannt.
- **Nur-Stempel-Zeilen** einer ganz unlesbaren Gruppe zählen weiter als Datenpunkt (Faktensammlung G.6):
  bemerkt, nicht Teil dieser Arbeit.

## Ausdrücklich nicht in dieser Arbeit

- Felder aus einem Wetterdienst (`Eifel-Joe#74`).
- Eine einstellbare Grenze, und ein Abschalten des Hinweises (J5: fest 3 h für die erste Fassung).
- Eine Zustands-Entität „Wetterdaten veraltet“.
- Ersatzwerte oder ein Rückfall auf den Wetterdienst während eines Ausfalls.
- HAs eigene Ausfallzeit.
- Ein Satz in der Berechnungs-Erklärung für Gruppen auf *behalten* (sie bleiben byte-identisch).
- Ein toter Untersensor an einem lebenden Gerät, der seinen Zahlenwert behält (blinder Fleck aus Frage 2;
  wird er `unavailable`, ist er erfasst).
- Integrationen, die die letzte Beobachtung eines Cloud-Dienstes weiterreichen und dabei denselben Wert
  weiter melden, obwohl die Station schweigt (zweiter blinder Fleck; bräuchte die Beobachtungszeit des
  Dienstes, die jede Integration anders oder gar nicht liefert).

## Verworfen

- **Design 1, Löcher je Rolle** (Revision 1): je Gruppe ein ET-Loch und ein Regen-Loch, weniger Code. JustChr wählt
  Design 2, weil Design 1 die ET der ganzen Gruppe aussetzt, wenn ein Eingang stirbt (J2).
- **„Teil 1 nie allein ausliefern“** (Plan Revision 1, weil der Hinweistext den Schnitt versprach): überholt durch
  JustChrs Aufteilung (J3). Der Hinweistext von PR 1 verspricht deshalb keinen Schnitt.
- **Die Einstellung schon in PR 1:** ein Schalter ohne Wirkung, solange nichts geschnitten wird.

## Tests

Jeweils RED vor GREEN.

**PR 1** (gebaut: 116 Tests in vier Dateien; alle 60 Mutationen auf die Wächter getötet)
- **Erkennung:** Geräte-Maximum über die bürgenden Sensoren (D1: Helfer, `update`-Entitäten und fremde
  Integrationen bürgen nicht, ein gemappter Helfer ist gedeckt, auf einem geteilten Gerät bürgt zusätzlich die
  Integration der gemappten Entität); eigene Entität `unavailable`; Entität ohne Gerät;
  `input_number`; Start-Karenz; Lebenszeichen über einen Neustart, auch über HAs Abschaltfolge ohne Speichern von
  Hand (Präzisierung 7); Stempel im Rahmen des Puffers.
- **Liste:** Öffnen nach 3 h, nicht vorher; Schließen mit richtigem Ende, eigene Rückkehr vor Geräte-Änderung (D3);
  7-Tage-Kürzung; Leeren bei Quellwechsel und Reset, Lebenszeichen bleiben (Präzisierung 8); Speichern im Panel
  lässt die Liste stehen; Store-Rundlauf (beide Felder überleben Speichern und Laden, ein Store ohne sie lädt).
- **Melden:** Event-Inhalt bei Beginn und Ende; Hinweistext in 8 Sprachen mit seinen Platzhaltern;
  i18n-Vollständigkeit.
- **JustChrs drei Hinweis-Tests** (J4), als eigene Testdatei, gegen **echten Store und echte Issue-Registry**
  (lokal echt; der Registry-Test aus Plan-Task 8 lief im Probelauf echt):
  1. der Hinweis verschwindet, wenn der Sensor wieder meldet;
  2. er übersteht einen Neustart mitten im Ausfall: HAs Abschaltfolge (STOP, FINAL_WRITE) schreibt die Liste, ein
     neuer Store lädt sie, ein neuer Koordinator zeigt den Hinweis beim Setup sofort wieder, mit unverändertem
     Beginn (Revision 3: vorher speicherte der Test von Hand und sah den Schreibweg des Herunterfahrens nicht);
  3. er fällt weg, wenn die Gruppe gelöscht wird, samt End-Event;
  4. (zusätzlich) er fällt weg, wenn der Sensor in der Gruppe ersetzt wird, samt End-Event (Präzisierung 6).
- **Keine Verhaltensänderung:** Der Diff berührt keinen Rechenpfad; die volle Suite ist namensgleich mit der
  Baseline.
- Mutationen auf die tragenden Wächter (Geräte-Maximum, eigene `unavailable`-Entität, `input_number`, 3-h-Grenze,
  Kürzung, Ende bei erster Meldung, Start-Karenz, Neustart-Wiederherstellung, Löschen, Quellwechsel, Reset,
  Schreib-Sparsamkeit, Ausnahme-Schutz).

**PR 2**
- **Einstellung:** Bestand lädt als `keep`; Erst-Einrichtung und neue Gruppe sind `pause`; Domain-Migration behält
  `keep`; Schema und Panel tragen den Schlüssel; Wechsel gleicht den Hinweis an.
- **Byte-Identität:** Eine Gruppe auf *behalten* mit Ausfällen in der Liste liefert dasselbe Aggregat, dieselbe
  Buchung und dieselbe Erklärung wie ohne Liste.
- **Gate:** Mit Stundenrechnung schneidet auch eine pausierende Gruppe nicht.
- **Sperren in der Aggregation:** zeitgewichtet; einfaches Mittel; Einzelwert; Tmin/Tmax; `last_entry`;
  Regenzähler ausgenommen; eingefrorene Poll-Zeilen fallen weg; Feld ohne gültige Zeit fehlt.
- **Buchen:** Schnittmenge der Pflichtfelder in der Tagesform; Sonnenschätzung; Passthrough; Regenrate.
- **Aufzeichnungen:** keine Kalibrier- oder Amplituden-Aufzeichnung über eine Sperre.
- **Melden:** Erklärungssatz; Hinweis-Variante; i18n-Vollständigkeit.

**PR 3**
- Stundenanteil; Klarheitsquote ohne Brücke; Druck aus der Höhe; nachgespielte Bilanz samt Abgleich;
  Live-Schätzung samt Temperatur-Anker; Gate entfernt.

Jeder PR: volle Suite mit Namensvergleich gegen die Baseline; Mutationen auf seine Wächter.

## Ende-zu-Ende-Kriterium

**PR 1, HA-Test.** Sensorgruppen aus Entitäten von Geräten, die wir steuern: MQTT-Sensoren per YAML unter einem
eigenen Topic-Präfix, **ohne Discovery** (Plan, Task 15). Die MQTT-Integration von HA-Test hängt am Broker von HA-Prod
(gelesen 2026-10-04); Discovery könnte dort Geräte anlegen, ein eigenes Präfix abonniert HA-Prod nicht. Vom User
freigegeben am 2026-10-04 (Variante 1; verworfen: Template-Helfer ohne Gerät, weil der Geräte-Pfad dann nicht live
liefe; eigener Broker für HA-Test, weil das HA-Test die Z2M-Geräte nähme).

1. Ein Gerät meldet 3,5 h lang **unveränderte** Werte → es entsteht kein Ausfall. Für beide Schreibweisen,
   soweit das Mittel sie hergibt: ein Gerät, das bei jedem Update schreibt (`last_reported` rückt vor), und eines,
   das nur bei Änderung schreibt und dessen Felder bis auf eines ruhig bleiben. Das zweite ist zugleich der einzige
   Lauf des `config_entry_id`-Zweigs auf neuerem HA (Präzisierung 12).
2. Zwei Geräte schweigen → der Hinweis erscheint rund 3 h nach der letzten Meldung, das Start-Event kommt an,
   und eine Berechnung aller Zonen in dieser Zeit läuft ohne Fehler (PR 1 ändert keine Rechnung; dass sie
   unverändert ist, belegen Diff und Suite).
3. HA-Test-Neustart mitten im Ausfall (angekündigt) → Beginn und Hinweis unverändert.
4. Das eine Gerät meldet wieder → der Hinweis verschwindet, das End-Event kommt an, der Eintrag schließt mit dem
   richtigen Ende.
5. Die Gruppe des anderen Geräts wird gelöscht → ihr Hinweis verschwindet, das End-Event kommt an.

**PR 1, HA-Prod (Feldtest, R9):** nach dem Update auf ein production-Build mit PR 1 (nur auf Zuruf des Users)
passiv beobachten: kein Fehlalarm, auch nicht in Nebelnächten mit 99 % Feuchte; ein echter Ausfall, falls einer
vorkommt, mit plausiblem Beginn und Ende. Dauer legt der User fest; Richtwert eine Woche.

**PR 2, HA-Test** mit ausgeschalteter Stundenrechnung (HA-Test ist Wegwerf): Eine pausierende Gruppe schweigt
3,5 h → die Berechnung nennt die Sperre in ihrer Erklärung und bucht ET nur für den gültigen Teil; eine Gruppe auf
*behalten* rechnet wie vorher. Mit eingeschalteter Stundenrechnung schneidet nichts.

**PR 3, HA-Test** mit eingeschalteter Stundenrechnung: dasselbe für Stundenform, nachgespielte Bilanz und
Live-Schätzung. **HA-Prod** danach passiv, sobald die Gruppe dort pausiert (Umstellen ist Sache des Users).

## Lieferung

1. ~~Issue an JustChr~~ — erledigt: `JustChr#188`, beantwortet 2026-10-03; Eifel-Joe#8 trägt
   `upstream:freigegeben`.
2. **PR 1:** Plan (`docs/superpowers/plans/2026-10-03-dead-weather-sensor-common.md`, an Revision 2 angepasst,
   probegelaufen) → Bau im Worktree von `upstream/master` → Live-Test HA-Test → PR an JustChr (Texte vorher zur
   Freigabe, keine Verweise auf unsere Issues; Rezept: Memory `hasi-pr-build-recipe`) → **production** bekommt
   PR 1 sofort (User-Regel), auch vor dem Merge → Feldtest auf HA-Prod nach Zuruf.
3. **PR 2:** eigener Plan, frühestens nach dem Merge von PR 1; gepostet nach dem Feldtest (R9).
4. **PR 3:** eigener Plan nach PR 2.
5. **P1:** Spec und Pläne nach jeder Freigabe und beim Abschluss nach `archive/design-history`.
