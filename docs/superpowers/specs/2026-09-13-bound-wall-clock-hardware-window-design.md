# Die Arm-Schranke rechnet mit dem Fenster, das die Hardware wirklich läuft

Datum: 2026-09-13 · Folge-PR zu [#135](https://github.com/JustChr/HAsmartirrigation/pull/135)
· Basis `upstream/master` = `437042a7` (v2026.09.15)

## Herkunft

In #135 als bewusst ausgeklammerte Lücke benannt und im Docstring von `bound_wall_clock` als
„KNOWN GAP" festgehalten. JustChr beim Merge: „agreed it is a follow-up, and yes please.
Threading `duration_unit` through `ZoneRun` is the right size for its own PR."

## Wurzel

`bound_wall_clock` (`run_window.py:564`) liefert die längste Wanduhrzeit, die die Zonen eines
Zeitplans belegen können. Der Scheduler zieht sie in `_duration_bound` vom Zielzeitpunkt ab und
arm't daran den zweistufigen Entscheidungspunkt. Die Schranke rechnet mit `maximum_duration`
plus `lead_time`, **ohne** die Hardware-Rundung.

Ein selbstschließendes Ventil mit Minuten-Einheit wird aber auf ganze Minuten aufgerundet und
läuft sie auch. Seit `e9f2da5` (#88) und #135 buchen Lauf, Kettenfortschritt und Finish-Anker
dieses Fenster. Die Schranke liegt damit je Minuten-Zone um bis zu eine Rundung zu kurz. Unter
`sequential` und `rotating` summiert sich das je Zone. Der eigene Docstring der Funktion nennt eine
zu kurze Schranke die Richtung, die sich der Arm nicht leisten kann.

## Befunde

**Track und Umrechnung decken sich exakt.** `track_for_zone` baut sich aus denselben Prädikaten,
die `hardware_priced_seconds` benutzt:

| Track | Prädikat | Umrechnung heute in `hardware_priced_seconds` |
|---|---|---|
| `classic` | nicht selbstschließend | keine |
| `station` | `is_opensprinkler_zone` | `opensprinkler_window` |
| `batch` | `is_batch_zone` | `hardware_window` mit Einheit |
| `service` | `is_self_closing_zone` | `hardware_window` mit Einheit |

**Wo die Schranke herkommt.** Einziger Aufrufer ist `scheduler._duration_bound`, mit den
`ZoneRun`s aus `irrigation.async_plan_zone_runs(…, ignore_demand=True)`. Die tragen `lead_time`
bereits. `ZoneRun` wird an zwei Stellen gebaut: `irrigation.py` (in `async_plan_zone_runs`) und
`run_window.nominal_demand_seconds`. Die zweite speist die Schranke nicht.

**Der Lauf schickt den Vorlauf mit.** `duration_from_deficit` klemmt auf `maximum_duration` und
addiert `lead_time` danach; die gesamte Dauer geht an das Ventil. Gerundet werden muss also
`maximum_duration + lead_time`, nicht die Maximaldauer allein.

## Design

1. **Gemeinsame Umrechnung** `hardware_priced_for_track(track, unit, seconds)` in `run_window.py`:
   - `classic` → unverändert;
   - `station` → `opensprinkler_window(seconds)`;
   - `batch`, `service` → zweite Hälfte von `hardware_window(seconds, unit)`, fehlende Einheit als
     Sekunden (wie `zone.get(ZONE_DURATION_UNIT, DURATION_UNIT_SECONDS)` heute);
   - nicht endliche Werte unverändert zurück, weil `math.ceil(inf)` einen `OverflowError` wirft und
     eine unbegrenzte Zone unbegrenzt bleiben muss.
2. **`hardware_priced_seconds(zone, seconds)`** delegiert: `track_for_zone(zone)` und die Einheit der
   Zone an die gemeinsame Funktion. Verhalten unverändert.
3. **`ZoneRun.duration_unit: str | None = None`**, gesetzt an beiden Baustellen aus
   `zone.get(const.ZONE_DURATION_UNIT)`.
4. **`bound_wall_clock`** rundet nach dem Addieren des Vorlaufs mit der gemeinsamen Funktion, anhand
   von `r.track` und `r.duration_unit`. Eine vom Aufrufer gelieferte `ceiling` wird ebenso gerundet;
   die Rundung eines schon gerundeten Werts ändert ihn nicht. Die KNOWN-GAP-Notiz wird durch eine
   Beschreibung des jetzigen Verhaltens ersetzt.

## Verworfen

- **Feld plus eigene Rundungslogik in `bound_wall_clock`, gehalten durch einen Kreuz-Pin:** zwei
  Schreibweisen einer Entscheidung, nur durch einen Test verbunden. Genau die Form, die #135 mit
  Kreuz-Pins absichern musste, weil dort Modulgrenzen das Teilen verhinderten. Hier verhindert
  nichts das Teilen.
- **Schranke beim Bau von `ZoneRun` vorab berechnen:** weicht von der vereinbarten Form ab, verlagert
  das Parsen von Maximaldauer und Vorlauf in zwei Konstruktoren, und ein `ZoneRun` ohne das Feld
  fiele still auf die alte Rechnung zurück.

## Wirkung

Der Entscheidungspunkt am Ende verankerter, zweistufiger Zeitpläne rückt um bis zu eine Rundung je
Minuten-Zone früher, unter `sequential` je Zone. Auf HA-Prod ändert sich nichts: Beet (Minuten,
2700 s + 10 s Vorlauf) steigt von 2710 auf 2760 s, aber unter `parallel` bestimmt Kirschlorbeer
(Sekunden, 3600 + 10 = 3610 s) die Schranke.

## Fehlerfälle

- Zone ohne `maximum_duration` und ohne `ceiling`: bleibt `math.inf`, wird nicht gerundet.
- Unbekannte oder fehlende Einheit: Sekunden-Zweig von `hardware_window`, wie heute im Lauf.
- Nicht positive Werte: `hardware_window` klemmt auf 0, `opensprinkler_window` ebenso.

## Prüfkriterien

- Gemeinsame Funktion je Track, einschließlich `inf` und einer Station mit Bruchteilsekunden.
- `bound_wall_clock` für eine Minuten-Zone ohne Vorlauf (263 → 300) und mit Vorlauf (2700 + 10 →
  2760); für eine klassische Zone mit Minuten-Einheit (unverändert); für eine Station (Aufrundung
  auf ganze Sekunden); unbegrenzte Zone bleibt `inf`.
- Kreuz-Pin über alle Bewässerungsmodi aus `const`: die Schranke einer Einzelzone entspricht
  `hardware_priced_seconds(zone, maximum_duration + lead_time)`. Umgeht `bound_wall_clock` die
  gemeinsame Funktion, schlägt er fehl.
- Bestehende Tests zu `hardware_priced_seconds` und `bound_wall_clock` bleiben grün.
- Jede Zusicherung per Mutation als beißend nachgewiesen.

## Außerhalb

- Die zweite KNOWN-GAP-Notiz in `run_window.py:797` (Verteiler-Mitglieder) ist ein anderer Befund.
