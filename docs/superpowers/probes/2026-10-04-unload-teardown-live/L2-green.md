# L2 GREEN — Deaktivieren mitten im Lauf, HA-Test, installiert v2026.10.04b1 (2026-10-04)

Aufbau wie L1 (`L1-red.md`, `L1-green.md`). Flussquelle statisch 6.0 L/min.

## Ablauf (Ortszeit)
| Zeit | Ereignis | Quelle |
|---|---|---|
| 08:02:50.554 | Pumpe an (Settle 5 s) | `last_changed` |
| 08:02:55.557 | Lauf dispatcht, Ventil an; Plan-Gutschrift +1,2 mm | `pending_bucket_events`, `last_changed` |
| ≈08:03:56 | Eintrag deaktiviert (`ha_set_integration enabled=false`) | Antwort |
| 08:03:56.056 | WARNING `Zone 8: stopping its self-closing run because the Irrigation Plus config entry is being disabled` | Log |
| 08:03:56.059 | genau ein Teillauf: `self_closing`, geplant 180 s, ist **61 s**, **6,05 L gemessen**, `partial`, `self_closing_stopped`; Korrektur −0,595 mm | `run_log`, `pending_bucket_events` |
| 08:03:56.156 | Pumpe aus (Master-Ende sofort) | `last_changed` |
| 08:03:56.225 | Ventil aus (Stop service `script.grace_emu_stop`) | `last_changed` |
| 08:04:43.456 | Profiler-Abzug D4' (Eintrag deaktiviert) | Log |
| 08:04:43.752 | Objekte: `0x5fb390c8d20` (jetzt abgebaut) und `0x5fb385b2ba0` (beim L1-GREEN-Neuladen abgebaut) | Log |
| ≈08:04:48 | Eintrag wieder aktiviert (`last_updated` der Zone 08:04:48.813); keine weitere Buchung | Diagnose |

`water_used_total` 66,9003 → 72,9505 (+6,05 = 60,5 s × 6 L/min). Gutschrift netto +0,605 mm.

## Befund
Gegen RED (`L2-red.md`):

| | RED (v2026.09.30b2) | GREEN (v2026.10.04b1) |
|---|---|---|
| Ventil | an bis zum Countdown (180 s) | zu 0,17 s nach der Abbruch-Meldung (Stop service) |
| Buchung | 07:52:33 durch den abgebauten Koordinator, `completed`, 180 s, 18,9 L | 08:03:56 beim Deaktivieren, `partial`, 61 s, 6,05 L |
| Pumpe | 5,000 s nach der toten Buchung (toter Aus-Timer) | sofort, 0,10 s nach der Abbruch-Meldung |
| Abtaster nach dem Ende | weg (der tote Backstop schloss ihn) | weg (`l2_grid_green.txt`) |

Reihenfolge: Die Pumpe ging 69 ms vor dem Ventil aus. `_sc_dispatch_stop` ruft den Stop service ohne
`blocking` auf (`self_closing.py:1002`, unverändert aus dem bestehenden Stopp-Pfad); das Skript schließt
das Ventil, während das Master-Ende schon läuft. Gutmütige Reihenfolge: die Pumpe läuft nie gegen ein
geschlossenes Ventil.

Objektbestand: Auch mit dem Fix ist der beim Neuladen abgebaute Koordinator knapp 6 min später noch im
Speicher. Er ist also kein Unterscheidungsmerkmal; maßgeblich ist die Timer-Liste.
