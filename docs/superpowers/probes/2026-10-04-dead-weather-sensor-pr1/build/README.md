# Stummer Wettersensor, PR 1 — Bau, Reviews, Live-Test (2026-10-04/05)

Ergänzt `../README.md` (Probelauf vom 2026-10-04). PR: [JustChr#190](https://github.com/JustChr/HAsmartirrigation/pull/190).

| Datei | Inhalt |
|---|---|
| `deviations.md` | Abweichungsprotokoll des Baus: jede Review-Bewertung (übernommen / abgelehnt, mit Beleg), User-Entscheidungen D1–D3, Fix-Runden A–C, E, F, Falten, Rebase auf v2026.10.04 |
| `final-review-opus.txt` | Abschluss-Review des ganzen PRs (Opus), wörtlich |
| `fixE.py`, `fixF.py` | Ersetzungslisten der Commits E und F; erzeugen Auftragstext und erwarteten Baum aus derselben Liste |
| `m1probe_run.py` | Probe zu Review-Punkt M1: welche Mutation der Neustart-Test über STOP/FINAL_WRITE fängt (und welche nicht) |
| `probeE_s0.py`, `probeF_m60.py` | Gegenproben am Endstand von E und F |
| `make_mutate5.py`, `probe_mutate5.py` | 60 Mutationen, jede gegen alle vier Testdateien |
| `mutate-F.txt`, `mutate-R.txt` | Ergebnisse vor und nach dem Rebase: 60/60, Killer-Mengen gleich |
| `fold.py`, `fold_check.py` | Falten der Task-Historie in vier Feature-Commits (Baum identisch), Prüfung jedes Zwischenstands |
| `names-base-bbf2.txt`, `names-R.txt` | Fehlernamen der Baseline `bbf2e151` (v2026.10.04) und des rebasten PRs — identisch (422) |
| `run_suite.sh` | Volle Suite mit Namensvergleich |
| `../livetest/L-pr1.md` | Live-Test auf HA-Test: alle fünf Schritte, beide Schreibweisen, `config_entry_id`-Zweig live |
