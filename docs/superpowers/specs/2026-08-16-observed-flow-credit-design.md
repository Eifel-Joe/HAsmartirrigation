# Spec: Observed-Watering — Measured-Flow Crediting + Plausibility Cap

**Datum:** 2026-08-16
**Status:** Spec (zur Freigabe)
**Kontext:** Live-Vorfall HA-Prod 2026-08-16 — Memory `hasi-observed-phantom-open-bug`

## Problem

`observed-watering` schreibt eine extern beobachtete Ventil-Öffnung dem Bucket
zeitbasiert gut: `volume_l = throughput_lpm × Minuten`
(`observed_watering.py:175`) und liest den Flow-Sensor **nie**. Ein
Zigbee-Ventil, das nach einem `unavailable`-Reconnect fälschlich `open` meldete
(real geschlossen, 0 Fluss), wurde mit **1349 L** gutgeschrieben
(21304 s × 3,8 L/min) → Bucket auf Maximum → Bewässerung fälschlich unterdrückt.
Der Durchflusszähler der Zone zeigte die ganze Zeit 0 Fluss — die Wahrheit war
vorhanden, wurde aber nicht konsultiert.

## Anforderungen

1. **Flow-Sensor-Zonen**: Kredit aus dem **gemessenen** Durchfluss über das
   `open→close`-Fenster (bestehende FlowMeter-Engine wiederverwenden), nicht aus
   `Zeit × throughput`.
2. **Nicht-Flow-Zonen** (z.B. Beet, `flow_sensor=null`): `Zeit × throughput`
   bleibt, aber mit **Plausibilitäts-Cap**.
3. **Universeller Cap** als Basis-Absicherung für beide Zonentypen.
4. **REGEL-8-Schwesterpfad-Check**: self-closing, distributor.
5. **Verbrauchsstatistik** (run-log, `water_used_total`) bleibt ehrlich
   (gedeckelt).

## Optionen (erwogen)

| Option | Beschreibung | Bewertung |
|---|---|---|
| A — Guard | `Zeit × throughput` + Flow-Anstieg-Check: open ohne Anstieg → kein Kredit | Minimaler Eingriff, aber bleibt bei echten Läufen ungenau (Schätzung); Pflaster |
| **B — Measured flow** | FlowMeter über `open→close`-Fenster, gemessener Kredit | Präzise; nutzt vorhandenen Zähler; **existierende Vorlage** in self-closing |

**Entscheidung: B** (User, 2026-08-16). B ist mehr Arbeit (15-s-Sampler +
Lifecycle), aber die FlowMeter-Engine (`flow_metering.py`, pure-Python, keine
HA-Kopplung) misst genau ein Ventil-`open→close`-Fenster — und `self-closing`
treibt sie bereits so über ein extern geschlossenes Ventil
(`self_closing.py:151-222`). Wir spiegeln dieses Muster.

## Design

**Open-Edge** (`_observed_state_changed` new_on, `observed_watering.py:129`),
nur wenn `zone[ZONE_FLOW_SENSOR]` gesetzt:
- Flow-Sample lesen, Meter via bestehendem `_flow_build_meter(zone, sample)`
  (`irrigation.py:814`) bauen (löst Zählertyp aus gespeichertem Streak auf).
- 15-s-Sampler via `async_track_time_interval` starten (Vorlage
  `_sc_start_flow_sampling`, `self_closing.py:176`). observed ist heute rein
  event-basiert; dieser Sampler ist der Haupt-Zusatz.
- Meter + Cancel-Handle + `started` pro Zone halten (Key wie `_observed_on_since`).

**Close-Edge** (`observed_watering.py:131-140`): Sampler abbrechen, finales
Read, `meter.delivered()`:
- `> 0` → Kredit = **`min(measured, throughput × capped_seconds)`**
  (Sanity-Ceiling gegen konstant-Nicht-Null-klemmende Sensoren).
- `== 0.0` (stuck-open dry, Sensor liefert Readings) → **Kredit 0** (der Bug-Fall;
  Aussage eindeutig).
- `== None` (toter/fehlkonfigurierter Sensor, kein Reading) → **gedeckelte
  `Zeit × throughput`-Schätzung + Problem-Flag** (Wasser nicht verlieren, aber
  deckeln und Sensor sichtbar als Problem markieren).

**Nicht-Flow-Zonen** (`flow_sensor` leer): Kredit = `throughput × capped_seconds`.

**Universeller Cap:** `capped_seconds = min(seconds, maximum_duration + 30 s)`.
`maximum_duration` = bestehendes Zonenfeld (`const.py:349`, default 3600 s); die
+30 s (neue Konstante `OBSERVED_CAP_MARGIN_SECONDS`) sind Puffer, damit ein
legitimer externer Lauf nahe `maximum_duration` nicht abgeschnitten wird.
Beispiel Bug: 21304 s → ≤3630 s → ~230 L statt 1349 L.

**Statistik:** `actual_s`, `volume_l` (run-log via `_record_run`) und
`water_used_total` (`add_to_total`) nutzen den **gedeckelten** Wert.

**Cross-run-Learning:** observed **liest** den Zählertyp (`flow_learn_resolve`,
gespeicherter Streak), **schreibt** aber `flow_last_end`/`flow_reset_streak`
**nicht** — wie der Verteiler-Pfad (`irrigation.py:1276`). Sonst vergiften
interleaved externe Öffnungen die Lern-Konvergenz der sauber sequenzierten
SI-Läufe (`_flow_learn_end_changes`, `irrigation.py:840`).

**Lifecycle-Sorgfalt:** Sampler abbrechen bei Close, `async_teardown_observed_watering`
(`observed_watering.py:89`), Re-Subscribe (`:74-78`), HA-Shutdown; Single-Flight
je Zone (Cancel-and-pop bei neuem Open, Vorlage `self_closing.py:168`).

**Ein Fix deckt beides:** classic-observed und Verteiler-Member-observed
(`ZONE_OBSERVED_ENTITY`) laufen durch **denselben** `_credit_observed_watering`.

## REGEL-8-Schwesterpfad-Check (Ergebnis: observed ist der einzige Ausreißer)

- **self-closing** (`_sc_finish_run`): bereits flow-gemessen; sein Zeit-Fallback
  (`_timed_volume_l`) rechnet mit `planned_s`, nicht roher Elapsed → kein
  Phantom-Zeit-Risiko.
- **Verteiler-Member** (`_dist_credit_zone`, `distributor.py:868`): metered nutzt
  `measured_l`; Zeit-Fallback schätzt aus dem **geplanten** Fenster (expliziter
  Kommentar `distributor.py:893`) → bereits abgesichert.
- **observed**: der **einzige** Pfad, der rohe externe Sekunden × throughput ohne
  Sensor-Widerspruch und ohne Fensterbindung bucht.

## Nicht dazugehörig (Scope / YAGNI)

- Keine Änderung an self-closing/distributor (Schwesterpfade schon geschützt).
- Kein Cross-run-Learning-Write aus observed.
- Kein neues Cap-**Setting** (nur eine feste Margin-Konstante; reuse
  `maximum_duration`).
- Ventil schon offen beim HA-Start (kein open-Edge gesehen) → nichts gutschreiben
  (Status quo, `observed_watering.py:133-136`).
- Die **Zigbee-Hardware** (Phantom-`open`) ist User-seitig; dieser Fix macht HASI
  nur robust gegen falsche Ventilzustände.

## Ende-zu-Ende-Kriterium (beweist, dass es funktioniert)

1. Flow-Zone, Ventil `open` 21304 s, Flow-Sensor flach/0 → Kredit **~0 L** (statt 1349).
2. Flow-Zone, echter externer Lauf mit realem Fluss → **gemessener** Kredit
   (≠ Zeit × throughput), gedeckelt am Sanity-Ceiling.
3. Nicht-Flow-Zone, `open` 21304 s → Kredit ≤ `throughput × (maximum_duration+30)`
   (~230 L), Stats ebenfalls gedeckelt.
4. Flow-Zone, toter Sensor (kein Reading), `open` 21304 s → gedeckelter Kredit
   **+ Problem-Flag**.
5. per_run-Zähler: observed-Lauf mit Mid-Run-Reset wird korrekt gemessen (15-s-Sampler).
6. Volle Test-Suite grün; keine Regression an self-closing/distributor/normalem observed.
7. Live (HA-Test → HA-Prod, eigener freigegebener Schritt): simulierter Phantom-`open`
   bucht nicht mehr 1349 L.

## Umsetzung + Review (2026-08-17)

Umgesetzt auf Branch `fix/observed-measured-flow-credit` (von `upstream/master`),
TDD, 6 Tasks + Härtungen. Zwei bewusste Abweichungen vom Plan:
- **Kein `_credited_depth_native`** im Credit-Pfad: das teilt durch den Zone-Multiplier
  (nur für SI-eigene *timed* Läufe korrekt). Externes Wasser hebt die Bodenfeuchte um
  die tatsächliche Tiefe (`volume_l / size_m2`) — der bestehende observed-Pfad rechnet
  das bereits so; `_credited_depth_native` wäre eine Multiplier-Regression gewesen.
- **`_observed_cancel_meter` schon in Task 3** (nicht Task 6), sonst wäre der Sampler
  nicht eigenständig testbar (single-flight).
- **Zusatz-Härtung:** Sampler-Start **synchron** (kein `async_create_task`) — schließt
  einen Open→Close-Flap-Race, der Meter+Timer leaken ließe.

**Adversarialer 4-Lens-Review** (Correctness / Lifecycle / REGEL-8-Integration /
Test-Qualität, jede Findung verifiziert): 14 Funde, 6 bestätigt (alle `low`):
- **Gefixt:** (1) negatives `measured_l` → Floor bei 0 (net-negatives Reading darf
  Bucket nicht drainen); (2) negative `maximum_duration` → `< 0`-Guard wie
  `calculation.py`; (4) `delivered()==0.0 AND saw_reset()` = per_run-Zähler als
  lifetime fehl-resolved → `None` (gedeckelte Zeit) statt 0-Credit — Phantom-open
  triggert nie `saw_reset`, Bug-Fix bleibt intakt; (6) End-to-End-Test der
  Close-Edge-Verdrahtung ergänzt.
- **Akzeptiert (dokumentiert, nicht gefixt):** (3) set-erhaltender Zone-id-Remap
  während laufendem externem Lauf leakt einen 15-s-Timer — exotisch + self-healing;
  als Code-Kommentar in `async_setup_observed_watering` festgehalten.
