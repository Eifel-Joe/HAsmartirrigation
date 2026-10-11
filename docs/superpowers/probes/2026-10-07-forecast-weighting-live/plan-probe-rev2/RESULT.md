# Probelauf Plan Revision 2 (2026-10-11), Eifel-Joe#61

Plan: `HAsmartirrigation/docs/superpowers/plans/2026-10-07-forecast-weighting-live-verification.md`, Abschnitt
„Revision 2“. Codeblöcke wörtlich aus dem Plan (Python-Blöcke des Rev.-2-Abschnitts, per Skript extrahiert),
Interpreter `HAsmartirrigation/.venv` (Python 3.12), `-p _local_socket_unblock`, Ordner `plan-probe-rev2/`.

- **Task 3a Step 2 RED:** `ModuleNotFoundError: No module named 'scout'` (Collection-Fehler).
- **Task 3a Step 4 GREEN:** `6 passed`.
- **Task 3a Step 5 Mutationen:** (a) ohne `abs` → `1 failed, 5 passed` (`test_more_rain_tomorrow…`);
  (b) ohne Mindestregen → `3 failed, 3 passed` (u. a. `test_rain_today…`, Reserve 3.5 statt 2.0);
  (c) ohne T1 → `1 failed, 5 passed` (`test_without_a_t1…`). Alle getötet, je vom vorgesehenen Test.
- **Task 3a Step 6 (live, 09:17 UTC):** Open-Meteo `/v1/gfs` antwortet; `rows=96`, erster Stempel 2026-10-11 00:00 UTC,
  letzter 2026-10-14 23:00 UTC (Review Focus 1 erfüllt). `ok=True`: Brest 48.39/-4.49 (Reserve 2.70), Rostock
  54.09/12.10 (2.17), Goeteborg 57.71/11.97 (0.45); übrige 24 `ok=False`. Ausgabe: `scout-probe-0917.txt`.
  Gilt nur für diesen Zeitpunkt — bei der Ausführung neu laufen lassen.
- **Baustein X (HA-Test, nur lesend, `CUTOFF` 09:20:00):** läuft in der Sandbox ohne Änderung. 19 Dokumente (Zyklus
  09:20:42), jedes 6 Stücke, `n_hourly` 168, `steps_ok`, `has_daily`, `n_precip` 177, `masked` true,
  `key_pattern` false; **eine** `series`-Nummer für alle 19 (Schub-Identität im Normalfall gegeben). Prüfsumme
  `[168, 301056436800, 0]` (Regen 0 am Heimatort). `window_first` 07:26:16 — Fenster reichte über 3 h zurück.
- Nicht probegelaufen (schreibend auf HA-Test): Task 4R Steps 1–3/5–7, 5R, 10R.
