# HASI — Session-Stand

## 2026-09-21 (4) — Eifel-Joe#22 Wetterpuffer-Zeitzone: Spec + Plan, Doku-PR raus

### Stand (verifiziert)
- **Spec + Plan geschrieben und archiviert.** `docs/superpowers/specs/2026-09-21-weather-buffer-aware-time-design.md`
  und `docs/superpowers/plans/2026-09-21-weather-buffer-aware-time.md`, beide auf
  `archive/design-history` = **`b085791f`** (per `git ls-remote` bestaetigt). Regel P1 erfuellt.
  Im Hauptbaum liegen sie untracked — sie gehoeren nicht in den Upstream-PR.
- **`JustChr#164`** (Doku `TZ=`) eroeffnet aus `docs/container-timezone` auf `upstream/master`
  = `965a4f9d`. **Rein additiv, 2 Dateien, +34/-0**, CRLF erhalten (`file` geprueft).
  `lint` und `validate` gruen; `test (3.13)` + `test-ha-floor` liefen bei Sitzungsende noch.
- **`Eifel-Joe#22` kommentiert:** [issuecomment-5765927213](https://github.com/Eifel-Joe/HAsmartirrigation/issues/22#issuecomment-5765927213).
  Label `upstream:freigegeben` bleibt richtig (spaeterer Stand als `upstream:gemeldet`).
- **Branch `fix/weather-buffer-aware-time`** von `upstream/master` = `965a4f9d` steht bereit,
  **noch kein Code** — die Umsetzung faengt frisch mit dem Plan an.
- **Der Bug ist numerisch belegt**, nicht nur gelesen: Prozess-TZ UTC + HA Europe/Berlin laesst
  eine echte Stunde als drei messen (Fehler == UTC-Offset, konstant). Rechnung steht im Spec.

### Entscheidungen dieser Sitzung
- **A+B ein PR** (Schreiber+Migration+Leser), **C** (Laufzeit-Check Prozess- vs. HA-Offset) und
  **D** (Doku) getrennt; D zuerst, weil JustChr ausdruecklich darum bat.
- **Ein gemeinsamer Coerce-Helfer** `helpers.as_stored_aware` statt vier verstreuter naiv-Annahmen.
- **Prozess-Zone injizierbar** (`helpers._process_timezone`), weil `time.tzset()` unter Windows
  fehlt und ein nur-in-CI-Test nie selbst rot-gruen gesehen wird.
- **Keine Detektion** des geaenderten Prozess-TZ — Begruendung im Spec unter D4.
  **Die Antwort an JustChr geht bewusst erst mit dem Code-PR** auf `JustChr#160` raus, nicht vorab.

### Verworfen
- **Zukunfts-Clamp auf migrierte Stempel:** richtungsblind. JustChrs eigenes Szenario (UTC -->
  echte Zone) erhoeht den Offset, die Stempel landen in der *Vergangenheit*, Trefferquote 0 %.
  Zusaetzlich falsch-positiv auf Boards ohne gepufferte RTC (Migration laeuft vor NTP-Konvergenz).
- **Paarung naiver gegen aware Stempel** zur Offset-Rekonstruktion: Rauschen = Signal, und eine
  frisch eingerichtete Installation hat gar keine aware Stempel.
- **Jede datenbasierte Heuristik:** der DST-Ruecksprung im Herbst ist byte-identisch zu einem
  Container-TZ-Fix.

### Fallen
- **Der Spec war an einer Stelle falsch und ist korrigiert.** Ich hatte angenommen, die
  Solargeometrie repariere sich durch das Aware-Machen von selbst. Falsch: `et_estimate.py:140`
  und `weather_aggregate.py:725` lesen den Offset aus dem **Schluessel** `row["tz_offset_h"]`,
  gefuellt nur an `weather_aggregate.py:970` mit `tz.utcoffset(hour_start)`. Ohne Aenderung genau
  dieser Zeile bliebe die teuerste Haelfte des Bugs offen — **und die Suite haette es nicht
  gemerkt**. Jetzt Task 6 mit `hour_start.utcoffset()`.
- **Heredoc mit `<<'EOF'` scheitert unter MSYS an Anfuehrungszeichen im Text** (`unexpected EOF`).
  Fuer laengere Markdown-Dateien das Write-Tool nehmen, nicht `cat >`.
- **Zeilenenden:** `docs/*.md` ist CRLF. Einfuegen per Python mit `\r\n`-Join, sonst reisst der
  Diff die ganze Datei auf.
- **Worktree-Kollision:** `archive/design-history` haengt bereits in
  `D:/Entwicklung/HASI/pr139-work/archive-wt`. Kein zweiter Worktree moeglich — den vorhandenen
  per `fetch` + `reset --hard FETCH_HEAD` aktualisieren und nutzen.
- **Die Verifikationsstufe des Analyse-Workflows hat mehrere „garantierter Crash"-Befunde der
  ersten Stufe widerlegt** (beide Seiten sind heute naiv, es kracht nichts). Erste-Stufe-Befunde
  eines Fan-outs nicht ungeprueft in einen Spec uebernehmen.

### Naechste Schritte
1. **`/clear`, dann Umsetzung** streng nach `docs/superpowers/plans/2026-09-21-weather-buffer-aware-time.md`
   auf Branch `fix/weather-buffer-aware-time`. Tasks 1–8, TDD, ein Commit pro gruenem Task.
   Task 3 ist absichtlich gross (ein Vergleichsraum, sonst `TypeError` zwischen den Commits).
2. **`JustChr#164` beobachten** — bei Reviewwunsch nachziehen; die Zeile in
   `installation-download.md` ist im PR-Body ausdruecklich zum Streichen angeboten.
3. **Nach A+B:** Detektionsantwort auf `JustChr#160` (Text-Rohfassung:
   `D:/Entwicklung/HASI/issue22-work/comment-issue22.md`, Detektionsteil wurde herausgenommen —
   die lange Fassung steht im Spec unter D4 und in der Workflow-Auswertung).
4. **Danach (C):** eigener PR, Laufzeit-Check `datetime.now().astimezone().utcoffset()` gegen
   `dt_util.now().utcoffset()`.
5. **Offen aus frueheren Sitzungen:** `JustChr#162` + `JustChr#163` warten auf Review.

### Revision — Umsetzungsversuch gelaufen, auf JustChr wartend

- **Task 1 committet und gruen** (`c17a8111`): `helpers.as_stored_aware` + `_process_timezone`,
  5 Tests. **Pin aus Task 2 gruen** (`TypeError` --> `1/24`).
- **Task 3 NICHT fertig**, liegt als ausdruecklich markierter WIP (`c9720a72`). Tasks 4-8 offen.
- **Der Plan war unvollstaendig: es gibt ZWEI naive Herkuenfte**, mit entgegengesetzter
  richtiger Deutung. Store-Stempel = prozess-lokal; Wetter-Client-/Forecast-Zeilen
  (`_rows_since` :880, `_projected_extremes` :599) = HA-lokal. Details in Spec Revision 2.
- **Warum es lange nach Testalterung aussah:** `_intraday_for_zone` verschluckt jede Exception
  (`live_estimate.py:1213-1218`, DEBUG + `REASON_FAILED`). **222 verschluckte `TypeError` in
  einer Testdatei**, gemeldet als `Obtained: None`. Diagnose nur mit `exc_info=True`.
- **Umfangszahl war zur Haelfte mein Rechner:** 193 neue Fehlschlaege mit Prozess auf MESZ,
  **98** mit auf UTC gezwungener Prozesszone. Baseline `upstream/master`: 7 failed / 3191 passed
  / 320 errors (Windows, vorbestehend). 72 der 98 in drei `live_estimate`-Dateien.
- **Befund an JustChr gemeldet**, mit Schnitt-Frage:
  [issuecomment-5766722593](https://github.com/JustChr/HAsmartirrigation/issues/160#issuecomment-5766722593).
  Empfehlung: erst ein verhaltensneutraler PR, der die Eingaenge total macht, dann der Flip.
  **Antwort steht aus — vor ihr wird nicht weitergebaut.**
- **`JustChr#164` (Doku) ist CI-gruen**, alle vier Checks.
- Spec Revision 2 archiviert: `archive/design-history` = `e44792f7`.
- Baseline-Worktree wieder entfernt.

### Empfohlene Skills
- `superpowers:executing-plans` bzw. `superpowers:subagent-driven-development`,
  `superpowers:test-driven-development`, `superpowers:verification-before-completion`
- Fuer den PR: `pr-workflow`, Memory `hasi-pr-build-recipe`; Kommentierung: Regel P2
- Test-Env: Memory `hasi-local-test-env-rebuild`

---


## 2026-09-21 (3) — zwei Upstream-PRs offen, Querverweis-Panne bereinigt

### Stand (verifiziert)
- **`JustChr#162`** (PR A, Observed-Doppelgutschrift) eroeffnet, CI 4/4 gruen, noch kein Review.
  Unser Issue dazu: `Eifel-Joe#1`.
- **`JustChr#163`** (Observed-Sperre nach Neustart) eroeffnet aus `fix/observed-lock-after-restart`,
  vier Commits auf `upstream/master` = `965a4f9d`, **PR-Diff 6 Dateien, +232/-1**, kein `docs/`,
  kein Frontend. Unser Issue dazu: `Eifel-Joe#23`, bleibt offen bis der PR schliesst.
  Belege: Suite 3191 --> **3196 passed** bei `diff`-identischen 327 FAILED-/ERROR-Namen;
  `black --check` 68 unveraendert, `ruff` gruen; **Mutationsproben 5 / 5 gefangen / 0 ueberlebt**.
  Spec, Plan und Nachtrag: `archive/design-history` @ `05c43936` (gepusht).
- **Nachmessung zu `Eifel-Joe#23` gefahren** und dabei das eigene Messinstrument widerlegt: das Skript
  aus dem Issue baut den Zustand von Hand und ruft den Resume-Pfad nie, meldet also auch gegen den
  gefixten Stand "weiter offen". Ersetzt durch den Ende-zu-Ende-Test
  `test_after_a_resume_the_observer_stays_silent_in_the_old_gap`. Spec Abschnitt 7 korrigiert.
- **Querverweise aus altmenorgs `altmen#161` entfernt** (User-Auftrag). Ein Verweis laesst sich nur
  durch Loeschen der Quelle tilgen — Editieren des Bodies reicht nicht, auf 5-->4 am eigenen Repo
  nachgewiesen. `Eifel-Joe#12` geloescht, das Tracking-Issue neu als **`Eifel-Joe#42`** angelegt,
  12 Dateiverweise + 1 Issue-Body nachgezogen. Ergebnis: **0 Verweise von uns** auf `altmen#161`.
  Die drei Verweise auf `JustChr#159/#160/#162` bleiben stehen (User-Entscheidung).

### Verworfen
- **Die Schliessen-Flanke als Ort des PR-A-Fixes.** Das Praedikat ist in **beide** Richtungen falsch,
  je nachdem ob das Ventil vor oder nach `dispatch + run_seconds + 30` schliesst.
- **`_watch_start` als einziger Fixpunkt fuer `Eifel-Joe#23`.** Die Signatur kennt `elapsed` nicht, und
  sie laeuft auch auf dem Normalpfad, wo der Marker bereits korrekt steht.
- **`max(0.0, planned - elapsed)`.** Ueberdehnt das Fenster um bis zu 35 s; Mutationsprobe M3 faengt es.

### Fallen
- **`git stash -- <datei>` bewirkt nichts, wenn der Fix committet ist.** Der erste RED-Versuch fuer den
  Ende-zu-Ende-Test lief deshalb gruen und waere beinahe als Beleg durchgegangen.
- **`npm_config_cache` mit Windows-Pfad wird unter MSYS als relativ gelesen** — 33 MB landeten in
  `frontend/EntwicklungHASIprA-npm-cache/`. Untracked, nie committet, entfernt.
- **`gh release create --target` nimmt keinen Kurz-SHA**, nur die vollen 40 Zeichen.
- **Zahlen aus dem eigenen Nachtrag gegenlesen:** dort stand `+179/-1`, gemessen sind `+232/-1`.
- **Das Label zum Upstream-PR vergessen.** `upstream:gemeldet` fehlte auf `Eifel-Joe#23`, der User
  fand es. Nachgesetzt; Pflicht jetzt in Regel P2 und im Memory `hasi-todo-file`. Vollpruefung
  ueber alle 41 Issues: sonst nichts offen. Ohne `groesse:` sind `Eifel-Joe#24`-`#31` — die
  Quellzeilen `➂`-`➈` hatten nie eine, **bewusst so gelassen** (User 21.09.). Ohne `schwere:`
  sind die Feature-Issues `#34`-`#40`, folgerichtig. Bei JustChr haben wir kein Label-Recht.

### Naechste Schritte
- Reviews abwarten: `JustChr#162` und `JustChr#163`.
- `Eifel-Joe#21` (`JustChr#159`, Prognose-Gewichtung) und `Eifel-Joe#22` (`JustChr#160`, Zeitzonen-Naht)
  — beide "yours to build"; bei `#160` wartet JustChr auf **unser Urteil** zur TZ-Wechsel-Annahme.
- Aufraeumen: lokale Branches `dry2`–`dry7`, `tmp/*`, `rebuild/v2026.09.18b2`, `backup/*`,
  11 gemergte `fix/*`, Worktree `pr139-work/dry2`.
- HA-Test laeuft auf Pre-Release **v2026.09.21b1**; `observed_watering_enabled` bewusst **an**,
  Zaehler Zone 1 bei 55,28 L (Reset abgelehnt, weil der Knopf auch den Verlauf loescht).

### Empfohlene Skills
- `superpowers:receiving-code-review` sobald JustChr antwortet.
- `task-loop` fuer `Eifel-Joe#21` / `Eifel-Joe#22`.


## 2026-09-21 (2) — PR A gebaut, Fehler auf HA-Test feldbelegt, nichts gepusht

### Stand (verifiziert)
- **PR A ist fertig gebaut**, Branch `fix/observed-credit-si-takeover` von `upstream/master` = `965a4f9d`,
  vier Commits: `d1e6c9d6` (Marker verwerfen), `42dc9edb` (Sampler abbrechen), `a85aaccb` (Docstring),
  `582a0e02` (Test-Nachtrag aus der Mutationsprobe). **PR-Diff = 3 Dateien**, kein `docs/`, kein Frontend,
  kein `dist`. Spec und Plan: `docs/superpowers/specs/` bzw. `plans/2026-09-21-observed-double-credit.md`.
- **Belege:** Suite 3191 → **3196 passed** bei `diff`-identischen 327 FAILED-/ERROR-Namen
  (`prA-work/baseline-names.txt` gegen `final-names.txt`); `black --check` 68 unverändert, `ruff` grün;
  Mutationsproben **5 / 4 gefangen / 1 äquivalent / 0 unerklärt** (`prA-work/mutations.md`).
- **✅ Vorher-Messung auf HA-Test gefahren — der Fehler ist reproduziert.** Zone 1 „Beet", Fenster 214,14 s:
  Verbrauchszähler 33,0 → **51,27598833 L**, echtes Wasser 14,27598833 L, Differenz **exakt 4,000000 L** =
  die 60 s des SI-Laufs doppelt. Zwei Verlaufseinträge (`manual` 60 s/4 L, `observed` 214 s/14,28 L), dazu
  die Observer-Logzeile. Vollständig in der Spec, Abschnitt 9 — hier nicht doppeln.
- **Design-Historie lokal** auf `archive/design-history` @ `b73b6bb6` (zwei Commits). **Nicht gepusht.**
- **PR-Body fertig** in `prA-work/pr-body.md`. **Nicht freigegeben, nicht gepusht, kein PR eröffnet.**
- **HA-Test hinterlassen:** `observed_watering_enabled` bleibt **an** (für die Nachher-Messung), Log-Pegel
  zurück auf `warning`, Ventil und Master-Pumpe aus. Zone 1 steht auf 51,28 L — **Reset-Entscheidung offen**.

### Die Aufgabenliste ist umgezogen (21.09., User-Entscheidung)

**Kanonisch sind ab jetzt die Issues in `Eifel-Joe/HAsmartirrigation`** — 40 Stück, Einstiegspunkt das
angepinnte **`Eifel-Joe#42`** (Reihenfolge, Abhängigkeiten, Konventionen). Grund: die ToDo war nur über
Claude lesbar, und die Inventur vom 21.09. brauchte sieben Agenten, um überhaupt festzustellen, was offen
ist — sie fand zwei längst erledigte und zwei falsch einsortierte Punkte.

- **Form:** Englisch oben, Deutsch darunter (nicht eingeklappt). **Titel bleiben englisch** (User-Entscheidung):
  zweisprachige Titel lägen bei 170–200 Zeichen und machten die Liste zwei- bis dreizeilig pro Eintrag; der
  deutsche Überblick läuft einzeilig über `Eifel-Joe#42`.
- **Jeder Body nennt die frühere Bezeichnung** (`PR A`–`T`, `N1`–`N7`, `Befund 1`–`9`, `F1`–`F5`, `➀`–`⑪`),
  sonst wären `SESSION-STAND.md`, die Memories und `archive/design-history` nicht mehr auflösbar.
- **Zitierkonvention:** immer `Eifel-Joe#4` bzw. `JustChr#162`, nie eine nackte Raute — unser Zähler beginnt
  bei 1 und wächst in JustChrs Bereich hinein.
- **Pflegepflicht** (der Zweck der Umstellung): JustChrs Einwände am verlinkten PR/Issue kommen als
  Kommentar ins zugehörige Issue, in seinen Worten; schließt der Upstream-Bezug, schließt unseres mit;
  Reste bekommen ein **neues** Issue. Steht in `Eifel-Joe#42`, in der Projekt-`CLAUDE.md` als **Regel P2**
  und im Memory `hasi-todo-file`.
- `ToDo.md` ist von 386 auf 301 Zeilen geschrumpft und trägt nur noch Sitzungsstände; Sicherung der alten
  Fassung: `prA-work/ToDo.md.bak-vor-issues`.
- **Qualitätssicherung der Migration:** die 26 Bodies der Welle 2 entstanden per Workflow und wurden
  **mechanisch** geprüft — jeder Backtick-Bezeichner und jede `datei:zeile` aus der Quelle muss in beiden
  Sprachen vorkommen. 1 Beanstandung von 26. Vom Gegenprüfer gemeldete acht wurden einzeln geprüft, vier
  zurückgewiesen (er hielt ein Datum für erfunden, das in der Abschnittsüberschrift stand).

### Verworfen
- **Prädikat an der Schließen-Flanke.** In beide Richtungen falsch, getrennt davon, ob das Ventil vor oder
  nach `dispatch + run_seconds + 30` zugeht. Begründung mit Zahlen in der Spec, Abschnitt 3, Option 1.
- **Neu-Scharfstellen am Laufende.** Fünf Laufende-Stellen, braucht beide Hälften der Öffnen-Flanke, offene
  Frage zur Verlaufslogik → bewusst raus, als ToDo ➉ gewichtet vermerkt.
- **Der Eimer als Messwert der Feldmessung.** Hätte „kein Fehler" gemeldet — siehe Fallen.
- **Der Panel-Knopf „Jetzt bewässern" als Test-Trigger.** Filtert auf `ZONE_DURATION > 0`, und dieses Feld
  setzt die wetterabhängige Rechnung. Auf HA-Test standen die geplanten Läufe durchgehend auf
  `skipped/precipitation` bei Eimer 0.

### Fallen
- **Der Eimer maskiert Doppelgutschriften.** Jeder Gutschriftpfad schreibt ihn **absolut**
  (`async_write_watered_bucket`), der zuletzt schreibende gewinnt; am 21.09. nahm der Läufer die
  Observed-Gutschrift 8 ms später wieder zurück. Additiv und ungeklemmt ist nur `water_used_total`.
- **`custom_components/**` ist per MCP nur LESBAR.** Ein Fix lässt sich auf HA-Test nicht einspielen; auch
  `observed_watering_enabled` und `observed_entity` gehen nur über die HTTP-Views des Panels. Details im
  Memory `hasi-livetest-capability-boundary`.
- **`button.*_reset_usage` leert auch den kompletten Verlauf der Zone**, nicht nur den Zähler.
- **HA-Test hinkt upstream hinterher.** Installierter Stand vom 2026-09-20 vormittags, also **vor** #153
  und #157. Einzelne Dateien zwischen Branch und Instanz zu kopieren ist deshalb nicht sicher — die
  Importe passen nicht mehr zusammen.
- ⚠️ **Der Diagnostics-/Options-Dump enthält den Wetter-API-Schlüssel im Klartext.** Nicht in Issues,
  Logs oder Anhänge kopieren. (Wert absichtlich hier nicht genannt.)
- **Agenten-Zeilenangaben nachlesen.** Über beide Workflows 149 Urteile, 0 kassierte Aussagen, aber **19
  teilweise** — fast durchweg Zeilenversatz von 1 bis 13 Zeilen. Drei aus der ersten Runde übernommene
  Verweise waren in der Spec falsch und wurden korrigiert.
- **Dingbat-Codepoints:** ➈ ist U+2788, ➉ ist U+2789. Eine Ersetzung mit U+2789 für ➈ greift stillschweigend
  nicht (der Assert fing es ab).
- **`docs/superpowers/` und `docs/SESSION-STAND.md` sind untracked UND nicht gitignored** und liegen im
  Jekyll-`docs/`-Ordner, der nach upstream geht. Gezielt stagen, nie `git add .`.

### Nächste Schritte

**Reihenfolge: erst Live-Test auf HA-Test, dann PR.** So lief es bei #139 und #146, und `task-loop` stellt
den Live-Test vor „fertig". Eine frühere Notiz dieser Sitzung schlug die umgekehrte Reihenfolge vor — die
ist zurückgezogen.

✅ **Schritte 1–3 sind am 21.09. erledigt:** Zähler bleibt stehen (User-Entscheidung, der Reset-Knopf
hätte den Verlauf mitgelöscht); `production` auf `upstream/master` neu gebaut (**0 behind**, der frühere
Stand war 1 behind — vom User bemerkt), Pre-Release **v2026.09.21b1** gepusht und per HACS auf HA-Test
installiert, Neustart, Manifest verifiziert; **Nachher-Messung gefahren und grün** (Spec, Abschnitt 9.2).
Offen ist nur noch der Upstream-PR.

1. ~~Zähler-Reset entscheiden~~ — erledigt, bleibt stehen.
2. **Fix auf HA-Test bringen.** Per MCP geht es **nicht** (`custom_components/**` nur lesbar). Zwei Wege,
   beide freigabepflichtig, danach jeweils HA-Neustart (Memory `ha-no-auto-restart`):
   (a) **Pre-Release auf `production` bauen und per HACS ziehen** — das Rezept von #146, Memory
   `hasi-production-on-upstream`; kostet einen `--force-with-lease`-Push und ein GitHub-Release.
   (b) **Den GANZEN Ordner** `custom_components/irrigation_plus/` vom PR-Branch kopieren.
   ⛔ **NICHT nur `irrigation.py` kopieren.** Am 21.09. geprüft: HA-Test läuft einen Stand vom 20.09.
   vormittags, dessen `run_window.py` `zone_confirm_seconds` definiert, aber **kein**
   `zone_non_water_seconds` (das kam mit #157 am 20.09. abends). Der PR-Branch importiert genau dieses
   Symbol → `ImportError` beim Laden, Integration tot.
3. **Nachher-Messung**, identischer Ablauf zur Vorher-Messung (Spec, Abschnitt 9). Erwartung:
   `water_used_total` **+14,28 L statt +18,28 L** und **ein** Verlaufseintrag statt zwei. Ergebnis in den
   PR-Body, der Absatz „I have not yet measured the fixed build" wird dadurch ersetzt.
4. ~~ToDo-Punkt ➀ nachmessen~~ — ✅ **erledigt 21.09., Ergebnis: WEITER OFFEN** (`Eifel-Joe#23`, [Kommentar](https://github.com/Eifel-Joe/HAsmartirrigation/issues/23#issuecomment-5762950614)). Gegen den gefixten Branch gemessen: der Fix hängt am Dispatch, hier findet keiner statt. Restdifferenz `30 − grace` wie vorhergesagt — **+21 s** bei Vorgabewerten, +25 s bei Marge 0, **+30 s** ohne `confirm_entity`, 0 s bei Marge 25, −5 s bei Marge 30. Erreichbarkeit reproduziert: Datensatz `planned + 10 s` alt → `zone_run_in_flight` False, beide Marker leer, Beobachter stellt sich scharf, Schließen-Flanke plant die Gutschrift. Fix wäre ein Einzeiler im Resume-Pfad.
5. ~~PR eröffnen~~ — ✅ **erledigt 21.09.: [JustChr#162](https://github.com/JustChr/HAsmartirrigation/pull/162)**,
   MERGEABLE, 3 Dateien, +157/−11. Branch und `archive/design-history` (@ `afca8ef9`) sind gepusht.
   PR-Body trägt beide Messungen. **Jetzt: JustChrs Review abwarten.** Nachbesserungen als neue Commits,
   **kein Rebase** auf dem gepushten Branch.
   ⚠️ Im PR-Body steht bewusst **keine Fork-Versionsnummer** (User-Entscheidung 21.09.): der Testbuild wird
   nur funktional benannt („a pre-release built from this branch on top of `upstream/master`"), weil unser
   `vYYYY.MM.NN` mit JustChrs identischem Schema kollidiert und mit dem Fix nichts zu tun hat.
6. Danach **PR B** (Kette F1+F4+F3) aus der Arbeitsreihenfolge, `ToDo.md` ab Zeile 59.

### Empfohlene Skills
- `pr-workflow` + Memory `hasi-pr-build-recipe` für Push und PR.
- `superpowers:verification-before-completion` vor jedem „fertig".
- Für PR B wieder `superpowers:brainstorming` → `writing-plans` → `test-driven-development`.


## 2026-09-21 — Befunde geprüft, drei gemeldet, #149 diagnostiziert, v2026.09.20 released, Liste neu sortiert

### Stand (verifiziert)
- **Release [v2026.09.20](https://github.com/Eifel-Joe/HAsmartirrigation/releases/tag/v2026.09.20) draußen.**
  `production` = `40163afc`, **0 behind / 1 ahead** auf upstream v2026.09.21. **Fork-Delta erstmals wieder
  NUR Branding.** Belege und Rezept-Fallen stehen in Memory `hasi-production-on-upstream` — hier nicht doppeln.
  ⚠️ **HA-Prod-Update macht der User selbst** (ausdrücklich, 21.09.). Der Release bringt der Anlage vor
  allem `78f9ce2c` (#149), das war in keinem bisherigen Build.
- **Fünf eigene PRs gemergt** (#153/#154/#155/#156/#157). Patch-Vergleich gemacht: JustChr hat an unserer
  Arbeit nichts geändert. **#147 ist zu — der Feature-Stopp ist aufgehoben.**
- **Drei Meldungen offen:** [#158](https://github.com/JustChr/HAsmartirrigation/issues/158) Solrad-Default,
  [#159](https://github.com/JustChr/HAsmartirrigation/issues/159) Vorhersage-Gewichtung,
  [#160](https://github.com/JustChr/HAsmartirrigation/issues/160) Zeitzonen-Naht. Noch keine Antwort.
- **[#149](https://github.com/JustChr/HAsmartirrigation/issues/149) beantwortet** — Formel selbst
  nachgerechnet (`gutgeschrieben = echter Regen + Σ Zählerstand vor jedem Reset`), Gegenprobe auf HA-Prod
  gemessen. Offen: Megalos' Gegenprobe an seinem Graphen.
- **Die Aufgabenliste ist neu gebaut.** `ToDo.md` ab Zeile 59, Abschnitt **„🎯 Arbeitsreihenfolge —
  verbindlich ab 2026-09-21"**: 18 Arbeitseinheiten A–R plus Politur und Features, nach Schwere, mit
  Abhängigkeiten. **Das ist der Einstiegspunkt der Folgesitzung.** Grundlage: Inventur aller 35 offenen
  Punkte (2 erledigt, 1 teilweise) und eine Bündel-Prüfung (8 vorgeschlagen, **5 gefallen**, 3 halten).

### Verworfen
- **Verdacht gegen unser eigenes `78f9ce2c`** (Regression durch den Strip): vom Gegenprüfer kassiert —
  `tests/test_source_leak.py:111-118` nagelt „unlesbare Quelle → Feld fehlt" als **gewolltes** Ergebnis fest.
  Wäre eine Fehlmeldung über einen gerade veröffentlichten Release gewesen.
- **`store.py:1255` (`Current Precipitation` bekommt `{}`)** als Leck-Pfad: korrektes Verhalten, leeres Dict
  heißt „nie konfiguriert", dann IST der Wetterdienst die legitime Quelle.
- **Vier `manual_*`-Felder in `Config`** als „verlorene Einstellungen": es sind **tote Felder**. Die
  Koordinaten leben in den Config-Entry-Options (`__init__.py:850-855`). In die Ladeliste aufnehmen wäre
  **schädlich** (zweite konkurrierende Wahrheit) → löschen.
- **Fünf Bündel-Vorschläge**, jeder mit dem Alternativschnitt in der ToDo dokumentiert.

### Fallen
- **`docs/SESSION-STAND.md` ist untracked UND nicht gitignored**, im Jekyll-`docs/`-Ordner, der nach
  upstream geht. `git add .` trägt die Notizen in einen Upstream-PR. Gezielt stagen.
- **Heredocs fressen eine Backslash-Ebene.** `python - <<'EOF'` mit `D:\\…` kam als `D:\…` an, `\b` wurde
  zum Backspace-Steuerzeichen und landete in der Datei. Für Pfade in Heredocs **Vorwärtsschrägstriche**
  nehmen; lange Texte lieber per Write-Tool in eine Datei und dann splicen.
- **Agentenzahlen nie ungeprüft übernehmen** (bestätigt Memory `workflow-agent-hygiene`): die ET-Zahlen zu
  #158 wichen ~3 Prozentpunkte von der eigenen Messung ab. Belastbarer Anker war der analytisch
  herleitbare Gleichstand bei dT = 16,5 K.
- **Die Gegenprüfer-Linse zahlt sich aus.** In dieser Sitzung hat sie drei Fehlmeldungen verhindert und
  fünf von acht Bündeln gekippt — darunter drei, deren tragende Belege am Code schlicht falsch waren.
- **Branch-Diffs gegen einen späteren master-Commit sind wertlos** (verschiedene Basen). Für den
  Squash-Vergleich beide Patches gegen ihre eigene `merge-base` erzeugen und die Patches diffen.
- **Hauptbaum steht auf `rebuild/v2026.09.20`**, nicht auf `production` (gleicher Commit `40163afc`).

### Nächste Schritte
1. **PR A — Observed-Doppelgutschrift** (hoch, M, auf Prod scharf). Fixort geklärt: `_note_si_valve`
   (`irrigation.py:115-131`) verwirft `_observed_on_since[zone_id]` und ruft `_observed_cancel_meter` —
   deckt alle acht Dispatch-Pfade. **Zwei Fallen** stehen in der ToDo-Tabelle (Prädikat nicht kopieren;
   SI-Lauf kann früher enden als das externe Ventil). Danach Punkt ➀ **nachmessen**, nicht abhaken.
2. Dann B (Kette F1+F4+F3), C1 → C2, D, E — Reihenfolge und Fallen in der ToDo-Tabelle.
3. Offen aus #98: Frontend-Warnung („still yours if you want it") und zwei Feldmessungen.
4. **Aufräumen, wenn die #139-Historie nicht mehr gegengelesen wird:** Worktrees `befunde-work/base`,
   `pr139-work/dry2`, `pr139-work/archive-wt`; Branches `dry2`–`dry7`, `backup/*`, die gemergten `fix/*`.

### Empfohlene Skills
- `superpowers:brainstorming` → `superpowers:writing-plans` → `superpowers:test-driven-development` für PR A.
- `pr-workflow` + Memory `hasi-pr-build-recipe` für den Upstream-PR; Regel P1 (Design-Historie) beachten.


## 2026-09-20 — #139: PR #150 offen, live nachgemessen, zwei Folge-Issues

### Stand (verifiziert)
- **[PR #150](https://github.com/JustChr/HAsmartirrigation/pull/150)** offen, Branch `fix/backstop-grace`,
  17 Commits, `29 files changed, +4178/-842`. Nach dem Merge von `upstream/master` (v2026.09.17):
  **MERGEABLE / CLEAN**, alle fünf CI-Checks grün (build, lint, validate, test 3.13, test-ha-floor).
- **Umfang** wie am 19.09. vereinbart; T3b auf JustChrs Antwort vom 19.09. ebenfalls gestrichen.
  Sechs Nacharbeiten aus dem eigenen Review als C1–C6 im PR (C3/C5 = Raten-Fluss-Schnitt am Aus-Bericht,
  ein Loch, das erst der Zuschlag öffnet).
- **Belege:** Suite `7 failed, 3121 passed, 9 skipped, 320 errors` (3137 gesammelt; Namen identisch mit
  master), 111 neue Testfunktionen (eine über 5 Fälle parametrisiert = 115 Items), vitest 616 → 624,
  `dist` reproduzierbar. **Mutationsproben 155 / 150 gefangen / 5 äquivalent / 0 Überlebende**; ohne
  tötende Probe nur der i18n-Hilfetext-Pin (gewollt).
- **Faktenprüfung vor dem PR** (8 Gruppen gegen den Branch, jeder Verdacht von 3 Skeptikern gegengelesen):
  1 bestätigter Fund (Katalogzahl im Kommentarentwurf), 5 abgewiesen. Selbst gefunden und korrigiert:
  die 4-s-Vorgabe behauptete 1,1 s Reserve, real sind es **0,78 s** (Nachmessung 3,22 s liegt über der
  Zehn-Tage-Spanne 2,08–2,90 s).
- **Live:** HA-Test 9 Szenarien gegen `grace_emu_*`, getrieben von einem Skript **auf der Instanz**;
  HA-Prod je ein kurzer Handlauf: Kirschlorbeer 60,001 s offen → Abschluss +5,009 s → `actual_s` 60;
  Beet 63,222 s offen → +5,004 s → **`actual_s` 63** (vorher 60). Der Wächterpfad war auf dieser Anlage
  vorher unerreichbar. **Nicht belegt auf Prod:** der Raten-Fluss-Schnitt (Kirschlorbeer zählt `per_run`,
  Beet hat keinen Sensor) — im PR benannt.
- **Zwei Folge-Issues angelegt:** [#151](https://github.com/JustChr/HAsmartirrigation/issues/151)
  Fensterbepreisung (mit den drei Selbstkorrekturen meiner 15.09.-Beschreibung),
  [#152](https://github.com/JustChr/HAsmartirrigation/issues/152) Master-Lücke nach Neustart
  (vorbestehend, vom PR unverändert) — beide auf #150 verlinkt.
- **JustChr 20.09.:** hat seine Zusage vom 19.09. widerrufen und **v2026.09.17 ohne diesen PR als Stable**
  ausgeliefert; der PR eröffnet die nächste Beta-Kette. Nichts soll gehetzt werden. Sein Heads-up nannte
  „sixteen catalogue files" — im #139-Kommentar auf **acht** korrigiert (Backend-Katalog hat keinen
  Zonenfeld-Abschnitt, sein eigener Befund vom 15.09.; #125 hat exakt dieselben acht angefasst).
- **Design-Historie gepusht** (Regel P1): `origin/archive/design-history` @ `f6b7e595`, 6 Commits, inkl.
  Umsetzungsnachtrag im Plan und beider Review-Runden in der Spec.

### Nächste Schritte
1. CI auf #150 und JustChrs Review abwarten.
2. Nach einem Merge: Produktiv-Rebuild auf upstream, Pre-Release-Stand ablösen.
3. Aufräumen: `dry2`–`dry7`, `tmp/*`, `rebuild/v2026.09.18b2`, `backup/fix-backstop-grace-premerge`,
   Worktrees `pr139-work/dry2` und `pr139-work/archive-wt` — erst wenn die Historie nicht mehr
   gegengelesen wird (Archiv zitiert die `dry`-SHAs).

### Fallen
- Der Merge-Commit-Konflikt kam **nur** von der Versionszeichenkette in den vier `dist`-Bundles.
  Generierte Dateien nicht von Hand mergen: neu bauen und stagen (`git add -f`).
- Kein Rebase auf dem schon gepushten PR-Branch — Merge, JustChr squasht beim Merge ohnehin.


## 2026-09-19 — #139: JustChrs Umfangsantwort verarbeitet, Probelauf der Änderungen

### Stand (verifiziert)
- **JustChrs Antwort** vom 16.09. ([issuecomment-5692654650](https://github.com/JustChr/HAsmartirrigation/issues/139#issuecomment-5692654650)), Regel: Ein Commit gehört in den Fix, wenn er eine Lücke schließt, die erst die Wartezeit öffnet. DRIN: Start ab Ein-Meldung + Toleranz max(1 s, Marge), In-flight (T9), T3b, T7. RAUS: T6 (Backstop mit gespeicherter Aus-Meldung), T10 (Zeitfenster-Preis, eigenes Issue nach stable). Marge 4 s angenommen.
- **Workflow `wf_969540fa-c34`** (Ergebnis `pr139-work\wf-scope-answer.json`): T6+T10 in `dry2` gestrichen → Branch `tmp/drop-6-10` @ `361b52f7`; black/ruff grün; 7 Service-Suiten `222 passed, 1 error`; volle Suite `7 failed, 2987 passed, 320 errors` (zweimal), FAILED/ERROR-Namen identisch mit `baseline-0b418644.txt`. Schwester-Pfad-Prüfung (10 Funde, je 2 Gegenprüfer) und Mutationsprüfung In-flight (überlebt: Anker `RUN_VALVE_ON`, `<` → `<=`; kein Test für den zweiten Dispatch in der Wartezeit).
- **User-Entscheidungen 19.09.** (alle Empfehlungen): (a) Neustart nach der Wartezeit mit gespeicherter Aus-Meldung → `planned_s`; (b) Fensterregel nur mit gespeicherter Aus-Meldung, sonst Basis-Regel (ändert E4); (c) Stopp vor dem Planende ignoriert die gespeicherte Aus-Meldung; (d) Stopp in der Wartezeit rechnet nach der Watcher-Regel ab (completed innerhalb der Toleranz); (e) T3b mit T9 überflüssig → JustChr korrigieren, Streichen vorschlagen; (f) Neustart in der Wartezeit holt den Master nicht neu (upstream gibt beim überfälligen Neustart schon heute ohne Holen frei, `master.py` `async_master_release`).
- **Gepostet (Freigabe „mach weiter“ 19.09.):** [issuecomment-5740280769](https://github.com/JustChr/HAsmartirrigation/issues/139#issuecomment-5740280769) aus `pr139-work\comment-139-answer.md` — kündigt a–d, f und die T9-Tests an, schlägt das Streichen von T3b vor, korrigiert die Zahlen zu Punkt 1.
- **Probelauf läuft:** Workflow `wf_ec3b95ac-161`, `dry2` Branch `dry3/backstop-grace` (von `tmp/drop-6-10`), je Task ein Agent, der den Task-Commit an seiner Position ändert (`pr139-work\seqedit.py`), Belege in `pr139-work\dry3-logs\`. Reihenfolge: Texte → T5 (b) → T7 (c, d) → T8 (a, f, Test auf +602) → T9 (Dispatch-Tests) → Schluss (volle Suite, Einzelcommit-Prüfung, range-diff, Eventualfall „T3b gestrichen“).

- **JustChr 19.09. 07:55** ([issuecomment-5740329987](https://github.com/JustChr/HAsmartirrigation/issues/139#issuecomment-5740329987)): T3b RAUS (PR-Text: Lücke unter einer Sekunde zwischen In-flight-Ende und Backstop als bekannt nennen), a–d, f, T9-Tests DRIN, Test „Master nicht angefordert“ ausdrücklich; der nächste stable wartet nur auf #139; **Nachmessung beider Zonen VOR dem Merge**. #146 gemergt 07:44 (`2b2c403b`).
- **Probelauf fertig:** `wf_ec3b95ac-161` (Ergebnis `pr139-work\wf-dry3.json`, Belege `pr139-work\dry3-logs\`), danach T3b gestrichen + Helfer eingefaltet (`dry4`), Rebase auf `2b2c403b` → **Referenzbranch `dry5/backstop-grace` @ `58d6b7b5`** (Worktree `pr139-work\dry2`). Basis 7/3006/320 (3022), dry5 7/3097/320 (3113), Namen identisch; vitest 616 → 624; black/ruff je Commit grün; dist byte-gleich reproduziert; Änderungszeilen identisch mit dem Stand auf 0b418644.
- **User 19.09.:** Umsetzung als **Nachvollzug** der dry5-Commits (je Task erst Tests → Rot, dann Code → Grün, gleiche Nachricht); Plan = kompakte Revision 3. Live-Test: HA-Test mit Emulator `grace_emu_*` (angelegt, belegt; voller HA-Test-Zugriff freigegeben; Testskript auf HA-Test statt MCP-Takt), dann Pre-Release auf HA-Prod + je Zone ein kurzer `run_zone` durch den User.
- **Spec/Plan Revision 3** wird geschrieben: Workflow `wf_9b839069-b13`, Ausgabe `pr139-work\rev3\` (spec.md, plan-*.md, evidence.md, pr-body-draft.md, issue-window-pricing.md).
- **Rev 3 fertig:** Referenzbranch `dry6/backstop-grace` @ `70dc0c18` (Worktree `pr139-work\dry2`; T3 Real-Timer-Test verpasster Schluss, T5 Pin späte Meldung → `planned_s`); volle Suite 7/3099/320 (3115), Namen = Basis `2b2c403b`; vitest 624; jede der 101 neuen Test-Items fällt an ≥ 1 Probe. Spec + Plan Revision 3 lokal auf `archive/design-history` @ `5658ef72` (4 Commits vor origin, nicht gepusht); Teile in `pr139-work
ev3\`, PR-Entwurf `rev3\pr-body-draft.md`, Issue-Entwurf `rev3\issue-window-pricing.md`. **Wartet auf Plan-Freigabe.**
### Nächste Schritte
1. (erledigt) Probelauf auswerten; dann Spec + Plan überarbeiten (Regel P1, `pr139-work\archive-wt`, lokal): T6/T10 als gestrichen markieren, T2/T3b/T5/T7/T8/T9/T13/T14 und Kopf neu, E3/E4 + neue Entscheidungen, PR-Text-Abschnitte („bewusst unverändert“ mit beiden Auslösern, Reichweite ergänzt, kein `actual_s <= planned_s`), Schritt für das Issue Zeitfenster-Preis (`pr139-work\issue-window-pricing.md`, Korrekturen aus dem Kommentar einarbeiten).
2. Plan-Freigabe durch den User, dann Umsetzung ab Task 0 auf `fix/backstop-grace`.
3. JustChrs Antwort zu T3b abwarten; streicht er, gilt der Eventualfall aus dem Probelauf.

### Fallen
- Mehrere Agenten im selben Worktree: Prüfer lasen `dry2`, während ein anderer mutierte (Zwischenzustand gesehen). Zahlen aus solchen Läufen vor Übernahme nachmessen (z. B. die +602/+604-Werte aus der Gegenprüfung).


## 2026-09-16 — #146 auf rollierendes 24-h-Fenster umgebaut, gepusht und beantwortet

### Stand (verifiziert)
- **Branch** `fix/rain-guard-run-date` @ `a205ce96`, **gepusht** (`30e48419..a205ce96`, Freigabe 16.09.). PR danach MERGEABLE. Über `upstream/master` (`0b418644`): PR-2-Commits + 2 Merges (`a4395b13`, `ef1ff65f`) + 15 Umbau-Commits (`13a9f501` … `a205ce96`).
- **Merge-Falle:** `f14ebbdd` ≠ `upstream/master` (Release-Commit `0b418644` bumpt Versionen + dist). Gelöst: `merge -s ours 8dbc0223`, dann normaler Merge `upstream/master` (konfliktfrei). JustChrs Rezept `-s ours origin/master` hätte den Versionsbump verloren → im Kommentar erwähnt.
- **Belege Endstand:** Suite 7 failed / **3006 passed** / 320 errors (master 2906), FAILED/ERROR-Namen identisch (`pr146-work\after-final.txt`); vitest 616; black/ruff grün; dist byte-identisch reproduziert (seit `e70184e5` kein Frontend-Commit mehr).
- **Mutationssatz auf `a205ce96`** (`pr146-work\mutate.py`, Ergebnisse `mutation-results.json`, Log `mutation-run.log`): 44/45 beißen; der eine Überlebende (Temperatur-Ziel hinter beiden Reichweiten) war schlecht gestellt, die schärfere Fassung beißt (`mutation-temperature.json`); „Kalendertage zurück" (JustChrs Wunsch) → 25 Tests fallen (`mutation-calendar.json`). Frontend-Proben (en-Revert → vitest, de-Kopie → i18n-Test) in Task 8.
- **Messungen Live-API 16.09.** (Schlüssel `pr146-work\secrets\`, außerhalb des Repos): Pirate Default ⌊F⌋+47 h, `extend=hourly` ⌊F⌋+167 h, 30 986 → 85 602 Byte; Tagesblock = Ortsmitternacht, 86400 s; Σ Stundenraten = `precipAccumulation×10`; Open-Meteo F−32 h … F+159 h. Rohdokumente `pr146-work\pirate-*.json`, `openmeteo.json`.
- **Abgesendet (Freigabe 16.09.):** PR-Titel „Examine rain from the run's start, not from the day after it", Body aus `pr146-work\pr-body-new.md`, [Kommentar](https://github.com/JustChr/HAsmartirrigation/pull/146#issuecomment-5701002859) aus `pr146-work\comment-146.md`. Alter Body gesichert `pr-body-old.md`.
- **Design-Historie gesichert** (User: nur #146): #146-Commit auf `origin/archive/design-history` umgesetzt + Umsetzungs-Nachtrag, gepusht `fca77ee5..8abfa6ca`. Lokaler Archiv-Branch (Worktree `pr139-work\archive-wt`) neu aufgebaut: origin + drei #139-Commits `0280abb5`/`0ddd8cb6`/`fbb535a5` (vorher `22dfaa12`/`895c9c7d`/`6421499e`), weiter ungepusht; der alte #146-Commit `3e76cf09` wurde nach Patch-ID-Gleichheit übersprungen.
- **Live-Test HA-Test ✅ (16.–19.09.):** Pre-Release [v2026.09.18b1](https://github.com/Eifel-Joe/HAsmartirrigation/releases/tag/v2026.09.18b1) = `production` @ `d8eeb21b` (force-with-lease, Backup lokal `production-backup-v2026.09.17`). Galway, Pirate Weather: Abend-Dispatch 20:03 Fenster 1 → 3,17 mm übersprungen (alt 1,00 → gegossen), = Branch-Rechnung; 3 weitere Dispatches übersprungen; Fenster 3 → 2,41 mm vollständig, keine „covers only part"-Zeile; Gegenprobe Fenster 7 → Zeile da. Protokoll `D:\Entwicklung\HASI\pr146-work\live\ergebnis-livetest.md`. Debug-Logging zurückgesetzt. Ergebnis auf #146 gepostet ([issuecomment-5739763518](https://github.com/JustChr/HAsmartirrigation/pull/146#issuecomment-5739763518)). HA-Test zurückgestellt und geprüft (Heimkoordinaten, Fenster 1, Vorschau 0,00 mm; Wächter an, Pre-Release bleibt). Lokaler Rebuild-Zweig gelöscht (= production).

### Entscheidungen (User, 2026-09-16)
- Beide Härtungen: Pirate `extend=hourly` + Met-Office-Dokumentwahl per `covering_until` (JustChrs Wortlaut „when the hourly series ends before the window does").
- JustChrs Real-Client-Testdatei umgeformt übernommen (Pirate aus aufgezeichneter Antwort, `berlin`-Fixture lokal).
- Plan freigegeben, subagent-getrieben ausgeführt; Modelle gestaffelt (Memory `agent-model-tiering`).

### Verworfen
- Anteiliges Auffüllen / „Rest"-Variante: bricht `test_owm_s_last_day_starting_at_the_series_end_is_not_counted_again` (6,0 statt 3,0; falsch datierter Slot).
- Toleranz auf der Abdeckung: Lücke ist ein Band, Größe wäre geraten.
- Met-Office-Dokumente verschmelzen: `_hourly_segments` nimmt den kleinsten Abstand → Dreistundenwerte deckten nur 1 h.
- Mutationsläufe im Worktree: dort gewinnt `custom_components` aus `pytest_homeassistant_custom_component/testing_config` → Worktree-Code wird nicht importiert. Läufe im Hauptbaum (alles committet, Rücksetzen per Hash geprüft).

### Fallen
- Subagent läuft nur die Tests, die man nennt: Task 5 brach `test_hourly_temperature_forecast.py::…hourly_block` (URL-Schwanz nach `exclude=`), erst die volle Suite fand es → volle Suite gehört in JEDEN Task-Auftrag.
- Zwei Agenten starben mitten in Mutationsproben (Session-Limit, 401). Einer hinterließ eine **aktive Mutation** im Baum → vor Weiterarbeit immer `git diff` + `mut\*.bak`/`.sha` prüfen.
- Zwischenstand-Lesen: den Baum nicht lesen, während ein Agent mutiert (Fehlalarm „2 Tests rot").
- Prüfer-Agenten behaupten gern „Test läuft lokal nicht" — `.E` heißt: bestanden, Teardown-Fehler (Lingering timer, Vorbestand).
- Messbehauptungen: eine Nachstellung mit präpariertem Dokument ist keine Messung (Docstring korrigiert, `a205ce96`).

### Nächste Schritte
1. CI und JustChrs Review von #146 abwarten (PR an die Sitzung gebunden, Auto-Fix aus). Nachbesserungen als neue Commits, kein Rebase. Bei Änderungen am Code den Mutationssatz (`pr146-work\mutate.py`) im Hauptbaum erneut fahren.
2. #139-Commits auf dem Archiv-Branch bleiben lokal, bis #139 freigegeben ist; vor dem Löschen von `fix/backstop-grace` sichern (Regel P1).
3. Live-Test HA-Test (Open-Meteo, prüft nur die Fensterform) — eigene Freigabe.
4. Vorbestehende Befunde (ToDo.md, „Befunde aus dem #146-Umbau") nach JustChrs Antwort als Issues anbieten.
5. #139 bleibt zurückgestellt bis zur Antwort auf die Umfangsfrage.

---

## 2026-09-15/16 — #139 Backstop-Wartezeit: Spec + Plan (mit Probelauf), JustChr-Stand

### Stand (verifiziert)
- **Spec** `docs/superpowers/specs/2026-09-15-backstop-grace-design.md` und **Plan** `docs/superpowers/plans/2026-09-15-backstop-grace.md` liegen lokal auf `archive/design-history` (Worktree `D:\Entwicklung\HASI\pr139-work\archive-wt`), **nicht gepusht** (Push erst in Plan Task 14, Freigabe). Entscheidungen E1–E7 und alle Begründungen stehen in der Spec, nicht hier.
- **Arbeitsbranch** `fix/backstop-grace` = `upstream/master` `0b418644` (v2026.09.16), keine eigenen Commits. Arbeitsbaum: nur `?? docs/SESSION-STAND.md`.
- **Probelauf** (Wegwerf, lokal): `D:\Entwicklung\HASI\pr139-work\dry2`, Branch `dry2/backstop-grace` @ `67301a8b`, 13 Commits (T01–T12 + T03b). Suite gegen Basis `0b418644`: 7 failed / 2906 → **2993 passed** / 320 errors, FAILED/ERROR-Namen identisch (+87 Items); vitest 614 → 622; 109 Mutationsproben (101 gefangen, 8 äquivalent); Tasks 3b/6/7/10 einzeln und gemeinsam streichbar (konfliktfrei, grün). Messdateien `pr139-work\baseline-0b418644.txt`, `after-polish.txt`.
- **Kommentar auf #139** gepostet (Umfangsfrage, 4 abtrennbare Zusätze): [issuecomment-5685683675](https://github.com/JustChr/HAsmartirrigation/issues/139#issuecomment-5685683675) — Antwort steht aus (Stand 16.09. Nacht).
- **Upstream:** #144/#145 gemergt, Beta v2026.09.16; #146 bekommt Umbau-Wunsch (rollierendes 24-h-Fenster + 48-h-Abdeckung), Issue #147 „nur Fixes“ — Details in `D:\Entwicklung\HASI\ToDo.md` „Stand 2026-09-16“.
- **HA-Test** Sonoff-Emulator vorhanden (MCP gelesen 15.09.). Pre-Release-Weg: `production` + `fix/backstop-grace` (bringt #144/#145 mit), #146 eigenes Pre-Release.
- Aufgeräumt: erster Probelauf (`dry-backend`, `dry-frontend`, Branches `dry/*`) entfernt; `dry2` bleibt bis zur Umsetzung als Referenz.

### Verworfen
- `actual_s` ab `RUN_STARTED` mit 1 s Toleranz: normale Kirschlorbeer-Enden würden Teil-Läufe (Recorder 13.09.).
- `RUN_VALVE_OFF` aus jedem Subscription-Ereignis: `unavailable → off` nach Neustart stempelt die Wiederkehr (Plan-Kritik, Major) → E6.
- Pre-Release „nur production + #139“: mit neuer Basis nur per Rückport-Variante möglich → #144/#145 mitnehmen.

### Fallen
- **C: voll** (29 MB): Temp/npm-Cache in allen Plan-Befehlsblöcken nach `D:\Entwicklung\HASI\pr139-work\tmp` / `npm-cache` umgeleitet. Ohne Platz können Windows/HA-Werkzeuge trotzdem scheitern.
- Commit-Nachrichten: Zeilen, die mit `#` beginnen (z. B. „#139 gives …“), löscht git beim Rebase/Fixup still als Kommentar → „Issue #139 …“.
- freezegun friert auch die Loop-Uhr: echte `async_call_later` nur im selben `freeze_time`-Block armieren und vorstellen.
- Worktree-Dateien sind CRLF: Mutationsproben mit Backup + SHA-256-Vergleich zurücksetzen; `git status` allein beweist nichts.
- #146-Merge: `merge -s ours upstream/master` würde die Release-Version zurückdrehen; `-s ours 8dbc0223`, dann normal mergen.

### Nächste Schritte
1. **#139 ist zurückgestellt** (User, 2026-09-16): keine Umsetzung, kein Push, keine Freigabe des Plans, bis JustChr auf die Umfangsfrage antwortet. Plan und Spec liegen fertig lokal auf `archive/design-history` (`6421499e`, `895c9c7d`).
2. **#146-Umbau ist der nächste Arbeitsschritt** (neue Sitzung): JustChrs zwei Kommentare vom 15.09. auf #146, Spec/Plan-Revision nach Regel P1 (`archive/design-history`: `…/2026-09-13-rain-guard-run-date*`), Merge wie unter Fallen.
3. JustChrs Antwort auf #139 abwarten; streicht er Zusätze, vor Plan Task 14 die Commits mit den geprüften Befehlen aus Task 13 Step 8 droppen.
4. **#139-Umsetzung** nach Plan (`superpowers:subagent-driven-development`), ab Task 0; Probelauf `dry2` als Referenz, danach aufräumen (Task 14 Step 8).
5. Danach Befunde aus `D:\Entwicklung\HASI\ToDo.md`.

### Empfohlene Skills
- #146: `superpowers:receiving-code-review`, `superpowers:writing-plans` (Revision), `superpowers:test-driven-development`, `pr-workflow` §6
- #139: `superpowers:subagent-driven-development`, `code-doku`, `superpowers:verification-before-completion`, `superpowers:finishing-a-development-branch`, `pr-workflow`

---

## 2026-09-15 (Fortsetzung) — PR 2 Umsetzung läuft

### Stand (Zwischenstand)

- vitest-Basis gemessen: 22 Dateien / 614 passed (`D:\Entwicklung\HASI\baseline-pr2-vitest.txt`), Node v24.15.0.
- Tasks 1–9 committed, jeweils mit Spec- und Qualitätsprüfung abgenommen, alle Mutationsproben gefangen. SHAs nach Autosquash (Met-Office-Docstring in Task 3):
  - `29bfa268` T1, `5522f5ad` T2, `214cd55c` T3, `b291a3d5` T4, `090b59dd` T5, `d36b7333` T6, `ad70a322` T7, `49a71895` T9
  - Beleg Autosquash 1: `git diff 9e2d1a9b 106b04e6` zeigt nur den neuen Met-Office-Docstring-Punkt; `test_forecast_window.py` 27 passed.
  - Beleg Autosquash 2: `git diff 106b04e6 49a71895` zeigt nur den `const.py`-Kommentar zur Gewichtung („Shares the look-ahead setting … counts it from the day after the calculation“).
- Schlussprüfung als Workflow `wf_f11fb27f-815` (6 Linsen, Dedupe, je 2 Gegenprüfer; nur lesend) läuft.
- Task 10 (am 2026-09-15 gegen `9e2d1a9b`): black/ruff grün; Suite 7 failed / 2906 → **2959 passed** / 320 errors, FAILED-Namen identisch; vitest 614 → 616; dist in sync; Geschwister-Checks wie erwartet; keine SHAs.
- Abweichungen vom Plan (Review-Fixes), erklären die +53 statt +49:
  - T2: Test „negativ/NaN“ geteilt (negative Rate war vom Loch nicht unterscheidbar) — +1
  - T3: Pin für leere Intervallliste (`bool(intervals)`-Wächter ungetestet) — +1
  - T6: **Verhaltensänderung über den Plan hinaus:** Entscheidung auf dem gerundeten Wert (`observed = round(mm, 2)`, `would_skip = observed >= threshold`). Grund: sekundenweise Integration ergab 10 h × 0,2 mm = 1,9999999999999998 → Chip „2,0 von 2,0 mm“, aber bewässert. Test parametrisiert — +2

### Entscheidungen (User, 2026-09-15 Fortsetzung)

- **Basis:** PR 2 wird auf #145 gestapelt geöffnet (gehört zusammen). `--base master`, im Text die neuen Commits benennen.
- **Met-Office-Hinweis** (angeschnittener letzter Tag) kommt in den Modul-Docstring von `forecast_window.py`, als Fixup in den Task-3-Commit (Autosquash, Branch ungepusht).
- Bis zum fertigen PR durchziehen; PR-Text und #137-Kommentar vor dem Absenden vorlegen.
- **Schlussprüfung** (`wf_f11fb27f-815`, 6 Linsen, 16 Befunde, je 2 Gegenprüfer): 9 bestätigt (alle klein: Ausblick nennt laufenden Lauf mit vergangenem Start, 5 Testlücken, 2 Doku-Formulierungen, Test-Docstring „checked on the install“), 2 User-Entscheidungen, 5 strittig/widerlegt (Rundung imperial ≤0,005 mm, überlappende Tageseinträge, Off-Grid-Stempel, 1-s-Toleranz, Teardown-Timer vorbestehend). Fixes laufen als Workflow `wf_384a26b0-657` (Fixup-Commits auf T3/T6/T7/T9).
- **Met Office Dokumentwahl (User):** Toleranz auf `min(Lebensdauer, 3 h)` deckeln. Grund: bei Tages-/Zweitages-Update gewann ein bis 24/48 h älteres Stundendokument, dessen 48-h-Reihe vor dem Laufdatum endet → Wächter entscheidet nicht, obwohl das Dreistundendokument abdeckt. Fixup auf T5 mit Tests (Grenze, cache_seconds, fehlender Zeitstempel, neueres Stundendokument).
- **48-h-Reichweite (User):** Pirate Weather und Met Office (Stundendokument) lassen bei Fenster ≥3 den letzten Fenstertag großteils unbedeckt (Beispiel 6,57 → 4,67 mm). Nur benennen: Docstring, PR-Text, #137. Kein `extend=hourly`.
- **JustChrs Bitte** (Pirate-Weather-Tages-`time` als „aus der API übernommen, nicht gemessen“ in den Docstring) war im Code nicht erfüllt → im Fix-Workflow (T3-Fixup).
- **Fix-Runde 1 fertig** (alle 4 Jobs geprüft und abgenommen, noch NICHT autosquasht): `747d856d` fixup T7 (Ausblick überspringt laufenden Lauf via `not_before`, Dispatch-Pin, exakte Jetzt-Pins; ein Alt-Test lief nach realem Datum → `freeze_time`), `03f3d7e4` fixup T6 (Teilfenster-Test 4,58 mm, DEBUG-Pin, Docstring ohne „install“/„HA-Prod“), `40cc97db` fixup T3 (Ein-Messwert-Pin, „nicht überlappend“, Pirate-Weather-Hinweis), `41ddeb5a` fixup T9 (Doku „starting with the day of the run“, „reaches or exceeds“).
- **Fix-Runde 2 läuft** (`wf_b3fd0755-89d`): Met Office 3-h-Deckel (fixup T5), 48-h-Grenze + älterer Pirate-Kommentar entschärft (fixup T3), `general_precipitation_threshold` „reaches or exceeds“ in 8 Sprachen + Pin + dist (fixup T9).
- **Fix-Runde 2 fertig** (3 Jobs abgenommen): Met Office `tolerance = min(lifetime, 3 h)` + 14 Tests, 48-h-Grenze im Docstring (präzisiert: am Laufdatum Tag 3, Vorschau am Vorabend ein paar Stunden von Tag 2), älterer Pirate-Kommentar entschärft, `general_precipitation_threshold` „reaches or exceeds“ in 8 Sprachen + Pytest-Pin (Schlüssel wird im Panel derzeit nirgends gerendert) + dist.
- **Endstand `30e48419`** (8 Commits nach Autosquash, `git diff` vorher/nachher jeweils leer): `29bfa268` T1, `5522f5ad` T2, `2851f25a` T3, `9c2d4175` T4, `766f8f12` T5, `58476c9c` T6, `4fdcca19` T7, `30e48419` T9.
- **Belege Endstand (2026-09-15):** Suite gegen `a8cb8167` (unterscheidet sich vom Endstand nur im 48-h-Docstring-Absatz): 7 failed / 2906 → **2976 passed** / 320 errors, FAILED-Namen identisch; +70 = 28+17+14+8+2+1 gesammelte Items. vitest 614 → 616. `npm run build` reproduziert dist. black/ruff grün. Keine privaten Verweise/SHAs in hinzugefügten Zeilen. `test_forecast_window.py` am Endstand 28 passed.
- **Abgesendet (User-Freigabe 2026-09-15):** Branch gepusht (`origin/fix/rain-guard-run-date` @ `30e48419`), [PR #146](https://github.com/JustChr/HAsmartirrigation/pull/146) geöffnet (gestapelt auf #145/#144, `--base master`), [Kommentar auf #137](https://github.com/JustChr/HAsmartirrigation/issues/137#issuecomment-5678306428) gepostet, Design-Historie `archive/design-history` @ `fca77ee5` gepusht (Spec-Nachtrag „Umsetzung und Schlussprüfung“, Plan-Kopf). Archiv-Worktree entfernt, keine `worktree-*`-Branches.

### Nächste Schritte

1. CI und Review von #146 abwarten (PR ist an die Sitzung gebunden, Auto-Fix aktiv). Nachbesserungen als neue Commits, kein Rebase (`pr-workflow` §6) — der Branch ist jetzt gepusht.
2. Nach dem Merge von #144 und #145: master in `fix/dated-daily-forecast` und danach in `fix/rain-guard-run-date` mergen, kein Rebase.
3. **Task 12 Live-Test** braucht eigene Freigabe: HA-Test (Open-Meteo) mit dem Branch bespielen oder bis zum Produktiv-Release warten; Kriterien im Plan (Hilfetext je Modus, Chip = Summe der Open-Meteo-Stundenwerte des Laufdatums ab Abfragezeit ±0,05 mm, keine Exception).
4. Danach #139 (Backstop-Marge, Spec + Plan nötig), dann die restlichen Befunde aus `D:\Entwicklung\HASI\ToDo.md`.

### Fallen dieser Runde

- **Fixup + Autosquash** funktioniert sauber, solange der Branch ungepusht ist; Beleg jedes Mal `git diff <vorher> <nachher>` leer. Bundle-Dateien können nach `npm run build` als ` M` erscheinen, obwohl bytegleich (veralteter Index-Stempel) → Rebase bricht sonst ab; SHA-256 vergleichen, dann `git restore --source=HEAD`.
- **Tests mit fest verdrahtetem Datum** kippen, sobald Code „vergangene“ Zeitpunkte filtert (`not_before`): `freeze_time` setzen.
- **Workflow-Prüfer liefern Zeilennummern aus älteren Ständen** — Befunde am Code nachprüfen (drei Fälle diese Runde).
- **Mutationsproben parallel zu anderen Agenten** im selben Baum verboten; Schlussprüfer nur lesend, Experimente unter `pr2-work/review/`.

### Gesammelte Nebenbefunde (minor, noch nicht entschieden)

- `day_projection.forecast_rain_mm` (Schwester-Pfad, vorbestehend): streckt Raten über Lücken bis `_MAX_FORECAST_GAP_H`, NaN geht in die Summe, Duplikat behält die niedrigere Rate.
- Met Office: angeschnittener letzter Tag hinter der Stundenreihe zählt als voll abgedeckt mit zu kleiner Summe — im Spec als „im Code benannt“ gefordert, im Modul-Docstring von `forecast_window.py` fehlt der Punkt.
- Met Office `_forecast_document`: bei Auto-Update aus ist `cache_seconds`=0 → Lebensdauer 60 s; naive Fetch-Stempel über DST-Wechsel ±1 h (vorbestehendes Muster wie `_is_fresh`).

---

## 2026-09-15 — PR 2 zu #137: Plan geprüft, probegelaufen, freigegeben

### Stand

**Verifiziert:**
- [PR #144](https://github.com/JustChr/HAsmartirrigation/pull/144) und [PR #145](https://github.com/JustChr/HAsmartirrigation/pull/145): offen, ohne Review und ohne Kommentar. CI von #145 4/4 grün.
- Branch `fix/rain-guard-run-date` @ `f14ebbdd`:
  - entspricht #145, noch kein eigener Commit
  - Arbeitsbaum sauber bis auf diese Datei
- Basis-Suite `D:\Entwicklung\HASI\baseline-pr2.txt`: 7 failed / 2906 passed / 320 errors, gleiche FAILED-Namen wie bei PR 1.
- vitest-Basis: im Probelauf 22 Dateien / 614 passed. Im echten Lauf noch messen (Task 0 Step 3).
- **Plan und Spec, Revision 2026-09-15, vom User freigegeben**, auf `archive/design-history` @ `2f5fcc6e`:
  - `docs/superpowers/plans/2026-09-13-rain-guard-run-date.md`
  - `docs/superpowers/specs/2026-09-13-rain-guard-run-date-design.md` mit Nachtrag 2026-09-15
- **Geprüft wurde der Plan dreimal:**
  1. 22 Agenten gegen den Code nach #144/#145
  2. Probelauf der Tasks 1–7 und 9 in Wegwerf-Worktrees
  3. Nachtest der danach geänderten Stellen: 47 von 48 Aussagen gehalten; zwei Formatierungs-Kleinigkeiten eingearbeitet
- Alle `worktree-*`-Branches und `.claude/worktrees` entfernt.
- HA-Prod-Zeitzone per MCP geprüft: `Europe/Berlin`.
- Arbeitsordner `D:\Entwicklung\HASI\pr2-work\` außerhalb des Repos angelegt. Darin `mut/` für Mutations-Backups; der Plan verweist auf diesen Ordner.

### Entscheidungen (User, 2026-09-15)

- **Abendläufe:** Die Form „Datum des Laufs“ wird gebaut, per Test festgenagelt und im PR sowie auf #137 offengelegt. Mit Fenster 1 sieht ein Lauf um 21:00 nur noch drei Stunden.
- **Hilfetext** getrennt je Modus (`lookahead_help.{skip,water_less}`), in 8 Sprachen und in der Doku.
- **Met-Office-Dokumentwahl** kommt als eigener Commit in PR 2.
- Alle weiteren Festlegungen samt Begründung stehen im Spec-Nachtrag vom 2026-09-15.

### Verworfen

- **Plan vom 13.09. unverändert ausführen:** wäre an drei Stellen gescheitert:
  - `tests/test_init.py::TestPrecipitationLookAhead`
  - der Testzeitzone US/Pacific
  - einer wirkungslosen Mutationsprobe am 25-Stunden-Tag
- **Panel-Regel (Tagesmitte) für den Wächter:** freigegeben ist die Überlappung. Gemeinsam genutzt wird nur `day_span`, damit ist die offene Frage vom 14.09. beantwortet.
- **Tageseinträge „ab Reihenende oder später“:** OWMs 00Z-Slot würde doppelt gezählt, deshalb strikt „nach dem Reihenende“.
- **Met Office „der zuletzt abgerufene gewinnt“ ohne Toleranz:** würde nach jeder Berechnung das Stundenprodukt aus der Live-Schätzung werfen. Toleranz ist deshalb eine Cache-Lebensdauer.
- **INFO-Log an `run_start is None` ohne weitere Maßnahme:** der Ausblick ohne geplanten Lauf hätte bei jedem Refresh geloggt. Deshalb nennen Vorschauen immer einen Zeitpunkt.

### Fallen

- **Testzeitzone:** Das autouse-`hass` setzt US/Pacific für JEDEN Test. Eine Zone nur über ein per Namen angefordertes Fixture setzen, mit `set_default_time_zone` und Rücksetzen in `finally`.
- **NaN:** `max(0.0, nan)` ergibt 0.0. `math.isfinite` gehört vor jedes `max`.
- **Lint:** ruff wählt `B` (B905: `zip` ohne `strict=`) und `I`. `npm run build` ist lint + rollup: eine prettier-Beanstandung bricht den Build, und vitest bemerkt sie nicht.
- **Workflow-Worktrees** starten auf `6e11d112`, nicht auf HEAD. Im Prompt detachen lassen. Die Isolations-Sperre verweigert git- und pytest-Befehle mit Shell-Variablen.
- **Python-Heredoc mit Windows-Pfaden:** `\U` in normalen Strings ist ein Unicode-Escape. Raw-Strings verwenden oder das Skript als Datei schreiben.
- **Workflow-Ergebnisse** stehen als JSON unter `result` in `…/tasks/<id>.output`, sonst in `journal.jsonl`.

### Nächste Schritte

1. **Umsetzung (nach `/clear`):**
   - Plan vom Archiv lesen: `MSYS_NO_PATHCONV=1 git show origin/archive/design-history:docs/superpowers/plans/2026-09-13-rain-guard-run-date.md`
   - Mit `superpowers:subagent-driven-development` ausführen, ab Task 0 Step 3. Der Branch steht schon.
2. **Freigaben:** Task 11 (PR-Text, #137-Kommentar, Basis: auf #145 stapeln oder Merge abwarten) und Task 12 (Live-Test) brauchen je eine eigene.
3. **Nebenher:** Reviews von #144/#145 beobachten. Nach dem Squash-Merge von #144 master in `fix/dated-daily-forecast` mergen (kein Rebase), dann den PR-2-Branch nachziehen.
4. **Danach:** #139, dann die restlichen Befunde aus `D:\Entwicklung\HASI\ToDo.md`.

### Empfohlene Skills

- `superpowers:subagent-driven-development`, je Task `superpowers:test-driven-development`
- `code-doku`, `superpowers:verification-before-completion`
- am Ende `superpowers:requesting-code-review` und `superpowers:finishing-a-development-branch`
- `pr-workflow` für Task 11

---

## 2026-09-14 spät — PR 1 zu #137 (Tagesspanne) als #145, gestapelt auf #144

### Stand

**Verifiziert:**
- [PR #144](https://github.com/JustChr/HAsmartirrigation/pull/144): offen, CI 4/4 grün, MERGEABLE, noch kein Review und kein Kommentar.
- [PR #145](https://github.com/JustChr/HAsmartirrigation/pull/145) offen.
  - Branch `fix/dated-daily-forecast` @ `f14ebbdd`, gestapelt auf #144 (`d0e7cb6c`). User-Entscheidung: PR ohne Merge von #144, weil die Open-Meteo-Spanne laut JustChr in PR 1 gehört und in #144 nicht enthalten ist.
  - 5 Commits: OWM `2a52a6d0` (mit den Konstanten), Met Office `f509ba19`, Open-Meteo-Spanne `7c855cd3`, Pirate Weather `ac45c24f`, Panel `f14ebbdd`.
- Lokale Suite am selben Tag gemessen:
  - Basis auf `d0e7cb6c`: 7 failed / 2890 passed / 320 errors.
  - Branch: 7 / 2906 / 320, identische FAILED-Namen. +16 entspricht den neuen Test-Items (13 Funktionen).
  - Lint grün. 17 Mutanten unabhängig nachgefahren, alle gefangen.
- Design-Historie gepusht, `archive/design-history` @ `774f047a`:
  - Plan: Task 3 aufgeteilt, Stapelung auf #144 vermerkt.
  - Plan Task 5 und Spec: Regel „Tagesmitte“ fürs Panel statt Tagesbeginn.
- Aufgeräumt: Worktrees `base-pr1` und `archive-wt` entfernt, Messdateien `baseline-pr1.txt` und `after-pr1.txt` gelöscht, keine `worktree-*`-Branches.

### Entscheidungen

- **Panel** beschriftet nach dem Ortsdatum der Tagesmitte, und nur wenn Beginn UND Ende gesetzt sind; sonst gilt die Position.
  - Beginn: westlich von UTC einen Tag zu früh, weil OWM und Met Office UTC-Tage liefern.
  - Ende: östlich von UTC einen Tag zu spät.
  - Bei genau UTC+12 gewinnt das spätere Datum, per Test festgenagelt.

### Verworfen

- **Panel nach Tagesbeginn** (so stand es im Plan): Tag zu früh westlich von UTC. Gefunden hat das die Qualitätsprüfung am Beispiel Los Angeles.
- **Rückfall `end or start`:** bringt denselben Fehler zurück, wenn nur der Beginn da ist.
- **Pirate-Weather-Block ohne `time` abfangen:** die API liefert `time` immer, und die Nachbarfelder werden genauso streng gelesen.

### Fallen

- **HA-Zeitzone der Testumgebung ist US/Pacific**, nicht UTC. Zeitzonen-Mutanten brauchen explizit gesetzte Zonen, mit Wiederherstellung in `finally`.
- **Ein Test, dessen erwartete Tage mit der Positionszählung zusammenfallen, beweist die Datenherkunft nicht.** Er braucht eine Fixture mit Lücke oder übersprungenem Tag. Das betraf OWM, Met Office und Open-Meteo, alle drei nachgezogen.
- **`==` auf zeitzonenbehafteten datetimes** vergleicht nur den Zeitpunkt. `utcoffset() == 0` muss eigens festgenagelt werden.
- **`Etc/GMT-12` ist UTC+12**, das POSIX-Vorzeichen ist umgekehrt.
- **Die Ausgabedatei eines Workflows ist kein reines JSON.** Ergebnisse aus `journal.jsonl` im Transcript-Ordner lesen.
- **Fixups auf Task-Commits, die nicht HEAD sind:** `git commit --fixup=<sha>`, dann `GIT_SEQUENCE_EDITOR=true git rebase -i --autosquash <basis>`. Nur solange der Branch nicht gepusht ist.

### Nächste Schritte

1. CI von #145 prüfen, Reviews von #144 und #145 abwarten. Nachbesserungen als neue Commits, kein amend (`pr-workflow` §6).
2. Nach dem Squash-Merge von #144:
   - `git fetch upstream`, dann master in `fix/dated-daily-forecast` mergen, kein Rebase.
   - Ein Konflikt in `OpenMeteoClient.py` ist wahrscheinlich.
   - Push nur nach Freigabe.
3. PR 2 (Wächter am Laufdatum) nach Plan `2026-09-13-rain-guard-run-date.md`.
   - Die Regel „welcher Ortstag ist dieser Eintrag“ aus `websocket_get_weather_forecast` in einen geteilten Helfer ziehen, nicht neu herleiten.
   - Basis klären: auf #145 stapeln oder den Merge abwarten.
4. Danach #139 (Spec und Plan nötig), dann die restlichen Befunde aus der ToDo.

### Empfohlene Skills

- `pr-workflow` (§6 Nachbesserung)
- `superpowers:writing-plans` zum Abgleich des PR-2-Plans, dann `superpowers:subagent-driven-development`
- `superpowers:verification-before-completion`

---

## 2026-09-14 abends — #140/#141 gemergt, Issues #142/#143, PR #144 (Open-Meteo), sequential-Test

### Stand

**Verifiziert:**
- #140 (`4e53caf`) und #141 (`368a149`) von JustChr gemergt. `production` (`bf2b38b7`) ist inhaltlich upstream/master + Branding, steht aber 2 hinter den Squash-Commits → Rebuild erst mit der nächsten Upstream-Änderung.
- #137 entschieden (issuecomment-5667633763): PR 0 Open-Meteo zuerst, dann PR 1 Tagesspanne, dann PR 2 Wächter am Laufdatum. #139 entschieden (issuecomment-5667625952): Backstop-Zuschlag mit Latenz-Marge je Zone, wir bauen.
- Issues angelegt: [#142](https://github.com/JustChr/HAsmartirrigation/issues/142) Pirate-Weather-Tagesmittel, [#143](https://github.com/JustChr/HAsmartirrigation/issues/143) `live_estimate`-Fallback `forecast[0]`.
- [PR #144](https://github.com/JustChr/HAsmartirrigation/pull/144) offen: Branch `fix/open-meteo-forecast-starts-tomorrow` @ `d0e7cb6c` (Datumsfilter + `get_data`-Stundenfehler). CI beim Anlegen 1 grün / 3 laufend. Lokale Suite gegen master am selben Tag: 7 failed / 2883 → 2890 passed / 320 errors, identische FAILED-Liste. Design-Eintrag auf `archive/design-history` (`2ec66189`).
- HA-Prod: `zone_sequencing: sequential` (User). Alle drei Zonen im Überschuss, Sunrise am 15.09. bewässert nichts; der #98-Kettentest wartet auf natürlichen Bedarf (Memory `hasi-sequential-test-98`).
- HA-MCP war nach PC-Neustart weg, per /mcp neu verbunden (Diagnose-Rezept: Memory `verify-ha-system`).

**Offen:** Reihenfolge (User): PR 0 → PR 1 → PR 2 → #139 → restliche Befunde. Details in `D:\Entwicklung\HASI\ToDo.md`.

### Fallen

- **Mutationsskripte:** Backup auf die Platte, `try/finally`, absoluter venv-Pfad. Ein relativer Pfad `.venv/Scripts/python.exe` scheitert in `subprocess` unter Windows; der erste Lauf hinterließ die Datei mutiert.
- **Python-Hilfsskripte nicht im Ordner `irrigation_plus` starten:** dessen `datetime.py` verdeckt das Standardmodul.
- **Gegenprobe auf master im Worktree:** `_local_socket_unblock.py` ist untracked und muss in den Worktree kopiert werden.
- **„Jetzt bewässern“ / „Alle Zonen bewässern“** schreibt einen Überschuss-Bucket auf das Ziel herunter (kein `_mark_manual_run`) — nicht für Tests auf Prod benutzen.
- **Konfig-Ausgaben** vollständig maskieren (homarr trägt einen `ApiKey`-Header).

### Nächste Schritte

1. CI und Review von #144 abwarten (`ccd_pr get_status`).
2. PR 1 nach Plan `2026-09-13-dated-daily-forecast.md` ohne Task 3 (steckt in #144); Open-Meteo-Spanne auf dem #144-Stand aufsetzen, Branch erst nach dem Merge von #144 von upstream/master.
3. Danach PR 2, dann #139 (Spec + Plan nötig), dann die restlichen Befunde aus der ToDo.

---

## 2026-09-14 — Arm-Schranke (#140), PyETO-Tag (#141), Prod auf v2026.09.17

### Stand

**Verifiziert:**
- [PR #140](https://github.com/JustChr/HAsmartirrigation/pull/140) offen, Branch `fix/bound-wall-clock-hardware-window` @ `21f55808`. CI rot ausschließlich durch den master-Datumsfehler; erklärt im [Kommentar auf #140](https://github.com/JustChr/HAsmartirrigation/pull/140#issuecomment-5665561795).
- [PR #141](https://github.com/JustChr/HAsmartirrigation/pull/141) offen, Branch `fix/pyeto-day-of-year` @ `c6596478`, CI 4/4 grün, mergebar.
- [Issue #137](https://github.com/JustChr/HAsmartirrigation/issues/137): Zwei-PR-Vorschlag kommentiert, Antwort von JustChr steht aus. [Issue #139](https://github.com/JustChr/HAsmartirrigation/issues/139): wartet auf Formwahl.
- Fork: `production` = `bf2b38b7` = [Release v2026.09.17](https://github.com/Eifel-Joe/HAsmartirrigation/releases/tag/v2026.09.17) (upstream `437042a7` + #141 + #140 + Branding), hassfest und HACS grün. Rollback: Tag `v2026.09.16`.
- HA-Prod: v2026.09.17 nach Neustart am 14.09. geladen (Manifest geprüft), keine Integrations-Issues. Keine Automation, kein Skript, kein Dashboard ruft Dienste von Irrigation Plus auf.
- Design-Historie gepusht auf `archive/design-history` (`b61e18f2`): `docs/superpowers/specs/2026-09-13-bound-wall-clock-hardware-window-design.md`, `docs/superpowers/plans/2026-09-13-bound-wall-clock-hardware-window.md`, `docs/superpowers/specs/2026-09-14-pyeto-day-of-year-design.md`, `docs/superpowers/plans/2026-09-14-pyeto-day-of-year.md`, dazu die zwei Regen-Pläne `docs/superpowers/plans/2026-09-13-dated-daily-forecast.md` und `…-rain-guard-run-date.md`.
- Hauptbaum auf `production`, sauber bis auf diese Datei. Gelöschte lokale Branches (Wiederherstellung per SHA): `fix/inlet-and-anchor-hardware-window` `52e450c9`, `fix/flow-cal-litre-floor` `93fe524f`, `fix/manual-bucket-assertion` `c0d368f1`, `backup/production-pre-v2026.09.17` `4d4ee13d`, `rebuild/v2026.09.17` `bf2b38b7`, `rebuild/v2026.09.17-pre141` `5bbc09d7`. Termin-Lauf „Regen-Beleg #137“ gestoppt.

**Offen:** alles Weitere steht in `D:\Entwicklung\HASI\ToDo.md`, Abschnitt „Jetzt dran“ (Status-Eintrag vom 14.09. und Block „Befunde aus der Arbeit an #137, #140 und #141“) sowie „Feature-Backlog“.

### Verworfen

- **PyETO-Fix in #140 bündeln:** zwei fremde Themen, JustChr squasht beides unter den Titel von #140. User hat zweimal den eigenen PR gewählt.
- **Tag im Wetterdatensatz, Pflichtparameter, nur den Test festnageln, Fensterende statt Fensterbeginn:** Begründungen im Spec `2026-09-14-pyeto-day-of-year-design.md`, Abschnitt „Verworfen“. Das Fensterende ist zusätzlich per Mutation M10 im PR #141 widerlegt.
- **„Tageszeit-Flake“ als Erklärung des roten Tests:** falsch. Mit eingefrorener Uhr ist er datumsabhängig (13.09. grün, 14.09. rot zu jeder Uhrzeit).

### Fallen

- **Datumsabhängige Tests:** Basis und Branch immer am selben Tag messen, sonst sieht ein Vorbestandsfehler wie eine Regression aus. Bisektieren mit dem freezegun-Plugin aus Plan `2026-09-14-pyeto-day-of-year.md`, Task 5 Step 1.
- **Plan-Erwartungen veralten**, sobald Reviews nachbessern (Testzahlen, Code-Schreibweise). Prüf-Tasks gegen den Endstand beurteilen, nicht wörtlich.
- **Von Agenten entworfene PR-Texte** tragen Zahlen aus Zwischenständen. Vor der Freigabe nachmessen: zwei Mutationszahlen in #141 waren falsch.
- **Ganzzahliger Pin prüft keinen Rundungszweig** — dritter Fall, jetzt 263,6 im Kreuz-Pin.
- **Workflow mit `isolation: worktree`** hinterlässt `worktree-*`-Branches und `.claude/worktrees/` im Repo. Nach jedem solchen Lauf aufräumen.
- **Workflow-Skript per Python unter Windows editiert** bekommt CRLF und wird als „control characters“ abgelehnt. Bytes mit LF schreiben.
- **Langes Markdown per Bash-Heredoc** scheiterte am Quoting; dafür das Write-Tool nehmen.
- **HACS sieht ein neues Fork-Release** erst nach `update_information` für `Eifel-Joe/HAsmartirrigation`.

### Nächste Schritte

1. Reaktionen von JustChr prüfen: `gh pr view 140 141 --repo JustChr/HAsmartirrigation`, `gh issue view 137 139 --repo JustChr/HAsmartirrigation`.
2. Nach dem Merge von #141: `git fetch upstream`, `master` in `fix/bound-wall-clock-hardware-window` mergen (kein Rebase), Push nur mit Freigabe, dann CI von #140 prüfen.
3. Sobald #140 und #141 upstream sind: Prod-Rebuild nach Memory `hasi-production-on-upstream` (Fork-Delta dann nur Branding).
4. Nach JustChrs Antwort auf #137: die zwei Regen-Pläne auf `archive/design-history` an seine Antwort anpassen und ausführen.

### Empfohlene Skills

- `superpowers:systematic-debugging` zuerst, falls die CI von #140 nach dem Merge nicht grün wird.
- `pr-workflow` für Push und PR-Schritte an JustChr.
- Für die Regen-PRs: `superpowers:writing-plans` (Plan-Abgleich), dann `superpowers:subagent-driven-development`, `superpowers:verification-before-completion`, `superpowers:finishing-a-development-branch`.

---

## 2026-09-12 — Upstream kam parallel; zwei PRs und ein Issue offen

**Der Tag in einem Satz:** JustChr hat die Minuten-Aufrundung morgens um 08:41 selbst
gefixt (`e9f2da51`, aus unserem #88-Messbericht, sechs Stunden bevor unser PR aufging).
Der eigene Branch wurde weggeworfen und auf seinem Stand neu aufgesetzt.

### Offen bei JustChr

| | Inhalt | Stand |
|---|---|---|
| [PR #135](https://github.com/JustChr/HAsmartirrigation/pull/135) | Verteiler-Einlass, Finish-Anker, Rundungsregeln zusammengelegt (`hardware_window` + `opensprinkler_window`) | CI grün, CLEAN |
| [PR #136](https://github.com/JustChr/HAsmartirrigation/pull/136) | Kalibrier-Schwelle in Litern statt Sekunden (`FLOW_CAL_MIN_SAMPLE_L`) | CI grün, CLEAN |
| [Issue #137](https://github.com/JustChr/HAsmartirrigation/issues/137) | Regen-Wächter prüft nie den Bewässerungstag selbst | wartet auf seine Formwahl |

[PR #134](https://github.com/JustChr/HAsmartirrigation/pull/134) geschlossen als überholt,
mit Kommentar zur Parallelität. Design-Historie für #135 und #136 liegt auf
`archive/design-history` und ist gepusht.

### Entscheidungen, die Bestand haben

- **OpenSprinkler wird umgerechnet**, nicht ausgeschlossen. `run_station` rundet wirklich
  (Decke auf ganze Sekunden, Untergrenze 1). JustChrs Variante war besser; unser alter Pin
  wurde umgedreht.
- **Nicht bauen, bevor JustChr die Form gewählt hat.** Er hat sie an einem Tag zweimal
  bestimmt und beide Male besser als der eigene Vorschlag. Vorbauen kostete heute neun Commits.
- **Regen: Issue statt Branch.** Die zwei Lösungswege unterscheiden sich im Umfang um vier
  Wetterquellen; auf den falschen zu setzen heißt wegwerfen, nicht nachbessern.

### Befunde, die noch niemand gefixt hat

- **Der Finish-Backstop hat keinen Zuschlag.** `async_call_later(planned_seconds)`, ohne
  Marge. Nach `e9f2da51` feuert er auf Beet 1,4 s vor der Schlussmeldung statt 38 s — das
  Vorzeichen kippt nicht, `_watch_finish` bleibt auf BEIDEN Zonen unerreichbar (Kirschlorbeer
  aus einem zweiten Grund: Ventil 0,567 s zu früh, Entprellung wird vom Backstop kassiert).
  JustChrs Vorhersage auf #88 trifft damit nicht zu. Auf #88 als Angebot formuliert.
- **`bound_wall_clock`** rechnet nicht um; braucht ein `duration_unit`-Feld auf `ZoneRun`.
  In #135 als Folge-Arbeit angeboten.
- **Millimeterzahl im Verlaufseintrag ist KEIN Dreizeiler.** `detail` ist ein übersetzter
  Gründe-Code, exakt verglichen in `_skip_logged_today` und gegen `_EVICTABLE_SKIP_DETAILS`.
  Braucht ein eigenes Feld plus Frontend.

### Fallen dieser Runde

- 🔴 **Ein Pin auf einer GANZEN Zahl prüft den Rundungszweig nicht.** Die alten
  OpenSprinkler-Pins blieben grün, als das Verhalten umgedreht wurde, weil sie bei 263,0
  standen. Neu bei 263,4. Zweites Vorkommen derselben Falle in zwei Tagen.
- Beet hat **keinen Flusssensor** — `_sc_finish_flow` gibt `None`, die Kalibrierprüfung steigt
  sofort aus. JustChrs Aussage über „überhöhte Beet-Proben" geht ins Leere; auf #88 korrigiert.
- Lokale Suite: **immer gegen den Elternstand messen**. Basis `upstream/master` = 7 failed /
  2788 passed / 307 errors.

### Termin

Einmaliger Termin `hasi-regen-beleg-137` am 13.09. um 11:00: prüft, ob wie vorhergesagt
bewässert wurde, obwohl am selben Tag Regen fällt. Legt einen Kommentarentwurf vor,
schickt ihn NICHT ab.

---

## 2026-09-11/12 — Minuten-Aufrundung: Spec, Plan, Serie abgeschlossen, 6 Commits

Nicht hier wiederholt, per Pfad referenziert: Spec und Plan liegen auf `archive/design-history`
unter `docs/superpowers/specs/2026-09-11-hardware-duration-accounting-design.md` und
`docs/superpowers/plans/2026-09-11-hardware-duration-accounting.md`. **Der Plan ist die
Wahrheit, nicht ein Chatverlauf.**

### Stand (nur Verifiziertes)

- **Der Befund**, live gemessen auf HA-Prod: ein Ventil, dessen Schluss der Hardware gehört
  und das nur ganze Minuten nimmt, bekommt aufgerundet und läuft auch so lange; gebucht wurde
  die ungerundete Zahl. Beet: 502 s --> 540 --> 542,8 gemessen (+7,6 %); 265 --> 300 --> 302,3
  (+13,2 %); 263 --> 300 --> 302,1 (+14,1 %). Drei von drei Läufen.
- **Arbeitsbranch `local/minute-rounding`**, von `upstream/master` = `72406c8d` (v2026.09.14).
  Vier Commits, 6 Dateien, +357/−7:
  - `f8b82a20` `hardware_window(seconds, unit) -> tuple[int, float]` in `duration_math.py`
  - `b06231b4` `_sc_convert` wird Weiterleitung darauf
  - `402adb72` der self-closing-Lauf verbucht die wirksame Dauer
  - `8464b3b0` der Batch-Plan und seine Buchhaltung nennen dieselbe Dauer
  - `c413f937` Verteiler-Einlass: `_dist_convert` gelöscht, `_dist_open_inlet` gibt die
    wirksame Dauer zurück, der Zyklus nimmt sie; dazu die Zusicherung, dass die
    Rundungsregel genau einmal existiert
  - `ebf08529` Mess-Obergrenze, Master-Frist und Zyklus-Schätzung an dasselbe Fenster
    gebunden — reines `_dist_inlet_instruction` aus dem Öffnen herausgelöst, einmal VOR
    `cap = window` gerufen; `InletInstruction`-NamedTuple, damit ein Vertauschen der beiden
    Hälften nicht mehr formulierbar ist (CI hat keinen Typprüfer)
- **Schluss-Nachweis auf `ebf08529`:** Regel genau 1× im Baum, Lint grün, volle Suite gegen
  `upstream/master` gemessen — **7 failed / 2783 passed / 306 errors vorher, 7 failed / 2808 passed / 308 nachher,
  identische Fehlernamen, +25 Tests.** Die zwei neuen Errors sind Teardown-Artefakte der
  neuen Batch-Tests.
- 🔴 **OFFENE ENTSCHEIDUNG, blockiert den PR** — siehe Nächste Schritte, Punkt 1.
- **Alle fünf durch Spec- UND Qualitätsprüfung abgenommen.** Die Tests wurden nicht nur grün
  gesehen, sondern durch Mutation als beißend nachgewiesen.
- **Lint grün** (`black`, `ruff`). Fehlerzahlen der Suite gegen den jeweiligen Elternstand
  gemessen, nicht angenommen: 7 failed / 306 errors vorher, identische Fehlernamen nachher,
  die zwei neuen Errors sind die Teardown-Artefakte der zwei neuen Batch-Tests.
- **⚠️ Der Hauptbaum steht auf `local/minute-rounding`, nicht auf `production`.** Vor
  Produktiv-Arbeit zurückstellen.
- **Worktree** für die Design-Historie liegt im Scratchpad unter `archive-wt`, Branch
  `archive/design-history`, vier Commits, noch **nicht gepusht**.

### Verworfen

- **Abrunden statt aufrunden** (die Hardware folgt den Büchern). Harter Rand: eine gerechnete
  Dauer unter einer Minute ergäbe null, man bräuchte doch eine Untergrenze und hätte dort
  wieder aufgerundet. Dazu der Grundsatz des Betreibers: lieber etwas überwässern als zu wenig.
- **Die Umrechnung aus `_sc_dispatch_open` zurückgeben** (die elegantere Form). Scheitert an
  der Reihenfolge: das Observed-Sperrfenster muss VOR dem Öffnen armiert werden, die Korrektur
  muss also vor dem Absenden stehen.
- **OpenSprinkler mitnehmen.** Erfüllt die Bedingung nicht — `run_station` nimmt ganze
  Sekunden, es gibt dort keine Einheiten-Umrechnung. Durch einen eigenen Pin gesichert.

### Fallen

- **🔴 Ein grüner Test ist kein beißender Test.** Zwei Zusicherungen bestanden auch mit
  revertiertem Fix: eine rechnete auf einem Literal statt den Produktionspfad zu beobachten,
  die andere nagelte mit einer GANZEN Zahl einen Zweig fest, in dem die Umrechnung ein No-op
  ist. Beide gefunden, beide ersetzt. **Mutations-Gegenprobe ist Pflicht.**
- **🔴 Der Ceiling-Clamp frisst den Beweis.** Eine Testzone ohne Defizit bucht `min(0.0, ...)`
  = 0,0 — die naheliegende Gutschrift-Assertion wäre wertlos gewesen. Die Fixture trägt jetzt
  `ZONE_BUCKET: -10.0`.
- **`git stash` revertiert nichts, was schon committet ist.** Ein Gegenbeweis kam deshalb
  falsch-negativ zurück. Den Hunk direkt entfernen und danach per Hash-Vergleich
  wiederherstellen.
- **Name-Shadowing:** `planned_seconds` ist in `batch.py` eine importierte Funktion. Eine
  lokale Variable so zu nennen verdeckt sie für die ganze Funktion; der Nächste, der
  `planned_seconds(run)` ergänzt, bekommt einen TypeError. Lokal heißt es `planned`.
- **Kommentare nach `code-doku` brauchen alle drei Teile.** Wurzel, Fix-Logik und NOT-TO-DO.
  Zweimal fehlten Teile, beide Male in der Prüfung gefangen.
- Die lokale Suite ist unter Windows unvollständig. **Immer gegen den Elternstand vergleichen**,
  nie gegen null.

### Nächste Schritte

1. 🔴 **ENTSCHEIDUNG EINHOLEN, bevor irgendetwas rausgeht: die Mess-Obergrenze `cap`.**
   `cap = window` bindet in `distributor.py` VOR der Neuzuweisung, die Master-Abschaltfrist
   wird daraus berechnet. Unser Fix verlängert das Fenster, das diese Frist überdauern muss,
   um bis zu 59 s, ohne die Frist mitzuziehen. Im Review durchgerechnet: bei kurzer Pause deckt
   die Frist 291 s, während die Schleife 310 s verbraucht — **die Pumpe kann mitten im Fenster
   abschalten, was vor diesem Commit nicht möglich war.** Gleiches Muster: die Zyklus-
   Dauerschätzung summiert weiter gepreiste Werte, stimmte vorher mit der Schleife überein,
   jetzt nicht mehr. **Drausssenlassen ist also NICHT neutral.**
   Drei Wege: (a) mitnehmen — den reinen Rechenteil aus `_dist_open_inlet` herauslösen
   (`_dist_inlet_instruction(distributor, seconds) -> (hw, seconds)`, ohne Nebenwirkung) und
   EINMAL vor `cap = window` rufen, dann nehmen Obergrenze, Frist, Schlafdauer und Gutschrift
   dieselbe Zahl aus derselben Quelle, ohne zweite Kopie der Regel; (b) den Verteiler-Commit aus
   dem PR nehmen, dann geht ein vollständiger PR über self-closing + Batch raus; (c) so lassen
   und beschreiben. **Empfehlung: (a).**
2. Danach: `_sc_convert`-Shim entfernen — nur noch ein Aufrufer, `_sc_dispatch_open`.
3. Upstream-PR nach Skill `pr-workflow`. **Text vorher im Chat freigeben** (Projektregel).
   Branch von `upstream/master`, NUR Fix+Test.
4. Regel P1: Spec und Plan liegen auf `archive/design-history` (4 Commits), **noch nicht
   gepusht**.
5. ⚠️ **Hauptbaum steht auf `local/minute-rounding`, nicht auf `production`** — vor
   Produktiv-Arbeit zurückstellen. Zwei Worktrees im Scratchpad: `archive-wt`, `base-wt`.
### Für den PR-Text vorgemerkt

Der Fix heilt drei Dinge gratis mit, im Review nachgewiesen: `async_stop_self_closing` rechnete
`min(elapsed/planned, 1.0)` und gab einem Stopp bei t=280 auf einem echten 300-s-Ventil **volle**
Gutschrift für 93 % des Wassers; der Neustart-Abgleich hielt einen Lauf für beendet, während das
Ventil noch 30 s offen war; `_watch_finish` entscheidet an derselben Zahl. **Nicht** hineinschreiben:
die beiden Wiederarmierungen in `run_watch.py` erben zwar formal, sind für diesen Modus aber
unerreichbar. Für die Release-Notes: ein manueller Lauf „2,5 Minuten" bucht künftig 180 s statt 150.

### Empfohlene Skills

`superpowers:subagent-driven-development` (läuft), pro Task
`superpowers:test-driven-development`, am Ende `superpowers:finishing-a-development-branch`
und `pr-workflow`.

---

## 2026-09-08/09 — Domain-Umzug auf `irrigation_plus`, Prod + Test + 2 PRs

### Stand (nur Verifiziertes)
- **HA-Prod ist umgezogen.** `smart_irrigation` → `irrigation_plus`, neuer Entry
  `01M20YP65K7ZSZWSG1KT2RBV5T`, installiert **v2026.09.14**, Update auf v2026.09.15
  sichtbar (HACS aufgefrischt, `pending_update: true`). Alte Integration entfernt,
  Ordner gelöscht, 0 Reste außer `update.smart_irrigation_update` (gehört HACS).
- **Import verlustfrei belegt**, nicht behauptet: Konfiguration 20/20 Felder identisch,
  Zeitplan „Sunrise" feldweise, Zone Beet 25 Felder + 50 Run-Log-Einträge inkl.
  Ventil-Verdrahtung, Kirschlorbeer 7,24/5162,53 und Kirschbaum 7,95/1077,28 exakt.
  Entitäten: 63 alt = 51 neu + 12 Diagnose-Sensoren (danach wieder aktiviert).
- **API-Schlüssel überlebt.** Lag im ALTEN Slot `weather_service_api_key` (Entry von
  2025-06-13), beide Slots nach dem Import da, erzwungener `update_all_zones` ohne
  Authentifizierungsfehler. Dieser Pfad war auf HA-Test NICHT probebar (dort Open-Meteo).
- **Erster Lauf unter neuem Namen (09.09., 06:26):** Beet, 502 s, 25,94 L,
  `self_closing`/`completed`, Zähler exakt +25,94, Bucket −0,85 → +0,23. Keine Fehler.
- **Nacharbeiten auf Prod fertig:** `config/influx.yaml`-Glob auf `sensor.irrigation_plus_*`,
  beide Dashboards umgestellt (inkl. `card_mod`-Jinja und Bucket-Unterknöpfe),
  `automation.irrigation` + 4 Template-Helfer gelöscht, 12 Diagnose-Sensoren reaktiviert.
- **HA-Test** ebenfalls umgezogen (Generalprobe), Entry `01M20AD0AWZJ15ZXSF1ECVJZN3`.
- **Fork:** `production` = `b5f47f27` = **v2026.09.15**, **0 behind** upstream
  (`8d219884` = deren v2026.09.13), CI komplett grün inkl. HACS Action.
  Backups: `backup/production-pre-v2026.09.13` / `-14` / `-15`.
- **Upstream:** Issues #129 und #130 **geschlossen**, #128 offen. PRs
  [#131](https://github.com/JustChr/HAsmartirrigation/pull/131) (Wortlaut, 8 Sprachen) und
  [#132](https://github.com/JustChr/HAsmartirrigation/pull/132) (Marker) **gemergt**.
  Sein Folge-Fix `db603d88` korrigiert einen Fehler in unserem #132 (s. Fallen).

### Fallen (haben Zeit gekostet oder hätten Schaden angerichtet)
- **🔴 Parallelbetrieb = zwei Bewässerungssteuerungen auf denselben Ventilen.** Kein
  domänenübergreifender Guard. Gegenmittel und Belege: Memory
  `hasi-migration-dual-run-hazard`. Die Regenverzögerung VOR dem Hinzufügen ist der
  eine Hebel, der beide Kopien anhält — auf Prod durchgemessen, sie wandert mit der
  rohen Store-Kopie und armiert nach dem Aufheben wieder.
- **🔴 Fremdgelieferte Werte brauchen exakten Vergleich.** Ich stellte in #132 die
  Marker von einer Konstante auf das Fork-Manifest um und ließ den Teilstring-Vergleich
  stehen — `@org` trifft `altmenorg`. Erkannt, in den Docstring geschrieben und
  weggeredet. Memory `supplied-values-need-stricter-matching`.
- **Pins, die aus dem falschen Grund grün sind.** Zweimal an einem Tag: `irrig` steckt im
  Produktnamen (→ `irrigazion`), und der Bewässerungs-Stamm steckt in sechs Katalogen
  schon in „irrigation history" (→ Import-Schritt auf das Wort für *Ventil* gepinnt).
  **Mutations-Gegenprobe ist Pflicht, grün allein beweist nichts.**
- **Reparatur-Dialoge sind per MCP NICHT auslösbar** (REST-Flow, MCP kann nur einmalige
  WS-Kommandos). Der Nutzer muss klicken. Nachbauen würde `async_cleanup_is_safe` umgehen.
- **`.storage/*` ist über `ha_read_file` nicht lesbar** (Allowlist). Für Soll-Ist-Vergleiche
  den Diagnostics-Dump nehmen, mit `diagnostics_data_path` (z. B. `data.store.config`)
  gegen die Kontext-Grenze.
- **Nach jedem HA-Neustart liefert das MCP-Add-on ~1 Minute lang 502**, obwohl die
  Weboberfläche schon 200 antwortet. Nicht als Fehlschlag deuten, warten.
- **Der lokale `brand/`-Ordner erreicht die HACS-Kachel nicht** — HACS schreibt die
  CDN-Adresse fest ins `entity_picture`. Details in `hasi-domain-migration-rehearsal`.
  **User-Entscheidung: liegt bei JustChr, nichts unternehmen.**
- **Auto-Merges sind gefährlicher als Konflikte.** `migrate_domain.py` mergte konfliktfrei
  und hätte still unseren überholten Marker-Ansatz weitergeführt.
- **Ein bewusstes Fork-Delta unter UPSTREAMS Namen belassen.** Die Zusicherung
  `test_this_repository_derives_exactly_the_upstream_marker` ist bei uns
  `("eifel-joe","justchr")`, bei upstream `("justchr",)` — gleicher Testname, damit der
  nächste Merge darauf kollidiert statt still eine Seite zu nehmen. Hat funktioniert.

### Nächste Schritte (offen)
1. **Vier Grafana-Views** im Dashboard „Garten" (`grafana-uberblick/-effektivitaet/-wetter/-bilanz`)
   fragen InfluxDB weiter unter `sensor.smart_irrigation_*` ab. Altdaten bleiben, ab
   2026-09-08 abends schreibt HA unter dem neuen Namen → Kurven brechen ab. **Außerhalb
   von HA, braucht den User.** Angeboten: angepasste Flux-Abfragen formulieren.
2. **#128** wartet auf JustChrs Schließung.
3. Optional: Prod von v2026.09.14 auf v2026.09.15 (exakter Marker-Vergleich; für diese
   Anlage folgenlos, Neustart nötig).
4. Weiter offen aus früheren Sitzungen: Regen-Skip-Issue (war bis nach dem Umzug vertagt),
   Mid-Run-Ventil-Messung + `sequential`-Test für JustChr (witterungsabhängig),
   Durchsatz-Frage Kirschbaum, Hochbeet-Bodensonde tot seit 04.09.

### Werkzeuge / Befehle
- Tests: `./.venv/Scripts/python.exe -m pytest <pfad> -p _local_socket_unblock`
- Lint: `uvx black --check custom_components/irrigation_plus/` und `uvx ruff check …`
  (**`ruff` ist nicht im PATH**, `uvx` nötig — die Palette nennt es ohne Präfix)
- Frontend: `cd custom_components/irrigation_plus/frontend && npm ci && npm run build`,
  danach `git add -f …/dist/`
- **Bekannt-roter Test unter Windows:** `test_panel.py::test_async_register_panel_static_path_config`
  (Pfadtrenner) — fällt auf unverändertem upstream/master genauso, kein Regress.
- **Im Scratchpad und nach `/clear` WEG:** `fingerprint.py` (zwei Diagnostics-Dumps rein,
  feldweiser Diff der Zonen/Config/Zeitpläne raus) und `prod_before.json`. In ~10 min
  neu schreibbar; nur nötig, wenn wieder ein Umzug verglichen wird.

---

## 2026-09-02 — Produktiv-Rebuild v2026.09.01 + PR #114-Nachlese

### Stand (nur Verifiziertes)
- **production = `8fe9be15` = Fork-[v2026.09.01](https://github.com/Eifel-Joe/HAsmartirrigation/releases/tag/v2026.09.01)**,
  **0 behind** upstream/master (`388b02fa` = v2026.09.02). Fork-Delta **LEER** (nur
  Eifel-Joe-Branding: manifest owner/links, README-Heads-up, en.json-URL-Patch).
  CI grün (hassfest 26s + HACS Action 46s), Release + ZIP-Asset Download **200**.
  Backup lokal `backup/production-pre-v2026.09.01` = `9b2746ab`.
- **Rebuild-Rezept sauber durchgezogen** (Memory `hasi-production-on-upstream`, neuer
  v09.01-Eintrag): von upstream/master gebaut, Branding via
  `git checkout production -- README.md manifest.json`, Versionen SYNCHRON v2026.09.01
  (manifest+const mit `v`, package ohne), en.json 4→0 github-URLs, dist Node-24
  (nur Versions-String). Alle Gates belegt: black ✓, ruff ✓, 0-behind ✓, dist=09.01 ✓.
- **PR [#114](https://github.com/JustChr/HAsmartirrigation/pull/114) (i18n flow-advisory) GEMERGT** (`6e25eeed`, upstream v09.02).
  JustChr bat VOR dem Merge um einen Regressions-Pin, den wir **nicht** lieferten →
  er schrieb ihn selbst (`60e15ecd`, beide Strings, mutation-getestet). Entschuldigung +
  Live-Test-Zusage auf #114 gepostet ([issuecomment-5516439077](https://github.com/JustChr/HAsmartirrigation/pull/114#issuecomment-5516439077)).
- **Prozess-Schutz gegen genau diese Lücke verankert:** Skill `pr-workflow` §3a
  (Regressions-Pin-Check vor `gh pr create`) + §6 (Reviewer-Test-Bitte vor Merge liefern)
  + Memory `regression-pin-on-removals`.
- **Design-Historie:** observed-flow-credit Spec+Plan verifiziert **bereits** in
  `archive/design-history` (`d0730a6f`, inhaltsgleich, nur CRLF). Untracked-Reste +
  überholte alte SESSION-STAND.md aufgeräumt. Arbeitsbaum sauber, auf Branch `production`.

### Fallen (haben Zeit gekostet)
- **🔴 Tag-Kollision:** JustChr hat `v2026.09.01` UND `v2026.09.02` als eigene Tags.
  `git fetch upstream` zieht sie → lokaler Tag `v2026.09.01` zeigt auf JustChrs Commit,
  nicht auf production. **ZIP IMMER aus dem SHA** `git archive 8fe9be15:…`, Release via
  `gh release create --target production`, lokalen Tag danach `git tag -f v2026.09.01 8fe9be15`.
  ZIP VOR Upload verifiziert: **en.json 0 URLs = eindeutiger Fork-Beleg** (JustChrs Tag hätte 4).
- **`ruff` nicht im PATH** → `uvx ruff check custom_components/smart_irrigation/` (wie black via uvx).
- **MSYS:** Process-Substitution (`<(…)`) scheitert (`/proc/…/fd`), `grep -c` == 0 bricht
  `&&`-Ketten ab. Für Diffs Temp-Dateien nutzen, `diff --strip-trailing-cr` gegen CRLF-Rauschen.
- **Cloud-Monitoring nicht möglich:** die `schedule`-Skill erzeugt Cloud-Agenten ohne Route
  ins LAN → erreichen HA-Prod (192.168.20.2) nicht, HA-MCP ist lokal (kein claude.ai-Connector).
  → Kirschlorbeer-Überwachung bleibt ToDo/Memory-basiert.

### Nächste Schritte (offen)
1. **User:** HA-Prod auf **v2026.09.01** updaten (HACS) + Neustart (Freigabe nötig,
   Memory `ha-no-auto-restart`) → bringt #111 (measured-flow/Ceiling) + #114 live.
2. **Kirschlorbeer Flow-Cal Live-Test** (Zusage an JustChr #114, Memory
   `hasi-kirschlorbeer-flow-cal-livetest`): **BLOCKER Witterung** — seit >1 Woche keine
   Bewässerung (Stand 2026-09-02). Sobald wieder Läufe kommen: ≥3 Läufe mit Flussmessung
   sammeln → prüfen (a) bleibt der Kalibrier-Hinweis auf korrekt konfigurierter Zone still,
   (b) reale Rate vs 300 s-Short-Run-Schwelle (`OBSERVED_FLOW_CAL_MIN_SECONDS`) → Ergebnis
   auf #114 zurückmelden. Voraussetzung: Schritt 1 (Prod muss v09.01-Code tragen).
3. **Regel P1** für neue Features weiterhin beachten: Spec+Plan ENTSTEHEN lassen und
   VOR Branch-Löschung nach `archive/design-history` schieben (Memory `preserve-design-docs-archive-branch`).

### Kontext
- upstream v2026.09.02 ist bei JustChr ein **Pre-Release/Beta**; unser Fork-Release v09.01
  ist ein **volles** Release (Fork-Versionsschema folgt dem Kalender, unabhängig von upstream).
- Fork-Delta leer — alle Eigenentwicklungen sind upstream (#47/#54/#59/#60/#70/#71/#73/#79/#95/#111/#114).

### Empfohlene Skills (Folgesitzung)
- `task-loop`, `pr-workflow`, `superpowers:requesting-code-review`
- Produktiv-Rebuild: Memory `hasi-production-on-upstream`; Test-Env: `hasi-local-test-env-rebuild`
- Live: MCP-Präfixe `mcp__HA-Test__` / `mcp__HA-Prod__`, Memory `verify-ha-system`
