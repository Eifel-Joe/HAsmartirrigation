# L1 RED — Neuladen mitten im Lauf, HA-Test, installiert v2026.09.30b2 (2026-10-04)

Aufbau: Zone 8 „Grace Test“ (Service, Bestätigung `binary_sensor.grace_emu_flowing`,
Durchflusssensor `input_number.hasi_flow_probe` = 6.0 L/min, Durchsatz 4 L/min),
Master `input_boolean.test_pumpe` mit „nach Lauf aus“, Profiler-Integration hinzugefügt.

## Ablauf (Ortszeit)
| Zeit | Ereignis | Quelle |
|---|---|---|
| 07:39:37.053 | `run_zone` Zone 8, 3 min; Ventil, Fluss, Pumpe an | `pending_bucket_events.ts`, Zustände |
| 07:39:46.212 | Profiler-Abzug D1 | Log |
| zwischen 07:41:51 und 07:42:34 | `homeassistant.reload_config_entry` | Dienstaufruf |
| ≈07:42:26 | Nachfolger hoch (`last_updated` der Zone 07:42:26.393; neue 600-s-Zwillinge im Abzug) | Diagnose, D2 |
| 07:42:34.984 | Profiler-Abzug D2, neuer Koordinator `0x52c9d0b91a0` (alt `0x52cb658faa0`) | Log |
| 07:42:37.054 | Ventil aus (Hardware-Countdown) | `last_changed` |
| 07:42:42.058 | genau eine Buchung: `self_closing`, 180 s geplant/ist, **12 L** (nach Zeit, 180 s × 4 L/min), `completed` | `run_log` |
| 07:42:47.059 | Pumpe aus | `last_changed` |
| 07:44:23.625 | Profiler-Abzug D3 | Log |
| 07:47:49.719 | `dump_log_objects SmartIrrigationCoordinator`: **zwei** Objekte, `0x52c9d0b91a0` und `0x52cb658faa0` | Log |
| 07:47:49.760 | Profiler-Abzug D4 | Log |

`water_used_total` 24.0 → 36 (einmal +12).

## Befund
Der Profiler zeigt Intervall-Timer nur als `_TrackTimeInterval._interval_listener()`. Der Abtaster
ist am Raster erkennbar: 15 s ab Laufstart (`l1_grid.py`, Ausgabe `l1_grid_red.txt`):

- D0 (vor dem Lauf): kein Timer im Raster.
- D1: Tick 1 um 07:39:52.052 (15,000 s nach dem Start).
- D2 (nach dem Neuladen): Tick 12.
- D3 (nach Laufende und Buchung): Tick 20.
- D4 (5 min nach Laufende): Tick 33, mittlere Periode 15,0007 s.

Der Nachfolger startet für den übernommenen Lauf keinen eigenen Abtaster: kein zweiter Timer im
15-s-Raster. Der Abtaster des alten Koordinators überlebt Neuladen, Laufende und Buchung und hält den
alten Koordinator im Speicher. Das ist der Defekt aus der Spec.

Die Buchung bleibt einmalig und nach Zeit (12 L statt gemessener 18 L). Das ist erwartet, auch auf der
GREEN-Seite gleich.
