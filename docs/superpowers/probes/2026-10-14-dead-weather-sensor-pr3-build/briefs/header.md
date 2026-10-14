# Auftrag — Kontext und Regeln (gilt für jeden Task dieses Plans)

## Kontext

- Projekt: Home-Assistant-Integration `irrigation_plus` (Fork von „Smart Irrigation“). Dieser Branch baut den dritten
  Schritt zum Thema „stummer Wettersensor“: Eine Sensorgruppe mit der Einstellung *pausieren* bucht für die Zeit, in
  der ein Sensor stumm war, in **jeder** Rechenform nichts mehr — Commit in Tages- und Stundenform, nachgespielte
  Bilanz und Live-Schätzung. Jede Gruppe auf *behalten* rechnet, erklärt und schätzt byte-identisch wie heute. Erkennung,
  Ausfall-Liste `sensor_outages`, Einstellung `on_silent_sensor` und der Schnitt im Tagespfad (nur ohne
  Stundenrechnung) sind schon in der Basis.
- **Worktree:** `D:\Entwicklung\HASI\issue8-pr3-work\wt` (Git Bash: `/d/Entwicklung/HASI/issue8-pr3-work/wt`),
  Branch `feat/pause-silent-sensor-hourly-live`, Basis `6fa424e8`. Arbeite NUR dort.
- Plan (nur bei Bedarf, dein Task steht unten vollständig): `D:\Entwicklung\HASI\HAsmartirrigation\docs\superpowers\plans\2026-10-14-dead-weather-sensor-pr3.md`.
  Spec: `D:\Entwicklung\HASI\HAsmartirrigation\docs\superpowers\specs\2026-10-14-dead-weather-sensor-pr3-design.md`.
- Der Plan wurde am 2026-10-14 auf derselben Basis testgetrieben probegelaufen; **seine Code- und Testblöcke sind aus
  den Probe-Commits erzeugt**, nicht abgetippt. Jede RED-/GREEN-Erwartung ist gemessen. **Setze die Blöcke wörtlich
  ein** (Zeichen für Zeichen, inkl. Kommentare und Docstrings). `Create`-Blöcke sind die ganze Datei; `Modify`-Blöcke
  sind Diffs (`git show --unified=3`) — übertrage die `+`/`-`-Zeilen an die gezeigte Stelle.

## Regeln

1. **TDD wie im Task beschrieben:** zuerst die Tests (Step 1), RED laufen lassen und die Ausgabe festhalten, dann den
   Code, dann GREEN. Die RED-/GREEN-Erwartungen sind gemessen — weicht deine Beobachtung ab, STOP und als
   `DONE_WITH_CONCERNS`/`BLOCKED` melden, nichts „passend machen“.
2. **Testbefehl** (aus dem Worktree-Root, es gibt dort kein eigenes `.venv`) — **immer mit Temp auf D:**, nie auf dem
   Systemlaufwerk C: (pytest schreibt nach `TEMP`; C: ist voll und darf nicht weiter wachsen):
   `export TEMP=D:/Entwicklung/HASI/issue8-pr3-work/tmp TMP=D:/Entwicklung/HASI/issue8-pr3-work/tmp TMPDIR=D:/Entwicklung/HASI/issue8-pr3-work/tmp`
   im selben Befehlsblock vor jedem pytest-Lauf, dann
   `TZ=UTC /d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest <pfad> -p _local_socket_unblock -q`
   (`../task_compare.sh` setzt das selbst). Alle eigenen Ablagen (Rohausgaben, Hilfsskripte) nur unter
   `D:\Entwicklung\HASI\issue8-pr3-work\`, nie unter `C:\…` oder `/tmp`.
   Nur die im Task genannten Testdateien und das Skript aus Step „Prüfen“ (`../task_compare.sh tN …`). **Die volle
   Suite NICHT laufen lassen** — die fährt der Controller (parallele pytest-Läufe erzeugen auf diesem Rechner
   `WinError 10055`-Flakes). Starte pytest nie im Hintergrund und lass keinen Lauf zurück.
3. **„Grün“ lokal:** Tests mit einem echten `SmartIrrigationCoordinator` enden hier zusätzlich mit
   `ERROR at teardown … Lingering timer after test` (lokaler Vorbestand der Windows-Test-Env, in CI sauber). RED/GREEN
   an der **Testphase** ablesen (`passed`/`failed`), nicht an `errors`. Jeder andere ERROR ist echt.
4. **Lint** nach dem Code-Schritt, wie im Task genannt — im selben Befehlsblock vorher
   `export UV_CACHE_DIR=D:/Entwicklung/HASI/issue8-pr3-work/uv-cache` (der Standard-Cache liegt auf dem vollen C:,
   dort scheitert uvx mit `os error 112`): `uvx black custom_components/irrigation_plus/` und
   **`uvx ruff@0.16.10 check custom_components/irrigation_plus/`** (genau diese Version; ruff 0.17 meldet `UP017` in
   Dateien, die dieser Branch nicht anfasst). Beides muss sauber sein. Ändert black eine Datei, die dein Task nicht
   anfasst: STOP und melden.
5. **Commit:** genau die Commit-Message aus dem Task (englisch), mehrzeilig per Heredoc
   `git commit -F - <<'EOF' … EOF`. Letzte Zeile **genau**:
   `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>` (Vorgabe des Plans, auch wenn du ein anderes Modell bist).
   Gezielt stagen (`git add <dateien>` wie im Task), kein `git add -A`/`git add .`. Nach dem Commit:
   `git status --short` muss leer sein (bis auf die unversionierte `_local_socket_unblock.py`).
6. **Keine Verweise** auf Fork-Issues (`Eifel-Joe#…`), Upstream-Issues (`JustChr#…`), Spec-/Plan-Kürzel
   („Task 4“, „spec §2“, „G4“, „F2“), „PR 2/PR 3“ in Code, Tests, Doku oder Commit-Messages — außer der Task diktiert
   den Wortlaut selbst.
7. **Verboten:** `git push`, `git stash`, `git reset --hard`, `git rebase`, `git checkout <sha> -- …`, `git cherry-pick`,
   jede schreibende `gh`-Aktion, jede Home-Assistant-/MCP-Aktion, Änderungen im Hauptbaum
   `D:\Entwicklung\HASI\HAsmartirrigation` und im Probe-Worktree `issue8-pr3-work\probe-wt`. Keine Subagenten starten
   (auch keinen Reviewer — die Review kommt vom Controller).
8. **Arbeitskopie ist CRLF** (`core.autocrlf=true`), der Index LF. Mit den Edit-/Write-Tools arbeiten; `git diff --stat`
   darf nur die Zeilen deines Tasks zählen (zeigt er ganze Dateien als geändert: Zeilenenden prüfen und angleichen).
9. **Getesteter Stand als Schiedsrichter:** Scheitert ein Block trotzdem (Anker nicht gefunden, Syntax, Test rot nach
   dem Code, Lint, Build), gilt der im Probelauf getestete Stand. Den Probe-Commit dieses Tasks nennt dir der Abschnitt
   „Hinweise“; ansehen nur lesend per `git -C /d/Entwicklung/HASI/issue8-pr3-work/wt show <sha> -- <pfad>` bzw.
   `git -C … diff <vorgänger-sha> <sha> -- <pfad>`. **Nicht** cherry-picken, nicht auschecken, nicht kopieren, um TDD zu
   überspringen; jede Nutzung im Bericht nennen.
10. **Bericht** in die Datei, die dir der Controller nennt: was umgesetzt, RED (Befehl + relevante Ausgabe + warum
    erwartet), GREEN (Befehl + Ausgabe), Lint-Ausgabe, Ausgabe von `task_compare.sh`, Commit-SHA, Abweichungen vom
    Plan (Step, was, warum). Antwort an den Controller danach kurz (≤ 15 Zeilen): Status
    `DONE | DONE_WITH_CONCERNS | BLOCKED | NEEDS_CONTEXT`, Commit(s), eine Zeile Testergebnis, Bedenken, Pfad des
    Berichts.

## Global Constraints des Plans (verbindlich)

- Basis = `6fa424e8`; alle Zeilenangaben dort, in `custom_components/irrigation_plus/`.
- Kein Store-Versionssprung, kein neues Store-Feld; der Übertrag `_HourlyCarry` lebt nur im Speicher.
- Keine neuen Übersetzungsschlüssel. Panel-Hilfe `panels.mappings.cards.mapping.on-silent-sensor.help`: nur der letzte
  Satz fällt, in allen 8 Sprachen (`de en es fr it nl no sk`).
- Sperre = `[start + 3 h, end)`, halboffen; ein offener Eintrag sperrt bis zum `end` des Aufrufers (Commit: sein `now`;
  Live: `inputs["now"]`). Eine Pufferzeile genau auf diesem `end` zählt als gemessen.
- Pflichtmengen: Stundenform `HOURLY_ROW_REQUIRED` = Temperatur, Feuchte, Wind, Sonne; Tagesform
  `_REQUIRED_SENSOR_FIELDS` aus der Basis; ausgegeben von `required_sensor_fields(module_name, *, hourly=False)`.
- Mit `blocked=None`, `blocked={}` oder Sperren nur fremder Felder laufen `build_hourly_rows`, `build_substeps`,
  `hourly_eto_priced`, `eto_hourly_series` und die Live-Leser wie bisher (Tests vergleichen mit `==`).
- Keine Verweise auf Fork-Issues, Spec-/Plan-Kürzel oder „PR 2/PR 3“ in Code, Tests, Doku, Commit-Messages.
- Lint nur `uvx black` und `uvx ruff@0.16.10 check` auf `custom_components/irrigation_plus/`.
- Uhr: Puffer-, Ausfall- und Fensterstempel sind naiv auf HAs Uhr; die neuen Tests übergeben naive Zeiten direkt
  (`now=`) oder nutzen die Fixtures von `tests/test_live_estimate_replayed_balance.py`.

