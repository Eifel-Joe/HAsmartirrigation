# Nebenbefunde aus dem Bau von Eifel-Joe#10 — Proben (2026-10-05)

Beim Bau des saisonalen Ausblicks (Eifel-Joe#10, upstream JustChr#191) fielen fünf Kandidaten an. Geprüft auf
upstream v2026.10.04 (`bbf2e151`), drei davon mit den Proben hier. Die Proben importieren die Integration nie: sie
ziehen einzelne echte Funktionen per `ast` aus Kopien der Quelldateien und laufen mit der Standardbibliothek.
Die Nummern „candidate 3/4/5“ in ihren Docstrings sind die Kandidaten-Nummern unten.

| Kandidat | Befund | Ergebnis |
|---|---|---|
| 1 | `generate_watering_calendar`: keine Dienst-Antwort, Events fehlen in `usage-events.md`, das Ziel wird ignoriert | bestätigt; **nicht angelegt** (User 2026-10-05: vorerst nicht), Entwurf `not-filed/issue-A-calendar-service.md` |
| 2 | Saison-Karte zeigt einen gescheiterten Monat als 0,0 und verdeckt eine gescheiterte erste Zone | bestätigt; **nicht angelegt** (ebenso), Entwurf `not-filed/issue-B-card-failed-month.md` |
| 3 | Niederschlag „Keine / nicht verwendet“ bucht trotzdem den Regen des Wetterdienstes, mit der Zähler-Regel | Verhalten bestätigt, Absicht offen → **Eifel-Joe#84** |
| 4 | PyETO teilt in der Polarnacht durch null; die Zone wird übersprungen und bleibt an dem Tag hängen | Division bestätigt; das Hängenbleiben nur aus dem Code abgeleitet → **Eifel-Joe#85** |
| 5 | PyETO-Zone ohne Niederschlagsquelle und ohne Wetterdienst | kein Fehler der Rechnung: die Zeile hat kein `Precipitation`, gebucht wird 0 (`precip_none_probe`, Abschnitt C). Dass der Ausblick trotzdem Klima-Regen abzieht, ist eine benannte Grenze von JustChr#191 |

| Datei | Was |
|---|---|
| `extract_blobs.sh` | legt die gelesenen Quellkopien aus `bbf2e151` an (`sh extract_blobs.sh <Klon>`). Nachgeprüft in einem frischen Ordner: alle zehn Kopien byte-gleich mit denen, aus denen die Ausgaben stammen, und alle drei Ausgaben byte-gleich reproduziert |
| `probe_lib.py` | gemeinsamer Lader: das echte `calculate`/`calculate_et_for_day` von PyETO gegen die mitgelieferte FAO-56-Bibliothek |
| `polar_night_probe.py` → `.out.txt` | Kandidat 4: Sonnengeometrie, dunkle Tage je Breite, jedes Strahlungsverfahren bei 69° N am 21. Dezember, Kalender-Monate, Jahresdurchlauf |
| `polar_latch_probe.py` → `.out.txt` | Kandidat 4: bildet den Ablauf von `calculation.py` nach (Wasserstand rückt nur bei Erfolg vor, `weather_day` aus dem Wasserstand), November bis März ohne Eingriff, dazu die Erholung nach dem Setzen des Eimers. **Kein echter Koordinator** — deshalb steht das Hängenbleiben im Issue als abgeleitet |
| `precip_none_probe.py` → `.out.txt` | Kandidaten 3 und 5: `strip_foreign_source_values` je Quelle, die Aggregat-Regel (0,4 statt 0,8 mm), der Fall ohne Wetterdienst |
| `not-filed/` | die beiden nicht angelegten Entwürfe, so wie sie dem User am 2026-10-05 vorlagen; in B ist nur die Nummer des Polarnacht-Verweises auf die echte berichtigt (Eifel-Joe#85) |

Ausführen (gelaufen mit dem Repo-`.venv`, Python 3.12):

```bash
sh extract_blobs.sh /d/Entwicklung/HASI/HAsmartirrigation
/d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe polar_night_probe.py
```
