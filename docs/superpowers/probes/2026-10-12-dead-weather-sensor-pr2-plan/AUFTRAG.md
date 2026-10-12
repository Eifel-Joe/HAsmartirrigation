# Probelauf des Plans für PR 2 (stummer Wettersensor, Schnitt im Tagespfad)

Du bist ein Probeläufer. Du führst einen Implementierungsplan in einem **Wegwerf-Worktree** aus, um zu prüfen, ob seine
Code-Snippets und RED/GREEN-Erwartungen stimmen. Dein Ergebnis ist ein Bericht und ein Patch, kein Produkt.

## Quellen (zuerst lesen)

- Plan: `D:\Entwicklung\HASI\HAsmartirrigation\docs\superpowers\plans\2026-10-12-dead-weather-sensor-pr2.md`
- Spec: `D:\Entwicklung\HASI\HAsmartirrigation\docs\superpowers\specs\2026-10-11-dead-weather-sensor-pr2-design.md`

## Harte Grenzen

- **Nichts nach außen:** kein `git push`, keine `gh`-Aufrufe, die schreiben, keine Home-Assistant-Aufrufe (keine
  `mcp__HA-*`-Tools), keine Releases. Tasks 11 und 12 des Plans werden NICHT ausgeführt, ebenso nicht Task 10 Step 5
  (Review).
- **Nicht den Hauptbaum anfassen:** `D:\Entwicklung\HASI\HAsmartirrigation` bleibt unverändert (nur `git worktree add`
  von dort aus und Lesen). Kein `git stash`.
- Alles Temporäre unter `D:\Entwicklung\HASI\issue8-pr2-work\probe\`.

## Abweichungen vom Plan

- Worktree **nicht** `issue8-pr2-work\wt`, sondern `D:\Entwicklung\HASI\issue8-pr2-work\probe-wt`, Branch
  `probe/pr2-plan` (statt `feat/pause-silent-weather-sensor`). Basis `upstream/master` (erwartet `6a40e083`).
  `_local_socket_unblock.py` aus dem Hauptbaum hineinkopieren.
- Baseline-/Ergebnisdateien nach `D:\Entwicklung\HASI\issue8-pr2-work\probe\` statt `..\`.
- Testbefehl immer mit dem absoluten Interpreter:
  `TZ=UTC /d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest <pfad> -p _local_socket_unblock -q`
  aus dem Worktree-Root. Die volle Suite dauert lange: als Hintergrund-Befehl starten und die Ausgabedatei erst nach
  Laufende lesen.

## Vorgehen

1. Task 0 (Worktree, Baseline der vollen Suite mit Namensliste, `npm ci` + vitest).
2. Tasks 1 bis 9 der Reihe nach, **wörtlich** nach dem Plan: Test schreiben, RED laufen lassen, Code einsetzen, GREEN
   laufen lassen, Lint, Commit (lokal). Bei jedem Step festhalten: Stimmte die RED-Erwartung (welcher Fehler, wie viele
   Fälle)? Stimmte die GREEN-Erwartung (Anzahl)?
3. Scheitert ein Snippet (Syntax, falscher Anker, Test rot nach dem Code, Lint-Fehler, `npm run build` scheitert):
   **minimal** korrigieren, so dass die Absicht des Plans und der Spec erhalten bleibt, und die Abweichung
   protokollieren. Nie eine Erwartung „passend machen“, ohne zu verstehen, warum sie nicht stimmte. Ist eine
   Korrektur nicht klein oder ändert sie Verhalten gegenüber der Spec: STOP für diesen Task, protokollieren, mit dem
   nächsten unabhängigen Task weitermachen.
4. Task 10 Steps 1–4 und 6: Lint, volle Suite mit Namensvergleich gegen die Baseline, Frontend-Bau (dist danach
   unverändert?), Mutationen nach der Tabelle in Step 4 (Skript selbst schreiben, nach Vorbild
   `D:\Entwicklung\HASI\issue66-work\mutate.py`: Sicherung + sha256, Anker genau einmal, Timeout je Lauf, Rücksetzen
   prüfen), Grep auf eigene Bezüge.
5. Patch sichern: `git -C D:/Entwicklung/HASI/issue8-pr2-work/probe-wt diff upstream/master..HEAD > D:/Entwicklung/HASI/issue8-pr2-work/probe/probe-2026-10-12.patch`
   und `git log --oneline upstream/master..HEAD > .../probe/commits.txt`.

## Protokoll und Bericht

- `D:\Entwicklung\HASI\issue8-pr2-work\probe\deviations.md`: je Abweichung Task/Step, was im Plan stand, was
  passierte (Fehlerausgabe gekürzt), was du geändert hast, warum.
- `D:\Entwicklung\HASI\issue8-pr2-work\probe\steps.md`: je Task RED-/GREEN-Ergebnis mit Zahlen.
- `D:\Entwicklung\HASI\issue8-pr2-work\probe\mutate-pr2.txt`: Mutation, KILLED/SURVIVED, Killer.
- Abschlussbericht (deine Antwort, höchstens ~60 Zeilen): Baseline-Zahlen, Endzahlen der Suite, Namensvergleich,
  Zahl neuer Tests je Datei, alle Abweichungen kurz, Mutationsergebnis, offene Probleme. Keine Behauptung ohne die
  Ausgabe, die sie belegt; Zahlen aus den Dateien zitieren.
- Den Worktree **nicht** entfernen (er wird nach Durchsicht weggeräumt).
