| Spec PR 3 | Task |
|---|---|
| §1 Rahmen: *behalten* byte-identisch, Regenzähler nie, keine Store-Felder | 1 (`zone_blocked_spans`), 2–3 (`==`-Tests ohne/mit leeren/fremden Sperren), 6 (Gruppe auf *behalten*) |
| §1 Einheit Gate/Anteil/Texte | Reihenfolge 4 → 5 (Rahmen) |
| §1 Rückbau | keine Store-Änderung; kein Task nötig |
| §2.1 Sperren ohne Gate, freie Funktion, Hülle bleibt | 1, 5 |
| §2.2 Helfer „gültige Proben je Feld“ | 2 (`_masked_hold_table`, `_masked_mean`) |
| §2.3 Stundenzeilen: Mittel über eigene gültige Zeit, Gewicht = gemeinsame Zeit, leere Zeile ohne ET, nie `None` | 2 |
| §2.3 G4 Pflichtfeld wegen Sperre ganz ohne Probe | 2 (`booked = []`, Tests „every reading inside a span“, „never read still falls back“) |
| §2.3 G5 Klarheitsquote | 2 (`solar_samples` ohne Sperre, `_books_nothing` in `_ratio_hold_solar`) |
| §2.3 Druck | 2 (Test `TestPressureIsNotRequired`) |
| §2.4 Pflichtmenge je Form, Anteil nach der Formwahl, kein zweites Skalieren, Satz 2 | 4 |
| §2.5 G6 Lage der ET, G7 Regenzuwächse | 3 (Teilschritte), 2 (`_precip_increments` mit Sperren) |
| §2.6 Tagesform unter Stundenschalter, Aufzeichnungen | 4 (`TestTheDailyFormUnderTheHourlySwitch`), 5 (umgedrehter PR-2-Test) |
| §3.1 Sperren einmal je Neuberechnung, alle Leser, Live-`now` für den Niederschlag | 6 |
| §3.2 G9 Quellenkette, Spiegel × Anteil, 0 statt `None` | 7 |
| §3.3 G10 Hochrechnung; `_latest_temperature` | 8; 6 |
| §3.4 G11 Übertrags-Schlüssel; Neuberechnung nach Öffnen/Schließen | 6; 9 (ungedrosselt, siehe Abweichung unten) |
| §3.5 Gleichlauf Live = Commit | 6 (`hourly_sensor`), 7 (`daily_mirror`) |
| §4 Hinweis/Log/Re-Sync/Panel-Hilfe/Doku/Kommentare | 5, 7 (Live-Satz der Doku), 6 (Live-Kommentare) |
| *Tests* (Byte-Identität, Teil A, Teil B, Mutationen, volle Suite) | 1–9, 10 |
| *Ende-zu-Ende-Kriterium* | 11 |
| *Lieferung* (Stapeln, Pre-Release, Merge, PR, P1) | 0, 10–12 |

**Abweichungen von der Spec, im Probelauf entschieden (zur Kenntnis mit der Plan-Freigabe):**
- §3.4 nennt `async_refresh_zone_estimates_throttled`. Genommen ist die **ungedrosselte**
  `async_refresh_zone_estimates`: Die gedrosselte verwirft jeden Aufruf innerhalb von 60 s nach der letzten Neuberechnung
  (`live_estimate.py:1772-1786`). Eine Pufferzeile kurz vor dem Öffnen hätte den Anstoß geschluckt, und bei einer stummen
  Station kommt danach keine mehr. Die Prüfung läuft nur alle 5 min und frischt höchstens einmal je Lauf auf, nur bei
  pausierenden Gruppen.
- §2.3 ließ offen, wie Zeilen mit Gewicht 0 ihre Messfelder darstellen: **leer** (nur `time`, `hour_start`, `hour`,
  `doy`, `coverage_h`, ggf. `tz_offset_h` und `precipitation`). Die zwei Leser der Messfelder überspringen sie
  (`eto_hourly_series`, `_ratio_hold_solar`).
- Präzisierung zu G7: Ein Regenraten-Zuwachs wird an den Sperrgrenzen geteilt und landet am Ende **seines gemessenen
  Teils**. Sonst landete Regen kurz vor einer Sperre erst bei der nächsten behaltenen Probe (Befund im Probelauf). Die
  Summe gleicht dem Aggregat (Abgleich-Toleranz 1e-6 relativ).
- `zone_blocked_spans` prüft nur `None` für Anfang und Ende; ein leeres oder verkehrtes Fenster ergibt über
  `blocked_spans` ohnehin keine Sperre (`None`). Der zusätzliche Vergleich war gleichwertig (Mutation überlebte).
