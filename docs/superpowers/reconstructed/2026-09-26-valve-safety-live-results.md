# Live-Test v2026.09.22b1 auf HA-Test — BEIDE BESTANDEN

Build `45682c0b` = upstream `418ab8a0` + Branding + `Eifel-Joe#3`/`#4`.
Per HACS installiert, HA-Test neu gestartet; die **geladene** Integration meldet
`v2026.09.22b1` (Diagnose-`integration_manifest`). Ausgangswerte: `livetest-baseline.md`.
Alle Läufe auf Zone **Grace Test** (id 8), `watering_mode: service`.

---

## Eifel-Joe#3 — BESTANDEN, beide Hälften

### Erst ein Fehlversuch, und warum er keiner war

Erster Anlauf: `input_boolean.grace_emu_unavailable` auf `on`, damit die
Bestätigungs-Entität unerreichbar wird. **Ergebnis: kein Fehler, Lauf lief normal
durch** (Ventil an 21:01:18, aus 21:02:18, exakt 60 s).

Korrektes Verhalten, kein Defekt — `_confirm_valve_running` (`irrigation.py:794`):

```python
if state is None or state.state in ("unavailable", "unknown"):
    return None  # not verifiable — don't fault write-only valves
```

`unavailable` liefert `None`, nicht `False`; ein nicht lesbares Ventil wird bewusst
nicht bestraft. **Der Testaufbau war falsch, nicht der Fix.** Für
`PROBLEM_VALVE_DID_NOT_OPEN` muss die Entität lesbar sein und 30 s lang `off` bleiben.

### Phase A — der Fehler wird gesetzt

Aufbau: `script.grace_emu_run` vorübergehend ohne `input_boolean.turn_on`. Danach
wortgleich zurückgestellt — **Konfigurations-Hash wieder `9476640a0091f385`,
identisch zum Original.**

| Nachweis | Vorher | Nachher |
|---|---|---|
| `..._grace_test_problem` | `off` | **`on`** |
| `fault_reason` | `null` | **`valve_did_not_open`** |
| Hub `irrigation_plus_problem` | `off`, `zones: []` | **`on`**, `zones: ["Grace Test"]` |
| Eimer | −2,72 | −2,72 unverändert |

Log: `22:43:32.028 WARNING Zone 8 irrigation fault: valve_did_not_open`

Vor dem Fix feuerte diese Stelle nur das Bus-Event; der Sensor blieb dunkel.

### Phase B — ein guter Lauf löscht ihn

| Zeit | Ereignis |
|---|---|
| 22:43:32 | Fehler gesetzt |
| 22:45:49 | Ventil schließt, 60-s-Lauf zu Ende |
| **22:45:54** | **Fehler gelöscht** — `fault_reason: null`, Hub `zones: []` |

Vor dem Fix hatte `_clear_zone_fault` auf dem Self-Closing-Pfad **keinen einzigen
Aufrufer**: der Fehler wäre bis zum nächsten HA-Neustart stehen geblieben.

---

## Eifel-Joe#4 — BESTANDEN

Zonenfelder vom User gesetzt: `throughput: 4`, `flow_sensor: sensor.wasser_vorne_flow`.
Der Sensor meldet `0` bei Einheit `m³/h` → enthält `/` → wird als **Raten**-Sensor
gelesen, 0 m³/h = 0 L/min. **Lebender Sensor, kein Wasser** — der Leitfall, real
vorhanden statt simuliert.

### Verlauf, mitten im Lauf gemessen

| Zeit | Nachweis |
|---|---|
| 22:50:49 | Lauf startet, Ventil auf, **Eimer −2,72 → −2,32** (optimistische Gutschrift +0,4 mm aus 4 L auf 10 m²) |
| 22:51:54 | Lauf endet trocken |

### Endstand gegen die Ausgangswerte

| Kriterium | Vorher | Nachher | Erwartet |
|---|---|---|---|
| Eimer | −2,72 | **−2,72** | zurück auf den Vorlauf-Wert ✓ |
| `water_used_total` | 0,0 | **0,0** (`last_changed` unverändert 20:56) | unbewegt ✓ |
| Protokoll-Ergebnis | — | **`failed`** | `failed` ✓ |
| Protokoll-Grund | — | **`flow_never_started`** | `flow_never_started` ✓ |
| `volume_l` | — | **0** | 0 ✓ |
| Problem-Sensor | `off` | **`on`**, Grund `flow_never_started` | an ✓ |
| `last_irrigation` | `unknown` | **`unknown`** | nicht gestempelt ✓ |

Protokolleintrag wörtlich:

```json
{"ts":"2026-09-26T22:51:54","trigger":"self_closing","planned_s":60,
 "actual_s":60,"volume_l":0,"result":"failed","detail":"flow_never_started"}
```

Eimer-Buchführung, beide Richtungen im Store:

```json
{"ts":"22:50:49","mm": 0.4}   // optimistische Gutschrift beim Öffnen
{"ts":"22:51:54","mm":-0.4}   // Rücknahme beim trockenen Abschluss
```

Log: `22:51:54.314 WARNING Zone 8 irrigation fault: flow_never_started`

**Ohne den Fix hätte derselbe Lauf gemeldet:** `completed`, 4 L Verbrauch, Eimer auf
−2,32 stehen gelassen — eine Zone, die nichts bekommen hat, als versorgt verbucht.

**Nebenbefund, der eine Spec-Zusage bestätigt:** `last_irrigation` blieb `unknown`.
Spec §4.3 Schritt 4 argumentierte, `_stamp_run_finalized(zone_id, 0.0)` brauche keinen
Sonderfall, weil beide Zweige von selbst ablehnen. Live bestätigt.

---

## Zustand des Testsystems

- `script.grace_emu_run` zurückgestellt, Hash identisch zum Original
- `input_boolean.grace_emu_unavailable` auf `off` (wie vorgefunden)
- **Offen gelassen:** Grace Test trägt weiter `flow_sensor` + `throughput 4` und steht
  auf Fehler `flow_never_started`. Jeder weitere Lauf dort wird wieder trocken sein,
  solange der Sensor 0 meldet. Zum Aufräumen: Flusssensor-Feld im Panel leeren, dann
  löscht der nächste gute Lauf den Fehler.
- Grace Test hat drei neue Protokolleinträge (abgebrochen, abgeschlossen, trocken)
