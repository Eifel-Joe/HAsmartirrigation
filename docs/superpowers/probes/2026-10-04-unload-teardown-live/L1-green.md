# L1 GREEN — Neuladen mitten im Lauf, HA-Test, installiert v2026.10.04b1 (2026-10-04)

Pre-Release `v2026.10.04b1` (production `4ebd458c`) per HACS installiert; Dateien vor dem Neustart
geprüft (`master.py` mit `async_master_end_cycle_now`, Stand 07:55:04); HA-Test neu gestartet
(angekündigt), Eintrag `loaded`, Manifest `v2026.10.04b1`, Log nur die bekannten `via_device`-Hinweise.
Koordinator nach dem Neustart `0x5fb385b2ba0`. Offset Epoche − Schleifenzeit unverändert
(Monotonic-Uhr des Hosts), gegengeprüft an zwei `_TrackPointUTCTime`-Zeilen.

## Ablauf (Ortszeit)
| Zeit | Ereignis | Quelle |
|---|---|---|
| 07:57:53.004 | Abzug D0' (vor dem Lauf) | Log |
| 07:58:03.853 | Pumpe an (Settle 5 s) | `last_changed` |
| 07:58:08.857 | Lauf dispatcht, Ventil an; Plan-Gutschrift 1,2 mm | `pending_bucket_events`, `last_changed` |
| 07:58:35.441 | Abzug D1' (Lauf, vor dem Neuladen) | Log |
| ≈07:58:56 | `homeassistant.reload_config_entry`; Nachfolger hoch 07:58:56.722 (`last_updated` der Zone) | Dienstaufruf, Diagnose |
| 07:59:05.722 | Abzug D2' (nach dem Neuladen, Ventil noch an) | Log |
| 08:01:08.859 | Ventil aus (Hardware-Countdown, 180 s) | `last_changed` |
| 08:01:13.863 | genau eine Buchung: `self_closing`, 180/180 s, **12 L** (nach Zeit), `completed` | `run_log` |
| 08:01:18.864 | Pumpe aus, 5,0 s nach der Buchung (Aus-Timer des Nachfolgers) | `last_changed` |
| 08:01:32.519 | Abzug D3' | Log |

`water_used_total` 54,9003 → 66,9003 (einmal +12).

## Befund
Raster (`l1_green.py`, Ausgabe `l1_grid_green.txt`):

- D0' (vor dem Lauf): kein Timer im Raster.
- D1': Tick 2.
- D2' (direkt nach dem Neuladen): **kein Timer** im Raster.
- D3' (nach dem Laufende): **kein Timer** im Raster.

Gegen RED (`L1-red.md`): Dort stand der Abtaster nach dem Neuladen in Tick 12, nach dem Laufende in
Tick 20, 5 min später in Tick 33 und noch 13,7 min nach dem Start in Tick 55. Mit dem Fix geht er mit dem
Koordinator. Die Buchung ist auf beiden Seiten gleich: genau eine, nach Zeit. Das sagt der PR-Text unter
„Neuladen“ zu.
