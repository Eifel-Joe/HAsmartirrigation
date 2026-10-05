# Für das Abschluss-Review am Endstand (aus den Task-Reviews)

- Task 1 / R1-4: drei Sätze am Endstand nachlesen — `watering_calendar.py` Kommentar in
  `_calculate_monthly_et_pyeto` („only where the calculation books it“), Testkommentar „no Kc (reads as
  1.0)“ im Ganzkalender-PyETO-Test, Klassen-Docstring von `TestAMonthIsPricedByTheCalculationsRules`.
- Task 1 / R1-6: am Endstand sind `json`, `math`, `ZONE_KC`, `_ROOT`, `_module_instance` in
  `tests/test_watering_calendar.py` benutzt (sonst F401, falls `tests/` je gelintet würde).
- Task 1 / R1-3 (abgelehnt, zur Kenntnis): kein Vertragstest „PyETO-Gleichung ignoriert Regen“;
  `calculation.py` trägt dieselbe Annahme.
- Bewusst bewerten: die Nutzertexte (Karte, Dienst, Doku, `calculation_notes`) sagen „derived from latitude
  only“, der Generator nimmt den Luftdruck aus der Höhe (`altitudeToPressure(self._elevation …)`). Freigegebene
  Formulierung der Spec; Kernaussage „nicht gemessen“ — im Abschluss-Review als Frage stellen, nicht stillschweigend.

## Für den PR-Text (Task 12)

- Südhalbkugel: der Klima-Commit ändert dort effektiv nur `average_daily_et` (Passthrough-ET). Feuchte, Wind,
  gemäßigter Regen und Taupunkt lagen dort schon winterlich (Juli-Gipfel = Südwinter); die PyETO-ET-Spalte im Süden
  ist unverändert. Nicht behaupten, der Süden ändere sich für PyETO.
- Norden (Reviewer-Nachrechnung, vor dem PR selbst nachmessen): PyETO-ET 50° N Juli 5,13 → 5,67 mm/Tag, Januar
  0,85 → 0,66; Juli-Regen (gemäßigt) 120 → 60 mm.
- Spec Abschnitt 5 formuliert „Luftfeuchte, Wind, Niederschlag … bleiben im Süden in der Phase des Nordens, im
  Widerspruch zu ‚Winter‘“ — für Feuchte/Wind/Regen im Süden ungenau (dort passte es zufällig); nicht in den PR übernehmen.
- `calculation_notes` ist API-sichtbar (WebSocket, HTTP-View, Event `irrigation_plus_watering_calendar_generated`):
  neuer Wortlaut als eine Zeile im PR nennen. Kein Verbraucher im Repo parst ihn (Reviewer Task 6).

## Für den Live-Test (Task 11, Sichtprüfung durch den User nach Strg+F5)

- Hinweiszeile in der Karte „Saisonaler Ausblick“: liegt sie zu eng auf dem Tabellenkopf? (`.weather-note` hat
  keinen Außenabstand; Reviewer-Rendering `review-scratch\t8_note_gap.png`.) Falls ja:
  `.weather-note + .seasonal-table { margin-top: 8px; }` in `view-weather-data.ts` (Bundles neu bauen).
- Wortlaut-Fragen an den User: „latitude only“ vs. Höhe (Option 1 lassen / Option 2 „Breitengrad und Höhe“) und die
  deutsche Dienstbeschreibung („veranschaulichenden Klimas“ → „…allein aus dem Breitengrad abgeleiteten
  Beispielklimas“?).

## Nebenbefunde (Kandidaten für eigene Issues, nicht in diesem PR)

- Ein fehlgeschlagener Monat (`watering_calendar.py`, `except` in der Monatsschleife) liefert `estimated_et_mm: 0.0`
  und Menge `0.0` neben `error`; die Karte ignoriert `error` und zeigt 0 ET für den Monat (Reviewer Task 6).
- PyETO-Gleichung wirft `ZeroDivisionError` ab |Breite| ≥ 68–70° in der Polarnacht (`sol_rad_from_sun_hours`,
  Tageslänge 0); im Kalender je Monat abgefangen (Reviewer Task 1 und 5). Vorbestand.
