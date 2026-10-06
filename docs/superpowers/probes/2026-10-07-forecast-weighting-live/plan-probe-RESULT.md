# Probelauf des Plans 2026-10-07 (Tasks 0–2), Eifel-Joe#61

Plan: `HAsmartirrigation/docs/superpowers/plans/2026-10-07-forecast-weighting-live-verification.md`
Codeblöcke wörtlich aus dem Plan entnommen (die ersten drei ```python-Blöcke), Interpreter
`HAsmartirrigation/.venv` (Python 3.12, HA < 2025.5), `-p _local_socket_unblock`.

- Task 0 echt ausgeführt: `upstream/master` = `6a40e083`; `git archive 6a40e083 custom_components` nach
  `issue61-work/src-6a40e083/`; `_local_socket_unblock.py` nach `issue61-work/` kopiert; `livetest/` angelegt.
- Task 1: RED = Collection-Fehler (kein `o1`), GREEN = `7 passed`. Mutationen (a) Stunde ab Stempel,
  (b) kein Abschneiden vor der Auswertung, (c) keine Lochprüfung: je `1 failed, 6 passed` → alle getötet;
  Original danach wieder `7 passed`.
- Task 2 (Imperial-Probe gegen `src-6a40e083`): `.FF` — `2 failed, 1 passed`.
  - Kontrolle metrisch: PASS (Panel und Lauf = Dauer aus `-12.7 + 5.08` mm).
  - Panel imperial: `assert 0 == 112` — `_live_run_duration(zone, -0.5 in, metric=False, credit=5.08 mm)`
    liefert 0 statt 112 s.
  - Lauf imperial: `_zone_run_decision(...)` liefert `None` („zone dropped: the mm credit covered the inch deficit“).
- Herkunft der Gutschrift (gelesen, `src-6a40e083`): `forecast_weighting_credit` (`calculation.py:1039-1137`) enthält
  keine Einheiten-Umrechnung (grep auf metric/unit/inch/convert leer) und gibt `rain.mm` zurück (`:1137`); Pirate fragt
  immer `si` ab (`PirateWeatherClient.py:124`); kein Wettermodul rechnet in Zoll um.
  → Verdacht E3 für beide Live-Funktionen **bestätigt**; Ende-zu-Ende auf einer echten imperialen Installation nicht
  gemessen.
