# Live-Test v2026.09.22b1 auf HA-Test — Ausgangswerte

Erhoben 2026-09-26, **vor** dem Neustart, unmittelbar nach der HACS-Installation.
Build: `v2026.09.22b1` = Commit `45682c0b`, upstream `418ab8a0` + Branding + `Eifel-Joe#3`/`#4`.

## Problem-Sensoren (alle AUS — das ist der Nullpunkt für #3)

| Entität | Zustand |
|---|---|
| `binary_sensor.irrigation_plus_problem` (Hub) | off |
| `binary_sensor.irrigation_plus_beet_problem` | off |
| `binary_sensor.irrigation_plus_grace_test_problem` | off |
| `binary_sensor.irrigation_plus_kirschlorbeer_problem` | off |
| `binary_sensor.irrigation_plus_test1_problem` … `test6_problem` | off |

## Eimer und Verbrauch (der Nullpunkt für #4)

| Zone | bucket | water_used | last_irrigation | last_water_used |
|---|---|---|---|---|
| Beet | 1.56 | 55.28 | 2026-09-21T13:33:21+00:00 | 4.0 |
| Grace Test | −2.72 | 0.0 | unknown | unknown |
| Kirschlorbeer | −0.0 | 112.67 | 2026-07-05T10:43:06+00:00 | 49.98 |
| Test1 | −0.99 | 1173.35 | 2026-09-16T07:02:29+00:00 | 25.2 |

## Verfügbare Messquellen

- Flusssensoren, alle auf `0` — der `#4`-Leitfall ist real vorhanden, nicht simuliert:
  `sensor.wasser_vorne_flow`, `sensor.wasser_hinten_flow`, `sensor.wasser_3_flow`
- Sonoff-Emulator: `input_boolean.sonoff_emu_valve`, `input_boolean.sonoff_emu_fault`,
  `binary_sensor.sonoff_emu_flowing`, `script.sonoff_emu_run`
- Verteiler `gardena1` mit Test1…Test6 auf den Ausgängen 1–6

## Was der Test zeigen muss

**#3** — eine Self-Closing-Zone mit `confirm_entity`, das aus bleibt: der Problem-Sensor
muss **an** gehen (heute bleibt er aus). Danach ein guter Lauf: er muss wieder **aus**
gehen (heute bleibt er an, bis HA neu startet).

**#4** — eine Zone auf einen `sensor.wasser_*_flow` (steht auf 0) und ein Lauf über das
volle Fenster: Protokoll `failed` mit Grund `flow_never_started`, Eimer zurück auf den
Vorlauf-Wert, `water_used` **unverändert**. Heute: `completed`, Eimer satt, Verbrauch um
die volle Planmenge erhöht.
