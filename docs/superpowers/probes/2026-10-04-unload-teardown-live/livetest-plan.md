# Live-Test Eifel-Joe#9 auf HA-Test (Arbeitsvorlage)

Ende-zu-Ende-Kriterium der Spec. Instanz: **HA-Test** (MCP-Präfix `mcp__HA-Test__`). Integration
`irrigation_plus`, Eintrag `01M20AD0AWZJ15ZXSF1ECVJZN3`, installiert `v2026.09.30b2` (RED-Seite: Defekt
vorhanden, `self_closing.py`/`master.py` seit 1876aa03 unverändert).

## Aufbau (vorhanden, 2026-10-04 gelesen)

- Zone 8 „Grace Test“: Service, `script.grace_emu_run` / `script.grace_emu_stop`, Feld `seconds`,
  Bestätigung `binary_sensor.grace_emu_flowing`, Ventil `input_boolean.grace_emu_valve`.
  **Fehlt: Durchflusssensor** → `input_number.hasi_flow_probe` (L/min) im Panel eintragen (HTTP-View,
  per MCP nicht schreibbar; User oder Browser mit User-Login). Nach dem Test wieder entfernen.
- Master `input_boolean.test_pumpe`, `master_off_after = true`, Settle 5 s, Kick aus.
- `zone_sequencing = parallel` (keine Kette nötig für die zwei Szenen).
- `input_number.grace_emu_off_delay = 0`.
- **Fehlt: Profiler-Integration** → vor dem Test hinzufügen (Config-Flow `profiler`, angekündigt).

## Szenen (je RED auf v2026.09.30b2, dann GREEN auf dem Pre-Release)

Vorher: Uhrzeit notieren, `water_used_total` von Zone 8 und Länge des Lauf-Logs lesen
(`ha_eval_template`), Flussquelle auf 6.0 L/min.

### L1 Neuladen mitten im Lauf
1. `irrigation_plus.run_zone` Zone 8, `duration: 180`.
2. Nach ~60 s: Eintrag neu laden.
3. Direkt danach `profiler.log_event_loop_scheduled`; nach Laufende (+~150 s) noch einmal.
4. Erwartet RED: nach Laufende steht noch ein Intervall-Handle aus `self_closing` (`_tick`).
   GREEN: keins mehr; genau ein Lauf im Log, `water_used_total` genau einmal gestiegen.

### L2 Deaktivieren mitten im Lauf
1. `run_zone` Zone 8, `duration: 180`; nach ~60 s Eintrag deaktivieren.
2. Erwartet RED: `grace_emu_valve` bleibt bis ~180 s an; Pumpe geht ~5 s nach Laufende aus (toter Timer).
   GREEN: Ventil sofort zu (Stop service), Pumpe sofort aus.
3. Wieder aktivieren; RED: Lauf vollständig gebucht (Plan); GREEN: genau ein Teillauf,
   `water_used_total` genau einmal um das Teilvolumen (~6 L bei 60 s und 6 L/min).

### L3 Entfernen
Nur per Unit-Test (`TestRemovingMidRun`), auf HA-Test zerstörerisch.

## Danach
Flussquelle 0, Durchflusssensor an Zone 8 wieder leer, Profiler darf bleiben (oder entfernen, User).
Belege (Log-Auszüge, Zustände mit Zeiten) nach `issue9-work/livetest/`.
