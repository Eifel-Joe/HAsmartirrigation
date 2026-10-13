# Auftrag — Kontext und Regeln (gilt für jeden Task dieses Plans)

## Kontext

- Projekt: Home-Assistant-Integration `irrigation_plus` (Fork von „Smart Irrigation“). Dieser Branch baut **PR 2 von 3**
  zum Thema „stummer Wettersensor“: Eine Sensorgruppe mit der Einstellung *pausieren* bucht für die Zeit, in der ein
  Sensor stumm war, nichts mehr — im Commit des Tagespfads, nur ohne Stundenrechnung. Jede Gruppe auf *behalten*
  rechnet und erklärt byte-identisch wie heute. PR 1 (Erkennung, Ausfall-Liste `sensor_outages`, Hinweis, Event) ist
  schon in der Basis.
- **Worktree:** `D:\Entwicklung\HASI\issue8-pr2-work\wt` (Git Bash: `/d/Entwicklung/HASI/issue8-pr2-work/wt`),
  Branch `feat/pause-silent-weather-sensor`, Basis `upstream/master` = `6a40e083`. Arbeite NUR dort.
- Plan (nur bei Bedarf, dein Task steht unten vollständig): `D:\Entwicklung\HASI\HAsmartirrigation\docs\superpowers\plans\2026-10-12-dead-weather-sensor-pr2.md`.
  Spec: `D:\Entwicklung\HASI\HAsmartirrigation\docs\superpowers\specs\2026-10-11-dead-weather-sensor-pr2-design.md`.
- Der Plan wurde am 2026-10-12 auf derselben Basis wörtlich probegelaufen: alle Snippets liefen, jede RED/GREEN-Erwartung
  traf. **Setze die Snippets wörtlich ein** (Zeichen für Zeichen, inkl. Kommentare und Docstrings).

## Regeln

1. **TDD wie im Task beschrieben:** zuerst den Test schreiben, RED laufen lassen und die Ausgabe festhalten, dann den
   Code, dann GREEN. Die RED-/GREEN-Erwartungen des Tasks sind gemessen — weicht deine Beobachtung ab, STOP und als
   `DONE_WITH_CONCERNS`/`BLOCKED` melden, nichts „passend machen“.
2. **Testbefehl** (aus dem Worktree-Root, es gibt dort kein eigenes `.venv`):
   `TZ=UTC /d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest <pfad> -p _local_socket_unblock -q`
   Nur die im Task genannten Testdateien. **Die volle Suite NICHT laufen lassen** — die fährt der Controller nach
   deinem Commit mit Namensvergleich gegen die Baseline (parallele pytest-Läufe erzeugen auf diesem Rechner
   `WinError 10055`-Flakes).
3. **„Grün“ lokal:** Tests mit einem echten `SmartIrrigationCoordinator` enden hier zusätzlich mit
   `ERROR at teardown … Lingering timer after test` (lokaler Vorbestand der Windows-Test-Env, in CI sauber). RED/GREEN
   an der **Testphase** ablesen (`passed`/`failed`), nicht an `errors`. Jeder andere ERROR ist echt.
4. **Lint** nach jedem Code-Schritt, wie im Task genannt: `uvx black <dateien>` und
   `uvx ruff check custom_components/irrigation_plus/`. ruff 0.17.0 meldet **20 vorhandene `UP017`** in Dateien, die
   dieser Branch nicht anfasst (`forecast_window.py`, `weathermodules/*`) — die bleiben stehen. Prüfung:
   `uvx ruff check custom_components/irrigation_plus/ --output-format concise | grep -v UP017` muss bis auf die
   Zusammenfassungszeile leer sein.
5. **Commit:** genau die Commit-Message aus dem Task (englisch), mehrzeilig per Heredoc
   `git commit -F - <<'EOF' … EOF`. Letzte Zeile **genau**:
   `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>` (Vorgabe des Plans, auch wenn du ein anderes Modell bist).
   Gezielt stagen (`git add <dateien>`), kein `git add -A`/`git add .`.
6. **Keine Verweise** auf Fork-Issues (`Eifel-Joe#…`), Upstream-Issues (`JustChr#…`), Spec-/Plan-Kürzel
   („Task 4“, „spec §2“, „F1“), „PR 1/2/3“ in Code, Tests, Doku oder Commit-Messages — außer der Task diktiert den
   Wortlaut selbst.
7. **Verboten:** `git push`, `git stash`, `git reset --hard`, `git rebase`, jede schreibende `gh`-Aktion, jede
   Home-Assistant-/MCP-Aktion, Änderungen im Hauptbaum `D:\Entwicklung\HASI\HAsmartirrigation`. Keine Subagenten
   starten (auch keinen Reviewer — die Review kommt vom Controller).
8. **Arbeitskopie ist CRLF** (`core.autocrlf=true`), das Repo LF. Mit den Edit-/Write-Tools arbeiten; `git diff` darf
   nicht jede Zeile zeigen (falls doch: Zeilenenden prüfen und angleichen).
9. **Getesteter Stand als Schiedsrichter:** Scheitert ein Snippet trotzdem (Anker nicht gefunden, Syntax, Test rot nach
   dem Code, Lint, Build), gilt der im Probelauf getestete Stand. Den Commit dieses Tasks aus dem Probelauf nennt dir
   der Abschnitt „Hinweise“ unten; ansehen nur per `git -C /d/Entwicklung/HASI/issue8-pr2-work/wt show <sha> -- <pfad>`.
   **Nicht** cherry-picken, nicht auschecken, nicht kopieren, um TDD zu überspringen; jede Nutzung im Bericht nennen.
10. **Bericht** in die Datei, die dir der Controller nennt: was umgesetzt, RED (Befehl + relevante Ausgabe + warum
    erwartet), GREEN (Befehl + Ausgabe), Lint-Ausgabe, Commit-SHA, Abweichungen vom Plan (Step, was, warum).
    Antwort an den Controller danach kurz (≤ 15 Zeilen): Status `DONE | DONE_WITH_CONCERNS | BLOCKED | NEEDS_CONTEXT`,
    Commit(s), eine Zeile Testergebnis, Bedenken, Pfad des Berichts.

## Global Constraints des Plans (verbindlich)

- Basis `upstream/master` = `6a40e083`; alle Zeilenangaben dort, in `custom_components/irrigation_plus/`.
- Kein Store-Versionssprung (`STORAGE_VERSION = 14`, `STORAGE_MINOR_VERSION = 2` bleiben).
- Werte der Einstellung: genau `"keep"` und `"pause"`; Schlüssel `"on_silent_sensor"`; Hinweis-Schlüssel
  `"weather_sensor_stale_paused"`; Erklärungsschlüssel `module.calculation.explanation.sensor-outage` und
  `module.calculation.explanation.sensor-outage-share`.
- Sperre = `[start + 3 h, end)`, halboffen; offener Eintrag bis `now` des Commits.
- Mit `blocked=None` läuft in `aggregate_window`, `calculate_module` und den Aufzeichnungen kein neuer Code.
- Zeiten im Erklärungssatz `%Y-%m-%d %H:%M` auf HAs Uhr; Anteil in ganzen Prozent (`f"{share * 100:.0f}"`).
- Neue UI-Strings in allen 8 Sprachen (`de en es fr it nl no sk`), Platzhalter je Sprache gleich.
- Keine Verweise auf Fork-Issues, Spec-/Plan-Kürzel oder „PR 2/PR 3“ in Code, Tests, Doku, Commit-Messages.
- Lint nur `uvx black` + `uvx ruff check` auf `custom_components/irrigation_plus/` (ruff prüft auch die
  Import-Reihenfolge, Regel `I`).
- Uhr: Puffer-Stempel, Ausfall-Stempel, Wasserzeichen und `now` sind naiv auf HAs Uhr. In den Tests ist HAs Zone
  US/Pacific (autouse `hass`), die Prozesszone per `TZ=UTC` UTC. Die neuen Tests übergeben naive Zeiten direkt.

