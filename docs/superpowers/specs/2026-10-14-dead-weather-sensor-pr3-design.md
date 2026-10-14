# Stummer Wettersensor, PR 3: der Schnitt im Stundenpfad und in der Live-Schätzung

Detail-Design für `Eifel-Joe#8`, Teil 3 der Aufteilung aus `JustChr#188` („(3) the hourly path and live estimate“).
**Ergänzt** die Spec `2026-10-03-dead-weather-sensor-design.md` (Revision 3, im Folgenden „Rev. 3“) und die Detail-Spec
`2026-10-11-dead-weather-sensor-pr2-design.md` („PR-2-Spec“, mit Nachtrag E1–E4). Sie entscheidet, was dort für PR 3
offen ist: die 23 Fragen aus §4 der Faktensammlung `D:\Entwicklung\HASI\issue8-pr3-work\context-2026-10-14.md`. Alles,
was hier nicht steht, gilt aus Rev. 3 und der PR-2-Spec.

Basis: der PR-2-Kopf `6fa424e8` (Branch `feat/pause-silent-weather-sensor`, offen als `JustChr#197`) = `upstream/master`
`6a40e083` + 18 PR-2-Commits. Zeilenangaben beziehen sich auf diesen Commit und auf `custom_components/irrigation_plus/`,
sofern nicht anders angegeben; am 2026-10-14 per `grep -n` auf einer Lese-Kopie bestätigt
(`D:\Entwicklung\HASI\issue8-pr3-work\src\`).

**Status: vom User freigegeben am 2026-10-14.** Die Entscheidungen G1–G12 und die Abschnitte 1–5 hat der User im Chat
einzeln freigegeben, danach die schriftliche Fassung („Spec passt“). Nächster Schritt: Plan (`superpowers:writing-plans`).

## Ziel in einem Satz

Was nicht gemessen ist, wird nicht gebucht (R5) — für Sensorgruppen auf *pausieren* jetzt in **jeder** Rechenform:
Commit in der Tagesform (PR 2) und in der Stundenform, nachgespielte Bilanz (Teilschritte) und Live-Schätzung. Gruppen
auf *behalten* rechnen, erklären und schätzen byte-identisch wie heute (R4). Nach PR 3 bleibt keiner der Zwischenstände
aus Rev. 3 (*Zwischenstände*) und der PR-2-Spec.

Schreibweise wie in der PR-2-Spec: Fenster `[ws, we)`, gültige Zeit eines Feldes `V` = Fenster minus seine Sperren,
`s` = Buchungsanteil. Neu: **Pflichtmenge** einer Rechenform = die Felder, ohne die sie nicht rechnen kann.

## Entscheidungen (User, 2026-10-14)

| # | Frage (§4 der Sammlung) | Entscheidung | Verworfen |
|---|---|---|---|
| G1 | Basis, solange `JustChr#197` offen ist (20) | **Stapeln:** Spec, Plan und Bau jetzt auf `6fa424e8`; der PR an JustChr erst nach dem Merge von #197, umgesetzt auf den gemergten master; Änderungen aus dem Review von PR 2 werden nachgezogen | Spec + Plan jetzt, Bau nach dem Merge; nur Spec jetzt |
| G2 | Ein PR oder zwei (—) | **Ein PR** wie vereinbart, Spec und Plan in **Teil A (Commit)** und **Teil B (Live)**, getrennte Commit-Gruppen, PR-Text mit zwei Abschnitten | Zwei PRs (weicht von der vereinbarten Dreiteilung ab, neuer Zwischenstand); erst nur Teil A |
| G3 | Teilweise gültige Stunde (1) | Jedes Feld nur über **seine eigene gültige Zeit** der Stunde gemittelt (nie in eine Sperre hinein gehalten; nach der Sperre gilt der Wert von davor, F2) × Anteil der **Schnittmenge** der Pflichtfelder; gesperrte Stunden bleiben als Zeile mit ET 0 | Mittel wie heute × Anteil (rechnet im gültigen Teil mit dem eingefrorenen Wert); Mittel über die Schnittmenge (eigenes Integral je Stunde, Live-Pfad im Minutentakt); ganz-oder-gar-nicht ab Schwelle (F3 verwarf den Mindestanteil) |
| G4 | Pflichtfeld der Stundenform ganzes Fenster gesperrt (2, 3) | **Stundenform bleibt:** Fehlt ein Feld *wegen einer Sperre*, ergeben sich Zeilen mit Gewicht 0 (ET 0, Fenster verbraucht); fehlt es aus anderem Grund, der heutige Weg zur Tagesform (Logik F1). **Pflichtmenge je Form:** Stundenform Temperatur, Feuchte, Wind, Sonne; Tagesform wie PR 2 | Rückfall auf die Tagesform hinnehmen (bucht bei stummer Sonne den vollen geschätzten Tag); Rückfall mit Anteil aus beiden Mengen |
| G5 | Sonne nach einer Sperre, Klarheitsquote (5) | Proben **in** der Sperre zählen nicht, weder als Messung der Stunde noch als Quelle einer Quote; **nach** der Sperre gilt die Quote von davor bis zur nächsten Probe (F2 in Quoten) | Quote überquert nie eine Sperre (Nachtstunden nach einer Abend-Sperre zählten nicht) |
| G6 | Lage der ET in den Teilschritten (7) | **Sonnengewichte nur aus gültiger Zeit:** gesperrte Teile Gewicht 0, gültige nach Sonne, ganz dunkle Stunde wie heute nach Zeit. Reine Lage-Änderung, die Summe bleibt | Rev. 3 wörtlich (gesperrte Teile nach Zeit: legt ET in ungebuchte Zeit); nichts ändern |
| G7 | Abgleich Aggregat/Teilschritte bei gesperrter Regenrate (8) | Die Zuwächse einer Regenrate (`riemannsum`) zählen **dieselben gültigen Zeitanteile** wie das Aggregat; der Abgleich hält. Keine neue WARNING | Nur WARNING bei Abweichung; beides |
| G8 | Bedeutung von „N % des Zeitraums“ in der Stundenform (10) | **Zeitanteil** = `valid_share` mit der Pflichtmenge der Stundenform; ein Begriff für beide Formen, keine neuen Texte | Mengenanteil (müsste gesperrte Stunden mit eingefrorenen Werten rechnen; neuer Wortlaut in 8 Sprachen) |
| G9 | Live: Sperre nimmt der Sensorquelle das ganze Fenster (14, 15) | **Die Sensorquelle meldet ET 0, die Quellenkette rutscht wegen einer Sperre nie zum Wetterdienst.** `daily_mirror` bekommt das geschnittene Aggregat × Anteil wie der Commit und gibt bei Anteil 0 → 0 statt `None` | Kette laufen lassen (Rückfall auf den Wetterdienst, gegen Entscheidung 1); keine Schätzung mit neuem Grund |
| G10 | Hochrechnung bis zum Entscheidungspunkt bei offener Sperre (16) | **Vorschau wie heute, aber aus dem geschnittenen Aggregat;** keine Annahme über die Rückkehr. Ohne Tageswert entfällt sie wie heute | Sperre bleibt offen (Rest-ET 0); alles wie heute (toter Wert formt die Vorschau) |
| G11 | Cache und Auffrischung der Live-Schätzung (17) | **Ausfall-Einträge** der Gruppe (Beginn, Ende, Felder) und `on_silent_sensor` in den **Schlüssel** von `_HourlyCarry`; die Liveness-Prüfung stößt beim Öffnen und Schließen `async_refresh_zone_estimates_throttled` an | Ausdrückliches Verwerfen bei jedem Auslöser; nur der Schlüssel ohne Neuberechnung |
| G12 | Bauweg (6, 12) | **Freie Funktion** für die Sperren, einmal je Commit bzw. Live-Neuberechnung, durchgereicht als `blocked=None`; **ein Helfer** liefert je gesperrtem Feld behaltene Proben und gültige Abschnitte; ungesperrte Felder laufen durch den heutigen Code | Puffer vorab maskieren (hält den Wert durch die Sperre, gegen G3/G5); jede Lese-Stelle rechnet selbst (sechs „jetzt“) |

Ohne eigene Frage, weil Rev. 3 sie schon festlegt: **Druck** (Rev. 3 Z. 283-284) und **`_latest_temperature`**
(Rev. 3 Z. 290-291), siehe Abschnitte 2 und 3.

### Präzisierungen gegenüber Rev. 3

- Rev. 3 Z. 285 („die gehaltene Klarheitsquote überbrückt keine Sperre“) heißt nach G5: In der Sperre zählt nichts; nach
  der Sperre gilt die Quote von davor.
- Rev. 3 Z. 286-287 („in gesperrten Stunden nach Zeit statt nach Sonne verteilen, vorhandener Rückfall“) wird durch G6
  ersetzt: Der Rückfall nach Zeit greift bei Lücken nicht, weil die Sonnentabelle flach hält (`weather_aggregate.py:765`);
  gesperrte Teile bekommen das Gewicht 0.
- Rev. 3 Z. 289 nennt einen Live-Aufruf; es sind vier Leser plus die Hochrechnung (Abschnitt 3).
- Rev. 3 Z. 154 (Entscheidung 8) begründete das Gate mit dem Abgleich; G7 beseitigt den Grund.

## 1. Rahmen

- **Unverändert:** *behalten* ist byte-identisch in Ergebnis, Stundenzeilen, Teilschritten, Erklärung, Live-Schätzung und
  Logs. Regenzähler (`delta`) werden nie geschnitten (`cuts_field`, `sensor_liveness.py:186`). Nur Sensorfelder. Kein
  neues Store-Feld: `on_silent_sensor` und `sensor_outages` kommen aus PR 1/2; der Übertrag `_HourlyCarry` liegt nur im
  Speicher.
- **Einheit:** Wegfall des Gates, Anteil im Stundenzweig und die Text-Anpassungen landen im **selben Commit**. Ein Stand
  „Gate weg, Stundenzweig ungeschnitten“ gibt eine falsche Erklärung aus („für N % gebucht“ bei voll gebuchter ET,
  `calculation.py:1349-1358`, `:1539-1540`) und darf auch zwischen zwei Commits des Branches nicht entstehen.
- **Rückbau** auf einen PR-2-Build: Pausierende Gruppen mit Stundenrechnung rechnen wieder ungeschnitten, der Hinweis
  nennt wieder den *behalten*-Text; kein Datenverlust.

## 2. Teil A: Commit

### 2.1 Sperren ohne Gate (G12)

- Neue freie Funktion `zone_blocked_spans(store, zone, start, end)` in **`sensor_liveness.py`** neben `blocked_spans`
  (`:201`); dort liegen alle Zutaten (`outages_of` `:169`, `group_pauses` `:177`, `cuts_field` `:186`, `coerce_stamp`).
  Frei, weil das Live-Mixin in Tests allein läuft und ein Querruf ins Rechen-Mixin dort vom pauschalen `except` in
  `_intraday_for_zone` als `REASON_FAILED` verschluckt würde (`live_estimate.py:561-571`). Inhalt = heutige Methode
  `_blocked_spans_for_zone` (`calculation.py:420-453`) **ohne** die Bedingung `hourly_calculation_enabled` (`:439-440`),
  mit ausdrücklichem Fensteranfang: `None` bei *behalten*, ohne Fensteranfang, bei leerem Fenster oder ohne verbleibende
  Sperre; sonst `blocked_spans(outages_of(mapping), start, end)` gefiltert mit `cuts_field`.
- `_blocked_spans_for_zone(zone, *, now)` **bleibt** als dünne Hülle des Commits (`start` = Wasserzeichen, `end` = `now`)
  und ruft die Funktion; ihre Aufrufstelle in `async_calculate_zone` (`:674`) und die PR-2-Tests, die sie direkt rufen
  (`tests/test_silent_sensor_commit.py:103`, `:143`), bleiben stehen — das hält den Stapel auf #197 klein.
- Transport wie PR 2, erweitert: `blocked=` an `_hourly_et_for_zone` (`:945`) → `hourly_eto_priced`
  (`et_estimate.py:148`) → `build_hourly_rows` (`weather_aggregate.py:1007`), und an `_substeps_for_zone` (`:1051`) →
  `build_substeps` (`weather_aggregate.py:1211`). Alle neuen Parameter optional mit Standard `None`; ohne Sperre läuft
  kein neuer Code.

### 2.2 Der Helfer „gültige Proben je Feld“ (G12)

- Direkt nach der Aufteilung nach Feld (`_group_by_sensor`, `weather_aggregate.py:184`; beide Reduzierer rufen sie gleich
  nach `_effective_series`) liefert ein Helfer je **gesperrtem** Feld die behaltenen Proben (Zeilen in einer Sperre fallen
  weg; die Randzeile bleibt als Wert, zählt als Probe nur, wenn `ws` in `V` liegt — wie PR-2-Spec §2) und die gültigen
  Abschnitte (`_valid_segments`, `:666`; Haltewert `_held`, `:684`).
- Felder ohne Eintrag in `blocked` gehen unverändert durch die heutigen Tabellen (`_hold_integral_table`, `:765`;
  `_hourly_mean`, `:875`) — byte-identisch, auch in der Fließkomma-Reihenfolge.
- Nicht in `_effective_series` (`:856`) schneiden: die Funktion kennt keine Felder, eine Poll-Zeile trägt gesperrte und
  ungesperrte Felder zugleich, und Regenzähler dürfen nie verlieren.

### 2.3 Stundenzeilen (G3, G4, G5, Druck)

- **Stundenmittel eines gesperrten Feldes** = ∫ Haltewert über (`V` ∩ Stunde) / |`V` ∩ Stunde|; der Haltewert springt nie in
  eine Sperre hinein; nach der Sperre gilt der Wert von davor (F2).
- **Gewicht der Stunde** = heutige Abdeckung (`coverage_h`, `weather_aggregate.py:1127-1142`; ET = `eto_hourly(…) ×
  coverage_h`, `et_estimate.py:131-144`) × |⋂ `V_p` ∩ Stunde| / |Stunde ∩ Fenster| über die Pflichtmenge der Stundenform
  `_HOURLY_ROW_REQUIRED` (`weather_aggregate.py:71-76`: Temperatur, Feuchte, Wind, Sonne). Ist die Schnittmenge leer, bleibt
  die Zeile mit Gewicht 0 stehen (ET 0) — **nie** `None` aus den Stundenmitteln (`:1151-1153` verwirft sonst die ganze
  Stundenform) und keine fehlende Stunde in `hourly_et` (`:1189-1193` ließe die Teilschritte still auf Einmal-Buchung
  fallen). Eine Stunde mit Gewicht 0 trägt ET 0 **ohne** ET-Rechnung: Kein erfundener oder gehaltener Wert geht in
  `eto_hourly` ein, auch dann nicht, wenn ein Feld im ganzen Fenster keine behaltene Probe hat (G4). Wie solche Zeilen ihre
  Messfelder darstellen (leer oder mit Haltewert), legt der Plan nach den Lesern der Zeilen fest; die ET-Summe und
  `hourly_et` hängen nicht davon ab.
- **Pflichtfeld wegen Sperre ganz ohne Probe** (G4): Der Zeilenbau unterscheidet „nie gelesen“ (heutiges `None` bei
  `:1090-1095` → Tagesform wie heute) von „gesperrt“ (Zeilen mit Gewicht 0, `hourly_eto_priced` liefert `(0.0, {Stunde:
  0.0, …})`). Vorbild: F1 der PR-2-Spec.
- **Klarheitsquote** (`_ratio_hold_solar`, `:909-1004`; G5): Sonnen-Proben in einer Sperre zählen weder als „gelesene
  Stunde“ (`newest`) noch als Quelle einer Quote (`measured`). Stunden nach der Sperre ohne neue Probe bekommen die Quote
  von davor. Stunden in der Sperre dürfen gefüllt werden; sie zählen wegen Gewicht 0 nicht.
- **Druck** (Rev. 3): Mittel nur über seine gültige Zeit; eine Stunde ohne gültigen Druck trägt kein `pressure_kpa`
  (`:1161-1162`), das ET-Modul nimmt den Höhendruck wie heute. Druck ist kein Pflichtfeld der Stundenform.
- **Fensterkanten, Zeitumstellung, `last_entry`-Probe** (`:1096-1101`): wie heute, nur auf die behaltenen Proben angewandt.

### 2.4 Anteil und Erklärung (G4, G8)

- **Pflichtmenge je Form:** `_REQUIRED_SENSOR_FIELDS` (`calculation.py:65-82`) wird nach Rechenform geschlüsselt
  (PyETO-Tagesform wie PR 2: Taupunkt, Temperatur, Wind, Druck; PyETO-Stundenform: `_HOURLY_ROW_REQUIRED`; Passthrough:
  ET-Feld) und für die Live-Schätzung nutzbar (heute privat).
- **Stundenzweig** (`calculation.py:1349-1358`): Der Anteil steckt in den Zeilengewichten; `et_delta = -hourly_total × kc`
  bleibt ohne zweites Skalieren. `share` für die Erklärung = `valid_share(blocked, Stunden-Pflichtmenge, ws, we)` (G8). Der
  Tagesform-Ausdruck (`:1359-1365`) bleibt wie PR 2.
- **Welche Form lief,** steht erst nach `_hourly_et_for_zone` fest (`calculation.py:1293-1297`); der Anteil wird danach mit
  der passenden Menge bestimmt. `s = 0` in der Tagesform wie PR 2 (Modul nicht aufgerufen); in der Stundenform ergibt sich
  0 aus den Zeilen.
- **Erklärung:** die PR-2-Sätze `sensor-outage` und `sensor-outage-share` (`_silent_sensor_explanation`, `:1890`) an
  derselben Stelle (`:1539-1540`), jetzt auch im Stundenzweig; Satz 2 nennt den Zeitanteil, gehalten auf 1…99 % (E3).
  Kc-Satz unverändert (im Stundenzweig zeigt er den geschnittenen Wert, in der Tagesform wie PR 2 den ungeschnittenen
  Mittelwert — hingenommen). Keine neuen Texte.

### 2.5 Nachgespielte Bilanz (G6, G7)

- **Sonnengewichte** der Teilschritte (`build_substeps`, `:1320-1335`) aus der Sonnentabelle der **gültigen** Zeit:
  gesperrte Teile Gewicht 0, gültige nach Sonne; eine ganz dunkle Stunde wie heute nach Zeit innerhalb der Stunde
  (`_weights_from_hourly_et`, `:1196-1206`). Wirkt auf die Lage (Drainage, Deckel), nicht auf die Summe; gilt in beiden
  Formen (in der Tagesform bei eingeschalteter Stundenrechnung verteilt sie die mit `s` verkleinerte ET).
- **Regenzuwächse** (`_precip_increments`, `:803-834`): bei gesperrter Regenrate `(v0+v1)/2 × gültige Stunden des Paars`,
  dieselbe Rechnung wie `_riemann_over` (`:708-720`); Proben in einer Sperre fallen weg. Damit stimmt der Abgleich
  (`calculation.py:1091-1101`). Regenzähler unverändert.
- Sperrgrenzen werden keine zusätzlichen Schnittpunkte der Teilschritte (`_substep_boundaries`, `:835`).

### 2.6 Tagesform bei eingeschalteter Stundenrechnung, Aufzeichnungen

- Läuft bei eingeschalteter Stundenrechnung die Tagesform (geschätzte Sonne, `forecast_days > 0`, fehlende Koordinaten,
  Fenster über 168 h, ein nie gelesenes Pflichtfeld; `calculation.py:945-1040`), gilt der PR-2-Pfad vollständig; das Gate
  war das einzige Hindernis. Die Teiltag-Grenze (F3) gilt dort weiter.
- `_record_window_amplitude` (`:720`) und `_record_window_radiation` (`:774`) laufen in beiden Formen auf dem
  Tagesform-Aggregat; ihr PR-2-Ausschluss greift nach dem Wegfall des Gates ohne Codeänderung (`:743-744`, `:783-784`).

## 3. Teil B: Live-Schätzung

### 3.1 Sperren einmal je Neuberechnung (G12)

- `_intraday_for_zone` (`live_estimate.py:1305`) ruft `zone_blocked_spans(store, zone, anchor, now_local)` einmal; `anchor`
  ist der vorhandene `_window_anchor` (`:241-261`, max(`last_calculated`, Wasserzeichen)). Dieselben Sperren gehen an:
  - `_aggregate_live_window` (`:590`) → `aggregate_window(…, blocked=)`;
  - `_observed_precip_since_mm` (`:638`), das dafür das Live-`now` bekommt (heute ohne, Rückfall auf `local_naive_now()`);
  - `_buffer_hourly_et` (`:718`) → `hourly_eto_priced(…, blocked=)` (Methode `hourly_sensor`);
  - `_buffer_water_steps` (`:1147`) → `build_substeps(…, blocked=)`;
  - `_latest_temperature` (`:888`).
- `_carry_estimate_to` (`:1828`) bestimmt die Sperren einmal für sich mit demselben Anker und demselben `now`.

### 3.2 Quellenkette (G9)

- Reihenfolge heute (`:1387-1517`): `hourly_sensor` → `daily_mirror` → Stundenreihe des Wetterdienstes (`hourly`) →
  Prognose-Ersatz (`proxy`) → `REASON_NO_ET_SOURCE`.
- `hourly_sensor` liefert mit Teil A gesperrte Stunden mit ET 0 und bleibt die Quelle.
- `_daily_mirror_et` (`:1104`) bekommt das geschnittene Aggregat und multipliziert die Tagessumme mit dem Anteil der
  Tagesform-Pflichtmenge wie der Commit (`calculation.py:1359-1365`); bei Anteil 0 gibt sie **0** zurück statt `None`
  (heute `None`, wenn Min/Max-Temperatur fehlen, `live_estimate.py:1015-1016`). Fehlt ein Feld aus anderem Grund, bleibt
  der heutige Weg.
- Ergebnis: Die Kette verlässt die Sensorquelle nur aus anderen Gründen, **nie wegen einer Sperre**.

### 3.3 Hochrechnung, aktuelle Temperatur

- `_carry_estimate_to` (G10): `_aggregate_live_window(…, blocked=)` (`:1893`) und damit `_composed_day_et` (`:967`) aus dem
  geschnittenen Aggregat; Rest wie heute (`:1903-1944`). Ohne Tageswert entfällt die Hochrechnung wie heute
  (`carried_to_decision = False`).
- `_latest_temperature` (Rev. 3): Liegt `now` in einer Sperre der Temperatur, gilt `last_entry` nicht als aktuell → kein
  Anker → die Extreme kommen aus der Beobachtung (Stufe `observed`, `:944-963`).

### 3.4 Cache und Auffrischung (G11)

- `_HourlyCarry` (`:182-206`) bekommt im Schlüssel neben `anchor` die Ausfall-Einträge der Gruppe als unveränderliches
  Tupel (`entity_id`, `start`, `end`, `fields`) und `on_silent_sensor`. Es zählen die Einträge, nicht die zugeschnittenen
  Sperren (eine offene Sperre endet bei `now` und änderte den Schlüssel jede Minute). Öffnen, Schließen, Kürzen nach
  7 Tagen und ein Einstellungswechsel verwerfen den Übertrag damit von selbst.
- `async_check_sensor_liveness` (`sensor_liveness.py:465`) stößt nach dem Öffnen oder Schließen eines Ausfalls
  `async_refresh_zone_estimates_throttled` (`live_estimate.py:1772`) an. Heute frischt bei einer ganz stummen Station mit
  `continuousupdates` nichts auf (Auslöser: Commit, Pufferzeile `continuous_update.py:556`, Lauf, Poll).

### 3.5 Gleichlauf, Grenzen

- **Zielbild:** Nach dem Commit am Ende eines Ausfalls ist der Live-Eimer gleich dem gebuchten Eimer, für `hourly_sensor`
  und `daily_mirror`, weil dieselben Sperren durch denselben Zeilenbau laufen. Abweichungen nur aus der Erkennungs-Latenz
  (Prüftakt 5 min, `end` auf die Prüfperiode genau, D3) und ms-Splittern der Rückkehrzeiten (L1 aus PR 2).
- **Passthrough-Zonen:** Die Live-Schätzung hat für sie keine Sensor-ET (`_daily_form_applies`, `:795`, `:825-826`);
  geschnitten wird dort nur eine gesperrte Regenrate.
- Die Kommentare „exactly as `_aggregate_for_zone`“ (`:600-603`, `:627`) stimmen wieder; der PR-2-Zusatz „die
  Live-Schätzung schneidet noch nicht“ fällt weg.

## 4. Melden, Texte, Doku

- **Hinweis und Log:** `_group_cuts` (`sensor_liveness.py:585-595`) verliert die Bedingung `not
  hourly_calculation_enabled(...)`; Hinweis-Variante (`_stale_issue_key`, `:597-612`) und Schnitt-Text im WARNING
  (`:529-539`) hängen nur noch an *pausieren* und einem offenen Ausfall mit geschnittenem Feld (E1). Hinweistexte
  unverändert (sie nennen die Stundenrechnung nicht).
- **Neu-Synchronisieren:** Der Aufruf beim Umschalten der Stundenrechnung (`__init__.py:1246-1250`) entfällt samt Test;
  es bleiben Öffnen/Schließen, Einstellungs- und Zuordnungswechsel, Setup.
- **Panel-Hilfe** `panels.mappings.cards.mapping.on-silent-sensor.help`: der letzte Satz („Gilt nur, solange ‚Stündliche
  Verdunstung‘ (Experimentelle Funktionen) aus ist.“) wird in allen 8 Sprachen gestrichen, ohne neuen Text. `dist` neu
  bauen (2 von 4 Bundles enthalten den Satz), `git add -f`, Dateizahl prüfen.
- **Doku** `docs/configuration-sensor-groups.md`: Zeile 59 nennt die Pflichtfelder je Form (Tagesform: Temperatur,
  Taupunkt, Wind, Druck; Stundenform: Temperatur, Feuchte, Wind, Sonne) und „the calculation“ statt „the daily
  calculation“. Absatz Zeile 62 neu: ohne „nur ohne Stundenrechnung“ und ohne den Live-Zwischenstand; die Teiltag-Grenze
  bleibt, auf die Tagesform beschränkt; neu, dass die Stundenform Stunde für Stunde schneidet und der Prozentwert Zeit zählt
  (eine nachts gesperrte Sonne senkt ihn, kostet kaum Verdunstung). Fassung deutsch zur Freigabe mit dem Plan, dann
  englisch.
- **Code-Kommentare** mit „daily form“, „hourly calculation off“, „live estimate does not“: `sensor_liveness.py:11-14`,
  `:586-590`; `const.py:715-718`; `weather_aggregate.py:346-350`, `:609`; `calculation.py:420-432`; `live_estimate.py`
  (Z4 der Sammlung).

## Tests

RED vor GREEN je Verhalten; volle Suite mit Namensvergleich gegen eine **auf `6fa424e8` neu gemessene** Baseline; i18n-
Vollständigkeit; vitest; `dist` gleich Build; black + ruff.

- **Byte-Identität:** *behalten*, `blocked=None`, `blocked={}` und Sperren fremder Felder → Stundenzeilen (Dicts mit `==`),
  Teilschritte, Erklärung und Live-Ergebnis exakt wie ohne PR 3.
- **Teil A:** Stundenzeilen mit Sperre am Anfang, in der Mitte, am Ende einer Stunde, über eine ganze Stunde, über das ganze
  Fenster (G4, Gewicht 0, kein Wechsel zur Tagesform; „nie gelesen“ wechselt weiter); Wert nach der Sperre (F2);
  Klarheitsquote (G5: keine Quote aus der Sperre, Quote von davor danach); Druck (Höhendruck in Stunden ohne gültigen
  Druck); kein `None` aus den Stundenmitteln; Teilschritte laufen unter Sperre (Satz `water-balance-substepped`), Gewicht 0
  in gesperrten Teilen (G6); Abgleich mit gesperrter Regenrate (G7); Anteil und Satz im Stundenzweig (G8), ET mit und ohne
  Sperre gegen von Hand gerechnete Sollwerte; Tagesform-Rückfall unter Stundenrechnung schneidet wie PR 2;
  Aufzeichnungen im Stundenbetrieb; Hinweis-Variante und WARNING mit Stundenrechnung; kein Re-Sync mehr beim Umschalten.
  Die vier PR-2-Tests zum Zwischenstand werden umgedreht bzw. entfernt (`tests/test_silent_sensor_commit.py:124-128`,
  `:465-478`; `tests/test_sensor_liveness_coordinator.py:1010-1016`, `:1067-1087`).
- **Teil B:** Sperren einmal gerechnet, an allen Lesern angekommen (inkl. Niederschlag mit Live-`now`); Kette rutscht nicht
  zum Wetterdienst (G9); `daily_mirror` × Anteil, Anteil 0 → 0; Hochrechnung aus geschnittenem Aggregat (G10);
  `_latest_temperature`; Schlüssel des Übertrags verwirft bei Öffnen, Schließen, Einstellungswechsel (G11); Neuberechnung
  angestoßen; Live-Mixin allein ohne Querruf; **Gleichlauf** Live-Eimer = Commit-Eimer nach einem Ausfall für
  `hourly_sensor` und `daily_mirror` (Muster `tests/test_live_estimate_replayed_balance.py`, `approx`).
- **Testszenen:** Stempel in HAs Rahmen bauen oder `now=` übergeben (freezegun = UTC, `hass` = US/Pacific); Stundenform-
  Tests brauchen PyETO mit `_solrad_behavior="3"`, `forecast_days = 0` und Koordinaten (die PR-2-Hilfe `_module(...)` setzt
  das nicht).
- **Mutationen** auf: Gewicht 0 statt `None`, Zeilen in der Sperre fallen weg, Quote nicht aus der Sperre, Haltewert nicht
  in die Sperre, Abgleich-Zeitanteile, Pflichtmenge je Form, `daily_mirror` 0 statt `None`, Schlüssel des Übertrags,
  Auslöser der Neuberechnung, Wegfall des Gates, Wegfall des Re-Syncs.

## Ende-zu-Ende-Kriterium (HA-Test)

Aufbau: Stundenrechnung an, Live-Schätzung an, PyETO mit gemessener Sonne (`solrad_behavior = 3`), `forecast_days = 0`,
Koordinaten gesetzt. Eine pausierende Sensorgruppe aus YAML-MQTT-Geräten unter eigenem Topic-Präfix, ohne Discovery (der
Broker von HA-Test hängt an HA-Prod), mit Temperatur, Feuchte, Wind und Sonne. Die Geräte schweigen **tagsüber** 3,5 h,
kehren zurück, danach Commit der Zone. Vorher den Stand von Stundenrechnung und Live-Schätzung notieren.

Soll:

1. Während der Sperre zeigt der Hinweis die Pausier-Variante, obwohl die Stundenrechnung an ist.
2. Die Live-ET seit dem Anker wächst ab Beginn + 3 h nicht mehr (nur die Drainage bewegt den Eimer); Methode bleibt
   `hourly_sensor`, keine Wetterdienst-Stufe.
3. Die Erklärung nach dem Commit nennt Beginn + 3 h bis Ende und den Prozentwert, der **vorab** aus Wasserzeichen, `now`
   und dem Ausfall-Eintrag (Diagnostics `data.store.mappings[].sensor_outages`) gerechnet wurde; der Satz
   `water-balance-substepped` steht da.
4. Der Live-Eimer direkt nach dem Commit ist gleich dem gebuchten Eimer (Toleranz aus der Erkennungs-Latenz).
5. Dieselbe Lage auf *behalten*: kein Satz, Hinweis im PR-1-Text.

Danach Stundenrechnung und Live-Schätzung auf den notierten Stand. Das 60-min-Intervall und der Pirate-Schlüssel auf
HA-Test bleiben unberührt; die Zonen 0/1 kommen nie auf `service`.

## Lieferung

- Branch `feat/pause-silent-sensor-hourly-live` von `6fa424e8`, Worktree `D:\Entwicklung\HASI\issue8-pr3-work\wt`; Teil A
  und Teil B als getrennte Commit-Gruppen, jeder Commit grün.
- Ablauf: Pre-Release → Live-Test HA-Test → nach dem Merge von `JustChr#197` `rebase --onto` auf den gemergten master,
  neu belegt (Suite mit Namensvergleich, Mutationen) → PR an JustChr. Ändert das Review von #197 PR-2-Stellen, zieht PR 3
  nach.
- Kein Versionssprung im PR; `dist` neu bauen, `git add -f`, Dateizahl prüfen; Diff und Commit-Messages ohne eigene Bezüge
  (Memory `no-own-issue-refs-upstream`; Fork-Commit-Messages „upstream PR 197“); PR-Text deutsch zur Freigabe, dann
  englisch, mit zwei Abschnitten (Commit, Live).
- Archiv nach P1 jeweils nach Freigabe von Spec und Plan.
- production und HA-Prod nur auf Zuruf. Auf HA-Prod (Stundenrechnung und Live-Schätzung an, Gruppe „Greimerath“ auf
  *behalten*) ändert PR 3 nichts, bis der User die Gruppe umstellt — eine eigene Entscheidung außerhalb von PR 3.

## Ausdrücklich nicht in PR 3

- Dienst-Felder (`Eifel-Joe#74`), einstellbare Grenze, Abschalten des Hinweises (Rev. 3).
- Mindestanteil für Teiltage (F3), Rückfall auf die Prognose (F4), Mengenanteil im Prozentsatz (G8).
- Änderungen an `calcmodules/pyeto` und `calcmodules/passthrough`.
- Neue Store-Felder; neue Texte außer der Streichung in der Panel-Hilfe und der Doku.
- Änderungen an der Quellenkette über „nie wegen einer Sperre“ hinaus.
- Umstellen von HA-Prod.

## Betroffene Stellen PR 3

`sensor_liveness.py` (freie Sperren-Funktion `zone_blocked_spans`, `_group_cuts`, Auffrischung nach Öffnen/Schließen,
Kommentare), `calculation.py` (Transport, Wegfall des Gates, Pflichtmenge je Form, Anteil im Stundenzweig, Kommentare),
`weather_aggregate.py` (Helfer gültige Proben, `build_hourly_rows`, `_ratio_hold_solar`, `build_substeps`,
`_precip_increments`, Kommentare), `et_estimate.py` (`hourly_eto_priced` reicht `blocked=` durch), `live_estimate.py` (vier
Leser, Hochrechnung, `_daily_mirror_et`, `_latest_temperature`, `_HourlyCarry`-Schlüssel, Kommentare), `__init__.py`
(Re-Sync entfällt), `const.py` (Kommentar), `frontend/localize/languages/*.json` (8, Streichung), `frontend/dist/`
(2 Bundles), `docs/configuration-sensor-groups.md`, Tests.

## Zuordnung der offenen Fragen (§4 der Faktensammlung)

| § 4 | Wo entschieden |
|---|---|
| 1 Teilweise gültige Stunde | G3, 2.3 |
| 2 Pflichtfelder je Form | G4, 2.4 |
| 3 Pflichtfeld ganzes Fenster gesperrt | G4, 2.3 |
| 4 Druck | Rev. 3, 2.3 |
| 5 Sonne, Klarheitsquote | G5, 2.3 |
| 6 Ansatz im Reduzierer | G12, 2.2 |
| 7 Teilschritte, Lage | G6, 2.5 |
| 8 Abgleich, Regenrate | G7, 2.5 |
| 9 Gate-Wegfall als Einheit | 1 (*Einheit*), 2.4 |
| 10 Erklärung im Stundenbetrieb | G8, 2.4 |
| 11 Aufzeichnungen | 2.6 |
| 12 Live-Aufrufstellen, Helfer, `now` | G12, 3.1 |
| 13 `_latest_temperature` | Rev. 3, 3.3 |
| 14 Live-Quellenkette | G9, 3.2 |
| 15 Live ohne Stundenrechnung (`daily_mirror`) | G9, 3.2 |
| 16 Hochrechnung | G10, 3.3 |
| 17 Übertrag, Auffrischung | G11, 3.4 |
| 18 Texte nach Gate-Wegfall | 4 |
| 19 Rückbau | 1 |
| 20 Lieferung | G1, *Lieferung* |
| 21 HA-Prod | *Lieferung* |
| 22 Live-Test | *Ende-zu-Ende-Kriterium* |
| 23 Teiltag-Grenze, Doku | 2.6, 4 |
