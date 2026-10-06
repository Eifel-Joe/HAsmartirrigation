# Probelauf des Plans zu Eifel-Joe#11 (2026-10-06)

Gegen `upstream/master` `7001c754`, im Wegwerf-Worktree `D:\Entwicklung\HASI\issue11-work\probe-wt`
(Plan: `docs/superpowers/plans/2026-10-06-device-registry-2027-8.md`).

| Datei | Inhalt |
|---|---|
| `apply_plan_task.py` | wendet die Blöcke einer Plan-Task wörtlich an („Lege an“, „Ersetze … durch“, „Hänge an“) |
| `run_suite.sh` | volle Suite mit Vergleich der FAILED/ERROR-Namen gegen die Baseline |
| `mutate.py` | 16 Mutationen, geprüft gegen `tests/test_device_registry_compat.py` |
| `run-base.log` | Baseline auf `7001c754`: `7 failed, 3783 passed, 9 skipped, 415 errors` (422 Namen) |
| `run-probe.log` | Probe-Kopf `290892af`: `7 failed, 3795 passed, 9 skipped, 417 errors`; +2 Namen (teardown) |
| `mutate-probe.txt` | 16/16 KILLED, je Mutation die tötenden Tests |
| `probe-2026-10-06.patch` | getesteter Stand, `git diff 7001c754..290892af` |

Die Pfade in den Werkzeugen zeigen auf `D:\Entwicklung\HASI\issue11-work\`. Die lokalen teardown-ERRORs der zwei
Setup-Tests („Lingering timer“, 300-s-Takt der Sensor-Lebendprüfung) sind Vorbestand der Windows-Umgebung.
