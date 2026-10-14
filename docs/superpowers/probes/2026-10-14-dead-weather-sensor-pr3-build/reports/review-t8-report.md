### Spec Compliance

- ✅ Spec compliant. Der Diff setzt Plantext und Spec G10 / §3.1 / §3.3 um: `_carry_estimate_to` bestimmt die Sperren einmal für sich
  (`live_estimate.py:2020`, `zone_blocked_spans(self.store, zone, anchor, now_local)` -- derselbe Anker und dasselbe `now` wie
  `_intraday_for_zone`, vgl. `:1488`), schneidet das Aggregat damit (`:2021-2023`) und reicht dieselben Sperren an
  `_composed_day_et` weiter (`:2042`). Der Rest der Hochrechnung (Rest-Teil, Regen, Drainage, `carried_to_decision`) ist
  unverändert. Es gibt keine Annahme über die Rückkehr: kein Code, der eine offene Sperre über `now` hinaus fortschreibt.
- ✅ Geprüft, ob die Hochrechnung "die Sperren so bekommt, wie G10 es verlangt" (Auftrag des Controllers). Alles, was `_carry_estimate_to`
  aus Sensorwerten bezieht, läuft jetzt geschnitten:
  - `agg` aus `_aggregate_live_window(..., blocked=)` (`:2021`, Weiterreichen an `aggregate_window` bei `:661`).
  - Temperatur-Anker der Resthochrechnung: `_composed_day_et(blocked=)` --> `_projected_extremes(blocked=)` (`:1072`) -->
    `_latest_temperature(..., blocked=, now=)` (`:992`, `:938-940`).
  - `_mirror_blend` (Aufrufer `:2029`, einziger Aufrufer im Modul laut Grep) braucht keine Sperren: Es entscheidet nur über
    `_daily_form_applies` (Modul-/Quellenachse) und `_commit_forecast` (Prognosetage), liest keinen Sensorwert. Kein Mangel.
  - `trailing_temperature_amplitude` / `trailing_radiation_calibration` lesen bereits gebuchte Fenster (Historie), keine laufenden
    Sensorzeilen; `forecast_rain_mm` kommt aus dem Wetterdienst.
- ✅ "Ohne Tageswert entfällt die Hochrechnung wie heute": Bei ganztägig gesperrter Temperatur liefert `_aggregate_blocked` (`weather_aggregate.py:620-622`)
  für das Feld nichts (keine Segmente --> `return`), also kein Min/Max --> `_projected_extremes` gibt `None` (`:970-973`) -->
  `_composed_day_et` gibt `None` --> `return projected` (`:2044-2045`, `carried_to_decision = False`). Durch Lesen belegt, nicht durch einen Task-8-Test (siehe Minor 2).
- ✅ Byte-Identität ohne Sperren: `zone_blocked_spans` gibt für *behalten*, Zone ohne Gruppe, leeres Fenster und Sperren nur fremder
  Felder `None` (`sensor_liveness.py:252-268`). Mit `blocked=None` ist `_aggregate(...)` unverändert (`weather_aggregate.py:522`:
  `spans = blocked.get(key) if blocked else None`), und `_latest_temperature` fragt `(blocked or {}).get(...)`, `any(...)` über leere
  Spans --> `False` (`live_estimate.py:938-940`). Die Hochrechnung läuft dort wie vorher.
- ✅ Global Constraints: kein Store-Feld, keine Übersetzungsschlüssel, keine Verweise auf Issues/Kürzel/"PR 2/PR 3" in den
  hinzugefügten Zeilen und der Commit-Message (`git log -1 ca0955f8` gelesen), Trailer wortgleich zum Plan, Lint laut Bericht sauber.
- ⚠️ Nicht aus dem Diff prüfbar, Controller sollte nachsehen: Ob ein späterer Task die Verdrahtung `_carry_estimate_to` -->
  `_composed_day_et(blocked=)` --> `_latest_temperature` über die Stufe `self-contained` (ohne stündliche Prognose) belegt. Die
  Task-8-Tests tun es nicht (Minor 1). Falls kein späterer Task es tut, sollte ein Test dazu.
- ⚠️ Nicht aus dem Diff prüfbar: Für Zonen mit gemessener Sonne in der Tagesform liest `_projected_radiation` (`:1126-1161`) den
  geschnittenen Mittelwert `agg[SOLRAD]`, skaliert ihn aber mit der ganzen verstrichenen Zeit (`observed = mean * elapsed_h / 24`, `:1140`).
  Sperrstunden der Sonne am Tag werden damit mit einem Mittel aus gültiger Zeit (inkl. Nachtnullen) aufgefüllt; das Ergebnis kann
  zwischendurch niedrig liegen. Am Fensterende konvergiert es auf den geschnittenen Mittelwert, den auch der Commit bucht (`:1137-1138`).
  Der Plan/G10 verlangt hier nichts anderes ("Vorschau wie heute, aber aus dem geschnittenen Aggregat"), also kein Befund -- nur
  zur Kenntnis für die Gesamtreview.

### Strengths

- Minimaler, genau passender Eingriff (9 Zeilen Code): die Sperren werden einmal erfragt und an genau die zwei Leser gereicht, die
  Sensorwerte der Hochrechnung bestimmen. Der Kommentar (`:2017-2019`) nennt den Grund (eingefrorener Wert ist keine Beobachtung)
  und passt zum Stil von `_intraday_for_zone` (`:1484-1488`).
- Der Aufruf liegt innerhalb des bestehenden `try` ("a projection must never raise"); Argumentreihenfolge und Zeitbasis stimmen mit dem
  Schwester-Pfad `_intraday_for_zone` überein, sodass Schätzung und Hochrechnung dasselbe geschnittene Aggregat sehen.
- Test 2 ist ein echter Verhaltens-Pin: Zählung über den Modul-Namespace (`monkeypatch.setattr(live_estimate_module, "zone_blocked_spans", ...)`,
  greift, weil `live_estimate.py` den Namen global aufruft), Anzahl = 1 und Argumente `(ANCHOR, MID)` -- pinnt Einmaligkeit, Anker und `now` zugleich.
  Das Zählen beginnt nach dem Aufruf von `_intraday_for_zone`, misst also nur `_carry_estimate_to`.
- Test 1 nutzt den echten Koordinator, eine echte PyETO-Instanz und die vorhandenen Fixtures; die Szene ist sauber gebaut: die
  eingefrorenen Zeilen sind genau die Zeilen in `[lo, hi)` der Sperre (`+7 h <= t < MID`), die Zeile bei `MID` bleibt ungefroren, passend zur
  Halboffen-Regel. `carried_to_decision is True` für beide Läufe sichert ab, dass der Vergleich nicht über einen frühen Ausstieg
  zustande kommt. RED (`1.6405 < 1.6405`, `0 == 1`) und GREEN (`6 passed`, alle 6 ERROR = "Lingering timer") sind in den Rohdateien
  `task-8-red.txt` / `task-8-green.txt` nachgelesen und passen zum Bericht; keine weiteren Warnungen.

### Issues

#### Critical (Must Fix)

Keine.

#### Important (Should Fix)

Keine.

#### Minor (Nice to Have)

1. `custom_components/irrigation_plus/live_estimate.py:2042` (`blocked=blocked` an `_composed_day_et`) wird von keinem Task-8-Test
   bemerkt (**plan-mandated** Lücke, Tests stehen wörtlich im Plan). Die Weitergabe wirkt nur über `_projected_extremes` -->
   `_latest_temperature` (`:992`), und das wird nur erreicht, wenn keine stündliche Prognose den Rest abdeckt
   (`remainder is None`, `:989`). Test 1 übergibt aber `forecast=_hourly_forecast()`: `_estimating_inputs` setzt dann
   `hourly_forecast_tier = "service"` (`tests/test_live_estimate_replayed_balance.py:1319`), und `forecast_remainder`
   (`day_projection.py:226-243`) liefert für die 30 h ab `T0` eine Liste, die das Fensterende (`T0 + 26 h`) einschließt -- der
   Diurnal-Zweig läuft nie. Streicht man `blocked=blocked,` an `:2042`, bleibt jeder Test grün. Betroffen wäre gerade die Gruppe ohne
   Wetterdienst (Stufe `self-contained`): die Hochrechnung würde an den eingefrorenen `last_entry`-Wert des toten Sensors verankert,
   also an genau den Wert, den der Commit-Text als "keine Beobachtung" ausschließt. `_latest_temperature` selbst ist einzeln getestet
   (`tests/test_live_estimate_silent_sensor.py:195-206`), die Verdrahtung ab `_carry_estimate_to` nicht. Vorschlag: ein Test mit
   `forecast=None`, `MAPPING_DATA_LAST_ENTRY = {T: 40.0}` und offenem Temperatur-Ausfall; gepaust darf sie nicht auf 40 °C verankert sein.
   Voraussetzung: eine von null verschiedene `trailing_temperature_amplitude` (committete Fenster in der Historie), sonst gibt
   `diurnal_remainder` (`day_projection.py:397`) ohnehin `None` und beide Läufe fallen auf `observed` -- der Test wäre leer.
   Wer es vorab belegen will: Mutation "`blocked=blocked,` an `:2042` entfernen" und `tests/test_live_estimate_silent_sensor_daily.py` laufen lassen --
   erwartet bleibt `6 passed` (von mir nicht gelaufen, Regel: keine Tests).
2. `tests/test_live_estimate_silent_sensor_daily.py:184` (`paused < kept`) prüft nur die Richtung. Das fängt "Aggregat nicht geschnitten"
   (RED belegt das), aber nicht "zu viel geschnitten" oder die Halboffen-Grenze am Ende (die Zeile bei `MID` zählt als gemessen: ein
   geschlossenes `[lo, hi]` würde sie ebenfalls streichen, ohne dass der Test es sieht -- die Grenze ist nur an der Spans-Funktion
   selbst gepinnt). Zwei Zusatzpunkte in derselben Linie, alle ohne Task-8-Test: (a) ganztägig gesperrte Temperatur -->
   `carried_to_decision is False` (G10-Schlusssatz), (b) *behalten*/`blocked=None` --> Hochrechnung `==` ohne Ausfall-Eintrag
   (die Global Constraint "Tests vergleichen mit `==`" ist für `_carry_estimate_to` nur über `_intraday_for_zone`-Tests, nicht für diese
   Funktion belegt; `tests/test_live_estimate_silent_sensor.py:90-97` deckt nur die Schätzung), (c) Zweig `own_equation = False`
   (Hargreaves, `:2040`) und Stundenform. Alle drei ließen sich mit wenigen kurzen Tests belegen; keiner ist Blocker, weil die Code-Pfade
   von `blocked` unabhängig verzweigen bzw. durch Lesen belegt sind.
3. `tests/test_live_estimate_silent_sensor_daily.py:152` Docstring von `_frozen_zone`: "While silent from 7 h after the anchor ..."
   -- stumm ist der Sensor ab `+4 h` (`_silent(store, zone, 4)`), `+7 h` ist der Beginn der Sperre (Start + 3 h) und der Beginn der
   eingefrorenen Zeilen. Der Wortlaut ist plantreu, nur sachlich ungenau; Hinweis für die Gesamtreview, nicht für diesen Task zu ändern.

### Assessment

**Task quality:** Approved
**Reasoning:** Der Code-Eingriff ist klein, trifft G10/§3.1/§3.3 vollständig und lässt Gruppen ohne Sperren byte-identisch laufen; die zwei
Tests pinnen Wirkung (geschnittenes Aggregat) und Einmaligkeit/Anker/`now` echt. Offen bleibt als Minor, dass die Weitergabe an `_composed_day_et`
(Anker der Temperatur-Hochrechnung bei fehlender stündlicher Prognose) von keinem Test bemerkt würde.
