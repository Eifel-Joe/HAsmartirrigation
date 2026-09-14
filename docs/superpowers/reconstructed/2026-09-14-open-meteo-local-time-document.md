# Open-Meteo: das Ortszeit-Dokument als Ortszeit lesen (PR 0 zu #137)

**Stand:** 2026-09-14, Branch `fix/open-meteo-forecast-starts-tomorrow` (von upstream/master `4e53caf4`), Commit `d0e7cb6c`, **PR [#144](https://github.com/JustChr/HAsmartirrigation/pull/144)** (geöffnet 2026-09-14).
**Anlass:** JustChr auf #137 (issuecomment-5667633763): Open-Meteo-Tagesfix zuerst und eigenständig, vor PR 1 (Tagesspanne) und PR 2 (Wächter am Laufdatum).

## Befund
Die Anfrage enthält `timezone=auto` und `past_days=1`. Alle Reihen der Antwort sind Ortszeit, die Tagesreihen beginnen gestern.
1. `get_forecast_data` übersprang nur Index 0 (= gestern) und lieferte **heute** als ersten Vorhersagetag. Live belegt (Berlin, 14.09.): `daily.time` ab 13.09.
2. Schwester-Pfad (User-Entscheidung: in denselben PR): `_current_hour_index` verglich die UTC-Stunde mit Ortszeit-Zeilen → `get_data` las bei UTC+2 die Zeile von vor zwei Stunden, bei negativem Offset Stunden voraus; `OBSERVATION_TIME` stempelte die Ortszeit als UTC. Seit Einführung des Clients vorhanden. Sonde im Scratchpad: 10:30 UTC → Zeile 10:00 Ortszeit statt 12:00.

## Entscheidung
- Datumsfilter statt Index, „heute am Ort“ aus `utc_offset_seconds` des Dokuments (Wunsch JustChr).
- Aktuelle Stunde = letzte Zeile nicht nach „jetzt am Ort“; ohne solche Zeile die früheste (vorher: letzte = eine Woche voraus).
- `OBSERVATION_TIME` = Ortszeit-Stempel minus Offset.

## Verworfen
- **Zwei Positionen überspringen:** bricht bei einem nach Mitternacht aus dem Cache gelesenen Dokument und bei jeder Änderung von `past_days` (Mutant M5, nur vom Cache-Test gefangen).
- **UTC-Datum oder HA-Uhr als „heute“:** falscher Tag, wenn Standort- und UTC/HA-Zone auseinanderliegen (Mutant M2).
- **Reihe in UTC anfordern (`timezone=GMT`):** Tagesreihen und `get_hourly_data` hängen an Ortsdatum und -stunde.
- **Tagesspanne gleich mit einbauen:** gehört laut JustChr in PR 1.

## Nachweis
- 7 neue Tests (`_openmeteo_doc` nach Live-Antwortform; Vorhersage: morgen zuerst, Ortsdatum bei UTC+2/UTC−5, Cache über Mitternacht; aktuelle Bedingungen: Ortsstunde bei UTC+2/UTC−5, vor der ersten Zeile).
- 6 Mutationen, jede rot an den erwarteten Tests. Volle lokale Suite gegen master am selben Tag: gleiche 7 failed / 320 errors, 2883 → 2890 passed.
- Adversariales Review (4 Linsen × 2 Gegenprüfer): 3 bestätigte Test-/Kommentarlücken geschlossen; Wächter-Verhaltensänderung und HA-Zeitzonen-Abweichung als Release-Notes-/PR-1-Hinweis.

## Offen / Folge
- PR 1: Tagesspanne `FORECAST_DAY_START/END`; Panel und PyETO zählen bis dahin von der HA-Uhr.
- OWM/Met Office gruppieren Tage nach UTC-Datum (JustChr: Argument für PR 1).
