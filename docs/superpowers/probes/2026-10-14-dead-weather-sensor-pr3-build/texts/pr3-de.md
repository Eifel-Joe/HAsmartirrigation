**Titel:** feat(liveness): eine pausierende Sensorgruppe wird auch in der Stundenrechnung und in der Live-Schätzung geschnitten

## Problem

Seit #197 lässt eine Sensorgruppe auf *Pausieren* die stumme Zeit eines Sensors weg, aber nur in der Tagesrechnung und nur, solange „Stündliche Verdunstung“ aus ist. Mit der Stundenrechnung bucht der Commit den eingefrorenen Wert weiter. Die Live-Schätzung schneidet in keiner Form; in der Tagesform kann sie deshalb einen Lauf während eines Ausfalls nach mehr Verdunstung bemessen, als danach gebucht wird (#188). Das ist der dritte der drei PRs, um die du auf #188 gebeten hast: Stundenpfad und Live-Schätzung. Wie angekündigt auf den gemergten master gesetzt; die 14 Commits sind nur die neuen.

## Fix

### Teil A — der Commit

- **Eine Funktion schneidet das Fenster einer Zone für jeden Aufrufer** (`zone_blocked_spans` in `sensor_liveness.py`; Store, Zone und Fenster ausdrücklich), damit Commit und Live-Schätzung dieselben Sperren bekommen. Die Bedingung „nur ohne Stundenrechnung“ fällt weg.
- **Stundenzeilen:** Ein gesperrtes Feld wird in jeder Stunde nur über seine eigene gültige Zeit gemittelt, nie in eine Sperre hinein gehalten; danach gilt wieder der Wert von davor, wie in der Tagesform. Gebucht wird je Stunde nur die Zeit, in der Temperatur, Feuchte, Wind und Sonne gemeinsam gemessen waren. Eine Stunde ganz ohne solche Zeit bleibt als Zeile ohne Messwerte und ohne ET: Die Stundenreihe bleibt vollständig, ein stummer Sensor schickt das Fenster also nicht in die Tagesform. Fehlt ein Feld aus einem anderen Grund, bleibt der heutige Weg zur Tagesform. Der Druck ist kein Pflichtfeld; wo er gesperrt ist, springt wie heute der Höhendruck ein.
- **Klarheitsquote:** Eine Probe in einer Sperre zählt weder als Messung ihrer Stunde noch als Quelle einer Quote; nach der Sperre gilt die Quote von davor bis zur nächsten Probe.
- **Nachgespielte Bilanz (Teilschritte):** ET wird nur in gemessene Zeit gelegt (gesperrte Teile haben Sonnengewicht 0, eine dunkle Stunde verteilt ihren Teil über ihre gemessene Zeit). Nur die Lage ändert sich, die Summe nicht. Eine gesperrte Regenrate zählt nur ihre gemessenen Anteile, also hält der Abgleich mit dem Niederschlag des Aggregats — der Grund, aus dem #197 die Stundenform noch ausnahm.
- **Anteil nach der Form, die gelaufen ist** (`required_sensor_fields`, auch von der Live-Schätzung benutzt): Stundenform Temperatur, Feuchte, Wind, Sonne; Tagesform wie in #197. Die Stundensumme enthält schon nur den gemessenen Teil und wird nicht noch einmal skaliert; die Erklärung nennt den Zeitanteil mit demselben Satz wie in #197.
- **Was der Nutzer sieht:** Hinweis-Variante und WARNING aus #197 hängen nicht mehr an der Stundenrechnung, und das Umschalten der Stundenrechnung schreibt offene Hinweise nicht mehr um. In der Panel-Hilfe fällt der Satz „Gilt nur, solange ‚Stündliche Verdunstung‘ (Experimentelle Funktionen) aus ist.“ in allen 8 Sprachen (2 der 4 Bundles neu gebaut). Die Doku nennt die Pflichtfelder je Form, sagt, was die Stundenform mit einer teilweise gemessenen Stunde macht, und dass der Prozentwert Zeit zählt.

### Teil B — die Live-Schätzung

- **Dieselben Sperren an jedem Leser:** einmal je Neuberechnung vom Anker bis zu ihrem `now` gerechnet und an Aggregat und Niederschlag, Stundenzeilen, nachgespielte Bilanz und die aktuelle Temperatur gegeben; Letztere wird nicht von einem gerade stummen Sensor gelesen.
- **Quellenkette:** Ein wegen einer Sperre leeres Fenster liefert 0 ET statt `None`. Die Kette fällt deswegen nie auf die Stundenreihe eines Wetterdienstes zurück, aus der der Commit nie bucht. Der Tagesform-Spiegel bucht den Anteil, den der Commit bucht; ein ganz stummes Fenster bucht 0, auch wenn keine nutzbare Prognose da ist.
- **Hochrechnung bis zum Entscheidungspunkt:** aus dem geschnittenen Aggregat; ob der Sensor zurückkehrt, wird in keine Richtung angenommen.
- **Übertrag und Auffrischung:** Der Schlüssel des Stundenübertrags enthält die Ausfall-Einträge der Gruppe und ihre Einstellung (die Einträge, nicht die daraus geschnittenen Sperren; eine offene Sperre änderte den Schlüssel sonst jede Minute). Die Prüfung frischt die Schätzungen einmal auf, wenn ein Ausfall einer pausierenden Gruppe beginnt oder endet, und zwar ungedrosselt: Eine stumme Station schickt danach keine Zeile, die einen verschluckten Anstoß nachholen würde.
- Eine Gruppe auf *Letzten Wert behalten* wird geschätzt wie bisher.

### Wo der Bau von meinem Vorschlag auf #188 abweicht oder ihn genauer fasst

1. **Klarheitsquote:** Der Vorschlag sagte, die gehaltene Quote überbrücke keine Sperre. Gebaut ist: In der Sperre zählt keine Probe, danach gilt die Quote von davor. Sonst zählten die Nachtstunden nach einer Sperre am Abend nicht.
2. **Ein Pflichtfeld der Stundenform ist das ganze Fenster gesperrt:** Die Stundenform bleibt und bucht 0 ET, statt auf die Tagesform zurückzufallen, die bei stummer Sonne den vollen geschätzten Tag gebucht hätte.
3. **Der Prozentwert zählt Zeit, nicht Menge:** Eine nachts stumme Sonneneinstrahlung senkt ihn, kostet aber kaum Verdunstung. Ein Mengenanteil hätte die gesperrten Stunden mit dem eingefrorenen Wert rechnen müssen. Die Doku sagt es.
4. **Grenze:** Für Passthrough-Zonen hat die Live-Schätzung keine Sensor-ET; dort wird nur eine gesperrte Regenrate geschnitten.

## Testing

- **80 neue pytest-Fälle**, 60 in fünf neuen Testdateien, 20 in vier bestehenden; vier Tests, die den Zwischenstand aus #197 festhielten, sind umgedreht oder entfallen. Darunter: byte-identische Stundenzeilen, Teilschritte, Erklärung und Live-Ergebnis für *Letzten Wert behalten*, für keine/leere Sperren und für Sperren fremder Felder (Vergleich mit `==`); Sperre am Anfang, in der Mitte, am Ende einer Stunde, über eine ganze Stunde und über das ganze Fenster; ein Fenster, das in einer Sperre beginnt; nur der Druck stumm; Offset-Stempel im Ausfall-Eintrag; Live-Eimer = gebuchter Eimer nach einem Ausfall in beiden Formen; die Live-Schätzung allein ohne den Rechen-Mixin.
- **37 Mutationen** der tragenden Prüfungen, jede gefangen.
- **Volle Suite lokal** (Python 3.12, HA 2024.12): die fehlschlagenden Tests namensgleich wie auf `master`, passed 3925 → 4001. Auf 32 der neuen Tests, die einen echten Koordinator bauen, folgt lokal ein Teardown-ERROR „Lingering timer“; 466 bestehende Tests zeigen lokal dasselbe Muster, CI nicht. `black` sauber, `ruff` 0.17.1 (dein neuer Pin) sauber; der frische Bundle-Build ist byte-gleich mit den committeten.
- **Live auf einer Testinstanz**, Stundenrechnung und Live-Schätzung an, PyETO mit gemessener Sonne, ein MQTT-Gerät mit Temperatur, Feuchte, Wind und Sonne, eine pausierende und eine behaltende Gruppe am selben Gerät:
  - Nach 3 h zeigt die pausierende Gruppe die Hinweis-Variante aus #197, obwohl die Stundenrechnung an ist; die behaltende den Text aus #190.
  - Die Live-ET der pausierenden Zone wuchs ab Beginn + 3 h nicht mehr; Quelle durchgehend die stündliche Sensorrechnung, nie der Wetterdienst. Die der behaltenden wuchs weiter.
  - Nach der Rückkehr bucht die pausierende Zone 56 % der ET, genau den vorab aus den gespeicherten Zeiten gerechneten Anteil (Fenster 5 h 34 min, davon 2 h 28 min gesperrt), mit einem Satz für alle vier Felder und der Wasserbilanz in 7 Teilschritten. Der Live-Eimer direkt vor dem Commit lag weniger als 0,0001 mm neben dem gebuchten. Die behaltende Zone bucht voll, ohne Satz.
  - Die Sensoren schwiegen 5½ statt der geplanten 3½ Stunden; an den Prüfungen ändert das nichts.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
