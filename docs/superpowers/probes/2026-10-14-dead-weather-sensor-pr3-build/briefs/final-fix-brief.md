# Abschluss-Fix-Welle — Auftrag

Branch `feat/pause-silent-sensor-hourly-live`, Worktree `D:\Entwicklung\HASI\issue8-pr3-work\wt` (Git Bash
`/d/Entwicklung/HASI/issue8-pr3-work/wt`), Kopf `e62b046f`. Alle Tasks des Plans sind gebaut und einzeln reviewt; das
Abschluss-Review (Opus) urteilt „bereit mit Fixes“: 0 Critical, 1 Important (fehlende Tests, die die Spec verlangt),
13 Minor. **Die Produktionslogik ändert sich nicht.** Du schreibst Tests, berichtigst Kommentare/Docstrings und benennst
einen Parameter um.

## Die Befunde — Wortlaut, Fix-Vorschläge, genaue Testnamen

Lies **zuerst** `D:\Entwicklung\HASI\issue8-pr3-work\sdd\final-review-report.md`, Abschnitte „Important“ (I1 mit den
Tests **A-Commit, A-Live, B, C, D**) und „Minor“ (**M1–M13**). Das ist deine Anforderungsliste; die dort genannten
Testnamen, Aufbauten und Erwartungen gelten. Zeilennummern beziehen sich auf `e62b046f`.

Der Controller hat entschieden — umzusetzen ist **alles**: I1 (A-Commit, A-Live, B, C, D) und M1–M13, mit diesen
Präzisierungen:
- **M4:** Parameter `dt_hours` → `measured_hours` in `_weights_from_hourly_et` (weather_aggregate.py ~1354) inkl. aller
  Aufrufer und des Kommentars „measured time within the hour“. Reine Umbenennung, kein Verhaltenswechsel.
- **M7:** Der umgedrehte Test zieht in eine eigene Klasse (z. B. `TestTheHourlySwitchDoesNotDecide`); Testfunktionsname
  bleibt.
- **M2:** Kommentar und Docstring in `_daily_mirror_et` berichtigen (Wortlaut-Vorschlag im Bericht). Die Commit-Message
  von `08728aa7` bleibt (kein amend, kein rebase).
- Fallen Fixture-Details anders aus als im Bericht skizziert (z. B. wie `inputs` ohne Stundenprognose gebaut werden),
  nimm die vorhandenen Helfer der jeweiligen Testdatei; Ziel und Erwartung des Tests sind maßgeblich, nicht die Skizze.
  Jede Abweichung im Bericht nennen.

## Regeln

1. **Pins mit Beleg:** Jeder neue oder verschärfte Test, der eine Verdrahtung oder Entscheidung festnageln soll
   (A-Commit, A-Live, B, C, D, M5-Test, M8, M10, M11, M12), muss einmal **rot** werden unter einer vorübergehenden
   Probe-Mutation genau dieser Verdrahtung (Beispiele im Bericht unter „Fängt: …“, z. B. `required=()`,
   `blocked=` weglassen). Vorgehen je Pin: Test schreiben → grün auf dem jetzigen Code → Mutation per Edit-Werkzeug
   setzen → derselbe Test rot (Ausgabe festhalten) → Mutation per Edit-Werkzeug exakt zurücknehmen →
   `git diff --quiet -- <produktionsdatei> && echo restored` (vor dem Commit der Kommentar-Änderungen an dieser Datei
   prüfen; danach gegen den Stand vor der Mutation per `sha256sum` vergleichen). Kein `git stash`, kein `git checkout`.
   Ein Pin, der unter seiner Mutation grün bleibt, ist kein Pin: dann den Test schärfen oder als offen melden.
2. **Mutationsanker:** Die 37 Anker des Mutationslaufs müssen danach weiter je genau einmal stehen. Prüfen am Ende:
   `cd /d/Entwicklung/HASI/issue8-pr3-work && MUT_CHECK=1 /d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -I mutate-pr3.py wt mutations-check.json | grep -c "anchor count 1 "`
   → `37`. Ändere keine Codezeile, die nicht Kommentar/Docstring/M4-Umbenennung ist.
3. **Tests laufen lassen:** nur die betroffenen Testdateien, immer mit Temp auf D: im selben Befehlsblock:
   `export TEMP=D:/Entwicklung/HASI/issue8-pr3-work/tmp TMP=D:/Entwicklung/HASI/issue8-pr3-work/tmp TMPDIR=D:/Entwicklung/HASI/issue8-pr3-work/tmp`
   dann `TZ=UTC /d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest <pfade> -p _local_socket_unblock -q`.
   Tests mit echtem Koordinator enden lokal mit Teardown-ERROR „Lingering timer“ (Vorbestand) — an `passed`/`failed`
   ablesen. **Keine volle Suite** (fährt der Controller). Zum Schluss:
   `../task_compare.sh tfix $(ls tests/test_live_estimate*.py tests/test_silent_sensor*.py tests/test_sensor_liveness*.py tests/test_hourly_rows_blocked.py tests/test_substeps_blocked.py tests/test_next_irrigation*.py)`
   → keine neuen FAILED, keine Baseline-Namen weg außer den zwei bekannten (plus ggf. dem durch M7 verschobenen, falls er
   in der Baseline stand — dann im Bericht nennen).
4. **Lint:** `export UV_CACHE_DIR=D:/Entwicklung/HASI/issue8-pr3-work/uv-cache` im selben Befehlsblock, dann
   `uvx black custom_components/irrigation_plus/` und `uvx ruff@0.16.10 check custom_components/irrigation_plus/` →
   sauber; ändert black eine Datei außerhalb deiner Änderungen: STOP und melden.
5. **Nichts auf C:** keine Ablage unter `C:\…`, `/tmp` oder per `| tee` dorthin. Rohausgaben nach
   `D:\Entwicklung\HASI\issue8-pr3-work\sdd\fix\` (anlegen).
6. **Commits** (neue Commits, kein amend), gezielt stagen, englische Messages mit WAS und WARUM, ohne Verweise auf
   Fork-Issues (`Eifel-Joe#…`), Upstream-Nummern (`JustChr#…`), Spec-/Plan-Kürzel (`G11`, `Task N`, „PR 2/3“,
   „I1“, „M4“), letzte Zeile genau `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`; mehrzeilig per
   `git commit -F - <<'EOF' … EOF`. Gliederung:
   1. `test(...)`: die Pins aus I1 (A-Commit, A-Live, B, C, D) — WARUM: ohne sie bemerkte kein Test, wenn eine Sperre
      oder Pflichtmenge einen Leser nicht erreicht.
   2. `test(...)`: die übrigen Test-Schärfungen (M5-Test, M7, M8, M9, M10, M11, M12).
   3. `docs(...)` oder `refactor(...)`: Kommentare/Docstrings (M1, M2, M3, M5-Docstring, M6, M10-Docstring, M13) und die
      M4-Umbenennung.
   Danach `git status --short` leer (bis auf `_local_socket_unblock.py`).
7. **Verboten:** `git push`, `git stash`, `git reset`, `git rebase`, `git checkout`, `git cherry-pick`, schreibende
   `gh`-Aktionen, HA-/MCP-Aktionen, Änderungen außerhalb des Worktrees (außer `sdd\fix\`). Keine Subagenten.

## Bericht

`D:\Entwicklung\HASI\issue8-pr3-work\sdd\final-fix-report.md`: je Befund (I1-A … I1-D, M1 … M13) was geändert, Test
(Name), GREEN, RED unter welcher Mutation (Befehl + Ausgabe, Beleg `restored`), Abweichungen vom Bericht; dann Lint,
Anker-Check (`37`), `task_compare`-Ausgabe, Commit-SHAs mit Messages. Antwort an den Controller kurz (≤ 20 Zeilen):
Status, Commits, je Befund eine Zeile (erledigt/offen), Testergebnis, Bedenken, Pfad.
