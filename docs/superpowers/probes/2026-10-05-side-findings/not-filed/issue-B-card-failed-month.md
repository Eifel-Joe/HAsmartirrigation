## English

**What.** When one month of the seasonal outlook fails, `_calculate_monthly_watering_for_zone` appends a placeholder with `estimated_et_mm: 0.0` and `estimated_watering_volume_liters: 0.0` plus an `error` (`watering_calendar.py:165-180`). The card (`frontend/src/views/weather/view-weather-data.ts`) never reads `error`: it shows the month as "0.0 mm" ET with "-" for rain and temperature, a plausible number with no marker. When the card's zone (the lowest-id enabled zone) fails as a whole (`monthly_estimates: []` plus `error`, e.g. a zone without module or mapping, `watering_calendar.py:111-121`), the card says "No watering calendar data available for this zone." and hides the healthy zones. The old per-zone calendar showed that error (`panels.zones.calendar.error_prefix`, still in the catalogues); the display was lost in `f2671da8`. Every card load computes all zones and logs a WARNING per failure.

**Reachability.** A month fails, for example, in the polar night (Eifel-Joe#85); a whole zone fails when the lowest-id enabled zone is incomplete.

**Fix sketch.** Placeholder values `None` instead of `0.0` (the card already renders `None` as "-") and a marker for a month with `error`; take the first zone that has estimates, and show its `error` when none has. Upstream.

**Severity:** `schwere:niedrig`; display only. At HA-Prod's latitude no month fails, and all its zones are complete.

**Former designations:** none (side finding of the Eifel-Joe#10 build; build notes on `archive/design-history`, `docs/superpowers/probes/2026-10-05-seasonal-outlook-build/final-review-carry.md`).

## Deutsch

**Was.** Scheitert ein Monat des saisonalen Ausblicks, hängt `_calculate_monthly_watering_for_zone` einen Platzhalter mit `estimated_et_mm: 0.0` und `estimated_watering_volume_liters: 0.0` plus `error` an (`watering_calendar.py:165-180`). Die Karte (`frontend/src/views/weather/view-weather-data.ts`) liest `error` nie: Sie zeigt den Monat mit „0.0 mm“ ET und „-“ für Regen und Temperatur, eine glaubhafte Zahl ohne Kennzeichen. Scheitert die Zone der Karte (die enabled Zone mit der kleinsten ID) als Ganzes (`monthly_estimates: []` plus `error`, z. B. eine Zone ohne Modul oder Mapping, `watering_calendar.py:111-121`), steht dort „No watering calendar data available for this zone.“, und die gesunden Zonen bleiben verborgen. Der alte Kalender je Zone zeigte diesen Fehler an (`panels.zones.calendar.error_prefix`, noch in den Katalogen); die Anzeige ging mit `f2671da8` verloren. Jeder Aufruf der Karte rechnet alle Zonen und loggt je Fehlschlag eine WARNING.

**Erreichbarkeit.** Ein Monat scheitert z. B. in der Polarnacht (Eifel-Joe#85); eine ganze Zone, wenn die enabled Zone mit der kleinsten ID unvollständig ist.

**Fix-Skizze.** Platzhalter `None` statt `0.0` (die Karte zeigt `None` schon als „-“) und ein Kennzeichen für einen Monat mit `error`; die erste Zone mit Werten nehmen und deren `error` zeigen, wenn keine Werte hat. Upstream.

**Schwere:** `schwere:niedrig`; nur Anzeige. Auf der Breite von HA-Prod scheitert kein Monat, und alle Zonen dort sind vollständig.

**Frühere Bezeichnungen:** keine (Nebenbefund des Baus von Eifel-Joe#10; Bau-Notizen auf `archive/design-history`, `docs/superpowers/probes/2026-10-05-seasonal-outlook-build/final-review-carry.md`).
