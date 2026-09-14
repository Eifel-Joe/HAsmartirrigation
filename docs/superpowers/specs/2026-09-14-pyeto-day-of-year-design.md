# PyETO rechnet mit dem Tag der Wetterdaten statt mit dem Tag der Uhr

Datum: 2026-09-14 · eigener Upstream-PR, nicht Teil von #140
· Basis `upstream/master` = `437042a7` (v2026.09.15)

## Herkunft

Die CI auf PR #140 ist seit 2026-09-14 rot. Einziger Fehlschlag in beiden Test-Jobs
(je 2871 passed):

```
tests/test_live_estimate_replayed_balance.py::TestTheGapNarrowsAsTheWindowCloses::test_the_projected_day_closes_on_the_committed_one
assert 0.3987768847146156 > 0.4
```

Auf `master` schlägt der Test lokal identisch fehl; #140 ist nicht die Ursache.
Entscheidungen des Users: eigener PR statt Bündelung in #140; alle Aufrufer desselben
Fehlers im selben Fix (Schwester-Pfad-Regel); Tag als optionaler Parameter.

## Wurzel

`calcmodules/pyeto/__init__.py:230`, in `PyETO.calculate_et_for_day`:

```python
day_of_year = datetime.datetime.now().timetuple().tm_yday
```

Der Tag des Jahres für `sol_dec`, `sunset_hour_angle`, `inv_rel_dist_earth_sun`,
`et_rad` und `cs_rad` kommt aus der Uhr, nicht aus dem Tag, zu dem die Wetterdaten
gehören. Die Zeile stammt aus `8a52ce40` (2023-08-14) und ist seitdem unverändert.

## Belege

Nur das Datum wird verändert, alles andere bleibt gleich:

| Uhr | Ergebnis |
| --- | --- |
| ganze Uhr eingefroren, 2026-09-13 05:00 und 16:00 UTC | grün |
| ganze Uhr eingefroren, 2026-09-14 05:00 und 18:00 UTC | rot, 0.39878 |
| ganze Uhr eingefroren, 2026-09-20 12:00 UTC | rot, 0.37652 |
| nur PyETOs `datetime.now()` auf 2026-09-13 | grün |
| nur PyETOs `datetime.now()` auf 2026-09-20 | rot, 0.37652 |
| nur PyETOs `datetime.now()` auf 2026-05-22, den Tag des Tests | grün |

Mechanik: Der Test vergleicht zwei PyETO-Auswertungen desselben Fensters, die sich nur in
der Tageshöchsttemperatur unterscheiden (29,0 °C gegen 26,0 °C). Der einzige Term der
Differenz, der vom Tag des Jahres abhängt, ist die kurzwellige Nettostrahlung, und sie
ist proportional zur extraterrestrischen Strahlung Ra. Der Abstand fällt deshalb mit der
Jahreszeit und liegt am Test-Breitengrad nur über 0,4, solange Ra über etwa
30,4 MJ/m²/Tag liegt.

Zwei weitere Tests hängen vom selben Datum ab und kippen ohne Fix im Herbst:

- `TestTheForecastTierIsPublished::test_the_self_contained_tier_beats_reading_the_extremes_off_the_morning`
  wird etwa ab Mitte Oktober rot.
- `test_solrad_clamp_warning.py::TestTheCalculationPath::test_a_plausible_reading_warns_about_nothing`
  übergibt Wetterdaten ohne Datum. Am Breitengrad der Test-Fixture (32,87°) liegt die
  Klarhimmelstrahlung ab etwa 2026-10-13 unter den 20 MJ des Tests, dann greift der Clamp.

## Befunde

**Aufrufer** (Kartierung aller Wege in die Tagesformel):

| Aufrufer | Tag, zu dem die Wetterdaten gehören | Uhr heute richtig? |
| --- | --- | --- |
| Tägliche Berechnung `calculation.calculate_module` (feste Zeit, vor dem Lauf, nachgeholt, Dienste) | Fenster ab der letzten Berechnung bis jetzt | bei Abendrechnung ja, bei Frührechnung und der Mitternachts-Absicherung einen Tag voraus |
| Stündliche Form `_hourly_et_for_zone` | jede Stunde mit ihrem eigenen Tag | ja, ruft PyETO nicht auf |
| Live-Schätzung `live_estimate._composed_day_et` | Anker bis Anker plus 24 h | manchmal |
| Hargreaves-Ersatz in `_composed_day_et` (Zonen ohne eigene Tagesformel) | dasselbe Fenster | nutzt das Datum der Aktualisierung |
| Vorhersagetage in `PyETO.calculate` | Eintrag x ist laut Vertrag morgen plus x | nie |
| Bewässerungskalender `watering_calendar._calculate_monthly_et_pyeto` | ein Monat | nie, alle zwölf Monate bekommen den Tag des Öffnens |

Alle Wege der täglichen Berechnung laufen durch eine Stelle: `calculate_module` ruft
`modinst.calculate(weather_data=..., forecast_data=...)`. Dort liegen das Fensterende
`now` und der Fensterbeginn `zone[ZONE_LAST_CONSUMED]` bereits vor. Die Live-Schätzung hat
`anchor` und `now`. Der Kalender hat `month` und nutzt schon das Referenzjahr 2024.
Vorhersage-Einträge tragen bei keinem der vier Wetterdienste ein Datum.

**HA-Prod** (Diagnose, 2026-09-14):

| Einstellung | Wert |
| --- | --- |
| `autocalcmode` / `calctime` | `fixed_time` / 23:00 |
| PyETO `solrad_behavior` | `3` = DontEstimate, Strahlung gemessen |
| PyETO `forecast_days` | 0 |
| `hourlycalculation` | an |
| `live_estimate_enabled` | an |

## Design

1. **`PyETO.calculate_et_for_day(weather_data, *, day=None, warn_on_clamp=True)`.** `day`
   ist ein `datetime.date`. Mit `day` rechnet die Formel Sonnenstand und Strahlung für
   diesen Tag. Ohne `day` gilt wie bisher das heutige Datum. Das ist der Rückfall für
   fremde Aufrufer und für Tests ohne Datum.
2. **`PyETO.calculate(weather_data, forecast_data, *, day=None, forecast_first_day=None,
   warn_on_clamp=True)`.** Die Wetterdaten werden mit `day` gerechnet, Vorhersage-Eintrag
   `x` mit `forecast_first_day` plus `x` Tage. Fehlt `forecast_first_day`, gilt der Tag nach
   `day`; fehlt auch `day`, der Tag nach heute. Beide neuen Parameter sind keyword-only,
   weil Tests `calculate(weather, None)` positionell aufrufen.
3. **Eine Regel für den Tag eines Wetterfensters**, als Funktion in `weather_aggregate.py`
   neben `_window_bounds`: Der Tag ist das Datum von Fensterbeginn plus zwölf Stunden;
   ohne bekannten Beginn das Datum des Fensterendes. Die Funktion liest keine Uhr.
   Begründung: Berechnung und Live-Schätzung beginnen am selben Zeitpunkt und bekommen so
   denselben Tag, bevor das Fenster schließt. Bei 24 Stunden ist es die Fenstermitte.
   Bei Abendrechnung bleibt das Datum gleich; bei Frührechnung ist es der Vortag, dem die
   meisten Wetterstunden gehören.
4. **Aufrufer:**
   - `calculate_module` übergibt `day` nach der Regel aus Fensterbeginn und `now` sowie
     `forecast_first_day` als Datum von `now` plus ein Tag, weil die Vorhersage im selben
     Durchgang abgerufen wird und laut Vertrag morgen beginnt.
   - `_composed_day_et` bestimmt `day` nach der Regel aus `anchor` und `now`, übergibt ihn
     an `modinst.calculate` und rechnet auch den Hargreaves-Ersatz mit diesem Tag.
   - `_calculate_monthly_et_pyeto` übergibt `datetime.date(2024, month, 15)`.
5. **Kein Zustand am Modulobjekt.** Berechnung, Live-Schätzung und Kalender teilen ein
   zwischengespeichertes Objekt, die Live-Schätzung rechnet jede Minute. Der Tag reist nur
   als Argument.

## Verworfen

- **Tag im Wetterdatensatz:** `aggregate_window` schreibt einen Datumsschlüssel, PyETO
  liest ihn mit. Erreicht Berechnung, Schätzung und Test-Helfer ohne Änderung an den
  Aufrufstellen, legt aber einen Nicht-Wetterwert in einen Datensatz aus Sensorfeldern,
  und Kalender und Vorhersagetage bräuchten trotzdem einen eigenen Weg.
- **Tag als Pflichtparameter:** Kein Aufrufer könnte ihn vergessen, aber jeder fremde
  Aufrufer bräche, und mehr Tests änderten sich, als der Fix braucht.
- **Nur den Test festnageln:** Die CI würde grün, der Fehler in Berechnung, Schätzung,
  Vorhersagetagen und Kalender bliebe.
- **Fensterende statt Fensterbeginn:** Berechnung und Schätzung bekämen verschiedene Tage,
  bis das Fenster schließt; genau diese Übereinstimmung prüfen die Schätzungstests.

## Tests

Bestehende datumsabhängige Tests:

- Der Test-Helfer `_committed_daily_et` in `test_live_estimate_replayed_balance.py` ruft
  PyETO direkt auf und übergibt denselben Tag, den die Regel für das nachgespielte Fenster
  liefert (2026-05-22). Dort beträgt der Abstand 0,5546.
- Der Clamp-Test ohne Datum bekommt einen ausdrücklichen Hochsommertag, an dem 20 MJ
  plausibel sind.

Neue Tests, jeweils zuerst rot:

- PyETO: Dieselben Wetterdaten ergeben am 21. Juni und am 21. Dezember verschiedene Werte;
  ein übergebener Tag liefert dasselbe wie der Rückfall bei auf diesen Tag eingefrorener Uhr.
- Vorhersagetage: Zwei gleiche Einträge werden mit dem ersten Vorhersagetag und dem Tag
  danach bewertet; der Mittelwert wird gegen einzeln berechnete Tageswerte geprüft.
- Regel für den Wettertag: Beginn 23:00 ergibt den Folgetag, Beginn 06:00 und 02:00
  denselben Tag, unbekannter Beginn das Datum des Endes.
- Berechnung: Dasselbe Wetterfenster ergibt mit der Uhr im Mai und im Dezember denselben
  Wert.
- Live-Schätzung: dasselbe für die Hochrechnung, dazu ein Pin auf den Tag der
  Hargreaves-Ersatzschätzung.
- Kalender: Die zwölf Aufrufe bekommen der Reihe nach den 15. jedes Monats.

Mutationsproben: Tag in der Berechnung weglassen; Fensterende statt Fensterbeginn;
Vorhersage-Versatz entfernen; Kalendertag weglassen; Ersatzschätzung wieder mit dem Datum
der Aktualisierung. Jede muss mindestens einen der neuen Tests rot machen.

## Wirkung

- **HA-Prod:** Die Eimer ändern sich nicht. Berechnung und Live-Schätzung laufen dort über
  die stündliche Form; auch die Tagesformel bekäme bei 23:00 dasselbe Datum. Aus
  Einstellungen und Code geschlossen, nicht gemessen.
- **Bewässerungskalender:** ändert sich sichtbar, auch auf Prod. Wintermonate fallen,
  Sommermonate steigen, und die Tabelle hängt nicht mehr vom Tag des Öffnens ab.
- **Installationen mit geschätzter Strahlung** (Voreinstellung): Frührechnung vor dem Lauf
  und die Mitternachts-Absicherung rechnen künftig mit dem Vortag. Mitte September macht
  ein Tag weniger als ein Prozent Verdunstung aus.
- **Installationen mit Vorhersagetagen:** jeder Vorhersagetag mit seinem eigenen Tag.
- **PR #140** wird grün, sobald der Fix auf `master` liegt und `master` in den Branch
  gemergt ist.

## Fehlerfälle

- Kein `day`: heute, wie bisher.
- Fensterbeginn unbekannt (nie berechnete Zone): Datum des Fensterendes.
- Fenster länger als ein Tag (ausgelassene Berechnung): Mitte des ersten Tages, wie die
  Live-Schätzung.
- Zeitzonen: Die Regel liest keine Uhr und übernimmt den Zeitpunkt des Aufrufers. Eine
  Abweichung zwischen Betriebssystem- und HA-Zeitzone bleibt, wie sie ist.
- Referenzjahr 2024 ist ein Schaltjahr: Der 15. März ist dort Tag 75 statt 74.
  Vernachlässigbar.

## Prüfkriterien

- Die drei datumsabhängigen Tests laufen mit eingefrorener Uhr am 2026-03-01, 2026-05-22,
  2026-09-14 und 2026-12-21 grün.
- Jeder neue Test ist vor der Änderung rot und danach grün; jede Mutation beißt.
- Volle Suite gegen die Basis am selben Tag: nur die umgebungsbedingten Vorbestandsfehler.
- CI des PRs: beide Test-Jobs grün.

## Außerhalb

- Open-Meteo-Vorhersagen fehlen Taupunkt und Luftdruck, deshalb tragen sie in
  `PyETO.calculate` nichts bei (`OpenMeteoClient.py` 222-230).
- Die einfache Näherung für Wetterdienste ohne Stundenwerte (`live_estimate.py` um 1048)
  rechnet mit dem Datum der Aktualisierung und dem ersten Vorhersageeintrag; letzteres
  steht schon auf #137.
- `DEFAULT_SOLRAD_BEHAVIOR` ist ein Enum-Mitglied, die Verzweigungen vergleichen gegen
  `.value`-Strings. Nicht geprüft.
- Der Kalender zählt Niederschlag zur Verdunstung und zieht ihn danach wieder ab; der
  Static-Zweig behandelt einen Tageswert als Monatswert. Nicht geprüft.
- Abweichung zwischen Betriebssystem- und HA-Zeitzone.
