# Task 10b — Bericht des Implementers

**Status:** DONE_WITH_CONCERNS (alle sechs Commits gebaut, alles grün; ein bestehender Test musste am Harness
angepasst werden — Abweichung 1, bitte prüfen).

Worktree `D:\Entwicklung\HASI\issue8-pr2-work\wt`, Branch `feat/pause-silent-weather-sensor`, Basis `a9708bec`.
`git status --short` am Ende leer. Hilfsskripte und Logs: `D:\Entwicklung\HASI\issue8-pr2-work\sdd\tmp\`
(`runtests.sh`, `c1_notice.py`, `c3_help.py`, `c4_docs.py`, `ast_nodoc.py`, `check_wording.py`, `check_help.py`,
`check_messages.py`, `*.log`). Kein Subagent, kein Push, kein stash/reset/rebase, keine HA-/MCP-Aktion.

Testbefehl überall: `sdd/tmp/runtests.sh <label> <dateien>` =
`TZ=UTC /d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest <dateien> -p _local_socket_unblock -q`
aus dem Worktree-Root, Ausgabe nach `sdd/tmp/<label>.log`; das Skript zählt zusätzlich die
`Lingering timer`-Teardown-Fehler und alle anderen `E   `-Zeilen.

Baseline vor C1 (die fünf Testdateien des Tasks): `121 passed, 28 errors` — alle 28 `Lingering timer after test`.

## Commits

| # | SHA | Subject |
|---|---|---|
| C1 | `720b9e84` | fix(liveness): the paused notice and log only where a field is actually cut |
| C2 | `e8365801` | fix(calculation): the share sentence never reads 100 % or 0 % against what was booked |
| C3 | `da6c4904` | fix(panel): the pause help says what it leaves out and names the hourly setting |
| C4 | `dbb49884` | docs: what a pause leaves out, and the sensors it catches unawares |
| C5 | `12a05a37` | docs(comments): no comment claims the hourly form or the live estimate is cut |
| C6 | `549d5e2e` | test: pin the edges of a pause the reviews found unpinned |

Alle sechs Messages per Skript gegen die Codeblöcke des Plantexts verglichen (`check_messages.py`): 6 × `OK`,
Zeichen für Zeichen inkl. Trailer `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## C1 — `720b9e84`

Geändert:
- `sensor_liveness.py`: neuer Modul-Helfer `cuts_field(field, mappings_config) -> bool` neben `group_pauses`
  (wahr außer bei `effective_aggregate(...) == MAPPING_CONF_AGGREGATE_DELTA`; Import
  `from .weather_aggregate import effective_aggregate` — kein Zyklus: `weather_aggregate` importiert nur `const`,
  `et_hourly`, `helpers`). Docstring: warum ein Regenzähler nie geschnitten wird.
  `_stale_issue_key(mapping_id, outages)`: Variante nur bei `_group_cuts(mapping)` und einem offenen Ausfall mit
  einem `cuts_field`-Feld (`config = mapping.get(MAPPING_MAPPINGS) or {}`, `mapping` aus dem Store wie bisher);
  `_sync_stale_issue` ruft es mit seinen `outages`, Signatur unverändert. WARNING-Schleife: Schnitt-Text nur bei
  `cuts and any(cuts_field(f, config) for f in outage.fields)`, sonst der bisherige „its last value is still used“.
  Schnitt-Text wörtlich (per AST-Konstante gegen den Plan geprüft: `True`).
- `calculation.py`: Gate-Filter jetzt `if cuts_field(field, config)`; der nun unbenutzte Import
  `effective_aggregate` entfällt, `cuts_field` kommt in den `sensor_liveness`-Import (von black mehrzeilig gesetzt).
- `__init__.py`: `if const.MAPPING_ON_SILENT_SENSOR in data or const.MAPPING_MAPPINGS in data:` mit Kommentar
  („that hangs on the setting and on which fields the group cuts“).
- `translations/*.json` (8): nur `issues.weather_sensor_stale_paused.description`, Absatz 1 komplett und letzter
  Satz von Absatz 2 (Skript `c1_notice.py`: dekodiert nur diese eine JSON-Zeile, Round-Trip-Prüfung vor dem
  Schreiben, Platzhalter `{since}`/`{entities}` je genau einmal). Titel, Absatz 3 und Rest von Absatz 2 unverändert
  (word-diff geprüft). de/en per `check_wording.py` gegen den Plantext: `de p1 OK, de p2 OK, en p1 OK, en p2 OK`.
- Tests `tests/test_sensor_liveness_coordinator.py`, Klasse `TestThePausedNotice`: Helfer `_rain_gauge_group`
  (pausierende Gruppe, Niederschlag als Sensor mit Aggregat `delta`, optional weitere Felder) und vier Tests:
  `test_a_silent_rain_gauge_alone_keeps_the_plain_notice`,
  `test_a_silent_temperature_beside_it_brings_the_paused_notice` (Log je Entität über `record.args[1]` geprüft),
  `test_a_rain_gauge_turned_rain_rate_rewrites_the_open_notice` (über `_FakeStore`, `async_update_mapping_config`
  mit `mappings`), `test_only_a_cumulative_rain_gauge_is_never_cut`.
- Zusätzlich (siehe Abweichung 1): `TestTheOutageRecordFollowsTheConfiguration::test_a_source_change_empties_the_record_and_drops_the_notice`.

**RED** (Tests geschrieben, Code unverändert) — `runtests.sh c1-red tests/test_sensor_liveness_coordinator.py`:
```
4 failed, 43 passed
test_a_silent_rain_gauge_alone_keeps_the_plain_notice:
  AssertionError: assert 'weather_sensor_stale_paused' == 'weather_sensor_stale'
test_a_silent_temperature_beside_it_brings_the_paused_notice:
  AssertionError: assert 'its last value is still used' in 'Sensor group Garden: sensor.rain (Precipitation)
  has not reported since 2026-07-01 08:59:59; its values are no longer used and no evapotranspiration is booked
  while it is silent'
test_a_rain_gauge_turned_rain_rate_rewrites_the_open_notice:
  AssertionError: assert 'weather_sensor_stale_paused' == 'weather_sensor_stale'
test_only_a_cumulative_rain_gauge_is_never_cut:
  AttributeError: module '...sensor_liveness' has no attribute 'cuts_field'
```
Erwartet: der alte Code wählt die Variante allein nach Gruppe/Stundenrechnung und schreibt für den Regenzähler den
Schnitt-Text; `cuts_field` gibt es noch nicht. (Test 2 scheitert am Log, sein Schlüssel stimmte schon.)

**Zwischenstand** nach `sensor_liveness.py` + Gate, vor `__init__.py` — `runtests.sh c1-mid …`:
`1 failed, 46 passed`; `test_a_rain_gauge_turned_rain_rate_rewrites_the_open_notice`:
`assert 'weather_sensor_stale' == 'weather_sensor_stale_paused'` — erwartet, der Re-Sync bei `mappings` fehlte noch.

**Nach `__init__.py`** — `runtests.sh c1-green …`: `1 failed, 46 passed`, jetzt der **bestehende**
`test_a_source_change_empties_the_record_and_drops_the_notice`:
`assert 'weather_sensor_stale_0' not in {'weather_sensor_stale_0': {... 'translation_key': 'weather_sensor_stale' ...}}`
→ Abweichung 1.

**GREEN** — `runtests.sh c1-green2 tests/test_sensor_liveness_coordinator.py`: `47 passed in 3.40s`.
Nachbarn (weil `async_update_mapping_config` geändert): `runtests.sh c1-neighbours tests/test_mapping_source_change.py
tests/test_sensor_liveness_repair.py tests/test_weather_buffer_one_frame.py tests/test_create_returns_id.py
tests/test_silent_sensor_commit.py`: `53 passed, 30 errors` (30 × Lingering timer, sonst keine `E`-Zeile).
Vor dem Commit — `runtests.sh c1-final tests/test_sensor_liveness_coordinator.py tests/test_silent_sensor_commit.py
tests/test_i18n_completeness.py tests/test_sensor_liveness_repair.py tests/test_mapping_source_change.py`:
`153 passed, 28 errors` (28 × Lingering timer).

## C2 — `e8365801`

Geändert: `calculation._silent_sensor_explanation`: `percent = round(share * 100)`, bei `share > 0` mindestens 1,
dann höchstens 99 (der Block läuft nur bei `share < 1`), eingesetzt als `str(percent)`; Kommentar mit dem Grund.
Tests in `TestTheExplanation`: `test_a_share_that_would_round_to_100_reads_99` (Ausfall 2 h bis 5 h 02 → 2 min
Sperre 05:00–05:02), `test_a_share_that_would_round_to_0_reads_1` (Ausfall −3 h bis 23 h 58 → 2 min gültig),
`test_a_field_blocked_throughout_books_0_percent` (PyETO, Taupunkt das ganze Fenster gesperrt). Der 79-%-Test bleibt.

**RED** — `runtests.sh c2-red tests/test_silent_sensor_commit.py -k TestTheExplanation`:
`2 failed, 6 passed, 24 deselected, 8 errors` (8 × Lingering timer); gescheitert die 99-%- und die 1-%-Probe; der
0-%-Pin grün wie im Plan erwartet. Tatsächlicher Text heute (`-vv`, `c2-red-vv.log`): „booked for 100 % of the
period“ bzw. „booked for 0 % of the period“.

**GREEN** — `runtests.sh c2-green tests/test_silent_sensor_commit.py`: `32 passed, 31 errors` (31 × Lingering timer,
keine andere `E`-Zeile).

## C3 — `da6c4904`

Geändert: `frontend/localize/languages/*.json` (8), nur `panels.mappings.cards.mapping.on-silent-sensor.help`
(Skript `c3_help.py`, prüft je Sprache, dass `panels.experimental.hourly_calculation.title` und
`panels.experimental.title` der Datei im neuen Text stehen). de/en per `check_help.py` gegen den Plan: `de OK, en OK`.
Quotes je Datei-Konvention: de/sk „…“, es/it/no «…», fr « … », nl “…”, en `\"…\"` (wie im Plantext).

- `npx vitest run` (Node v24.15.0): `Test Files 27 passed (27)`, `Tests 661 passed (661)`.
- `npm run build`: alle vier Bundles gebaut.
- `git add -f custom_components/irrigation_plus/frontend/dist/`; `git diff --cached --name-only | wc -l` = 10
  (8 Sprachdateien + **2 Bundles**), `… | grep dist/ | wc -l` = 2.
- **Abweichung von der Erwartung „nur `irrigation-plus-card-impl.js`“:** auch `irrigation-plus.js` hat sich
  geändert. Je 1 Zeile (`2 +-`); der word-diff beider Bundles zeigt ausschließlich den englischen Hilfetext
  (`help:"Pause: … without the hourly calculation."` → `help:'Pause: … while "Hourly evapotranspiration"
  (Experimental features) is off.'`). Beide Bundles betten `en.json` ein; `irrigation-plus.js` hat schon
  `2621a230` beim Einführen dieser Strings mitgeändert. Kein Bundle enthält die deutschen Texte.
- `runtests.sh c3-i18n tests/test_i18n_completeness.py`: `67 passed`.

## C4 — `dbb49884`

`docs/configuration-sensor-groups.md`, genau die fünf Ersetzungen (Skript `c4_docs.py` nimmt die Texte aus dem
Plantext selbst und prüft jedes alte Stück auf genau ein Vorkommen): Pause-Punkt bis vor „Rain from a cumulative rain
gauge“, Keep-Klammer, erster Satz des Stundenrechnungs-Absatzes, letzter Satz des Drei-Stunden-Absatzes, neuer Absatz
nach dem Absatz zu Sensoren ohne Gerät. `git diff --stat`: 1 Datei, `6 insertions(+), 4 deletions(-)`; der Diff
zeigt nur diese Stellen. Keine Tests betroffen.

## C5 — `12a05a37`

- `calculation.py`, Docstring `_blocked_spans_for_zone`: „The hourly form is not cut here: it would have to be cut
  together with the live estimate.“ Der Regenzähler-Satz verweist auf `sensor_liveness.cuts_field`
  („Which fields are blocked, ``sensor_liveness.cuts_field`` decides: never a cumulative rain gauge.“).
- `const.py`, Kommentar über `ISSUE_WEATHER_SENSOR_STALE_PAUSED`: „Chosen where the group's daily calculation really
  leaves the silent time out: a pausing group, the hourly calculation off, and an open outage with a field that is
  cut (see sensor_liveness.cuts_field).“
- `live_estimate.py`: Modul-Docstring („… exactly what the commit will see (but for a pausing sensor group's silent
  time; see ``_aggregate_live_window``);“), erste Zeile von `_aggregate_live_window` (Fortsetzungszeile „-- but for
  the one deliberate difference in the last paragraph.“), `_projected_extremes` („(but for a pausing sensor group's
  silent time; see ``_aggregate_live_window``)“), `_daily_mirror_et` („(a pausing sensor group's silent time aside;
  see ``_aggregate_live_window``)“, Absatz dafür neu umbrochen).

**Beleg „nur Kommentare/Docstrings“** — `ast_nodoc.py HEAD wt <3 Dateien>` vor dem Commit (AST ohne Docstrings
verglichen; Kommentare stehen nie im AST):
```
custom_components/irrigation_plus/calculation.py IDENTICAL without docstrings | with docstrings: differ
custom_components/irrigation_plus/const.py IDENTICAL without docstrings | with docstrings: identical
custom_components/irrigation_plus/live_estimate.py IDENTICAL without docstrings | with docstrings: differ
exit=0
```

## C6 — `549d5e2e`

Sieben Pins, alle sofort grün (kein roter Pin, kein Befund):
1. `test_silent_sensor_setting.py::test_the_mapping_view_leaves_an_omitted_setting_omitted` —
   `MAPPING_VIEW_SCHEMA({MAPPING_NAME: "x"}) == {MAPPING_NAME: "x"}`.
2. `test_silent_sensor_commit.py::TestTheGate::test_an_open_outage_blocks_up_to_the_commits_now` —
   `_outage(2)` offen → `{T: ((W + 5 * H, NOW),)}`.
3. `test_weather_aggregate_blocked.py::TestFieldsWithoutValidTime::test_a_carried_value_alone_is_not_filled_in_either`
   — Zeilen nur Taupunkt, `last_entry={T: 20.0}`, T ganz gesperrt → `T`, `MAX_TEMP`, `MIN_TEMP` fehlen.
4. `test_weather_aggregate_blocked.py::TestTwoSpansOnOneField` (Sperren 3–6 h und 12–18 h, Zeilen 0/2/8/20 h plus je
   eine eingefrorene in jeder Sperre): einfaches Mittel 25.0, zeitgewichtet 28.0, `riemannsum` 315.0 — Rechnung je im
   Kommentar.
5. `test_weather_aggregate_blocked.py::TestAWindowWithoutAWatermark::test_the_held_value_stands_in[average|maximum]`
   — `watermark=None`, zwei Zeilen am Fensterstart mit gleichem Stempel (10.0, 12.0), Sperre `[W, W+2h)`,
   `now = W+4h` → 12.0 (deckt `… if values else held[0]` und `elif not values`).
6. `test_sensor_liveness_blocked.py::TestBlockedSpans::test_outages_whose_spans_touch_merge` — 3–10 h und 10–14 h
   → eine Sperre 3–14 h.
7. `test_sensor_liveness_coordinator.py::TestThePausedNotice::test_a_keeping_group_switched_to_pause_gets_the_paused_notice`
   — `_FakeStore`, Gruppe auf `keep` mit offenem Hinweis (PR-1-Text), dann `on_silent_sensor: "pause"` → Variante.

`runtests.sh c6 <fünf Testdateien>`: `138 passed, 32 errors` (32 × Lingering timer; 121 + 4 + 3 + 10 neue Tests).

## Abschluss

- `runtests.sh final tests/test_sensor_liveness_coordinator.py tests/test_silent_sensor_commit.py
  tests/test_silent_sensor_setting.py tests/test_weather_aggregate_blocked.py tests/test_sensor_liveness_blocked.py
  tests/test_i18n_completeness.py`: `205 passed, 32 errors in 24.92s` — alle 32 `Lingering timer`, keine andere
  `E`-Zeile.
- `git status --short`: leer.
- Wortlaute am HEAD erneut geprüft: `check_wording.py` 4 × OK, `check_help.py` 2 × OK.
- Eigenbezug-Grep über `git diff a9708bec..HEAD` (nur `+`-Zeilen, inkl. dist) auf
  `Eifel-Joe|JustChr|#<zahl>|PR <n>|E1–E4|Task|10b|review|spec|§|F1–F5|Befund|N1–N7`: keine Treffer. In den Messages
  einziger Treffer „reviews“ im Subject von C6 — vom Plan wörtlich diktiert (Regel 6, Ausnahme).
- `git diff a9708bec..HEAD --stat`: 29 Dateien, alle in der Files-Liste des Plans.

## Lint

Vor jedem Commit `uvx black …` und `uvx ruff check custom_components/irrigation_plus/ --output-format concise | grep -v UP017`:
- C1: black `1 file reformatted` (die Testdatei; danach `71 files left unchanged`); ruff nur `Found 20 errors.` /
  `[*] 20 fixable with --fix.` — alle 20 UP017 (nach `grep -v UP017` bleibt nur die Zusammenfassung).
- C2: black `71 files left unchanged`; ruff dito 20 × UP017.
- C3, C4: black `--check` `70 files would be left unchanged`; ruff dito.
- C5: black `70 files left unchanged`; ruff dito.
- C6: black `75 files left unchanged` (inkl. der fünf Testdateien); ruff dito; zusätzlich `uvx ruff check` auf die
  fünf Testdateien: `All checks passed!`.

## Abweichungen vom Plantext

1. **C1, bestehender Test angepasst (Bedenken, bitte prüfen).** Nach Schritt 5 (Re-Sync auch bei `mappings`) schlug
   `TestTheOutageRecordFollowsTheConfiguration::test_a_source_change_empties_the_record_and_drops_the_notice` fehl:
   dessen Mock-Store (`_mock_store_coord`) liefert aus `get_mapping` immer das Mapping von **vor** dem Schreiben,
   also mit offenem Ausfall; der neue Re-Sync liest danach und hob den gerade von `_retire_outages` gelöschten
   Hinweis wieder an. Der echte Store aktualisiert `self.mappings` in `async_update_mapping` synchron
   (`attr.evolve`), der Re-Sync sieht dort den geleerten Ausfall-Datensatz und tut nichts; belegt durch den grünen
   Echt-Store-Test `test_sensor_liveness_repair.py::test_the_notice_goes_when_its_sensor_is_replaced` (in
   `c1-neighbours` und `c1-final`). Anpassung: im Test hält ein `side_effect` auf `async_update_mapping` das
   Geschriebene fest (`store.get_mapping.return_value = {**group, **changes}`, Kommentar dazu); keine Assertion
   geändert. Alternative wäre eine Produktionsänderung (Re-Sync bei Quellwechsel überspringen) gewesen — außerhalb
   des Plans, daher nicht gemacht. Der Fall ist genau das Muster, das C6-Pin 7 absichert (Abgleich liest nach dem
   Schreiben).
2. **C1, über den Plantext hinaus, aber zwingend/klein:** unbenutzten Import `effective_aggregate` aus
   `calculation.py` entfernt (sonst ruff F401); je ein Satz Docstring an `_group_cuts` („Which fields it leaves out,
   ``cuts_field`` says.“) und an `_stale_issue_key` (wann die Variante gilt), damit kein Kommentar wieder zu viel
   verspricht.
3. **C3:** 2 geänderte Bundles statt 1 (s. o.), beide nur der en-Hilfetext.
4. **sk, Hinweis Absatz 1:** „zavlažujú menej alebo vôbec“ → „… menej alebo vôbec nie“ — der Absatz wird ohnehin
   komplett aus dem Englischen („less or not at all“) übersetzt; der alte Text hatte keine Verneinung.
5. **C5, `_aggregate_live_window`:** die Einschränkung steht als Fortsetzung der ersten Zeile
   („… will --“ / „but for the one deliberate difference in the last paragraph.“), statt den Satz zu kürzen.
6. **Zusätzliche Testläufe** (sequenziell, einzeln, keine volle Suite): nach C1 die Nachbardateien
   `test_mapping_source_change.py`, `test_sensor_liveness_repair.py`, `test_weather_buffer_one_frame.py`,
   `test_create_returns_id.py`, weil `async_update_mapping_config` geändert wurde — alle grün.
7. **Zeilenenden:** `test_silent_sensor_commit.py`, `test_silent_sensor_setting.py`,
   `test_weather_aggregate_blocked.py`, `test_sensor_liveness_blocked.py` sind in der Arbeitskopie schon seit
   früheren Tasks reines LF (nicht gemischt); git meldet „LF will be replaced by CRLF“, der Diff zeigt nur die
   geänderten Zeilen. Nicht angefasst.

## Übersetzungen es fr it nl no sk (zur Prüfung)

Begriffe: Regenzähler = es *pluviómetro*, fr *pluviomètre*, it *pluviometro*, nl *regenmeter*, no *nedbørsmåler*,
sk *zrážkomer* (die Dateien hatten noch keinen Begriff dafür). „still counts“ ist als „wird weiter gebucht/gezählt“
übersetzt, mit dem Buchungsverb der jeweiligen Datei (es *contabilizar*, fr *compter*, it *conteggiare*, nl *telt mee*,
no *teller med*, sk *započítavať*). Template-Sensor: es *sensor de plantilla*, fr *capteur de modèle*, it *sensore
template*, nl *template-sensor*, no *malsensor*, sk *šablónový senzor* (Begriffe der Dateien: plantillas, modèles,
template, templates, maler, šablóny). Optionsname = `on-silent-sensor.keep` der Sprache; Einstellung/Bereich =
`panels.experimental.hourly_calculation.title` / `panels.experimental.title` der Sprache.

### es

Option name in the panel (`on-silent-sensor.keep`): Mantener el último valor; setting: Evapotranspiración horaria; area: Funciones experimentales

Notice, paragraph 1 (complete):

> Irrigation Plus no tiene noticias de {entities} desde {since}. Tras tres horas sin datos, esos valores dejan de usarse; un pluviómetro se sigue contabilizando. Donde el cálculo de la evapotranspiración no puede prescindir de alguno de ellos, no se contabiliza evapotranspiración para el tiempo sin valores; por eso las zonas que dependen de ellos riegan menos o nada hasta que lleguen valores nuevos.

Notice, last sentence of paragraph 2:

> Si la integración solo se actualiza cada pocas horas, o el sensor solo informa cuando cambia su valor (por ejemplo, un sensor de plantilla sin dispositivo que se queda en 0 mientras no hay viento), pon el grupo de sensores en «Mantener el último valor»; si no, cada vez falta una parte del tiempo.

Panel help (`panels.mappings.cards.mapping.on-silent-sensor.help`):

> Pausar: tras 3 horas sin informar, los valores del sensor dejan de usarse; donde el cálculo de la evapotranspiración no puede prescindir de ellos, no se contabiliza evapotranspiración para ese tiempo. Un pluviómetro se sigue contabilizando. Solo se aplica mientras «Evapotranspiración horaria» (Funciones experimentales) esté desactivada.

### fr

Option name in the panel (`on-silent-sensor.keep`): Garder la dernière valeur; setting: Évapotranspiration horaire; area: Fonctionnalités expérimentales

Notice, paragraph 1 (complete):

> Irrigation Plus n’a plus de nouvelles de {entities} depuis {since}. Après trois heures de silence, ces valeurs ne sont plus utilisées ; un pluviomètre reste compté. Là où le calcul de l’évapotranspiration ne peut se passer de l’une d’elles, aucune évapotranspiration n’est comptée pour le temps sans valeurs : les zones qui en dépendent arrosent donc moins, voire pas du tout, jusqu’à l’arrivée de nouvelles valeurs.

Notice, last sentence of paragraph 2:

> Si l’intégration ne se met à jour qu’à quelques heures d’intervalle, ou si le capteur n’envoie une mesure que lorsque sa valeur change (par exemple un capteur de modèle sans appareil qui reste à 0 tant qu’il n’y a pas de vent), réglez le groupe de capteurs sur « Garder la dernière valeur » ; sinon, une partie du temps manque à chaque fois.

Panel help (`panels.mappings.cards.mapping.on-silent-sensor.help`):

> Mettre en pause : après 3 heures sans mesure, les valeurs du capteur ne sont plus utilisées ; là où le calcul de l’évapotranspiration ne peut s’en passer, aucune évapotranspiration n’est comptée pour cette durée. Un pluviomètre reste compté. Ne s’applique que tant que « Évapotranspiration horaire » (Fonctionnalités expérimentales) est désactivée.

### it

Option name in the panel (`on-silent-sensor.keep`): Mantieni l’ultimo valore; setting: Evapotraspirazione oraria; area: Funzioni sperimentali

Notice, paragraph 1 (complete):

> Irrigation Plus non riceve notizie da {entities} dal {since}. Dopo tre ore di silenzio questi valori non vengono più usati; un pluviometro continua a essere conteggiato. Dove il calcolo dell’evapotraspirazione non può fare a meno di uno di essi, per il tempo senza valori non si conteggia evapotraspirazione; per questo le zone che ne dipendono irrigano meno o per niente finché non arrivano nuovi valori.

Notice, last sentence of paragraph 2:

> Se l’integrazione si aggiorna solo ogni poche ore, o il sensore invia dati solo quando il suo valore cambia (ad esempio un sensore template senza dispositivo che resta a 0 finché non c’è vento), imposta il gruppo di sensori su «Mantieni l’ultimo valore»: altrimenti ogni volta manca una parte del tempo.

Panel help (`panels.mappings.cards.mapping.on-silent-sensor.help`):

> Metti in pausa: dopo 3 ore senza dati, i valori del sensore non vengono più usati; dove il calcolo dell’evapotraspirazione non può farne a meno, per quel tempo non si conteggia evapotraspirazione. Un pluviometro continua a essere conteggiato. Vale solo finché «Evapotraspirazione oraria» (Funzioni sperimentali) è disattivata.

### nl

Option name in the panel (`on-silent-sensor.keep`): Laatste waarde behouden; setting: Verdamping per uur; area: Experimentele functies

Notice, paragraph 1 (complete):

> Irrigation Plus heeft sinds {since} niets meer van {entities} gehoord. Na drie uur stilte worden deze waarden niet meer gebruikt; een regenmeter telt nog steeds mee. Waar de verdampingsberekening niet zonder een van deze waarden kan, wordt voor de tijd zonder waarden geen verdamping geboekt; zones die ervan afhangen, beregenen daardoor minder of helemaal niet tot er nieuwe waarden binnenkomen.

Notice, last sentence of paragraph 2:

> Werkt de integratie maar om de paar uur bij, of meldt de sensor alleen wanneer zijn waarde verandert (zoals een template-sensor zonder apparaat die bij windstilte op 0 blijft), zet de sensorgroep dan op ‘Laatste waarde behouden’, anders ontbreekt elke keer een deel van de tijd.

Panel help (`panels.mappings.cards.mapping.on-silent-sensor.help`):

> Pauzeren: na 3 uur zonder melding worden de waarden van de sensor niet meer gebruikt; waar de verdampingsberekening niet zonder deze waarden kan, wordt voor die tijd geen verdamping geboekt. Een regenmeter telt nog steeds mee. Geldt alleen zolang “Verdamping per uur” (Experimentele functies) uit staat.

### no

Option name in the panel (`on-silent-sensor.keep`): Behold siste verdi; setting: Timesvis evapotranspirasjon; area: Eksperimentelle funksjoner

Notice, paragraph 1 (complete):

> Irrigation Plus har ikke hørt fra {entities} siden {since}. Etter tre timer uten signal brukes ikke disse verdiene lenger; en nedbørsmåler teller fortsatt med. Der fordampningsberegningen ikke klarer seg uten en av dem, bokføres det ingen fordampning for tiden uten verdier; soner som er avhengige av dem, vanner derfor mindre eller ikke i det hele tatt til nye verdier kommer inn.

Notice, last sentence of paragraph 2:

> Oppdateres integrasjonen bare med noen timers mellomrom, eller rapporterer sensoren bare når verdien endres (for eksempel en malsensor uten enhet som blir stående på 0 så lenge det ikke blåser), sett sensorgruppen til «Behold siste verdi», ellers mangler en del av tiden hver gang.

Panel help (`panels.mappings.cards.mapping.on-silent-sensor.help`):

> Sett på pause: etter 3 timer uten rapport brukes ikke sensorens verdier lenger; der fordampningsberegningen ikke klarer seg uten dem, bokføres det ingen fordampning for den tiden. En nedbørsmåler teller fortsatt med. Gjelder bare så lenge «Timesvis evapotranspirasjon» (Eksperimentelle funksjoner) er av.

### sk

Option name in the panel (`on-silent-sensor.keep`): Ponechať poslednú hodnotu; setting: Hodinová evapotranspirácia; area: Experimentálne funkcie

Notice, paragraph 1 (complete):

> Irrigation Plus od {since} nedostal nič od {entities}. Po troch hodinách ticha sa tieto hodnoty prestanú používať; zrážkomer sa naďalej započítava. Tam, kde sa výpočet evapotranspirácie bez niektorej z nich nezaobíde, sa za čas bez hodnôt nezapočíta žiadna evapotranspirácia; zóny, ktoré od nich závisia, preto zavlažujú menej alebo vôbec nie, kým neprídu nové hodnoty.

Notice, last sentence of paragraph 2:

> Ak sa integrácia aktualizuje len raz za niekoľko hodín alebo senzor hlási len vtedy, keď sa zmení jeho hodnota (napríklad šablónový senzor bez zariadenia, ktorý pri bezvetrí zostáva na 0), nastav skupinu senzorov na „Ponechať poslednú hodnotu“, inak zakaždým chýba časť času.

Panel help (`panels.mappings.cards.mapping.on-silent-sensor.help`):

> Pozastaviť: po 3 hodinách bez hlásenia sa hodnoty senzora prestanú používať; tam, kde sa výpočet evapotranspirácie bez nich nezaobíde, sa za tento čas nezapočíta žiadna evapotranspirácia. Zrážkomer sa naďalej započítava. Platí len, kým je „Hodinová evapotranspirácia“ (Experimentálne funkcie) vypnutá.

