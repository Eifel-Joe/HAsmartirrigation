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
- **Volle Suite:** @@SUITE@@
- **Mutationen:** @@MUTATIONS@@
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

- [ ] **Step 1: Upstream-Runde und Basis prüfen**

```bash
cd /d/Entwicklung/HASI/HAsmartirrigation
git fetch upstream && git fetch origin
git rev-parse --short=8 origin/feat/pause-silent-weather-sensor
gh pr view 197 --repo JustChr/HAsmartirrigation --json state,mergedAt,commits --jq '{state, mergedAt, n: (.commits|length)}'
```

Erwartet: `6fa424e8`, PR offen, 18 Commits. Hat das Review von PR 197 Commits hinzugefügt: Basis = neuer Kopf, jede
Anker-Stelle dieses Plans per `grep -n` neu suchen und die Baseline dort messen. Ist PR 197 schon gemergt: Basis =
`upstream/master` (dann enthält er PR 2 gesquasht); Anker ebenso neu suchen.

- [ ] **Step 2: Worktree von `6fa424e8` anlegen**

```bash
cd /d/Entwicklung/HASI/HAsmartirrigation
git worktree add --no-track -b feat/pause-silent-sensor-hourly-live /d/Entwicklung/HASI/issue8-pr3-work/wt 6fa424e8
cp _local_socket_unblock.py /d/Entwicklung/HASI/issue8-pr3-work/wt/
cd /d/Entwicklung/HASI/issue8-pr3-work/wt && git log --oneline -1
```

- [ ] **Step 3: Baseline der vollen Suite** (Memory `rebaseline-when-the-base-moves`)

```bash
cd /d/Entwicklung/HASI/issue8-pr3-work/wt
TZ=UTC /d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests -p _local_socket_unblock -q --no-header -rfE > ../suite-base-wt.txt 2>&1
tr '\r' '\n' < ../suite-base-wt.txt | grep -E "^(FAILED|ERROR) tests" | sed -E 's/ - .*//' | sort > ../names-base-wt.txt
tail -c 300 ../suite-base-wt.txt
```

Erwartet (gemessen auf `6fa424e8` am 2026-10-13): `7 failed, 3925 passed, 9 skipped, … 466 errors`. Die Datei erst nach
Laufende lesen.

- [ ] **Step 4: Vergleichsskript für die Task-Prüfungen anlegen**

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

@@TASKS@@

### Task 10: Lint, volle Suite, Mutationen, Review

**Files:** keine Codeänderung (Fix-Runden aus dem Review als eigene Commits mit Test zuerst).

- [ ] **Step 1: Lint und Eigenbezüge**

```bash
cd /d/Entwicklung/HASI/issue8-pr3-work/wt
uvx black --check custom_components/irrigation_plus/ && uvx ruff@0.16.10 check custom_components/irrigation_plus/
git diff 6fa424e8..HEAD -- custom_components/ tests/ docs/ | grep "^+" | grep -nE "Eifel-Joe|spec D[0-9]|spec §|Task [0-9]|G[0-9]{1,2}\b|PR [A-T]\b|PR [23]\b"
git log 6fa424e8..HEAD --format='%H%n%B' | grep -nE "Eifel-Joe#|JustChr#"
git grep -n "Eifel-Joe#" HEAD -- custom_components tests
```

Erwartet: Lint sauber; die drei Greps leer.

- [ ] **Step 2: Volle Suite mit Namensvergleich**

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

- [ ] **Step 3: Mutationen**

```bash
cd /d/Entwicklung/HASI/issue8-pr3-work
MUT_CHECK=1 /d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -I mutate-pr3.py wt mutations-wt.json | grep -vc "anchor count 1 "
MUT_TIMEOUT=400 /d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -I mutate-pr3.py wt mutations-wt.json > mutate-wt.txt 2>&1; tail -4 mutate-wt.txt
```

Erwartet: jede der 37 Anker genau einmal; „37 killed / 37 applied“, jede vom genannten Killer; jede Quelle byte-gleich
zurück. Kein pytest-Lauf daneben (Memory `workflow-agent-hygiene`).

- [ ] **Step 4: Abschluss-Review** (`superpowers:requesting-code-review`, Opus): Diff `6fa424e8..HEAD`, Spec PR 3 und dieser
  Plan. Rückmeldungen über `superpowers:receiving-code-review` prüfen; Entscheidungen, die die Spec berühren, dem User
  vorlegen.

- [ ] **Step 5: P1** — Plan-Häkchen und Bauprotokoll (`issue8-pr3-work\task-*.txt`, `suite-final.txt`, `mutate-wt.txt`,
  Review-Bericht) nach `archive/design-history`, `docs/superpowers/probes/2026-10-14-dead-weather-sensor-pr3-build/`;
  Push nur nach Freigabe.

### Task 11: Pre-Release und Live-Test auf HA-Test

**Files:** keine Codeänderung im Branch.

- [ ] **Step 1: production-Pre-Release** nach Memory `hasi-production-on-upstream` (Rezept von v2026.10.13b1): frisch von
  `upstream/master`, Branding, offene Eigenentwicklungen (PR 2 vollständig inkl. `fa701bcd`/`6fa424e8`, dieser Branch),
  Build, Versionen synchron, `en.json` 0 URLs, Suite mit Namensvergleich, ZIP aus dem SHA. Release-Text deutsch zur
  Freigabe, dann englisch; Push und Release nur nach Freigabe.
- [ ] **Step 2: HA-Test aktualisieren** (HACS `update_information`, dann `download` mit `version`; Neustart ankündigen,
  Memory `ha-no-auto-restart`), geladen und Version prüfen. Stand von `hourlycalculation` und `live_estimate_enabled`
  notieren.
- [ ] **Step 3: Aufbau nach Spec PR 3, *Ende-zu-Ende-Kriterium*:** YAML-MQTT-Geräte unter eigenem Topic-Präfix, ohne
  Discovery (der Broker hängt an HA-Prod), mit Temperatur, Feuchte, Wind und Sonne (`force_update: true`, ein Gerät);
  pausierende Sensorgruppe; PyETO mit gemessener Sonne, `forecast_days = 0`; Stundenrechnung und Live-Schätzung an. Werkzeuge
  wie PR 2: `issue8-pr2-work\livetest\` (Memory `hasi-livetest-capability-boundary`). **Tagsüber** 3,5 h schweigen
  lassen, dann wieder senden und die Zone berechnen.
- [ ] **Step 4: Soll prüfen** (vorab gerechnet und notiert): (1) Hinweis-Variante „pausiert“ trotz Stundenrechnung;
  (2) Live-ET seit dem Anker wächst ab Beginn + 3 h nicht mehr, Methode `hourly_sensor`; (3) Erklärung nennt Beginn + 3 h bis
  Ende, den vorab gerechneten Prozentwert und den Satz „Number of steps“; (4) Live-Eimer direkt nach dem Commit = gebuchter
  Eimer; (5) dieselbe Lage auf *behalten*: kein Satz, Hinweis im PR-1-Text. Protokoll `issue8-pr3-work\livetest\L-pr3.md`.
- [ ] **Step 5: Aufräumen auf HA-Test:** Geräte und Gruppe entfernen, Stundenrechnung und Live-Schätzung auf den
  notierten Stand; 60-min-Intervall und Pirate-Schlüssel unberührt; Zonen 0/1 nie auf `service`.

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

@@SELFCHECK@@
