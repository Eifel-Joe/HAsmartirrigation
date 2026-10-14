# Review Task 9 — Ein Ausfall frischt die Live-Schätzung auf (`ca0955f8..e5d184e3`)

### Spec Compliance
- ✅ Spec compliant. Geprüft gegen Brief und Spec §3.4 (zweiter Teil), mit der freigegebenen Abweichung (ungedrosselt):
  - Auslöser: `_async_check_mapping_liveness` gibt `bool(opened or closed) and group_pauses(mapping)` zurück
    (`sensor_liveness.py:603`); es gibt in der Methode keinen vorzeitigen `return` (Zeilen 538-603), jeder Pfad
    erreicht diese Zeile. `async_check_sensor_liveness` sammelt das Flag und ruft **nach** der Schleife genau einmal
    `_refresh_estimates_after_outage_change` (`:507-520`), also einmal je Prüfung, nicht je Gruppe.
  - Ungedrosselt: `getattr(self, "async_refresh_zone_estimates", None)` (`:530`), nicht `..._throttled`. Die Begründung im
    Docstring stimmt mit dem Code überein: `LIVE_ESTIMATE_MIN_REFRESH_SECONDS = 60`
    (`live_estimate.py:128`), `SENSOR_LIVENESS_INTERVAL_SECONDS = 300` (`const.py:699`), die gedrosselte Variante
    verwirft innerhalb von 60 s (`live_estimate.py:1904-1909`).
  - Plan-Review-Focus („Neuberechnung wirft, Prüfung läuft durch und hält den Ausfall fest“): Der Ausfall wird in
    `_async_check_mapping_liveness` (`:567-571`) geschrieben, bevor die Auffrischung läuft; die Auffrischung hängt in
    eigenem `try/except Exception` (`:533-536`); Test `test_a_refresh_that_fails_leaves_the_check_intact`.
  - Gruppe auf *behalten*: Rückgabe `False` (wegen `group_pauses`), `cut_changed` bleibt `False`, keine zusätzliche
    Neuberechnung; Test `test_a_group_that_keeps_does_not`. Sonst unverändert (Rückgabetyp `None` -> `bool` ist der
    einzige Unterschied; es gibt keinen weiteren Aufrufer von `_async_check_mapping_liveness` im Repo, per Grep).
  - Kein Store-Feld, keine Übersetzung, keine Verweise auf Issues/Task-/PR-Kürzel im Diff (Code, Tests, Commit-Zeile).
  - Diff entspricht Zeichen für Zeichen dem Plan-Diff (Controller-Prüfung bestätigt).
- ⚠️ Cannot verify from diff: Die Spec selbst nennt in §3.4 (`…-pr3-design.md:195-196`) und in der G11-Zeile (`:41`) noch
  `async_refresh_zone_estimates_throttled`. Code und Spec widersprechen sich jetzt an dieser Stelle; die Abweichung ist
  freigegeben, aber nur im Plan festgehalten. Spec nachziehen (Controller), sonst „repariert“ später jemand den Code
  zur Spec hin (siehe Important unten).
- ⚠️ Cannot verify from diff: Ob ein Wechsel von `on_silent_sensor` bei offenem Ausfall die Schätzung auffrischt (Spec
  §3.4 behandelt ihn nur über den Übertrags-Schlüssel; der Brief verlangt für Task 9 nur Öffnen/Schließen). Gehört nicht
  zu diesem Task, liegt in anderem Code.

### Strengths
- Kleinster möglicher Eingriff: Rückgabewert statt zweitem Mechanismus; Auffrischung einmal nach der Schleife, damit alle
  Gruppen ihre Store-Schreibvorgänge hinter sich haben und der NOT-TO-DO (kein Yield zwischen Lesen und Zurückschreiben
  einer Gruppe) unberührt bleibt.
- Fehlerisolierung richtig geschnitten: die Auffrischung steht außerhalb des per-Gruppe-`try`, hat ein eigenes
  `except Exception` (kein `BaseException`, `CancelledError` bleibt durchlässig) und loggt mit `exc_info=True`. Der
  Stil (`# noqa: BLE001`, DEBUG) entspricht dem bestehenden Muster `irrigation.py:3315-3317`.
- Die Tests prüfen Verhalten am echten `SmartIrrigationCoordinator` (nur die Auffrischung ist gedoubelt) und töten die
  naheliegenden Mutationen: `if cut_changed` entfernt (Test 1), `and group_pauses` entfernt (Test 4), `opened`-only
  bzw. `closed`-only (Tests 3 bzw. 1), Auffrischung je Gruppe statt je Prüfung (Test 5), Ausnahme nicht abgefangen
  (Test 6), Dauerzustand löst bei jedem Lauf aus (Test 2).
- Die Gegenprobe „Ausfall bleibt offen -> kein zweiter Anstoß“ (Test 2) und „schließt -> zweiter Anstoß“ (Test 3) bilden
  den Zustandswechsel ab, nicht nur den Erstzustand.

### Issues

#### Critical (Must Fix)
Keine.

#### Important (Should Fix)
1. **Die zentrale, von der Spec abweichende Entscheidung „ungedrosselt“ ist durch keinen Test festgehalten**
   (`tests/test_sensor_liveness_coordinator.py:1235`, `sensor_liveness.py:530`) — **plan-mandated** (Testtext ist
   wörtlich vorgegeben), der Mensch entscheidet.
   Die Tests ersetzen nur `coord.async_refresh_zone_estimates` durch einen `AsyncMock`. Würde `:530` auf
   `"async_refresh_zone_estimates_throttled"` umgestellt (also genau die Spec-Fassung), liefen alle sechs Tests grün:
   die echte gedrosselte Methode liest `_zone_estimates_refreshed_at` (am `__new__`-Koordinator nicht gesetzt ->
   `None`, `live_estimate.py:1904-1906`) und ruft dann `self.async_refresh_zone_estimates()`, also den Mock; der Mock
   setzt den Zeitstempel nie, die Drossel greift in keinem Test. Der ganze Grund für die Abweichung (eine Pufferzeile
   < 60 s vor dem Öffnen schluckt den Anstoß, danach kommt bei stummer Station keine mehr) ist damit nur als Docstring
   gesichert, während die Spec-Texte (`:41`, `:195-196`) das Gegenteil sagen.
   Fix (test-only, 3 Zeilen): in `_silent_station` zusätzlich `coord.async_refresh_zone_estimates_throttled =
   AsyncMock()`; in `test_an_outage_that_opens_refreshes_the_estimates` danach
   `coord.async_refresh_zone_estimates_throttled.assert_not_awaited()`. Mutationsprobe: `:530` auf die gedrosselte
   Variante stellen -> der Test muss rot werden (Refresh-Mock `Awaited 0 times`).

#### Minor (Nice to Have)
1. `sensor_liveness.py:603` — dieselbe Frage („schneidet diese Gruppe?“) wird hier mit `group_pauses(mapping)`
   gestellt, `:583` und `:657` fragen über die Naht `self._group_cuts(mapping)`. Gleiches Ergebnis heute, aber zwei
   Schreibweisen für einen Begriff. Zudem löst auch ein Ausfall nur eines nicht geschnittenen Feldes
   (kumulierender Regenmesser, `cuts_field` False) einer pausierenden Gruppe eine Auffrischung aus; harmlos (eine
   zusätzliche Neuberechnung je Öffnen/Schließen) und von Plan/Spec so verlangt („pausierende Gruppe“), nur der
   Vollständigkeit halber.
2. `sensor_liveness.py:531-532` — der Wächter `if refresh is None: return` wird von keinem Test erreicht (beide Testdateien,
   die die Prüfung fahren, bauen den echten Koordinator, der die Methode hat) und ist im Verhalten gleich dem
   Ausnahmepfad: `await None()` wirft `TypeError`, den `except Exception` (`:535`) schluckt. Entfernte man den Wächter,
   bliebe jeder Test grün. Entweder weglassen oder mit einem Double ohne die Methode festnageln.
3. `tests/test_sensor_liveness_coordinator.py:1286-1290` (`test_a_refresh_that_fails_leaves_the_check_intact`) — ohne
   `assert_awaited_once()` auf dem `AsyncMock(side_effect=RuntimeError)` ist der Test leer, falls die Auffrischung gar
   nicht mehr aufgerufen wird (`store.mappings[1][SENSOR_OUTAGES]` ist ohnehin vor der Auffrischung geschrieben). Eine
   Zeile ergänzen, dann prüft er wirklich den Fehlerpfad.
4. `sensor_liveness.py:574-603` — Wirft nach dem Store-Schreiben (`:567-571`) noch etwas in der Gruppe
   (`_fire_weather_stale`, `_sync_stale_issue`), geht das Flag verloren: die nächste Prüfung sieht `kept == outages`,
   kein Öffnen/Schließen, und die Schätzung bleibt bis zum nächsten Poll/Commit/Lauf auf altem Stand. Schmal und
   begrenzt (dieselbe Lücke haben dort schon Ereignis und Notice); nur zur Kenntnis.
5. `tests/test_sensor_liveness_coordinator.py:213-231` (`_coord`) — die bestehenden Tests mit `_pausing(...)`-Gruppen
   (`:1004-1100`) rufen jetzt über den echten Koordinator die echte `async_refresh_zone_estimates` gegen `Mock`-`hass`
   und `_FakeStore` (ohne `config`) auf; sie scheitern dort vermutlich im verschluckten DEBUG-Pfad (welche Zeile genau
   wirft, nicht geprüft). Kein roter Test, aber unbeabsichtigte Kopplung; ein Standard-`AsyncMock` in `_coord` hielte
   sie aus dem Live-Pfad heraus.

Zur Controller-Frage (Geviertstrich in `sensor_liveness.py:535`, einziges Nicht-ASCII-Zeichen der Datei, sonst `--`):
kein Handlungsbedarf. Das Paket nutzt das schon (`batch.py:281`, `live_estimate.py:1872`), `BLE` ist in
`pyproject.toml` gar nicht ausgewählt (das `noqa` ist reine Kennzeichnung), Python liest UTF-8, ruff/black sind laut Bericht
sauber. Der Text ist plan-diktiert und identisch zum Probe-Commit; ich würde ihn so lassen.

### Assessment
**Task quality:** Needs fixes
**Reasoning:** Die Implementierung ist korrekt, klein und trifft Spec §3.4 samt freigegebener Abweichung; offen ist ein
rein testseitiger Punkt: die gerade deshalb bewusst von der Spec abweichende Entscheidung „ungedrosselt“ wird von keinem
der sechs Tests festgehalten (Umstellung auf die gedrosselte Variante bliebe grün), was als plan-mandated Lücke beim
Menschen liegt. Der Rest sind Minor-Punkte.
