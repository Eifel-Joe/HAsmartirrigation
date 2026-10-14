# Bericht Task 5 — Das Gate fällt (Hinweis, Log, Panel-Hilfe, Doku)

Status: **DONE** (keine Abweichung vom Plan).
Commit: **`60ac780b`** (`feat(liveness): a pausing group is cut under the hourly calculation too`), Branch
`feat/pause-silent-sensor-hourly-live`, direkt auf `1160abc5`. Nach dem Commit: `git status --short` leer.
Probe-Commit `3333f841` / Vorgänger `27e7b551` wurden **nicht** angesehen (kein Schiedsrichter-Bedarf, Regel 9 nicht genutzt).

## Was umgesetzt wurde

- Step 1: vier Tests umgedreht (Edit-Werkzeug, CRLF blieb erhalten):
  - `tests/test_sensor_liveness_coordinator.py`: `test_under_the_hourly_calculation_too_they_are_no_longer_used`,
    `test_switching_the_hourly_calculation_leaves_the_notice_alone`
  - `tests/test_silent_sensor_commit.py`: `test_the_hourly_calculation_is_cut_the_same`,
    `test_a_pausing_group_under_the_hourly_switch_is_cut_too`
- Step 3: `calculation.py` (`_blocked_spans_for_zone` ohne Stunden-Gate, Docstring), `sensor_liveness.py`
  (Moduldocstring, `_group_cuts` = `group_pauses(mapping)` ohne lokalen Import, `async_resync_stale_issue` Docstring),
  `__init__.py` (Re-Sync-Block in `async_update_config` entfällt), `const.py` (Kommentar), `weather_aggregate.py`
  (Docstring `aggregate_window`).
- Step 4: Panel-Hilfe, letzter Satz in 8 Sprachen entfernt.
- Step 5: `docs/configuration-sensor-groups.md` (Zeile 59 und 62, Wortlaut aus dem Plan).
- Step 6: Bundles gebaut, die zwei anderen per `git checkout --` zurückgesetzt.

Beleg für Wörtlichkeit: Die `index`-Zeilen (Blob-Hashes nach dem Edit) im gestagten Diff sind **identisch** mit denen der
Plan-Diffs: `__init__.py 68630f03..29a729cd`, `calculation.py cc432db1..07d66f9f`, `const.py 592dad2d..68a2fc87`,
`sensor_liveness.py f45f3eda..0c009009`, `weather_aggregate.py 6d21067f..aa2684b5`,
`docs/configuration-sensor-groups.md a474e7b4..42f7f1cf`, `test_sensor_liveness_coordinator.py b503f756..004ccad1`,
`test_silent_sensor_commit.py 4cfad275..3b4283b9`. Die Dateien sind damit byte-gleich zum getesteten Probe-Stand.

## Step 2 — RED

```
K="test_the_hourly_calculation_is_cut_the_same or test_a_pausing_group_under_the_hourly_switch_is_cut_too or test_under_the_hourly_calculation_too_they_are_no_longer_used or test_switching_the_hourly_calculation_leaves_the_notice_alone"
TZ=UTC /d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests/test_silent_sensor_commit.py tests/test_sensor_liveness_coordinator.py -p _local_socket_unblock -q -k "$K"
```

Relevante Ausgabe (vollständig in `sdd/tmp/t5-red.txt`):

```
E   AssertionError: assert None == {'Temperature': ((datetime.datetime(2026, 7, 1, 5, 0), datetime.datetime(2026, 7, 1, 10, 0)),)}
      (test_the_hourly_calculation_is_cut_the_same: das Gate liefert unter Stundenrechnung noch None)
E   assert -4.0 == -3.1666666666666665 ± 3.2e-06
      (test_a_pausing_group_under_the_hourly_switch_is_cut_too: nichts geschnitten, -4.0 statt -4.0*19/24)
E   AssertionError: assert 'weather_sensor_stale' == 'weather_sensor_stale_paused'
      (test_under_the_hourly_calculation_too_they_are_no_longer_used; Log noch "its last value is still used")
E   AssertionError: assert {'is_fixable'...07-01 07:00'}} == {}
      (test_switching_the_hourly_calculation_leaves_the_notice_alone: Re-Sync schreibt die Meldung noch um)
FAILED  ...TestTheGate::test_the_hourly_calculation_is_cut_the_same
FAILED  ...TestAGroupThatIsNotCutCalculatesAsBefore::test_a_pausing_group_under_the_hourly_switch_is_cut_too
FAILED  ...TestThePausedNotice::test_under_the_hourly_calculation_too_they_are_no_longer_used
FAILED  ...TestThePausedNotice::test_switching_the_hourly_calculation_leaves_the_notice_alone
ERROR   ... (2 x teardown "Lingering timer", lokaler Vorbestand)
================= 4 failed, 82 deselected, 2 errors in 3.18s ==================
```

Erwartet und gemessen: identisch zum Probelauf (`4 failed, 82 deselected, 2 errors`). Die Tests scheitern, weil das Gate
und die Stunden-Bedingungen im Code noch stehen.

## Step 4 — `strip_help.py`

Vergleich: Plan-Block per Write-Werkzeug nach `sdd/tmp/strip_help_plan.py` geschrieben; `wc -c` beide 1622 Bytes,
`cmp strip_help.py sdd/tmp/strip_help_plan.py` --> `IDENTICAL`. Vorhandene Datei ausgeführt:

```
/d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -I ../strip_help.py custom_components/irrigation_plus/frontend/localize/languages
de.json: removed
en.json: removed
es.json: removed
fr.json: removed
it.json: removed
nl.json: removed
no.json: removed
sk.json: removed
```

`git diff --stat -- .../languages`: 8 Dateien, je `2 +-` (1 Zeile). Alle 8 JSON-Dateien parsen weiter; Zeilenenden
unverändert (je 1234 CRLF = 1234 LF, kein loses CR).

## Step 6 — Bundles

`node --version` = v24.15.0; `npm ci && npm run build` ohne Fehler (nur die bekannten rollup-Hinweise zu `output.name`
und die npm-audit-Meldung). `git status --short -- .../dist` direkt nach dem Build: alle 4 Bundles `M`.
Nach `git checkout -- irrigation-plus-card.js irrigation-plus-card-legacy.js`:

```
 M custom_components/irrigation_plus/frontend/dist/irrigation-plus-card-impl.js
 M custom_components/irrigation_plus/frontend/dist/irrigation-plus.js
irrigation-plus-card-impl.js 0
irrigation-plus-card-legacy.js 0
irrigation-plus-card.js 0
irrigation-plus.js 0
```

(`grep -c 'Applies only while'` je Bundle: 0.) Zusätzlich: die 7 anderen Satzanfänge (`Gilt nur, solange`, `Solo se aplica
mientras`, ...) kommen in keinem der beiden geänderten Bundles vor (je 0; die Bundles enthalten nur den englischen Text).

Inhaltsprüfung der beiden geänderten Bundles gegen `HEAD` (Skript `sdd/tmp/bundle_diff.py`/Inline): Außerhalb des einen
Literals `'Pause: after 3 hours without a report, ...'` sind sie **byte-identisch** zu `HEAD` (`rest identical: True`,
beide Bundles); Differenz 80 Bytes je Bundle. Im Literal fällt genau der Satz
` Applies only while "Hourly evapotranspiration" (Experimental features) is off.` weg; der Minifier wechselt dabei die
Quote-Form von `'...\'...'` auf `"...'..."` (Folge der entfallenen `"` im Satz, kein inhaltlicher Eingriff).

## Step 7 — GREEN

Gleicher Befehl wie Step 2 (`sdd/tmp/t5-green.txt`):

```
ERROR tests/test_silent_sensor_commit.py::TestTheGate::test_the_hourly_calculation_is_cut_the_same
ERROR tests/test_silent_sensor_commit.py::TestAGroupThatIsNotCutCalculatesAsBefore::test_a_pausing_group_under_the_hourly_switch_is_cut_too
================= 4 passed, 82 deselected, 2 errors in 3.19s ==================
```

Die 2 ERROR sind Teardown-"Lingering timer" (lokaler Vorbestand, Regel 3).

## Step 8 — Lint und Vergleich

```
uvx black custom_components/irrigation_plus/   -->  All done!  70 files left unchanged.   (Exit 0)
uvx ruff@0.16.10 check custom_components/irrigation_plus/   -->  All checks passed!
```

`../task_compare.sh t5 tests/test_silent_sensor_commit.py tests/test_sensor_liveness_coordinator.py tests/test_sensor_liveness_blocked.py tests/test_i18n_completeness.py tests/test_silent_sensor_hourly_commit.py tests/test_silent_sensor_setting.py tests/test_sensor_liveness_repair.py`:

```
baseline names missing now: 2
ERROR tests/test_silent_sensor_commit.py::TestAGroupThatIsNotCutCalculatesAsBefore::test_a_pausing_group_under_the_hourly_calculation_matches_too
ERROR tests/test_silent_sensor_commit.py::TestTheGate::test_with_the_hourly_calculation_nothing_is_cut
new FAILED: 0
new ERROR per file:
      2 ERROR tests/test_silent_sensor_commit.py
      8 ERROR tests/test_silent_sensor_hourly_commit.py
======================= 204 passed, 44 errors in 31.77s =======================
```

Entspricht der Erwartung: genau die zwei alten Namen entfallen (die umbenannten), keine neuen FAILED, neue ERROR nur
2 + 8. `sdd/classify_new_errors.py task-t5-base.txt task-t5-names.txt task-t5.txt` --> alle 10 neuen Namen `ok`,
`UNEXPECTED: 0`. Zusätzlich: 44 ERROR in der Datei, 44 x `Failed: Lingering timer`, kein Setup-ERROR.

## Step 9 — Commit

```
git add <9 Dateien/Verzeichnisse laut Task>
git add -f custom_components/irrigation_plus/frontend/dist/
git diff --cached --name-only | wc -l
18
```

Die 18 Dateien: 5 Python (`__init__.py`, `calculation.py`, `const.py`, `sensor_liveness.py`, `weather_aggregate.py`),
8 Sprachdateien, 2 Bundles (`irrigation-plus.js`, `irrigation-plus-card-impl.js`), `docs/configuration-sensor-groups.md`,
2 Testdateien. Commit-Message wörtlich aus dem Task (Heredoc), letzte Zeile
`Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`. Ergebnis: `[feat/pause-silent-sensor-hourly-live 60ac780b]`,
`18 files changed, 50 insertions(+), 63 deletions(-)`. `git status --short` danach leer.

## Selbstreview des Diffs (nach Staging, vor und nach dem Commit)

- Wörtlich zum Plan: ja (Blob-Hashes siehe oben).
- Nur Task-Dateien: ja, 18 Dateien, keine weiteren; kein `.venv`/`node_modules`/`package-lock`-Eintrag im Status.
- Zeilenenden: alle geänderten Python-/Test-/Doku-/JSON-Dateien weiter reines CRLF in der Arbeitskopie (Byte-Zählung
  `\r\n == \n == \r`); Index LF.
- Genau 2 Bundles, nur die eine Hilfezeile (siehe Step 6).
- Verbotene Verweise: `grep` auf die hinzugefügten Zeilen nach `Eifel-Joe`, `JustChr`, `#<Zahl>`, `PR <n>`, `Task <n>`,
  `spec §`, `G<n>`, `F<n>` --> keine Treffer (Exit 1). Das bestehende `(#188)` im Moduldocstring von
  `sensor_liveness.py` ist Vorbestand und nicht Teil des Diffs.

## Abweichungen vom Plan

Keine. Verwendete Hilfsmittel jenseits des Plans: `sdd/classify_new_errors.py` (nur lesend, Zusatzprüfung der neuen
ERROR), ein Byte-Vergleich der zwei Bundles gegen `HEAD` (nur lesend). Probe-Commit nicht benutzt.
