# Finish-Backstop mit Wartezeit: der Watcher darf ein normales Laufende abschließen

Datum: 2026-09-15 · **Revision 3: 2026-09-19** · Upstream-Issue [#139](https://github.com/JustChr/HAsmartirrigation/issues/139)
· Basis `upstream/master` = `2b2c403b` („fix(skip): examine rain from the run's start, not from the day after it (#146)“)
· Arbeitsbranch `fix/backstop-grace` · Probelauf-Referenz `dry6/backstop-grace` (Worktree
`D:/Entwicklung/HASI/pr139-work/dry2`, zehn Commits T1–T12 ohne T3b/T6/T10; seit dem 19.09. abends, Vorgänger
`dry5/backstop-grace` mit gleichem Produktivcode und dist).
· Form: JustChr 09-14 ([issuecomment-5667625952](https://github.com/JustChr/HAsmartirrigation/issues/139#issuecomment-5667625952));
Umfang: JustChr 09-16 ([issuecomment-5692654650](https://github.com/JustChr/HAsmartirrigation/issues/139#issuecomment-5692654650))
und 09-19 ([issuecomment-5740329987](https://github.com/JustChr/HAsmartirrigation/issues/139#issuecomment-5740329987)). Wir bauen.

**Zeilenangaben** gelten für `2b2c403b`. `git diff --stat 0b418644 2b2c403b` berührt `self_closing.py`, `run_watch.py`,
`run_state.py`, `irrigation.py`, `master.py`, `run_chain.py`, `observed_watering.py`, `batch.py`, `calculation.py`,
`store.py`, `sensor.py`, `flow_metering.py` und `__init__.py` nicht. Deren Angaben aus Revision 2 gelten deshalb unverändert
(Stichproben am 19.09. an `2b2c403b` nachgelesen: `self_closing.py:385/476/487/494/496/629/859-867`,
`run_watch.py:602-604/823/828`, `run_state.py:93-99`, `irrigation.py:68/129-130/1035/3309`, `observed_watering.py:138-140`,
`calculation.py:464`, `batch.py:226`, `run_chain.py:228-237`, `master.py:120-155`). #146 hat `const.py`,
`websockets.py` und `skip_conditions.py` verschoben; deren Angaben sind hier für `2b2c403b` neu gelesen. Zeilen im
neuen Code nennen den Stand `dry5/backstop-grace`; auf `dry6/backstop-grace` sind sie gleich, weil dry6 nur
`tests/test_service_watch.py` und zwei Commit-Nachrichten ändert (`git diff dry5/backstop-grace dry6/backstop-grace`:
eine Datei, +113/−21).

**Stand upstream:** JustChr hält den nächsten stabilen Release nur noch für diesen PR an, „not a reason to rush it“; der
Merge wartet auf die Nachmessung beider Zonen (E10).

**Quellen:** Karte des Codes Workflow `wf_6e62f6f5-88b` (7 Code-Leser, 5 Gegenprüfer, Vollständigkeitsprüfung,
Recorder-Leser auf HA-Prod, nur lesend). Umfangsprüfung nach JustChrs Regel: `D:/Entwicklung/HASI/pr139-work/wf-scope-answer.json`
(`result.impact.map.changes`, `result.impact.critic`, Schwester-Pfad-Befunde `result.sister` SP-1 bis SP-10 mit je zwei
Gegenprüfungen). Probelauf der Entscheidungen: `wf-dry3.json`, Protokolle `dry3-logs/` (T5.md, T7.md, T8.md, T9.md, final.md).
Kommentare auf #139: `issue139-comments.md`.

## Herkunft

Ein Service-Lauf mit `confirm_entity` hat zwei Wege zum Abschluss:

- **Watcher:** das Ventil meldet „aus“, nach `finish_settle_seconds` = 5 s Entprellung
  entscheidet `_watch_finish` (`run_watch.py:772-831`).
- **Backstop:** `_sc_schedule_cleanup(zone_id, planned_seconds)` (`self_closing.py:414-429`,
  scharf bei `:629`), ohne jeden Zuschlag.

Der Backstop kommt immer zuerst. Er ruft `_sc_finish_run`, das über `_os_cancel_watch`
auch die laufende Entprellung abbricht (`self_closing.py:348`, `run_watch.py:311-324`), und
schreibt `completed` mit `actual_s = planned_s` (`self_closing.py:385`).

### Messungen HA-Prod (Recorder, 10 Tage Aufbewahrung, alle Zeiten HA-Host-Uhr)

| Zone | Lauf | Ventil offen | Fenster | Backstop − Aus | Confirm-Schwanz |
|---|---|---|---|---|---|
| Beet (Tuya, Minuten) | 09.09. | 542,83 s | 540 | −39,94 s | 0,892 s |
| Beet | 10.09. | 302,35 s | 300 | −36,43 s | 0,912 s |
| Beet | 11.09. früh | 302,08 s | 300 | −38,18 s | 0,896 s |
| Beet | 13.09. (nach `e9f2da51`) | 422,90 s | 420 | **−2,03 s** | 0,863 s |
| Kirschlorbeer (SONOFF, Sekunden) | 11.09. | 2299,41 s | 2299 | +0,57 s | 0,973 s |
| Kirschlorbeer | 13.09. | 1118,33 s | 1119 | +1,13 s | 0,461 s |

- Beet schließt 2,08–2,90 s nach seinem Fenster (Gerät schließt ~62 s nach dem letzten
  Minuten-Tick). Der Backstop kam in allen vier normalen Läufen vor der Aus-Meldung.
- Kirschlorbeer meldet innerhalb ±0,7 s um Ein + geplant; der Backstop feuert 0,57/1,13 s
  nach „aus“, also mitten in die 5-s-Entprellung.
- Kirschbaum: kein Lauf im Aufbewahrungsfenster.
- Der einzige Watcher-Abschluss dieser Anlage (erzwungener Stopp 11.09. 16:26) kam bei Aus + 5,009 s;
  `actual_s` 113,98 gegen 109,89 s offen = +4,09 s.
- Backstop-Scharfschaltung liegt ~4 ms nach `RUN_STARTED`.
- Keine `unavailable`-Episode überlappt einen Lauf (alle Episoden treffen alle drei Ventile
  gleichzeitig = Neustart-Muster).

JustChr hat die Zahlen am 09-14 gegen den Code bestätigt und die Default-Marge am 09-16 darauf gestützt.

## Wurzel

1. Backstop ohne Zuschlag (`self_closing.py:629`, Neustart `:867`).
2. `actual_s` wird nicht am Aus-Übergang gemessen: `_watch_finish` liest `elapsed` erst in
   `_decide` nach der Entprellung (`run_watch.py:823`), `async_stop_self_closing` liest es
   noch einmal selbst (`self_closing.py:764`). Ein abgeschlossener Lauf verwirft es ganz
   (`self_closing.py:385`). Der +4-s-Versatz existiert deshalb nur in Teil-Läufen.
3. Startseite: `RUN_STARTED` wird nach `_confirm_valve_running` gestempelt
   (`self_closing.py:535` --> `:587`), der Confirm pollt im 1-s-Takt (`irrigation.py:725-767`).

## Anforderungen (JustChr, #139)

1. Backstop = geplantes Fenster + `finish_settle_seconds` + Latenz-Marge je Zone, nur für
   Läufe mit bestätigtem `RUN_WATCH_ENTITY`; ohne `confirm_entity` exakt beim Fenster.
2. `actual_s` am Aus-Übergang; die Entprellung entscheidet nur, OB der Lauf endete.
3. Startseite nach unserer Wahl mit Recorder-Daten. 09-16: Ein-Meldung als Start und max(1 s, Marge) als Toleranz „in“.
4. Überall, wo der Backstop scharf wird, dieselbe Marge. 09-16: die Neustart-Hälfte gilt, die Pause-Hälfte kann für
   Service-Läufe nicht eintreten (siehe unten).
5. Nur Service-Policy; Batch und OpenSprinkler unberührt, im PR benannt.
6. Zonenfeld --> Panel, Übersetzungen in 8 Sprachen, dist unter Node 22 (wie #125). 09-16: nur die 8 Panel-Kataloge.
7. Tests, je mutationsgeprüft: Schluss in der Marge --> `_watch_finish` mit `actual_s` = beobachtetes Fenster;
   verpasster Schluss --> Backstop; write-only unverändert; die Wiederaufnahme trägt die Marge (für Service: Neustart statt
   Pause/Resume, plus Pin, dass Batch weiter `remaining` neu plant). 09-16: jeder neue Test mutationsgeprüft, auch die zwei
   über die Form hinaus; das In-flight-Fenster am liebsten mit einer Prüfung auf überlebende Mutationen („a second dispatch
   during the grace is the failure that costs water“). 09-19: Tests am Dispatch einschließlich der Anker-Mutation, die
   vorher überlebte; ein Test, der prüft, dass ein Neustart in der Wartezeit den Master nicht anfordert.
8. Default-Marge aus unseren Messungen (09-16: 4 s angenommen, der PR-Text zitiert die Messbereiche). Der PR-Text listet
   jede nicht abschaltbare Änderung mit Reichweite (mindestens: `actual_s`, Teil-Läufe bei normalem Ende erreichbar,
   sequentielle Kette wartet auf den echten Schluss), eine Zeile „Watch-Policies von Batch und OpenSprinkler unberührt“ und
   die bewusst unveränderten Fälle: 09-16 die späte Aus-Meldung (#3) und den Zeitfenster-Preis (#1); 09-19 die
   Sub-Sekunden-Lücke zwischen dem Ende von In-flight und dem Abschluss durch den Backstop. Die drei weiteren Fälle der
   #3-Art (von uns am 09-19 benannt, von JustChr angenommen) gehören in dieselbe Liste.
9. 09-19: die Nachmessung beider Zonen kommt **vor** dem Merge („the proof I most want to see before it goes in“).

### Abweichungen von der Vorgabe (auf #139 am 09-15 vorgelegt, von JustChr am 09-16 bestätigt)

- **Zu 4/7:** `_watch_resume` (`run_watch.py:744-762`) ist für Service-Läufe unerreichbar. Es
  wird nur aus `_watch_evaluate` gerufen, wenn `policy.segmented` (`run_watch.py:602-604`);
  `SERVICE_WATCH_POLICY.segmented=False` (`self_closing.py:56`), Batch `True` (`batch.py:72`). `_watch_pause` braucht
  `_watch_paused`, das nur Batch für Batch-Läufe überschreibt (`batch.py:415-416`). Eine Marge
  dort änderte nur Batch. Service-Backstops werden genau an zwei Stellen scharf: Dispatch
  (`self_closing.py:629`) und Neustart (`:867`). Der Pause/Resume-Test wird deshalb ein
  Neustart-Test plus ein Pin, dass die Batch-Wiederaufnahme unverändert `remaining` plant. JustChr 09-16: „You are
  right and I was wrong“; der Pin bewacht auch die Naht, falls eine Self-Closing-Policy je segmentiert wird.
- **Zu 6:** Der Backend-Katalog `translations/*.json` hat nur `config`, `options`, `services`,
  `entity`, `issues` — keinen Bereich für Zonenfelder. #125 (`0e0bb5d1`) änderte nur die
  Panel-Sprachdateien, ebenso #47/#57. Es gibt also genau einen Katalog für dieses Feld. JustChr 09-16: bestätigt.

Beide gehören weiter in den PR-Text (E5). Dazu kommt dort eine dritte, nicht auf #139 vorgelegte Abweichung im
Wortlaut: JustChr schrieb am 09-14 „Record the instant the valve reported off when `_watch_defer_finish` starts
waiting“. Gespeichert wird stattdessen `last_changed` der ersten Aus-Meldung direkt nach einem laufenden Zustand
(Design 1, `RUN_VALVE_OFF`): die Auswertung läuft als Task nach der Meldung, und ein reines Attribut-Update des schon
„aus“ meldenden Ventils startet das Warten neu; ein Stempel beim Eintritt in `_watch_defer_finish` käme also zu spät und
könnte wandern (siehe „Verworfen“). Die Absicht (das Ende am Aus-Übergang, nicht nach der Entprellung) ist dieselbe.

## Entscheidungen

„Wartezeit“ heißt im Folgenden `SERVICE_WATCH_SETTLE_SECONDS` (5, `const.py:562`) + Marge, bei Default 9 s.

### E1–E7 (User, 2026-09-15), in Revision 3 nachgezogen

- **E1 Startpunkt und Toleranz:** eigenes Laufdatenfeld mit der Ein-Meldung des Ventils (`RUN_VALVE_ON`);
  `RUN_STARTED` bleibt. Toleranz zwischen abgeschlossen und Teil-Lauf = max(1 s, Marge). **Rev. 3:** die Toleranz gilt
  nur, wo eine gespeicherte Aus-Meldung das Fenster schließt (Watcher, (b)) und beim Stopp in der Wartezeit ((d)); ein
  Lauf ohne Aus-Meldung behält die Basisregel mit 1 s. Grund (unverändert): ab `RUN_STARTED` gemessen wäre Kirschlorbeer
  13.09. ein Teil-Lauf (1117,87 + 1 < 1119: kein `irrigation_finished`, keine Kalibrierprobe, Etikett
  `self_closing_stopped`); ab Ventil-Ein mit 1 s blieben nur 0,33 s Luft. JustChr 09-16: „in“, weil ein normales Ende als
  Teil-Lauf eine Regression wäre, die die Wartezeit einführt.
- **E2 Default-Marge 4 s** (ganze Sekunden, 0–30). Deckt die gemessene Notwendigkeit 2,03 s mit ~2 s und die rohe
  Tuya-Latenz 2,90 s mit 1,1 s. JustChr 09-16 angenommen; der PR-Text zitiert die Bereiche (Beet 2,08–2,90 s nach dem
  Fenster, Kirschlorbeer innerhalb ±0,7 s; 13.09.: Beets Backstop 2,03 s vor der Aus-Meldung, Kirschlorbeers Ventil
  meldete 1,13 s vor dem Backstop, in die Entprellung).
- **E3 (Rev. 3) Die Wartezeit zieht nur das In-flight-Fenster mit** (Design 4) und damit jeden Leser von
  `zone_run_in_flight`: Dispatch-Wächter, Berechnungs-Aufschub, Observed-Unterdrückung (`observed_watering.py:138`).
  **Nicht mehr:** Zeitfenster-Preis (T10; JustChr 09-16: eigenes Issue nach dem stabilen Release) und Observed-Sperre
  (T3b; JustChr 09-19, Entscheidung (e)).
- **E4 (Rev. 3) ersetzt.** Die Watcher-Hälfte („ohne gespeicherte Aus-Meldung: Fenster = min(jetzt − Ventil-Ein,
  geplant)“) ist durch (b) ersetzt, die Neustart-Hälfte durch (a) und (f). Die Grenze `min(jetzt − Anker, geplant)` lebt
  nur noch im manuellen Stopp (Design 3.2): vor dem Ende als Deckel, in der Wartezeit bei noch „an“ meldendem Ventil =
  geplant.
- **E5 Abweichungen von der Vorgabe** im PR-Text erklären (beide oben, von JustChr bestätigt).
- **E6 Aus-Meldung nur direkt nach „an“:** siehe Design 1, `RUN_VALVE_OFF`. **Rev. 3:** `on --> unavailable --> off`
  speichert nichts, der Lauf fällt unter (b).
- **E7 Neutrale Namen in neuen Test-Fixtures** (keine echten Zonennamen der Anlage in neu
  hinzugefügten Tests; vorhandene upstream-Namen wie „Beet“ bzw. `script.irrigation_beet` bleiben).

### E8 Umfangsregel (JustChr 09-16, 5692654650)

**Ein Commit gehört zum Fix, wenn er ein Loch schließt, das die Wartezeit selbst öffnet.** Was einen Datensatz nur
besser macht als heute, ist eine Verbesserung und wartet bis nach dem stabilen Release (#147, „keep it to what the fix
needs“). Angewandt:

- **Drin:** Ein-Meldung als Start mit max(1 s, Marge) (sonst würde ein normales Ende partial); In-flight bis zum Ende
  der Wartezeit (sonst passiert ein zweiter Dispatch in der Wartezeit alle Wächter); manueller Stopp (sonst bucht ein
  Stopp in der Wartezeit die Wartezeit als Bewässerung oder wird partial, beides heute unmöglich); dieselbe Wartezeit beim
  Neustart, einschließlich der Schwelle `planned + Wartezeit` (Design 5, SP-2).
- **Draußen:** T6 (Backstop auf gespeicherter Aus-Meldung), T10 (Zeitfenster-Preis), T3b (Observed-Sperre) und die drei
  Fälle der #3-Art aus (a), (b), (c).

### User-Entscheidungen 2026-09-19 (auf #139 angekündigt in 5740280769, von JustChr in 5740329987 angenommen)

- **(a)** Ein Neustart nach `planned + Wartezeit` mit gespeicherter `RUN_VALVE_OFF` schließt mit `planned_s` ab, wie
  heute (T8). Grund: Zwilling von #3 auf dem Neustart-Pfad (SP-1); der Datensatz wird durch die Wartezeit nicht schlechter.
- **(b)** Die Fensterregel gilt nur mit gespeicherter `RUN_VALVE_OFF`. Ein Wartezeit-Lauf ohne sie behält die
  Basisregel: `elapsed` ab `RUN_OBSERVED_START` nach der Entprellung, abgeschlossen gdw. `elapsed + 1 >= planned`. Sonst
  säße die 4-s-Toleranz auf einer Uhr, die die 5 s Entprellung schon enthält: ein unberichteter Schluss bis ~9 s zu früh
  würde mit voller Gutschrift abgeschlossen (heute ~6 s). Ersetzt die Watcher-Hälfte von E4 (T5, SP-4). JustChr 09-19:
  „The second one matters most.“
- **(c)** Ein manueller Stopp vor dem geplanten Ende misst von `RUN_VALVE_ON` bis zum Stopp, gedeckelt auf geplant, und
  nutzt nie eine gespeicherte Aus-Meldung (T7). Grund: vor dem Ende hat deren Entprellung noch nicht entschieden, ob es
  der Schluss oder ein Blip war; der Stopp wird gemessen wie heute (nur vom früheren Anker aus).
- **(d)** Ein manueller Stopp in der Wartezeit rechnet nach der Watcher-Regel ab: abgeschlossen innerhalb der Toleranz
  über `_sc_finish_run` mit `actual_s` = Fenster, das Ventil vorher geschlossen; sonst Teil-Lauf auf dem Fenster. Der neue
  Zweig hängt an `close_valve`, damit der eigene Teil-Lauf des Watchers ohne Aus-Meldung (`close_valve=False`) auf der
  Basis-Uhr bleibt (T7). Grund: ein Stopp in der Wartezeit wäre sonst `partial` ohne `irrigation_finished` und
  Kalibrierprobe, wo der Backstop heute schon `completed` geschrieben hätte — dieselbe Regression wie bei der Toleranz,
  erreichbar über Stop im Panel und Stop-all.
- **(e)** T3b gestrichen; `zone_finish_grace_seconds` entsteht deshalb nie (aus T2 herausgefaltet, der TS-Kommentar in
  T11 umformuliert). Grund: `observed_watering.py:138` prüft `zone_run_in_flight` vor dem Sperr-Timer, mit T9 ist eine
  Ein-Flanke in der Wartezeit schon unterdrückt. Die Sperre hätte nur die Zeit NACH dem Abschluss um 9 s verlängert (die
  bestehende Lücke langsamer Ventile, nicht von der Wartezeit geöffnet) und darin auch ein echtes externes Öffnen
  verschluckt (SP-8). JustChr 09-19: „drop it“, wartet mit 1 und 3 auf nach Stable.
- **(f)** Ein Neustart in der Wartezeit (`planned <= elapsed < planned + Wartezeit`) stellt den Backstop neu und nimmt
  den Watcher neu auf, fordert aber den Master **nicht** an (T8). Grund: Pumpe an, ggf. Kick und Master-Settle (Default
  10 s, `const.py:1039`) für ein Ventil, dessen Countdown vorbei ist, wäre neues Verhalten der Wartezeit; heute beendet
  dieser Neustart den Lauf und startet die Pumpe nie. JustChr 09-19 bat um einen Test, der das Nicht-Anfordern prüft
  (T8 mit Grenztests +600 und +609).
- **(SP-3)** Der Neustart-Test mit gespeicherter Aus-Meldung startet bei +602 neu (Aus bei +601): Backstop 7,0 s bis
  609, Entprellung bei 607, die Entprellung entscheidet. Ab +604 = planned + Marge ist der neu gestellte Backstop
  spätestens gleichzeitig mit der Entprellung fällig und vor ihr gestellt; in Produktion feuert er zuerst und schließt
  für `planned_s` ab. Der Test benutzt den echten Backstop-Timer (T8).
- **(T9)** Tests am Dispatch: ein zweites `async_run_self_closing` und ein `async_run_zone` in der Wartezeit werden
  abgelehnt und lassen Datensatz, Zähler, Master-Hold und Backstop unberührt; Pins für eingefrorene Marge, Anker und
  Grenze. Alle früher überlebenden Proben werden jetzt gefangen.

### Umfang des PR

| Task | Commit auf `dry6` (dry5) | Inhalt | Stand |
|---|---|---|---|
| T1 | `ca77c287` (gleich) | Zonenfeld `latency_margin` (Store, Laden, Websocket) | drin |
| T2 | `a6a9e382` (gleich) | Laufdaten-Schlüssel, Policy-Flag, reine Helfer, Batch-Pin | drin, ohne `zone_finish_grace_seconds` (e) |
| T3 | `c6a4c842` (`4be8c894`) | Dispatch friert Marge und Ventil-Ein ein, Backstop + Wartezeit; seit dry6 Echt-Timer-Test für den verpassten Schluss | drin |
| T3b | — | Observed-Sperre + Wartezeit | **gestrichen** (JustChr 09-19) |
| T4 | `dd43f09c` (`9380fb74`) | `RUN_VALVE_OFF` aufzeichnen, bei Blip löschen | drin |
| T5 | `c234fb23` (`b423feca`) | Watcher rechnet nach dem Ventil-Fenster ab, nur mit Aus-Meldung (b); seit dry6 Pin für den unveränderten T6-Fall | drin |
| T6 | — | Backstop rechnet auf gespeicherter Aus-Meldung ab | **gestrichen** (JustChr 09-16) |
| T7 | `f1266999` (`bcae641c`) | Manueller Stopp (c)/(d) | drin |
| T8 | `4819d2fc` (`09aba7a4`) | Neustart (a)/(f)/SP-3 | drin |
| T9 | `0c0c9416` (`ed9b2e4f`) | In-flight + Wartezeit, Dispatch-Tests | drin |
| T10 | — | Zeitfenster-Preis + Wartezeit | **gestrichen** (JustChr 09-16 --> eigenes Issue nach Stable) |
| T11 | `0e68d978` (`7f57cf4f`) | Panel-Feld + vitest | drin |
| T12 | `70dc0c18` (`58d6b7b5`) | 8 Sprachen, Doku, dist | drin |

Die Task-Nummern bleiben; gestrichene Tasks behalten ihre Nummer mit dem Vermerk „gestrichen“.

### E9 Nachvollzug statt Neubau (User 19.09.)

Die echte Umsetzung auf `fix/backstop-grace` ist ein **Nachvollzug** der `dry6`-Commits (bis zum 19.09. abends: `dry5`).
Je Task:

1. Nur die Testdateien des Tasks aus dem `dry6`-Commit auschecken, laufen lassen und das RED mit dem Plan vergleichen.
2. Dann die Produktivdateien auschecken; GREEN, die 7 Service-Suiten (`tests/test_service_watch.py
   tests/test_finish_grace_helpers.py tests/test_run_in_flight.py tests/test_confirm_reserve.py tests/test_self_closing.py
   tests/test_run_watch.py tests/test_observed_watering.py`, soweit schon vorhanden) plus `tests/test_i18n_completeness.py`,
   black und ruff; Commit mit derselben Nachricht (per Pipe `git log -1 --format=%B "$SRC" | git commit -q -F -`, danach
   `TREE-SAME` und `MSG-SAME`; Prozess-Substitution für `git commit -F` scheitert in dieser Git-Bash, Plan-Kopfteil).
3. Die Mutationsproben laufen in der Schlussprüfung auf dem echten Branch erneut.

Der Plan ist eine kompakte Revision 3 (Entscheidungen, je Task Was/Warum, erwartetes RED/GREEN, Proben), keine
Codeblöcke. So entsteht kein Produktionscode vor einem fehlschlagenden Test, und der Code ist der geprüfte des Probelaufs.

### E10 Live-Test vor dem Merge (JustChr 09-19, User 19.09.)

Zuerst HA-Test mit dem Wartezeit-Emulator, gesteuert von einem HA-Skript auf HA-Test, damit keine MCP-Latenz in die
Zeitmessung eingeht (voller HA-Test-Zugriff für diesen Test freigegeben). Dann ein Fork-Pre-Release auf HA-Prod
(`production` neu auf upstream `2b2c403b` + dieser Branch + Branding) und je Zone EIN kurzer manueller `run_zone` (Beet =
Tuya-Minutenventil, Kirschlorbeer = SONOFF-Sekundenventil), ausgelöst vom **User**: Claude schaltet keine
Bewässerungs-Hardware (der Auto-Modus-Klassifikator blockierte das am 09-11). Natürliche Läufe danach als zusätzlicher
Beleg. Schreiben, Installieren und Neustart auf HA-Prod nur mit ausdrücklicher Freigabe. Kriterien: End-to-End-Abschnitt.

### Wortlaut

Der Wortlaut der 16 Panel-Texte (2 Schlüssel × 8 Sprachen) und des Docs-Punkts ist freigegeben (Revision 2, Plan Task 12)
und seit `dry2` unverändert (Range-Diff `=` für T12, `dry3-logs/final.md`).

## Design

### 1. Laufdaten (nur bestätigte Service-Läufe, beim Dispatch festgelegt)

Präzedenz `RUN_CEILING` (`const.py:949`, `self_closing.py:591`): ein Wert, der mitten im Lauf nicht von einer
Zonenänderung verschoben werden darf. Laufdatensätze sind rohe Dicts in `Config.active_valve_runs`; neue Schlüssel
überstehen Neustarts ohne Schema-Änderung (`store.py:1086-1092`, `:1568-1579`; Schreiben über `_watch_update_run`,
`run_watch.py:408-428`). `RUN_SEGMENT_STARTED`/`RUN_WATERED_SECONDS` NICHT wiederverwenden — sie schalten den Lauf auf
segmentierte Behandlung (`run_watch.py:81-84`, `irrigation.py:386-400`).

- **`RUN_LATENCY_MARGIN`** — `zone_latency_margin(zone)` beim Dispatch: ganze Sekunden, gerundet, auf 0–30 geklemmt;
  fehlend oder unlesbar --> 4. Geschrieben nur im Block, der `RUN_WATCH_ENTITY` setzt (`dry5 self_closing.py:663`), also
  nur für bestätigte Läufe. Seine Anwesenheit ist das Tor (Design 2).
- **`RUN_VALVE_ON`** — ISO-UTC aus `_sc_valve_on_instant(confirm_target, dispatched_at, confirmed_at)`: `last_changed`
  der Confirm-Entität, geklemmt auf [`dispatched_at`, `confirmed_at`]; ohne State `confirmed_at`. `dispatched_at` ist ein
  `utcnow()` unmittelbar vor `_sc_dispatch_open` (`self_closing.py:496`), `confirmed_at` ein `utcnow()` unmittelbar nach
  der Rückkehr von `_confirm_valve_running`. Ein vor dem Dispatch schon offenes Ventil (`irrigation.py:750-753` bestätigt
  beim ersten Lesen) bekommt so `dispatched_at` statt einer alten Meldung; eine Meldung, die nach der Confirm-Rückkehr
  gestempelt ist, wird auf `confirmed_at` geklemmt. `_confirm_valve_running` behält seine Rückgabe (drei weitere Aufrufer
  vergleichen `is False`: `irrigation.py:1405`, `:2106`, `distributor.py:1493`, dazu viele Test-Stubs). Präzedenz für
  einen geklemmten Hardware-Start: `opensprinkler.py:283-318`.
- **`RUN_VALVE_OFF`** — ISO-UTC der ersten Aus-Meldung seit dem letzten „an“, aus `new_state.last_changed` des
  Zustandsereignisses. HA übernimmt `last_changed`, solange der Zustandstext gleich bleibt
  (`homeassistant/core.py:2328-2330`); ein reines Attribut-Update eines schon „aus“-Ventils löst zwar `state_changed` aus
  und startet die Entprellung neu (`run_watch.py:784-785`), verschiebt den gespeicherten Wert aber nicht. Gesetzt nur aus
  einem Ereignis der Subscription, dessen VORHERIGER Zustand laufend war (`on`/`open`/`opening`); die Subscription reicht
  dazu `old_state` als `previous_state` an `_watch_evaluate` weiter. Also NIE aus der ersten Auswertung beim Neuaufnehmen
  nach einem Neustart und NIE aus `unavailable`/`unknown`/fehlend --> `off`: nach einem Neustart melden die Z2M-Ventile
  zuerst `unavailable`, und `last_changed` des folgenden `off`-Ereignisses ist die Wiederkehr der Entität, nicht der
  Schluss (`core.py:2321-2326`; auf HA-Prod belegt). Bewusst in Kauf genommen: `on --> unavailable --> off` mitten im Lauf
  speichert nichts; der Lauf wird dann nach der Basisregel abgerechnet ((b); 10 Tage Recorder: keine solche Episode
  während eines Laufs). Gelöscht, wenn der Watcher für den Lauf wieder einen laufenden Zustand sieht (Blip), damit ein
  alter Wert die nächste Aus-Meldung nicht überdauert. Nicht vor `RUN_VALVE_ON`: ein Fenster kleiner 0 wird 0.

**Reine Helfer** in `run_watch.py` (T2, `dry5 run_watch.py:267-340`): `zone_latency_margin`, `run_latency_margin`,
`run_has_finish_grace` (das Tor), `run_finish_grace_seconds` (Wartezeit oder 0), `run_completion_tolerance`
(max(1, Marge) mit Tor, sonst 1), `valve_window_seconds(run, now)` (Anker `RUN_VALVE_ON`, sonst `RUN_OBSERVED_START`,
sonst `RUN_STARTED`; mit Aus-Meldung `off − Anker`, ohne sie `min(now − Anker, planned)`; ohne Anker `planned`).
`zone_finish_grace_seconds` gibt es nicht ((e)).

**Policy-Flag** `WatchPolicy.settles_on_valve_window: bool = False` (`dry5 run_watch.py:219`), nur
`SERVICE_WATCH_POLICY` setzt `True`. Batch und OpenSprinkler bleiben byte-gleich; ihre Tests sind das Orakel.

`RUN_STARTED`, `RUN_OBSERVED_START` und damit Panel-Fenster (`irrigation.py:377/401`), `_sc_run_elapsed`
(`self_closing.py:674-679`) und Neustart-`elapsed` (`:859`) bleiben unverändert.

### 2. Backstop

- **Tor** („die Wartezeit gilt“): `RUN_WATCH_ENTITY` UND eingefrorene `RUN_LATENCY_MARGIN` UND die Policy des
  `RUN_MODE` hat `settles_on_valve_window`. `RUN_WATCH_ENTITY` allein reicht nicht (OpenSprinkler `self_closing.py:596`,
  Batch `batch.py:359`). Datensätze aus der Zeit vor dem Update haben keine Marge und laufen nach der heutigen Formel.
- **Dispatch** (`self_closing.py:629`, `dry5 :701`): `_sc_schedule_cleanup(zone_id, planned_seconds +
  run_finish_grace_seconds(record))`. Bei 600 s geplant und Default-Marge 609 s, bei Marge 0 605 s; write-only (kein
  `confirm_entity`) und nicht prüfbarer Confirm (`None`, Entität nicht lesbar; beide ohne `RUN_WATCH_ENTITY`,
  `self_closing.py:597-603`) genau `planned`.
- `_sc_schedule_cleanup` bleibt unverändert; es wird auch von `run_watch.py:703/760` und `opensprinkler.py:666` benutzt.
  Die Wartezeit wird an den Service-Aufrufstellen addiert.
- **Neustart:** Design 5.
- **Feuert der Backstop,** ruft er wie heute `_sc_finish_run(zone_id)` ohne `actual_s`: `completed`, `actual_s =
  planned_s` — **auch mit gespeicherter `RUN_VALVE_OFF`** (T6 gestrichen, JustChr 09-16: „records `planned_s`, exactly as
  today“). Mit gespeicherter Aus-Meldung erreicht er einen Lauf auf zwei Wegen: (1) das Ventil meldet den Schluss später
  als die Marge, die Entprellung endete also nach `planned + Wartezeit`; (2) ein reines Attribut-Update des schon
  „aus“-Ventils, das weniger als `SERVICE_WATCH_SETTLE_SECONDS` vor dem Backstop eintrifft, startet die Entprellung über
  den Backstop hinaus neu (SP-10). Beide: bekannt und bewusst unverändert. `_sc_finish_run` bricht über
  `_os_cancel_watch` den Watcher samt Entprellung ab, eine spätere Entprellung kann also keinen Folgelauf abrechnen.

### 3. Abschluss

Gesteuert über das Policy-Flag (Design 1). Batch und OpenSprinkler bleiben byte-gleich.

#### 3.1 Watcher

- **Weg** (`_watch_finish`, `dry5 run_watch.py:986-990`): `run_has_finish_grace(run)` UND `RUN_VALVE_OFF` gespeichert
  --> `_watch_settle_by_window`. Sonst unverändert die Basisregel (b): `elapsed = _sc_run_elapsed(run)` nach der
  Entprellung (ab `RUN_OBSERVED_START`, für Service = `RUN_STARTED`, `run_watch.py:483-486`); `elapsed + 1 >= planned`
  --> `_sc_finish_run(zid)` (`actual_s = planned_s`), sonst `async_stop_self_closing(zid, close_valve=False)` ohne
  `actual_s`. Das gilt auch für jeden Datensatz ohne eingefrorene Marge (Batch, OpenSprinkler, Service-Läufe von vor dem
  Update).
- **`_watch_settle_by_window`** (`dry5 run_watch.py:964`): Fenster = `valve_window_seconds(run, now)` = `RUN_VALVE_OFF −
  RUN_VALVE_ON`. Abgeschlossen, wenn `Fenster + max(1, RUN_LATENCY_MARGIN) >= planned` --> `_sc_finish_run(zid,
  actual_s=Fenster)`; sonst Teil-Lauf `async_stop_self_closing(zid, close_valve=False, actual_s=Fenster)`.
- **`_sc_finish_run(zone_id, *, actual_s=None)`**: mit Wert wird dieser als `actual_s` geschrieben (Watcher mit
  Aus-Meldung, abschließender Stopp in der Wartezeit); ohne Wert wie heute `planned_s` (Backstop, Basisregel des Watchers,
  Sofort-Abschluss nach Neustart, OpenSprinkler `opensprinkler.py:660`, Batch). Zeitvolumen (`:378`) und Kalibrierprobe
  (`:404`) bleiben bei `planned_s`.
- **`async_stop_self_closing(..., actual_s=None)`**: mit Wert gilt er für `delivered_frac` (`:765`), Zeitvolumen (`:812`)
  und `actual_s` (`:820`). Ein Wert, drei Verbraucher: Eimer, Volumen und `actual_s` stimmen überein.
- Die Entprellung selbst bleibt 5 s und entscheidet nur noch, ob der Lauf endete (Blip-Prüfung `run_watch.py:803-813`).
- **Keine Zusage `actual_s <= planned_s`:** ein spät meldendes Ventil bucht mehr als geplant (Test: 602 von 600;
  rechnerisch Beet 13.09.: 422,90 von 420).

Beispiele aus den Tests (600 s geplant, Marge 4): Schluss bei +602 --> `completed` 602; bei +597 --> `completed` 597;
bei +590 --> Teil-Lauf, gutgeschrieben für 590; Marge 0 und +599,5 --> `completed` 599,5; unberichteter Schluss
(`unavailable` bei +590, `off` bei +593), Entscheidung bei +598 --> Teil-Lauf 598 ohne Kalibrierprobe; unberichteter
Schluss mit Entscheidung bei +599,5 --> `completed` mit `planned_s` 600.

#### 3.2 Manueller Stopp (T7)

`async_stop_self_closing`, Auswahl von `elapsed` (`dry5 self_closing.py:856ff.`):

| Fall | Messung | Ergebnis |
|---|---|---|
| `actual_s` übergeben | dieser Wert | Watcher-Teil-Lauf mit Aus-Meldung (3.1) |
| `close_valve` UND Tor, Stopp vor dem Ende (`_sc_elapsed(RUN_STARTED) < planned`) — (c) | `valve_window_seconds` mit `RUN_VALVE_OFF` ausgeblendet: `min(jetzt − RUN_VALVE_ON, planned)` | Teil-Lauf wie heute, nur vom Anker `RUN_VALVE_ON`; eine gespeicherte Aus-Meldung zählt nicht |
| `close_valve` UND Tor, Stopp ab dem Ende (in der Wartezeit) — (d) | `valve_window_seconds(run)`: bis zur gespeicherten Aus-Meldung, sonst `planned` (Ventil meldet noch „an“) | `Fenster + Toleranz >= planned` --> `_sc_finish_run(zone_id, actual_s=Fenster)`, `return True`; sonst Teil-Lauf auf dem Fenster |
| sonst | `_sc_run_elapsed(run)` wie heute | Watcher-Teil-Lauf ohne Aus-Meldung (`close_valve=False`), write-only, Batch, OpenSprinkler, Datensätze von vor dem Update |

- **Tor `close_valve`:** der einzige Aufrufer mit `close_valve=True` ist der manuelle Stopp (`_sc_maybe_stop` <--
  `async_stop_zone` <-- `async_stop_all_zones`). Der Watcher-Teil-Lauf ohne Aus-Meldung wurde auf der Uhr ab
  `RUN_OBSERVED_START` entschieden und wird auf ihr gebucht; ohne das Tor würde er ab `RUN_VALVE_ON` gebucht (um bis zu einen
  Confirm-Poll mehr), und mit einem Poll über 1 s könnte ein als partial entschiedener Lauf `actual_s == planned_s` bei
  voller Gutschrift bekommen (T5-Protokoll, offene Frage 1, gelöst durch Option (ii)).
- **Vorher/nachher-Grenze ab `RUN_STARTED`**, dem Anker des Backstops, nicht ab `RUN_VALVE_ON`; `<`: ein Stopp genau bei
  `planned` gilt als in der Wartezeit. Folge des Deckels: ein Stopp 0,2 s vor dem Ende (von `RUN_STARTED`), bei
  `RUN_VALVE_ON` 0,6 s früher, bucht `partial` mit `actual_s` 600 von 600 (`delivered_frac` 1, keine Eimer-Korrektur).
- **Reihenfolge beim abschließenden Stopp:** `_os_cancel_watch`, Master-Freigabe, Stopp-Service (Ventil zu), DANN
  `_sc_finish_run` mit Abrechnung, `irrigation_finished`, Kalibrierprobe, aufgeschobener Berechnung und Ketten-Fortschritt
  wie beim Watcher; der Stopp kehrt vor seinem eigenen Abrechnungs-Code zurück, nichts wird doppelt gebucht. Die zweite
  Master-Freigabe in `_sc_finish_run` ist harmlos (`holds.discard` auf ein schon entferntes Token; ohne andere Holds setzt
  sie nur den Aus-Timer auf die Frist, die er schon hat, `master.py:135-155`). Die Freigabe hinter das Schließen zu
  verschieben ließe den Pumpen-Hold hängen, wenn der Stopp-Service wirft.
- **Erreichbar:** das Panel listet die Zone mit ihrem Stop bis zum Abschluss (`get_active_runs`, `irrigation.py:449-463`),
  Stop-all erreicht sie über dieselbe Liste (`irrigation.py:515-525`), unabhängig vom In-flight-Fenster.

#### 3.3 Nachgerechnet 13.09. (Default-Marge 4)

| Zone | Fenster | Watcher schließt ab | Backstop | Ergebnis |
|---|---|---|---|---|
| Beet | 422,90 s | 06:20:36,86 | 06:20:38,82 | `completed` über `_watch_finish`, `actual_s` 422,90 (über `planned_s` 420) |
| Kirschlorbeer | 1118,33 s | 06:32:11,68 | 06:32:16,81 | `completed` (1118,33 + 4 ≥ 1119), `actual_s` 1118,33 |

Beide Läufe hatten eine normale `on --> off`-Meldung, fallen also unter die Fensterregel, nicht unter (b).

### 4. In-flight-Fenster (einzige mitgezogene Stelle, E3)

- **Fenster** (`_self_closing_run_in_flight`, `run_state.py:88-99`, `dry5 :103-113`): nicht-queued `planned +
  run_finish_grace_seconds(run)`; die queued OpenSprinkler-Frist bleibt. Wartezeit aus der **eingefrorenen** Marge, nicht
  aus der Zone. Anker unverändert `RUN_OBSERVED_START` oder `RUN_STARTED` (Service: `RUN_STARTED`), **nicht**
  `RUN_VALVE_ON`: das Fenster darf nicht kürzer werden als der Backstop. Vergleich `<`: bei genau `planned + Wartezeit`
  ist der Lauf nicht mehr in flight, zeitgleich mit der Fälligkeit des Backstops.
- **Leser** (`2b2c403b`): Dispatch `self_closing.py:476`; `irrigation.py:1035` (`_drop_zones_already_running`, über
  `:847` geplant und `:3275` „Jetzt bewässern“); `irrigation.py:3309` (`run_zone`); `batch.py:226`; Berechnungs-Aufschub
  `calculation.py:464` und Wiederholung `run_state.py:169`; Observed `observed_watering.py:138`; Ketten-Dispatch
  `run_chain.py:248` (die sequentielle Kette überspringt eine Zone in flight) und `:408` (die Rotation lässt den Rest
  einer Zone in flight fallen). Service-Ketten warten ohnehin, solange ein Datensatz ihres Modus existiert
  (`run_chain.py:235-237`).
- **Was es schließt** (JustChr 09-16: „the worst outcome in this whole issue“): ohne die Erweiterung passiert ein
  zweiter Dispatch derselben Zone in der Wartezeit alle Wächter. Er ersetzt den noch nicht abgerechneten Datensatz
  (`self_closing.py:209-216`), oder der alte Backstop bzw. die alte Entprellung feuert während seiner Confirm-Abfrage und
  rechnet den alten Lauf mit der Pumpen-Freigabe (geteiltes Token `sc:{zone}`, `self_closing.py:192-199`) und dem Zähler
  des neuen ab (`:350`, `:359`, `:412`). Eine Berechnung in dieser Zeit würde nicht aufgeschoben, und die absolute
  Eimer-Schreibung des Abschlusses überschriebe ihr ET (`:367-374`, `:779-796`).
- **Garantie am Dispatch (T9):** ein zweites `async_run_self_closing(zone, trigger="manual")` 3 s nach dem Ende gibt
  `False` zurück, ein `async_run_zone(2, 10)` wird vor dem Manuell-Marker abgelehnt; das Ventil öffnet nicht erneut, der
  Datensatz (gleiches `RUN_STARTED`), der Zähler (nicht neu gestartet, nicht abgeschlossen), der Master-Hold (einmal
  genommen, nicht freigegeben) und der Backstop (einmal gestellt, dasselbe Handle) bleiben; danach rechnet der erste Lauf
  über seinen eigenen, echten Backstop ab.
- **Bekannt und bewusst unverändert (JustChr 09-19):** eine Sub-Sekunden-Lücke zwischen dem Ende von In-flight
  (`RUN_STARTED + planned + Wartezeit`) und dem Backstop, der den Datensatz entfernt. Der Backstop wird Millisekunden
  nach `RUN_STARTED` gestellt (gemessen ~4 ms, siehe Herkunft) und feuert mit der Loop-Latenz; in dieser Lücke ist die
  Zone „nicht in flight“, ihr Datensatz besteht noch. Dieselbe Lücke besteht heute am geplanten Ende (In-flight endet
  bei `RUN_STARTED + planned`, der Backstop Millisekunden später); ohne T9 wäre sie mit der Wartezeit auf 9 s gewachsen.
- **Observed:** eine Ein-Flanke in der Wartezeit unterdrückt `observed_watering.py:138` über `zone_run_in_flight`, vor
  dem Sperr-Timer. Nach dem Abschluss gilt die Sperre wie heute (`_note_si_valve(zone, planned)`, `self_closing.py:487`,
  + `SI_VALVE_SUPPRESS_MARGIN` 30, `irrigation.py:68/129`); keine Verlängerung ((e)).
- **Panel-Countdown** bleibt Start + geplant (`irrigation.py:401`); während der Wartezeit steht `ends_at` schon in der
  Vergangenheit, die Zone bleibt mit Stop gelistet.
- **Nicht mehr hier:** Zeitfenster-Preis (T10) und Observed-Sperre (T3b) --> „Ausdrücklich nicht dazu“.

### 5. Neustart (`async_resume_self_closing_runs`, `self_closing.py:859-875`, `dry5 :1001-1041`)

`elapsed` wie heute ab `RUN_STARTED` einschließlich Ausfallzeit; `grace = run_finish_grace_seconds(run)` (0 für jeden
Datensatz ohne Tor). Gleicher Pfad beim Neuladen des Config-Entrys (`__init__.py:211/237`).

| Zustand | Verhalten |
|---|---|
| `elapsed >= planned + grace` | sofort `_sc_finish_run(zone_id)`: `completed`, `actual_s = planned_s`, **egal was gespeichert ist** ((a)); kein Master, kein Backstop, kein Watcher |
| `planned <= elapsed < planned + grace` | **kein** `async_master_acquire` ((f)); Backstop `planned + grace − elapsed`; Watcher neu aufnehmen |
| `elapsed < planned` | Master-Hold neu nehmen (wie heute, `:866`); Backstop `planned + grace − elapsed`; Watcher neu aufnehmen |

Was der neu aufgenommene Watcher vorfindet:

| Ventil beim Neuaufnehmen | Abschluss |
|---|---|
| `RUN_VALVE_OFF` vor dem Ausfall gespeichert, Ventil „aus“ | die erste Auswertung startet die Entprellung, `_watch_finish` rechnet nach der Fensterregel ab — **nur wenn die Entprellung vor dem neu gestellten Backstop entscheidet**, also bei einem Neustart vor `planned + Marge` (Test: Aus +601, Neustart +602, Backstop 7,0 s bis 609, Entprellung 607 --> `completed` 601). Ab `planned + Marge` ist der Backstop spätestens gleichzeitig mit der Entprellung fällig und zuerst gestellt; er schließt mit `planned_s` ab (Neustart-Variante von #3, bekannt und unverändert; SP-3) |
| „aus“ gefunden oder `unavailable` --> `off`, keine Aus-Meldung | nichts gespeichert (E6), Basisregel (b): +604 gefunden aus --> Entscheidung bei 610 --> `completed` 600; +604 `unavailable`, `off` bei +606 --> Entscheidung bei 612 --> `completed` 600; +200 gefunden aus (Aus bei +150) --> Teil-Lauf 205 (enthält Ausfall und Entprellung, wie heute) |
| noch „an“ | Watcher wartet auf die Aus-Meldung; sonst der Backstop |

- **Warum die Schwelle `planned + grace` bleibt (SP-2, Gegenprüfung):** der Vorschlag, sie auf `planned` zurückzusetzen,
  hielt dem Neuladen des Config-Entrys nicht stand. Beim Neuladen bleibt der Backstop-Timer des alten Koordinators stehen
  (`async_unload`, `__init__.py:2196-2291`, bricht `_sc_cleanup_handles` nicht ab), fällig bei `planned + grace`. Endete der
  Datensatz beim Neuladen schon bei `planned`, wäre die Zone bis zu 9 s „frei“, und der alte Timer könnte einen in dieser
  Lücke gestarteten Lauf derselben Zone abrechnen (`_sc_finish_run` sucht nur nach `zone_id`). Das ist das Loch, das die
  Wartezeit öffnet; die Schwelle hält den Datensatz und damit den Wächter aus T9 bis zum Ende der Wartezeit (E8).
- **Master in der Wartezeit:** ein live laufender Lauf behält seinen Dispatch-Hold bis zum Abschluss (Reichweite); ein
  in der Wartezeit neu aufgenommener hat keinen, und `_sc_finish_run` gibt später ein nicht gehaltenes Token frei (wie
  beim Sofort-Abschluss immer schon).
- Write-only-Datensätze und Datensätze ohne die neuen Felder: `grace` 0, heutige Formel; Pin
  `tests/test_self_closing.py:491` `(2, 500.0)` bleibt.

### 6. Zonenfeld, Panel, Übersetzungen, Doku

- **`const.py`** Service-Block (`:851-863` auf `2b2c403b`): `ZONE_LATENCY_MARGIN = "latency_margin"`,
  `DEFAULT_LATENCY_MARGIN_SECONDS = 4`, `MAX_LATENCY_MARGIN_SECONDS = 30`; die drei Laufdaten-Schlüssel bei
  `RUN_WATCH_ENTITY` (`:961`).
- **`store.py`**: `attr.ib` `latency_margin` (Default 4) auf `ZoneEntry` (`:229-316`) UND `zone.get(ZONE_LATENCY_MARGIN,
  DEFAULT_LATENCY_MARGIN_SECONDS)` im Ladeblock (`:1115-1212`; ohne die Zeile fällt der Wert bei jedem Neuladen zurück).
  Kein Versionssprung, `STORAGE_VERSION` 14 bleibt (`tests/test_store_self_closing.py:17-21`). Folge: jede bestehende
  Service-Zone mit `confirm_entity` bekommt 4 s.
- **`websockets.py`** Zonen-Schema (`SmartIrrigationZoneView` ab `:275`, neben `ZONE_MAXIMUM_DURATION` `:304`):
  `vol.Optional(const.ZONE_LATENCY_MARGIN): vol.Coerce(int)`; nicht in die Liste der servereigenen Felder (ab `:342`).
- **`set_zone`** bleibt (feste Erlaubt-Liste `LIST_SET_ZONE_ALLOWED_ARGS`, `const.py:434`).
- **Panel** `frontend/src/views/zones/view-zone-settings.ts`, nur Service-Block, Zeile unter `confirm_entity`, sichtbar
  nur mit gesetztem `confirm_entity` (`_showLatencyMargin`); Überschrift mit `(${UNIT_SECONDS})`, Zahlenfeld `step 1`,
  0–30, Wert `zone.latency_margin ?? 4`; `_clampLatencyMargin` rundet und klemmt, ein leeres oder ungültiges Feld wird
  ignoriert statt 0 zu speichern (Muster `lead_time`). Der Kommentar nennt keinen Backend-Helfer mehr ((e)). `const.ts`
  `ZONE_LATENCY_MARGIN`, `types.ts` `latency_margin?: number`. vitest
  `view-zone-settings-latency-margin.test.ts` (4 Sichtbarkeit, 4 Klemme).
- **Übersetzungen**: `panels.zones.labels.latency_margin` und `latency_margin_help` in allen 8
  `frontend/localize/languages/*.json`, echte Übersetzungen. `tests/test_i18n_completeness.py` prüft fehlende/verwaiste
  Schlüssel und englische Kopien.
- **dist**: `irrigation-plus.js` und `irrigation-plus-card-impl.js` (en.json steckt in beiden, `localize.ts`); Node 24
  lokal = Node-22-CI; `git add -f`. `card.js`/`card-legacy.js` unverändert.
- **Doku**: `docs/configuration-my-zones.md` Punkt „Latency margin“ unter „Confirm entity“ (Sekunden, Default 4, 0–30,
  nur mit Confirm-Entität; Abschluss auf den eigenen Meldungen; ohne Meldung `completed` bei geplant + 5 s + Marge).

## Tests

### Harness

Basis `tests/test_service_watch.py` (echtes `hass`, `_coord`/`_zone`/`_dispatch`). Dispatch und ganzer Ablauf in EINEM
`freeze_time`/`freezer`-Block (freezegun friert auch die Loop-Uhr ein), vorstellen mit `tick(n)` +
`async_fire_time_changed` + `async_block_till_done` (Helfer `_advance`, `_run_until_the_valve_closes`); die Uhr zwischen
Aus und Entscheidung WIRKLICH vorstellen (sonst bleibt der +5-s-Fehler unsichtbar). `async_fire_time_changed` feuert bis
0,5 s zu früh — Grenzen mit Abstand. Eimer negativ halten, damit die Deckelung den Beweis nicht frisst. Jeder Test mit
echten Timern endet abgerechnet (lokal sonst „Lingering timer“).

- **Echter Backstop-Timer** nur, wo der Zeitpunkt oder die Reihenfolge Backstop gegen Entprellung der Beweis ist:
  `_the_real_backstop_from_here(c)` entfernt `_coord`s Doubles `_sc_schedule_cleanup`/`_sc_cancel_cleanup` und hüllt den
  echten `_sc_schedule_cleanup` in `Mock(wraps=...)`. Seit dry6 steht der Helfer in T3 (mit `_finished`, vorher T7/T8)
  und dient dem T3-Test für den verpassten Schluss, dem T6-Pin in T5, dem SP-3-Test in T8 und den Dispatch-Tests in T9.
  Die übrigen Tests lesen den Arm-Wert über `_coord`s Double.
- **Befund T9:** in `_coord` ist `store.config` ein nacktes `Mock`, `active_valve_runs` also keine Liste; in
  `tests/test_service_watch.py` kann deshalb kein Dispatch-Wächter greifen. Die Dispatch-Tests benutzen
  `_service_coord_on_its_store(hass)`, das wie `tests/test_batch.py` bei jedem Persistieren `active_valve_runs` setzt.

### Liste (Stand `dry6`)

- **T1** — `tests/test_distributor_integration.py::test_zone_view_coerces_latency_margin_to_int`;
  `tests/test_store_self_closing.py::test_latency_margin_survives_reload`, `::test_zone_stored_without_latency_margin_loads_the_default`.
- **T2** — `tests/test_finish_grace_helpers.py` (neu): `TestZoneLatencyMargin` (`"7"`-->7, 7,6-->8, −3-->0, 99-->30,
  `"x"`-->4; fehlend --> Default), `TestRunLatencyMargin`, `TestRunHasFinishGrace` (bestätigter Service-Lauf mit Marge ja;
  vor dem Update, unbestätigt, Batch/OpenSprinkler mit beiden Schlüsseln nein), `TestRunFinishGraceAndTolerance`,
  `TestValveWindowSeconds` (Aus − Ein; Aus vor Ein = 0; ohne Aus Zeit seit Ein, gedeckelt auf geplant; Anker-Rückfall auf
  `RUN_OBSERVED_START`/`RUN_STARTED`; ohne Anker `planned`), `TestOnlyTheServicePolicySettlesOnTheValveWindow`,
  `TestABatchResumeArmsExactlyTheRemainder` (Pin: eine pausierte Batch-Wiederaufnahme mit denselben Schlüsseln plant genau
  `remaining`).
- **T3** — `tests/test_service_watch.py`: `test_the_finish_backstop_is_armed_once` `(2, 609)`;
  `TestAConfirmedRunFreezesItsMarginAtDispatch` (Default 4; Zonenwert 7; write-only und nicht prüfbar tragen weder Marge
  noch Ventil-Ein); `TestTheValveOnReportIsClampedToTheDispatch` (vorher offen --> Dispatch; spätere Meldung --> ihr
  `last_changed`, `RUN_STARTED` +1 s; Meldung nach der Confirm-Rückkehr --> auf diese geklemmt);
  `TestTheBackstopWaitsOnlyForAConfirmedValve` (Marge 0 --> `(2, 605)`; write-only und nicht prüfbar --> `(2, 600)`);
  `TestAMissedCloseStillSettlesViaTheBackstop` (neu in dry6: Marge 4, Ventil meldet nie „aus“, echter Backstop-Timer; bei
  +608 nichts abgerechnet, bei +610 `completed` mit `actual_s == planned_s == 600`, `irrigation_finished` einmal, Datensatz
  weg, Master einmal freigegeben, kein Timer übrig).
- **T4** — `TestTheWatcherRecordsTheValvesOwnOffReport` (8): Aus-Ereignis speichert `last_changed`; Attribut-Update
  verschiebt nicht; `off` nach einer `unavailable`-Phase behält die erste Aus-Meldung; `on --> unavailable --> off` mitten
  im Lauf speichert nichts; „an“ in der Entprellung löscht; neu aufgenommener Lauf speichert weder die erste Auswertung noch
  `off` nach `unavailable`; Datensatz von vor dem Update speichert nichts.
- **T5** — `TestAConfirmedRunIsSettledOnItsValveWindow` (9) und der T6-Pin (1): Schluss knapp nach dem Fenster (`completed` 602), in der
  Marge (`completed` 597), jenseits der Marge (Teil-Lauf 590, Gutschrift aus dem Fenster), Marge 0 toleriert 1 s
  (`completed` 599,5), Marge 0 darüber hinaus Teil-Lauf, `on --> unavailable --> off` behält die Basisregel (Teil-Lauf 308
  ab `RUN_OBSERVED_START`), unberichteter Schluss 7 s früh bleibt Teil-Lauf (598, Pin von (b)), unberichteter Schluss
  innerhalb der alten Sekunde `completed` mit `planned_s` 600, Datensatz von vor dem Update behält die Basisregel;
  dazu seit dry6 `TestACloseReportedPastTheMarginIsKnownAndDeliberatelyUnchanged` (Pin des gestrichenen T6: Aus-Meldung
  +606 gespeichert, echter Backstop bei 609 schließt mit 600 ab, nicht 606; am Elternstand gewollt grün, rot gegen eine
  Probe, die T6s Verhalten zurückbringt).
- **T7** — `TestAManualStopMeasuresFromTheValvesOnReport` (13, Zahlen `dry3-logs/T7.md`): Stopp mitten im Lauf ab
  Ventil-Ein (Teil-Lauf 100); Ventil-Ein +0,4, Stopp +100 --> 99,6; Aus +300 gespeichert, Stopp +302 --> Teil-Lauf **302**
  (nicht 300, (c)); Stopp +600,8 bei Ein +0,4 --> Teil-Lauf **600** (Deckel); Aus +597, Stopp +601 --> **`completed` 597**,
  Stopp vor dem Datensatz gesendet, `irrigation_finished` und Kalibrierprobe je einmal; Aus +601, Stopp +604 -->
  **`completed` 601**; Marge 0, Aus +598, Stopp +601 --> Teil-Lauf 598 ohne Event/Kalibrierprobe; Ventil noch an, Stopp
  +604 --> **`completed`, `actual_s == planned_s == 600`**; Stopp genau bei +600 --> `completed` 600 (Grenze `<`);
  Stop-all bei +604 nach Aus +601 --> `completed` 601; Zwilling: derselbe späte Schluss über Entprellung und über Stopp
  bucht identisch (Datensatz, Eimer-Schreibungen, Zähler, gelerntes Zonen-Update, Stempel, Events, Kalibrierprobe,
  aufgeschobene Berechnung, freigegebene Tokens); Watcher-Teil-Lauf ohne Aus-Meldung behält `RUN_OBSERVED_START` (307,
  nicht 307,6); write-only misst weiter ab Start.
- **T8** — `TestARestartCarriesTheFinishGrace` (10, `dry3-logs/T8.md`): +100 --> Backstop `(2, 509.0)`, Master einmal;
  **+600 --> kein Master**, `(2, 9.0)`, Watcher neu; +604 Ventil an --> `(2, 5.0)`, kein Master, Lauf bleibt; +604
  gefunden aus --> `completed` `planned_s` 600, kein Master; +604 `unavailable`, `off` +606 --> `completed` 600, kein
  Master; +200 gefunden aus --> Teil-Lauf 205, `(2, 409.0)`, Master einmal; **Aus +601, Neustart +602, echter Backstop
  `(2, 7.0)` --> `completed` 601, Timer mit dem Lauf weg, kein Master** (SP-3); **+609 --> sofort abgeschlossen**, 600, kein
  Backstop/Watcher/Master; Aus +601, Neustart +700 --> **600** (Pin von (a)); +700 ohne Aus-Meldung --> 600, kein Master.
- **T9** — `tests/test_run_in_flight.py`: +605 in flight, +610 nicht; write-only ohne Wartezeit; Datensatz von vor der
  Marge behält sein Fenster; eingefrorene Marge 10 bei Zonenmarge 4 --> in flight bei +614, nicht bei +616;
  `RUN_VALVE_ON` 1 s vor `RUN_STARTED` --> bei `RUN_STARTED + 608` noch in flight (Anker-Pin); 608,999 in flight, 609,0
  nicht (Grenz-Pin); `TestASecondDispatchInsideTheFinishGraceIsRefused` (zweites `async_run_self_closing` und
  `async_run_zone` bei +603, siehe Design 4).
- **T11** — vitest `view-zone-settings-latency-margin.test.ts`: sichtbar mit `confirm_entity`, verborgen bei `null`, leer,
  fehlend; Klemme: ganze Zahl bleibt, Rundung, unter 0/über 30 geklemmt, leer/NaN ignoriert.
- **T12** — `tests/test_i18n_completeness.py` (bestehend) deckt die zwei Schlüssel in 8 Sprachen.

Keine Tests von T3b, T6 oder T10.

### Abdeckung der Vorgabe (für den PR-Text)

- Schluss in der Wartezeit --> `_watch_finish`, `actual_s` = beobachtetes Fenster: T5 (602, 597), mit echtem Backstop
  der SP-3-Test in T8 (601).
- Verpasster Schluss --> Backstop: seit dry6 ein eigener Echt-Timer-Test in T3,
  `TestAMissedCloseStillSettlesViaTheBackstop::test_a_valve_that_never_reports_off_is_finished_when_the_grace_is_out`
  (bei +608 nichts abgerechnet, bei +610 `completed`, `actual_s == planned_s == 600`, `irrigation_finished` einmal,
  Datensatz weg, Master-Freigabe einmal, kein Timer übrig). Er fängt alle vier Backstop-Proben (ohne Wartezeit, nie
  gestellt, Rückruf rechnet nicht ab, Rückruf bucht die Uhr statt des Plans), die letzten beiden je an einem Stand als
  einziger Test (Rückruf rechnet nicht ab: am T3-Stand; Rückruf bucht die Uhr: am Branch-HEAD nach Schritt T3,
  `bc41374b`, Produktivcode = Endstand, ein Test weniger; `dry6-logs/T3.md`). Am Endstand `70dc0c18` fängt der T5-Pin
  (`TestACloseReportedPastTheMarginIsKnownAndDeliberatelyUnchanged`, echter Backstop) beide mit
  (`dry6-logs/T3-end-probes.txt`). Dazu der Arm-Wert `(2, 609)` (T3), die Dispatch-Tests in T9, die den ersten Lauf
  über den echten Backstop bei +610 abrechnen, und die Pins +609/+700 in T8. Auf `dry5` fehlte dieser Test;
  die Real-Timer-Tests aus Revision 2 lagen in T6 und fielen mit ihm (`wf-scope-answer.json`,
  `result.impact.map.changes`, Task-5/13-Punkt; Befund der Vollständigkeitsprüfung, `wf-rev3.json`).
- write-only unverändert: T3 `(2, 600)`, dazu die unveränderten Pins unten.
- Wiederaufnahme trägt die Marge: Neustart-Re-Arm T8 (`(2, 509.0)` bei +100) plus Batch-Pin T2.
- In-flight am Dispatch einschließlich Anker: T9.
- Master nicht angefordert beim Neustart in der Wartezeit: T8 (+600, +602, +604 ×3; ebenso +609 und beide
  +700-Tests, mit und ohne gespeicherte Aus-Meldung); vor dem Ende weiter angefordert (+100, +200).

### Geänderte und unveränderte Pins

- **Geändert (einziger Pin-Wert):** `tests/test_service_watch.py::TestAFullRunIsStillAFullRun::test_the_finish_backstop_is_armed_once`
  `(2, 600)` --> `(2, 609)` (`2b2c403b` Zeile 216).
- **Angepasst, Assertion unverändert:** `test_a_valve_off_at_the_planned_end_completes` behält `actual_s == planned_s ==
  600`, läuft aber in `freeze_time`, damit die auf den Dispatch geklemmte Ein-Meldung genau `started` ist und das Fenster
  genau 600 s.
- **Unverändert:** `tests/test_self_closing.py:109` `(2, 600.0)`, `:491` `(2, 500.0)`, `:1198` `(2, 300.0)`, `:1224`
  `(2, 263.0)`; `tests/test_opensprinkler.py:1116-1117` (`415 < remaining < 425`); `tests/test_confirm_reserve.py` wird nicht
  berührt (kein T10, kein Pin 30 --> 39 mehr).

### Messstand `dry6` (19.09. abends; T1 und T2 unverändert aus `dry5`)

- Volle Suite Basis `2b2c403b`: `7 failed, 3006 passed, 9 skipped, 10 warnings, 320 errors` (`collected 3022 items`,
  `baseline-2b2c403b.txt`); `dry6`: `7 failed, 3099 passed, 9 skipped, 10 warnings, 320 errors` (`collected 3115 items`,
  `after-dry6.txt`); FAILED/ERROR-Namensmengen identisch (7 FAILED, 321 ERROR-Namen = 320 Tests + 1 Logzeile
  `ERROR    custom_components…` aus `test_batch.py`; `dry6-logs/full-suite.md`); +93 Items (89 neue Testfunktionen,
  eine davon mit 5 Parametern). Die 7 FAILED sind lokale Windows-Fehler (Event-Loop:
  `aiodns needs a SelectorEventLoop`, `winloop` fehlt; ein Pfadtrenner in `test_panel.py`), die 320 Errors alle
  `Lingering timer`-Teardowns (nachgezählt in `baseline-2b2c403b.txt`).
- vitest Basis 22 Dateien / 616 Tests (Messung 19.09. laut Workflow-Auftrag, kein Protokoll in `pr139-work`) --> `dry6`
  `23 passed (23)` / `624 passed (624)` (`dry6-logs/full-suite.md`).
- black/ruff auf jedem Commit sauber (`dry6-logs/percommit.md`; mit der Dateiliste des Plans `70`–`73 files would be
  left unchanged.`, `scratch/dry5-checks.log`, am dry6-Endstand nachgemessen: 73).
- 7 Service-Suiten + `tests/test_i18n_completeness.py` je Commit: T2 240 (`scratch/dry5-checks.log`, derselbe Commit),
  T3 251, T4 259, T5 269, T7 282, T8 292, T9 300, T11 300, T12 300 passed (`dry6-logs/percommit.md`), immer `1 error` =
  der vorbestehende Lingering timer in
  `TestOneOffSampleIsNotEvidenceTheWaterStopped::test_the_run_is_not_settled_before_the_window_is_out`. T1: 238 passed mit
  T1s eigenen Dateien (`replaycheck-logs/T01-suites.txt`, 19.09.: `238 passed, 1 error in 15.11s`); das
  dry5-Protokoll zeigt für T1 „no tests ran“, weil seine Liste `tests/test_finish_grace_helpers.py` enthält, das es bei
  T1 noch nicht gibt.
- dist aus den Quellen byte-gleich reproduziert, alle vier Bundles `SAME` (Hashes `scratch/dry5-checks.log`; Node
  v24.15.0 = Node-22-CI laut `node --version` am 19.09. und `dry3-logs/final.md`); dry6 hat dieselben dist-Bytes.
- Die #139-Änderungszeilen auf `dry5` sind identisch mit denselben Zeilen auf `dry4/backstop-grace` (Basis `0b418644`):
  `scratch/d4.txt` = `scratch/d5.txt` (`cmp` ohne Unterschied); `dry6` ändert keinen Produktivcode.
- RED/GREEN je Task: `rev3/evidence.md` (T3–T12 auf dry6 neu gemessen).

### Mutationsproben (Probelauf `dry3`, Protokolle `dry3-logs/`)

- T5: 13 Proben, 11 gefangen, 1 äquivalent (`gate-off-only`: `RUN_VALVE_OFF` entsteht nur hinter dem Tor), 1 bei T5
  überlebend (`base-partial-passes-window`), ab T7 gefangen von `test_the_watchers_own_partial_keeps_its_observed_start`.
- T7: 21 Proben, 21 gefangen (u. a. Grenze invertiert/entfernt/`<=`, Toleranz ignoriert, gespeicherte Aus-Meldung vor
  dem Ende benutzt, Abschluss-Zweig entfernt, Ventil nicht geschlossen, Abrechnung vor dem Schließen, `close_valve`-Tor
  entfernt).
- T8: 12 Proben, 12 gefangen (Master in der Wartezeit wieder angefordert, Master vor dem Ende weggelassen, `<=`,
  Fenster-Abschluss nach der Wartezeit wieder eingeführt, Schwelle zurück auf `planned`, Re-Arm ohne Wartezeit u. a.).
- T9: 8 Proben, 8 gefangen, darunter die drei früher überlebenden (`lte-boundary`, `frozen-margin-to-default`,
  `anchor-prefers-valve-on`). Die Probe `live-zone-margin` rief `zone_finish_grace_seconds`, das es ab `dry4` nicht mehr
  gibt; im Nachvollzug über `zone_latency_margin` formulieren.
- T1–T4, T11, T12: Proben aus Revision 2 (Plan, Task 13 Step 7).
- dry6 (19.09. abends, `dry6-logs/T3.md`, `T5.md`, `probes.md`): die vier Backstop-Proben gegen den Echt-Timer-Test
  in T3 (alle gefangen, am T3-Stand, an `bc41374b` und am Endstand `70dc0c18`, `dry6-logs/T3-end-probes.txt`), die
  T6-Probe gegen den Pin in T5 (gefangen, nur von ihm) und neun Proben für die Tests, die bis dahin keine Probe fing
  (T2 ×5, T7 ×2, T11 ×2; alle gefangen). Zuordnung Item --> fangende Probe: `dry6-logs/killmap.md`, jedes der 101
  neuen Test-Items (93 pytest + 8 vitest) scheitert an mindestens einer Probe.
- Alle Proben (133, davon 5 äquivalent) laufen in der Schlussprüfung auf dem echten Branch erneut (E9), dazu die
  Prüfung, dass jedes neue Item an mindestens einer scheitert (Plan, Task 13 Step 8b).

## Reichweite: nicht abschaltbare Änderungen (für den PR-Text)

Betroffen ist jede Service-Zone mit `confirm_entity`. Die Marge kann auf 0 verkleinert werden, die 5 s Entprellung
bleiben (Wartezeit dann 5 s, Toleranz 1 s).

- **`actual_s` aus den eigenen Meldungen des Ventils:** abgeschlossene Läufe mit Aus-Meldung = Fenster von Ein- bis
  Aus-Meldung statt `planned_s`, auch über `planned_s` (ein spät meldendes Ventil bucht 601 von 600); Teil-Läufe mit
  Aus-Meldung ohne den +5-s-Versatz (Gutschrift-Rücknahme, Zeitvolumen, `actual_s` aus dem Fenster). Sichtbar im
  Attribut `duration` des Sensors `last_water_used` (`sensor.py:1051`, gerundet `irrigation.py:2873-2874`); die
  Verlaufstabelle im Panel zeigt `actual_s` nicht.
- **Teil-Läufe bei normalem Ende erreichbar:** meldet das Ventil seinen Schluss mehr als max(1 s, Marge) vor dem Ende,
  wird der Lauf `partial`. Heute wurde ein Schluss bis ~6 s vor dem Ende `completed`: unter 5 s kam der Backstop bei
  `planned` der Entprellung zuvor, bei 5–6 s reichte die 1-s-Toleranz auf der Uhr nach der Entprellung. Neu `partial`
  sind also gemeldete Schlüsse zwischen Marge und ~6 s vor dem Ende (bei Marge 0: zwischen 1 s und ~6 s). Ohne
  Aus-Meldung bleibt die Grenze bei ~6 s ((b)).
- **Die sequentielle Kette wartet auf den echten Schluss:** Abschluss bei Aus + 5 s, ohne Aus-Meldung bei `planned + 9 s`;
  die nächste Zone einer `sequential`/rotierenden Kette folgt erst dann (`run_chain.py:235-251`).
- **Unter `rotating`** wird die Einwirkzeit (`last_finish`) beim Abschluss gestempelt (`run_chain.py:228-234`), also
  später als heute.
- **Pumpen-Hold:** die Dispatch-Freigabe kommt beim Abschluss, die Pumpe geht `MASTER_RELEASE_GRACE_SECONDS` (5,
  `const.py:1045`) danach aus statt bei `planned` + 5 s (`master.py:135-155`); innerhalb einer Kette hält der Ketten-Token
  ohnehin.
- **`irrigation_finished`, `last_irrigation`/Verlaufs-Zeitstempel und die aufgeschobene Berechnung** wandern mit dem
  Abschluss (`self_closing.py:389-401`, `irrigation.py:2816-2918`).
- **Panel:** die Zone bleibt bis zum Abschluss, also bis zu einer Wartezeit über das Fenster hinaus, mit ihrem Stop
  gelistet; `ends_at` liegt dann schon zurück (`irrigation.py:401`, `:449-463`).
- **Dispatch in der Wartezeit fällt weg, statt aufgeschoben zu werden:** ein geplanter Lauf, „Jetzt bewässern“,
  `run_zone` (und ein Batch-Dispatch, nur wenn die Zone in diesen Sekunden von Service auf Batch umgestellt wurde) für
  eine Zone in ihrer Wartezeit wird für diesen Dispatch verworfen; heute liefe er. Service-Ketten sind nicht betroffen.
- **Berechnungs-Aufschub** reicht durch die Wartezeit (`calculation.py:464`, `run_state.py:169`).
- **Manueller Stopp mitten im Lauf** misst ab `RUN_VALVE_ON` statt ab `RUN_OBSERVED_START` (um bis zu einen
  Confirm-Poll länger); ein Stopp in der Wartezeit rechnet nach der Watcher-Regel ab (vorher unerreichbar).
- **Neustart in der Wartezeit** schließt nicht mehr sofort ab, sondern wartet auf Watcher oder Backstop, ohne die Pumpe
  anzufordern.
- **Durchfluss-Ratensensor:** mit gespeicherter `RUN_VALVE_OFF` endet die Integration an der Aus-Meldung
  (`FlowMeter.end_rate_at`, R1/C3): das letzte Intervall wird bis zur Meldung mit der zuletzt gemessenen Rate
  gutgeschrieben, die Lesung nach dem Schluss zählt nicht. Das gilt für den Watcher-Abschluss (abgeschlossen und
  Teil-Lauf), den Stopp in der Wartezeit (d), den Stopp vor dem Ende (c) mit noch entprellender Meldung und den
  Backstop, der mit der Meldung im Datensatz feuert. Ohne gespeicherte Aus-Meldung (write-only, nicht prüfbar,
  `on --> unavailable --> off`, nach Neustart wieder aufgenommen, Backstop vor der Meldung) bleibt es wie heute: ein
  Sensor, der seinen letzten Wert hält, wird bis zum Abschluss integriert, einer, der auf 0 fällt, verliert das
  Intervall über dem Schluss (`flow_metering.py:160-170` auf dem Endstand, rechter Endpunkt). Zähler (Totalizer)
  unberührt: ihre Lesung nach dem Schluss gehört zum Lauf. Nachtrag R1.
- **Unberührt:** Batch, OpenSprinkler (Watch-Policies und Tests byte-gleich), Verteiler (eigener Pfad ohne
  `_sc_`/`_watch_`, `distributor.py:677-760`), write-only Service-Zonen, Datensätze von vor dem Update,
  `irrigation_finished`-Nutzlast, Panel-Countdown.

## Ausdrücklich nicht dazu — bekannt und bewusst unverändert

### Im PR-Text als „known and deliberately unchanged“ zu nennen

- **#3 / T6 — Backstop mit gespeicherter Aus-Meldung** schließt mit `planned_s` ab, nicht auf dem Fenster (JustChr 09-16).
  Zwei Auslöser: (1) ein Schluss, der später als die Marge gemeldet wird; (2) ein reines Attribut-Update des schon
  „aus“-Ventils in den letzten `SERVICE_WATCH_SETTLE_SECONDS` vor dem Backstop hält die Entprellung über ihn hinaus am
  Leben (SP-10). Ob ein bestimmtes Z2M-Ventil solche Updates sendet, lässt sich aus dem Code nicht sagen; die Nachmessung
  achtet darauf (End-to-End). Auslöser (1) pinnt seit dry6 ein Test in T5
  (`test_the_backstop_finishes_it_for_the_plan_before_the_debounce`); der PR-Text sagt das.
- **(a) Neustart nach der Wartezeit** mit gespeicherter Aus-Meldung --> `planned_s`, wie heute (Zwilling von #3). Ebenso
  ein Neustart ab `planned + Marge` innerhalb der Wartezeit, bei dem der neu gestellte Backstop vor der Entprellung feuert
  (SP-3).
- **(b) Läufe ohne gespeicherte Aus-Meldung** (`on --> unavailable --> off`, oder ein Neustart, der das Ventil schon „aus“
  findet) behalten die heutige Regel: `elapsed` nach der Entprellung, 1 s Toleranz; ihr `actual_s` enthält weiter die 5 s
  Entprellung (und bei einem Neustart die Ausfallzeit).
- **(c) Manueller Stopp vor dem geplanten Ende** misst bis zum Stopp, wie heute, auch wenn eine Aus-Meldung gespeichert ist.
- **Sub-Sekunden-Lücke** zwischen dem Ende von In-flight und dem Backstop, der den Datensatz entfernt (Design 4;
  JustChr 09-19).
- **Neustart-Lücke von rund 10 s (R2, vorbestehend):** die Wiederaufnahme liest `elapsed` VOR
  `async_master_acquire`, das bei ausgeschalteter Pumpe Kick-Pause und Master-Settle (Default 10 s, `const.py:1039`)
  schläft; der danach gestellte Backstop ist um diese Zeit später fällig als das Ende des In-flight-Fensters. Dieselbe
  Form hat der Basiscode (`planned − elapsed` nach demselben `await`), die Wartezeit öffnet die Lücke also nicht. Der
  PR-Text nennt sie neben der Sub-Sekunden-Lücke als vorbestehend und unverändert und verweist auf das eigene Issue
  (Entwurf `D:/Entwicklung/HASI/pr139-work/rev3/issue-restart-master-gap.md`). Nachtrag R2.
- **#1 / T10 — Zeitfenster-Preis:** `zone_confirm_seconds` (`run_window.py:336-361`) preist eine bestätigte Zone weiter
  mit `VALVE_CONFIRM_TIMEOUT` (30, `const.py:548`) ohne Wartezeit. Eigenes Issue nach dem stabilen Release mit den
  PR-Zahlen und drei Korrekturen (Kommentar 5740280769): unter `rotating` ist der Preis je Slot, bewegt sich also um mehr
  als 9 s je Zone; der Unterpreis beginnt, sobald der Confirm länger als 30 − Entprellung − Marge dauert (21 s bei
  Default) UND der Schluss verpasst wird, ab Marge 26 genügt ein verpasster Schluss allein; Service-Zonen werden von der
  Frist nicht abgeschnitten (`irrigation.py:980-985`), die Kosten sind ein späteres Finish, kein abgeschnittener Schwanz.
  Entwurf: `D:/Entwicklung/HASI/pr139-work/rev3/issue-window-pricing.md`, korrigiert am 19.09. (die drei Korrekturen,
  die 21-s-Schwelle, kein `zone_finish_grace_seconds`); der ältere `pr139-work/issue-window-pricing.md` ist überholt. Der
  PR-Text nennt die Zahlen selbst (Schwelle 21 s bzw. Marge ab 26 s, 9 s je Zone unter `sequential`, je Slot unter
  `rotating`, späteres Finish), weil das Issue auf sie verweist.
- **T3b — Observed-Sperre über den Abschluss hinaus:** nicht verlängert; die Lücke langsamer Ventile (Confirm +
  Schluss-Latenz über 30 s) besteht wie heute und wartet auf nach dem stabilen Release (JustChr 09-19).

### Sonst nicht Teil des Fixes

- `_watch_resume`, Watch-Policies von Batch und OpenSprinkler.
- `RUN_STARTED`, `RUN_OBSERVED_START`, Panel-Countdown.
- Divisor der Kalibrierprobe und Zeitvolumen abgeschlossener Läufe (bleiben `planned_s`).
- Stopp des Durchfluss-Samplers bei der Aus-Meldung.
- Rückgabeform von `_confirm_valve_running`.
- Ein toleranzbewusster Stopp VOR dem Ende (SP-6/SP-7-Varianten jenseits von (c)/(d)).

### Vorbestehende Befunde (in `D:\Entwicklung\HASI\ToDo.md` eintragen, nicht in den PR)

- `async_unload` bricht weder Backstop-Timer noch Durchfluss-Sampler ab (`__init__.py:2196-2291`); ein Neuladen lässt den
  alten Koordinator auf dem geteilten Store abrechnen. Relevant für den Reload-Test auf HA-Test (End-to-End) und der
  Grund für die Neustart-Schwelle (Design 5).
- Fehlerbehandlung des Dispatch (`self_closing.py:640-647`) lässt den bei `:629` scharfen Backstop und den bei `:604`
  gespeicherten Datensatz stehen.
- Ein nach Neustart mitten in der Bewässerung übernommener Batch-Lauf bekommt keinen Backstop (`batch.py:741-756`).
- Observed-Doppelgutschrift, wenn der Dispatch auf ein extern geöffnetes Ventil trifft und `observed_entity` dieselbe
  Entität ist (`observed_watering.py:146`, `:157-172`).
- Veralteter Docstring `get_total_irrigation_duration` („self-closing track … always max(duration)“, `skip_conditions.py:527-533`
  auf `2b2c403b`).
- Unbenutzter Parameter `planned` in `_watch_start` (`run_watch.py:491-563`).
- Die Observed-Sperre deckt langsame Ventile nicht (Confirm + Schluss-Latenz über 30 s), unabhängig von der Wartezeit (SP-8).

## Verworfen

- **`actual_s` ab `RUN_STARTED` mit 1 s Toleranz (Vorgabe wörtlich):** normale Kirschlorbeer-Enden würden Teil-Läufe (E1).
- **Ventil-Ein mit 1 s Toleranz:** 0,33 s Luft auf einer Stichprobe von zwei Läufen.
- **`RUN_STARTED` auf die Ventil-Meldung verschieben:** fünf Leser würden mitwandern (In-flight, Panel,
  `_sc_run_elapsed`, Neustart, `RUN_OBSERVED_START`); ein vorher offenes Ventil hätte einen Stunden alten Anker.
- **Rückgabe von `_confirm_valve_running` erweitern:** drei weitere Aufrufer und viele Stubs.
- **Marge in `_sc_schedule_cleanup`:** träfe Batch und OpenSprinkler.
- **Aus-Zeitpunkt beim Eintritt in `_watch_defer_finish` stempeln:** Attribut-Rauschen und Task-Latenz verschieben ihn;
  `last_changed` des ersten Aus-Ereignisses ist fest.
- **Default-Marge 3 s** (0,1 s Luft gegen die rohe Latenz) und **5 s** (User wählte 4).
- **Nichts mitziehen:** 9-s-Loch für einen Doppel-Dispatch. (Rev. 3: nur In-flight mitziehen ist jetzt die Entscheidung,
  E3; der Unterpreis ist bekannt und bewusst unverändert.)
- **T6 — Backstop rechnet auf gespeicherter Aus-Meldung ab:** Verbesserung eines Datensatzes, den die Wartezeit nicht
  verschlechtert (E8; JustChr 09-16).
- **T10 — Zeitfenster-Preis + Wartezeit:** Kosten 9 s je bestätigter Zone unter `sequential` auf jeder Anlage gegen
  einen Nutzen nur im Eckfall; mitten in der Stabilisierung geht die Abwägung andersherum (JustChr 09-16).
- **T3b — Observed-Sperre + Wartezeit:** In-flight deckt die Wartezeit schon; die Sperre hätte nach dem Abschluss ein
  echtes externes Öffnen verschluckt ((e)).
- **E4 Fensterregel ohne Aus-Meldung (`min(jetzt − Ventil-Ein, geplant)` mit Toleranz max(1, Marge)):** ein
  unberichteter Schluss bis ~9 s zu früh würde `completed` ((b), SP-4).
- **Neustart nach der Wartezeit auf dem gespeicherten Fenster abrechnen:** Zwilling von #3 ((a), SP-1).
- **Schwelle des Sofort-Abschlusses beim Neustart zurück auf `planned` (SP-2-Split):** öffnet beim Neuladen des
  Config-Entrys die Lücke für einen zweiten Dispatch neben dem stehengebliebenen alten Backstop (Design 5).
- **Master beim Neustart in der Wartezeit wieder anfordern:** Pumpe an, Kick, Master-Settle für ein geschlossenes Ventil ((f)).
- **Stopp vor dem Ende auf der gespeicherten Aus-Meldung (SP-6):** vor der Entscheidung der Entprellung könnte es ein
  Blip sein ((c)).
- **Stopp in der Wartezeit als schlichter Teil-Lauf (SP-7):** `partial` ohne `irrigation_finished` und Kalibrierprobe,
  wo heute `completed` stünde ((d)).
- **Stopp-Zweig ohne `close_valve`-Tor:** der Watcher-Teil-Lauf ohne Aus-Meldung würde ab `RUN_VALVE_ON` statt auf der
  Uhr seiner Entscheidung gebucht; ebenso verworfen Option (i), die Basisregel mit `actual_s=elapsed` zu versehen
  (`dry3-logs/T5.md`, offene Frage 1).
- **SP-3-Test an der Grenze +604:** mit dem Backstop-Double pinnt er 601, ein Ergebnis, das die Produktion dort nicht
  liefert. Mit echtem Backstop sind beide Timer zur selben Zeit (609) fällig, und die Timer-Reihenfolge entscheidet: in
  Produktion feuert der zuerst gestellte Backstop (--> `planned_s`); im Harness ergaben zwei Messungen verschiedene Sieger
  (Gegenprüfung SP-3 auf `tmp/drop-6-10`: 601; T8-Prüfung auf `dry3`, `dry3-logs/T8-sp3-restart-at-604.txt`: 600). Eine
  Assertion an diesem Gleichstand pinnt keine Eigenschaft; der Test liegt deshalb bei +602.
- **`zone_finish_grace_seconds` ohne Aufrufer stehen lassen:** toter Helfer nach (e); aus T2 herausgefaltet.
- **Neustart ohne Aus-Meldung immer `completed` mit `planned_s`** und **ungedeckelt wie heute** (Revision 2): durch (b)
  überholt, der Neustart ohne Aus-Meldung folgt jetzt der Basisregel.

## End-to-End-Kriterium (vor dem Merge, E10)

Beweisziel: der Watcher schließt das normale Laufende auf echten Ventilen ab — `completed`, `actual_s` = das vom
Ventil gemeldete Fenster, Abschluss bei Aus + 5 s, nicht der Backstop bei `planned + 9 s`.

### 1. HA-Test mit dem Wartezeit-Emulator

Gebaut am 19.09., getrennt von `sonoff_emu_*`, weil der Verteiler Gardena1 auf `input_boolean.sonoff_emu_valve` Pulse zählt:

- `input_boolean.grace_emu_valve` (Ventil); `binary_sensor.grace_emu_flowing` (Template, laufend; `availability` =
  `input_boolean.grace_emu_unavailable` aus) als Confirm-Entität;
- `input_number.grace_emu_off_delay` (−10 … 60 s, Schritt 0,1, steht auf 0) verschiebt den Schluss (positiv = späte
  Meldung wie Tuya, negativ = früh);
- `script.grace_emu_run` (Feld `seconds`, `mode: restart`: öffnen, `seconds + off_delay` warten, schließen);
  `script.grace_emu_stop` (bricht das Lauf-Skript ab, schließt das Ventil; der `stop_service` der Zone);
- `input_boolean.grace_emu_master` (Test-Master, nur während des Tests als `irrigation_plus`-Master gesetzt).
- Geprüft am 19.09.: `off_delay` 2,5 + `seconds` 3 --> offen 5,502 s; der `unavailable`-Schalter macht `flowing`
  `unavailable`, danach `off`.

Service-Zone: `run_service` = `script.grace_emu_run`, `duration_field` = `seconds`, Einheit Sekunden, `confirm_entity` =
`binary_sensor.grace_emu_flowing`, `stop_service` = `script.grace_emu_stop`, `latency_margin` 4 (Panel-Zeile erscheint
unter „Confirm entity“, verschwindet ohne sie). Gesteuert von einem HA-Skript auf HA-Test (setzt `off_delay`, startet
den Lauf, stoppt/lädt zur rechten Zeit), damit keine MCP-Latenz in die Zeitmessung eingeht; ausgewertet danach lesend aus
Recorder und Diagnostics. HA-Test ist für diesen Test freigegeben (User 19.09.); vor jedem schreibenden Aufruf die
Instanz nennen, Routing strikt per Präfix `mcp__HA-Test__`. Auf HA-Test läuft derselbe Code wie im Pre-Release
(Aufspielweg: Plan, Task 15).

Szenarien (geplantes Fenster P, kurz; genaue Werte legt der Plan fest). Ergebnisse: **nicht gemessen**.

| # | Einstellung | Bestanden, wenn |
|---|---|---|
| 1 | Normalende, `off_delay` 0 | `completed`; `actual_s` = Fenster aus dem Recorder ±1 s; Abschluss (`last_irrigation`) = Aus + 5 s ±0,5 s |
| 2 | späte Meldung in der Marge, `off_delay` +2,5 | `completed`; `actual_s` ≈ P + 2,5 (über `planned_s`); Abschluss = Aus + 5 s, vor P + 9 |
| 3 | früher Schluss in der Marge, `off_delay` −2 | `completed`; `actual_s` ≈ P − 2 |
| 4 | früher Schluss jenseits der Marge, `off_delay` −6 | Teil-Lauf; `actual_s` ≈ P − 6; Abschluss = Aus + 5 s |
| 5 | späte Meldung jenseits der Marge, `off_delay` +6 | Abschluss beim Backstop P + 9; `completed`, `actual_s = planned_s` (bekannter Fall #3; die Aus-Meldung bei P + 6 steht nur im Recorder) |
| 6 | unberichteter Schluss (`grace_emu_unavailable` vor dem Schluss an, danach aus) | keine Aus-Meldung; Basisregel (b) |
| 7 | Stopp in der Wartezeit bei noch „an“ (großes `off_delay`, Stopp bei P + 3) | Ventil durch `script.grace_emu_stop` zu; `completed`, `actual_s = planned_s`; `irrigation_finished` einmal |
| 8 | zweiter `run_zone` bei P + 3 | abgelehnt; `script.grace_emu_run` nicht neu gestartet; genau ein Verlaufseintrag |
| 9 | Neustart in der Wartezeit: Marge 30 vor dem Lauf gesetzt (Wartezeit 35), Config-Entry-Reload zwischen P und P + 35 (derselbe Wiederaufnahme-Pfad) | Backstop neu gestellt, Watcher neu aufgenommen, `input_boolean.grace_emu_master` durch den Reload nicht angefordert ((f)); Abschluss durch Watcher oder Backstop; genau ein Verlaufseintrag |

Im Plan (Task 15) heißen die Szenarien S1 (1), S2 (2), S8 (3), S9 (4), S3 (5), S5 (6), S4 (7), S7 (8) und S6 (9); dort
stehen die genauen Werte (P = 60 s) und, wie `irrigation_finished` je Szenario gezählt wird (Hilfs-Automation ins
Logbuch: 1 bei jedem `completed`, 0 bei 4 und 6).

Dazu in jedem Szenario: keine Exception von `irrigation_plus` im Log. Ein echter HA-Neustart dauert länger als die
Wartezeit, deshalb Szenario 9 über den Reload. Dabei bleibt der Backstop-Timer des alten Koordinators stehen
(vorbestehender Befund `async_unload`), fällig zur selben Zeit wie der neue; `_sc_finish_run` ist idempotent, daher das
Kriterium „genau ein Verlaufseintrag“. Wie das Nicht-Anfordern des Masters sichtbar gemacht wird (der Master hält beim
Reload noch den Dispatch-Hold), legt der Plan fest. `grace_emu_master` wird nach dem Test wieder als Master entfernt.

**Grenze:** der Emulator meldet ohne Funk-Latenz; `off_delay` verschiebt Schluss und Meldung gemeinsam. Er belegt die
Mechanik, nicht das Verhalten der echten Ventile.

### 2. HA-Prod vor dem Merge

Fork-Pre-Release: `production` neu auf upstream `2b2c403b` gebaut + `fix/backstop-grace` + Branding (Rezept Memory
`hasi-production-on-upstream`: Versionen synchron, Release-ZIP aus dem SHA, `en.json`-URL-Fix). Installieren und
Neustart nur mit ausdrücklicher Freigabe. Danach je Zone EIN kurzer manueller `run_zone`, **vom User ausgelöst**: Beet
(Tuya, Minuten) und Kirschlorbeer (SONOFF, Sekunden). Auswertung lesend aus dem Recorder:

- `completed`; `actual_s` = gemeldetes Fenster ±1 s (Beet erwartet über `planned_s`, Meldung 2–3 s nach dem Fenster;
  Kirschlorbeer innerhalb ±0,7 s); Abschluss = Aus + 5 s ±0,5 s, nicht `planned + 9 s`; keine Exception im Log.
- Schließt ein Lauf bei `planned + 9 s` mit einer Aus-Meldung im Recorder, prüfen, ob die Latenz über der Marge lag oder
  Attribut-Updates die Entprellung am Leben hielten (SP-10). Die Aus-Meldung steht danach nicht mehr im Datensatz (der
  Abschluss entfernt ihn), nur im Recorder.
- Natürliche Läufe danach als zusätzlicher Beleg (Kirschbaum: Laufzeit, Reihenfolge und Ventil-Timing verwertbar,
  Durchfluss als Messquelle gesperrt, Memory `hasi-kirschbaum-hose-defect`). Keine Läufe erzwingen.

Ergebnis als Kommentar auf dem PR entwerfen, vorlegen, nach Freigabe posten, dazu auf #139 ein Satz mit Link; erst
danach der Merge.

## Revision 3 (2026-09-19)

Gegenüber Revision 2 (Stand 15.09., Basis `0b418644`, alle vier abtrennbaren Teile noch zur Wahl):

- **Basis** `0b418644` --> `2b2c403b` (#146 gemergt). Die #139-Änderungszeilen sind auf beiden Basen identisch
  (`scratch/d4.txt` = `scratch/d5.txt`).
- **Umfang nach JustChrs Regel** (E8; 5692654650): T6 und T10 raus; T3b zuerst drin, nach unserer Korrektur der
  Prämisse (5740280769: `observed_watering.py:138` + In-flight decken die Wartezeit) raus (5740329987); T7 drin, erweitert
  um (c) und (d); T9 drin, mit Tests am Dispatch (JustChrs Wunsch in 5692654650, bestätigt in 5740329987).
- **E3** auf das In-flight-Fenster verengt; **E4** ersetzt durch (b) (Watcher) und (a)/(f) (Neustart); **E1**
  präzisiert (Toleranz nur mit Aus-Meldung bzw. im Stopp in der Wartezeit).
- **Design 2:** der Backstop schließt immer mit `planned_s` ab; die zwei Auslöser des bekannten Falls sind benannt
  (SP-10).
- **Design 3:** Watcher-Weg zusätzlich an `RUN_VALVE_OFF` gebunden (b); neuer Abschnitt 3.2 für den Stopp mit (c), (d)
  und dem `close_valve`-Tor; keine Zusage `actual_s <= planned_s` (SP-5).
- **Design 4:** Zeitfenster-Preis und Observed-Sperre gestrichen; Garantie am Dispatch und die Sub-Sekunden-Lücke
  (bekannt und unverändert, 5740329987) beschrieben; Leser-Liste aus SP-9.
- **Design 5:** Neustart-Tabelle nach T8 neu: nach der Wartezeit `planned_s` egal was gespeichert ist (a); in der
  Wartezeit kein Master, Re-Arm, Neuaufnahme (f); Reihenfolge Backstop gegen Entprellung (SP-3); Begründung der Schwelle
  über das Neuladen des Config-Entrys (Gegenprüfung zu SP-2).
- **Design 6:** `zone_finish_grace_seconds` entfällt, TS-Kommentar ohne Backend-Helfer (e).
- **Tests:** Liste auf `dry5`, am Abend auf `dry6` gezogen; keine Tests von T3b/T6/T10; T3 +1 Echt-Timer-Test für den
  verpassten Schluss (dry6), T5 +2 Pins für (b) und +1 Pin für das gestrichene T6 (dry6), T7 13 Tests, T8 10 Tests mit
  echtem Backstop im SP-3-Test, T9 +5 Tests (Dispatch, Marge, Anker, Grenze). Einziger geänderter Pin-Wert `(2, 600)` -->
  `(2, 609)`; `tests/test_confirm_reserve.py` unberührt. Der fehlende eigene Real-Timer-Test für den verpassten Schluss
  (Kritik in `wf-scope-answer.json`, erneut in `wf-rev3.json`) steht seit dry6 in T3; dazu der Pin für das gestrichene
  T6 in T5.
- **Reichweite** um die Punkte erweitert, die JustChrs Liste fehlten (Gegenprüfung in `wf-scope-answer.json`,
  `result.sister`): Pumpen-Hold, Einwirkzeit unter `rotating`, `irrigation_finished`/`last_irrigation`/aufgeschobene
  Berechnung, Panel mit Stop, verworfene Dispatches, Berechnungs-Aufschub, Stopp ab `RUN_VALVE_ON`, Neustart in der
  Wartezeit, `actual_s` über `planned_s`.
- **„Ausdrücklich nicht dazu“** neu gegliedert in die PR-Text-Liste (T6 mit beiden Auslösern, (a), (b), (c),
  Sub-Sekunden-Lücke, T10 mit den drei Korrekturen, T3b) und die übrigen Punkte; der Issue-Entwurf zum Zeitfenster-Preis
  liegt korrigiert in `rev3/issue-window-pricing.md`.
- **Verworfen** um T6, T10, T3b, E4, den SP-2-Split, das Master-Wiederanfordern, SP-6/SP-7 und die zwei SP-3-Testvarianten
  ergänzt.
- **Methode:** Nachvollzug der `dry6`-Commits (zuerst `dry5`) statt Neubau (E9), Plan als kompakte Revision 3.
- **End-to-End:** vor dem Merge statt danach (JustChr 5740329987); HA-Test mit dem neuen Wartezeit-Emulator und einem
  HA-Skript statt `sonoff_emu_*` per MCP; HA-Prod über ein Pre-Release mit je einem vom User ausgelösten Lauf je Zone.
- **Probelauf-Geschichte:** `dry2/backstop-grace` (alle Tasks, `0b418644`) --> `tmp/drop-6-10` (T6/T10 gestrichen) -->
  `dry3/backstop-grace` (Entscheidungen a–f, T9-Tests, Texte; `wf-dry3.json`, `dry3-logs/`) --> `tmp/dry3-drop-3b` -->
  `dry4/backstop-grace` (Helfer in T2/T11 herausgefaltet) --> `dry5/backstop-grace` (auf `2b2c403b` rebased, dist in T12
  neu gebaut) --> `dry6/backstop-grace` (19.09. abends: Echt-Timer-Test für den verpassten Schluss in T3, T6-Pin in T5,
  neue Proben für jeden bis dahin ungefangenen Test; nur Tests und zwei Nachrichten geändert, `dry6-logs/`).
- **Nachtrag 19.09. abends:** Befunde der Vollständigkeits- und der Nachvollzugs-Prüfung (`wf-rev3.json`) eingearbeitet:
  Live-Test mit allen neun Szenarien und `irrigation_finished` gezählt; Ergebnis als Kommentar auf dem PR, von #139
  verlinkt; Verweis auf den korrigierten Issue-Entwurf; Commit-Zeile und MSG-SAME in jedem Task des Plans.

## Nachtrag: Befunde der Schluss-Review (2026-09-19)

**Quelle:** die Schluss-Review von Task 13 auf `fix/backstop-grace` (Stand `66763c34`, zehn Commits auf `2b2c403b`),
Ergebnis in `D:/Entwicklung/HASI/pr139-work/wf-task13.json` (`result.review`). Verdikt: „I found no correctness bug in
the grace mechanics themselves“ — Timer, Entprellung gegen Backstop, Stopp, Neustart, In-flight und die Abgrenzung
gegen Batch, OpenSprinkler, Verteiler und write-only halten wie beschrieben. Fünf Befunde: zwei wichtige (R1, R2),
drei kleine (R3, R4, R5).

Der User hat am 19.09. je Befund entschieden. Gebaut wurde zuerst als Probelauf `dry7/backstop-grace` (vier Commits
C1–C4 auf `66763c34`, Worktree `D:/Entwicklung/HASI/pr139-work/dry2`, Protokolle `dry7-logs/C1.md` bis `C4.md`,
Schlussprüfung `dry7-logs/final.md`). Der Nachvollzug auf dem echten Branch steht im Plan als Task 13b, in derselben
Form wie T1–T12 (E9).

**SHA-Korrektur 20.09.** Dieser Abschnitt nannte C1–C4 zuerst unter ihren `dry7`-SHAs. Die gehören dem
Probelauf-Branch und sind von `fix/backstop-grace` aus **nicht erreichbar** — sie lösen nur so lange auf, wie der
Worktree `dry2` und sein Branch existieren, und verschwinden mit dem nächsten `gc`. Da hier steht, was **ausgeliefert**
wurde, nennen Tabelle und „Gebaut“-Zeilen unten jetzt die Branch-SHAs; die `dry7`-SHAs stehen nur noch in dieser
Zuordnung, und der Plan (Task 13b, Spalte `SRC`) behält sie, weil er den Nachvollzug beschreibt und von dort
auscheckt. Die Bäume sind paarweise gleich (`git diff <dry7> <branch>` je leer, 20.09. geprüft), also gilt jede im
`dry7`-Abschnitt gemessene Zahl unverändert für den Branch-Commit:

| | `dry7` (Probelauf) | `fix/backstop-grace` (ausgeliefert) | `git diff` |
|---|---|---|---|
| C1 (R3) | `83dca3a2` | `308c1907` | leer |
| C2 (R5) | `d9b468ee` | `20c2a008` | leer |
| C3 (R1) | `0c6010f1` | `2e829217` | leer |
| C4 (R4) | `ba44620d` | `a0baf8c6` | leer |

Geprüft mit `git merge-base --is-ancestor <sha> fix/backstop-grace`: die vier rechten SHAs sind Vorfahren, die vier
linken nicht. Alle übrigen SHAs in Spec und Plan wurden am 20.09. genauso geprüft; das Ergebnis steht unten unter
„SHA-Prüfung (20.09., alle Vorkommen)“.

| Befund | Art | Entscheidung (User 19.09.) | Umsetzung |
|---|---|---|---|
| **R1** Ratensensor verliert das Intervall über dem Schluss | wichtig, **Loch der Wartezeit** | in diesem PR fixen, eigener abtrennbarer Commit | C3 `2e829217` |
| **R2** Neustart liest `elapsed` vor dem Master-Acquire | wichtig, **vorbestehend** | nicht hier fixen: im PR-Text offenlegen, eigenes Issue | kein Commit; Entwurf `rev3/issue-restart-master-gap.md` |
| **R3** vier Kommentare aus der Zeit vor der Wartezeit | klein | nur Wortlaut | C1 `308c1907` |
| **R4** Doku und Panel-Hilfe nennen die Ein-Meldung nicht | klein | Doku + Panel-Hilfe in 8 Sprachen + PR-Text | C4 `a0baf8c6` |
| **R5** Kopf-Test läuft gegen das Backstop-Double | klein | einen Dispatch-Test mit echtem Timer | C2 `20c2a008` |

R1 ist der einzige Produktivcode-Fix; C1 ist kommentar-only, C2 reiner Test, C4 Doku/Übersetzungen/dist.

### R1 — Ein Ratensensor verliert bis zu einem Poll-Intervall über dem Schluss (wichtig, Loch der Wartezeit)

**Befund.** `FlowMeter._sample_rate` schreibt jedes Intervall mit der Rate seines RECHTEN Endpunkts gut
(`flow_metering.py:156-164` auf `2b2c403b`). Vor der Wartezeit rechnete der Backstop am geplanten Ende ab, da war das
Ventil noch offen: die Schlusslesung sah Fluss, verloren waren nur die 2–3 s zwischen Plan und echtem Schluss. Mit der
Wartezeit wird ein bestätigter Lauf frühestens `SERVICE_WATCH_SETTLE_SECONDS` (5 s) nach der Aus-Meldung abgerechnet
(Watcher) oder bei `planned + Wartezeit` (Backstop). Die Lesung, die das Intervall über dem Schluss schließt — ein
15-s-Tick danach oder die Schlusslesung in `_sc_finish_flow` — sieht das Wasser schon stehen, und das ganze Intervall
wird mit 0 gutgeschrieben: bis zu ein `FLOW_POLL_INTERVAL` (15 s, `const.py:508`) echten Flusses geht verloren, wenn das
Ventil nach seinem Plan schließt. Die Gegenrichtung (Sensor hält seinen letzten Wert, also zu viel) stand schon in der
Reichweite, diese Richtung nicht.

**Beleg (Review-Szenario).** 300-s-Lauf, Ratensensor 10 L/min, fällt ~1 s nach dem Schluss auf 0. Letzter Tick mit
Fluss bei +288, Ventil zu bei +302, Meldung +302,5. Heute: Schlusslesung des Backstops bei ~+301 sieht 10 L/min,
(288, 301] wird gutgeschrieben, ~1 s fehlt. Mit der Wartezeit: Entprellung entscheidet +307,5, Schlusslesung 0,
(288, 307,5] wird mit 0 gutgeschrieben — ~14 s, rund 2,3 L von ~50 L (4,7 %). Die gemessene Menge steuert die absolute
Eimer-Abstimmung und die Kalibrierprobe, beide also zu niedrig.

**Entscheidung (User 19.09.).** In diesem PR fixen, eigener Commit: **trägt der abzurechnende Lauf eine gespeicherte
`RUN_VALVE_OFF`, endet die Rate-Integration an der Aus-Meldung** — das letzte Intervall bis zur Meldung mit der zuletzt
gemessenen Rate, die Lesung nach dem Schluss zählt nicht. Läufe ohne Aus-Meldung und Zähler (Totalizer) behalten das
heutige Verhalten. Nach E8 ist das ein Loch, das die Wartezeit selbst öffnet: vorher las der Backstop vor dem Schluss.
Der Punkt „Stopp des Durchfluss-Samplers bei der Aus-Meldung“ unter „Sonst nicht Teil des Fixes“ bleibt gültig:
gestoppt wird der Sampler nicht, gerechnet wird beim Abschluss.

**Gebaut (C3 `2e829217`, `fix(flow): end a confirmed run's rate integration at the valve's off report`).**

- `FlowMeter` merkt sich je angenommener Ratenprobe, die seine Uhr vorstellt, eine Marke `(at, bis dahin
  gutgeschriebene Liter, Rate in L/min)` — angehängt genau dort, wo `_last_at` vorrückt; eine nicht vorrückende Probe
  erzeugt also keine Marke. Die umgerechnete Rate wird einmal berechnet und wiederverwendet (dieselben
  Float-Operationen in derselben Reihenfolge), `delivered()` bleibt für jeden anderen Nutzer bit-gleich.
- Neu `FlowMeter.end_rate_at(at)` (`flow_metering.py:198` auf dem Endstand): die letzte Marke bei oder vor `at` ist der
  Stand der Integration dort; das Intervall von ihr bis `at` wird mit der Rate dieser Marke gutgeschrieben (der letzten
  mit Wasser gemessenen), begrenzt durch `max_gap_s` (`FLOW_MAX_GAP_SECONDS` = 60, `const.py:512`) wie jedes Intervall,
  und jede spätere Probe fällt heraus, weil `_delivered` auf den Stand der Marke zurückgesetzt wird. Keine Marke bei
  oder vor `at` --> 0.0, der Aufrufer fällt auf sein Zeitvolumen zurück (`delivered()` bleibt ohne jede Lesung `None`).
  Ein Totalizer kehrt sofort zurück: sein Zähler steigt nur für geflossenes Wasser, eine späte Lesung gehört zum Lauf.
- `_sc_finish_flow(zone_id, run=None)` (`self_closing.py:311`) liest wie heute einmal ab und ruft danach, wenn `run`
  eine `RUN_VALVE_OFF` trägt, `meter.end_rate_at(off − started)` auf der Uhr des Meters. Erst lesen, dann schneiden ist
  ein Pfad für beide Meter-Arten: der Totalizer behält seine Schlusslesung, dem Ratenmeter wird sie abgeschnitten.
  `_sc_finish_run` und `async_stop_self_closing` reichen ihren Datensatz durch; die drei Aufrufer, die nur einen Meter
  verwerfen (`_sc_start_flow_sampling`, fehlgeschlagener Confirm, Ausnahme im Aufbau), reichen nichts.
- **Reichweite des Schnitts** (am Datensatz entschieden, nicht am Pfad): Watcher-Abschluss (abgeschlossen und Teil-Lauf
  auf dem Fenster), Stopp in der Wartezeit (d), Stopp vor dem Ende (c) mit noch entprellender Aus-Meldung — `actual_s`
  bleibt dort bis zum Stopp gemessen, (c) ist eine Regel für die Teil-Lauf-Entscheidung, der Fluss ist eine Messung —,
  und der Backstop, der mit der Meldung im Datensatz feuert (der Datensatz behält `actual_s = planned_s`, #3/T6
  unverändert; die Regel sagt, wann das Wasser stand, nicht wer abrechnet).
- **Unverändert:** Läufe ohne Aus-Meldung (write-only, nicht prüfbar, `on --> unavailable --> off`, vom Neustart
  wieder aufgenommen, Backstop vor der Meldung), Totalizer, OpenSprinkler und Batch (ihre Datensätze tragen nie
  `RUN_VALVE_OFF`), der klassische und der metered Runner, Verteiler und Observed (rufen `end_rate_at` nie), ein
  Neustart (der Meter lebt nur im Speicher und ist danach weg).
- **Verworfen** (`dry7-logs/C3.md`): den Sampler bei der Aus-Meldung stoppen (koppelt Watcher und Meter, ein Blip
  löscht die Meldung wieder, ein Tick kann zwischen `last_changed` und die aufzeichnende Auswertung fallen); die
  Schlusslesung bei gespeicherter Meldung auslassen (schreibt das Intervall über dem Schluss trotzdem nicht gut und
  nimmt Ticks zwischen Schluss und Abschluss nicht zurück); linke Endpunkte für jede Probe (änderte die geteilte Engine
  für klassisch, Verteiler und Observed); eine künstliche Probe zum Aus-Zeitpunkt (ein Tick nach dem Schluss macht `at`
  nicht vorrückend, die Engine ignoriert sie); nur auf den Fenster-Pfaden schneiden, mit einem Flag aus `actual_s`
  (ließe Backstop- und Teil-Lauf-Pfad nach dem Schluss lesen und fügte einen Parameter hinzu, wo der Datensatz es schon
  sagt); eigene Tick-Historie in `self_closing.py` (dupliziert Lücken- und Umrechnungsregeln außerhalb der
  einheitengetesteten Engine).
- **Eine Abweichung vom Entwurf,** vom Lint gefunden: die Suche „letzte Marke bei oder vor `at`“ war zuerst eine
  `for … else`-Schleife; `ruff` B007 rügte die Schleifenvariablen, also
  `next((m for m in reversed(self._rate_marks) if m[0] <= at), None)` — gleiches Verhalten, erneut durch alle Tests und
  Proben belegt.

**Tests.** 8 End-to-End in `tests/test_service_watch.py::TestAConfirmedRunsFlowEndsAtItsOffReport` (echtes `hass`,
echter Watcher, echter Sampler und echtes Intervall unter einer eingefrorenen Uhr, die in Schritten von höchstens einem
Poll gestellt wird, damit jeder 15-s-Tick zu seiner Zeit feuert; Rate 10 L/min, `_timed_volume_l` 1.0, damit eine
verlorene Messung nicht als Wert durchgeht; Fixture `sensor.zone_flow`, E7):

| Test | Fall | Erwartet |
|---|---|---|
| `test_a_close_settled_by_the_watcher_is_metered_to_its_off_report` | 612 s Plan, Aus +614, Sensor danach 0 | 102,333 L (heute 100,0) |
| `test_a_sensor_that_holds_its_last_value_is_not_metered_past_it` | Sensor hält 10 L/min | 102,333 L (heute 103,167) |
| `test_a_partial_settled_on_its_window_is_metered_to_its_off_report` | Aus +598, Teil-Lauf auf dem Fenster | 99,667 L |
| `test_a_stop_in_the_grace_is_metered_to_the_off_report` | (d), Aus +614, Stopp +616 | 102,333 L |
| `test_a_stop_before_the_plan_is_metered_to_a_stored_off_report` | (c), Aus +298, Stopp +301 | 49,667 L, `actual_s` 301 |
| `test_the_backstop_meters_to_an_off_report_it_beat_to_the_settle` | 605 s Plan, Aus +611, Backstop +614 | 101,833 L, `actual_s == planned_s == 605` |
| `test_a_close_nobody_reported_is_metered_as_before` | `on --> unavailable --> off`, Basisregel (b) | unverändert 100,0 L |
| `test_a_totalizer_keeps_the_climb_it_reports_after_the_close` | Zähler meldet nach dem Schluss nach | 102,333 L |

Dazu 8 Einheiten in `tests/test_flow_meter.py`: `test_end_rate_at_holds_the_last_rate_to_the_cut_and_drops_later_samples`,
`…_holds_the_converted_rate`, `…_bridges_no_wider_gap_than_a_sample_would` (60 s überbrückt, 75 s nicht),
`…_a_sample_keeps_that_samples_credit`, `…_before_any_reading_credits_nothing`, `…_without_any_reading_stays_none`,
`…_ignores_a_sample_that_did_not_advance`, `…_leaves_a_totalizer_alone`.

RED (Tests zuerst, Produktivcode unberührt): `14 failed, 37 passed, 3 errors`, darunter
`assert 100.0 == 102.33333333333333 ± 1.0e-02` (Watcher), `assert 103.16666666666667 == 102.33333333333333 …`
(haltender Sensor), `assert 97.5 == 99.66666666666667 …` (Teil-Lauf), `assert 100.0 == 102.33333333333333 …` (Stopp in
der Wartezeit), `assert 47.5 == 49.666666666666664 …` (Stopp vor dem Plan), `assert 100.0 == 101.83333333333333 …`
(Backstop mit Meldung) und 8× `AttributeError: 'FlowMeter' object has no attribute 'end_rate_at'`. Die zwei Pins, die
sich NICHT ändern dürfen (ohne Aus-Meldung 100,0 L; Totalizer 102,333 L), waren schon am alten Code grün; die 3 Errors
sind Lingering timer der drei RED-Tests, die vor ihrer Entprellung abbrachen, und sind im GREEN weg. GREEN: `51 passed`.

**Mutationsproben:** 10, alle gefangen (`dry7-logs/C3.md`, zwei Läufe mit gleichem Ergebnis): Datensatz nicht
durchgereicht (in `_sc_finish_run` bzw. in `async_stop_self_closing`), erst schneiden dann lesen, letztes Intervall
ohne Lückengrenze überbrückt, Marke nur strikt vor dem Schnitt (`m[0] < at`), ohne Marke den heutigen Stand behalten,
Totalizer-Tor entfernt, rohe statt umgerechnete Rate in der Marke, Marke bei jeder Probe statt nur bei vorrückender,
letztes Intervall gar nicht gutgeschrieben (10 Tests fallen).

### R2 — Beim Neustart wird `elapsed` vor dem Master-Acquire gelesen (wichtig, vorbestehend)

**Befund.** In `async_resume_self_closing_runs` wird `elapsed` vor `await self.async_master_acquire(...)` gelesen. Ist
die Pumpe aus, schläft dieser Aufruf die Kick-Pause und das Master-Settle (Default 10 s, `const.py:1039`); der danach
mit `planned + grace − elapsed` gestellte Backstop ist also rund 10 s nach dem Ende des In-flight-Fensters fällig. In
diesen Sekunden liest die Zone „nicht in flight“, während Datensatz, Watcher und Backstop leben — genau die Invariante,
die die Anker-Tests aus T9 pinnen (In-flight endet, wenn der Backstop fällig ist). Dieselbe Form hat der Basiscode
(`planned − elapsed` nach demselben `await`): **die Wartezeit öffnet dieses Loch nicht**, sie verschiebt es mit. Der
Block wird von diesem PR allerdings ohnehin umgeschrieben.

**Beleg (Review-Szenario).** Master konfiguriert, HA startet 100 s in einen 600-s-Lauf neu, Marge 4. Die
Wiederaufnahme schläft von +100 bis +110 und stellt dann 509 s: Backstop fällig +619, In-flight endet +609. Wird die
Aus-Meldung verpasst oder kommt sie später als die Marge, passiert ein geplanter, manueller oder `run_zone`-Dispatch
bei +612 den Wächter, nimmt `sc:{zone}`, öffnet das Ventil und pollt den Confirm; bei +619 rechnet der alte Backstop
den ALTEN Datensatz ab, gibt das geteilte Token frei (die Pumpe darf 5 s später unter offenem Ventil ausgehen) und
bucht gegen den Meter des neuen Laufs — der Doppel-Dispatch, den JustChr „the worst outcome in this whole issue“
nannte. Der Schlaf verzögert außerdem die folgenden Datensätze derselben Schleife um dasselbe Maß.

**Entscheidung (User 19.09.).** Nicht in diesem PR. Nach E8 ist es kein Loch, das die Wartezeit öffnet; der PR-Text
nennt es neben der Sub-Sekunden-Lücke als vorbestehend und unverändert, und es bekommt ein eigenes Issue (Englisch,
Entwurf `D:/Entwicklung/HASI/pr139-work/rev3/issue-restart-master-gap.md`) mit Szenario und Einzeiler-Fix: die
Restlaufzeit NACH dem Acquire berechnen oder den Backstop vor dem Acquire stellen. Testskizze im Issue: ein Neustart,
dessen Master-Acquire die eingefrorene Uhr um das Settle vorstellt, prüft, dass der Backstop bei
`RUN_STARTED + planned + grace` fällig ist.

**Nicht gebaut.** Weder in `dry7` noch auf dem Branch gibt es dazu einen Commit; `git diff --stat 66763c34 a0baf8c6`
enthält keine Zeile aus diesem Block (`dry7-logs/final.md`, Abschnitt 6).

### R3 — Vier Kommentare beschreiben noch die Zeit vor der Wartezeit (klein)

**Befund und Beleg.** (1) `_sc_finish_run`, Kommentar auf `planned_s`: „(the run ran for its full planned duration)“ —
ein abgeschlossener Lauf kann jetzt ein Fenster bis zu max(1 s, Marge) unter dem Plan oder über ihm haben. (2)
`_sc_schedule_cleanup`-Docstring: „Schedule the cosmetic finish after the run's planned duration“ — die
Service-Aufrufstellen übergeben `planned + Wartezeit`. (3) Docstring von `async_resume_self_closing_runs`: „if the run
is overdue it has already closed (finalise); if it is still within its window …“ — „overdue“ heißt jetzt jenseits von
Plan UND Wartezeit. (4) Lead-in des `else`-Zweigs der Wiederaufnahme: „Still inside the hardware window: the valve is
open“ — der Zweig deckt jetzt auch die Wartezeit nach dem Fenster, in der das Ventil längst zu ist und der Master nicht
neu genommen wird.

**Entscheidung (User 19.09.).** Nur Wortlaut.

**Gebaut (C1 `308c1907`, `docs(service): describe the finish grace in the restart, cleanup and finish comments`).**
`planned_s` ist jetzt „what the run was sized and credited for“ und sagt nichts mehr über die Laufzeit; der
Cleanup-Docstring sagt „after the given delay“ und erklärt, was der Aufrufer übergibt; der Wiederaufnahme-Docstring
definiert „overdue“ als Plan UND Wartezeit; der `else`-Lead-in heißt „Not yet overdue: … re-armed … re-adopted …
without retaking the master in the grace“, die bestehende Erklärung des `elapsed` kleiner `planned`-Tors folgt
unverändert.

**Kriterien statt Test** (kommentar-only, nicht automatisiert prüfbar): AST-Vergleich mit geleerten Docstrings --> „AST
MATCH: code is identical once docstrings are stripped“; Token-Diff ohne Kommentare und dreifach gequotete Strings -->
3345 Token vorher wie nachher, `MATCH`. Dazu black/ruff sauber und die 8 Service-Suiten `300 passed, 1 error` (der
vorbestehende Lingering-timer-Teardown in
`TestOneOffSampleIsNotEvidenceTheWaterStopped::test_the_run_is_not_settled_before_the_window_is_out`, in der Baseline
belegt und in `wf-task13.json` als zulässiger Lauf-zu-Lauf-Unterschied benannt).

### R4 — Doku und Panel-Hilfe nennen nur die Aus-Meldung (klein)

**Befund und Beleg.** Das Fenster ist `RUN_VALVE_OFF − RUN_VALVE_ON`, die Prüfung vergleicht Fenster gegen Plan
(`_watch_settle_by_window`). Eine Ein-Meldung, die dem physischen Öffnen nachhinkt, verkürzt das Fenster also genau wie
ein früher Schluss: eine Confirm-Entität, deren Ein-Meldung ihrer Aus-Meldung um mehr als die Marge nachhinkt, macht
**jedes normale Ende zum Teil-Lauf** (Gutschrift zurückgenommen, kein `irrigation_finished`, keine Kalibrierprobe). Im
Basiscode wurden solche Läufe abgeschlossen, weil der Backstop zuerst kam. Erreichbares Muster: ein aus dem Durchfluss
abgeleiteter `binary_sensor` — die Form von `binary_sensor.valve_flowing` in den Tests und von `grace_emu_flowing` im
Emulator (E10). Die Doku warnte bisher nur vor der späten Aus-Meldung.

**Entscheidung (User 19.09.).** Doku (`docs/configuration-my-zones.md`, Punkt „Latency margin“) und Panel-Hilfe
(`latency_margin_help` in allen 8 Katalogen: de en es fr it nl no sk) beschreiben die Toleranz über dem **gemeldeten**
Ein-bis-Aus-Fenster, sagen, dass die Marge auch die späte Ein-Meldung auffängt, und empfehlen das Ventil selbst als
Confirm-Entität statt eines Durchfluss-Indikators. Derselbe Punkt in den PR-Text. dist neu bauen (Node 24 = Node-22-CI),
die geänderten Bundles mit `git add -f` stagen (Memory `hasi-i18n-all-languages`).

**Gebaut (C4 `a0baf8c6`, `docs(i18n): explain on-report lag in the latency margin help`).** 11 Dateien, 29/29 Zeilen:
Doku-Punkt, 8 Kataloge und die zwei dist-Bundles, die die Kataloge bündeln (`irrigation-plus.js`,
`irrigation-plus-card-impl.js`; `card.js` und `card-legacy.js` unverändert). Die 7 Übersetzungen sind aus dem eigenen
Wortschatz jeder Sprache gebaut (Label, `confirm_entity`, `flow_sensor`, die Lauf-Ergebnis-Wörter
Abgeschlossen/Teilweise aus `services.history_dialog.results`, das Fenster-Substantiv der Zeitfenster-Schlüssel), nicht
aus dem englischen Satz maschinell übersetzt, und übernehmen das Parallelsatz-Muster des bisherigen Textes derselben
Sprache.

**Kriterien statt Test** (UI-Text, vorher benannt): `tests/test_i18n_completeness.py` grün (keine fehlenden, keine
verwaisten Schlüssel, kein Wert gleich dem englischen) — gemessen `66 passed`; alle 8 Werte nennen (a) das
Ein-bis-Aus-Fenster bzw. die späte Ein-Meldung und (b) das Ventil selbst statt eines Durchflusssensors; der Doku-Punkt
sagt dasselbe wie die Panel-Hilfe, damit beide nicht auseinanderlaufen; vitest bleibt bei 23 Dateien / 624 Tests; die 8
Service-Suiten unverändert (`309 passed, 1 error`). Alle acht JSON-Dateien wurden nach der Änderung geparst.

### R5 — Der Kopf-Test läuft am Dispatch gegen das Backstop-Double (klein)

**Befund und Beleg.** Der von JustChr verlangte Kopf-Test („a close inside the grace settles via `_watch_finish` with
`actual_s` = the observed window“) lief am Dispatch-Pfad gegen `_coord`s `_sc_schedule_cleanup`-Double, das nie feuert.
Dass der Watcher wirklich zuerst kommt, folgte nur aus der Zusammensetzung: der Arm-Pin `(2, 609)` plus der
Echt-Timer-Test für den verpassten Schluss. Den echten Timer mit einem gewinnenden Watcher gab es nur auf dem
Neustart-Pfad (SP-3).

**Entscheidung (User 19.09.).** Eine Variante am Dispatch-Pfad mit dem ECHTEN Backstop
(`_the_real_backstop_from_here`): Schluss bei +602 gemeldet, auf +608 vorstellen --> `completed`, `actual_s` 602; über
+609 hinaus --> kein zweiter Abschluss, kein Cleanup-Timer übrig.

**Gebaut (C2 `20c2a008`, `test(service): let the watcher beat the real backstop on the dispatch path`).** Neuer Test
`TestAConfirmedRunIsSettledOnItsValveWindow::test_the_watcher_settles_it_before_the_real_backstop_fires`: echter
Backstop vor dem Dispatch gestellt (Marge 4, fällig 609), Uhr bei offenem Ventil bis +601 **gegangen**, Schluss bei
+602 gemeldet, bei +608 Lauf weg, ein Datensatz, `completed`, `actual_s == approx(602)`, ein `irrigation_finished`;
nach +610 weiterhin ein Datensatz, ein Event, eine Master-Freigabe, keine wartende Entprellung, kein Cleanup-Timer.

**Harness-Befund (gilt für jeden künftigen Echt-Timer-Test).** Der erste Entwurf sprang mit `frozen.tick(602)` zum
Schluss, wie `_run_until_the_valve_closes` — und **überlebte** die Probe „Backstop am Plan gestellt“. Wurzel, mit einer
instrumentierten Wegwerf-Kopie belegt: ein Timer, der innerhalb eines `tick`-Sprungs fällig wird, landet nur in der
Ready-Queue der Loop, hinter dem Schritt des Tests; das nächste `_advance` feuert die Entprellung synchron, deren
Abschluss `_sc_cancel_cleanup` ruft, und der eingereihte Backstop wird als abgebrochen übersprungen. Ein Sprung kann
also **nie** zeigen, dass ein Backstop zu früh feuert. Deshalb wird die Uhr über das geplante Ende **gegangen**, bevor
der Schluss gemeldet wird; der Docstring des Tests sagt warum. Die Cleanup-Timer-Assertion steht am Ende, damit die
„kein zweiter Abschluss“-Assertion die dritte Probe trifft.

**Kein RED.** Der Test prüft bestehendes Verhalten (R5 verlangte einen Test, keinen Fix): er war sofort grün
(`1 passed`). Seine Falsifikation sind die Proben (`dry7-logs/C2.md`, je Probe die neue Test-Datei allein und die 7
Service-Suiten):

| Probe | Mutation | neue Test-Datei | gefangen an |
|---|---|---|---|
| `backstop-no-grace` | Dispatch stellt `planned` statt `planned + Wartezeit` | FAILED | `assert 600.0 == 602 ± 1.0e-02` (der Backstop bei 600 schloss für den Plan ab); dazu die zwei Arm-Pins und der Test für den verpassten Schluss |
| `window-route-removed` | Fensterweg im `_watch_finish` auf `if False:` | FAILED | `assert 600.0 == 602 ± 1.0e-02`; dazu 7 weitere Tests |
| `second-settle-unguarded` | weder Abbruch des Backstops beim Abschluss noch Idempotenz-Stopp | FAILED | `c._record_run.assert_awaited_once()` --> „Awaited 2 times“; dazu 5 weitere (verpasster Schluss, T6-Pin, SP-3-Neustart, zwei in `test_self_closing.py`) |
| `finish-keeps-backstop` (ergänzend) | nur der `_sc_cancel_cleanup` beim Abschluss entfernt | FAILED | `assert not c._sc_cleanup_timers()` (das Handle bleibt stehen) |
| `finish-not-idempotent` (ergänzend) | nur der Idempotenz-Stopp entfernt | passed (erwartet) | auf diesem Pfad bricht schon der Abbruch den Backstop ab, der zweite Schutz wird nie erreicht; er bleibt gepinnt von `test_self_closing.py::test_finish_is_idempotent_when_run_missing` |

### Messstand `dry7` (2026-09-20, `dry7-logs/final.md`)

- black `68 files would be left unchanged.`, ruff `All checks passed!` am Endstand `a0baf8c6` (im Probelauf an
  `ba44620d` gemessen, baumgleich).
- Volle Suite gegen die Basis vom selben Tag (`baseline-2b2c403b-fix-0919.txt`): `collected 3022` -->
  `collected 3132`; `7 failed, 3006 passed, 9 skipped, 10 warnings, 320 errors` -->
  `7 failed, 3116 passed, 9 skipped, 10 warnings, 320 errors`. Delta passed = Delta collected = **+110**, also
  ausschließlich neue grüne Tests (+93 aus T1–T12, +17 aus C2/C3). FAILED/ERROR-Namensmengen sortiert verglichen:
  333/333 Zeilen, Diff leer.
- Je Commit im separaten Worktree: C1 `300 passed, 1 error`; C2 `301`; C3 `309` (dazu `tests/test_flow_meter.py`
  allein `43 passed`); C4 `309` — immer derselbe eine vorbestehende Teardown-Error, black und ruff je sauber.
- vitest unverändert `23 passed (23)` / `624 passed (624)`; C1–C4 fassen keine Frontend-Testdatei an.
- dist aus den Quellen neu gebaut (Node v24.15.0), alle vier Bundles identisch zum Commit (nur CR/LF-Rauschen).
- `git diff --stat 66763c34 a0baf8c6`: 15 Dateien, 539 Einfügungen, 43 Löschungen — `flow_metering.py`,
  `self_closing.py`, `docs/configuration-my-zones.md`, 8 Kataloge, 2 Bundles, `tests/test_flow_meter.py`,
  `tests/test_service_watch.py`. R2 erwartungsgemäß nicht im Diff.

### Folgen für die Abschnitte oben

- **Reichweite:** der Punkt zum Durchfluss-Ratensensor ist neu gefasst (Integration endet an der Aus-Meldung, sobald
  eine gespeichert ist).
- **Ausdrücklich nicht dazu:** R2 ist als vorbestehende Neustart-Lücke neben der Sub-Sekunden-Lücke aufgenommen.
- **Tests/Harness:** der Sprung-Befund aus C2 gilt für jeden Test, der einen Timer gegen einen anderen antreten lässt:
  die Uhr über die Fälligkeit **gehen**, nicht springen.
- **Proben:** zu den 133 aus Task 13 kommen 15 aus `dry7` (5 zu C2, 10 zu C3); Task 13b lässt sie auf dem echten
  Branch erneut laufen.

## Nachtrag: Befunde der zweiten Review-Runde (2026-09-20)

**Quelle:** die Review der vier Nachzieh-Commits C1–C4 auf `fix/backstop-grace` (Stand `a0baf8c6`, vierzehn Commits auf
`2b2c403b`), Ergebnis in `D:/Entwicklung/HASI/pr139-work/wf-followups.json` (`result.review`). Verdikt zum einzigen
Produktivcode-Commit: „C3 (2e829217) is correct and well scoped; I found no defect that would change a delivered volume
in a normal run“ — Einheiten, Zeitbasis (der Schnitt läuft auf der Uhr des Meters, nicht auf dem Anker des Datensatzes),
Totalizer-Tor, „keine Aus-Meldung“-Fall und die Abdeckung aller fünf Aufrufstellen von `_sc_finish_flow` einzeln
nachgewiesen. C1 sei kommentar-treu, C2 diskriminiere echt („a backstop armed at the plan would fire inside it and
settle for 600“), C4 sei in allen acht Sprachen zutreffend.

**Fünf Befunde, alle als `minor` eingestuft.** Der User hat am 2026-09-20 entschieden: **alle fünf vor dem
Pre-Release fixen.** Die Nummerierung R6–R10 setzt die erste Runde (R1–R5) fort; in Klammern die Position im
Review-Ergebnis.

| Befund | Ort | Entscheidung (User 20.09.) | Umsetzung |
|---|---|---|---|
| **R6** (1) Schluss-Intervall mit `max_gap_s` (4 Polls) statt einem Poll begrenzt | `flow_metering.py:223` | fixen | C5 `3623e71b` |
| **R7** (2) Kalibrier-Hinweis teilt durch `planned_s`, gemessen ist das Fenster | `self_closing.py:452` | fixen | C5 `3623e71b` |
| **R8** (3) `latency_margin_help` hat die Warte-Hälfte in allen 8 Sprachen verloren | `…/languages/en.json:630` u. a. | fixen | C6 `9da4c0b2` |
| **R9** (4) Französisch benennt die zwei Fenster-Kanten unsymmetrisch | `…/languages/fr.json:411` | fixen | C6 `9da4c0b2` |
| **R10** (5) Spec nennt C3/C4 unter nicht erreichbaren `dry7`-SHAs | dieses Dokument, Nachtrag der ersten Runde | fixen | kein Code-Commit; die SHA-Korrektur oben |

**Abweichung von E9 (Nachvollzug statt Neubau), bewusst und vom User am 20.09. so entschieden.** C5 und C6 wurden
**direkt auf `fix/backstop-grace` mit TDD** gebaut — erst der fehlschlagende Test, dann der Produktivcode —, nicht
erst als Probelauf und dann nachvollzogen. Begründung: E9 galt für den Rumpf, der aus mehreren Probeläufen
(`dry2`…`dry7`) hervorgegangen war; dort ersetzte der Nachvollzug eine bereits gemessene Bauarbeit. R6–R9 sind
dagegen kleine, von der Review NACH den Probeläufen gefundene Korrekturen an vier Dateien: ein achter Probelauf
hätte dieselbe Arbeit zweimal gemacht, ohne neue Evidenz, und die globale Regel „kein Produktionscode vor einem
fehlschlagenden Test“ ist auf dem echten Branch direkt erfüllt und unten belegt (RED vor GREEN, verbatim). Der
Verzicht auf den Probelauf kostet nur das eine, was er sonst liefert — die Vorab-Messung der Suiten-Zahlen —, und
die steht hier stattdessen als Vorher/Nachher gegen die Branch-Basis `a0baf8c6`.

### R6 — Das Schluss-Intervall wird mit vier Polls statt einem begrenzt (klein)

**Befund.** `end_rate_at` begrenzt den Schwanz — das Intervall von der letzten Marke bis zur Aus-Meldung — mit
`_max_gap_s` (`FLOW_MAX_GAP_SECONDS` = 4 Polls = 60 s). Diese Grenze wurde für ein Intervall gewählt, das an
**beiden** Enden eine Lesung hat. Hier ist das ferne Ende eine Ventil-Meldung, keine Flussprobe: bis zu 60 s können
aus einem Sensor extrapoliert werden, der seit der Marke tot ist — genau der Fall, den `_sample_rate` nicht
gutschreibt. Der Docstring („bounded by max_gap_s like any interval“) übertünchte den Unterschied.

**Beleg (Review-Szenario).** 612-s-Lauf, 10 L/min, Zigbee-Flusssensor fällt bei +570 auf `unavailable` (jeder
spätere Tick und die Schlusslesung in `_sc_finish_flow` liefern `None`, `irrigation.py:1125`), Ventil meldet Aus bei
+614. `end_rate_at(614)` findet die Marke bei 570, `dt = 44 <= 60`, und schreibt 44 s × 10 L/min ≈ **7,3 L gut, die
kein Sensor gemessen hat** — vor C3 wurde nach 570 gar nichts gutgeschrieben. `_sc_finish_run` stimmt den Eimer
**absolut** aus den gemessenen Litern ab, der Überschuss wandert also in das Defizit des nächsten Laufs. Die Review
stellte `flow_metering.py:222-224` dem eigenen Kommentar von `_sample_rate` gegenüber
(`flow_metering.py:166-167`: „gap too large … do not credit the recovered rate across it (would over-credit)“) und
wies darauf hin, dass `tests/test_flow_meter.py:377` die 60 s als gewollt pinnte.

**Entscheidung (User 20.09.).** Fixen. Im Normalfall ist der Schwanz ohnehin durch den Meldeverzug begrenzt (eine
Marke liegt innerhalb eines Polls vor dem Schnitt, und jede Probe zwischen physischem Schluss und Meldung liest 0
und wird die Marke), die engere Grenze kostet also nichts: jeder legitime Schwanz in den C3-Tests (letzter Tick 600,
Schnitt 611–614) liegt unter einem Poll.

**Gebaut (C5 `3623e71b`, `fix(flow): bound the off-report tail by one poll and price the advisory on the measured window`, Teil 1).**
`end_rate_at(at, *, poll_s: float | None = None)` nimmt die Kadenz des Samplers und begrenzt den Schwanz mit der
**engsten** Grenze, die es hat: `bounds = [b for b in (self._max_gap_s, poll_s) if b is not None]`, dann
`if not bounds or dt <= min(bounds)`. Die Kadenz wird von der einzigen Schnittstelle durchgereicht, die sie ohnehin
kennt — `_sc_finish_flow` ruft `meter.end_rate_at((off − started).total_seconds(), poll_s=const.FLOW_POLL_INTERVAL)`,
dieselbe Konstante, die `_sc_start_flow_sampling` für sein Intervall liest.

- **Verworfen** (im Commit als NOT-TO-DO festgehalten): den Poll aus `max_gap_s` ableiten (heute
  `FLOW_POLL_INTERVAL × 4` — eine Kopplung, die das nächste Nachziehen einer der beiden Konstanten still bricht);
  die Kadenz am Meter speichern (belastet jeden Aufrufer, der nie schneidet); `_sample_rate` genauso verschärfen
  (dessen Intervalle haben an beiden Enden eine Lesung, wofür `max_gap_s` gewählt wurde).
- Ein Aufrufer ohne `poll_s` behält exakt die bisherige Grenze; `end_rate_at` hat weiterhin genau einen Aufrufer.

### R7 — Der Kalibrier-Hinweis teilt durch den Plan, gemessen ist das Fenster (klein)

**Befund.** Der Flow-Kalibrier-Hinweis rechnet `observed_lpm = measured_l / (seconds / 60.0)`
(`irrigation.py:1245`) — sein ganzer Zweck ist die **beobachtete Rate**. `_sc_finish_run` übergab dafür `planned_s`.
Seit C3 spannen die Liter aber das **gemeldete** An-bis-Aus-Fenster: Zähler und Nenner werden über verschiedene
Fenster gemessen. C3 erzeugt den Bruch nicht (vorher liefen die Liter bis zur letzten Lesung mit Wasser, auch nicht
`planned_s`), dreht aber sein Vorzeichen — ein Ventil, das nach seinem Plan schließt, liefert jetzt Liter für mehr
Sekunden als der Divisor.

**Beleg (Review-Szenario).** Minuten-Ventil, 60-s-Plan, Schluss 4 s zu spät gemeldet: 10 L über ein 64-s-Fenster.
10 L / 60 s liest sich als 10,0 L/min gegen wahre 9,4 L/min — **6,7 % Verzerrung auf jedem Lauf**, in einem Band,
das bei `FLOW_CAL_DEVIATION` = 0,15 mit `FLOW_CAL_MIN_SAMPLES` = 3 beurteilt wird. Auf langen Läufen ist es
vernachlässigbar (0,3 % bei 612 s): ein Effekt kleiner Zonen, kein Blocker.

**Entscheidung (User 20.09.).** Fixen, mit der von der Review vorgeschlagenen Form.

**Gebaut (C5 `3623e71b`, Teil 2).** `_sc_finish_run` preist den Hinweis auf dem Fenster, über das die Liter gemessen
wurden: `await self._flow_calibration_check(zone, measured, planned_s if actual_s is None else actual_s)` —
dieselbe Regel, der das aufgezeichnete `actual_s` schon folgt. Ein Lauf ohne Meldung hat nur seinen Plan, und behält
ihn: **Backstop, write-only, OpenSprinkler und Batch bleiben auf `planned_s`.**

- **Nicht mitgezogen:** das Zeitvolumen oben bleibt auf `planned_s` — es preist das Wasser, für das der Lauf
  **gutgeschrieben** wurde, und das ist der Plan (im Commit als NOT-TO-DO festgehalten).
- **Schwester-Pfad-Check:** die zwei anderen Aufrufer von `_flow_calibration_check` wurden geprüft und übergeben
  bereits das Fenster, das sie gemessen haben (Observed-Watering das externe Öffnen, Verteiler `actual_seconds`) —
  kein Spiegel-Bug.

### R8 — Die Panel-Hilfe nennt nur noch die Toleranz, nicht mehr die Wartezeit (klein)

**Befund.** Die in C4 neu gefasste `latency_margin_help` beschrieb nur noch die Abschluss-Toleranz und ließ die
andere Hälfte dessen weg, was der eine Wert tut: **wie lange die Integration auf die Aus-Meldung wartet, bevor sie
den Lauf ohne sie abschließt.** Diese Hälfte stand im alten Text und steht weiterhin in der Doku — Panel und Doku
widersprachen sich also darüber, was die Einstellung steuert. Die Auslassung war in allen acht Katalogen gleich
(de:411, es:411, fr:411, it:451, nl:411, no:411, sk:411, en:630), also konsequent und kein Ausrutscher einer
Sprache.

**Beleg.** Entfallen war „Irrigation Plus waits this long for the report before it settles the run without it“;
`docs/configuration-my-zones.md:93` trägt es weiter („The integration waits this long for the confirm entity to
report *off* before it settles the run without that report. … A run whose close report never arrives is settled as
complete at planned duration + 5 s + margin.“). Im Code hängen beide Hälften am selben Wert:
`run_finish_grace_seconds` = Settle + eingefrorene Marge, `run_completion_tolerance` = die Marge
(`run_watch.py:304-310`). Szenario der Review: wer für ein schläfriges Ventil die Marge auf das Maximum 30 stellt,
erfährt aus dem Panel nicht, dass Lauf, Verlaufseintrag und Master-/Pumpen-Halt jetzt 35 s nach dem geplanten Ende
abgeschlossen werden.

**Entscheidung (User 20.09.).** Fixen: beide Hälften in allen acht Katalogen, die Warnung vor der späten
Ein-Meldung und die Empfehlung „Ventil statt Durchflusssensor“ aus C4 bleiben.

**Gebaut (C6 `9da4c0b2`, `docs(i18n): say what the latency margin waits for and what it tolerates`).** Alle acht
Texte neu gefasst; jeder trägt jetzt (a) die Wartezeit, (b) die Toleranz auf dem gemeldeten Fenster, (c) das
Auffangen der späten Ein-Meldung und (d) die Empfehlung, auf das Ventil selbst zu zeigen. Jeder Text ist **kürzer**
als der, den er ersetzt (en 560 → 517, de 671 → 591, es 668 → 612, fr 760 → 618, it 703 → 613, nl 661 → 558,
no 631 → 544, sk 571 → 518 Zeichen). `docs/configuration-my-zones.md` trug beide Hälften und die Empfehlung schon
und bleibt **unverändert** — die Richtung des Fixes ist Panel zu Doku, nicht umgekehrt.

Englisch, wie committet:

> „How many seconds this valve may take after the end of its run to report that it closed. Irrigation Plus waits
> this long for that report before it settles the run without it, and the same value is the tolerance on the
> reported on-to-off window: a window that falls short of the planned duration by no more than the margin still
> counts as a complete run, which likewise absorbs a late 'on' report. Only used with a confirm entity — point it
> at the valve itself, not at a flow sensor, which lags the water on both edges.“

### R9 — Französisch benennt die zwei Kanten des Fensters unsymmetrisch (klein)

**Befund und Beleg.** Französisch war die einzige der acht Sprachen, die das Fenster mit einem unsymmetrischen Paar
benannte — `activation` (ein Einschalten) gegen `fermeture` (ein physisches Schließen) —, während Englisch und die
anderen sechs ein symmetrisches An/Aus-Paar verwenden (de „An-bis-Aus-Fenster“, es „ventana de encendido a
apagado“, it „finestra segnalata di accensione-spegnimento“, nl „aan-tot-uit-venster“, no „på-til-av-vinduet“,
sk „okno zapnutia až vypnutia“, en „reported on-to-off window“). Der übrige französische Text zitierte die Zustände
dann korrekt als 'on' und 'off' — zwei Vokabulare für dieselben zwei Kanten.

**Entscheidung (User 20.09.).** Fixen, mit dem von der Review vorgeschlagenen symmetrischen Paar.

**Gebaut (C6 `9da4c0b2`).** `d'activation à désactivation`, passend zum `état activé` desselben Katalogs in
`confirm_entity_help`; zusätzlich der Doppelpunkt mit dem normalen Leerzeichen dieses Katalogs statt eines
alleinstehenden geschützten Leerzeichens. Französisch, wie committet:

> „Nombre de secondes dont cette vanne dispose après la fin de son exécution pour signaler sa fermeture. Irrigation
> Plus attend ce signalement pendant ce délai avant de clôturer l'exécution sans lui, et cette même valeur est la
> tolérance sur la fenêtre signalée d'activation à désactivation : une fenêtre plus courte que la durée prévue d'au
> plus la marge compte toujours comme une exécution complète, ce qui absorbe aussi un signalement 'on' tardif.
> Utilisé uniquement avec une entité de confirmation — pointez-la vers la vanne elle-même, non vers un capteur de
> débit, qui accuse un retard sur l'eau aux deux extrémités.“

Nachgemessen an den **committeten** Blobs (`git show HEAD:<katalog>`): `d'activation à désactivation` vorhanden,
`d'activation à fermeture` nicht mehr.

### R10 — Die Spec nennt C3 und C4 unter nicht erreichbaren SHAs (klein)

**Befund und Beleg.** Der Nachtrag der ersten Runde führte C1–C4 unter den `dry7`-SHAs (`83dca3a2`, `d9b468ee`,
`0c6010f1`, `ba44620d`). Der Branch trägt `308c1907`, `20c2a008`, `2e829217`, `a0baf8c6`;
`git merge-base --is-ancestor 0c6010f1 fix/backstop-grace` scheitert für beide genannten. Die Bäume sind paarweise
gleich (`git diff 0c6010f1 2e829217` und `git diff ba44620d a0baf8c6` je leer) und die festgehaltene Diffstat stimmt
mit dem Branch überein (`git diff --stat 66763c34 a0baf8c6` --> 15 Dateien, 539 Einfügungen, 43 Löschungen), jede
Messung galt also weiter — nur die Zeiger hingen in der Luft und hätten nach einem `gc` nicht mehr aufgelöst. Nach
Regel P1 gehen diese Dokumente auf `archive/design-history`; ein Archiv, dessen SHAs nicht gegen den ausliefernden
Branch auflösen, ist keine Historie.

**Entscheidung (User 20.09.).** Fixen, **vor** dem Schieben ins Archiv.

**Gebaut (kein Code-Commit).** Die SHA-Korrektur oben in diesem Dokument: Entscheidungstabelle und alle
„Gebaut“-Zeilen nennen die Branch-SHAs, die `dry7`-SHAs stehen nur noch in der Zuordnungstabelle, und
`git diff --stat 66763c34 ba44620d` ist zu `… 66763c34 a0baf8c6` geworden. Der Plan behält seine `SRC`-Spalte mit den
`dry7`-SHAs, weil er beschreibt, von wo der Nachvollzug auscheckt, nicht was ausgeliefert ist. Vollständiges
Prüfergebnis für **jeden** SHA in beiden Dokumenten unten unter „SHA-Prüfung (20.09., alle Vorkommen)“.

### C5 — TDD-Beleg (RED vor GREEN, verbatim)

Beide Tests standen **vor** jeder Produktivänderung; Auswahl über `tests/test_service_watch.py` und
`tests/test_flow_meter.py`, `--tb=line`:

```
tests\test_service_watch.py FFF.                                         [ 28%]
tests\test_flow_meter.py ..F.F.....                                      [100%]
D:\Entwicklung\HASI\HAsmartirrigation\tests\test_service_watch.py:746: assert 600.0 == 602 ± 1.0e-02
D:\Entwicklung\HASI\HAsmartirrigation\tests\test_service_watch.py:1209: assert 600.0 == 597 ± 1.0e-02
D:\Entwicklung\HASI\HAsmartirrigation\tests\test_service_watch.py:2156: assert 60.0 == 64 ± 1.0e-02
D:\Entwicklung\HASI\HAsmartirrigation\tests\test_flow_meter.py:385: TypeError: FlowMeter.end_rate_at() got an unexpected keyword argument 'poll_s'
D:\Entwicklung\HASI\HAsmartirrigation\tests\test_flow_meter.py:417: TypeError: FlowMeter.end_rate_at() got an unexpected keyword argument 'poll_s'
================= 5 failed, 9 passed, 111 deselected in 1.54s ==================
```

Der vierte ausgewählte Test — der Pin „Backstop behält den Plan“
(`test_a_close_nobody_reported_keeps_the_plan`) — war von Anfang an grün: er pinnt Verhalten, das sich **nicht**
bewegen darf. GREEN, dieselbe Auswahl nach der Umsetzung:

```
tests\test_service_watch.py ....                                         [ 28%]
tests\test_flow_meter.py ..........                                      [100%]
===================== 14 passed, 111 deselected in 1.67s ======================
```

**Tests von C5** (4 neue Items, 3 bewegte Pins):

| Datei | Test | Fall |
|---|---|---|
| `test_flow_meter.py` | `test_end_rate_at_bridges_no_wider_gap_than_one_poll` (umbenannt aus `…_than_a_sample_would`) | 30,0 s überbrückt (2,5 + 2,5 L), 30,5 s nicht (2,5 L) |
| `test_flow_meter.py` | `test_end_rate_at_without_a_poll_keeps_the_max_gap_bound` **(neu)** | ohne Kadenz gilt `max_gap_s` wie bisher |
| `test_flow_meter.py` | `test_end_rate_at_credits_no_tail_from_a_sensor_dead_since_the_mark` **(neu)** | das Review-Szenario: 95 L, nicht 102,3 L |
| `test_service_watch.py` | `TestTheAdvisoryIsPricedOnTheWindowItMeasured::test_a_late_close_is_priced_on_the_reported_window` **(neu)** | 60-s-Plan, Schluss +64: Divisor 64, `measured / (seconds/60)` == 10 L/min |
| `test_service_watch.py` | `…::test_a_close_nobody_reported_keeps_the_plan` **(neu, von Anfang grün)** | ohne Meldung Divisor 60, am ECHTEN Backstop-Timer |
| `test_service_watch.py` | zwei bestehende Hinweis-Pins (Z. 746, 1209) | 600 → 602 bzw. 600 → 597 |

`tests/test_flow_meter.py` hat damit **zehn** Einheiten zu `end_rate_at` (vorher acht).

**Mutationsproben C5: fünf, einzeln, alle gefangen.** Je Probe Sicherung nach
`D:/Entwicklung/HASI/pr139-work/mut/<name>.bak`, CRLF-erhaltend angewandt, aus der Sicherung zurückgespielt,
sha256 vorher/nachher verglichen und der Baum je wieder auf die vier beabsichtigten Dateien geprüft:

| Probe | Mutation | Ergebnis | gefangen an |
|---|---|---|---|
| `m1` | Poll-Grenze zurück auf `if self._max_gap_s is None or dt <= self._max_gap_s:` | 2 failed, 123 passed | `test_flow_meter.py:390` `assert 5.083333333333334 == 2.5 ± 2.5e-06`; `:418` `assert 102.33333333333333 == 95.0 ± 9.5e-05` — die 7,33 L Phantom-Gutschrift der Review |
| `m2` | Grenze ganz weg (`delivered += rate * dt / 60.0` bedingungslos) | 3 failed, 122 passed | `:390`, `:404` (der Pin ohne Kadenz), `:418` |
| `m3` | `min(bounds)` zu `max(bounds)` | 2 failed, 123 passed | `:390` und `:418`, gleiche Werte wie `m1` |
| `m4` | Divisor zurück auf `planned_s` | 3 failed, 160 passed | `test_service_watch.py:746` `assert 600.0 == 602 ± 1.0e-02`; `:1209` `assert 600.0 == 597 ± 1.0e-02`; `:2156` `assert 60.0 == 64 ± 1.0e-02` |
| `m5` | Divisor **immer** `actual_s` (muss den Backstop-Pin brechen) | 4 failed, 159 passed | `test_service_watch.py:2181` `assert None == 60` (der neue Backstop-Pin), dazu zwei `irrigation.py:1222: TypeError: '<=' not supported …` |

sha256 je Datei vor und nach der Wiederherstellung gleich (`flow_metering.py` `6327a398…e825f3d` bei m1–m3,
`self_closing.py` `dafb1079…04feb9a9` bei m4–m5). `m5` ist die Gegenprobe zu R7: sie zeigt, dass der Fix den
Backstop-Pfad **nicht** mitnimmt.

### C6 — TDD-Beleg (RED vor GREEN, verbatim)

Der neue Pin `tests/test_i18n_completeness.py::test_the_latency_margin_help_says_what_it_waits_for_and_what_it_tolerates`
wurde gegen den Text von `a0baf8c6` geschrieben und fiel:

```
tests\test_i18n_completeness.py:303: in test_the_latency_margin_help_says_what_it_waits_for_and_what_it_tolerates
    assert "waits this long" in text, text
E   AssertionError: How many seconds the reported on-to-off window may fall short of the planned duration and still count as a complete run. That tolerance covers a late 'off' report, ...
====================== 1 failed, 66 deselected in 1.40s =======================
```

GREEN danach: `67 passed in 3.53s` (`tests/test_i18n_completeness.py`).

Der Pin friert je Hälfte **eine** Wendung des englischen Textes ein (`"waits this long"`,
`"still counts as a complete run"`) und **nicht** die sieben Übersetzungen — dieselbe Konvention wie der
Niederschlagsschwellen-Pin darüber; die Schlüsselparität und `test_no_value_is_left_as_the_english_string` decken
die anderen sieben ab.

**Kriterien statt Probe** (UI-Text, vorher benannt; gegen die committeten Blobs mit `git show HEAD:<katalog>`
gemessen):

| Sprache | Wartezeit | Toleranz | späte Ein-Meldung | Ventil statt Durchfluss | ≠ en | Zeichen |
|---|---|---|---|---|---|---|
| en | ja | ja | ja | ja | ja | 517 |
| de | ja | ja | ja | ja | ja | 591 |
| es | ja | ja | ja | ja | ja | 612 |
| fr | ja | ja | ja | ja | ja | 618 |
| it | ja | ja | ja | ja | ja | 613 |
| nl | ja | ja | ja | ja | ja | 558 |
| no | ja | ja | ja | ja | ja | 544 |
| sk | ja | ja | ja | ja | ja | 518 |

Doku unverändert und beide Hälften weiterhin darin (`docs/configuration-my-zones.md`, `grep -c` je 1). dist neu
gebaut: nur `irrigation-plus.js` und `irrigation-plus-card-impl.js` ändern sich (sie bündeln die Kataloge), die
anderen zwei sind gegen HEAD unverändert (CR ignoriert); vitest bleibt bei 23 Dateien / 624 Tests.

**Keine Mutationsprobe zu C6.** Der Bericht führt keine, und das ist konsequent: C6 ändert reinen Anzeigetext plus
den Pin darauf, und dessen Falsifikation ist der RED-Lauf oben — er ist gegen den vorherigen committeten Text
gelaufen und gefallen. Die Sicherung `mut/en.json.bak` ist byte-gleich zum committeten Blob
(sha256 `f8f496e7daededa1…`, identisch mit `git show HEAD:…/en.json` in CRLF), der Baum kam also sauber zurück.

### Messstand C5/C6 (2026-09-20, Endstand `9da4c0b2`)

- **Lint am Endstand:** `uvx black --check custom_components/irrigation_plus/` --> `68 files would be left
  unchanged.`; mit den drei berührten Testdateien `71`; `uvx ruff check custom_components/irrigation_plus/` -->
  `All checks passed!`.
- **Volle Suite, Branch-Basis `a0baf8c6` (`after-13b.txt`) --> C5 committet (`after-c5-committed.txt`) --> C6
  (`after-c6.txt`):**

  ```
  a0baf8c6:  collected 3132  |  7 failed, 3116 passed, 9 skipped, 10 warnings, 320 errors in 239.78s
  3623e71b:  collected 3136  |  7 failed, 3120 passed, 9 skipped, 10 warnings, 320 errors in 243.78s
  9da4c0b2:  collected 3137  |  7 failed, 3121 passed, 9 skipped, 10 warnings, 320 errors in 236.38s
  ```

  Delta passed = Delta collected = **+4** (C5) und **+1** (C6), also ausschließlich neue grüne Tests. Die
  FAILED/ERROR-Namensmengen sind über alle drei Läufe gleich: je **330** Zeilen, `diff` leer (`a0baf8c6` gegen
  `9da4c0b2` und `3623e71b` gegen `9da4c0b2`). Die sieben FAILED sind die bekannten lokalen Windows-Fehlschläge
  (`test_init` ×2, `test_next_irrigation_sensor`, `test_opensprinkler_teardown` ×3, `test_panel`); CI ist der Gate
  (Projekt-`CLAUDE.md`).
- **Die neun benannten Suiten am committeten Stand:** `356 passed, 1 error in 23.52s`, mit demselben einen
  vorbestehenden Teardown-Error
  (`tests/test_service_watch.py::TestOneOffSampleIsNotEvidenceTheWaterStopped::test_the_run_is_not_settled_before_the_window_is_out`,
  „Lingering timer“). Er ist **nicht neu**: er steht ebenso im Branch-Basislauf (`after-13b.txt:2772` und `:3891`).
- **Diffstats:** C5 `4 files changed, 158 insertions(+), 24 deletions(-)`
  (`flow_metering.py`, `self_closing.py`, `tests/test_flow_meter.py`, `tests/test_service_watch.py`);
  C6 `11 files changed, 36 insertions(+), 10 deletions(-)` (8 Kataloge, 2 Bundles,
  `tests/test_i18n_completeness.py`).
- **Baum nach beiden Commits sauber**, nur `?? docs/SESSION-STAND.md` (vorbestehend, nicht verfolgt). Nichts
  gepusht; der Branch steht auf **16 Commits** über `upstream/master`.

### Folgen für die Abschnitte oben

- **Reichweite / Flussmessung am Ratensensor:** der Schwanz bis zur Aus-Meldung ist jetzt mit **einem Poll**
  begrenzt, nicht mit vier. Ein Sensor, der seit seiner letzten Marke tot ist, schreibt nichts mehr über die Marke
  hinaus gut.
- **Reichweite, neuer Punkt:** der **Kalibrier-Hinweis** wird auf dem Fenster gepreist, über das seine Liter
  gemessen wurden (`actual_s`, wenn das Ventil seinen Schluss gemeldet hat, sonst `planned_s`). Das Zeitvolumen und
  die absolute Eimer-Abstimmung bleiben davon unberührt.
- **„R1 ist der einzige Produktivcode-Fix“** gilt nur noch für die erste Runde: C5 ist der zweite
  Produktivcode-Commit dieses Nachtrags (`flow_metering.py`, `self_closing.py`).
- **Panel-Hilfe:** trägt wieder **beide** Hälften — Wartezeit und Toleranz —, und deckt sich damit wieder mit
  `docs/configuration-my-zones.md`. Der englische Text ist ab jetzt durch einen Test gepinnt.
- **Proben:** zu den 148 aus Task 13/13b (133 + 15) kommen **5 aus C5**; Summe **153, davon 148 gefangen und 5
  äquivalent** (dieselben fünf wie in Task 13). Neue Test-Items über den ganzen Branch: **115** pytest
  (110 aus T1–T12/C1–C4 + 4 aus C5 + 1 aus C6) plus 8 vitest = **123**; kein Item ohne fangende Probe bzw. — für
  den i18n-Pin aus C6 — ohne belegten RED-Lauf gegen den vorherigen Text.
- **E9 (Nachvollzug statt Neubau)** hat mit C5/C6 eine benannte Ausnahme: kleine Review-Korrekturen nach dem
  letzten Probelauf werden direkt auf dem Branch mit TDD gebaut. Im Plan steht das als **Task 13c**.

### SHA-Prüfung (20.09., alle Vorkommen)

Jeder SHA-förmige Token in beiden Dokumenten wurde mit `git cat-file -t` und
`git -C D:/Entwicklung/HASI/HAsmartirrigation merge-base --is-ancestor <sha> fix/backstop-grace` geprüft. Jeder, der
ein Git-Objekt sein soll, löst im Haupt-Repo als `commit` auf — es gibt keinen toten Zeiger.

Gezählt wird der Endstand beider Dokumente **nach** dieser Korrektur, die in diesem Abschnitt zitierten SHAs
eingeschlossen.

- **Spec: 38 SHA-förmige Tokens.** Drei sind gar keine Git-Objekte, sondern sha256-Präfixe aus den Probentabellen
  (`6327a398`, `dafb1079`, `04feb9a9`). Von den 35 Commits sind **zwölf Vorfahren** von `fix/backstop-grace`: die
  Basis `2b2c403b`, das Release `0b418644`, die geerbten `e9f2da51`, `0e0bb5d1` und `4e53caf4`, der Stand vor der
  Review `66763c34`, die vier korrigierten C1–C4 (`308c1907`, `20c2a008`, `2e829217`, `a0baf8c6`) und die beiden
  neuen C5/C6 (`3623e71b`, `9da4c0b2`). Die übrigen **23 sind ausschließlich Probelauf-Commits** (`dry5`, `dry6`,
  `dry7`) und damit erwartungsgemäß nicht erreichbar — die bestehende Konvention für Zwischenstände, die die
  Review ausdrücklich als eigene Sache stehen ließ. Ein einziger darunter, `bc41374b` (Z. 568 und 631, ein
  T3-Zwischenstand aus `dry6`), hängt an **gar keiner** Branch mehr und löst nur bis zum nächsten `gc` auf; er
  trägt keine Messung, die nicht daneben auch am Endstand `70dc0c18` steht.
- **Plan: 68 SHA-förmige Tokens.** Dieselben drei sha256-Präfixe; von den 65 Commits sind **neun Vorfahren**
  (`2b2c403b` und `0b418644` je kurz und voll, `4e53caf4`, `66763c34`, `a0baf8c6`, `3623e71b`, `9da4c0b2`). Die
  übrigen **56** sind die `SRC`-Spalte des Nachvollzugs (`dry2`…`dry7`, `tmp/drop-6-10`, `tmp/dry3-drop-3b`), drei
  Doku-Commits auf `archive/design-history` und zwei Commits aus `production` / `fix/rain-guard-run-date`. Das ist
  **so gewollt**: der Plan sagt, von wo ausgecheckt wird, nicht was ausgeliefert ist, und hält das im Kopfteil
  „Nachvollzug“ ausdrücklich fest — Task 13c hat deshalb als einziger Task **keine** `SRC`-Spalte. Drei davon
  hängen an keiner Branch mehr, mit derselben Einschränkung wie `bc41374b`.
- **Korrigiert wurden nur die vier Paare aus R10** — die Stellen, die einen **ausgelieferten** Commit benennen.
  Alles andere ist geprüft und bleibt absichtlich stehen.
