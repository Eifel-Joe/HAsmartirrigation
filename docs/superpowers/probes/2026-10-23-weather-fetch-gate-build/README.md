# Wetter-Clients: ein Abruf, Pause nach dem Fehlschlag — Bau-Belege

Spec `docs/superpowers/specs/2026-10-23-weather-client-fetch-gate-design.md`, Plan
`docs/superpowers/plans/2026-10-23-weather-client-fetch-gate.md`. PR an upstream:
[JustChr#199](https://github.com/JustChr/HAsmartirrigation/pull/199) (2026-10-28), Branch
`fix/weather-client-fetch-gate`, Kopf `9455f2f5`, Basis upstream `c46c41fc`.

Herkunft: Arbeitsordner `D:\Entwicklung\HASI\issue89-work\` — `sdd\` → `sdd/`, `probe\` → hier, `baseline\` → nur
Namenslisten und Schlusszeilen (die vollen Suite-Ausgaben, je ~1,4 MB, blieben lokal), `live\` →
`../2026-10-23-weather-fetch-gate-live/`, PR-Texte → `../2026-10-28-weather-fetch-gate-pr/`.

- `sdd/progress.md` — Ledger: alle Festlegungen, Befunde, Mutationen, Suite-Läufe; maßgeblich vor den Checkboxen im Plan.
- `sdd/task-*-brief.md` / `task-*-report.md` — Auftrag und Bericht je Task; `review-*.diff` — die Pakete der Reviews.
- `baseline/names-c46c41fc.txt` = `names-9455f2f5.txt` (byte-gleich): FAILED/ERROR-Namen, Filter `^(FAILED|ERROR) tests/`.
- `baseline/suite-summaries.txt` — Schlusszeile je Lauf; `branch` = `48945139`, `final` = `2ba2f05a`.
- `probe_cases.py` — Probe aus dem Plan (Uhr-Steuerung in den Tests).

**SHAs im Ledger und in den Review-Diffs:** Die Commit-Texte von Task 2–7 wurden vor dem Push umformuliert, die Bäume
sind identisch (geprüft per `%T`). Zuordnung alt → gepusht: `7b5454b6` → `436d66af`, `cb6c83ed` → `6a1ea83a`,
`49a5a3e8` → `bfe1a9ea`, `79d1569f` → `efcdf823`, `48945139` → `2caf6f1e`, `bf5579fd` → `2ba2f05a`. `06173427` war der
lokale Vorgänger von `9455f2f5` (4/2 Zeilen im Wartenden-Test). `9a87d9b1` blieb unverändert.
