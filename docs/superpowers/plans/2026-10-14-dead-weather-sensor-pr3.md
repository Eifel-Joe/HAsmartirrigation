# Stummer Wettersensor, PR 3 (Stundenpfad und Live-Schätzung) — Implementierungsplan

> **Für agentische Ausführung:** PFLICHT-SKILL: `superpowers:subagent-driven-development` (empfohlen) oder
> `superpowers:executing-plans`, Task für Task. Schritte nutzen Checkboxen (`- [ ]`).

**Ziel:** Eine Sensorgruppe auf *pausieren* bucht für die Zeit, in der ein Sensor stumm war, in **jeder** Rechenform
nichts mehr — Commit in Tages- und Stundenform, nachgespielte Bilanz und Live-Schätzung; jede Gruppe auf *behalten*
rechnet, erklärt und schätzt byte-identisch wie heute.

**Architektur:** Eine freie Funktion `zone_blocked_spans(store, zone, start, end)` in `sensor_liveness.py` liefert die
Sperren eines Fensters; der Commit ruft sie einmal (ab Wasserzeichen), die Live-Schätzung einmal je Neuberechnung (ab
ihrem Anker) und reicht sie als `blocked=` an jeden Leser des Puffers. Im Reduzierer hält eine maskierte Tabelle je
gesperrtem Feld nur dessen gültige Zeit: Stundenzeilen mitteln darüber und werden nur für die gemeinsam gemessene Zeit
der Stunden-Pflichtfelder berechnet (eine ganz gesperrte Stunde bleibt als Zeile ohne ET), die Klarheitsquote nimmt nur
Proben außerhalb der Sperren, die Teilschritte legen ET nur in gemessene Zeit, eine gesperrte Regenrate zählt nur ihre
gemessenen Anteile. Der Anteil richtet sich nach der Form, die lief (`required_sensor_fields`). Das Gate aus PR 2 fällt.

**Tech-Stack:** Python 3.12 (lokale Test-Env), Home Assistant 2024.12.5 über `pytest-homeassistant-custom-component`;
Frontend nur Neubau der Bundles (Node 24).

**Spec:** `docs/superpowers/specs/2026-10-14-dead-weather-sensor-pr3-design.md` (freigegeben 2026-10-14), dazu für alles,
was sie nicht neu entscheidet, die PR-2-Spec `2026-10-11-dead-weather-sensor-pr2-design.md` und Rev. 3
`2026-10-03-dead-weather-sensor-design.md`. Zitiert als „Spec PR 3 §N“ bzw. „G1“–„G12“.

**Freigabe:** Plan, Doku-Wortlaut (Abschnitt *Wortlaute*) und die vier Abweichungen von der Spec (Selbstprüfung am Ende)
vom User freigegeben am 2026-10-14; Ausführung **subagent-driven** in einer frischen Sitzung. Teil A = Tasks 1–5, Teil
B = Tasks 6–9.

**Probelauf (2026-10-14, gegen `6fa424e8`):** Tasks 1–9 testgetrieben in einem Wegwerf-Worktree
(`D:\Entwicklung\HASI\issue8-pr3-work\probe-wt`, losgelöst), die Code- und Test-Blöcke dieses Plans sind **aus diesen
Commits erzeugt** (Generator `issue8-pr3-work\make_plan.py`), nicht abgetippt.
- Je Task RED vor GREEN, danach die betroffenen Testdateien mit Namensvergleich gegen die Baseline; Lint sauber.
- **Volle Suite:** 7 failed / **3989 passed** / 9 skipped / 487 errors gegen die Baseline 7 / 3925 / 9 / 466 desselben Commits
  (`6fa424e8`, gemessen 2026-10-13). +64 passed = die neuen Fälle (9 + 17 + 9 + 10 + 8 + 5 + 6); FAILED-Namen identisch;
  es entfallen nur die zwei in Task 5 umbenannten Namen; die neuen ERROR-Namen sind alle Teardown-Fehler „Lingering
  timer“ der Tests mit echtem Koordinator (`test_live_estimate_silent_sensor.py` 8, `…_daily.py` 5,
  `test_silent_sensor_hourly_commit.py` 8, die 2 umbenannten in `test_silent_sensor_commit.py`), „Lingering timer“
  932 → 974 (= 2 × 21).
- **Mutationen:** **37/37 getötet**, jede vom in Task 10 genannten Killer; jede Quelle danach byte-gleich (sha256), `git diff --quiet
  HEAD` sauber (`issue8-pr3-work\mutate-pr3.py`, Ergebnis `mutate-final.txt`, `mutations-final.json`). Im ersten Lauf
  überlebte eine Mutation (eine gleichwertige Bedingung in `zone_blocked_spans`, entfernt) und eine wurde nur von einem
  fremden Test gefangen (der Spiegel-Gleichlauf merkte ein ungeschnittenes Aggregat nicht → verschärft).
- **RED-Erwartungen:** je Task mechanisch gemessen — Stand des Vorgängers plus nur die Tests des Tasks, dann die
  RED-Zeile dieses Plans (`issue8-pr3-work\red_check.sh`, Ergebnis `red-check.txt`); alle neun wie angegeben.
- Beim Probelauf berichtigt: zwei eigene Testfehler (Regen landet am Ende seines Intervalls; Testszene mit einer
  Stunde-1-Sperre und ungleichem `hourly_et`), ein echter Befund (Regen direkt vor einer Sperre landete erst bei der
  nächsten Probe → Zuwächse werden an den Sperrgrenzen geteilt, Task 2), drei zu schwache Tests, jeweils durch eine
  überlebende oder falsch gefangene Mutation bzw. beim Lesen aufgefallen (Klarheitsquote mit stundengenauer Sperre;
  Übertrag mit `now` genau auf der vollen Stunde; Spiegel-Gleichlauf, den ein ungeschnittenes Aggregat nicht störte →
  Temperatur in der Sperre jetzt eingefroren), eine gleichwertige Bedingung entfernt (`start >= end` in
  `zone_blocked_spans`), ein Bestandstest mit fester Lambda-Signatur (Task 6), eine eingefrorene Zeile genau auf `now` im
  Fixture (Task 8, halboffene Sperre); ergänzt: der Test „Fenster beginnt in einer Sperre“ (Review Focus).
- Getesteter Stand: `D:\Entwicklung\HASI\issue8-pr3-work\probe-2026-10-14.patch`. **Weicht ein Block dieses Plans vom
  Patch ab, gilt der Patch**; die Abweichung dann im Plan berichtigen.

## Global Constraints

- Basis = PR-2-Kopf `6fa424e8` (Branch `feat/pause-silent-weather-sensor`, upstream PR 197 offen); alle Zeilenangaben dort,
  in `custom_components/irrigation_plus/`. Neuer Branch `feat/pause-silent-sensor-hourly-live` von `6fa424e8` (G1).
- Kein Store-Versionssprung, kein neues Store-Feld; der Übertrag `_HourlyCarry` lebt nur im Speicher.
- Keine neuen Übersetzungsschlüssel. Panel-Hilfe `panels.mappings.cards.mapping.on-silent-sensor.help`: nur der letzte
  Satz fällt, in allen 8 Sprachen (`de en es fr it nl no sk`).
- Sperre = `[start + 3 h, end)`, halboffen; ein offener Eintrag sperrt bis zum `end` des Aufrufers (Commit: sein `now`;
  Live: `inputs["now"]`). Eine Pufferzeile genau auf diesem `end` zählt als gemessen.
- Pflichtmengen: Stundenform `HOURLY_ROW_REQUIRED` = Temperatur, Feuchte, Wind, Sonne; Tagesform
  `_REQUIRED_SENSOR_FIELDS` aus PR 2; ausgegeben von `required_sensor_fields(module_name, *, hourly=False)`.
- Mit `blocked=None`, `blocked={}` oder Sperren nur fremder Felder laufen `build_hourly_rows`, `build_substeps`,
  `hourly_eto_priced`, `eto_hourly_series` und die Live-Leser wie bisher (Tests vergleichen mit `==`).
- Keine Verweise auf Fork-Issues, Spec-/Plan-Kürzel (`G1`–`G12`, `Task N`) oder „PR 2/PR 3“ in Code, Tests, Doku,
  Commit-Messages; ein upstream-PR heißt in Fork-Commits „upstream PR 197“.
- Lint nur `uvx black` und `uvx ruff@0.16.10 check` auf `custom_components/irrigation_plus/` — ruff 0.17 meldet UP017 in
  Dateien, die dieser Branch nicht anfasst.

## Review Focus

- **Ein Fenster, das in einer Sperre beginnt:** Die Randzeile trägt den Wert des toten Sensors; in der Sperre zählt sie
  nicht, nach der Sperre gilt sie als Wert von davor (F2). Erwartet: gesperrte Stunden ohne ET, die Stunden danach mit dem
  Randwert (Test in Task 2).
- **Ausfall-Einträge mit Offset-Stempeln** (von Hand editiert, anderer Build): die Live-Schätzung wirft nicht, sie schneidet
  wie mit naiven Stempeln (Test in Task 1).
- **Eine Gruppe auf *behalten* mit Ausfällen im Speicher:** Live-Schätzung, Übertrag und Commit unverändert (Tests in
  Task 6 und, aus PR 2, `test_keep_with_outages_and_pause_without_one_match_a_plain_group`).
- **Nur der Druck stumm:** keine Stunde verliert Zeit, der Höhendruck springt ein (Test in Task 2).
- **Die Neuberechnung nach einem Ausfall wirft:** die Liveness-Prüfung läuft durch und hält den Ausfall fest (Test in
  Task 9).

---

## Rahmen

- **Dieser Plan ist PR 3 von dreien**, gestapelt auf PR 2 (G1). Der PR an JustChr geht erst nach dem Merge von upstream PR
  197 raus (Task 12); bis dahin entstehen Branch, Pre-Release und Live-Test.
- **Liefer-Reihenfolge:** Task 0 → Teil A (Tasks 1–5) → Teil B (Tasks 6–9) → Task 10 (Lint, volle Suite, Mutationen,
  Review) → Task 11 (Pre-Release, Live-Test HA-Test) → Task 12 (nach dem Merge von PR 197: umsetzen, PR, Nachlauf).
  Alles, was nach außen geht (Push, Release, PR, Kommentare, Issue-Änderungen), nur nach Freigabe im Chat; Texte vorher
  zeigen, deutsch, dann englisch. Vor jedem Außen-Schritt eine Upstream-Runde (Memory `upstream-sweep-first`).
- **Einheit (Spec PR 3 §1):** Task 5 entfernt das Gate erst, wenn Task 4 den Stundenzweig richtig bucht. Kein Commit
  dazwischen darf „Gate weg, Stundenzweig ungeschnitten“ sein.
- **Testbefehl** (aus dem Worktree; dort gibt es kein eigenes `.venv`):
  `TZ=UTC /d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest <pfad> -p _local_socket_unblock -q`
- **„Grün“ lokal:** Tests mit einem echten `SmartIrrigationCoordinator` enden lokal mit einem Teardown-ERROR „Lingering
  timer“, auch wenn der Test bestanden hat (Vorbestand; Memory `hasi-local-test-env-rebuild`). „Alle grün“ heißt hier:
  kein FAILED, ERRORs nur dieser Art, jede neue Testfunktion `passed`. Neue Dateien mit solchen Tests:
  `tests/test_silent_sensor_hourly_commit.py`, `tests/test_live_estimate_silent_sensor.py`,
  `tests/test_live_estimate_silent_sensor_daily.py`.
- **Namensvergleich je Task** (Schritt „Prüfen“): die betroffenen Testdateien laufen lassen, FAILED/ERROR-Namen gegen die
  Baseline dieser Dateien vergleichen — kein Baseline-Name entfällt (außer den in Task 5 umbenannten), keine neuen FAILED.
  Skript: `D:\Entwicklung\HASI\issue8-pr3-work\task_compare.sh <label> <testdateien…>` (Task 0, Schritt 4).
- **Frontend:** nur in Task 5 — `cd custom_components/irrigation_plus/frontend && npm ci && npm run build`; danach ändern
  sich genau 2 Bundles (`irrigation-plus.js`, `irrigation-plus-card-impl.js`), die anderen zwei nur im Zeilenende →
  `git checkout --` auf sie. `dist/` ist ignoriert, die Bundles getrackt → `git add -f`, Dateizahl prüfen.
- **Uhr:** Puffer-, Ausfall- und Fensterstempel sind naiv auf HAs Uhr; die neuen Tests übergeben naive Zeiten direkt
  (`now=`) oder nutzen die Fixtures von `tests/test_live_estimate_replayed_balance.py`.
- **Commit-Messages** englisch, WAS und WARUM, Schluss `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`;
  mehrzeilig per `git commit -F - <<'EOF' … EOF`. Die unten vorgegebenen Messages wörtlich.
- **Zeilenenden:** Die Quell- und Testdateien liegen im Worktree mit LF. Python-Skripte, die Dateien umschreiben, schreiben
  per Temp-Datei + `os.replace` mit `newline=""`; Doku und Übersetzungen byte-genau (CRLF bleibt, wo es ist).

## Dateien

| Datei | Verantwortung |
|---|---|
| `custom_components/irrigation_plus/sensor_liveness.py` | `zone_blocked_spans`; Hinweis/Log ohne Stundenbedingung; Neuberechnung nach Öffnen/Schließen |
| `custom_components/irrigation_plus/weather_aggregate.py` | `HOURLY_ROW_REQUIRED` öffentlich; maskierte Tabelle; Stundenzeilen, Klarheitsquote, Regenzuwächse, Teilschritte unter Sperren |
| `custom_components/irrigation_plus/et_estimate.py` | `hourly_eto_priced(…, blocked=)`; leere Zeile → ET 0 |
| `custom_components/irrigation_plus/calculation.py` | Hülle `_blocked_spans_for_zone` ohne Gate; `required_sensor_fields`; Anteil nach Form; Sperren an Stundenzeilen und Teilschritte |
| `custom_components/irrigation_plus/live_estimate.py` | Sperren einmal je Neuberechnung an alle Leser; Übertrags-Schlüssel; Spiegel × Anteil; Hochrechnung |
| `custom_components/irrigation_plus/__init__.py` | Re-Sync beim Umschalten der Stundenrechnung entfällt |
| `custom_components/irrigation_plus/const.py` | Kommentar |
| `custom_components/irrigation_plus/frontend/localize/languages/*.json` (8) | Panel-Hilfe: letzter Satz fällt |
| `custom_components/irrigation_plus/frontend/dist/*.js` (2 von 4) | neu gebaut |
| `docs/configuration-sensor-groups.md` | Pflichtfelder je Form; Absatz zu Stundenform, Live-Schätzung, Anteil |
| `tests/test_sensor_liveness_blocked.py` | + `zone_blocked_spans` |
| neu: `tests/test_hourly_rows_blocked.py` | Stundenzeilen, Klarheitsquote, Regen, `hourly_eto_priced` |
| neu: `tests/test_substeps_blocked.py` | Teilschritte unter Sperren |
| neu: `tests/test_silent_sensor_hourly_commit.py` | Commit in der Stundenform; Pflichtmengen je Form |
| `tests/test_silent_sensor_commit.py`, `tests/test_sensor_liveness_coordinator.py` | PR-2-Zwischenstand umgedreht; Neuberechnung nach Ausfall |
| neu: `tests/test_live_estimate_silent_sensor.py` | Live-Schätzung, Stundenquelle, Übertrag, aktuelle Temperatur, Regen |
| neu: `tests/test_live_estimate_silent_sensor_daily.py` | Tagesform-Spiegel, kein Rückfall auf den Wetterdienst, Hochrechnung |
| `tests/test_live_estimate_replayed_balance.py` | Test-Double nimmt die neuen Schlüsselwörter an |

---

### Task 0: Arbeitsumgebung und Baseline

**Files:** keine Codeänderung.

- [x] **Step 1: Upstream-Runde und Basis prüfen**

```bash
cd /d/Entwicklung/HASI/HAsmartirrigation
git fetch upstream && git fetch origin
git rev-parse --short=8 origin/feat/pause-silent-weather-sensor
gh pr view 197 --repo JustChr/HAsmartirrigation --json state,mergedAt,commits --jq '{state, mergedAt, n: (.commits|length)}'
```

Erwartet: `6fa424e8`, PR offen, 18 Commits. Hat das Review von PR 197 Commits hinzugefügt: Basis = neuer Kopf, jede
Anker-Stelle dieses Plans per `grep -n` neu suchen und die Baseline dort messen. Ist PR 197 schon gemergt: Basis =
`upstream/master` (dann enthält er PR 2 gesquasht); Anker ebenso neu suchen.

- [x] **Step 2: Worktree von `6fa424e8` anlegen**

```bash
cd /d/Entwicklung/HASI/HAsmartirrigation
git worktree add --no-track -b feat/pause-silent-sensor-hourly-live /d/Entwicklung/HASI/issue8-pr3-work/wt 6fa424e8
cp _local_socket_unblock.py /d/Entwicklung/HASI/issue8-pr3-work/wt/
cd /d/Entwicklung/HASI/issue8-pr3-work/wt && git log --oneline -1
```

- [x] **Step 3: Baseline der vollen Suite** (Memory `rebaseline-when-the-base-moves`)

```bash
cd /d/Entwicklung/HASI/issue8-pr3-work/wt
TZ=UTC /d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests -p _local_socket_unblock -q --no-header -rfE > ../suite-base-wt.txt 2>&1
tr '\r' '\n' < ../suite-base-wt.txt | grep -E "^(FAILED|ERROR) tests" | sed -E 's/ - .*//' | sort > ../names-base-wt.txt
tail -c 300 ../suite-base-wt.txt
```

Erwartet (gemessen auf `6fa424e8` am 2026-10-13): `7 failed, 3925 passed, 9 skipped, … 466 errors`. Die Datei erst nach
Laufende lesen.

- [x] **Step 4: Vergleichsskript für die Task-Prüfungen anlegen**

```bash
cat > /d/Entwicklung/HASI/issue8-pr3-work/task_compare.sh <<'SH'
#!/usr/bin/env bash
# task_compare.sh <label> <test files...>: run them, compare FAILED/ERROR names with the baseline of those files.
set -u
label=$1; shift
W=/d/Entwicklung/HASI/issue8-pr3-work
cd $W/wt || exit 2
TZ=UTC /d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest "$@" -p _local_socket_unblock -q --no-header -rfE > $W/task-$label.txt 2>&1
tr '\r' '\n' < $W/task-$label.txt | grep -E "^(FAILED|ERROR) tests" | sed -E 's/ - .*//' | sort > $W/task-$label-names.txt
pat=$(printf '%s\n' "$@" | sed 's#tests/##; s#\.py$##' | paste -sd'|')
grep -E "$pat" $W/names-base-wt.txt | sort > $W/task-$label-base.txt
echo "baseline names missing now: $(comm -23 $W/task-$label-base.txt $W/task-$label-names.txt | wc -l)"
comm -23 $W/task-$label-base.txt $W/task-$label-names.txt
echo "new FAILED: $(comm -13 $W/task-$label-base.txt $W/task-$label-names.txt | grep -c '^FAILED')"
echo "new ERROR per file:"; comm -13 $W/task-$label-base.txt $W/task-$label-names.txt | grep '^ERROR' | sed -E 's/::.*//' | sort | uniq -c
tr '\r' '\n' < $W/task-$label.txt | grep -E "^=+ .*(passed|failed).* in " | tail -1
SH
chmod +x /d/Entwicklung/HASI/issue8-pr3-work/task_compare.sh
```

Neue ERROR dürfen nur aus den drei neuen Dateien mit echtem Koordinator kommen (Teardown „Lingering timer“; im Zweifel
`grep -c "Lingering timer"` in der Ausgabe).

---

## Teil A — Commit

### Task 1: Die Sperren eines Fensters als freie Funktion

**Files:**
- Modify: `custom_components/irrigation_plus/sensor_liveness.py` (neue Funktion nach `valid_share`, `:223-235`)
- Modify: `custom_components/irrigation_plus/calculation.py` (Importe `:44-50`, `_blocked_spans_for_zone` `:420-453`)
- Test: `tests/test_sensor_liveness_blocked.py`

**Interfaces:**
- Produces: `zone_blocked_spans(store, zone: dict, start, end) -> dict | None` in `sensor_liveness.py` — `None` für eine
  Gruppe auf *behalten*, ohne Gruppe, ohne Anfang/Ende oder ohne verbleibende Sperre; sonst `{feld: ((von, bis), …)}`
  ohne Regenzähler. `CalculationMixin._blocked_spans_for_zone(zone, *, now)` bleibt mit gleicher Signatur und ruft die
  Funktion; das Gate auf die Stundenrechnung bleibt bis Task 5.

- [x] **Step 1: Tests schreiben**

Modify `tests/test_sensor_liveness_blocked.py`:

```diff
diff --git a/tests/test_sensor_liveness_blocked.py b/tests/test_sensor_liveness_blocked.py
index c08d0b10..bdd109b6 100644
--- a/tests/test_sensor_liveness_blocked.py
+++ b/tests/test_sensor_liveness_blocked.py
@@ -1,6 +1,9 @@
 """The time a pausing sensor group does not book: blocked spans and the share left."""
 
 from datetime import datetime, timedelta
+from types import SimpleNamespace
+
+from homeassistant.util import dt as dt_util
 
 from custom_components.irrigation_plus import const
 from custom_components.irrigation_plus.sensor_liveness import (
@@ -8,6 +11,7 @@ from custom_components.irrigation_plus.sensor_liveness import (
     blocked_spans,
     group_pauses,
     valid_share,
+    zone_blocked_spans,
 )
 
 T0 = datetime(2026, 7, 1, 0, 0, 0)  # window start, naive on HA's clock
@@ -117,3 +121,90 @@ class TestGroupPauses:
         assert group_pauses({const.MAPPING_ON_SILENT_SENSOR: "keep"}) is False
         assert group_pauses({}) is False
         assert group_pauses({const.MAPPING_ON_SILENT_SENSOR: "PAUSE"}) is False
+
+
+def _store(mapping):
+    """A store that knows one sensor group, under id 1."""
+    return SimpleNamespace(get_mapping=lambda mid: mapping if mid == 1 else None)
+
+
+def _mapping(*, setting="pause", outages=(), mappings=None):
+    return {
+        const.MAPPING_ON_SILENT_SENSOR: setting,
+        const.MAPPING_SENSOR_OUTAGES: [o.to_store() for o in outages],
+        const.MAPPING_MAPPINGS: mappings or {},
+    }
+
+
+ZONE = {const.ZONE_MAPPING: 1}
+
+
+class TestZoneBlockedSpans:
+    """One zone's window as the commit and the live estimate both ask for it."""
+
+    def test_a_pausing_group_is_cut_where_its_outage_blocks(self):
+        store = _store(_mapping(outages=[_outage(2, 10)]))
+        assert zone_blocked_spans(store, ZONE, T0, END) == {
+            "Temperature": ((T0 + 5 * H, T0 + 10 * H),)
+        }
+
+    def test_the_window_start_is_the_callers(self):
+        """The commit measures from its watermark, the live estimate from its
+        anchor; the function takes either."""
+        store = _store(_mapping(outages=[_outage(2, 10)]))
+        assert zone_blocked_spans(store, ZONE, T0 + 7 * H, END) == {
+            "Temperature": ((T0 + 7 * H, T0 + 10 * H),)
+        }
+
+    def test_an_open_outage_blocks_up_to_the_window_end(self):
+        store = _store(_mapping(outages=[_outage(2)]))
+        assert zone_blocked_spans(store, ZONE, T0, END) == {
+            "Temperature": ((T0 + 5 * H, END),)
+        }
+
+    def test_the_calculation_form_is_not_asked(self):
+        """No gate on the hourly calculation: every form cuts the same time."""
+        store = _store(_mapping(outages=[_outage(2, 10)]))
+        store.config = SimpleNamespace(**{const.CONF_HOURLY_CALCULATION: True})
+        assert zone_blocked_spans(store, ZONE, T0, END) is not None
+
+    def test_a_group_that_keeps_is_not_cut(self):
+        store = _store(_mapping(setting="keep", outages=[_outage(2, 10)]))
+        assert zone_blocked_spans(store, ZONE, T0, END) is None
+
+    def test_a_window_no_outage_reaches_is_not_cut(self):
+        store = _store(_mapping(outages=[_outage(-30, -20), _outage(2, 4)]))
+        assert zone_blocked_spans(store, ZONE, T0, END) is None
+
+    def test_no_group_no_start_or_no_window_is_not_cut(self):
+        store = _store(_mapping(outages=[_outage(2, 10)]))
+        assert zone_blocked_spans(store, {const.ZONE_MAPPING: None}, T0, END) is None
+        assert zone_blocked_spans(store, {const.ZONE_MAPPING: 2}, T0, END) is None
+        assert zone_blocked_spans(store, ZONE, None, END) is None
+        assert zone_blocked_spans(store, ZONE, END, END) is None
+        assert zone_blocked_spans(store, ZONE, END, T0) is None
+
+    def test_a_rain_gauge_is_never_cut_and_a_rain_rate_is(self):
+        rain = const.MAPPING_PRECIPITATION
+
+        def spans(aggregate):
+            mappings = {rain: {const.MAPPING_CONF_AGGREGATE: aggregate}}
+            store = _store(
+                _mapping(outages=[_outage(2, 10, fields=(rain,))], mappings=mappings)
+            )
+            return zone_blocked_spans(store, ZONE, T0, END)
+
+        assert spans(const.MAPPING_CONF_AGGREGATE_DELTA) is None
+        assert spans(const.MAPPING_CONF_AGGREGATE_RIEMANNSUM) == {
+            rain: ((T0 + 5 * H, T0 + 10 * H),)
+        }
+
+    def test_stamps_with_an_offset_are_read_on_has_clock(self):
+        """A stored stamp may carry an offset; it is compared on HA's clock."""
+        store = _store(_mapping(outages=[_outage(2, 10)]))
+        aware_end = dt_util.as_utc(
+            dt_util.as_local(END.replace(tzinfo=dt_util.DEFAULT_TIME_ZONE))
+        )
+        assert zone_blocked_spans(store, ZONE, T0, aware_end) == {
+            "Temperature": ((T0 + 5 * H, T0 + 10 * H),)
+        }
```

- [x] **Step 2: RED**

Run: `TZ=UTC /d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests/test_sensor_liveness_blocked.py -p _local_socket_unblock -q`
Expected: Sammelfehler `ImportError: cannot import name 'zone_blocked_spans'`.

- [x] **Step 3: Implementierung**

Modify `custom_components/irrigation_plus/calculation.py`:

```diff
diff --git a/custom_components/irrigation_plus/calculation.py b/custom_components/irrigation_plus/calculation.py
index b194baf4..b32b5977 100644
--- a/custom_components/irrigation_plus/calculation.py
+++ b/custom_components/irrigation_plus/calculation.py
@@ -41,13 +41,7 @@ from .helpers import (
 )
 from .helpers import as_datetime as _as_datetime
 from .localize import localize
-from .sensor_liveness import (
-    blocked_spans,
-    cuts_field,
-    group_pauses,
-    outages_of,
-    valid_share,
-)
+from .sensor_liveness import valid_share, zone_blocked_spans
 from .weather_aggregate import (
     aggregate_window,
     build_substeps,
@@ -420,37 +414,20 @@ class CalculationMixin:
     def _blocked_spans_for_zone(self, zone, *, now):
         """The time this zone's window may not book from its sensor group, or None.
 
-        Only a group that pauses a silent sensor is cut, and only in the daily
-        form: with the hourly calculation the replayed balance checks itself
-        against this aggregate's precipitation, so cutting one and not the
-        other would fail that check. The hourly form is not cut here: it would
-        have to be cut together with the live estimate. None leaves the commit
-        as it always was, and so does a window no outage reaches, or a zone
-        that has never consumed (its first commit anchors it). Which fields are
-        blocked, ``sensor_liveness.cuts_field`` decides: never a cumulative
-        rain gauge.
+        The commit's window runs from the zone's watermark to ``now``, and
+        ``sensor_liveness.zone_blocked_spans`` cuts it -- the function the live
+        estimate asks too. A zone that has never consumed has no watermark and
+        is not cut (its first commit anchors it).
+
+        Only in the daily form for now: with the hourly calculation the replayed
+        balance checks itself against this aggregate's precipitation, so cutting
+        one and not the other would fail that check.
         """
-        mapping_id = zone.get(const.ZONE_MAPPING)
-        if mapping_id is None:
-            return None
-        mapping = self.store.get_mapping(mapping_id)
-        if not mapping or not group_pauses(mapping):
-            return None
         if hourly_calculation_enabled(self.store):
             return None
-        watermark = coerce_stamp(zone.get(const.ZONE_LAST_CONSUMED), STAMP_FROM_STORE)
-        now = coerce_stamp(now, STAMP_FROM_STORE)
-        if watermark is None or now is None or watermark >= now:
-            return None
-        config = mapping.get(const.MAPPING_MAPPINGS) or {}
-        blocked = {
-            field: spans
-            for field, spans in blocked_spans(
-                outages_of(mapping), watermark, now
-            ).items()
-            if cuts_field(field, config)
-        }
-        return blocked or None
+        return zone_blocked_spans(
+            self.store, zone, zone.get(const.ZONE_LAST_CONSUMED), now
+        )
 
     async def _aggregate_for_zone(self, zone, *, now, blocked=None):
         """Aggregate this zone's window of its mapping's shared buffer.
```

Modify `custom_components/irrigation_plus/sensor_liveness.py`:

```diff
diff --git a/custom_components/irrigation_plus/sensor_liveness.py b/custom_components/irrigation_plus/sensor_liveness.py
index 57396369..f45f3eda 100644
--- a/custom_components/irrigation_plus/sensor_liveness.py
+++ b/custom_components/irrigation_plus/sensor_liveness.py
@@ -235,6 +235,39 @@ def valid_share(blocked: dict, fields, start: datetime, end: datetime) -> float:
     return max(0.0, (length - gone) / length)
 
 
+def zone_blocked_spans(store, zone: dict, start, end) -> dict | None:
+    """A pausing group's blocked time in one zone's window ``[start, end)``, or None.
+
+    The one place the commit and the live estimate take their spans from, so both
+    leave out the same time. A free function over the store rather than a method:
+    the live estimate's mixin runs on its own in its tests, where a cross-mixin
+    call raises and is swallowed as a failed estimate. ``start`` is the caller's
+    -- the commit's watermark, the estimate's anchor -- and ``end`` its ``now``,
+    which also ends an open outage.
+
+    None leaves a window exactly as it always was: a group that keeps, a zone
+    without a group or a start, an empty window, or one no outage reaches. Which
+    fields are cut, ``cuts_field`` says: never a cumulative rain gauge.
+    """
+    mapping_id = zone.get(const.ZONE_MAPPING)
+    if mapping_id is None:
+        return None
+    mapping = store.get_mapping(mapping_id)
+    if not mapping or not group_pauses(mapping):
+        return None
+    start = coerce_stamp(start, STAMP_FROM_STORE)
+    end = coerce_stamp(end, STAMP_FROM_STORE)
+    if start is None or end is None:
+        return None
+    config = mapping.get(const.MAPPING_MAPPINGS) or {}
+    blocked = {
+        field: spans
+        for field, spans in blocked_spans(outages_of(mapping), start, end).items()
+        if cuts_field(field, config)
+    }
+    return blocked or None
+
+
 def _merged(spans) -> tuple[tuple[datetime, datetime], ...]:
     """Sorted spans with every overlap or touch joined into one."""
     merged: list[tuple[datetime, datetime]] = []
```

- [x] **Step 4: GREEN**

Run: wie Step 2. Expected: `25 passed`.

- [x] **Step 5: Prüfen**

```bash
cd /d/Entwicklung/HASI/issue8-pr3-work/wt
uvx black custom_components/irrigation_plus/ && uvx ruff@0.16.10 check custom_components/irrigation_plus/
../task_compare.sh t1 tests/test_sensor_liveness_blocked.py tests/test_silent_sensor_commit.py
```

Expected: kein Baseline-Name entfällt, keine neuen FAILED, keine neuen ERROR.

- [x] **Step 6: Commit**

```bash
git add custom_components/irrigation_plus/sensor_liveness.py custom_components/irrigation_plus/calculation.py tests/test_sensor_liveness_blocked.py
git commit -F - <<'EOF'
refactor(liveness): one function cuts a zone's window for every caller

The commit's gate method computed the blocked spans itself. The live
estimate needs the same spans for its own window, and its mixin cannot
call the calculation's: it runs alone in its tests, where a cross-mixin
call raises and is swallowed as a failed estimate. zone_blocked_spans
takes the store, the zone and the window explicitly; the commit's method
wraps it and still declines under the hourly calculation for now.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
```

### Task 2: Stundenzeilen buchen nur gemessene Zeit

**Files:**
- Modify: `custom_components/irrigation_plus/weather_aggregate.py` (`_HOURLY_ROW_REQUIRED` `:71` → öffentlich; neue
  Helfer nach `_hold_integral_upto` `:793-800`; `_precip_increments` `:803`; `_books_nothing` vor `_ratio_hold_solar`
  `:909`; `build_hourly_rows` `:1007-1174`)
- Modify: `custom_components/irrigation_plus/et_estimate.py` (`eto_hourly_series` `:103-145`, `hourly_eto_priced`
  `:148-191`)
- Test: neu `tests/test_hourly_rows_blocked.py`

**Interfaces:**
- Produces: `HOURLY_ROW_REQUIRED` (bisher `_HOURLY_ROW_REQUIRED`; kein Test nutzt den alten Namen);
  `build_hourly_rows(…, blocked=None)`; `hourly_eto_priced(…, blocked=None)`;
  `_precip_increments(samples, aggregate, *, spans=None, start=None, end=None)` (alte Aufrufe bleiben gültig);
  `_masked_hold_table(samples, spans, start, end, *, mask=None)`, `_masked_upto(table, t)`, `_masked_mean(table, a, b)`,
  `_overlap_hours(segments, a, b)`, `_books_nothing(row)`. Eine gesperrte Stunde ist eine Zeile mit `coverage_h == 0.0`
  ohne Messfelder; `eto_hourly_series` gibt für sie `0.0`.

- [x] **Step 1: Tests schreiben**

Create `tests/test_hourly_rows_blocked.py`:

```python
"""Hourly rows of a pausing sensor group: each hour books only its measured time.

A blocked field is averaged over its own valid time in the hour, never held into a
span, and after one the value from before holds again. The hour is charged for the
time in which every field the hourly equation needs was measured at once
(``coverage_h``); an hour without such time stays a row with no ET, so neither the
hourly form nor the replayed balance falls over. Fields without spans go through
the tables they always did, so rows of a group that keeps are unchanged.
"""

import datetime
from datetime import timedelta

import pytest

from custom_components.irrigation_plus import const
from custom_components.irrigation_plus.et_estimate import (
    SiteGeometry,
    eto_hourly_series,
    hourly_eto_priced,
)
from custom_components.irrigation_plus.weather_aggregate import (
    HOURLY_ROW_REQUIRED,
    aggregate_window,
    build_hourly_rows,
)

T0 = datetime.datetime(2026, 6, 21, 0, 0, 0)
H = timedelta(hours=1)
M = timedelta(minutes=1)
LAT, LON, ELEV = 50.0, 7.0, 300.0
T = const.MAPPING_TEMPERATURE
RH = const.MAPPING_HUMIDITY
WIND = const.MAPPING_WINDSPEED
SUN = const.MAPPING_SOLRAD
P = const.MAPPING_PRESSURE
RAIN = const.MAPPING_PRECIPITATION
W_TO_MJ_DAY = 0.0864


def _sun(stamp):
    """Daylight in W/m2 as MJ/day/m2, flat within each hour."""
    hour = stamp.hour
    return (600.0 if 6 <= hour < 20 else 0.0) * W_TO_MJ_DAY


def _dense(hours=24, *, temp=lambda s: 10.0 + s.hour, skip=()):
    """A poll buffer: every field on every row, every 10 minutes.

    ``skip`` lists ``(field, from, to)`` stretches in which that field writes no
    row, as a deadband does for a value that does not move.
    """
    readings = []
    stamp = T0
    while stamp < T0 + hours * H:
        row = {
            const.RETRIEVED_AT: stamp,
            T: temp(stamp),
            RH: 60.0,
            WIND: 2.0,
            SUN: _sun(stamp),
            P: 1000.0,
        }
        for field, lo, hi in skip:
            if lo <= stamp < hi:
                row.pop(field)
        readings.append(row)
        stamp += 10 * M
    return readings


def _rows(readings, *, hours=24, blocked=None, **kwargs):
    return build_hourly_rows(
        readings,
        T0,
        kwargs.pop("mappings_config", {}),
        now=T0 + hours * H,
        latitude=LAT,
        longitude=LON,
        elevation=ELEV,
        tz_offset_h=2.0,
        blocked=blocked,
        **kwargs,
    )


def _by_hour(rows):
    return {row["hour_start"]: row for row in rows}


class TestFieldsWithoutSpans:
    def test_no_spans_an_empty_dict_and_a_foreign_field_give_the_same_rows(self):
        readings = _dense()
        plain = _rows(readings)
        assert _rows(readings, blocked={}) == plain
        assert _rows(
            readings, blocked={const.MAPPING_DEWPOINT: ((T0, T0 + 5 * H),)}
        ) == (plain)

    def test_the_required_fields_are_public(self):
        assert HOURLY_ROW_REQUIRED == (T, RH, WIND, SUN)


class TestABlockedHourBooksNothing:
    def test_hours_inside_a_span_stay_as_rows_without_et(self):
        rows = _by_hour(_rows(_dense(), blocked={T: ((T0 + 10 * H, T0 + 12 * H),)}))
        assert len(rows) == 24
        for hour in (10, 11):
            row = rows[T0 + hour * H]
            assert row["coverage_h"] == 0.0
            assert "temperature" not in row
            assert "solar_mj_h" not in row
        assert rows[T0 + 9 * H]["coverage_h"] == 1.0
        assert rows[T0 + 12 * H]["coverage_h"] == 1.0

    def test_the_series_charges_such_a_row_nothing(self):
        rows = _rows(_dense(), blocked={T: ((T0 + 10 * H, T0 + 12 * H),)})
        series = eto_hourly_series(rows, LAT, LON, 2.0, ELEV)
        by_hour = dict(zip([r["hour_start"] for r in rows], series, strict=True))
        assert by_hour[T0 + 10 * H] == 0.0
        assert by_hour[T0 + 11 * H] == 0.0
        assert by_hour[T0 + 12 * H] > 0.0

    def test_a_partly_blocked_hour_is_charged_its_measured_part(self):
        rows = _by_hour(
            _rows(_dense(), blocked={T: ((T0 + 10 * H, T0 + 11 * H + 15 * M),)})
        )
        assert rows[T0 + 11 * H]["coverage_h"] == pytest.approx(0.75)

    def test_hours_outside_the_spans_match_the_unblocked_rows(self):
        readings = _dense()
        plain = _by_hour(_rows(readings))
        cut = _by_hour(_rows(readings, blocked={T: ((T0 + 10 * H, T0 + 12 * H),)}))
        for hour in (*range(10), *range(12, 24)):
            for key in ("temperature", "humidity", "wind_2m", "pressure_kpa"):
                assert cut[T0 + hour * H][key] == pytest.approx(
                    plain[T0 + hour * H][key]
                )


class TestEachFieldIsAveragedOverItsOwnValidTime:
    def test_two_fields_silent_in_different_parts_of_one_hour(self):
        """Temperature 20 + minute/10 every ten minutes in hour 10; it is blocked
        10:00-10:20 and humidity 10:40-11:00. The hour books 10:20-10:40, the
        intersection, but temperature averages its own 10:20-11:00:
        (22 + 23 + 24 + 25) / 4 = 23.5, not (22 + 23) / 2 over the intersection."""

        def temp(stamp):
            return 20.0 + stamp.minute / 10 if stamp.hour == 10 else 15.0

        blocked = {
            T: ((T0 + 10 * H, T0 + 10 * H + 20 * M),),
            RH: ((T0 + 10 * H + 40 * M, T0 + 11 * H),),
        }
        row = _by_hour(_rows(_dense(temp=temp), blocked=blocked))[T0 + 10 * H]
        assert row["coverage_h"] == pytest.approx(20 / 60)
        assert row["temperature"] == pytest.approx(23.5)

    def test_a_frozen_value_stamped_inside_a_span_is_not_used(self):
        """A poll keeps stamping the dead sensor's value fresh. Temperature is
        13 until 03:20, frozen at 99 through the span 03:30-05:00 and reports
        again (16) only from 05:20. Hour 5 holds the value from before the span,
        13, until 05:20: (13 * 20 + 16 * 40) / 60 = 15.0."""

        def temp(stamp):
            if T0 + 3 * H + 30 * M <= stamp < T0 + 5 * H:
                return 99.0
            return 13.0 if stamp < T0 + 5 * H else 16.0

        readings = _dense(temp=temp, skip=[(T, T0 + 5 * H, T0 + 5 * H + 20 * M)])
        rows = _by_hour(
            _rows(readings, blocked={T: ((T0 + 3 * H + 30 * M, T0 + 5 * H),)})
        )
        assert rows[T0 + 5 * H]["temperature"] == pytest.approx(15.0)
        assert rows[T0 + 3 * H]["temperature"] == pytest.approx(13.0)
        assert rows[T0 + 3 * H]["coverage_h"] == pytest.approx(0.5)


class TestAWindowThatStartsInsideASpan:
    def test_the_dead_sensors_boundary_value_is_never_priced(self):
        """Silent since before the window: the boundary row carries the frozen 99,
        and so does every poll row until the sensor is back at 03:00 with 20."""

        def temp(stamp):
            return 99.0 if stamp < T0 + 3 * H else 20.0

        rows = _by_hour(
            _rows(_dense(temp=temp), blocked={T: ((T0 - 2 * H, T0 + 3 * H),)})
        )
        for hour in (0, 1, 2):
            assert rows[T0 + hour * H]["coverage_h"] == 0.0
        assert rows[T0 + 3 * H]["coverage_h"] == 1.0
        assert rows[T0 + 3 * H]["temperature"] == pytest.approx(20.0)


class TestARequiredFieldBlockedThroughout:
    def test_the_rows_stay_and_book_nothing(self):
        rows = _rows(_dense(), blocked={SUN: ((T0, T0 + 24 * H),)})
        assert rows is not None
        assert len(rows) == 24
        assert all(row["coverage_h"] == 0.0 for row in rows)
        assert sum(eto_hourly_series(rows, LAT, LON, 2.0, ELEV)) == 0.0

    def test_a_field_whose_every_reading_is_inside_a_span_books_nothing(self):
        readings = _dense(hours=24)
        for row in readings:
            if row[const.RETRIEVED_AT] < T0 + 8 * H:
                row.pop(T)
        rows = _rows(readings, blocked={T: ((T0 + 8 * H, T0 + 24 * H),)})
        assert rows is not None
        assert all(row["coverage_h"] == 0.0 for row in rows)

    def test_a_field_never_read_still_falls_back(self):
        readings = _dense()
        for row in readings:
            row.pop(T)
        assert _rows(readings, blocked={SUN: ((T0, T0 + 2 * H),)}) is None


class TestPressureIsNotRequired:
    def test_an_hour_without_valid_pressure_takes_the_elevation(self):
        rows = _by_hour(_rows(_dense(), blocked={P: ((T0 + 10 * H, T0 + 12 * H),)}))
        assert "pressure_kpa" not in rows[T0 + 10 * H]
        assert rows[T0 + 10 * H]["coverage_h"] == 1.0
        assert "temperature" in rows[T0 + 10 * H]
        assert rows[T0 + 12 * H]["pressure_kpa"] == pytest.approx(100.0)


class TestTheClearnessRatio:
    """Solar readings inside a span are neither an hour's own reading nor the
    source of a ratio; after the span the ratio from before it holds."""

    @staticmethod
    def _frozen(readings, lo, hi, value):
        for row in readings:
            if lo <= row[const.RETRIEVED_AT] < hi:
                row[SUN] = value
        return readings

    def test_frozen_solar_inside_a_span_changes_no_row(self):
        """Silent from 11:30, the sun is frozen at 999 until 13:00 and writes
        nothing more until 15:00. Hour 11 has its own reading before the span;
        the frozen ones must not become its ratio, carried on to 13 and 14."""
        span = (T0 + 11 * H + 30 * M, T0 + 13 * H)
        quiet = (SUN, T0 + 13 * H, T0 + 15 * H)
        clean = _dense(skip=[(SUN, *span), quiet])
        frozen = self._frozen(_dense(skip=[quiet]), *span, 999.0)
        assert _rows(frozen, blocked={SUN: (span,)}) == _rows(
            clean, blocked={SUN: (span,)}
        )

    def test_after_the_span_the_ratio_from_before_holds(self):
        """No solar reading from 11:00 to 15:00, the sensor back without a row.
        Hours 13 and 14 take the ratio measured before the span -- what the
        unblocked rows give for a buffer without the silent readings."""
        silent = (T0 + 11 * H, T0 + 15 * H)
        span = (T0 + 11 * H, T0 + 13 * H)
        readings = _dense(skip=[(SUN, *silent)])
        cut = _by_hour(_rows(readings, blocked={SUN: (span,)}))
        plain = _by_hour(_rows(readings))
        for hour in (13, 14):
            assert cut[T0 + hour * H]["solar_mj_h"] == pytest.approx(
                plain[T0 + hour * H]["solar_mj_h"]
            )


class TestRain:
    def test_a_blocked_rain_rate_is_bucketed_over_its_valid_time_only(self):
        """The rows carry the same rain the aggregate books for the window."""
        readings = _dense()
        for row in readings:
            row[RAIN] = 2.0
        config = {
            RAIN: {
                const.MAPPING_CONF_AGGREGATE: const.MAPPING_CONF_AGGREGATE_RIEMANNSUM
            }
        }
        blocked = {RAIN: ((T0 + 10 * H, T0 + 12 * H),)}
        rows = _rows(readings, blocked=blocked, mappings_config=config)
        by_hour = _by_hour(rows)
        # Rain lands at the end of its interval: 09:50-10:00 is hour 10's, and
        # nothing after it until the span ends.
        assert by_hour[T0 + 10 * H]["precipitation"] == pytest.approx(2.0 / 6)
        assert by_hour[T0 + 11 * H]["precipitation"] == 0.0
        total = aggregate_window(
            readings, T0, config, now=T0 + 24 * H, blocked=blocked
        )[RAIN]
        assert sum(row["precipitation"] for row in rows) == pytest.approx(total)
        # The rate integrates up to the last reading (23:50), less the span.
        assert total == pytest.approx(2.0 * (21 + 50 / 60))


class TestPricing:
    def test_hourly_eto_priced_passes_the_spans_on(self):
        geometry = SiteGeometry(LAT, LON, ELEV, 2.0, None)
        args = (_dense(), T0, {})
        kwargs = {"now": T0 + 24 * H, "last_entry": None, "geometry": geometry}
        _rows_plain, plain = hourly_eto_priced(*args, **kwargs)
        rows, cut = hourly_eto_priced(
            *args, **kwargs, blocked={T: ((T0 + 10 * H, T0 + 12 * H),)}
        )
        assert sum(cut) < sum(plain)
        hours = [row["hour_start"] for row in rows]
        assert cut[hours.index(T0 + 10 * H)] == 0.0
```

- [x] **Step 2: RED**

Run: `TZ=UTC /d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests/test_hourly_rows_blocked.py -p _local_socket_unblock -q`
Expected: Sammelfehler `ImportError: cannot import name 'HOURLY_ROW_REQUIRED'`.

- [x] **Step 3: Implementierung** (der Diff enthält auch die Umbenennung `_HOURLY_ROW_REQUIRED` → `HOURLY_ROW_REQUIRED`,
  drei Stellen)

Modify `custom_components/irrigation_plus/et_estimate.py`:

```diff
diff --git a/custom_components/irrigation_plus/et_estimate.py b/custom_components/irrigation_plus/et_estimate.py
index 08273043..f9d1d435 100644
--- a/custom_components/irrigation_plus/et_estimate.py
+++ b/custom_components/irrigation_plus/et_estimate.py
@@ -118,7 +118,8 @@ def eto_hourly_series(
     * ``coverage_h`` — the fraction of the hour the row actually covers,
       defaulting to a whole hour. The partial hours at the ends of a
       calculation window are charged their real share this way rather than a
-      full hour of ET.
+      full hour of ET. A row covering no time (a pausing sensor group's blocked
+      hour, which carries no readings) is charged 0 without being priced.
     * ``tz_offset_h`` — this row's OWN UTC offset, overriding the argument. A
       window can span up to seven days and therefore a DST transition, after
       which one offset for the whole window puts the rows on the far side of it
@@ -128,6 +129,9 @@ def eto_hourly_series(
     """
     out = []
     for r in rows:
+        if r.get("coverage_h", 1.0) <= 0:
+            out.append(0.0)
+            continue
         eto = eto_hourly(
             t_c=r["temperature"],
             rh_pct=r["humidity"],
@@ -153,6 +157,7 @@ def hourly_eto_priced(
     now,
     last_entry,
     geometry: SiteGeometry,
+    blocked=None,
 ):
     """Reduce a buffer window to hourly rows and price each one. ``(rows, series)``.
 
@@ -160,7 +165,8 @@ def hourly_eto_priced(
     calculation and the live estimate cannot price the same window differently.
     Two callers hand-maintaining the same seven-argument call is what put them
     out of step before; the drift is silent, because a window that reduces with
-    the wrong geometry still returns a plausible number.
+    the wrong geometry still returns a plausible number. ``blocked`` (a pausing
+    sensor group's spans) goes to ``build_hourly_rows`` for the same reason.
 
     Returns None when the window will not reduce -- no readings, a required
     field missing from both the window and the carry-forward, or a window longer
@@ -179,6 +185,7 @@ def hourly_eto_priced(
         elevation=geometry.elevation,
         tz_offset_h=geometry.tz_offset_h,
         tz=geometry.tz,
+        blocked=blocked,
     )
     if not rows:
         return None
```

Modify `custom_components/irrigation_plus/weather_aggregate.py`:

```diff
diff --git a/custom_components/irrigation_plus/weather_aggregate.py b/custom_components/irrigation_plus/weather_aggregate.py
index a3501009..3b4fdc8f 100644
--- a/custom_components/irrigation_plus/weather_aggregate.py
+++ b/custom_components/irrigation_plus/weather_aggregate.py
@@ -68,7 +68,7 @@ _HOURLY_ROWS_MAX_HOURS = 24 * 7
 # Fields an hourly FAO-56 row cannot be built without. Pressure is optional (the
 # ETo helper derives it from elevation when absent) and precipitation is carried
 # for the row consumers rather than for the ET itself.
-_HOURLY_ROW_REQUIRED = (
+HOURLY_ROW_REQUIRED = (
     const.MAPPING_TEMPERATURE,
     const.MAPPING_HUMIDITY,
     const.MAPPING_WINDSPEED,
@@ -800,7 +800,89 @@ def _hold_integral_upto(points, values, cumulative, t):
     return cumulative[i] + values[i] * (t - points[i]).total_seconds()
 
 
-def _precip_increments(samples, aggregate):
+def _masked_hold_table(samples, spans, start, end, *, mask=None):
+    """A blocked level field's held step function over its valid time, or None.
+
+    The hold rules of ``_hold_integral_table`` restricted to where the field was
+    measured, as ``_aggregate_blocked`` applies them to a whole window: a reading
+    stamped inside one of ``spans`` is dropped (the frozen value a poll keeps
+    stamping fresh), nothing is held into a span, and after one the value from
+    before it holds again -- a sensor back at the value it had writes no row.
+    ``mask`` is where the function is zero, ``spans`` unless a caller also has
+    to skip the time other fields were silent; readings are dropped by
+    ``spans`` alone.
+
+    Returns ``(points, values, cumulative, covered)``: ``values[i]`` is in force
+    on ``[points[i], points[i + 1]]`` and None where masked, ``cumulative`` is the
+    running integral and ``covered`` the running valid time, in seconds. None
+    when no reading survives: the field then has no value to hold.
+    """
+    mask = spans if mask is None else mask
+    kept = sorted(
+        ((t, v) for t, v in samples if t <= start or not _blocked_at(t, spans)),
+        key=lambda sample: sample[0],
+    )
+    if not kept:
+        return None
+    stamps = [t for t, _ in kept]
+    cuts = sorted(
+        {start, end}
+        | {t for t in stamps if start < t < end}
+        | {edge for span in mask for edge in span if start < edge < end}
+    )
+    points, values, cumulative, covered = [cuts[0]], [], [0.0], [0.0]
+    for a, b in itertools.pairwise(cuts):
+        seconds = (b - a).total_seconds()
+        # Every reading and every span edge is a cut, so one value and one
+        # state hold on the whole piece: the last reading at or before its
+        # start, the first one before any.
+        value = (
+            None
+            if _blocked_at(a, mask)
+            else kept[max(bisect.bisect_right(stamps, a) - 1, 0)][1]
+        )
+        points.append(b)
+        values.append(value)
+        cumulative.append(cumulative[-1] + (0.0 if value is None else value * seconds))
+        covered.append(covered[-1] + (0.0 if value is None else seconds))
+    return points, values, cumulative, covered
+
+
+def _masked_upto(table, t):
+    """``(integral, covered)`` of a masked table from the window start to ``t``."""
+    points, values, cumulative, covered = table
+    if t <= points[0]:
+        return 0.0, 0.0
+    if t >= points[-1]:
+        return cumulative[-1], covered[-1]
+    i = bisect.bisect_right(points, t) - 1
+    if values[i] is None:
+        return cumulative[i], covered[i]
+    seconds = (t - points[i]).total_seconds()
+    return cumulative[i] + values[i] * seconds, covered[i] + seconds
+
+
+def _masked_mean(table, a, b):
+    """Mean of a masked field over its valid time inside ``[a, b]``, or None."""
+    if table is None:
+        return None
+    integral_a, covered_a = _masked_upto(table, a)
+    integral_b, covered_b = _masked_upto(table, b)
+    covered = covered_b - covered_a
+    if covered <= 0:
+        return None
+    return (integral_b - integral_a) / covered
+
+
+def _overlap_hours(segments, a, b):
+    """Hours of ``[a, b]`` that lie inside ``segments``."""
+    seconds = sum(
+        max(0.0, (min(b, hi) - max(a, lo)).total_seconds()) for lo, hi in segments
+    )
+    return seconds / 3600
+
+
+def _precip_increments(samples, aggregate, *, spans=None, start=None, end=None):
     """``[(time, mm)]`` whose sum is exactly what ``_aggregate`` reports.
 
     The two halves of the calculation have to agree to the last decimal: the
@@ -808,6 +890,11 @@ def _precip_increments(samples, aggregate):
     and a mismatch would surface as a ledger that does not add up. So this
     mirrors the arithmetic in ``_aggregate`` rather than re-deriving it.
 
+    ``spans`` is a pausing group's blocked time for a rain RATE in ``[start,
+    end)``. Each increment then counts only its valid part, as
+    ``_riemann_over`` does for the aggregate, so a window cut there still
+    reconciles. A gauge is never cut, and ignores them.
+
     Returns None when the field has no time structure to sub-step, which is the
     signal to keep the single-shot path.
     """
@@ -817,6 +904,25 @@ def _precip_increments(samples, aggregate):
         # (#149). Taken from the shared rule rather than re-stated here, so this
         # cannot drift from the total ``_aggregate`` reports.
         return cumulative_delta_increments(samples)
+    if aggregate == const.MAPPING_CONF_AGGREGATE_RIEMANNSUM and spans:
+        kept = sorted(
+            ((t, v) for t, v in samples if t <= start or not _blocked_at(t, spans)),
+            key=lambda sample: sample[0],
+        )
+        if len(kept) < 2:
+            # _aggregate_blocked reports a lone rate verbatim, as _aggregate does.
+            return None
+        segments = _valid_segments(spans, start, end)
+        out = []
+        for (t0, v0), (t1, v1) in itertools.pairwise(kept):
+            # _riemann_over's trapezoid, split at the spans: each measured part
+            # lands at its own end, so rain that fell just before a span is not
+            # carried past it to the next reading.
+            for a, b in segments:
+                lo, hi = max(a, t0), min(b, t1)
+                if hi > lo:
+                    out.append((hi, (v0 + v1) / 2 * (hi - lo).total_seconds() / 3600))
+        return out
     if aggregate == const.MAPPING_CONF_AGGREGATE_RIEMANNSUM:
         if len(samples) < 2:
             # A lone rate sample takes _aggregate's single-value path, which
@@ -906,6 +1012,11 @@ def _row_rso_eq36(row, hour, doy, latitude, longitude, elevation, tz_offset_h):
     return clear_sky_radiation_hourly_eq36(ra, sin_beta, pressure_kpa, avp)
 
 
+def _books_nothing(row):
+    """Whether an hourly row is charged no time (a pausing group's blocked hour)."""
+    return row.get("coverage_h", 1.0) <= 0
+
+
 def _ratio_hold_solar(rows, solar_samples, latitude, longitude, elevation, tz_offset_h):
     """Refill the solar of hours that saw no reading from a held clearness ratio.
 
@@ -929,6 +1040,10 @@ def _ratio_hold_solar(rows, solar_samples, latitude, longitude, elevation, tz_of
     ``SOLAR_CLEAR_SKY_TOLERANCE`` for the same reason the ingest clamp is: a
     physically impossible reading must not be projected forward across a gap.
     That ingest clamp stays — it guards readings, this guards fabricated hours.
+
+    An hour that books nothing (``coverage_h`` 0, a pausing group's blocked
+    hour) carries no reading to take a ratio from and needs no solar; the ratio
+    is carried across it, so after a span the one from before it holds.
     """
     if latitude is None or longitude is None:
         return
@@ -947,7 +1062,7 @@ def _ratio_hold_solar(rows, solar_samples, latitude, longitude, elevation, tz_of
     measured = {}
     for row in rows:
         sample = newest.get(row["hour_start"])
-        if sample is None:
+        if sample is None or _books_nothing(row):
             continue
         stamp, value = sample
         rso = _row_rso_eq36(
@@ -989,7 +1104,7 @@ def _ratio_hold_solar(rows, solar_samples, latitude, longitude, elevation, tz_of
     first = next(r for r in held if r is not None)
 
     for row, ratio in zip(rows, held, strict=True):
-        if row["hour_start"] in newest:
+        if row["hour_start"] in newest or _books_nothing(row):
             # This hour has a measurement; its own mean stands. Includes the
             # dark hours that produced a reading but no usable Rso.
             continue
@@ -1016,6 +1131,7 @@ def build_hourly_rows(
     elevation=0.0,
     tz_offset_h=0.0,
     tz=None,
+    blocked=None,
 ):
     """Reduce a zone's window of the shared buffer to hourly FAO-56 rows, or None.
 
@@ -1054,6 +1170,18 @@ def build_hourly_rows(
     partial hours at each end of the window are charged their real share rather
     than a whole hour of ET.
 
+    ``blocked`` is a pausing sensor group's blocked time per field
+    (``sensor_liveness.zone_blocked_spans``). A blocked field is averaged over
+    its own valid time in each hour, by the rules ``_aggregate_blocked`` applies
+    to the window, and is left out of an hour in which it has none. An hour is
+    then charged only for the time in which every field of
+    ``HOURLY_ROW_REQUIRED`` was measured at once: ``coverage_h`` shrinks to that
+    time, and an hour without any stays a row with ``coverage_h`` 0 and no
+    readings -- it books no ET, and the per-hour series stays complete. A field
+    whose readings all lie inside its spans has no value to hold, so it books
+    nothing either, where a field never read still falls back as below. Fields
+    without spans are reduced exactly as without the argument.
+
     Returns None whenever the window cannot support hourly rows — no readings, a
     zero-length window, an absurdly long one, or any required field missing from
     both the window and the carry-forward. The caller then keeps the daily form,
@@ -1076,8 +1204,11 @@ def build_hourly_rows(
 
     by_sensor = _group_by_sensor(effective)
     tables = {}
+    # A pausing group's blocked fields, over their valid time only; None where
+    # no reading survived to hold.
+    masked = {}
     solar_samples = None
-    for key in (*_HOURLY_ROW_REQUIRED, const.MAPPING_PRESSURE):
+    for key in (*HOURLY_ROW_REQUIRED, const.MAPPING_PRESSURE):
         samples = by_sensor.get(key)
         if samples:
             samples = _clamped_samples(samples, start, end)
@@ -1090,9 +1221,21 @@ def build_hourly_rows(
         else:
             samples = None
         if samples is None:
-            if key in _HOURLY_ROW_REQUIRED:
+            if key in HOURLY_ROW_REQUIRED:
                 return None
             continue
+        spans = blocked.get(key) if blocked else None
+        if spans:
+            masked[key] = _masked_hold_table(samples, spans, start, end)
+            if key == const.MAPPING_SOLRAD:
+                # A frozen value stamped inside a span is neither an hour's own
+                # reading nor the source of a ratio.
+                solar_samples = [
+                    (t, v)
+                    for t, v in samples
+                    if t <= start or not _blocked_at(t, spans)
+                ]
+            continue
         if key == const.MAPPING_SOLRAD:
             # Retained so the ratio hold can tell an hour that saw a reading
             # from one that did not. The clamped copy, so the boundary and the
@@ -1101,6 +1244,19 @@ def build_hourly_rows(
             solar_samples = samples
         tables[key] = _hold_integral_table(samples, start, end)
 
+    # The time each hour is charged for: every required field measured at once.
+    # None while no required field has spans, which charges every hour exactly
+    # as before; empty when one has no value to hold at all.
+    booked = None
+    required_spans = [
+        span for key in HOURLY_ROW_REQUIRED if key in masked for span in blocked[key]
+    ]
+    if required_spans:
+        if any(masked[key] is None for key in HOURLY_ROW_REQUIRED if key in masked):
+            booked = []
+        else:
+            booked = _valid_segments(sorted(required_spans), start, end)
+
     # Precipitation is not part of the ET, but the row shape carries it for the
     # consumers that read a window as a series. Omitted entirely rather than
     # zero-filled when the field has no time structure: an absent key is honest,
@@ -1113,6 +1269,9 @@ def build_hourly_rows(
             increments = _precip_increments(
                 precip_samples,
                 effective_aggregate(const.MAPPING_PRECIPITATION, mappings_config),
+                spans=blocked.get(const.MAPPING_PRECIPITATION) if blocked else None,
+                start=start,
+                end=end,
             )
             if increments is not None:
                 rain_by_hour = {}
@@ -1139,7 +1298,9 @@ def build_hourly_rows(
             # coverage is charged through coverage_h instead.
             "hour": hour_start.hour + 0.5,
             "doy": hour_start.timetuple().tm_yday,
-            "coverage_h": coverage,
+            "coverage_h": (
+                coverage if booked is None else _overlap_hours(booked, a, b)
+            ),
         }
         if tz is not None:
             # Resolved from THIS row's stamp, not once for the window: the
@@ -1148,9 +1309,25 @@ def build_hourly_rows(
             row_offset = tz.utcoffset(hour_start)
             if row_offset is not None:
                 row["tz_offset_h"] = row_offset.total_seconds() / 3600.0
+        if _books_nothing(row):
+            # No time in this hour with every required field measured: it books
+            # no ET and carries no reading that would claim otherwise. It stays,
+            # so every hour of the window has its quantum.
+            if rain_by_hour is not None:
+                row["precipitation"] = rain_by_hour.get(hour_start, 0.0)
+            rows.append(row)
+            hour_start += step
+            continue
         means = {key: _hourly_mean(table, a, b) for key, table in tables.items()}
         if any(v is None for v in means.values()):
             return None
+        for key, table in masked.items():
+            # Every required field has valid time in an hour that books some,
+            # so only pressure can be left out here -- and then the ETo helper
+            # derives it from the elevation, as for a group without a barometer.
+            value = _masked_mean(table, a, b)
+            if value is not None:
+                means[key] = value
         row["temperature"] = means[const.MAPPING_TEMPERATURE]
         row["humidity"] = means[const.MAPPING_HUMIDITY]
         # Sensor wind speed is handed to FAO-56 as u2 exactly as the daily path
```

- [x] **Step 4: GREEN**

Run: wie Step 2. Expected: `17 passed`.

- [x] **Step 5: Prüfen**

```bash
uvx black custom_components/irrigation_plus/ && uvx ruff@0.16.10 check custom_components/irrigation_plus/
../task_compare.sh t2 tests/test_hourly_rows_blocked.py tests/test_summed_hourly_eto.py tests/test_solar_ratio_hold.py tests/test_cumulative_delta.py tests/test_hourly_rows_dst.py tests/test_water_balance_substeps.py tests/test_weather_aggregate_blocked.py tests/test_et_hourly.py tests/test_live_estimate_from_buffer.py
```

Expected: kein Baseline-Name entfällt, keine neuen FAILED oder ERROR.

- [x] **Step 6: Commit**

```bash
git add custom_components/irrigation_plus/weather_aggregate.py custom_components/irrigation_plus/et_estimate.py tests/test_hourly_rows_blocked.py
git commit -F - <<'EOF'
feat(weather): hourly rows charge each hour only for its measured time

A pausing sensor group's blocked field is averaged over its own valid
time in each hour, never held into a span, and after one the value from
before holds again. The hour is charged only for the time in which
temperature, humidity, wind and the sun were all measured; an hour
without any stays a row without readings and without ET, so the per-hour
series stays complete and a silent sensor never sends the window to the
daily form. Readings stamped inside a span neither count for their hour
nor feed the clearness ratio, and a blocked rain rate adds only its
measured part, landing at the end of it. Without spans every row is what
it was.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
```

### Task 3: Die nachgespielte Bilanz legt ET nur in gemessene Zeit

**Files:**
- Modify: `custom_components/irrigation_plus/weather_aggregate.py` (`build_substeps` `:1211-1361`)
- Test: neu `tests/test_substeps_blocked.py`

**Interfaces:**
- Consumes: `_masked_hold_table`, `_masked_upto`, `_overlap_hours`, `_precip_increments(…, spans=, start=, end=)` aus
  Task 2.
- Produces: `build_substeps(…, blocked=None, required=())` — `required` = Pflichtmenge der Form, die der Commit rechnet.

- [x] **Step 1: Tests schreiben**

Create `tests/test_substeps_blocked.py`:

```python
"""Replayed water balance of a pausing sensor group: ET lands only in measured time.

The sub-steps place the window's ET by measured sun. Where a field the calculation
needs was silent nothing is booked, so nothing is placed there either; a blocked
rain rate adds only its measured rain, so the steps still reconcile with the
aggregate. Only the placement moves -- the weights still sum to one.
"""

import datetime
from datetime import timedelta

import pytest

from custom_components.irrigation_plus import const
from custom_components.irrigation_plus.weather_aggregate import (
    HOURLY_ROW_REQUIRED,
    aggregate_window,
    build_substeps,
)

T0 = datetime.datetime(2026, 6, 21, 0, 0, 0)
NOW = T0 + timedelta(hours=24)
H = timedelta(hours=1)
M = timedelta(minutes=1)
T = const.MAPPING_TEMPERATURE
SUN = const.MAPPING_SOLRAD
RAIN = const.MAPPING_PRECIPITATION
RATE = {RAIN: {const.MAPPING_CONF_AGGREGATE: const.MAPPING_CONF_AGGREGATE_RIEMANNSUM}}
DAILY = (const.MAPPING_DEWPOINT, T, const.MAPPING_WINDSPEED, const.MAPPING_PRESSURE)


def _sun(stamp):
    hour = stamp.hour + stamp.minute / 60
    return max(0.0, 700.0 * (1 - abs(hour - 13) / 7)) * 0.0864


def _readings(*, rain=None):
    """Every 10 minutes: temperature and sun; ``rain`` maps a stamp to a rate."""
    out = []
    stamp = T0
    while stamp < NOW:
        row = {const.RETRIEVED_AT: stamp, T: 18.0, SUN: _sun(stamp)}
        if rain is not None:
            row[RAIN] = rain(stamp)
        out.append(row)
        stamp += 10 * M
    return out


def _steps(readings, **kwargs):
    config = kwargs.pop("mappings_config", {})
    return build_substeps(readings, T0, config, now=NOW, **kwargs)


def _span_of(steps, lo, hi):
    """Indices of the steps lying inside ``[lo, hi)``."""
    out, t = [], T0
    for i, step in enumerate(steps):
        end = t + timedelta(hours=step.dt_hours)
        if lo <= t and end <= hi:
            out.append(i)
        t = end
    return out


class TestWithoutSpans:
    def test_no_spans_an_empty_dict_and_a_foreign_field_give_the_same_steps(self):
        readings = _readings()
        plain = _steps(readings)
        assert _steps(readings, blocked={}, required=DAILY) == plain
        assert (
            _steps(
                readings,
                blocked={const.MAPPING_HUMIDITY: ((T0 + 10 * H, T0 + 12 * H),)},
                required=DAILY,
            )
            == plain
        )


class TestTheEtLandsInMeasuredTime:
    def test_a_required_field_silent_places_no_et_there(self):
        readings = _readings()
        span = (T0 + 10 * H, T0 + 12 * H)
        plain = _steps(readings)
        cut = _steps(readings, blocked={T: (span,)}, required=DAILY)
        inside = _span_of(cut, *span)
        assert inside
        assert all(cut[i].et_weight == 0.0 for i in inside)
        assert sum(s.et_weight for s in cut) == pytest.approx(1.0)
        # Outside the span the sun shapes it as before, renormalised.
        lost = sum(plain[i].et_weight for i in inside)
        for i, step in enumerate(cut):
            if i not in inside:
                assert step.et_weight == pytest.approx(plain[i].et_weight / (1 - lost))

    def test_a_field_the_form_does_without_moves_nothing(self):
        readings = _readings()
        span = (T0 + 10 * H, T0 + 12 * H)
        assert _steps(
            readings, blocked={const.MAPPING_HUMIDITY: (span,)}, required=DAILY
        ) == _steps(readings)

    def test_silent_sun_places_no_et_in_its_span_either(self):
        """The sun's own frozen value must not weight its silent time."""
        readings = _readings()
        span = (T0 + 10 * H, T0 + 12 * H)
        cut = _steps(readings, blocked={SUN: (span,)}, required=DAILY)
        assert all(cut[i].et_weight == 0.0 for i in _span_of(cut, *span))

    def test_inside_an_hour_the_quantum_goes_to_its_measured_part(self):
        """Hour 11 is cut by a rain event at 11:10; temperature is silent until
        11:15. The step 11:00-11:10 gets nothing of the hour's quantum."""

        def rain(stamp):
            return 3.0 if T0 + 11 * H <= stamp <= T0 + 11 * H + 10 * M else 0.0

        readings = _readings(rain=rain)
        hourly_et = {T0 + h * H: (0.2 if 6 <= h < 20 else 0.01) for h in range(24)}
        cut = _steps(
            readings,
            mappings_config=RATE,
            hourly_et=hourly_et,
            blocked={T: ((T0 + 9 * H, T0 + 11 * H + 15 * M),)},
            required=HOURLY_ROW_REQUIRED,
        )
        first = _span_of(cut, T0 + 11 * H, T0 + 11 * H + 10 * M)
        assert len(first) == 1
        assert cut[first[0]].et_weight == 0.0

    def test_a_dark_hour_spreads_its_quantum_over_its_measured_time(self):
        """Hour 2 is dark and cut by rain at 02:10, 02:20 and 02:30; temperature
        is silent until 02:30. The steps before 02:30 get none of the hour's ET,
        02:30-03:00 all of it -- what the whole hour gets without the span."""

        def rain(stamp):
            return 3.0 if T0 + 2 * H + 10 * M <= stamp <= T0 + 2 * H + 20 * M else 0.0

        readings = _readings(rain=rain)
        hourly_et = {T0 + h * H: 0.01 for h in range(24)}
        args = {"mappings_config": RATE, "hourly_et": hourly_et}
        plain = _steps(readings, **args)
        cut = _steps(
            readings,
            **args,
            blocked={T: ((T0 + 2 * H, T0 + 2 * H + 30 * M),)},
            required=HOURLY_ROW_REQUIRED,
        )
        silent = _span_of(cut, T0 + 2 * H, T0 + 2 * H + 30 * M)
        measured = _span_of(cut, T0 + 2 * H + 30 * M, T0 + 3 * H)
        hour = _span_of(plain, T0 + 2 * H, T0 + 3 * H)
        assert len(silent) == 3
        assert all(cut[i].et_weight == 0.0 for i in silent)
        assert len(measured) == 1
        assert cut[measured[0]].et_weight == pytest.approx(
            sum(plain[i].et_weight for i in hour)
        )

    def test_a_window_with_no_measured_time_still_steps(self):
        """Nothing is booked, so the ET to place is 0 -- the rain still replays."""
        readings = _readings(rain=lambda stamp: 1.0)
        steps = _steps(
            readings,
            mappings_config=RATE,
            blocked={T: ((T0, NOW),)},
            required=DAILY,
        )
        assert steps is not None
        assert sum(s.et_weight for s in steps) == pytest.approx(1.0)


class TestTheRainStillReconciles:
    def test_a_blocked_rain_rate_adds_only_its_measured_rain(self):
        readings = _readings(rain=lambda stamp: 2.0)
        blocked = {RAIN: ((T0 + 10 * H, T0 + 12 * H),)}
        steps = _steps(readings, mappings_config=RATE, blocked=blocked, required=DAILY)
        total = aggregate_window(readings, T0, RATE, now=NOW, blocked=blocked)[RAIN]
        assert sum(s.precip_mm for s in steps) == pytest.approx(total, rel=1e-9)
        assert sum(s.precip_mm for s in _steps(readings, mappings_config=RATE)) > total

    def test_rain_just_before_a_span_lands_before_it(self):
        """The reading of 10:00 lies on the span's start and is dropped; the rain
        of 09:50-10:00 still lands at 10:00, not at the next reading."""
        readings = _readings(rain=lambda stamp: 2.0)
        blocked = {RAIN: ((T0 + 10 * H, T0 + 12 * H),)}
        steps = _steps(readings, mappings_config=RATE, blocked=blocked, required=DAILY)
        before = _span_of(steps, T0 + 9 * H, T0 + 10 * H)
        assert sum(steps[i].precip_mm for i in before) == pytest.approx(2.0)
```

- [x] **Step 2: RED**

Run: `TZ=UTC /d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests/test_substeps_blocked.py -p _local_socket_unblock -q`
Expected: `9 failed`, jeweils `TypeError: build_substeps() got an unexpected keyword argument 'blocked'`.

- [x] **Step 3: Implementierung**

Modify `custom_components/irrigation_plus/weather_aggregate.py`:

```diff
diff --git a/custom_components/irrigation_plus/weather_aggregate.py b/custom_components/irrigation_plus/weather_aggregate.py
index 3b4fdc8f..6d21067f 100644
--- a/custom_components/irrigation_plus/weather_aggregate.py
+++ b/custom_components/irrigation_plus/weather_aggregate.py
@@ -1386,7 +1386,15 @@ def _weights_from_hourly_et(weights, hours, dt_hours, hourly_et):
 
 
 def build_substeps(
-    readings, watermark, mappings_config, *, now=None, hourly_et=None, applied=None
+    readings,
+    watermark,
+    mappings_config,
+    *,
+    now=None,
+    hourly_et=None,
+    applied=None,
+    blocked=None,
+    required=(),
 ):
     """Cut a zone's window into ordered water-balance sub-steps, or None.
 
@@ -1417,6 +1425,16 @@ def build_substeps(
     exactly as rain is; the caller must then start the replay from the level
     BEFORE those credits, since the stored bucket already contains them.
 
+    ``blocked`` is a pausing sensor group's blocked time per field and
+    ``required`` the fields the zone's form of the equation cannot do without.
+    ET is booked only where all of those were measured, so it is placed only
+    there: the sun weighs the steps over that time alone, and the sun's own
+    blocked time weighs nothing either, its frozen value being no measurement.
+    That moves where the window's ET lands, never how much there is. A blocked
+    rain rate adds only its measured rain, as the aggregate does, so the two
+    still reconcile. Without spans on any of those fields the steps are exactly
+    what they were.
+
     Returns None whenever the window cannot be sub-stepped faithfully — no
     timestamps, a zero-length window, a precipitation aggregate with no time
     structure, or a step whose hour is missing from ``hourly_et``. The caller
@@ -1447,6 +1465,9 @@ def build_substeps(
         increments = _precip_increments(
             precip_samples,
             effective_aggregate(const.MAPPING_PRECIPITATION, mappings_config),
+            spans=blocked.get(const.MAPPING_PRECIPITATION) if blocked else None,
+            start=start,
+            end=end,
         )
         if increments is None:
             return None
@@ -1486,25 +1507,59 @@ def build_substeps(
     # against 0.039 for the flat one, with an hour-boundary jump smaller than a
     # typical within-hour step. That is what keeps the intra-day shape honest for
     # anything that later publishes it.
+    #
+    # A pausing group books ET only where every required field was measured, so
+    # ``mask`` -- that blocked time plus the sun's own -- is where none is
+    # placed. None while neither has spans, which leaves the placement as it was.
+    mask = None
+    booked = None
+    if blocked:
+        spans = sorted(
+            span
+            for key in {*required, const.MAPPING_SOLRAD}
+            for span in blocked.get(key, ())
+        )
+        if spans:
+            mask = spans
+            booked = _valid_segments(spans, start, end)
     solar = by_sensor.get(const.MAPPING_SOLRAD)
     table = None
+    masked_sun = None
     if solar:
         solar = _clamped_samples(solar, start, end)
         if solar is not None:
-            points, values, cumulative = _hold_integral_table(solar, start, end)
-            if cumulative[-1] > 0:
-                table = (points, values, cumulative)
+            if mask is None:
+                points, values, cumulative = _hold_integral_table(solar, start, end)
+                if cumulative[-1] > 0:
+                    table = (points, values, cumulative)
+            else:
+                sun = _masked_hold_table(
+                    solar,
+                    blocked.get(const.MAPPING_SOLRAD, ()),
+                    start,
+                    end,
+                    mask=mask,
+                )
+                if sun is not None and sun[2][-1] > 0:
+                    masked_sun = sun
 
     steps = []
     weights = []
     hours = []
+    # Each step's measured time, in hours: all of it without a mask.
+    measured = []
     for i in range(len(cuts) - 1):
         a, b = cuts[i], cuts[i + 1]
         dt_hours = (b - a).total_seconds() / 3600
-        if table is None:
+        measured_hours = dt_hours if booked is None else _overlap_hours(booked, a, b)
+        if masked_sun is not None:
+            weight = max(
+                0.0, _masked_upto(masked_sun, b)[0] - _masked_upto(masked_sun, a)[0]
+            )
+        elif table is None:
             # No usable radiation (unmapped, or a window entirely after dark):
             # fall back to elapsed time, which is the same total spread flat.
-            weight = dt_hours
+            weight = measured_hours
         else:
             weight = max(
                 0.0,
@@ -1513,11 +1568,10 @@ def build_substeps(
         weights.append(weight)
         hours.append(a.replace(minute=0, second=0, microsecond=0))
         steps.append((dt_hours, rain_at.get(b, 0.0), applied_at.get(b, 0.0)))
+        measured.append(measured_hours)
 
     if hourly_et is not None:
-        weights = _weights_from_hourly_et(
-            weights, hours, [dt for dt, _, _ in steps], hourly_et
-        )
+        weights = _weights_from_hourly_et(weights, hours, measured, hourly_et)
         if weights is None:
             return None
 
@@ -1525,10 +1579,15 @@ def build_substeps(
     if total <= 0:
         # Night-only window under solar weighting. ET over such a window is
         # <= 0.017 mm/day, but it still has to go somewhere: spread it by time.
-        weights = [dt for dt, _, _ in steps]
+        weights = list(measured)
         total = sum(weights)
         if total <= 0:
-            return None
+            # No measured time at all: nothing is booked, so the ET to place is
+            # 0 -- spread it flat, so the rain still replays.
+            weights = [dt for dt, _, _ in steps]
+            total = sum(weights)
+            if total <= 0:
+                return None
 
     return [
         WaterStep(dt_hours, weight / total, precip_mm, applied_mm)
```

- [x] **Step 4: GREEN**

Run: wie Step 2. Expected: `9 passed`.

- [x] **Step 5: Prüfen**

```bash
uvx black custom_components/irrigation_plus/ && uvx ruff@0.16.10 check custom_components/irrigation_plus/
../task_compare.sh t3 tests/test_substeps_blocked.py tests/test_water_balance_substeps.py tests/test_summed_hourly_eto.py tests/test_live_estimate_replayed_balance.py
```

Expected: kein Baseline-Name entfällt, keine neuen FAILED oder ERROR.

- [x] **Step 6: Commit**

```bash
git add custom_components/irrigation_plus/weather_aggregate.py tests/test_substeps_blocked.py
git commit -F - <<'EOF'
feat(weather): the replayed balance places a pausing group's ET in measured time

The sub-steps spread the window's ET by measured sun. Where a field the
zone's form needs was silent nothing is booked, so nothing is placed
there either; the sun's own silent time weighs nothing, its frozen value
being no measurement, and a dark hour spreads its share over its
measured part. A blocked rain rate adds only its measured rain, so the
steps still reconcile with the aggregate. Only the placement moves.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
```

### Task 4: Der Commit bucht die Stundenform, Anteil nach der Form, die lief

**Files:**
- Modify: `custom_components/irrigation_plus/calculation.py` (Importe `:51-57`; Kommentar `_REQUIRED_SENSOR_FIELDS`
  `:65-82` und neue Funktion danach; `_hourly_et_for_zone` `:945-1049`; `_substeps_for_zone` `:1051-1101`;
  `calculate_module`: Anteil `:1256-1268` hinter die Formwahl `:1293-1297`, Teilschritt-Aufruf `:1405-1407`)
- Test: neu `tests/test_silent_sensor_hourly_commit.py`

**Interfaces:**
- Consumes: `HOURLY_ROW_REQUIRED` (Task 2), `hourly_eto_priced(…, blocked=)` (Task 2), `build_substeps(…, blocked=,
  required=)` (Task 3).
- Produces: `required_sensor_fields(module_name, *, hourly=False)` (öffentlich in `calculation.py`, auch für die
  Live-Schätzung); `_hourly_et_for_zone(…, blocked=None)`; `_substeps_for_zone(…, blocked=None, required=())`.
- Das Gate steht noch: Im Betrieb erreicht die Stundenform bis Task 5 keine Sperre; die Tests rufen `calculate_module`
  direkt mit Sperren.

- [x] **Step 1: Tests schreiben**

Create `tests/test_silent_sensor_hourly_commit.py`:

```python
"""A pausing sensor group's commit in the hourly form of the calculation.

The hourly rows charge each hour only for its measured time, so the summed ET is
already the booked part; it is not scaled a second time. The share the
explanation names is the time in which every field of the form that ran was
measured -- temperature, humidity, wind and the sun for the hourly form, the
daily form's own fields when it runs instead. The replayed balance still runs
under a blocked rain rate.
"""

import datetime
from datetime import timedelta
from unittest.mock import AsyncMock, Mock

import homeassistant.util.dt as dt_util
import pytest
from homeassistant.util.unit_system import METRIC_SYSTEM

from custom_components.irrigation_plus import SmartIrrigationCoordinator, const
from custom_components.irrigation_plus.calculation import required_sensor_fields
from custom_components.irrigation_plus.et_estimate import eto_hourly_series
from custom_components.irrigation_plus.store import SmartIrrigationStorage
from custom_components.irrigation_plus.weather_aggregate import (
    HOURLY_ROW_REQUIRED,
    build_hourly_rows,
)

T0 = datetime.datetime(2026, 6, 21, 0, 0, 0)
NOW = T0 + timedelta(hours=24)
H = timedelta(hours=1)
M = timedelta(minutes=1)
LAT, LON, ELEV = 39.68987, -84.07865, 311.0
T = const.MAPPING_TEMPERATURE
RH = const.MAPPING_HUMIDITY
SUN = const.MAPPING_SOLRAD
RAIN = const.MAPPING_PRECIPITATION
RATE = {RAIN: {const.MAPPING_CONF_AGGREGATE: const.MAPPING_CONF_AGGREGATE_RIEMANNSUM}}
HOURLY_SENTENCE = "sum of hourly FAO-56 et0"


def _offset_h():
    offset = dt_util.now().utcoffset()
    return offset.total_seconds() / 3600.0 if offset else 0.0


def _readings(*, rain=None):
    out = []
    stamp = T0
    while stamp < NOW:
        hour = stamp.hour + stamp.minute / 60
        row = {
            const.RETRIEVED_AT: stamp,
            T: 18.0 + 6 * (1 - abs(hour - 14) / 14),
            RH: 65.0,
            const.MAPPING_WINDSPEED: 2.0,
            SUN: max(0.0, 700.0 * (1 - abs(hour - 13) / 7)) * 0.0864,
            const.MAPPING_DEWPOINT: 10.0,
            const.MAPPING_PRESSURE: 1005.0,
        }
        if rain is not None:
            row[RAIN] = rain(stamp)
        out.append(row)
        stamp += 10 * M
    return out


@pytest.fixture
async def coordinator(hass):
    hass.data[const.DOMAIN] = {
        const.CONF_USE_WEATHER_SERVICE: False,
        const.CONF_WEATHER_SERVICE: None,
    }
    hass.config.units = METRIC_SYSTEM
    hass.config.language = "en"
    store = SmartIrrigationStorage(hass)
    await store.async_load()
    entry = Mock()
    entry.unique_id = "t"
    entry.data = {}
    entry.options = {}
    c = SmartIrrigationCoordinator(hass, None, entry, store)
    c.store = store
    c._effective_latitude = LAT
    c._effective_longitude = LON
    c._effective_elevation = ELEV
    await store.async_update_config(
        {const.CONF_CONTINUOUS_UPDATES: True, const.CONF_HOURLY_CALCULATION: True}
    )
    return c, store


async def _zone(c, store, readings, *, config=None, solrad="3", daily_et=5.0):
    mapping = await store.async_create_mapping(
        {
            const.MAPPING_NAME: "Garden",
            const.MAPPING_MAPPINGS: config or {},
            const.MAPPING_DATA: readings,
        }
    )
    module = await store.async_create_module(
        {const.MODULE_NAME: "PyETO", "description": "", "config": {}}
    )
    instance = Mock()
    instance.calculate = Mock(return_value=-daily_et)
    instance._solrad_behavior = solrad
    instance.forecast_days = 0
    c.getModuleInstanceByID = AsyncMock(return_value=instance)
    return await store.async_create_zone(
        {
            const.ZONE_NAME: "Front",
            const.ZONE_MAPPING: mapping[const.MAPPING_ID],
            const.ZONE_MODULE: module[const.MODULE_ID],
            const.ZONE_STATE: const.ZONE_STATE_AUTOMATIC,
            const.ZONE_BUCKET: 0.0,
            const.ZONE_MAXIMUM_BUCKET: 25.4,
            const.ZONE_DRAINAGE_RATE: 0.0,
            const.ZONE_THROUGHPUT: 10.0,
            const.ZONE_SIZE: 10.0,
            const.ZONE_MULTIPLIER: 1.0,
            const.ZONE_MAXIMUM_DURATION: 3600,
            const.ZONE_LEAD_TIME: 0,
            const.ZONE_LAST_CONSUMED: T0,
        }
    )


async def _commit(c, zone, blocked=None):
    weatherdata, _ = await c._aggregate_for_zone(zone, now=NOW, blocked=blocked)
    return await c.calculate_module(zone, weatherdata, None, now=NOW, blocked=blocked)


def _summed(readings, blocked, config=None):
    rows = build_hourly_rows(
        readings,
        T0,
        config or {},
        now=NOW,
        latitude=LAT,
        longitude=LON,
        elevation=ELEV,
        tz_offset_h=_offset_h(),
        tz=dt_util.DEFAULT_TIME_ZONE,
        blocked=blocked,
    )
    return sum(eto_hourly_series(rows, LAT, LON, _offset_h(), ELEV))


class TestTheFieldsEachFormNeeds:
    def test_the_hourly_form_needs_temperature_humidity_wind_and_sun(self):
        assert required_sensor_fields("PyETO", hourly=True) == HOURLY_ROW_REQUIRED

    def test_the_daily_form_and_passthrough_keep_theirs(self):
        assert set(required_sensor_fields("PyETO")) == {
            const.MAPPING_DEWPOINT,
            T,
            const.MAPPING_WINDSPEED,
            const.MAPPING_PRESSURE,
        }
        assert required_sensor_fields("Passthrough") == (
            const.MAPPING_EVAPOTRANSPIRATION,
        )
        assert required_sensor_fields("Passthrough", hourly=True) == (
            const.MAPPING_EVAPOTRANSPIRATION,
        )
        assert required_sensor_fields("Static") is None


class TestTheHourlyForm:
    async def test_it_books_the_rows_once_and_names_the_share(self, coordinator):
        c, store = coordinator
        readings = _readings()
        zone = await _zone(c, store, readings)
        blocked = {T: ((T0 + 10 * H, T0 + 12 * H),)}
        data = await _commit(c, zone, blocked)
        expected = _summed(readings, blocked)
        assert expected < _summed(readings, None)
        assert data[const.ZONE_DELTA] == pytest.approx(-expected, abs=1e-9)
        explanation = data[const.ZONE_EXPLANATION]
        assert HOURLY_SENTENCE in explanation
        assert "Evapotranspiration booked for 92 % of the period." in explanation

    async def test_a_required_field_silent_throughout_books_nothing(self, coordinator):
        c, store = coordinator
        zone = await _zone(c, store, _readings())
        data = await _commit(c, zone, {SUN: ((T0, NOW),)})
        assert data[const.ZONE_DELTA] == 0.0
        assert HOURLY_SENTENCE in data[const.ZONE_EXPLANATION]
        assert "booked for 0 % of the period" in data[const.ZONE_EXPLANATION]

    async def test_humidity_counts_in_the_hourly_form(self, coordinator):
        c, store = coordinator
        zone = await _zone(c, store, _readings())
        data = await _commit(c, zone, {RH: ((T0 + 10 * H, T0 + 12 * H),)})
        assert "booked for 92 % of the period" in data[const.ZONE_EXPLANATION]

    async def test_dewpoint_does_not(self, coordinator):
        c, store = coordinator
        zone = await _zone(c, store, _readings())
        plain = await _commit(c, zone)
        data = await _commit(
            c, zone, {const.MAPPING_DEWPOINT: ((T0 + 10 * H, T0 + 12 * H),)}
        )
        assert data[const.ZONE_DELTA] == pytest.approx(plain[const.ZONE_DELTA])
        assert "booked for" not in data[const.ZONE_EXPLANATION]


class TestTheDailyFormUnderTheHourlySwitch:
    """Estimated sun keeps the daily form; its own fields decide the share."""

    async def test_humidity_does_not_count_there(self, coordinator):
        c, store = coordinator
        zone = await _zone(c, store, _readings(), solrad="1")
        data = await _commit(c, zone, {RH: ((T0 + 10 * H, T0 + 12 * H),)})
        assert HOURLY_SENTENCE not in data[const.ZONE_EXPLANATION]
        assert data[const.ZONE_DELTA] == pytest.approx(-5.0)
        assert "booked for" not in data[const.ZONE_EXPLANATION]

    async def test_temperature_does(self, coordinator):
        c, store = coordinator
        zone = await _zone(c, store, _readings(), solrad="1")
        data = await _commit(c, zone, {T: ((T0 + 10 * H, T0 + 12 * H),)})
        assert data[const.ZONE_DELTA] == pytest.approx(-5.0 * 22 / 24)
        assert "booked for 92 % of the period" in data[const.ZONE_EXPLANATION]


class TestTheReplayedBalance:
    async def test_it_still_replays_under_a_blocked_rain_rate(self, coordinator):
        c, store = coordinator
        readings = _readings(
            rain=lambda stamp: 1.0 if stamp.hour in (9, 10, 11, 15) else 0.0
        )
        zone = await _zone(c, store, readings, config=RATE)
        blocked = {RAIN: ((T0 + 10 * H, T0 + 12 * H),)}
        data = await _commit(c, zone, blocked)
        assert "Number of steps:" in data[const.ZONE_EXPLANATION]

    async def test_it_still_replays_under_a_blocked_required_field(self, coordinator):
        c, store = coordinator
        zone = await _zone(c, store, _readings(rain=lambda stamp: 1.0), config=RATE)
        data = await _commit(c, zone, {T: ((T0 + 10 * H, T0 + 12 * H),)})
        assert "Number of steps:" in data[const.ZONE_EXPLANATION]
```

- [x] **Step 2: RED**

Run: `TZ=UTC /d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests/test_silent_sensor_hourly_commit.py -p _local_socket_unblock -q`
Expected: Sammelfehler `ImportError: cannot import name 'required_sensor_fields'`.

- [x] **Step 3: Implementierung**

Modify `custom_components/irrigation_plus/calculation.py`:

```diff
diff --git a/custom_components/irrigation_plus/calculation.py b/custom_components/irrigation_plus/calculation.py
index b32b5977..cc432db1 100644
--- a/custom_components/irrigation_plus/calculation.py
+++ b/custom_components/irrigation_plus/calculation.py
@@ -43,6 +43,7 @@ from .helpers import as_datetime as _as_datetime
 from .localize import localize
 from .sensor_liveness import valid_share, zone_blocked_spans
 from .weather_aggregate import (
+    HOURLY_ROW_REQUIRED,
     aggregate_window,
     build_substeps,
     merge_latest_per_field,
@@ -56,11 +57,12 @@ _LOGGER = logging.getLogger(__name__)
 # regardless of zone watermarks (bounds storage if a zone stops consuming).
 BUFFER_RETENTION = timedelta(days=7)
 
-# The sensor-group fields each module cannot book without: a pausing group books
-# only the part of a window in which all of them were measured. PyETO's daily
-# form refuses a day without the fields of DAILY_FORM_FIELDS, whose minimum and
-# maximum temperature are derived from the mapped Temperature; a missing Solar
-# Radiation it estimates instead. Passthrough books its ET field.
+# The sensor-group fields each module cannot book without in its daily form: a
+# pausing group books only the part of a window in which all of them were
+# measured. PyETO's daily form refuses a day without the fields of
+# DAILY_FORM_FIELDS, whose minimum and maximum temperature are derived from the
+# mapped Temperature; a missing Solar Radiation it estimates instead. Passthrough
+# books its ET field.
 _REQUIRED_SENSOR_FIELDS = {
     "PyETO": tuple(
         dict.fromkeys(
@@ -76,6 +78,21 @@ _REQUIRED_SENSOR_FIELDS = {
 }
 
 
+def required_sensor_fields(module_name, *, hourly=False):
+    """The fields a module cannot book without, in the form that ran, or None.
+
+    A pausing sensor group books only the part of a window in which all of them
+    were measured, so the share depends on the form of the equation: PyETO's
+    hourly form needs temperature, humidity, wind and the sun
+    (``HOURLY_ROW_REQUIRED``) and derives pressure from the elevation, its
+    daily form the fields above. A free function, because the live estimate
+    has to book the same share and its mixin cannot call this one's.
+    """
+    if hourly and module_name == "PyETO":
+        return HOURLY_ROW_REQUIRED
+    return _REQUIRED_SENSOR_FIELDS.get(module_name)
+
+
 def pending_bucket_events(zone):
     """A zone's unconsumed mid-window bucket credits as ``[(naive_local, mm)]``.
 
@@ -919,7 +936,7 @@ class CalculationMixin:
         """
         return hourly_calculation_enabled(self.store)
 
-    def _hourly_et_for_zone(self, zone, modinst, *, now):
+    def _hourly_et_for_zone(self, zone, modinst, *, now, blocked=None):
         """Summed FAO-56 hourly ETo over this zone's window, or None to use the daily form.
 
         The daily FAO-56 equation run on window-mean weather is systematically
@@ -950,6 +967,11 @@ class CalculationMixin:
 
         In every case the caller keeps the daily path, so the fallback is today's
         behaviour rather than a fabricated series.
+
+        ``blocked`` (a pausing group's spans) charges each hour only for its
+        measured time, so the total is already the booked part. A required
+        field silent throughout keeps this form and books nothing: it is not one
+        of the reasons above to leave it.
         """
         if not self._hourly_calculation_enabled():
             return None
@@ -1008,6 +1030,7 @@ class CalculationMixin:
             # clearness ratio rather than the last absolute value, which needs
             # the site's own solar geometry.
             geometry=SiteGeometry(latitude, longitude, elevation, tz_offset_h, tz),
+            blocked=blocked,
         )
         if priced is None:
             return None
@@ -1026,7 +1049,15 @@ class CalculationMixin:
         return total, per_hour
 
     def _substeps_for_zone(
-        self, zone, precip_total, *, now, hourly_et=None, applied=None
+        self,
+        zone,
+        precip_total,
+        *,
+        now,
+        hourly_et=None,
+        applied=None,
+        blocked=None,
+        required=(),
     ):
         """Water-balance sub-steps for this zone's window, or None to lump.
 
@@ -1042,6 +1073,9 @@ class CalculationMixin:
         so the two have to replay for exactly the same zones. Answering that
         question here rather than at the call site is what lets the estimate ask
         it of a zone without reproducing the conditions.
+
+        ``blocked`` and ``required`` (the fields of the form that ran) place a
+        pausing group's ET only where it was booked; see ``build_substeps``.
         """
         if not replayed_balance_applies(self.store, zone):
             return None
@@ -1062,6 +1096,8 @@ class CalculationMixin:
             now=now,
             hourly_et=hourly_et,
             applied=applied,
+            blocked=blocked,
+            required=required,
         )
         if not steps:
             return None
@@ -1230,19 +1266,6 @@ class CalculationMixin:
         # back to the single-shot path.
         if now is None:
             now = local_naive_now()
-        # A pausing group books only the part of the window in which every field
-        # the module cannot do without was measured; None for every other commit,
-        # which books exactly as it always has.
-        share = None
-        if blocked is not None:
-            required = _REQUIRED_SENSOR_FIELDS.get(m[const.MODULE_NAME])
-            watermark = coerce_stamp(
-                zone.get(const.ZONE_LAST_CONSUMED), STAMP_FROM_STORE
-            )
-            if required is not None and watermark is not None:
-                share = valid_share(
-                    blocked, required, watermark, coerce_stamp(now, STAMP_FROM_STORE)
-                )
         # precip = 0
         ha_config_is_metric = self.hass.config.units is METRIC_SYSTEM
         bucket = zone.get(const.ZONE_BUCKET)
@@ -1268,10 +1291,26 @@ class CalculationMixin:
         # it would warn the user to check a sensor whose reading the calculation
         # never used. A clamp warning has to mean something.
         hourly = (
-            self._hourly_et_for_zone(zone, modinst, now=now)
+            self._hourly_et_for_zone(zone, modinst, now=now, blocked=blocked)
             if module_uses_precipitation
             else None
         )
+        # A pausing group books only the part of the window in which every field
+        # the form that ran cannot do without was measured; None for every other
+        # commit, which books exactly as it always has. The hourly rows charge
+        # each hour for that part already, so there the share only names it.
+        required = required_sensor_fields(
+            m[const.MODULE_NAME], hourly=hourly is not None
+        )
+        share = None
+        if blocked is not None:
+            watermark = coerce_stamp(
+                zone.get(const.ZONE_LAST_CONSUMED), STAMP_FROM_STORE
+            )
+            if required is not None and watermark is not None:
+                share = valid_share(
+                    blocked, required, watermark, coerce_stamp(now, STAMP_FROM_STORE)
+                )
         delta = 0.0
         if m[const.MODULE_NAME] == "PyETO":
             # share 0: a field the equation cannot do without was silent for the
@@ -1380,7 +1419,13 @@ class CalculationMixin:
         # stops acting and the gap is frozen in.
         applied = pending_bucket_events(zone)
         steps = self._substeps_for_zone(
-            zone, precip, now=now, hourly_et=hourly_et, applied=applied
+            zone,
+            precip,
+            now=now,
+            hourly_et=hourly_et,
+            applied=applied,
+            blocked=blocked,
+            required=required or (),
         )
         # Consumed whether or not the replay ran: the single-shot path cannot
         # place them, and carrying them into a later window would put them
```

- [x] **Step 4: GREEN**

Run: wie Step 2. Expected: `10 passed`, dazu 8 Teardown-ERROR „Lingering timer“.

- [x] **Step 5: Prüfen**

```bash
uvx black custom_components/irrigation_plus/ && uvx ruff@0.16.10 check custom_components/irrigation_plus/
../task_compare.sh t4 tests/test_silent_sensor_hourly_commit.py tests/test_silent_sensor_commit.py tests/test_summed_hourly_eto.py tests/test_water_balance_substeps.py tests/test_live_estimate_replayed_balance.py tests/test_live_estimate_without_hourly_calculation.py
```

Expected: kein Baseline-Name entfällt; keine neuen FAILED; neue ERROR nur 8 in `test_silent_sensor_hourly_commit.py`.

- [x] **Step 6: Commit**

```bash
git add custom_components/irrigation_plus/calculation.py tests/test_silent_sensor_hourly_commit.py
git commit -F - <<'EOF'
feat(calculation): the hourly form books a pausing group's measured time

The commit hands the blocked spans to the hourly rows and to the replayed
balance, and takes the share once the form is known: the hourly form
needs temperature, humidity, wind and the sun, the daily form its own
fields (required_sensor_fields, shared with the live estimate). The
hourly total already holds the measured part and is not scaled again;
the explanation names the time share. Nothing reaches this in operation
while the gate still declines the hourly calculation.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
```

### Task 5: Das Gate fällt — Hinweis, Log, Panel-Hilfe, Doku

**Files:**
- Modify: `custom_components/irrigation_plus/calculation.py` (`_blocked_spans_for_zone`)
- Modify: `custom_components/irrigation_plus/sensor_liveness.py` (Moduldocstring `:11-14`, `_group_cuts` `:585-595`,
  `async_resync_stale_issue` Docstring)
- Modify: `custom_components/irrigation_plus/__init__.py` (`:1246-1250` entfällt)
- Modify: `custom_components/irrigation_plus/const.py` (Kommentar `:715-718`)
- Modify: `custom_components/irrigation_plus/weather_aggregate.py` (Docstring `aggregate_window` `:346-350`)
- Modify: `custom_components/irrigation_plus/frontend/localize/languages/*.json` (8) und 2 Bundles in `dist/`
- Modify: `docs/configuration-sensor-groups.md` (Zeile 59 und 62, Wortlaut nach Freigabe)
- Test: `tests/test_silent_sensor_commit.py`, `tests/test_sensor_liveness_coordinator.py` (je 2 Tests umgedreht)

**Interfaces:** keine neuen Namen.

- [x] **Step 1: Die vier Tests des Zwischenstands umdrehen**

Modify `tests/test_sensor_liveness_coordinator.py`:

```diff
diff --git a/tests/test_sensor_liveness_coordinator.py b/tests/test_sensor_liveness_coordinator.py
index b503f756..004ccad1 100644
--- a/tests/test_sensor_liveness_coordinator.py
+++ b/tests/test_sensor_liveness_coordinator.py
@@ -1007,13 +1007,14 @@ class TestThePausedNotice:
         assert "no longer used" in caplog.text
         assert "still used" not in caplog.text
 
-    async def test_under_the_hourly_calculation_its_values_are_still_used(
+    async def test_under_the_hourly_calculation_too_they_are_no_longer_used(
         self, monkeypatch, caplog
     ):
         group = _pausing(_group(fields={"Temperature": "sensor.temp"}))
         key = await self._silent(monkeypatch, group, hourly=True)
-        assert key == const.ISSUE_WEATHER_SENSOR_STALE
-        assert "still used" in caplog.text
+        assert key == const.ISSUE_WEATHER_SENSOR_STALE_PAUSED
+        assert "no longer used" in caplog.text
+        assert "still used" not in caplog.text
 
     async def test_changing_the_setting_rewrites_the_open_notice(self, monkeypatch):
         coord, _, issues = _mock_store_coord(
@@ -1064,27 +1065,20 @@ class TestThePausedNotice:
             await coord.async_update_mapping_config(0, {const.MAPPING_NAME: "renamed"})
         assert issues.open["weather_sensor_stale_0"] == {}
 
-    async def test_switching_the_hourly_calculation_rewrites_open_notices(
+    async def test_switching_the_hourly_calculation_leaves_the_notice_alone(
         self, monkeypatch
     ):
+        """Both forms cut, so the switch no longer decides the notice's text."""
         group = _pausing(_sensor_group_zero("sensor.old"))
         coord, store, issues = _mock_store_coord(monkeypatch, group)
         store.async_update_config = AsyncMock()
         store.async_get_mappings = AsyncMock(return_value=[group])
 
-        store.config = _hourly(True)
-        with patch("custom_components.irrigation_plus.async_dispatcher_send"):
-            await coord.async_update_config({const.CONF_HOURLY_CALCULATION: True})
-        assert issues.open["weather_sensor_stale_0"]["translation_key"] == (
-            const.ISSUE_WEATHER_SENSOR_STALE
-        )
-
-        store.config = _hourly(False)
-        with patch("custom_components.irrigation_plus.async_dispatcher_send"):
-            await coord.async_update_config({const.CONF_HOURLY_CALCULATION: False})
-        assert issues.open["weather_sensor_stale_0"]["translation_key"] == (
-            const.ISSUE_WEATHER_SENSOR_STALE_PAUSED
-        )
+        for hourly in (True, False):
+            store.config = _hourly(hourly)
+            with patch("custom_components.irrigation_plus.async_dispatcher_send"):
+                await coord.async_update_config({const.CONF_HOURLY_CALCULATION: hourly})
+            assert issues.open["weather_sensor_stale_0"] == {}
 
     async def test_a_group_without_an_open_outage_is_not_asked_about(self, monkeypatch):
         group = _pausing(_sensor_group_zero("sensor.old"))
```

Modify `tests/test_silent_sensor_commit.py`:

```diff
diff --git a/tests/test_silent_sensor_commit.py b/tests/test_silent_sensor_commit.py
index 4cfad275..3b4283b9 100644
--- a/tests/test_silent_sensor_commit.py
+++ b/tests/test_silent_sensor_commit.py
@@ -121,11 +121,13 @@ class TestTheGate:
         mid = await _group(store, setting="keep", outages=[_outage(2, 10)])
         assert _gate(c, store, await _zone(store, mid)) is None
 
-    async def test_with_the_hourly_calculation_nothing_is_cut(self, coord):
+    async def test_the_hourly_calculation_is_cut_the_same(self, coord):
         c, store = coord
         await store.async_update_config({const.CONF_HOURLY_CALCULATION: True})
         mid = await _group(store, outages=[_outage(2, 10)])
-        assert _gate(c, store, await _zone(store, mid)) is None
+        assert _gate(c, store, await _zone(store, mid)) == {
+            T: ((W + 5 * H, W + 10 * H),)
+        }
 
     async def test_a_window_no_outage_reaches_is_not_cut(self, coord):
         c, store = coord
@@ -462,9 +464,9 @@ class TestAGroupThatIsNotCutCalculatesAsBefore:
         assert keep == plain
         assert quiet == plain
 
-    async def test_a_pausing_group_under_the_hourly_calculation_matches_too(
-        self, coord
-    ):
+    async def test_a_pausing_group_under_the_hourly_switch_is_cut_too(self, coord):
+        """The stub keeps the daily form (no measured sun), so the daily fields
+        decide: temperature blocked 05:00-10:00 leaves 19 of 24 hours."""
         c, store = coord
         await store.async_update_config({const.CONF_HOURLY_CALCULATION: True})
         module_id, _ = await _module(c, store, "PyETO", returns=-4.0)
@@ -475,7 +477,9 @@ class TestAGroupThatIsNotCutCalculatesAsBefore:
             await _group(store, setting="keep"),
             await _group(store, outages=[_outage(2, 10)]),
         )
-        assert paused == plain
+        assert plain[const.ZONE_DELTA] == pytest.approx(-4.0)
+        assert paused[const.ZONE_DELTA] == pytest.approx(-4.0 * 19 / 24)
+        assert "booked for 79 % of the period" in paused[const.ZONE_EXPLANATION]
 
 
 class TestTheExplanation:
```

- [x] **Step 2: RED**

```bash
K="test_the_hourly_calculation_is_cut_the_same or test_a_pausing_group_under_the_hourly_switch_is_cut_too or test_under_the_hourly_calculation_too_they_are_no_longer_used or test_switching_the_hourly_calculation_leaves_the_notice_alone"
TZ=UTC /d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests/test_silent_sensor_commit.py tests/test_sensor_liveness_coordinator.py -p _local_socket_unblock -q -k "$K"
```

Expected: `4 failed` (im Probelauf gegen den Stand von Task 4 gemessen).

- [x] **Step 3: Implementierung (Python, Kommentare)**

Modify `custom_components/irrigation_plus/__init__.py`:

```diff
diff --git a/custom_components/irrigation_plus/__init__.py b/custom_components/irrigation_plus/__init__.py
index 68630f03..29a729cd 100644
--- a/custom_components/irrigation_plus/__init__.py
+++ b/custom_components/irrigation_plus/__init__.py
@@ -1243,11 +1243,6 @@ class SmartIrrigationCoordinator(
         if const.CONF_AUTO_UPDATE_ENABLED in data:
             await self.set_up_auto_update_time(data)
         await self.store.async_update_config(data)
-        if const.CONF_HOURLY_CALCULATION in data:
-            # A pausing group's notice says whether its values are left out,
-            # and only the daily form leaves them out.
-            for mapping in await self.store.async_get_mappings():
-                self.async_resync_stale_issue(mapping)
         async_dispatcher_send(self.hass, const.DOMAIN + "_config_updated")
 
     async def set_up_auto_update_time(self, data):  # noqa: D102
```

Modify `custom_components/irrigation_plus/calculation.py`:

```diff
diff --git a/custom_components/irrigation_plus/calculation.py b/custom_components/irrigation_plus/calculation.py
index cc432db1..07d66f9f 100644
--- a/custom_components/irrigation_plus/calculation.py
+++ b/custom_components/irrigation_plus/calculation.py
@@ -434,14 +434,11 @@ class CalculationMixin:
         The commit's window runs from the zone's watermark to ``now``, and
         ``sensor_liveness.zone_blocked_spans`` cuts it -- the function the live
         estimate asks too. A zone that has never consumed has no watermark and
-        is not cut (its first commit anchors it).
-
-        Only in the daily form for now: with the hourly calculation the replayed
-        balance checks itself against this aggregate's precipitation, so cutting
-        one and not the other would fail that check.
+        is not cut (its first commit anchors it). Every form of the calculation
+        takes the same spans: the aggregate, the hourly rows and the replayed
+        balance are cut together, so the balance still reconciles with the
+        aggregate's precipitation.
         """
-        if hourly_calculation_enabled(self.store):
-            return None
         return zone_blocked_spans(
             self.store, zone, zone.get(const.ZONE_LAST_CONSUMED), now
         )
```

Modify `custom_components/irrigation_plus/const.py`:

```diff
diff --git a/custom_components/irrigation_plus/const.py b/custom_components/irrigation_plus/const.py
index 592dad2d..68a2fc87 100644
--- a/custom_components/irrigation_plus/const.py
+++ b/custom_components/irrigation_plus/const.py
@@ -713,9 +713,9 @@ MAPPING_SENSOR_LAST_SEEN = "sensor_last_seen"
 # One repair issue per sensor group: f"{ISSUE_WEATHER_SENSOR_STALE}_{mapping_id}".
 ISSUE_WEATHER_SENSOR_STALE = "weather_sensor_stale"
 # The same notice for a group that pauses a silent sensor: its values are no
-# longer used. Chosen where the group's daily calculation really leaves the
-# silent time out: a pausing group, the hourly calculation off, and an open
-# outage with a field that is cut (see sensor_liveness.cuts_field).
+# longer used. Chosen where the group's calculation really leaves the silent time
+# out: a pausing group and an open outage with a field that is cut (see
+# sensor_liveness.cuts_field).
 ISSUE_WEATHER_SENSOR_STALE_PAUSED = "weather_sensor_stale_paused"
 # What a sensor group does with a silent sensor (MappingEntry.on_silent_sensor):
 # keep using its last value, as before, or pause it so that the silent time books
```

Modify `custom_components/irrigation_plus/sensor_liveness.py`:

```diff
diff --git a/custom_components/irrigation_plus/sensor_liveness.py b/custom_components/irrigation_plus/sensor_liveness.py
index f45f3eda..0c009009 100644
--- a/custom_components/irrigation_plus/sensor_liveness.py
+++ b/custom_components/irrigation_plus/sensor_liveness.py
@@ -10,8 +10,8 @@ while an outage is open, and a bus event when one starts and when it ends (#188)
 
 The outage record says when a sensor fell silent and the notice tells the user. A
 group that keeps a silent sensor's last value calculates as before; for a group
-that pauses it, ``blocked_spans`` turns the record into the time its daily
-calculation does not book (calculation._blocked_spans_for_zone).
+that pauses it, ``zone_blocked_spans`` turns the record into the time its
+calculation and its live estimate do not book.
 
 The rules are plain functions, testable without a running Home Assistant; the
 ``SensorLivenessMixin`` at the end is the coordinator glue.
@@ -616,16 +616,13 @@ class SensorLivenessMixin:
         )
 
     def _group_cuts(self, mapping: dict) -> bool:
-        """Whether this group's daily calculation leaves a silent sensor's time out.
+        """Whether this group's calculation leaves a silent sensor's time out.
 
-        A pausing group, and only without the hourly calculation (see
-        calculation._blocked_spans_for_zone); every other group still uses the
-        last value. Which fields it leaves out, ``cuts_field`` says.
+        A pausing group, in every form of the calculation (``zone_blocked_spans``);
+        every other group still uses the last value. Which fields it leaves out,
+        ``cuts_field`` says.
         """
-        # Imported here: calculation imports this module.
-        from .calculation import hourly_calculation_enabled
-
-        return group_pauses(mapping) and not hourly_calculation_enabled(self.store)
+        return group_pauses(mapping)
 
     def _stale_issue_key(self, mapping_id, outages: list[Outage]) -> str:
         """The notice's text: the paused one where the group's values are cut.
@@ -645,7 +642,7 @@ class SensorLivenessMixin:
         return const.ISSUE_WEATHER_SENSOR_STALE
 
     def async_resync_stale_issue(self, mapping: dict | None) -> None:
-        """Bring a group's open notice in line with its setting and the calculation form.
+        """Bring a group's open notice in line with its setting and its fields.
 
         Called when either changes; otherwise the notice is touched only when an
         outage opens or closes. A group without an open outage has no notice.
```

Modify `custom_components/irrigation_plus/weather_aggregate.py`:

```diff
diff --git a/custom_components/irrigation_plus/weather_aggregate.py b/custom_components/irrigation_plus/weather_aggregate.py
index 6d21067f..aa2684b5 100644
--- a/custom_components/irrigation_plus/weather_aggregate.py
+++ b/custom_components/irrigation_plus/weather_aggregate.py
@@ -344,8 +344,8 @@ def aggregate_window(
             produces; defaults to False so poll-only installs keep the plain
             mean they have always had.
         blocked: ``{field: ((from, to), ...)}``, each field's blocked time
-            inside the window (sensor_liveness.blocked_spans). Only a pausing
-            sensor group's daily commit passes it. A blocked field is reduced
+            inside the window (sensor_liveness.zone_blocked_spans). Only a
+            pausing sensor group's commit passes it. A blocked field is reduced
             over its valid time and left out when it has none; a field without
             spans is reduced exactly as without the argument.
 
```

- [x] **Step 4: Panel-Hilfe in 8 Sprachen** — Skript nach `D:\Entwicklung\HASI\issue8-pr3-work\strip_help.py` legen
  (per Write-Werkzeug, die englische Zeile enthält `\"`) und ausführen:

```python
"""Drop the hourly-calculation sentence from the panel help in all 8 languages.

Byte-exact: each file must contain its sentence (with the leading space) exactly
once; the file is rewritten via a temp file + os.replace, line endings untouched.
"""

import os
import sys
from pathlib import Path

DIR = Path(sys.argv[1])
SENTENCES = {
    "de.json": " Gilt nur, solange „Stündliche Verdunstung“ (Experimentelle Funktionen) aus ist.",
    "en.json": ' Applies only while \\"Hourly evapotranspiration\\" (Experimental features) is off.',
    "es.json": " Solo se aplica mientras «Evapotranspiración horaria» (Funciones experimentales) esté desactivada.",
    "fr.json": " Ne s’applique que tant que « Évapotranspiration horaire » (Fonctionnalités expérimentales) est désactivée.",
    "it.json": " Vale solo finché «Evapotraspirazione oraria» (Funzioni sperimentali) è disattivata.",
    "nl.json": " Geldt alleen zolang “Verdamping per uur” (Experimentele functies) uit staat.",
    "no.json": " Gjelder bare så lenge «Timesvis evapotranspirasjon» (Eksperimentelle funksjoner) er av.",
    "sk.json": " Platí len, kým je „Hodinová evapotranspirácia“ (Experimentálne funkcie) vypnutá.",
}

for name, sentence in SENTENCES.items():
    path = DIR / name
    data = path.read_bytes()
    needle = sentence.encode("utf-8")
    count = data.count(needle)
    if count != 1:
        sys.exit(f"{name}: sentence found {count} times, expected 1")
    tmp = path.with_suffix(".json.tmp")
    tmp.write_bytes(data.replace(needle, b"", 1))
    os.replace(tmp, path)
    print(f"{name}: removed")
```

```bash
/d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -I ../strip_help.py custom_components/irrigation_plus/frontend/localize/languages
```

Expected: 8 × `removed`; `git diff --stat` 8 Dateien, je 1 Zeile.

- [x] **Step 5: Doku** — nach der Freigabe des Wortlauts (Abschnitt *Wortlaute*); der Block zeigt die englische Fassung
  des Probelaufs:

Modify `docs/configuration-sensor-groups.md`:

```diff
diff --git a/docs/configuration-sensor-groups.md b/docs/configuration-sensor-groups.md
index a474e7b4..42f7f1cf 100644
--- a/docs/configuration-sensor-groups.md
+++ b/docs/configuration-sensor-groups.md
@@ -56,10 +56,10 @@ Irrigation Plus checks every five minutes whether the sensors of a sensor group
 
 Once a sensor has not reported for three hours, Irrigation Plus shows a repair notice for its sensor group and fires the `irrigation_plus_weather_stale` event (see [Events](usage-events.md)). When the sensor reports again, the notice clears itself and a second event marks the end. What the calculation does meanwhile depends on the sensor group's setting **When a sensor goes silent**:
 
-- **Pause** (the default for a newly created sensor group): from three hours after the sensor's last report until it reports again, its values are no longer used. Where the evapotranspiration calculation cannot do without one of them (for PyETO: temperature, dewpoint, wind speed and pressure; for the passthrough module: its evapotranspiration sensor), the daily calculation books no evapotranspiration for that time. Rain from a cumulative rain gauge still counts in full, because what the gauge reads after its return was measured, only delivered late. Zones that depend on the silent sensor therefore water less, or not at all, until it reports again. The explanation of the calculation names the silent time and the share that was booked.
+- **Pause** (the default for a newly created sensor group): from three hours after the sensor's last report until it reports again, its values are no longer used. Where the evapotranspiration calculation cannot do without one of them, no evapotranspiration is booked for that time: for PyETO's daily form that is temperature, dewpoint, wind speed and pressure, for its hourly form (**Hourly evapotranspiration**, under **Setup → Experimental**) temperature, humidity, wind speed and solar radiation, and for the passthrough module its evapotranspiration sensor. Rain from a cumulative rain gauge still counts in full, because what the gauge reads after its return was measured, only delivered late. Zones that depend on the silent sensor therefore water less, or not at all, until it reports again. The explanation of the calculation names the silent time and the share that was booked.
 - **Keep the last value** (the setting of every sensor group created before this option existed): the calculation keeps using the sensor's last value, as it always did.
 
-Pausing applies only while **Hourly evapotranspiration** (under **Setup → Experimental**) is off; with it on, the last value is still used. With the live estimate, a run during an outage can be sized on more evapotranspiration than the calculation books afterwards. The daily calculation averages a pausing sensor over the hours in which it reported, so which part of the day was missing can shift the result.
+With the live estimate, a run during an outage can be sized on more evapotranspiration than the calculation books afterwards. The hourly form works hour by hour: an hour counts only for the time in which every value it needs was measured. The daily form averages a pausing sensor over the hours in which it reported, so which part of the day was missing can shift the result. The share named in the explanation counts time: solar radiation that is silent at night lowers it while costing hardly any evapotranspiration.
 
 The three hours are fixed. An integration that updates less often, such as a cloud service polled every six hours, therefore raises the notice between its updates even though nothing has failed. If such a sensor group is on **Pause**, switch it to **Keep the last value**; otherwise part of the time between its updates is never booked.
 
```

- [x] **Step 6: Bundles bauen**

```bash
cd custom_components/irrigation_plus/frontend && npm ci && npm run build && cd -
git status --short -- custom_components/irrigation_plus/frontend/dist
git checkout -- custom_components/irrigation_plus/frontend/dist/irrigation-plus-card.js custom_components/irrigation_plus/frontend/dist/irrigation-plus-card-legacy.js
for f in custom_components/irrigation_plus/frontend/dist/*.js; do echo "$f $(grep -c 'Applies only while' $f)"; done
```

Expected: nur `irrigation-plus.js` und `irrigation-plus-card-impl.js` geändert (die anderen zwei nur im Zeilenende); in
keinem Bundle mehr „Applies only while“.

- [x] **Step 7: GREEN**

Run: wie Step 2. Expected: `4 passed` (dazu 2 Teardown-ERROR).

- [x] **Step 8: Prüfen**

```bash
uvx black custom_components/irrigation_plus/ && uvx ruff@0.16.10 check custom_components/irrigation_plus/
../task_compare.sh t5 tests/test_silent_sensor_commit.py tests/test_sensor_liveness_coordinator.py tests/test_sensor_liveness_blocked.py tests/test_i18n_completeness.py tests/test_silent_sensor_hourly_commit.py tests/test_silent_sensor_setting.py tests/test_sensor_liveness_repair.py
```

Expected: es entfallen genau die zwei alten Namen `test_with_the_hourly_calculation_nothing_is_cut` und
`test_a_pausing_group_under_the_hourly_calculation_matches_too`; keine neuen FAILED; neue ERROR nur 2 in
`test_silent_sensor_commit.py` (die umbenannten) und 8 in `test_silent_sensor_hourly_commit.py`.

- [x] **Step 9: Commit**

```bash
git add custom_components/irrigation_plus/calculation.py custom_components/irrigation_plus/sensor_liveness.py custom_components/irrigation_plus/__init__.py custom_components/irrigation_plus/const.py custom_components/irrigation_plus/weather_aggregate.py custom_components/irrigation_plus/frontend/localize/languages/ docs/configuration-sensor-groups.md tests/test_silent_sensor_commit.py tests/test_sensor_liveness_coordinator.py
git add -f custom_components/irrigation_plus/frontend/dist/
git diff --cached --name-only | wc -l    # 18
git commit -F - <<'EOF'
feat(liveness): a pausing group is cut under the hourly calculation too

Only the daily form cut, because the replayed balance checks itself
against the aggregate's rain and the hourly rows were not cut. Both are
now, so the commit's spans no longer depend on the switch: the notice and
the log say a group's values are left out wherever it pauses, switching
the hourly calculation no longer rewrites open notices, and the panel
help drops its "only while hourly is off" sentence (bundles rebuilt).
The docs name the fields each form needs and what the hourly form does
with a partly measured hour.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
```

## Teil B — Live-Schätzung

### Task 6: Die Live-Schätzung schneidet dieselben Sperren

**Files:**
- Modify: `custom_components/irrigation_plus/live_estimate.py` (Moduldocstring `:21-22`; Importe `:78-112`;
  `_HourlyCarry` `:182-206` und neue `_carried_outages`; `_aggregate_live_window` `:590-636`;
  `_observed_precip_since_mm` `:638-660`; `_buffer_hourly_et` `:718-793`; `_latest_temperature` `:888-908`;
  `_projected_extremes` `:910-965`; `_composed_day_et` `:967-1065`; `_daily_mirror_et` `:1104-1145` (nur
  durchreichen); `_buffer_water_steps` `:1147-1207`; `_intraday_for_zone` `:1305-1644`)
- Modify: `custom_components/irrigation_plus/weather_aggregate.py` (Docstring `aggregate_window`)
- Test: neu `tests/test_live_estimate_silent_sensor.py`; `tests/test_live_estimate_replayed_balance.py` (`:536`, ein
  Test-Double)

**Interfaces:**
- Consumes: `zone_blocked_spans` (Task 1), `required_sensor_fields` (Task 4), `hourly_eto_priced(…, blocked=)` (Task 2),
  `build_substeps(…, blocked=, required=)` (Task 3).
- Produces: `_HourlyCarry.outages` (Standard `()`), `_carried_outages(mapping) -> tuple`,
  `_aggregate_live_window(zone, anchor, *, now=None, blocked=None)`,
  `_observed_precip_since_mm(zone, anchor, *, now=None, blocked=None)`, `_buffer_hourly_et(…, blocked=None)`,
  `_latest_temperature(zone, agg, *, blocked=None, now=None)`, `_projected_extremes(…, blocked=None)`,
  `_composed_day_et(…, blocked=None)`, `_daily_mirror_et(…, blocked=None)`, `_buffer_water_steps(…, blocked=None,
  required=())`.

- [x] **Step 1: Tests schreiben** (und das Test-Double anpassen, das die neuen Schlüsselwörter sonst mit `TypeError`
  ablehnt — die Schätzung gälte dann als fehlgeschlagen)

Modify `tests/test_live_estimate_replayed_balance.py`:

```diff
diff --git a/tests/test_live_estimate_replayed_balance.py b/tests/test_live_estimate_replayed_balance.py
index 1586c8ff..43b1d5f9 100644
--- a/tests/test_live_estimate_replayed_balance.py
+++ b/tests/test_live_estimate_replayed_balance.py
@@ -533,7 +533,7 @@ class TestFallingBackToTheLumpedForm:
         monkeypatch.setattr(
             le.LiveEstimateMixin,
             "_observed_precip_since_mm",
-            lambda self, zone, anchor: 99.0,
+            lambda self, zone, anchor, **_kwargs: 99.0,
         )
 
         est = c._intraday_for_zone(zone, _inputs())
```

Create `tests/test_live_estimate_silent_sensor.py`:

```python
"""The live estimate of a pausing sensor group leaves out the time the commit does.

The estimate exists to show the path the stored bucket takes, so it cuts the same
spans the commit will: computed once per refresh, from the estimate's own anchor
to its ``now``, and handed to every reader of the buffer. A group that keeps is
estimated exactly as before.
"""

from datetime import timedelta

import pytest

from custom_components.irrigation_plus import const
from custom_components.irrigation_plus import live_estimate as live_estimate_module
from custom_components.irrigation_plus.sensor_liveness import Outage
from tests.test_live_estimate_replayed_balance import (
    NOW,
    T0,
    _inputs,
    _rate_readings,
    _zone,
    make_coordinator,
)

H = timedelta(hours=1)
T = const.MAPPING_TEMPERATURE


@pytest.fixture
async def coordinator(hass):
    return await make_coordinator(hass)


def _record(start_h, end_h=None, fields=(T,)):
    return Outage(
        "sensor.t",
        "dev1",
        tuple(fields),
        T0 + start_h * H,
        None if end_h is None else T0 + end_h * H,
    ).to_store()


async def _silent(store, zone, *outages, setting=const.ON_SILENT_SENSOR_PAUSE):
    await store.async_update_mapping(
        zone[const.ZONE_MAPPING],
        {
            const.MAPPING_ON_SILENT_SENSOR: setting,
            const.MAPPING_SENSOR_OUTAGES: list(outages),
        },
    )


async def _committed(c, store, zone, now=NOW):
    """What the commit writes, through its own spans."""
    zone = store.get_zone(zone[const.ZONE_ID])
    blocked = c._blocked_spans_for_zone(zone, now=now)
    weatherdata, _ = await c._aggregate_for_zone(zone, now=now, blocked=blocked)
    return await c.calculate_module(zone, weatherdata, None, now=now, blocked=blocked)


class TestTheLiveCurveLandsOnTheCutBucket:
    async def test_the_hourly_source_agrees_with_the_commit(self, coordinator):
        """Temperature silent from 06:00 to 12:00: 09:00-12:00 is blocked."""
        c, store = coordinator
        zone = await _zone(c, store, 2.0, rain_at={20: 6.0})
        uncut = await _committed(c, store, zone)
        await _silent(store, zone, _record(6, 12))

        est = c._intraday_for_zone(store.get_zone(zone[const.ZONE_ID]), _inputs())
        data = await _committed(c, store, zone)

        assert est["method"] == "hourly_sensor"
        assert est["live_deficit"] == pytest.approx(
            round(data[const.ZONE_BUCKET], 2), abs=0.01
        )
        assert data[const.ZONE_BUCKET] > uncut[const.ZONE_BUCKET] + 0.1
        assert est["balance_form"] == "replayed"

    async def test_an_open_outage_cuts_up_to_now(self, coordinator):
        c, store = coordinator
        zone = await _zone(c, store, 2.0)
        await _silent(store, zone, _record(14))
        est = c._intraday_for_zone(store.get_zone(zone[const.ZONE_ID]), _inputs())
        data = await _committed(c, store, zone)
        assert est["live_deficit"] == pytest.approx(
            round(data[const.ZONE_BUCKET], 2), abs=0.01
        )

    async def test_a_group_that_keeps_is_estimated_as_before(self, coordinator):
        c, store = coordinator
        zone = await _zone(c, store, 2.0, rain_at={20: 6.0})
        before = c._intraday_for_zone(store.get_zone(zone[const.ZONE_ID]), _inputs())
        c._hourly_carry().clear()
        await _silent(store, zone, _record(6, 12), setting=const.ON_SILENT_SENSOR_KEEP)
        after = c._intraday_for_zone(store.get_zone(zone[const.ZONE_ID]), _inputs())
        assert after == before


class TestTheRainItPublishes:
    async def test_a_blocked_rain_rate_is_published_as_the_commit_books_it(
        self, coordinator
    ):
        """A rate is integrated over its measured time only; a gauge never
        loses rain (the commit's rule, and the published trace is its rain)."""
        c, store = coordinator
        rate = {
            const.MAPPING_PRECIPITATION: {
                const.MAPPING_CONF_AGGREGATE: const.MAPPING_CONF_AGGREGATE_RIEMANNSUM
            }
        }
        zone = await _zone(
            c,
            store,
            2.0,
            readings=_rate_readings({10: 2.0, 11: 2.0, 15: 1.0}),
            mappings_config=rate,
        )
        uncut = c._intraday_for_zone(store.get_zone(zone[const.ZONE_ID]), _inputs())
        await _silent(
            store, zone, _record(6, 12, fields=(const.MAPPING_PRECIPITATION,))
        )
        est = c._intraday_for_zone(store.get_zone(zone[const.ZONE_ID]), _inputs())
        zone = store.get_zone(zone[const.ZONE_ID])
        blocked = c._blocked_spans_for_zone(zone, now=NOW)
        weatherdata, _ = await c._aggregate_for_zone(zone, now=NOW, blocked=blocked)
        assert est["precip_since"] == pytest.approx(
            weatherdata[const.MAPPING_PRECIPITATION], abs=1e-3
        )
        assert est["precip_since"] < uncut["precip_since"] - 1.0


class TestTheSpansAreComputedOnce:
    async def test_one_refresh_asks_once(self, coordinator, monkeypatch):
        c, store = coordinator
        zone = await _zone(c, store, 2.0, rain_at={20: 6.0})
        await _silent(store, zone, _record(6, 12))
        calls = []
        real = live_estimate_module.zone_blocked_spans

        def counting(*args, **kwargs):
            calls.append(args)
            return real(*args, **kwargs)

        monkeypatch.setattr(live_estimate_module, "zone_blocked_spans", counting)
        est = c._intraday_for_zone(store.get_zone(zone[const.ZONE_ID]), _inputs())
        assert est["available"] is True
        assert len(calls) == 1
        _store, _zone_arg, start, end = calls[0]
        assert (start, end) == (T0, NOW)


class TestTheCarryFollowsTheOutages:
    """At 23:30 the hours up to 23:00 are carried. A change of the outage record
    or of the setting must price them again rather than reuse them."""

    LATE = NOW - timedelta(minutes=30)

    def _est(self, c, store, zone):
        return c._intraday_for_zone(
            store.get_zone(zone[const.ZONE_ID]), _inputs(now=self.LATE)
        )

    async def test_an_outage_that_closes_drops_the_carried_hours(self, coordinator):
        """Carried while the outage was open, hours 09-23 were blocked; it
        closed at 12:00, so 12-23 count again."""
        c, store = coordinator
        zone = await _zone(c, store, 2.0)
        await _silent(store, zone, _record(6))
        open_est = self._est(c, store, zone)
        assert c._hourly_carry()

        await _silent(store, zone, _record(6, 12))
        warm = self._est(c, store, zone)
        c._hourly_carry().clear()
        cold = self._est(c, store, zone)
        assert warm == cold
        assert warm["et_since"] > open_est["et_since"]

    async def test_switching_the_setting_drops_the_carried_hours(self, coordinator):
        c, store = coordinator
        zone = await _zone(c, store, 2.0)
        await _silent(store, zone, _record(6, 12))
        paused = self._est(c, store, zone)

        await _silent(store, zone, _record(6, 12), setting=const.ON_SILENT_SENSOR_KEEP)
        warm = self._est(c, store, zone)
        c._hourly_carry().clear()
        cold = self._est(c, store, zone)
        assert warm == cold
        assert warm["et_since"] > paused["et_since"]


class TestTheCurrentTemperature:
    async def test_a_silent_temperature_is_not_read_as_current(self, coordinator):
        c, store = coordinator
        zone = await _zone(c, store, 2.0)
        await store.async_update_mapping(
            zone[const.ZONE_MAPPING], {const.MAPPING_DATA_LAST_ENTRY: {T: 25.0}}
        )
        zone = store.get_zone(zone[const.ZONE_ID])
        assert c._latest_temperature(zone, {}) == 25.0
        silent = {T: ((NOW - 2 * H, NOW),)}
        assert c._latest_temperature(zone, {}, blocked=silent, now=NOW) is None
        earlier = {T: ((NOW - 5 * H, NOW - 2 * H),)}
        assert c._latest_temperature(zone, {}, blocked=earlier, now=NOW) == 25.0
```

- [x] **Step 2: RED**

Run: `TZ=UTC /d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests/test_live_estimate_silent_sensor.py -p _local_socket_unblock -q`
Expected: alle bis auf `test_a_group_that_keeps_is_estimated_as_before` rot — `AttributeError: module
'custom_components.irrigation_plus.live_estimate' has no attribute 'zone_blocked_spans'`, `TypeError: … _latest_temperature()
got an unexpected keyword argument 'blocked'`, Live-Eimer ≠ Commit-Eimer, kein Unterschied im Niederschlag/Übertrag.

- [x] **Step 3: Implementierung**

Modify `custom_components/irrigation_plus/live_estimate.py`:

```diff
diff --git a/custom_components/irrigation_plus/live_estimate.py b/custom_components/irrigation_plus/live_estimate.py
index 24784ff1..10122244 100644
--- a/custom_components/irrigation_plus/live_estimate.py
+++ b/custom_components/irrigation_plus/live_estimate.py
@@ -18,8 +18,8 @@ ledger:
   forecast tier available — the configured weather service, else a Home
   Assistant weather entity, else the site's own history (see
   ``day_projection``) — and the module instance the commit uses prices the
-  result, so the inputs converge on exactly what the commit will see (but for
-  a pausing sensor group's silent time; see ``_aggregate_live_window``);
+  result, so the inputs converge on exactly what the commit will see, a
+  pausing sensor group's silent time left out on both sides;
 * **the weather client's hourly series**, where one exposes solar radiation;
 * a **Hargreaves-seeded proxy** distributed over the elapsed hours, for
   providers with neither.
@@ -80,6 +80,7 @@ from .calculation import (
     hourly_radiation_series,
     pending_bucket_events,
     replayed_balance_applies,
+    required_sensor_fields,
     trailing_radiation_calibration,
     trailing_temperature_amplitude,
     zone_module_models_weather,
@@ -109,6 +110,7 @@ from .et_estimate import (
     rigorous_et_since,
 )
 from .helpers import STAMP_FROM_CLIENT, coerce_stamp, convert_between
+from .sensor_liveness import group_pauses, outages_of, zone_blocked_spans
 from .weather_aggregate import aggregate_window, build_substeps, weather_day
 
 _LOGGER = logging.getLogger(__name__)
@@ -199,11 +201,33 @@ class _HourlyCarry(NamedTuple):
     every earlier hour missing from ``build_substeps``' ``hourly_et``, which is a
     documented reason for it to refuse the window — so the estimate would fall
     back to the lumped form for as long as the carry was warm, i.e. always.
+
+    ``outages`` is the other thing a closed hour depends on: a pausing sensor
+    group's outage record (``_carried_outages``). An outage opens on the next
+    check, up to five minutes after its span began, and closes at a return that
+    can lie before the last refresh, so a carried hour can change after it
+    closed. The record, not its clipped spans, is the key: an open span ends at
+    "now" and would change it every minute.
     """
 
     anchor: datetime.datetime
     boundary: datetime.datetime
     per_hour: dict
+    outages: tuple = ()
+
+
+def _carried_outages(mapping) -> tuple:
+    """What a sensor group's cut depends on beyond the anchor: its outage record.
+
+    Empty for a group that keeps, whose record cuts nothing, so its carry is not
+    dropped for an outage it does not act on.
+    """
+    if not isinstance(mapping, dict) or not group_pauses(mapping):
+        return ()
+    return tuple(
+        (outage.entity_id, outage.start, outage.end, outage.fields)
+        for outage in outages_of(mapping)
+    )
 
 
 def _parse_stored_as_ha_local(value):
@@ -587,9 +611,8 @@ class LiveEstimateMixin:
                 _LOGGER.debug("intraday: could not resolve module %s: %s", module_id, e)
         return out
 
-    def _aggregate_live_window(self, zone, anchor, *, now=None):
-        """The zone's elapsed window, reduced exactly as ``_aggregate_for_zone`` will --
-        but for the one deliberate difference in the last paragraph.
+    def _aggregate_live_window(self, zone, anchor, *, now=None, blocked=None):
+        """The zone's elapsed window, reduced exactly as ``_aggregate_for_zone`` will.
 
         One reduction serving both halves of the estimate: the precipitation
         trace, and the day-level inputs the mirrored daily equation consumes. The
@@ -597,10 +620,8 @@ class LiveEstimateMixin:
         two agree by construction rather than by two hand-maintained argument
         lists happening to match -- which is how they drifted before.
 
-        One difference is deliberate: a pausing sensor group's commit leaves a
-        silent sensor's time out (calculation._blocked_spans_for_zone), and this
-        estimate does not, so a run during an outage can be sized on more ET than
-        the commit books afterwards.
+        ``blocked`` is a pausing sensor group's silent time over this window
+        (``zone_blocked_spans``), the same spans the commit cuts.
         """
         mapping_id = zone.get(const.ZONE_MAPPING)
         if mapping_id is None:
@@ -624,7 +645,6 @@ class LiveEstimateMixin:
             # Must match _aggregate_for_zone exactly: a different aggregation
             # here would show up as the "Live bucket" sensor disagreeing with
             # the bucket the nightly calc produces.
-            # (Apart from a pausing group's blocked time; see the docstring.)
             time_weighted=(
                 getattr(
                     getattr(self.store, "config", None),
@@ -633,9 +653,10 @@ class LiveEstimateMixin:
                 )
                 is True
             ),
+            blocked=blocked,
         )
 
-    def _observed_precip_since_mm(self, zone, anchor):
+    def _observed_precip_since_mm(self, zone, anchor, *, now=None, blocked=None):
         """Observed precipitation (mm) collected for the zone's sensor group
         since ``anchor`` (its last calculation).
 
@@ -652,9 +673,10 @@ class LiveEstimateMixin:
         The candidates are equal on a healthy install — the daily calc writes
         both watermarks from one ``now`` — which is exactly why a divergence
         only shows up after a weather-data reset or a source change and then
-        looks like anything but a window bug.
+        looks like anything but a window bug. ``now`` and ``blocked`` are the
+        caller's for the same reason: a pausing group's spans end at that ``now``.
         """
-        agg = self._aggregate_live_window(zone, anchor)
+        agg = self._aggregate_live_window(zone, anchor, now=now, blocked=blocked)
         if not agg:
             return 0.0
         return agg.get(const.MAPPING_PRECIPITATION, 0.0) or 0.0
@@ -715,7 +737,7 @@ class LiveEstimateMixin:
             return False
         return forecast_days == 0
 
-    def _buffer_hourly_et(self, zone, anchor, *, now, geometry):
+    def _buffer_hourly_et(self, zone, anchor, *, now, geometry, blocked=None):
         """``(total_mm, {hour_start: eto_mm})`` since ``anchor`` from the buffer.
 
         Summed FAO-56 hourly ETo, in the same shape ``_hourly_et_for_zone``
@@ -731,6 +753,9 @@ class LiveEstimateMixin:
 
         Cheap by construction: completed hours are carried in
         ``_hourly_carry`` and only the current partial hour is re-reduced.
+
+        ``blocked`` (a pausing group's spans from ``anchor`` to ``now``) charges
+        each hour only for its measured time, as in the commit.
         """
         if not self._hourly_form_applies(zone):
             return None
@@ -747,8 +772,14 @@ class LiveEstimateMixin:
 
         zone_id = zone.get(const.ZONE_ID)
         carry = self._hourly_carry().get(zone_id)
+        outages = _carried_outages(mapping)
         watermark, base = anchor, {}
-        if carry is not None and carry.anchor == anchor and anchor <= carry.boundary:
+        if (
+            carry is not None
+            and carry.anchor == anchor
+            and carry.outages == outages
+            and anchor <= carry.boundary
+        ):
             if carry.boundary <= now:
                 watermark, base = carry.boundary, carry.per_hour
             # A boundary in the future means the clock went backwards; recompute
@@ -766,6 +797,7 @@ class LiveEstimateMixin:
             now=now,
             last_entry=mapping.get(const.MAPPING_DATA_LAST_ENTRY),
             geometry=geometry,
+            blocked=blocked,
         )
         if priced is None:
             return None
@@ -788,7 +820,7 @@ class LiveEstimateMixin:
                 closed[hour] = closed.get(hour, 0.0) + eto
         if current_hour > watermark and closed:
             self._hourly_carry()[zone_id] = _HourlyCarry(
-                anchor, current_hour, {**base, **closed}
+                anchor, current_hour, {**base, **closed}, outages
             )
         return sum(per_hour.values()), per_hour
 
@@ -885,7 +917,7 @@ class LiveEstimateMixin:
             return None
         return _Blend(rows, commit_at.date() + datetime.timedelta(days=1))
 
-    def _latest_temperature(self, zone, agg):
+    def _latest_temperature(self, zone, agg, *, blocked=None, now=None):
         """The temperature the sensor group is reading now, or None.
 
         The self-contained projection is held to pass through this, so it
@@ -893,7 +925,14 @@ class LiveEstimateMixin:
         The mapping's last-seen entry is preferred over the window mean because
         it is the CURRENT reading; the window's mean is the fallback for a group
         that has no last entry at all.
+
+        None while a pausing group's temperature is silent at ``now``: its last
+        entry is then the dead sensor's value, and a mean is no current reading.
+        Spans end at the estimate's ``now``, so an open one reaches it.
         """
+        spans = (blocked or {}).get(const.MAPPING_TEMPERATURE, ())
+        if now is not None and any(hi >= now for _, hi in spans):
+            return None
         mapping = self.store.get_mapping(zone.get(const.ZONE_MAPPING))
         if mapping:
             latest = (mapping.get(const.MAPPING_DATA_LAST_ENTRY) or {}).get(
@@ -907,15 +946,16 @@ class LiveEstimateMixin:
         value = (agg or {}).get(const.MAPPING_TEMPERATURE)
         return None if value is None else float(value)
 
-    def _projected_extremes(self, zone, agg, inputs, *, now, window_end, geometry):
+    def _projected_extremes(
+        self, zone, agg, inputs, *, now, window_end, geometry, blocked=None
+    ):
         """``(tmin, tmax, tier)`` for the window, off the composition.
 
         Observed so far, extended over the hours the window has not reached, with
         the extremes taken from the two together. The remainder shrinks to
         nothing as the window closes, so the inputs converge on exactly what the
-        commit will see (but for a pausing sensor group's silent time; see
-        ``_aggregate_live_window``) -- no blend rule, no gate times, and no
-        residual left standing at the moment of commit.
+        commit will see -- no blend rule, no gate times, and no residual left
+        standing at the moment of commit.
 
         Tiers are tried in a fixed order. The forecast-backed ones
         arrive already resolved on ``inputs``, since the series is fetched once
@@ -944,7 +984,7 @@ class LiveEstimateMixin:
         if remainder is None:
             remainder = diurnal_remainder(
                 now,
-                self._latest_temperature(zone, agg),
+                self._latest_temperature(zone, agg, blocked=blocked, now=now),
                 trailing_temperature_amplitude(
                     self.store, zone.get(const.ZONE_MAPPING)
                 ),
@@ -965,7 +1005,17 @@ class LiveEstimateMixin:
         return low, high, tier
 
     def _composed_day_et(
-        self, zone, agg, inputs, *, anchor, now, geometry, modinst, blend=_TODAY_ALONE
+        self,
+        zone,
+        agg,
+        inputs,
+        *,
+        anchor,
+        now,
+        geometry,
+        modinst,
+        blend=_TODAY_ALONE,
+        blocked=None,
     ):
         """``(day_total_mm, tier)`` for the window's whole day, or None.
 
@@ -980,6 +1030,9 @@ class LiveEstimateMixin:
         Hargreaves stands in off the same composed
         extremes, because a day total is still needed to price the hours between
         now and a decision point, and no other source of one exists that early.
+
+        ``blocked`` is a pausing group's silent time: ``agg`` is already cut by
+        it, and a temperature silent now anchors no remainder.
         """
         if not agg:
             return None
@@ -1011,6 +1064,7 @@ class LiveEstimateMixin:
             # stretch at a day, so the window never exceeds about two.
             window_end=anchor + datetime.timedelta(hours=24),
             geometry=geometry,
+            blocked=blocked,
         )
         if low is None:
             return None
@@ -1101,7 +1155,9 @@ class LiveEstimateMixin:
             return None, None
         return observed + clearness * ra_remaining, TIER_SELF_CONTAINED
 
-    def _daily_mirror_et(self, zone, agg, inputs, *, anchor, now, geometry):
+    def _daily_mirror_et(
+        self, zone, agg, inputs, *, anchor, now, geometry, blocked=None
+    ):
         """A :class:`_DayTotal` of the window's charge from the zone's OWN daily equation, or None.
 
         The whole point: a zone that estimates solar radiation gets a live
@@ -1136,6 +1192,7 @@ class LiveEstimateMixin:
             geometry=geometry,
             modinst=modinst,
             blend=blend,
+            blocked=blocked,
         )
         if day is None:
             return None
@@ -1145,7 +1202,16 @@ class LiveEstimateMixin:
         return day._replace(total_mm=day.total_mm * float(multiplier))
 
     def _buffer_water_steps(
-        self, zone, anchor, *, now, hourly_et, precip_total, applied
+        self,
+        zone,
+        anchor,
+        *,
+        now,
+        hourly_et,
+        precip_total,
+        applied,
+        blocked=None,
+        required=(),
     ):
         """Water-balance sub-steps over the live window, or None to lump.
 
@@ -1173,6 +1239,9 @@ class LiveEstimateMixin:
         water. They are derived from the same rows by the same rule, so a
         disagreement means an assumption has broken, and lumping the window is the
         self-consistent answer.
+
+        ``blocked`` and ``required`` place a pausing group's ET where it is booked,
+        as in the commit's replay.
         """
         mapping_id = zone.get(const.ZONE_MAPPING)
         if mapping_id is None:
@@ -1191,6 +1260,8 @@ class LiveEstimateMixin:
             now=now,
             hourly_et=hourly_et,
             applied=applied,
+            blocked=blocked,
+            required=required,
         )
         if not steps:
             return None
@@ -1382,6 +1453,11 @@ class LiveEstimateMixin:
                 offset = dt_util.now().utcoffset()
                 tz_offset_h = offset.total_seconds() / 3600.0 if offset else 0.0
                 site_tz = dt_util.DEFAULT_TIME_ZONE
+            # A pausing sensor group's silent time, ONCE for this refresh and
+            # handed to every reader of the buffer below: the commit cuts the same
+            # spans, and readers that each asked for themselves would end an open
+            # outage at slightly different "now"s.
+            blocked = zone_blocked_spans(self.store, zone, anchor, now_local)
 
             rows = inputs["rows"]
             # The buffer FIRST, ahead of any weather client's own hourly series.
@@ -1396,6 +1472,7 @@ class LiveEstimateMixin:
                 anchor,
                 now=now_local,
                 geometry=geometry,
+                blocked=blocked,
             )
             hourly_et = None
             forecast_tier = None
@@ -1405,7 +1482,9 @@ class LiveEstimateMixin:
             # day-level inputs from this, and the precipitation trace is the same
             # window's rain. Two reductions of one window is a needless second
             # pass on a path that runs every minute per zone.
-            agg = self._aggregate_live_window(zone, anchor, now=now_local)
+            agg = self._aggregate_live_window(
+                zone, anchor, now=now_local, blocked=blocked
+            )
             mirrored = (
                 None
                 if buffer_et is not None
@@ -1416,13 +1495,16 @@ class LiveEstimateMixin:
                     anchor=anchor,
                     now=now_local,
                     geometry=geometry,
+                    blocked=blocked,
                 )
             )
             if buffer_et is not None:
                 et_mm, hourly_et = buffer_et
                 # Same anchor as the ET, aggregated the way the daily calc does
                 # (rate -> Riemann, cumulative gauge -> delta).
-                precip_mm = self._observed_precip_since_mm(zone, anchor)
+                precip_mm = self._observed_precip_since_mm(
+                    zone, anchor, now=now_local, blocked=blocked
+                )
                 method = "hourly_sensor"
                 # The buffer is current to now, not to the last closed hour.
                 as_of = now_local.isoformat()
@@ -1457,7 +1539,9 @@ class LiveEstimateMixin:
                 # than aggregated per source, and cut at whole-hour row
                 # boundaries instead of at the anchor. Same anchor as the ET, so
                 # the balance is still the difference of one window.
-                precip_mm = self._observed_precip_since_mm(zone, anchor)
+                precip_mm = self._observed_precip_since_mm(
+                    zone, anchor, now=now_local, blocked=blocked
+                )
                 method = "hourly"
                 as_of = window[-1]["time"] if window else None
             else:
@@ -1512,7 +1596,9 @@ class LiveEstimateMixin:
                 # actually collected into the sensor group since the last calc,
                 # aggregated the same way the daily calc does (rate->Riemann /
                 # gauge->delta), so it's time-weighted. 0 when nothing collected.
-                precip_mm = self._observed_precip_since_mm(zone, anchor)
+                precip_mm = self._observed_precip_since_mm(
+                    zone, anchor, now=now_local, blocked=blocked
+                )
                 method = "proxy"
                 as_of = local.isoformat()
 
@@ -1563,6 +1649,16 @@ class LiveEstimateMixin:
                     # the estimate is a projection from the last commit rather
                     # than a commit of its own.
                     applied=pending_bucket_events(zone),
+                    blocked=blocked,
+                    # The fields of the form the commit runs: the hourly one
+                    # exactly where the buffer source applied.
+                    required=required_sensor_fields(
+                        (self.store.get_module(zone.get(const.ZONE_MODULE)) or {}).get(
+                            const.MODULE_NAME
+                        ),
+                        hourly=buffer_et is not None,
+                    )
+                    or (),
                 )
             # Drainage comes back alongside the deficit rather than being
             # re-derived: it is a trace of its own on the dashboard (bucket,
```

Modify `custom_components/irrigation_plus/weather_aggregate.py`:

```diff
diff --git a/custom_components/irrigation_plus/weather_aggregate.py b/custom_components/irrigation_plus/weather_aggregate.py
index aa2684b5..4846e3bd 100644
--- a/custom_components/irrigation_plus/weather_aggregate.py
+++ b/custom_components/irrigation_plus/weather_aggregate.py
@@ -345,9 +345,9 @@ def aggregate_window(
             mean they have always had.
         blocked: ``{field: ((from, to), ...)}``, each field's blocked time
             inside the window (sensor_liveness.zone_blocked_spans). Only a
-            pausing sensor group's commit passes it. A blocked field is reduced
-            over its valid time and left out when it has none; a field without
-            spans is reduced exactly as without the argument.
+            pausing sensor group's commit and live estimate pass it. A blocked
+            field is reduced over its valid time and left out when it has none;
+            a field without spans is reduced exactly as without the argument.
 
     Returns:
         The aggregated weather dict (including ``MAPPING_DATA_MULTIPLIER``), or
```

- [x] **Step 4: GREEN**

Run: wie Step 2. Expected: `8 passed`, dazu Teardown-ERROR.

- [x] **Step 5: Prüfen**

```bash
uvx black custom_components/irrigation_plus/ && uvx ruff@0.16.10 check custom_components/irrigation_plus/
../task_compare.sh t6 $(ls tests/test_live_estimate*.py tests/test_silent_sensor*.py tests/test_next_irrigation*.py)
```

Expected: es entfallen nur die zwei in Task 5 umbenannten Namen; keine neuen FAILED; neue ERROR nur aus den neuen Dateien
und den zwei umbenannten Tests.

- [x] **Step 6: Commit**

```bash
git add custom_components/irrigation_plus/live_estimate.py custom_components/irrigation_plus/weather_aggregate.py tests/test_live_estimate_silent_sensor.py tests/test_live_estimate_replayed_balance.py
git commit -F - <<'EOF'
feat(live): the live estimate leaves out a pausing group's silent time

The estimate exists to show the path the stored bucket takes, so it now
cuts the spans the commit will: computed once per refresh from its own
anchor to its now and handed to every reader of the buffer -- the
aggregate and its rain, the hourly rows, the replayed balance, and the
current temperature, which is not read from a sensor silent right now.
The completed-hour carry is keyed on the group's outage record and
setting as well: an outage opens on the next check and closes at a
return that can lie before the last refresh, so a carried hour can
change after it closed. A group that keeps is estimated as before.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
```

### Task 7: Der Tagesform-Spiegel bucht den Anteil des Commits

**Files:**
- Modify: `custom_components/irrigation_plus/live_estimate.py` (Import `valid_share`; `_daily_mirror_et`)
- Modify: `docs/configuration-sensor-groups.md` (Satz zur Live-Schätzung in Zeile 62)
- Test: neu `tests/test_live_estimate_silent_sensor_daily.py` (erste zwei Klassen)

**Interfaces:**
- Consumes: `required_sensor_fields` (Task 4), `valid_share` (PR 2), `_daily_mirror_et(…, blocked=)` (Task 6).
- Produces: `_daily_mirror_et` gibt bei Anteil 0 `_DayTotal(0.0, TIER_OBSERVED)` statt `None`.

- [x] **Step 1: Tests schreiben**

Create `tests/test_live_estimate_silent_sensor_daily.py`:

```python
"""The live estimate's daily mirror of a pausing sensor group books what the commit does.

A zone whose commit runs the daily equation is estimated by that same equation
over the elapsed window. For a pausing group the commit books only the share of
the window in which every field of the daily form was measured, so the mirror
books that share too. A field silent for the whole window leaves nothing to book
-- which is an answer, not a reason to price the window from a weather service.
"""

from datetime import timedelta

import pytest

from custom_components.irrigation_plus import const
from custom_components.irrigation_plus.sensor_liveness import Outage
from tests.test_live_estimate_replayed_balance import (
    ANCHOR,
    WINDOW_END,
    _estimating_inputs,
    _estimating_zone,
    _hourly_forecast,
    _provider_rows,
    make_coordinator,
)

H = timedelta(hours=1)
T = const.MAPPING_TEMPERATURE


@pytest.fixture
async def coordinator(hass):
    """The shipped default: the hourly calculation off, the daily form runs."""
    return await make_coordinator(hass, hourly_calculation=False)


async def _silent(store, zone, start_h, end_h=None, fields=(T,)):
    await store.async_update_mapping(
        zone[const.ZONE_MAPPING],
        {
            const.MAPPING_ON_SILENT_SENSOR: const.ON_SILENT_SENSOR_PAUSE,
            const.MAPPING_SENSOR_OUTAGES: [
                Outage(
                    "sensor.t",
                    "dev1",
                    tuple(fields),
                    ANCHOR + start_h * H,
                    None if end_h is None else ANCHOR + end_h * H,
                ).to_store()
            ],
        },
    )


async def _committed(c, store, zone, now=WINDOW_END):
    zone = store.get_zone(zone[const.ZONE_ID])
    blocked = c._blocked_spans_for_zone(zone, now=now)
    weatherdata, _ = await c._aggregate_for_zone(zone, now=now, blocked=blocked)
    return await c.calculate_module(zone, weatherdata, None, now=now, blocked=blocked)


def _estimate(c, store, zone, instance, module, **inputs_kw):
    inputs = _estimating_inputs(instance, module, forecast=_hourly_forecast())
    inputs.update(inputs_kw)
    return c._intraday_for_zone(store.get_zone(zone[const.ZONE_ID]), inputs)


class TestTheMirrorBooksTheShare:
    async def test_it_lands_on_the_cut_bucket(self, coordinator):
        """Temperature silent from 4 h to 12 h after the anchor, frozen at 40 °C
        and stamped fresh by the poll: 7-12 h blocked."""
        c, store = coordinator
        zone, module, instance = await _estimating_zone(c, store, 2.0)
        store.set_mapping_buffer(
            zone[const.ZONE_MAPPING],
            [
                (
                    {**row, T: 40.0}
                    if ANCHOR + 7 * H <= row[const.RETRIEVED_AT] < ANCHOR + 12 * H
                    else row
                )
                for row in store.get_mapping_buffer(zone[const.ZONE_MAPPING])
            ],
        )
        uncut = await _committed(c, store, zone)
        await _silent(store, zone, 4, 12)

        est = _estimate(c, store, zone, instance, module)
        data = await _committed(c, store, zone)

        assert est["method"] == "daily_mirror"
        assert est["live_deficit"] == pytest.approx(
            round(data[const.ZONE_BUCKET], 2), abs=0.01
        )
        assert data[const.ZONE_BUCKET] > uncut[const.ZONE_BUCKET] + 0.3

    async def test_a_field_the_daily_form_does_without_changes_nothing(
        self, coordinator
    ):
        c, store = coordinator
        zone, module, instance = await _estimating_zone(c, store, 2.0)
        plain = _estimate(c, store, zone, instance, module)
        await _silent(store, zone, 4, 12, fields=(const.MAPPING_HUMIDITY,))
        assert _estimate(c, store, zone, instance, module) == plain


class TestNothingMeasuredIsNothingBooked:
    async def test_it_does_not_fall_back_to_a_weather_service(self, coordinator):
        """A client's hourly series is at hand, and would be the next source."""
        c, store = coordinator
        zone, module, instance = await _estimating_zone(c, store, 2.0)
        rows = _provider_rows(0.0)
        await _silent(store, zone, -4)

        est = _estimate(c, store, zone, instance, module, rows=rows, tz=0.0)
        data = await _committed(c, store, zone)

        assert est["method"] == "daily_mirror"
        assert est["et_since"] == 0.0
        assert est["live_deficit"] == pytest.approx(
            round(data[const.ZONE_BUCKET], 2), abs=0.01
        )
```

- [x] **Step 2: RED**

Run: `TZ=UTC /d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests/test_live_estimate_silent_sensor_daily.py -p _local_socket_unblock -q`
Expected: `2 failed, 1 passed` — der Live-Eimer verfehlt den gebuchten (ohne Anteil), und
`AssertionError: assert 'hourly' == 'daily_mirror'` (die Kette rutscht zur Stundenreihe des Wetterdienstes).

- [x] **Step 3: Implementierung**

Modify `custom_components/irrigation_plus/live_estimate.py`:

```diff
diff --git a/custom_components/irrigation_plus/live_estimate.py b/custom_components/irrigation_plus/live_estimate.py
index 10122244..7bfc4141 100644
--- a/custom_components/irrigation_plus/live_estimate.py
+++ b/custom_components/irrigation_plus/live_estimate.py
@@ -110,7 +110,12 @@ from .et_estimate import (
     rigorous_et_since,
 )
 from .helpers import STAMP_FROM_CLIENT, coerce_stamp, convert_between
-from .sensor_liveness import group_pauses, outages_of, zone_blocked_spans
+from .sensor_liveness import (
+    group_pauses,
+    outages_of,
+    valid_share,
+    zone_blocked_spans,
+)
 from .weather_aggregate import aggregate_window, build_substeps, weather_day
 
 _LOGGER = logging.getLogger(__name__)
@@ -1165,14 +1170,19 @@ class LiveEstimateMixin:
         computed with a different equation and then compared against it.
 
         The elapsed window is reduced by the same call the commit reduces the
-        whole window with (a pausing sensor group's silent time aside; see
-        ``_aggregate_live_window``), its day-level extremes are replaced by the
-        composed ones, and the zone's own module instance prices the result.
-        The window's share is ``MAPPING_DATA_MULTIPLIER`` -- the commit's own
+        whole window with, its day-level extremes are replaced by the composed
+        ones, and the zone's own module instance prices the result. The window's
+        share is ``MAPPING_DATA_MULTIPLIER`` -- the commit's own
         ``hour_multiplier`` out of the same aggregate -- so the estimate charges
         the elapsed hours at the rate the projected day total sets, and never
         charges past now.
 
+        A pausing sensor group's commit books only the part of the window in
+        which every field of its daily form was measured (``blocked``), so this
+        books the same part. With none, nothing is booked: a field silent
+        throughout answers 0 here rather than None, which would send the source
+        chain on to a weather service the commit never books from.
+
         The crop coefficient is deliberately NOT applied here; the caller applies
         it to whichever source produced the window total, exactly as the commit
         applies it to the ET term alone.
@@ -1183,6 +1193,14 @@ class LiveEstimateMixin:
         blend = self._mirror_blend(zone, modinst, inputs, anchor=anchor, now=now)
         if blend is None:
             return None
+        share = None
+        if blocked:
+            module = self.store.get_module(zone.get(const.ZONE_MODULE)) or {}
+            fields = required_sensor_fields(module.get(const.MODULE_NAME))
+            if fields is not None:
+                share = valid_share(blocked, fields, anchor, now)
+                if share == 0:
+                    return _DayTotal(0.0, TIER_OBSERVED)
         day = self._composed_day_et(
             zone,
             agg,
@@ -1199,7 +1217,10 @@ class LiveEstimateMixin:
         multiplier = agg.get(const.MAPPING_DATA_MULTIPLIER)
         if multiplier is None:
             return None
-        return day._replace(total_mm=day.total_mm * float(multiplier))
+        total = day.total_mm * float(multiplier)
+        if share is not None:
+            total *= share
+        return day._replace(total_mm=total)
 
     def _buffer_water_steps(
         self,
```

Doku (Wortlaut nach Freigabe; englische Fassung des Probelaufs):

Modify `docs/configuration-sensor-groups.md`:

```diff
diff --git a/docs/configuration-sensor-groups.md b/docs/configuration-sensor-groups.md
index 42f7f1cf..2d8bc77c 100644
--- a/docs/configuration-sensor-groups.md
+++ b/docs/configuration-sensor-groups.md
@@ -59,7 +59,7 @@ Once a sensor has not reported for three hours, Irrigation Plus shows a repair n
 - **Pause** (the default for a newly created sensor group): from three hours after the sensor's last report until it reports again, its values are no longer used. Where the evapotranspiration calculation cannot do without one of them, no evapotranspiration is booked for that time: for PyETO's daily form that is temperature, dewpoint, wind speed and pressure, for its hourly form (**Hourly evapotranspiration**, under **Setup → Experimental**) temperature, humidity, wind speed and solar radiation, and for the passthrough module its evapotranspiration sensor. Rain from a cumulative rain gauge still counts in full, because what the gauge reads after its return was measured, only delivered late. Zones that depend on the silent sensor therefore water less, or not at all, until it reports again. The explanation of the calculation names the silent time and the share that was booked.
 - **Keep the last value** (the setting of every sensor group created before this option existed): the calculation keeps using the sensor's last value, as it always did.
 
-With the live estimate, a run during an outage can be sized on more evapotranspiration than the calculation books afterwards. The hourly form works hour by hour: an hour counts only for the time in which every value it needs was measured. The daily form averages a pausing sensor over the hours in which it reported, so which part of the day was missing can shift the result. The share named in the explanation counts time: solar radiation that is silent at night lowers it while costing hardly any evapotranspiration.
+The live estimate leaves out the same time as the calculation, so a run during an outage is not sized on more evapotranspiration than is booked afterwards. The hourly form works hour by hour: an hour counts only for the time in which every value it needs was measured. The daily form averages a pausing sensor over the hours in which it reported, so which part of the day was missing can shift the result. The share named in the explanation counts time: solar radiation that is silent at night lowers it while costing hardly any evapotranspiration.
 
 The three hours are fixed. An integration that updates less often, such as a cloud service polled every six hours, therefore raises the notice between its updates even though nothing has failed. If such a sensor group is on **Pause**, switch it to **Keep the last value**; otherwise part of the time between its updates is never booked.
 
```

- [x] **Step 4: GREEN**

Run: wie Step 2. Expected: `3 passed`, dazu Teardown-ERROR.

- [x] **Step 5: Prüfen**

```bash
uvx black custom_components/irrigation_plus/ && uvx ruff@0.16.10 check custom_components/irrigation_plus/
../task_compare.sh t7 $(ls tests/test_live_estimate*.py tests/test_silent_sensor*.py tests/test_next_irrigation*.py)
```

- [x] **Step 6: Commit**

```bash
git add custom_components/irrigation_plus/live_estimate.py docs/configuration-sensor-groups.md tests/test_live_estimate_silent_sensor_daily.py
git commit -F - <<'EOF'
feat(live): the daily mirror books the share the commit books

A zone whose commit runs the daily equation is estimated by that
equation over the elapsed window; for a pausing group the commit books
only the part in which every field of the daily form was measured, so
the mirror books that part too. A field silent throughout now answers 0
instead of None: None sent the source chain on to a weather service's
hourly series, a source the commit never books from. The docs say the
live estimate leaves out the same time.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
```

### Task 8: Die Hochrechnung rechnet aus der gemessenen Zeit

**Files:**
- Modify: `custom_components/irrigation_plus/live_estimate.py` (`_carry_estimate_to` `:1828-1982`)
- Test: `tests/test_live_estimate_silent_sensor_daily.py` (Klasse `TestTheProjectionToTheDecisionPoint`)

**Interfaces:**
- Consumes: `zone_blocked_spans` (Task 1), `_aggregate_live_window(…, blocked=)` und `_composed_day_et(…, blocked=)`
  (Task 6).

- [x] **Step 1: Tests schreiben**

Modify `tests/test_live_estimate_silent_sensor_daily.py`:

```diff
diff --git a/tests/test_live_estimate_silent_sensor_daily.py b/tests/test_live_estimate_silent_sensor_daily.py
index 7fd0b71a..9a568ec7 100644
--- a/tests/test_live_estimate_silent_sensor_daily.py
+++ b/tests/test_live_estimate_silent_sensor_daily.py
@@ -12,6 +12,7 @@ from datetime import timedelta
 import pytest
 
 from custom_components.irrigation_plus import const
+from custom_components.irrigation_plus import live_estimate as live_estimate_module
 from custom_components.irrigation_plus.sensor_liveness import Outage
 from tests.test_live_estimate_replayed_balance import (
     ANCHOR,
@@ -119,3 +120,65 @@ class TestNothingMeasuredIsNothingBooked:
         assert est["live_deficit"] == pytest.approx(
             round(data[const.ZONE_BUCKET], 2), abs=0.01
         )
+
+
+class TestTheProjectionToTheDecisionPoint:
+    """The projection books nothing, but it is priced off the window's observed
+    part -- which for a pausing group is the part that was measured."""
+
+    MID = ANCHOR + 14 * H
+    UNTIL = ANCHOR + 20 * H
+
+    async def _frozen_zone(self, c, store):
+        """While silent from 7 h after the anchor the sensor froze at 40 °C, a
+        poll stamping it fresh. The reading at ``MID`` itself is a measurement:
+        an open span ends at the refresh's "now", half-open."""
+        zone, module, instance = await _estimating_zone(c, store, 2.0)
+        readings = [
+            (
+                {**row, T: 40.0}
+                if ANCHOR + 7 * H <= row[const.RETRIEVED_AT] < self.MID
+                else row
+            )
+            for row in store.get_mapping_buffer(zone[const.ZONE_MAPPING])
+            if row[const.RETRIEVED_AT] <= self.MID
+        ]
+        store.set_mapping_buffer(zone[const.ZONE_MAPPING], readings)
+        inputs = _estimating_inputs(
+            instance, module, now=self.MID, forecast=_hourly_forecast()
+        )
+        return zone, inputs
+
+    def _projected(self, c, store, zone, inputs):
+        zone = store.get_zone(zone[const.ZONE_ID])
+        estimate = c._intraday_for_zone(zone, inputs)
+        return c._carry_estimate_to(zone, estimate, inputs, self.UNTIL)
+
+    async def test_it_is_priced_from_the_cut_window(self, coordinator):
+        c, store = coordinator
+        zone, inputs = await self._frozen_zone(c, store)
+        kept = self._projected(c, store, zone, inputs)
+        await _silent(store, zone, 4)
+        paused = self._projected(c, store, zone, inputs)
+        assert kept["carried_to_decision"] is True
+        assert paused["carried_to_decision"] is True
+        assert paused["projected_et"] < kept["projected_et"]
+
+    async def test_it_asks_for_its_spans_once(self, coordinator, monkeypatch):
+        c, store = coordinator
+        zone, inputs = await self._frozen_zone(c, store)
+        await _silent(store, zone, 4)
+        estimate = c._intraday_for_zone(store.get_zone(zone[const.ZONE_ID]), inputs)
+        calls = []
+        real = live_estimate_module.zone_blocked_spans
+
+        def counting(*args, **kwargs):
+            calls.append(args)
+            return real(*args, **kwargs)
+
+        monkeypatch.setattr(live_estimate_module, "zone_blocked_spans", counting)
+        c._carry_estimate_to(
+            store.get_zone(zone[const.ZONE_ID]), estimate, inputs, self.UNTIL
+        )
+        assert len(calls) == 1
+        assert calls[0][2:] == (ANCHOR, self.MID)
```

- [x] **Step 2: RED**

Run: `TZ=UTC /d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests/test_live_estimate_silent_sensor_daily.py -p _local_socket_unblock -q -k Projection`
Expected: `2 failed` — `assert 1.6405 < 1.6405` (die Hochrechnung bleibt ungeschnitten) und `assert 0 == 1` (keine
Sperren erfragt).

- [x] **Step 3: Implementierung**

Modify `custom_components/irrigation_plus/live_estimate.py`:

```diff
diff --git a/custom_components/irrigation_plus/live_estimate.py b/custom_components/irrigation_plus/live_estimate.py
index 7bfc4141..fc481527 100644
--- a/custom_components/irrigation_plus/live_estimate.py
+++ b/custom_components/irrigation_plus/live_estimate.py
@@ -2007,7 +2007,13 @@ class LiveEstimateMixin:
                     v if metric else convert_between(const.UNIT_MM, const.UNIT_INCH, v)
                 )
 
-            agg = self._aggregate_live_window(zone, anchor, now=now_local)
+            # A pausing group's silent time, once: the projection books nothing,
+            # but it is priced off the window's observed part, and a dead
+            # sensor's frozen value is no observation.
+            blocked = zone_blocked_spans(self.store, zone, anchor, now_local)
+            agg = self._aggregate_live_window(
+                zone, anchor, now=now_local, blocked=blocked
+            )
             modinst = (inputs.get("modules") or {}).get(zone.get(const.ZONE_MODULE))
             # Only the zones whose commit runs the daily equation may be priced
             # by their own module: for anyone else that instance is configured
@@ -2026,6 +2032,7 @@ class LiveEstimateMixin:
                 geometry=geometry,
                 modinst=modinst if own_equation else None,
                 blend=blend if own_equation else _TODAY_ALONE,
+                blocked=blocked,
             )
             if day is None:
                 return projected
```

- [x] **Step 4: GREEN**

Run: `… -m pytest tests/test_live_estimate_silent_sensor_daily.py …`. Expected: `5 passed`, dazu Teardown-ERROR.

- [x] **Step 5: Prüfen**

```bash
uvx black custom_components/irrigation_plus/ && uvx ruff@0.16.10 check custom_components/irrigation_plus/
../task_compare.sh t8 $(ls tests/test_live_estimate*.py tests/test_silent_sensor*.py tests/test_next_irrigation*.py)
```

- [x] **Step 6: Commit**

```bash
git add custom_components/irrigation_plus/live_estimate.py tests/test_live_estimate_silent_sensor_daily.py
git commit -F - <<'EOF'
feat(live): the projection to the decision point is priced off measured time

The projection books nothing, but it composes the day from the window's
observed part, and a dead sensor's frozen value is no observation. It
takes the group's spans once, from the same anchor and now, and composes
the day from the cut aggregate; whether the sensor will return is not
assumed either way.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
```

### Task 9: Ein Ausfall frischt die Live-Schätzung auf

**Files:**
- Modify: `custom_components/irrigation_plus/sensor_liveness.py` (`async_check_sensor_liveness` `:465-484`, neue
  `_refresh_estimates_after_outage_change`, `_async_check_mapping_liveness` gibt `bool` zurück)
- Test: `tests/test_sensor_liveness_coordinator.py` (neue Klasse `TestTheEstimateFollowsTheRecord`)

**Interfaces:**
- Consumes: `LiveEstimateMixin.async_refresh_zone_estimates` (vorhanden, über `getattr`, weil Test-Doubles der Prüfung
  ohne ihn laufen).
- Produces: `_async_check_mapping_liveness(…) -> bool` — wahr, wenn bei einer pausierenden Gruppe ein Ausfall geöffnet
  oder geschlossen wurde.

- [x] **Step 1: Tests schreiben**

Modify `tests/test_sensor_liveness_coordinator.py`:

```diff
diff --git a/tests/test_sensor_liveness_coordinator.py b/tests/test_sensor_liveness_coordinator.py
index 004ccad1..895a4700 100644
--- a/tests/test_sensor_liveness_coordinator.py
+++ b/tests/test_sensor_liveness_coordinator.py
@@ -1214,3 +1214,75 @@ class TestThePausedNotice:
         assert sensor_liveness.cuts_field("Precipitation", gauge) is False
         assert sensor_liveness.cuts_field("Precipitation", rate) is True
         assert sensor_liveness.cuts_field("Temperature", gauge) is True
+
+
+class TestTheEstimateFollowsTheRecord:
+    """A pausing group's live estimate cuts its outages, and a silent station
+    writes no rows that would refresh it -- so the check does, once, when an
+    outage of such a group opens or closes."""
+
+    def _silent_station(self, monkeypatch, *groups):
+        last = T0 - STALE - timedelta(seconds=1)
+        coord, store, issues = _coord(
+            monkeypatch,
+            list(groups),
+            {
+                "sensor.temp": _state("sensor.temp", "21.5", last),
+                "sensor.wind": _state("sensor.wind", "2.0", last),
+            },
+            {"dev1": ["sensor.temp"], "dev2": ["sensor.wind"]},
+        )
+        coord.async_refresh_zone_estimates = AsyncMock()
+        return coord, store
+
+    async def test_an_outage_that_opens_refreshes_the_estimates(self, monkeypatch):
+        coord, _ = self._silent_station(
+            monkeypatch, _pausing(_group(fields={"Temperature": "sensor.temp"}))
+        )
+        await coord.async_check_sensor_liveness(now=T0)
+        coord.async_refresh_zone_estimates.assert_awaited_once()
+
+    async def test_a_check_that_changes_nothing_does_not(self, monkeypatch):
+        coord, _ = self._silent_station(
+            monkeypatch, _pausing(_group(fields={"Temperature": "sensor.temp"}))
+        )
+        await coord.async_check_sensor_liveness(now=T0)
+        await coord.async_check_sensor_liveness(now=T0 + timedelta(minutes=5))
+        coord.async_refresh_zone_estimates.assert_awaited_once()
+
+    async def test_an_outage_that_closes_refreshes_them_again(self, monkeypatch):
+        coord, _ = self._silent_station(
+            monkeypatch, _pausing(_group(fields={"Temperature": "sensor.temp"}))
+        )
+        await coord.async_check_sensor_liveness(now=T0)
+        back = T0 + timedelta(minutes=3)
+        coord.hass.states.get = Mock(
+            side_effect={"sensor.temp": _state("sensor.temp", "22.0", back)}.get
+        )
+        await coord.async_check_sensor_liveness(now=T0 + timedelta(minutes=5))
+        assert coord.async_refresh_zone_estimates.await_count == 2
+
+    async def test_a_group_that_keeps_does_not(self, monkeypatch):
+        coord, store = self._silent_station(
+            monkeypatch, _group(fields={"Temperature": "sensor.temp"})
+        )
+        await coord.async_check_sensor_liveness(now=T0)
+        assert store.mappings[1][const.MAPPING_SENSOR_OUTAGES]
+        coord.async_refresh_zone_estimates.assert_not_awaited()
+
+    async def test_two_groups_in_one_check_refresh_once(self, monkeypatch):
+        coord, _ = self._silent_station(
+            monkeypatch,
+            _pausing(_group(1, fields={"Temperature": "sensor.temp"})),
+            _pausing(_group(2, name="Lawn", fields={"Windspeed": "sensor.wind"})),
+        )
+        await coord.async_check_sensor_liveness(now=T0)
+        coord.async_refresh_zone_estimates.assert_awaited_once()
+
+    async def test_a_refresh_that_fails_leaves_the_check_intact(self, monkeypatch):
+        coord, store = self._silent_station(
+            monkeypatch, _pausing(_group(fields={"Temperature": "sensor.temp"}))
+        )
+        coord.async_refresh_zone_estimates = AsyncMock(side_effect=RuntimeError)
+        await coord.async_check_sensor_liveness(now=T0)
+        assert store.mappings[1][const.MAPPING_SENSOR_OUTAGES]
```

- [x] **Step 2: RED**

Run: `TZ=UTC /d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests/test_sensor_liveness_coordinator.py -p _local_socket_unblock -q -k TestTheEstimateFollowsTheRecord`
Expected: `4 failed, 2 passed` (`Expected mock to have been awaited once. Awaited 0 times.`; die zwei grünen sind die
Wächter „behalten“ und „Fehler bleibt folgenlos“).

- [x] **Step 3: Implementierung**

Modify `custom_components/irrigation_plus/sensor_liveness.py`:

```diff
diff --git a/custom_components/irrigation_plus/sensor_liveness.py b/custom_components/irrigation_plus/sensor_liveness.py
index 0c009009..966a8697 100644
--- a/custom_components/irrigation_plus/sensor_liveness.py
+++ b/custom_components/irrigation_plus/sensor_liveness.py
@@ -504,9 +504,11 @@ class SensorLivenessMixin:
         this check's stale copy, and the outages and their events would return.
         """
         now = now if now is not None else local_naive_now()
+        cut_changed = False
         for mapping in await self.store.async_get_mappings():
             try:
-                await self._async_check_mapping_liveness(mapping, now)
+                if await self._async_check_mapping_liveness(mapping, now):
+                    cut_changed = True
             except Exception:
                 # A periodic check: one broken group must not stop the others,
                 # every five minutes, for good.
@@ -514,8 +516,27 @@ class SensorLivenessMixin:
                     "Sensor liveness check failed for sensor group %s",
                     mapping.get(const.MAPPING_ID),
                 )
+        if cut_changed:
+            await self._refresh_estimates_after_outage_change()
 
-    async def _async_check_mapping_liveness(self, mapping: dict, now: datetime) -> None:
+    async def _refresh_estimates_after_outage_change(self) -> None:
+        """Recompute the live estimates once a pausing group's cut has moved.
+
+        Nothing else would: a silent station writes no rows, so the ingestion
+        that normally refreshes them stays quiet until the next poll, commit or
+        run. Not the throttled refresh -- a reading in the last minute would
+        swallow it, and this check comes round only every five minutes.
+        """
+        refresh = getattr(self, "async_refresh_zone_estimates", None)
+        if refresh is None:
+            return
+        try:
+            await refresh()
+        except Exception:  # noqa: BLE001 — an estimate must not break the check
+            _LOGGER.debug("Live estimate refresh after an outage failed", exc_info=True)
+
+    async def _async_check_mapping_liveness(self, mapping: dict, now: datetime) -> bool:
+        """Check one sensor group; whether an outage of a pausing one opened or closed."""
         mapping_id = mapping[const.MAPPING_ID]
         name = mapping.get(const.MAPPING_NAME) or str(mapping_id)
         outages = outages_of(mapping)
@@ -579,6 +600,7 @@ class SensorLivenessMixin:
             self._fire_weather_stale(mapping_id, name, outage)
         if opened or closed:
             self._sync_stale_issue(mapping_id, name, kept)
+        return bool(opened or closed) and group_pauses(mapping)
 
     def _sensor_liveness_snapshot(self, entity_id: str):
         """``(own, siblings, device_id)`` for one sensor-mapped entity."""
```

- [x] **Step 4: GREEN**

Run: wie Step 2. Expected: `6 passed`.

- [x] **Step 5: Prüfen**

```bash
uvx black custom_components/irrigation_plus/ && uvx ruff@0.16.10 check custom_components/irrigation_plus/
../task_compare.sh t9 $(ls tests/test_live_estimate*.py tests/test_silent_sensor*.py tests/test_sensor_liveness*.py tests/test_next_irrigation*.py)
```

- [x] **Step 6: Commit**

```bash
git add custom_components/irrigation_plus/sensor_liveness.py tests/test_sensor_liveness_coordinator.py
git commit -F - <<'EOF'
feat(liveness): an outage of a pausing group refreshes the live estimate

A silent station writes no rows, so the ingestion that normally
refreshes the estimates stays quiet until the next poll, commit or run,
and the panel kept showing ET for a sensor that is no longer counted.
The check refreshes them once when an outage of a pausing group opens or
closes -- unthrottled, since a reading in the last minute would
otherwise swallow it. A failing refresh is logged and leaves the check
intact.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
```



### Task 10: Lint, volle Suite, Mutationen, Review

**Files:** keine Codeänderung (Fix-Runden aus dem Review als eigene Commits mit Test zuerst).

- [x] **Step 1: Lint und Eigenbezüge**

```bash
cd /d/Entwicklung/HASI/issue8-pr3-work/wt
uvx black --check custom_components/irrigation_plus/ && uvx ruff@0.16.10 check custom_components/irrigation_plus/
git diff 6fa424e8..HEAD -- custom_components/ tests/ docs/ | grep "^+" | grep -nE "Eifel-Joe|spec D[0-9]|spec §|Task [0-9]|G[0-9]{1,2}\b|PR [A-T]\b|PR [23]\b"
git log 6fa424e8..HEAD --format='%H%n%B' | grep -nE "Eifel-Joe#|JustChr#"
git grep -n "Eifel-Joe#" HEAD -- custom_components tests
```

Erwartet: Lint sauber; die drei Greps leer.

- [x] **Step 2: Volle Suite mit Namensvergleich**

```bash
cd /d/Entwicklung/HASI/issue8-pr3-work/wt
TZ=UTC /d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests -p _local_socket_unblock -q --no-header -rfE > ../suite-final.txt 2>&1
tr '\r' '\n' < ../suite-final.txt | grep -E "^(FAILED|ERROR) tests" | sed -E 's/ - .*//' | sort > ../names-final.txt
comm -23 ../names-base-wt.txt ../names-final.txt
diff <(grep "^FAILED" ../names-base-wt.txt) <(grep "^FAILED" ../names-final.txt) && echo "FAILED gleich"
comm -13 ../names-base-wt.txt ../names-final.txt | sed -E 's/::.*//' | sort | uniq -c
tail -c 300 ../suite-final.txt
```

Erwartet (Probelauf): `7 failed, 3987 passed, 9 skipped, … 486 errors`; entfallen sind genau die zwei in Task 5
umbenannten Namen; FAILED gleich; neu nur ERROR aus `test_live_estimate_silent_sensor.py` (7),
`test_live_estimate_silent_sensor_daily.py` (5), `test_silent_sensor_commit.py` (2 = die umbenannten) und
`test_silent_sensor_hourly_commit.py` (8) — alle „Lingering timer“. +64 passed = die neuen Fälle (9 + 17 + 9 + 10 + 8 +
5 + 6; die 4 umgedrehten ersetzen alte).

- [x] **Step 3: Mutationen**

```bash
cd /d/Entwicklung/HASI/issue8-pr3-work
MUT_CHECK=1 /d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -I mutate-pr3.py wt mutations-wt.json | grep -vc "anchor count 1 "
MUT_TIMEOUT=400 /d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -I mutate-pr3.py wt mutations-wt.json > mutate-wt.txt 2>&1; tail -4 mutate-wt.txt
```

Erwartet: jede der 37 Anker genau einmal; „37 killed / 37 applied“, jede vom genannten Killer; jede Quelle byte-gleich
zurück. Kein pytest-Lauf daneben (Memory `workflow-agent-hygiene`).

- [x] **Step 4: Abschluss-Review** (`superpowers:requesting-code-review`, Opus): Diff `6fa424e8..HEAD`, Spec PR 3 und dieser
  Plan. Rückmeldungen über `superpowers:receiving-code-review` prüfen; Entscheidungen, die die Spec berühren, dem User
  vorlegen.

- [x] **Step 5: P1** — Plan-Häkchen und Bauprotokoll (`issue8-pr3-work\task-*.txt`, `suite-final.txt`, `mutate-wt.txt`,
  Review-Bericht) nach `archive/design-history`, `docs/superpowers/probes/2026-10-14-dead-weather-sensor-pr3-build/`;
  Push nur nach Freigabe.

### Task 11: Pre-Release und Live-Test auf HA-Test

**Files:** keine Codeänderung im Branch.

- [x] **Step 1: production-Pre-Release** nach Memory `hasi-production-on-upstream` (Rezept von v2026.10.13b1): frisch von
  `upstream/master`, Branding, offene Eigenentwicklungen (PR 2 vollständig inkl. `fa701bcd`/`6fa424e8`, dieser Branch),
  Build, Versionen synchron, `en.json` 0 URLs, Suite mit Namensvergleich, ZIP aus dem SHA. Release-Text deutsch zur
  Freigabe, dann englisch; Push und Release nur nach Freigabe.
- [x] **Step 2: HA-Test aktualisieren** (HACS `update_information`, dann `download` mit `version`; Neustart ankündigen,
  Memory `ha-no-auto-restart`), geladen und Version prüfen. Stand von `hourlycalculation` und `live_estimate_enabled`
  notieren.
- [x] **Step 3: Aufbau nach Spec PR 3, *Ende-zu-Ende-Kriterium*:** YAML-MQTT-Geräte unter eigenem Topic-Präfix, ohne
  Discovery (der Broker hängt an HA-Prod), mit Temperatur, Feuchte, Wind und Sonne (`force_update: true`, ein Gerät);
  pausierende Sensorgruppe; PyETO mit gemessener Sonne, `forecast_days = 0`; Stundenrechnung und Live-Schätzung an. Werkzeuge
  wie PR 2: `issue8-pr2-work\livetest\` (Memory `hasi-livetest-capability-boundary`). **Tagsüber** 3,5 h schweigen
  lassen, dann wieder senden und die Zone berechnen.
  *Erledigt 2026-10-15:* eigenes PyETO-Modul (Modul 0 schätzte die Sonne), Gruppen *pausieren* + *behalten*, T0 09:30:11;
  **Abweichung:** 5,5 h Stille statt 3,5 h (Timer-Meldung ausgeblieben, User „jetzt zurück“), Rückkehr 14:58:15.
- [x] **Step 4: Soll prüfen** (vorab gerechnet und notiert): (1) Hinweis-Variante „pausiert“ trotz Stundenrechnung;
  (2) Live-ET seit dem Anker wächst ab Beginn + 3 h nicht mehr, Methode `hourly_sensor`; (3) Erklärung nennt Beginn + 3 h bis
  Ende, den vorab gerechneten Prozentwert und den Satz „Number of steps“; (4) Live-Eimer direkt nach dem Commit = gebuchter
  Eimer; (5) dieselbe Lage auf *behalten*: kein Satz, Hinweis im PR-1-Text. Protokoll `issue8-pr3-work\livetest\L-pr3.md`.
  *Erledigt 2026-10-15:* 1–5 ✅ (3: ein Satz, 56 % = vorab; 4: Live vor dem Commit = gebucht, 8,6·10⁻⁵ mm). Nebenbefund B1
  (Live-Übertrag gegen Klarheitsquote) vorbestehend upstream, nicht PR 3. Protokoll im Archiv
  `probes/2026-10-14-dead-weather-sensor-pr3-build/livetest/`.
- [x] **Step 5: Aufräumen auf HA-Test:** Geräte und Gruppe entfernen, Stundenrechnung und Live-Schätzung auf den
  notierten Stand; 60-min-Intervall und Pirate-Schlüssel unberührt; Zonen 0/1 nie auf `service`.
  *Erledigt 2026-10-15 15:05–15:07*, Kontrolle ohne Reste, Konfiguration wie vorher.

### Task 12: Nach dem Merge von upstream PR 197 — umsetzen, PR, Nachlauf

- [ ] **Step 1:** Upstream-Runde; `git fetch upstream`; den Merge-Commit von PR 197 finden.
- [ ] **Step 2:** Nur die Commits dieses Branches auf den gemergten Stand setzen:
  `git rebase --onto upstream/master 6fa424e8 feat/pause-silent-sensor-hourly-live`. Der Branch wird **vor diesem
  Schritt nicht gepusht** (globale Regel: kein Rebase auf gepushten Branches); production bekommt seine Commits in Task 11
  per Cherry-Pick. Konflikte entstehen nur, wo JustChr PR 2 geändert hat; je Konflikt Test zuerst.
- [ ] **Step 3:** Neu belegen: Baseline auf `upstream/master`, volle Suite mit Namensvergleich, Mutationen, Lint, Greps
  aus Task 10 Step 1, `dist` neu bauen.
- [ ] **Step 4:** PR-Text mit zwei Abschnitten (Commit, Live), deutsch zur Freigabe, dann englisch; Push und
  `gh pr create --repo JustChr/HAsmartirrigation --base master --head Eifel-Joe:feat/pause-silent-sensor-hourly-live` nur
  nach Freigabe (Skill `pr-workflow`, Memory `hasi-pr-build-recipe`).
- [ ] **Step 5:** P2: Kommentar auf Eifel-Joe#8, `#42` Punkt 9, Label; Archiv nach P1.

---

## Wortlaute (zur Freigabe)

**Doku `docs/configuration-sensor-groups.md`** — erst deutsch, nach Freigabe englisch (die englische Fassung steht in den
Blöcken von Task 5 und Task 7 und wird nach der Freigabe angeglichen).

Zeile 59 (Aufzählungspunkt *Pausieren*), neuer zweiter Satz:

> Wo die Verdunstungsrechnung ohne einen davon nicht auskommt, wird für diese Zeit keine Verdunstung gebucht: bei der
> täglichen Form von PyETO sind das Temperatur, Taupunkt, Windgeschwindigkeit und Luftdruck, bei seiner stündlichen Form
> (**Stündliche Verdunstung**, unter **Einrichtung → Experimentell**) Temperatur, Luftfeuchte, Windgeschwindigkeit und
> Sonneneinstrahlung, beim Passthrough-Modul sein Verdunstungssensor.

Absatz Zeile 62 (ersetzt den heutigen):

> Die Live-Schätzung lässt dieselbe Zeit aus wie die Berechnung; ein Lauf während eines Ausfalls wird also nicht nach mehr
> Verdunstung bemessen, als danach gebucht wird. Die stündliche Form rechnet Stunde für Stunde: Eine Stunde zählt nur mit
> der Zeit, in der jeder Wert gemessen wurde, den sie braucht. Die tägliche Form mittelt einen pausierenden Sensor über die
> Stunden, in denen er gemeldet hat; welcher Teil des Tages fehlte, kann das Ergebnis deshalb verschieben. Der in der
> Erklärung genannte Anteil zählt Zeit: Eine nachts stumme Sonneneinstrahlung senkt ihn, kostet aber kaum Verdunstung.

**Panel-Hilfe:** nur Streichung des letzten Satzes, kein neuer Text.

**Commit-Messages:** stehen je Task; englisch, ohne eigene Bezüge.

## Selbstprüfung gegen die Spec PR 3

| Spec PR 3 | Task |
|---|---|
| §1 Rahmen: *behalten* byte-identisch, Regenzähler nie, keine Store-Felder | 1 (`zone_blocked_spans`), 2–3 (`==`-Tests ohne/mit leeren/fremden Sperren), 6 (Gruppe auf *behalten*) |
| §1 Einheit Gate/Anteil/Texte | Reihenfolge 4 → 5 (Rahmen) |
| §1 Rückbau | keine Store-Änderung; kein Task nötig |
| §2.1 Sperren ohne Gate, freie Funktion, Hülle bleibt | 1, 5 |
| §2.2 Helfer „gültige Proben je Feld“ | 2 (`_masked_hold_table`, `_masked_mean`) |
| §2.3 Stundenzeilen: Mittel über eigene gültige Zeit, Gewicht = gemeinsame Zeit, leere Zeile ohne ET, nie `None` | 2 |
| §2.3 G4 Pflichtfeld wegen Sperre ganz ohne Probe | 2 (`booked = []`, Tests „every reading inside a span“, „never read still falls back“) |
| §2.3 G5 Klarheitsquote | 2 (`solar_samples` ohne Sperre, `_books_nothing` in `_ratio_hold_solar`) |
| §2.3 Druck | 2 (Test `TestPressureIsNotRequired`) |
| §2.4 Pflichtmenge je Form, Anteil nach der Formwahl, kein zweites Skalieren, Satz 2 | 4 |
| §2.5 G6 Lage der ET, G7 Regenzuwächse | 3 (Teilschritte), 2 (`_precip_increments` mit Sperren) |
| §2.6 Tagesform unter Stundenschalter, Aufzeichnungen | 4 (`TestTheDailyFormUnderTheHourlySwitch`), 5 (umgedrehter PR-2-Test) |
| §3.1 Sperren einmal je Neuberechnung, alle Leser, Live-`now` für den Niederschlag | 6 |
| §3.2 G9 Quellenkette, Spiegel × Anteil, 0 statt `None` | 7 |
| §3.3 G10 Hochrechnung; `_latest_temperature` | 8; 6 |
| §3.4 G11 Übertrags-Schlüssel; Neuberechnung nach Öffnen/Schließen | 6; 9 (ungedrosselt, siehe Abweichung unten) |
| §3.5 Gleichlauf Live = Commit | 6 (`hourly_sensor`), 7 (`daily_mirror`) |
| §4 Hinweis/Log/Re-Sync/Panel-Hilfe/Doku/Kommentare | 5, 7 (Live-Satz der Doku), 6 (Live-Kommentare) |
| *Tests* (Byte-Identität, Teil A, Teil B, Mutationen, volle Suite) | 1–9, 10 |
| *Ende-zu-Ende-Kriterium* | 11 |
| *Lieferung* (Stapeln, Pre-Release, Merge, PR, P1) | 0, 10–12 |

**Abweichungen von der Spec, im Probelauf entschieden (zur Kenntnis mit der Plan-Freigabe):**
- §3.4 nennt `async_refresh_zone_estimates_throttled`. Genommen ist die **ungedrosselte**
  `async_refresh_zone_estimates`: Die gedrosselte verwirft jeden Aufruf innerhalb von 60 s nach der letzten Neuberechnung
  (`live_estimate.py:1772-1786`). Eine Pufferzeile kurz vor dem Öffnen hätte den Anstoß geschluckt, und bei einer stummen
  Station kommt danach keine mehr. Die Prüfung läuft nur alle 5 min und frischt höchstens einmal je Lauf auf, nur bei
  pausierenden Gruppen.
- §2.3 ließ offen, wie Zeilen mit Gewicht 0 ihre Messfelder darstellen: **leer** (nur `time`, `hour_start`, `hour`,
  `doy`, `coverage_h`, ggf. `tz_offset_h` und `precipitation`). Die zwei Leser der Messfelder überspringen sie
  (`eto_hourly_series`, `_ratio_hold_solar`).
- Präzisierung zu G7: Ein Regenraten-Zuwachs wird an den Sperrgrenzen geteilt und landet am Ende **seines gemessenen
  Teils**. Sonst landete Regen kurz vor einer Sperre erst bei der nächsten behaltenen Probe (Befund im Probelauf). Die
  Summe gleicht dem Aggregat (Abgleich-Toleranz 1e-6 relativ).
- `zone_blocked_spans` prüft nur `None` für Anfang und Ende; ein leeres oder verkehrtes Fenster ergibt über
  `blocked_spans` ohnehin keine Sperre (`None`). Der zusätzliche Vergleich war gleichwertig (Mutation überlebte).
