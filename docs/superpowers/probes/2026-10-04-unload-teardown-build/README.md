# Eifel-Joe#9 — Bau-Belege (2026-10-04)

Branch `fix/unload-self-closing-handles`, 12 Commits auf `e9c79ec4`, Kopf `ab3eb45f`, upstream als JustChr#189.
Spec und Plan: `docs/superpowers/specs/2026-10-03-unload-self-closing-teardown-design.md`,
`docs/superpowers/plans/2026-10-03-unload-self-closing-teardown.md`.

| Datei | Was |
|---|---|
| `final_mutate.py` | Mutations-Treiber über den Endstand: 53 Varianten (Matrix 1–38 des Plans + 39–53 aus den Reviews), je mit benanntem Killer, Timeout, Wiederherstellung aus dem Speicher |
| `mutate-final-53.txt`, `mutate-final.json` | Ergebnis: 53/53 getötet, jede Zeile mit Killer und Lauf-Bilanz |
| `spec_check.py` | Spec-Check je Commit: Blob genau = Basis + Plan-Operationen, Testdatei = Folge der Plan-Blöcke, Commit-Message |
| `verify_task.py` | Vormessung im Wegwerf-Worktree vor jedem Dispatch: Stand nach Commit N, RED-Seite, Mutanten |
| `names-baseline.txt`, `names-final.txt` | FAILED/ERROR-Namen der vollen Suite auf `e9c79ec4` und auf `ab3eb45f` (je 422, identisch; Filter `^(FAILED|ERROR) tests`) — die Windows-Altlasten der gepinnten HA |

Volle Suite auf `ab3eb45f`: 7 failed / 3667 passed / 9 skipped / 415 errors, +49 Tests gegen die Basis. Der
Produktiv-Rebuild `4ebd458c` (Pre-Release v2026.10.04b1) maß 7/3676/9/415 mit denselben 422 Namen.

Der Live-Test liegt nebenan in `../2026-10-04-unload-teardown-live/`.
