### Spec Compliance
- ✅ Spec compliant. Geprüft gegen Interface und Global Constraints:
  - `zone_blocked_spans(store, zone, start, end) -> dict | None` liegt in `sensor_liveness.py:238`, direkt nach `valid_share`. `None` für: keine Gruppe (`:139-140`), Gruppe nicht gefunden oder auf *behalten* (`:141-143`), Anfang/Ende nicht lesbar (`:144-147`), keine verbleibende Sperre (`:154`, `blocked or None`). Sonst `{feld: ((von, bis), …)}`, Regenzähler über `cuts_field` ausgefiltert (`:152`).
  - `CalculationMixin._blocked_spans_for_zone(zone, *, now)` behält die Signatur (`calculation.py:414`), ruft die Funktion (`:428-430`), und das Gate `hourly_calculation_enabled(self.store)` bleibt (`:426`), wie der Task es für „bis Task 5“ vorschreibt.
  - Halboffene Sperre `[start + 3 h, end)`, offener Eintrag bis `end` des Aufrufers: unverändert in `blocked_spans` (`sensor_liveness.py:203-222`), die neue Funktion reicht `end` unverändert durch; vom Test `test_an_open_outage_blocks_up_to_the_window_end` (`tests/test_sensor_liveness_blocked.py:159`) gepinnt.
  - Kein Store-Versionssprung, kein neues Feld, keine neuen Übersetzungsschlüssel: Diff berührt nur die drei Dateien. Keine Fork-/Upstream-Issue-Verweise, Spec-/Plan-Kürzel oder „PR 2/PR 3“ in Diff oder Commit-Message (Diff gelesen; Message per `git show` geprüft, Trailer wie vorgegeben).
  - `git diff d4817574 HEAD --stat` ist leer: der Baum ist identisch zum Probe-Commit.
- ⚠️ Cannot verify from diff: Der Docstring von `_blocked_spans_for_zone` (`calculation.py:417-419`) sagt „the function the live estimate asks too“. In diesem Commit stimmt das noch nicht: `live_estimate.py:601-604` sagt ausdrücklich, die Live-Schätzung schneide nicht. Das ist Plantext, der erst nach dem Live-Task wahr wird. Der Controller sollte beim Branch-Review prüfen, dass der Satz am Ende wahr ist und `live_estimate.py:601` mitgezogen wurde.
- ⚠️ Cannot verify from diff: Die Modul-Docstring-Zeilen `sensor_liveness.py:12-14` („its daily calculation … calculation._blocked_spans_for_zone“) und die `cuts_field`-Docstring `:190-193` bleiben unverändert (der Task sieht dort nichts vor). Das gehört in die Doku-Runde am Ende, siehe Minor 2.

### Strengths
- Der Wrapper bleibt verhaltensgleich. Das habe ich nachgerechnet: Die alte Prüfung `watermark >= now` ist ersetzt durch `blocked_spans` auf einem leeren Fenster. Dort gilt `lo >= start >= end >= hi`, also `hi <= lo` und `continue`; das Ergebnis ist `{}` und `blocked or None` ergibt `None` (`sensor_liveness.py:218-220`). Das gilt auch für offene Einträge (`hi = end`). Die Reihenfolge Hourly-Gate vor Gruppen-Prüfung ändert das Ergebnis nicht, denn `hourly_calculation_enabled` ist ein reines `getattr` (`calculation.py:119-122`). Gruppen auf *behalten* bleiben also byte-identisch bei `None`, pausierende Gruppen in der Tagesform liefern dieselben Spannen.
- Die Funktion nimmt nur `store`, `zone`, `start`, `end` und liest den Schalter für die Stundenrechnung nicht. Die Begründung (freie Funktion, damit ein Mixin allein in seinen Tests nicht an einem Cross-Mixin-Aufruf scheitert) deckt sich mit der Vorgängerentscheidung bei `hourly_calculation_enabled` (`calculation.py:108-121`). Es entsteht kein Importkreis: `sensor_liveness` importiert `calculation` weiterhin nicht.
- Die Importbereinigung in `calculation.py:44` ist vollständig. `valid_share` wird weiter bei `:1243` genutzt, `coerce_stamp` und `STAMP_FROM_STORE` weiter bei `:223` und `:1239-1244`. Außer `calculation.py` importiert niemand `blocked_spans`, `cuts_field`, `group_pauses` oder `outages_of` über das Calculation-Modul (Grep über Repo, auch in Tests und `patch`-Strings: keine Treffer).
- Die Tests prüfen echtes Verhalten gegen die echten Funktionen: `Outage.to_store()` geht durch `from_store`, es wird nichts gemockt außer dem Store als `SimpleNamespace`. Sie pinnen: Beginn des Aufrufers (`:151`), offenes Ende (`:159`), Gate-Freiheit (`:165`), *behalten* (`:171`), kein Treffer inklusive der 3-h-Brücke (`:175`), alle fünf `None`-Zweige (`:179-185`) und Regenzähler gegen Regenrate (`:187`). Die Zweige der alten Methode (Wasserstand, Gruppe, Hourly-Gate, Regenzähler, Offset) sind zusätzlich weiter durch `tests/test_silent_sensor_commit.py:109-170` am Wrapper gepinnt. Die Baseline-Namen dort sind laut Bericht unverändert.
- Die Anweisung „Zeichen für Zeichen“ ist eingehalten (Blob-Gleichheit zum Probe-Commit), und der Bericht ist ehrlich: Lingering-timer-Fehler sind als Vorbestand benannt.

### Issues
#### Critical (Must Fix)
Keine.

#### Important (Should Fix)
Keine.

#### Minor (Nice to Have)
1. `tests/test_sensor_liveness_blocked.py:202-210` (`test_stamps_with_an_offset_are_read_on_has_clock`): Der Test unterscheidet nicht, ob ein Stempel auf HAs Uhr gelesen wird. Er läuft ohne `hass`-Fixture, `dt_util.DEFAULT_TIME_ZONE` ist dort UTC, `as_local` ist also die Identität. Eine Implementierung mit `.replace(tzinfo=None)` statt `as_local` bliebe grün. Er pinnt nur, dass `end` überhaupt durch `coerce_stamp` läuft (ohne Coercion: `TypeError` naiv/aware in `blocked_spans`). Es ist auch nur `end` aware, nicht `start`. Der Zonen-Pfad ist am Wrapper durch `tests/test_silent_sensor_commit.py:~140-150` (mit `hass`-Fixture, US/Pacific) gepinnt, daher kein Loch im Gesamtbild. Zum Härten hier: `dt_util.set_default_time_zone(<Zone ≠ UTC>)` mit Rückstellung im `finally` (Muster `tests/test_precipitation_guard.py:37`), und `start` mit Offset testen.
2. Docstrings mit veralteten oder vorgreifenden Querverweisen, nach dem Branch-Ende nachzuziehen:
   - `calculation.py:417-419`: „the function the live estimate asks too“ ist heute falsch (siehe ⚠️).
   - `sensor_liveness.py:190-193` (`cuts_field`): „The commit's gate (calculation._blocked_spans_for_zone) and the notice both ask here“. Seit diesem Commit fragt `zone_blocked_spans` (selbes Modul, `:265`) `cuts_field`, nicht mehr das Gate direkt. Transitiv bleibt es richtig, aber ungenau.
   - `sensor_liveness.py:12-14`: nennt weiter nur „its daily calculation“ und die Methode als Quelle.
3. `tests/test_sensor_liveness_blocked.py:165-169` (`test_the_calculation_form_is_not_asked`): `is not None` pinnt das fehlende Gate, würde aber auch bei falschen Spannen grün bleiben. Besser auf die erwarteten Spannen vergleichen (`== {"Temperature": ((T0 + 5 * H, T0 + 10 * H),)}`). Kein Fehlerrisiko, nur Schärfe.
4. `tests/test_sensor_liveness_blocked.py:179-185`: „kein Anfang“ ist nur mit `None` getestet. Ein nicht lesbarer String (`coerce_stamp` → `None`, `sensor_liveness.py:144`) ist derselbe Zweig und laut Docstring von `coerce_stamp` der eigentliche Anlass für das No-raise-Verhalten. Ein zusätzlicher `assert … "garbage" … is None` kostet eine Zeile.

### Assessment
**Task quality:** Approved
**Reasoning:** Die Extraktion ist verhaltensgleich zur alten Methode (Wasserstand-Guard fällt über das leere Fenster sauber weg, Gate und Signatur bleiben), die Funktion deckt den Interface-Vertrag vollständig ab, und die neuen Tests prüfen echtes Verhalten mit allen `None`-Zweigen. Es bleiben nur Minor-Punkte: ein nicht-trennscharfer Zeitzonen-Test, ein vorgreifender Docstring und Testschärfe.
