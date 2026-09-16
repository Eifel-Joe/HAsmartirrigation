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

## Nachtrag 2026-09-15: Planprüfung vor dem Bau von PR 2

Vor der Ausführung wurde der Plan gegen den Stand nach #144/#145 geprüft: sechs Leser, jeder schwere
Befund von einem zweiten Agenten gegengeprüft, keiner widerlegt. Was sich am Design ändert:

- **Lücken in der Stundenreihe.** Open-Meteo und Pirate Weather lassen Zeilen ohne Wert weg. Ein
  Messwert gilt höchstens für einen Takt der Reihe (kleinster Abstand), längere Abstände sind Löcher
  und zählen als nicht abgedeckt. Ohne diese Grenze wurden aus 2 mm nachgerechnet 11 bis 14 mm.
- **Tageseinträge nur hinter der Reihe.** Ein Eintrag füllt nur auf, wenn seine Spanne erst NACH dem
  letzten Zeitstempel der Reihe beginnt. Gleichheit reicht nicht: bei einem Abruf zwischen 00Z und
  03Z ist OWMs letzter Slot 00Z gestempelt und landet im neuen Tag, sein Regen fiel aber in den drei
  Stunden davor (Probelauf 2026-09-15). OWM baut Tage aus derselben Dreistundenliste; der letzte
  Tag enthält nur die Werte bis zum Ende der Reihe, beansprucht aber den ganzen Tag, was doppelt zählte
  und „vollständig“ meldete. Das Unterzählen danach geht Richtung gießen. Die Spanne im Client bleibt
  der ganze Tag (das Panel beschriftet nach ihrer Mitte).
- **Gescheiterter Abruf.** Alle Clients liefern dann keine Tagesliste, die Stundenreihe liest aber
  weiter das letzte gute Dokument. Ohne Tagesliste entscheidet der Wächter nicht (wie bisher).
- **Vergangenes Laufdatum** (Vorschau eines schon begonnenen Laufs) gilt als nicht abgedeckt.
- **Met Office** zog das stündliche Dokument vor, das nur `get_data` auffrischt; der Wächter läuft
  vor `get_data`. Beide Stunden-Accessoren nehmen jetzt das Dreistundendokument, wenn es mehr als eine
  Cache-Lebensdauer später abgerufen wurde (User: eigener Commit in PR 2; heilt `live_estimate` mit).
- **Geteilter Spannen-Leser `day_span`** für Panel und Wächter. Die Regeln bleiben verschieden: Panel
  = Ortsdatum der Tagesmitte, Wächter = Überlappung (von JustChr freigegeben). Das offene „geteilter
  Helfer“ aus der Sitzung vom 14.09. ist damit beantwortet.
- **Abendläufe** (User: bauen, offenlegen). Mit Fenster 1 sieht ein Lauf um 21:00 nur die restlichen
  drei Stunden seines Datums. Folgt wörtlich der Form „Datum des Laufs“, per Test festgenagelt, im
  PR und auf #137 benannt, im Hilfetext erwähnt.
- **Hilfetext je Modus** (User). „Weniger bewässern“ nutzt dieselbe Einstellung, zählt aber weiter ab
  dem Tag nach der Berechnung. `lookahead_help` wird `{skip, water_less}` in acht Sprachen, das Panel
  wählt nach Modus; `docs/configuration-when-to-water.md` ebenso.
- **Log.** Ist das Laufdatum beim Dispatch nicht abgedeckt, schreibt der Wächter INFO statt DEBUG.
  Den Dispatch erkennt er daran, dass kein Laufbeginn genannt ist; Ausblick und Projektion nennen
  deshalb immer einen Zeitpunkt, auch ohne geplanten Lauf (sonst INFO bei jedem Dashboard-Refresh).
- **Tests.** Die Testumgebung setzt über das autouse-Fixture US/Pacific; die Wächter-Tests stellen den
  Live-Fall in Europe/Berlin nach und prüfen mit Regen in der ersten Ortsstunde, dass HAs Zone
  entscheidet. `tests/test_init.py::TestPrecipitationLookAhead` hielt „1 = morgen“ fest und wird auf
  das Laufdatum umgeschrieben.

- **Zeitzone HA-Prod** per MCP geprüft (2026-09-15): `Europe/Berlin`. Die Wächter-Tests stellen den
  Fall in dieser Zone nach.
- **Reichweite Met Office** (Korrektur zu Befund 6 oben): die Stundenreihe reicht 48 h ab dem letzten
  `get_data`, nicht ab jetzt. Mit PR 2 greift das Dreistundendokument, wenn das stündliche mehr als
  eine Cache-Lebensdauer älter ist.
- **Chip gegen Panel:** Die Millimeterzahl des Wächters ist nicht die Summe der Panel-Zeilen (Stundenreihe
  zuerst, Ortstage, vergangene Stunden abgeschnitten). Steht in `docs/configuration-weather-location.md`
  und im PR-Text, nicht im Hilfetext.
- **Sprachdateien und Browser-Cache:** Nicht-englische Kataloge werden nur über `VERSION` neu geladen.
  Für einen Live-Blick auf den deutschen Text vor einem Release: Refresh-Drill oder Versionssprung.

Weitere bekannte Unschärfen, im Modul-Docstring benannt: `day_projection.forecast_rain_mm` behandelt
den ersten Messwert strenger (lehnt ab, wenn die Reihe nach der Spanne beginnt); Open-Meteos einzelner
Offset gilt auch für die Stundenreihe. Ungeprüft: wo die Reihen von OWM und Met Office relativ zur
Abrufzeit beginnen. Beginnt eine zu spät, entscheidet der Wächter nicht, und es wird gegossen.

## Nachtrag 2026-09-15: Umsetzung und Schlussprüfung

Umgesetzt auf `fix/rain-guard-run-date`, acht Commits auf #145. Jeder Task lief mit Spec- und
Qualitätsprüfung, danach eine Schlussprüfung über den ganzen Branch (sechs Blickwinkel, jeder Befund
von zwei Gegenprüfern). Abweichungen vom Plan:

- **Entscheidung auf dem gerundeten Wert.** `observed = round(mm, 2)`, `would_skip = observed >= threshold`.
  Die sekundenweise Integration ergab für 10 h × 0,2 mm 1,9999999999999998: Chip „2,0 von 2,0 mm“, trotzdem
  bewässert. Kein Epsilon (Größe wäre geraten, Chip könnte weiter widersprechen).
- **Ausblick überspringt laufende Läufe.** `async_get_upcoming_runs` hält einen am Ende verankerten Lauf,
  der noch bewässert, auf seinem vergangenen Start. Nach Mitternacht fiele damit das ganze Laufdatum als
  vergangen weg, der Chip zeigte „nicht verfügbar“. `_next_irrigate_run_utc(…, not_before=now)` nur im
  Ausblick; die Tage-zwischen-Projektion bleibt unverändert.
- **Met-Office-Toleranz auf drei Stunden gedeckelt** (User): `min(Cache-Lebensdauer, 3 h)`. Bei Tages- oder
  Zweitages-Update gewann sonst ein bis 24/48 h älteres Stundendokument, dessen 48-h-Reihe vor dem
  Laufdatum endet, obwohl das frische Dreistundendokument den Tag abdeckt. Drei Stunden = Takt des
  gröberen Produkts; beim stündlichen Update ändert sich nichts.
- **48-h-Reichweite nur benannt** (User): Pirate Weather ohne `extend=hourly` und das Met-Office-
  Stundendokument. Der Tageseintrag des Tages, in dem die Reihe endet, beginnt vor ihrem Ende und fällt
  weg. Am Laufdatum geprüft verliert ein Fenster ab drei Tagen den Großteil von Tag 3, eine Vorschau am
  Vorabend ein paar Stunden von Tag 2. Richtung gießen. `extend=hourly` als möglicher Folge-PR.
- **„reaches or exceeds“** in `docs/configuration-when-to-water.md` und `general_precipitation_threshold`
  (acht Sprachen, Pytest-Pin): verglichen wurde schon immer mit `>=`, die Rundung macht Gleichheit
  erreichbar. Der Schlüssel wird im Panel derzeit nicht gerendert.
- **Pirate-Weather-Tages-`time`** im Client und im Modul-Docstring als „aus der API-Doku, nicht gemessen“
  (Bitte von JustChr auf #137, war in #145 nur im PR-Text).
- **Zusätzliche Pins** über den Plan hinaus: negative Rate und NaN getrennt, leere Intervallliste,
  Ein-Messwert-Takt, Teilfenster entscheidet, DEBUG in Vorschauen, Dispatch nennt keinen Start, exakte
  Jetzt-Zeitpunkte, Met-Office-Grenzen (Deckel, `>`, `cache_seconds`, fehlende Zeitstempel).
- **Geprüft statt „ungeprüft“** (siehe oben): OWM ist am Dispatch mit frischem Cache abgedeckt (der erste
  Messwert reicht einen Takt zurück); Met Office mit stündlichem Update ebenso; nach einem Neustart füllt
  `get_forecast_data` bei allen vier Clients das Dokument, das der Stunden-Accessor liest.
- **In der Schlussprüfung verworfen:** gerundeter Wert gegen ungerundete Zoll-Schwelle (≤ 0,005 mm),
  überlappende Tageseinträge (kein Client erzeugt sie; im Docstring benannt), ein Stempel neben dem Raster
  (freigegebene Regel, Richtung gießen), 1-s-Toleranz in der letzten Sekunde des Tages (0 mm).
- **Belege am Endstand:** Suite 7 failed / 2906 → 2976 passed / 320 errors, FAILED-Namen identisch
  (+70 Items); vitest 614 → 616; `npm run build` reproduziert dist; black/ruff grün.

## Außerhalb des Codes

- Eigenes Issue zum Backstop ohne Zuschlag samt +4,11-s-Versatz (von JustChr erbeten).
- Kommentar auf #137 zur Open-Meteo-Verschiebung und zum Satz über die Gewichtung.
- Beide Texte werden vor dem Absenden im Chat freigegeben.

## Nachtrag 2026-09-16: Umbau auf ein rollierendes 24-Stunden-Fenster

JustChr hat auf #146 (zwei Kommentare, 2026-09-15) die Form geändert, nachdem der
PR-Text die Folge für Abendläufe offengelegt hatte. Sein Satz dazu: „It changed the
decision."

### E8 — Das Fenster wird rollierend

**Fenster = ab Laufstart `precipitation_forecast_days` × 24 Stunden**, in absoluter
UTC-Arithmetik, statt Ortskalendertagen.

**Seine Begründung, nicht unsere:** Mit Kalendertagen wechselt jede bestehende
Installation, die abends bewässert, beim Update still von „sieht morgen" auf „sieht
die letzten Stunden von heute", und nichts sagt ihr, die Einstellung zu ändern.
Genau solche stillen Wechsel vermeidet der Fork. Die Bedeutung der Einstellung
bleibt damit auch für Abendläufe grob erhalten (1 ≈ ein Tag Vorausschau), was die
Kalendertagform nur für Morgenläufe leistete.

**Folgen, die damit gewollt sind:**

- Der Morgenfall aus #137 bleibt wörtlich erhalten (Sa. trocken → kein Übersprung,
  So. 2,15 mm → Übersprung). JustChr: „Please keep that test."
- Ein Abendlauf um 21:00 mit Fenster 1 sieht wieder den nächsten Morgen. Der Test
  `test_an_evening_run_with_a_one_day_window_sees_only_the_rest_of_its_day` kehrt
  sich um.
- Eine Umstellungsnacht hat wieder 24 echte Stunden; HAs Zone zieht keine Grenze
  mehr. Die drei DST-Tests kehren sich um (25,0 → 24,0; 23,0 → 24,0; Abdeckung
  false → true).
- **Am Dispatch ist das rollierende Fenster eine echte Obermenge des
  Kalendertagfensters**, länger um genau die Ortstageszeit des Laufs. Es kann also
  Läufe streichen, die die Kalendertagform bewässert hätte — die Richtung, die weh
  tut. Das gehört in den PR-Text, nicht nur in einen Test.
- Zwei bewusst gegenläufige Tests (`…first_local_hour_is_not_on_the_day_before` und
  `…first_local_hour_counts_for_the_run_date`) verlieren ihre Aussage: sie hielten
  fest, dass HAs Zone die Grenze zieht. Sie werden durch das Gegenstück ersetzt —
  dass der Laufstart die Grenze zieht.

**Unverändert** (von ihm aufgezählt): Stundenreihe zuerst, Lücken als Löcher,
Tageseinträge nur wenn sie nach dem letzten Stempel der Reihe beginnen, Entscheidung
auf dem gerundeten Wert, „reaches or exceeds", die Met-Office-Dokumentregel, die
Gewichtung bleibt unangetastet, und das Durchreichen durch Dispatch, Projektion und
Ausblick.

### E9 — Die Zeitzone verlässt das Modul

Nach dem Umbau überlebt in `forecast_window.py` keine Nutzung der HA-Zone:
`tz` fällt aus `expected_rain` und `window_intervals`, `_local_midnight_utc` wird
gelöscht, und die einzige Übergabestelle in `skip_conditions.py` entfällt.
Die drei verbleibenden `.astimezone(_UTC)` normalisieren hereinkommende
zeitzonenbehaftete Werte (Tagesspanne, Auswertungszeitpunkt, Stundenstempel) und
bleiben. `day_span` rechnet ohnehin nur in UTC, der Panel-Pfad ist unberührt.

**Falle, gespiegelt statt beseitigt:** `run_start + timedelta(hours=24)` auf einem
`ZoneInfo`-behafteten Zeitpunkt ist Wanduhr-Arithmetik (Berlin 2026-10-25 00:00
plus ein Tag = 25 echte Stunden) — dieselbe Falle, vor der heute
`_local_midnight_utc` warnt. Der Produktionsaufrufer normalisiert bereits per
`dt_util.as_utc`; das Modul muss es trotzdem selbst tun, weil Tests direkt
hineinrufen.

### E10 — Abdeckung: „Laufdatum abgedeckt" wird „erste 24 Stunden abgedeckt"

Block 0 ist `[Laufstart, Laufstart + 24 h)`, am Auswertungszeitpunkt beschnitten wie
heute; „abgedeckt" heißt, dass dieser **Rest** lückenlos ist. Unabgedeckt heißt
weiterhin: der Wächter entscheidet nicht, INFO am Dispatch, DEBUG in Vorschauen.

Zwei Feinheiten, die beim Umschreiben kippen können:

- Das Idiom `bool(intervals) and intervals[0][0] == 0` ist das Einzige, was
  „Block 0 ist geschrumpft" von „Block 0 ist ganz weg" unterscheidet. Bei Fenster 1
  (der Voreinstellung) fängt `bool(intervals)` denselben Fall; ab Fenster 2 nicht
  mehr. Wird `window_intervals` zu einer schlichten `(start, end)`-Liste vereinfacht,
  entscheidet ein 25 Stunden alter Lauf über den Regen des Folgetags — #137, nur in
  Skip-Richtung. Bleibt als Pin.
- `_COVERAGE_TOLERANCE_SECONDS = 1.0` macht einen Rest unter einer Sekunde
  stillschweigend „abgedeckt" mit 0,0 mm. Unter dem rollierenden Fenster soll daraus
  „kein erster Block mehr da" werden.

### Messung 2026-09-16: JustChrs Abdeckungsfrage beantwortet

Er bat, seine Analyse („ein fast tagealtes Dokument lässt die ersten 24 h
unabgedeckt") per Test zu belegen oder zu widerlegen. Reichweite der Stundenreihe ab
dem Abruf F, zweimal unabhängig gegen das echte `_hourly_segments` nachgerechnet,
drei davon gegen die Live-API gemessen:

| Client | Reihe reicht | bricht bei Dokumentalter |
|---|---|---|
| Pirate Weather (ohne `extend`) | F + 46:20 h (**gemessen**) | > 23 h − Minuten der Abrufstunde |
| Pirate Weather (`extend=hourly`) | F + 166 h (**gemessen**) | — |
| Met Office stündlich | F + 47:20 h | > 24 h − m |
| Met Office dreistündlich | F + 167:20 h | — |
| OWM | F + 119:20 h | > 93 h |
| Open-Meteo | F + 158:20 h (**gemessen**) | > 119 h |

**Belegt, aber enger als angenommen.** Der Wächter ruft selbst zuerst
`get_forecast_data` auf, und bei OWM, Pirate Weather und Open-Meteo frischt genau
dieser Aufruf das Dokument auf, das der Stunden-Accessor danach liest. Bei der
ausgelieferten Voreinstellung (stündliches Update, `cache_seconds` 3599 s) ist das
Dokument beim Wächter unter einer Stunde alt: **im Standard kann der Fall am Dispatch
nicht eintreten.** Erreichbar ist er mit Tages-Intervall, mit einem
Stunden-Intervall ab 23, und über den vorbestehenden Fehler weiter unten.

Bei Met Office greift zusätzlich die Dokumentregel aus PR 2: liegt das stündliche
Dokument mehr als `min(Cache-Lebensdauer, 3 h)` hinter dem dreistündlichen, gewinnt
das dreistündliche mit 167 h Reichweite. Die Bedingung `ttl > 21 h − m` ist dafür
**notwendig, nicht hinreichend** — die Behauptung „ab 8 Stunden Intervall bricht
Met Office" wurde in der Gegenprüfung widerlegt.

**Zusätzlich gemessen** (räumt drei Annahmen dieser Spec ab):

- Der Tagesblock von Pirate Weather ist Ortsmitternacht: `2026-09-15T22:00Z` gleich
  `2026-09-16T00:00+02:00`, alle Spannen im Dokument exakt 86400 s. Die Formulierung
  „aus der API-Doku, nicht gemessen" kann für die Tagesspanne entfallen.
- `precipIntensity` in SI ist mm/h, und die Summe der Stundenwerte eines Ortstags ist
  **exakt** `precipAccumulation × 10` desselben Tags (2,50 mm und 6,40 mm an zwei
  Tagen). Die cm-nach-mm-Umrechnung im Client stimmt.
- Der erste Stundenstempel liegt auf der bereits angebrochenen Abrufstunde. Gelesen
  als „endet am Stempel" beschriebe der erste Eintrag eine vergangene Stunde. Das
  stützt die Dark-Sky-Konvention „Beginn" und damit den Verdacht, dass wir die Reihe
  eine Stunde zu früh lesen — Richtung: wir schneiden am Ende eine Stunde zu viel ab,
  melden „nicht abgedeckt" und gießen. Die sichere Richtung. Bleibt als benannte
  Unschärfe, der Docstring-Vorbehalt bleibt stehen.
- `extend=hourly` kostet 30 986 auf 85 602 Byte (Faktor 2,76) bei unveränderter
  Antwortzeit; der Tagesblock bleibt bei acht Einträgen.

### E11 — Beide Auswege werden gebaut (User, 2026-09-16)

- **Pirate Weather fragt `extend=hourly` an.** Beseitigt den Fall ganz und nebenbei
  das Dauer-DEBUG „covers only part of the N-day window", das bei Fenster ab 2 sonst
  zum Normalzustand würde (48 h Fenster gegen 46 bis 47 h Reichweite).
- **Met Office nimmt das dreistündliche Dokument, wenn die Stundenreihe vor dem
  Fensterende endet.** Rein interne Dokumentwahl, dieselbe Stelle wie die Regel aus
  PR 2.

Belegt auf dem Schlüssel des Users; andere Tarife ungetestet — das gehört in den
PR-Text.

### E12 — JustChrs Real-Client-Testdatei wird umgeformt übernommen (User)

Alle sechs importierten Helfer existieren unverändert, alle vier handgebauten
Dokumente parsen gegen ihren Client, und alle neun Fälle halten auch unter dem
rollierenden Fenster (durchgerechnet). Zwei Änderungen: der Pirate-Weather-Fall wird
aus der **aufgezeichneten echten Antwort** gespeist statt aus einem Modell, und das
modulübergreifend importierte Fixture `berlin` wird vermieden — dafür gibt es in
dieser Suite keinen Präzedenzfall.

### Verworfen (mit Beleg)

- **Anteiliges Auffüllen aus dem Tageseintrag**, auch die „Rest"-Variante
  (Tagessumme minus das, was die Reihe innerhalb der Spanne schon integriert hat):
  bricht den angepinnten Regressionstest
  `test_owm_s_last_day_starting_at_the_series_end_is_not_counted_again`. Dessen
  letztes Reihensegment liegt AUSSERHALB der Spanne des Tageseintrags, der Rest ist
  also die vollen 3 mm und ergäbe über die ganze Spanne verteilt 6,0 mm, wo der Test
  3,0 festnagelt. Die Doppelzählung entsteht durch einen **falsch datierten Slot**,
  nicht durch Überlappung — eine Rest-Rechnung kann sie nicht sehen.
- **Toleranz auf der Abdeckung** („entscheide, wenn die ersten 24 h bis auf X
  abgedeckt sind"): die Lücke ist kein kleiner Rand, sondern ein Band (siehe unten),
  und die Größe von X wäre geraten — dieselbe Begründung, mit der PR 2 schon ein
  Epsilon unter der Schwelle abgelehnt hat.

### Vorbestehende Befunde, NICHT Teil dieses PR

- **Die Abdeckung ist nicht monoton im Alter des Dokuments.** Mit dem echten Modul
  gemessen, Vorschaufenster `[14. 00:00Z, 15. 00:00Z)`, Tageseintrag 5 mm: Reihe
  endet 13. 23:00Z, dann abgedeckt mit 5,00 mm. Reihe endet **eine Stunde später**,
  14. 00:00Z, dann unabgedeckt mit 0,00 mm. Ursache ist die Regel „Tageseintrag nur,
  wenn seine Spanne NACH dem Reihenende beginnt": eine Reihe, die ins Fenster
  hineinragt, disqualifiziert den ganzen Tageseintrag. Das gilt genauso unter
  Kalendertagen — der Umbau verschärft es nur, weil Block 0 am Dispatch über zwei
  Datumsgrenzen geht. Richtung: „nicht entscheiden", also gießen.
- **Auto-Update abschalten setzt `cache_seconds` nicht zurück** (Auto-Update-Zweig
  in `__init__.py`; nur der Auto-*Calc*-Zweig tut es). Wer „täglich" einstellt und
  dann Auto-Update abschaltet, behält ttl gleich 86399 s auf dem lebenden Client,
  während nichts mehr turnusmäßig abruft — der schlechteste Fall für die
  Abdeckungsfrage überhaupt.
- **`day_projection.forecast_rain_mm`** liest dieselben Dokumente mit einer zweiten,
  strengeren Reichweitenregel. Deren Spanne ist „jetzt bis zum nächsten
  Entscheidungspunkt", der Umbau hebt ihre Anforderung also nicht an.
