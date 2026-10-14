# Imperial: Vorhersage-Gutschrift in mm auf ein Defizit in Zoll (2026-10-11)

Gehört zu Eifel-Joe#88 → `JustChr#195` (dort gemeldet am 2026-10-11).

`test_live_credit_units.py` ist ein RED-Test für den Live-Pfad: `forecast_weighting_credit` liefert Millimeter, das Panel
(`LiveEstimateMixin._live_run_duration`) und der Lauf (`IrrigationRunnerMixin._zone_run_decision`) addieren den Wert
unumgerechnet zum Live-Defizit, das in Anzeige-Einheiten geführt wird.

Gemessen am 2026-10-14 auf `6a40e083` (Lese-Kopie als `PYTHONPATH`, `-p _local_socket_unblock`): **2 failed, 1 passed**

- `test_imperial_panel_credits_the_forecast_in_the_deficits_unit`: `assert 0 == 112`
- `test_imperial_run_credits_the_forecast_in_the_deficits_unit`: „zone dropped: the mm credit covered the inch deficit“
- `test_metric_panel_and_run_agree_with_the_mm_credit`: grün (Kontrolle, metrisch stimmt die Rechnung)

Herkunft: `D:\Entwicklung\HASI\session-1011b-work\`, seit 2026-10-14 `D:\Entwicklung\HASI\_erledigt\session-1011b-work\`.
Die Vorab-Sonde `imperial_probe_test.py` liegt schon unter `probes/2026-10-07-forecast-weighting-live/`.
