### Spec Compliance

- ✅ Spec compliant. Geprüft gegen Brief/Spec §1 (Einheit), §2.1, §2.6, §4 und den freigegebenen Wortlaut:
  - Gate fällt: `calculation.py:431-444` (`_blocked_spans_for_zone` ruft nur noch `zone_blocked_spans`; Docstring nennt alle Formen). `hourly_calculation_enabled` bleibt in `calculation.py` definiert und in Gebrauch (`:125`, `:186`, `:934`), kein toter Import.
  - Hinweis/Log: `sensor_liveness.py:618-626` `_group_cuts` = `group_pauses(mapping)`, lokaler Import samt Kommentar weg. Beide Aufrufer (`:562` Log-Text, `:635` `_stale_issue_key`) hängen damit nur noch an *pausieren* + `cuts_field`; die WARNING-Texte (`:564-572`) sind formneutral und unverändert (Spec §4: „Hinweistexte unverändert“).
  - Neu-Synchronisieren: der Block in `async_update_config` (`__init__.py`, alt `:1246-1250`) entfällt; der verbleibende Aufrufer `async_resync_stale_issue` (`__init__.py:1842`, Einstellungs-/Zuordnungswechsel) bleibt. `git grep` über `custom_components` und `tests`: keine weitere Stelle, die auf den Stundenschalter reagiert.
  - Kommentare/Docstrings (`sensor_liveness.py` Modul + `_group_cuts` + `async_resync_stale_issue`, `const.py:715-718`, `weather_aggregate.py:346-350`, `calculation.py`) sind angepasst; ein `git grep` nach „daily form / hourly calculation off / only without the hourly / still used“ über `custom_components/*.py` findet keine weitere veraltete Stelle außerhalb von `live_estimate.py` (Task 6) und `sensor_liveness.py:572` (die korrekte *behalten*-Variante).
  - Panel-Hilfe: nur der letzte Satz fällt, in allen 8 Sprachen je 1 Zeile (Diff); alle 8 Dateien parsen als JSON und enden korrekt (de „…zählt weiter.“, en „…still counts.“, usw.). Keine neuen Schlüssel.
  - Bundles: im Commit-Baum steht in keinem der 4 Bundles mehr „Applies only while“ (`git show … | grep -c` = 0 je Bundle); die Hilfe-Literale in `irrigation-plus.js` und `irrigation-plus-card-impl.js` habe ich gegen `1160abc5` verglichen: genau der Satz fehlt, sonst gleich (nur Quote-Form `'…\'…'` -> `"…'…"` durch den Minifier). Stat: genau 2 Bundles, je 1 Zeile.
  - Doku Z. 59/62: englische Fassung stimmt mit dem freigegebenen deutschen Wortlaut überein (Pflichtfelder Tagesform Temperatur/Taupunkt/Wind/Druck, Stundenform Temperatur/Luftfeuchte/Wind/Sonne, Passthrough Verdunstungssensor; Stunde-für-Stunde-Satz; Tagesform-Mittelung; Zeitanteil-Satz mit nachts stummer Sonne). Der erste Satz des freigegebenen Absatzes („Die Live-Schätzung lässt dieselbe Zeit aus …“) fehlt hier planmäßig (späterer Task); der bestehende Satz „With the live estimate, a run during an outage can be sized on more evapotranspiration …“ bleibt und ist in diesem Stand noch wahr. Inhalt deckt sich mit Spec §2.3/§2.4 (Gewicht = Zeitanteil über die Pflichtmenge; Anteil zählt Zeit).
  - Globale Regeln: kein Store-Feld/Versionssprung, keine neuen Übersetzungsschlüssel, keine Verweise auf Fork-Issues, `Task N`, `G…`, „PR 2/PR 3“ in den hinzugefügten Zeilen (Diff gelesen; das bestehende `(#188)` im Moduldocstring ist Kontext, nicht Teil des Diffs). Commit-Message und Trailer wörtlich nach Plan (`git log -1`).
  - Testnamen: die vier umgedrehten Tests tragen die Namen aus dem Plan; die alten zwei Namen entfallen (laut Controller bestätigt).
- ⚠️ Nicht aus dem Diff prüfbar: (a) Die Bundle-Diffs selbst (Einzeiler, vom Controller als byte-gleich zum Probe-Build geprüft; ich habe nur das Literal verglichen). (b) Vorwärtsverweise, die erst mit der Live-Task wahr werden: `sensor_liveness.py:13-14` („… the time its calculation and its live estimate do not book“) und `calculation.py:435-436` („… the function the live estimate asks too“). In diesem Stand ruft `live_estimate.py` `zone_blocked_spans` noch nicht (`git grep zone_blocked_spans`: nur `calculation.py`, `sensor_liveness.py`, `weather_aggregate.py`-Docstrings). Planvorgabe wörtlich; der Controller sollte nach der Live-Task prüfen, dass beides stimmt. (c) Der in `docs/configuration-sensor-groups.md:62` verbliebene Interims-Satz zur Live-Schätzung muss in der Live-Task durch den freigegebenen ersten Satz ersetzt werden. (d) Ich habe keine Tests gestartet; RED/GREEN-Belege stammen aus dem Bericht (4 failed -> 4 passed, 2 bekannte Teardown-ERROR).

### Strengths

- Der Commit ist exakt die „Einheit“ aus der Spec: Gate, Hinweis, Log, Re-Sync, Panel-Hilfe, Bundles und Doku in einem Schritt, nachdem Task 4 den Stundenzweig gebucht hat; kein Zwischenstand mit falscher Erklärung.
- Die Blob-Hashes im Bericht stimmen mit den `index`-Zeilen des Diffs und der Plan-Diffs überein; Test-/Code-Änderungen sind minimal und gezielt.
- Umgedrehte Tests prüfen echtes Verhalten und haben Zähne: `test_switching_the_hourly_calculation_leaves_the_notice_alone` (`test_sensor_liveness_coordinator.py:1068-1081`) schlägt fehl, sobald der Re-Sync-Aufruf zurückkehrt (die Meldung würde von `{}` auf einen `translation_key` umgeschrieben), und prüft beide Richtungen des Schalters in einer Schleife; `test_under_the_hourly_calculation_too_they_are_no_longer_used` pinnt Schlüssel UND beide Log-Richtungen (`"no longer used"` vorhanden, `"still used"` fehlt); `test_the_hourly_calculation_is_cut_the_same` pinnt die exakten halboffenen Grenzen `[W+5h, W+10h)` (gleiche Werte wie der Tagesform-Gate-Test daneben).
- `test_a_pausing_group_under_the_hourly_switch_is_cut_too` rechnet über den echten `async_calculate_zone`-Pfad und prüft Delta (`-4.0 * 19/24`), den unveränderten Vergleichswert der *behalten*-Gruppe (`-4.0`) und den Erklärungssatz „79 %“ (19/24 = 79,2 %) — Gate-Wegfall, Sperre und Anteil in einem Test.
- Der Docstring-Satz „so the balance still reconciles with the aggregate's precipitation“ nennt den ursprünglichen Grund des Gates und sagt, warum er entfällt.
- Gruppen auf *behalten* bleiben unberührt: `zone_blocked_spans` liefert für sie weiter `None`, `_group_cuts` ist `False`, der Re-Sync hat für sie nie anderes getan.

### Issues

#### Critical (Must Fix)
Keine.

#### Important (Should Fix)
Keine.

#### Minor (Nice to Have)

1. `tests/test_silent_sensor_commit.py:467` (Klasse `TestAGroupThatIsNotCutCalculatesAsBefore`, `:437`): Der umgedrehte Test behauptet jetzt einen Schnitt, steht aber in einer Klasse, deren Name „wird nicht geschnitten, rechnet wie vorher“ sagt. Wer die Klasse liest, bekommt das Gegenteil des Testinhalts. Besser in `TestTheBooking` (`:285`) verschieben oder die Klasse umbenennen. **plan-mandated** (Platzierung steht so im Plan-Diff); Polish, kein Blocker.
2. `tests/test_silent_sensor_commit.py:124-130` / `:467-482`: Kein Test fährt die *echte Stundenform* (gemessene Sonne) durch `async_calculate_zone` mit dem Gate. Die Naht ist stückweise abgedeckt (Gate-Test; `TestTheCommitCarriesTheSpans` für die Weitergabe an `calculate_module`; Task-4-Tests rufen `_aggregate_for_zone`/`calculate_module(blocked=…)` direkt und umgehen damit das Gate), der Endzustand „Schalter an + Sonne gemessen + pausierende Gruppe über `async_calculate_zone`“ wird erst vom Live-Test/Task-10 gesehen. Ein einzelner Test mit `_readings()` aus `test_silent_sensor_hourly_commit.py` würde die Naht schließen. Coverage-Wunsch, kein Defekt.
3. `sensor_liveness.py:618-626`: `_group_cuts` ist jetzt ein Einzeiler `return group_pauses(mapping)` ohne Gebrauch von `self`; die zwei Aufrufer (`:562`, `:635`) könnten `group_pauses(mapping)` direkt rufen. Der Name dokumentiert aber die Absicht („schneidet diese Gruppe“) und der Plan schreibt den Code wörtlich vor; daher nur Polish. **plan-mandated**.

### Assessment

**Task quality:** Approved
**Reasoning:** Der Task setzt Spec §1 „Einheit“ und §4 vollständig und wörtlich nach Plan um (Gate, Hinweis, Log, Re-Sync, 8 Sprachen + 2 Bundles, Doku nach freigegebenem Wortlaut), die umgedrehten Tests pinnen jede Entscheidung mit echtem Verhalten, und *behalten*-Gruppen bleiben unberührt; offen sind nur Minor-Punkte (Testklassen-Platzierung, eine fehlende Ende-zu-Ende-Naht) und zwei Vorwärtsverweise, die erst mit der Live-Task wahr werden.
