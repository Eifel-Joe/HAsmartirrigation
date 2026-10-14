### Spec Compliance

- ✅ Spec compliant (Spec §2.4 und §2.6, Plan-Task 4; Diff `74d7192a..1160abc5`).
  - Pflichtmenge je Form: `required_sensor_fields(module_name, *, hourly=False)` ist öffentlich (calculation.py:81-93 im Worktree), liefert für PyETO+`hourly=True` `HOURLY_ROW_REQUIRED` (Tupel, weather_aggregate.py:71-76: Temperatur, Feuchte, Wind, Sonne), sonst `_REQUIRED_SENSOR_FIELDS.get(...)`. Passthrough bleibt beim ET-Feld, Static `None`. Unit-Test deckt alle drei Module (tests/test_silent_sensor_hourly_commit.py:259-275 im Diff).
  - Form zuerst, Anteil danach: `required`/`share` stehen jetzt hinter `hourly = self._hourly_et_for_zone(...)` (calculation.py:1293-1313), `hourly=hourly is not None`. Zwischen der alten und der neuen Stelle wird `share`/`required` nicht gelesen (Grep über calculation.py: Verwendungen erst ab :1319) — kein UnboundLocalError-Risiko.
  - Stundenzweig ohne zweites Skalieren: `et_delta = -hourly_total * kc` unverändert (calculation.py:1373-1374), `et_delta *= share` bleibt im `else` der Tagesform (:1378-1381). `share` dient im Stundenzweig nur der Erklärung (`_silent_sensor_explanation(blocked, share)`, :1561-1562, schon formunabhängig).
  - `share == 0`: Tagesform ruft das Modul nicht (`hourly is None and share != 0`, :1319); Stundenform ergibt 0 aus den Zeilen — vom Test `test_a_required_field_silent_throughout_books_nothing` belegt (Form bleibt Stunde, Delta 0.0, Satz "0 %").
  - Durchreichen: `_hourly_et_for_zone(..., blocked=None)` → `hourly_eto_priced(..., blocked=)` (:939, :1033; et_estimate.py:160 nimmt den Parameter); `_substeps_for_zone(..., blocked=None, required=())` → `build_substeps(..., blocked=, required=)` (:1051-1100; weather_aggregate.py:1396-1397); Aufruf in `calculate_module` mit `blocked=blocked, required=required or ()` (:1421-1429).
  - Tagesform bei eingeschalteter Stundenrechnung (§2.6): geschätzte Sonne (`solrad="1"`) → `hourly is None` → Tagespflichtmenge; Test pinnt Feuchte zählt nicht (Delta -5.0, kein "booked for"), Temperatur zählt (22/24, 92 %).
  - Gate bleibt: `_blocked_spans_for_zone` liefert unter Stundenrechnung weiter `None` (calculation.py:443-444); kein Zwischenstand "Gate weg, Stundenzweig ungeschnitten".
  - Keep-Gruppen / `blocked=None` byte-gleich: `hourly_eto_priced` bekommt `blocked=None` (Default), `build_substeps` wertet `required` nur unter `if blocked:` aus (weather_aggregate.py:1516) — das jetzt immer berechnete und übergebene `required` ist bei `blocked in (None, {})` wirkungslos; `share` bleibt `None` ohne `blocked` (calculation.py:1305-1306).
  - Keine Verweise auf Issues/Spec-/Plan-Kürzel/"PR n": Grep auf den Diff nach `PR ?\d|Task|G\d+|Eifel|JustChr|#\d+|F\d` ohne Treffer. Kein Store-/Übersetzungs-Eingriff (Diff berührt nur calculation.py + Testdatei).
  - Anrufer-Check (benanntes Risiko: neue Kwargs `blocked=` an `hourly_eto_priced`/`build_substeps` brechen strenge Spies/Mocks): `tests/test_weather_buffer_one_frame.py:255-258` (`*args, **kwargs`), `tests/test_lumped_credit_drainage.py:588` (`lambda *args, **kwargs`), die übrigen Tests rufen mit Defaults — keine exakte Signatur-Bindung gefunden.
  - Risiko "Static/Passthrough bekommt `required or ()` + Sonnenmaske": gegenstandslos, `replayed_balance_applies` verlangt PyETO (calculation.py:143-158, :186-188).
  - Risiko "Test-Offset saisonabhängig": `_offset_h()` im Test spiegelt wörtlich die Produktionsrechnung (`dt_util.now().utcoffset()`, calculation.py:1020-1021) — gleiche Quelle, keine Jahreszeit-Flake.
- ⚠️ Cannot verify from diff: (a) Ergebnis der vollen Suite (Controller) — das Vergleichsskript deckt nur 6 Dateien; andere Dateien mit echten Koordinator-Commits unter `blocked` laufen nur dort. (b) Der Docstring von `_blocked_spans_for_zone` (calculation.py:439-441, "Only in the daily form for now … would fail that check") stimmt bis zum Gate-Wegfall und muss in dem Commit fallen, der das Gate entfernt — der Controller sollte das dort prüfen. (c) Ob die Verdrahtung `required` → Lage der ET in den Teilschritten an anderer Stelle des Plans auf Commit-/Live-Ebene gepinnt wird (siehe Minor 1).

### Strengths

- Die Reihenfolge ist sauber begründet im Code: Formwahl zuerst, Anteil danach, mit Kommentar, warum der Stundenzweig den Anteil nur benennt (calculation.py:1298-1301). `hourly is not None` ist die einzig richtige Formfrage (Tupel vs. `None`; ein Gesamtwert 0.0 bleibt Stundenform).
- Kein doppeltes Skalieren und der Beleg dafür: Test 1 vergleicht das Delta mit einem unabhängig per `build_hourly_rows` + `eto_hourly_series` gerechneten Wert auf 1e-9 und fordert `expected < ungeschnitten` — ein zweites `* share` (0,92) würde sofort rot.
- Die Testpaare pinnen die Formabhängigkeit der Pflichtmenge in beide Richtungen: Feuchte zählt in der Stundenform, nicht in der Tagesform; Temperatur zählt in beiden; Taupunkt zählt in der Stundenform nicht. Jede Mutation von `hourly=hourly is not None` (immer True / immer False) fällt an mindestens einem Test auf.
- Der Regen-Test (`blocked={RAIN: …}`, Riemann-Summe) fängt ein fehlendes `blocked=` im `_substeps_for_zone`-Aufruf (Abgleich Aggregat/Teilschritte würde reißen, "Number of steps:" fehlte).
- Der zweite Replay-Test (`T` gesperrt, Regen konstant) pinnt, dass gesperrte Stunden mit ET 0 in `hourly_et` stehen bleiben — fehlte eine Stunde, fiele die Bilanz still auf Einmal-Buchung.
- Kleiner, gezielter Diff; `required_sensor_fields` als freie Funktion mit Begründung (Live-Mixin kann nicht quer rufen — deckt sich mit der Begründung in `zone_blocked_spans`, sensor_liveness.py:238-247). Lint (black/ruff) laut Bericht sauber; die 8 Teardown-ERROR sind klassifiziert.

### Issues

#### Critical (Must Fix)

Keine.

#### Important (Should Fix)

Keine.

#### Minor (Nice to Have)

1. tests/test_silent_sensor_hourly_commit.py:578-582 / calculation.py:1428 — Die Verdrahtung `required=required or ()` in den Replay ist durch keinen Test dieses Tasks gepinnt. Mutation `required=()` (oder `required` ganz weglassen in `_substeps_for_zone`, calculation.py:1100) lässt alle 10 Tests grün: `test_it_still_replays_under_a_blocked_required_field` prüft nur `"Number of steps:" in explanation`, und die Lage der ET ändert die Niederschlagssumme (Abgleich) nicht. Auch `blocked=` allein ist nur über den Regenpfad belegt. Folge: eine falsch gewählte Pflichtmenge für den Replay (z. B. Tagesfelder in der Stundenform) bliebe unbemerkt, bis eine spätere Live-Prüfung sie trifft. Fix: in einem der beiden Replay-Tests `calculation.build_substeps` spionieren und `kwargs["required"] == HOURLY_ROW_REQUIRED` bzw. die Tagesfelder (und `blocked`) prüfen, oder ein Szenario mit drainage-/deckelempfindlicher Lage wählen und Bucket mit/ohne Sperre vergleichen. **plan-mandated** (Testblock wörtlich aus dem Plan) — der Mensch entscheidet.
2. tests/test_silent_sensor_hourly_commit.py:537-545 (`test_dewpoint_does_not`) — Die "wie bisher"-Zusage für Sperren nur fremder Felder wird mit `pytest.approx(...)` (rel. 1e-6) statt `==` geprüft, obwohl die Global Constraints "Tests vergleichen mit ==" nennen und beide Läufe exakt denselben Rechenweg nehmen. Eine Abweichung unterhalb 1e-6 (z. B. eine zusätzliche Stundenteilung durch eine fremde Sperrgrenze) fiele nicht auf. Fix: `==` auf das Delta, zusätzlich Erklärung/Bucket vergleichen. **plan-mandated**.
3. tests/test_silent_sensor_hourly_commit.py — Der Rückfall "Pflichtfeld nie gelesen → `hourly_eto_priced` liefert `None` → Tagesform mit Tagespflichtmenge" (Spec 2.6) ist auf Commit-Ebene nicht eigens geprüft; die Tagesform-Tests laufen nur über geschätzte Sonne (`solrad="1"`). Beide Wege enden in `hourly is None`, der Code-Pfad ist derselbe, daher nur Randnotiz.
4. calculation.py:84-88 (Docstring `required_sensor_fields`) — "its daily form the fields above" verweist auf den Kommentar über `_REQUIRED_SENSOR_FIELDS`, nicht auf eine benannte Stelle; besser `_REQUIRED_SENSOR_FIELDS` beim Namen nennen. Text plan-diktiert, rein kosmetisch.

### Assessment

**Task quality:** Approved
**Reasoning:** Der Diff setzt §2.4/§2.6 vollständig und ohne Zusatz um, der Stundenzweig bucht einmal und benennt den Anteil, Gruppen ohne Sperren laufen byte-gleich, und das Gate bleibt bis zur Folge-Änderung; die Tests pinnen die Formabhängigkeit der Pflichtmengen und das Nicht-Doppel-Skalieren belastbar. Offen sind nur Test-Schärfe-Punkte (Minor 1-2), beide aus dem Plantext.
