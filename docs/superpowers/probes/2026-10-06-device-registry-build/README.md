# Bau des Plans „Geräte-Registry vor HA 2027.8“ (2026-10-06)

Branch `fix/device-registry-2027-8` im Worktree `D:\Entwicklung\HASI\issue11-work\wt`, Basis `7001c754`
(`upstream/master`). Plan: `docs/superpowers/plans/2026-10-06-device-registry-2027-8.md` — Tasks 0–6 freigegeben;
1b–5b sind Nachträge aus den Per-Task-Quality-Reviews (nicht Teil der Freigabe, je ein eigener Commit, Begründung im
Plan). Ablauf je Task: Implementer (Sonnet, Blöcke per `apply_plan_task.py`, RED → GREEN), mechanischer Spec-Check,
volle Suite mit Namensvergleich, Quality-Review (Sonnet), bei Befunden Nachtrag + Re-Review.

| Datei | Inhalt |
|---|---|
| `spec_check.py` | Spec-Check je Task: Baum == Probe-Commit desselben Tasks plus die Nachtrags-Blöcke (vom selben Werkzeug angewandt, byte-genau); nach dem letzten Task Baum == Probe-Endstand; Dateien == `git add`-Zeile; Message == Plan; keine eigenen Verweise; Baum sauber |
| `apply_plan_task.py` | wie im Plan-Probelauf, jetzt auch mit Task-Kennungen wie `1b` |
| `mutate.py` | 36 Mutationen (M01–M16 aus dem Plan, M17–M36 aus den Nachträgen), auch mehrteilige (M27) |
| `run_suite.sh` | volle Suite mit Namensvergleich gegen `names-base.txt` (Baseline `7001c754`) |
| `delta-1b.patch` … `delta-5b.patch` | der jeweilige Nachtrag, gegen den vorigen Probe-Endstand |
| `probe-2026-10-06-5b.patch` | getesteter Endstand (`git diff 7001c754..a9a8e834` im Wegwerf-Worktree); der Branch ist byte-gleich damit |
| `mutate-probe-1b.txt` … `-5b.txt` | Mutationsläufe auf dem jeweiligen Probe-Endstand (zuletzt 36/36 KILLED) |
| `suite-summaries.txt` | volle Suite nach jedem Task: Baseline `7 / 3783 / 9 / 415`, Endstand `7 / 3805 / 9 / 418` (+22 Tests, +3 teardown-ERRORs „Lingering timer“ der Setup-Tests; Namen sonst identisch) |
| `prompts/` | Auftrags-Kontext für die Implementer (`common.md`) und die Reviewer (`review-common.md`) |

Zwischenstand beim Anlegen (lokal, ungepusht): Branch-Kopf `08e5c576` (zehn Commits). Endprüfung (Task 6), finale
Mutationen auf dem Branch und Gesamt-Review folgen; Ergebnisse im Sitzungsstand.
