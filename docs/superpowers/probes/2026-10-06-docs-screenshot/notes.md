# Doku-Screenshot Weather & Location (Eifel-Joe#87 → upstream PR 194), 2026-10-06

Reiner Doku-PR: nur `docs/assets/images/configuration-weather-location-1.png` ersetzt (Branch von
`upstream/master` `6a40e083`, ein Commit `74025d20`). Kein Spec/Plan (trivial nach Regel P1); dieser
Ordner hält die nicht reproduzierbaren Belege und das Werkzeug.

## Kriterien (vor der Aufnahme benannt) und Ergebnis

- K1 Bild zeigt genau Forecast, Weather Records (zwei Sensorgruppen) und Seasonal outlook mit
  Hinweiszeile, englisch, hell, ohne Standortkarte — erfüllt (Sichtprüfung).
- K2 Werte der Karte = WS `irrigation_plus/watering_calendar` der ersten Zone (Test1, PyETO) — erfüllt,
  alle 12 Monate auf eine Nachkommastelle gleich (`capture-values.json`).
- K3 PR-Diff genau eine Datei, keine eigenen Verweise in Diff/Commit — erfüllt; Blob `4ed19b62` =
  Aufnahme; PNG nur IHDR/IDAT/IEND (keine Metadaten), 221 934 Byte (alt 288 097), 2288 × 2130 px.
- K4 Zonen 0 (Kirschlorbeer) und 1 (Beet) danach wieder `automatic`, erste Kalenderzone wieder id 0 —
  erfüllt. Laut Recorder (Attribut `state` von `sensor.irrigation_plus_kirschlorbeer`/`_beet`)
  deaktiviert 21:02:12 UTC, wieder `automatic` 21:02:56 UTC (44 s). PR und #87-Kommentar sagen
  „a few minutes“ bzw. „etwa vier Minuten“ — geschätzt; der User entschied, das nicht nachzukorrigieren.
- K5 CI am PR grün — erfüllt (4/4, `mergeStateStatus` CLEAN).

## Befund: die Karte nimmt die ET der ersten Zone

`view-weather-data.ts` nimmt `monthly_estimates` des ersten Kalendereintrags (aktive Zone mit der
kleinsten ID) und nimmt an, die Klimaspalten seien für alle Zonen gleich. Für Regen und Temperatur stimmt
das; die ET kommt aus `watering_calendar._calculate_monthly_watering_for_zone` je Modul: PyETO
Referenz-ET, Static `max(0, -calculate()) × Tage`, Passthrough `average_daily_et × Tage`
(`2.0 + 2.0 * summer`, also 2–4 mm/Tag). Auf HA-Test ist Zone 0 Static ohne Satz (Modul 2, `config {}`)
→ Karte ET 0.0 mm in allen 12 Monaten, Regen 120/116/105/90/75/64/60/64/75/90/105/116 mm, Temperatur
0/2/7.5/15/22.5/28/30/28/22.5/15/7.5/2 °C (`evidence-static-first-zone.png`, 21:01:14 UTC).
Im PR als Antwort auf JustChrs Bitte (Release-Notes v2026.10.05) gemeldet, Korrektur angeboten; Form
entscheidet er. Bauen wir sie, bekommt sie ein neues Fork-Issue. HA-Prod: erste Zone PyETO → dort
unsichtbar.

## Werkzeug

`login.py`: Edge (Playwright, `channel="msedge"`) mit eigenem Profil `edge-profile`, sichtbares Fenster;
der User meldet sich an (Haken „Keep me logged in“), das Skript wartet auf
`irrigation-plus-view-weather-data` und meldet Sprache/Design. `capture.py <out.png> [Breite]`: headless
mit demselben Profil, Gerätefaktor 2, Element-Screenshot des Views; Breite 1400 → Element 1144 CSS-px →
2288 px wie das alte Bild (Seitenleiste 256 px). Ausgabe mit `PYTHONIOENCODING=utf-8` in eine Datei
umleiten (sonst cp1252-Fehler an „—“/„°“). venv: `uv venv --python 3.12` + `uv pip install playwright
pillow` (kein Browser-Download nötig). Das Profil enthält die HA-Test-Anmeldung → nicht archivieren,
nach dem Merge löschen.

## Nebenbei geklärt (kein Befund)

- Die Wetterdaten-Tabelle zeigte nur zwei Zeilen, eine vom 16.09.: `_prune_mapping_buffer` behält je
  Feld die letzte Zeile vor dem Schnitt, gleich welchen Alters (Docstring) — gewollt.
- `ha_get_history` (MCP, `minimal_response=false`) rechnet das Zonen-Attribut `last_updated` (naiver
  Ortszeit-String) als UTC nach Europe/Berlin um → erscheint 2 h zu spät; HA-Prod per Template:
  Attribut = Zustandszeit. Werkzeug-Artefakt, nicht die Integration.
