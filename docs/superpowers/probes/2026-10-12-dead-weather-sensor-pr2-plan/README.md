# Probelauf des Plans für PR 2 (stummer Wettersensor, Schnitt im Tagespfad), 2026-10-12

Plan: `docs/superpowers/plans/2026-10-12-dead-weather-sensor-pr2.md`; Spec:
`docs/superpowers/specs/2026-10-11-dead-weather-sensor-pr2-design.md`.

Ein Sonnet-Agent hat die Tasks 0–9 und Task 10 Steps 1–4 und 6 wörtlich in einem Wegwerf-Worktree auf `6a40e083`
ausgeführt (Auftrag `AUFTRAG.md`); die Zahlen sind an den Ergebnisdateien nachgeprüft.

- `steps.md`: RED/GREEN je Task; `deviations.md`: Abweichungen D1–D7 (im Plan berichtigt, siehe Plankopf).
- `baseline.txt`, `names-baseline.txt`, `names-pr2.txt`: volle Suite vorher/nachher (7/3819/9/430 → 7/3903/9/458).
- `mutate-pr2.py`, `mutate-pr2.txt`: 22/22 Mutationen getötet.
- `probe-2026-10-12.patch`, `commits.txt`: der getestete Stand (36 Dateien, davon zwei Frontend-Bundles). Weicht ein
  Snippet des Plans vom Patch ab, gilt der Patch.

Nicht archiviert: die vollen Suite-Logs (je ~1,2 MB) und die Hilfsskripte des Agenten, mit denen er die Snippets
eingesetzt hat; der Patch enthält das Ergebnis.
