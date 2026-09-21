# Mutationsproben — PR A (Observed-Doppelgutschrift)

Gegen `fix/observed-credit-si-takeover` @ `582a0e02`, Basis `upstream/master` = `965a4f9d`.
Probenlauf: `tests/test_experimental_features.py` + `tests/test_observed_watering.py` (57 Tests).
Skripte: `scratchpad/mutate.py` (M1–M4), `scratchpad/mutate_m5.py` (M5).

| # | Mutation | Ergebnis | Getötet von |
|---|---|---|---|
| M1 | `pending.pop(zid, None)` ersatzlos | **CAUGHT** (4 failed) | `..._already_open_valve_drops_the_external_window`, `..._flap_after_the_takeover...`, `..._string_zone_id`, `test_si_takeover_cancels_an_external_flow_sampler` |
| M2 | `pending.pop(zid, …)` → `pending.pop(zone_id, …)` | **CAUGHT** (2 failed) | `..._string_zone_id`, `test_si_takeover_cancels_an_external_flow_sampler` |
| M3 | `self._observed_cancel_meter(zid)` ersatzlos | **CAUGHT** (1 failed) | `test_si_takeover_cancels_an_external_flow_sampler` |
| M4 | `_observed_cancel_meter(zid)` → `_observed_cancel_meter(zone_id)` | **CAUGHT** (1 failed) — *nach* der Testverschärfung | `test_si_takeover_cancels_an_external_flow_sampler` |
| M5 | Den ganzen Anspruch auf `run_seconds > 0` gaten | **SURVIVED — äquivalent** | — |

**Proben 5 · gefangen 4 · äquivalent 1 · unerklärt überlebend 0.**

## M4 war eine echte Lücke, kein äquivalenter Mutant

Im ersten Lauf überlebte M4: `test_si_takeover_cancels_an_external_flow_sampler` übergab die Zonen-ID als
`int`, dort sind `zid` und `zone_id` derselbe Wert. Der Meter-Dict ist aber — wie der Marker-Dict — auf den
`int` aus dem Speicher geschlüsselt (`observed_watering.py`, `_observed_meters()[zone.get(ZONE_ID)]`), und
der klassische wie der rotierende Läufer reichen ihre Zonen-ID unnormalisiert durch
(`irrigation.py:1413/:1639/:2123`). Ein Aufruf mit einer Zeichenkette hätte den Sampler also stehen lassen.

Geschlossen mit RED zuerst: M4 gesetzt → verschärfter Test (`_note_si_valve("2", 600)`) fällt mit
`Expected 'mock' to have been called once. Called 0 times.` → M4 zurückgenommen → grün.
Commit `582a0e02`. Nebeneffekt: M2 wird seitdem von zwei Tests getötet statt von einem.

## M5 ist äquivalent, nicht ungetestet

Das verworfene `run_seconds > 0`-Gate ändert das Verhalten an keiner erreichbaren Stelle. Zwei der acht
Aufrufe sind Schließ-seitige Nachjustierungen mit `run_seconds=0` (`irrigation.py:1523` in
`_run_valve_metered`, `:1702` in `_irrigate_zone_flow_slot`), beide **nach** dem eigenen `turn_off` des
Läufers. Zu diesem Zeitpunkt steht das Unterdrückungsfenster noch auf `t_open + max_seconds + 30` bzw.
`t_open + slot + 30` — bei `real_flow` also auf dem stundenlangen Sicherheitsfenster, im Rotationsfall
mindestens 30 s in der Zukunft, auch wenn der Slot seine volle Länge ausschöpft. Eine externe Öffnen-Flanke
zwischen Öffnen und diesem Punkt wäre daher unterdrückt worden und hätte gar keinen Marker gesetzt: es gibt
nichts, was das Gate retten könnte.

Ein Test dafür müsste einen Zustand herstellen, den der Produktivcode nicht herstellen kann — also den
Marker von Hand setzen, während das Fenster noch läuft. Das würde nicht das Gate prüfen, sondern die
Testvorrichtung. Deshalb protokolliert statt totgeschlagen.
