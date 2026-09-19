# #139 Finish-Backstop mit Wartezeit — Implementation Plan (Revision 3, Nachvollzug)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
>
> Dieser Plan ist ein **Nachvollzug**: der Code wird nicht neu getippt. Jeder Task holt die Testdateien seines
> geprüften Commits auf `dry6/backstop-grace`, vergleicht das RED mit dem Plan, holt dann den Produktivcode und
> committet mit derselben Nachricht (Abschnitt „Nachvollzug“).

**Goal:** Ein bestätigter Service-Lauf (Zone mit `confirm_entity`) wartet nach seinem geplanten Fenster die
5-s-Entprellung plus eine Latenz-Marge je Zone ab. So schließt der Watcher ein normales Laufende auf der eigenen
Aus-Meldung des Ventils ab (`completed`, `actual_s` = Fenster von Ein- bis Aus-Meldung, Abschluss bei Aus + 5 s),
statt dass der Backstop ihm bei `planned` zuvorkommt (JustChr/HAsmartirrigation#139). Jeder Commit schließt ein
Loch, das die Wartezeit selbst öffnet (Umfangsregel E8); alles andere bleibt wie heute.

**Architecture:** Beim Dispatch friert ein bestätigter Service-Lauf die Marge seiner Zone (`RUN_LATENCY_MARGIN`)
und die Ein-Meldung des Ventils (`RUN_VALVE_ON`: `last_changed` der Confirm-Entität, geklemmt auf
[Dispatch, Confirm-Rückkehr]) in seinen Laufdatensatz ein. Der Watcher zeichnet die erste Aus-Meldung direkt nach
einem laufenden Zustand auf (`RUN_VALVE_OFF`) und löscht sie bei einem Blip. Reine Helfer in `run_watch.py`
(`zone_latency_margin`, `run_latency_margin`, `run_has_finish_grace`, `run_finish_grace_seconds`,
`run_completion_tolerance`, `valve_window_seconds`) antworten nur hinter dem Tor aus Policy-Flag
`settles_on_valve_window` (nur `SERVICE_WATCH_POLICY`), `RUN_WATCH_ENTITY` und eingefrorener Marge; Batch,
OpenSprinkler, write-only und Datensätze von vor dem Update bestehen es nie. Die Aufrufer:

- **Backstop** am Dispatch und beim Neustart = geplant + `SERVICE_WATCH_SETTLE_SECONDS` (5) + Marge (Default 9 s
  Wartezeit). Feuert er, schließt er wie heute mit `planned_s` ab, auch mit gespeicherter Aus-Meldung (T6 gestrichen).
- **Watcher:** mit gespeicherter `RUN_VALVE_OFF` die Fensterregel (`completed` gdw. Fenster + max(1 s, Marge) >=
  geplant, `actual_s` = Fenster; sonst Teil-Lauf auf dem Fenster); ohne sie die Basisregel von heute (Entscheidung (b)).
- **Manueller Stopp:** vor dem geplanten Ende von `RUN_VALVE_ON` bis zum Stopp, gedeckelt auf geplant, nie auf einer
  gespeicherten Aus-Meldung (c); in der Wartezeit nach der Watcher-Regel, Ventil zuerst zu, nur im Zweig
  `close_valve` (d).
- **Neustart:** ab geplant + Wartezeit sofort `planned_s` (a); in der Wartezeit Backstop neu, Watcher neu, Master
  **nicht** angefordert (f); vor dem Ende wie heute, Backstop mit Wartezeit.
- **In-flight-Fenster** bis geplant + Wartezeit aus der eingefrorenen Marge, Anker unverändert `RUN_STARTED`; damit
  greifen Dispatch-Wächter, Berechnungs-Aufschub und Observed-Unterdrückung (`observed_watering.py:138`) auch in der
  Wartezeit.

Nicht mehr enthalten: `zone_finish_grace_seconds`, eine Verlängerung der Observed-Sperre (T3b), der Zeitfenster-Preis
(T10), die Backstop-Abrechnung auf gespeicherter Aus-Meldung (T6). Das Zonenfeld `latency_margin` (Default 4, ganze
Sekunden, 0–30) läuft über Store, Websocket, Panel (nur mit `confirm_entity`), die 8 Panel-Kataloge, Doku und dist.

**Tech Stack:** Python 3.12.0, Home-Assistant-Custom-Integration `custom_components/irrigation_plus` (attrs,
voluptuous), pytest 8.3.3 + pytest-homeassistant-custom-component + freezegun (lokal HA 2024.12.5 im Repo-`.venv`,
geprüft 19.09.; CI neuer und maßgeblich), black + ruff (CI-Lint); Frontend TypeScript + lit, vitest 4.1.8,
eslint, rollup (lokal Node v24.15.0 / npm 11.12.1 = Node-22-CI, geprüft 19.09.).

---

## Grundlagen

- **Spec (Quelle der Wahrheit):** `archive/design-history:docs/superpowers/specs/2026-09-15-backstop-grace-design.md`,
  **Revision 3**. Bis zur Archivierung in Task 14 liegt Revision 3 als `D:/Entwicklung/HASI/pr139-work/rev3/spec.md`;
  auf `archive/design-history` steht lokal noch Revision 2 (`0ddd8cb6`), der Branch ist 3 Commits vor
  `origin/archive/design-history` und nicht gepusht (geprüft 19.09. mit `git rev-list --left-right --count`: `3 0`).
  Zeilenangaben, Begründungen, Reichweite und die Liste „bekannt und bewusst unverändert“ stehen dort; der Plan
  wiederholt sie nicht.
- **Basis:** `2b2c403b` = `upstream/master`, „fix(skip): examine rain from the run's start, not from the day after
  it (#146)“, 2026-09-19 09:44 +0200. Sie hat sich von `0b418644` wegbewegt, weil #146 am 2026-09-19 gemergt wurde;
  JustChr hält den nächsten stabilen Release nur noch für diesen PR an. Von den Dateien dieses Fixes berührt #146
  (`git diff --stat 0b418644 2b2c403b`: 34 Dateien) nur `const.py`, `websockets.py`, die 8 Panel-Kataloge und die zwei
  dist-Bundles `irrigation-plus.js`/`irrigation-plus-card-impl.js` (geprüft 19.09.); deshalb wurde dist in T12 auf der
  neuen Basis neu gebaut. `self_closing.py`, `run_watch.py`, `run_state.py` und `store.py` sind unberührt. Die
  #139-Änderungszeilen sind auf beiden Basen identisch (`scratch/d4.txt` = `scratch/d5.txt`, `cmp` ohne Unterschied).
  Zeilenangaben gelten für `2b2c403b`, im neuen Code für `dry6/backstop-grace`. Dessen Produktivcode und dist sind
  byte-gleich mit `dry5/backstop-grace`: `git diff dry5/backstop-grace dry6/backstop-grace` betrifft nur
  `tests/test_service_watch.py` (+113/−21, `dry6-logs/T5.md`, Abschnitt „Tree delta“).
- **Arbeitsbranch:** `fix/backstop-grace` im Repo `D:/Entwicklung/HASI/HAsmartirrigation`. Er steht noch auf
  `0b418644` ohne eigene Commits, ist nicht nach `origin` gepusht und verfolgt `upstream/master` (geprüft 19.09.);
  Task 0 spult ihn auf `2b2c403b` vor.
- **Referenzbranch:** `dry6/backstop-grace` = `70dc0c185e57bc6b88003689c2198c8e6b54ad8a`, ausgecheckt im Worktree
  `D:/Entwicklung/HASI/pr139-work/dry2` (Worktree dieses Repos, gemeinsamer Objektspeicher). Zehn Commits auf
  `2b2c403b`, `git diff --stat 2b2c403b 70dc0c18`: `26 files changed, 3490 insertions(+), 810 deletions(-)`
  (gemessen 19.09. abends). Die Spalte dry5 nennt den geprüften Vorgänger (T1 und T2 sind dieselben Commits):

  | Task | dry6-Commit | dry5 | Betreff |
  |---|---|---|---|
  | T1 | `ca77c2879617f578e9c982633a5a56272ce81715` | gleich | feat(service): add a per-zone latency margin setting for confirmed valves |
  | T2 | `a6a9e382f26d189dd7716cbf725bc84349068e2d` | gleich | feat(run-watch): add the finish-grace run keys, policy flag and helpers |
  | T3 | `c6a4c842acb025abd3412a3ec51bab1576a2ae03` | `4be8c894` | feat(service): wait out the finish grace before a confirmed run's backstop |
  | T4 | `dd43f09cfdb9153622361ab8ecadb9ddfb816608` | `9380fb74` | feat(run-watch): record a confirmed valve's own off report |
  | T5 | `c234fb23902bae3e8bbc1de4cbf0166bf85fb3d5` | `b423feca` | feat(run-watch): settle a confirmed service run on its valve window |
  | T7 | `f1266999363694f76daec7b21027494a3217cf7a` | `bcae641c` | feat(service): measure a manual stop on the valve's own window |
  | T8 | `4819d2fc5b39e78ad86cac3f21d353443465c3b0` | `09aba7a4` | feat(service): carry the finish grace across a restart |
  | T9 | `0c0c941691aaa8f76b06a4a368e129cf59465c4c` | `ed9b2e4f` | feat(service): keep a confirmed run in flight through its finish grace |
  | T11 | `0e68d9781e1f6c866c0e35f964bfe3d729ace284` | `7f57cf4f` | feat(panel): add latency margin field for confirmed service zones |
  | T12 | `70dc0c185e57bc6b88003689c2198c8e6b54ad8a` | `58d6b7b5` | feat(i18n): translate and document the latency margin zone field |

  Was dry6 gegenüber dry5 ändert (`dry6-logs/T3.md`, `T5.md`; alles nur in `tests/test_service_watch.py` und in zwei
  Commit-Nachrichten):
  - **T3** bekommt den Echt-Timer-Test für einen verpassten Schluss
    (`TestAMissedCloseStillSettlesViaTheBackstop::test_a_valve_that_never_reports_off_is_finished_when_the_grace_is_out`);
    die Modul-Helfer `_finished` (bisher T7) und `_the_real_backstop_from_here` (bisher T8) samt Import
    `async_capture_events` stehen jetzt in T3s Teil der Datei. Die Nachricht hat einen Absatz mehr.
  - **T5** bekommt den Regressions-Pin für das gestrichene T6
    (`TestACloseReportedPastTheMarginIsKnownAndDeliberatelyUnchanged::test_the_backstop_finishes_it_for_the_plan_before_the_debounce`).
    Die Nachricht hat einen Absatz mehr („known and deliberately unchanged; a test pins it“).
  - **T7** und **T8** definieren die verschobenen Helfer nicht mehr (sonst ruff F811); T8 behält an seiner einen
    Aufrufstelle den Hinweis als Kommentar. T4, T9, T11, T12: nur neuer Elternstand.
- **Verifikation von `dry6` (19.09. abends; T1 und T2 unverändert aus `dry5`):**
  - Volle Suite Basis `2b2c403b`: `collected 3022 items`, `7 failed, 3006 passed, 9 skipped, 10 warnings, 320 errors`
    (`D:/Entwicklung/HASI/pr139-work/baseline-2b2c403b.txt`); `dry6`: `collected 3115 items`,
    `7 failed, 3099 passed, 9 skipped, 10 warnings, 320 errors` (`after-dry6.txt`); FAILED/ERROR-Namensmengen identisch
    (7 FAILED- und 321 ERROR-Namen = 320 Tests + 1 Logzeile `ERROR    custom_components…` aus `test_batch.py`,
    `dry6-logs/full-suite.md`). +93 Test-Items (89 neue Testfunktionen, eine davon mit 5 Parametern), alle grün.
  - vitest Basis 22 Dateien / 616 Tests (Messung laut Workflow-Auftrag 19.09., kein Protokoll in `pr139-work`;
    gegengerechnet: Endstand minus T11s eine Datei mit 8 Tests) --> `dry6` `Test Files  23 passed (23)`,
    `Tests  624 passed (624)` (`dry6-logs/full-suite.md`).
  - black/ruff: am Endstand `70dc0c18` mit der Dateiliste dieses Plans `73 files would be left unchanged.` /
    `All checks passed!` (gemessen 19.09. abends). Je Commit sauber: `dry6-logs/percommit.md` (dort mit
    `custom_components/irrigation_plus/` plus den Testdateien des Commits, daher 69/68 Dateien). Die Zahlen 70–73 dieses
    Plans stammen aus `scratch/dry5-checks.log` mit der Liste `git diff --name-only 2b2c403b -- tests`; dry6 fügt keine
    Testdatei hinzu, die Dateimenge ist also gleich.
  - 7 Service-Suiten + `tests/test_i18n_completeness.py` je Commit: T1 238 (mit T1s eigenen Dateien), T2 240, T3 251,
    T4 259, T5 269, T7 282, T8 292, T9 300, T11 300, T12 300 passed, immer `1 error` = der vorbestehende Lingering timer
    in `TestOneOffSampleIsNotEvidenceTheWaterStopped::test_the_run_is_not_settled_before_the_window_is_out`. Quelle
    T3–T12 `dry6-logs/percommit.md`; T2 `scratch/dry5-checks.log` (derselbe Commit); T1
    `replaycheck-logs/T01-suites.txt` (19.09., `238 passed, 1 error in 15.11s`; das dry5-Protokoll zeigt dort
    `no tests ran`, weil seine Liste die bei T1 noch fehlende `tests/test_finish_grace_helpers.py` enthielt;
    gegengerechnet 240 − 30 + 28 = 238).
  - dist aus den Quellen byte-gleich reproduziert (CR ignoriert), alle vier Bundles `SAME` (Hashes
    `scratch/dry5-checks.log`; Node v24.15.0 laut `node --version` am 19.09. und `dry3-logs/final.md`); dry6 hat
    dieselben dist-Bytes.
  - RED/GREEN je Task: `D:/Entwicklung/HASI/pr139-work/rev3/evidence.md` (T1/T2 von dry5, T3–T12 auf dry6 neu gemessen);
    Rohdaten T1/T2 `rev3/raw/`, T3–T12 `dry6-logs/evidence-raw/<task>_{stat,files,testfuncs,RED,GREEN}.txt`.
  - Mutationsproben: aus dem Probelauf `dry3` (alte Basis, mit T3b) T5 13 Proben (11 gefangen, 1 äquivalent, 1 bei T5
    überlebend und ab T7 gefangen), T7 21/21, T8 12/12, T9 8/8 einschließlich der drei früher überlebenden
    (`lte-boundary`, `frozen-margin-to-default`, `anchor-prefers-valve-on`); Protokolle `dry3-logs/T5.md`, `T7.md`,
    `T8.md`, `T9.md`. Auf dry6 neu gefahren (`dry6-logs/T3.md`, `T5.md`, `probes.md`): die vier Backstop-Proben zum
    Echt-Timer-Test (am T3-Stopp, am Branch-HEAD nach Schritt T3 `bc41374b` und am Endstand `70dc0c18`,
    `dry6-logs/T3-end-probes.txt`; alle gefangen), die T6-Probe gegen den T5-Pin (gefangen, nur von
    ihm) und neun Proben für die Tests, die bis dahin keine Probe fing (T2 ×5, T7 ×2, T11 ×2, alle gefangen). Die
    Zuordnung Item --> fangende Probe (`dry6-logs/killmap.md`): jedes der 101 neuen Test-Items (93 pytest + 8 vitest)
    scheitert an mindestens einer protokollierten Probe. Die Ergebnisse aus dry3/Rev. 2 übertragen sich, weil die
    Änderungszeilen identisch sind; die Zählungen der Test-Items nicht. Task 13 wiederholt alle Proben auf dem echten
    Branch (E9).
- **Probelauf-Geschichte** (Branches existieren lokal, geprüft 19.09.):
  1. `dry2/backstop-grace` (`67301a8b`, 15.09., Basis `0b418644`): alle Tasks T1–T12 mit 3b, 6 und 10 (Revision 2).
  2. `tmp/drop-6-10` (`361b52f7`, 19.09.): T6 und T10 gestrichen (`after-drop-6-10.txt`).
  3. `dry3/backstop-grace` (`157d3134`): Entscheidungen (a)–(f), T9-Tests, Texte; Protokolle
     `D:/Entwicklung/HASI/pr139-work/dry3-logs/`, Ergebnisse `D:/Entwicklung/HASI/pr139-work/wf-dry3.json`.
  4. `tmp/dry3-drop-3b` (`da827b76`): T3b per `rebase --onto` konfliktfrei gestrichen, toter Helfer
     `zone_finish_grace_seconds` als eigener Refactor-Commit entfernt (`dry3-logs/final.md`, Abschnitt 6).
  5. `dry4/backstop-grace` (`fc827da7`): diese Entfernung in T2 und T11 hineingefaltet.
  6. `dry5/backstop-grace` (`58d6b7b5`): auf `2b2c403b` rebased, dist in T12 neu gebaut.
  7. `dry6/backstop-grace` (`70dc0c18`, 19.09. abends): aus dry5 in einem interaktiven Rebase; T3 mit dem
     Echt-Timer-Test für den verpassten Schluss und den verschobenen Helfern, T5 mit dem Pin für das gestrichene T6,
     zwei Nachrichten um je einen Absatz ergänzt; Produktivcode und dist unverändert. Protokolle
     `D:/Entwicklung/HASI/pr139-work/dry6-logs/`.

  Der erste Probelauf von Revision 1 (`dry/backstop-grace`, `dry/backstop-grace-frontend` auf `4e53caf4`) existiert
  nicht mehr.
- **Design-Historie (Regel P1):** Spec und Plan Revision 3 kommen in Task 14 auf `archive/design-history`, vor jedem
  Löschen eines Dev-Branches.
- **Revisionen:**
  - **Rev. 1 (2026-09-15):** Plan zur Spec vom 09-15, erster Probelauf auf `4e53caf4`.
  - **Rev. 2 (2026-09-16):** Revisions-Probelauf `dry2/backstop-grace` auf `0b418644` (13 Commits, Task 1–12 mit 3b);
    7982 Zeilen mit vollständigen Codeblöcken; T3b, T6, T7 und T10 als abtrennbare Commits, Umfangsfrage auf #139
    ([issuecomment-5685683675](https://github.com/JustChr/HAsmartirrigation/issues/139#issuecomment-5685683675)).
    Lokal archiviert als `fbb535a5`.
  - **Rev. 3 (2026-09-19):** JustChrs Antworten vom 09-16 und 09-19 eingearbeitet; Entscheidungen (a)–(f), SP-3 und
    die T9-Dispatch-Tests; T3b, T6 und T10 gestrichen (Nummern bleiben); E3 und E4 revidiert; neue Basis `2b2c403b`;
    Methode Nachvollzug statt Codeblöcke (E9); Live-Test vor dem Merge (E10).
  - **Rev. 3, Nachtrag 19.09. abends:** Referenz von `dry5` auf `dry6` umgestellt (Echt-Timer-Test für den verpassten
    Schluss in T3, Pin für das gestrichene T6 in T5, neue Proben für jeden bis dahin ungefangenen Test); die Befunde
    der Vollständigkeits- und der Nachvollzugs-Prüfung (`wf-rev3.json`, `result.reviews[1]`, `[2]`) eingearbeitet:
    Commit-Zeile und MSG-SAME in jedem Task, Live-Test mit allen 9 Szenarien der Spec, ein Ort für das Live-Ergebnis
    (Kommentar auf dem PR, von #139 verlinkt), Log-Pfade, T12-Variante.

## Entscheidungen

Einzeilig mit Quelle; Details in der Spec (Revision 3), Abschnitt „Entscheidungen“ und dem genannten Design-Abschnitt.
Kommentare auf #139: `D:/Entwicklung/HASI/pr139-work/issue139-comments.md` (5667625952 JustChr 09-14 Form;
5685683675 unsere Umfangsfrage 09-15; 5692654650 JustChr 09-16; 5740280769 unsere Antwort 09-19 =
`comment-139-answer.md`; 5740329987 JustChr 09-19).

- **E1 (Rev. 3)** Anker = eigene Ein-Meldung (`RUN_VALVE_ON`), `RUN_STARTED` bleibt; Toleranz max(1 s, Marge) nur mit
  gespeicherter Aus-Meldung (Watcher) und beim Stopp in der Wartezeit. User 15.09.; JustChr 5692654650. Spec E1, Design 1/3.
- **E2** Default-Marge 4 s, ganze Sekunden, 0–30; der PR-Text zitiert die Messbereiche (Beet 2,08–2,90 s nach dem Fenster,
  Kirschlorbeer innerhalb ±0,7 s; 13.09.: Beets Backstop 2,03 s vor der Aus-Meldung, Kirschlorbeers Ventil 1,13 s vor dem
  Backstop). User 15.09.; JustChr 5692654650. Spec E2.
- **E3 (Rev. 3)** Die Wartezeit zieht nur das In-flight-Fenster mit (und damit alle Leser von `zone_run_in_flight`);
  Zeitfenster-Preis und Observed-Sperre nicht mehr. JustChr 5692654650 und 5740329987. Spec E3, Design 4.
- **E4 (Rev. 3) ersetzt:** Watcher-Hälfte durch (b), Neustart-Hälfte durch (a) und (f); `min(jetzt − Anker, geplant)` lebt
  nur noch im manuellen Stopp. Spec E4, Design 3.2.
- **E5** Die zwei Abweichungen von der Vorgabe (`_watch_resume` für Service unerreichbar --> Neustart-Test plus Batch-Pin;
  nur die Panel-Kataloge) werden im PR-Text erklärt. JustChr 5692654650 bestätigt. Spec „Abweichungen von der Vorgabe“.
- **E6 (Rev. 3)** `RUN_VALVE_OFF` nur aus einem Ereignis, dessen Vorzustand laufend war; `on --> unavailable --> off`
  speichert nichts und fällt unter (b). User 15.09. Spec E6, Design 1.
- **E7** Neutrale Namen in neu hinzugefügten Test-Fixtures; vorhandene upstream-Namen bleiben. User 15.09. Spec E7.
- **E8 Umfangsregel:** ein Commit gehört zum Fix, wenn er ein Loch schließt, das die Wartezeit selbst öffnet;
  Verbesserungen eines Datensatzes warten bis nach dem stabilen Release (#147). JustChr 5692654650. Spec E8.
- **(a)** Neustart nach geplant + Wartezeit mit gespeicherter `RUN_VALVE_OFF` --> `planned_s` wie heute (T8).
  User 19.09., angekündigt 5740280769, angenommen 5740329987. Spec (a), Design 5.
- **(b)** Fensterregel nur mit gespeicherter `RUN_VALVE_OFF`; ohne sie Basisregel (`elapsed` ab `RUN_OBSERVED_START`
  nach der Entprellung, `completed` gdw. `elapsed + 1 >= planned`), sonst würde ein unberichteter Schluss bis ~9 s zu
  früh `completed` (T5). User 19.09.; JustChr 5740329987 („The second one matters most.“). Spec (b), Design 3.1.
- **(c)** Stopp vor dem geplanten Ende: `RUN_VALVE_ON` bis Stopp, gedeckelt auf geplant, nie auf einer gespeicherten
  Aus-Meldung (T7). User 19.09.; 5740329987. Spec (c), Design 3.2.
- **(d)** Stopp in der Wartezeit nach der Watcher-Regel über `_sc_finish_run(actual_s=Fenster)`, Ventil vorher zu; der
  Zweig hängt an `close_valve`, der Watcher-Teil-Lauf ohne Aus-Meldung bleibt auf der Basis-Uhr (T7). User 19.09.;
  5740329987. Spec (d), Design 3.2.
- **(e)** T3b gestrichen, `zone_finish_grace_seconds` entsteht nie (aus T2 herausgefaltet, TS-Kommentar in T11
  umformuliert); der PR-Text nennt die Sub-Sekunden-Lücke zwischen dem Ende von In-flight und dem Backstop als bekannt
  und bewusst unverändert. JustChr 5740329987 („drop it“). Spec (e), Design 4.
- **(f)** Neustart in der Wartezeit: Backstop neu, Watcher neu, Master **nicht** angefordert; Test mit Grenzen +600 und
  +609 (T8). User 19.09.; JustChr 5740329987 bat um den Test. Spec (f), Design 5.
- **(SP-3)** Der Neustart-Test mit gespeicherter Aus-Meldung startet bei +602 neu (bei +604 sind beide Timer
  gleichzeitig fällig; in Produktion gewinnt der zuerst gestellte Backstop, im Harness wechselte der Sieger zwischen
  zwei Messungen) und benutzt den echten Backstop-Timer (T8). User 19.09. Spec (SP-3), „Verworfen“.
- **(T9)** Dispatch-Tests: zweites `async_run_self_closing` und `async_run_zone` in der Wartezeit werden abgelehnt und
  lassen Datensatz, Zähler, Master-Hold und Backstop unberührt; Pins für eingefrorene Marge, Anker und Grenze.
  JustChr 5692654650 und 5740329987. Spec (T9), Design 4.
- **T6 gestrichen:** Backstop mit gespeicherter Aus-Meldung bucht `planned_s` wie heute; PR-Text „known and deliberately
  unchanged“ mit beiden Auslösern. JustChr 5692654650. Spec „Ausdrücklich nicht dazu“. Seit dry6 pinnt ein Test in T5
  das unveränderte Verhalten (späte Aus-Meldung jenseits der Marge --> Backstop, `planned_s`).
- **T10 gestrichen:** Zeitfenster-Preis als eigenes Issue nach dem stabilen Release, mit den drei Korrekturen aus
  5740280769 (je Slot unter `rotating`; Unterpreis ab Confirm über 30 − 5 − Marge = 21 s bei Default und verpasstem
  Schluss, ab Marge 26 genügt der verpasste Schluss; späteres Finish statt abgeschnittenem Schwanz). JustChr 5692654650,
  5740329987. Entwurf: `D:/Entwicklung/HASI/pr139-work/rev3/issue-window-pricing.md`, korrigiert am 19.09. (die drei
  Korrekturen, 21-s-Schwelle, kein `zone_finish_grace_seconds`); der ältere `pr139-work/issue-window-pricing.md` ist
  überholt.
- **E9 Nachvollzug statt Neubau:** Tests zuerst aus dem `dry6`-Commit, RED vergleichen, dann Produktivcode, GREEN,
  Suiten, Lint, Commit mit derselben Nachricht; Mutationsproben in Task 13 auf dem echten Branch. User 19.09. Spec E9.
- **E10 Live-Test vor dem Merge:** HA-Test mit dem Wartezeit-Emulator (HA-Skript auf HA-Test, keine MCP-Latenz), dann
  Fork-Pre-Release auf HA-Prod und je Zone EIN kurzer, vom User ausgelöster `run_zone`. JustChr 5740329987
  („the proof I most want to see before it goes in“); User 19.09. Spec E10, „End-to-End-Kriterium“.

## Nachvollzug

**Regel (E9):** Je Task zuerst NUR die Testdateien aus dem `dry6`-Commit auschecken und laufen lassen; das RED muss dem
Task-Abschnitt entsprechen. Dann die Produktivdateien auschecken; GREEN, die Suiten, black und ruff wie im Plan; danach
ist der Arbeitsbaum gleich dem `dry6`-Commit, und der Commit bekommt dieselbe Nachricht. So entsteht kein
Produktionscode vor einem fehlschlagenden Test, und der Code ist der geprüfte des Probelaufs. Der Worktree `dry2`
teilt den Objektspeicher dieses Repos (`git -C D:/Entwicklung/HASI/pr139-work/dry2 rev-parse --git-common-dir` -->
`D:/Entwicklung/HASI/HAsmartirrigation/.git`, 19.09.), die SHAs lösen deshalb im Haupt-Repo auf.

### Dateien je Task (aus `rev3/evidence.md`; `git diff --name-only SRC~1 SRC` = TESTS + PROD, geprüft 19.09. auf dry6)

Kurzform: `cc/` = `custom_components/irrigation_plus/`, `fe/` = `custom_components/irrigation_plus/frontend/`. In den
Befehlen immer die vollen Pfade.

| Task | SRC (`dry6`) | TESTS | PROD |
|---|---|---|---|
| T1 | `ca77c287` | `tests/test_distributor_integration.py tests/test_store_self_closing.py` | `cc/const.py cc/store.py cc/websockets.py` |
| T2 | `a6a9e382` | `tests/test_finish_grace_helpers.py` (neu) | `cc/const.py cc/run_watch.py cc/self_closing.py` |
| T3 | `c6a4c842` | `tests/test_service_watch.py` | `cc/self_closing.py` |
| T4 | `dd43f09c` | `tests/test_service_watch.py` | `cc/run_watch.py` |
| T5 | `c234fb23` | `tests/test_service_watch.py` | `cc/run_watch.py cc/self_closing.py` |
| T7 | `f1266999` | `tests/test_service_watch.py` | `cc/self_closing.py` |
| T8 | `4819d2fc` | `tests/test_service_watch.py` | `cc/self_closing.py` |
| T9 | `0c0c9416` | `tests/test_run_in_flight.py` | `cc/run_state.py` |
| T11 | `0e68d978` | `fe/src/views/zones/view-zone-settings-latency-margin.test.ts` (neu) | `fe/src/const.ts fe/src/types.ts fe/src/views/zones/view-zone-settings.ts` |
| T12 | `70dc0c18` | — | `fe/dist/irrigation-plus-card-impl.js fe/dist/irrigation-plus.js fe/localize/languages/{de,en,es,fr,it,nl,no,sk}.json docs/configuration-my-zones.md` (11 Dateien) |

### Erwartung je Task (Kurzform; Details, FAILED-Namen und Assertion-Zeilen im Task-Abschnitt)

Quellen: RED/GREEN der eigenen Tests `rev3/evidence.md`; Suiten T3–T12 `dry6-logs/percommit.md`, T2
`scratch/dry5-checks.log`, T1 `replaycheck-logs/T01-suites.txt` (siehe Grundlagen); black `scratch/dry5-checks.log` (Dateimenge auf dry6
gleich, am Endstand nachgemessen: 73). „Suiten“ = `$SUITES` aus Block B, jeweils mit genau `1 error` (vorbestehender
Lingering timer).

| Task | RED eigene Tests | GREEN eigene Tests | Suiten | black |
|---|---|---|---|---|
| T1 | `collected 28 items`, `3 failed, 25 passed` (3× `AttributeError: … has no attribute 'ZONE_LATENCY_MARGIN'`) | `28 passed` | 238 passed | 70 |
| T2 | `collected 0 items / 1 error`, `1 error` (Sammelfehler `ImportError: cannot import name 'run_completion_tolerance'`) | `30 passed` | 240 passed | 71 |
| T3 | `collected 28 items`, `8 failed, 20 passed, 1 error` | `28 passed, 1 error` | 251 passed | 72 |
| T4 | `collected 36 items`, `4 failed, 32 passed, 5 errors` | `36 passed, 1 error` | 259 passed | 72 |
| T5 | `collected 46 items`, `5 failed, 41 passed, 1 error` | `46 passed, 1 error` | 269 passed | 72 |
| T7 | `collected 59 items`, `9 failed, 50 passed, 5 errors` | `59 passed, 1 error` | 282 passed | 72 |
| T8 | `collected 69 items`, `7 failed, 62 passed, 2 errors` | `69 passed, 1 error` | 292 passed | 72 |
| T9 | `collected 27 items`, `6 failed, 21 passed, 2 errors` | `27 passed` | 300 passed | 73 |
| T11 | vitest `Test Files  1 failed (1)`, `Tests  8 failed (8)` (`TypeError: el._showLatencyMargin is not a function` 4×, `el._clampLatencyMargin` 4×) | `Test Files  1 passed (1)`, `Tests  8 passed (8)` | 300 passed | 73 |
| T12 | — (kein Testfile; Kriterien vorher benannt, siehe Variante T12) | dist 4× `SAME` | 300 passed | 73 |

ruff: immer `All checks passed!`.

### Block A — Vorbedingung und RED (nur die Tests)

Die drei Zeilen `T=`, `SRC=`, `TESTS=` (und in Block B `PROD=`) setzt der Task aus den Tabellen; hier mit den Werten von
Task 3 ausgefüllt. Jeder Block ist eine eigene Shell: die Variablen in jedem Block neu setzen.

```bash
cd D:/Entwicklung/HASI/HAsmartirrigation
mkdir -p D:/Entwicklung/HASI/pr139-work/tmp D:/Entwicklung/HASI/pr139-work/npm-cache && export TEMP=D:/Entwicklung/HASI/pr139-work/tmp TMP=D:/Entwicklung/HASI/pr139-work/tmp TMPDIR=D:/Entwicklung/HASI/pr139-work/tmp npm_config_cache=D:/Entwicklung/HASI/pr139-work/npm-cache
PY=D:/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe
R=D:/Entwicklung/HASI/pr139-work/replay
T=T03
SRC=c6a4c842acb025abd3412a3ec51bab1576a2ae03
TESTS="tests/test_service_watch.py"
git branch --show-current
git status --short
test "$(git rev-parse HEAD^{tree})" = "$(git rev-parse "$SRC~1^{tree}")" && echo PARENT-TREE-SAME
git checkout "$SRC" -- $TESTS
"$PY" -m pytest $TESTS -p _local_socket_unblock -q --tb=line -p no:cacheprovider > $R/$T-red.txt 2>&1
grep -E "^collected |^(FAILED|ERROR) |^E  |\.py:[0-9]+: " $R/$T-red.txt; tail -n 1 $R/$T-red.txt
```

Erwartet: `fix/backstop-grace`; `git status --short` nur `?? docs/SESSION-STAND.md`; `PARENT-TREE-SAME` (der Branch
steht inhaltlich genau auf dem Elternstand des `dry6`-Commits); danach das RED des Tasks. Fehlt `PARENT-TREE-SAME`:
STOPP, nichts auschecken.

### Block B — GREEN, Suiten, Lint, Gleichstand

```bash
cd D:/Entwicklung/HASI/HAsmartirrigation
mkdir -p D:/Entwicklung/HASI/pr139-work/tmp D:/Entwicklung/HASI/pr139-work/npm-cache && export TEMP=D:/Entwicklung/HASI/pr139-work/tmp TMP=D:/Entwicklung/HASI/pr139-work/tmp TMPDIR=D:/Entwicklung/HASI/pr139-work/tmp npm_config_cache=D:/Entwicklung/HASI/pr139-work/npm-cache
PY=D:/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe
R=D:/Entwicklung/HASI/pr139-work/replay
T=T03
SRC=c6a4c842acb025abd3412a3ec51bab1576a2ae03
TESTS="tests/test_service_watch.py"
PROD="custom_components/irrigation_plus/self_closing.py"
SUITES="tests/test_service_watch.py tests/test_finish_grace_helpers.py tests/test_run_in_flight.py tests/test_confirm_reserve.py tests/test_self_closing.py tests/test_run_watch.py tests/test_observed_watering.py tests/test_i18n_completeness.py"
git checkout "$SRC" -- $PROD
"$PY" -m pytest $TESTS -p _local_socket_unblock -q --tb=line -p no:cacheprovider > $R/$T-green.txt 2>&1; tail -n 1 $R/$T-green.txt
"$PY" -m pytest $SUITES -p _local_socket_unblock -q --tb=line -p no:cacheprovider > $R/$T-suites.txt 2>&1; tail -n 1 $R/$T-suites.txt; grep -E "^(FAILED|ERROR) " $R/$T-suites.txt
uvx black --check custom_components/irrigation_plus/ $(git diff --name-only 2b2c403b -- tests) 2>&1 | tail -n 1
uvx ruff check custom_components/irrigation_plus/ 2>&1 | tail -n 1
git diff "$SRC" --stat; git diff --cached "$SRC" --stat; echo "(diff-ende)"
```

Erwartet: GREEN, Suiten und black laut Tabelle; einzige ERROR-Zeile der Suiten
`ERROR tests/test_service_watch.py::TestOneOffSampleIsNotEvidenceTheWaterStopped::test_the_run_is_not_settled_before_the_window_is_out`;
ruff `All checks passed!`; beide Diffs leer, also direkt `(diff-ende)`. `git diff --name-only 2b2c403b -- tests` zählt die
schon gestagten Testdateien des Tasks mit, so dass black dieselbe Dateimenge sieht wie im Probelauf.

### Block C — Commit mit derselben Nachricht

```bash
cd D:/Entwicklung/HASI/HAsmartirrigation
SRC=c6a4c842acb025abd3412a3ec51bab1576a2ae03
git log -1 --format=%B "$SRC" | git commit -q -F -
test "$(git rev-parse HEAD^{tree})" = "$(git rev-parse "$SRC^{tree}")" && echo TREE-SAME
diff <(git log -1 --format=%B HEAD) <(git log -1 --format=%B "$SRC") && echo MSG-SAME
git log --oneline -1
git status --short
```

Erwartet: `TREE-SAME`, `MSG-SAME`, ein neuer SHA mit dem Betreff des Tasks, `git status --short` nur
`?? docs/SESSION-STAND.md`. Der Commit ist lokal; gepusht wird erst in Task 14 nach Freigabe. Die Nachrichten der
`dry6`-Commits enden bereits mit `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>`.

Block C steht in dieser Form (Pipe, `TREE-SAME`, `MSG-SAME`) in jedem Task-Abschnitt. Geprüft am 19.09. im
Scratch-Worktree `D:/Entwicklung/HASI/pr139-work/replaycheck` (inzwischen entfernt) für T1, T5, T7 und T12, damals gegen
die dry5-SHAs: jedes Mal Exit 0, `TREE-SAME`, `MSG-SAME` (`replaycheck-logs/`, `wf-rev3.json`, `result.reviews[2]`).

### Varianten

Die Task-Abschnitte sind maßgeblich; weicht dieser Kopfteil von ihnen ab, gilt der Task-Abschnitt. Ihre Protokolle liegen
immer unter `D:/Entwicklung/HASI/pr139-work/replay/<Tnn>-{red,green,suites}.txt` (`Tnn` zweistellig, z. B. `T03`).

- **T1:** In Block B gibt es `tests/test_finish_grace_helpers.py` noch nicht (im Probelauf-Protokoll deshalb `no tests
  ran`). `SUITES="tests/test_service_watch.py tests/test_run_in_flight.py tests/test_confirm_reserve.py
  tests/test_self_closing.py tests/test_run_watch.py tests/test_observed_watering.py tests/test_i18n_completeness.py
  tests/test_distributor_integration.py tests/test_store_self_closing.py"`, erwartet `238 passed, 1 error`.
- **T2:** Die Testdatei ist neu; das RED ist ein Sammelfehler (`Interrupted: 1 error during collection`), keine Assertion.
- **T11:** Block A und B wie oben (Auschecken aus dem Repo-Wurzelverzeichnis), aber die pytest-Zeile für `$TESTS` samt
  ihrer Auswertung jeweils durch diesen vitest-Block ersetzen (RED in A, GREEN in B):

  ```bash
  cd D:/Entwicklung/HASI/HAsmartirrigation/custom_components/irrigation_plus/frontend
  mkdir -p D:/Entwicklung/HASI/pr139-work/tmp D:/Entwicklung/HASI/pr139-work/npm-cache && export TEMP=D:/Entwicklung/HASI/pr139-work/tmp TMP=D:/Entwicklung/HASI/pr139-work/tmp TMPDIR=D:/Entwicklung/HASI/pr139-work/tmp npm_config_cache=D:/Entwicklung/HASI/pr139-work/npm-cache
  L=D:/Entwicklung/HASI/pr139-work/replay/T11-red.txt   # in Block B: T11-green.txt
  npx vitest run src/views/zones/view-zone-settings-latency-margin.test.ts > $L 2>&1
  grep -E "Test Files|Tests |TypeError" $L
  ```

  Die Suiten und black/ruff laufen in Block B trotzdem (300 / 73). Die volle vitest-Suite misst Task 13 (23 Dateien /
  624 Tests am `dry6`-Endstand, `dry6-logs/full-suite.md`); an T11 allein ist sie nicht gemessen.
- **T12:** Maßgeblich ist der Abschnitt Task 12 (Teil b). Kurzfassung:
  - kein Block A (keine Testdatei); stattdessen ein Ersatz-RED nur mit `en.json` (Task 12 Step 2);
  - dann die übrigen Kataloge und die Doku aus `SRC` (Step 3);
  - dist aus den Quellen bauen und alle vier Bundles gegen `SRC` vergleichen (Step 4, Build-Log
    `D:/Entwicklung/HASI/pr139-work/replay/T12-build.txt`);
  - nur die zwei geänderten Bundles `irrigation-plus.js` und `irrigation-plus-card-impl.js` mit `git add -f` stagen,
    die zwei übrigen auf den Index zurücksetzen (Step 5; nach dem Build zeigen sie nur Zeilenenden-Rauschen);
  - Block B ohne die pytest-Zeile für `$TESTS` (ohne Dateiargument sammelte pytest die ganze Suite; Step 6), dann
    Block C (Step 7).

  Prüfkriterien, VOR dem Auschecken benannt (globale Regel „kein Produktionscode vor einem fehlschlagenden Test“ -->
  beobachtbares Kriterium): `tests/test_i18n_completeness.py` in den Suiten grün (300 passed, 1 error), alle vier
  dist-Bundles aus den Quellen byte-gleich zu `SRC` (CR ignoriert; Hashes in Task 12 Step 4, real aus
  `scratch/dry5-checks.log`, dry6 hat dieselben dist-Bytes), `TREE-SAME` nach dem Commit. **Vor** Block C zeigt
  `git status --short` die 11 gestagten Dateien als `M ` (die zwei Bundles, die 8 Kataloge, die Doku) und
  `?? docs/SESSION-STAND.md`; erst **nach** Block C steht dort nur noch `?? docs/SESSION-STAND.md` (Befund der
  Nachvollzugs-Prüfung, `wf-rev3.json`, `result.reviews[2]`). Die Nachvollzugs-Prüfung stagte alle vier Bundles mit
  `git add -f` und kam ebenfalls auf `TREE-SAME`, weil die zwei unveränderten Bundles auf dieselben Blobs normalisieren
  (die Blobs in `SRC` enthalten kein CR, geprüft 19.09.); maßgeblich bleibt die Form aus Task 12.

### Stopp-Regel

Weicht RED, GREEN, Suiten, Lint, ein Diff, `PARENT-TREE-SAME`, `TREE-SAME` oder `MSG-SAME` vom Plan ab: **STOPP. Nicht
committen, nichts reparieren, den Stand lassen** und dem User berichten (Ausgabe und Log-Datei unter
`D:/Entwicklung/HASI/pr139-work/replay/` zeigen). `dry6/backstop-grace` ist die geprüfte Referenz; eine Abweichung ist ein
Befund, kein Anlass für einen Fix-Versuch. Als Abweichung zählt: eine andere FAILED/ERROR-Menge, ein anderer
Assertion-Text oder eine andere Zeilennummer, eine andere Zählung in `collected` oder in der Zusammenfassung. Keine
Abweichung: Laufzeiten, das Pfadpräfix (`…\pr139-work\dry2\tests\…` in `evidence.md` gegen
`…\HAsmartirrigation\tests\…`), Speicheradressen `at 0x…` in Lingering-timer-Zeilen, `�` statt `±`.

Wiederherstellen erst nach Rücksprache, dann mit
`git restore --source=HEAD --staged --worktree -- $TESTS $PROD` (in einem Scratch-Repo am 19.09. geprüft: stellt
geänderte Dateien her und entfernt eine im `SRC` neue Datei; Status danach leer). NICHT `git checkout -- .` (spielt nur
den schon überschriebenen Index zurück, `evidence.md` „Methodik-Korrektur“) und kein `git reset --hard` (globale
`CLAUDE.md`, Git).

### Abweichungen vom Auftragstext (belegt)

- **Commit-Nachricht per Pipe statt `git commit -F <(…)`:** in Git Bash scheitert Prozess-Substitution mit dem nativen
  `git` (Scratch-Repo 19.09.: `fatal: could not read log file '/proc/1324/fd/63': No such file or directory`). Die
  Pipe `git log -1 --format=%B "$SRC" | git commit -q -F -` lieferte im selben Scratch-Repo `MSG-SAME` und `TREE-SAME`.
  `diff <(…) <(…)` funktioniert, weil `diff` ein MSYS-Programm ist.
- **Vier dist-Bundles statt drei:** getrackt sind vier (`git ls-tree -r --name-only 2b2c403b -- …/frontend/dist`), T12
  ändert zwei davon (`irrigation-plus.js`, `irrigation-plus-card-impl.js`); verglichen werden alle vier wie im Probelauf.
- **Zusätzliche Prüfungen:** `PARENT-TREE-SAME` vor dem Auschecken, `git diff --cached "$SRC"` neben `git diff "$SRC"`,
  `TREE-SAME` und `MSG-SAME` nach dem Commit (stärker als ein leerer Diff).
- **pytest-Schalter** `--tb=line -p no:cacheprovider` zusätzlich zu `-p _local_socket_unblock -q`: `--tb=line` erzeugt die
  Assertion-Zeilen im Format von `evidence.md`, `no:cacheprovider` wie in allen Messungen des Probelaufs.
- **Basis-Datei:** Task 0 schreibt die neue Messung nach `baseline-2b2c403b-fix-MMDD.txt`, damit die Referenz
  `baseline-2b2c403b.txt` nicht überschrieben wird.
- **Probe in einem frischen Worktree:** `_local_socket_unblock.py` (das Plugin hinter `-p _local_socket_unblock`) ist nicht
  getrackt (`git ls-files -- _local_socket_unblock.py` leer). Wer den Nachvollzug in einem Scratch-Worktree
  (`git worktree add …`) probt, kopiert die Datei zuerst aus `D:/Entwicklung/HASI/HAsmartirrigation/` hinein, sonst
  bricht jeder pytest-Lauf mit `ImportError: Error importing plugin "_local_socket_unblock"` ab (Befund der
  Nachvollzugs-Prüfung, 19.09.). Der echte Nachvollzug läuft im Haupt-Repo, dort liegt die Datei; Task 13 Step 3
  kopiert sie in den Basis-Worktree.

## Tasks

- **Task 0:** Ausgangslage prüfen und Basis messen (Speicherplatz, Arbeitsbranch auf `2b2c403b` vorspulen,
  Referenzbranch, volle Suite, vitest, Mutationswerkzeug).
- **Task 1:** Latenz-Marge als Zonenfeld: gespeichert, geladen, per Websocket gesetzt, noch ohne Wirkung (`ca77c287`).
- **Task 2:** Laufdaten-Schlüssel, Policy-Flag, reine Helfer und Batch-Pin, ohne `zone_finish_grace_seconds` (`a6a9e382`).
- **Task 3:** Dispatch friert Marge und Ventil-Ein ein, der Backstop trägt die Wartezeit; Echt-Timer-Test für den
  verpassten Schluss (`c6a4c842`).
- **Task 3b: gestrichen** — Observed-Sperre über die Wartezeit (JustChr 5740329987, Entscheidung (e)).
- **Task 4:** Der Watcher zeichnet die Aus-Meldung des Ventils auf und löscht sie bei einem Blip (`dd43f09c`).
- **Task 5:** Der Watcher rechnet mit gespeicherter Aus-Meldung nach dem Ventil-Fenster ab, sonst nach der Basisregel (b);
  Pin für den unveränderten T6-Fall (`c234fb23`).
- **Task 6: gestrichen** — Backstop rechnet auf gespeicherter Aus-Meldung ab (JustChr 5692654650).
- **Task 7:** Manueller Stopp: vor dem Ende ab `RUN_VALVE_ON` (c), in der Wartezeit nach der Watcher-Regel (d) (`f1266999`).
- **Task 8:** Ein Neustart übernimmt die Wartezeit: (a), (f), SP-3 (`4819d2fc`).
- **Task 9:** Das In-flight-Fenster trägt die Wartezeit, mit Dispatch-Tests (`0c0c9416`).
- **Task 10: gestrichen** — Zeitfenster-Preis (JustChr 5692654650 --> eigenes Issue nach dem stabilen Release).
- **Task 11:** Panel-Feld „Latenz-Marge“ + vitest (`0e68d978`).
- **Task 12:** Übersetzungen in 8 Sprachen, Doku, dist (`70dc0c18`).
- **Task 13:** Schlussprüfung auf dem echten Branch: Baumgleichheit aller zehn Commits mit `dry6`, Lint, volle Suite gegen
  die Basis vom selben Tag (erwartet die `dry6`-Zahlen `collected 3115 items`,
  `7 failed, 3099 passed, 9 skipped, 10 warnings, 320 errors`, Namensmengen gleich), vitest 23 / 624, dist,
  Schwester-Pfade, Text-Hygiene, alle 133 Mutationsproben erneut (T9-Probe `live-zone-margin` über
  `zone_latency_margin` neu formuliert, weil `zone_finish_grace_seconds` nicht existiert) und die Prüfung, dass jedes
  der 101 neuen Test-Items an mindestens einer Probe scheitert (Step 8b).
- **Task 14:** PR-Text (Englisch; Messbasis der Default-Marge, Reichweite, „known and deliberately unchanged“, E5,
  Batch/OpenSprinkler unberührt), Push und PR, Kommentar auf #139, Design-Historie (Spec und Plan Revision 3 auf
  `archive/design-history`), Befunde in `D:\Entwicklung\HASI\ToDo.md`, Aufräumen der Probelauf-Branches und des
  Worktrees `dry2` — jeder Außenschritt mit eigener Freigabe, jeder Text vorher im Chat.
- **Task 15:** Live-Test vor dem Merge (E10): zuerst HA-Test mit dem Wartezeit-Emulator, gesteuert von einem HA-Skript auf
  HA-Test (die 9 Szenarien der Spec als S1–S9); dann Fork-Pre-Release auf HA-Prod (`production` neu auf upstream
  `2b2c403b` + dieser Branch + Branding) und je Zone EIN kurzer `run_zone`, ausgelöst vom User (Beet =
  Tuya-Minutenventil, Kirschlorbeer = SONOFF-Sekundenventil); natürliche Läufe danach als zusätzlicher Beleg; Ergebnis
  als Kommentar auf dem PR nach Freigabe, dazu auf #139 ein Satz mit Link; erst danach der Merge.

## Umgebungswarnungen

- **Speicherplatz auf `C:`:** am 19.09. 8,9 GB frei (`df -h`, Task 0), im Revisions-Probelauf am 15.09. nur 58 MB.
  JEDER Befehlsblock, der pytest, vitest oder npm startet, beginnt direkt nach seinem `cd` mit der Umleitungszeile
  (`mkdir -p … && export TEMP=… TMP=… TMPDIR=… npm_config_cache=…`); jeder Block ist eine eigene Shell. Unter 5 GB frei:
  dem User melden; unter 500 MB oder bei `ENOSPC`: STOPP.
- **CRLF:** der Arbeitsbaum ist CRLF ausgecheckt (`core.autocrlf=true`), nur `dist/irrigation-plus.js` hat `eol=lf`
  (`git check-attr`, 19.09.). `git checkout "$SRC" -- …` schreibt CRLF, `git diff` normalisiert; der Beleg für Gleichheit
  ist `TREE-SAME`. Nach `npm run build` zeigen die drei übrigen Bundles ` M` ohne Inhaltsänderung (`dry3-logs/final.md`,
  Abschnitt 6), bis sie gestagt oder aus `SRC` zurückgeholt sind.
- **Mutationswerkzeuge (Task 13 Step 8):** der Treiber `D:/Entwicklung/HASI/pr139-work/mut/rev3_probes.py` (legt Task 13
  an; liest mit Universal-Newlines, Suchtexte mit `\n`, schreibt die Mutation mit LF, erst die `.bak` stellt die
  CRLF-Bytes wieder her) und die CRLF-Skripte `mut/dry3_t5_probes.py`, `dry3_t7_probes.py`, `dry3_t8_probes.py`
  (Suchtexte mit `\r\n` wörtlich, `newline=''`), die Task 13 als `real_t5/t7/t8_probes.py` mit neuem
  Sicherungspräfix kopiert. `mut/mutate.py` (seit 19.09. 08:19 CRLF-erhaltend, `ABORT: search string occurs N times`)
  gehört nur zu den Probeläufen Rev. 2/`dry3` und wird in Task 13 nicht benutzt. Sicherung nach `mut/…bak` und
  SHA-256-Prüfung nach dem Zurückkopieren bleiben Pflicht.
- **Lingering timers:** lokal (HA 2024.12.5) endet ein Test mit noch scharfem echtem Timer als
  `Failed: Lingering timer …`-Error; die Basis hat 320 davon. Jeder Lauf mit `tests/test_service_watch.py` zeigt den einen
  vorbestehenden in `TestOneOffSampleIsNotEvidenceTheWaterStopped`. RED-Läufe erzeugen zusätzlich eigene Teardown-Errors
  (T4 +4, T7 +4, T8 +1; T9 2, weil am Elternstand der abgelehnte Dispatch durchgeht und einen eigenen Backstop-Timer
  stellt), siehe `evidence.md`. `IRRIGATION_PLUS_HA_FLOOR=1` nur zum Vergleich, nie um einen neuen Timer zu verstecken.
- **freeze_time:** freezegun friert auch die Loop-Uhr ein. Ein echtes `async_call_later` muss im selben
  `freeze_time(...) as frozen`-Block gestellt werden, in dem die Uhr vorgestellt wird: `frozen.tick(n)`,
  `async_fire_time_changed(hass, dt_util.utcnow())`, `await hass.async_block_till_done()`. `async_fire_time_changed`
  feuert bis 0,5 s zu früh und bewegt `utcnow` nicht, das tut nur `tick`. (Relevant für Diagnose und Mutationsproben;
  der Nachvollzug schreibt keine Tests.)
- **Datumsabhängige Tests:** Basis (Task 0) und Endstand (Task 13) am selben Kalendertag messen.
- **Quelle des Nachvollzugs:** Die `dry6`-Objekte liegen im gemeinsamen Objektspeicher `HAsmartirrigation/.git`, nicht im
  Worktree. `git worktree remove` löscht weder Branch noch Objekte; erst das Löschen des Branches `dry6/backstop-grace`
  macht die Commits unerreichbar (ein späteres `git gc` kann sie entfernen). Den Worktree `dry2` deshalb erst in Task 14
  entfernen und nur, wenn der Branch `dry6/backstop-grace` bestehen bleibt oder `fix/backstop-grace` alle zehn Commits
  trägt (Baumgleichheit je Commit, Task 13). Den Branch `dry6/backstop-grace` nicht vor dem Abschluss von Task 13
  löschen. Im Worktree `dry2` nichts ändern (`git -C D:/Entwicklung/HASI/pr139-work/dry2 status --short` bleibt leer);
  solange er auf `dry6/backstop-grace` steht, kann das Haupt-Repo diesen Branch nicht auschecken (nicht nötig).
  `dry5/backstop-grace` bleibt als Vorgänger bis Task 14 stehen.
- **Tracking:** `fix/backstop-grace` verfolgt `upstream/master` (`branch.fix/backstop-grace.remote=upstream`). Nie ein
  bloßes `git push`; in Task 14 nach Freigabe genau `git push -u origin fix/backstop-grace`, das das Tracking auf `origin`
  umstellt.
- **Außenwirkung:** Push, PR, Kommentare, Issues, Tags und Releases nur nach ausdrücklicher Freigabe, Texte vorher im Chat.
  Keine IP-Adressen und keine SHAs unserer Branches in PR-Text, Kommentaren oder Code (SHAs nur hier im Plan).
  HA-Prod: Schreiben, Installieren und Neustart nur mit ausdrücklicher Freigabe; Bewässerungs-Hardware schaltet der User,
  nicht Claude. HA-Test ist für den Test freigegeben; vor jedem schreibenden Aufruf die Instanz nennen, Routing strikt
  per Präfix `mcp__HA-Test__` / `mcp__HA-Prod__`.

---

### Task 0: Ausgangslage prüfen und Basis messen

**Files:** keine Änderung im Repo. Messdateien und Protokolle liegen außerhalb des Repos unter
`D:/Entwicklung/HASI/pr139-work/`.

- [ ] **Step 1: Speicherplatz prüfen und Umleitung setzen**

```bash
cd D:/Entwicklung/HASI/HAsmartirrigation
mkdir -p D:/Entwicklung/HASI/pr139-work/tmp D:/Entwicklung/HASI/pr139-work/npm-cache && export TEMP=D:/Entwicklung/HASI/pr139-work/tmp TMP=D:/Entwicklung/HASI/pr139-work/tmp TMPDIR=D:/Entwicklung/HASI/pr139-work/tmp npm_config_cache=D:/Entwicklung/HASI/pr139-work/npm-cache
df -h /c /d
echo "$TEMP $npm_config_cache"
mkdir -p D:/Entwicklung/HASI/pr139-work/replay
```

Erwartet: `C:` mindestens 5 GB frei. Am 19.09. beim Schreiben dieses Plans (real):

```
Filesystem      Size  Used Avail Use% Mounted on
C:              476G  467G  8.9G  99% /c
D:              1.9T  399G  1.5T  22% /d
```

und `D:/Entwicklung/HASI/pr139-work/tmp D:/Entwicklung/HASI/pr139-work/npm-cache`. Unter 5 GB: dem User melden; unter
500 MB: STOPP.

- [ ] **Step 2: Ausgangslage lesen**

`docs/SESSION-STAND.md` und `D:\Entwicklung\HASI\ToDo.md` lesen (Session-Hygiene), dann:

```bash
cd D:/Entwicklung/HASI/HAsmartirrigation
git status --short
git branch --show-current
git log --oneline -1
```

Erwartet: `git status --short` nur `?? docs/SESSION-STAND.md`; sonst STOPP (auf einem unsauberen Stand wird nicht
angefangen). Stand beim Schreiben (19.09., real): Branch `fix/rain-guard-run-date`,
`a205ce96 docs(forecast): call the skip-direction example a reproduction` (der #146-Branch; #146 ist gemergt).

- [ ] **Step 3: Upstream holen und Basis bestätigen**

```bash
cd D:/Entwicklung/HASI/HAsmartirrigation
git fetch upstream
git rev-parse upstream/master
git log --oneline -1 upstream/master
git rev-parse fix/backstop-grace
git rev-list --count fix/backstop-grace..upstream/master
git rev-list --count upstream/master..fix/backstop-grace
git rev-parse --verify -q origin/fix/backstop-grace || echo "kein origin/fix/backstop-grace"
```

Erwartet (real 19.09. vor dem Fetch):

```
2b2c403b59b416a8fd3304cb0fa1c9979c86e2a8
2b2c403b fix(skip): examine rain from the run's start, not from the day after it (#146)
0b41864440c9067558c27578bedac1b85a630ca3
1
0
kein origin/fix/backstop-grace
```

Ist `upstream/master` nach dem Fetch NICHT `2b2c403b59b416a8fd3304cb0fa1c9979c86e2a8`: **STOPP und den User fragen.** Die
Referenz `dry6` ist auf `2b2c403b` geprüft; eine neuere Basis braucht erst einen neuen Probelauf-Rebase und neue Zahlen.

- [ ] **Step 4: Arbeitsbranch auf die Basis vorspulen**

```bash
cd D:/Entwicklung/HASI/HAsmartirrigation
git checkout fix/backstop-grace
git merge --ff-only upstream/master
git log --oneline -1
git rev-list --count HEAD..upstream/master
git rev-list --count upstream/master..HEAD
git status --short
```

Erwartet: der Wechsel gelingt (untracked `docs/SESSION-STAND.md` steht in keinem der beiden Bäume); `merge` meldet
`Fast-forward` (übriger Wortlaut nicht gemessen); `2b2c403b fix(skip): examine rain from the run's start, not from the day
after it (#146)`; `0`; `0`; `?? docs/SESSION-STAND.md`. Verweigert `git checkout` den Wechsel oder ist kein Fast-forward
möglich: STOPP.

- [ ] **Step 5: Referenzbranch prüfen**

```bash
cd D:/Entwicklung/HASI/HAsmartirrigation
git rev-parse dry6/backstop-grace
git merge-base --is-ancestor 2b2c403b dry6/backstop-grace && echo BASIS-IST-VORFAHR
git log --oneline 2b2c403b..dry6/backstop-grace
git -C D:/Entwicklung/HASI/pr139-work/dry2 rev-parse --git-common-dir
git -C D:/Entwicklung/HASI/pr139-work/dry2 branch --show-current
git -C D:/Entwicklung/HASI/pr139-work/dry2 status --short; echo "(dry2-status-ende)"
```

Erwartet (real 19.09. abends):

```
70dc0c185e57bc6b88003689c2198c8e6b54ad8a
BASIS-IST-VORFAHR
70dc0c18 feat(i18n): translate and document the latency margin zone field
0e68d978 feat(panel): add latency margin field for confirmed service zones
0c0c9416 feat(service): keep a confirmed run in flight through its finish grace
4819d2fc feat(service): carry the finish grace across a restart
f1266999 feat(service): measure a manual stop on the valve's own window
c234fb23 feat(run-watch): settle a confirmed service run on its valve window
dd43f09c feat(run-watch): record a confirmed valve's own off report
c6a4c842 feat(service): wait out the finish grace before a confirmed run's backstop
a6a9e382 feat(run-watch): add the finish-grace run keys, policy flag and helpers
ca77c287 feat(service): add a per-zone latency margin setting for confirmed valves
D:/Entwicklung/HASI/HAsmartirrigation/.git
dry6/backstop-grace
(dry2-status-ende)
```

Anderer SHA, fehlender Commit oder ein nicht leerer `dry2`-Status: STOPP.

- [ ] **Step 6: Volle Suite als Basis messen (am selben Tag wie Task 13)**

```bash
cd D:/Entwicklung/HASI/HAsmartirrigation
mkdir -p D:/Entwicklung/HASI/pr139-work/tmp D:/Entwicklung/HASI/pr139-work/npm-cache && export TEMP=D:/Entwicklung/HASI/pr139-work/tmp TMP=D:/Entwicklung/HASI/pr139-work/tmp TMPDIR=D:/Entwicklung/HASI/pr139-work/tmp npm_config_cache=D:/Entwicklung/HASI/pr139-work/npm-cache
W=D:/Entwicklung/HASI/pr139-work
B=$W/baseline-2b2c403b-fix-$(date +%m%d).txt
test "$(git rev-parse HEAD)" = 2b2c403b59b416a8fd3304cb0fa1c9979c86e2a8 && echo HEAD-IST-BASIS
D:/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests -p _local_socket_unblock -q -rfE -p no:cacheprovider > "$B" 2>&1
echo "$B"; grep "^collected" "$B"; tail -n 1 "$B"; grep "^FAILED" "$B"
names() { grep -E '^(FAILED|ERROR) ' "$1" | sed 's/ - .*//' | sort -u; }
comm -3 <(names $W/baseline-2b2c403b.txt) <(names "$B") | head -20; echo "(comm-ende)"
```

Erwartet (Referenz: gemessen 19.09. im Worktree `dry2` bei `2b2c403b`, Datei `baseline-2b2c403b.txt`, ~4 min):
`HEAD-IST-BASIS`, `collected 3022 items`,
`= 7 failed, 3006 passed, 9 skipped, 10 warnings, 320 errors in 240.90s (0:04:00) =` (Laufzeit variiert) mit genau diesen
FAILED-Namen (vorbestehend unter Windows/HA 2024.12.5):

```
FAILED tests/test_init.py::TestSmartIrrigationIntegration::test_async_setup_entry_success
FAILED tests/test_init.py::TestSmartIrrigationIntegration::test_async_setup_entry_with_weather_service
FAILED tests/test_next_irrigation_sensor.py::TestSetupAnnouncesSchedules::test_setup_entry_announces_after_loading_schedules
FAILED tests/test_opensprinkler_teardown.py::TestShutdown::test_a_real_stop_stops_the_stations
FAILED tests/test_opensprinkler_teardown.py::TestShutdown::test_a_restart_leaves_the_run_to_be_re_adopted
FAILED tests/test_opensprinkler_teardown.py::TestShutdown::test_the_hook_does_not_outlive_its_coordinator
FAILED tests/test_panel.py::TestSmartIrrigationPanel::test_async_register_panel_static_path_config
```

und `comm -3` ohne Zeile, also direkt `(comm-ende)`. Weichen Zahlen oder Namen ab (an einem anderen Tag als dem 19.09.
möglich, die Suite ist datumsabhängig): dem User melden und vor Task 1 klären. Die neue Datei ist die Basis für Task 13.
Findet Task 13 nicht am selben Kalendertag statt, misst Task 13 die Basis an seinem Tag erneut in einem temporären,
abgekoppelten Worktree bei `2b2c403b`.

- [ ] **Step 7: vitest-Basis messen**

```bash
cd D:/Entwicklung/HASI/HAsmartirrigation/custom_components/irrigation_plus/frontend
mkdir -p D:/Entwicklung/HASI/pr139-work/tmp D:/Entwicklung/HASI/pr139-work/npm-cache && export TEMP=D:/Entwicklung/HASI/pr139-work/tmp TMP=D:/Entwicklung/HASI/pr139-work/tmp TMPDIR=D:/Entwicklung/HASI/pr139-work/tmp npm_config_cache=D:/Entwicklung/HASI/pr139-work/npm-cache
node --version
npm ci > D:/Entwicklung/HASI/pr139-work/replay/T00-npm-ci.txt 2>&1; echo "npm ci exit $?"
npm test 2>&1 | grep -E "Test Files|Tests "
```

Erwartet: `v24.15.0` (real 19.09.); `npm ci exit 0`; dann

```
 Test Files  22 passed (22)
      Tests  616 passed (616)
```

Quelle der 616: Messung 19.09. laut Workflow-Auftrag, kein Protokoll in `pr139-work`; gegengerechnet aus `dry6`
(`23 passed (23)` / `624 passed (624)`, `dry6-logs/full-suite.md`) minus T11s eine Datei mit 8 Tests. `npm ci` legt
auch die `node_modules` an, die Task 11 und 12 brauchen.

- [ ] **Step 8: Mutationswerkzeuge prüfen (für Task 13)**

```bash
M=D:/Entwicklung/HASI/pr139-work/mut
sha256sum $M/dry3_t5_probes.py $M/dry3_t7_probes.py $M/dry3_t8_probes.py $M/mutate.py
grep -c 'newline=""' $M/dry3_t5_probes.py $M/dry3_t7_probes.py $M/dry3_t8_probes.py
ls $M/rev3_probes.py 2>/dev/null || echo "rev3_probes.py: legt Task 13 Step 8 an"
```

Erwartet (real 19.09. abends):

```
4632ddbb42a37e69b88888ab2668d8f89b5bd5aea7bdf0301cb1bcf87c34da7d *…/dry3_t5_probes.py
fa8bdeb62991aaa95e099db10ef45d7ef797d0baa49377aa7aada416cde9b0f3 *…/dry3_t7_probes.py
fee0092ec0b602489bd1f2a971b9c8b0de372c04395822e4809b63c509a23c7e *…/dry3_t8_probes.py
2768512c815829d6db727b1b0b57a1eff0553db61e07a073e999cc3b13381e3a *…/mutate.py
```

dazu `grep -c` je Skript `2` (Lesen und Schreiben mit `newline=""`, CRLF-erhaltend) und
`rev3_probes.py: legt Task 13 Step 8 an`. Die drei `dry3`-Skripte sind die Vorlagen der CRLF-Proben in Task 13; alle 46
Suchtexte kommen auf dry6 genau einmal vor (geprüft 19.09. abends, lesend). Der Hash von `mutate.py` belegt nur die
Probeläufe; Task 13 benutzt es nicht. Anderer Hash eines `dry3`-Skripts: dem User melden, bevor Task 13 Proben fährt.

- [ ] **Step 9: Kein Commit.** Weiter mit Task 1 nach dem Nachvollzug (Block A–C).

---

# #139 Finish-Backstop mit Wartezeit — Plan Revision 3, Teil a: Task 1, 2, 3, 3b, 4, 5

> Teil des Plans Revision 3 (2026-09-19, Referenz seit dem Abend `dry6`). Kopf (Grundlagen, Entscheidungen,
> Nachvollzug-Verfahren, Task 0) und die Tasks ab 7 stehen in den anderen Teilen. Jeder Task hier ist ein
> **Nachvollzug** (E9) eines geprüften Commits von `dry6/backstop-grace` (Worktree `D:/Entwicklung/HASI/pr139-work/dry2`,
> Basis `2b2c403b`): Tests aus dem `dry6`-Commit auschecken, RED gegen den Plan prüfen, dann die Produktivdateien
> auschecken, GREEN + 7 Suiten + Lint, Baum gegen den `dry6`-Commit prüfen, mit derselben Nachricht committen. Code wird
> nicht abgetippt.

## Lesehilfe für Task 1–5

- **Kennzeichnung.** „Erwartet (real, Quelle)“ ist aus einem Protokoll kopiert. „Soll (nicht gemessen)“ folgt aus dem
  Verfahren und wird im Nachvollzug zum ersten Mal beobachtet. Pfade von Protokollen relativ zu
  `D:/Entwicklung/HASI/pr139-work/`.
- **Quellen der Zahlen.** RED/GREEN je Task: `rev3/evidence.md` (T1/T2 von dry5 mit denselben SHAs, Rohdaten
  `rev3/raw/`; T3–T5 am 19.09. abends auf dry6 neu gemessen, Rohdaten `dry6-logs/evidence-raw/Tn_{RED,GREEN}.txt`, alles
  im Worktree `dry2`). 7 Suiten + i18n je Commit: T3–T5 `dry6-logs/percommit.md`, T2 `scratch/dry5-checks.log`
  (derselbe Commit), T1 `replaycheck-logs/T01-suites.txt` (19.09.). black je Commit: `scratch/dry5-checks.log` (Skript
  `scratch/dry5-checks.sh`); dry6 fügt keine Testdatei hinzu, die Dateimenge und damit die Zahl bleibt gleich, ruff
  auf dry6 je Commit sauber (`dry6-logs/percommit.md`). Commit-Statistik: `git show --stat` laut `rev3/evidence.md`.
  Mutationsproben T1–T4: Plan Revision 2 (`archive-wt/docs/superpowers/plans/2026-09-15-backstop-grace.md`), dazu die
  dry6-Proben (`dry6-logs/T3.md`, `dry6-logs/probes.md`); T5: `dry3-logs/T5.md`, `dry3-logs/T5-probes.txt` und
  `dry6-logs/T5.md`.
- **Protokolle.** Jeder Lauf schreibt nach `D:/Entwicklung/HASI/pr139-work/replay/<Tnn>-{red,green,suites}.txt` (wie
  Block A/B im Kopfteil); die Befehle zeigen danach die auszuwertenden Zeilen.
- **Pfadpräfix.** Die RED-Protokolle stammen aus `dry2`; im Nachvollzug steht `D:\Entwicklung\HASI\HAsmartirrigation\`
  statt `D:\Entwicklung\HASI\pr139-work\dry2\`. Gleich sein müssen: FAILED/ERROR-Zeilen, Zeilennummern und Text der
  Assertions, die Zählzeile. Nicht verglichen werden Laufzeiten, Speicheradressen (`at 0x…`) und Zeitstempel.
- **`�` in den Protokollen** ist das `±` aus `pytest.approx`; die Windows-Konsole stellt es falsch dar
  (`rev3/evidence.md`, Methodik-Korrektur).
- **Der eine vorbestehende Error.** Jeder Lauf mit `tests/test_service_watch.py` zeigt
  `ERROR tests/test_service_watch.py::TestOneOffSampleIsNotEvidenceTheWaterStopped::test_the_run_is_not_settled_before_the_window_is_out`
  (`Failed: Lingering timer after job <Job call_later 5 ...>`), RED wie GREEN, Basis wie Commit (`rev3/evidence.md`).
  Kein Effekt eines Tasks.
- **RED-Befehl** mit `--tb=line -rfE` wie im Probelauf (eine Zeile je Assertion), dazu `-q -p no:cacheprovider`.
- **7 Suiten + i18n** = Liste `SEVEN` aus `scratch/dry5-checks.sh`:
  `tests/test_service_watch.py tests/test_finish_grace_helpers.py tests/test_run_in_flight.py tests/test_confirm_reserve.py tests/test_self_closing.py tests/test_run_watch.py tests/test_observed_watering.py tests/test_i18n_completeness.py`.
  `tests/test_finish_grace_helpers.py` entsteht erst in Task 2. Das Protokoll zeigt für T1 deshalb `no tests ran`;
  Task 1 lässt die Datei weg und nimmt seine zwei eigenen Testdateien dazu.
- **Lint-Dateiliste** `$(git diff --name-only 2b2c403b -- tests)` = alle bis dahin berührten Testdateien (Arbeitsbaum
  gegen die Basis). Sie entspricht `git diff --name-only 2b2c403b HEAD -- tests` am abgekoppelten Commit in
  `scratch/dry5-checks.sh`; daher die Dateizahlen 70/71/72 unten.
- **Commit wie Block C im Kopfteil.** `git commit -F <(git log -1 --format=%B "$SRC")` funktioniert in dieser Git-Bash
  nicht. Gemessen 19.09. mit derselben Prozess-Substitution, nur lesend:
  `git hash-object <(git log -1 --format=%B ca77c287)` --> `fatal: could not open '/proc/1304/fd/63' for reading: No such file or directory`.
  `git.exe` ist ein natives Windows-Programm und sieht den `/proc`-Pfad der MSYS-Bash nicht; die PID wechselt je Lauf.
  Die Tasks geben die Nachricht deshalb per Pipe an `git commit -q -F -`. `TREE-SAME` und `MSG-SAME` danach belegen,
  dass Baum und Nachricht dem `dry6`-Commit gleichen (`diff <(…) <(…)` geht, weil `diff` ein MSYS-Programm ist).
- **Weicht RED oder GREEN ab: STOPP.** Nicht committen, dem User berichten, der Arbeitsbaum bleibt für die Diagnose
  stehen. Kein `git reset --hard` (globale Git-Regel). `git checkout -- .` stellt den Stand NICHT her, weil der Index
  schon die `dry6`-Version trägt (`rev3/evidence.md`, Methodik-Korrektur).
- **Voraussetzung aus Task 0:** Branch `fix/backstop-grace`, HEAD `2b2c403b`, `git status --short` nur
  `?? docs/SESSION-STAND.md`. Stand 19.09. (nur gelesen): `fix/backstop-grace` steht noch auf `0b418644`, der
  Hauptarbeitsbaum auf `fix/rain-guard-run-date`. Die `dry6`-SHAs lösen im Hauptrepo auf (gemeinsamer Objektspeicher,
  `git cat-file -t c6a4c842` --> `commit`, `git cat-file -t 70dc0c18` --> `commit`, geprüft 19.09. abends).
- **Mutationsproben.** Die Tabellen je Task stammen aus den Probeläufen. Die Änderungszeilen auf `dry6` sind die von
  `dry5`, und die sind mit `dry4` identisch (`scratch/d4.txt` = `scratch/d5.txt`); `dry4` unterscheidet sich von
  `dry2`/`dry3` für T1–T5 nur in Texten und in den Entscheidungen, die die Tabellen nennen. Jeder Suchtext kommt am
  `dry5`-Commit des Tasks genau einmal vor (geprüft 19.09. per Skript gegen `git show SHA:DATEI`, LF-normalisiert);
  am dry6-Endstand kommt jede Ersetzung des Treibers `mut/rev3_probes.py` und jeder Suchtext der CRLF-Skripte genau
  einmal vor (geprüft 19.09. abends, lesend). Die mit „dry6“ markierten Proben liefen am 19.09. abends auf dry6
  (`dry6-logs/T3.md`, `T5.md`, `probes.md`). **Task 13 läuft alle Proben auf dem echten Branch erneut** (E9): T1–T4,
  den Rev.-2-Teil von T5 und die T6-Pin-Probe mit dem Treiber `mut/rev3_probes.py`, den (b)-Teil von T5 mit dem
  CRLF-Skript `mut/real_t5_probes.py` (Kopie von `mut/dry3_t5_probes.py`), je mit Sicherung als `.bak` und
  SHA-256-Prüfung nach jeder Probe (plan-30, Task 13 Step 8). Testzahlen wie `29 deselected` stammen aus dem jeweiligen
  Probelauf und können auf dem echten Branch abweichen. Übertragbar ist, welche Tests fallen und mit welcher Assertion.

---

### Task 1: Latenz-Marge als Zonenfeld (gespeichert, geladen, per POST setzbar; noch ohne Wirkung)

**dry6:** `ca77c287` (derselbe Commit wie auf dry5) — `feat(service): add a per-zone latency margin setting for confirmed valves`

**Files** (Zeilen auf `ca77c287`):
- TEST: `tests/test_distributor_integration.py`, `tests/test_store_self_closing.py`
- PROD: `custom_components/irrigation_plus/const.py` (Service-Block `:860-871`),
  `custom_components/irrigation_plus/store.py` (Importe `:111`, `:167`; `ZoneEntry.latency_margin` `:296-299`;
  Ladeblock `:1200-1204`), `custom_components/irrigation_plus/websockets.py` (Zonen-Schema `:305-309`)
- `git show --stat` (evidence.md): `5 files changed, 126 insertions(+)`

**Was und warum**
- Anforderung 1 aus #139: der Backstop bekommt eine Latenz-Marge **je Zone**. Dieser Task legt nur das Feld an:
  `ZONE_LATENCY_MARGIN = "latency_margin"`, `DEFAULT_LATENCY_MARGIN_SECONDS = 4`, `MAX_LATENCY_MARGIN_SECONDS = 30`
  (`const.py`), `latency_margin = attr.ib(type=int, default=DEFAULT_LATENCY_MARGIN_SECONDS)` auf `ZoneEntry`, die
  Ladezeile `zone.get(ZONE_LATENCY_MARGIN, DEFAULT_LATENCY_MARGIN_SECONDS)` und
  `vol.Optional(const.ZONE_LATENCY_MARGIN): vol.Coerce(int)` im Schema von `SmartIrrigationZoneView`.
- Default 4 s (E2, von JustChr 09-16 angenommen): deckt die gemessene Notwendigkeit (Beet 13.09.: Backstop 2,03 s vor
  der Aus-Meldung) mit ~2 s Luft und die rohe Tuya-Latenz (2,08–2,90 s nach dem Fenster) mit 1,1 s. Obergrenze 30,
  damit ein Tippfehler eine Kette nicht minutenlang hält.
- Die Ladezeile ist Pflicht: ohne sie gewinnt der `attr`-Default, und ein gesetzter Wert fiele bei jedem Neustart auf
  4 zurück. `Coerce(int)`, weil das Schema Zusatzschlüssel durchlässt und ein gePOSTetes `"6"` sonst als String im
  Store landet. Das Feld steht nicht in der Liste der servereigenen Felder, der User setzt es.
- Kein `STORAGE_VERSION`-Sprung (14 bleibt). Eine vor #139 gespeicherte Zone lädt mit 4; jede bestehende Service-Zone
  mit `confirm_entity` bekommt damit 4 s (Reichweite, PR-Text).
- Kein Laufverhalten ändert sich. Die Marge wirkt erst ab Task 3.

**Tests**
- `tests/test_store_self_closing.py::test_latency_margin_survives_reload` — Marge 7 übersteht einen Neuladevorgang über
  das eigene Persistenzformat (`attr.asdict`); pinnt die Ladezeile.
- `tests/test_store_self_closing.py::test_zone_stored_without_latency_margin_loads_the_default` — eine Zone ohne
  Schlüssel lädt mit 4, und `DEFAULT_LATENCY_MARGIN_SECONDS == 4`.
- `tests/test_distributor_integration.py::test_zone_view_coerces_latency_margin_to_int` — ein gePOSTetes `"6"` kommt
  als `int` 6 beim Koordinator an.
- Neue Test-Helfer `_reload_payload(reg)` und `_reloaded(hass, data)` in `tests/test_store_self_closing.py`.
  Fixture-Namen: `Beet`/`script.irrigation_beet`/`valve.beet` (stehen upstream schon in der Datei, E7) und neutral
  `Front`/`script.irrigation_front`/`valve.front`.

- [ ] **Step 1: Tests aus dem `dry6`-Commit auschecken**

```bash
cd /d/Entwicklung/HASI/HAsmartirrigation
SRC=ca77c287; TESTS="tests/test_distributor_integration.py tests/test_store_self_closing.py"
git branch --show-current
git log --oneline -1
git status --short
[ "$(git rev-parse HEAD^{tree})" = "$(git rev-parse "$SRC~1^{tree}")" ] && echo PARENT-TREE-SAME
git checkout "$SRC" -- $TESTS
git status --short
```

Erwartet: `fix/backstop-grace`; `2b2c403b fix(skip): examine rain from the run's start, not from the day after it (#146)`
(Betreff real, `git log` in `dry2`); vor dem Checkout nur `?? docs/SESSION-STAND.md`. Soll (nicht gemessen):
`PARENT-TREE-SAME`, danach `M  tests/test_distributor_integration.py`, `M  tests/test_store_self_closing.py`,
`?? docs/SESSION-STAND.md`.

- [ ] **Step 2: RED prüfen**

```bash
cd /d/Entwicklung/HASI/HAsmartirrigation
mkdir -p D:/Entwicklung/HASI/pr139-work/tmp D:/Entwicklung/HASI/pr139-work/npm-cache && export TEMP=D:/Entwicklung/HASI/pr139-work/tmp TMP=D:/Entwicklung/HASI/pr139-work/tmp TMPDIR=D:/Entwicklung/HASI/pr139-work/tmp npm_config_cache=D:/Entwicklung/HASI/pr139-work/npm-cache
TESTS="tests/test_distributor_integration.py tests/test_store_self_closing.py"
L=D:/Entwicklung/HASI/pr139-work/replay/T01-red.txt
D:/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest $TESTS -p _local_socket_unblock -q --tb=line -rfE -p no:cacheprovider > $L 2>&1
grep -E "^collected |^(FAILED|ERROR) |^E  |\.py:[0-9]+: " $L; tail -n 1 $L
```

Erwartet (real, `rev3/evidence.md` T1 RED, Parent `2b2c403b` mit den Testdateien aus `ca77c287`):

```
collected 28 items
FAILED tests/test_distributor_integration.py::test_zone_view_coerces_latency_margin_to_int
FAILED tests/test_store_self_closing.py::test_latency_margin_survives_reload
FAILED tests/test_store_self_closing.py::test_zone_stored_without_latency_margin_loads_the_default
======================== 3 failed, 25 passed in 2.27s =========================
```

mit diesen Assertion-Zeilen:

```
D:\Entwicklung\HASI\pr139-work\dry2\tests\test_distributor_integration.py:327: AttributeError: module 'custom_components.irrigation_plus.const' has no attribute 'ZONE_LATENCY_MARGIN'
D:\Entwicklung\HASI\pr139-work\dry2\tests\test_store_self_closing.py:123: AttributeError: module 'custom_components.irrigation_plus.const' has no attribute 'ZONE_LATENCY_MARGIN'
D:\Entwicklung\HASI\pr139-work\dry2\tests\test_store_self_closing.py:150: AttributeError: module 'custom_components.irrigation_plus.const' has no attribute 'ZONE_LATENCY_MARGIN'
```

Genau die drei neuen Tests fallen, alle an der fehlenden Konstante; die 25 übrigen Tests der beiden Dateien bleiben grün.

- [ ] **Step 3: Produktivdateien aus dem `dry6`-Commit auschecken**

```bash
cd /d/Entwicklung/HASI/HAsmartirrigation
SRC=ca77c287; PROD="custom_components/irrigation_plus/const.py custom_components/irrigation_plus/store.py custom_components/irrigation_plus/websockets.py"
git checkout "$SRC" -- $PROD
```

- [ ] **Step 4: GREEN, 7 Suiten + i18n + eigene Dateien**

```bash
cd /d/Entwicklung/HASI/HAsmartirrigation
mkdir -p D:/Entwicklung/HASI/pr139-work/tmp D:/Entwicklung/HASI/pr139-work/npm-cache && export TEMP=D:/Entwicklung/HASI/pr139-work/tmp TMP=D:/Entwicklung/HASI/pr139-work/tmp TMPDIR=D:/Entwicklung/HASI/pr139-work/tmp npm_config_cache=D:/Entwicklung/HASI/pr139-work/npm-cache
TESTS="tests/test_distributor_integration.py tests/test_store_self_closing.py"
SUITES="tests/test_service_watch.py tests/test_run_in_flight.py tests/test_confirm_reserve.py tests/test_self_closing.py tests/test_run_watch.py tests/test_observed_watering.py tests/test_i18n_completeness.py"
D:/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest $TESTS -p _local_socket_unblock -q --tb=line -rfE -p no:cacheprovider > D:/Entwicklung/HASI/pr139-work/replay/T01-green.txt 2>&1; tail -n 1 D:/Entwicklung/HASI/pr139-work/replay/T01-green.txt
D:/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest $SUITES $TESTS -p _local_socket_unblock -q --tb=line -rfE -p no:cacheprovider > D:/Entwicklung/HASI/pr139-work/replay/T01-suites.txt 2>&1
grep -E "^(FAILED|ERROR) " D:/Entwicklung/HASI/pr139-work/replay/T01-suites.txt | sed 's/ - .*//'
tail -1 D:/Entwicklung/HASI/pr139-work/replay/T01-suites.txt
```

Erwartet: Taskdateien (real, `rev3/evidence.md` T1 GREEN)
`============================= 28 passed in 2.10s ==============================`.
Suiten: `238 passed, 1 error` (Replay-Probe 19.09. mit genau dieser Dateiliste, `replaycheck-logs/T01-suites.txt`:
`collected 238 items`, `238 passed, 1 error in 15.11s`; passt rechnerisch zu T2: 240 − 30 Items von
`tests/test_finish_grace_helpers.py` + 28 Items der T1-Dateien). Die einzige `ERROR`-Zeile ist der vorbestehende
Lingering timer, keine `FAILED`-Zeile.

- [ ] **Step 5: Lint**

```bash
cd /d/Entwicklung/HASI/HAsmartirrigation
mkdir -p D:/Entwicklung/HASI/pr139-work/tmp D:/Entwicklung/HASI/pr139-work/npm-cache && export TEMP=D:/Entwicklung/HASI/pr139-work/tmp TMP=D:/Entwicklung/HASI/pr139-work/tmp TMPDIR=D:/Entwicklung/HASI/pr139-work/tmp npm_config_cache=D:/Entwicklung/HASI/pr139-work/npm-cache
uvx black --check custom_components/irrigation_plus/ $(git diff --name-only 2b2c403b -- tests)
uvx ruff check custom_components/irrigation_plus/
```

Erwartet (real, `scratch/dry5-checks.log` bei `ca77c287`): `70 files would be left unchanged.` / `All checks passed!`

- [ ] **Step 6: Baum gleich `dry6`**

```bash
cd /d/Entwicklung/HASI/HAsmartirrigation
SRC=ca77c287
git diff "$SRC" --stat
git status --short
```

Soll (nicht gemessen): `git diff` leer; Status die fünf Dateien als `M ` (gestagt durch den Checkout) und
`?? docs/SESSION-STAND.md`.

- [ ] **Step 7: Commit mit derselben Nachricht**

```bash
cd /d/Entwicklung/HASI/HAsmartirrigation
SRC=ca77c287
git log -1 --format=%B "$SRC" | git commit -q -F -
test "$(git rev-parse HEAD^{tree})" = "$(git rev-parse "$SRC^{tree}")" && echo TREE-SAME
diff <(git log -1 --format=%B HEAD) <(git log -1 --format=%B "$SRC") && echo MSG-SAME
git log -1 --format=%B | grep -c '^#'
git show --stat --format= HEAD | tail -1
git log --oneline -1
git status --short
```

Soll (nicht gemessen): `TREE-SAME`, `MSG-SAME`, `0` (keine Zeile mit `#` am Anfang),
` 5 files changed, 126 insertions(+)` (Zahl real aus `git show --stat ca77c287`), `<neuer SHA> feat(service): add a
per-zone latency margin setting for confirmed valves`, danach nur `?? docs/SESSION-STAND.md`.

**Mutationsproben (Probelauf)**

Gemessen im Revisions-Probelauf `dry2` auf Basis `0b418644`, Commit `745e4bac` (Plan Revision 2, Task 1, Step 10;
T1 blieb in `dry3` unverändert, Range-Diff `=`, `dry3-logs/final.md` §5). Lauf je Probe: `-k "latency_margin"` auf
`tests/test_store_self_closing.py tests/test_distributor_integration.py` (3 Tests ausgewählt, 25 abgewählt; auf `dry6`
ohne Mutation gemessen: `3 passed, 25 deselected`). `store-revert` schreibt den Stand der Basis zurück (Treiber:
`base_file`); auf dem echten Branch
`git show 2b2c403b:custom_components/irrigation_plus/store.py > custom_components/irrigation_plus/store.py` (`store.py`
ist zwischen `0b418644` und `2b2c403b` unverändert, `rev3/spec.md`, Zeilenangaben). Task 13 läuft die Proben erneut.

| Probe | Mutation (Suchtext --> Ersatz) | Test | Beobachtet (Probelauf) |
|---|---|---|---|
| load-line | `store.py`: `                        latency_margin=zone.get(\n                            ZONE_LATENCY_MARGIN, DEFAULT_LATENCY_MARGIN_SECONDS\n                        ),\n` --> leer | `test_latency_margin_survives_reload` | FAIL `assert 4 == 7` (1 failed, 2 passed) |
| load-default | `store.py`: dieselben drei Zeilen --> `                        latency_margin=zone.get(ZONE_LATENCY_MARGIN),\n` | `test_zone_stored_without_latency_margin_loads_the_default` | FAIL `assert None == 4` (1 failed, 2 passed) |
| const-default | `const.py`: `DEFAULT_LATENCY_MARGIN_SECONDS = 4` --> `DEFAULT_LATENCY_MARGIN_SECONDS = 5` | `test_zone_stored_without_latency_margin_loads_the_default` | FAIL `assert 5 == 4` (1 failed, 2 passed) |
| store-revert | `store.py` komplett auf den Stand der Basis | beide Store-Tests | FAIL 2x `KeyError: 'latency_margin'` (2 failed, 1 passed) |
| ws-coerce-removed | `websockets.py`: `                vol.Optional(const.ZONE_LATENCY_MARGIN): vol.Coerce(int),\n` --> leer | `test_zone_view_coerces_latency_margin_to_int` | FAIL `AssertionError: assert '6' == 6` (1 failed, 2 passed) |
| ws-coerce-float | `websockets.py`: `vol.Optional(const.ZONE_LATENCY_MARGIN): vol.Coerce(int)` --> `vol.Optional(const.ZONE_LATENCY_MARGIN): vol.Coerce(float)` (nur `vol.Coerce(int)` allein kommt 17-mal vor) | `test_zone_view_coerces_latency_margin_to_int` | FAIL `assert False` / `where False = isinstance(6.0, int)` (1 failed, 2 passed) |

6 von 6 gefangen; jeder der drei neuen Tests scheitert an mindestens einer Probe.

---

### Task 2: Laufdaten-Schlüssel, Policy-Flag und reine Helfer für die Wartezeit (noch ohne Aufrufer)

**dry6:** `a6a9e382` (derselbe Commit wie auf dry5) — `feat(run-watch): add the finish-grace run keys, policy flag and helpers`

**Files** (Zeilen auf `a6a9e382`):
- TEST: `tests/test_finish_grace_helpers.py` (neu)
- PROD: `custom_components/irrigation_plus/const.py` (`RUN_LATENCY_MARGIN` `:981`, `RUN_VALVE_ON` `:989`,
  `RUN_VALVE_OFF` `:1005`, direkt nach `RUN_WATCH_ENTITY`), `custom_components/irrigation_plus/run_watch.py`
  (`WatchPolicy.settles_on_valve_window` `:206-219`; Modul-Helfer `:267-339` zwischen `run_credit_ceiling` und
  `queue_deadline_seconds`), `custom_components/irrigation_plus/self_closing.py` (`SERVICE_WATCH_POLICY` setzt das Flag,
  `:63-68`)
- `git show --stat` (evidence.md): `4 files changed, 394 insertions(+)`

**Was und warum**
- Dispatch (T3), Watcher (T5), manueller Stopp (T7), Neustart (T8) und In-flight (T9) sollen dieselbe Antwort auf vier
  Fragen lesen: welcher Lauf wartet über sein Fenster hinaus, wie lange, wie weit unter dem Fenster gilt noch als
  abgeschlossen, und wie lange war das Ventil offen. Reine Funktionen in `run_watch.py`, ohne `hass`:
  `zone_latency_margin(zone)` (ganze Sekunden, gerundet, auf 0–30 geklemmt, fehlend oder unlesbar --> 4),
  `run_latency_margin(run)` (eingefrorene Marge oder `None`), `run_has_finish_grace(run)` (das Tor),
  `run_finish_grace_seconds(run)` (Entprellung + Marge, sonst 0), `run_completion_tolerance(run)` (max(1, Marge),
  ohne Tor 1) und `valve_window_seconds(run, now)` (Anker `RUN_VALVE_ON`, sonst `RUN_OBSERVED_START`, sonst
  `RUN_STARTED`; mit Aus-Meldung `off − Anker`, nie kleiner 0; ohne sie `min(now − Anker, planned)`; ohne Anker
  `planned`).
- **Das Tor** ist Policy-Flag `settles_on_valve_window` (nur `SERVICE_WATCH_POLICY` setzt `True`) UND
  `RUN_WATCH_ENTITY` UND eingefrorene Marge. `RUN_WATCH_ENTITY` allein reicht nicht, OpenSprinkler- und
  Batch-Datensätze tragen ihn auch (`self_closing.py:596`, `batch.py:359`). Ein Datensatz von vor dem Update hat keine
  Marge und behält die Zeitsteuerung, unter der er gestartet wurde.
- Die drei Laufdaten-Schlüssel sind in `const.py` dokumentiert. Laufdatensätze sind rohe Dicts in
  `active_valve_runs`, neue Schlüssel brauchen keine Schema-Änderung. Der Kommentar zu `RUN_VALVE_OFF` beschreibt schon
  Entscheidung (b): nur ein Lauf mit dieser Meldung wird auf seinem Fenster abgerechnet, ein Schluss ohne Meldung
  behält die Uhr-Regel des Watchers (Textänderung aus `dry3`, `dry3-logs/T5.md` Stopp 1).
- **`zone_finish_grace_seconds` gibt es nicht mehr** (Entscheidung (e)). Nur die gestrichene Observed-Sperre (T3b)
  rief ihn; er wurde mit seiner Testklasse `TestZoneFinishGrace` (5 Tests) aus T2 herausgefaltet
  (`dry3-logs/final.md` §6, danach `dry4`).
- **Batch-Pin** statt Pause/Resume-Test für Service (Abweichung zu Anforderung 4/7, von JustChr 09-16 bestätigt):
  `_watch_resume` ist für Service unerreichbar (nur bei `policy.segmented`), eine Marge dort änderte nur Batch. Der
  Test pinnt, dass eine pausierte Batch-Wiederaufnahme mit denselben Schlüsseln weiter genau `remaining` plant.
- Kein Aufrufer ändert sich. Batch und OpenSprinkler bleiben byte-gleich.

**Tests** (`tests/test_finish_grace_helpers.py`, neu; 26 Testfunktionen, eine davon mit 5 Parametern --> 30 Items).
`rev3/evidence.md` spricht von 26 Namen, führt aber nur 25 auf und vermutet deshalb 4 Items ohne neuen Namen.
Nachgezählt 19.09. mit `git show a6a9e382:tests/test_finish_grace_helpers.py`: in der Liste fehlt nur der asynchrone
`test_resume_re_arms_the_backstop_for_the_remaining_window_only`; 26 − 1 + 5 = 30, keine verschobenen Tests.
- `TestZoneLatencyMargin::test_the_margin_is_whole_seconds_clamped_to_its_bounds` — `"7"`-->7, 7,6-->8, −3-->0, 99-->30,
  `"x"`-->4 (5 Parameter).
- `TestZoneLatencyMargin::test_a_zone_stored_without_a_margin_gets_the_default` — Zone ohne Schlüssel und `None` --> 4.
- `TestRunLatencyMargin::test_the_frozen_margin_is_read_back_as_seconds` — 4 --> 4,0, `"6"` --> 6,0.
- `TestRunLatencyMargin::test_a_record_without_a_margin_answers_none` — kein Schlüssel oder kein Dict --> `None`.
- `TestRunLatencyMargin::test_a_negative_margin_reads_as_zero_and_garbage_as_none` — −2 --> 0,0, `"x"` --> `None`.
- `TestRunHasFinishGrace::test_a_confirmed_service_run_with_a_margin_has_it` — das Tor ist offen.
- `TestRunHasFinishGrace::test_a_record_from_before_the_update_has_none` — ohne eingefrorene Marge zu.
- `TestRunHasFinishGrace::test_an_unconfirmed_run_has_none` — ohne `RUN_WATCH_ENTITY` zu.
- `TestRunHasFinishGrace::test_a_batch_record_carrying_both_keys_has_none` — Batch mit beiden Schlüsseln: zu.
- `TestRunHasFinishGrace::test_an_opensprinkler_record_carrying_both_keys_has_none` — OpenSprinkler ebenso.
- `TestRunFinishGraceAndTolerance::test_the_grace_is_settle_plus_the_frozen_margin` — 5 + 4 = 9,0.
- `TestRunFinishGraceAndTolerance::test_a_run_without_grace_waits_nothing_extra` — ohne Tor 0,0.
- `TestRunFinishGraceAndTolerance::test_the_completion_tolerance_is_the_margin` — Toleranz 4,0.
- `TestRunFinishGraceAndTolerance::test_the_completion_tolerance_never_drops_below_one_second` — Marge 0 --> 1,0.
- `TestRunFinishGraceAndTolerance::test_a_run_without_grace_keeps_the_one_second_slack` — Batch --> 1,0.
- `TestValveWindowSeconds::test_the_window_is_the_off_report_minus_the_on_report` — Ein +0,5, Aus +420,5 --> 420,0.
- `TestValveWindowSeconds::test_an_off_report_before_the_on_report_is_a_zero_window` — Aus vor Ein --> 0,0.
- `TestValveWindowSeconds::test_without_an_off_report_the_window_is_the_time_since_on` — ohne Aus, +300 --> 300,0.
- `TestValveWindowSeconds::test_without_an_off_report_the_window_is_bounded_by_the_plan` — ohne Aus, +900 --> 600,0.
- `TestValveWindowSeconds::test_the_anchor_falls_back_to_the_observed_start` — ohne `RUN_VALVE_ON` Anker
  `RUN_OBSERVED_START` (120,0, nicht 170,0).
- `TestValveWindowSeconds::test_the_anchor_falls_back_to_the_dispatch_instant` — ohne beide Anker `RUN_STARTED` (170,0).
- `TestValveWindowSeconds::test_a_record_with_no_anchor_answers_the_plan` — gar kein Anker --> `planned` 600,0.
- `TestOnlyTheServicePolicySettlesOnTheValveWindow::test_the_service_policy_settles_on_the_valve_window` — Service `True`.
- `TestOnlyTheServicePolicySettlesOnTheValveWindow::test_the_batch_policy_does_not` — Batch `False`.
- `TestOnlyTheServicePolicySettlesOnTheValveWindow::test_the_opensprinkler_policy_does_not` — OpenSprinkler `False`.
- `TestABatchResumeArmsExactlyTheRemainder::test_resume_re_arms_the_backstop_for_the_remaining_window_only` — Batch-Lauf
  mit Marge und Watch-Entität, 60 s bewässert: Backstop `(1, 540.0)`, kein Zuschlag.
- Neue Test-Helfer: `_iso(offset_s)`, `_service_zone(**kw)`, `_confirmed_run(mode=..., **kw)` (geplant 600 s, Marge 4,
  `RUN_STARTED` = `T0` = 2026-01-10 10:00:00 UTC), `_Host` (`SelfClosingMixin` + `RunWatchMixin` mit Lauf-Liste im
  Speicher); neutrale Entität `binary_sensor.valve_flowing` (E7).

- [ ] **Step 1: Tests aus dem `dry6`-Commit auschecken**

```bash
cd /d/Entwicklung/HASI/HAsmartirrigation
SRC=a6a9e382; TESTS="tests/test_finish_grace_helpers.py"
git status --short
[ "$(git rev-parse HEAD^{tree})" = "$(git rev-parse "$SRC~1^{tree}")" ] && echo PARENT-TREE-SAME
git checkout "$SRC" -- $TESTS
git status --short
```

Soll (nicht gemessen): vorher nur `?? docs/SESSION-STAND.md`, `PARENT-TREE-SAME` (HEAD = Nachvollzug von Task 1),
danach zusätzlich `A  tests/test_finish_grace_helpers.py`.

- [ ] **Step 2: RED prüfen**

```bash
cd /d/Entwicklung/HASI/HAsmartirrigation
mkdir -p D:/Entwicklung/HASI/pr139-work/tmp D:/Entwicklung/HASI/pr139-work/npm-cache && export TEMP=D:/Entwicklung/HASI/pr139-work/tmp TMP=D:/Entwicklung/HASI/pr139-work/tmp TMPDIR=D:/Entwicklung/HASI/pr139-work/tmp npm_config_cache=D:/Entwicklung/HASI/pr139-work/npm-cache
TESTS="tests/test_finish_grace_helpers.py"
L=D:/Entwicklung/HASI/pr139-work/replay/T02-red.txt
D:/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest $TESTS -p _local_socket_unblock -q --tb=line -rfE -p no:cacheprovider > $L 2>&1
grep -E "^collected |^(FAILED|ERROR) |^E  |\.py:[0-9]+: " $L; tail -n 1 $L
```

Erwartet (real, `rev3/evidence.md` T2 RED; Rohdaten `rev3/raw/T2_RED.txt`). RED ist hier ein Sammelfehler beim
Import, keine Assertion. `grep` und `tail` des Steps geben Folgendes aus (auf die Rohdaten angewandt, 19.09. abends).
Die letzte Zeile der Rohdaten ist ein Rahmenkommentar des Messskripts; im Step ist `$L` reine pytest-Ausgabe, `tail`
zeigt also die Summenzeile. Im Nachvollzug steht `HAsmartirrigation` statt `pr139-work\dry2` in den Pfaden; die
Laufzeit wird nicht verglichen.

```
collected 0 items / 1 error
C:\Users\Nutzer\AppData\Local\Programs\Python\Python312\Lib\importlib\__init__.py:90: in import_module
tests\test_finish_grace_helpers.py:27: in <module>
E   ImportError: cannot import name 'run_completion_tolerance' from 'custom_components.irrigation_plus.run_watch' (D:\Entwicklung\HASI\pr139-work\dry2\custom_components\irrigation_plus\run_watch.py)
ERROR tests/test_finish_grace_helpers.py
============================== 1 error in 1.49s ===============================
```

Nur in der Logdatei, nicht in dieser Ausgabe: die Kopfzeile
`ImportError while importing test module '…\tests\test_finish_grace_helpers.py'.` und
`!!!!!!!!!!!!!!!!!!! Interrupted: 1 error during collection !!!!!!!!!!!!!!!!!!!!`.

- [ ] **Step 3: Produktivdateien aus dem `dry6`-Commit auschecken**

```bash
cd /d/Entwicklung/HASI/HAsmartirrigation
SRC=a6a9e382; PROD="custom_components/irrigation_plus/const.py custom_components/irrigation_plus/run_watch.py custom_components/irrigation_plus/self_closing.py"
git checkout "$SRC" -- $PROD
```

- [ ] **Step 4: GREEN, 7 Suiten + i18n**

```bash
cd /d/Entwicklung/HASI/HAsmartirrigation
mkdir -p D:/Entwicklung/HASI/pr139-work/tmp D:/Entwicklung/HASI/pr139-work/npm-cache && export TEMP=D:/Entwicklung/HASI/pr139-work/tmp TMP=D:/Entwicklung/HASI/pr139-work/tmp TMPDIR=D:/Entwicklung/HASI/pr139-work/tmp npm_config_cache=D:/Entwicklung/HASI/pr139-work/npm-cache
TESTS="tests/test_finish_grace_helpers.py"
SEVEN="tests/test_service_watch.py tests/test_finish_grace_helpers.py tests/test_run_in_flight.py tests/test_confirm_reserve.py tests/test_self_closing.py tests/test_run_watch.py tests/test_observed_watering.py tests/test_i18n_completeness.py"
D:/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest $TESTS -p _local_socket_unblock -q --tb=line -rfE -p no:cacheprovider > D:/Entwicklung/HASI/pr139-work/replay/T02-green.txt 2>&1; tail -n 1 D:/Entwicklung/HASI/pr139-work/replay/T02-green.txt
D:/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest $SEVEN -p _local_socket_unblock -q --tb=line -rfE -p no:cacheprovider > D:/Entwicklung/HASI/pr139-work/replay/T02-suites.txt 2>&1
grep -E "^(FAILED|ERROR) " D:/Entwicklung/HASI/pr139-work/replay/T02-suites.txt | sed 's/ - .*//'
tail -1 D:/Entwicklung/HASI/pr139-work/replay/T02-suites.txt
```

Erwartet (real): Taskdatei `============================= 30 passed in 1.92s ==============================`
(`rev3/evidence.md` T2 GREEN); Suiten `======================== 240 passed, 1 error in 15.16s ========================`
(`scratch/dry5-checks.log`, `a6a9e382`), die `ERROR`-Zeile ist der vorbestehende Lingering timer, keine `FAILED`-Zeile.

- [ ] **Step 5: Lint**

```bash
cd /d/Entwicklung/HASI/HAsmartirrigation
mkdir -p D:/Entwicklung/HASI/pr139-work/tmp D:/Entwicklung/HASI/pr139-work/npm-cache && export TEMP=D:/Entwicklung/HASI/pr139-work/tmp TMP=D:/Entwicklung/HASI/pr139-work/tmp TMPDIR=D:/Entwicklung/HASI/pr139-work/tmp npm_config_cache=D:/Entwicklung/HASI/pr139-work/npm-cache
uvx black --check custom_components/irrigation_plus/ $(git diff --name-only 2b2c403b -- tests)
uvx ruff check custom_components/irrigation_plus/
```

Erwartet (real, `scratch/dry5-checks.log` bei `a6a9e382`): `71 files would be left unchanged.` / `All checks passed!`

- [ ] **Step 6: Baum gleich `dry6`**

```bash
cd /d/Entwicklung/HASI/HAsmartirrigation
SRC=a6a9e382
git diff "$SRC" --stat
git status --short
```

Soll (nicht gemessen): `git diff` leer; Status `M ` für die drei Produktivdateien, `A ` für die neue Testdatei,
`?? docs/SESSION-STAND.md`.

- [ ] **Step 7: Commit mit derselben Nachricht**

```bash
cd /d/Entwicklung/HASI/HAsmartirrigation
SRC=a6a9e382
git log -1 --format=%B "$SRC" | git commit -q -F -
test "$(git rev-parse HEAD^{tree})" = "$(git rev-parse "$SRC^{tree}")" && echo TREE-SAME
diff <(git log -1 --format=%B HEAD) <(git log -1 --format=%B "$SRC") && echo MSG-SAME
git log -1 --format=%B | grep -c '^#'
git show --stat --format= HEAD | tail -1
git log --oneline -1
git status --short
```

Soll (nicht gemessen): `TREE-SAME`, `MSG-SAME`, `0`, ` 4 files changed, 394 insertions(+)` (Zahl real aus
`git show --stat a6a9e382`), `<neuer SHA> feat(run-watch): add the finish-grace run keys, policy flag and helpers`,
danach nur `?? docs/SESSION-STAND.md`.

**Mutationsproben (Probelauf)**

Gemessen im Revisions-Probelauf `dry2` auf Basis `0b418644`, am abgekoppelten Commit `94cc3785` in einem
Prüf-Worktree (Plan Revision 2, Task 2, Step 10; Skript `mut/r7_probes.py`). Lauf je Probe:
`tests/test_finish_grace_helpers.py -k "…"` mit den Namen aus der Spalte `-k`. `run_watch` = `custom_components/irrigation_plus/run_watch.py`,
`self_closing` = `custom_components/irrigation_plus/self_closing.py`. Task 13 läuft die Proben erneut.

| Probe | Datei: Suchtext --> Ersatz | `-k` | Beobachtet (Probelauf) |
|---|---|---|---|
| zone-clamp | run_watch: `    return max(0, min(const.MAX_LATENCY_MARGIN_SECONDS, value))` --> `    return value` | `clamped_to_its_bounds` | FAIL (2) `assert -3 == 0` |
| zone-round | run_watch: `value = int(round(float(raw)))` --> `value = int(float(raw))` | `clamped_to_its_bounds` | FAIL `assert 7 == 8` |
| zone-garbage | run_watch: `    except (TypeError, ValueError):\n        return const.DEFAULT_LATENCY_MARGIN_SECONDS\n` --> `    except (TypeError, ValueError):\n        return 0\n` | `clamped_to_its_bounds` | FAIL `assert 0 == 4` |
| zone-default | run_watch: `    if raw is None:\n        return const.DEFAULT_LATENCY_MARGIN_SECONDS\n` --> `    if raw is None:\n        return 0\n` | `stored_without_a_margin` | FAIL `assert 0 == 4` |
| run-margin-negative | run_watch: `        return max(0.0, float(raw))` --> `        return float(raw)` | `negative_margin` | FAIL `assert -2.0 == 0.0` |
| run-grace-policy | run_watch: `    return watch_policy_for(run.get(const.RUN_MODE)).settles_on_valve_window` --> `    return True` | `batch_record_carrying or opensprinkler_record_carrying` | FAIL (2) `assert True is False` |
| run-grace-margin-gate | run_watch: `    if run_latency_margin(run) is None:\n        return False\n` --> leer | `before_the_update` | FAIL `assert True is False` |
| run-grace-watch-gate | run_watch: `    if not isinstance(run, dict) or not run.get(const.RUN_WATCH_ENTITY):` --> `    if not isinstance(run, dict):` | `unconfirmed_run_has_none or run_without_grace_waits_nothing` | FAIL (2) `assert True is False` |
| run-grace-settle | run_watch: `return float(policy.finish_settle_seconds) + float(run_latency_margin(run))` --> `return float(run_latency_margin(run))` | `settle_plus_the_frozen_margin` | FAIL `assert 4.0 == 9.0` |
| tolerance-floor | run_watch: `return max(1.0, float(run_latency_margin(run)))` --> `return float(run_latency_margin(run))` | `never_drops_below_one_second` | FAIL `assert 0.0 == 1.0` |
| tolerance-no-grace | run_watch: `    if not run_has_finish_grace(run):\n        return 1.0\n` --> leer | `keeps_the_one_second_slack` | FAIL `assert 4.0 == 1.0` |
| window-off-clamp | run_watch: `return max(0.0, (off - anchor).total_seconds())` --> `return (off - anchor).total_seconds()` | `off_report_before_the_on_report` | FAIL `assert -5.0 == 0.0` |
| window-plan-bound | run_watch: `return max(0.0, min((now - anchor).total_seconds(), planned))` --> `return max(0.0, (now - anchor).total_seconds())` | `bounded_by_the_plan` | FAIL `assert 900.0 == 600.0` |
| window-anchor-valve-on | run_watch: `        run.get(const.RUN_VALVE_ON)\n        or run.get(const.RUN_OBSERVED_START)\n` --> `        run.get(const.RUN_OBSERVED_START)\n` | `off_report_minus_the_on_report or time_since_on` | FAIL (1 von 2) `assert 420.5 == 420.0 ± 4.2e-04` |
| window-anchor-observed | run_watch: `        or run.get(const.RUN_OBSERVED_START)\n` --> leer | `falls_back_to_the_observed_start` | FAIL `assert 170.0 == 120.0` |
| window-no-anchor | run_watch: `    if anchor is None:\n        return planned\n` --> `    if anchor is None:\n        return 0.0\n` | `no_anchor` | FAIL `assert 0.0 == 600.0` |
| policy-service-flag | self_closing: `    settles_on_valve_window=True,\n` --> leer | `service_policy_settles or confirmed_service_run_with_a_margin` | FAIL (2) `assert False is True` |
| policy-default-true | run_watch: `    settles_on_valve_window: bool = False` --> `    settles_on_valve_window: bool = True` | `batch_policy_does_not or opensprinkler_policy_does_not` | FAIL (2) `assert True is False` |
| resume-adds-settle | run_watch `_watch_resume`: `        remaining = max(0.0, planned_seconds(run) - self._sc_run_elapsed(run))` --> dieselbe Zeile + ` + const.SERVICE_WATCH_SETTLE_SECONDS` | `remaining_window_only` | FAIL `assert (1, 545.0) == (1, 540.0)` |

19 von 19 gefangen. **Entfallen** (Probelauf: 22 Proben, 22 gefangen): `zone-mode-gate`, `zone-confirm-gate` und
`zone-grace-settle`. Sie mutierten `zone_finish_grace_seconds` und fielen mit ihm und seinen fünf Tests weg
(Entscheidung (e)). `zone_latency_margin` selbst ist weiter durch `zone-clamp`, `zone-round`, `zone-garbage` und
`zone-default` abgedeckt; T3 ruft ihn beim Dispatch (Proben `margin-record`, `margin-default` dort).

**Dazu dry6** (19.09. abends, am Endstand `70dc0c18`, Lauf über die 7 Service-Suiten; `dry6-logs/probes.md`). Vier Tests
fing bis dahin keine Probe, dazu der Fall `"7"` des parametrisierten Klemm-Tests (`dry6-logs/killmap.md`). Im Treiber
von Task 13 laufen sie auf `tests/test_finish_grace_helpers.py` mit dem `-k` der Tabelle (ohne Mutation auf dry6:
`2 passed`, `3 passed`, `1 passed`, `1 passed`, `5 passed`, jeweils mit dem Rest der 30 abgewählt).

| Probe | `run_watch.py`: Suchtext --> Ersatz | `-k` | Beobachtet (dry6, 7 Suiten) |
|---|---|---|---|
| no-margin-reads-zero | in `run_latency_margin`: `    if raw is None:\n        return None\n    try:\n        return max(0.0, float(raw))\n` --> dieselben Zeilen mit `return 0.0` | `record_without_a_margin_answers_none or before_the_update_has_none` | FAIL 4: `test_a_record_without_a_margin_answers_none` (`assert 0.0 is None`), `test_a_record_from_before_the_update_has_none`, dazu T4 `test_a_record_from_before_the_update_records_nothing` und T5 `test_a_record_from_before_the_update_keeps_the_old_rule` (`4 failed, 230 passed, 2 errors`) |
| frozen-margin-constant | `        return max(0.0, float(raw))\n` --> `        return 4.0\n` | `frozen_margin_is_read_back or negative_margin or never_drops_below_one_second` | FAIL 7, darunter `test_the_frozen_margin_is_read_back_as_seconds` (`assert 4.0 == 6.0`), `negative_margin` (`4.0 == 0.0`), `never_drops_below_one_second` (`4.0 == 1.0`), dazu die zwei „margin of zero“-Tests aus T3/T5, T7s Stopp jenseits der Toleranz und T9s Marge-10-Test |
| tolerance-always-one | `    return max(1.0, float(run_latency_margin(run)))\n` --> `    return 1.0\n` | `completion_tolerance_is_the_margin` | FAIL 3: `test_the_completion_tolerance_is_the_margin` (`assert 1.0 == 4.0`), T5 `close_inside_the_margin`, T7 Stopp in der Toleranz |
| anchor-no-started-fallback | in `valve_window_seconds` die Zeile `        or run.get(const.RUN_STARTED)\n` entfernt (Suchtext mit der Zeile davor und danach) | `falls_back_to_the_dispatch_instant` | FAIL nur `test_the_anchor_falls_back_to_the_dispatch_instant` (`assert 600.0 == 170.0`) |
| string-margin-is-garbage (Zusatz) | in `zone_latency_margin`: vor `value = int(round(float(raw)))` ein `if isinstance(raw, str): raise ValueError(raw)` | `clamped_to_its_bounds` | FAIL nur `test_the_margin_is_whole_seconds_clamped_to_its_bounds[7-7]` (`assert 4 == 7`) |

Damit T2: 24 Proben, 24 gefangen; jedes der 30 Items scheitert an mindestens einer Probe (`[x-4]` an `zone-garbage`,
`test_without_an_off_report_the_window_is_the_time_since_on` an T5s `window-planned-without-off`).

---

### Task 3: Dispatch friert Marge und Ventil-Ein ein, der Backstop trägt die Wartezeit

**dry6:** `c6a4c842` (dry5: `4be8c894`) — `feat(service): wait out the finish grace before a confirmed run's backstop`

**Files** (Zeilen auf `c6a4c842`; der Produktivcode ist der von `4be8c894`):
- TEST: `tests/test_service_watch.py` (Pin `test_the_finish_backstop_is_armed_once` geändert; drei neue Klassen direkt
  danach; seit dry6 dahinter die Modul-Helfer `_finished` und `_the_real_backstop_from_here`, der Import
  `async_capture_events` und die vierte Klasse `TestAMissedCloseStillSettlesViaTheBackstop`)
- PROD: `custom_components/irrigation_plus/self_closing.py` (Importe `run_finish_grace_seconds`, `zone_latency_margin`;
  `_sc_valve_on_instant` `:439`; in `async_run_self_closing`: `dispatched_at` `:524`, `confirmed_at` `:573`,
  Laufdatensatz `:639-649`, Backstop `:675-686`)
- `git show --stat` (evidence.md): `2 files changed, 259 insertions(+), 2 deletions(-)`
- Commit-Nachricht: die von `4be8c894` plus ein Absatz vor dem Trailer: „A valve that never reports its close is still
  finished by that backstop, for its plan, once the grace is out. A test drives the real timer for it.“

**Was und warum**
- **Wurzel 1:** Der Backstop eines bestätigten Service-Laufs wurde genau beim geplanten Fenster scharf
  (`self_closing.py:629` auf `2b2c403b`). Er kam dem Watcher in jedem normalen Lauf zuvor: vor der Aus-Meldung des
  Tuya-Ventils (Beet 13.09.: 2,03 s davor) oder mitten in die 5-s-Entprellung (Kirschlorbeer 13.09.: 1,13 s nach „aus“),
  wo `_sc_finish_run` sie über `_os_cancel_watch` abbricht. Der Lauf wurde nie auf dem abgerechnet, was das Ventil tat.
- **Neu beim Dispatch**, nur im Block, der `RUN_WATCH_ENTITY` setzt (also nur für bestätigte Läufe):
  `record[RUN_LATENCY_MARGIN] = zone_latency_margin(zone)`, eingefroren, damit eine Änderung mitten im Lauf einen schon
  gestellten Backstop nicht verschiebt. Seine Anwesenheit ist das Tor aus Task 2.
- **Wurzel 3 / E1:** `RUN_STARTED` wird erst nach der Rückkehr von `_confirm_valve_running` gestempelt (1-s-Poll), also
  bis zu einem Poll nach dem Wasser. `record[RUN_VALVE_ON] = _sc_valve_on_instant(confirm_target, dispatched_at, confirmed_at)`:
  `last_changed` der Confirm-Entität, geklemmt auf [`dispatched_at`, `confirmed_at`], ohne State `confirmed_at`.
  `dispatched_at` ist ein `utcnow()` direkt vor `_sc_dispatch_open`, `confirmed_at` ein `utcnow()` direkt nach der
  Confirm-Rückkehr. Die Klemme hält ein schon offenes Ventil (Confirm akzeptiert es beim ersten Lesen) davon ab, den
  Anker Stunden zurückzuziehen. `_confirm_valve_running` behält seine boolesche Rückgabe (drei weitere Aufrufer
  vergleichen `is False`). `RUN_STARTED` bleibt für alle anderen Leser, wie es ist.
- **Backstop** `planned_seconds + run_finish_grace_seconds(record)`: bei Default-Marge 600 --> 609, bei Marge 0 --> 605.
  Write-only und nicht prüfbarer Confirm tragen weder Marge noch `RUN_WATCH_ENTITY` und bleiben genau bei `planned`.
  Der Zuschlag steht an der Service-Aufrufstelle; `_sc_schedule_cleanup` bleibt unverändert, weil Batch und
  OpenSprinkler ihn teilen.
- Die Observed-Sperre `_note_si_valve(zone, planned)` bleibt unverändert: Task 3b ist gestrichen (siehe unten).

**Tests** (`tests/test_service_watch.py`)
- `TestAFullRunIsStillAFullRun::test_the_finish_backstop_is_armed_once` (geändert, der einzige geänderte Pin-Wert
  der Reihe) — einmal gestellt, `(2, 600)` --> `(2, 609)`.
- `TestAConfirmedRunFreezesItsMarginAtDispatch::test_the_default_margin_is_frozen_into_the_record` — `RUN_LATENCY_MARGIN == 4`.
- `TestAConfirmedRunFreezesItsMarginAtDispatch::test_the_zones_own_margin_is_frozen_into_the_record` — Zonenwert 7 --> 7.
- `TestAConfirmedRunFreezesItsMarginAtDispatch::test_a_write_only_run_carries_neither_margin_nor_valve_on` — ohne
  `confirm_entity` keiner der beiden Schlüssel.
- `TestAConfirmedRunFreezesItsMarginAtDispatch::test_an_unverifiable_run_carries_neither_margin_nor_valve_on` — Ventil
  `unavailable` (Confirm `None`): keiner der beiden Schlüssel.
- `TestTheValveOnReportIsClampedToTheDispatch::test_a_valve_already_open_is_anchored_at_the_dispatch` — seit einer
  Stunde „on“ --> `RUN_VALVE_ON` = Dispatch.
- `TestTheValveOnReportIsClampedToTheDispatch::test_a_valve_reporting_on_after_the_dispatch_is_anchored_at_its_report`
  — Meldung +0,4 s, Poll-Rückkehr +1 s --> `RUN_VALVE_ON` = +0,4, `RUN_STARTED` = +1.
- `TestTheValveOnReportIsClampedToTheDispatch::test_a_report_stamped_after_the_confirm_returned_is_clamped_to_it` —
  Meldung auf +5 gestempelt, Rückkehr +1 --> +1.
- `TestTheBackstopWaitsOnlyForAConfirmedValve::test_a_margin_of_zero_still_waits_out_the_debounce` — Marge 0 --> `(2, 605)`.
- `TestTheBackstopWaitsOnlyForAConfirmedValve::test_a_write_only_run_is_backstopped_at_exactly_its_window` — `(2, 600)`.
- `TestTheBackstopWaitsOnlyForAConfirmedValve::test_an_unverifiable_run_is_backstopped_at_exactly_its_window` — `(2, 600)`.
- `TestAMissedCloseStillSettlesViaTheBackstop::test_a_valve_that_never_reports_off_is_finished_when_the_grace_is_out`
  (neu in dry6; der von JustChr 09-14 verlangte Test „a missed close still settles via the backstop“) — Marge 4, geplant
  600, das Ventil meldet „an“ und nie „aus“, **echter** Backstop-Timer über `_the_real_backstop_from_here(c)` vor dem
  Dispatch, alles in einem `freeze_time`-Block. Bei +608 (eine Sekunde vor 600 + 5 + 4): Datensatz noch da, kein
  `_record_run`, kein `irrigation_finished`, keine Master-Freigabe. Bei +610: `completed`,
  `actual_s == planned_s == 600`, `irrigation_finished` genau einmal, Datensatz weg, Master einmal freigegeben, kein
  Backstop-Timer mehr (`_sc_cleanup_timers()` leer).
- Neue Modul-Helfer (seit dry6 hier statt in T7/T8): `_finished(hass)` fängt `irrigation_plus_irrigation_finished`
  (`async_capture_events`); `_the_real_backstop_from_here(c)` löscht `_coord`s Doubles `_sc_schedule_cleanup` und
  `_sc_cancel_cleanup` und hüllt den echten `_sc_schedule_cleanup` in `Mock(wraps=...)`, damit der Arm-Wert prüfbar
  bleibt und der Timer wirklich feuert. Weitere Nutzer: `_finished` in T7; `_the_real_backstop_from_here` im T6-Pin
  von T5, im SP-3-Test von T8 und (importiert) in den Dispatch-Tests von T9.
- Unverändert grün bleiben die write-only-Pins in `tests/test_self_closing.py` (`(2, 600.0)`, `(2, 500.0)`,
  `(2, 300.0)`, `(2, 263.0)`; Teil der 7 Suiten).

- [ ] **Step 1: Tests aus dem `dry6`-Commit auschecken**

```bash
cd /d/Entwicklung/HASI/HAsmartirrigation
SRC=c6a4c842; TESTS="tests/test_service_watch.py"
git status --short
[ "$(git rev-parse HEAD^{tree})" = "$(git rev-parse "$SRC~1^{tree}")" ] && echo PARENT-TREE-SAME
git checkout "$SRC" -- $TESTS
git status --short
```

Soll (nicht gemessen): vorher nur `?? docs/SESSION-STAND.md`, `PARENT-TREE-SAME`, danach zusätzlich
`M  tests/test_service_watch.py`.

- [ ] **Step 2: RED prüfen**

```bash
cd /d/Entwicklung/HASI/HAsmartirrigation
mkdir -p D:/Entwicklung/HASI/pr139-work/tmp D:/Entwicklung/HASI/pr139-work/npm-cache && export TEMP=D:/Entwicklung/HASI/pr139-work/tmp TMP=D:/Entwicklung/HASI/pr139-work/tmp TMPDIR=D:/Entwicklung/HASI/pr139-work/tmp npm_config_cache=D:/Entwicklung/HASI/pr139-work/npm-cache
TESTS="tests/test_service_watch.py"
L=D:/Entwicklung/HASI/pr139-work/replay/T03-red.txt
D:/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest $TESTS -p _local_socket_unblock -q --tb=line -rfE -p no:cacheprovider > $L 2>&1
grep -E "^collected |^(FAILED|ERROR) |^E  |\.py:[0-9]+: " $L; tail -n 1 $L
```

Erwartet (real, `rev3/evidence.md` T3 RED, gemessen auf dry6; Rohdaten `dry6-logs/evidence-raw/T3_RED.txt`):

```
collected 28 items
FAILED tests/test_service_watch.py::TestAFullRunIsStillAFullRun::test_the_finish_backstop_is_armed_once
FAILED tests/test_service_watch.py::TestAConfirmedRunFreezesItsMarginAtDispatch::test_the_default_margin_is_frozen_into_the_record
FAILED tests/test_service_watch.py::TestAConfirmedRunFreezesItsMarginAtDispatch::test_the_zones_own_margin_is_frozen_into_the_record
FAILED tests/test_service_watch.py::TestTheValveOnReportIsClampedToTheDispatch::test_a_valve_already_open_is_anchored_at_the_dispatch
FAILED tests/test_service_watch.py::TestTheValveOnReportIsClampedToTheDispatch::test_a_valve_reporting_on_after_the_dispatch_is_anchored_at_its_report
FAILED tests/test_service_watch.py::TestTheValveOnReportIsClampedToTheDispatch::test_a_report_stamped_after_the_confirm_returned_is_clamped_to_it
FAILED tests/test_service_watch.py::TestTheBackstopWaitsOnlyForAConfirmedValve::test_a_margin_of_zero_still_waits_out_the_debounce
FAILED tests/test_service_watch.py::TestAMissedCloseStillSettlesViaTheBackstop::test_a_valve_that_never_reports_off_is_finished_when_the_grace_is_out
ERROR tests/test_service_watch.py::TestOneOffSampleIsNotEvidenceTheWaterStopped::test_the_run_is_not_settled_before_the_window_is_out
==================== 8 failed, 20 passed, 1 error in 2.39s ====================
```

mit

```
D:\Entwicklung\HASI\pr139-work\dry2\tests\test_service_watch.py:223: assert (2, 600.0) == (2, 609)
D:\Entwicklung\HASI\pr139-work\dry2\tests\test_service_watch.py:239: KeyError: 'latency_margin'
D:\Entwicklung\HASI\pr139-work\dry2\tests\test_service_watch.py:246: KeyError: 'latency_margin'
D:\Entwicklung\HASI\pr139-work\dry2\tests\test_service_watch.py:292: KeyError: 'valve_on'
D:\Entwicklung\HASI\pr139-work\dry2\tests\test_service_watch.py:314: KeyError: 'valve_on'
D:\Entwicklung\HASI\pr139-work\dry2\tests\test_service_watch.py:335: KeyError: 'valve_on'
D:\Entwicklung\HASI\pr139-work\dry2\tests\test_service_watch.py:343: assert (2, 600.0) == (2, 605)
D:\Entwicklung\HASI\pr139-work\dry2\tests\test_service_watch.py:405: assert None is not None
```

Es fallen 7 der 11 neuen Tests und der geänderte Pin. Der neue Echt-Timer-Test fällt an seiner ersten Prüfung: am
Elternstand feuert der echte Backstop schon bei +600, bei +608 ist der Datensatz weg (`:405`). Die vier
write-only/nicht-prüfbar-Tests sind schon am Parent grün; sie pinnen unverändertes Verhalten. Der `ERROR` ist der
vorbestehende Lingering timer.

- [ ] **Step 3: Produktivdatei aus dem `dry6`-Commit auschecken**

```bash
cd /d/Entwicklung/HASI/HAsmartirrigation
SRC=c6a4c842; PROD="custom_components/irrigation_plus/self_closing.py"
git checkout "$SRC" -- $PROD
```

- [ ] **Step 4: GREEN, 7 Suiten + i18n**

```bash
cd /d/Entwicklung/HASI/HAsmartirrigation
mkdir -p D:/Entwicklung/HASI/pr139-work/tmp D:/Entwicklung/HASI/pr139-work/npm-cache && export TEMP=D:/Entwicklung/HASI/pr139-work/tmp TMP=D:/Entwicklung/HASI/pr139-work/tmp TMPDIR=D:/Entwicklung/HASI/pr139-work/tmp npm_config_cache=D:/Entwicklung/HASI/pr139-work/npm-cache
TESTS="tests/test_service_watch.py"
SEVEN="tests/test_service_watch.py tests/test_finish_grace_helpers.py tests/test_run_in_flight.py tests/test_confirm_reserve.py tests/test_self_closing.py tests/test_run_watch.py tests/test_observed_watering.py tests/test_i18n_completeness.py"
D:/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest $TESTS -p _local_socket_unblock -q --tb=line -rfE -p no:cacheprovider > D:/Entwicklung/HASI/pr139-work/replay/T03-green.txt 2>&1; tail -n 1 D:/Entwicklung/HASI/pr139-work/replay/T03-green.txt
D:/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest $SEVEN -p _local_socket_unblock -q --tb=line -rfE -p no:cacheprovider > D:/Entwicklung/HASI/pr139-work/replay/T03-suites.txt 2>&1
grep -E "^(FAILED|ERROR) " D:/Entwicklung/HASI/pr139-work/replay/T03-suites.txt | sed 's/ - .*//'
tail -1 D:/Entwicklung/HASI/pr139-work/replay/T03-suites.txt
```

Erwartet (real): Taskdatei `========================= 28 passed, 1 error in 2.36s =========================`
(`rev3/evidence.md` T3 GREEN); Suiten `======================== 251 passed, 1 error in 16.33s ========================`
(`dry6-logs/percommit.md`, `c6a4c842`); beide `ERROR` = der vorbestehende Lingering timer, keine `FAILED`-Zeile. Der
neue Echt-Timer-Test endet mit gefeuertem Backstop und fügt keinen Error hinzu.

- [ ] **Step 5: Lint**

```bash
cd /d/Entwicklung/HASI/HAsmartirrigation
mkdir -p D:/Entwicklung/HASI/pr139-work/tmp D:/Entwicklung/HASI/pr139-work/npm-cache && export TEMP=D:/Entwicklung/HASI/pr139-work/tmp TMP=D:/Entwicklung/HASI/pr139-work/tmp TMPDIR=D:/Entwicklung/HASI/pr139-work/tmp npm_config_cache=D:/Entwicklung/HASI/pr139-work/npm-cache
uvx black --check custom_components/irrigation_plus/ $(git diff --name-only 2b2c403b -- tests)
uvx ruff check custom_components/irrigation_plus/
```

Erwartet (real, `scratch/dry5-checks.log` bei `4be8c894`; dieselbe Dateimenge auf dry6, ruff dort sauber laut
`dry6-logs/percommit.md`): `72 files would be left unchanged.` / `All checks passed!`

- [ ] **Step 6: Baum gleich `dry6`**

```bash
cd /d/Entwicklung/HASI/HAsmartirrigation
SRC=c6a4c842
git diff "$SRC" --stat
git status --short
```

Soll (nicht gemessen): `git diff` leer; Status `M ` für die zwei Dateien, `?? docs/SESSION-STAND.md`.

- [ ] **Step 7: Commit mit derselben Nachricht**

```bash
cd /d/Entwicklung/HASI/HAsmartirrigation
SRC=c6a4c842
git log -1 --format=%B "$SRC" | git commit -q -F -
test "$(git rev-parse HEAD^{tree})" = "$(git rev-parse "$SRC^{tree}")" && echo TREE-SAME
diff <(git log -1 --format=%B HEAD) <(git log -1 --format=%B "$SRC") && echo MSG-SAME
git log -1 --format=%B | grep -c '^#'
git show --stat --format= HEAD | tail -1
git log --oneline -1
git status --short
```

Soll (nicht gemessen): `TREE-SAME`, `MSG-SAME`, `0`, ` 2 files changed, 259 insertions(+), 2 deletions(-)` (Zahl real
aus `git show --stat c6a4c842`), `<neuer SHA> feat(service): wait out the finish grace before a confirmed run's
backstop`, danach nur `?? docs/SESSION-STAND.md`.

**Mutationsproben (Probelauf)**

Gemessen im Revisionslauf 2026-09-15 auf Basis `0b418644` am Commit von Task 3; die vier Proben mit mehrzeiligem
Suchtext liefen im Feinschliff am Commit `dbbb42fd` erneut, mit denselben Ergebnissen (Plan Revision 2, Task 3,
Step 12). Datei `custom_components/irrigation_plus/self_closing.py`, Lauf je Probe: das `-k` aus der Tabelle auf
`tests/test_service_watch.py`. Die Zeitstempel in der Spalte „Beobachtet“ sind die des Probelaufs. Task 13 läuft die
Proben erneut. Die Spalte `-k` nennt die Auswahl von Task 13; `or MissedClose` kam mit dry6 dazu, die Zählungen in
„Beobachtet“ stammen aus der Auswahl ohne diesen Teil.

| Probe | Mutation in `self_closing.py` (Suchtext --> Ersatz) | `-k` | Beobachtet (Probelauf) |
|---|---|---|---|
| margin-record | `                record[const.RUN_LATENCY_MARGIN] = zone_latency_margin(zone)\n` --> leer | `armed_once or default_margin_is_frozen or zones_own_margin or margin_of_zero` | FAIL (4) `assert (2, 600.0) == (2, 609)`, `KeyError: 'latency_margin'` (2x), `assert (2, 600.0) == (2, 605)` |
| margin-default | `record[const.RUN_LATENCY_MARGIN] = zone_latency_margin(zone)` --> `record[const.RUN_LATENCY_MARGIN] = const.DEFAULT_LATENCY_MARGIN_SECONDS` | `zones_own_margin or margin_of_zero` | FAIL (2) `assert 4 == 7`, `assert (2, 609.0) == (2, 605)` |
| valve-on-record | `                record[const.RUN_VALVE_ON] = self._sc_valve_on_instant(\n                    confirm_target, dispatched_at, confirmed_at\n                )\n` --> leer | `ClampedToTheDispatch` | FAIL (3) `KeyError: 'valve_on'` (`3 failed, 24 deselected`) |
| clamp-lower | `min(max(reported, lower), upper)` --> `min(reported, upper)` | `ClampedToTheDispatch` | FAIL (1: `already_open`) `'…T17:24:06+00:00' == '…T18:24:06+00:00'` |
| clamp-upper | `min(max(reported, lower), upper)` --> `max(reported, lower)` | `ClampedToTheDispatch` | FAIL (1: `stamped_after_the_confirm`) `'…18:24:20+00:00' == '…18:24:16+00:00'` |
| report-ignored | `reported = state.last_changed if state else upper` --> `reported = upper` | `ClampedToTheDispatch` | FAIL (1: `reporting_on_after`) `'…18:24:25+00:00' == '…400000+00:00'` |
| lower-is-confirm-return | `confirm_target, dispatched_at, confirmed_at` --> `confirm_target, confirmed_at, confirmed_at` | `ClampedToTheDispatch` | FAIL (1: `reporting_on_after`) `'…18:24:33+00:00' == '…400000+00:00'` |
| upper-is-dispatch | `confirm_target, dispatched_at, confirmed_at` --> `confirm_target, dispatched_at, dispatched_at` | `ClampedToTheDispatch` | FAIL (2: `reporting_on_after`, `stamped_after_the_confirm`) `'…18:24:41+00:00' == '…41.400000+00:00'` |
| backstop-no-grace | `planned_seconds + run_finish_grace_seconds(record)` --> `planned_seconds` | `armed_once or WaitsOnlyForAConfirmedValve or MissedClose` | FAIL (2) `assert (2, 600.0) == (2, 609)`, `assert (2, 600.0) == (2, 605)`; auf dry6 (als `T3-backstop-without-grace`, dieselbe Mutation mit mehrzeiligem Suchtext, am T3-Stopp, an `bc41374b` und am Endstand `70dc0c18`) zusätzlich der Echt-Timer-Test (`3 failed, 182 passed, 1 error`, `3 failed, 230 passed, 1 error` bzw. `3 failed, 231 passed, 1 error`) |
| backstop-grace-from-zone (**neu formuliert**) | `planned_seconds + run_finish_grace_seconds(record)` --> `planned_seconds + (const.SERVICE_WATCH_SETTLE_SECONDS + zone_latency_margin(zone) if zone.get(const.ZONE_CONFIRM_ENTITY) else 0)` | `armed_once or WaitsOnlyForAConfirmedValve or MissedClose` | Im Probelauf lautete der Ersatz `planned_seconds + zone_finish_grace_seconds(zone)` (plus Import) und fiel mit FAIL (1: `unverifiable_run_is_backstopped`) `assert (2, 609.0) == (2, 600)` (`1 failed, 3 passed, 23 deselected`). Den Helfer gibt es nicht mehr ((e)); die Neufassung bildet sein Zonen-Tor (Confirm gesetzt) direkt nach. Sie ist NICHT wortgleich mit `backstop-grace-always`: mit dem Tor bleibt write-only bei `(2, 600)`, nur der nicht prüfbare Confirm bekommt die Wartezeit. Ergebnis der Neufassung: **nicht gemessen** (Ersetzung trifft auf dry6 genau einmal und kompiliert). Soll: derselbe eine Fehlschlag |
| backstop-grace-always | `planned_seconds + run_finish_grace_seconds(record)` --> `planned_seconds + const.SERVICE_WATCH_SETTLE_SECONDS + zone_latency_margin(zone)` | `armed_once or WaitsOnlyForAConfirmedValve or MissedClose` | FAIL (2: write-only, unverifiable) `assert (2, 609.0) == (2, 600)` |
| margin-for-every-record | `            await self._sc_add_run(record)\n` --> `            record[const.RUN_LATENCY_MARGIN] = zone_latency_margin(zone)\n            await self._sc_add_run(record)\n` | `FreezesItsMargin` | FAIL (2) `assert 'latency_margin' not in {…}` (`2 failed, 2 passed, 23 deselected`) |
| valve-on-for-unverifiable | `            await self._sc_add_run(record)\n` --> `            if confirm_target and not is_opensprinkler:\n                record[const.RUN_VALVE_ON] = self._sc_valve_on_instant(\n                    confirm_target, dispatched_at, confirmed_at\n                )\n            await self._sc_add_run(record)\n` | `FreezesItsMargin` | FAIL (1: `unverifiable_run_carries`) `assert 'valve_on' not in {…}` (`1 failed, 3 passed, 23 deselected`) |

**Dazu dry6: der verpasste Schluss auf dem echten Backstop-Timer** (`dry6-logs/T3.md`, `dry6-logs/T3-end-probes.txt`).
Gemessen an drei Ständen, Lauf über die 7 Service-Suiten, SHA-256 vor und nach jeder Probe gleich:

- am T3-Stopp (`self_closing.py` von T3; Sicherung `mut/dry6-T3-*.bak`);
- am Branch-HEAD nach Schritt T3 (`bc41374b`, nach T5/T7/T8/T9; Produktivcode = Endstand, ein Test weniger, denn der
  T5-Pin `TestACloseReportedPastTheMarginIsKnownAndDeliberatelyUnchanged` kam erst danach; Sicherung
  `mut/dry6-T3H-*.bak`);
- am Endstand `70dc0c18` (19.09. abends nachgefahren, dieselben Suchtexte; Sicherung `mut/dry6-T3E-*.bak`). Der T5-Pin
  läuft mit dem echten Backstop und fängt deshalb drei der vier Proben mit.

Im Treiber von Task 13 laufen sie auf `tests/test_service_watch.py tests/test_run_in_flight.py` mit `-k "MissedClose or SecondDispatch"` (die erste auch
mit `armed_once or WaitsOnlyForAConfirmedValve`); ohne Mutation auf dry6: `3 passed, 93 deselected` bzw.
`7 passed, 89 deselected`.

| Probe | Mutation in `self_closing.py` | Beobachtet am T3-Stopp | Beobachtet an `bc41374b` | Beobachtet am Endstand `70dc0c18` |
|---|---|---|---|---|
| backstop-callback-dropped | im Backstop-Rückruf `_done` `await self._sc_finish_run(zone_id)` --> `return None` | FAIL nur der Echt-Timer-Test (`1 failed, 184 passed, 1 error`) | FAIL der Echt-Timer-Test und die zwei T9-Dispatch-Tests (`3 failed, 230 passed, 1 error`) | FAIL dieselben drei und der T5-Pin (`4 failed, 230 passed, 2 errors`) |
| backstop-finishes-on-elapsed | der Backstop bucht die Uhr statt des Plans: am T3-Stopp in `_sc_finish_run` `actual_s=planned_s,` --> `actual_s=self._sc_run_elapsed(run),`; ab `bc41374b` (T5 gab `_sc_finish_run` den Parameter `actual_s`) in `_done` `_sc_finish_run(zone_id, actual_s=self._sc_run_elapsed(run) if run else None)` | FAIL der Echt-Timer-Test (`610.0 == 600.0`) und `test_a_valve_off_at_the_planned_end_completes` (`2 failed, 183 passed, 1 error`) | FAIL **nur** der Echt-Timer-Test (`1 failed, 232 passed, 1 error`) | FAIL der Echt-Timer-Test und der T5-Pin (beide `610.0 == 600.0`; `2 failed, 232 passed, 2 errors`) |
| backstop-never-armed | der Aufruf `self._sc_schedule_cleanup(zone_id, planned_seconds + run_finish_grace_seconds(record))` --> `pass` | FAIL 8: `armed_once`, die drei `WaitsOnlyForAConfirmedValve`-Tests, der Echt-Timer-Test, drei Pins in `tests/test_self_closing.py` | FAIL 10: dieselben 8 und die zwei T9-Dispatch-Tests | FAIL 11: dieselben 10 und der T5-Pin (`11 failed, 223 passed, 2 errors`) |

Das zweite `error` am Endstand ist ein Teardown-Error des gescheiterten T5-Pins (für `backstop-finishes-on-elapsed`
nachgelesen: Lingering timer der Entprellung, `dry6-logs/T3-end-probes.txt`). Die vierte Probe der Sitzung,
`T3-backstop-without-grace`, ist `backstop-no-grace` aus der Tabelle oben. Als einziger Test fängt der Echt-Timer-Test
den Rückruf des Backstops (`backstop-callback-dropped`) am T3-Stopp und die gebuchte Uhr
(`backstop-finishes-on-elapsed`) an `bc41374b`. Am Endstand `70dc0c18` fängt der T5-Pin beide mit. Im Treiber von
Task 13 (`-k K3D`) ist der T5-Pin nicht ausgewählt.

Zusammen: Probelauf Rev. 2 13 von 13 gefangen; dry6 3 neue Proben, alle gefangen; jeder neue Test und der geänderte Pin
scheitert an mindestens einer Probe. Auf dem echten Branch (Task 13): 16 Proben, davon 15 mit gemessenem Ergebnis und die
neu formulierte `backstop-grace-from-zone`. Die Proben der Observed-Sperre (Task 3b) entfallen.

---

### Task 3b — gestrichen

Geplant war `_note_si_valve(zone, planned + Wartezeit)` beim Dispatch (Observed-Sperre über die Wartezeit). Gestrichen
nach JustChr 09-19 ([issuecomment-5740329987](https://github.com/JustChr/HAsmartirrigation/issues/139#issuecomment-5740329987),
auf unseren Kommentar 5740280769): `observed_watering.py:138` prüft `zone_run_in_flight` vor dem Sperr-Timer, und mit
Task 9 unterdrückt In-flight eine Ein-Flanke in der Wartezeit schon. Die Sperre hätte nur 9 s NACH dem Abschluss
angehängt (bestehende Lücke langsamer Ventile, nicht von der Wartezeit geöffnet) und darin ein echtes externes Öffnen
verschluckt; sie wartet auf nach Stable. Folge (e): `zone_finish_grace_seconds` entsteht nicht (Task 2). Der PR-Text
nennt als „known and deliberately unchanged“ die Sub-Sekunden-Lücke zwischen dem Ende von In-flight und dem Backstop,
der den Datensatz entfernt (von JustChr erbeten), und die unveränderte Sperre nach dem Abschluss. Kein Commit.

---

### Task 4: Der Watcher zeichnet die Aus-Meldung des Ventils auf und löscht sie bei einem Blip

**dry6:** `dd43f09c` (dry5: `9380fb74`, Inhalt gleich, nur neuer Elternstand) — `feat(run-watch): record a confirmed valve's own off report`

**Files** (Zeilen auf `dd43f09c`):
- TEST: `tests/test_service_watch.py` (Modul-Helfer `_report`, neue Klasse `TestTheWatcherRecordsTheValvesOwnOffReport`
  nach `TestOneOffSampleIsNotEvidenceTheWaterStopped`)
- PROD: `custom_components/irrigation_plus/run_watch.py` (`_watch_state_changed` übergibt
  `previous_state=event.data.get("old_state")` `:661-665`; `_watch_evaluate(..., *, previous_state=None)` `:668`;
  Laufend-Zweig löscht `RUN_VALVE_OFF` `:704-711`; Aus-Zweig zeichnet es auf `:720-755`)
- `git show --stat` (evidence.md): `2 files changed, 233 insertions(+), 3 deletions(-)`

**Was und warum**
- **Wurzel 2, Endseite:** `actual_s` soll am Aus-Übergang gemessen werden, nicht wenn die Entprellung entscheidet.
  Dieser Task speichert dafür das Ende des Ventil-Fensters: `RUN_VALVE_OFF` = `last_changed` des Zustands der ersten
  Aus-Meldung seit dem letzten „an“. Abgelesen, nicht von der Uhr gestempelt: die Auswertung läuft als Task nach der
  Meldung, die Entprellung entscheidet Sekunden später. HA behält `last_changed`, solange der Zustandstext gleich
  bleibt, ein reines Attribut-Update verschiebt den Wert also nicht. Ein gespeicherter Wert wird nie überschrieben.
- **E6:** Aufgezeichnet wird nur aus einem Ereignis, dessen Vorzustand laufend war (`RUNNING_STATES`). Die Subscription
  reicht dazu `old_state` als Schlüsselwort `previous_state` an `_watch_evaluate` weiter. Die erste Auswertung in
  `_watch_start` und die Neu-Auswertungen eines Modus übergeben nichts. Deshalb nie aus der ersten Auswertung nach einem
  Neustart und nie aus `unavailable`/`unknown`/fehlend --> `off`: Z2M-Ventile kommen nach einem Neustart zuerst als
  `unavailable` zurück, und `last_changed` des folgenden `off` ist ihre Wiederkehr, nicht der Schluss (auf HA-Prod
  belegt, `rev3/spec.md` Design 1).
- **Blip:** Sieht der Watcher das Ventil wieder laufend, wird `RUN_VALVE_OFF` gelöscht (nur mit dem Policy-Flag).
  Sonst überdauerte ein alter Wert die nächste Aus-Meldung und schnitte das Fenster um den Abstand des Blips ab.
- Nur für Läufe mit Wartezeit (`run_has_finish_grace`). Write-only, Batch, OpenSprinkler und Datensätze von vor dem
  Update zeichnen nichts auf.
- Bewusst in Kauf genommen: `on --> unavailable --> off` mitten im Lauf speichert nichts. Ein solcher Lauf wird wie
  jeder Schluss ohne Meldung abgerechnet, ab Task 5 nach der Basisregel (b). 10 Tage Recorder zeigen keine solche
  Episode während eines Laufs.
- Die Abrechnung selbst ändert sich in diesem Task nicht. Jeder Test prüft vor dem Ablauf der Entprellung und ruft
  danach `_settle`, damit kein Timer liegen bleibt.

**Tests** (`tests/test_service_watch.py`, `TestTheWatcherRecordsTheValvesOwnOffReport`)
- `test_an_off_event_records_the_states_last_changed` — `RUN_VALVE_OFF` = `last_changed` der Meldung, noch nicht abgerechnet.
- `test_an_attribute_only_update_does_not_move_the_off_report` — `off` mit neuem Attribut 3 s später: Wert bleibt.
- `test_an_off_after_an_unavailable_spell_keeps_the_first_off_report` — `off`, `unavailable`, `off`: die erste Meldung bleibt.
- `test_an_off_after_an_unavailable_mid_run_records_nothing` — `on --> unavailable --> off`: nichts gespeichert,
  Entprellung läuft.
- `test_an_on_inside_the_debounce_clears_the_off_report` — `on` 1 s nach `off`: gelöscht, Lauf besteht weiter.
- `test_a_re_adopted_run_does_not_record_the_initial_off` — Neuaufnahme nach Neustart findet „off“: nichts gespeichert.
- `test_a_re_adopted_run_does_not_record_an_off_after_unavailable` — Neuaufnahme bei `unavailable`, dann `off`:
  nichts gespeichert.
- `test_a_record_from_before_the_update_records_nothing` — Datensatz ohne Marge: nichts gespeichert.
- Neuer Modul-Helfer `_report(hass, state, when, attributes=None)`: setzt das Ventil mit `last_changed = when`; ab
  Task 5 weiterverwendet.

- [ ] **Step 1: Tests aus dem `dry6`-Commit auschecken**

```bash
cd /d/Entwicklung/HASI/HAsmartirrigation
SRC=dd43f09c; TESTS="tests/test_service_watch.py"
git status --short
[ "$(git rev-parse HEAD^{tree})" = "$(git rev-parse "$SRC~1^{tree}")" ] && echo PARENT-TREE-SAME
git checkout "$SRC" -- $TESTS
git status --short
```

Soll (nicht gemessen): vorher nur `?? docs/SESSION-STAND.md`, `PARENT-TREE-SAME`, danach zusätzlich
`M  tests/test_service_watch.py`.

- [ ] **Step 2: RED prüfen**

```bash
cd /d/Entwicklung/HASI/HAsmartirrigation
mkdir -p D:/Entwicklung/HASI/pr139-work/tmp D:/Entwicklung/HASI/pr139-work/npm-cache && export TEMP=D:/Entwicklung/HASI/pr139-work/tmp TMP=D:/Entwicklung/HASI/pr139-work/tmp TMPDIR=D:/Entwicklung/HASI/pr139-work/tmp npm_config_cache=D:/Entwicklung/HASI/pr139-work/npm-cache
TESTS="tests/test_service_watch.py"
L=D:/Entwicklung/HASI/pr139-work/replay/T04-red.txt
D:/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest $TESTS -p _local_socket_unblock -q --tb=line -rfE -p no:cacheprovider > $L 2>&1
grep -E "^collected |^(FAILED|ERROR) |^E  |\.py:[0-9]+: " $L; tail -n 1 $L
```

Erwartet (real, `rev3/evidence.md` T4 RED, gemessen auf dry6):

```
collected 36 items
FAILED tests/test_service_watch.py::TestTheWatcherRecordsTheValvesOwnOffReport::test_an_off_event_records_the_states_last_changed
FAILED tests/test_service_watch.py::TestTheWatcherRecordsTheValvesOwnOffReport::test_an_attribute_only_update_does_not_move_the_off_report
FAILED tests/test_service_watch.py::TestTheWatcherRecordsTheValvesOwnOffReport::test_an_off_after_an_unavailable_spell_keeps_the_first_off_report
FAILED tests/test_service_watch.py::TestTheWatcherRecordsTheValvesOwnOffReport::test_an_on_inside_the_debounce_clears_the_off_report
ERROR tests/test_service_watch.py::TestOneOffSampleIsNotEvidenceTheWaterStopped::test_the_run_is_not_settled_before_the_window_is_out
ERROR tests/test_service_watch.py::TestTheWatcherRecordsTheValvesOwnOffReport::test_an_off_event_records_the_states_last_changed
ERROR tests/test_service_watch.py::TestTheWatcherRecordsTheValvesOwnOffReport::test_an_attribute_only_update_does_not_move_the_off_report
ERROR tests/test_service_watch.py::TestTheWatcherRecordsTheValvesOwnOffReport::test_an_off_after_an_unavailable_spell_keeps_the_first_off_report
ERROR tests/test_service_watch.py::TestTheWatcherRecordsTheValvesOwnOffReport::test_an_on_inside_the_debounce_clears_the_off_report
=================== 4 failed, 32 passed, 5 errors in 3.01s ====================
```

mit

```
D:\Entwicklung\HASI\pr139-work\dry2\tests\test_service_watch.py:528: KeyError: 'valve_off'
D:\Entwicklung\HASI\pr139-work\dry2\tests\test_service_watch.py:545: KeyError: 'valve_off'
D:\Entwicklung\HASI\pr139-work\dry2\tests\test_service_watch.py:566: KeyError: 'valve_off'
D:\Entwicklung\HASI\pr139-work\dry2\tests\test_service_watch.py:595: KeyError: 'valve_off'
```

(Gleiches Bild wie auf dry5; ein Item mehr durch den neuen T3-Test, die Zeilen um 68 verschoben.)

Vier der acht neuen Tests fallen am fehlenden Schlüssel. Jeder davon hinterlässt zusätzlich einen Lingering timer, weil
er vor seinem `_settle` abbricht; zusammen mit dem vorbestehenden sind das 5 Errors. Die vier Tests, die „nichts
gespeichert“ prüfen (`unavailable_mid_run`, die zwei `re_adopted_run`, `before_the_update`), sind schon am Parent grün:
dort zeichnet noch gar nichts auf.

- [ ] **Step 3: Produktivdatei aus dem `dry6`-Commit auschecken**

```bash
cd /d/Entwicklung/HASI/HAsmartirrigation
SRC=dd43f09c; PROD="custom_components/irrigation_plus/run_watch.py"
git checkout "$SRC" -- $PROD
```

- [ ] **Step 4: GREEN, 7 Suiten + i18n**

```bash
cd /d/Entwicklung/HASI/HAsmartirrigation
mkdir -p D:/Entwicklung/HASI/pr139-work/tmp D:/Entwicklung/HASI/pr139-work/npm-cache && export TEMP=D:/Entwicklung/HASI/pr139-work/tmp TMP=D:/Entwicklung/HASI/pr139-work/tmp TMPDIR=D:/Entwicklung/HASI/pr139-work/tmp npm_config_cache=D:/Entwicklung/HASI/pr139-work/npm-cache
TESTS="tests/test_service_watch.py"
SEVEN="tests/test_service_watch.py tests/test_finish_grace_helpers.py tests/test_run_in_flight.py tests/test_confirm_reserve.py tests/test_self_closing.py tests/test_run_watch.py tests/test_observed_watering.py tests/test_i18n_completeness.py"
D:/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest $TESTS -p _local_socket_unblock -q --tb=line -rfE -p no:cacheprovider > D:/Entwicklung/HASI/pr139-work/replay/T04-green.txt 2>&1; tail -n 1 D:/Entwicklung/HASI/pr139-work/replay/T04-green.txt
D:/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest $SEVEN -p _local_socket_unblock -q --tb=line -rfE -p no:cacheprovider > D:/Entwicklung/HASI/pr139-work/replay/T04-suites.txt 2>&1
grep -E "^(FAILED|ERROR) " D:/Entwicklung/HASI/pr139-work/replay/T04-suites.txt | sed 's/ - .*//'
tail -1 D:/Entwicklung/HASI/pr139-work/replay/T04-suites.txt
```

Erwartet (real): Taskdatei `========================= 36 passed, 1 error in 2.98s =========================`
(`rev3/evidence.md` T4 GREEN); Suiten `======================== 259 passed, 1 error in 16.44s ========================`
(`dry6-logs/percommit.md`, `dd43f09c`); `ERROR` = der vorbestehende Lingering timer, keine `FAILED`-Zeile. Batch und
OpenSprinkler laufen durch den geänderten `_watch_evaluate` ohne `previous_state`, und ihre Datensätze bestehen
`run_has_finish_grace` nie. Ihre Suiten deckt die volle Suite in Task 13 ab (auf `dry6` FAILED/ERROR-Namensmengen
identisch zur Basis, `dry6-logs/full-suite.md`).

- [ ] **Step 5: Lint**

```bash
cd /d/Entwicklung/HASI/HAsmartirrigation
mkdir -p D:/Entwicklung/HASI/pr139-work/tmp D:/Entwicklung/HASI/pr139-work/npm-cache && export TEMP=D:/Entwicklung/HASI/pr139-work/tmp TMP=D:/Entwicklung/HASI/pr139-work/tmp TMPDIR=D:/Entwicklung/HASI/pr139-work/tmp npm_config_cache=D:/Entwicklung/HASI/pr139-work/npm-cache
uvx black --check custom_components/irrigation_plus/ $(git diff --name-only 2b2c403b -- tests)
uvx ruff check custom_components/irrigation_plus/
```

Erwartet (real, `scratch/dry5-checks.log` bei `9380fb74`; dieselbe Dateimenge auf dry6): `72 files would be left
unchanged.` / `All checks passed!`

- [ ] **Step 6: Baum gleich `dry6`**

```bash
cd /d/Entwicklung/HASI/HAsmartirrigation
SRC=dd43f09c
git diff "$SRC" --stat
git status --short
```

Soll (nicht gemessen): `git diff` leer; Status `M ` für die zwei Dateien, `?? docs/SESSION-STAND.md`.

- [ ] **Step 7: Commit mit derselben Nachricht**

```bash
cd /d/Entwicklung/HASI/HAsmartirrigation
SRC=dd43f09c
git log -1 --format=%B "$SRC" | git commit -q -F -
test "$(git rev-parse HEAD^{tree})" = "$(git rev-parse "$SRC^{tree}")" && echo TREE-SAME
diff <(git log -1 --format=%B HEAD) <(git log -1 --format=%B "$SRC") && echo MSG-SAME
git log -1 --format=%B | grep -c '^#'
git show --stat --format= HEAD | tail -1
git log --oneline -1
git status --short
```

Soll (nicht gemessen): `TREE-SAME`, `MSG-SAME`, `0`, ` 2 files changed, 233 insertions(+), 3 deletions(-)` (Zahl real
aus `git show --stat dd43f09c`), `<neuer SHA> feat(run-watch): record a confirmed valve's own off report`, danach nur
`?? docs/SESSION-STAND.md`.

**Mutationsproben (Probelauf)**

Gemessen im Revisions-Probelauf auf Basis `0b418644`, in einem Probe-Worktree am damaligen Commit dieses Tasks
`6aef25d3` (`run_watch.py` und `tests/test_service_watch.py` dort identisch mit dem Endstand `adcb6fba`; Plan
Revision 2, Task 4, Step 9). Datei `custom_components/irrigation_plus/run_watch.py`, Lauf je Probe
`-k TestTheWatcherRecordsTheValvesOwnOffReport` auf `tests/test_service_watch.py`. Die Datei hatte dort 37 Items, weil
die 2 Tests von T3b dazugehörten („29 deselected“); auf `dry6` hat sie bei T4 36 (dry5: 35). `dry3` änderte an T4 nur
Kommentare, einen Test-Docstring und die Commit-Nachricht (`dry3-logs/T5.md`, Stopp 2); die Codezeilen der Proben sind
unverändert. „Zeile `X` entfernt“ = die ganze Zeile mit Einrückung und `\n`, Ersatz leer: 20 Leerzeichen vor
`previous_state=event.data.get("old_state"),`, 16 vor den `and …`-Zeilen des Aus-Zweigs.
`guard-removed-and-last-updated` wendet `first-off-guard-removed` und `last-updated` nacheinander an. Task 13 läuft die
Proben erneut.

| Probe | Mutation in `run_watch.py` | Beobachtet (Probelauf) |
|---|---|---|
| previous-state-not-passed | `_watch_state_changed`: Zeile `previous_state=event.data.get("old_state"),` entfernt | FAIL (4: `records_the_states_last_changed`, `attribute_only_update`, `unavailable_spell`, `inside_the_debounce_clears`) `KeyError: 'valve_off'` — `4 failed, 4 passed, 29 deselected, 4 errors` |
| initial-evaluate-records | `                previous_state is not None\n                and previous_state.state in RUNNING_STATES\n` --> `                (previous_state is None or previous_state.state in RUNNING_STATES)\n` | FAIL (1: `re_adopted_run_does_not_record_the_initial_off`) `AssertionError: assert not '2026-09-15T18:52:45+00:00'` |
| clock-not-last-changed | `state.last_changed.isoformat()` --> `dt_util.utcnow().isoformat()` | FAIL (4: dieselben wie previous-state-not-passed) `assert '2026-09-15T1....472689+00:00' == '2026-09-15T1....500000+00:00'` |
| grace-gate-removed | Zeile `and run_has_finish_grace(run)` entfernt | FAIL (1: `before_the_update_records_nothing`) `AssertionError: assert not '2026-09-15T18:53:07+00:00'` |
| running-condition-removed | Zeile `and previous_state.state in RUNNING_STATES` entfernt | FAIL (2: `unavailable_mid_run_records_nothing`, `re_adopted_run_does_not_record_an_off_after_unavailable`) `AssertionError: assert not '2026-09-15T18:54:19+00:00'`, `...:54:21+00:00` — `2 failed, 6 passed, 29 deselected, 2 errors` |
| unavailable-accepted | `previous_state.state in RUNNING_STATES` --> `previous_state.state in (*RUNNING_STATES, "unavailable")` | FAIL (2: dieselben) `AssertionError: assert not '2026-09-15T18:54:30+00:00'`, `...:54:31+00:00` |
| clear-removed | `await self._watch_update_run(zid, {const.RUN_VALVE_OFF: None})` --> `pass` | FAIL (1: `inside_the_debounce_clears`) `AssertionError: assert not '2026-09-15T18:53:37.500000+00:00'` |
| clear-gated-on-segmented | `if policy.settles_on_valve_window and run.get(const.RUN_VALVE_OFF):` --> `if policy.segmented and run.get(const.RUN_VALVE_OFF):` | FAIL (1: `inside_the_debounce_clears`) `AssertionError: assert not '2026-09-15T18:53:48.500000+00:00'` |
| first-off-guard-removed (äquivalent) | Zeile `and not run.get(const.RUN_VALVE_OFF)` entfernt | `8 passed, 29 deselected`. Äquivalent unter E6: ein zweites `off` folgt auf `unavailable` oder `off`, nicht auf „laufend“, und ein laufender Zustand dazwischen löscht `RUN_VALVE_OFF`. Die Bedingung bleibt als Schutz gegen Überschreiben |
| guard-removed-and-last-updated (äquivalent) | beide: Schutzzeile entfernt UND `state.last_changed` --> `state.last_updated` | `8 passed, 29 deselected`. Äquivalent: aufgezeichnet wird nur beim echten Wechsel aus „laufend“, dort ist `last_changed == last_updated` |
| last-updated (äquivalent) | nur `state.last_changed` --> `state.last_updated` | `8 passed, 29 deselected`. Äquivalent aus demselben Grund; `last_changed` bleibt, weil es „Zeitpunkt des Zustandswechsels“ bedeutet |
| clear-policy-gate-removed (äquivalent) | `policy.settles_on_valve_window and` im Laufend-Zweig entfernt | `8 passed, 29 deselected`. Äquivalent: `RUN_VALVE_OFF` entsteht nur für Läufe mit Wartezeit (dieselbe Policy-Flagge). Das Tor bleibt, damit der Laufend-Zweig für Batch/OpenSprinkler keinen Schreibpfad bekommt |

8 von 8 nicht-äquivalenten Proben gefangen, 4 äquivalent mit Begründung; jeder der acht Tests scheitert an mindestens
einer Probe. Die Zeitstempel sind die des Probelaufs. Plan Revision 2 nennt zusätzlich, dass `running-condition-removed`
und `unavailable-accepted` den damaligen Neustart-Test `test_a_valve_back_from_unavailable_after_the_restart_is_bounded`
fingen. Auf `dry6` heißt der Test nach (a)/(b) `test_a_valve_back_from_unavailable_completes_for_its_plan`; ob die
beiden Proben ihn dort fangen, ist **nicht gemessen**. `test_a_record_from_before_the_update_records_nothing` fängt
seit dry6 zusätzlich die T2-Probe `no-margin-reads-zero`. `unavailable-accepted` fängt ab Task 5 zusätzlich die drei
Tests ohne Aus-Meldung (Tabelle Task 5).

---

### Task 5: Abschluss nimmt `actual_s` an, der Watcher rechnet mit gespeicherter Aus-Meldung nach dem Ventil-Fenster ab

**dry6:** `c234fb23` (dry5: `b423feca`) — `feat(run-watch): settle a confirmed service run on its valve window`

**Files** (Zeilen auf `c234fb23`; der Produktivcode ist der von `b423feca`):
- TEST: `tests/test_service_watch.py` (`test_a_valve_off_at_the_planned_end_completes` auf eingefrorene Uhr umgestellt;
  Modul-Helfer `_advance` und `_run_until_the_valve_closes`; neue Klasse `TestAConfirmedRunIsSettledOnItsValveWindow`
  nach `TestTheWatcherRecordsTheValvesOwnOffReport`; seit dry6 dahinter die Klasse
  `TestACloseReportedPastTheMarginIsKnownAndDeliberatelyUnchanged` mit dem Pin für das gestrichene T6)
- PROD: `custom_components/irrigation_plus/run_watch.py` (`_watch_valve_window` `:960`, `_watch_settle_by_window`
  `:964-984`, Weiche in `_watch_finish` `:990-1004`), `custom_components/irrigation_plus/self_closing.py`
  (`_sc_finish_run(zone_id, *, actual_s=None)` `:340`, `actual_s=planned_s if actual_s is None else actual_s` `:405`;
  `async_stop_self_closing(..., actual_s=None)` `:778-785`, `elapsed = actual_s if actual_s is not None else self._sc_run_elapsed(run)` `:848`)
- `git show --stat` (evidence.md): `3 files changed, 350 insertions(+), 7 deletions(-)`
- Commit-Nachricht: die von `b423feca` plus ein letzter Absatz vor dem Trailer: eine Aus-Meldung später als die Marge
  landet in der Entprellung, der Backstop bei planned + Entprellung + Marge kommt zuerst und schließt für den Plan ab
  „as it always has“; „that case is known and deliberately unchanged; a test pins it“.

**Was und warum**
- **Wurzel 2:** `_watch_finish` las `elapsed` erst nach der 5-s-Entprellung (`run_watch.py:823` auf `2b2c403b`),
  `async_stop_self_closing` las die Uhr noch einmal (`self_closing.py:764`), und ein abgeschlossener Lauf verwarf den
  Wert ganz für `planned_s` (`:385`). Ein Ventil, das 2–3 s spät oder etwas früh schloss, stand als pünktlich da, und
  jeder vom Watcher abgerechnete Teil-Lauf buchte die Entprellung als Bewässerung (einziger Watcher-Abschluss auf
  HA-Prod, 11.09.: `actual_s` 113,98 gegen 109,89 s offen, +4,09 s).
- **Neu, nur mit gespeicherter Aus-Meldung:** `_watch_finish` leitet einen Lauf mit `run_has_finish_grace(run)` UND
  `RUN_VALVE_OFF` an `_watch_settle_by_window`. Fenster = `valve_window_seconds` = `RUN_VALVE_OFF − RUN_VALVE_ON`.
  Abgeschlossen, wenn `Fenster + max(1, Marge) >= planned` --> `_sc_finish_run(zid, actual_s=Fenster)`; sonst Teil-Lauf
  `async_stop_self_closing(zid, close_valve=False, actual_s=Fenster)`. Die Entprellung entscheidet nur noch, OB der
  Lauf endete.
- **E1, Toleranz max(1 s, Marge):** die Meldungen eines Ventils liegen beiderseits des geplanten Endes (Kirschlorbeer
  13.09.: 1118,33 von 1119 s). Mit 1 s blieben ab Ventil-Ein nur 0,33 s Luft, ab `RUN_STARTED` wäre der Lauf ein
  Teil-Lauf gewesen. JustChr 09-16: „in“, sonst wäre ein normales Ende als Teil-Lauf eine Regression der Wartezeit.
- **Entscheidung (b)** (ersetzt die Watcher-Hälfte von E4; SP-4; JustChr 09-19: „The second one matters most.“): Ein
  Wartezeit-Lauf OHNE gespeicherte Aus-Meldung (`on --> unavailable --> off`, oder ein `off`, das nur die erste
  Auswertung eines neu aufgenommenen Watchers sah) behält die Basisregel: `elapsed` ab `RUN_OBSERVED_START`, gelesen
  nach der Entprellung; abgeschlossen gdw. `elapsed + 1 >= planned` (`actual_s = planned_s`), sonst
  `async_stop_self_closing(zid, close_valve=False)` ohne `actual_s`. Rechnung: die Entprellung entscheidet 5 s nach dem
  Schluss, also `elapsed = (planned − x) + 5` bei einem Schluss x Sekunden vor dem Ende. Basisregel:
  `(planned − x) + 5 + 1 >= planned` gdw. `x <= 6`, ein unberichteter Schluss bis ~6 s zu früh wird abgeschlossen (heute
  genauso). Die Marge als Toleranz auf derselben Uhr: `(planned − x) + 5 + 4 >= planned` gdw. `x <= 9`, bis ~9 s zu
  früh mit voller Gutschrift. Das wäre ein Loch, das erst die Wartezeit öffnet. Pin:
  `test_an_unreported_close_seven_seconds_early_stays_partial` (Schluss +593, Entscheidung +598: `598 + 1 < 600`
  Teil-Lauf; mit Marge wäre `598 + 4 >= 600` abgeschlossen). Dasselbe gilt für jeden Datensatz ohne eingefrorene
  Marge (Batch, OpenSprinkler, Service-Läufe von vor dem Update).
- `_sc_finish_run(zone_id, *, actual_s=None)`: mit Wert wird er als `actual_s` geschrieben; ohne Wert wie bisher
  `planned_s` (Backstop, Basisregel, OpenSprinkler, Batch). Zeitvolumen und Kalibrierprobe bleiben bei `planned_s`,
  dem Fenster, für das der Lauf gutgeschrieben und bemessen wurde. **Keine Zusage `actual_s <= planned_s`:** ein spät
  meldendes Ventil bucht 602 von 600.
- `async_stop_self_closing(..., actual_s=None)`: ein übergebener Wert speist `delivered_frac`, Zeitvolumen und
  `actual_s`, damit Eimer, Volumen und Verlauf übereinstimmen. Ohne Wert liest er die Uhr wie bisher.
- **T6 gestrichen** (JustChr 09-16): feuert der Backstop, schreibt er weiter `planned_s`, auch mit gespeicherter
  Aus-Meldung. Im PR-Text als „known and deliberately unchanged“. Seit dry6 pinnt ein Test genau diesen Fall (siehe
  Tests), damit ein späteres Wiedereinführen von T6 nicht unbemerkt bleibt.
- **Offene Frage 1 aus `dry3-logs/T5.md`** (Anker des Watcher-Teil-Laufs ohne Aus-Meldung): bei T5 bucht er
  `_sc_run_elapsed` wie die Basis. Task 7 hängt seinen neuen Zweig an `close_valve` (Entscheidung (d)), damit das so
  bleibt. Die Probe `base-partial-passes-window` überlebt deshalb bei T5 und wird ab Task 7 gefangen.
- Reichweite (PR-Text): gemeldete Schlüsse zwischen Marge und ~6 s vor dem Ende werden neu `partial` (bei Marge 0:
  zwischen 1 s und ~6 s). Ohne Aus-Meldung bleibt die Grenze bei ~6 s.

**Tests** (`tests/test_service_watch.py`; 600 s geplant, Default-Marge 4, Dispatch und Schluss unter einer
eingefrorenen Uhr, `RUN_VALVE_ON` = Dispatch)
- `TestAFullRunIsStillAFullRun::test_a_valve_off_at_the_planned_end_completes` (angepasst, Assertion unverändert) —
  läuft jetzt in `freeze_time`, damit das Fenster genau 600 s ist; `actual_s == planned_s == 600`.
- `test_a_close_just_after_the_window_completes_on_the_reported_window` — Schluss +602 --> `completed`, `actual_s` 602
  (nicht 608, nicht 600); Zeitvolumen und Kalibrierprobe bei 600.
- `test_a_close_inside_the_margin_completes_on_the_reported_window` — +597 --> `completed` 597.
- `test_a_close_beyond_the_margin_is_a_partial_credited_for_its_window` — +590 --> `partial` 590 (nicht 596), Eimer
  `-20 + 20 * 590 / 600`.
- `test_a_margin_of_zero_still_tolerates_one_second` — Marge 0, +599,5 --> `completed` 599,5.
- `test_a_margin_of_zero_settles_a_close_beyond_that_second_as_partial` — Marge 0, +598,5 --> `partial` 598,5.
- `test_an_off_after_an_unavailable_mid_run_keeps_the_old_rule` — `unavailable` +300, `off` +302 (nicht gespeichert),
  Entscheidung +308 --> `partial` 308 ab `RUN_OBSERVED_START`, nicht 302.
- `test_an_unreported_close_seven_seconds_early_stays_partial` — Pin von (b): `unavailable` +590, `off` +593,
  Entscheidung +598 --> `partial` 598, keine Kalibrierprobe.
- `test_an_unreported_close_inside_the_old_second_completes_for_its_plan` — `unavailable` +592, `off` +594,5,
  Entscheidung +599,5 --> `completed`, `actual_s == planned_s == 600`.
- `test_a_record_from_before_the_update_keeps_the_old_rule` — ohne Marge und Ventil-Ein, Schluss +593,5, Entscheidung
  +599,5 --> `completed` 600, nicht 599,5.
- `TestACloseReportedPastTheMarginIsKnownAndDeliberatelyUnchanged::test_the_backstop_finishes_it_for_the_plan_before_the_debounce`
  (neu in dry6; Regressions-Pin für das gestrichene T6) — Marge 4, geplant 600, echter Backstop-Timer; das Ventil meldet
  „aus“ bei +606, gespeichert als `RUN_VALVE_OFF`, die Entprellung wäre bei 611 fällig. Der Backstop bei 609 schließt
  den Lauf `completed` mit `actual_s == planned_s == 600` ab (nicht 606); bei +612 gibt es weiter genau einen
  `_record_run`, keine offene Entprellung und keinen Backstop-Timer. Am Elternstand ist er **grün**, gewollt: er hält
  fest, was der Basisstand schon tut (siehe RED).
- Neue Modul-Helfer `_advance(hass, frozen, seconds)` (Uhr vorstellen, Timer feuern) und
  `_run_until_the_valve_closes(hass, c, zone, closed_after, *, before=None)` (Dispatch, Aus-Meldung, Entprellung
  ablaufen lassen unter einer Uhr); ab Task 7 weiterverwendet.

- [ ] **Step 1: Tests aus dem `dry6`-Commit auschecken**

```bash
cd /d/Entwicklung/HASI/HAsmartirrigation
SRC=c234fb23; TESTS="tests/test_service_watch.py"
git status --short
[ "$(git rev-parse HEAD^{tree})" = "$(git rev-parse "$SRC~1^{tree}")" ] && echo PARENT-TREE-SAME
git checkout "$SRC" -- $TESTS
git status --short
```

Soll (nicht gemessen): vorher nur `?? docs/SESSION-STAND.md`, `PARENT-TREE-SAME`, danach zusätzlich
`M  tests/test_service_watch.py`.

- [ ] **Step 2: RED prüfen**

```bash
cd /d/Entwicklung/HASI/HAsmartirrigation
mkdir -p D:/Entwicklung/HASI/pr139-work/tmp D:/Entwicklung/HASI/pr139-work/npm-cache && export TEMP=D:/Entwicklung/HASI/pr139-work/tmp TMP=D:/Entwicklung/HASI/pr139-work/tmp TMPDIR=D:/Entwicklung/HASI/pr139-work/tmp npm_config_cache=D:/Entwicklung/HASI/pr139-work/npm-cache
TESTS="tests/test_service_watch.py"
L=D:/Entwicklung/HASI/pr139-work/replay/T05-red.txt
D:/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest $TESTS -p _local_socket_unblock -q --tb=line -rfE -p no:cacheprovider > $L 2>&1
grep -E "^collected |^(FAILED|ERROR) |^E  |\.py:[0-9]+: " $L; tail -n 1 $L
```

Erwartet (real, `rev3/evidence.md` T5 RED, gemessen auf dry6; `�` = `±`):

```
collected 46 items
FAILED tests/test_service_watch.py::TestAConfirmedRunIsSettledOnItsValveWindow::test_a_close_just_after_the_window_completes_on_the_reported_window
FAILED tests/test_service_watch.py::TestAConfirmedRunIsSettledOnItsValveWindow::test_a_close_inside_the_margin_completes_on_the_reported_window
FAILED tests/test_service_watch.py::TestAConfirmedRunIsSettledOnItsValveWindow::test_a_close_beyond_the_margin_is_a_partial_credited_for_its_window
FAILED tests/test_service_watch.py::TestAConfirmedRunIsSettledOnItsValveWindow::test_a_margin_of_zero_still_tolerates_one_second
FAILED tests/test_service_watch.py::TestAConfirmedRunIsSettledOnItsValveWindow::test_a_margin_of_zero_settles_a_close_beyond_that_second_as_partial
ERROR tests/test_service_watch.py::TestOneOffSampleIsNotEvidenceTheWaterStopped::test_the_run_is_not_settled_before_the_window_is_out
==================== 5 failed, 41 passed, 1 error in 3.85s ====================
```

mit

```
D:\Entwicklung\HASI\pr139-work\dry2\tests\test_service_watch.py:739: assert 600.0 == 602 � 1.0e-02
D:\Entwicklung\HASI\pr139-work\dry2\tests\test_service_watch.py:756: assert 600.0 == 597 � 1.0e-02
D:\Entwicklung\HASI\pr139-work\dry2\tests\test_service_watch.py:767: assert 596.0 == 590 � 1.0e-02
D:\Entwicklung\HASI\pr139-work\dry2\tests\test_service_watch.py:782: assert 600.0 == 599.5 � 1.0e-02
D:\Entwicklung\HASI\pr139-work\dry2\tests\test_service_watch.py:794: AssertionError: assert 'completed' == 'partial'
```

Die fünf Tests mit gespeicherter Aus-Meldung fallen (dieselben wie auf dry5): die Basis bucht `planned_s` (600) oder den
Wert nach der Entprellung (596 statt 590) und schließt 598,5 bei Marge 0 ab. Die vier übrigen Tests der Klasse pinnen
die Basisregel ((b), Datensatz von vor dem Update) und sind schon am Parent grün; der angepasste Pin ebenso. Der neue
T6-Pin ist am Parent ebenfalls grün, und das ist gewollt: er pinnt unverändertes Verhalten. Dass er etwas fängt, zeigt
die Probe `t6-backstop-settles-on-stored-off` (Tabelle unten).

- [ ] **Step 3: Produktivdateien aus dem `dry6`-Commit auschecken**

```bash
cd /d/Entwicklung/HASI/HAsmartirrigation
SRC=c234fb23; PROD="custom_components/irrigation_plus/run_watch.py custom_components/irrigation_plus/self_closing.py"
git checkout "$SRC" -- $PROD
```

- [ ] **Step 4: GREEN, 7 Suiten + i18n**

```bash
cd /d/Entwicklung/HASI/HAsmartirrigation
mkdir -p D:/Entwicklung/HASI/pr139-work/tmp D:/Entwicklung/HASI/pr139-work/npm-cache && export TEMP=D:/Entwicklung/HASI/pr139-work/tmp TMP=D:/Entwicklung/HASI/pr139-work/tmp TMPDIR=D:/Entwicklung/HASI/pr139-work/tmp npm_config_cache=D:/Entwicklung/HASI/pr139-work/npm-cache
TESTS="tests/test_service_watch.py"
SEVEN="tests/test_service_watch.py tests/test_finish_grace_helpers.py tests/test_run_in_flight.py tests/test_confirm_reserve.py tests/test_self_closing.py tests/test_run_watch.py tests/test_observed_watering.py tests/test_i18n_completeness.py"
D:/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest $TESTS -p _local_socket_unblock -q --tb=line -rfE -p no:cacheprovider > D:/Entwicklung/HASI/pr139-work/replay/T05-green.txt 2>&1; tail -n 1 D:/Entwicklung/HASI/pr139-work/replay/T05-green.txt
D:/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest $SEVEN -p _local_socket_unblock -q --tb=line -rfE -p no:cacheprovider > D:/Entwicklung/HASI/pr139-work/replay/T05-suites.txt 2>&1
grep -E "^(FAILED|ERROR) " D:/Entwicklung/HASI/pr139-work/replay/T05-suites.txt | sed 's/ - .*//'
tail -1 D:/Entwicklung/HASI/pr139-work/replay/T05-suites.txt
```

Erwartet (real): Taskdatei `========================= 46 passed, 1 error in 3.84s =========================`
(`rev3/evidence.md` T5 GREEN); Suiten `======================== 269 passed, 1 error in 17.41s ========================`
(`dry6-logs/percommit.md`, `c234fb23`); `ERROR` = der vorbestehende Lingering timer, keine `FAILED`-Zeile. Die
geänderten Signaturen (`actual_s=None`) lassen OpenSprinkler und Batch unberührt; ihre Suiten deckt die volle Suite in
Task 13 ab.

- [ ] **Step 5: Lint**

```bash
cd /d/Entwicklung/HASI/HAsmartirrigation
mkdir -p D:/Entwicklung/HASI/pr139-work/tmp D:/Entwicklung/HASI/pr139-work/npm-cache && export TEMP=D:/Entwicklung/HASI/pr139-work/tmp TMP=D:/Entwicklung/HASI/pr139-work/tmp TMPDIR=D:/Entwicklung/HASI/pr139-work/tmp npm_config_cache=D:/Entwicklung/HASI/pr139-work/npm-cache
uvx black --check custom_components/irrigation_plus/ $(git diff --name-only 2b2c403b -- tests)
uvx ruff check custom_components/irrigation_plus/
```

Erwartet (real, `scratch/dry5-checks.log` bei `b423feca`; dieselbe Dateimenge auf dry6): `72 files would be left
unchanged.` / `All checks passed!`

- [ ] **Step 6: Baum gleich `dry6`**

```bash
cd /d/Entwicklung/HASI/HAsmartirrigation
SRC=c234fb23
git diff "$SRC" --stat
git status --short
```

Soll (nicht gemessen): `git diff` leer; Status `M ` für die drei Dateien, `?? docs/SESSION-STAND.md`.

- [ ] **Step 7: Commit mit derselben Nachricht**

```bash
cd /d/Entwicklung/HASI/HAsmartirrigation
SRC=c234fb23
git log -1 --format=%B "$SRC" | git commit -q -F -
test "$(git rev-parse HEAD^{tree})" = "$(git rev-parse "$SRC^{tree}")" && echo TREE-SAME
diff <(git log -1 --format=%B HEAD) <(git log -1 --format=%B "$SRC") && echo MSG-SAME
git log -1 --format=%B | grep -c '^#'
git show --stat --format= HEAD | tail -1
git log --oneline -1
git status --short
```

Soll (nicht gemessen): `TREE-SAME`, `MSG-SAME`, `0`, ` 3 files changed, 350 insertions(+), 7 deletions(-)` (Zahl real
aus `git show --stat c234fb23`), `<neuer SHA> feat(run-watch): settle a confirmed service run on its valve window`,
danach nur `?? docs/SESSION-STAND.md`.

**Mutationsproben (Probelauf)**

Gemessen im Probelauf `dry3` auf Basis `0b418644` am Commit `d0e1eb33` (T5 nach Entscheidung (b)); Protokoll
`dry3-logs/T5.md` §4, Rohausgabe `dry3-logs/T5-probes.txt`, Sicherungen `mut/dry3-T5-PROBE.bak`, SHA-256 nach jeder
Wiederherstellung gleich. Lauf je Probe: `tests/test_service_watch.py tests/test_finish_grace_helpers.py` ganz; dort
81 Tests (mit den 2 Tests von T3b und den 5 von `TestZoneFinishGrace`), auf `dry6` bei T5 76 (46 + 30). Der Probelauf
ersetzte mit CRLF-Suchtexten (`newline=''`); die Tabelle notiert sie mit `\n`. Datei
`custom_components/irrigation_plus/run_watch.py`. Task 13 läuft diese Proben erneut mit dem CRLF-Skript
`mut/real_t5_probes.py` (Kopie von `mut/dry3_t5_probes.py` mit neuem Sicherungspräfix, plan-30 Task 13 Step 8); alle 13
Suchtexte kommen auf dry6 genau einmal vor (geprüft 19.09. abends, lesend).

| Probe | Mutation in `run_watch.py` (Suchtext --> Ersatz) | Beobachtet (Probelauf) |
|---|---|---|
| gate-dropped | `        if run_has_finish_grace(run) and run.get(const.RUN_VALVE_OFF):\n` --> `        if run_has_finish_grace(run):\n` | GEFANGEN 2: `seven_seconds_early_stays_partial` (`assert 'completed' == 'partial'`), `inside_the_old_second_completes_for_its_plan` (`assert 599.5 == 600.0`) |
| gate-inverted | dieselbe Zeile --> `        if run_has_finish_grace(run) and not run.get(const.RUN_VALVE_OFF):\n` | GEFANGEN 7: die fünf Tests mit Aus-Meldung (`600.0 == 602`, `== 597`, `596.0 == 590`, `600.0 == 599.5`, `'completed' == 'partial'`) und die zwei unberichteten Schlüsse |
| gate-off-only (äquivalent) | dieselbe Zeile --> `        if run.get(const.RUN_VALVE_OFF):\n` | ÜBERLEBT, äquivalent: `RUN_VALVE_OFF` schreibt nur der Aufzeichnungszweig aus Task 4, und der steht selbst hinter `run_has_finish_grace(run)`; die eingefrorene Marge wird nie entfernt. `record_from_before_the_update` entfernt die Marge vor dem Schluss, dort entsteht also auch keine Aus-Meldung |
| gate-wrong-key | dieselbe Zeile --> `        if run_has_finish_grace(run) and run.get(const.RUN_VALVE_ON):\n` | GEFANGEN 2: wie gate-dropped |
| always-routed | dieselbe Zeile --> `        if True:\n` | GEFANGEN 3: die zwei unberichteten Schlüsse und `record_from_before_the_update_keeps_the_old_rule` (`assert 599.5 == 600.0`) |
| never-routed | dieselbe Zeile --> `        if False:\n` | GEFANGEN 5: die fünf Tests mit Aus-Meldung |
| base-tolerance-two | `        if elapsed + 1 >= planned:\n` --> `        if elapsed + 2 >= planned:\n` | GEFANGEN 1: `seven_seconds_early_stays_partial` (`'completed' == 'partial'`) |
| base-tolerance-margin | dieselbe Zeile --> `        if elapsed + run_completion_tolerance(run) >= planned:\n` (die Toleranz von E4 auf der alten Uhr) | GEFANGEN 1: `seven_seconds_early_stays_partial` |
| base-tolerance-zero | dieselbe Zeile --> `        if elapsed >= planned:\n` | GEFANGEN 2: `inside_the_old_second_completes_for_its_plan`, `record_from_before_the_update_keeps_the_old_rule` (`'partial' == 'completed'`) |
| base-finish-passes-elapsed | `            await self._sc_finish_run(zid)\n` --> `            await self._sc_finish_run(zid, actual_s=elapsed)\n` | GEFANGEN 2: `inside_the_old_second_completes_for_its_plan`, `record_from_before_the_update_keeps_the_old_rule` (`599.5 == 600.0`) |
| base-partial-passes-window | `            await self.async_stop_self_closing(zid, close_valve=False)\n` --> `            await self.async_stop_self_closing(\n                zid, close_valve=False, actual_s=self._watch_valve_window(run)\n            )\n` | ÜBERLEBT bei T5 (`81 passed, 1 error`): unter allen T5-Fixtures gilt `RUN_VALVE_ON == RUN_OBSERVED_START ==` Dispatch (eingefrorene Uhr), allgemein aber nicht äquivalent. **Ab Task 7 gefangen** von `test_the_watchers_own_partial_keeps_its_observed_start`: `assert 307.6 == 307 ± 1.0e-02`, `1 failed, 101 passed, 1 error` (`dry3-logs/T7-t5probe-rerun.txt`, am T7-Stand von `dry3`) |
| window-planned-without-off (neu bewertet) | `    return max(0.0, min((now - anchor).total_seconds(), planned))\n` --> `    return planned\n` | GEFANGEN 1, nur noch vom T2-Helfertest `test_without_an_off_report_the_window_is_the_time_since_on` (`assert 600.0 == 300.0`). Nach (b) erreicht kein Abrechnungspfad bei T5 diesen Zweig; ab Task 7 der manuelle Stopp |
| unavailable-accepted (Code aus T4, neu bewertet) | `                and previous_state.state in RUNNING_STATES\n` --> `                and previous_state.state in (*RUNNING_STATES, "unavailable")\n` | GEFANGEN 5 (+5 Lingering timer, die Tests brechen vor `_advance` ab; `5 failed, 76 passed, 6 errors`): `test_an_off_after_an_unavailable_mid_run_records_nothing`, `test_a_re_adopted_run_does_not_record_an_off_after_unavailable`, `test_an_off_after_an_unavailable_mid_run_keeps_the_old_rule`, `test_an_unreported_close_seven_seconds_early_stays_partial`, `test_an_unreported_close_inside_the_old_second_completes_for_its_plan` |

13 Proben: 11 gefangen, 1 äquivalent (`gate-off-only`), 1 überlebt bei T5 auf einer unveränderten Basiszeile und wird
ab Task 7 gefangen (`base-partial-passes-window`; `rev3/spec.md`, Mutationsproben). Die geforderten Proben sind dabei:
Weiche ohne Aus-Meldungs-Bedingung (`gate-dropped`), geänderte Toleranz der Basisregel (`base-tolerance-two`/`-margin`/`-zero`)
und die neu bewertete Grenze ohne Aus-Meldung (`window-planned-without-off`).

**Dazu dry6: die Probe gegen den T6-Pin** (`dry6-logs/T5.md`; Sicherung `mut/dry6-T5-…bak`, SHA-256 gleich). Der Pin ist
am Elternstand grün, also zeigt erst eine Probe, dass er etwas fängt: sie bringt T6s Verhalten zurück (Revision 2,
`_sc_backstop_fired` aus `a3c220e5` auf `dry2`, hier in den Backstop-Rückruf eingesetzt).

| Probe | Mutation in `self_closing.py` | Beobachtet am T5-Stopp | Beobachtet am Endstand |
|---|---|---|---|
| t6-backstop-settles-on-stored-off | `_done`: `await self._sc_finish_run(zone_id)` --> Datensatz holen; mit Wartezeit und gespeicherter `RUN_VALVE_OFF` `await self._watch_settle_by_window(zone_id, run)` und `return`, sonst wie bisher | FAIL nur der T6-Pin, `:941 assert 606.0 == 600.0` (`1 failed, 202 passed, 1 error`) | FAIL nur der T6-Pin (`1 failed, 233 passed, 1 error`) |

Kein anderer Test fängt diese Probe. Im Treiber von Task 13 ist sie der Satz `t05pin` (`-k
KnownAndDeliberatelyUnchanged`, ohne Mutation auf dry6 `1 passed, 68 deselected`). Mit den 9 Rev.-2-Proben des
Satzes `t05r2` (plan-30) hat T5 damit 22 gezählte Proben: 13 hier, ohne die Dublette `unavailable-accepted` (zählt bei
T4), plus 9 plus diese eine.

---

<!-- Plan #139, Revision 3, Teil „Tasks b“: Task 6 (gestrichen) bis Task 12. Nachvollzug-Verfahren, Stopp-Regel,
     Umgebung (TEMP-Umleitung, CRLF, Lingering timer) und Ausgangslage stehen im Kopfteil. Zahlen ohne Quellangabe gibt
     es hier nicht; was auf dry5/dry6 nicht gemessen wurde, heißt „nicht gemessen“. Referenz ist seit dem 19.09. abends
     `dry6/backstop-grace`; Produktivcode und dist sind dort gleich `dry5`, nur `tests/test_service_watch.py` und die
     Nachrichten von T3 und T5 unterscheiden sich (Kopfteil, Grundlagen). -->

---

### Task 6 — gestrichen: Der Backstop rechnet einen Lauf mit gespeicherter Aus-Meldung nach dem Ventil-Fenster ab

**Kein Commit, keine Tests, nichts nachzuvollziehen.** Die Nummer bleibt frei.

- **Was es war (Revision 2):** `_sc_schedule_cleanup`s inneres `_done` rief eine neue Methode `_sc_backstop_fired`.
  Feuerte der Backstop eines bestätigten Service-Laufs, obwohl der Watcher schon `RUN_VALVE_OFF` gespeichert hatte,
  wurde der Lauf über `_watch_settle_by_window` auf dem gemeldeten Fenster abgerechnet statt mit `planned_s`.
- **Warum gestrichen:** JustChr am 16.09.
  ([issuecomment-5692654650](https://github.com/JustChr/HAsmartirrigation/issues/139#issuecomment-5692654650),
  „Out — 3“). Ohne den Commit bucht dieser Lauf `planned_s`, genau wie heute. Das ist die Verbesserung eines
  Datensatzes, den die Wartezeit nicht verschlechtert, und Verbesserungen warten bis nach dem stabilen Release (#147).
  Unser Kommentar vom 19.09. (5740280769) nannte drei weitere Fälle derselben Art ((a), (b), (c)). JustChr am 19.09.
  (5740329987): „stay as today“.
- **Folgen im Plan:**
  - `_sc_backstop_fired` und der Test-Helfer `_with_the_real_backstop` aus Revision 2 existieren nicht.
  - Die Real-Timer-Tests „verpasster Schluss --> `planned_s`“ aus Revision 2 fielen mit T6 weg (Spec, „Abdeckung der
    Vorgabe“). Die Abdeckung liegt jetzt an diesen Stellen:
    - seit dry6 der Echt-Timer-Test in T3,
      `TestAMissedCloseStillSettlesViaTheBackstop::test_a_valve_that_never_reports_off_is_finished_when_the_grace_is_out`:
      bei +608 nichts abgerechnet, bei +610 `completed` mit `actual_s == planned_s == 600`, `irrigation_finished` einmal;
    - der Arm-Wert `(2, 609)` in T3;
    - die Dispatch-Tests in T9, die den ersten Lauf über den echten Backstop bei +610 abrechnen;
    - die Pins +609 und +700 in T8.
  - Seit dry6 pinnt ein Test in T5 den Fall selbst:
    `TestACloseReportedPastTheMarginIsKnownAndDeliberatelyUnchanged::test_the_backstop_finishes_it_for_the_plan_before_the_debounce`
    (Aus-Meldung bei +606 gespeichert, Backstop bei 609 schließt mit 600 ab, nicht 606). Er fällt gegen eine Probe, die
    T6s Verhalten zurückbringt (`assert 606.0 == 600.0`), und nur er (`dry6-logs/T5.md`; Task 13, Satz `t05pin`).
  - Der Docstring von `_watch_settle_by_window` („Only for a run whose off report is on record (see _watch_finish)“)
    ist damit genau: T8 ruft es nicht mehr auf.
- **PR-Text** (Pflicht laut JustChr 09-16): eine Zeile „known and deliberately unchanged“, mit dem Hinweis, dass ein Test
  den Fall pinnt. Ein Backstop mit schon gespeicherter Aus-Meldung bucht `planned_s`. Es gibt zwei Auslöser (Spec,
  „Ausdrücklich nicht dazu“):
  - ein Schluss, der später als die Marge gemeldet wird: die Aus-Meldung landet in der Entprellung, und der Backstop
    bei `planned + 5 + Marge` entscheidet zuerst;
  - ein reines Attribut-Update des schon „aus“ meldenden Ventils in den letzten `SERVICE_WATCH_SETTLE_SECONDS` vor dem
    Backstop hält die Entprellung über den Backstop hinaus am Leben (SP-10).

  Dazu kommen die Neustart-Zwillinge (a) und die SP-3-Variante (Task 8). Die Nachmessung (E10) achtet auf den zweiten
  Auslöser.
- **Beleg, dass das Streichen sauber ist:** siehe 5740280769, „dropping … is clean: the suite loses only their own
  tests, and the FAILED/ERROR names stay the same as on master“. Grundlage sind `after-drop-6-10.txt` und
  `baseline-0b418644.txt`; `comm -3` auf die Namensmengen ist leer (`dry3-logs/final.md`, Abschnitt 3).

---

### Task 7: Der manuelle Stopp misst ab der Ein-Meldung des Ventils und rechnet in der Wartezeit nach der Watcher-Regel ab

**dry6:** `f1266999` (dry5: `bcae641c`), `feat(service): measure a manual stop on the valve's own window`
(`2 files changed, 510 insertions(+), 6 deletions(-)`; dry5: +516, weil dort `_finished` und sein Import noch hier
standen). **Elternstand auf dry6:** `c234fb23` (T5).

**Files**
- TEST: `tests/test_service_watch.py`. Neu sind die Klasse `TestAManualStopMeasuresFromTheValvesOnReport` (13 Tests) und
  der Modul-Helfer `_stops_seen_by_the_record`. Die Tests benutzen `_finished` (fängt
  `irrigation_plus_irrigation_finished`); der Helfer und sein Import `async_capture_events` stehen seit dry6 in T3.
- PROD: `custom_components/irrigation_plus/self_closing.py`. Geändert werden:
  - die Importe `run_completion_tolerance` und `run_has_finish_grace` aus `.run_watch`;
  - die Auswahl von `elapsed` in `async_stop_self_closing`;
  - die Docstrings von `async_stop_self_closing` und `_sc_finish_run`.

**Was und warum**

Diesen Task hat JustChr am 16.09. als „In — 4“ aufgenommen; am 19.09. folgte „belongs inside #4“ für den Stopp in der
Wartezeit. Er schließt zwei Löcher.

- **Anker.** `async_stop_self_closing` las `elapsed` bisher ab `RUN_OBSERVED_START`. Bei einem Service-Lauf ist das die
  Confirm-Rückkehr, bis zu einen Poll nach der Ein-Meldung des Ventils. Ein gestoppter Lauf wurde also kürzer gemessen
  als einer, den der Watcher auf dem Ventil-Fenster (ab `RUN_VALVE_ON`) abrechnet.
- **Loch der Wartezeit.** Ab dem geplanten Ende wartet der Lauf in seiner Wartezeit auf die Aus-Meldung; früher
  schloss ihn der Backstop genau dort mit `planned_s` ab. Ein Stopp in dieser Zeit hätte ohne T7 zwei Folgen:
  - die Wartezeit wird als Bewässerung gebucht (ein Teil-Lauf für mehr als den Plan);
  - der Lauf wird `partial`, ohne `irrigation_finished` und ohne Kalibrierprobe.

  Beides ist heute unmöglich. Der Fall ist erreichbar: das Panel listet die Zone bis zum Abschluss mit ihrem Stop
  (`get_active_runs`), und Stop-all erreicht sie über dieselbe Liste, unabhängig vom In-flight-Fenster.

Neue Auswahl von `elapsed` (Spec, Design 3.2):

| Fall | Messung | Ergebnis |
|---|---|---|
| `actual_s` übergeben | dieser Wert | Watcher-Teil-Lauf mit Aus-Meldung (unverändert seit T5) |
| `close_valve` UND `run_has_finish_grace(run)`, `_sc_elapsed(RUN_STARTED) < planned` — **(c)** | `_watch_valve_window({**run, RUN_VALVE_OFF: None})`, also `min(jetzt − RUN_VALVE_ON, planned)` | Teil-Lauf wie heute, nur vom Anker `RUN_VALVE_ON` aus; eine gespeicherte Aus-Meldung zählt nicht |
| `close_valve` UND Tor, ab dem geplanten Ende — **(d)** | `_watch_valve_window(run)`: bis zur gespeicherten Aus-Meldung, sonst `planned` (Ventil meldet noch „an“) | `Fenster + run_completion_tolerance(run) >= planned` --> `await self._sc_finish_run(zone_id, actual_s=Fenster)`, `return True`; sonst Teil-Lauf auf dem Fenster (fällt in den bestehenden Teil-Lauf-Code) |
| sonst | `_sc_run_elapsed(run)` wie bisher | Watcher-Teil-Lauf ohne Aus-Meldung, write-only, Batch, OpenSprinkler, Datensätze von vor dem Update |

- **(c) vor dem Ende.** Hier hat die Entprellung einer gespeicherten Aus-Meldung noch nicht entschieden, ob es der
  Schluss war oder ein Blip. Der Stopp ist das Ende des Laufs, wie immer schon. Gemessen wird bis zum Stopp, gedeckelt
  auf `planned`.
  - Die Grenze wird ab `RUN_STARTED` gemessen, dem Anker des Backstops, nicht ab `RUN_VALVE_ON`.
  - Der Vergleich ist `<`: ein Stopp genau bei `planned` gilt als in der Wartezeit.
  - Ohne den Deckel würde ein Stopp 0,2 s vor dem Ende bei einer 0,6 s früheren Ein-Meldung 600,4 von 600 buchen.
- **(d) in der Wartezeit.** Der Stopp rechnet nach der Watcher-Regel auf denselben Meldungen ab.
  - `completed` innerhalb von max(1 s, Marge) läuft über `_sc_finish_run` mit `actual_s` = Fenster. Das bringt Eimer,
    Zähler (einmal), Stempel, `irrigation_finished`, Kalibrierprobe, aufgeschobene Berechnung und Ketten-Fortschritt
    wie beim Watcher.
  - Der Stopp kehrt vor seinem eigenen Abrechnungs-Code zurück, nichts wird doppelt gebucht. Der Zwillingstest
    vergleicht beides Feld für Feld.
  - Ein spät meldendes Ventil bucht 601 von 600. Nirgends steht deshalb die Zusage `actual_s <= planned_s`.
- **Ventil zuerst geschlossen.** Die Präambel des Stopps läuft unverändert vor dem neuen Zweig: `_os_cancel_watch`,
  Master-Freigabe, Stopp-Service (Ventil zu). Erst danach rechnet `_sc_finish_run` ab. Das pinnt
  `_stops_seen_by_the_record` (`seen == [1]`, Daten `{"zone_id": 2, "dauer": 0}`).
- **Zweite Master-Freigabe, harmlos.** `_sc_finish_run` ruft `_os_cancel_watch` und `async_master_release` noch einmal.
  - Der Watcher ist schon weg.
  - `holds.discard` auf das schon entfernte Token tut nichts. Ohne andere Holds stellt die Freigabe nur den Aus-Timer
    der Pumpe auf die Frist, die er schon hat (`master.py`, `async_master_release`/`async_master_schedule_off`).
  - Die Freigabe hinter das Schließen zu verschieben ließe den Pumpen-Hold hängen, wenn der Stopp-Service wirft.
    Deshalb bleibt es so. Der Code-Kommentar und der Docstring des Zwillingstests sagen es.
- **Tor `close_valve`.** Der einzige Aufrufer mit `close_valve=True` ist der manuelle Stopp (`_sc_maybe_stop` <--
  `async_stop_zone` <-- `async_stop_all_zones`).
  - Der eigene Teil-Lauf des Watchers ohne Aus-Meldung (`_watch_finish` --> `async_stop_self_closing(zid,
    close_valve=False)` ohne `actual_s`) bleibt auf `_sc_run_elapsed`. Das ist die Uhr, auf der seine Vollständigkeit
    nach Entscheidung (b) entschieden wurde.
  - Ohne das Tor würde er ab `RUN_VALVE_ON` gebucht, um bis zu einen Confirm-Poll länger. Bei einem Poll über 1 s könnte
    ein als `partial` entschiedener Lauf `actual_s == planned_s` mit voller Gutschrift bekommen. Das war die offene
    Frage 1 aus T5, gelöst mit Option (ii).
  - Pin: `test_the_watchers_own_partial_keeps_its_observed_start` bucht 307, nicht 307,6.
- **`_sc_run_elapsed` bleibt** für jeden Lauf ohne eingefrorene Marge (write-only, Batch, OpenSprinkler, Service-Datensatz
  von vor dem Update). Deren warteschlangengebundenes und segmentiertes Timing kennt das Fenster nicht.
- **Texte.** Der Docstring von `_sc_finish_run` nennt jetzt den Stopp in der Wartezeit als zweiten Aufrufer mit
  `actual_s` („where a valve still reporting on makes it the plan“). Der Kommentarblock des Zweigs begründet: den Anker,
  das Tor, (c), (d) und das doppelte Abbauen/Freigeben.
- **Stop-all braucht T9 nicht.** `get_active_runs` listet jeden gespeicherten Datensatz, unabhängig vom
  In-flight-Fenster. Der Test richtet `store.config.active_valve_runs` des `_coord`-Doubles auf die gespeicherte Liste,
  wie `test_batch`/`test_opensprinkler`.

**Tests** (`TestAManualStopMeasuresFromTheValvesOnReport`; Szenarien aus `dry3-logs/T7.md`; Ergebnis am Elternstand aus
`rev3/evidence.md`, Abschnitt T7)

| # | Test | Entscheidung | Szenario --> erwartet | am Elternstand |
|---|---|---|---|---|
| 1 | `test_a_stop_mid_run_is_measured_from_the_valve_on_report` | (c) | +100 --> Teil-Lauf 100 | grün (fängt seit dry6 die Probe `before-end-books-plan`) |
| 2 | `test_a_valve_reporting_on_after_the_dispatch_is_measured_from_its_report` | (c) | Ein +0,4, Confirm +1, Stopp +100 --> 99,6 | rot |
| 3 | `test_a_stop_before_the_planned_end_is_not_booked_on_an_off_report` | (c)-Pin | Aus +300 gespeichert, Stopp +302 --> Teil-Lauf **302** (nicht 300); Entprellung bei 306 abgelaufen, ein Datensatz | grün |
| 4 | `test_a_stop_just_before_the_planned_end_is_capped_at_the_plan` | (c)-Deckel | Ein +0,4, Confirm +1, Stopp +600,8 (599,8 nach `RUN_STARTED`) --> Teil-Lauf **600** (nicht 599,8, nicht 600,4), Zeitvolumen 600 | rot |
| 5 | `test_a_stop_in_the_grace_after_an_off_report_inside_the_tolerance_completes` | (d) | Aus +597 (Marge 4), Stopp +601 --> **`completed` 597**, Stopp vor dem Datensatz gesendet, Event und Kalibrierprobe je einmal (auf 600) | rot |
| 6 | `test_a_stop_in_the_grace_after_a_late_off_report_completes_on_it` | (d) später Schluss | Aus +601, Stopp +604 --> **`completed` 601**, `seen == [1]`, ein Datensatz, Event einmal | rot |
| 7 | `test_a_stop_in_the_grace_after_an_off_report_beyond_the_tolerance_is_partial` | (d) | Marge 0, Aus +598, Stopp +601 --> Teil-Lauf **598**, kein Event, keine Kalibrierprobe | rot |
| 8 | `test_a_stop_in_the_grace_with_the_valve_still_on_completes_for_the_plan` | (d) Ventil an | +604 --> **`completed`, `actual_s == planned_s == 600`**, Zeitvolumen 600, `seen == [1]` | rot |
| 9 | `test_a_stop_exactly_at_the_planned_end_is_settled_in_the_grace` | Grenze `<` | Stopp genau bei +600 (Ventil an) --> `completed` 600 | rot |
| 10 | `test_a_stop_all_in_the_grace_settles_the_run_the_same_way` | Stop-all | Aus +601, `async_stop_all_zones()` bei +604 --> `completed` 601, `seen == [1]` | rot |
| 11 | `test_a_completing_stop_books_exactly_what_the_watcher_would` | (d)-Zwilling | derselbe späte Schluss einmal über die Entprellung, einmal über einen Stopp bei +604, gemessener Durchfluss 90 L. Gleich müssen sein: Datensatz, Eimer-Schreibungen, Zähler-Aufrufe, gelerntes Zonen-Update, Stempel, Events, Kalibrierprobe, aufgeschobene Berechnung, freigegebene Tokens | rot |
| 12 | `test_the_watchers_own_partial_keeps_its_observed_start` | (b) × T7 | Ein +0,4, Confirm +1, `unavailable` +300, `off` +302 (nicht gespeichert), Entscheidung +308 --> Teil-Lauf **307** (ab `RUN_OBSERVED_START`), nicht 307,6 | grün |
| 13 | `test_a_write_only_run_keeps_the_elapsed_since_its_start` | sonst | unverändert, letzter Test der Klasse | grün (fängt seit dry6 die Probe `else-books-plan`) |

**Nachvollzug** (Verfahren im Kopfteil; bei jeder Abweichung von RED oder GREEN: STOPP, nicht committen, melden)

- [ ] **Step 1: Ausgangslage prüfen, Tests auschecken, RED**

```bash
cd D:/Entwicklung/HASI/HAsmartirrigation
mkdir -p D:/Entwicklung/HASI/pr139-work/tmp D:/Entwicklung/HASI/pr139-work/npm-cache && export TEMP=D:/Entwicklung/HASI/pr139-work/tmp TMP=D:/Entwicklung/HASI/pr139-work/tmp TMPDIR=D:/Entwicklung/HASI/pr139-work/tmp npm_config_cache=D:/Entwicklung/HASI/pr139-work/npm-cache
SRC=f1266999
TESTS="tests/test_service_watch.py"
git branch --show-current                 # fix/backstop-grace
git log -1 --format=%s                    # feat(run-watch): settle a confirmed service run on its valve window
git status --short                        # nur: ?? docs/SESSION-STAND.md
git diff "$SRC^" --stat                   # leer: der Baum ist der von T5 auf dry6
git checkout "$SRC" -- $TESTS
L=D:/Entwicklung/HASI/pr139-work/replay/T07-red.txt
D:/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest $TESTS -p _local_socket_unblock -q --tb=line -rfE -p no:cacheprovider > $L 2>&1
grep -E "^collected |^(FAILED|ERROR) |^E  |\.py:[0-9]+: " $L; tail -n 1 $L
```

Erwartet (wörtlich aus `rev3/evidence.md`, T7, gemessen auf dry6). Die Pfade dort zeigen auf den Worktree `dry2`; hier
steht `D:\Entwicklung\HASI\HAsmartirrigation\`. Die Laufzeit schwankt. Das `�` ist `±` aus `pytest.approx`, falsch
dargestellt von der Windows-Konsole.

```
collected 59 items
FAILED tests/test_service_watch.py::TestAManualStopMeasuresFromTheValvesOnReport::test_a_valve_reporting_on_after_the_dispatch_is_measured_from_its_report
FAILED tests/test_service_watch.py::TestAManualStopMeasuresFromTheValvesOnReport::test_a_stop_just_before_the_planned_end_is_capped_at_the_plan
FAILED tests/test_service_watch.py::TestAManualStopMeasuresFromTheValvesOnReport::test_a_stop_in_the_grace_after_an_off_report_inside_the_tolerance_completes
FAILED tests/test_service_watch.py::TestAManualStopMeasuresFromTheValvesOnReport::test_a_stop_in_the_grace_after_a_late_off_report_completes_on_it
FAILED tests/test_service_watch.py::TestAManualStopMeasuresFromTheValvesOnReport::test_a_stop_in_the_grace_after_an_off_report_beyond_the_tolerance_is_partial
FAILED tests/test_service_watch.py::TestAManualStopMeasuresFromTheValvesOnReport::test_a_stop_in_the_grace_with_the_valve_still_on_completes_for_the_plan
FAILED tests/test_service_watch.py::TestAManualStopMeasuresFromTheValvesOnReport::test_a_stop_exactly_at_the_planned_end_is_settled_in_the_grace
FAILED tests/test_service_watch.py::TestAManualStopMeasuresFromTheValvesOnReport::test_a_stop_all_in_the_grace_settles_the_run_the_same_way
FAILED tests/test_service_watch.py::TestAManualStopMeasuresFromTheValvesOnReport::test_a_completing_stop_books_exactly_what_the_watcher_would
ERROR tests/test_service_watch.py::TestOneOffSampleIsNotEvidenceTheWaterStopped::test_the_run_is_not_settled_before_the_window_is_out
ERROR tests/test_service_watch.py::TestAManualStopMeasuresFromTheValvesOnReport::test_a_stop_in_the_grace_after_an_off_report_inside_the_tolerance_completes
ERROR tests/test_service_watch.py::TestAManualStopMeasuresFromTheValvesOnReport::test_a_stop_in_the_grace_after_a_late_off_report_completes_on_it
ERROR tests/test_service_watch.py::TestAManualStopMeasuresFromTheValvesOnReport::test_a_stop_in_the_grace_after_an_off_report_beyond_the_tolerance_is_partial
ERROR tests/test_service_watch.py::TestAManualStopMeasuresFromTheValvesOnReport::test_a_stop_all_in_the_grace_settles_the_run_the_same_way
=================== 9 failed, 50 passed, 5 errors in 5.07s ====================
```

Assertions in dieser Reihenfolge; in Klammern die Zuordnung zu den Tests:

```
D:\Entwicklung\HASI\pr139-work\dry2\tests\test_service_watch.py:1055: assert 99.0 == 99.6 � 1.0e-02
D:\Entwicklung\HASI\pr139-work\dry2\tests\test_service_watch.py:1123: assert 599.8 == 600
D:\Entwicklung\HASI\pr139-work\dry2\tests\test_service_watch.py:1151: AssertionError: assert 'partial' == 'completed'
D:\Entwicklung\HASI\pr139-work\dry2\tests\test_service_watch.py:1194: AssertionError: assert 'partial' == 'completed'
D:\Entwicklung\HASI\pr139-work\dry2\tests\test_service_watch.py:1228: assert 601.0 == 598 � 1.0e-02
D:\Entwicklung\HASI\pr139-work\dry2\tests\test_service_watch.py:1264: AssertionError: assert 'partial' == 'completed'
D:\Entwicklung\HASI\pr139-work\dry2\tests\test_service_watch.py:1290: AssertionError: assert 'partial' == 'completed'
D:\Entwicklung\HASI\pr139-work\dry2\tests\test_service_watch.py:1314: AssertionError: assert 'partial' == 'completed'
D:\Entwicklung\HASI\pr139-work\dry2\tests\test_service_watch.py:1364: AssertionError: assert {'bucket': [c...hed': [], ...} == {'bucket': [c...': 2}]}], ...}
```

Zuordnung der Zeilen:
- 1055: späte Ein-Meldung;
- 1123: Deckel (der Elternstand misst ab `RUN_OBSERVED_START`);
- 1151, 1194, 1264, 1290, 1314: in der Toleranz, später Schluss, Ventil an, genau am Ende, Stop-all (der Elternstand
  bucht `partial`);
- 1228: jenseits der Toleranz (der Elternstand misst bis zum Stopp: 601 statt 598);
- 1364: Zwilling.

(Dieselben FAILED und ERROR wie auf dry5; 59 statt 57 Items durch die neuen Tests in T3 und T5, die Zeilen um 107
verschoben.)

Die Errors: 1 vorbestehender Lingering timer plus 4 Teardown-Errors der abgebrochenen Tests (`_decide` der Entprellung,
Muster wie in T4). Am Elternstand grün sind 4 der 13 Tests: Nr. 1, 3, 12, 13, also die Pins unveränderten Verhaltens.

- [ ] **Step 2: Produktivcode auschecken, GREEN, 7 Service-Suiten**

```bash
cd D:/Entwicklung/HASI/HAsmartirrigation
mkdir -p D:/Entwicklung/HASI/pr139-work/tmp D:/Entwicklung/HASI/pr139-work/npm-cache && export TEMP=D:/Entwicklung/HASI/pr139-work/tmp TMP=D:/Entwicklung/HASI/pr139-work/tmp TMPDIR=D:/Entwicklung/HASI/pr139-work/tmp npm_config_cache=D:/Entwicklung/HASI/pr139-work/npm-cache
SRC=f1266999
TESTS="tests/test_service_watch.py"
PROD="custom_components/irrigation_plus/self_closing.py"
PY=D:/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe
git checkout "$SRC" -- $PROD
$PY -m pytest $TESTS -p _local_socket_unblock -q --tb=line -rfE -p no:cacheprovider > D:/Entwicklung/HASI/pr139-work/replay/T07-green.txt 2>&1
grep -E "^collected " D:/Entwicklung/HASI/pr139-work/replay/T07-green.txt; tail -n 1 D:/Entwicklung/HASI/pr139-work/replay/T07-green.txt
$PY -m pytest tests/test_service_watch.py tests/test_finish_grace_helpers.py tests/test_run_in_flight.py tests/test_confirm_reserve.py tests/test_self_closing.py tests/test_run_watch.py tests/test_observed_watering.py tests/test_i18n_completeness.py -p _local_socket_unblock -q -p no:cacheprovider --tb=line -rfE > D:/Entwicklung/HASI/pr139-work/replay/T07-suites.txt 2>&1
grep -E "^(FAILED|ERROR) | passed" D:/Entwicklung/HASI/pr139-work/replay/T07-suites.txt | sed 's/ - .*//'
```

Erwartet. Die Testdatei laut `rev3/evidence.md`, die sieben Suiten plus i18n laut `dry6-logs/percommit.md`:

```
collected 59 items
========================= 59 passed, 1 error in 5.04s =========================
```

```
ERROR tests/test_service_watch.py::TestOneOffSampleIsNotEvidenceTheWaterStopped::test_the_run_is_not_settled_before_the_window_is_out
======================== 282 passed, 1 error in 18.65s ========================
```

- [ ] **Step 3: Lint und Baumvergleich**

```bash
cd D:/Entwicklung/HASI/HAsmartirrigation
SRC=f1266999
uvx black --check custom_components/irrigation_plus/ $(git diff --name-only 2b2c403b -- tests)
uvx ruff check custom_components/irrigation_plus/
git diff "$SRC" --stat
git diff --cached "$SRC" --stat
```

Erwartet (`scratch/dry5-checks.log`, am Commit `bcae641c`; dieselbe Dateimenge auf dry6, ruff dort sauber laut
`dry6-logs/percommit.md`): `72 files would be left unchanged.` und `All checks passed!`. Die 72 sind die 68 Dateien in
`custom_components/irrigation_plus/` plus die 4 bis hierher berührten Testdateien. Beide Diffs sind leer.

- [ ] **Step 4: Commit mit derselben Nachricht**

```bash
cd D:/Entwicklung/HASI/HAsmartirrigation
SRC=f1266999
git log -1 --format=%B "$SRC" | git commit -q -F -
test "$(git rev-parse HEAD^{tree})" = "$(git rev-parse "$SRC^{tree}")" && echo TREE-SAME
diff <(git log -1 --format=%B HEAD) <(git log -1 --format=%B "$SRC") && echo MSG-SAME
git log -1 --format=%B | grep -c '^#'     # 0
git show --stat --format= HEAD | tail -1  # 2 files changed, 510 insertions(+), 6 deletions(-)
git diff "$SRC" HEAD --stat               # leer
git log --oneline -1                      # neuer SHA, Betreff des Tasks
git status --short                        # nur: ?? docs/SESSION-STAND.md
```

**Mutationsproben (Probelauf)**

Die Proben stammen aus `dry3-logs/T7.md` und `T7-probes-table.md` (Rohdaten `T7-probes.txt`). Das Skript ist
`D:/Entwicklung/HASI/pr139-work/mut/dry3_t7_probes.py {worktree} {out-file} [probe ...]`: je Probe eine
Suchen/Ersetzen-Stelle mit CRLF, Sicherung `mut/dry3-T7-{probe}.bak`, Wiederherstellung mit SHA-256-Prüfung. Getestet
wird `tests/test_service_watch.py`; `grace-gate-dropped` läuft über die 7 Suiten plus `test_opensprinkler`, `test_batch`,
`test_credit_ceiling` und `test_stop_zone`.

Die Änderungszeilen von T7 sind auf `dry5` (und damit `dry6`, gleicher Produktivcode) dieselben wie auf `dry3`. Beide
Stände unterscheiden sich in den T7-Dateien nur um die T3b-Zeilen: 20 Zeilen `self_closing.py` und die 2 T3b-Tests
(`git diff 5e30fecf bcae641c -- custom_components/irrigation_plus/self_closing.py tests/test_service_watch.py`; ohne
Pfadfilter zeigt der Diff zusätzlich die ganze #146-Basisänderung und das Entfernen von `zone_finish_grace_seconds`,
38 Dateien). Alle 21 Suchtexte kommen auf `dry5` genau einmal vor (geprüft am 19.09. bei der
Planerstellung), auf `dry6` ebenso (19.09. abends, lesend). Die Zählungen passed/errors aus `dry3` gelten nicht, weil
`tests/test_service_watch.py` dort andere Tests hatte. Hier stehen deshalb nur die fangenden Tests und die Meldungen. In
der Schlussprüfung (Task 13) laufen alle Proben erneut, mit `{worktree}` = `D:/Entwicklung/HASI/HAsmartirrigation`.

| Probe | Mutation in `self_closing.py` | gefangen von (dry3) |
|---|---|---|
| end-inverted | `… RUN_STARTED)) < planned:` --> `>= planned:` | 9: alle (c)/(d)-Tests außer den beiden unveränderten Ankern; `300.0 == 302`, `'completed' == 'partial'`, `'partial' == 'completed'`, `600.0 == 598`, Zwilling |
| end-removed-always-before | Bedingung --> `if True:` | 7: jeder Test nach dem Ende (`'partial' == 'completed'`, `600.0 == 598`, Zwilling) |
| end-removed-always-after | Bedingung --> `if False:` | 2: Pin vor dem Ende (`300.0 == 302`), Deckel knapp davor (`'completed' == 'partial'`) |
| end-lte | `< planned` --> `<= planned` | 1: `exactly_at_the_planned_end` (`'partial' == 'completed'`) |
| end-anchored-on-valve-on | Bedingung auf `RUN_VALVE_ON` statt `RUN_STARTED` | 1: `just_before_the_planned_end` (`'completed' == 'partial'`) |
| before-uses-stored-off | (c) `_watch_valve_window({**run, RUN_VALVE_OFF: None})` --> `_watch_valve_window(run)` | 1: Pin vor dem Ende (`300.0 == 302`) |
| before-uncapped | (c) --> `_sc_elapsed(run.get(RUN_VALVE_ON))` | 1: Deckel (`600.4 == 600`) |
| before-from-observed-start | (c) --> `_sc_run_elapsed(run)` | 2: `99.0 == 99.6`, `599.8 == 600` |
| tolerance-ignored | `elapsed + run_completion_tolerance(run) >= planned` --> `elapsed >= planned` | 1: in der Toleranz (`'partial' == 'completed'`) |
| tolerance-one-second | --> `elapsed + 1 >= planned` | 1: dieselbe |
| completed-branch-dropped | --> `if False:` (immer Teil-Lauf) | 6: in der Toleranz, später Schluss, Ventil an, genau am Ende, Stop-all, Zwilling |
| always-completed | --> `if True:` | 1: jenseits der Toleranz (`'completed' == 'partial'`) |
| finish-without-actual-s | `_sc_finish_run(zone_id, actual_s=elapsed)` --> `_sc_finish_run(zone_id)` | 4: `600.0 == 597`, `600.0 == 601` (später Schluss, Stop-all), Zwilling |
| no-return-after-finish | `return True` entfernt (der Stopp fällt in den Teil-Lauf-Code) | 6: jeder abschließende Test (`'partial' == 'completed'` auf dem zweiten Datensatz), Zwilling |
| after-ignores-stored-off | (d) Fenster ohne `RUN_VALVE_OFF` | 5: `600.0 == 597`, `600.0 == 601`, jenseits der Toleranz `'completed' == 'partial'`, Stop-all, Zwilling |
| after-measured-to-stop | (d) --> `_sc_elapsed(run.get(RUN_VALVE_ON))` | 6: `601.0 == 597`, `604.0 == 601`, `'completed' == 'partial'`, `604.0 == 600.0`, Stop-all, Zwilling |
| valve-not-closed-when-past-end | `if close_valve:` --> `if close_valve and not (…nach dem Ende…):` | 4: `assert [0] == [1]` in: in der Toleranz, später Schluss, Ventil an, Stop-all |
| settle-before-close | abschließende Abrechnung vor den Schließ-Block gesetzt | 4: `assert [0] == [1]` (dieselben vier) |
| close-valve-gate-dropped | `elif close_valve and run_has_finish_grace(run):` --> `elif run_has_finish_grace(run):` | 1: Watcher-Teil-Lauf-Pin (`307.6 == 307`) |
| grace-gate-dropped | --> `elif close_valve:` (Fenster für jeden manuellen Stopp) | 4, nur bestehende Tests (T7s eigene bleiben grün, write-only fällt auf `RUN_STARTED` zurück): `test_self_closing.py::test_stop_calls_stop_service_and_corrects_bucket`, `::test_stop_without_stop_service_corrects_accounting_only` (`IndexError`), `::test_self_closing_early_stop_bucket_reconciles_from_pre_bucket` (`0.0 == 15.0`), `test_credit_ceiling.py::test_a_short_run_is_still_corrected_down_by_the_stop` (`0.0 == -2.5`) |
| branch-reverted | --> `elif False:` (Verhalten des Elternstands) | 9 (= RED gegen den Elternstand) |

Ergebnis: 21 Proben, 21 gefangen, 0 äquivalent, 0 überlebend.

**Dazu dry6** (19.09. abends, am Endstand `70dc0c18`, Lauf über die 7 Service-Suiten; `dry6-logs/probes.md`). Zwei neue
Tests fing bis dahin keine der 21 Proben: Nr. 1 (Stopp mitten im Lauf) und Nr. 13 (write-only). In Task 13 laufen beide
im Treiber-Satz `t07add` auf `tests/test_service_watch.py` (ohne Mutation auf dry6 `69 passed, 1 error`).

| Probe | Mutation in `self_closing.py` | Beobachtet (dry6) |
|---|---|---|
| before-end-books-plan | (c): `elapsed = self._watch_valve_window({**run, const.RUN_VALVE_OFF: None})` --> `elapsed = planned` | FAIL 3: Nr. 1 (`600.0 == 100`), Nr. 2 (`600.0 == 99.6`), Nr. 3 (`600.0 == 302`) |
| else-books-plan | letzter Zweig: `elapsed = self._sc_run_elapsed(run)` --> `elapsed = planned` (Suchtext mit `else:` davor und `delivered_frac` danach) | FAIL 8: Nr. 12 (`600.0 == 307`), Nr. 13 (`600.0 == 100`), T5 `off_after_an_unavailable_mid_run_keeps_the_old_rule` (`600.0 == 308`) und `seven_seconds_early_stays_partial` (`600.0 == 598`), T8 `found_off_mid_run` (`600.0 == 205`), drei Tests in `tests/test_self_closing.py` |

Damit T7: 23 Proben, 23 gefangen; jeder der 13 Tests scheitert an mindestens einer.

Zusatz: T5s überlebende Probe `base-partial-passes-window` (`run_watch.py`, Teil-Lauf des Watchers mit
`actual_s=self._watch_valve_window(run)`) wird ab T7 gefangen, und zwar von
`test_the_watchers_own_partial_keeps_its_observed_start` mit `assert 307.6 == 307 ± 1.0e-02`
(`dry3-logs/T7-t5probe-rerun.txt`).

---

### Task 8: Ein Neustart übernimmt die Wartezeit

**dry6:** `4819d2fc` (dry5: `09aba7a4`), `feat(service): carry the finish grace across a restart`
(`2 files changed, 360 insertions(+), 5 deletions(-)`; dry5: +375, weil dort `_the_real_backstop_from_here` noch hier
stand). **Elternstand auf dry6:** `f1266999` (T7).

**Files**
- TEST: `tests/test_service_watch.py`. Neu sind die Modul-Helfer `_ha_goes_down` und `_ha_comes_back`, dazu die Klasse
  `TestARestartCarriesTheFinishGrace` (10 Tests) am Dateiende. Der SP-3-Test benutzt `_the_real_backstop_from_here`,
  der seit dry6 in T3 definiert ist; an der einen Aufrufstelle steht der frühere Docstring-Hinweis als Kommentar
  („the restart arms the only real timer“). T9 importiert den Helfer ebenfalls.
- PROD: `custom_components/irrigation_plus/self_closing.py`, Service-Zweig von `async_resume_self_closing_runs`.
- Läuft unverändert mit: `tests/test_self_closing.py::test_resume_finalises_overdue_and_reschedules_partial`
  (Pin `(2, 500.0)`).

**Was und warum**

Der Neustart-Abgleich rechnete mit der alten Formel. Nach dem Plan wurde der Lauf für den Plan abgeschlossen, im Plan
wurde der Backstop auf `planned − elapsed` gestellt. Ein Neustart in der Wartezeit hätte den Lauf abgerechnet, bevor ein
später Schluss gesehen werden konnte. Genau diesen Fehler soll die Wartezeit beheben. Deshalb zählt jetzt
`grace = run_finish_grace_seconds(run)` mit; für jeden Datensatz ohne eingefrorene Marge (write-only, von vor dem Update)
ist das 0, also die alte Formel. `elapsed` wird wie bisher ab `RUN_STARTED` gemessen, Ausfallzeit eingeschlossen.
Denselben Pfad nimmt das Neuladen des Config-Entrys.

| Zustand | Verhalten |
|---|---|
| `elapsed >= planned + grace` | sofort `_sc_finish_run(zone_id)`: `completed`, `actual_s = planned_s`, **egal was gespeichert ist** (a); kein Master, kein Backstop, kein Watcher |
| `planned <= elapsed < planned + grace` | **kein** `async_master_acquire` (f); Backstop auf `planned + grace − elapsed`; Watcher neu aufnehmen |
| `elapsed < planned` | Master-Hold neu nehmen (wie bisher); Backstop auf `planned + grace − elapsed`; Watcher neu aufnehmen |

- **Warum die Schwelle `planned + grace` (SP-2).** Beim Neuladen des Config-Entrys bleibt der Backstop-Timer des alten
  Koordinators stehen, fällig bei `planned + grace`: `async_unload` bricht `_sc_cleanup_handles` nicht ab
  (vorbestehender Befund, Spec). Endete der Datensatz beim Neuladen schon bei `planned`, wäre die Zone bis zu 9 s „frei“.
  Der alte Timer könnte dann einen in dieser Lücke gestarteten Lauf derselben Zone abrechnen, denn `_sc_finish_run` sucht
  nur nach `zone_id`. Die Schwelle hält den Datensatz und damit den Wächter aus T9 bis zum Ende der Wartezeit.
- **(a) nach der Wartezeit.** Das gilt auch mit gespeicherter `RUN_VALVE_OFF`: der Lauf wird für den Plan abgeschlossen,
  wie heute. Es ist der Neustart-Zwilling von #3/T6, denn auch der Backstop schließt einen solchen Lauf für den Plan ab.
  Auf dem Fenster abzurechnen würde nur einen Datensatz verbessern, den die Wartezeit nicht verschlechtert. Bekannt und
  bewusst unverändert; ein Test pinnt es (+700).
- **(f) Neustart in der Wartezeit ohne Master-Anforderung.** Der eigene Countdown des Ventils ist vorbei. Ein neuer Hold
  würde die Pumpe einschalten, sie ggf. kicken und das Master-Settle abwarten (Default 10 s), alles für ein schon
  geschlossenes Ventil. Heute beendet dieser Neustart den Lauf und startet die Pumpe nie.
  - JustChr am 19.09.: „Please pin it with a test that asserts the master is not requested“. Das tun die Tests +600
    (Grenze), +602, +604 ×3, dazu +609 und beide +700-Tests (mit und ohne gespeicherte Aus-Meldung), jeweils mit
    `async_master_acquire.assert_not_awaited()`.
  - Vor dem Ende (+100, +200) wird der Hold wie bisher genau einmal genommen.
  - Wenn der Lauf später abgerechnet wird, gibt `_sc_finish_run` ein nicht gehaltenes Token frei (`holds.discard`), wie
    beim Sofort-Abschluss schon immer.
  - Unterschied zum live laufenden Lauf: der behält seinen Dispatch-Hold bis zum Abschluss. Das ist gewollt und im
    PR-Text unter „Behaviour changes not behind the setting“, Punkt „Pump hold“, genannt.
- **Neu aufgenommener Watcher (b).** Zwei Fälle speichern keine Aus-Meldung, weil `last_changed` dann die Rückkehr der
  Entität ist und nicht der Schluss: ein beim Neuaufnehmen schon „aus“ gefundenes Ventil und `unavailable --> off`.
  Solche Läufe rechnen wie jeder unberichtete Schluss ab (`_watch_finish`, Basisregel).
  - Eine vor dem Ausfall gespeicherte Aus-Meldung bleibt im Datensatz und rechnet auf ihrem Fenster ab, wenn die
    Entprellung vor dem neu gestellten Backstop entscheidet.
  - Die frühere Formulierung „bounded window min(now − anchor, planned)“ (E4) ist aus Kommentar und Tests entfernt.
- **SP-3 mit dem echten Backstop, Neustart bei +602.** Der Test mit gespeicherter Aus-Meldung läuft so ab: Aus +601,
  „HA weg“ vor der Entprellung (fällig 606), Neustart +602.
  - `_the_real_backstop_from_here(c)` löscht `_coord`s Doubles `_sc_schedule_cleanup`/`_sc_cancel_cleanup` und hüllt den
    echten `_sc_schedule_cleanup` in `Mock(wraps=...)`. Der Arm-Wert `(2, 7.0)` (609 − 602) bleibt so prüfbar, und der
    Timer feuert wirklich.
  - Die Entprellung ist bei 607 fällig, der Backstop bei 609. Ein Vorstellen auf 608 liefert `completed` mit
    `actual_s ≈ 601`; der Timer ist mit dem Lauf weg.
  - **Warum der echte Timer:** mit dem Double könnte der Test nicht zeigen, dass die Entprellung den Backstop wirklich
    schlägt, und genau diese Reihenfolge ist der Kern von SP-3.
  - **Warum +602:** ab +604 (= `planned` + Marge) wird der Backstop auf höchstens die Entprellung gestellt, und zwar vor
    ihr. In Produktion feuert der zuerst gestellte Backstop und schließt für den Plan ab. Bei genau +604 sind im Harness
    beide Timer zum selben eingefrorenen Zeitpunkt (609) fällig, und das Ergebnis ist nicht deterministisch: auf `dry3`
    scheiterte derselbe Test mit Neustart bei +604 mit `assert 600.0 == 601 ± 1.0e-02`
    (`dry3-logs/T8-sp3-restart-at-604.txt`), auf `tmp/drop-6-10` ergab dieselbe Variante 601 (3 von 3 Läufen,
    `wf-scope-answer.json`). Eine Assertion an diesem Gleichstand pinnt keine Eigenschaft (Spec, „Verworfen“). Bei +602
    liegen 2 s zwischen den beiden Fälligkeiten; `async_fire_time_changed` feuert bis 0,5 s zu früh.
- **Docstring der Klasse.** Mit dem Backstop-Double sehen die übrigen Tests die Entscheidung des Watchers auch dort, wo
  in Wirklichkeit der Backstop zuerst käme. Ohne Aus-Meldung rechnen beide gleich ab, für den Plan. Belegt: die beiden
  +604-Tests ohne Aus-Meldung bestehen unverändert mit dem echten Backstop, `2 passed`
  (`dry3-logs/T8-real-backstop-no-off.txt`).
- **Write-only-Pin unverändert.** Ohne Marge ist `grace` 0, und im `else` gilt immer `elapsed < planned`. Der Hold
  bleibt, der Arm-Wert `(2, 500.0)` bleibt.

**Tests** (`TestARestartCarriesTheFinishGrace`; Szenarien aus `dry3-logs/T8.md`; Elternstand aus `rev3/evidence.md`)

| # | Test | Punkt | Szenario --> erwartet | am Elternstand |
|---|---|---|---|---|
| 1 | `test_a_run_inside_its_window_re_arms_the_backstop_with_the_grace` | Re-Arm, (f) | +100 --> Backstop `(2, 509.0)`, Master einmal | rot |
| 2 | `test_a_restart_exactly_at_the_plan_takes_no_master_hold` | (f)-Grenze | +600 --> kein Master, `(2, 9.0)`, Watcher neu, nichts gebucht | rot |
| 3 | `test_a_restart_inside_the_grace_does_not_finish_a_valve_still_on` | (f) | +604, Ventil an --> `(2, 5.0)`, Lauf bleibt, Watcher neu, kein Master | rot |
| 4 | `test_a_valve_found_off_inside_the_grace_completes_for_its_plan` | (b), (f) | +604 aus gefunden --> Entscheidung bei 610, `actual_s == planned_s == 600`, kein Master | rot |
| 5 | `test_a_valve_back_from_unavailable_completes_for_its_plan` | (b), (f) | +604 `unavailable`, `off` +606 --> Entscheidung bei 612, `completed` 600 (nicht 606), kein Master | rot |
| 6 | `test_a_valve_found_off_mid_run_is_a_partial_up_to_the_decision` | (b), (f) | +200 aus gefunden (Aus +150) --> Teil-Lauf 205, Eimer −20 + 20·205/600, `(2, 409.0)`, Master einmal | rot |
| 7 | `test_a_stored_off_report_inside_the_grace_settles_on_its_window` | SP-3 | Aus +601, Neustart +602, echter Backstop `(2, 7.0)` --> `completed` 601, Timer weg, kein Master | rot |
| 8 | `test_a_restart_exactly_at_the_end_of_the_grace_finishes_the_run` | Schwellen-Grenze | +609 --> sofort abgeschlossen, 600, kein Backstop/Watcher/Master | grün |
| 9 | `test_a_stored_off_report_past_the_grace_is_finished_for_the_plan` | (a)-Pin | Aus +601, Neustart +700 --> `actual_s == planned_s == 600` | grün |
| 10 | `test_no_off_report_past_the_grace_completes_for_the_plan_at_once` | (a), (f) | +700 ohne Aus-Meldung --> 600, kein Master | grün |

**Nachvollzug**

- [ ] **Step 1: Ausgangslage prüfen, Tests auschecken, RED**

```bash
cd D:/Entwicklung/HASI/HAsmartirrigation
mkdir -p D:/Entwicklung/HASI/pr139-work/tmp D:/Entwicklung/HASI/pr139-work/npm-cache && export TEMP=D:/Entwicklung/HASI/pr139-work/tmp TMP=D:/Entwicklung/HASI/pr139-work/tmp TMPDIR=D:/Entwicklung/HASI/pr139-work/tmp npm_config_cache=D:/Entwicklung/HASI/pr139-work/npm-cache
SRC=4819d2fc
TESTS="tests/test_service_watch.py"
git log -1 --format=%s                    # feat(service): measure a manual stop on the valve's own window
git status --short                        # nur: ?? docs/SESSION-STAND.md
git diff "$SRC^" --stat                   # leer: der Baum ist der von T7 auf dry6
git checkout "$SRC" -- $TESTS
L=D:/Entwicklung/HASI/pr139-work/replay/T08-red.txt
D:/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest $TESTS -p _local_socket_unblock -q --tb=line -rfE -p no:cacheprovider > $L 2>&1
grep -E "^collected |^(FAILED|ERROR) |^E  |\.py:[0-9]+: " $L; tail -n 1 $L
```

Erwartet (wörtlich aus `rev3/evidence.md`, T8, gemessen auf dry6):

```
collected 69 items
FAILED tests/test_service_watch.py::TestARestartCarriesTheFinishGrace::test_a_run_inside_its_window_re_arms_the_backstop_with_the_grace
FAILED tests/test_service_watch.py::TestARestartCarriesTheFinishGrace::test_a_restart_exactly_at_the_plan_takes_no_master_hold
FAILED tests/test_service_watch.py::TestARestartCarriesTheFinishGrace::test_a_restart_inside_the_grace_does_not_finish_a_valve_still_on
FAILED tests/test_service_watch.py::TestARestartCarriesTheFinishGrace::test_a_valve_found_off_inside_the_grace_completes_for_its_plan
FAILED tests/test_service_watch.py::TestARestartCarriesTheFinishGrace::test_a_valve_back_from_unavailable_completes_for_its_plan
FAILED tests/test_service_watch.py::TestARestartCarriesTheFinishGrace::test_a_valve_found_off_mid_run_is_a_partial_up_to_the_decision
FAILED tests/test_service_watch.py::TestARestartCarriesTheFinishGrace::test_a_stored_off_report_inside_the_grace_settles_on_its_window
ERROR tests/test_service_watch.py::TestOneOffSampleIsNotEvidenceTheWaterStopped::test_the_run_is_not_settled_before_the_window_is_out
ERROR tests/test_service_watch.py::TestARestartCarriesTheFinishGrace::test_a_valve_found_off_mid_run_is_a_partial_up_to_the_decision
=================== 7 failed, 62 passed, 2 errors in 5.99s ====================
```

```
C:\Users\Nutzer\AppData\Local\Programs\Python\Python312\Lib\unittest\mock.py:944: AssertionError: expected call not found.
C:\Users\Nutzer\AppData\Local\Programs\Python\Python312\Lib\unittest\mock.py:955: AssertionError: Expected 'mock' to be called once. Called 0 times.
D:\Entwicklung\HASI\pr139-work\dry2\tests\test_service_watch.py:1543: assert None is not None
D:\Entwicklung\HASI\pr139-work\dry2\tests\test_service_watch.py:1570: assert None is not None
D:\Entwicklung\HASI\pr139-work\dry2\tests\test_service_watch.py:1603: assert None is not None
C:\Users\Nutzer\AppData\Local\Programs\Python\Python312\Lib\unittest\mock.py:944: AssertionError: expected call not found.
D:\Entwicklung\HASI\pr139-work\dry2\tests\test_service_watch.py:1682: TypeError: 'NoneType' object is not subscriptable
```

(Dieselben FAILED und ERROR wie auf dry5; 69 statt 67 Items, 62 statt 60 passed durch die neuen Tests in T3 und T5.)

Zuordnung der Zeilen in derselben Reihenfolge; die Details aus der Langfassung stehen in `dry3-logs/T8.md`, RED gegen
den Elternstand:
- +100: `Expected: mock(2, 509.0)`, `Actual: mock(2, 500.0)`;
- +600: der Backstop wird nie gestellt, weil der Elternstand sofort abschließt;
- +604 an, +604 aus gefunden, +604 `unavailable`: der Lauf ist schon weg;
- +200: `Expected: mock(2, 409.0)`, `Actual: mock(2, 400.0)`;
- +602 mit gespeicherter Aus-Meldung: der Lauf ist weg.

Die 2 Errors sind der vorbestehende Lingering timer und der Teardown-Error des abgebrochenen +200-Tests. Am Elternstand
grün sind 3 der 10 Tests: Nr. 8, 9, 10, denn der Elternstand schließt jeden Lauf nach dem Plan sofort für den Plan ab.

- [ ] **Step 2: Produktivcode auschecken, GREEN, 7 Service-Suiten**

```bash
cd D:/Entwicklung/HASI/HAsmartirrigation
mkdir -p D:/Entwicklung/HASI/pr139-work/tmp D:/Entwicklung/HASI/pr139-work/npm-cache && export TEMP=D:/Entwicklung/HASI/pr139-work/tmp TMP=D:/Entwicklung/HASI/pr139-work/tmp TMPDIR=D:/Entwicklung/HASI/pr139-work/tmp npm_config_cache=D:/Entwicklung/HASI/pr139-work/npm-cache
SRC=4819d2fc
TESTS="tests/test_service_watch.py"
PROD="custom_components/irrigation_plus/self_closing.py"
PY=D:/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe
git checkout "$SRC" -- $PROD
$PY -m pytest $TESTS -p _local_socket_unblock -q --tb=line -rfE -p no:cacheprovider > D:/Entwicklung/HASI/pr139-work/replay/T08-green.txt 2>&1
grep -E "^collected " D:/Entwicklung/HASI/pr139-work/replay/T08-green.txt; tail -n 1 D:/Entwicklung/HASI/pr139-work/replay/T08-green.txt
$PY -m pytest tests/test_service_watch.py tests/test_finish_grace_helpers.py tests/test_run_in_flight.py tests/test_confirm_reserve.py tests/test_self_closing.py tests/test_run_watch.py tests/test_observed_watering.py tests/test_i18n_completeness.py -p _local_socket_unblock -q -p no:cacheprovider --tb=line -rfE > D:/Entwicklung/HASI/pr139-work/replay/T08-suites.txt 2>&1
grep -E "^(FAILED|ERROR) | passed" D:/Entwicklung/HASI/pr139-work/replay/T08-suites.txt | sed 's/ - .*//'
```

Erwartet (`rev3/evidence.md`; `dry6-logs/percommit.md`):

```
collected 69 items
========================= 69 passed, 1 error in 5.92s =========================
```

```
ERROR tests/test_service_watch.py::TestOneOffSampleIsNotEvidenceTheWaterStopped::test_the_run_is_not_settled_before_the_window_is_out
======================== 292 passed, 1 error in 19.52s ========================
```

Der Write-only-Pin `tests/test_self_closing.py::test_resume_finalises_overdue_and_reschedules_partial` gehört zu den
292.

- [ ] **Step 3: Lint und Baumvergleich**

```bash
cd D:/Entwicklung/HASI/HAsmartirrigation
SRC=4819d2fc
uvx black --check custom_components/irrigation_plus/ $(git diff --name-only 2b2c403b -- tests)
uvx ruff check custom_components/irrigation_plus/
git diff "$SRC" --stat
git diff --cached "$SRC" --stat
```

Erwartet (`scratch/dry5-checks.log`, `09aba7a4`; dieselbe Dateimenge auf dry6): `72 files would be left unchanged.`,
`All checks passed!`; beide Diffs leer.

- [ ] **Step 4: Commit mit derselben Nachricht**

```bash
cd D:/Entwicklung/HASI/HAsmartirrigation
SRC=4819d2fc
git log -1 --format=%B "$SRC" | git commit -q -F -
test "$(git rev-parse HEAD^{tree})" = "$(git rev-parse "$SRC^{tree}")" && echo TREE-SAME
diff <(git log -1 --format=%B HEAD) <(git log -1 --format=%B "$SRC") && echo MSG-SAME
git log -1 --format=%B | grep -c '^#'     # 0
git show --stat --format= HEAD | tail -1  # 2 files changed, 360 insertions(+), 5 deletions(-)
git diff "$SRC" HEAD --stat               # leer
git log --oneline -1                      # neuer SHA, Betreff des Tasks
git status --short                        # nur: ?? docs/SESSION-STAND.md
```

**Mutationsproben (Probelauf)**

Die Proben stammen aus `dry3-logs/T8.md` (Rohdaten `T8-probes.txt`). Das Skript ist
`D:/Entwicklung/HASI/pr139-work/mut/dry3_t8_probes.py {worktree} {out-file} [probe ...]`. Getestet werden
`tests/test_service_watch.py` und `tests/test_self_closing.py`. Die Änderungszeilen auf `dry5`/`dry6` sind dieselben wie
auf `dry3`, und alle 12 Suchtexte kommen auf `dry5` und `dry6` genau einmal vor (geprüft am 19.09. bzw. 19.09. abends,
lesend). Die Zählungen aus `dry3` gelten
nicht (T3b). In der Schlussprüfung (Task 13) laufen die Proben erneut auf `D:/Entwicklung/HASI/HAsmartirrigation`.

| Probe | Mutation (Service-Zweig des Neustarts) | gefangen von (dry3) |
|---|---|---|
| acquire-in-grace (Pflicht) | `if elapsed < planned:` --> `if True:` | 5: +600, +604 an, +604 aus gefunden, +604 `unavailable`, +602 (`Expected mock to not have been awaited. Awaited 1 times.`) |
| acquire-dropped (Pflicht) | --> `if False:` | 2: +100, +200 (`Expected mock to have been awaited once. Awaited 0 times.`) |
| acquire-lte | --> `if elapsed <= planned:` | 1: +600 (`Awaited 1 times`) |
| stored-off-settle-reintroduced (Pflicht) | Sofort-Abschluss --> das frühere `if grace and run.get(const.RUN_VALVE_OFF): await self._watch_settle_by_window(zone_id, run) else: await self._sc_finish_run(zone_id)` | 1: +700-Pin mit Aus-Meldung (`assert 601.0 == 600.0`) |
| past-grace-finish-on-window | `_sc_finish_run(zone_id)` --> `_sc_finish_run(zone_id, actual_s=self._watch_valve_window(run))` | 2: +700-Pin (`601.0 == 600.0`), `test_self_closing.py::test_resume_finalises_overdue_and_reschedules_partial` (`Expected: mock(1) Actual: mock(1, actual_s=60.0)`) |
| no-finish-past-grace | Sofort-Abschluss --> `pass` | 4: +609, +700 mit Aus, +700 ohne Aus (`assert {...record...} is None`), Write-only-Pin (`awaited 0 times`) |
| threshold-back-to-planned (Pflicht) | `if elapsed >= planned + grace:` --> `if elapsed >= planned:` | 5: +600 (`called 0 times`), +604 ×3 (`assert None is not None`), +602 (`TypeError`) |
| threshold-strict | --> `if elapsed > planned + grace:` | 1: +609 (`assert {...record...} is None`) |
| rearm-without-grace (Pflicht) | `planned + grace - elapsed` --> `planned - elapsed` | 7: `509.0/500.0`, `9.0/0.0`, `5.0/-4.0` (×3), `409.0/400.0`, `7.0/-2.0` |
| grace-reverted | `grace = run_finish_grace_seconds(run)` --> `grace = 0.0` | 7: dieselben sieben |
| grace-for-every-record | --> `grace = float(SERVICE_WATCH_SETTLE_SECONDS + DEFAULT_LATENCY_MARGIN_SECONDS)` | 1: Write-only-Pin (`Expected: mock(2, 500.0) Actual: mock(2, 509.0)`) |
| watcher-not-readopted | `if watch_entity:` (Neuaufnahme) --> `if False:` | 11: 7 dieser Klasse + 4 bestehende: `TestTheWatcherRecordsTheValvesOwnOffReport::test_a_re_adopted_run_does_not_record_the_initial_off`, `::test_a_re_adopted_run_does_not_record_an_off_after_unavailable`, `TestTheSubscriptionSurvivesARestart::test_a_run_still_inside_its_window_is_re_adopted`, `::test_and_it_still_ends_the_run_on_a_valve_off` |

Ergebnis: 12 Proben, 12 gefangen, 0 äquivalent, 0 überlebend. Jeder neue oder geänderte Test fällt unter mindestens einer
Probe (Zuordnung in `dry3-logs/T8.md`, Abschnitt 4). Zwei testseitige Zusatzprüfungen stützen die Docstrings:
`T8-sp3-restart-at-604.txt` (siehe SP-3 oben) und `T8-real-backstop-no-off.txt` (siehe Klassen-Docstring oben).

---

### Task 9: Das In-flight-Fenster trägt die Wartezeit, belegt am Dispatch

**dry6:** `0c0c9416` (dry5: `ed9b2e4f`, Inhalt gleich, nur neuer Elternstand), `feat(service): keep a confirmed run in
flight through its finish grace` (`2 files changed, 291 insertions(+), 2 deletions(-)`). **Elternstand auf dry6:**
`4819d2fc` (T8).

**Files**
- TEST: `tests/test_run_in_flight.py`. Neu sind:
  - der Helfer `_service_run` und die sechs Tests auf Prädikatsebene;
  - der Abschnitt „… not even inside a confirmed run's finish grace (#139)“ mit dem Harness
    `_service_coord_on_its_store`, den Helfern `_valve_opens`, `_into_the_grace`, `_assert_the_first_run_is_untouched`
    und `_settled_by_its_own_backstop` sowie der Klasse `TestASecondDispatchInsideTheFinishGraceIsRefused` (2 Tests);
  - Importe aus `tests.test_service_watch`: `_coord`, `_dispatch`, `_the_real_backstop_from_here` (seit dry6 in T3
    definiert, auf dry5 in T8) und `_zone`, im Stil von `tests/test_finish_anchor_hardware_window.py`.
- PROD: `custom_components/irrigation_plus/run_state.py`. Geändert werden der Import `run_finish_grace_seconds`, der
  Docstring und das Fenster in `_self_closing_run_in_flight`.

Die Dateien sind auf `dry3` (`c83e8980`), `dry5` und `dry6` inhaltsgleich;
`git diff c83e8980 0c0c9416 -- tests/test_run_in_flight.py custom_components/irrigation_plus/run_state.py` ist leer
(geprüft 19.09. abends).

**Was und warum**

- **Das Loch.** `_self_closing_run_in_flight` endete am geplanten Fenster. In der Wartezeit galt die Zone als frei,
  obwohl Datensatz, Watcher und Backstop noch lebten. Ein zweiter Dispatch derselben Zone passierte damit jeden Wächter.
  Dann gibt es zwei Ausgänge:
  - er ersetzt den noch nicht abgerechneten Datensatz;
  - oder der alte Backstop bzw. die alte Entprellung feuert während seiner Confirm-Abfrage und rechnet den alten Lauf mit
    der Pumpen-Freigabe (geteiltes Token `sc:{zone}`) und dem Zähler des neuen ab.

  Eine Berechnung in dieser Zeit wurde auch nicht mehr aufgeschoben. JustChr am 16.09. nannte das „the worst outcome in
  this whole issue“.
- **Neu.** Das nicht warteschlangengebundene Fenster ist `planned + run_finish_grace_seconds(run)`; die queued
  OpenSprinkler-Frist bleibt.
  - Die Wartezeit kommt aus der **eingefrorenen** Marge des Datensatzes, wie beim Backstop, nicht aus der Zone.
  - Der Anker bleibt `RUN_OBSERVED_START` oder `RUN_STARTED`, **nicht** `RUN_VALVE_ON`. Das Fenster darf nicht vor dem
    Backstop enden, und der wird ab `RUN_STARTED` gestellt (Dispatch und Neustart).
  - Der Vergleich bleibt `<`: bei genau `planned + Wartezeit` ist die Zone frei, zeitgleich mit der Fälligkeit des
    Backstops.
  - Write-only, Datensätze von vor dem Update, Batch und OpenSprinkler haben Wartezeit 0 und behalten ihr Fenster.
- **Leser, die mitziehen** (Spec, Design 4):
  - Dispatch-Wächter in `self_closing.py`;
  - `_drop_zones_already_running` (geplant und „Jetzt bewässern“);
  - `run_zone`, Batch;
  - Berechnungs-Aufschub und dessen Wiederholung;
  - Observed-Unterdrückung (`observed_watering.py:138`). Eine Ein-Flanke in der Wartezeit ist damit schon vor dem
    Sperr-Timer unterdrückt; deshalb ist T3b gestrichen (Entscheidung (e)).
- **Garantie am Dispatch.** Darum bat JustChr am 16.09. („surviving-mutation check“) und am 19.09. („including the
  anchor mutation that survived“). Nach einem echten ersten Dispatch unter `freeze_time`, 3 s nach dem geplanten Ende
  (+603, mehr als 1 s von beiden Rändern der 9 s):
  - ein zweites `c.async_run_self_closing(zone, trigger="manual")` gibt `False` zurück;
  - ein `c.async_run_zone(2, 10)` wird vor dem Manuell-Marker abgelehnt.

  In beiden Fällen gilt danach:
  - das Ventil öffnet nicht erneut (`script.irrigation_beet` einmal, über `EVENT_CALL_SERVICE`);
  - der Datensatz ist gleich, mit demselben `RUN_STARTED`;
  - der Zähler ist nicht neu gestartet und nicht abgeschlossen;
  - der Master ist einmal genommen und nicht freigegeben;
  - der Backstop ist einmal gestellt, mit demselben Handle;
  - beim `run_zone` bleibt kein `_live_run_zones`/`_manual_run_zones`-Marker zurück.

  Danach rechnet der erste Lauf über seinen **eigenen echten** Backstop ab (+610: Datensatz weg, `_record_run` einmal,
  Master-Freigabe einmal). Kein Timer bleibt liegen. Was der Backstop dabei bucht (`completed`, `planned_s`), prüft der
  Echt-Timer-Test in T3; seit dry6 fangen die zwei Dispatch-Tests ab T9 auch die T3-Proben
  `backstop-callback-dropped` und `backstop-never-armed` (gemessen an `bc41374b`, `dry6-logs/T3.md`, und am Endstand
  `70dc0c18`, `dry6-logs/T3-end-probes.txt`).
- **Befund zum Harness.** In `tests/test_service_watch.py` ist `store.config` des `_coord` ein nacktes `Mock`, und
  `active_valve_runs` ist keine Liste. Dort kann deshalb kein Dispatch-Wächter greifen.
  `_service_coord_on_its_store(hass)` bildet den echten Store nach: bei jedem Persistieren wird `active_valve_runs`
  gesetzt, wie in `tests/test_batch.py`.
- **Pins gegen die früher überlebenden Proben.** Im früheren Probelauf (`wf-scope-answer.json`, `result.drop.mut`)
  überlebten drei Proben; jetzt fängt jede ihr eigener Test:
  - `lte-boundary`: `test_the_grace_ends_exactly_when_the_backstop_is_due` (eingefroren: 608,999 in flight, 609,0
    nicht);
  - `frozen-margin-to-default`: `test_a_confirmed_run_waits_out_its_own_frozen_margin` (Marge im Datensatz 10 bei
    Zonenmarge 4: in flight bei +614, nicht bei +616);
  - `anchor-prefers-valve-on`: `test_the_grace_counts_from_the_dispatch_not_the_valve_on_report`
    (`RUN_OBSERVED_START == RUN_STARTED`, `RUN_VALVE_ON` einen `VALVE_CONFIRM_POLL` = 1 s davor: bei `RUN_STARTED` + 608
    noch in flight).

  Die ältere Probe `watch-entity-gate-dropped` mutiert T2s Helfer und wird von T2s eigenen Tests gefangen; sie wurde
  hier nicht wiederholt.
- **Bekannt und bewusst unverändert** (JustChr 09-19, Pflichtzeile im PR-Text): eine Lücke unter einer Sekunde zwischen
  dem Ende von In-flight (`RUN_STARTED + planned + Wartezeit`) und dem Backstop, der den Datensatz entfernt.
  - Der Backstop wird Millisekunden nach `RUN_STARTED` gestellt und feuert mit der Loop-Latenz.
  - Dieselbe Lücke besteht heute schon am geplanten Ende. Ohne T9 wäre sie mit der Wartezeit auf 9 s gewachsen.
- **Reichweite für den PR-Text:** ein Dispatch in der Wartezeit (geplant, „Jetzt bewässern“, `run_zone`) wird verworfen
  statt aufgeschoben; Service-Ketten sind nicht betroffen.

**Tests** (`tests/test_run_in_flight.py`; Elternstand aus `rev3/evidence.md`)

| Test | Szenario --> erwartet | am Elternstand |
|---|---|---|
| `test_a_confirmed_service_run_stays_in_flight_through_its_finish_grace` | Marge 4: +605 in flight, +610 nicht | rot |
| `test_a_write_only_service_run_gets_no_finish_grace` | ohne Watch-Entität und Marge: +605 nicht in flight | grün |
| `test_a_service_run_persisted_before_the_margin_keeps_its_window` | bestätigt, ohne Marge: +605 nicht in flight | grün |
| `test_a_confirmed_run_waits_out_its_own_frozen_margin` | eingefrorene Marge 10, Zone liest 4: +614 in flight, +616 nicht | rot |
| `test_the_grace_counts_from_the_dispatch_not_the_valve_on_report` | Anker-Pin, eingefroren: `RUN_STARTED` + 608 in flight | rot |
| `test_the_grace_ends_exactly_when_the_backstop_is_due` | Grenz-Pin, eingefroren: 608,999 `True`, 609,0 `False` | rot |
| `TestASecondDispatchInsideTheFinishGraceIsRefused::test_a_second_self_closing_dispatch_is_refused` | +603 `async_run_self_closing` --> `False`, erster Lauf unberührt, eigener Backstop rechnet ab | rot |
| `TestASecondDispatchInsideTheFinishGraceIsRefused::test_a_manual_run_zone_is_refused_the_same_way` | +603 `async_run_zone(2, 10)` --> abgelehnt, unberührt, kein Marker, eigener Backstop | rot |

**Nachvollzug**

- [ ] **Step 1: Ausgangslage prüfen, Tests auschecken, RED**

```bash
cd D:/Entwicklung/HASI/HAsmartirrigation
mkdir -p D:/Entwicklung/HASI/pr139-work/tmp D:/Entwicklung/HASI/pr139-work/npm-cache && export TEMP=D:/Entwicklung/HASI/pr139-work/tmp TMP=D:/Entwicklung/HASI/pr139-work/tmp TMPDIR=D:/Entwicklung/HASI/pr139-work/tmp npm_config_cache=D:/Entwicklung/HASI/pr139-work/npm-cache
SRC=0c0c9416
TESTS="tests/test_run_in_flight.py"
git log -1 --format=%s                    # feat(service): carry the finish grace across a restart
git status --short                        # nur: ?? docs/SESSION-STAND.md
git diff "$SRC^" --stat                   # leer: der Baum ist der von T8 auf dry6
git checkout "$SRC" -- $TESTS
L=D:/Entwicklung/HASI/pr139-work/replay/T09-red.txt
D:/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest $TESTS -p _local_socket_unblock -q --tb=line -rfE -p no:cacheprovider > $L 2>&1
grep -E "^collected |^(FAILED|ERROR) |^E  |\.py:[0-9]+: " $L; tail -n 1 $L
```

Erwartet (wörtlich aus `rev3/evidence.md`, T9; auf dry6 identisch mit dry5):

```
collected 27 items
FAILED tests/test_run_in_flight.py::test_a_confirmed_service_run_stays_in_flight_through_its_finish_grace
FAILED tests/test_run_in_flight.py::test_a_confirmed_run_waits_out_its_own_frozen_margin
FAILED tests/test_run_in_flight.py::test_the_grace_counts_from_the_dispatch_not_the_valve_on_report
FAILED tests/test_run_in_flight.py::test_the_grace_ends_exactly_when_the_backstop_is_due
FAILED tests/test_run_in_flight.py::TestASecondDispatchInsideTheFinishGraceIsRefused::test_a_second_self_closing_dispatch_is_refused
FAILED tests/test_run_in_flight.py::TestASecondDispatchInsideTheFinishGraceIsRefused::test_a_manual_run_zone_is_refused_the_same_way
ERROR tests/test_run_in_flight.py::TestASecondDispatchInsideTheFinishGraceIsRefused::test_a_second_self_closing_dispatch_is_refused
ERROR tests/test_run_in_flight.py::TestASecondDispatchInsideTheFinishGraceIsRefused::test_a_manual_run_zone_is_refused_the_same_way
=================== 6 failed, 21 passed, 2 errors in 2.09s ====================
```

```
D:\Entwicklung\HASI\pr139-work\dry2\tests\test_run_in_flight.py:196: assert False is True
D:\Entwicklung\HASI\pr139-work\dry2\tests\test_run_in_flight.py:255: assert False is True
D:\Entwicklung\HASI\pr139-work\dry2\tests\test_run_in_flight.py:288: assert False is True
D:\Entwicklung\HASI\pr139-work\dry2\tests\test_run_in_flight.py:308: AssertionError: 608.999
D:\Entwicklung\HASI\pr139-work\dry2\tests\test_run_in_flight.py:596: assert True is False
D:\Entwicklung\HASI\pr139-work\dry2\tests\test_run_in_flight.py:550: assert 2 == 1
```

Zuordnung der Zeilen:
- 196: +605;
- 255: Marge 10;
- 288: Anker;
- 308: Grenze;
- 596: der zweite `async_run_self_closing` gibt `True` zurück;
- 550: im Helfer `_assert_the_first_run_is_untouched`, beim `run_zone`-Test: das Ventil wurde zweimal geöffnet.

Die 2 Errors gibt es nur am Elternstand. Es ist jeweils ein `Lingering timer after job` mit `Job call_later 609.0` auf
`SelfClosingMixin._sc_schedule_cleanup`, also der Backstop, den der durchgelassene zweite Dispatch neu gestellt hat. Kein
vorbestehender Error, denn `tests/test_service_watch.py` läuft hier nicht mit. Am Elternstand grün sind 2 der 8 neuen
Tests (write-only, vor der Marge); die Wartezeit 0 ist dort Altverhalten.

Was der zweite Dispatch am Elternstand tatsächlich tut, belegt die Diagnose `dry3-logs/T9-diag-parent.txt`:
- Ventil zweimal geöffnet;
- Datensatz ersetzt (`RUN_STARTED` auf +603);
- `_sc_start_flow_sampling` zweimal aufgerufen;
- `async_master_acquire` zweimal aufgerufen;
- `_sc_schedule_cleanup` zweimal `(2, 609.0)`, anderes Handle;
- beim `run_zone` zusätzlich `_manual_run_zones == {2}`.

- [ ] **Step 2: Produktivcode auschecken, GREEN, 7 Service-Suiten**

```bash
cd D:/Entwicklung/HASI/HAsmartirrigation
mkdir -p D:/Entwicklung/HASI/pr139-work/tmp D:/Entwicklung/HASI/pr139-work/npm-cache && export TEMP=D:/Entwicklung/HASI/pr139-work/tmp TMP=D:/Entwicklung/HASI/pr139-work/tmp TMPDIR=D:/Entwicklung/HASI/pr139-work/tmp npm_config_cache=D:/Entwicklung/HASI/pr139-work/npm-cache
SRC=0c0c9416
TESTS="tests/test_run_in_flight.py"
PROD="custom_components/irrigation_plus/run_state.py"
PY=D:/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe
git checkout "$SRC" -- $PROD
$PY -m pytest $TESTS -p _local_socket_unblock -q --tb=line -rfE -p no:cacheprovider > D:/Entwicklung/HASI/pr139-work/replay/T09-green.txt 2>&1
grep -E "^collected " D:/Entwicklung/HASI/pr139-work/replay/T09-green.txt; tail -n 1 D:/Entwicklung/HASI/pr139-work/replay/T09-green.txt
$PY -m pytest tests/test_service_watch.py tests/test_finish_grace_helpers.py tests/test_run_in_flight.py tests/test_confirm_reserve.py tests/test_self_closing.py tests/test_run_watch.py tests/test_observed_watering.py tests/test_i18n_completeness.py -p _local_socket_unblock -q -p no:cacheprovider --tb=line -rfE > D:/Entwicklung/HASI/pr139-work/replay/T09-suites.txt 2>&1
grep -E "^(FAILED|ERROR) | passed" D:/Entwicklung/HASI/pr139-work/replay/T09-suites.txt | sed 's/ - .*//'
```

Erwartet (`rev3/evidence.md`; `dry6-logs/percommit.md`):

```
collected 27 items
============================= 27 passed in 2.03s ==============================
```

```
ERROR tests/test_service_watch.py::TestOneOffSampleIsNotEvidenceTheWaterStopped::test_the_run_is_not_settled_before_the_window_is_out
======================== 300 passed, 1 error in 19.90s ========================
```

Die neuen Dispatch-Tests enden jeweils mit gefeuertem echtem Backstop und fügen keinen Error hinzu.

- [ ] **Step 3: Lint und Baumvergleich**

```bash
cd D:/Entwicklung/HASI/HAsmartirrigation
SRC=0c0c9416
uvx black --check custom_components/irrigation_plus/ $(git diff --name-only 2b2c403b -- tests)
uvx ruff check custom_components/irrigation_plus/
git diff "$SRC" --stat
git diff --cached "$SRC" --stat
```

Erwartet (`scratch/dry5-checks.log`, `ed9b2e4f`; dieselbe Dateimenge auf dry6): `73 files would be left unchanged.`
(68 + 5 Testdateien, jetzt mit `tests/test_run_in_flight.py`), `All checks passed!`; beide Diffs leer.

- [ ] **Step 4: Commit mit derselben Nachricht**

```bash
cd D:/Entwicklung/HASI/HAsmartirrigation
SRC=0c0c9416
git log -1 --format=%B "$SRC" | git commit -q -F -
test "$(git rev-parse HEAD^{tree})" = "$(git rev-parse "$SRC^{tree}")" && echo TREE-SAME
diff <(git log -1 --format=%B HEAD) <(git log -1 --format=%B "$SRC") && echo MSG-SAME
git log -1 --format=%B | grep -c '^#'     # 0
git show --stat --format= HEAD | tail -1  # 2 files changed, 291 insertions(+), 2 deletions(-)
git diff "$SRC" HEAD --stat               # leer
git log --oneline -1                      # neuer SHA, Betreff des Tasks
git status --short                        # nur: ?? docs/SESSION-STAND.md
```

**Mutationsproben (Probelauf)**

Die Proben stammen aus `dry3-logs/T9.md` (Rohdaten `T9-probes.txt`, frühere Läufe `T9-probes-run1.txt`,
`T9-probes-run2.txt`). Das Skript ist `D:/Entwicklung/HASI/pr139-work/scratch/t9/probes.py`. Getestet wird
`tests/test_run_in_flight.py`, zuerst mit `-k` auf die fünf im `dry3`-Nachtrag hinzugekommenen Tests (Marge 10, Anker,
Grenze, beide Dispatch-Tests; bei `drop-grace` vorab nur die Dispatch-Tests), danach die ganze Datei. Test- und
Produktivdatei sind auf `dry3`, `dry5` und `dry6` inhaltsgleich, die Ergebnisse gelten also. Alle 8 Suchtexte kommen auf
`dry5` und `dry6` genau einmal vor (geprüft am 19.09. bzw. 19.09. abends, lesend).

Die Schlussprüfung (Task 13) fährt diese Proben nicht mehr mit `scratch/t9/probes.py` (fester Pfad `dry2`, fest
verdrahtetes Log), sondern mit dem Treiber-Satz `t09` in `mut/rev3_probes.py` auf dem echten Branch, ganze Datei; die
Ersetzung von `live-zone-margin` steht dort in der Form unten.

| Probe | Datei | Mutation | gefangen von (dry3) |
|---|---|---|---|
| drop-grace (benannt) | `run_state.py` | `else planned + run_finish_grace_seconds(run)` --> `else planned` | beide Dispatch-Tests (`assert True is False` l.596; `assert 2 == 1` l.550); in der Datei außerdem Marge 10, Anker, Grenze und der +605/+610-Test |
| anchor-prefers-valve-on (benannt) | `run_state.py` | `(observed or run.get(const.RUN_STARTED))` --> `(run.get(const.RUN_VALVE_ON) or observed or run.get(const.RUN_STARTED))` | nur der Anker-Pin (l.288 `assert False is True`) |
| lte-boundary (benannt) | `run_state.py` | `.total_seconds() < window` --> `<= window` | nur der Grenz-Pin (l.308 `AssertionError: 609.0`) |
| frozen-margin-to-default (benannt) | `run_watch.py` | in `run_finish_grace_seconds`: `float(run_latency_margin(run))` --> `float(const.DEFAULT_LATENCY_MARGIN_SECONDS)` | nur Marge 10 (l.255 `assert False is True`) |
| grace-doubled | `run_state.py` | --> `else planned + 2 * run_finish_grace_seconds(run)` | Marge 10 (+616-Hälfte, l.264), Grenze (l.308); in der Datei auch die +610-Hälfte des +605/+610-Tests |
| grace-for-every-record | `run_state.py` | --> `else planned + float(SERVICE_WATCH_SETTLE_SECONDS + DEFAULT_LATENCY_MARGIN_SECONDS)` | Marge 10 (l.255: 609 ist zu kurz); in der Datei auch die Pins write-only und vor der Marge |
| grace-without-plan | `run_state.py` | --> `else run_finish_grace_seconds(run)` | alle 5 Nachtrag-Tests; in der Datei insgesamt 8, darunter zwei Basis-Tests (`inside_its_window_counts`, `dispatch_rejects_a_second_run`) |
| live-zone-margin | `run_state.py` | Fenster aus der Marge der **Zone** statt aus dem Datensatz | Marge 10 (l.255), Anker, Grenze; die Dispatch-Tests sind hier äquivalent, weil Zonen- und eingefrorene Marge dort gleich sind |

Ergebnis: 8 Proben, 8 gefangen, 0 äquivalent, 0 überlebend. Jede der vier benannten Proben fängt ein eigener neuer Test
von T9, `drop-grace` fangen beide Dispatch-Tests.

**`live-zone-margin` neu formulieren.** Die Ersetzung auf `dry3` rief `zone_finish_grace_seconds`, und das gibt es seit
Entscheidung (e) nicht mehr. Unverändert liefe die Probe in einen `AttributeError` und wäre aus dem falschen Grund
„gefangen“. Für den erneuten Lauf wird das Fenster aus `zone_latency_margin` der Zone berechnet, hinter demselben Tor
wie bisher:

```
WINDOW  = 'else planned + run_finish_grace_seconds(run)'
ERSATZ  = 'else planned + ((float(const.SERVICE_WATCH_SETTLE_SECONDS) + __import__("custom_components.irrigation_plus.run_watch", fromlist=["_"]).zone_latency_margin(self.store.get_zone(zone_id))) if run_finish_grace_seconds(run) else 0.0)'
```

Erwartung, auf `dry5`/`dry6` **nicht gemessen** (die Ersetzung trifft auf dry6 genau einmal und kompiliert): gefangen
von `test_a_confirmed_run_waits_out_its_own_frozen_margin`. Die Zone
liest dort 4, das Fenster wird also 609, und +614 ist nicht mehr in flight. Ob Anker- und Grenz-Pin sie ebenfalls fangen,
hängt an der Zone des `_coord` dieser Tests. Die liefert ohne Feld den Default 4, die Probe wäre dort also äquivalent;
auch das ist nicht gemessen. Maßgeblich ist, dass der Marge-10-Test sie fängt.

---

### Task 10 — gestrichen: Der Zeitfenster-Preis trägt die Wartezeit

**Kein Commit, keine Tests, nichts nachzuvollziehen.** Die Nummer bleibt frei.

- **Was es war (Revision 2):** `zone_confirm_seconds` (`run_window.py`) sollte für den Self-Closing-Track mit
  `confirm_entity` `VALVE_CONFIRM_TIMEOUT + zone_finish_grace_seconds(zone)` liefern, bei Default 39 statt 30. Der Pin
  `tests/test_confirm_reserve.py::test_a_self_closing_zone_pays_only_with_a_confirm_entity` wäre von 30 auf 39 gegangen.
- **Warum gestrichen:** JustChr am 16.09.
  ([issuecomment-5692654650](https://github.com/JustChr/HAsmartirrigation/issues/139#issuecomment-5692654650),
  „Out — 1“). Die Kosten: Finish-Anker und Arm-Schranke verschieben sich für **jede** bestätigte Service-Zone unter
  `sequential`, auf jeder Anlage. Der Nutzen: ein richtiger Preis nur im Eckfall. Mitten in der Stabilisierung geht die
  Abwägung andersherum. Deshalb ein eigenes Issue nach dem stabilen Release: „it is a real gap and I do not want it
  lost“.
- **Folgen im Plan:**
  - `run_window.py` und `tests/test_confirm_reserve.py` bleiben unberührt; der Pin bleibt 30.
  - `zone_finish_grace_seconds` gibt es nach Entscheidung (e) nicht. Das Folge-Issue bzw. sein PR muss den zonenbezogenen
    Wartezeit-Helfer selbst mitbringen: nur `WATERING_MODE_SERVICE` mit `confirm_entity`, dann
    `SERVICE_WATCH_SETTLE_SECONDS + zone_latency_margin(zone)`.
- **PR-Text:** der Zeitfenster-Preis wird als bewusst offengelassen genannt, mit Verweis auf das Folge-Issue. Das
  verlangte JustChr am 16.09. unter „What the PR body still needs“: „the two cases you are deliberately leaving … the
  window pricing (1)“.
- **Folge-Issue:** Angelegt wird es erst, wenn der PR offen ist (5740280769: „I'll open that issue with the PR's numbers
  once the PR is up“). Text und Titel werden vorher im Chat gezeigt und freigegeben. Es nennt die PR-Zahlen und die drei
  Korrekturen aus 5740280769, die JustChr am 19.09. begrüßte („good to have in that issue“):
  - unter `rotating` gilt der Preis je Slot, er bewegt sich also um mehr als 9 s je Zone;
  - der Unterpreis beginnt, sobald der Confirm länger dauert als 30 − Entprellung − Marge (21 s bei Default) UND der
    Schluss verpasst wird; ab einer Marge von 26 s genügt ein verpasster Schluss allein;
  - Service-Zonen schneidet die Frist nicht ab; die Kosten sind ein späteres Finish, kein abgeschnittener Schwanz.
- **Entwurf:** `D:/Entwicklung/HASI/pr139-work/rev3/issue-window-pricing.md`, korrigiert am 19.09.: er enthält die drei
  Korrekturen (Preis je Slot unter `rotating`, Schwelle 30 − Entprellung − Marge = 21 s bei Default und Marge ab 26 s,
  späteres Finish statt abgeschnittenem Schwanz) und nennt `zone_finish_grace_seconds` nicht mehr („The zone-level grace
  helper that the dropped commit used is not in #<PR>“). Der ältere Entwurf `pr139-work/issue-window-pricing.md` ist
  überholt und wird nicht benutzt. Angelegt wird in Task 14 Step 6.

---

### Task 11: Panel-Feld „Latenz-Marge“ + vitest-Sichtbarkeitstor und Klemme

**dry6:** `0e68d978` (dry5: `7f57cf4f`, Inhalt gleich, nur neuer Elternstand), `feat(panel): add latency margin field for
confirmed service zones` (`4 files changed, 144 insertions(+)`). **Elternstand auf dry6:** `0c0c9416` (T9).

**Files**
- TEST: `custom_components/irrigation_plus/frontend/src/views/zones/view-zone-settings-latency-margin.test.ts` (neu,
  8 vitest-Tests: 4 Sichtbarkeit, 4 Klemme).
- PROD:
  - `custom_components/irrigation_plus/frontend/src/const.ts`: `ZONE_LATENCY_MARGIN = "latency_margin"`;
  - `custom_components/irrigation_plus/frontend/src/types.ts`: `latency_margin?: number` in `SmartIrrigationZone`, mit
    Kommentar;
  - `custom_components/irrigation_plus/frontend/src/views/zones/view-zone-settings.ts`: Import, `_showLatencyMargin`,
    `_clampLatencyMargin`, Zeile im Service-Block.

**Was und warum**

- **Die Zeile.** Sie steht im Service-Block der Zoneneinstellungen, direkt unter dem `confirm_entity`-Picker, und nur
  dort. Der Batch-Block hat einen eigenen Confirm-Picker und bekommt die Zeile nicht.
  - Sichtbar nur mit gesetztem `confirm_entity` (`_showLatencyMargin(zone)` = `!!zone?.confirm_entity`). Ohne Confirm
    meldet nichts den Schluss des Ventils, das Backend gibt keine Wartezeit, und das Feld wäre ein toter Regler.
  - Überschrift `panels.zones.labels.latency_margin` mit `(${UNIT_SECONDS})`, Beschreibung `latency_margin_help`.
  - Zahlenfeld `step 1`, `min 0`, `max 30`, Wert `zone.latency_margin ?? 4`.
- **Die Klemme.** `@input` speichert über `_clampLatencyMargin`: runden, auf [0, 30] klemmen. Das sind dieselben Grenzen
  wie im Backend (`MAX_LATENCY_MARGIN_SECONDS`). Ein leeres oder ungültiges Feld (`valueAsNumber` ist NaN) ergibt `null`
  und wird ignoriert, statt beim Tippen 0 zu speichern, wie beim Feld `lead_time`. Die Klemme ist als eigene Methode
  ausgelagert, damit vitest sie prüfen kann.
- **Umformulierter Kommentar (Entscheidung (e)).** Revision 2 schrieb über `_showLatencyMargin` „MUST mirror the backend
  gate `zone_finish_grace_seconds` in run_watch.py (confirm_entity truthy); keep the two in sync.“ Den Helfer gibt es
  nicht mehr. Jetzt steht dort „(already scoped to SERVICE zones by the mode check above)“. Das ist der einzige
  Unterschied zu Revision 2: `view-zone-settings.ts` hat 57 statt 58 Zeilen im Diff; die übrigen Änderungszeilen und die
  Testdatei sind gleich (Vergleich der Änderungszeilen von `69a343e6`, T11 auf `dry3` = Revision 2, mit `7f57cf4f` (inhaltsgleich mit dry6 `0e68d978`),
  19.09.).
- **Bis Task 12** gibt `localize` für die zwei neuen Schlüssel `undefined` zurück. Die Überschrift zeigt dann nur „(s)“.
  Das ist kein Build-Fehler.
- **Reichweite des Tests.** vitest prüft die beiden Methoden, nicht das gerenderte Template. Dass `render()` die Zeile
  hinter das Tor setzt und über die Klemme speichert, prüft die Panel-Kontrolle von Hand im Live-Test (E10). Der
  Kommentar im Test sagt das.
- Dieser Commit enthält nur Quellen, kein dist; dist baut Task 12 mit den Übersetzungen neu.

**Tests** (vitest `view-zone-settings-latency-margin.test.ts`)

| describe | it | prüft |
|---|---|---|
| visibility gate | `shows when a confirm_entity is set` | `_showLatencyMargin({confirm_entity: "binary_sensor.valve_flowing"})` = `true` |
| | `hides when confirm_entity is null` | `null` --> `false` |
| | `hides when confirm_entity is an empty string` | `""` --> `false` |
| | `hides when confirm_entity is missing` | `{}` und `undefined` --> `false` |
| input clamp | `keeps a whole number inside the range` | 4, 0, 30 bleiben |
| | `rounds to whole seconds` | 2,6 --> 3; 2,4 --> 2 |
| | `clamps below 0 and above 30` | −3 --> 0; 45 --> 30 |
| | `ignores an empty or invalid input (NaN)` | NaN --> `null` |

**Nachvollzug**

- [ ] **Step 1: Ausgangslage prüfen, Frontend-Abhängigkeiten, vitest-Basis**

```bash
cd D:/Entwicklung/HASI/HAsmartirrigation
mkdir -p D:/Entwicklung/HASI/pr139-work/tmp D:/Entwicklung/HASI/pr139-work/npm-cache && export TEMP=D:/Entwicklung/HASI/pr139-work/tmp TMP=D:/Entwicklung/HASI/pr139-work/tmp TMPDIR=D:/Entwicklung/HASI/pr139-work/tmp npm_config_cache=D:/Entwicklung/HASI/pr139-work/npm-cache
SRC=0e68d978
git log -1 --format=%s                    # feat(service): keep a confirmed run in flight through its finish grace
git status --short                        # nur: ?? docs/SESSION-STAND.md
git diff "$SRC^" --stat                   # leer: der Baum ist der von T9 auf dry6
cd custom_components/irrigation_plus/frontend
node --version                            # v24.15.0 (wie im Probelauf)
npm ci
npx vitest run 2>&1 | grep -E "Test Files|Tests "
```

Erwartet: Basis `22` Dateien / `616` Tests, alle grün. Das ist die Zahl aus dem Auftrag vom 19.09.; ein Protokoll dazu
liegt in `pr139-work` nicht vor (Spec, „Messstand `dry6`“). T1 bis T9 berühren kein Frontend, der Stand ist also der von
`2b2c403b`.

```
 Test Files  22 passed (22)
      Tests  616 passed (616)
```

- [ ] **Step 2: Test auschecken, RED**

```bash
cd D:/Entwicklung/HASI/HAsmartirrigation
mkdir -p D:/Entwicklung/HASI/pr139-work/tmp D:/Entwicklung/HASI/pr139-work/npm-cache && export TEMP=D:/Entwicklung/HASI/pr139-work/tmp TMP=D:/Entwicklung/HASI/pr139-work/tmp TMPDIR=D:/Entwicklung/HASI/pr139-work/tmp npm_config_cache=D:/Entwicklung/HASI/pr139-work/npm-cache
SRC=0e68d978
TESTS="custom_components/irrigation_plus/frontend/src/views/zones/view-zone-settings-latency-margin.test.ts"
git checkout "$SRC" -- $TESTS
cd custom_components/irrigation_plus/frontend
npx vitest run src/views/zones/view-zone-settings-latency-margin.test.ts
```

Erwartet (wörtlich aus `rev3/evidence.md`, T11; alle 8 mit demselben Muster, weil die Methoden am Elternstand fehlen):

```
FAIL src/views/zones/view-zone-settings-latency-margin.test.ts > view-zone-settings latency_margin visibility gate > shows when a confirm_entity is set
TypeError: el._showLatencyMargin is not a function
FAIL ... > hides when confirm_entity is null
TypeError: el._showLatencyMargin is not a function
FAIL ... > hides when confirm_entity is an empty string
TypeError: el._showLatencyMargin is not a function
FAIL ... > hides when confirm_entity is missing
TypeError: el._showLatencyMargin is not a function
FAIL ... > keeps a whole number inside the range
TypeError: el._clampLatencyMargin is not a function
FAIL ... > rounds to whole seconds
TypeError: el._clampLatencyMargin is not a function
FAIL ... > clamps below 0 and above 30
TypeError: el._clampLatencyMargin is not a function
FAIL ... > ignores an empty or invalid input (NaN)
TypeError: el._clampLatencyMargin is not a function
```

```
 Test Files  1 failed (1)
      Tests  8 failed (8)
```

- [ ] **Step 3: Quellen auschecken, GREEN, ganzes vitest, Frontend-Lint, Python-Suiten**

```bash
cd D:/Entwicklung/HASI/HAsmartirrigation
mkdir -p D:/Entwicklung/HASI/pr139-work/tmp D:/Entwicklung/HASI/pr139-work/npm-cache && export TEMP=D:/Entwicklung/HASI/pr139-work/tmp TMP=D:/Entwicklung/HASI/pr139-work/tmp TMPDIR=D:/Entwicklung/HASI/pr139-work/tmp npm_config_cache=D:/Entwicklung/HASI/pr139-work/npm-cache
SRC=0e68d978
FE=custom_components/irrigation_plus/frontend/src
PROD="$FE/const.ts $FE/types.ts $FE/views/zones/view-zone-settings.ts"
git checkout "$SRC" -- $PROD
cd custom_components/irrigation_plus/frontend
npx vitest run src/views/zones/view-zone-settings-latency-margin.test.ts 2>&1 | grep -E "Test Files|Tests "
npx vitest run 2>&1 | grep -E "Test Files|Tests "
npm run lint
cd D:/Entwicklung/HASI/HAsmartirrigation
D:/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests/test_service_watch.py tests/test_finish_grace_helpers.py tests/test_run_in_flight.py tests/test_confirm_reserve.py tests/test_self_closing.py tests/test_run_watch.py tests/test_observed_watering.py tests/test_i18n_completeness.py -p _local_socket_unblock -q -p no:cacheprovider --tb=line -rfE > D:/Entwicklung/HASI/pr139-work/replay/T11-suites.txt 2>&1
grep -E "^(FAILED|ERROR) | passed" D:/Entwicklung/HASI/pr139-work/replay/T11-suites.txt | sed 's/ - .*//'
```

Erwartet:
- die Testdatei laut `rev3/evidence.md`:

  ```
   Test Files  1 passed (1)
        Tests  8 passed (8)
  ```

- das ganze vitest mit `23` Dateien / `624` Tests. Das wurde am `dry6`-Endstand `70dc0c18` gemessen
  (`dry6-logs/full-suite.md`; ebenso am dry5-Endstand, `scratch/dry5-checks.log`), an T11 selbst **nicht gemessen**. Die
  Quellen unter `frontend/src` sind an T11 und T12 gleich.

  ```
   Test Files  23 passed (23)
        Tests  624 passed (624)
  ```

- `npm run lint` führt `eslint src/**/*.ts` aus: ohne Befund, Exit 0. Gemessen am `dry5`-Endstand als erster Teil von
  `npm run build` (`scratch/dry5-build.txt`), mit denselben `.ts`-Dateien. `npm run lint` statt `npm run build`, damit
  dist hier unberührt bleibt.
- die Python-Suiten laut `dry6-logs/percommit.md`, `0e68d978`, unverändert gegenüber T9:

  ```
  ERROR tests/test_service_watch.py::TestOneOffSampleIsNotEvidenceTheWaterStopped::test_the_run_is_not_settled_before_the_window_is_out
  ======================== 300 passed, 1 error in 19.96s ========================
  ```

- [ ] **Step 4: Lint (Python) und Baumvergleich**

```bash
cd D:/Entwicklung/HASI/HAsmartirrigation
SRC=0e68d978
uvx black --check custom_components/irrigation_plus/ $(git diff --name-only 2b2c403b -- tests)
uvx ruff check custom_components/irrigation_plus/
git status --short                        # nur die 4 Frontend-Dateien (staged) und ?? docs/SESSION-STAND.md; kein dist
git diff "$SRC" --stat
git diff --cached "$SRC" --stat
```

Erwartet (`scratch/dry5-checks.log`, `7f57cf4f`; dieselbe Dateimenge auf dry6): `73 files would be left unchanged.`,
`All checks passed!`; beide Diffs leer.

- [ ] **Step 5: Commit mit derselben Nachricht**

```bash
cd D:/Entwicklung/HASI/HAsmartirrigation
SRC=0e68d978
git log -1 --format=%B "$SRC" | git commit -q -F -
test "$(git rev-parse HEAD^{tree})" = "$(git rev-parse "$SRC^{tree}")" && echo TREE-SAME
diff <(git log -1 --format=%B HEAD) <(git log -1 --format=%B "$SRC") && echo MSG-SAME
git log -1 --format=%B | grep -c '^#'     # 0
git show --stat --format= HEAD | tail -1  # 4 files changed, 144 insertions(+)
git diff "$SRC" HEAD --stat               # leer
git log --oneline -1                      # neuer SHA, Betreff des Tasks
git status --short                        # nur: ?? docs/SESSION-STAND.md
```

**Mutationsproben (Probelauf)**

Die Proben stammen aus Revision 2, Plan Task 11 Step 13. Gemessen wurde am Commit `7c626143` von `dry2`: Sicherungen
`mut/r7-t11-{name}.bak`, Ersetzung mit `D:/Entwicklung/HASI/pr139-work/mut/mutate.py` (Suchtext genau einmal),
Wiederherstellung mit SHA-256-Prüfung. Getestet wurde die vitest-Datei aus Step 2.

Die Testdatei ist auf `dry5`/`dry6` identisch, und `view-zone-settings.ts` unterscheidet sich nur im Kommentar. Die
Zählungen innerhalb der einen Datei (8 Tests) gelten deshalb. Die drei Suchtexte `return !!zone?.confirm_entity;`,
`Math.max(0, Math.min(30, Math.round(v)))` und `    if (isNaN(v)) return null;` kommen auf `dry5` je genau einmal vor
(geprüft am 19.09.), auf `dry6` ebenso, dazu `Math.min(30, Math.round(v))` (19.09. abends, lesend). In der
Schlussprüfung (Task 13) laufen die Proben erneut (Treiber-Satz `t11`).

| Probe | Änderung in `view-zone-settings.ts` | beobachtet (Revision 2) |
|---|---|---|
| gate-always-true | `return !!zone?.confirm_entity;` --> `return true;` | FAIL `hides when confirm_entity is null`, `… is an empty string`, `… is missing`, also `3 failed \| 5 passed (8)` |
| gate-ignores-empty | --> `return zone?.confirm_entity != null;` | FAIL `hides when confirm_entity is an empty string`, `1 failed \| 7 passed (8)` |
| clamp-no-upper | `Math.max(0, Math.min(30, Math.round(v)))` --> `Math.max(0, Math.round(v))` | FAIL `clamps below 0 and above 30`, `1 failed \| 7 passed (8)` |
| clamp-no-lower | --> `Math.min(30, Math.round(v))` | FAIL `clamps below 0 and above 30`, `1 failed \| 7 passed (8)` |
| clamp-no-round | --> `Math.max(0, Math.min(30, v))` | FAIL `rounds to whole seconds`, `1 failed \| 7 passed (8)` |
| clamp-no-nan-guard | Zeile `if (isNaN(v)) return null;` entfernt | FAIL `ignores an empty or invalid input (NaN)`, `1 failed \| 7 passed (8)` |

Ergebnis: 6 Proben, 6 gefangen. Nach der letzten Wiederherstellung wieder `Tests  8 passed (8)`.

**Dazu dry6** (19.09. abends, am Endstand, ganzes vitest mit 23 Dateien; `dry6-logs/probes.md`). Zwei Tests fing bis
dahin keine Probe: „shows when a confirm_entity is set“ (ein Tor, das immer `false` gibt, blieb unbemerkt) und „keeps a
whole number inside the range“.

| Probe | Änderung in `view-zone-settings.ts` | beobachtet (dry6) |
|---|---|---|
| gate-always-false | `return !!zone?.confirm_entity;` --> `return false;` | FAIL „shows when a confirm_entity is set“ (`expected false to be true`), `Tests  1 failed \| 623 passed (624)` |
| clamp-upper-29 | `Math.min(30, Math.round(v))` --> `Math.min(29, Math.round(v))` | FAIL „keeps a whole number inside the range“ und „clamps below 0 and above 30“ (`expected 29 to be 30`), `Tests  2 failed \| 622 passed (624)` |

Damit T11: 8 Proben, 8 gefangen; jeder der 8 Tests scheitert an mindestens einer.

---

### Task 12: Übersetzungen „Latenz-Marge“ in 8 Sprachen + Doku + dist

**dry6:** `70dc0c18` (dry5: `58d6b7b5`, Inhalt und dist-Bytes gleich, nur neuer Elternstand), `feat(i18n): translate
and document the latency margin zone field` (`11 files changed, 829 insertions(+), 791 deletions(-)`).
**Elternstand auf dry6:** `0e68d978` (T11).

**Files**
- TEST: keiner geändert. `tests/test_i18n_completeness.py` besteht und prüft fehlende und verwaiste Schlüssel, englische
  Kopien ab 4 Prosa-Wörtern und Platzhalter.
- PROD (aus `$SRC` ausgecheckt):
  - `custom_components/irrigation_plus/frontend/localize/languages/{de,en,es,fr,it,nl,no,sk}.json`, je 2 Zeilen;
  - `docs/configuration-my-zones.md`, 1 Zeile.
- PROD (aus den Quellen gebaut, nicht ausgecheckt, `git add -f`):
  `custom_components/irrigation_plus/frontend/dist/irrigation-plus.js` und `.../dist/irrigation-plus-card-impl.js`.

**Was und warum**

- **Katalog-Schlüssel.** `panels.zones.labels.latency_margin` und `latency_margin_help` kommen in alle 8
  Panel-Sprachdateien, als echte Übersetzungen mit den Begriffen der jeweiligen Datei für Lauf, Ventil und
  Bestätigungs-Entität. Sie stehen im Service-Block direkt nach `"confirm_entity_help"` und vor `"observed_entity"`.
  Damit zeigt die Zeile aus T11 „Latency margin (s)“ (en) statt nur „(s)“.
- **Wortlaut.** Die 16 Texte hat der User am 15.09. freigegeben (Revision 2, Plan Task 12 Step 1, Tabelle). Sie sind
  seitdem unverändert: die hinzugefügten Zeilen von T12 sind auf `dry3` (`157d3134`), `dry5` und `dry6` identisch (Vergleich am
  19.09.; `dry3-logs/final.md`, Range-Diff `=` für T12). Wer einen Text ändern will, legt ihn dem User vorher erneut vor.
- **Backend-Katalog** `translations/*.json`: nichts. Er hat keinen Abschnitt für Zonenfelder (nur `config`, `options`,
  `services`, `entity`, `issues`); JustChr hat das am 16.09. bestätigt („as on #125“).
- **Doku.** In `docs/configuration-my-zones.md` kommt ein Punkt „Latency margin“ direkt unter „Confirm entity“:
  Sekunden, Default 4, 0–30, nur mit Confirm-Entität. Er sagt, worauf gewartet wird; dass ein innerhalb der Marge vor dem
  Ende gemeldeter Schluss als vollständig zählt; und dass ein Lauf ohne Schluss-Meldung bei geplant + 5 s + Marge
  abschließt.
- **dist.**
  - Nur `en.json` steckt im Bundle (`localize.ts` importiert es); die übrigen Sprachen lädt es zur Laufzeit. Deshalb
    ändern sich genau `irrigation-plus.js` (Panel, mit dem T11-Code) und `irrigation-plus-card-impl.js`.
    `irrigation-plus-card.js` und `irrigation-plus-card-legacy.js` bleiben inhaltsgleich.
  - Gebaut wird lokal mit Node v24.15.0. Das reproduziert die Node-22-CI byte-genau; die CI prüft die Frische durch
    Neubau plus `git diff` (Kommentar in `.gitattributes`, `irrigation-plus.js` ist `eol=lf`).
  - dist ist gitignored, deshalb `git add -f`.

**Tests:** `tests/test_i18n_completeness.py` (unverändert) läuft in den sieben Suiten plus i18n mit; vitest ganz.

**Nachvollzug**

- [ ] **Step 1: Ausgangslage prüfen**

```bash
cd D:/Entwicklung/HASI/HAsmartirrigation
SRC=70dc0c18
git log -1 --format=%s                    # feat(panel): add latency margin field for confirmed service zones
git status --short                        # nur: ?? docs/SESSION-STAND.md
git diff "$SRC^" --stat                   # leer: der Baum ist der von T11 auf dry6
```

- [ ] **Step 2: Ersatz-RED: nur `en.json` (nicht im dry5/dry6-Nachweis)**

T12 hat keine Testdatei, also gibt es kein RED im Sinne des Nachvollzugs (`rev3/evidence.md`: „Kein RED-Lauf“). Damit
der Wächter der Kataloge einmal sichtbar anschlägt, wird zuerst nur `en.json` ausgecheckt.

```bash
cd D:/Entwicklung/HASI/HAsmartirrigation
mkdir -p D:/Entwicklung/HASI/pr139-work/tmp D:/Entwicklung/HASI/pr139-work/npm-cache && export TEMP=D:/Entwicklung/HASI/pr139-work/tmp TMP=D:/Entwicklung/HASI/pr139-work/tmp TMPDIR=D:/Entwicklung/HASI/pr139-work/tmp npm_config_cache=D:/Entwicklung/HASI/pr139-work/npm-cache
SRC=70dc0c18
git checkout "$SRC" -- custom_components/irrigation_plus/frontend/localize/languages/en.json
D:/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests/test_i18n_completeness.py -p _local_socket_unblock -q --tb=line -rfE -p no:cacheprovider > D:/Entwicklung/HASI/pr139-work/replay/T12-red.txt 2>&1
grep -E "^FAILED | passed| failed" D:/Entwicklung/HASI/pr139-work/replay/T12-red.txt
```

Erwartet ist, dass genau die 7 Nicht-en-Sprachen an fehlenden Schlüsseln scheitern:
`FAILED tests/test_i18n_completeness.py::test_no_missing_keys[panel-de]` sowie `[panel-es]`, `[panel-fr]`,
`[panel-it]`, `[panel-nl]`, `[panel-no]` und `[panel-sk]`, jeweils mit der Meldung
`… is missing 2 key(s) present in en.json …`.
- Namen und Meldung stammen aus Revision 2 auf `0b418644`: dort `7 failed, 58 passed`.
- `tests/test_i18n_completeness.py` hat sich zwischen `0b418644` und `2b2c403b` geändert (+18 Zeilen). Die Zählung auf
  `2b2c403b` ist **nicht gemessen**.
- Geprüft wird deshalb nur die Menge der FAILED-Namen. Fehlt einer der sieben: STOPP. Erscheinen außer ihnen weitere
  FAILED-Namen, etwa aus den seit `0b418644` hinzugekommenen Prüfungen, werden sie notiert und vor Step 3 gemeldet.
  Ein Vergleichswert dafür existiert nicht.

- [ ] **Step 3: Übrige Kataloge und Doku auschecken**

```bash
cd D:/Entwicklung/HASI/HAsmartirrigation
SRC=70dc0c18
L=custom_components/irrigation_plus/frontend/localize/languages
PROD="$L/de.json $L/en.json $L/es.json $L/fr.json $L/it.json $L/nl.json $L/no.json $L/sk.json docs/configuration-my-zones.md"
git checkout "$SRC" -- $PROD
```

- [ ] **Step 4: dist aus den Quellen bauen und gegen `$SRC` vergleichen (CR ignoriert)**

```bash
cd D:/Entwicklung/HASI/HAsmartirrigation/custom_components/irrigation_plus/frontend
mkdir -p D:/Entwicklung/HASI/pr139-work/tmp D:/Entwicklung/HASI/pr139-work/npm-cache && export TEMP=D:/Entwicklung/HASI/pr139-work/tmp TMP=D:/Entwicklung/HASI/pr139-work/tmp TMPDIR=D:/Entwicklung/HASI/pr139-work/tmp npm_config_cache=D:/Entwicklung/HASI/pr139-work/npm-cache
node --version                            # v24.15.0
npm ci && npm run build > D:/Entwicklung/HASI/pr139-work/replay/T12-build.txt 2>&1; echo "build exit $?"; tail -n 3 D:/Entwicklung/HASI/pr139-work/replay/T12-build.txt
cd D:/Entwicklung/HASI/HAsmartirrigation
SRC=70dc0c18
D=custom_components/irrigation_plus/frontend/dist
for f in irrigation-plus.js irrigation-plus-card-impl.js irrigation-plus-card.js irrigation-plus-card-legacy.js; do
  a=$(tr -d '\r' < $D/$f | sha256sum | cut -c1-12)
  b=$(git show "$SRC:$D/$f" | tr -d '\r' | sha256sum | cut -c1-12)
  echo "$f built=$a committed=$b $([ "$a" = "$b" ] && echo SAME || echo DIFF)"
done
git diff --stat -- $D
```

Erwartet:
- Build: `eslint src/**/*.ts` ohne Befund, dann viermal `created dist in …`, Exit 0. Die zwei `output.name`-Warnungen
  für die IIFE-Bundles `irrigation-plus.ts` und `irrigation-plus-card-impl.ts` sind vorbestehend
  (`scratch/dry5-build.txt`).
- Vergleich, wörtlich aus `scratch/dry5-checks.log` (dort gegen `HEAD` = `58d6b7b5`; hier gegen `$SRC` = `70dc0c18`, der
  dieselben dist-Bytes hat: `git diff dry5/backstop-grace dry6/backstop-grace` betrifft nur
  `tests/test_service_watch.py`):

  ```
  irrigation-plus.js built=0618bb5011cf committed=0618bb5011cf SAME
  irrigation-plus-card-impl.js built=dd8f325f5628 committed=dd8f325f5628 SAME
  irrigation-plus-card.js built=ca776b0a4d18 committed=ca776b0a4d18 SAME
  irrigation-plus-card-legacy.js built=df654e9711f3 committed=df654e9711f3 SAME
  ```

- `git diff --stat -- $D` gegen den Index, also den Elternstand: genau `irrigation-plus-card-impl.js | 2 +-` und
  `irrigation-plus.js | 1601`, zusammen `812 insertions(+), 791 deletions(-)`. Das ist aus dem Commit-Stat von
  `70dc0c18` (gleich dem von `58d6b7b5`) abgeleitet (829 − 8 × 2 − 1 = 812 Einfügungen; alle 791 Löschungen sind dist),
  nicht separat gemessen. `git diff --stat 2b2c403b 70dc0c18 -- …/frontend/dist` ergibt dieselben
  `2 files changed, 812 insertions(+), 791 deletions(-)` (gemessen 19.09. abends).
- `git status --short` kann zusätzlich `irrigation-plus-card.js` und `irrigation-plus-card-legacy.js` zeigen. Das sind
  nur Zeilenenden (Revision 2, Task 12 Step 8: `git diff --numstat` für beide leer).

Weicht eine Zeile auf `DIFF` ab: STOPP. Dann Node-Version, `npm ci` und den Stand der Quellen prüfen.

- [ ] **Step 5: Zeilenenden-Rauschen zurücksetzen, die zwei Bundles stagen, Stichprobe**

```bash
cd D:/Entwicklung/HASI/HAsmartirrigation
D=custom_components/irrigation_plus/frontend/dist
git checkout -- $D/irrigation-plus-card.js $D/irrigation-plus-card-legacy.js
git add -f $D/irrigation-plus.js $D/irrigation-plus-card-impl.js
cd $D
grep -o "Latency margin" irrigation-plus.js | wc -l             # 1
grep -o "Latency margin" irrigation-plus-card-impl.js | wc -l   # 1
grep -o "_showLatencyMargin" irrigation-plus.js | wc -l         # 2
grep -o "Latenz-Marge" irrigation-plus.js | wc -l               # 0 (de wird zur Laufzeit geladen)
```

Die vier Zahlen sind am 19.09. an den committeten Bundles von `58d6b7b5` gemessen (Planerstellung); `70dc0c18` hat
dieselben Bundles. `Latency margin` kommt in `irrigation-plus-card.js` und `irrigation-plus-card-legacy.js` je 0-mal
vor.

- [ ] **Step 6: Python-Suiten, vitest, Lint, Baumvergleich**

```bash
cd D:/Entwicklung/HASI/HAsmartirrigation
mkdir -p D:/Entwicklung/HASI/pr139-work/tmp D:/Entwicklung/HASI/pr139-work/npm-cache && export TEMP=D:/Entwicklung/HASI/pr139-work/tmp TMP=D:/Entwicklung/HASI/pr139-work/tmp TMPDIR=D:/Entwicklung/HASI/pr139-work/tmp npm_config_cache=D:/Entwicklung/HASI/pr139-work/npm-cache
SRC=70dc0c18
D:/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests/test_service_watch.py tests/test_finish_grace_helpers.py tests/test_run_in_flight.py tests/test_confirm_reserve.py tests/test_self_closing.py tests/test_run_watch.py tests/test_observed_watering.py tests/test_i18n_completeness.py -p _local_socket_unblock -q -p no:cacheprovider --tb=line -rfE > D:/Entwicklung/HASI/pr139-work/replay/T12-suites.txt 2>&1
grep -E "^(FAILED|ERROR) | passed" D:/Entwicklung/HASI/pr139-work/replay/T12-suites.txt | sed 's/ - .*//'
(cd custom_components/irrigation_plus/frontend && npx vitest run 2>&1 | grep -E "Test Files|Tests ")
uvx black --check custom_components/irrigation_plus/ $(git diff --name-only 2b2c403b -- tests)
uvx ruff check custom_components/irrigation_plus/
git diff "$SRC" --stat
git diff --cached "$SRC" --stat
```

Erwartet:
- die sieben Suiten plus i18n laut `rev3/evidence.md`, T12, und `dry6-logs/percommit.md`, `70dc0c18`:

  ```
  ERROR tests/test_service_watch.py::TestOneOffSampleIsNotEvidenceTheWaterStopped::test_the_run_is_not_settled_before_the_window_is_out
  ======================== 300 passed, 1 error in 19.92s ========================
  ```

- vitest laut `dry6-logs/full-suite.md`, `70dc0c18`:

  ```
   Test Files  23 passed (23)
        Tests  624 passed (624)
  ```

- Lint: `73 files would be left unchanged.`, `All checks passed!` (`scratch/dry5-checks.log`; am dry6-Endstand mit
  derselben Dateiliste nachgemessen, 19.09. abends).
- Beide Diffs leer: der Baum, einschließlich der zwei gebauten Bundles, ist der von `70dc0c18`.
- `git status --short` zeigt bis hierher die 11 gestagten Dateien als `M ` und `?? docs/SESSION-STAND.md`; nach dem
  Commit in Step 7 bleibt nur `?? docs/SESSION-STAND.md`.

- [ ] **Step 7: Commit mit derselben Nachricht**

```bash
cd D:/Entwicklung/HASI/HAsmartirrigation
SRC=70dc0c18
git log -1 --format=%B "$SRC" | git commit -q -F -
test "$(git rev-parse HEAD^{tree})" = "$(git rev-parse "$SRC^{tree}")" && echo TREE-SAME
diff <(git log -1 --format=%B HEAD) <(git log -1 --format=%B "$SRC") && echo MSG-SAME
git log -1 --format=%B | grep -c '^#'     # 0
git show --stat --format= HEAD | tail -1  # 11 files changed, 829 insertions(+), 791 deletions(-)
git diff "$SRC" HEAD --stat               # leer
git log --oneline -1                      # neuer SHA, Betreff des Tasks
git status --short                        # nur: ?? docs/SESSION-STAND.md
```

Nach diesem Commit ist `fix/backstop-grace` baumgleich mit `dry6/backstop-grace`: `git diff dry6/backstop-grace HEAD
--stat` ist leer. Die Commits unterscheiden sich nur in Zeitstempeln und SHAs.

**Mutationsproben (Probelauf)**

Die Proben stammen aus Revision 2, Plan Task 12 Step 10: Sicherung `mut/t12-{probe}.bak`, Ersetzung mit
`D:/Entwicklung/HASI/pr139-work/mut/mutate.py`, Wiederherstellung mit SHA-256-Prüfung. Getestet wird
`tests/test_i18n_completeness.py`. Die `latency_margin_help`-Zeile kommt in `sk.json` und `fr.json` auf `dry5` und
`dry6` je genau einmal vor (geprüft am 19.09. bzw. 19.09. abends mit `rev3_probes.py --count`). Die Zählungen aus Revision 2 (`1 failed, 64 passed` auf `0b418644`) gelten nicht, weil
sich die Testdatei seitdem geändert hat. Hier stehen deshalb nur der fangende Test und die Meldung. In der
Schlussprüfung (Task 13) laufen die Proben erneut.

| Probe | Änderung (Suchtext --> Ersatz) | gefangen von (Revision 2) |
|---|---|---|
| sk-help-missing | in `sk.json` die ganze `latency_margin_help`-Zeile (8 Leerzeichen Einrückung, bis einschließlich `,` und Zeilenende) --> leer | `test_no_missing_keys[panel-sk]`: `sk.json is missing 1 key(s) present in en.json; … ['panels.zones.labels.latency_margin_help']` |
| fr-help-english | in `fr.json` die `latency_margin_help`-Zeile --> dieselbe Zeile mit dem englischen Wert (Schlüssel, Einrückung und Komma bleiben) | `test_no_value_is_left_as_the_english_string[panel-fr]`: `fr.json has 1 value(s) identical to the English text: ['.panels.zones.labels.latency_margin_help']` |

Ergebnis: 2 Proben, 2 gefangen. Für dist gibt es keine Mutationsprobe. Die Prüfung dort ist die Byte-Gleichheit aus
Step 4, und in der Schlussprüfung der erneute Build gegen den Endstand.

---

## Teil 3: Abschluss — Task 13 bis 15

Teil von Plan-Revision 3 (2026-09-19). Grundlage ist `rev3/spec.md` (Revision 3). Alle Zahlen stammen aus
realen Messungen; die Quelle steht jeweils dabei. Was nicht gemessen wurde, heißt „nicht gemessen“.

**Konventionen dieses Teils**

- Git läuft in `D:/Entwicklung/HASI/HAsmartirrigation` auf `fix/backstop-grace`. Die Basis ist `2b2c403b`
  (= `upstream/master`, „fix(skip): examine rain from the run's start …“ (#146)).
- Referenz ist `dry6/backstop-grace` (`70dc0c18`) im Worktree `D:/Entwicklung/HASI/pr139-work/dry2`. Der
  Nachvollzug (Teile a und b) übernimmt Test- und Produktivdateien aus den dry6-Commits. Deshalb gelten die auf dry6
  gemessenen Zahlen als Erwartung für den echten Branch, solange Step 1 von Task 13 gleiche Bäume zeigt. Produktivcode
  und dist von dry6 sind byte-gleich mit `dry5/backstop-grace` (`58d6b7b5`); wo eine Zahl nur auf dry5 gemessen
  wurde und von den Tests nicht abhängt (dist-Hashes, black-Dateimenge, Zeilen im Produktivcode), steht das dabei.
- Jeder Block, der pytest, npm oder vitest startet, beginnt nach seinem `cd` mit
  `mkdir -p D:/Entwicklung/HASI/pr139-work/tmp D:/Entwicklung/HASI/pr139-work/npm-cache && export TEMP=D:/Entwicklung/HASI/pr139-work/tmp TMP=D:/Entwicklung/HASI/pr139-work/tmp TMPDIR=D:/Entwicklung/HASI/pr139-work/tmp npm_config_cache=D:/Entwicklung/HASI/pr139-work/npm-cache`
  (Laufwerk C: ist fast voll).
- Test: `D:/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest <Dateien> -p _local_socket_unblock -q`.
  Lint: `uvx black --check custom_components/irrigation_plus/ <berührte Tests>` und
  `uvx ruff check custom_components/irrigation_plus/`.
- Die Tasks T3b, T6 und T10 sind **gestrichen**. Ihre Nummern bleiben frei, es gibt keine Tests und keine
  Proben von ihnen. Seit dry6 pinnt ein Test in T5 den Fall, den T6 geändert hätte; die Probe dazu
  (`t6-backstop-settles-on-stored-off`) gehört zu T5.
- Der vorbestehende Error, der in jedem Lauf mit `tests/test_service_watch.py` auftaucht:
  `TestOneOffSampleIsNotEvidenceTheWaterStopped::test_the_run_is_not_settled_before_the_window_is_out`
  (`Lingering timer after job <Job call_later 5 …>`). Er steht schon in der Basis (`rev3/evidence.md`).
- Nach außen geht nichts ohne Freigabe im Chat: kein push, kein `gh`, kein Post, kein Issue. Auf HA-Prod
  schreibt, installiert und startet Claude nur nach ausdrücklicher Freigabe. HA-Test ist für den Live-Test
  freigegeben (User 19.09.). Vor jedem schreibenden MCP-Aufruf wird die Instanz genannt.

**Quellen der Zahlen**

| Kürzel | Datei |
|---|---|
| Basis-Suite | `D:/Entwicklung/HASI/pr139-work/baseline-2b2c403b.txt` (19.09.) |
| dry6-Suite | `D:/Entwicklung/HASI/pr139-work/after-dry6.txt` (19.09. abends; Auswertung `dry6-logs/full-suite.md`) |
| dry6-Prüfungen | `D:/Entwicklung/HASI/pr139-work/dry6-logs/percommit.md` (Suiten, black/ruff je Commit), `full-suite.md` (volle Suite, vitest) |
| dry5-Prüfungen | `D:/Entwicklung/HASI/pr139-work/scratch/dry5-checks.log` (Skript `scratch/dry5-checks.sh`): dist-Hashes, black mit der Dateiliste dieses Plans, T2-Suiten |
| RED/GREEN je Task | `D:/Entwicklung/HASI/pr139-work/rev3/evidence.md` (T1/T2 von dry5, T3–T12 von dry6) |
| Proben T5/T7/T8/T9 | `dry3-logs/T5.md`, `T7.md`, `T7-probes-table.md`, `T7-t5probe-rerun.txt`, `T8.md`, `T9.md` |
| Proben dry6 | `dry6-logs/T3.md` (Backstop, Echt-Timer-Test), `T5.md` (T6-Pin), `probes.md` (T2, T7, T11), `killmap.md` (Item --> Probe) |
| Proben T1–T5 (Rev. 2), T11, T12 | alter Plan `archive-wt/docs/superpowers/plans/2026-09-15-backstop-grace.md`, Task 1 Step 10, Task 2 Step 10, Task 3 Step 12, Task 4 Step 9, Task 5 Step 9, Task 11 Step 13, Task 12 Step 10, Task 13 Step 7 |
| Planungsmessungen 19.09. | am 19.09. beim Schreiben dieses Teils lesend auf dry5 erhoben (Suchtext-Zählung, Hygiene-Greps, Zählung je Datei aus den zwei Suite-Dateien); unten jeweils „gemessen 19.09. auf dry5“ |
| Planungsmessungen 19.09. abends | bei der Umstellung auf dry6 lesend im Worktree `dry2` erhoben (Hygiene-Greps, Zählung je Datei, `rev3_probes.py --count`, Grundzahlen der Probenläufe ohne Mutation, black am Endstand); unten jeweils „gemessen 19.09. abends auf dry6“ |

---

### Task 13: Schlussprüfung

Keine neue Produktionslogik. Dieser Task prüft den Endstand von T1–T12 auf `fix/backstop-grace` gegen die
Basis `2b2c403b`:

- Lint und volle Suite gegen eine Basis vom selben Tag
- vitest und Reproduzierbarkeit von dist
- jeden Commit einzeln
- Text-Hygiene und Schwester-Pfade
- alle Mutationsproben, jetzt auf dem echten Branch (E9)

Deckt ein Schritt einen Defekt auf, gilt: eigener Commit mit Test, dann Step 2–5 erneut. Nach drei
fehlgeschlagenen Fix-Versuchen am selben Punkt ist STOPP (3-Fix-Regel).

**Files:** keine Änderung im Repo. Messdateien und der Probe-Treiber liegen außerhalb des Repos unter
`D:/Entwicklung/HASI/pr139-work/`.

- [ ] **Step 1: Stand prüfen und Nachvollzug belegen**

```bash
cd /d/Entwicklung/HASI/HAsmartirrigation
git status --short
git rev-parse --abbrev-ref HEAD
git merge-base --is-ancestor 2b2c403b HEAD && echo base-ok
git log --oneline --reverse 2b2c403b..HEAD
for c in $(git rev-list --reverse 2b2c403b..HEAD); do git show --stat --format="%h %s" $c | sed -n '1p;$p'; done
git diff --stat 2b2c403b HEAD | tail -1
git diff --stat 2b2c403b HEAD -- custom_components/irrigation_plus/frontend/dist | tail -1
paste <(git rev-list --reverse 2b2c403b..dry6/backstop-grace) <(git rev-list --reverse 2b2c403b..HEAD) | while read a b; do git diff --quiet $a $b && echo "same $(git log -1 --format=%s $b)" || echo "DIFF $a $b"; done
git diff --stat dry6/backstop-grace HEAD
for c in $(git rev-list 2b2c403b..HEAD); do git log -1 --format=%B $c | grep -q '^#' && echo "HASHLINE $c"; done; echo hash-check-done
```

Erwartet:

- `git status --short` ist leer bis auf `?? docs/SESSION-STAND.md`.
- Branch `fix/backstop-grace`, dann `base-ok`.
- Zehn Commits in dieser Reihenfolge, je Task genau einer. Die Statistik stammt von dry6 (19.09. abends) und muss
  gleich sein:

| Task | dry6-Commit | Betreff | `git show --stat` |
|---|---|---|---|
| T1 | `ca77c287` | `feat(service): add a per-zone latency margin setting for confirmed valves` | 5 files, +126 |
| T2 | `a6a9e382` | `feat(run-watch): add the finish-grace run keys, policy flag and helpers` | 4 files, +394 |
| T3 | `c6a4c842` | `feat(service): wait out the finish grace before a confirmed run's backstop` | 2 files, +259 −2 |
| T4 | `dd43f09c` | `feat(run-watch): record a confirmed valve's own off report` | 2 files, +233 −3 |
| T5 | `c234fb23` | `feat(run-watch): settle a confirmed service run on its valve window` | 3 files, +350 −7 |
| T7 | `f1266999` | `feat(service): measure a manual stop on the valve's own window` | 2 files, +510 −6 |
| T8 | `4819d2fc` | `feat(service): carry the finish grace across a restart` | 2 files, +360 −5 |
| T9 | `0c0c9416` | `feat(service): keep a confirmed run in flight through its finish grace` | 2 files, +291 −2 |
| T11 | `0e68d978` | `feat(panel): add latency margin field for confirmed service zones` | 4 files, +144 |
| T12 | `70dc0c18` | `feat(i18n): translate and document the latency margin zone field` | 11 files, +829 −791 |

- Gesamt-Diff `26 files changed, 3490 insertions(+), 810 deletions(-)`, davon dist
  `2 files changed, 812 insertions(+), 791 deletions(-)` (`irrigation-plus.js` und
  `irrigation-plus-card-impl.js`; gemessen 19.09. abends auf dry6).
- Zehnmal `same <Betreff>`, und `git diff --stat dry6/backstop-grace HEAD` gibt nichts aus. Damit ist der
  Nachvollzug baumgleich, und alle dry6-Zahlen unten gelten.
- Keine `HASHLINE`-Zeile, nur `hash-check-done` (auf dry6 gemessen 19.09. abends: keine Zeile, die mit `#` beginnt).

Druckt die Schleife ein `DIFF`: STOPP. Welche Datei abweicht, zeigt `git diff --stat <a> <b>`. Der Nachvollzug
dieses Tasks ist dann nicht baumgleich; das ist vor allem anderen zu klären.

- [ ] **Step 2: Lint (nur prüfen)**

```bash
cd /d/Entwicklung/HASI/HAsmartirrigation
uvx black --check custom_components/irrigation_plus/ $(git diff --name-only 2b2c403b HEAD -- tests)
uvx ruff check custom_components/irrigation_plus/
```

Erwartet: `73 files would be left unchanged.` und `All checks passed!` (gemessen 19.09. abends auf dry6 mit genau
diesen zwei Befehlen; ebenso dry5-Prüfungen, Commit T12). Die
berührten Tests sind `tests/test_distributor_integration.py`, `tests/test_finish_grace_helpers.py`,
`tests/test_run_in_flight.py`, `tests/test_service_watch.py` und `tests/test_store_self_closing.py`.

- [ ] **Step 3: Volle Suite gegen eine Basis vom selben Tag**

Es gibt datumsabhängige Tests. Die Basis wird deshalb am Tag der Schlussprüfung neu gemessen, in einem
temporären Worktree. Dauer je Lauf etwa 4 min. Die Läufe laufen nacheinander, nicht parallel.

```bash
cd /d/Entwicklung/HASI/HAsmartirrigation
mkdir -p D:/Entwicklung/HASI/pr139-work/tmp D:/Entwicklung/HASI/pr139-work/npm-cache && export TEMP=D:/Entwicklung/HASI/pr139-work/tmp TMP=D:/Entwicklung/HASI/pr139-work/tmp TMPDIR=D:/Entwicklung/HASI/pr139-work/tmp npm_config_cache=D:/Entwicklung/HASI/pr139-work/npm-cache
W=/d/Entwicklung/HASI/pr139-work
D=$(date +%m%d)
git worktree add --detach $W/base 2b2c403b
cp _local_socket_unblock.py $W/base/
(cd $W/base && /d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests -p _local_socket_unblock -q -rfE -p no:cacheprovider > $W/baseline-2b2c403b-$D.txt 2>&1)
./.venv/Scripts/python.exe -m pytest tests -p _local_socket_unblock -q -rfE -p no:cacheprovider > $W/after-real-$D.txt 2>&1
B=$W/baseline-2b2c403b-$D.txt; A=$W/after-real-$D.txt
grep -m1 "^collected" $B; grep -m1 "^collected" $A
tail -1 $B; tail -1 $A
diff <(grep "^FAILED" $B | sed 's/ - .*//' | sort -u) <(grep "^FAILED" $A | sed 's/ - .*//' | sort -u) && echo FAILED-same
diff <(grep "^ERROR" $B | sed 's/ - .*//' | sort -u) <(grep "^ERROR" $A | sed 's/ - .*//' | sort -u) && echo ERROR-same
grep -c "^ERROR" $A; grep "^ERROR" $A | sed 's/ - .*//' | sort -u | wc -l
```

Der Basis-Worktree bleibt für Step 4 (vitest der Basis) stehen und wird dort entfernt.

Erwartet (Basis-Suite vom 19.09. und dry6-Suite vom 19.09. abends; gilt so, wenn die Prüfung am 19.09. läuft; die
letzten vier Zeilen mit genau diesen Befehlen gegen `after-dry6.txt` gemessen):

```
collected 3022 items
collected 3115 items
= 7 failed, 3006 passed, 9 skipped, 10 warnings, 320 errors in 240.90s (0:04:00) =
= 7 failed, 3099 passed, 9 skipped, 10 warnings, 320 errors in 241.66s (0:04:01) =
FAILED-same
ERROR-same
326
322
```

An einem anderen Tag können die Absolutzahlen beider Läufe gleich wandern. Das Kriterium ist:

- identische FAILED- und ERROR-Namensmengen, und
- `collected` sowie `passed` je +93.

Die 7 FAILED sind vorbestehend (Namensliste in der Basis-Suite) und lokale Windows-Fehler, keine Lingering timer: sechs
scheitern am Event-Loop (`RuntimeError: aiodns needs a SelectorEventLoop on Windows`, dazu
`ModuleNotFoundError: No module named 'winloop'`), einer an Windows-Pfadtrennern (`test_panel.py`, `'\\config\\…'`);
nachgelesen 19.09. abends in `baseline-2b2c403b.txt`:

- `tests/test_init.py` ×2
- `tests/test_next_irrigation_sensor.py` ×1
- `tests/test_opensprinkler_teardown.py` ×3
- `tests/test_panel.py` ×1

Die 320 Errors sind lokale `Lingering timer`-Teardowns unter HA 2024.12: alle 320 Abschnitte `ERROR at teardown of …`
in `baseline-2b2c403b.txt` enthalten `Lingering timer` (gezählt 19.09. abends). `grep -c "^ERROR"` zählt 326, weil
sechs Logzeilen `ERROR:custom_components…`/`ERROR    custom_components…` aus `test_batch.py` mitgezählt werden; die
eindeutigen Zeilen sind 322 (320 Testnamen und zwei Formen derselben Logzeile aus `test_batch.py`; nachgezählt
19.09. abends auf `after-dry6.txt`: `grep "^ERROR tests" | sed 's/ - .*//' | sort -u | wc -l` = 320, 320 + 6 = 326).
Die „321 ERROR-Namen“ in `dry6-logs/full-suite.md` zählen mit `^(FAILED|ERROR) ` (Leerzeichen) nur die Form
`ERROR    custom_components…` mit: 320 Tests + 1 Logzeile.

Delta je Datei, gezählt aus den Fortschrittszeilen:

```bash
cd /d/Entwicklung/HASI/HAsmartirrigation
mkdir -p D:/Entwicklung/HASI/pr139-work/tmp D:/Entwicklung/HASI/pr139-work/npm-cache && export TEMP=D:/Entwicklung/HASI/pr139-work/tmp TMP=D:/Entwicklung/HASI/pr139-work/tmp TMPDIR=D:/Entwicklung/HASI/pr139-work/tmp npm_config_cache=D:/Entwicklung/HASI/pr139-work/npm-cache
D=$(date +%m%d)
./.venv/Scripts/python.exe - /d/Entwicklung/HASI/pr139-work/baseline-2b2c403b-$D.txt /d/Entwicklung/HASI/pr139-work/after-real-$D.txt <<'EOF'
import re, sys
P = re.compile(r"^(tests\S+\.py) ([.EFsxX]*) *\[ *\d+%\]\s*$"); C = re.compile(r"^([.EFsxX]+) *\[ *\d+%\]\s*$")
def parse(fn):
    d, cur = {}, None
    for l in open(fn, encoding="utf-8", errors="replace").read().splitlines():
        m = P.match(l)
        if m: cur = m.group(1).replace("\\", "/"); d[cur] = d.get(cur, "") + m.group(2); continue
        m = C.match(l)
        if m and cur: d[cur] += m.group(1)
    return d
b, a = parse(sys.argv[1]), parse(sys.argv[2]); k = lambda s: (s.count("."), s.count("E"), s.count("F"))
print("files", len(b), len(a))
for f in sorted(set(a) | set(b)):
    if f not in b or k(b[f]) != k(a[f]): print(f, k(b[f]) if f in b else "-", k(a[f]))
EOF
```

Erwartet (gemessen 19.09. abends mit genau diesem Skript, Basis-Suite gegen dry6-Suite):

```
files 155 156
tests/test_distributor_integration.py (19, 0, 0) (20, 0, 0)
tests/test_finish_grace_helpers.py - (30, 0, 0)
tests/test_run_in_flight.py (19, 0, 0) (27, 0, 0)
tests/test_service_watch.py (17, 1, 0) (69, 1, 0)
tests/test_store_self_closing.py (6, 0, 0) (8, 0, 0)
```

| Datei | Basis | Endstand | + | Aus Task (Zahl neuer Items laut `rev3/evidence.md`) |
|---|---|---|---|---|
| `tests/test_service_watch.py` | 17 (+1 E) | 69 (+1 E) | 52 | T3 11, T4 8, T5 10, T7 13, T8 10 |
| `tests/test_finish_grace_helpers.py` (neu) | — | 30 | 30 | T2 (26 Funktionen, eine parametrisiert zu 5) |
| `tests/test_run_in_flight.py` | 19 | 27 | 8 | T9 |
| `tests/test_store_self_closing.py` | 6 | 8 | 2 | T1 |
| `tests/test_distributor_integration.py` | 19 | 20 | 1 | T1 |
| **Summe** | | | **93** | |

Jede andere Datei ist gegen die Basis unverändert (das Skript listet sie nicht). Stichproben für „Batch,
OpenSprinkler und Bestand unberührt“ (passed / E / F, Basis = Endstand, gemessen 19.09. aus den Suite-Dateien, am
Abend gegen `after-dry6.txt` wiederholt, gleiche Werte):

| Datei | Basis = Endstand |
|---|---|
| `tests/test_batch.py` | 61 / 38 / 0 |
| `tests/test_opensprinkler.py` | 67 / 13 / 0 |
| `tests/test_opensprinkler_teardown.py` | 3 / 0 / 3 |
| `tests/test_self_closing.py` | 38 / 0 / 0 (Pins `(2, 600.0)`, `(2, 500.0)`, `(2, 300.0)`, `(2, 263.0)`) |
| `tests/test_confirm_reserve.py` | 22 / 0 / 0 (T10 gestrichen, kein Pin 30 --> 39) |
| `tests/test_credit_ceiling.py` | 38 / 0 / 0 |
| `tests/test_run_watch.py` | 14 / 0 / 0 |
| `tests/test_observed_watering.py` | 34 / 0 / 0 |
| `tests/test_service_chain.py` | 25 / 1 / 0 |
| `tests/test_master.py` | 19 / 0 / 0 |
| `tests/test_stop_zone.py` | 13 / 0 / 0 |
| `tests/test_i18n_completeness.py` | 66 / 0 / 0 |
| `tests/test_panel.py` | 7 / 0 / 1 |

Ein neuer FAILED oder ERROR ist ein Defekt dieses Plans: nicht weiter, zuerst am Basis-Worktree gegenprüfen.

- [ ] **Step 4: Frontend — npm ci, Build, dist reproduziert, vitest (Endstand und Basis)**

```bash
cd /d/Entwicklung/HASI/HAsmartirrigation/custom_components/irrigation_plus/frontend
mkdir -p D:/Entwicklung/HASI/pr139-work/tmp D:/Entwicklung/HASI/pr139-work/npm-cache && export TEMP=D:/Entwicklung/HASI/pr139-work/tmp TMP=D:/Entwicklung/HASI/pr139-work/tmp TMPDIR=D:/Entwicklung/HASI/pr139-work/tmp npm_config_cache=D:/Entwicklung/HASI/pr139-work/npm-cache
node --version
npm ci && npm run build
cd /d/Entwicklung/HASI/HAsmartirrigation
D=custom_components/irrigation_plus/frontend/dist
for f in irrigation-plus.js irrigation-plus-card-impl.js irrigation-plus-card.js irrigation-plus-card-legacy.js; do a=$(tr -d '\r' < $D/$f | sha256sum | cut -c1-12); b=$(git show HEAD:$D/$f | tr -d '\r' | sha256sum | cut -c1-12); echo "$f built=$a committed=$b $([ $a = $b ] && echo SAME || echo DIFF)"; done
git checkout -- $D
git status --short --untracked-files=no
cd custom_components/irrigation_plus/frontend && npx vitest run 2>&1 | grep -E "Test Files|Tests "
```

Erwartet (dist-Hashes aus den dry5-Prüfungen, 19.09.; dry6 hat dieselben dist-Bytes; vitest aus
`dry6-logs/full-suite.md`):

- Node `v24.15.0`; er reproduziert die Node-22-CI byte-genau.
- `npm run build` endet mit `created dist in …`.
- Die Hash-Schleife:

```
irrigation-plus.js built=0618bb5011cf committed=0618bb5011cf SAME
irrigation-plus-card-impl.js built=dd8f325f5628 committed=dd8f325f5628 SAME
irrigation-plus-card.js built=ca776b0a4d18 committed=ca776b0a4d18 SAME
irrigation-plus-card-legacy.js built=df654e9711f3 committed=df654e9711f3 SAME
```

- `git status --short --untracked-files=no` ist danach leer.
- vitest:

```
 Test Files  23 passed (23)
      Tests  624 passed (624)
```

Die Basiszahl `22 / 616` stammt aus dem Workflow-Auftrag vom 19.09.; in `pr139-work` gibt es dazu kein
Protokoll. Weil der PR-Text sie zitiert, wird sie hier im Basis-Worktree aus Step 3 gemessen. Danach wird
dieser Worktree entfernt:

```bash
cd /d/Entwicklung/HASI/pr139-work/base/custom_components/irrigation_plus/frontend
mkdir -p D:/Entwicklung/HASI/pr139-work/tmp D:/Entwicklung/HASI/pr139-work/npm-cache && export TEMP=D:/Entwicklung/HASI/pr139-work/tmp TMP=D:/Entwicklung/HASI/pr139-work/tmp TMPDIR=D:/Entwicklung/HASI/pr139-work/tmp npm_config_cache=D:/Entwicklung/HASI/pr139-work/npm-cache
npm ci && npx vitest run 2>&1 | grep -E "Test Files|Tests " | tee /d/Entwicklung/HASI/pr139-work/vitest-base-$(date +%m%d).txt
cd /d/Entwicklung/HASI/HAsmartirrigation
git worktree remove --force /d/Entwicklung/HASI/pr139-work/base
git worktree list | grep -c "pr139-work/base"
```

Erwartet: `Test Files  22 passed (22)` / `Tests  616 passed (616)` (Wert aus dem Workflow-Auftrag, bis hierher
ohne Protokoll), danach `0`. Weicht die Basiszahl ab, gilt die gemessene: +1 Datei und +8 Tests aus T11.

Weicht eine dist-SHA ab (`DIFF`), ist das Bundle aus T12 veraltet. Dann wird es mit `git add -f` in einem
eigenen `build(frontend):`-Commit nachgezogen, und Step 1–5 laufen erneut.

- [ ] **Step 5: Jeder Commit einzeln**

```bash
cd /d/Entwicklung/HASI/HAsmartirrigation
mkdir -p D:/Entwicklung/HASI/pr139-work/tmp D:/Entwicklung/HASI/pr139-work/npm-cache && export TEMP=D:/Entwicklung/HASI/pr139-work/tmp TMP=D:/Entwicklung/HASI/pr139-work/tmp TMPDIR=D:/Entwicklung/HASI/pr139-work/tmp npm_config_cache=D:/Entwicklung/HASI/pr139-work/npm-cache
test -z "$(git status --short --untracked-files=no)" || { echo DIRTY; exit 1; }
SEVEN="tests/test_service_watch.py tests/test_finish_grace_helpers.py tests/test_run_in_flight.py tests/test_confirm_reserve.py tests/test_self_closing.py tests/test_run_watch.py tests/test_observed_watering.py tests/test_i18n_completeness.py"
for c in $(git rev-list --reverse 2b2c403b..fix/backstop-grace); do
  git checkout -q --detach $c
  echo "-- $(git log --oneline -1)"
  uvx black --check custom_components/irrigation_plus/ $(git diff --name-only 2b2c403b HEAD -- tests) 2>&1 | tail -1
  uvx ruff check custom_components/irrigation_plus/ 2>&1 | tail -1
  F=""; for f in $SEVEN; do [ -f "$f" ] && F="$F $f"; done
  [ "$(git log -1 --format=%s)" = "feat(service): add a per-zone latency margin setting for confirmed valves" ] && F="$F tests/test_store_self_closing.py tests/test_distributor_integration.py"
  ./.venv/Scripts/python.exe -m pytest $F -p _local_socket_unblock -q -p no:cacheprovider 2>&1 | tail -1
done
git checkout -q fix/backstop-grace
git status --short --untracked-files=no
```

Erwartet: ruff jedes Mal `All checks passed!`. Die Suiten T3–T12 stammen aus `dry6-logs/percommit.md`, T2 aus den
dry5-Prüfungen (derselbe Commit), T1 aus `replaycheck-logs/T01-suites.txt` (19.09.). black stammt aus den
dry5-Prüfungen mit genau dieser Dateiliste; dry6 fügt keine Testdatei hinzu, und am dry6-Endstand ergab sie 73 (gemessen 19.09. abends).
`dry6-logs/percommit.md` prüfte black mit einer anderen Liste (`custom_components/irrigation_plus/` plus die Testdateien
des Commits: 69 bzw. 68 Dateien, alle unverändert).

| Commit | black | 7 Suiten + i18n (vorhandene Dateien) |
|---|---|---|
| T1 | `70 files would be left unchanged.` | `238 passed, 1 error` (mit T1s eigenen zwei Dateien; `replaycheck-logs/T01-suites.txt`, 19.09., `238 passed, 1 error in 15.11s` — das dry5-Protokoll zeigt für T1 `no tests ran`, weil seine Liste die bei T1 noch fehlende Helferdatei enthielt) |
| T2 | `71 files …` | `240 passed, 1 error` |
| T3 | `72 files …` | `251 passed, 1 error` |
| T4 | `72 files …` | `259 passed, 1 error` |
| T5 | `72 files …` | `269 passed, 1 error` |
| T7 | `72 files …` | `282 passed, 1 error` |
| T8 | `72 files …` | `292 passed, 1 error` |
| T9 | `73 files …` | `300 passed, 1 error` |
| T11 | `73 files …` | `300 passed, 1 error` |
| T12 | `73 files …` | `300 passed, 1 error` |

Der eine Error ist jedes Mal der vorbestehende Lingering timer (siehe Konventionen). Am Ende ist
`git status --short --untracked-files=no` leer, und der Branch steht wieder auf `fix/backstop-grace`.

- [ ] **Step 6: Text-Hygiene**

```bash
cd /d/Entwicklung/HASI/HAsmartirrigation
X=':!custom_components/irrigation_plus/frontend/dist'
git diff 2b2c403b HEAD -- custom_components tests docs | grep -cE "HA-Prod|HA-Test|Eifel|192\.168|Kirschlorbeer|Beet|[0-9a-f]{8,}"
git diff 2b2c403b HEAD -- custom_components tests docs | grep -E "HA-Prod|HA-Test|Eifel|192\.168|Kirschlorbeer|Beet|[0-9a-f]{8,}" | grep -v "^index " | cut -c1-120
git diff 2b2c403b HEAD -- custom_components tests docs "$X" | awk '/^\+\+\+ /{f=$2} /^\+.*(Beet|beet|Kirschlorbeer|kirschlorbeer|Kirschbaum|Tuya|SONOFF|Sonoff)/{print f": "substr($0,1,110)}'
git diff 2b2c403b HEAD -- custom_components tests docs "$X" | grep -cE "^\+.*\b([0-9]{1,3}\.){3}[0-9]{1,3}\b"
git diff 2b2c403b HEAD -- custom_components tests docs "$X" | grep -cE "^\+.*(HA-Prod|HA-Test|Eifel|eifel)"
git diff 2b2c403b HEAD -- custom_components tests docs "$X" | grep -cE "^\+.*\b[0-9a-f]{7,40}\b"
git diff 2b2c403b HEAD -- tests | grep -cE "^\+.*(2026, 9, 13|422\.9|423\.4|beet_flowing)"
git grep -n "zone_finish_grace_seconds" HEAD; echo "(zone_finish_grace_seconds: Ende)"
git grep -nE "actual_s <= planned|actual_s<=planned|never (exceeds|more than) (the )?plan" HEAD -- custom_components tests docs; echo "(actual_s-Zusage: Ende)"
git diff 2b2c403b HEAD -- custom_components tests docs "$X" | grep -nE "^\+.*(window pricing|priced into|lockout|_note_si_valve|SI_VALVE_SUPPRESS|settle a reported close|backstop settle|zone_confirm_seconds)"; echo "(T3b/T6/T10-Reste: Ende)"
git diff 2b2c403b HEAD -- custom_components tests docs "$X" | grep -nE "^\+.*\b(T3b|T6|T10|SP-[0-9]+|dry[0-9])\b"; echo "(Task-Kürzel: Ende)"
for c in $(git rev-list --reverse 2b2c403b..HEAD); do git log -1 --format=%B $c; done | grep -nE "\b[0-9a-f]{7,40}\b|Beet|Kirschlorbeer|Kirschbaum|HA-Prod|HA-Test|Eifel|192\.168|dry[0-9]|T3b|\bT6\b|T10|SP-[0-9]|pricing|lockout"; echo "(Commit-Texte: Ende)"
for c in $(git rev-list --reverse 2b2c403b..HEAD); do git log -1 --format=%B $c; done | grep -c "Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

Erwartet (gemessen 19.09. auf dry5 gegen `2b2c403b`; am Abend mit denselben Befehlen auf dry6 wiederholt, gleiche
Ergebnisse bis auf Punkt 6):

1. `30` Treffer. Davon sind 26 `index …`-Zeilen (git-Metadaten). Es bleiben 4 Zeilen:
   - das `-`/`+`-Paar derselben minifizierten dist-Zeile (Zahlenfolgen im Bundle, keine SHA);
   - `tests/test_service_watch.py`: `"""The Beet valve: it reports its close 2-3 s after the planned end."""`;
   - `tests/test_store_self_closing.py`: `"name": "Beet",`.
2. Neun Zeilen mit Gerätenamen:

   | Datei | Zeile (gekürzt) |
   |---|---|
   | `custom_components/irrigation_plus/const.py` | `# planned window beat that report on every normal run (#139): measured Tuya valves` |
   | `custom_components/irrigation_plus/self_closing.py` | `# every normal run (measured 2-3 s late on Tuya valves) or inside` |
   | `tests/test_run_in_flight.py` | `return [call for call in calls if call.data["service"] == "irrigation_beet"]` |
   | `tests/test_service_watch.py` | `completed run discarded it for planned_s, so neither the late Tuya close nor` |
   | `tests/test_service_watch.py` | `"""The Beet valve: it reports its close 2-3 s after the planned end."""` |
   | `tests/test_service_watch.py` | `stops = async_mock_service(hass, "script", "stop_irrigation_beet")` |
   | `tests/test_store_self_closing.py` | `"name": "Beet",` / `"run_service": "script.irrigation_beet",` / `"confirm_entity": "valve.beet",` |

   Alle haben Präzedenz auf `2b2c403b` (gemessen 19.09. mit `git grep`):
   - `Tuya`: `const.py:546`, `:558`, dazu `blueprints/script/tuya_z2m_valve.yaml`;
   - `irrigation_beet`: `tests/test_service_watch.py:65/66/75/76`, `tests/test_self_closing.py:47/76`,
     `tests/test_credit_ceiling.py:55` und `tests/test_store_self_closing.py:63/85/103`;
   - `valve.beet`: `tests/test_self_closing.py:363/373/411`;
   - `"Beet"`: `tests/test_credit_ceiling.py:53`, `tests/test_binary_sensor.py:51` und weitere.

   Belassen. `Kirschlorbeer` und `Kirschbaum` kommen in keiner neuen Zeile vor.
3. Die vier Zählbefehle (IP, Instanz- und Kontonamen, Hex-Folge, Installationsdaten) geben je `0`.
4. `zone_finish_grace_seconds`: keine Ausgabe vor „Ende“ (Entscheidung (e)).
5. Keine Zusage `actual_s <= planned_s` (SP-5).
6. Genau eine Zeile vor „(T3b/T6/T10-Reste: Ende)“, seit dry6:
   `+    first, nor what the backstop settles when it does. Dropping the instance` — aus dem Docstring von
   `_the_real_backstop_from_here` (seit dry6 in T3). Das Muster `backstop settle` trifft „backstop settles“; der Satz
   beschreibt, was der Echt-Timer-Test sieht (den Abschluss für den Plan wie heute), und ist kein Rest von T6. Sonst
   keine Reste von Zeitfenster-Preis, Observed-Sperre oder T6.
7. Keine Task-Kürzel im Diff.
8. Commit-Texte ohne SHA, private Namen und Arbeitskürzel (auch die neuen Absätze von T3 und T5). `10` Trailer.

- [ ] **Step 7: Schwester-Pfade (nur lesend)**

Aktualisiert die Tabelle aus Plan-Revision 2, Task 13 Step 5, auf den neuen Code. Zeilennummern:
`dry5/backstop-grace`, gegrept am 19.09.; auf `dry6/backstop-grace` gleich, weil der Produktivcode byte-gleich ist.
Nach dem Nachvollzug stehen sie gleich (Step 1). „Tor“ heißt
`run_has_finish_grace`: Service-Policy mit `settles_on_valve_window`, `RUN_WATCH_ENTITY` und eingefrorene
`RUN_LATENCY_MARGIN`. „Wartezeit“ heißt Entprellung 5 s + Marge.

```bash
cd /d/Entwicklung/HASI/HAsmartirrigation/custom_components/irrigation_plus
grep -nE "_sc_schedule_cleanup\(|_sc_finish_run\(|async_stop_self_closing\(|_watch_evaluate\(|_self_closing_run_in_flight\(|_watch_settle_by_window\(|_watch_valve_window\(|zone_run_in_flight\(" --include=*.py -r . | grep -v "def "
grep -nE "RUN_PLANNED_SECONDS|planned_seconds\(" --include=*.py -r . | grep -v "^./const.py"
grep -nE "RUN_VALVE_OFF|RUN_VALVE_ON|RUN_LATENCY_MARGIN" --include=*.py -r . | grep -v "^./const.py"
grep -nE "run_has_finish_grace|run_finish_grace_seconds|run_completion_tolerance|valve_window_seconds|zone_latency_margin|run_latency_margin|settles_on_valve_window" --include=*.py -r . | grep -v "def "
grep -n "RUN_STARTED" --include=*.py -r . | grep -v "^./const.py"
grep -n "_note_si_valve(\|zone_confirm_seconds(" --include=*.py -r .
grep -nE "self\._sc_|self\._watch_|_note_si_valve|async_stop_self_closing" distributor.py | wc -l
```

**Wo der Backstop scharf wird (`_sc_schedule_cleanup`)**

| Stelle | Pfad | Stand | Task |
|---|---|---|---|
| `self_closing.py:701-703` | Dispatch `async_run_self_closing` (Service und OpenSprinkler) | `planned_seconds + run_finish_grace_seconds(record)`; ohne Tor +0 (OpenSprinkler, write-only, nicht prüfbarer Confirm) | T3 |
| `self_closing.py:1022` | Neustart, Service-Zweig (`elapsed` kleiner `planned + grace`) | `planned + grace - elapsed`, `grace` aus `:1001` | T8 |
| `self_closing.py:442-443` `_done` | Rückruf des Backstops | `_sc_finish_run(zone_id)` ohne `actual_s`, also `planned_s`, auch mit gespeicherter Aus-Meldung | bewusst unverändert (T6 gestrichen) |
| `run_watch.py:845` | `_watch_observed_start` | nur `not opens_at_dispatch` = OpenSprinkler | unverändert |
| `run_watch.py:902` | `_watch_resume` | nur `segmented` = Batch; `remaining` ohne Wartezeit (`:896`) | unverändert, Pin in T2 (`remaining_window_only`) |
| `opensprinkler.py:666` | OpenSprinkler-Neustart | — | unverändert |
| `run_window.py:266` | Docstring, kein Aufruf | — | — |

**Wer `RUN_PLANNED_SECONDS` / `planned_seconds()` liest**

| Stelle | Leser | Stand / Task |
|---|---|---|
| `run_watch.py:232-235` | Definition `planned_seconds()` | — |
| `run_watch.py:326` | `valve_window_seconds`: Deckel ohne Aus-Meldung, Rückgabe ohne Anker | T2 |
| `run_watch.py:357`, `:367` | `queue_deadline_seconds` (OpenSprinkler-Warteschlange) | unverändert |
| `run_watch.py:802` | `_watch_observed_start` (Observed-Sperre, OpenSprinkler-Backstop) | unverändert |
| `run_watch.py:896` | `_watch_resume` (Batch) | unverändert |
| `run_watch.py:981` | `_watch_settle_by_window` | T5 |
| `run_watch.py:1005` | `_watch_finish`, Basisregel | unverändert, gepinnt in T5 |
| `run_state.py:98` | In-flight-Fenster: `planned + run_finish_grace_seconds(run)` (`:106`) | T9 |
| `self_closing.py:373` | `_sc_finish_run`: Zeitvolumen (`:397`) und Kalibrierprobe (`:429`) bleiben bei `planned_s`; `actual_s` fällt auf `planned_s` zurück (`:410`) | T5 (nur der Parameter `actual_s`) |
| `self_closing.py:640` | Dispatch (schreibt) | — |
| `self_closing.py:847` | `async_stop_self_closing` (`delivered_frac`, Grenze vor/nach dem Ende) | T7 |
| `self_closing.py:978` | Neustart | T8 |
| `irrigation.py:383` | Panel-Countdown `ends_at` | bewusst unverändert (Spec) |
| `batch.py:353` (schreibt), `batch.py:719` | Batch | unverändert |
| `opensprinkler.py:619`, `:643` | OpenSprinkler | unverändert |

**Wo über abgeschlossen oder Teil-Lauf entschieden wird**

| Stelle | Entscheidung | Task |
|---|---|---|
| `run_watch.py:990` | `_watch_finish`: Tor UND gespeicherte `RUN_VALVE_OFF` --> `_watch_settle_by_window` | T5 (b) |
| `run_watch.py:980-984` | `_watch_settle_by_window`: `window + run_completion_tolerance(run) >= planned` --> `_sc_finish_run(zid, actual_s=window)`, sonst Teil-Lauf mit `actual_s=window` | T5 |
| `run_watch.py:1005-1014` | Basisregel `elapsed + 1 >= planned` (ohne Aus-Meldung oder ohne Tor) | unverändert |
| `self_closing.py:856-899` | Stopp: `actual_s` übergeben / `close_valve` UND Tor: (c) vor dem Ende `:870-876`, (d) in der Wartezeit `:893-897` / sonst `_sc_run_elapsed` | T7 |
| `self_closing.py:1002-1008` | Neustart ab `planned + grace`: `_sc_finish_run(zone_id)`, also `planned_s`, egal was gespeichert ist | T8 (a) |
| `self_closing.py:1020-1021` | Neustart: Master nur bei `elapsed` kleiner `planned` | T8 (f) |
| `self_closing.py:443` | Backstop | unverändert (s. o.) |
| `run_watch.py:1028` | `_watch_give_up` | für Service unerreichbar (kein Give-up-Timer), nur OpenSprinkler |
| `batch.py:557`, `:663`, `:753` | Batch | unverändert |
| `opensprinkler.py:499`, `:660` | OpenSprinkler | unverändert |

**Neue Laufdaten-Schlüssel** (außer `const.py`):

- `RUN_LATENCY_MARGIN`: geschrieben nur in `self_closing.py:663`, im Block, der `RUN_WATCH_ENTITY` setzt.
  Gelesen in `run_watch.py:281` (`run_latency_margin`).
- `RUN_VALVE_ON`: geschrieben in `self_closing.py:664` (über `_sc_valve_on_instant`, `:456`). Gelesen in
  `run_watch.py:328`.
- `RUN_VALVE_OFF`: geschrieben in `run_watch.py:751`, gelöscht in `:711`. Gelesen in `:335`, `:704`, `:724`
  und `:990`. Ausgeblendet in `self_closing.py:876` (Stopp vor dem Ende).
- Kommentare und Docstrings: `run_watch.py:322`, `:968`; `self_closing.py:538`, `:585`.

**`previous_state`:** Nur die Subscription (`run_watch.py:664`) reicht `old_state` weiter. Die erste
Auswertung (`:651`), `batch.py:611` und `opensprinkler.py:603` übergeben nichts und zeichnen deshalb nie auf
(E6). `unavailable`/`unknown` enden vorher in `NO_INFO_STATES`.

**Leser des In-flight-Fensters** (`zone_run_in_flight` --> `_self_closing_run_in_flight`, `run_state.py:140`),
alle mit Wartezeit seit T9:

- Dispatch `self_closing.py:517`
- `irrigation.py:1035` (`_drop_zones_already_running`) und `:3309` (`run_zone`)
- `batch.py:226`
- `calculation.py:464` und Wiederholung `run_state.py:183`
- `observed_watering.py:138`
- `run_chain.py:248` und `:408`

Der Anker bleibt `RUN_OBSERVED_START` bzw. `RUN_STARTED` (`run_state.py:109`).

**Bewusst unverändert, weil gestrichen:**

- Observed-Sperre `_note_si_valve` (T3b): `self_closing.py:528` mit `planned_seconds`, dazu
  `run_watch.py:823`, `batch.py:330` und `irrigation.py:1403/1513/1629/1692/2097`.
- Zeitfenster-Preis `zone_confirm_seconds` (T10): `run_window.py:336-361` mit den Aufrufern `irrigation.py:2566`
  und `run_window.py:896`. Dafür gibt es das Folge-Issue (Task 14).

**Leser von `RUN_STARTED`:**

- Panel `irrigation.py:377`
- In-flight-Anker `run_state.py:109`
- letzter Rückfall-Anker des Fensters `run_watch.py:330`
- `run_watch.py:572` (`_watch_observed_start_iso`)
- `_sc_run_elapsed` `self_closing.py:753`
- Grenze vor/nach dem Ende im Stopp `:870` (T7)
- Neustart-`elapsed` `:993` (T8)
- Schreiber: `batch.py:352` und `self_closing.py:639`

**Verteiler:** Der letzte `grep` liefert `0` (gemessen 19.09. auf dry5; Produktivcode auf dry6 gleich). Eigener Pfad,
unberührt.

Ergebnis (erwartet): kein vom Plan übersehener Pfad. Die vorbestehenden Befunde stehen in Spec
„Vorbestehende Befunde“ und gehen in Task 14, Step 10 nach `ToDo.md`.

- [ ] **Step 8: Mutationsproben auf dem echten Branch**

**Verfahren (jede Probe einzeln):**

1. Datei nach `D:/Entwicklung/HASI/pr139-work/mut/<präfix>-<probe>.bak` kopieren und die SHA-256 notieren.
2. Die Ersetzung anwenden. Ein Suchtext muss genau einmal vorkommen, sonst Abbruch ohne Schreiben.
3. Die Tests laufen lassen.
4. Die `.bak` zurückkopieren und die SHA-256 prüfen; bei Abweichung Abbruch.

Gefangen heißt: mindestens ein `FAILED` (vitest: `FAIL`). Ein `Lingering timer`-Error allein zählt nicht.

Zwei Werkzeuge:

- **CRLF-Skripte des Probelaufs** für T5 (Entscheidung (b)), T7 und T8. Sie lesen und schreiben mit
  `newline=''` und `\r\n`-Suchtexten. Sie werden mit neuem Sicherungspräfix kopiert, damit die
  dry3-Sicherungen nicht überschrieben werden.
- **Treiber `mut/rev3_probes.py`** (unten, neu) für T1–T4, den Rev.-2-Teil von T5 und die T6-Pin-Probe, die zwei
  dry6-Proben von T7, T9, T11 und T12. Er liest mit Universal-Newlines und schreibt die mutierte Datei mit LF; erst die
  `.bak` stellt die CRLF-Bytes wieder her. Er ersetzt `mut/r7_probes.py` (Sätze t02/t05 der Revision 2),
  `scratch/t9/probes.py` (fester Pfad `dry2`, fest verdrahtetes Log) und die dry6-Hilfsskripte
  `scratch/dry6/probe.py` + `probes_*.py` (fester Pfad `dry2`).

**Geprüft 19.09. auf dry5, am Abend erneut auf dry6:** Jeder Suchtext der drei CRLF-Skripte (46 Proben: T5 13, T7 21,
T8 12) und jede Ersetzung des Treibers (88 Proben: t01 6, t02 24, t03 16, t04 12, t05r2 9, t05pin 1, t07add 2, t09 8,
t11 8, t12 2) kommt genau einmal vor. Jede mutierte Python-Datei kompiliert, jede mutierte JSON-Datei parst.

- Belege dry6 (lesend im Worktree `dry2`): `REV3_WT=D:/Entwicklung/HASI/pr139-work/dry2 python rev3_probes.py --count`
  mit genau dem Treiber unten --> `### count: 0 probe(s) do not apply`, 88 Zeilen `applies once`; die CRLF-Skripte über
  ein Zählskript, das ihre `PROBES` lädt und mit `newline=''` gegen die Dateien zählt --> `total 46 not exactly once 0`.
  Beide Skripte lagen im Scratchpad der Sitzung und sind nicht aufbewahrt; `--count` wiederholt die Prüfung auf dem
  echten Branch.

Auf dry6 gelaufen sind 14 Proben (19.09. abends, `dry6-logs/T3.md`, `T5.md`, `probes.md`): die vier Backstop-Proben
zum Echt-Timer-Test (am T3-Stopp, am Branch-HEAD nach Schritt T3 `bc41374b` und am Endstand `70dc0c18`,
`dry6-logs/T3-end-probes.txt`; eine davon ist `backstop-no-grace`), die T6-Pin-Probe (am T5-Stopp
und am Endstand) und neun Proben für die bis dahin ungefangenen Tests (T2 ×5, T7 ×2, T11 ×2). Alle übrigen Ergebnisse
unten stammen aus Revision 2 bzw. dry3.

Den Treiber als `D:/Entwicklung/HASI/pr139-work/mut/rev3_probes.py` anlegen (außerhalb des Repos, wird nie
committet):

```python
"""Rev. 3: mutation probes of T1-T4, T5 (Rev.-2 part and the T6 pin), T7 (dry6 part), T9, T11
and T12 on the real branch.

One probe at a time: copy the file to mut/rev3-<set>-<probe>.bak, record its sha256,
apply the edits (every search must occur exactly once), run the tests, copy the .bak
back and verify the sha256. Stops at the first restore that does not verify. The
mutated file is written with LF; only the .bak brings the CRLF bytes back.

Usage:
  python rev3_probes.py <set> [probe ...]   run one set
                                            (t01 t02 t03 t04 t05r2 t05pin t07add t09 t11 t12)
  python rev3_probes.py --count [set ...]   read-only: every edit applies exactly once
REV3_WT overrides the worktree (default: the main worktree on fix/backstop-grace).
"""

import hashlib
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys

WT = pathlib.Path(os.environ.get("REV3_WT", "D:/Entwicklung/HASI/HAsmartirrigation"))
PY = "D:/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe"
MUT = pathlib.Path("D:/Entwicklung/HASI/pr139-work/mut")
TMP = "D:/Entwicklung/HASI/pr139-work/tmp"
BASE = "2b2c403b"
CC = "custom_components/irrigation_plus/"
RW, SC, ST, RS, WS, CO = (
    CC + f
    for f in ("run_watch.py", "self_closing.py", "store.py", "run_state.py", "websockets.py", "const.py")
)
LANG = CC + "frontend/localize/languages/"
TS = CC + "frontend/src/views/zones/view-zone-settings.ts"
VT = "src/views/zones/view-zone-settings-latency-margin.test.ts"
SW, H, RF = "tests/test_service_watch.py", "tests/test_finish_grace_helpers.py", "tests/test_run_in_flight.py"
T1F = ["tests/test_store_self_closing.py", "tests/test_distributor_integration.py"]
I18N = ["tests/test_i18n_completeness.py"]
K3A = "armed_once or default_margin_is_frozen or zones_own_margin or margin_of_zero"
K3B = "armed_once or WaitsOnlyForAConfirmedValve or MissedClose"
K3D = "MissedClose or SecondDispatch"
K4 = "TestTheWatcherRecordsTheValvesOwnOffReport"
K5 = "TestAConfirmedRunIsSettledOnItsValveWindow or test_a_valve_off_at_the_planned_end_completes"

LOAD = (
    "                        latency_margin=zone.get(\n"
    "                            ZONE_LATENCY_MARGIN, DEFAULT_LATENCY_MARGIN_SECONDS\n"
    "                        ),\n"
)
VON = (
    "                record[const.RUN_VALVE_ON] = self._sc_valve_on_instant(\n"
    "                    confirm_target, dispatched_at, confirmed_at\n"
    "                )\n"
)
ADD = "            await self._sc_add_run(record)\n"
ARM = (
    "                self._sc_schedule_cleanup(\n"
    "                    zone_id, planned_seconds + run_finish_grace_seconds(record)\n"
    "                )\n"
)
DONE = "        async def _done(_now):\n            await self._sc_finish_run(zone_id)\n"
DONE_ELAPSED = (
    "        async def _done(_now):\n"
    "            run = await self._sc_find_run(zone_id)\n"
    "            await self._sc_finish_run(\n"
    "                zone_id, actual_s=self._sc_run_elapsed(run) if run else None\n"
    "            )\n"
)
DONE_T6 = (
    "        async def _done(_now):\n"
    "            run = await self._sc_find_run(zone_id)\n"
    "            if (\n"
    "                run is not None\n"
    "                and run_finish_grace_seconds(run)\n"
    "                and run.get(const.RUN_VALVE_OFF)\n"
    "            ):\n"
    "                await self._watch_settle_by_window(zone_id, run)\n"
    "                return\n"
    "            await self._sc_finish_run(zone_id)\n"
)
TOLW = "if window + run_completion_tolerance(run) >= planned_seconds(run):"
W9 = "else planned + run_finish_grace_seconds(run)"
CL = "Math.max(0, Math.min(30, Math.round(v)))"
HELP = re.compile(r'^([ \t]*"latency_margin_help": ).*?(,?)$', re.M)


def base_file(rel):
    def edit(_text):
        return subprocess.run(
            ["git", "-C", str(WT), "show", f"{BASE}:{rel}"],
            capture_output=True, text=True, encoding="utf-8", check=True,
        ).stdout
    return edit


def help_line_dropped(text):
    new, n = re.subn(r'^[ \t]*"latency_margin_help": .*\n', "", text, flags=re.M)
    assert n == 1, f"latency_margin_help lines: {n}"
    return new


def help_in_english(text):
    en = json.loads((WT / (LANG + "en.json")).read_text(encoding="utf-8"))
    value = en["panels"]["zones"]["labels"]["latency_margin_help"]
    new, n = HELP.subn(
        lambda m: m.group(1) + json.dumps(value, ensure_ascii=False) + m.group(2), text
    )
    assert n == 1, f"latency_margin_help lines: {n}"
    return new


# (name, file, edits, tests, -k); an edit is (search, replace) or a callable mapping text to text
PROBES = {
    "t01": [
        ("load-line", ST, [(LOAD, "")], T1F, "latency_margin"),
        ("load-default", ST, [(LOAD, "                        latency_margin=zone.get(ZONE_LATENCY_MARGIN),\n")], T1F, "latency_margin"),
        ("const-default", CO, [("DEFAULT_LATENCY_MARGIN_SECONDS = 4", "DEFAULT_LATENCY_MARGIN_SECONDS = 5")], T1F, "latency_margin"),
        ("store-revert", ST, [base_file(ST)], T1F, "latency_margin"),
        ("ws-coerce-removed", WS, [("                vol.Optional(const.ZONE_LATENCY_MARGIN): vol.Coerce(int),\n", "")], T1F, "latency_margin"),
        ("ws-coerce-float", WS, [("vol.Optional(const.ZONE_LATENCY_MARGIN): vol.Coerce(int)", "vol.Optional(const.ZONE_LATENCY_MARGIN): vol.Coerce(float)")], T1F, "latency_margin"),
    ],
    "t02": [
        ("zone-clamp", RW, [("    return max(0, min(const.MAX_LATENCY_MARGIN_SECONDS, value))", "    return value")], [H], "clamped_to_its_bounds"),
        ("zone-round", RW, [("value = int(round(float(raw)))", "value = int(float(raw))")], [H], "clamped_to_its_bounds"),
        ("zone-garbage", RW, [("    except (TypeError, ValueError):\n        return const.DEFAULT_LATENCY_MARGIN_SECONDS\n", "    except (TypeError, ValueError):\n        return 0\n")], [H], "clamped_to_its_bounds"),
        ("zone-default", RW, [("    if raw is None:\n        return const.DEFAULT_LATENCY_MARGIN_SECONDS\n", "    if raw is None:\n        return 0\n")], [H], "stored_without_a_margin"),
        ("run-margin-negative", RW, [("        return max(0.0, float(raw))", "        return float(raw)")], [H], "negative_margin"),
        ("run-grace-policy", RW, [("    return watch_policy_for(run.get(const.RUN_MODE)).settles_on_valve_window", "    return True")], [H], "batch_record_carrying or opensprinkler_record_carrying"),
        ("run-grace-margin-gate", RW, [("    if run_latency_margin(run) is None:\n        return False\n", "")], [H], "before_the_update"),
        ("run-grace-watch-gate", RW, [("    if not isinstance(run, dict) or not run.get(const.RUN_WATCH_ENTITY):", "    if not isinstance(run, dict):")], [H], "unconfirmed_run_has_none or run_without_grace_waits_nothing"),
        ("run-grace-settle", RW, [("return float(policy.finish_settle_seconds) + float(run_latency_margin(run))", "return float(run_latency_margin(run))")], [H], "settle_plus_the_frozen_margin"),
        ("tolerance-floor", RW, [("return max(1.0, float(run_latency_margin(run)))", "return float(run_latency_margin(run))")], [H], "never_drops_below_one_second"),
        ("tolerance-no-grace", RW, [("    if not run_has_finish_grace(run):\n        return 1.0\n", "")], [H], "keeps_the_one_second_slack"),
        ("window-off-clamp", RW, [("return max(0.0, (off - anchor).total_seconds())", "return (off - anchor).total_seconds()")], [H], "off_report_before_the_on_report"),
        ("window-plan-bound", RW, [("return max(0.0, min((now - anchor).total_seconds(), planned))", "return max(0.0, (now - anchor).total_seconds())")], [H], "bounded_by_the_plan"),
        ("window-anchor-valve-on", RW, [("        run.get(const.RUN_VALVE_ON)\n        or run.get(const.RUN_OBSERVED_START)\n", "        run.get(const.RUN_OBSERVED_START)\n")], [H], "off_report_minus_the_on_report or time_since_on"),
        ("window-anchor-observed", RW, [("        or run.get(const.RUN_OBSERVED_START)\n", "")], [H], "falls_back_to_the_observed_start"),
        ("window-no-anchor", RW, [("    if anchor is None:\n        return planned\n", "    if anchor is None:\n        return 0.0\n")], [H], "no_anchor"),
        ("policy-service-flag", SC, [("    settles_on_valve_window=True,\n", "")], [H], "service_policy_settles or confirmed_service_run_with_a_margin"),
        ("policy-default-true", RW, [("    settles_on_valve_window: bool = False", "    settles_on_valve_window: bool = True")], [H], "batch_policy_does_not or opensprinkler_policy_does_not"),
        ("resume-adds-settle", RW, [("        remaining = max(0.0, planned_seconds(run) - self._sc_run_elapsed(run))", "        remaining = max(0.0, planned_seconds(run) - self._sc_run_elapsed(run)) + const.SERVICE_WATCH_SETTLE_SECONDS")], [H], "remaining_window_only"),
        # dry6 (19.09.): the four tests no probe had caught, and the "7" case of the clamp test
        ("no-margin-reads-zero", RW, [("    if raw is None:\n        return None\n    try:\n        return max(0.0, float(raw))\n", "    if raw is None:\n        return 0.0\n    try:\n        return max(0.0, float(raw))\n")], [H], "record_without_a_margin_answers_none or before_the_update_has_none"),
        ("frozen-margin-constant", RW, [("        return max(0.0, float(raw))\n", "        return 4.0\n")], [H], "frozen_margin_is_read_back or negative_margin or never_drops_below_one_second"),
        ("tolerance-always-one", RW, [("    return max(1.0, float(run_latency_margin(run)))\n", "    return 1.0\n")], [H], "completion_tolerance_is_the_margin"),
        ("anchor-no-started-fallback", RW, [('        or run.get(const.RUN_OBSERVED_START)\n        or run.get(const.RUN_STARTED)\n        or ""\n', '        or run.get(const.RUN_OBSERVED_START)\n        or ""\n')], [H], "falls_back_to_the_dispatch_instant"),
        ("string-margin-is-garbage", RW, [("    try:\n        value = int(round(float(raw)))\n", "    try:\n        if isinstance(raw, str):\n            raise ValueError(raw)\n        value = int(round(float(raw)))\n")], [H], "clamped_to_its_bounds"),
    ],
    "t03": [
        ("margin-record", SC, [("                record[const.RUN_LATENCY_MARGIN] = zone_latency_margin(zone)\n", "")], [SW], K3A),
        ("margin-default", SC, [("record[const.RUN_LATENCY_MARGIN] = zone_latency_margin(zone)", "record[const.RUN_LATENCY_MARGIN] = const.DEFAULT_LATENCY_MARGIN_SECONDS")], [SW], "zones_own_margin or margin_of_zero"),
        ("valve-on-record", SC, [(VON, "")], [SW], "ClampedToTheDispatch"),
        ("clamp-lower", SC, [("min(max(reported, lower), upper)", "min(reported, upper)")], [SW], "ClampedToTheDispatch"),
        ("clamp-upper", SC, [("min(max(reported, lower), upper)", "max(reported, lower)")], [SW], "ClampedToTheDispatch"),
        ("report-ignored", SC, [("reported = state.last_changed if state else upper", "reported = upper")], [SW], "ClampedToTheDispatch"),
        ("lower-is-confirm-return", SC, [("confirm_target, dispatched_at, confirmed_at", "confirm_target, confirmed_at, confirmed_at")], [SW], "ClampedToTheDispatch"),
        ("upper-is-dispatch", SC, [("confirm_target, dispatched_at, confirmed_at", "confirm_target, dispatched_at, dispatched_at")], [SW], "ClampedToTheDispatch"),
        ("backstop-no-grace", SC, [("planned_seconds + run_finish_grace_seconds(record)", "planned_seconds")], [SW], K3B),
        ("backstop-grace-always", SC, [("planned_seconds + run_finish_grace_seconds(record)", "planned_seconds + const.SERVICE_WATCH_SETTLE_SECONDS + zone_latency_margin(zone)")], [SW], K3B),
        ("backstop-grace-from-zone", SC, [("planned_seconds + run_finish_grace_seconds(record)", "planned_seconds + (const.SERVICE_WATCH_SETTLE_SECONDS + zone_latency_margin(zone) if zone.get(const.ZONE_CONFIRM_ENTITY) else 0)")], [SW], K3B),
        ("margin-for-every-record", SC, [(ADD, "            record[const.RUN_LATENCY_MARGIN] = zone_latency_margin(zone)\n" + ADD)], [SW], "FreezesItsMargin"),
        ("valve-on-for-unverifiable", SC, [(ADD, "            if confirm_target and not is_opensprinkler:\n" + VON + ADD)], [SW], "FreezesItsMargin"),
        # dry6 (19.09.): the missed close, on the real backstop timer
        ("backstop-callback-dropped", SC, [(DONE, "        async def _done(_now):\n            return None\n")], [SW, RF], K3D),
        ("backstop-finishes-on-elapsed", SC, [(DONE, DONE_ELAPSED)], [SW, RF], K3D),
        ("backstop-never-armed", SC, [(ARM, "                pass\n")], [SW, RF], K3B + " or SecondDispatch"),
    ],
    "t04": [
        ("previous-state-not-passed", RW, [('                    previous_state=event.data.get("old_state"),\n', "")], [SW], K4),
        ("initial-evaluate-records", RW, [("                previous_state is not None\n                and previous_state.state in RUNNING_STATES\n", "                (previous_state is None or previous_state.state in RUNNING_STATES)\n")], [SW], K4),
        ("clock-not-last-changed", RW, [("state.last_changed.isoformat()", "dt_util.utcnow().isoformat()")], [SW], K4),
        ("grace-gate-removed", RW, [("                and run_has_finish_grace(run)\n", "")], [SW], K4),
        ("running-condition-removed", RW, [("                and previous_state.state in RUNNING_STATES\n", "")], [SW], K4),
        ("unavailable-accepted", RW, [("previous_state.state in RUNNING_STATES", 'previous_state.state in (*RUNNING_STATES, "unavailable")')], [SW], K4),
        ("clear-removed", RW, [("await self._watch_update_run(zid, {const.RUN_VALVE_OFF: None})", "pass")], [SW], K4),
        ("clear-gated-on-segmented", RW, [("if policy.settles_on_valve_window and run.get(const.RUN_VALVE_OFF):", "if policy.segmented and run.get(const.RUN_VALVE_OFF):")], [SW], K4),
        ("first-off-guard-removed", RW, [("                and not run.get(const.RUN_VALVE_OFF)\n", "")], [SW], K4),
        ("guard-removed-and-last-updated", RW, [("                and not run.get(const.RUN_VALVE_OFF)\n", ""), ("state.last_changed.isoformat()", "state.last_updated.isoformat()")], [SW], K4),
        ("last-updated", RW, [("state.last_changed.isoformat()", "state.last_updated.isoformat()")], [SW], K4),
        ("clear-policy-gate-removed", RW, [("if policy.settles_on_valve_window and run.get(const.RUN_VALVE_OFF):", "if run.get(const.RUN_VALVE_OFF):")], [SW], K4),
    ],
    "t05r2": [
        ("finish-actual-dropped", SC, [("actual_s=planned_s if actual_s is None else actual_s,", "actual_s=planned_s,")], [SW], K5),
        ("stop-actual-dropped", SC, [("        if actual_s is not None:\n            elapsed = actual_s\n", "        if False:\n            elapsed = actual_s\n")], [SW], K5),
        ("tolerance-one-second", RW, [(TOLW, "if window + 1 >= planned_seconds(run):")], [SW], K5),
        ("tolerance-no-floor", RW, [(TOLW, "if window + float(run_latency_margin(run)) >= planned_seconds(run):")], [SW], K5),
        ("decide-time-window", RW, [("return valve_window_seconds(run, dt_util.utcnow())", "return valve_window_seconds({**run, const.RUN_VALVE_OFF: dt_util.utcnow().isoformat()}, dt_util.utcnow())")], [SW], K5),
        ("finish-window-not-passed", RW, [("await self._sc_finish_run(zid, actual_s=window)", "await self._sc_finish_run(zid)")], [SW], K5),
        ("stop-window-not-passed", RW, [("await self.async_stop_self_closing(zid, close_valve=False, actual_s=window)", "await self.async_stop_self_closing(zid, close_valve=False)")], [SW], K5),
        ("finish-volume-on-actual", SC, [("volume_l = self._timed_volume_l(zone, planned_s)", "volume_l = self._timed_volume_l(zone, actual_s)")], [SW], K5),
        ("finish-calibration-on-actual", SC, [("await self._flow_calibration_check(zone, measured, planned_s)", "await self._flow_calibration_check(zone, measured, actual_s)")], [SW], K5),
    ],
    # dry6 (19.09.): the dropped T6 brought back; only the T5 pin may catch it
    "t05pin": [
        ("t6-backstop-settles-on-stored-off", SC, [(DONE, DONE_T6)], [SW], "KnownAndDeliberatelyUnchanged"),
    ],
    # dry6 (19.09.): the two T7 tests no probe had caught; whole file, as in the dry6 run
    "t07add": [
        ("before-end-books-plan", SC, [("                elapsed = self._watch_valve_window({**run, const.RUN_VALVE_OFF: None})\n", "                elapsed = planned\n")], [SW], None),
        ("else-books-plan", SC, [("        else:\n            elapsed = self._sc_run_elapsed(run)\n        delivered_frac", "        else:\n            elapsed = planned\n        delivered_frac")], [SW], None),
    ],
    "t09": [
        ("drop-grace", RS, [(W9, "else planned")], [RF], None),
        ("anchor-prefers-valve-on", RS, [('(observed or run.get(const.RUN_STARTED)) or ""', '(run.get(const.RUN_VALVE_ON) or observed or run.get(const.RUN_STARTED)) or ""')], [RF], None),
        ("lte-boundary", RS, [(".total_seconds() < window", ".total_seconds() <= window")], [RF], None),
        ("frozen-margin-to-default", RW, [("return float(policy.finish_settle_seconds) + float(run_latency_margin(run))", "return float(policy.finish_settle_seconds) + float(const.DEFAULT_LATENCY_MARGIN_SECONDS)")], [RF], None),
        ("grace-doubled", RS, [(W9, "else planned + 2 * run_finish_grace_seconds(run)")], [RF], None),
        ("grace-for-every-record", RS, [(W9, "else planned + float(const.SERVICE_WATCH_SETTLE_SECONDS + const.DEFAULT_LATENCY_MARGIN_SECONDS)")], [RF], None),
        ("grace-without-plan", RS, [(W9, "else run_finish_grace_seconds(run)")], [RF], None),
        ("live-zone-margin", RS, [(W9, 'else planned + ((float(const.SERVICE_WATCH_SETTLE_SECONDS) + __import__("custom_components.irrigation_plus.run_watch", fromlist=["_"]).zone_latency_margin(self.store.get_zone(zone_id))) if run_finish_grace_seconds(run) else 0.0)')], [RF], None),
    ],
    "t11": [
        ("gate-always-true", TS, [("return !!zone?.confirm_entity;", "return true;")], "vitest", None),
        ("gate-ignores-empty", TS, [("return !!zone?.confirm_entity;", "return zone?.confirm_entity != null;")], "vitest", None),
        ("clamp-no-upper", TS, [(CL, "Math.max(0, Math.round(v))")], "vitest", None),
        ("clamp-no-lower", TS, [(CL, "Math.min(30, Math.round(v))")], "vitest", None),
        ("clamp-no-round", TS, [(CL, "Math.max(0, Math.min(30, v))")], "vitest", None),
        ("clamp-no-nan-guard", TS, [("    if (isNaN(v)) return null;\n", "")], "vitest", None),
        # dry6 (19.09.): the two tests no probe had caught
        ("gate-always-false", TS, [("return !!zone?.confirm_entity;", "return false;")], "vitest", None),
        ("clamp-upper-29", TS, [("Math.min(30, Math.round(v))", "Math.min(29, Math.round(v))")], "vitest", None),
    ],
    "t12": [
        ("sk-help-missing", LANG + "sk.json", [help_line_dropped], I18N, None),
        ("fr-help-english", LANG + "fr.json", [help_in_english], I18N, None),
    ],
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def mutate(text, edits):
    for edit in edits:
        if callable(edit):
            text = edit(text)
            continue
        search, replace = edit
        count = text.count(search)
        if count != 1:
            raise ValueError(f"search occurs {count} times: {search[:70]!r}")
        text = text.replace(search, replace)
    return text


def run_tests(tests, k):
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTHONIOENCODING="utf-8", TEMP=TMP, TMP=TMP, TMPDIR=TMP)
    if tests == "vitest":
        out = subprocess.run(
            f"npx vitest run {VT}", shell=True, cwd=WT / (CC + "frontend"), env=env,
            capture_output=True, text=True, encoding="utf-8", errors="replace",
        ).stdout
        failed = [ln.strip() for ln in out.splitlines() if ln.strip().startswith("FAIL ")]
        summary = [ln.strip() for ln in out.splitlines() if re.match(r"\s*Tests\s", ln)]
        return list(dict.fromkeys(failed)), summary[-1:]
    cmd = [PY, "-m", "pytest", *tests, "-p", "_local_socket_unblock", "-q", "-p", "no:cacheprovider"]
    if k:
        cmd += ["-k", k]
    out = subprocess.run(
        cmd, cwd=WT, env=env, capture_output=True, text=True, encoding="utf-8", errors="replace"
    ).stdout
    failed = [ln.split(" - ")[0] for ln in out.splitlines() if ln.startswith("FAILED ")]
    summary = [ln.strip("= ") for ln in out.splitlines() if re.match(r"^=+ .*(passed|failed|error).* =+$", ln)]
    return failed, summary[-1:]


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    args = sys.argv[1:]
    if args and args[0] == "--count":
        bad = 0
        for pset in args[1:] or list(PROBES):
            for name, rel, edits, _tests, _k in PROBES[pset]:
                try:
                    mutated = mutate((WT / rel).read_text(encoding="utf-8"), edits)
                    if rel.endswith(".py"):
                        compile(mutated, rel, "exec")
                    elif rel.endswith(".json"):
                        json.loads(mutated)
                    print(f"{pset} {name}: applies once")
                except (ValueError, AssertionError, SyntaxError) as exc:
                    bad += 1
                    print(f"{pset} {name}: {exc}")
        print(f"### count: {bad} probe(s) do not apply")
        return
    pset, only = args[0], set(args[1:])
    head = subprocess.run(["git", "-C", str(WT), "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
    print(f"### set={pset} worktree={WT} HEAD={head}")
    caught = total = 0
    for name, rel, edits, tests, k in PROBES[pset]:
        if only and name not in only:
            continue
        total += 1
        path = WT / rel
        bak = MUT / f"rev3-{pset}-{name}.bak"
        shutil.copyfile(path, bak)
        before = sha(path)
        mutated = mutate(path.read_text(encoding="utf-8"), edits)
        try:
            path.write_text(mutated, encoding="utf-8", newline="\n")
            failed, summary = run_tests(tests, k)
        finally:
            shutil.copyfile(bak, path)
        if sha(path) != before:
            raise SystemExit(f"{name}: restore did not verify")
        caught += bool(failed)
        print(f"== {name} [{rel.split('/')[-1]}] caught={bool(failed)} restored=True | {' '.join(summary)}")
        for line in failed:
            print(f"   {line}")
    status = subprocess.run(
        ["git", "-C", str(WT), "status", "--short", "--untracked-files=no"], capture_output=True, text=True
    ).stdout
    print(f"### {pset}: {caught}/{total} caught; tracked files clean={not status.strip()}")


main()
```

Lauf (Voraussetzung: Step 4, damit `node_modules` für t11 da ist):

```bash
cd /d/Entwicklung/HASI/HAsmartirrigation
mkdir -p D:/Entwicklung/HASI/pr139-work/tmp D:/Entwicklung/HASI/pr139-work/npm-cache && export TEMP=D:/Entwicklung/HASI/pr139-work/tmp TMP=D:/Entwicklung/HASI/pr139-work/tmp TMPDIR=D:/Entwicklung/HASI/pr139-work/tmp npm_config_cache=D:/Entwicklung/HASI/pr139-work/npm-cache
M=/d/Entwicklung/HASI/pr139-work/mut
test -z "$(git status --short --untracked-files=no)" || { echo DIRTY; exit 1; }
# Vorlauf ohne Mutation (Grundzahlen der Auswahl)
./.venv/Scripts/python.exe -m pytest tests/test_service_watch.py tests/test_finish_grace_helpers.py -p _local_socket_unblock -q -p no:cacheprovider | tail -1
./.venv/Scripts/python.exe -m pytest tests/test_service_watch.py tests/test_self_closing.py -p _local_socket_unblock -q -p no:cacheprovider | tail -1
./.venv/Scripts/python.exe -m pytest tests/test_service_watch.py tests/test_finish_grace_helpers.py tests/test_run_in_flight.py tests/test_confirm_reserve.py tests/test_self_closing.py tests/test_run_watch.py tests/test_observed_watering.py tests/test_opensprinkler.py tests/test_batch.py tests/test_credit_ceiling.py tests/test_stop_zone.py -p _local_socket_unblock -q -p no:cacheprovider | tail -1
# Treiber
./.venv/Scripts/python.exe $M/rev3_probes.py --count | tail -1
for s in t01 t02 t03 t04 t05r2 t05pin t07add t09 t11 t12; do ./.venv/Scripts/python.exe $M/rev3_probes.py $s | tee -a $M/real-rev3-probes.txt; done
# CRLF-Skripte mit neuem Sicherungspräfix
for t in 5 7 8; do sed "s/dry3-T$t-/real-T$t-/" $M/dry3_t${t}_probes.py > $M/real_t${t}_probes.py; done
grep -c "real-T" $M/real_t5_probes.py $M/real_t7_probes.py $M/real_t8_probes.py
./.venv/Scripts/python.exe $M/real_t5_probes.py D:/Entwicklung/HASI/HAsmartirrigation $M/real-T5-probes.txt
./.venv/Scripts/python.exe $M/real_t7_probes.py D:/Entwicklung/HASI/HAsmartirrigation $M/real-T7-probes.txt
./.venv/Scripts/python.exe $M/real_t8_probes.py D:/Entwicklung/HASI/HAsmartirrigation $M/real-T8-probes.txt
git status --short --untracked-files=no
git diff --stat
```

**Erwartete Grundzahlen.** Gemessen 19.09. abends auf dry6 ohne Mutation (lesend, dieselben Auswahlen; die drei
Vorlauf-Zeilen oben sind die ersten drei):

- T5-Skript (`test_service_watch` + Helfer): `99 passed, 1 error`.
- T8-Skript (`test_service_watch` + `test_self_closing`): `107 passed, 1 error`.
- Breiter Satz der T7-Probe `grace-gate-dropped`: `413 passed, 52 errors`.
- T7-Skript (nur `test_service_watch`): `69 passed, 1 error`.
- `rev3_probes.py`:
  - t01 `-k latency_margin`: `3 passed, 25 deselected`
  - t02 (neue Proben, `tests/test_finish_grace_helpers.py`): `2 passed, 28 deselected` (`no-margin-reads-zero`),
    `3 passed, 27 deselected` (`frozen-margin-constant`), je `1 passed, 29 deselected` (`tolerance-always-one`,
    `anchor-no-started-fallback`), `5 passed, 25 deselected` (`string-margin-is-garbage`, wie `zone-*`)
  - t03 `-k K3A`: `6 passed, 63 deselected`; `-k K3B`: `5 passed, 64 deselected`; `ClampedToTheDispatch`:
    `3 passed, 66 deselected`; `FreezesItsMargin`: `4 passed, 65 deselected`; die Backstop-Proben auf beiden Dateien:
    `-k K3D` `3 passed, 93 deselected`, `-k "K3B or SecondDispatch"` `7 passed, 89 deselected`
  - t04 `-k TestTheWatcherRecordsTheValvesOwnOffReport`: `8 passed, 61 deselected`
  - t05r2 `-k K5`: `10 passed, 59 deselected`
  - t05pin `-k KnownAndDeliberatelyUnchanged`: `1 passed, 68 deselected`
  - t07add (ganze Datei): `69 passed, 1 error`
  - t09: `27 passed`; t11: `8 passed (8)`; t12: `66 passed`
- Weiter: `--count` meldet `### count: 0 probe(s) do not apply`, `grep -c` je `2` (Docstring Zeile 3 und
  `.bak`-Pfad; `sed` ohne `g` ersetzt je Zeile den einen Treffer), und am Ende sind `git status` und
  `git diff --stat` leer.

**Erwartete Ergebnisse je Probe.** „Beobachtet“ heißt: gemessen im genannten Lauf am damaligen Task-Commit.
Die Proben-Commits unterscheiden sich vom Endstand höchstens in Kommentaren, Docstrings und späteren Tests.
Die Produktionszeilen jeder Probe sind gleich; Beleg: alle Suchtexte treffen auf dry5 und dry6 genau einmal, und die
#139-Änderungszeilen sind laut Spec, Messstand dry6, auf dry4, dry5 und dry6 identisch. Auf dem Endstand können
weitere Tests späterer Tasks zusätzlich scheitern. Das Kriterium lautet deshalb „gefangen, mindestens von den
genannten Tests“.

**T1 — 6 Proben** (Revision 2 an `745e4bac`; T1 ist seitdem unverändert, range-diff `=`)

| Probe | Mutation | Beobachtet |
|---|---|---|
| load-line | drei Ladezeilen in `store.py` entfernt | FAIL `test_latency_margin_survives_reload` (`assert 4 == 7`) |
| load-default | Ladezeile ohne Default | FAIL `test_zone_stored_without_latency_margin_loads_the_default` (`assert None == 4`) |
| const-default | Default 4 --> 5 | FAIL dito (`assert 5 == 4`) |
| store-revert | `store.py` auf `2b2c403b` | FAIL beide Store-Tests (`KeyError: 'latency_margin'`) |
| ws-coerce-removed | Schema-Zeile entfernt | FAIL `test_zone_view_coerces_latency_margin_to_int` (`assert '6' == 6`) |
| ws-coerce-float | `Coerce(int)` --> `Coerce(float)` | FAIL dito (`isinstance(6.0, int)`) |

**T2 — 24 Proben** (19 aus Revision 2 nach dem Feinschliff an `94cc3785`, alle 22 am Endstand-Commit erneut
gefahren; 5 aus dry6 am Endstand `70dc0c18`, `dry6-logs/probes.md`). Gestrichen sind die drei Proben des entfallenen
`zone_finish_grace_seconds`: `zone-mode-gate`, `zone-confirm-gate` und `zone-grace-settle` (Entscheidung (e)).

| Probe | Beobachtet |
|---|---|
| zone-clamp | FAIL `clamped_to_its_bounds` ×2 (`assert -3 == 0`) |
| zone-round | FAIL `clamped_to_its_bounds` (`assert 7 == 8`) |
| zone-garbage | FAIL `clamped_to_its_bounds` (`assert 0 == 4`) |
| zone-default | FAIL `stored_without_a_margin` (`assert 0 == 4`) |
| run-margin-negative | FAIL `negative_margin` (`assert -2.0 == 0.0`) |
| run-grace-policy | FAIL `batch_record_carrying`, `opensprinkler_record_carrying` (`assert True is False`) |
| run-grace-margin-gate | FAIL `before_the_update` (`assert True is False`) |
| run-grace-watch-gate | FAIL `unconfirmed_run_has_none`, `run_without_grace_waits_nothing` |
| run-grace-settle | FAIL `settle_plus_the_frozen_margin` (`assert 4.0 == 9.0`) |
| tolerance-floor | FAIL `never_drops_below_one_second` (`assert 0.0 == 1.0`) |
| tolerance-no-grace | FAIL `keeps_the_one_second_slack` (`assert 4.0 == 1.0`) |
| window-off-clamp | FAIL `off_report_before_the_on_report` (`assert -5.0 == 0.0`) |
| window-plan-bound | FAIL `bounded_by_the_plan` (`assert 900.0 == 600.0`) |
| window-anchor-valve-on | FAIL 1 von 2 (`assert 420.5 == 420.0 ± 4.2e-04`) |
| window-anchor-observed | FAIL `falls_back_to_the_observed_start` (`assert 170.0 == 120.0`) |
| window-no-anchor | FAIL `no_anchor` (`assert 0.0 == 600.0`) |
| policy-service-flag | FAIL `service_policy_settles`, `confirmed_service_run_with_a_margin` (`assert False is True`) |
| policy-default-true | FAIL `batch_policy_does_not`, `opensprinkler_policy_does_not` (`assert True is False`) |
| resume-adds-settle | FAIL `remaining_window_only` (`assert (1, 545.0) == (1, 540.0)`) |
| no-margin-reads-zero (dry6) | FAIL `record_without_a_margin_answers_none` (`assert 0.0 is None`), `record_from_before_the_update_has_none`; in den 7 Suiten dazu je ein Test aus T4 und T5 |
| frozen-margin-constant (dry6) | FAIL `frozen_margin_is_read_back` (`assert 4.0 == 6.0`), `negative_margin` (`4.0 == 0.0`), `never_drops_below_one_second` (`4.0 == 1.0`); in den 7 Suiten 7 insgesamt |
| tolerance-always-one (dry6) | FAIL `completion_tolerance_is_the_margin` (`assert 1.0 == 4.0`); in den 7 Suiten dazu T5 `close_inside_the_margin`, T7 Stopp in der Toleranz |
| anchor-no-started-fallback (dry6) | FAIL nur `falls_back_to_the_dispatch_instant` (`assert 600.0 == 170.0`) |
| string-margin-is-garbage (dry6, Zusatz) | FAIL nur `clamped_to_its_bounds[7-7]` (`assert 4 == 7`) |

**T3 — 16 Proben** (12 aus Revision 2 am Commit von Task 3, die Proben mit mehrzeiligem Suchtext im Feinschliff an
`dbbb42fd` erneut; die neu formulierte `backstop-grace-from-zone`; 3 aus dry6, `dry6-logs/T3.md`).
`backstop-grace-from-zone` rief früher `zone_finish_grace_seconds`; jetzt bildet sie dessen Zonen-Tor direkt nach
(`… + (SERVICE_WATCH_SETTLE_SECONDS + zone_latency_margin(zone) if zone.get(ZONE_CONFIRM_ENTITY) else 0)`). Sie ist
nicht wortgleich mit `backstop-grace-always` (die hat kein Tor und trifft auch write-only), prüft also eine eigene
Verwechslung: Tor an der Zone statt am Datensatz. Mit `K3A` wählt das `-k` jetzt auch die zwei „margin of
zero“-Tests aus T5 aus. Sie können unter `margin-record` zusätzlich scheitern. `K3B` enthält seit dry6
`MissedClose`.

| Probe | Beobachtet |
|---|---|
| margin-record | FAIL 4: `armed_once` (`(2, 600.0) == (2, 609)`), zwei `KeyError: 'latency_margin'`, `margin_of_zero` (`(2, 600.0) == (2, 605)`) |
| margin-default | FAIL 2: `assert 4 == 7`, `assert (2, 609.0) == (2, 605)` |
| valve-on-record | FAIL 3 (`KeyError: 'valve_on'`) |
| clamp-lower | FAIL `already_open` (Zeitstempel eine Stunde früher) |
| clamp-upper | FAIL `stamped_after_the_confirm` |
| report-ignored | FAIL `reporting_on_after` |
| lower-is-confirm-return | FAIL `reporting_on_after` |
| upper-is-dispatch | FAIL `reporting_on_after`, `stamped_after_the_confirm` |
| backstop-no-grace | FAIL 2 (`(2, 600.0) == (2, 609)`, `(2, 600.0) == (2, 605)`); auf dry6 (`T3-backstop-without-grace`, dieselbe Mutation) dazu der Echt-Timer-Test, am T3-Stopp, an `bc41374b` und am Endstand `70dc0c18` |
| backstop-grace-always | FAIL 2: write-only, nicht prüfbar (`(2, 609.0) == (2, 600)`) |
| backstop-grace-from-zone | **neu formuliert, nicht gemessen**; alte Form FAIL `unverifiable_run_is_backstopped` (`(2, 609.0) == (2, 600)`); Soll: derselbe eine Fehlschlag |
| backstop-callback-dropped (dry6) | FAIL der Echt-Timer-Test und die zwei T9-Dispatch-Tests (nur `-k K3D` auf beiden Dateien sieht sie); in den 7 Suiten am Endstand `70dc0c18` dazu der T5-Pin (`4 failed, 230 passed, 2 errors`), den `-k K3D` nicht auswählt |
| backstop-finishes-on-elapsed (dry6) | FAIL der Echt-Timer-Test (`610.0 == 600.0`), in der Auswahl `-k K3D` nur er; in den 7 Suiten an `bc41374b` (Produktivcode = Endstand, ein Test weniger) nur er, am Endstand `70dc0c18` dazu der T5-Pin (`2 failed, 232 passed, 2 errors`); der Treiber fährt die Endstand-Form (`_done` übergibt `actual_s` = Uhr) |
| backstop-never-armed (dry6) | FAIL 11 am Endstand `70dc0c18` (10 an `bc41374b`): `armed_once`, drei `WaitsOnlyForAConfirmedValve`, Echt-Timer-Test, zwei T9-Dispatch-Tests, drei `test_self_closing`-Pins und der T5-Pin (der Treiber sieht die 7 aus seinen zwei Dateien, die sein `-k` auswählt) |
| margin-for-every-record | FAIL 2 (`assert 'latency_margin' not in {…}`) |
| valve-on-for-unverifiable | FAIL `unverifiable_run_carries` (`assert 'valve_on' not in {…}`) |

**T4 — 12 Proben, 8 gefangen, 4 äquivalent** (Revision 2 an `6aef25d3`; die Produktionszeilen der Proben und
die Testklasse sind dort gleich, dry3 änderte in T4 nur Kommentar und Docstring)

| Probe | Beobachtet |
|---|---|
| previous-state-not-passed | FAIL 4: `records_the_states_last_changed`, `attribute_only_update`, `unavailable_spell`, `inside_the_debounce_clears` (`KeyError: 'valve_off'`) |
| initial-evaluate-records | FAIL `re_adopted_run_does_not_record_the_initial_off` |
| clock-not-last-changed | FAIL dieselben 4 wie previous-state-not-passed |
| grace-gate-removed | FAIL `before_the_update_records_nothing` |
| running-condition-removed | FAIL `unavailable_mid_run_records_nothing`, `re_adopted_run_does_not_record_an_off_after_unavailable` |
| unavailable-accepted | FAIL dieselben 2 |
| clear-removed | FAIL `inside_the_debounce_clears` |
| clear-gated-on-segmented | FAIL `inside_the_debounce_clears` |
| first-off-guard-removed | **äquivalent**: ein zweites `off` folgt nie direkt auf „laufend“ (E6); erneutes Aufzeichnen bräuchte ein „an“ dazwischen, und das löscht `RUN_VALVE_OFF` |
| guard-removed-and-last-updated | **äquivalent**, aus demselben Grund und weil `last_changed == last_updated` beim echten Wechsel gilt |
| last-updated | **äquivalent** (`last_changed == last_updated` bei einem echten Zustandswechsel) |
| clear-policy-gate-removed | **äquivalent**: `RUN_VALVE_OFF` entsteht nur für Läufe mit Tor |

Die äquivalenten Proben enden erwartet mit `8 passed, 61 deselected` (auf dry6 ohne Mutation gemessen; die Datei hat
am Endstand 69 Items). In Revision 2 war es bei 37 Items `8 passed, 29 deselected`.

**T5 — 22 Proben, 21 gefangen, 1 äquivalent**

Teil A, Entscheidung (b), CRLF-Skript `real_t5_probes.py`: 13 Proben, davon eine Dublette. Beobachtet an der
T5-Station von dry3 (`dry3-logs/T5.md`), `base-partial-passes-window` am dry3-Endstand
(`T7-t5probe-rerun.txt`).

| Probe | Mutation (`run_watch.py`) | Beobachtet |
|---|---|---|
| gate-dropped | Tor ohne `RUN_VALVE_OFF` | FAIL 2: `seven_seconds_early_stays_partial` (`'completed' == 'partial'`), `inside_the_old_second_completes_for_its_plan` (`599.5 == 600.0`) |
| gate-inverted | `… and not run.get(RUN_VALVE_OFF)` | FAIL 7: die fünf Tests mit Aus-Meldung und beide Pins ohne |
| gate-off-only | nur `if run.get(RUN_VALVE_OFF):` | **äquivalent**: `RUN_VALVE_OFF` schreibt nur der Aufzeichnungszweig aus T4, und der steht hinter dem Tor; die Marge verlässt einen Datensatz nie |
| gate-wrong-key | `… and run.get(RUN_VALVE_ON)` | FAIL 2 wie gate-dropped |
| always-routed | `if True:` | FAIL 3: beide Pins ohne Aus-Meldung und `record_from_before_the_update_keeps_the_old_rule` (`599.5 == 600.0`) |
| never-routed | `if False:` | FAIL 5: die fünf Tests mit Aus-Meldung |
| base-tolerance-two | `elapsed + 2` | FAIL `seven_seconds_early_stays_partial` |
| base-tolerance-margin | `elapsed + run_completion_tolerance(run)` | FAIL dito (die verworfene E4-Toleranz) |
| base-tolerance-zero | `elapsed >= planned` | FAIL 2: `inside_the_old_second…`, `record_from_before_the_update…` |
| base-finish-passes-elapsed | `_sc_finish_run(zid, actual_s=elapsed)` | FAIL 2 dito (`599.5 == 600.0`) |
| base-partial-passes-window | Basis-Teil-Lauf mit `actual_s=self._watch_valve_window(run)` | ab T7 FAIL `test_the_watchers_own_partial_keeps_its_observed_start` (`307.6 == 307`); an der T5-Station allein überlebend (offene Frage 1, durch T7 gelöst) |
| window-planned-without-off | `valve_window_seconds`: ohne Aus-Meldung `return planned` | FAIL `test_without_an_off_report_the_window_is_the_time_since_on` (`600.0 == 300.0`) |
| unavailable-accepted | wie T4 `unavailable-accepted` | **Dublette**: läuft mit, zählt aber nicht doppelt; FAIL 5 (T4s zwei `records_nothing` und die drei Tests ohne Aus-Meldung) |

Teil B, Rev.-2-Proben auf `_watch_settle_by_window` und `_sc_finish_run`: 9 Proben, Treiber-Satz `t05r2`.
Beobachtet in Revision 2 an `8528d4d0` mit `-k K5` (8 Tests). Der Code dieser Stellen ist seitdem gleich; dry3
änderte in T5 nur das Tor und Texte.

| Probe | Beobachtet |
|---|---|
| finish-actual-dropped | FAIL 3: `just_after_the_window`, `inside_the_margin`, `margin_of_zero_still_tolerates` (`600.0 == 602`, `== 597`, `== 599.5`) |
| stop-actual-dropped | **umformuliert**: der alte Suchtext existiert seit T7 nicht mehr; jetzt `if actual_s is not None:` --> `if False:`. Die Wirkung ist dieselbe (`actual_s` ignoriert, Rückfall auf `_sc_run_elapsed`). Alte Form beobachtet: FAIL 2 `beyond_the_margin`, `beyond_that_second` (`596.0 == 590`, `604.5 == 598.5`). Neue Form: nicht gemessen, gleiches Ergebnis erwartet |
| tolerance-one-second | FAIL `inside_the_margin` (`'partial' == 'completed'`) |
| tolerance-no-floor | FAIL `margin_of_zero_still_tolerates` (`'partial' == 'completed'`) |
| decide-time-window | FAIL 5 (Fenster zum Entscheidungszeitpunkt statt an der Aus-Meldung) |
| finish-window-not-passed | FAIL 3 (`600.0 == 602`, `== 597`, `== 599.5`) |
| stop-window-not-passed | FAIL 2 (`596.0 == 590`, `604.5 == 598.5`) |
| finish-volume-on-actual | FAIL `just_after_the_window` (`602.0 == 600`) |
| finish-calibration-on-actual | FAIL `just_after_the_window` (`602.0 == 600`) |

Aus Revision 2 nicht mehr gefahren: `never-routed` und `always-routed` alter Form (Tor geändert; ersetzt durch
Teil A); `window-planned-without-off` und `unavailable-accepted` (in Teil A bzw. T4 enthalten).

Teil C, der Pin für das gestrichene T6: 1 Probe, Treiber-Satz `t05pin` (`dry6-logs/T5.md`).

| Probe | Mutation (`self_closing.py`) | Beobachtet (dry6) |
|---|---|---|
| t6-backstop-settles-on-stored-off | Backstop-Rückruf `_done` rechnet einen Lauf mit Wartezeit und gespeicherter `RUN_VALVE_OFF` über `_watch_settle_by_window` ab (T6s `_sc_backstop_fired` aus Revision 2) | FAIL nur `test_the_backstop_finishes_it_for_the_plan_before_the_debounce` (`assert 606.0 == 600.0`), am T5-Stopp und am Endstand; kein anderer Test fängt sie |

**T7 — 23 Proben, alle gefangen** (21 mit `real_t7_probes.py`, beobachtet an der T7-Station von dry3,
`dry3-logs/T7-probes-table.md`; 2 im Treiber-Satz `t07add`, beobachtet am dry6-Endstand, `dry6-logs/probes.md`).
Testauswahl: `tests/test_service_watch.py`, nur `grace-gate-dropped` mit dem breiten Satz.

| Probe | Mutation (`self_closing.py`) | Beobachtet |
|---|---|---|
| end-inverted | Grenze `< planned` --> `>= planned` | FAIL 9: alle (c)/(d)-Tests außer den zwei Anker-Tests |
| end-removed-always-before | Grenze --> `if True:` | FAIL 7: jeder Test nach dem Ende |
| end-removed-always-after | Grenze --> `if False:` | FAIL 2: `before_the_planned_end_is_not_booked_on_an_off_report` (`300.0 == 302`), `just_before_the_planned_end_is_capped` |
| end-lte | `<` --> `<=` | FAIL `exactly_at_the_planned_end_is_settled_in_the_grace` |
| end-anchored-on-valve-on | Grenze ab `RUN_VALVE_ON` | FAIL `just_before_the_planned_end_is_capped_at_the_plan` |
| before-uses-stored-off | (c) mit gespeicherter Aus-Meldung | FAIL `before_the_planned_end_is_not_booked_on_an_off_report` (`300.0 == 302`) |
| before-uncapped | (c) ohne Deckel | FAIL `just_before…` (`600.4 == 600`) |
| before-from-observed-start | (c) über `_sc_run_elapsed` | FAIL 2 (`99.0 == 99.6`, `599.8 == 600`) |
| tolerance-ignored | `elapsed >= planned` | FAIL `inside_the_tolerance_completes` |
| tolerance-one-second | `elapsed + 1 >= planned` | FAIL dito |
| completed-branch-dropped | Abschluss-Zweig `if False:` | FAIL 6 |
| always-completed | `if True:` | FAIL `beyond_the_tolerance_is_partial` |
| finish-without-actual-s | `_sc_finish_run(zone_id)` | FAIL 4 (`600.0 == 597`, `600.0 == 601`, Stop-all, Zwilling) |
| no-return-after-finish | `return True` entfernt | FAIL 6 (zweiter Datensatz `partial`) |
| after-ignores-stored-off | (d) ohne Aus-Meldung | FAIL 5 |
| after-measured-to-stop | (d) bis zum Stopp | FAIL 6 |
| valve-not-closed-when-past-end | Schließen nach dem Ende übersprungen | FAIL 4 (`assert [0] == [1]`) |
| settle-before-close | Abrechnung vor dem Schließen | FAIL 4 (`assert [0] == [1]`) |
| close-valve-gate-dropped | Tor ohne `close_valve` | FAIL `the_watchers_own_partial_keeps_its_observed_start` (`307.6 == 307`) |
| grace-gate-dropped | Tor nur `close_valve` | FAIL 4, nur in bestehenden Suiten: `test_self_closing.py` ×3 (`IndexError`, `0.0 == 15.0`) und `test_credit_ceiling.py::test_a_short_run_is_still_corrected_down_by_the_stop` (`0.0 == -2.5`) |
| branch-reverted | Zweig `elif False:` | FAIL 9 (= RED gegen den Elternstand) |
| before-end-books-plan (dry6) | (c) bucht `planned` statt des Fensters | FAIL 3: `stop_mid_run_is_measured_from_the_valve_on_report` (`600.0 == 100`), `valve_reporting_on_after_the_dispatch` (`600.0 == 99.6`), `before_the_planned_end_is_not_booked_on_an_off_report` (`600.0 == 302`) |
| else-books-plan (dry6) | letzter Zweig bucht `planned` statt `_sc_run_elapsed` | FAIL 8 in den 7 Suiten, in `tests/test_service_watch.py` 5: `write_only_run_keeps_the_elapsed_since_its_start` (`600.0 == 100`), `the_watchers_own_partial_keeps_its_observed_start` (`600.0 == 307`), T5 `off_after_an_unavailable_mid_run_keeps_the_old_rule`, T5 `seven_seconds_early_stays_partial`, T8 `found_off_mid_run` |

**T8 — 12 Proben, alle gefangen** (`real_t8_probes.py`; beobachtet an der T8-Station von dry3,
`dry3-logs/T8.md`). Testauswahl: `tests/test_service_watch.py` und `tests/test_self_closing.py`.

| Probe | Mutation (Neustart-Zweig) | Beobachtet |
|---|---|---|
| acquire-in-grace | `if elapsed < planned:` --> `if True:` | FAIL 5: +600, +604 ×3, +602 (`Expected mock to not have been awaited. Awaited 1 times.`) |
| acquire-dropped | --> `if False:` | FAIL 2: +100, +200 |
| acquire-lte | --> `<=` | FAIL +600 |
| stored-off-settle-reintroduced | Abschluss nach der Wartezeit wieder auf dem Fenster | FAIL +700-Pin (`601.0 == 600.0`) |
| past-grace-finish-on-window | `_sc_finish_run(zone_id, actual_s=window)` | FAIL 2: +700-Pin und `test_resume_finalises_overdue_and_reschedules_partial` |
| no-finish-past-grace | Abschluss --> `pass` | FAIL 4: +609, +700 ×2, write-only-Pin |
| threshold-back-to-planned | Schwelle `planned + grace` --> `planned` | FAIL 5 |
| threshold-strict | `>=` --> `>` | FAIL +609 |
| rearm-without-grace | `planned - elapsed` | FAIL 7 (`509.0/500.0`, `9.0/0.0`, `5.0/-4.0` ×3, `409.0/400.0`, `7.0/-2.0`) |
| grace-reverted | `grace = 0.0` | FAIL 7 |
| grace-for-every-record | `grace` = 5 + 4 für jeden Datensatz | FAIL write-only-Pin (`(2, 500.0)` gegen `(2, 509.0)`) |
| watcher-not-readopted | Neuaufnahme `if False:` | FAIL 11: 7 in der Klasse, dazu 4 bestehende Neuaufnahme-Tests |

**T9 — 8 Proben, alle gefangen** (Treiber-Satz `t09`, ganze Datei; beobachtet am dry3-Endstand,
`dry3-logs/T9.md`)

| Probe | Mutation | Beobachtet |
|---|---|---|
| drop-grace | In-flight ohne Wartezeit | FAIL 6 in der Datei, darunter beide Dispatch-Tests (`assert True is False`, `assert 2 == 1`) |
| anchor-prefers-valve-on | Anker `RUN_VALVE_ON` vor `RUN_OBSERVED_START` | FAIL nur `test_the_grace_counts_from_the_dispatch_not_the_valve_on_report` (die früher überlebende Anker-Mutation) |
| lte-boundary | `<` --> `<=` | FAIL nur `test_the_grace_ends_exactly_when_the_backstop_is_due` (`609.0`) |
| frozen-margin-to-default | `run_finish_grace_seconds` mit Default statt eingefrorener Marge | FAIL nur `test_a_confirmed_run_waits_out_its_own_frozen_margin` |
| grace-doubled | doppelte Wartezeit | FAIL 3 |
| grace-for-every-record | 5 + 4 für jeden Datensatz | FAIL 3 (Marge-10-Test, write-only- und Vor-dem-Update-Pin) |
| grace-without-plan | Fenster = nur Wartezeit | FAIL 8 |
| live-zone-margin | Marge aus der Zone statt aus dem Datensatz, hinter demselben Tor (`… if run_finish_grace_seconds(run) else 0.0`, wie Teil b, Task 9) | **umformuliert** (Spec, Mutationsproben T9): Ersatz jetzt über `zone_latency_margin`. Alte Form (über `zone_finish_grace_seconds`) beobachtet: FAIL 4 in der Datei, darunter der Marge-10-Test. Neue Form: nicht gemessen (trifft auf dry6 genau einmal und kompiliert); erwartet mindestens `test_a_confirmed_run_waits_out_its_own_frozen_margin` (Zone Marge 4, Datensatz 10). Mit dem Tor trifft sie die Pins für write-only und „vor der Marge“ nicht und prüft gezielt „Marge aus der Zone statt aus dem Datensatz“ |

**T11 — 8 Proben, alle gefangen** (Treiber-Satz `t11`, vitest; 6 aus Revision 2 nach dem Feinschliff an `7c626143`,
T11 ist seitdem nur im TS-Kommentar geändert, Entscheidung (e); 2 aus dry6, `dry6-logs/probes.md`)

| Probe | Beobachtet |
|---|---|
| gate-always-true | FAIL 3 „hides when …“ (`3 failed \| 5 passed (8)`) |
| gate-ignores-empty | FAIL „hides when confirm_entity is an empty string“ |
| clamp-no-upper | FAIL „clamps below 0 and above 30“ |
| clamp-no-lower | FAIL dito |
| clamp-no-round | FAIL „rounds to whole seconds“ |
| clamp-no-nan-guard | FAIL „ignores an empty or invalid input (NaN)“ |
| gate-always-false (dry6) | FAIL „shows when a confirm_entity is set“ (`expected false to be true`) |
| clamp-upper-29 (dry6) | FAIL „keeps a whole number inside the range“ und „clamps below 0 and above 30“ (`expected 29 to be 30`) |

**T12 — 2 Proben, beide gefangen** (Treiber-Satz `t12`; erster Probelauf an `0c205e46`; T12 ist ohne dist
patch-gleich)

| Probe | Beobachtet |
|---|---|
| sk-help-missing | FAIL `test_no_missing_keys[panel-sk]` (`… missing 1 key(s) … latency_margin_help`) |
| fr-help-english | FAIL `test_no_value_is_left_as_the_english_string[panel-fr]` |

Gemessen wurde bei 65 Tests `1 failed, 64 passed`. Die Datei hat auf `2b2c403b` 66 Tests (Suite-Dateien), also
wird hier `1 failed, 65 passed` erwartet.

**Summe (selbst gezählt aus den Tabellen oben)**

| Task | Proben | gefangen | äquivalent | davon umformuliert, auf dem neuen Text nicht gemessen |
|---|---|---|---|---|
| T1 | 6 | 6 | 0 | 0 |
| T2 | 24 | 24 | 0 | 0 |
| T3 | 16 | 16 | 0 | 1 (`backstop-grace-from-zone`) |
| T4 | 12 | 8 | 4 | 0 |
| T5 | 22 | 21 | 1 | 1 (`stop-actual-dropped`) |
| T7 | 23 | 23 | 0 | 0 |
| T8 | 12 | 12 | 0 | 0 |
| T9 | 8 | 8 | 0 | 1 (`live-zone-margin`) |
| T11 | 8 | 8 | 0 | 0 |
| T12 | 2 | 2 | 0 | 0 |
| **Gesamt** | **133** | **128** | **5** | **3** |

- Gelaufen wird 134-mal (Treiber 88, CRLF-Skripte 46): die T5-Dublette `unavailable-accepted` läuft im Skript mit,
  zählt aber nicht doppelt.
- Erwartet werden 0 überlebende nicht-äquivalente Proben, und jedes der 101 neuen Test-Items scheitert an mindestens
  einer Probe. Belegt ist das für die protokollierten Läufe (`dry6-logs/killmap.md`: vor den dry6-Proben 9 Items
  ohne fangende Probe, danach 0); Step 8b prüft es auf dem echten Branch.

Nicht gefahren, weil der Code nicht mehr existiert:

- T3b: 3 Proben; T6: 7 Proben; T10: 4 Proben.
- Die drei T2-Proben und die eine T3-Probe mit `zone_finish_grace_seconds`.
- Die überholten Rev.-2-Sätze von T7 (7 Proben) und T8 (11 Proben). Ihr Code ist durch (a), (c), (d), (f)
  ersetzt, und die dry3-Sätze prüfen die neuen Zeilen.

Überlebt eine als gefangen erwartete Probe: STOPP. Zuerst klären, ob die Probe nicht greift (Suchtext, falsche
Datei) oder ob ein Test fehlt. Ein fehlender Test ist ein Defekt nach der Regel in der Task-Einleitung. Wird
eine äquivalente Probe gefangen, ist das kein Fehler; das Protokoll hält es fest.

- [ ] **Step 8b: Jedes neue Test-Item scheitert an mindestens einer Probe** (JustChr 09-14 „Please mutation-test each
  one“, 09-16 „Mutation-test each new test“)

Die neuen Items: die 89 neuen Testfunktionen (per `ast` gegen `2b2c403b`, mit dem dry6-Skript `newtests.py`, auf das
Haupt-Repo umgestellt), die parametrisierte mit ihren 5 Fällen, zusammen 93, dazu die 8 vitest-`it` von T11: 101. Gegen
sie die Vereinigung aller `FAILED`-Namen (pytest) und `FAIL`-Namen (vitest) aus den vier Protokollen von Step 8.

```bash
cd /d/Entwicklung/HASI/HAsmartirrigation
M=/d/Entwicklung/HASI/pr139-work/mut
sed 's#D = "D:/Entwicklung/HASI/pr139-work/dry2"#D = "D:/Entwicklung/HASI/HAsmartirrigation"#' /d/Entwicklung/HASI/pr139-work/scratch/dry6/newtests.py > $M/real_newtests.py
grep -c 'HAsmartirrigation"' $M/real_newtests.py
./.venv/Scripts/python.exe $M/real_newtests.py > $M/real-newtests.tsv
wc -l < $M/real-newtests.tsv
./.venv/Scripts/python.exe - <<'EOF'
import pathlib
M = pathlib.Path("D:/Entwicklung/HASI/pr139-work/mut")
CASES = ["7-7", "7.6-8", "-3-0", "99-30", "x-4"]
items = []
for line in (M / "real-newtests.tsv").read_text(encoding="utf-8").splitlines():
    _sha, _subject, tid, params = line.split("\t")
    items += [f"{tid}[{c}]" for c in CASES] if params else [tid]
VITEST = ["shows when a confirm_entity is set", "hides when confirm_entity is null",
          "hides when confirm_entity is an empty string", "hides when confirm_entity is missing",
          "keeps a whole number inside the range", "rounds to whole seconds",
          "clamps below 0 and above 30", "ignores an empty or invalid input (NaN)"]
failed, failed_vitest = set(), set()
for log in ["real-rev3-probes.txt", "real-T5-probes.txt", "real-T7-probes.txt", "real-T8-probes.txt"]:
    for line in (M / log).read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if line.startswith("FAILED "):
            failed.add(line[len("FAILED "):].split(" - ")[0].strip())
        elif line.startswith("FAIL "):
            failed_vitest.add(line.split(" > ")[-1].strip())
missing = [i for i in items if i not in failed] + [v for v in VITEST if v not in failed_vitest]
print(f"items {len(items)} + {len(VITEST)} vitest = {len(items) + len(VITEST)}; ohne fangende Probe: {len(missing)}")
for m in missing:
    print("  ", m)
EOF
```

Erwartet: `1` aus `grep -c`; `89` Zeilen in `real-newtests.tsv` (so viele lieferte das Skript auf dry6,
`scratch/dry6/newtests.tsv`); dann `items 93 + 8 vitest = 101; ohne fangende Probe: 0`. Nennt die Liste ein Item: STOPP
wie bei einer überlebenden Probe (siehe oben), zuerst prüfen, ob eine erwartete Probe nicht gegriffen hat.

**Soll-Zuordnung Item --> fangende Proben.** Aus `dry6-logs/killmap.md` (dort mit den Laufbezeichnungen von Revision 2,
dry3 und dry6), hier mit den Satz- und Skriptnamen von Step 8. Satz `tNN` = Treiber `rev3_probes.py`,
„T5/T7/T8-Skript“ = `real_t5/t7/t8_probes.py`. Die Namen stammen aus Läufen am jeweiligen Task-Commit bzw. am dry6-Endstand;
am echten Endstand kann eine Probe weitere Tests fangen. ¹ = neu formuliert, gemessen ist nur die alte Form.

**T1**

| # | Test-Item | fangende Proben (Satz bzw. Skript: Probe) |
|---|---|---|
| 1 | `test_zone_view_coerces_latency_margin_to_int` | t01: ws-coerce-float, ws-coerce-removed |
| 2 | `test_latency_margin_survives_reload` | t01: load-line, store-revert |
| 3 | `test_zone_stored_without_latency_margin_loads_the_default` | t01: const-default, load-default, store-revert |

**T2**

| # | Test-Item | fangende Proben (Satz bzw. Skript: Probe) |
|---|---|---|
| 1 | `TestZoneLatencyMargin::test_the_margin_is_whole_seconds_clamped_to_its_bounds[7-7]` | t02: string-margin-is-garbage |
| 2 | `TestZoneLatencyMargin::test_the_margin_is_whole_seconds_clamped_to_its_bounds[7.6-8]` | t02: zone-round |
| 3 | `TestZoneLatencyMargin::test_the_margin_is_whole_seconds_clamped_to_its_bounds[-3-0]` | t02: zone-clamp |
| 4 | `TestZoneLatencyMargin::test_the_margin_is_whole_seconds_clamped_to_its_bounds[99-30]` | t02: zone-clamp |
| 5 | `TestZoneLatencyMargin::test_the_margin_is_whole_seconds_clamped_to_its_bounds[x-4]` | t02: zone-garbage |
| 6 | `TestZoneLatencyMargin::test_a_zone_stored_without_a_margin_gets_the_default` | t02: zone-default |
| 7 | `TestRunLatencyMargin::test_the_frozen_margin_is_read_back_as_seconds` | t02: frozen-margin-constant |
| 8 | `TestRunLatencyMargin::test_a_record_without_a_margin_answers_none` | t02: no-margin-reads-zero |
| 9 | `TestRunLatencyMargin::test_a_negative_margin_reads_as_zero_and_garbage_as_none` | t02: frozen-margin-constant, run-margin-negative |
| 10 | `TestRunHasFinishGrace::test_a_confirmed_service_run_with_a_margin_has_it` | t02: policy-service-flag |
| 11 | `TestRunHasFinishGrace::test_a_record_from_before_the_update_has_none` | t02: no-margin-reads-zero, run-grace-margin-gate |
| 12 | `TestRunHasFinishGrace::test_an_unconfirmed_run_has_none` | t02: run-grace-watch-gate |
| 13 | `TestRunHasFinishGrace::test_a_batch_record_carrying_both_keys_has_none` | t02: run-grace-policy |
| 14 | `TestRunHasFinishGrace::test_an_opensprinkler_record_carrying_both_keys_has_none` | t02: run-grace-policy |
| 15 | `TestRunFinishGraceAndTolerance::test_the_grace_is_settle_plus_the_frozen_margin` | t02: run-grace-settle |
| 16 | `TestRunFinishGraceAndTolerance::test_a_run_without_grace_waits_nothing_extra` | t02: run-grace-watch-gate |
| 17 | `TestRunFinishGraceAndTolerance::test_the_completion_tolerance_is_the_margin` | t02: tolerance-always-one |
| 18 | `TestRunFinishGraceAndTolerance::test_the_completion_tolerance_never_drops_below_one_second` | t02: frozen-margin-constant, tolerance-floor |
| 19 | `TestRunFinishGraceAndTolerance::test_a_run_without_grace_keeps_the_one_second_slack` | t02: tolerance-no-grace |
| 20 | `TestValveWindowSeconds::test_the_window_is_the_off_report_minus_the_on_report` | t02: window-anchor-valve-on |
| 21 | `TestValveWindowSeconds::test_an_off_report_before_the_on_report_is_a_zero_window` | t02: window-off-clamp |
| 22 | `TestValveWindowSeconds::test_without_an_off_report_the_window_is_the_time_since_on` | T5-Skript: window-planned-without-off |
| 23 | `TestValveWindowSeconds::test_without_an_off_report_the_window_is_bounded_by_the_plan` | t02: window-plan-bound |
| 24 | `TestValveWindowSeconds::test_the_anchor_falls_back_to_the_observed_start` | t02: window-anchor-observed |
| 25 | `TestValveWindowSeconds::test_the_anchor_falls_back_to_the_dispatch_instant` | t02: anchor-no-started-fallback |
| 26 | `TestValveWindowSeconds::test_a_record_with_no_anchor_answers_the_plan` | t02: window-no-anchor |
| 27 | `TestOnlyTheServicePolicySettlesOnTheValveWindow::test_the_service_policy_settles_on_the_valve_window` | t02: policy-service-flag |
| 28 | `TestOnlyTheServicePolicySettlesOnTheValveWindow::test_the_batch_policy_does_not` | t02: policy-default-true |
| 29 | `TestOnlyTheServicePolicySettlesOnTheValveWindow::test_the_opensprinkler_policy_does_not` | t02: policy-default-true |
| 30 | `TestABatchResumeArmsExactlyTheRemainder::test_resume_re_arms_the_backstop_for_the_remaining_window_only` | t02: resume-adds-settle |

**T3**

| # | Test-Item | fangende Proben (Satz bzw. Skript: Probe) |
|---|---|---|
| 1 | `TestAConfirmedRunFreezesItsMarginAtDispatch::test_the_default_margin_is_frozen_into_the_record` | t03: margin-record |
| 2 | `TestAConfirmedRunFreezesItsMarginAtDispatch::test_the_zones_own_margin_is_frozen_into_the_record` | t03: margin-default, margin-record |
| 3 | `TestAConfirmedRunFreezesItsMarginAtDispatch::test_a_write_only_run_carries_neither_margin_nor_valve_on` | t03: margin-for-every-record |
| 4 | `TestAConfirmedRunFreezesItsMarginAtDispatch::test_an_unverifiable_run_carries_neither_margin_nor_valve_on` | t03: margin-for-every-record, valve-on-for-unverifiable |
| 5 | `TestTheValveOnReportIsClampedToTheDispatch::test_a_valve_already_open_is_anchored_at_the_dispatch` | t03: clamp-lower, valve-on-record |
| 6 | `TestTheValveOnReportIsClampedToTheDispatch::test_a_valve_reporting_on_after_the_dispatch_is_anchored_at_its_report` | t03: lower-is-confirm-return, report-ignored, upper-is-dispatch, valve-on-record |
| 7 | `TestTheValveOnReportIsClampedToTheDispatch::test_a_report_stamped_after_the_confirm_returned_is_clamped_to_it` | t03: clamp-upper, upper-is-dispatch, valve-on-record |
| 8 | `TestTheBackstopWaitsOnlyForAConfirmedValve::test_a_margin_of_zero_still_waits_out_the_debounce` | t02: frozen-margin-constant; t03: backstop-never-armed, backstop-no-grace, margin-default, margin-record |
| 9 | `TestTheBackstopWaitsOnlyForAConfirmedValve::test_a_write_only_run_is_backstopped_at_exactly_its_window` | t03: backstop-never-armed, backstop-grace-always |
| 10 | `TestTheBackstopWaitsOnlyForAConfirmedValve::test_an_unverifiable_run_is_backstopped_at_exactly_its_window` | t03: backstop-never-armed, backstop-grace-always, backstop-grace-from-zone¹ |
| 11 | `TestAMissedCloseStillSettlesViaTheBackstop::test_a_valve_that_never_reports_off_is_finished_when_the_grace_is_out` | t03: backstop-callback-dropped, backstop-finishes-on-elapsed, backstop-never-armed, backstop-no-grace |

**T4**

| # | Test-Item | fangende Proben (Satz bzw. Skript: Probe) |
|---|---|---|
| 1 | `TestTheWatcherRecordsTheValvesOwnOffReport::test_an_off_event_records_the_states_last_changed` | t04: clock-not-last-changed, previous-state-not-passed |
| 2 | `TestTheWatcherRecordsTheValvesOwnOffReport::test_an_attribute_only_update_does_not_move_the_off_report` | t04: clock-not-last-changed, previous-state-not-passed |
| 3 | `TestTheWatcherRecordsTheValvesOwnOffReport::test_an_off_after_an_unavailable_spell_keeps_the_first_off_report` | t04: clock-not-last-changed, previous-state-not-passed |
| 4 | `TestTheWatcherRecordsTheValvesOwnOffReport::test_an_off_after_an_unavailable_mid_run_records_nothing` | t04: running-condition-removed, unavailable-accepted; T5-Skript: unavailable-accepted |
| 5 | `TestTheWatcherRecordsTheValvesOwnOffReport::test_an_on_inside_the_debounce_clears_the_off_report` | t04: clear-gated-on-segmented, clear-removed, clock-not-last-changed, previous-state-not-passed |
| 6 | `TestTheWatcherRecordsTheValvesOwnOffReport::test_a_re_adopted_run_does_not_record_the_initial_off` | t04: initial-evaluate-records; T8-Skript: watcher-not-readopted |
| 7 | `TestTheWatcherRecordsTheValvesOwnOffReport::test_a_re_adopted_run_does_not_record_an_off_after_unavailable` | t04: running-condition-removed, unavailable-accepted; T5-Skript: unavailable-accepted; T8-Skript: watcher-not-readopted |
| 8 | `TestTheWatcherRecordsTheValvesOwnOffReport::test_a_record_from_before_the_update_records_nothing` | t02: no-margin-reads-zero; t04: grace-gate-removed |

**T5**

| # | Test-Item | fangende Proben (Satz bzw. Skript: Probe) |
|---|---|---|
| 1 | `TestAConfirmedRunIsSettledOnItsValveWindow::test_a_close_just_after_the_window_completes_on_the_reported_window` | T5-Skript: gate-inverted, never-routed |
| 2 | `TestAConfirmedRunIsSettledOnItsValveWindow::test_a_close_inside_the_margin_completes_on_the_reported_window` | t02: tolerance-always-one; T5-Skript: gate-inverted, never-routed |
| 3 | `TestAConfirmedRunIsSettledOnItsValveWindow::test_a_close_beyond_the_margin_is_a_partial_credited_for_its_window` | T5-Skript: gate-inverted, never-routed |
| 4 | `TestAConfirmedRunIsSettledOnItsValveWindow::test_a_margin_of_zero_still_tolerates_one_second` | T5-Skript: gate-inverted, never-routed |
| 5 | `TestAConfirmedRunIsSettledOnItsValveWindow::test_a_margin_of_zero_settles_a_close_beyond_that_second_as_partial` | t02: frozen-margin-constant; T5-Skript: gate-inverted, never-routed |
| 6 | `TestAConfirmedRunIsSettledOnItsValveWindow::test_an_off_after_an_unavailable_mid_run_keeps_the_old_rule` | T5-Skript: unavailable-accepted; t07add: else-books-plan |
| 7 | `TestAConfirmedRunIsSettledOnItsValveWindow::test_an_unreported_close_seven_seconds_early_stays_partial` | T5-Skript: always-routed, base-tolerance-margin, base-tolerance-two, gate-dropped, gate-inverted, gate-wrong-key, unavailable-accepted; t07add: else-books-plan |
| 8 | `TestAConfirmedRunIsSettledOnItsValveWindow::test_an_unreported_close_inside_the_old_second_completes_for_its_plan` | T5-Skript: always-routed, base-finish-passes-elapsed, base-tolerance-zero, gate-dropped, gate-inverted, gate-wrong-key, unavailable-accepted |
| 9 | `TestAConfirmedRunIsSettledOnItsValveWindow::test_a_record_from_before_the_update_keeps_the_old_rule` | t02: no-margin-reads-zero; T5-Skript: always-routed, base-finish-passes-elapsed, base-tolerance-zero |
| 10 | `TestACloseReportedPastTheMarginIsKnownAndDeliberatelyUnchanged::test_the_backstop_finishes_it_for_the_plan_before_the_debounce` | t05pin: t6-backstop-settles-on-stored-off |

**T7**

| # | Test-Item | fangende Proben (Satz bzw. Skript: Probe) |
|---|---|---|
| 1 | `TestAManualStopMeasuresFromTheValvesOnReport::test_a_stop_mid_run_is_measured_from_the_valve_on_report` | t07add: before-end-books-plan |
| 2 | `TestAManualStopMeasuresFromTheValvesOnReport::test_a_valve_reporting_on_after_the_dispatch_is_measured_from_its_report` | T7-Skript: before-from-observed-start, branch-reverted; t07add: before-end-books-plan |
| 3 | `TestAManualStopMeasuresFromTheValvesOnReport::test_a_stop_before_the_planned_end_is_not_booked_on_an_off_report` | T7-Skript: before-uses-stored-off, end-inverted, end-removed-always-after; t07add: before-end-books-plan |
| 4 | `TestAManualStopMeasuresFromTheValvesOnReport::test_a_stop_just_before_the_planned_end_is_capped_at_the_plan` | T7-Skript: before-from-observed-start, before-uncapped, branch-reverted, end-anchored-on-valve-on, end-inverted, end-removed-always-after |
| 5 | `TestAManualStopMeasuresFromTheValvesOnReport::test_a_stop_in_the_grace_after_an_off_report_inside_the_tolerance_completes` | t02: tolerance-always-one; T7-Skript: after-ignores-stored-off, after-measured-to-stop, branch-reverted, completed-branch-dropped, end-inverted, end-removed-always-before, finish-without-actual-s, no-return-after-finish, settle-before-close, tolerance-ignored, tolerance-one-second, valve-not-closed-when-past-end |
| 6 | `TestAManualStopMeasuresFromTheValvesOnReport::test_a_stop_in_the_grace_after_a_late_off_report_completes_on_it` | T7-Skript: after-ignores-stored-off, after-measured-to-stop, branch-reverted, completed-branch-dropped, end-inverted, end-removed-always-before, finish-without-actual-s, no-return-after-finish, settle-before-close, valve-not-closed-when-past-end |
| 7 | `TestAManualStopMeasuresFromTheValvesOnReport::test_a_stop_in_the_grace_after_an_off_report_beyond_the_tolerance_is_partial` | t02: frozen-margin-constant; T7-Skript: after-ignores-stored-off, after-measured-to-stop, always-completed, branch-reverted, end-inverted, end-removed-always-before |
| 8 | `TestAManualStopMeasuresFromTheValvesOnReport::test_a_stop_in_the_grace_with_the_valve_still_on_completes_for_the_plan` | T7-Skript: after-measured-to-stop, branch-reverted, completed-branch-dropped, end-inverted, end-removed-always-before, no-return-after-finish, settle-before-close, valve-not-closed-when-past-end |
| 9 | `TestAManualStopMeasuresFromTheValvesOnReport::test_a_stop_exactly_at_the_planned_end_is_settled_in_the_grace` | T7-Skript: branch-reverted, completed-branch-dropped, end-inverted, end-lte, end-removed-always-before, no-return-after-finish |
| 10 | `TestAManualStopMeasuresFromTheValvesOnReport::test_a_stop_all_in_the_grace_settles_the_run_the_same_way` | T7-Skript: after-ignores-stored-off, after-measured-to-stop, branch-reverted, completed-branch-dropped, end-inverted, end-removed-always-before, finish-without-actual-s, no-return-after-finish, settle-before-close, valve-not-closed-when-past-end |
| 11 | `TestAManualStopMeasuresFromTheValvesOnReport::test_a_completing_stop_books_exactly_what_the_watcher_would` | T7-Skript: after-ignores-stored-off, after-measured-to-stop, branch-reverted, completed-branch-dropped, end-inverted, end-removed-always-before, finish-without-actual-s, no-return-after-finish |
| 12 | `TestAManualStopMeasuresFromTheValvesOnReport::test_the_watchers_own_partial_keeps_its_observed_start` | T5-Skript: base-partial-passes-window; T7-Skript: close-valve-gate-dropped; t07add: else-books-plan |
| 13 | `TestAManualStopMeasuresFromTheValvesOnReport::test_a_write_only_run_keeps_the_elapsed_since_its_start` | t07add: else-books-plan |

**T8**

| # | Test-Item | fangende Proben (Satz bzw. Skript: Probe) |
|---|---|---|
| 1 | `TestARestartCarriesTheFinishGrace::test_a_run_inside_its_window_re_arms_the_backstop_with_the_grace` | T8-Skript: acquire-dropped, grace-reverted, rearm-without-grace, watcher-not-readopted |
| 2 | `TestARestartCarriesTheFinishGrace::test_a_restart_exactly_at_the_plan_takes_no_master_hold` | T8-Skript: acquire-in-grace, acquire-lte, grace-reverted, rearm-without-grace, threshold-back-to-planned, watcher-not-readopted |
| 3 | `TestARestartCarriesTheFinishGrace::test_a_restart_inside_the_grace_does_not_finish_a_valve_still_on` | T8-Skript: acquire-in-grace, grace-reverted, rearm-without-grace, threshold-back-to-planned, watcher-not-readopted |
| 4 | `TestARestartCarriesTheFinishGrace::test_a_valve_found_off_inside_the_grace_completes_for_its_plan` | T8-Skript: acquire-in-grace, grace-reverted, rearm-without-grace, threshold-back-to-planned, watcher-not-readopted |
| 5 | `TestARestartCarriesTheFinishGrace::test_a_valve_back_from_unavailable_completes_for_its_plan` | T8-Skript: acquire-in-grace, grace-reverted, rearm-without-grace, threshold-back-to-planned, watcher-not-readopted |
| 6 | `TestARestartCarriesTheFinishGrace::test_a_valve_found_off_mid_run_is_a_partial_up_to_the_decision` | t07add: else-books-plan; T8-Skript: acquire-dropped, grace-reverted, rearm-without-grace, watcher-not-readopted |
| 7 | `TestARestartCarriesTheFinishGrace::test_a_stored_off_report_inside_the_grace_settles_on_its_window` | T8-Skript: acquire-in-grace, grace-reverted, rearm-without-grace, threshold-back-to-planned, watcher-not-readopted |
| 8 | `TestARestartCarriesTheFinishGrace::test_a_restart_exactly_at_the_end_of_the_grace_finishes_the_run` | T8-Skript: no-finish-past-grace, threshold-strict |
| 9 | `TestARestartCarriesTheFinishGrace::test_a_stored_off_report_past_the_grace_is_finished_for_the_plan` | T8-Skript: no-finish-past-grace, past-grace-finish-on-window, stored-off-settle-reintroduced |
| 10 | `TestARestartCarriesTheFinishGrace::test_no_off_report_past_the_grace_completes_for_the_plan_at_once` | T8-Skript: no-finish-past-grace |

**T9**

| # | Test-Item | fangende Proben (Satz bzw. Skript: Probe) |
|---|---|---|
| 1 | `test_a_confirmed_service_run_stays_in_flight_through_its_finish_grace` | t09: drop-grace, grace-doubled, grace-without-plan, live-zone-margin¹ |
| 2 | `test_a_write_only_service_run_gets_no_finish_grace` | t09: grace-for-every-record |
| 3 | `test_a_service_run_persisted_before_the_margin_keeps_its_window` | t09: grace-for-every-record |
| 4 | `test_a_confirmed_run_waits_out_its_own_frozen_margin` | t02: frozen-margin-constant; t09: drop-grace, frozen-margin-to-default, grace-doubled, grace-for-every-record, grace-without-plan, live-zone-margin¹ |
| 5 | `test_the_grace_counts_from_the_dispatch_not_the_valve_on_report` | t09: anchor-prefers-valve-on, drop-grace, grace-without-plan, live-zone-margin¹ |
| 6 | `test_the_grace_ends_exactly_when_the_backstop_is_due` | t09: drop-grace, grace-doubled, grace-without-plan, live-zone-margin¹, lte-boundary |
| 7 | `TestASecondDispatchInsideTheFinishGraceIsRefused::test_a_second_self_closing_dispatch_is_refused` | t03: backstop-callback-dropped, backstop-never-armed; t09: drop-grace, grace-without-plan |
| 8 | `TestASecondDispatchInsideTheFinishGraceIsRefused::test_a_manual_run_zone_is_refused_the_same_way` | t03: backstop-callback-dropped, backstop-never-armed; t09: drop-grace, grace-without-plan |

**T11**

| # | Test-Item | fangende Proben (Satz bzw. Skript: Probe) |
|---|---|---|
| 1 | vitest „shows when a confirm_entity is set“ | t11: gate-always-false |
| 2 | vitest „hides when confirm_entity is null“ | t11: gate-always-true |
| 3 | vitest „hides when confirm_entity is an empty string“ | t11: gate-always-true, gate-ignores-empty |
| 4 | vitest „hides when confirm_entity is missing“ | t11: gate-always-true |
| 5 | vitest „keeps a whole number inside the range“ | t11: clamp-upper-29 |
| 6 | vitest „rounds to whole seconds“ | t11: clamp-no-round |
| 7 | vitest „clamps below 0 and above 30“ | t11: clamp-upper-29, clamp-no-lower, clamp-no-upper |
| 8 | vitest „ignores an empty or invalid input (NaN)“ | t11: clamp-no-nan-guard |

Das Ergebnis geht mit Zahlen nach `D:/Entwicklung/HASI/pr139-work/real-final-check.md`:

- Probenzahl gesamt, gefangen, äquivalent;
- das Ergebnis von Step 8b (Items ohne fangende Probe, erwartet 0);
- die Suite-Zeilen aus Step 3;
- vitest aus Step 4.

Task 14 liest die Zahlen von dort.

- [ ] **Step 9: Kein Commit**

Dieser Task committet nichts. Die `.bak`-Dateien unter `mut/` dürfen danach gelöscht werden; sie liegen
außerhalb des Repos.

---

### Task 14: PR, Kommentare, Issue, Design-Historie

Es gelten:

- globale `CLAUDE.md`: „Text-Freigabe“ und „Alles, was nach außen geht … nur nach expliziter Freigabe“;
- Skill `pr-workflow`, bei Abschluss `superpowers:finishing-a-development-branch`;
- Regel P1 der Projekt-`CLAUDE.md`;
- Memories `workflow-agent-hygiene` (Zahlen auf dem Endstand nachmessen), `no-branch-shas-in-upstream-comments`,
  `no-ip-in-release-notes` und `regression-pin-on-removals` (PR-Text: „Node 22 (CI-pinned)“).

Reihenfolge nach außen: erst der PR, dann das Issue, dann der Kommentar auf #139. Das Issue und der Kommentar
nennen die PR-Nummer, und das Issue darf erst entstehen, wenn der PR existiert. Task 15 kann parallel zum PR
laufen. Der Merge wartet auf Task 15 (JustChr 09-19).

**Files:**

- Create (außerhalb des Repos):
  - `D:/Entwicklung/HASI/pr139-work/pr-body.md`
  - `D:/Entwicklung/HASI/pr139-work/issue-window-pricing-final.md`
  - `D:/Entwicklung/HASI/pr139-work/comment-139-pr.md`
- Modify:
  - `D:/Entwicklung/HASI/ToDo.md`
  - `HAsmartirrigation/docs/SESSION-STAND.md` (untracked)
  - Memory `hasi-backstop-has-no-grace.md` und die zugehörige Zeile in `MEMORY.md`
- Archiv: Spec, Plan Revision 3 und ein Umsetzungsnachtrag auf `archive/design-history`

- [ ] **Step 1: Zahlen auf dem Endstand übernehmen**

Aus `real-final-check.md` (Task 13):

- die Suite-Zeilen Basis und Endstand vom selben Tag;
- neue Items, erwartet +93;
- vitest Basis und Endstand, erwartet 616 --> 624;
- Proben gesamt, gefangen, äquivalent, erwartet 133 / 128 / 5;
- Items ohne fangende Probe (Step 8b), erwartet 0 von 101.

Jede Zahl im PR-Text muss aus diesen Ausgaben stammen, nicht aus diesem Plan und nicht aus dry6.

- [ ] **Step 2: PR-Text fertigstellen**

`rev3/pr-body-draft.md` nach `pr139-work/pr-body.md` kopieren. Darin:

- den HTML-Kommentar am Anfang löschen;
- alle Platzhalter `<from Task 13 …>` durch die Zahlen aus Step 1 ersetzen;
- den Abschnitt „Live test“ so lassen, wie er ist (Plan, Ergebnis folgt als Kommentar);
- `#<issue>` bleibt, bis Step 6 die Nummer liefert.

Prüf-Greps:

```bash
F=/d/Entwicklung/HASI/pr139-work/pr-body.md
grep -nE "\b([0-9]{1,3}\.){3}[0-9]{1,3}\b" $F; echo "(IP: Ende)"
grep -nE "\b[0-9a-f]{7,40}\b" $F; echo "(SHA: Ende)"
grep -nE "HA-Prod|HA-Test|Eifel|Kirschbaum|dry[0-9]|pr139-work|fix/backstop|T3b|\bT6\b|T10|<from Task" $F; echo "(Arbeitsnamen und Platzhalter: Ende)"
grep -n "Generated with \[Claude Code\]" $F
```

Erwartet: vor jedem „Ende“ keine Zeile, dann genau eine Footer-Zeile. Erlaubt sind die Namen, die #139 schon
benutzt (Beet, Kirschlorbeer).

- [ ] **Step 3: Text im Chat vorlegen, Freigabe abwarten**

Vorgelegt werden der PR-Text vollständig und der Titel. Titelvorschlag:
`Let the service watcher settle a normal run end: a finish grace with a per-zone latency margin`.
Ohne ausdrückliches „ja“ gibt es keinen Push und kein `gh`.

- [ ] **Step 4: Push und PR (nur nach Freigabe)**

```bash
cd /d/Entwicklung/HASI/HAsmartirrigation
git status --short --untracked-files=no
git fetch upstream
git rev-list --count HEAD..upstream/master
git push -u origin fix/backstop-grace
gh pr create --repo JustChr/HAsmartirrigation --base master --head Eifel-Joe:fix/backstop-grace \
  --title "Let the service watcher settle a normal run end: a finish grace with a per-zone latency margin" \
  --body-file /d/Entwicklung/HASI/pr139-work/pr-body.md
```

Erwartet: `0` behind vor dem Push und danach die PR-URL. Ist `upstream/master` inzwischen weiter: STOPP und
den User fragen. Nach der Projekt-Regel wird dann gemergt, nicht rebased.

- [ ] **Step 5: CI verfolgen**

`mcp__ccd_pr__get_status` für den neuen PR, ersatzweise `gh pr checks <PR> --repo JustChr/HAsmartirrigation`.
Erwartet: alle Checks grün. Ein roter Check ist vor jedem weiteren Außenschritt zu klären.

- [ ] **Step 6: Issue zum Zeitfenster-Preis (nur nach Freigabe, erst wenn der PR existiert)**

`rev3/issue-window-pricing.md` nach `pr139-work/issue-window-pricing-final.md` kopieren, den HTML-Kommentar am
Anfang löschen und `#<PR>` einsetzen. Die Confirm-Spanne (0,46–0,97 s) muss mit dem endgültigen PR-Text
übereinstimmen. Den Text im Chat vorlegen; nach „ja“:

```bash
gh issue create --repo JustChr/HAsmartirrigation \
  --title "Price a confirmed service zone's finish grace into the run window" \
  --body-file /d/Entwicklung/HASI/pr139-work/issue-window-pricing-final.md
```

Danach im PR-Text `#<issue>` durch die Nummer ersetzen. Die geänderte Zeile im Chat zeigen und nach Freigabe
anwenden:
`gh pr edit <PR> --repo JustChr/HAsmartirrigation --body-file /d/Entwicklung/HASI/pr139-work/pr-body.md`.

- [ ] **Step 7: Kommentar auf #139 (nur nach Freigabe)**

Entwurf für `pr139-work/comment-139-pr.md` (Englisch, kurz; Nummern nach Step 4 und 6 einsetzen):

```markdown
The PR is up: #<PR>.

It is the shape from 09-14 with what 09-16 and 09-19 settled:

- a finish grace of `finish_settle_seconds` + a per-zone `latency_margin` (default 4 s, 0-30) on the backstop
  of confirmed service runs only; write-only runs keep exactly the planned window;
- `actual_s` from the valve's own on and off reports, with `max(1 s, margin)` as the completion tolerance
  when the off report is on record;
- in-flight running to the end of the grace, with the dispatch-level tests (a second
  `async_run_self_closing` and a `run_zone` refused; record, meter, master hold and backstop untouched;
  the anchor mutation is caught now);
- the same grace on a restart, with a test that the master is not requested inside the grace;
- a manual stop inside the grace settled by the watcher's rule;
- the zone field in the panel and the eight panel catalogues, dist rebuilt, byte-identical to the Node 22 (CI-pinned)
  build;
- the tests you asked for, each mutation-tested, including a missed close settled by the real backstop timer, and a
  test pinning the late off report that stays as today.

Known and deliberately unchanged, each listed in the PR body: the backstop with a stored off report (both
triggers) and its restart twin, runs without a stored off report, a manual stop before the planned end,
the sub-second gap between the end of in-flight and the backstop removing the record, the observed-watering
lockout after the settle, and the window pricing, now #<issue>.

Before the merge, the re-measurement: first the test instance, with a valve emulator driven by a script on
the instance itself (normal end, a late report inside and beyond the margin, an early close inside and beyond
the margin, a stop and a restart inside the grace, a close nobody reported, a second dispatch inside the
grace); then one short manual run on each of the two zones on the production install. I'll post the numbers
as a comment on the PR and link it here.
```

```bash
gh issue comment 139 --repo JustChr/HAsmartirrigation --body-file /d/Entwicklung/HASI/pr139-work/comment-139-pr.md
```

- [ ] **Step 8: Design-Historie archivieren (Regel P1; Push nur nach Freigabe)**

Der Archiv-Worktree liegt unter `D:/Entwicklung/HASI/pr139-work/archive-wt` auf `archive/design-history`. Er
ist lokal 3 Commits voraus: `0280abb5`, `0ddd8cb6`, `fbb535a5` (Spec, Spec-Revision, Plan Revision 2).

1. Spec Revision 3: `rev3/spec.md` --> `docs/superpowers/specs/2026-09-15-backstop-grace-design.md`
   (überschreibt; die Geschichte bleibt in git).
2. Plan Revision 3: die Teile `rev3/plan-*.md` in Namensreihenfolge zusammensetzen -->
   `docs/superpowers/plans/2026-09-15-backstop-grace.md`. Davor listet `ls` die Teile, und der User bestätigt
   die Reihenfolge.
3. Umsetzungsnachtrag am Ende der Spec, Abschnitt `## Umsetzung (<Datum>)`, mit folgendem Inhalt:
   - PR-Nummer, Issue-Nummer;
   - Endzahlen aus `real-final-check.md`;
   - Abweichungen vom Plan (keine erwartet);
   - Stand des Live-Tests („folgt“, bis Task 15 ihn liefert).

```bash
cd /d/Entwicklung/HASI/HAsmartirrigation
WT=/d/Entwicklung/HASI/pr139-work/archive-wt
git worktree list | grep "archive/design-history"
git -C "$WT" status --short
ls /d/Entwicklung/HASI/pr139-work/rev3/plan-*.md
cp /d/Entwicklung/HASI/pr139-work/rev3/spec.md "$WT/docs/superpowers/specs/2026-09-15-backstop-grace-design.md"
cat $(ls /d/Entwicklung/HASI/pr139-work/rev3/plan-*.md | sort) > "$WT/docs/superpowers/plans/2026-09-15-backstop-grace.md"
# Umsetzungsnachtrag von Hand ans Spec-Ende anhängen, dann:
git -C "$WT" diff --stat
git -C "$WT" add docs/superpowers/specs/2026-09-15-backstop-grace-design.md docs/superpowers/plans/2026-09-15-backstop-grace.md
git -C "$WT" commit -m "docs: revise the #139 finish backstop grace to revision 3 and record its implementation"
git -C "$WT" log --oneline -5
```

Push nur nach Freigabe: `git -C "$WT" push origin archive/design-history`. Erwartet: vier Archiv-Commits gehen
mit hinaus. Der Worktree bleibt stehen, bis Task 15 sein Ergebnis im Nachtrag ergänzt hat (eigener Commit,
eigene Freigabe). Danach:
`git -C /d/Entwicklung/HASI/HAsmartirrigation worktree remove /d/Entwicklung/HASI/pr139-work/archive-wt`.

- [ ] **Step 9: Aufräumen (erst nach Step 8 und erst, wenn der echte Branch alles enthält)**

```bash
cd /d/Entwicklung/HASI/HAsmartirrigation
paste <(git rev-list --reverse 2b2c403b..dry6/backstop-grace) <(git rev-list --reverse 2b2c403b..fix/backstop-grace) | while read a b; do git diff --quiet $a $b && echo same || echo "DIFF $a $b"; done | sort | uniq -c
git diff --stat dry6/backstop-grace fix/backstop-grace
git branch -r | grep -E "dry[0-9]|tmp/"; echo "(Remote: Ende)"
git -C /d/Entwicklung/HASI/pr139-work/dry2 status --short
git worktree remove /d/Entwicklung/HASI/pr139-work/dry2
git branch -D dry2/backstop-grace tmp/drop-6-10 dry3/backstop-grace tmp/dry3-drop-3b dry4/backstop-grace dry5/backstop-grace dry6/backstop-grace
git worktree prune
git worktree list
git branch --list "dry*" "tmp/*" "worktree-*"
ls .claude/worktrees 2>/dev/null; echo "(.claude/worktrees: Ende)"
```

Erwartet:

- `10 same`, kein Diff, keine Remote-Treffer, `dry2` sauber.
- Danach zeigt `git worktree list` nur den Hauptbaum und bis zu seinem Ende den Archiv-Worktree.
- Keine `dry*`-, `tmp/*`- oder `worktree-*`-Branches, kein `.claude/worktrees`.

Die dry-Branches sind lokal und nie gepusht. Der Inhalt von `dry6` steckt baumgleich in `fix/backstop-grace`; die
Zwischenstände sind in `dry3-logs/` und `dry6-logs/` festgehalten. Das Löschen wird im Chat angekündigt.

- [ ] **Step 10: ToDo, Sitzungsstand, Memory**

- `D:/Entwicklung/HASI/ToDo.md`:
  - den #139-Eintrag unter „Jetzt dran“ auf PR-Nummer, Issue-Nummer, CI-Stand und „Live-Test vor dem Merge
    offen“ setzen;
  - im Block „Befunde aus der Planung von #139“ den Spec-Befund SP-8 ergänzen, falls er fehlt: Die
    Observed-Sperre deckt langsame Ventile nicht (Confirm + Schluss-Latenz über 30 s), unabhängig von der
    Wartezeit.
- `docs/SESSION-STAND.md`: Stand, Nummern, offene Punkte (Task 15).
- Memory `hasi-backstop-has-no-grace.md` und die Indexzeile in `MEMORY.md`: PR/Issue-Nummern, Endzahlen,
  nächster Schritt Live-Test.

---

### Task 15: Live-Test vor dem Merge

Beweisziel (Spec, End-to-End-Kriterium): Auf echten Ventilen schließt der Watcher das normale Laufende ab. Der
Lauf ist `completed`, `actual_s` ist das vom Ventil gemeldete Fenster, und der Abschluss liegt bei
Aus + 5 s — nicht beim Backstop bei `planned + 9 s`.

Reihenfolge:

1. Pre-Release bauen (Teil A).
2. HA-Test mit dem Wartezeit-Emulator (Teil B).
3. HA-Prod mit je einem vom User ausgelösten Lauf (Teil C).
4. Bericht (Teil D).

Freigaben:

- Push von `production`, das Release und jeder Post brauchen je eine Freigabe im Chat.
- HA-Test ist für diesen Test freigegeben (User 19.09.: voller HA-Test-Zugriff für diesen Test, Spec E10). Trotzdem
  wird vor jedem schreibenden Aufruf die Instanz genannt, und das Routing geht strikt über das Präfix
  `mcp__HA-Test__`. Der HA-Test-Neustart in Step 4 fällt unter diese Freigabe und wird vorher im Chat angekündigt
  (Projekt-`CLAUDE.md` und Memory `ha-no-auto-restart`: HA-Neustart nur mit ausdrücklicher Freigabe). Gilt die
  Freigabe in einer neuen Sitzung nicht mehr sicher, vor dem Neustart ausdrücklich fragen.
- Auf HA-Prod brauchen Installation und Neustart je eine eigene ausdrückliche Freigabe (Memory
  `ha-no-auto-restart`).
- Bewässerungs-Hardware auf HA-Prod schaltet nur der User. Der Auto-Modus-Klassifikator blockierte das am 09-11.
- Vor dem Anlegen von Skripten auf HA-Test den Skill `home-assistant-best-practices` des MCP-Servers lesen
  (MCP-Ressource bzw. `ha_get_skill_guide`).

**Zeichen in diesem Task:**

- P = geplantes Fenster = 60 s (`run_zone` Dauer 1, Einheit Minuten).
- t0 = Rückkehr von `irrigation_plus.run_zone` im Testskript, also ungefähr `RUN_STARTED`. `run_zone`
  wartet den Confirm ab.
- on und off = `last_changed` der Confirm-Entität.
- c = t0 − on, der Confirm-Schwanz. Erwartet 0–1 s: 1-s-Poll `VALVE_CONFIRM_POLL`; auf HA-Prod gemessen
  0,46–0,97 s (Spec, Herkunft).
- Wartezeit bei Marge 4: 9 s. Der Backstop wird bei t0 + 69 fällig.

#### Teil A: Fork-Pre-Release bauen

- [ ] **Step 1: Ausgangslage (lesend)**

```bash
cd /d/Entwicklung/HASI/HAsmartirrigation
git status --short --untracked-files=no
git fetch origin upstream
git rev-parse --short upstream/master
git log --oneline -1 origin/production
gh release list --repo Eifel-Joe/HAsmartirrigation --limit 3
gh pr list --repo JustChr/HAsmartirrigation --state open --author Eifel-Joe
git merge-base --is-ancestor upstream/master fix/backstop-grace && echo branch-on-upstream
git diff --stat 0b418644 upstream/master -- README.md custom_components/irrigation_plus/manifest.json docs/installation-rename.md tests/test_migrate_domain.py
git ls-tree upstream/master --name-only custom_components/irrigation_plus/brand tests/test_brand_assets.py
```

Erwartet (Stand 19.09.):

- `upstream/master` = `2b2c403b`; `origin/production` = `d8eeb21b`
  (`build: v2026.09.18b1 — production on upstream v2026.09.16 with Issue 146 on top`).
- Neuestes Release: `v2026.09.18b1` (Pre-release).
- Offen ist nur der PR aus Task 14. Ein weiterer offener PR von uns gehört nach der Production-Regel mit hinein:
  STOPP und den User fragen.
- `branch-on-upstream`.
- Die gebrandeten Dateien README, manifest, Migrationsleitfaden und `test_migrate_domain.py` hat upstream
  zwischen `0b418644` und `2b2c403b` nicht geändert (leere `--stat`, gemessen 19.09.). `brand/` und
  `tests/test_brand_assets.py` gibt es upstream nicht (leeres `ls-tree`, gemessen 19.09.). Ist upstream weiter
  als `2b2c403b`: STOPP, den Neubau der Basis mit dem User klären.

Versionsnummer: `v2026.09.18b2`. Das ist die nächste Beta nach `v2026.09.18b1`, weil `v2026.09.18` noch kein
Fork-Release ist. Ist sie schon vergeben, die nächste freie nehmen.

- [ ] **Step 2: Branch bauen, Branding, Versionen, dist**

`production` = `upstream/master` + dieser PR + Branding (Memory `hasi-production-on-upstream`). Das Branding
stammt aus dem Build-Commit `d8eeb21b`:

- Ganze Dateien nur, wo upstream sie seit `0b418644` nicht geändert hat (Step 1).
- In `const.py`, das #146 geändert hat, per Patch mit Kontext.
- Die Version wird danach umgesetzt.

```bash
cd /d/Entwicklung/HASI/HAsmartirrigation
git checkout -b rebuild/v2026.09.18b2 fix/backstop-grace
git checkout d8eeb21b -- README.md custom_components/irrigation_plus/manifest.json docs/installation-rename.md tests/test_migrate_domain.py tests/test_brand_assets.py custom_components/irrigation_plus/brand
git show d8eeb21b -- custom_components/irrigation_plus/const.py | git apply --3way
sed -i 's/v2026\.09\.18b1/v2026.09.18b2/' custom_components/irrigation_plus/const.py custom_components/irrigation_plus/manifest.json
sed -i 's/"version": "2026\.09\.16"/"version": "2026.09.18b2"/' custom_components/irrigation_plus/frontend/package.json
grep -h '"version"\|^VERSION' custom_components/irrigation_plus/manifest.json custom_components/irrigation_plus/frontend/package.json custom_components/irrigation_plus/const.py
grep -n "Eifel-Joe\|eifel-joe" custom_components/irrigation_plus/const.py custom_components/irrigation_plus/manifest.json
git diff --stat HEAD
```

Erwartet:

- drei Versionen `"version": "v2026.09.18b2"`, `"version": "2026.09.18b2"`, `VERSION = "v2026.09.18b2"`;
- `DOCUMENTATION_URL` und `MIGRATION_GUIDE_URL` auf Eifel-Joe, Codeowner `@Eifel-Joe`, beide Manifest-URLs auf
  Eifel-Joe;
- `git apply` ohne Konflikt. Bei einem Konflikt: STOPP, die drei Zeilen von Hand setzen und dem User zeigen.

Danach im README den Heads-up-Block von #146 auf diesen PR umschreiben (Englisch, Muster wie bei
`v2026.09.18b1`):

> - [#PR-NUMMER](https://github.com/JustChr/HAsmartirrigation/pull/PR-NUMMER) — a confirmed service valve's run end
>   was always settled by the backstop at exactly the planned window, before the valve had reported its own
>   close. The backstop now waits the 5 s debounce plus a per-zone latency margin (default 4 s), so the run is
>   settled on what the valve reported.

Build und Prüfung:

```bash
cd /d/Entwicklung/HASI/HAsmartirrigation/custom_components/irrigation_plus/frontend
mkdir -p D:/Entwicklung/HASI/pr139-work/tmp D:/Entwicklung/HASI/pr139-work/npm-cache && export TEMP=D:/Entwicklung/HASI/pr139-work/tmp TMP=D:/Entwicklung/HASI/pr139-work/tmp TMPDIR=D:/Entwicklung/HASI/pr139-work/tmp npm_config_cache=D:/Entwicklung/HASI/pr139-work/npm-cache
npm ci && npm run build
cd /d/Entwicklung/HASI/HAsmartirrigation
uvx black --check custom_components/irrigation_plus/
uvx ruff check custom_components/irrigation_plus/
./.venv/Scripts/python.exe -m pytest tests/test_brand_assets.py tests/test_migrate_domain.py tests/test_service_watch.py tests/test_finish_grace_helpers.py tests/test_run_in_flight.py tests/test_self_closing.py tests/test_i18n_completeness.py -p _local_socket_unblock -q -p no:cacheprovider | tail -3
grep -c "https://github.com" custom_components/irrigation_plus/translations/en.json
git status --short
git diff --stat -- custom_components/irrigation_plus/frontend/dist
```

Erwartet:

- black/ruff sauber.
- Tests grün bis auf den vorbestehenden einen Error. Die Zahl für diese Auswahl mit den Branding-Tests ist nicht
  gemessen.
- `grep -c` = `0`.
- dist: nur die Versionszeichenkette in den Bundles (Memory, frühere Rebuilds).

Commit, nur die gelisteten Bundles mit `-f`:

```bash
cd /d/Entwicklung/HASI/HAsmartirrigation
git add README.md docs/installation-rename.md tests/test_migrate_domain.py tests/test_brand_assets.py custom_components/irrigation_plus/brand custom_components/irrigation_plus/manifest.json custom_components/irrigation_plus/const.py custom_components/irrigation_plus/frontend/package.json
git add -f $(git diff --name-only -- custom_components/irrigation_plus/frontend/dist)
git status --short
git commit -F - <<'EOF'
build: v2026.09.18b2 — production on upstream with the finish grace on top

Rebuilt on JustChr's master, which now carries the rolling-window rain
guard, so the only open upstream work on top is the finish grace for
confirmed service valves, as it stands under review. A pre-release, for
the live test on the test instance and for one re-measurement per zone on
the production install before the merge.

Fork delta: Eifel-Joe branding (manifest, README, brand assets, the two URLs
in const.py, the migration guide's issue link and the owner-marker test),
versions v2026.09.18b2 in manifest, const and package.json, and the README
heads-up now names the one open pull request.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
git rev-list --count HEAD..upstream/master
git rev-list --count upstream/master..HEAD
git log -1 --format=%B | grep -c '^#'
```

Erwartet: `0` behind, `11` ahead (10 Commits des PR + 1 Build-Commit), `0` Zeilen mit `#` am Anfang.

- [ ] **Step 3: production, Release, ZIP (nach außen: Freigabe)**

Im Chat vorlegen: SHA, `git log --oneline upstream/master..HEAD`, Release-Titel und Release-Text. Nach „ja“:

```bash
cd /d/Entwicklung/HASI/HAsmartirrigation
SHA=$(git rev-parse rebuild/v2026.09.18b2)
git branch production-backup-v2026.09.18b1 d8eeb21b
git branch -f production rebuild/v2026.09.18b2
git push --force-with-lease=production:d8eeb21b origin production
mkdir -p /d/Entwicklung/HASI/pr139-work/release
git archive --format=zip -o /d/Entwicklung/HASI/pr139-work/release/irrigation_plus.zip "$SHA":custom_components/irrigation_plus
./.venv/Scripts/python.exe - <<'EOF'
import zipfile
z = zipfile.ZipFile("D:/Entwicklung/HASI/pr139-work/release/irrigation_plus.zip")
print(z.read("run_watch.py").count(b"def valve_window_seconds"))
print([l for l in z.read("manifest.json").decode().splitlines() if '"version"' in l])
print([l for l in z.read("const.py").decode().splitlines() if l.startswith("VERSION")])
print(z.read("translations/en.json").count(b"https://github.com"))
EOF
gh release create v2026.09.18b2 --repo Eifel-Joe/HAsmartirrigation --prerelease --target "$SHA" \
  --title "v2026.09.18b2 — finish grace for confirmed valves (pre-release, PR #<PR>)" \
  --notes-file /d/Entwicklung/HASI/pr139-work/release/notes-b2.md
gh release upload v2026.09.18b2 /d/Entwicklung/HASI/pr139-work/release/irrigation_plus.zip --repo Eifel-Joe/HAsmartirrigation
gh api repos/Eifel-Joe/HAsmartirrigation/releases/tags/v2026.09.18b2 --jq '.target_commitish, (.assets[].name)'
curl -sIL https://github.com/Eifel-Joe/HAsmartirrigation/releases/download/v2026.09.18b2/irrigation_plus.zip | grep -m1 -E "^HTTP/.* 200"
git fetch origin --tags
git tag -f v2026.09.18b2 "$SHA"
gh run list --repo Eifel-Joe/HAsmartirrigation --branch production --limit 2
```

Die ZIP-Prüfung muss vor dem Upload `1`, `v2026.09.18b2` (zweimal) und `0` zeigen. Danach erwartet: voller SHA
als Ziel, Asset `irrigation_plus.zip`, HTTP 200, CI von `production` grün.

- `--target` braucht den vollen SHA; ein Kurz-SHA gibt HTTP 422 (Memory).
- Das ZIP wird immer aus dem SHA gebaut, nie aus dem Tag-Namen.

Release-Text `release/notes-b2.md` (Englisch, im Chat freigeben lassen):

```markdown
Pre-release for the live test of JustChr/HAsmartirrigation#<PR> (issue #139).

Based on JustChr's master with the finish grace for confirmed service valves on top:

- The backstop of a service run with a confirm entity waits the 5 s debounce plus a per-zone latency margin
  (new zone field, default 4 s, 0-30), so the watcher settles a normal run end on the valve's own reports.
- `actual_s` is the window the valve reported, from its on report to its off report.
- A second dispatch inside that grace is refused; a restart or a manual stop inside it is settled on the same
  reports.

A test build: it runs on the test instance and, for one re-measurement per zone, on the production install
before the pull request is merged.
```

#### Teil B: HA-Test

- [ ] **Step 4: Auf HA-Test installieren und neu starten (HA-Test, freigegeben)**

Lesend:

- `mcp__HA-Test__ha_get_integration(query="irrigation_plus")` für Entry-ID und Zustand.
- Die installierte Version, erwartet `v2026.09.18b1` (ToDo, 19.09.). Quelle: Diagnostics oder
  `mcp__HA-Test__ha_read_file(path="custom_components/irrigation_plus/const.py")` (Zeile `VERSION = …`; die Allowlist
  von `ha_read_file` umfasst nur `custom_components/**/*.py`, `manifest.json` ist nicht lesbar).
- Den System-Log-Stand vorher: `mcp__HA-Test__ha_get_logs(source="system", search="irrigation_plus")`.

Schreibend auf **HA-Test**:

- `mcp__HA-Test__ha_manage_hacs(action="update_information", repository_id="Eifel-Joe/HAsmartirrigation")`
- `mcp__HA-Test__ha_manage_hacs(action="download", repository_id="Eifel-Joe/HAsmartirrigation", version="v2026.09.18b2")`
- Im Chat ankündigen: „Instanz **HA-Test**, Neustart nach dem HACS-Download von `v2026.09.18b2`“ (Freigabe vom 19.09.,
  siehe Freigaben oben); dann `mcp__HA-Test__ha_restart(confirm=True)` (ohne `confirm=True` lehnt das Werkzeug ab).

Danach etwa 1 min abwarten, bis das MCP-Add-on wieder antwortet. Prüfen:

- Integration `loaded`;
- Version `v2026.09.18b2` (Diagnostics oder `VERSION` in `const.py`, wie oben);
- keine neue `irrigation_plus`-Exception im System-Log.

- [ ] **Step 5: Emulator und Umgebung prüfen (lesend)**

`mcp__HA-Test__ha_get_state` für:

- `input_boolean.grace_emu_valve`, `binary_sensor.grace_emu_flowing`, `input_boolean.grace_emu_unavailable`;
- `input_number.grace_emu_off_delay`, `input_boolean.grace_emu_master`;
- `script.grace_emu_run`, `script.grace_emu_stop`.

Mit `mcp__HA-Test__ha_config_get_script` die Skripte `grace_emu_run` (Feld `seconds`, `mode: restart`) und
`grace_emu_stop` lesen.

Erwartet (Stand 19.09.):

- Ventil `off`, `flowing` `off`, `unavailable` `off`, `off_delay` `0.0`, Master `off`.
- Geprüft am 19.09.: `off_delay` 2,5 + `seconds` 3 ergab offen 5,502 s; der `unavailable`-Schalter macht
  `flowing` `unavailable`, danach `off`.

Umgebung, lesend:

- Diagnostics `data.store.config`: den Master-Block notieren (`master_entity`, `master_settle_seconds`,
  `master_kick_enabled`, `master_kick_pause_seconds`, `master_off_after`), für die Rückstellung.
- Diagnostics `data.store.zones`: vorhandene Zonen.
- Zeitpläne (Panel oder WS-Befehl `irrigation_plus/schedules` über `ha_call_service(ws_command=…)`, nur
  lesend): In der Testzeit darf kein geplanter Lauf fällig sein.

Aufruf für die Diagnostics:
`mcp__HA-Test__ha_get_integration(entry_id=<ID>, include_diagnostics=True, diagnostics_data_path="data.store.config")`.

- [ ] **Step 6: Testzone einrichten (HA-Test, schreibend über das Panel)**

Die Zonen- und Konfig-Schreibwege laufen über die HTTP-Views des Panels (`/api/irrigation_plus/zones`,
`/api/irrigation_plus/config`). Einen Dienst dafür gibt es nicht; die WS-Befehle `irrigation_plus/zones` und
`irrigation_plus/config` lesen nur. Also im Panel eintragen:

- vom User, oder
- von Claude im Browser-Pane, wenn dort eine HA-Test-Sitzung bereits angemeldet ist. Claude gibt kein Passwort
  ein.

Neue Zone „Grace Test“, Modus Service:

| Feld | Wert |
|---|---|
| `run_service` | `script.grace_emu_run` |
| `duration_field` | `seconds` |
| Einheit | Sekunden |
| `stop_service` | `script.grace_emu_stop` |
| `confirm_entity` | `binary_sensor.grace_emu_flowing` |
| `latency_margin` | 4 |

Kein Durchflusssensor, kein `observed_entity`.

Sichtprüfung im Panel: Die Zeile „Latency margin (s)“ erscheint unter „Confirm entity“ und verschwindet, wenn
die Confirm-Entität geleert wird. Danach wieder eintragen.

Lesend prüfen:

- die Zone in `data.store.zones` mit `latency_margin: 4`;
- ihren Hauptsensor (Attribut `id`) über `mcp__HA-Test__ha_search`. Das ist das Ziel für `run_zone` und
  `stop_zone` (Dienstschema: `services.yaml`, `run_zone` Feld `duration` in Minuten; Handler
  `services.py:314-340`).
- den Sensor „last water used“ der Zone (Attribute `timestamp`, `duration` = `actual_s`, `result`;
  `sensor.py:1045-1054`).

- [ ] **Step 7: Testskript anlegen (HA-Test, schreibend)**

`mcp__HA-Test__ha_config_set_script(script_id="grace_test_runner", config=…)`. Das YAML unten wird als Dict
übergeben. Vorher den Best-Practices-Skill lesen. Die zwei Platzhalter `ZONE_SENSOR` und `ENTRY_ID` durch die
Werte aus Step 4 und 6 ersetzen.

Das Skript misst alle Zeiten ab t0. Die Verzögerungen werden gegen die Uhr gerechnet, damit Blockzeiten (der
Reload in S6) nicht aufaddieren. Jede Aktion schreibt einen Logbuch-Eintrag mit Zeitstempel. So geht keine
MCP-Latenz in die Messung ein.

```yaml
alias: "grace test runner (#139)"
mode: single
fields:
  scenario:
    description: "S1 .. S9"
    required: true
    selector:
      select:
        options: ["S1", "S2", "S3", "S4", "S5", "S6", "S7", "S8", "S9"]
variables:
  zone: "ZONE_SENSOR"
  entry: "ENTRY_ID"
  off_delay: "{{ {'S1': 0, 'S2': 2.5, 'S3': 6, 'S4': 20, 'S5': -10, 'S6': 20, 'S7': 0, 'S8': -2, 'S9': -6}[scenario] }}"
  settle_by: "{{ 105 if scenario == 'S6' else 80 }}"
sequence:
  - action: input_boolean.turn_off
    target: { entity_id: input_boolean.grace_emu_unavailable }
  - action: input_number.set_value
    target: { entity_id: input_number.grace_emu_off_delay }
    data: { value: "{{ off_delay }}" }
  - wait_template: "{{ is_state('input_boolean.grace_emu_valve', 'off') }}"
    timeout: "00:00:05"
    continue_on_timeout: false
  - action: logbook.log
    data: { name: "grace test", message: "{{ scenario }} dispatch (off_delay {{ off_delay }})" }
  - action: irrigation_plus.run_zone
    target: { entity_id: "{{ zone }}" }
    data: { duration: 1 }
  - variables:
      t0: "{{ now().timestamp() }}"
  - action: logbook.log
    data: { name: "grace test", message: "{{ scenario }} t0 (run_zone returned)" }
  - choose:
      - conditions: "{{ scenario == 'S4' }}"
        sequence:
          - delay: "{{ [0, t0 + 63 - now().timestamp()] | max }}"
          - action: logbook.log
            data: { name: "grace test", message: "S4 stop_zone at t0+63" }
          - action: irrigation_plus.stop_zone
            target: { entity_id: "{{ zone }}" }
      - conditions: "{{ scenario == 'S5' }}"
        sequence:
          - delay: "{{ [0, t0 + 47 - now().timestamp()] | max }}"
          - action: input_boolean.turn_on
            target: { entity_id: input_boolean.grace_emu_unavailable }
          - action: logbook.log
            data: { name: "grace test", message: "S5 unavailable on at t0+47" }
          - delay: "{{ [0, t0 + 52 - now().timestamp()] | max }}"
          - action: input_boolean.turn_off
            target: { entity_id: input_boolean.grace_emu_unavailable }
          - action: logbook.log
            data: { name: "grace test", message: "S5 unavailable off at t0+52" }
      - conditions: "{{ scenario == 'S6' }}"
        sequence:
          - delay: "{{ [0, t0 + 63 - now().timestamp()] | max }}"
          - action: logbook.log
            data: { name: "grace test", message: "S6 reload at t0+63" }
          - action: homeassistant.reload_config_entry
            data: { entry_id: "{{ entry }}" }
          - action: logbook.log
            data: { name: "grace test", message: "S6 reload returned" }
      - conditions: "{{ scenario == 'S7' }}"
        sequence:
          - delay: "{{ [0, t0 + 63 - now().timestamp()] | max }}"
          - action: logbook.log
            data: { name: "grace test", message: "S7 second run_zone at t0+63" }
          - action: irrigation_plus.run_zone
            target: { entity_id: "{{ zone }}" }
            data: { duration: 1 }
          - action: logbook.log
            data: { name: "grace test", message: "S7 second run_zone returned" }
  - delay: "{{ [0, t0 + settle_by - now().timestamp()] | max }}"
  - action: input_number.set_value
    target: { entity_id: input_number.grace_emu_off_delay }
    data: { value: 0 }
  - action: logbook.log
    data: { name: "grace test", message: "{{ scenario }} done" }
```

Dazu eine Hilfs-Automation, die jedes `irrigation_finished` ins Logbuch schreibt, damit Step 9 es je Szenario zählen
kann (das Ereignis heißt `irrigation_plus_irrigation_finished`, Nutzlast `{"zones": [{"zone_id", "zone", "bucket"}],
"problems": []}`, `self_closing.py:414-425` auf dry6): `mcp__HA-Test__ha_config_set_automation` mit

```yaml
alias: "grace test: irrigation_finished (#139)"
mode: queued
triggers:
  - trigger: event
    event_type: irrigation_plus_irrigation_finished
actions:
  - action: logbook.log
    data:
      name: "grace test"
      message: "irrigation_finished {{ trigger.event.data.zones | map(attribute='zone_id') | join(',') }}"
```

Beide über `ha_config_get_script` bzw. `ha_config_get_automation` zurücklesen. Einen Lauf startet
`mcp__HA-Test__ha_call_service(domain="script", service="grace_test_runner", data={"scenario": "S1"})`, danach
etwa 80 s warten (S6: 105 s). Die Szenarien laufen einzeln, und nach jedem folgt die Kurzprüfung aus Step 9.

Optional für S7: `logger.set_level` mit `custom_components.irrigation_plus.irrigation: info`, damit die Absage
im Log erscheint („run_zone: zone N already has a run in flight, ignoring“, `irrigation.py:3311`). Danach
zurückstellen.

- [ ] **Step 8: Szenarien S1–S9 (HA-Test)**

Die neun Szenarien sind die der Spec (End-to-End §1, Spalte „Spec“). Die Erwartungen folgen aus dem Code auf dry6
(Produktivcode = dry5); auf HA-Test ist keine davon gemessen. Die Spalte `irrigation_finished` zählt die Logbuch-Einträge
der Hilfs-Automation aus Step 7 je Szenario.

- Ventil offen = `seconds` + `off_delay`, also 60 + `off_delay` (Skript-Überhang am 19.09.: 2 ms auf 5,5 s).
- `actual_s` wird gerundet gespeichert (`irrigation.py:2874`).
- Der Abschluss steht als `ts` im Verlaufseintrag (`dt_util.now()`, `irrigation.py:2871`).

| # | Spec | Einstellung | Ablauf im Skript | Ventil zu (Aus-Meldung) | Abschluss (`ts`) | Datensatz (`result`, `planned_s`, `actual_s`) | `irrigation_finished` | Was es belegt |
|---|---|---|---|---|---|---|---|---|
| S1 | 1 | `off_delay` 0, Marge 4 | — | on + 60,0, also c vor dem alten Backstop bei t0 + 60 (wie Kirschlorbeer) | off + 5,0 s ±0,5, deutlich vor t0 + 69 | `completed`, 60, 60 (Fenster 60,0 ±1) | 1 | Normalende über den Watcher, nicht über den Backstop |
| S2 | 2 | `off_delay` +2,5 | — | on + 62,5 (Tuya-artig, innerhalb der Marge) | off + 5,0 ±0,5 (≈ t0 + 67,5 − c), vor t0 + 69 | `completed`, 60, 62 oder 63 (Fenster ≈ 62,5, gerundet) | 1 | späte Meldung in der Marge; `actual_s` über `planned_s` |
| S8 | 3 | `off_delay` −2 | — | on + 58 (früher Schluss in der Marge) | off + 5,0 ±0,5 (≈ t0 + 63 − c) | `completed`, 60, 58 (Fenster 58; 58 + max(1, 4) ≥ 60) | 1 | früher Schluss innerhalb der Toleranz max(1 s, Marge): `completed` auf dem gemeldeten Fenster |
| S9 | 4 | `off_delay` −6 | — | on + 54 (früher Schluss jenseits der Marge) | off + 5,0 ±0,5 (≈ t0 + 59 − c) | `partial`, 60, 54 (Fenster 54; 54 + 4 < 60) | 0 | Teil-Lauf bei gemeldetem normalem Ende erreichbar („partials becoming reachable on normal ends“), gutgeschrieben für das Fenster, ohne die 5 s Entprellung |
| S3 | 5 | `off_delay` +6 | — | on + 66 (jenseits der Marge) | t0 + 69 ±0,5 (Backstop), also off + 3 + c, vor off + 5 | `completed`, 60, 60 (`planned_s`) | 1 | bekannt und bewusst unverändert (T6 gestrichen); die Aus-Meldung steht nur im Recorder |
| S5 | 6 | `off_delay` −10 | `grace_emu_unavailable` an bei t0 + 47, aus bei t0 + 52 | on + 50, verdeckt; `flowing`: on --> `unavailable` (t0 + 47) --> `off` (t0 + 52) | t0 + 57 ±0,5 (Rückkehr + 5) | `partial`, 60, 57 (±1; `elapsed` ab `RUN_STARTED` bei der Entscheidung, mit Entprellung wie heute) | 0 | kein `RUN_VALVE_OFF` aus `unavailable` --> `off` (E6); Basisregel (b). Unter der verworfenen E4-Regel wäre es `completed` (57 + 4 ≥ 60) |
| S4 | 7 | `off_delay` +20 | `irrigation_plus.stop_zone` bei t0 + 63 | bei der Stoppzeit durch `script.grace_emu_stop`, nicht bei on + 80 | Stoppzeit ±0,5 | `completed`, 60, 60 (Ventil meldete noch „an“: Fenster = geplant) | **1** | Stopp in der Wartezeit nach der Watcher-Regel (d); Ventil zuerst zu; kein `partial` ohne Event (Entscheidung (d)) |
| S7 | 8 | `off_delay` 0 | zweiter `irrigation_plus.run_zone` bei t0 + 63 | on + 60 | off + 5 ±0,5 | `completed`, 60, 60; genau **ein** neuer Eintrag | 1 | Dispatch in der Wartezeit abgelehnt (T9) |
| S6 | 9 | `off_delay` +20, Marge **30** (Wartezeit 35), Master `input_boolean.grace_emu_master` | Config-Entry-Reload bei t0 + 63 (in der Wartezeit, also (f)) | on + 80 | off + 5 ±0,5 (≈ t0 + 85 − c), vor t0 + 95 | `completed`, 60, 80 (Fenster 80, Toleranz 30) | 1 | Neustart in der Wartezeit: Backstop neu gestellt, Watcher neu aufgenommen, **Master nicht erneut angefordert**; genau ein Eintrag |

Zu S6:

- **Vorbereitung im Panel:** Marge der Testzone auf 30. Master: `master_entity` =
  `input_boolean.grace_emu_master`, `master_kick_enabled` an, `master_kick_pause_seconds` 1,
  `master_settle_seconds` 2, `master_off_after` an.
- **Warum der Kick sichtbar macht, ob angefordert wird:** Ein neuer Koordinator beginnt mit `_master_on` =
  False. Eine Anforderung schaltete den laufenden Master erst aus, dann wieder an (`master.py:80-89`). Das wäre
  ein sichtbarer Aus-Ein-Puls im Recorder.
- **Bestanden, wenn** `grace_emu_master` genau so aussieht:
  - einmal off --> on beim Dispatch (vor dem Öffnen: Kick 1 s + Settle 2 s);
  - kein Wechsel zwischen „S6 reload at t0+63“ und dem Abschluss;
  - on --> off etwa 5 s nach dem Abschluss (`MASTER_RELEASE_GRACE_SECONDS`, `master_off_after`).
- **Der alte Backstop:** Beim Reload bricht `async_unload` den Backstop-Timer des alten Koordinators nicht ab
  (vorbestehender Befund). Er wird wie der neue bei t0 + 95 fällig, findet keinen Datensatz mehr und schreibt
  nichts (`_sc_finish_run` kehrt ohne Datensatz zurück). Daher das Kriterium „genau ein Eintrag“.
- **Dauert der Reload über den Schluss hinaus** (Logbuch „reload returned“ nach der Aus-Meldung): Dann findet
  der neue Watcher das Ventil „aus“, ohne dass etwas gespeichert ist. Es gilt die Basisregel: `completed`, 60,
  60 bei Rückkehr + 5. Das Master-Kriterium gilt trotzdem. Die Reload-Dauer ist nicht gemessen.

In allen Szenarien: keine neue `irrigation_plus`-Exception im System-Log.

Ohne den Fix (Basis `2b2c403b`) sähe es so aus:

- S1: gleicher Datensatz, aber Abschluss bei t0 + 60 durch den Backstop, c Sekunden nach der Aus-Meldung, in
  die Entprellung.
- S2: Abschluss bei t0 + 60 vor der Aus-Meldung, `actual_s` 60.
- S4: Der Lauf wäre bei t0 + 60 schon abgeschlossen; der Stopp liefe ins Leere.
- S6: sofortiger Abschluss beim Reload mit 60.
- S7: Der Datensatz ist bei t0 + 60 schon weg, der zweite Lauf würde gestartet. Die Absage belegt T9.
- S8: Abschluss durch den Backstop bei t0 + 60, in die Entprellung, `completed` 60 statt 58.
- S9: Entscheidung der Entprellung bei ≈ t0 + 59, Teil-Lauf mit `actual_s` ≈ 59 − c (die 5 s Entprellung mitgebucht)
  statt 54.

- [ ] **Step 9: Auswerten (nur lesend, je Szenario)**

1. Logbuch: `mcp__HA-Test__ha_get_logs(source="logbook", search="grace test", hours_back=1)` für t0, die
   Aktionszeiten und die Einträge `irrigation_finished <zone_id>` der Hilfs-Automation zwischen Dispatch und „done“.
2. Recorder:
   `mcp__HA-Test__ha_get_history(entity_ids=["binary_sensor.grace_emu_flowing","input_boolean.grace_emu_valve","input_boolean.grace_emu_unavailable","input_boolean.grace_emu_master","script.grace_emu_run"], start_time=<dispatch − 1 min>, end_time=<done + 1 min>, significant_changes_only=false, order="asc")`
   für on, off und die Wechsel mit Millisekunden. Fenster = off − on.
3. Verlaufseintrag: `mcp__HA-Test__ha_get_integration(entry_id=<ID>, include_diagnostics=True, diagnostics_data_path="data.store.zones")`,
   die Testzone, letzter `run_log`-Eintrag (`ts`, `trigger`, `planned_s`, `actual_s`, `result`, `detail`).
   Gegenprobe: Historie des Sensors „last water used“ mit `minimal_response=false` (Attribute `timestamp`,
   `duration`, `result`).
4. System-Log: `mcp__HA-Test__ha_get_logs(source="system", search="irrigation_plus")` gegen den Stand von Step 4.
5. Optional, wo das Zeitfenster reicht: `data.store.config.active_valve_runs` lesen, während der Lauf in der
   Wartezeit ist. Bei S6 nach „reload returned“: `latency_margin: 30`, `valve_on`, noch kein `valve_off`.

Bestanden, wenn für jedes Szenario die Zeile aus Step 8 stimmt: `result`, `actual_s` ±1 s zum
Recorder-Fenster (S3, S4, S5: die dort genannte Regel), `ts` relativ zu off bzw. t0 ±0,5 s und die Zahl der
`irrigation_finished`-Einträge (S1, S2, S3, S4, S6, S7, S8 je genau 1; S5, S9 je 0). Dazu genau ein neuer
Verlaufseintrag je Szenario. Ergebnis mit den gemessenen Zahlen je Szenario nach
`D:/Entwicklung/HASI/pr139-work/live/ha-test-grace.md`.

- [ ] **Step 10: HA-Test zurückstellen (HA-Test, schreibend)**

- Master-Block im Panel auf die Werte aus Step 5 zurücksetzen (Master ohne Entität).
- Testzone „Grace Test“ löschen; ersatzweise auf `disabled` setzen.
- `input_number.grace_emu_off_delay` auf 0, `input_boolean.grace_emu_unavailable` aus,
  `input_boolean.grace_emu_master` aus.
- Logger-Level zurücksetzen, falls in Step 7 geändert.
- Die Hilfs-Automation „grace test: irrigation_finished (#139)“ bleibt wie das Testskript bis zum Merge stehen
  (Wiederholung nach Review-Änderungen) und wird mit ihm entfernt; in `ToDo.md` vermerken.
- `script.grace_test_runner` bleibt bis zum Merge stehen (Wiederholung nach Review-Änderungen). Das wird in
  `ToDo.md` vermerkt; nach dem Merge wird es entfernt.
- HA-Test bleibt auf `v2026.09.18b2`.

Lesend gegenprüfen: Diagnostics `data.store.config` gleich dem Stand aus Step 5; keine Testzone mehr.

#### Teil C: HA-Prod

- [ ] **Step 11: Prod-Stand lesen (nur lesend)**

- `mcp__HA-Prod__ha_get_integration(query="irrigation_plus")` für Entry-ID und Version (erwartet `v2026.09.17`,
  Memory `hasi-production-on-upstream`).
- Diagnostics `data.store.zones` für Beet und Kirschlorbeer: `watering_mode`, `run_service`, `duration_field`,
  `duration_unit`, `stop_service`, **`confirm_entity`**, `flow_sensor`, `observed_entity`. Noch kein
  `latency_margin`.
- `data.store.config` für den Master-Block.
- Nächste geplante Läufe, damit der Testlauf nicht mit einem Zeitplan kollidiert.
- Die Confirm-Entitäten und die Sensoren „last water used“ der beiden Zonen über `ha_search` auflösen und
  notieren.
- Nichts annehmen, was hier nicht gelesen wurde (Memory `verify-ha-system`).

- [ ] **Step 12: Installation und Neustart auf HA-Prod (je eigene Freigabe)**

Im Chat nennen: Instanz **HA-Prod**, Version `v2026.09.18b2`, Rückweg `v2026.09.17`.

Nach dem ersten „ja“:

- `mcp__HA-Prod__ha_manage_hacs(action="update_information", repository_id="Eifel-Joe/HAsmartirrigation")`
- `mcp__HA-Prod__ha_manage_hacs(action="download", repository_id="Eifel-Joe/HAsmartirrigation", version="v2026.09.18b2")`

Nach einem eigenen „ja“ für den Neustart: `mcp__HA-Prod__ha_restart(confirm=True)`.

Danach prüfen:

- Integration geladen, Version `v2026.09.18b2`;
- keine neue `irrigation_plus`-Exception;
- beide Zonen laden `latency_margin` 4, sichtbar im Panel und in den Diagnostics. Gespeicherte Zonen ohne das
  Feld bekommen beim Laden den Default (T1).

- [ ] **Step 13: Je Zone ein kurzer Lauf — ausgelöst vom User**

Claude schaltet keine Bewässerungs-Hardware. Vorschlag für den User: Entwicklerwerkzeuge --> Aktionen. Die
Läufe nacheinander, nicht gleichzeitig, mindestens 2 min Abstand; so lässt sich jeder Abschluss eindeutig
zuordnen.

```yaml
action: irrigation_plus.run_zone
target:
  entity_id: <Zonensensor Beet aus Step 11>
data:
  duration: 1
```

Danach dasselbe mit dem Zonensensor von Kirschlorbeer.

- Beet ist ein Tuya-Minutenventil: 1 Minute = Fenster 60 s.
- Kirschlorbeer ist ein SONOFF-Sekundenventil: 60 s.
- `run_zone` umgeht Skip-Bedingungen, Defizit-Tor und Regenverzögerung (`irrigation.py:3287-3295`).
- Die Gutschrift ist klein und echt.

- [ ] **Step 14: Auswerten (nur lesend)**

Wie Step 9, mit den Confirm-Entitäten aus Step 11 und `mcp__HA-Prod__…`. Bestanden je Zone, wenn:

1. `result` = `completed`;
2. `actual_s` = Fenster aus dem Recorder ±1 s. Erwartung aus den Messungen (Spec, Herkunft):
   - Beet 62–63 s, über `planned_s` 60 (Schluss 2,08–2,90 s nach dem Fenster);
   - Kirschlorbeer 59–61 s (±0,7 s um das Ende).
3. `ts` = off + 5 s ±0,5 s, also nicht `RUN_STARTED + 69`. Der Backstop läge bei etwa on + c + 69, bei Beet
   (c ≈ 0,86–0,91 s) etwa 2 s nach dem erwarteten Abschluss.
4. keine neue Exception.

Schließt ein Lauf bei `planned + 9 s` ab, obwohl der Recorder eine Aus-Meldung zeigt, die Ursache klären:

- lag die Latenz über der Marge (off später als on + 64)?
- oder hielten reine Attribut-Updates in den letzten 5 s vor dem Backstop die Entprellung am Leben (SP-10)?
  Dazu die Historie mit `minimal_response=false` und `significant_changes_only=false` lesen.

Beides ist bekannt und bewusst unverändert. Es wird mit Zahlen berichtet, nicht nachgebessert.

Kirschbaum ist ausgenommen: Wegen des Schlauchdefekts ist dort nur das Ventil-Timing verwertbar (Memory
`hasi-kirschbaum-hose-defect`). Natürliche Läufe danach (Beet, Kirschlorbeer, Kirschbaum nur Timing) werden
mit denselben Kriterien als zusätzlicher Beleg ausgewertet. Keine Läufe erzwingen. Ergebnis nach
`D:/Entwicklung/HASI/pr139-work/live/ha-prod-grace.md`.

HA-Prod bleibt auf `v2026.09.18b2` bis zum Merge und dem nächsten regulären Fork-Release. Der Rückweg auf
`v2026.09.17` (HACS-Download + Neustart) braucht je eine Freigabe.

#### Teil D: Bericht

- [ ] **Step 15: Ergebnis auf dem PR (und ein Hinweis auf #139), nur nach Freigabe**

Entwurf auf Englisch, mit Zahlen aus `live/ha-test-grace.md` und `live/ha-prod-grace.md`:

- je Szenario und Zone: Fenster aus dem Recorder, `actual_s`, `result`, Abschluss − off;
- für S6 der Master-Verlauf;
- für S7 die Absage;
- dazu, was bewusst unverändert blieb (S3).

Ohne IP-Adressen, ohne Branch-SHAs, ohne Entitätsnamen der Anlage (die Zonennamen Beet und Kirschlorbeer
stehen schon auf #139).

Im Chat vorlegen, nach „ja“: `gh pr comment <PR> --repo JustChr/HAsmartirrigation --body-file …`, dazu auf #139
ein Satz mit Link. Danach im Archiv-Worktree den Live-Test in den Umsetzungsnachtrag der Spec schreiben
(Task 14, Step 8: eigener Commit, Push nach Freigabe). Außerdem `ToDo.md`, `SESSION-STAND.md`, Memory
`hasi-backstop-has-no-grace` und `hasi-production-on-upstream` (neuer Pre-Release-Absatz) fortschreiben.

Der Merge ist JustChrs Entscheidung.
