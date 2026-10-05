# Live-Test Eifel-Joe#10 auf HA-Test — Saisonaler Ausblick

## Vorher (2026-10-05 ≈ 13:05 UTC, HA-Test mit v2026.10.04b2, alter Kalender-Code)

GET `/api/irrigation_plus/watering_calendar` per `ha_manage_custom_tool` (`api_get`), nur lesend. Konfiguration aus den
Diagnostics (`data.store`): Static-Zonen Kirschlorbeer (25 m², Kc 0,5, Modul 2 Static, Delta 0) und Beet (5 m², Kc 1,
Modul 1 Static, Delta 0); PyETO-Zonen Test1–Test6 (je 5 m², Kc 1, Multiplikator 1) und Grace Test (10 m², Kc 1);
metrisch; keine manuellen Koordinaten (HA-Standort, gemäßigtes Band).

| Zone | Monat | „ET“ mm | Regen mm | Temp °C | Menge L | Notiz |
|---|---|---|---|---|---|---|
| Static (beide) | 1 / 2 / 7 | 0 / 0 / 0 | 60 / 64,02 / 120 | 0 / 2,01 / 30 | 0 / 0 / 0 | „Based on typical … climate patterns“ |
| PyETO 5 m² | 1 | 86,01 | 60 | 0 | 130 | dito |
| PyETO 5 m² | 2 | 99,1 | 64,02 | 2,01 | 175,4 | dito |
| PyETO 5 m² | 7 | 279,61 | 120 | 30 | 798 | dito |
| Grace Test 10 m² | 1 / 2 / 7 | 86,01 / 99,1 / 279,61 | wie oben | | 260,1 / 350,8 / 1596,1 | dito |

Befund vorher, wie in der Spec: (86,01 − 60) × 5 = 130,05 und (279,61 − 120) × 5 = 798,05 → die Menge ist die reine ET,
der Regen steckt in der „ET“-Spalte; Regen-Gipfel im Juli; Static zeigt bei Delta 0 korrekt 0 (der Static-Fix ist auf
HA-Test nicht sichtbar — Delta absichtlich NICHT verändert: HA-Test hängt am MQTT-Broker von HA-Prod).

## Nachher (2026-10-05 ≈ 14:50 UTC, HA-Test mit v2026.10.05b2)

Weg: Pre-Release v2026.10.05b2 (`b1307c8b`) per HACS (`update_information`, dann `download` mit `version`); Dateien vor
dem Neustart geprüft (`const.py` VERSION b2, `watering_calendar.py` mit allen Fix-Markern, `sensor_liveness.py` da);
Neustart HA-Test angekündigt und ausgeführt; danach Hub-Gerät `sw_version` = v2026.10.05b2, Eintrag `loaded`,
HA 2026.9.3; System-Log nur die bekannte `via_device`-Hinweiszeile.

**Kriterium (1):** für alle 7 PyETO-Zonen × 12 Monate (84 Prüfungen)
`Menge == round(max(0, ET × kc − Regen) × Mult × Fläche, 1)` innerhalb `0,005 × kc × Mult × Fläche + 0,05` →
**0 Abweichungen**.

**Kriterium (2):** Regen Januar **120 mm**, Juli **60 mm** (vorher 60 / 120). Februar 115,98 mm.

| Zone | Monat | „ET“ mm | Regen mm | Temp °C | Menge L | Notiz |
|---|---|---|---|---|---|---|
| Static (beide, Delta 0) | 1 / 2 / 7 | 0 / 0 / 0 | 120 / 115,98 / 60 | 0 / 2,01 / 30 | 0 / 0 / 0 | „Illustrative … climate derived from latitude only“ |
| PyETO 5 m², Kc 1 | 1 | 20,25 | 120 | 0 | 0 | dito |
| PyETO 5 m², Kc 1 | 2 | 28,61 | 115,98 | 2,01 | 0 | dito |
| PyETO 5 m², Kc 1 | 7 | 175,74 | 60 | 30 | 578,7 | dito |
| Grace Test 10 m² | 7 | 175,74 | 60 | 30 | 1157,4 | dito |

Lesart: Die „ET“-Spalte ist jetzt die reine Referenz-ET (vorher ET + Monatsregen); die reine ET selbst ändert sich
gegenüber vorher (Januar 26,01 → 20,25, Juli 159,61 → 175,74), weil Feuchte und Wind jetzt im Winter ihren Gipfel haben
und die PyETO-Gleichung damit rechnet (Task-5-Reviewer: 50° N Juli ≈ 5,67 mm/Tag × 31 = 175,8). Juli
(175,74 − 60) × 5 = 578,7 L; im Winter übersteigt der Regen die ET → 0 L. Static mit Delta 0 bleibt korrekt 0.

**Kriterium (3):** Sichtprüfung der Karte „Saisonaler Ausblick“ durch den User nach Strg+F5 (2026-10-05): Hinweiszeile
sichtbar, Werte passen, Abstand zur Tabelle in Ordnung („Hinweis da, Abstand ok“). → **Live-Test bestanden.**
