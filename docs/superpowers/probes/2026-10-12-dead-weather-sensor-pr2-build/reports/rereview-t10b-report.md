# Re-Review der Fix-Welle (Sonnet), a9708bec..549d5e2e — vom Controller aus der Rückmeldung zusammengefasst

Verdikt: **alle Befunde erledigt, keine neue Critical/Important-Breakage.**

- Befund 1 (Hinweis/Log): ADDRESSED — `cuts_field` (sensor_liveness.py:186-198) von Gate (calculation.py:451),
  `_stale_issue_key` (:597-612) und Log (:537) genutzt; der Hinweis liest die an `_sync_stale_issue` übergebenen
  Ausfälle (:581), nicht den Store; Re-Sync bei `mappings` (__init__.py:1844) liest nach dem synchronen Store-Update.
- Befund 2 (gerätelose Sensoren): ADDRESSED — Hinweis-Satz in allen 8 Sprachen, Doku-Absatz; Rat „Helfer am Gerät“
  durch `_entities_of_device` gedeckt.
- 3 (Rückfall-Zweige): ADDRESSED — `TestAWindowWithoutAWatermark` (average + maximum), von Hand nachgerechnet.
- 4 (Rundung): ADDRESSED — calculation.py:1925-1928; Tests 99 % / 1 % / 0 % (0,9986 und 0,0014 nachgerechnet).
- 5 (Kommentare): ADDRESSED — AST-Vergleich ohne Docstrings identisch für calculation.py, const.py, live_estimate.py.
- 6/7 (Name der Einstellung, Doku-Wortlaut): ADDRESSED.
- 8a–8g (Pins): ADDRESSED, jeder Pin tötet den genannten Mutanten.
- Mock-Anpassung in `test_a_source_change_empties_the_record_and_drops_the_notice`: getreues Double
  (`{**group, **changes}` = `attr.evolve`), Produktionspfad durch
  `test_sensor_liveness_repair.py::test_the_notice_goes_when_its_sensor_is_replaced` gedeckt.
- Übersetzungen es/fr/it/nl/no/sk per Skript: keep-Label wörtlich, Name der Einstellung und des Bereichs wörtlich,
  Platzhalter unverändert, Anführungszeichen je Datei, Inhalt wie das Englische; sk „vôbec nie“ richtig.
- Minor (danach per Pin `030e12a3` erledigt): Filter `if outage.end is None` in `_stale_issue_key` (:608) ungepinnt.
- Out of scope: weather_aggregate.py:525 wiederholt die delta-Ausnahme inline (Importrichtung); live_estimate.py:596
  „agree by construction“ ohne Zusatz (durch erste Zeile und letzten Absatz gedeckt).
