# L2 RED — Deaktivieren mitten im Lauf, HA-Test, installiert v2026.09.30b2 (2026-10-04)

Aufbau wie L1 (`L1-red.md`). Flussquelle `input_number.hasi_flow_probe` statisch 6.0 L/min.

## Ablauf (Ortszeit)
| Zeit | Ereignis | Quelle |
|---|---|---|
| 07:49:19.959 | Pumpe an (Settle 5 s) | `last_changed` |
| 07:49:24.962 | Lauf dispatcht, Ventil an; Plan-Gutschrift 1,2 mm | `pending_bucket_events`, `last_changed` |
| ≈07:50:35 (zwischen 07:50:2x und 07:50:39.4) | Eintrag deaktiviert (`ha_set_integration enabled=false`, „unloaded“) | Antwort, Zustand 07:50:39 |
| 07:50:39.4 | Ventil **an**, Fluss an, Pumpe **an** | Zustände |
| 07:52:24.963 | Ventil aus — Hardware-Countdown, genau 180 s nach dem Öffnen | `last_changed` |
| 07:52:33.966 | Buchung durch den abgebauten Koordinator: `self_closing`, 180/180 s, **18,9 L gemessen**, `completed`; Nachgutschrift +0,69 mm | `run_log`, `pending_bucket_events` |
| 07:52:38.966 | Pumpe aus, **5,000 s** nach der Buchung (Aus-Timer des toten Koordinators) | `last_changed` |
| 07:53:17.814 | Profiler-Abzug D5 (Eintrag noch deaktiviert) | Log |
| 07:53:18.097 | Objekte: `0x52c9d0b91a0` (der jetzt abgebaute L1-Nachfolger) und `0x52cb658faa0` (L1-alt) | Log |
| ≈07:53:25 | Eintrag wieder aktiviert (`last_updated` der Zone 07:53:25.460) | Diagnose |

`water_used_total` 36 → 54,9003 (+18,9). Die 18,9 L enthalten die 9 s zwischen Ventil zu und Buchung,
weil der statische Helfer nach dem Schließen weiter 6,0 meldet — Artefakt des Aufbaus, kein Code-Befund.

## Befund
Genau das „Bisher“ des PR-Texts: Nach dem Deaktivieren läuft das Ventil bis zum Ende seines
Hardware-Countdowns weiter, ein Timer des abgebauten Koordinators bucht den Lauf als vollständig, und die
Pumpe geht rund 5 s später aus.

Raster in D5 (`l2_grid_red.txt`): Der L2-Abtaster ist weg, weil der tote Backstop seinen eigenen Datensatz
fand und den Lauf samt Abtaster abschloss. Der L1-Abtaster tickt weiter (Tick 55, 13,7 min nach seinem Start).
