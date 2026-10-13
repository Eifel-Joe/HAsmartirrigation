### Spec Compliance
- ✅ Spec compliant. Der Diff entspricht Step 3 und Step 4 des Tasks: Aufruf bei `calculation.py:1533-1534` direkt nach dem Kc-Block und vor `bucket-was`. Die Methode `_silent_sensor_explanation` steht bei `calculation.py:1884-1917` am Dateiende, wie die Hinweise es verlangen. Die Test-Klasse `TestTheExplanation` steht bei `tests/test_silent_sensor_commit.py:472-519`.
- ✅ Die Sprachdateien habe ich per Python geparst (read-only).
  - Alle 8 Dateien (`de en es fr it nl no sk`) sind gültiges JSON.
  - Beide Schlüssel stehen jeweils als letzte im Block `module.calculation.explanation`.
  - Die Platzhalter sind in allen 8 Sprachen gleich: `{end}`, `{fields}`, `{start}` bzw. `{share}`.
  - Die Zeilenenden sind durchgehend CRLF (1228 `\r\n` gleich 1228 `\n`), es gibt kein BOM.
  - Der Diff enthält keine Zeilenende-Rauschen (+113/−8).
- ✅ Die Feldnamen-Schlüssel `panels.mappings.cards.mapping.items.<field.lower()>` existieren in allen 8 Sprachen für alle 11 Felder, auch für die mit Leerzeichen (`solar radiation`, `maximum temperature`, `minimum temperature`, `current precipitation`).
- ✅ Die Platzhalter werden vollständig aufgelöst. Die einzigen Ersetzungsstellen sind `calculation.py:1908-1910` und `:1916`, und sie decken `{fields}`, `{start}`, `{end}` und `{share}` ab.
  - Die Panel-Quelle `frontend/src` referenziert `module.calculation.explanation.*` nicht. Das Panel zeigt die fertige Zeichenkette per `unsafeHTML(zone.explanation)` (`view-zone-settings.ts:1900`), also löst nur das Backend Platzhalter auf. `localize.py` liest dieselben JSON-Dateien über `LANGUAGE_FILES_DIR`.
  - `tests/test_i18n_completeness.py` prüft fehlende Schlüssel, verwaiste Schlüssel, Platzhalter-Gleichheit und englische Kopien über beide Kataloge.
- ⚠️ Die Bundles in `dist/` enthalten die neuen Schlüssel erst nach dem Neubau in Task 8. Das ist im Plan so vorgesehen und für die Backend-Ausgabe unschädlich.
- ⚠️ Mit eingeschalteter Stundenrechnung bekommt eine pausierende Gruppe keinen Satz, weil das Gate dann `None` liefert (`calculation.py:433-434`). Das ist wie in Spec und Plan gewollt und durch `test_a_pausing_group_under_the_hourly_calculation_matches_too` (`tests/test_silent_sensor_commit.py:456`, inkl. Explanation) abgedeckt.

### Strengths
- **`keep` und `blocked=None`:** Eine Gruppe auf `keep`, ohne Ausfall im Fenster, ohne Verbindung oder mit Stundenrechnung bekommt `blocked=None` (`calculation.py:427-447`). Dann läuft `if blocked:` (`:1533`) ins Leere, die Erklärung bleibt byte-identisch.
  - Das pinnt `TestAGroupThatIsNotCutCalculatesAsBefore` schon über `ZONE_EXPLANATION` (`tests/test_silent_sensor_commit.py:429-466`).
  - Der neue fünfte Test (`:518`) pinnt es zusätzlich.
- **`share` und Satz 2:** `share` ist nur dann nicht `None`, wenn `blocked is not None`, das Modul Pflichtfelder hat (PyETO, Passthrough) und eine Wasserstandsmarke existiert (`calculation.py:1253-1262`). Die Bedingung `share is not None and share < 1` (`:1912`) erzeugt Satz 2 also nur, wenn wirklich ein Anteil unter 1 gebucht wurde.
- **Satz 2 deckt sich mit der Buchung:** Der Pfad `hourly is not None` skaliert nicht mit `share`. Er ist nur bei eingeschalteter Stundenrechnung erreichbar (`_hourly_et_for_zone` liefert sonst `None`, `:971`), und dann ist `blocked` ohnehin `None`. Satz 2 behauptet also nie eine Skalierung, die nicht stattgefunden hat.
- **Keine Sätze, wo nichts gekappt wurde:** Für ein Feld, das das Modul nicht braucht, ist `share` genau 1.0, also kein Satz 2. Das pinnt der Test bei `:500-510` mit `<` statt `<=`. Für Static ist `share` `None`, das pinnt der Test bei `:512`. Eine reine Regenzähler-Sperre taucht nicht in `blocked` auf, weil das Gate Delta-Aggregate ausfiltert (`:445`).
- **Ein Satz je Sperre:** Felder mit gleicher Sperre werden zusammengefasst, Reihenfolge `sorted(fields)` nach Konstante. Die Erwartung "Dewpoint, Temperature" bei Eingabe `(T, DEW)` (`:479-492`) pinnt die Sortierung und das Zusammenfassen. Das `.lower()` im Schlüssel pinnt derselbe Test.
- **Zeiten:** Es sind naive Stempel auf HAs Uhr, formatiert mit `%Y-%m-%d %H:%M` (`:1909-1910`). Ein offener Ausfall endet im Satz bei `now`. Der Test prüft Start gleich Ausfallbeginn plus 3 h (05:00) und das Ende.
- **Prozent:** `f"{share * 100:.0f}"` entspricht der Vorgabe. 19/24 ergibt 79,17 und im Test "79".
- **Reihenfolge der Sätze:** Sie stehen nach dem Kc-Satz und vor `bucket-was`. Der Test prüft `index("(sensor silent)") < index("Bucket was")`.
- **Verweise:** In den hinzugefügten Zeilen gibt es keine Verweise auf Issues, Spec- oder Plan-Kürzel.

### Issues
#### Critical (Must Fix)
Keine.

#### Important (Should Fix)
Keine.

#### Minor (Nice to Have)
1. `calculation.py:1912-1916` (Format plan-vorgegeben): Ein Anteil knapp unter 1 oder knapp über 0 wird gerundet angezeigt und liest sich widersprüchlich.
   - Eine Sperre kürzer als etwa 7 Minuten in einem 24-h-Fenster ergibt "…booked for 100 % of the period." direkt hinter "No values from … (sensor silent)". Ein Ausfall, der nur wenig länger als die 3 h Überbrückung dauert, macht das realistisch.
   - Ein Anteil unter 0,5 % ergibt "0 %", obwohl `share != 0` und also gebucht wurde.
   - Die Aussage ist nicht falsch, aber irreführend. Ein Test dafür fehlt.
   - Ein Vorschlag wäre, den angezeigten Wert auf 1..99 zu klemmen, solange `0 < share < 1` gilt. Das weicht allerdings vom Plan-Wortlaut ab; die Entscheidung liegt beim Menschen.
2. `tests/test_silent_sensor_commit.py:472-519`: Der Zweig `share == 0` der Erklärung ist ungepinnt. Das ist der Fall, in dem ein Pflichtfeld das ganze Fenster stumm war ("booked for 0 %").
   - Die Buchungs-Tests für diesen Fall (`:312-335`, `:361-380`) prüfen die Erklärung nicht.
   - Ein Mutant `share < 1` zu `0 < share < 1` oder zu `if share and share < 1` würde unbemerkt durchgehen.
   - Vorschlag: einen Test mit PyETO und `outages=[_outage(-10, fields=(DEW,))]` ergänzen, der "booked for 0 % of the period" erwartet.
3. `tests/test_silent_sensor_commit.py:494-498`: Die Reihenfolge mehrerer Sätze (`sorted(fields_by_span.items())`, `calculation.py:1900`) ist ungepinnt. Der Test zählt nur und prüft ein Teilstück. Ohne `sorted` bleibt die Reihenfolge bei einem Feld gleich; sie unterschiede sich erst bei zwei Feldern mit versetzten Sperren.
4. Kc ungleich 1 zusammen mit Teilanteil ist ungetestet. Das ist keine Falschaussage, nur eine Lesbarkeitsprüfung.
   - `et_term` im Kc-Satz (`calculation.py:1531`) ist der unskalierte Modulwert. Die Folge liest sich so: "(Kc 0.80 × -2.00)", dann Satz 1 und "79 %".
   - Der Leser kann rekonstruieren: -2,00 × 0,80 × 0,79 ≈ -1,27. Die Sätze stehen in der Reihenfolge der Skalierungen und passen zusammen.
   - Der `hour_multiplier` (Fenster ungleich 24 h) fehlt weiter, wie schon vorher.
   - Der Kc-Satz vor dem Anteilssatz ist nicht gepinnt. Vorschlag: einen Test mit `kc=0.8` und Teilanteil, der die Reihenfolge der Sätze prüft.
5. `calculation.py:1535-1540` (vorbestehend, im Task ausdrücklich nicht zu beheben): Hinter dem letzten neuen Satz folgt "Bucket was" ohne Leerzeichen, also "…period.Bucket was 0.00". `bucket-was` hat kein führendes Leerzeichen. Der Fehler bestand schon hinter dem Delta- und dem Kc-Satz, wird aber jetzt in einer weiteren Variante sichtbar.
6. Nur zur Information, vom Plan so vorgegeben (Test `:512`, Review-Focus "Static-Zone"): Satz 1 erscheint auch für Zonen, deren Modul das Feld gar nicht nutzt (Static, oder PyETO bei nur gesperrter Sonne). Die Aussage "No values from X (sensor silent)" ist wahr und behauptet keine Buchungsfolge, kann aber so gelesen werden.

### Assessment
**Task quality:** Approved
**Reasoning:** Die Umsetzung ist plangetreu. Gruppen und Zonen ohne Sperre bleiben byte-identisch, Satz 2 erscheint nur bei einem wirklich gebuchten Teilanteil, und die acht Sprachen sind vollständig, gültig und platzhalter-gleich. Offen bleiben nur Minor-Punkte: ungepinnte Sonderfälle (`share == 0`, Satzreihenfolge, Kc mit Teilanteil) und die gerundete Anzeige "100 %" oder "0 %" bei Randanteilen.