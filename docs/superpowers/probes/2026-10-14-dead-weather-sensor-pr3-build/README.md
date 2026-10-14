# Bau PR 3 „stummer Wettersensor“ (Stundenpfad und Live-Schätzung) — Protokoll 2026-10-14

Bau des Plans `docs/superpowers/plans/2026-10-14-dead-weather-sensor-pr3.md` (Tasks 0–10), subagent-driven:
je Task Auftragsdatei (`briefs/header.md` + `briefs/notes/tN.md` + Plantext des Tasks), Implementer Sonnet,
Spec-Check per Skript, Task-Review Sonnet, Abschluss-Review Opus. Spec:
`docs/superpowers/specs/2026-10-14-dead-weather-sensor-pr3-design.md`.

- Worktree `D:\Entwicklung\HASI\issue8-pr3-work\wt`, Branch `feat/pause-silent-sensor-hourly-live` (lokal,
  ungepusht — gestapelt auf PR 2, wird nach dessen Merge per `rebase --onto` umgesetzt), Basis `6fa424e8`
  (Kopf von upstream PR 197). 14 Commits `d72c05d1` … `c21478c8`:
  - Tasks 1–9 je ein Commit (`d72c05d1`, `0d976997`, `74d7192a`, `1160abc5`, `60ac780b`, `f1b9a87d`, `2c374da9`,
    `ca0955f8`, `e5d184e3`);
  - Fix-Runde Task 7 `08728aa7`: im Tagesform-Spiegel wird der Anteil vor der Prognose bestimmt — bei Anteil 0 und
    fehlender spiegelbarer Prognose fiel die Kette sonst zum Wetterdienst, während der Commit 0 bucht (Spec G9);
  - Fix-Runde Task 9 `e62b046f`: Test hält die freigegebene Abweichung „ungedrosselte Neuberechnung“ fest;
  - Abschluss-Fix-Welle `08fed661` (Pins der Verdrahtungen), `1b0dfee0` (Test-Schärfungen), `c21478c8`
    (Kommentare/Docstrings, Umbenennung `dt_hours` → `measured_hours`). Produktionslogik unverändert.
- **Spec-Check** (`tools/spec_check.py`): Diff jedes Tasks je Datei gleich dem Diff des Probe-Commits desselben Tasks
  (Probe-Kette `d4817574` … `8bd004a9`, deren Range-Diff byte-gleich
  `probes/2026-10-14-dead-weather-sensor-pr3-plan/probe-2026-10-14.patch` ist). Alle 9 PASS; Bäume T1–T7 == Probe,
  ab T8 nur um die Zeilen der T7-Fix-Runde verschieden.
- **Je Task** `tools/task_compare.sh` auf den betroffenen Testdateien (Namensvergleich gegen die Baseline dieser Dateien),
  Ergebnisse in `reports/task-N-report.md`. **Volle Suite** (`tools/suite_compare.sh`, `suite/compare-*.txt`):
  Baseline `6fa424e8` 7 failed / 3925 passed / 9 skipped / 466 errors (`suite/names-base-wt.txt`, gleich der
  Probe-Baseline) → nach Teil A (T5) 7 / 3970 / 9 / 474 → nach T9 + Fix-Runden 7 / 3990 / 9 / 488 → Endstand `c21478c8`
  **7 / 4001 / 9 / 496**. FAILED-Menge immer gleich; es entfallen nur die zwei in Task 5 umbenannten Namen; alle neuen
  ERROR sind Teardown „Lingering timer“ von Tests mit echtem Koordinator (Klassifizierer `tools/classify_new_errors.py`,
  UNEXPECTED 0). Gegen den Probe-Endstand (3989/487) nur der Test der T7-Fix-Runde mehr; die Fix-Welle +11.
- **Mutationen** (`tools/mutate-pr3.py`, 37 Anker): auf `e62b046f` **37/37 getötet**, jede vom im Plan genannten Killer,
  jede Quelle sha256-gleich zurück (`suite/mutate-wt.txt`, `suite/mutations-wt.json`). Auf dem Endstand `c21478c8`
  (Anker 37/37 je genau einmal) lief zum Zeitpunkt dieses Protokolls ein zweiter Lauf — Ergebnis folgt mit dem
  nächsten Archiv-Stand.
- **Lint:** black (26.10.1) sauber, ruff 0.16.10 sauber (uv-Cache auf D:, weil C: voll war); Eigenbezüge in Diff und
  Commit-Messages 0.
- **Reviews:** `reports/review-tN-report.md` je Task, Nach-Reviews der Fix-Runden `reports/rereview-*-report.md`.
  Abschluss-Review `final-review-report.md`: „bereit mit Fixes“, 0 Critical, 1 Important (Spec verlangt Tests, die
  Verdrahtungen festhalten), 13 Minor; Triage der zurückgestellten Punkte `final-review-deferred.md`. Fix-Welle
  `reports/final-fix-report.md` (jeder Pin rot unter seiner Mutation belegt), Nach-Review 18/18 erledigt, 4 Minor
  geparkt (siehe Ledger).
- **Ledger** `progress.md`: Konflikt-Scan, alle Rulings mit Begründung und Kosten, geparkte Befunde.
- **Abweichung von der Spec, nicht im Spec-Text nachgezogen:** §3.4/G11 nennen
  `async_refresh_zone_estimates_throttled`; gebaut und vom User freigegeben ist die ungedrosselte Fassung (Plan,
  Selbstprüfung), seit `e62b046f` per Test gehalten.
- Umgebung: C: lief während des Baus voll; ab Task 8 gehen Temp und uv-Cache aller Läufe nach
  `D:\Entwicklung\HASI\issue8-pr3-work\`.
