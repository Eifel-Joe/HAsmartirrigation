# Auftrag: Faktensammlung für die Spec von PR 3 (stummer Wettersensor — Schnitt im Stundenpfad und in der Live-Schätzung)

Du bist ein Lese-Agent. **Nur lesen.** Kein Code ändern, kein Git-Schreibzugriff (kein checkout/commit/stash), keine
Home-Assistant-Aufrufe, `gh` nur lesend (`gh api` GET). Einzige Schreibaktion: die Ergebnisdatei (unten) per Write-Tool.

## Hintergrund in drei Sätzen

Die Integration Irrigation Plus (HA, Fork von JustChr) erkennt seit PR 1 stumme Wettersensoren und schreibt Ausfälle mit
(`sensor_liveness.py`, Feld `sensor_outages` je Sensorgruppe). PR 2 (Branch `feat/pause-silent-weather-sensor`, offen als
upstream PR 197) schneidet für Sensorgruppen auf *pausieren* (`on_silent_sensor = pause`) die gesperrte Zeit aus dem
**Tagespfad** des Commits — aber nur, wenn die Stundenrechnung aus ist (Gate). PR 3 soll denselben Schnitt im
**Stundenpfad** (hourly ET, nachgespielte Bilanz / Teilschritte) und in der **Live-Schätzung** bringen und das Gate
entfernen; danach soll es keine Zwischenstände mehr geben.

## Quellen

- **Code (maßgeblich):** `D:\Entwicklung\HASI\issue8-pr3-work\src\` = `git archive 6fa424e8` (PR-2-Kopf =
  `upstream/master` `6a40e083` + 18 PR-2-Commits). Zeilenangaben IMMER gegen diese Kopie, Pfade relativ zu
  `custom_components/irrigation_plus/` (Tests `tests/`, Doku `docs/`), per `grep -n` bzw. Read nachgeprüft.
- **PR-2-Diff:** `git -C D:\Entwicklung\HASI\HAsmartirrigation diff 6a40e083 6fa424e8 -- custom_components tests docs`
  (lesend; zeigt genau, was PR 2 eingeführt hat).
- **Spec Rev. 3:** `D:\Entwicklung\HASI\HAsmartirrigation\docs\superpowers\specs\2026-10-03-dead-weather-sensor-design.md`
  — für PR 3 v. a. Abschnitte *Schneiden: gemeinsame Regeln* (243–252), *Schnitt im Stundenpfad und in der
  Live-Schätzung (PR 3)* (279–292), *Zwischenstände* (294–301), *Melden*, *Dokumentation*, *Betroffene Stellen je PR*,
  *Tests*, *Ende-zu-Ende-Kriterium*. Die Zeilenangaben in Rev. 3 beziehen sich auf einen ÄLTEREN Commit (`e9c79ec4`) —
  jede davon auf `6fa424e8` umrechnen (Tabelle in Abschnitt 3.10).
- **PR-2-Detail-Spec (vollständig lesen):**
  `D:\Entwicklung\HASI\HAsmartirrigation\docs\superpowers\specs\2026-10-11-dead-weather-sensor-pr2-design.md`
  inkl. Nachtrag E1–E4.
- **PR-2-Plan (nur nachschlagen):** `D:\Entwicklung\HASI\HAsmartirrigation\docs\superpowers\plans\2026-10-12-dead-weather-sensor-pr2.md`.
- **Vorlage für Form und Tiefe:** `D:\Entwicklung\HASI\issue8-pr2-work\context-2026-10-11.md` (Faktensammlung für PR 2).
- **JustChr (lesend):** `gh api repos/JustChr/HAsmartirrigation/issues/comments/5972596286 --jq .body` (seine Bedingungen,
  `JustChr#188`), `…/issues/comments/5997966126` (Merge-Kommentar PR 1), `gh api repos/JustChr/HAsmartirrigation/pulls/197
  --jq .body` (PR-2-Text; was er über PR 3 / Zwischenstände liest). Nur kurz zitieren (ein Satz), sonst sinngemäß.

## Ergebnisdatei

`D:\Entwicklung\HASI\issue8-pr3-work\context-2026-10-14.md`, Deutsch, Code-Bezeichner wörtlich. Kopf: Stand, „nur
gelesen“, Basis `6fa424e8`. Markiere eigene Zusammenfassungen mit **[Zusammenfassung]**, Unsicheres mit
**[unbestätigt]**. Lieber eine genaue `datei:zeile` als drei vage Sätze.

### 1. Anforderungen an PR 3

Was Rev. 3 und die PR-2-Spec von PR 3 verlangen (mit `Spec:<zeile>`), und jede Stelle, an der PR 2 bewusst einen
Zwischenstand hinterlassen hat, den PR 3 auflösen muss.

### 2. JustChrs Aussagen zu PR 3

### 3. Code-Fakten auf `6fa424e8`

- **3.1 PR-2-Bausteine:** `blocked_spans`, `valid_share`, `cuts_field` (Helfer aus E1), `_blocked_spans_for_zone`
  (alle Gate-Bedingungen, besonders die Stundenrechnung), der Transport `blocked=` (`_aggregate_for_zone`,
  `aggregate_window`, `calculate_module`, `_record_window_*`), `_sync_stale_issue` (Bedingungen der Hinweis-Variante),
  Log-Texte, Re-Sync-Auslöser (u. a. Umschalten der Stundenrechnung in `async_update_config`). **Jede Stelle, an der
  PR 2 die Stundenrechnung als Bedingung abfragt**, mit `datei:zeile`.
- **3.2 Stundenpfad im Commit:** Wo zweigt der Commit in die Stundenrechnung ab (`hourly_calculation_enabled`), was ruft
  er auf (`build_hourly_rows`, `hourly_eto_priced`, `_effective_series`, `build_substeps`, Stundenzeilen aus
  `last_entry`)? Welche Pufferzeilen/Felder gehen je Stunde ein, wie werden Teilstunden an den Fenstergrenzen behandelt,
  wie wird heute ein fehlendes Feld in einer Stunde behandelt (Pflichtfelder der PyETO-Stundenform laut Code — mit
  Rev. 3 vergleichen: dort „Temperatur, Feuchte, Wind und Sonne; Druck aus der Höhe“), Druck aus der Höhe, Schätzung
  der Sonne, die gehaltene Klarheitsquote (Rev. 3: `weather_aggregate.py:757` auf altem Commit). Was ist das Ergebnis
  des Stundenpfads und wie fließt es in `et_delta` (Stundenzweig neben dem Tagesform-Ausdruck mit PR-2-Anteil `s`)?
  Passthrough im Stundenbetrieb?
- **3.3 Nachgespielte Bilanz / Teilschritte und Abgleich:** `build_substeps`, Verteilung nach Sonne vs. nach Zeit
  (Rückfall), der Abgleich zwischen Aggregat und Teilschritten (Rev. 3: `calculation.py:999-1008` auf altem Commit):
  was wird verglichen, was passiert bei Abweichung („still Einmal-Buchung“ laut Rev. 3 — belegen oder widerlegen),
  welches Aggregat liefert im Stundenbetrieb den Niederschlag.
- **3.4 Live-Schätzung:** der Aggregat-Aufruf (Rev. 3: `live_estimate.py:607`), die Kommentare „exactly as
  `_aggregate_for_zone`“ (PR 2 hat sie ergänzt), `_latest_temperature`, wie `live_deficit` entsteht (Tagesform? nutzt sie
  bei eingeschalteter Stundenrechnung den Stundenpfad?), Fensteranfang/-ende, Takt und Caching, Vorbedingungen
  (`forecast_days == 0`, `live_estimate_enabled`), Verbraucher (Laufbemessung in `irrigation.py`, Panel,
  `forecast_weighting_credit`). Sieht sie heute irgendwo `blocked`?
- **3.5 Aufzeichnungen im Stundenbetrieb:** `_record_window_radiation`, `_record_window_amplitude`,
  `radiation_calibration` — laufen sie im Stundenbetrieb, mit welchem Fenster, und schneidet PR 2 sie dort schon?
- **3.6 Erklärung im Stundenbetrieb:** Welche Sätze erzeugt der Stundenzweig, wo sitzen die PR-2-Sätze
  (`sensor-outage`, `sensor-outage-share`), passen sie dort?
- **3.7 Texte mit Stunden-Bezug:** jeder Text, der sagt, dass der Schnitt nur ohne Stundenrechnung gilt — Hinweis
  (`translations/*.json`), Panel (`frontend/localize/languages/*.json`), Doku (`docs/*.md`), Log-Strings,
  Code-Kommentare — Schlüssel und `datei:zeile`, je Sprache zählen.
- **3.8 Tests und Infrastruktur:** Testdateien für Stundenpfad, Teilschritte/Abgleich, Live-Schätzung; Fixtures und
  Helfer; wie die PR-2-Tests `blocked` setzen; Zahl der Aufrufstellen (Produktion / Tests) von `build_hourly_rows`,
  `hourly_eto_priced`, `_effective_series`, `build_substeps`, dem Live-Aggregat-Aufruf — damit die Spec den Preis einer
  Signaturänderung kennt.
- **3.9 Schwester-Pfade:** Alle anderen Leser des Sensorpuffers oder von `last_entry` (z. B. Skip-Prüfungen
  Temperatur/Wind/Frost, Regen-Wächter, Saison-Ausblick, Prognose-Gewichtung, Wetter-Tag, Current Precipitation,
  Strahlungs-Kalibrierung). Je Leser: liest er einen eingefrorenen Wert, und schließt Rev. 3 ihn ausdrücklich aus?
- **3.10 Umrechnung** jeder Rev.-3-Zeilenangabe aus dem PR-3-Abschnitt auf `6fa424e8` (Tabelle alt → neu).

### 4. Offene Fragen, die die Spec von PR 3 entscheiden muss

Nummeriert. Je Frage: worum es geht, die Optionen, und die Fakten für/gegen jede Option (mit `datei:zeile`). Eine
Empfehlung ist erlaubt, aber als solche gekennzeichnet. Denke mindestens an: Gewichtung einer teilweise gültigen
Stunde; Pflichtfelder der Stundenform (Code vs. Rev. 3); Druck und Sonne in gesperrten Stunden; die gehaltene
Klarheitsquote; Verteilung der Teilschritte und Abgleich; Passthrough stündlich; Live-Schätzung mit offenem Ausfall bis
jetzt und `_latest_temperature`; Live-Schätzung OHNE Stundenrechnung (Tagesform-Live, PR 2 schneidet dort noch nicht);
Wegfall des Gates und was an Hinweis-Variante, Log, Re-Sync-Auslösern, Panel-Hilfe und Doku folgt; Erklärungssätze im
Stundenbetrieb; Aufzeichnungen; Rückbau-/Rollback-Verhalten; Lieferung (PR 2 ist noch nicht gemergt: PR 3 auf PR 2
stapeln oder nach dem Merge bauen — nur die Fakten, z. B. wie viele PR-2-Stellen PR 3 berührt); Auswirkung auf HA-Prod
(Stundenrechnung an, Live-Schätzung an, Gruppe auf *behalten*).

### 5. Risiken und Fallen

Was beim Bauen leicht schiefgeht (Zeitzonen der Stempel — naiv, HAs Uhr; Teststunden in US/Pacific vs. freezegun UTC;
byte-identische Ergebnisse für *behalten*; Signaturänderungen mit vielen Testaufrufern; usw.), jeweils belegt.

## Rückmeldung an den Auftraggeber

Höchstens 15 Zeilen: Pfad der Ergebnisdatei, Zahl der offenen Fragen, die drei Befunde, die die Spec am stärksten
prägen (je mit `datei:zeile`), und alles, was du nicht klären konntest.
