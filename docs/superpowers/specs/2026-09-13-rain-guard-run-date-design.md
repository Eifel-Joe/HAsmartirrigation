# Regen-Wächter am Datum des Laufs

Datum: 2026-09-13 · Issue [#137](https://github.com/JustChr/HAsmartirrigation/issues/137)
· Basis `upstream/master` = `437042a7` (v2026.09.15) · zwei PRs, PR 2 baut auf PR 1 auf

## Symptom, live auf HA-Prod

Laufprotokoll aller drei Zonen:

| Tag | Ergebnis | Detail |
|---|---|---|
| 2026-09-12 06:19 | `skipped` | `precipitation` |
| 2026-09-13 06:20 | Beet `completed`, 420 s, 21,7 L | — |
| 2026-09-13 06:32 | Kirschlorbeer `completed`, 1119 s, 82,0 L | — |

Die Vorhersage für den 13. lag bei 3,38 → 2,15 → 1,52 → 4,8 mm (gelesen Sa. vormittags bis
So. 20:35), gemessen fielen bis 20:35 **0,8 mm**, erster Regen 16:45, also 10 Stunden nach
der Bewässerung. Konfiguration: Übersprung an, Schwelle 2 mm, Fenster 1 Tag.

Übersprungen wurde der trockene Tag vor dem Regen, bewässert wurde der Regentag.

## Frage 1: Fehleinstellung?

**Nein.** Belegt gegen Code und HA-Prod-Konfiguration:

- `precipitation_forecast_days` ist auf mindestens 1 geklemmt (`max(1, …)`, Frontend `min=1`),
  und 1 bedeutet „morgen". Kein Wert deckt den Bewässerungstag ab.
- Der Modus „weniger bewässern" (`forecast_weighting_enabled`) rechnet bei `fixed_time` um 23:00
  und trifft dadurch den richtigen Tag. Er hätte den Samstag nicht gestrichen. Bei aktiver
  Live-Schätzung rechnet `_zone_run_decision` die Dauer für Zonen **ohne** Flusssensor aber beim
  Start neu aus dem Live-Defizit (`_duration_for_deficit` → `zone_run_duration`), und die Kürzung
  fällt weg. Nur Flusssensor-Zonen behalten sie. Der Modus ist zudem experimentell.
- `before_run` verschiebt die Berechnung auf den Start und würde die Gewichtung ebenfalls einen Tag
  daneben legen.
- Es gibt nur einen Zeitplan („Sunrise", am Ende verankert). Der Wächter läuft ausschließlich
  beim Start (`scheduler.py:2247`); `scheduler.py:1358` ist nur Vorschau.

## Wurzel

`_eval_precipitation` summiert ganze Kalendertage aus `get_forecast_data`. Diese Liste beginnt
vertragsgemäß morgen, in jeder Quelle (`OWMClient.py:268`, `MetOfficeClient.py:343`,
`OpenMeteoClient.py:191`, Pirate Weather ab Index 1). Der Wächter läuft aber beim Start am
Morgen des Bewässerungstags, also beginnt sein Fenster am Tag **nach** dem Lauf.

## Befunde der Recherche, die das Design bestimmen

1. **Alle vier Quellen** haben `get_hourly_precipitation_forecast()` mit einheitlichem Vertrag:
   `[(zeitzonenbehafteter UTC-Zeitpunkt, mm/h)]`, Rate über das Intervall, das am Zeitstempel
   **endet**, gelesen aus dem bereits geholten Dokument. `LiveEstimateMixin` nutzt sie schon.
   Eine frühere Aussage, nur eine Quelle liefere Stundendaten, war falsch.
2. **Die Tageseinträge tragen kein Datum.** Fünf Stellen lesen sie positional:
   `skip_conditions.py:171` (Regen), `:367` (Frost), `calculation.py:1075` (Gewichtung),
   PyETO-Vorhersage, `live_estimate.py:1048`.
3. **Open-Meteo beginnt seit dem 12. Juni heute statt morgen.** `c5f03d1b` (30.05.) überspringt
   Index 0; `86b00dfb` (12.06.) fügt `&past_days=1` hinzu, ohne `get_forecast_data` anzupassen.
   Mit einem vergangenen Tag steht an Index 1 heute. Kein Test deckt das ab (der einzige
   Open-Meteo-Test zu `get_forecast_data` prüft Caching mit leerem Dokument).
4. **Das Panel** (`websocket_get_weather_forecast`) rechnet das Datum als `heute + i + 1` mit dem
   Kommentar „All clients skip today" und beschriftet Open-Meteo deshalb um einen Tag falsch.
5. **Tagesgrenzen unterscheiden sich:** OWM und Met Office bucketen nach UTC-Datum, Open-Meteo
   (`timezone=auto`) und Pirate Weather nach Ortsdatum.
6. **Reichweite der Stundenreihe:** OWM 5 Tage dreistündlich, Open-Meteo 7 Tage, Met Office
   48 Stunden (die Reihe zieht das stündliche Dokument vor), Pirate Weather 48 Stunden
   (API-Standard ohne `extend=hourly`, im Code nicht belegt).
7. Kein Code durchläuft alle Schlüssel eines Tageseintrags; Tagesprognosen werden nirgends
   gespeichert oder serialisiert. Ein zusätzliches Feld ist sicher.

## Entscheidung zur Form (JustChr auf #137, 2026-09-13)

**Option 1, verankert am Datum des Laufs** in Home-Assistant-Ortszeit. Bei N Tagen: Laufdatum plus
die N-1 folgenden Tage. Die Einstellung behält ihre Bedeutung. `get_forecast_data` schließt heute
weiter aus. Die Gewichtung bleibt in diesem Change unverändert.

### Verworfen

- **Option 2 aus #137** (Zahl aus der Nachtberechnung merken): unter `before_run` kommt die
  Berechnung beim Start, `forecast[0]` ist dann schon der Tag nach dem Lauf.
- **Rollierend 24 h × N ab Start** (zunächst gewählt): JustChrs Laufdatum-Semantik behält die
  Bedeutung der Einstellung und deckt die abendliche Vorschau ab. Aufgegeben zugunsten der
  Maintainer-Form.
- **Gemeinsames Fenster für „weniger bewässern"** (zunächst gewählt): JustChr will nur einen Satz
  im Issue, nicht in diesem Change.
- **Positionen behalten** (Open-Meteo-Index korrigieren, Tag 0 = morgen als Konstante): die
  Annahme bleibt unsichtbar und ist schon einmal still gebrochen.
- **Nur Stundenreihe, grob in 24-h-Blöcken auffüllen:** die Naht liegt um den Zeitzonenversatz
  daneben, Open-Meteo und Panel bleiben falsch.

## Design

### PR 1: Tageseinträge tragen ihr Datum

- Zwei neue Konstanten nach dem Vorbild von `RETRIEVED_AT = "retrieved"` und
  `OBSERVATION_TIME = "observed"` (`const.py:701-702`), **nicht** in der Liste der zuordenbaren
  Sensorfelder (`store.py:1405`): `FORECAST_DAY_START = "day_start"` und
  `FORECAST_DAY_END = "day_end"`, Beginn und Ende des Tages, den die Quelle meint, als
  zeitzonenbehaftete UTC-Zeitpunkte.
  Ein nacktes Datum reicht nicht, weil es den UTC-Tag von OWM als lokalen Tag ausgäbe.
- **OWM, Met Office:** UTC-Mitternacht bis zur nächsten UTC-Mitternacht.
- **Open-Meteo:** Ortsdatum abzüglich `utc_offset_seconds`; gefiltert wird „Tagesbeginn nach
  heute" statt Index 0. Beginnt damit wieder morgen.
  *(2026-09-14: Der Filter wurde als eigener PR #144 vorgezogen; PR 1 setzt darauf auf und
  ergänzt nur die Spanne.)*
- **Pirate Weather:** `time` ist ein absoluter Zeitpunkt; Ende = Beginn des nächsten Eintrags,
  beim letzten 24 Stunden später. **Annahme, ungemessen** (kein API-Schlüssel, keine Testdaten).
  *(Gebaut: Die Schleife lässt den letzten Block ohnehin aus, ein nächster Eintrag existiert
  also immer; ein „24 Stunden später“ wird nie gebraucht. Umstellungstage ergeben 23 oder 25 h.)*
- **Panel:** ~~zeigt das Ortsdatum des Tagesbeginns statt `heute + i + 1`.~~
  *(Gebaut 2026-09-14:)* zeigt das Ortsdatum der **Tagesmitte**, sofern Beginn und Ende gesetzt
  sind, sonst `heute + i + 1`. Das Ortsdatum des Beginns beschriftet UTC-Tage (OWM, Met Office)
  westlich von UTC einen Tag zu früh, das Ortsdatum des Endes östlich von UTC einen Tag zu spät.
  Begründung und Tests: Plan `2026-09-13-dated-daily-forecast.md`, Task 5.
- Verhalten ändert sich ~~nur für Open-Meteo-Nutzer~~ *(nach #144)* nur im Panel: OWM und
  Met Office werden richtig beschriftet, wenn HA-Ortsdatum und UTC-Datum auseinanderliegen.
  Frost-Wächter, Gewichtung, PyETO-Vorhersage und Regen-Wächter lesen weiter nach Position.

### PR 2: Regen-Wächter am Datum des Laufs

**Helfer**, neues Modul ohne Home-Assistant-Import:

- Eingaben: Ortsdaten des Fensters, Zeitzone, Auswertungszeitpunkt, Stundenreihe direkt vom Client,
  datierte Tageseinträge.
- Je Datum das Intervall ab dem späteren von Auswertungszeitpunkt und Ortsmitternacht bis zur
  nächsten Ortsmitternacht. Zeitzone über `zoneinfo`, Umstellungstage haben 23 oder 25 Stunden.
- Stundenreihe: jede Rate gilt für das Intervall, das an ihrem Zeitstempel endet; integriert wird
  die Überlappung mit dem Zielintervall. Die Intervalllänge ist der Abstand zum vorigen
  Zeitstempel; beim ersten Messwert der Abstand zum nächsten (OWM also drei Stunden).
  Das Ende der Stundenreihe ist ihr letzter Zeitstempel.
- Hinter dem Ende der Stundenreihe zählen Tageseinträge anteilig nach Überlappung ihres Intervalls.
- Ausgabe: Millimeter und ob das Fenster vollständig abgedeckt war.

**Datenfluss:**

- `async_evaluate_skip_conditions` erhält einen optionalen Laufbeginn und reicht ihn an
  `_eval_precipitation`. Laufdatum = Ortsdatum des Laufbeginns, ohne Angabe jetzt.
- Start (`_check_skip_conditions`): jetzt. Vorschau (`_projected_skip`): geplanter Start.
  Dashboard-Ausblick: nächster Bewässerungslauf aus `async_get_upcoming_runs` (die beiden Aufrufe
  tauschen die Reihenfolge); ist keiner geplant, gilt jetzt.
- Ergebnisform unverändert (`observed`, `threshold`); der Chip zeigt weiter „x mm (≥ y mm)".
- Docstring `skip_conditions.py:132` korrigiert; Hilfetext `lookahead_help` in allen acht Sprachen.

**Annahme zum Laufdatum:** OWM, Met Office und Pirate Weather sagen für vergangene Stunden nichts
vorher. Beim Start zählt vom Laufdatum nur der Rest ab dem Auswertungszeitpunkt. Regen, der vorher
schon fiel, gehört zur Messung, nicht zur Vorhersage.

### Fehlerfälle

- Keine Wetterquelle oder Abruf gescheitert: `available: false`, kein Übersprung (wie heute).
- Laufdatum nicht abgedeckt (beim Start ohne Stundenreihe, weil die Tagesprognose heute
  ausschließt): nicht verfügbar, kein Übersprung. Lieber gießen als streichen.
- Folgetage teilweise abgedeckt: es zählt, was da ist; unvollständige Abdeckung ins Debug-Log.
- Veralteter Cache um Mitternacht: Einträge fallen über ihr Ende heraus, unabhängig vom
  Parse-Zeitpunkt. OWMs `utcnow().date()` erreicht den Wächter nicht mehr.
- Bekannte Unschärfen, im Code benannt: Pirate Weather kann die Stunde um eins versetzen; Met
  Office liefert für einen angeschnittenen letzten Tag eine unvollständige Summe; Open-Meteo
  liefert nur einen `utc_offset_seconds`, an einem Umstellungstag im Fenster liegt dessen
  Tagesbeginn also eine Stunde daneben.

## Prüfkriterien

**PR 1:** je Quelle tragen Einträge Beginn und Ende, erster Eintrag nach heute; Open-Meteo mit
gestern/heute/morgen in den Testdaten; Pirate-Weather-Tagesdaten (heute ohne Test); Panel zeigt das
mitgelieferte Datum.

**PR 2:** Helfer ohne HA (Rest des Tages, Dreistunden-Slot über Mitternacht, Auffüllen hinter der
Stundenreihe, 23- und 25-Stunden-Tag, UTC-Tageseintrag gegen Ortsdatum). Wächter am echten Fall:
2,15 mm am 13., Fenster 1, Schwelle 2 — am 12. um 06:00 **kein** Übersprung, am 13. um 06:00
**Übersprung** (Regressions-Pin). Abend-Fall: am 12. um 20:00 für den Lauf am 13. schaut er auf
den 13. Vorschau reicht den geplanten Start durch. Paritätsprüfung der acht Sprachen. Jede
Zusicherung per Mutation als beißend nachgewiesen.

## Bewusst außerhalb

- `live_estimate.py:1048` liest `forecast[0]` als heutigen Tageswert; bei drei Quellen ist das morgen.
- Live-Neuberechnung verwirft die Gewichtung bei Zonen ohne Flusssensor.
- Gewichtung unter `before_run` einen Tag daneben (ein Satz auf #137).
- Pirate Weather: `max + min / 2.0` statt `(max + min) / 2`; Weglassen des letzten Tages ohne
  Begründung (seit 2024-06-16, `6908d436`).
- Millimeterzahl im Verlaufseintrag (eigenes Feld nötig, JustChr: später).

## Außerhalb des Codes

- Eigenes Issue zum Backstop ohne Zuschlag samt +4,11-s-Versatz (von JustChr erbeten).
- Kommentar auf #137 zur Open-Meteo-Verschiebung und zum Satz über die Gewichtung.
- Beide Texte werden vor dem Absenden im Chat freigegeben.
