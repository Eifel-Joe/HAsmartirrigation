# Eifel-Joe#10 — Bau des Saison-Ausblick-Fixes (2026-10-05)

Umsetzung des Plans `docs/superpowers/plans/2026-10-05-seasonal-outlook.md` (Tasks 0–10, subagent-driven) bis zum PR
[JustChr#191](https://github.com/JustChr/HAsmartirrigation/pull/191). Branch `fix/seasonal-outlook` = 9 Commits auf
`bbf2e151` (v2026.10.04), Kopf beim PR `34633730`. Live-Beleg: `../2026-10-05-seasonal-outlook-live/L-calendar.md`.

## Ablauf je Task

1. Implementer (Sonnet) bekommt eine kuratierte Auftragsdatei (`prompts/tN-full.md`, gebaut von `make_prompts.py` aus
   `prompts/common.md` + Plantext + gemessenen Erwartungen) und bringt die Plan-Blöcke wörtlich per
   `apply_plan_task.py` auf (Tests → RED → Code → GREEN), lintet, committet.
2. `spec_check.py N`: Commit-Stand byte-genau = Basis + Plan-Blöcke + Abweichungs-Blöcke der Tasks 1..N; Commit-Zahl,
   Messages, sauberer Baum, keine eigenen Verweise; ab Task 8 Bundles, nach Task 9 alles gegen den Probe-Patch.
3. Volle Suite + `expect_names.py`: genau die erwarteten neuen teardown-Namen, nichts weg.
4. Quality-Review (Sonnet, `prompts/review-common.md`, nur lesend), Befunde geprüft und als Blöcke in
   `deviations.md` übernommen oder mit Grund abgelehnt; Implementer amendet; `mutate.py` auf dem Stand; Nachprüfung.
5. Abschluss-Review des ganzen Branches (Opus, `prompts/final-review.md`) → Fixups per `git commit --fixup` /
   `--fixup=reword:` (`reword_editor.py`) + `git rebase --autosquash` (ohne `-i`; `MSYS2_ENV_CONV_EXCL=GIT_EDITOR`).

## Dateien

- `deviations.md` — jede Abweichung vom Plan mit Befund, Prüfung und Grund (Tasks 1–9, Abschluss-Review,
  User-Entscheidung zur deutschen Dienstbeschreibung); abgelehnte Review-Punkte mit Begründung.
- `final-review-carry.md` — Punkte für Abschluss-Review, Live-Test und PR-Text; Nebenbefunde.
- `apply_plan_task.py`, `spec_check.py`, `expect_names.py`, `mutate.py` (40 Mutationen), `reword_editor.py`,
  `make_prompts.py` — die Werkzeuge (brauchen `probe_plan.py` aus `../2026-10-05-seasonal-outlook/`).
- `mutate-final3.txt` — 40/40 getötet am PR-Kopf `34633730`.
- `names-base.txt` (Baseline `bbf2e151`, 422 Namen) und `names-final3.txt` (Kopf `ec70de5f`, 434 Namen: +12 neue
  Kalender-Tests am Koordinator-Fixture, lokal mit teardown-ERROR „Lingering timer“).
- `prompts/` — Auftrags- und Review-Vorlagen.
