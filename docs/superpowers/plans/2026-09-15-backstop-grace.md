# #139 Finish-Backstop mit Wartezeit — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ein bestätigter Service-Lauf (Zone mit `confirm_entity`) wartet nach seinem geplanten Fenster die
5-s-Entprellung plus eine Latenz-Marge je Zone ab. So rechnet der Watcher ein normales Laufende auf der
eigenen Aus-Meldung des Ventils ab (`actual_s` = Fenster von Ein- bis Aus-Meldung), statt dass der Backstop
ihm zuvorkommt (JustChr/HAsmartirrigation#139).

**Architecture:** Beim Dispatch friert ein bestätigter Service-Lauf die Marge der Zone
(`RUN_LATENCY_MARGIN`) und die Ein-Meldung des Ventils (`RUN_VALVE_ON`) in seinen Laufdatensatz ein; der
Watcher zeichnet die erste Aus-Meldung nach „an“ auf (`RUN_VALVE_OFF`). Reine Helfer in `run_watch.py`
beantworten Wartezeit, Toleranz und Ventil-Fenster hinter einem Tor aus Policy-Flag
`settles_on_valve_window` (nur Service), `RUN_WATCH_ENTITY` und eingefrorener Marge. Backstop (Dispatch,
Neustart), Watcher-Abschluss, manueller Stopp, In-flight-Fenster, Zeitfenster-Preis und Observed-Sperre
rufen sie auf; Batch, OpenSprinkler, write-only und Datensätze von vor dem Update bestehen das Tor nie. Das
Zonenfeld `latency_margin` läuft über Store, Websocket, Panel, 8 Sprachen, Doku und dist.

**Tech Stack:** Python 3.12, Home-Assistant-Custom-Integration `custom_components/irrigation_plus`
(attrs, voluptuous), pytest + pytest-homeassistant-custom-component + freezegun (lokal HA 2024.12.5, CI
neuer), black + ruff (CI-Lint); Frontend TypeScript + lit, vitest, eslint/prettier, rollup (Node 24 lokal
= Node-22-CI).

---

## Grundlagen

- **Spec (Quelle der Wahrheit):** `archive/design-history:docs/superpowers/specs/2026-09-15-backstop-grace-design.md`.
- **Basis:** `0b418644` (= `upstream/master`, `build: release v2026.09.16`, mit #144 und #145). Alle
  Zeilenangaben des Plans gelten für diesen Stand. Arbeitsbranch `fix/backstop-grace`.
- **Probeläufe:**
  - Erster Probelauf auf `4e53caf4` (Branches `dry/backstop-grace`, `dry/backstop-grace-frontend`). Er ist
    durch die Revision ersetzt; aus ihm stammen nur noch die Mutationsproben von Task 9, 10 und 12
    (Task 13, Step 7 belegt, warum sie gelten).
  - Revisions-Probelauf auf `0b418644` im Worktree `D:/Entwicklung/HASI/pr139-work/dry2`, Branch
    `dry2/backstop-grace`, einschließlich Feinschliff: 13 Commits (Task 1–12 mit 3b), Endstand `67301a8b`.
  - Endzahlen aus Task 13 (real): `28 files changed, 2958 insertions(+), 813 deletions(-)`; volle Suite
    `2906` → `2993 passed` (`collected` 2922 → 3009, +87 neue Test-Items) bei identischen 7 FAILED und
    320 Errors; vitest `614` → `622` (22 → 23 Dateien); black/ruff `67 files would be left unchanged.` /
    `All checks passed!`; dist aus den Quellen reproduziert; 109 Mutationsproben, 101 gefangen,
    8 äquivalent mit Begründung, 0 überlebende nicht-äquivalente.
- **Umfang:** Task 3b (Observed-Sperre), Task 6 (Backstop mit gespeicherter Aus-Meldung), Task 7 (manueller
  Stopp) und Task 10 (Zeitfenster-Preis) sind je ein eigener Commit und lassen sich einzeln streichen (im
  Probelauf geprüft, Task 13, Step 8). JustChr ist auf #139 gefragt, ob sie in den Fix gehören
  ([issuecomment-5685683675](https://github.com/JustChr/HAsmartirrigation/issues/139#issuecomment-5685683675)).
  Task 14 entscheidet nach seiner Antwort; ohne Antwort geht der PR mit allen vier.

## Entscheidungen (User, 2026-09-15)

Details jeweils in der Spec, Abschnitt „Entscheidungen“ und dem genannten Design-Abschnitt.

- **E1** Anker = eigene Ein-Meldung des Ventils (`RUN_VALVE_ON`), `RUN_STARTED` bleibt; Toleranz
  abgeschlossen/Teil-Lauf = max(1 s, Marge). Spec E1, Design 1 und 3.
- **E2** Default-Marge 4 s, ganze Sekunden, 0–30. Spec E2, Design 6.
- **E3** Die Wartezeit zieht In-flight-Fenster, Zeitfenster-Preis und Observed-Sperre mit. Spec E3, Design 4.
- **E4** Neustart ohne gespeicherte Aus-Meldung: Fenster = min(jetzt − Ventil-Ein, geplant). Spec E4, Design 3 und 5.
- **E5** Abweichungen von der Vorgabe auf #139 werden im PR-Text erklärt. Spec E5, „Befunde gegen die Vorgabe“.
- **E6** `RUN_VALVE_OFF` nur aus einem Ereignis, dessen Vorzustand laufend war (nie aus der ersten Auswertung,
  nie aus `unavailable`/`unknown` → `off`). Spec E6, Design 1 `RUN_VALVE_OFF`.
- **E7** Neutrale Namen in neu hinzugefügten Test-Fixtures; vorhandene upstream-Namen wie „Beet“ bleiben. Spec E7.

## Im Plan festgehaltene Abweichungen vom Planungsgerüst

- **Tor in Task 6:** `_sc_backstop_fired` prüft `run_finish_grace_seconds(run)` statt
  `run_has_finish_grace(run)`. Grund: Abtrennbarkeit. Task 6 importiert nichts und lässt sich allein
  streichen; der Helfer ist seit Task 3 importiert und für jeden Datensatz gleichwertig (Wartezeit ≥ 5 genau
  dann, wenn das Tor gilt, sonst 0). Task 7 importiert `run_has_finish_grace` selbst.
- **Test-Helfer `_advance`** entsteht in Task 5 (dort benutzt von `_run_until_the_valve_closes`), nicht in
  Task 6; Task 6, 7 und 8 benutzen ihn.
- **`_clampLatencyMargin`** ist in Task 11 als eigene Methode neben `_showLatencyMargin` ausgelagert, damit
  vitest auch die Klemme prüft.
- **Task 3b** ist vom Dispatch-Task 3 abgetrennt (Observed-Sperre als eigener Commit).
- **Schlüsselwort `previous_state`** (E6) statt des früheren `observed_transition` in `_watch_evaluate`.
- **Neutrale Fixture-Namen** (E7), z. B. `binary_sensor.valve_flowing` und `T0` = 2026-01-10 10:00:00 UTC in
  `tests/test_finish_grace_helpers.py`.

## Tasks

- **Task 0:** Ausgangslage prüfen und Basis messen (Speicherplatz, Branch, volle Suite, vitest, Mutationsverfahren, Vergleichslauf am Elternstand).
- **Task 1:** Latenz-Marge als Zonenfeld (gespeichert, geladen, per POST setzbar; noch ohne Wirkung).
- **Task 2:** Laufdaten-Schlüssel, Policy-Flag und reine Helfer für die Wartezeit (noch ohne Aufrufer).
- **Task 3:** Dispatch friert Marge und Ventil-Ein ein, der Backstop trägt die Wartezeit.
- **Task 3b:** Die Observed-Sperre trägt die Wartezeit eines bestätigten Laufs (abtrennbar).
- **Task 4:** Der Watcher zeichnet die Aus-Meldung des Ventils auf und löscht sie bei einem Blip.
- **Task 5:** Abschluss nimmt `actual_s` an, der Watcher rechnet nach dem Ventil-Fenster ab.
- **Task 6:** Der Backstop rechnet einen Lauf mit gespeicherter Aus-Meldung nach dem Ventil-Fenster ab (abtrennbar).
- **Task 7:** Der manuelle Stopp misst ab der Ein-Meldung des Ventils (abtrennbar).
- **Task 8:** Ein Neustart übernimmt die Wartezeit.
- **Task 9:** Das In-flight-Fenster trägt die Wartezeit.
- **Task 10:** Der Zeitfenster-Preis trägt die Wartezeit (abtrennbar).
- **Task 11:** Panel-Feld „Latenz-Marge“ + vitest-Sichtbarkeitstor.
- **Task 12:** Übersetzungen „Latenz-Marge“ in 8 Sprachen + Doku + dist.
- **Task 13:** Schlussprüfung (Lint, volle Suite gegen die Basis, vitest, dist, Schwester-Pfade, Text-Hygiene, Mutationsproben, Abtrennbarkeit).
- **Task 14:** PR-Text, Kommentar auf #139, Design-Historie, Befunde — jeder Außenschritt mit eigener Freigabe.
- **Task 15:** Live-Test — zuerst HA-Test mit dem Sonoff-Emulator, dann Nachmessung auf HA-Prod.

## Umgebungswarnungen

- **Speicherplatz auf `C:`:** im Probelauf nur 58 MB frei. Task 0, Step 1 prüft das; unter 5 GB STOPP oder
  Umleitung von `TEMP`/`TMP`/`TMPDIR`/`npm_config_cache` nach `D:/Entwicklung/HASI/pr139-work/`, und zwar
  in jedem Block, der pytest, vitest oder npm startet.
- **CRLF:** der Arbeitsbaum ist CRLF ausgecheckt (`core.autocrlf=true`, `i/lf w/crlf`), nur
  `dist/irrigation-plus.js` ist `eol=lf`. Mutationsproben schreiben LF zurück: immer aus der `.bak`
  wiederherstellen und die SHA-256 prüfen (Task 0, Step 5). Nach `npm run build` zeigen die drei
  Card-Bundles ` M` ohne Inhaltsänderung (Task 12, Step 8; Task 13, Step 4).
- **Lingering timers:** lokal (HA 2024.12.5) enden Tests mit noch scharfem echtem Timer als
  `Failed: Lingering timer …`-Error. Die Basis hat 320 davon; jeder neue Test mit echtem Timer endet
  abgerechnet oder mit abgebrochenen Timern. `IRRIGATION_PLUS_HA_FLOOR=1` nur zum Vergleich, nie um einen
  neuen Timer zu verstecken. Die Vergleichsläufe am Elternstand (Task 0, Step 6) belegen, dass kein Error neu ist.
- **freeze_time:** freezegun friert auch die Loop-Uhr ein. Ein echtes `async_call_later` muss im selben
  `freeze_time(...) as frozen`-Block gestellt werden, in dem die Uhr vorgestellt wird. Vorstellen mit
  `frozen.tick(n)`, `async_fire_time_changed(hass, dt_util.utcnow())` und `await hass.async_block_till_done()`.
  `async_fire_time_changed` feuert bis 0,5 s zu früh (≥ 1 s Abstand zu Fälligkeiten) und bewegt `utcnow`
  nicht, das tut nur `tick`.

---

### Task 0: Ausgangslage prüfen und Basis messen

**Files:** keine Änderung im Repo. Messdateien, das Mutationsskript und die Sicherungen liegen außerhalb des
Repos unter `D:\Entwicklung\HASI\pr139-work\`.

- [ ] **Step 1: Speicherplatz prüfen**

```bash
cd /d/Entwicklung/HASI/HAsmartirrigation
df -h /c /d
```

Erwartet: `C:` hat mindestens 5 GB frei. Im Revisions-Probelauf am 2026-09-15 war das NICHT so (real):

```
Filesystem      Size  Used Avail Use% Mounted on
C:              476G  476G   58M 100% /c
D:              1.9T  403G  1.5T  22% /d
```

pytest schreibt in `TEMP`, `npm ci` und vitest schreiben in `TEMP` und in den npm-Cache, und beide liegen
standardmäßig unter `C:\Users\…\AppData\Local`. Deshalb beginnt JEDER Befehlsblock dieses Plans, der pytest,
vitest oder npm startet, direkt nach seinem `cd` mit genau der zweiten Zeile des Blocks unten (Umleitung nach
`D:`); das ist unabhängig vom freien Platz eingetragen und schadet nicht, wenn `C:` genug hat. Jeder Block ist
eine eigene Shell, `export` wirkt nur im selben Block — die Zeile nie weglassen. Unter 5 GB frei auf `C:`:
dem User melden (Windows und HA-Werkzeuge außerhalb der Umleitung können trotzdem scheitern); unter 500 MB:
STOPP, bis Platz geschaffen ist.

```bash
cd /d/Entwicklung/HASI/HAsmartirrigation
mkdir -p D:/Entwicklung/HASI/pr139-work/tmp D:/Entwicklung/HASI/pr139-work/npm-cache && export TEMP=D:/Entwicklung/HASI/pr139-work/tmp TMP=D:/Entwicklung/HASI/pr139-work/tmp TMPDIR=D:/Entwicklung/HASI/pr139-work/tmp npm_config_cache=D:/Entwicklung/HASI/pr139-work/npm-cache
echo "$TEMP $npm_config_cache"
```

Erwartet (real):

```
D:/Entwicklung/HASI/pr139-work/tmp D:/Entwicklung/HASI/pr139-work/npm-cache
```

Der Feinschliff des Revisions-Probelaufs lief mit dieser Umleitung vor jedem Test- und npm-Befehl. Meldet ein
Befehl trotzdem `ENOSPC`, STOPP und dem User berichten.

- [ ] **Step 2: Branch und Arbeitsbaum prüfen**

```bash
cd /d/Entwicklung/HASI/HAsmartirrigation
git fetch upstream
git status --short
git branch --show-current
git log --oneline -1
git rev-list --count HEAD..upstream/master
```

Erwartet: Branch `fix/backstop-grace`, HEAD `0b418644` (`build: release v2026.09.16`, = `upstream/master`
mit #144 und #145), `rev-list` = `0`, `git status --short` leer bis auf `?? docs/SESSION-STAND.md`.
Ist `upstream/master` inzwischen weiter (`rev-list` > 0), STOPP und mit dem User klären, ob der Branch vor
Task 1 neu von `upstream/master` gezogen wird. Die Zeilenangaben des Plans gelten für `0b418644`; der erste
Probelauf auf `4e53caf4` ist durch die Revision ersetzt.

- [ ] **Step 3: Volle Suite als Basis messen (am selben Tag wie die Schlussprüfung)**

```bash
cd /d/Entwicklung/HASI/HAsmartirrigation
mkdir -p D:/Entwicklung/HASI/pr139-work/tmp D:/Entwicklung/HASI/pr139-work/npm-cache && export TEMP=D:/Entwicklung/HASI/pr139-work/tmp TMP=D:/Entwicklung/HASI/pr139-work/tmp TMPDIR=D:/Entwicklung/HASI/pr139-work/tmp npm_config_cache=D:/Entwicklung/HASI/pr139-work/npm-cache
./.venv/Scripts/python.exe -m pytest tests -p _local_socket_unblock -q -rfE -p no:cacheprovider > /d/Entwicklung/HASI/pr139-work/baseline-$(git rev-parse --short HEAD).txt 2>&1
tail -1 /d/Entwicklung/HASI/pr139-work/baseline-$(git rev-parse --short HEAD).txt
grep "^FAILED" /d/Entwicklung/HASI/pr139-work/baseline-$(git rev-parse --short HEAD).txt
```

Erwartet (real gemessen 2026-09-15 auf `0b418644`, Datei `baseline-0b418644.txt`, `collected 2922 items`, ~4 min):
`= 7 failed, 2906 passed, 9 skipped, 10 warnings, 320 errors in 249.45s (0:04:09) =`
mit genau diesen FAILED-Namen (vorbestehend unter Windows/HA 2024.12.5, nicht von diesem Plan):

```
FAILED tests/test_init.py::TestSmartIrrigationIntegration::test_async_setup_entry_success
FAILED tests/test_init.py::TestSmartIrrigationIntegration::test_async_setup_entry_with_weather_service
FAILED tests/test_next_irrigation_sensor.py::TestSetupAnnouncesSchedules::test_setup_entry_announces_after_loading_schedules
FAILED tests/test_opensprinkler_teardown.py::TestShutdown::test_a_real_stop_stops_the_stations
FAILED tests/test_opensprinkler_teardown.py::TestShutdown::test_a_restart_leaves_the_run_to_be_re_adopted
FAILED tests/test_opensprinkler_teardown.py::TestShutdown::test_the_hook_does_not_outlive_its_coordinator
FAILED tests/test_panel.py::TestSmartIrrigationPanel::test_async_register_panel_static_path_config
```

Die Suite enthält datumsabhängige Tests; Basis und Endstand deshalb am selben Tag messen.

- [ ] **Step 4: vitest-Basis messen**

```bash
cd /d/Entwicklung/HASI/HAsmartirrigation/custom_components/irrigation_plus/frontend
mkdir -p D:/Entwicklung/HASI/pr139-work/tmp D:/Entwicklung/HASI/pr139-work/npm-cache && export TEMP=D:/Entwicklung/HASI/pr139-work/tmp TMP=D:/Entwicklung/HASI/pr139-work/tmp TMPDIR=D:/Entwicklung/HASI/pr139-work/tmp npm_config_cache=D:/Entwicklung/HASI/pr139-work/npm-cache
npm ci
npm test 2>&1 | tail -5
```

Erwartet (Revisions-Probelauf auf `0b418644`, Node 24.15.0, siehe Task 11, Step 1): `npm ci` Exit 0, dann

```
 Test Files  22 passed (22)
      Tests  614 passed (614)
```

- [ ] **Step 5: Mutationsverfahren einrichten (gilt für jede Mutationsprobe in Task 1–12)**

Datei `D:/Entwicklung/HASI/pr139-work/mut/mutate.py` anlegen (außerhalb des Repos, wird nie committet):

```python
"""Exact, single-occurrence string replacement for mutation probes."""

import pathlib
import sys

path, old, new = sys.argv[1], sys.argv[2], sys.argv[3]
p = pathlib.Path(path)
text = p.read_text(encoding="utf-8")
count = text.count(old)
if count != 1:
    sys.exit(f"expected exactly one occurrence, found {count}: {old!r}")
p.write_text(text.replace(old, new), encoding="utf-8", newline="\n")
print(f"mutated {path}")
```

Regeln für jede Probe (die Tasks verweisen hierher und nennen je Probe nur Suchtext → Ersatz):

- **Suchtexte benutzen `\n` als Zeilenende, nie `\r\n`.** Die Dateien sind CRLF ausgecheckt
  (`git ls-files --eol`: `i/lf w/crlf`), aber `read_text` liest mit Universal-Newlines, im Speicher steht
  also `\n`. In Bash wird ein mehrzeiliger Suchtext als `$'…\n…'` übergeben. Ein `\n` in einer Tabellenzelle
  der Tasks heißt genau das.
- „Zeile `X` entfernt“ heißt: Suchtext = die ganze Zeile mit ihrer Einrückung und dem abschließenden `\n`,
  Ersatz leer (`''`). „`A` → `B`“ heißt: Suchtext `A`, Ersatz `B`. Findet das Skript den Suchtext nicht
  genau einmal, bricht es mit `expected exactly one occurrence, found N` ab und schreibt nichts. Wo das
  nötig war, nennen die Tasks einen Suchtext mit Nachbarzeilen.
- **Wiederherstellung aus der `.bak` und SHA-256-Prüfung sind Pflicht**, auch nach einer Probe, die nichts
  gefangen hat. Das Skript schreibt die GANZE Datei mit LF zurück. Im Probelauf gemessen (Ersetzung ohne
  Inhaltsänderung): `git status --short` zeigt die Datei als ` M`, `git diff --stat` ist leer und
  `sha256sum -c` meldet `FAILED`. Erst die zurückkopierte Sicherung stellt die CRLF-Bytes wieder her
  (`OK`, Status wie vor der Probe). `git status` allein belegt die Wiederherstellung also nicht.
- Sicherung je Probe unter `D:/Entwicklung/HASI/pr139-work/mut/tNN-<probe>.bak`; pytest unter einer Mutation
  mit `PYTHONDONTWRITEBYTECODE=1` und `-p no:cacheprovider`.

Beispiel: Task 1, Probe `load-line` (die drei Zeilen `latency_margin=zone.get(…)` im Ladeblock von
`store.py` entfernt). Ausführbar erst nach Task 1, Step 5:

```bash
cd /d/Entwicklung/HASI/HAsmartirrigation
mkdir -p D:/Entwicklung/HASI/pr139-work/tmp D:/Entwicklung/HASI/pr139-work/npm-cache && export TEMP=D:/Entwicklung/HASI/pr139-work/tmp TMP=D:/Entwicklung/HASI/pr139-work/tmp TMPDIR=D:/Entwicklung/HASI/pr139-work/tmp npm_config_cache=D:/Entwicklung/HASI/pr139-work/npm-cache
F=custom_components/irrigation_plus/store.py
B=D:/Entwicklung/HASI/pr139-work/mut/t01-load-line.bak
cp "$F" "$B"
S=$(sha256sum "$F" | cut -d' ' -f1)
./.venv/Scripts/python.exe D:/Entwicklung/HASI/pr139-work/mut/mutate.py "$F" $'                        latency_margin=zone.get(\n                            ZONE_LATENCY_MARGIN, DEFAULT_LATENCY_MARGIN_SECONDS\n                        ),\n' ''
PYTHONDONTWRITEBYTECODE=1 ./.venv/Scripts/python.exe -m pytest tests/test_store_self_closing.py tests/test_distributor_integration.py -p _local_socket_unblock -q -p no:cacheprovider -k latency_margin
cp "$B" "$F"
echo "$S  $F" | sha256sum -c -
git diff --stat
```

Erwartet (real beobachtet im Revisions-Probelauf `dry2` am Endstand `67301a8b`, mit der Umleitung aus
Step 1): `mutated custom_components/irrigation_plus/store.py`, dann `E   assert 4 == 7`,
`FAILED tests/test_store_self_closing.py::test_latency_margin_survives_reload` und
`1 failed, 2 passed, 25 deselected in 1.50s`, nach dem Zurückkopieren
`custom_components/irrigation_plus/store.py: OK`. `git diff --stat` ist dieselbe Ausgabe wie vor der Probe:
im Probelauf am Commit leer, im echten Lauf vor dem Commit von Task 1 die Statistik der fünf Dateien dieses
Tasks.

- [ ] **Step 6: Vergleichslauf am Elternstand (gilt für Task 4–10 und Task 13)**

Wenn ein Task sagt „Vergleichslauf am Elternstand“, läuft dieser Block. Er misst dieselben Testdateien einmal
im Arbeitsbaum und einmal in einem temporären, abgekoppelten Worktree am Elternstand. Danach vergleicht er
die sortierten `FAILED`/`ERROR`-Zeilen und entfernt den Worktree wieder. Die zwei Zeilen `P=` und `FILES=`
setzt der aufrufende Task; hier stehen die Werte, mit denen der Block real geprüft wurde.

`P` ist der Elternstand. Nach dem Commit des Tasks ist das `HEAD^` (so steht es im Block). Im Schritt
„Verwandte Suiten“, also VOR dem Commit, liegen die Änderungen des Tasks noch ungestagt im Baum, und der
Elternstand ist `HEAD`: dort `P=$(git rev-parse HEAD)`. Task 13 setzt `P=0b418644`.

```bash
cd /d/Entwicklung/HASI/HAsmartirrigation
mkdir -p D:/Entwicklung/HASI/pr139-work/tmp D:/Entwicklung/HASI/pr139-work/npm-cache && export TEMP=D:/Entwicklung/HASI/pr139-work/tmp TMP=D:/Entwicklung/HASI/pr139-work/tmp TMPDIR=D:/Entwicklung/HASI/pr139-work/tmp npm_config_cache=D:/Entwicklung/HASI/pr139-work/npm-cache
P=$(git rev-parse HEAD^)
FILES="tests/test_service_watch.py tests/test_batch.py"
W=/d/Entwicklung/HASI/pr139-work
git worktree add --detach $W/parent "$P"
cp _local_socket_unblock.py $W/parent/
./.venv/Scripts/python.exe -m pytest $FILES -p _local_socket_unblock -q -rfE -p no:cacheprovider > $W/related-head.txt 2>&1
cd $W/parent && /d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest $FILES -p _local_socket_unblock -q -rfE -p no:cacheprovider > $W/related-parent.txt 2>&1
cd /d/Entwicklung/HASI/HAsmartirrigation
git worktree remove --force $W/parent
tail -1 $W/related-parent.txt; tail -1 $W/related-head.txt
diff <(grep -E "^(FAILED|ERROR)" $W/related-parent.txt | sed 's/ - .*//' | sort -u) <(grep -E "^(FAILED|ERROR)" $W/related-head.txt | sed 's/ - .*//' | sort -u) && echo FAILED-ERROR-same
git worktree list | grep -c pr139-work/parent
```

Erwartet (real beobachtet mit genau diesem Block im Revisions-Probelauf, dort vom Worktree `dry2` aus am
Endstand `67301a8b`, `P` = `7c626143`, mit der Umleitung aus Step 1):

```
Preparing worktree (detached HEAD 7c626143)
HEAD is now at 7c626143 feat(panel): add latency margin field for confirmed service zones
======================= 121 passed, 39 errors in 11.23s =======================
======================= 121 passed, 39 errors in 11.70s =======================
FAILED-ERROR-same
0
```

Die erste Zusammenfassung ist der Elternstand, die zweite der Arbeitsbaum; die Zahlen des jeweiligen Tasks
nennt dessen Schritt „Verwandte Suiten“. Druckt `diff` eine Zeile statt `FAILED-ERROR-same`, ist ein FAILED
oder ERROR neu: nicht weiter, er gilt als Defekt dieses Plans. Die letzte Zeile `0` belegt, dass der
temporäre Worktree entfernt ist.

Kein Commit.

---

### Task 1: Latenz-Marge als Zonenfeld (gespeichert, geladen, per POST setzbar; noch ohne Wirkung)

**Files** (Zeilen auf `0b418644`):
- Modify: `custom_components/irrigation_plus/const.py:856-857` (Service-Block, direkt nach `ZONE_CONFIRM_ENTITY`)
- Modify: `custom_components/irrigation_plus/store.py:110-111, 165-166, 293-294, 1193-1194` (Import-Block, `ZoneEntry`, Zonen-Ladeblock in `async_load`)
- Modify: `custom_components/irrigation_plus/websockets.py:303-304` (Schema von `SmartIrrigationZoneView`)
- Test: `tests/test_store_self_closing.py`
- Test: `tests/test_distributor_integration.py`

Ziel: Die Zone bekommt `latency_margin` (ganze Sekunden, Default 4, Obergrenze 30 als benannte
Konstante). Das Feld übersteht einen Neuladevorgang, eine vor #139 gespeicherte Zone ohne den
Schlüssel lädt mit 4, und die Zonen-View reicht einen gePOSTeten String `"6"` als `int` 6 weiter.
Kein `STORAGE_VERSION`-Sprung (`test_storage_version_is_14` bleibt grün), kein Eintrag in der
Liste der servereigenen Felder. Laufverhalten ändert sich in diesem Task nicht.

Fixture-Namen (Nutzerentscheidung E7): Der Test zum gespeicherten Wert nutzt `Beet` /
`script.irrigation_beet` / `valve.beet`, weil genau diese Namen auf `0b418644` schon in derselben
Datei stehen (`tests/test_store_self_closing.py:59-66`). Der zweite, neue Fixture-Satz ist neutral:
`Front` / `script.irrigation_front` / `valve.front`. Keine Namen der realen Installation.

- [ ] **Step 1: Fehlschlagende Tests schreiben**

In `tests/test_store_self_closing.py` direkt nach `test_self_closing_fields_survive_reload`
(vor `test_active_valve_runs_survive_reload`) einfügen:

```python
def _reload_payload(reg):
    """The store's own persisted format, as async_load reads it back."""
    return {
        "config": attr.asdict(reg.config),
        "zones": [attr.asdict(z) for z in reg.zones.values()],
        "modules": [],
        "mappings": [],
    }


async def _reloaded(hass, data):
    fresh = SmartIrrigationStorage(hass)
    fresh._store.async_load = AsyncMock(return_value=data)
    await fresh.async_load()
    return fresh


async def test_latency_margin_survives_reload(hass):
    """Regression guard: the margin must be hydrated on load (#139).

    Without the zone.get(...) line in the load block the attr default wins and a
    margin the user set silently reverts to 4 s on every restart.
    """
    reg = await async_get_registry(hass)
    created = await reg.async_create_zone(
        {
            "name": "Beet",
            "size": 10.0,
            "throughput": 5.0,
            "watering_mode": const.WATERING_MODE_SERVICE,
            "run_service": "script.irrigation_beet",
            "confirm_entity": "valve.beet",
            const.ZONE_LATENCY_MARGIN: 7,
        }
    )
    zone_id = created["id"]
    assert created[const.ZONE_LATENCY_MARGIN] == 7

    fresh = await _reloaded(hass, _reload_payload(reg))

    assert fresh.get_zone(zone_id)[const.ZONE_LATENCY_MARGIN] == 7


async def test_zone_stored_without_latency_margin_loads_the_default(hass):
    """A zone persisted before #139 has no key and loads with 4 s, no migration."""
    reg = await async_get_registry(hass)
    created = await reg.async_create_zone(
        {
            "name": "Front",
            "size": 10.0,
            "throughput": 5.0,
            "watering_mode": const.WATERING_MODE_SERVICE,
            "run_service": "script.irrigation_front",
            "confirm_entity": "valve.front",
        }
    )
    zone_id = created["id"]
    data = _reload_payload(reg)
    for stored in data["zones"]:
        stored.pop(const.ZONE_LATENCY_MARGIN, None)
    assert all(const.ZONE_LATENCY_MARGIN not in z for z in data["zones"])

    fresh = await _reloaded(hass, data)

    assert const.DEFAULT_LATENCY_MARGIN_SECONDS == 4
    assert fresh.get_zone(zone_id)[const.ZONE_LATENCY_MARGIN] == 4
```

In `tests/test_distributor_integration.py` direkt nach `test_zone_view_accepts_membership_fields`
(vor `test_zone_view_ignores_server_owned_fields`) einfügen; die Datei importiert bereits
`SimpleNamespace`, `AsyncMock`, `MagicMock` und `const`:

```python
async def test_zone_view_coerces_latency_margin_to_int():
    """The panel posts the margin from a number input; the view hands on an int.

    The schema allows extra keys, so without an explicit Coerce(int) a posted
    "6" would reach the store as the string "6" (#139).
    """
    from unittest.mock import patch

    from custom_components.irrigation_plus.websockets import SmartIrrigationZoneView

    coordinator = AsyncMock()
    hass = SimpleNamespace(data={const.DOMAIN: {"coordinator": coordinator}})
    request = MagicMock()
    request.app = {"hass": hass}
    data = {const.ZONE_ID: 2, const.ZONE_LATENCY_MARGIN: "6"}
    request.json = AsyncMock(return_value=data)

    view = SmartIrrigationZoneView()
    view.json = MagicMock(return_value="OK")

    with patch("custom_components.irrigation_plus.websockets.async_dispatcher_send"):
        await view.post(request)

    coordinator.async_update_zone_config.assert_awaited_once()
    called = coordinator.async_update_zone_config.await_args
    forwarded = called.args[1] if len(called.args) > 1 else called.kwargs.get("data")
    assert forwarded[const.ZONE_LATENCY_MARGIN] == 6
    assert isinstance(forwarded[const.ZONE_LATENCY_MARGIN], int)
```

- [ ] **Step 2: Tests laufen lassen, Fehlschlag bestätigen (Konstante fehlt)**

```bash
cd /d/Entwicklung/HASI/HAsmartirrigation
mkdir -p D:/Entwicklung/HASI/pr139-work/tmp D:/Entwicklung/HASI/pr139-work/npm-cache && export TEMP=D:/Entwicklung/HASI/pr139-work/tmp TMP=D:/Entwicklung/HASI/pr139-work/tmp TMPDIR=D:/Entwicklung/HASI/pr139-work/tmp npm_config_cache=D:/Entwicklung/HASI/pr139-work/npm-cache
./.venv/Scripts/python.exe -m pytest tests/test_store_self_closing.py tests/test_distributor_integration.py -p _local_socket_unblock -q -k "latency_margin"
```

Erwartet (real beobachtet, Basis `0b418644` plus die Tests aus Step 1):

```
E   AttributeError: module 'custom_components.irrigation_plus.const' has no attribute 'ZONE_LATENCY_MARGIN'
FAILED tests/test_store_self_closing.py::test_latency_margin_survives_reload
FAILED tests/test_store_self_closing.py::test_zone_stored_without_latency_margin_loads_the_default
FAILED tests/test_distributor_integration.py::test_zone_view_coerces_latency_margin_to_int
====================== 3 failed, 25 deselected in 1.82s =======================
```

- [ ] **Step 3: Konstanten in `const.py` anlegen**

Im Service-Block, direkt nach `ZONE_CONFIRM_ENTITY = "confirm_entity"` und vor dem Kommentar
`# Observed-watering (opt-in): ...`:

Vorher:

```python
ZONE_CONFIRM_ENTITY = "confirm_entity"
# Observed-watering (opt-in): the physical valve/switch to watch for EXTERNAL
```

Nachher:

```python
ZONE_CONFIRM_ENTITY = "confirm_entity"
# How late a confirmed service valve may report its own close, in whole seconds.
# A run with a confirm_entity is finished by the watcher on the valve's off report
# plus SERVICE_WATCH_SETTLE_SECONDS of debounce; a backstop armed at exactly the
# planned window beat that report on every normal run (#139): measured Tuya valves
# report their close 2-3 s after their window, so the watcher never got to decide
# and actual_s was never the observed window. The margin is added to the backstop
# of confirmed service runs only (batch and OpenSprinkler keep their own timing)
# and is the tolerance between a completed and a partial run. Default 4 covers the
# measured need with ~2 s to spare; capped so a typo cannot hold a chain for minutes.
ZONE_LATENCY_MARGIN = "latency_margin"
DEFAULT_LATENCY_MARGIN_SECONDS = 4
MAX_LATENCY_MARGIN_SECONDS = 30
# Observed-watering (opt-in): the physical valve/switch to watch for EXTERNAL
```

(„Tuya“ ist eine Gerätemarke, kein Name der Installation, und steht upstream schon in
Produktionskommentaren: `const.py:543` und `:555`, `irrigation.py:733`, `duration_math.py:168` auf
`0b418644`. Belassen.)

- [ ] **Step 4: Tests erneut laufen lassen, jetzt am echten Verhalten rot**

```bash
cd /d/Entwicklung/HASI/HAsmartirrigation
mkdir -p D:/Entwicklung/HASI/pr139-work/tmp D:/Entwicklung/HASI/pr139-work/npm-cache && export TEMP=D:/Entwicklung/HASI/pr139-work/tmp TMP=D:/Entwicklung/HASI/pr139-work/tmp TMPDIR=D:/Entwicklung/HASI/pr139-work/tmp npm_config_cache=D:/Entwicklung/HASI/pr139-work/npm-cache
./.venv/Scripts/python.exe -m pytest tests/test_store_self_closing.py tests/test_distributor_integration.py -p _local_socket_unblock -q -k "latency_margin"
```

Erwartet (real beobachtet; `KeyError` = `ZoneEntry` kennt das Feld nicht, in beiden Store-Tests;
`'6' == 6` = die View reicht den String über `ALLOW_EXTRA` unverändert weiter):

```
E   KeyError: 'latency_margin'
E   AssertionError: assert '6' == 6
FAILED tests/test_store_self_closing.py::test_latency_margin_survives_reload
FAILED tests/test_store_self_closing.py::test_zone_stored_without_latency_margin_loads_the_default
FAILED tests/test_distributor_integration.py::test_zone_view_coerces_latency_margin_to_int
====================== 3 failed, 25 deselected in 1.64s =======================
```

- [ ] **Step 5: `store.py` — Importe, `ZoneEntry`-Feld, Ladezeile**

Import-Block `from .const import (` — zwei Namen alphabetisch einsortieren:

Vorher:

```python
    CONF_ZONE_SEQUENCING_MIN_ABSORPTION_TIME,
    DOMAIN,
```

Nachher:

```python
    CONF_ZONE_SEQUENCING_MIN_ABSORPTION_TIME,
    DEFAULT_LATENCY_MARGIN_SECONDS,
    DOMAIN,
```

Vorher:

```python
    ZONE_LAST_UPDATED,
    ZONE_LEAD_TIME,
```

Nachher:

```python
    ZONE_LAST_UPDATED,
    ZONE_LATENCY_MARGIN,
    ZONE_LEAD_TIME,
```

`ZoneEntry`, zwischen `confirm_entity` und `observed_entity`:

Vorher:

```python
    confirm_entity = attr.ib(type=str, default=None)
    # Observed-watering (opt-in): physical valve/switch watched for EXTERNAL runs
    # of a service/self-closing zone (no linked_entity). See ZONE_OBSERVED_ENTITY.
    observed_entity = attr.ib(type=str, default=None)
```

Nachher:

```python
    confirm_entity = attr.ib(type=str, default=None)
    # Seconds a confirmed service valve may report its close after its window
    # (#139). Additive: a zone stored without it loads with the default, no
    # schema bump. See ZONE_LATENCY_MARGIN.
    latency_margin = attr.ib(type=int, default=DEFAULT_LATENCY_MARGIN_SECONDS)
    # Observed-watering (opt-in): physical valve/switch watched for EXTERNAL runs
    # of a service/self-closing zone (no linked_entity). See ZONE_OBSERVED_ENTITY.
    observed_entity = attr.ib(type=str, default=None)
```

Zonen-Ladeblock in `SmartIrrigationStorage.async_load` (der `ZoneEntry(...)`-Aufruf mit dem
Kommentar „Self-closing valve mode config — must be hydrated here"):

Vorher:

```python
                        confirm_entity=zone.get("confirm_entity", None),
                        observed_entity=zone.get(ZONE_OBSERVED_ENTITY, None),
```

Nachher:

```python
                        confirm_entity=zone.get("confirm_entity", None),
                        # Migration: a zone stored before #139 has no margin and
                        # gets the default (additive, no STORAGE_VERSION bump).
                        latency_margin=zone.get(
                            ZONE_LATENCY_MARGIN, DEFAULT_LATENCY_MARGIN_SECONDS
                        ),
                        observed_entity=zone.get(ZONE_OBSERVED_ENTITY, None),
```

- [ ] **Step 6: `websockets.py` — Zonen-Schema zwingt `int`**

Im Schema von `SmartIrrigationZoneView` (die Liste mit `ZONE_MAXIMUM_DURATION`); die Liste der
servereigenen Felder in `post` bleibt unverändert:

Vorher:

```python
                vol.Optional(const.ZONE_MAXIMUM_DURATION): vol.Coerce(float),
                vol.Optional(const.ZONE_MAXIMUM_BUCKET): vol.Or(float, int, None),
```

Nachher:

```python
                vol.Optional(const.ZONE_MAXIMUM_DURATION): vol.Coerce(float),
                # #139: whole seconds from the panel's number input. Coerced so a
                # posted "6" is stored as 6 (ALLOW_EXTRA would pass the string on).
                # User-editable, so NOT in the server-owned strip list below; see
                # test_zone_view_coerces_latency_margin_to_int.
                vol.Optional(const.ZONE_LATENCY_MARGIN): vol.Coerce(int),
                vol.Optional(const.ZONE_MAXIMUM_BUCKET): vol.Or(float, int, None),
```

- [ ] **Step 7: Tests grün**

```bash
cd /d/Entwicklung/HASI/HAsmartirrigation
mkdir -p D:/Entwicklung/HASI/pr139-work/tmp D:/Entwicklung/HASI/pr139-work/npm-cache && export TEMP=D:/Entwicklung/HASI/pr139-work/tmp TMP=D:/Entwicklung/HASI/pr139-work/tmp TMPDIR=D:/Entwicklung/HASI/pr139-work/tmp npm_config_cache=D:/Entwicklung/HASI/pr139-work/npm-cache
./.venv/Scripts/python.exe -m pytest tests/test_store_self_closing.py tests/test_distributor_integration.py -p _local_socket_unblock -q -k "latency_margin"
```

Erwartet (real beobachtet):

```
====================== 3 passed, 25 deselected in 0.78s =======================
```

- [ ] **Step 8: Lint**

```bash
cd /d/Entwicklung/HASI/HAsmartirrigation
uvx black custom_components/irrigation_plus/
uvx ruff check custom_components/irrigation_plus/
```

Erwartet (real beobachtet):

```
67 files left unchanged.
All checks passed!
```

- [ ] **Step 9: Verwandte Suiten**

```bash
cd /d/Entwicklung/HASI/HAsmartirrigation
mkdir -p D:/Entwicklung/HASI/pr139-work/tmp D:/Entwicklung/HASI/pr139-work/npm-cache && export TEMP=D:/Entwicklung/HASI/pr139-work/tmp TMP=D:/Entwicklung/HASI/pr139-work/tmp TMPDIR=D:/Entwicklung/HASI/pr139-work/tmp npm_config_cache=D:/Entwicklung/HASI/pr139-work/npm-cache
./.venv/Scripts/python.exe -m pytest tests/test_store_self_closing.py tests/test_distributor_integration.py tests/test_store.py tests/test_store_buffers.py tests/test_store_distributor.py tests/test_store_legacy_migrations.py tests/test_store_operations.py tests/test_websocket_get_nominal_demand.py tests/test_websocket_get_schedules.py tests/test_websocket_run_zone.py tests/test_websocket_version.py -p _local_socket_unblock -q
```

Erwartet (real beobachtet): `149 passed`. Basis `0b418644` mit derselben Befehlszeile:
`146 passed in 10.62s`, alle grün; +3 neue Tests; `test_storage_version_is_14` enthalten und grün.

```
============================ 149 passed in 10.61s =============================
```

- [ ] **Step 10: Mutationsprobe**

Verfahren aus Task 0, Step 5: `mutate.py`, Suchtexte mit `\n`, Sicherung
`D:/Entwicklung/HASI/pr139-work/mut/t01-<probe>.bak`, nach jeder Probe Wiederherstellung aus der `.bak` und
SHA-256-Prüfung (Pflicht), `git diff --stat` wie vor der Probe. Lauf je Probe: `-k "latency_margin"` auf die
beiden Testdateien aus Step 2. Suchtext → Ersatz steht je Probe wörtlich in der Tabelle; jeder Suchtext
kommt am Commit dieses Tasks genau einmal vor. Die erste Probe vollständig:

```bash
cd /d/Entwicklung/HASI/HAsmartirrigation
mkdir -p D:/Entwicklung/HASI/pr139-work/tmp D:/Entwicklung/HASI/pr139-work/npm-cache && export TEMP=D:/Entwicklung/HASI/pr139-work/tmp TMP=D:/Entwicklung/HASI/pr139-work/tmp TMPDIR=D:/Entwicklung/HASI/pr139-work/tmp npm_config_cache=D:/Entwicklung/HASI/pr139-work/npm-cache
F=custom_components/irrigation_plus/store.py
B=D:/Entwicklung/HASI/pr139-work/mut/t01-load-line.bak
cp "$F" "$B"
S=$(sha256sum "$F" | cut -d' ' -f1)
./.venv/Scripts/python.exe D:/Entwicklung/HASI/pr139-work/mut/mutate.py "$F" $'                        latency_margin=zone.get(\n                            ZONE_LATENCY_MARGIN, DEFAULT_LATENCY_MARGIN_SECONDS\n                        ),\n' ''
PYTHONDONTWRITEBYTECODE=1 ./.venv/Scripts/python.exe -m pytest tests/test_store_self_closing.py tests/test_distributor_integration.py -p _local_socket_unblock -q -p no:cacheprovider -k "latency_margin"
cp "$B" "$F"
echo "$S  $F" | sha256sum -c -
git diff --stat
```

`store-revert` benutzt statt `mutate.py` den Stand der Basis:
`git show 0b418644:custom_components/irrigation_plus/store.py > custom_components/irrigation_plus/store.py`.
Das schreibt ebenfalls LF; Wiederherstellung und SHA-256-Prüfung wie oben.

| Probe | Mutation (Suchtext → Ersatz) | Test | Beobachtet (real, am Commit dieses Tasks) |
|---|---|---|---|
| load-line | `store.py`: `                        latency_margin=zone.get(\n                            ZONE_LATENCY_MARGIN, DEFAULT_LATENCY_MARGIN_SECONDS\n                        ),\n` → leer (die drei Zeilen im Ladeblock) | `test_latency_margin_survives_reload` | FAIL `assert 4 == 7` (1 failed, 2 passed) |
| load-default | `store.py`: dieselben drei Zeilen → `                        latency_margin=zone.get(ZONE_LATENCY_MARGIN),\n` | `test_zone_stored_without_latency_margin_loads_the_default` | FAIL `assert None == 4` (1 failed, 2 passed) |
| const-default | `const.py`: `DEFAULT_LATENCY_MARGIN_SECONDS = 4` → `DEFAULT_LATENCY_MARGIN_SECONDS = 5` | `test_zone_stored_without_latency_margin_loads_the_default` | FAIL `assert 5 == 4` / `where 5 = const.DEFAULT_LATENCY_MARGIN_SECONDS` (1 failed, 2 passed) |
| store-revert | `store.py` komplett auf den Stand `0b418644` (`git show`, siehe oben; kein `attr.ib`, keine Ladezeile) | beide Store-Tests | FAIL 2x `KeyError: 'latency_margin'` (2 failed, 1 passed) |
| ws-coerce-removed | `websockets.py`: `                vol.Optional(const.ZONE_LATENCY_MARGIN): vol.Coerce(int),\n` → leer | `test_zone_view_coerces_latency_margin_to_int` | FAIL `AssertionError: assert '6' == 6` (1 failed, 2 passed) |
| ws-coerce-float | `websockets.py`: `vol.Optional(const.ZONE_LATENCY_MARGIN): vol.Coerce(int)` → `vol.Optional(const.ZONE_LATENCY_MARGIN): vol.Coerce(float)` | `test_zone_view_coerces_latency_margin_to_int` | FAIL `assert False` / `where False = isinstance(6.0, int)` (1 failed, 2 passed) |

6 von 6 Proben gefangen; jeder der drei neuen Tests scheitert an mindestens einer Probe. Nach jeder
Wiederherstellung war die SHA-256 der Datei gleich dem Ausgangsstand (`store.py` `e226ea956100…`,
`const.py` `68d150d21053…`, `websockets.py` `b20d76e61a22…`) und `git status` sauber.

- [ ] **Step 11: Commit**

```bash
cd /d/Entwicklung/HASI/HAsmartirrigation
git add custom_components/irrigation_plus/const.py custom_components/irrigation_plus/store.py custom_components/irrigation_plus/websockets.py tests/test_store_self_closing.py tests/test_distributor_integration.py
git commit -F - <<'EOF'
feat(service): add a per-zone latency margin setting for confirmed valves

A confirmed service run is finished by the watcher on the valve's own off
report plus 5 s of debounce, but the backstop is armed at exactly the planned
window and beats that report on every normal run (#139). Measured Tuya valves
report their close 2-3 s after their window. The fix needs a per-zone margin
that the backstop and the completed/partial tolerance can add.

This commit only introduces the setting (default 4 s, capped at 30): stored on
ZoneEntry, hydrated on load so it does not revert to the default on every
restart, and coerced to int by the zone view so a value posted from the
panel's number input is not stored as a string. Zones stored before this
change load with the default; STORAGE_VERSION stays 14. No run behaviour
changes yet.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
```

Erwartet (real beobachtet, Revisions-Probelauf `dry2`, Commit `745e4bac`): `5 files changed, 126 insertions(+)`.

**Neue Test-Helfer:** `_reload_payload(reg)` und `_reloaded(hass, data)` in
`tests/test_store_self_closing.py` — spielen den Store über sein eigenes Persistenzformat
(`attr.asdict`) neu ein; spätere Tasks, die ein Zonen- oder Laufdatenfeld über einen Neuladevorgang
prüfen, können sie wiederverwenden.

---

### Task 2: Laufdaten-Schlüssel, Policy-Flag und reine Helfer für die Wartezeit (noch ohne Aufrufer)

**Files** (Zeilen auf `0b418644`):
- Modify: `custom_components/irrigation_plus/const.py:958-959` (RUN_*-Block, direkt nach `RUN_WATCH_ENTITY`)
- Modify: `custom_components/irrigation_plus/run_watch.py:205-206, 252-253` (`WatchPolicy`-Feld nach `finish_settle_seconds`; sieben Modul-Helfer zwischen `run_credit_ceiling` und `queue_deadline_seconds`)
- Modify: `custom_components/irrigation_plus/self_closing.py:62-63` (`SERVICE_WATCH_POLICY` setzt das Flag)
- Create: `tests/test_finish_grace_helpers.py`

Ziel: Alle Pfade, die ab Task 3 die Wartezeit brauchen (Dispatch, Backstop, Neustart, In-flight,
Zeitfenster-Preis), lesen EINE Antwort aus reinen Funktionen: welche Zone/welcher Lauf eine
Wartezeit hat (`zone_finish_grace_seconds`, `run_has_finish_grace`), wie lang sie ist
(`run_finish_grace_seconds`), welche Toleranz zwischen abgeschlossen und Teil-Lauf gilt
(`run_completion_tolerance`) und wie lang das Ventil offen gemeldet war (`valve_window_seconds`).
Das Tor ist die Policy (`settles_on_valve_window`, nur Service) plus eine eingefrorene Marge —
nicht `RUN_WATCH_ENTITY` allein, weil Batch- und OpenSprinkler-Datensätze diesen Schlüssel auch
tragen. Dazu der Ersatz für den Pause/Resume-Test aus der Vorgabe: `_watch_resume` plant für einen
Batch-Lauf mit denselben Schlüsseln weiter genau `remaining`. Kein Aufrufer ändert sich in diesem
Task; Batch und OpenSprinkler bleiben byte-gleich.

- [ ] **Step 1: Fehlschlagende Tests schreiben**

Neue Datei `tests/test_finish_grace_helpers.py` (so, wie `black` sie formatiert):

```python
"""The finish grace of a confirmed service run, as pure arithmetic (issue #139).

A confirmed service valve reports its own close a few seconds after its window,
and the watcher debounces that report for SERVICE_WATCH_SETTLE_SECONDS. These
helpers decide who gets the extra wait (a confirmed SERVICE run only, never a
batch or OpenSprinkler record that happens to carry the same keys), how long it
is, how short of the window still counts as completed, and how long the valve
was actually open. No coordinator and no hass: every answer is read off a zone
dict or a run record, which is what keeps the dispatch, the backstop, the
restart and the pricing paths from answering differently.
"""

from datetime import datetime, timedelta
from unittest.mock import Mock

import pytest
from homeassistant.util import dt as dt_util

# Importing self_closing registers the service policy (and, through its own
# imports, the batch and OpenSprinkler ones) before watch_policy_for is asked.
import custom_components.irrigation_plus.self_closing  # noqa: F401
from custom_components.irrigation_plus import const
from custom_components.irrigation_plus.batch import WATCH_POLICY as BATCH_POLICY
from custom_components.irrigation_plus.opensprinkler import (
    WATCH_POLICY as OPENSPRINKLER_POLICY,
)
from custom_components.irrigation_plus.run_watch import (
    RunWatchMixin,
    run_completion_tolerance,
    run_finish_grace_seconds,
    run_has_finish_grace,
    run_latency_margin,
    valve_window_seconds,
    watch_policy_for,
    zone_finish_grace_seconds,
    zone_latency_margin,
)
from custom_components.irrigation_plus.self_closing import (
    SERVICE_WATCH_POLICY,
    SelfClosingMixin,
)

VALVE = "binary_sensor.valve_flowing"
T0 = datetime(2026, 1, 10, 10, 0, 0, tzinfo=dt_util.UTC)


def _iso(offset_s: float) -> str:
    return (T0 + timedelta(seconds=offset_s)).isoformat()


def _service_zone(**kw) -> dict:
    zone = {
        const.ZONE_ID: 2,
        const.ZONE_WATERING_MODE: const.WATERING_MODE_SERVICE,
        const.ZONE_CONFIRM_ENTITY: VALVE,
    }
    zone.update(kw)
    return zone


def _confirmed_run(mode=const.WATERING_MODE_SERVICE, **kw) -> dict:
    run = {
        const.RUN_ZONE_ID: 2,
        const.RUN_MODE: mode,
        const.RUN_PLANNED_SECONDS: 600,
        const.RUN_STARTED: _iso(0),
        const.RUN_WATCH_ENTITY: VALVE,
        const.RUN_LATENCY_MARGIN: 4,
    }
    run.update(kw)
    return run


class TestZoneLatencyMargin:
    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ("7", 7),
            (7.6, 8),
            (-3, 0),
            (99, 30),
            ("x", 4),
        ],
    )
    def test_the_margin_is_whole_seconds_clamped_to_its_bounds(self, raw, expected):
        zone = _service_zone(**{const.ZONE_LATENCY_MARGIN: raw})
        assert zone_latency_margin(zone) == expected

    def test_a_zone_stored_without_a_margin_gets_the_default(self):
        assert zone_latency_margin(_service_zone()) == 4
        assert zone_latency_margin(None) == const.DEFAULT_LATENCY_MARGIN_SECONDS


class TestZoneFinishGrace:
    def test_a_confirmed_service_zone_waits_settle_plus_margin(self):
        assert zone_finish_grace_seconds(_service_zone()) == 9.0

    def test_a_margin_of_zero_still_leaves_the_debounce(self):
        zone = _service_zone(**{const.ZONE_LATENCY_MARGIN: 0})
        assert zone_finish_grace_seconds(zone) == 5.0

    def test_a_write_only_service_zone_has_no_grace(self):
        zone = _service_zone(**{const.ZONE_CONFIRM_ENTITY: None})
        assert zone_finish_grace_seconds(zone) == 0.0

    def test_a_batch_zone_with_a_confirm_entity_has_no_grace(self):
        zone = _service_zone(**{const.ZONE_WATERING_MODE: const.WATERING_MODE_BATCH})
        assert zone_finish_grace_seconds(zone) == 0.0

    def test_an_opensprinkler_zone_has_no_grace(self):
        zone = _service_zone(
            **{const.ZONE_WATERING_MODE: const.WATERING_MODE_OPENSPRINKLER}
        )
        assert zone_finish_grace_seconds(zone) == 0.0


class TestRunLatencyMargin:
    def test_the_frozen_margin_is_read_back_as_seconds(self):
        assert run_latency_margin(_confirmed_run()) == 4.0
        assert (
            run_latency_margin(_confirmed_run(**{const.RUN_LATENCY_MARGIN: "6"})) == 6.0
        )

    def test_a_record_without_a_margin_answers_none(self):
        run = _confirmed_run()
        del run[const.RUN_LATENCY_MARGIN]
        assert run_latency_margin(run) is None
        assert run_latency_margin(None) is None

    def test_a_negative_margin_reads_as_zero_and_garbage_as_none(self):
        assert (
            run_latency_margin(_confirmed_run(**{const.RUN_LATENCY_MARGIN: -2})) == 0.0
        )
        assert (
            run_latency_margin(_confirmed_run(**{const.RUN_LATENCY_MARGIN: "x"}))
            is None
        )


class TestRunHasFinishGrace:
    def test_a_confirmed_service_run_with_a_margin_has_it(self):
        assert run_has_finish_grace(_confirmed_run()) is True

    def test_a_record_from_before_the_update_has_none(self):
        """No margin frozen at dispatch: the run keeps the formula it started with."""
        run = _confirmed_run()
        del run[const.RUN_LATENCY_MARGIN]
        assert run_has_finish_grace(run) is False

    def test_an_unconfirmed_run_has_none(self):
        run = _confirmed_run()
        del run[const.RUN_WATCH_ENTITY]
        assert run_has_finish_grace(run) is False

    def test_a_batch_record_carrying_both_keys_has_none(self):
        """RUN_WATCH_ENTITY alone is not the gate: batch records carry it too."""
        run = _confirmed_run(mode=const.WATERING_MODE_BATCH)
        assert run_has_finish_grace(run) is False

    def test_an_opensprinkler_record_carrying_both_keys_has_none(self):
        run = _confirmed_run(mode=const.WATERING_MODE_OPENSPRINKLER)
        assert run_has_finish_grace(run) is False


class TestRunFinishGraceAndTolerance:
    def test_the_grace_is_settle_plus_the_frozen_margin(self):
        assert run_finish_grace_seconds(_confirmed_run()) == 9.0

    def test_a_run_without_grace_waits_nothing_extra(self):
        run = _confirmed_run()
        del run[const.RUN_WATCH_ENTITY]
        assert run_finish_grace_seconds(run) == 0.0

    def test_the_completion_tolerance_is_the_margin(self):
        assert run_completion_tolerance(_confirmed_run()) == 4.0

    def test_the_completion_tolerance_never_drops_below_one_second(self):
        run = _confirmed_run(**{const.RUN_LATENCY_MARGIN: 0})
        assert run_completion_tolerance(run) == 1.0

    def test_a_run_without_grace_keeps_the_one_second_slack(self):
        run = _confirmed_run(mode=const.WATERING_MODE_BATCH)
        assert run_completion_tolerance(run) == 1.0


class TestValveWindowSeconds:
    def test_the_window_is_the_off_report_minus_the_on_report(self):
        run = _confirmed_run(
            **{const.RUN_VALVE_ON: _iso(0.5), const.RUN_VALVE_OFF: _iso(420.5)}
        )
        now = T0 + timedelta(seconds=2000)
        assert valve_window_seconds(run, now) == pytest.approx(420.0)

    def test_an_off_report_before_the_on_report_is_a_zero_window(self):
        run = _confirmed_run(
            **{const.RUN_VALVE_ON: _iso(10), const.RUN_VALVE_OFF: _iso(5)}
        )
        assert valve_window_seconds(run, T0 + timedelta(seconds=20)) == 0.0

    def test_without_an_off_report_the_window_is_the_time_since_on(self):
        run = _confirmed_run(**{const.RUN_VALVE_ON: _iso(0)})
        assert valve_window_seconds(run, T0 + timedelta(seconds=300)) == 300.0

    def test_without_an_off_report_the_window_is_bounded_by_the_plan(self):
        """The valve closed while HA was down: never credit the outage as water."""
        run = _confirmed_run(**{const.RUN_VALVE_ON: _iso(0)})
        assert valve_window_seconds(run, T0 + timedelta(seconds=900)) == 600.0

    def test_the_anchor_falls_back_to_the_observed_start(self):
        run = _confirmed_run(
            **{
                const.RUN_STARTED: _iso(-50),
                const.RUN_OBSERVED_START: _iso(0),
                const.RUN_VALVE_OFF: _iso(120),
            }
        )
        assert valve_window_seconds(run, T0 + timedelta(seconds=500)) == 120.0

    def test_the_anchor_falls_back_to_the_dispatch_instant(self):
        run = _confirmed_run(
            **{const.RUN_STARTED: _iso(-50), const.RUN_VALVE_OFF: _iso(120)}
        )
        assert valve_window_seconds(run, T0 + timedelta(seconds=500)) == 170.0

    def test_a_record_with_no_anchor_answers_the_plan(self):
        run = _confirmed_run(**{const.RUN_VALVE_OFF: _iso(120)})
        del run[const.RUN_STARTED]
        assert valve_window_seconds(run, T0 + timedelta(seconds=500)) == 600.0


class TestOnlyTheServicePolicySettlesOnTheValveWindow:
    def test_the_service_policy_settles_on_the_valve_window(self):
        assert SERVICE_WATCH_POLICY.settles_on_valve_window is True
        assert (
            watch_policy_for(const.WATERING_MODE_SERVICE).settles_on_valve_window
            is True
        )

    def test_the_batch_policy_does_not(self):
        assert BATCH_POLICY.settles_on_valve_window is False
        assert (
            watch_policy_for(const.WATERING_MODE_BATCH).settles_on_valve_window is False
        )

    def test_the_opensprinkler_policy_does_not(self):
        assert OPENSPRINKLER_POLICY.settles_on_valve_window is False
        assert (
            watch_policy_for(const.WATERING_MODE_OPENSPRINKLER).settles_on_valve_window
            is False
        )


class _Host(SelfClosingMixin, RunWatchMixin):
    """Just enough coordinator to exercise _watch_resume on a run record."""

    def __init__(self, runs=None):
        self._runs = list(runs or [])
        self._sc_schedule_cleanup = Mock()

    async def _sc_active_runs(self):
        return [dict(r) for r in self._runs]

    async def _sc_persist_runs(self, runs):
        self._runs = [dict(r) for r in runs]


class TestABatchResumeArmsExactlyTheRemainder:
    async def test_resume_re_arms_the_backstop_for_the_remaining_window_only(self):
        """The pause/resume half of #139's test list, pinned where it really applies.

        _watch_resume is reached only for a segmented policy, and service is not
        segmented: a margin added there would change batch and nothing else. So
        the pin is the opposite one: a paused BATCH run whose record carries the
        same keys a confirmed service run does still re-arms its backstop for
        planned minus watered, with no settle and no margin on top.
        """
        run = _confirmed_run(
            mode=const.WATERING_MODE_BATCH,
            **{
                const.RUN_ZONE_ID: 1,
                const.RUN_OBSERVED_START: _iso(0),
                const.RUN_WATERED_SECONDS: 60.0,
                const.RUN_SEGMENT_STARTED: None,
            },
        )
        host = _Host([run])

        await host._watch_resume(1, dict(run))

        assert host._sc_schedule_cleanup.call_count == 1
        assert host._sc_schedule_cleanup.call_args.args == (1, 540.0)
        assert host._runs[0][const.RUN_SEGMENT_STARTED] is not None
```

Warum der Resume-Test am leichten `_Host` statt am Batch-Harness aus `tests/test_batch.py` hängt:
`_watch_resume` braucht weder `hass` noch Timer, nur `_sc_run_elapsed` (für einen pausierten
segmentierten Lauf exakt `RUN_WATERED_SECONDS`), `_watch_update_run` und einen
`_sc_schedule_cleanup`-Mock. So ist `remaining` deterministisch 600 − 60 = 540, ohne echte
Timer-Abhängigkeit oder Lingering-Timer-Risiko.

- [ ] **Step 2: Tests laufen lassen, Fehlschlag bestätigen**

```bash
cd /d/Entwicklung/HASI/HAsmartirrigation
mkdir -p D:/Entwicklung/HASI/pr139-work/tmp D:/Entwicklung/HASI/pr139-work/npm-cache && export TEMP=D:/Entwicklung/HASI/pr139-work/tmp TMP=D:/Entwicklung/HASI/pr139-work/tmp TMPDIR=D:/Entwicklung/HASI/pr139-work/tmp npm_config_cache=D:/Entwicklung/HASI/pr139-work/npm-cache
./.venv/Scripts/python.exe -m pytest tests/test_finish_grace_helpers.py -p _local_socket_unblock -q
```

Erwartet (real beobachtet; die Helfer existieren noch nicht, die ganze Datei scheitert beim Sammeln):

```
E   ImportError: cannot import name 'run_completion_tolerance' from 'custom_components.irrigation_plus.run_watch'
ERROR tests/test_finish_grace_helpers.py
!!!!!!!!!!!!!!!!!!! Interrupted: 1 error during collection !!!!!!!!!!!!!!!!!!!!
============================== 1 error in 1.37s ===============================
```

- [ ] **Step 3: `const.py` — drei Laufdaten-Schlüssel**

Im RUN_*-Block direkt nach `RUN_WATCH_ENTITY`, vor dem Segment-Block:

Vorher:

```python
RUN_WATCH_ENTITY = "watch_entity"
# --- Segmented run time (issue #88) ----------------------------------------
```

Nachher:

```python
RUN_WATCH_ENTITY = "watch_entity"
# The zone's latency margin, frozen into a CONFIRMED service run at dispatch
# (#139). Read back by the backstop, the completed/partial tolerance, the restart
# re-arm and the in-flight window, so a margin edited mid-run cannot move a
# backstop that is already armed. Its presence is also the gate: a record
# persisted before this field existed keeps the timing it was dispatched under,
# and a batch or OpenSprinkler record (which carries RUN_WATCH_ENTITY too) never
# gets one. See run_watch.run_has_finish_grace.
RUN_LATENCY_MARGIN = "latency_margin"
# ISO-8601 UTC instant the valve REPORTED itself on: the confirm entity's
# last_changed, clamped to [dispatch, confirm return]. RUN_STARTED is stamped
# after the confirm poll returns, up to a poll later than the water; measuring
# actual_s from it would shorten every run by that poll and turn a normal end
# into a partial. The clamp keeps a valve that was already open before dispatch
# from dragging the anchor hours back. RUN_STARTED stays as it is for everything
# else that reads it.
RUN_VALVE_ON = "valve_on"
# ISO-8601 UTC of the valve's first off report since its last on, taken from the
# state event's last_changed, so attribute updates of an already-off valve and
# the debounce task's own latency cannot move it. Recorded only from a state
# event whose previous state was running (on/open/opening), which is what "first
# off since the last on" means: never from the first evaluation after a restart
# (it has no previous state, and last_changed is the entity coming back, not the
# close) and never from unavailable/unknown/None -> off (Zigbee valves come back
# from a restart as unavailable first, and the off that follows carries their
# return in last_changed, not the close). Without an off report the window is
# bounded by the clock instead (run_watch.valve_window_seconds). Cleared when the
# valve reports running again. valve_on to valve_off is the run's actual_s.
RUN_VALVE_OFF = "valve_off"
# --- Segmented run time (issue #88) ----------------------------------------
```

- [ ] **Step 4: `run_watch.py` — Policy-Feld `settles_on_valve_window`**

Am Ende von `WatchPolicy`, nach `finish_settle_seconds`:

Vorher:

```python
    finish_settle_seconds: float = 0.0


def is_acknowledged(state) -> bool:
```

Nachher:

```python
    finish_settle_seconds: float = 0.0
    # Whether a run's end is settled on the VALVE'S OWN reports rather than on
    # the wall clock: its actual_s is the window from the on report to the off
    # report, its backstop waits finish_settle_seconds plus the zone's latency
    # margin past the planned window, and a run within that margin of its window
    # is completed, not partial (#139).
    #
    # Only a mode whose valve opens at dispatch and reports its own close has
    # those reports. A queue controller's watch entity is its station, whose
    # timing is the controller's, and a batch controller can pause, so both keep
    # False and stay byte-for-byte on the timing their tests pin. Keyed on the
    # policy rather than on RUN_WATCH_ENTITY, because batch and OpenSprinkler
    # records carry that key as well.
    settles_on_valve_window: bool = False


def is_acknowledged(state) -> bool:
```

- [ ] **Step 5: `run_watch.py` — sieben Modul-Helfer**

Zwischen `run_credit_ceiling` und `queue_deadline_seconds` (`watch_policy_for` steht am Dateiende;
der Aufruf im Funktionsrumpf ist zur Laufzeit aufgelöst, kein neuer Import nötig — `dt_util` und
`const` sind schon importiert):

Vorher:

```python
    try:
        return float(recorded)
    except (TypeError, ValueError):
        return float("inf")


def queue_deadline_seconds(runs: list, run: dict, *, mode: str | None = None) -> float:
```

Nachher:

```python
    try:
        return float(recorded)
    except (TypeError, ValueError):
        return float("inf")


def zone_latency_margin(zone: dict) -> int:
    """The zone's latency margin in whole seconds, clamped to [0, MAX]."""
    raw = (zone or {}).get(const.ZONE_LATENCY_MARGIN)
    if raw is None:
        return const.DEFAULT_LATENCY_MARGIN_SECONDS
    try:
        value = int(round(float(raw)))
    except (TypeError, ValueError):
        return const.DEFAULT_LATENCY_MARGIN_SECONDS
    return max(0, min(const.MAX_LATENCY_MARGIN_SECONDS, value))


def zone_finish_grace_seconds(zone: dict) -> float:
    """Seconds past the planned window a confirmed service run may take to settle.

    settle + margin for a SERVICE zone with a confirm_entity, else 0. Used where no run
    exists yet: the window pricing and the observed-watering lockout at dispatch.
    """
    zone = zone or {}
    if zone.get(const.ZONE_WATERING_MODE) != const.WATERING_MODE_SERVICE:
        return 0.0
    if not zone.get(const.ZONE_CONFIRM_ENTITY):
        return 0.0
    return float(const.SERVICE_WATCH_SETTLE_SECONDS + zone_latency_margin(zone))


def run_latency_margin(run: dict) -> float | None:
    """The margin frozen into a run at dispatch, or None (write-only / pre-update record)."""
    raw = run.get(const.RUN_LATENCY_MARGIN) if isinstance(run, dict) else None
    if raw is None:
        return None
    try:
        return max(0.0, float(raw))
    except (TypeError, ValueError):
        return None


def run_has_finish_grace(run: dict) -> bool:
    """True for a run whose end the watcher settles on the valve's own reports.

    All three: its mode's policy settles on the valve window (service only), it was
    confirmed (RUN_WATCH_ENTITY) and it carries a frozen margin. RUN_WATCH_ENTITY alone
    is not enough — OpenSprinkler and batch records carry it too.
    """
    if not isinstance(run, dict) or not run.get(const.RUN_WATCH_ENTITY):
        return False
    if run_latency_margin(run) is None:
        return False
    return watch_policy_for(run.get(const.RUN_MODE)).settles_on_valve_window


def run_finish_grace_seconds(run: dict) -> float:
    """settle + frozen margin for a run with a finish grace, else 0."""
    if not run_has_finish_grace(run):
        return 0.0
    policy = watch_policy_for(run.get(const.RUN_MODE))
    return float(policy.finish_settle_seconds) + float(run_latency_margin(run))


def run_completion_tolerance(run: dict) -> float:
    """Seconds short of the planned window that still count as a completed run."""
    if not run_has_finish_grace(run):
        return 1.0
    return max(1.0, float(run_latency_margin(run)))


def valve_window_seconds(run: dict, now) -> float:
    """Seconds the valve was reported open: its off report minus its on report.

    Anchor = RUN_VALVE_ON, else RUN_OBSERVED_START, else RUN_STARTED. Without an off
    report (the valve closed while HA was down) the window is bounded, not guessed:
    min(now - anchor, planned).
    """
    planned = planned_seconds(run)
    anchor = dt_util.parse_datetime(
        run.get(const.RUN_VALVE_ON)
        or run.get(const.RUN_OBSERVED_START)
        or run.get(const.RUN_STARTED)
        or ""
    )
    if anchor is None:
        return planned
    off = dt_util.parse_datetime(run.get(const.RUN_VALVE_OFF) or "")
    if off is not None:
        return max(0.0, (off - anchor).total_seconds())
    return max(0.0, min((now - anchor).total_seconds(), planned))


def queue_deadline_seconds(runs: list, run: dict, *, mode: str | None = None) -> float:
```

- [ ] **Step 6: `self_closing.py` — Service-Policy setzt das Flag**

Vorher:

```python
    finish_settle_seconds=const.SERVICE_WATCH_SETTLE_SECONDS,
)
register_watch_policy(SERVICE_WATCH_POLICY)
```

Nachher:

```python
    finish_settle_seconds=const.SERVICE_WATCH_SETTLE_SECONDS,
    # The valve reports both ends of the run itself, so actual_s is the window
    # between those reports and a close that arrives within the zone's latency
    # margin of the planned end still settles through the watcher (#139). The
    # backstop, armed at exactly the window, used to beat that report on every
    # normal run.
    settles_on_valve_window=True,
)
register_watch_policy(SERVICE_WATCH_POLICY)
```

`batch.py` und `opensprinkler.py` bleiben unverändert (Default `False`).

- [ ] **Step 7: Tests grün**

```bash
cd /d/Entwicklung/HASI/HAsmartirrigation
mkdir -p D:/Entwicklung/HASI/pr139-work/tmp D:/Entwicklung/HASI/pr139-work/npm-cache && export TEMP=D:/Entwicklung/HASI/pr139-work/tmp TMP=D:/Entwicklung/HASI/pr139-work/tmp TMPDIR=D:/Entwicklung/HASI/pr139-work/tmp npm_config_cache=D:/Entwicklung/HASI/pr139-work/npm-cache
./.venv/Scripts/python.exe -m pytest tests/test_finish_grace_helpers.py -p _local_socket_unblock -q
```

Erwartet (real beobachtet):

```
============================= 35 passed in 2.26s ==============================
```

- [ ] **Step 8: Lint**

```bash
cd /d/Entwicklung/HASI/HAsmartirrigation
uvx black custom_components/irrigation_plus/
uvx ruff check custom_components/irrigation_plus/
```

Erwartet (real beobachtet):

```
67 files left unchanged.
All checks passed!
```

(Die Testdatei liegt außerhalb des CI-Lint-Umfangs; sie wurde zusätzlich mit
`uvx black tests/test_finish_grace_helpers.py` formatiert — Step 1 zeigt diese Fassung.)

- [ ] **Step 9: Verwandte Suiten**

```bash
cd /d/Entwicklung/HASI/HAsmartirrigation
mkdir -p D:/Entwicklung/HASI/pr139-work/tmp D:/Entwicklung/HASI/pr139-work/npm-cache && export TEMP=D:/Entwicklung/HASI/pr139-work/tmp TMP=D:/Entwicklung/HASI/pr139-work/tmp TMPDIR=D:/Entwicklung/HASI/pr139-work/tmp npm_config_cache=D:/Entwicklung/HASI/pr139-work/npm-cache
./.venv/Scripts/python.exe -m pytest tests/test_finish_grace_helpers.py tests/test_run_segments.py tests/test_run_watch.py tests/test_batch.py tests/test_opensprinkler.py tests/test_service_watch.py -p _local_socket_unblock -q
```

Erwartet (real beobachtet):

```
======================= 210 passed, 52 errors in 21.98s =======================
```

Die 52 Errors sind ausnahmslos `Failed: Lingering timer after job ...` beim Teardown (lokale
HA-2024.12.5-Umgebung) und bestehen unverändert am Elternstand `745e4bac` (Task 1, Revisions-Probelauf `dry2`,
nach dem Feinschliff erneut gemessen): dieselben fünf Dateien dort `175 passed, 52 errors in 17.60s`; die
sortierten `FAILED`/`ERROR`-Zeilen beider Läufe sind identisch (`diff` leer). 210 = 175 + 35 neue Tests. Die Basis `0b418644` zeigt für diese Dateien
ebenfalls 52 Errors (real: `175 passed, 52 errors`). Keine neue Fehlschlag- oder Error-Zeile durch diesen Task.

- [ ] **Step 10: Mutationsprobe**

Verfahren aus Task 0, Step 5: `mutate.py`, Suchtexte mit `\n`, Sicherung
`D:/Entwicklung/HASI/pr139-work/mut/t02-<probe>.bak`, nach jeder Probe Wiederherstellung aus der `.bak` und
SHA-256-Prüfung (Pflicht), `git diff --stat` wie vor der Probe. Lauf je Probe:
`tests/test_finish_grace_helpers.py -k "<Test(s)>"` mit den Namen aus der Spalte „Test(s)“ (mehrere mit `or`
verbunden). Suchtext → Ersatz steht wörtlich in der Tabelle, so wie im Probelauf angewandt; jeder Suchtext
kommt genau einmal vor. `run_watch` = `custom_components/irrigation_plus/run_watch.py`, `self_closing` =
`custom_components/irrigation_plus/self_closing.py`.

| Probe | Datei: Suchtext → Ersatz | Test(s) | Beobachtet |
|---|---|---|---|
| zone-clamp | run_watch: `    return max(0, min(const.MAX_LATENCY_MARGIN_SECONDS, value))` → `    return value` | `clamped_to_its_bounds` | FAIL (2) `assert -3 == 0` |
| zone-round | run_watch: `value = int(round(float(raw)))` → `value = int(float(raw))` | `clamped_to_its_bounds` | FAIL `assert 7 == 8` |
| zone-garbage | run_watch: `    except (TypeError, ValueError):\n        return const.DEFAULT_LATENCY_MARGIN_SECONDS\n` → `    except (TypeError, ValueError):\n        return 0\n` | `clamped_to_its_bounds` | FAIL `assert 0 == 4` |
| zone-default | run_watch: `    if raw is None:\n        return const.DEFAULT_LATENCY_MARGIN_SECONDS\n` → `    if raw is None:\n        return 0\n` | `stored_without_a_margin` | FAIL `assert 0 == 4` |
| zone-mode-gate | run_watch: `    if zone.get(const.ZONE_WATERING_MODE) != const.WATERING_MODE_SERVICE:\n        return 0.0\n` → leer | `batch_zone_with_a_confirm`, `opensprinkler_zone_has_no_grace` | FAIL (2) `assert 9.0 == 0.0` |
| zone-confirm-gate | run_watch: `    if not zone.get(const.ZONE_CONFIRM_ENTITY):\n        return 0.0\n` → leer | `write_only_service_zone` | FAIL `assert 9.0 == 0.0` |
| zone-grace-settle | run_watch: `return float(const.SERVICE_WATCH_SETTLE_SECONDS + zone_latency_margin(zone))` → `return float(zone_latency_margin(zone))` | `waits_settle_plus_margin`, `still_leaves_the_debounce` | FAIL (2) `assert 4.0 == 9.0` |
| run-margin-negative | run_watch: `        return max(0.0, float(raw))` → `        return float(raw)` | `negative_margin` | FAIL `assert -2.0 == 0.0` |
| run-grace-policy | run_watch: `    return watch_policy_for(run.get(const.RUN_MODE)).settles_on_valve_window` → `    return True` | `batch_record_carrying`, `opensprinkler_record_carrying` | FAIL (2) `assert True is False` |
| run-grace-margin-gate | run_watch: `    if run_latency_margin(run) is None:\n        return False\n` → leer | `before_the_update` | FAIL `assert True is False` |
| run-grace-watch-gate | run_watch: `    if not isinstance(run, dict) or not run.get(const.RUN_WATCH_ENTITY):` → `    if not isinstance(run, dict):` | `unconfirmed_run_has_none`, `run_without_grace_waits_nothing` | FAIL (2) `assert True is False` |
| run-grace-settle | run_watch: `return float(policy.finish_settle_seconds) + float(run_latency_margin(run))` → `return float(run_latency_margin(run))` | `settle_plus_the_frozen_margin` | FAIL `assert 4.0 == 9.0` |
| tolerance-floor | run_watch: `return max(1.0, float(run_latency_margin(run)))` → `return float(run_latency_margin(run))` | `never_drops_below_one_second` | FAIL `assert 0.0 == 1.0` |
| tolerance-no-grace | run_watch: `    if not run_has_finish_grace(run):\n        return 1.0\n` → leer | `keeps_the_one_second_slack` | FAIL `assert 4.0 == 1.0` |
| window-off-clamp | run_watch: `return max(0.0, (off - anchor).total_seconds())` → `return (off - anchor).total_seconds()` | `off_report_before_the_on_report` | FAIL `assert -5.0 == 0.0` |
| window-plan-bound | run_watch: `return max(0.0, min((now - anchor).total_seconds(), planned))` → `return max(0.0, (now - anchor).total_seconds())` | `bounded_by_the_plan` | FAIL `assert 900.0 == 600.0` |
| window-anchor-valve-on | run_watch: `        run.get(const.RUN_VALVE_ON)\n        or run.get(const.RUN_OBSERVED_START)\n` → `        run.get(const.RUN_OBSERVED_START)\n` | `off_report_minus_the_on_report`, `time_since_on` | FAIL (1 von 2) `assert 420.5 == 420.0 ± 4.2e-04` |
| window-anchor-observed | run_watch: `        or run.get(const.RUN_OBSERVED_START)\n` → leer | `falls_back_to_the_observed_start` | FAIL `assert 170.0 == 120.0` |
| window-no-anchor | run_watch: `    if anchor is None:\n        return planned\n` → `    if anchor is None:\n        return 0.0\n` | `no_anchor` | FAIL `assert 0.0 == 600.0` |
| policy-service-flag | self_closing: `    settles_on_valve_window=True,\n` → leer | `service_policy_settles`, `confirmed_service_run_with_a_margin` | FAIL (2) `assert False is True` |
| policy-default-true | run_watch: `    settles_on_valve_window: bool = False` → `    settles_on_valve_window: bool = True` | `batch_policy_does_not`, `opensprinkler_policy_does_not` | FAIL (2) `assert True is False` |
| resume-adds-settle | run_watch `_watch_resume`: `        remaining = max(0.0, planned_seconds(run) - self._sc_run_elapsed(run))` → `        remaining = max(0.0, planned_seconds(run) - self._sc_run_elapsed(run)) + const.SERVICE_WATCH_SETTLE_SECONDS` | `remaining_window_only` | FAIL `assert (1, 545.0) == (1, 540.0)` |

22 von 22 Proben gefangen. Real beobachtet im Revisions-Probelauf nach dem Feinschliff: alle 22 Proben am
abgekoppelten Commit dieses Tasks (`94cc3785`, mit den neutralen Testdaten) in einem temporären Prüf-Worktree,
Ersetzung und Wiederherstellung per `D:/Entwicklung/HASI/pr139-work/mut/r7_probes.py <worktree> t02`
(Suchtext genau einmal, `PYTHONDONTWRITEBYTECODE=1`, nur die genannten Tests per `-k`, Sicherungen
`mut/r7-t02-<name>.bak`). Jede Zeile der Tabelle ist die dort beobachtete Ausgabe; die Proben der
Ankerkette beißen auch mit den neutralen Werten (Ein +0,5 s, Aus +420,5 s: ohne `RUN_VALVE_ON` wird der
Anker `RUN_STARTED` und das Fenster 420,5 statt 420,0). Nach jeder Wiederherstellung war die SHA-256 der
Datei gleich dem Ausgangsstand, die MD5 von `git diff` vor und nach allen Proben
`d41d8cd98f00b204e9800998ecf8427e` (leer, der Commit ist ausgecheckt) und `git status --short` leer.

Im echten Lauf (Proben vor dem Commit, auf dem ungestagten Stand) gilt stattdessen: Prüfsumme von
`git diff` vor und nach den Proben identisch, `git diff --stat` wieder `const.py | 28 +`,
`run_watch.py | 101 +`, `self_closing.py | 6 +`.

- [ ] **Step 11: Commit**

```bash
cd /d/Entwicklung/HASI/HAsmartirrigation
git add custom_components/irrigation_plus/const.py custom_components/irrigation_plus/run_watch.py custom_components/irrigation_plus/self_closing.py tests/test_finish_grace_helpers.py
git commit -F - <<'EOF'
feat(run-watch): add the finish-grace run keys, policy flag and helpers

A confirmed service run is settled by the watcher on the valve's own off
report, but its backstop is armed at exactly the planned window and beats
that report on every normal run (#139). The fix needs one answer, shared
by the dispatch, the backstop, the restart and the pricing paths, to four
questions: which run waits past its window, for how long, how far short of
the window still counts as completed, and how long the valve was open.

This adds those answers as pure helpers in run_watch.py, the run keys they
read (RUN_LATENCY_MARGIN frozen at dispatch, RUN_VALVE_ON, RUN_VALVE_OFF)
and a WatchPolicy flag, settles_on_valve_window, that only the service
policy sets. The gate is the policy plus a frozen margin, not
RUN_WATCH_ENTITY alone, because batch and OpenSprinkler records carry that
key too; a record persisted before this change has no margin and keeps
the timing it was dispatched under.

No call site uses them yet. A test pins that a paused batch run carrying
the same keys still re-arms its backstop for exactly the remainder:
_watch_resume is only reached for segmented policies, so a margin there
would change batch and nothing else.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
```

Erwartet (real beobachtet, Revisions-Probelauf `dry2` nach dem Feinschliff, Commit `94cc3785`):
`4 files changed, 427 insertions(+)` (`const.py | 28`, `run_watch.py | 101`, `self_closing.py | 6`,
`tests/test_finish_grace_helpers.py | 292`), `create mode 100644 tests/test_finish_grace_helpers.py`.

**Neue Test-Helfer:** in `tests/test_finish_grace_helpers.py` — `_service_zone(**kw)` (bestätigte
Service-Zone, `confirm_entity` gesetzt, ohne Marge = Default), `_confirmed_run(mode=..., **kw)`
(Laufdatensatz mit `RUN_WATCH_ENTITY` und `RUN_LATENCY_MARGIN` 4, geplant 600 s, `RUN_STARTED` = `T0`),
`_iso(offset_s)` (ISO-UTC relativ zu `T0` = 2026-01-10 10:00:00 UTC, ein neutrales Datum) und `_Host`
(`SelfClosingMixin` + `RunWatchMixin` mit Lauf-Liste im Speicher und `_sc_schedule_cleanup`-Mock).
Spätere Tasks, die reine Lauf-Arithmetik ohne `hass` prüfen, können sie wiederverwenden.

---

### Task 3: Dispatch friert Marge und Ventil-Ein ein, der Backstop trägt die Wartezeit

**Files** (Zeilen auf `0b418644`):
- Modify: `custom_components/irrigation_plus/self_closing.py:25-28, 430-431, 495-496, 538-539, 603-604, 629` (Import aus `.run_watch`; neuer Helfer `_sc_valve_on_instant` nach `_sc_schedule_cleanup`; in `async_run_self_closing`: `dispatched_at`, `confirmed_at`, Laufdatensatz im `elif confirmed:`-Zweig, Backstop-Aufruf)
- Test: `tests/test_service_watch.py:210-216` (bestehender Pin `test_the_finish_backstop_is_armed_once` angepasst; drei neue Klassen direkt danach, vor `TestTheWatcherNeverWritesAWateringRunOff`)

Ziel: Ein bestätigter Service-Lauf nimmt beim Dispatch die Marge seiner Zone (`RUN_LATENCY_MARGIN`)
und die Ein-Meldung seines Ventils (`RUN_VALVE_ON`, begrenzt auf [Dispatch, Confirm-Rückkehr]) in
den Datensatz auf. Der Backstop wird bei `planned + run_finish_grace_seconds(record)` scharf, also
bei Default `600 + 5 + 4 = 609`; write-only und nicht prüfbare Läufe tragen keinen der beiden
Schlüssel und behalten `(2, 600)`. Die Observed-Sperre (`_note_si_valve`) bleibt in diesem Task
unverändert; sie ist Task 3b, damit sie auf #139 getrennt gestrichen werden kann. Zur Abgrenzung der
Zahlen: Die 609 s hier sind die Backstop-Verzögerung. In Task 3b bekommt `_note_si_valve` dasselbe
Argument 609, die Sperre selbst dauert aber `Argument + SI_VALVE_SUPPRESS_MARGIN`
(`irrigation.py:68`, `SI_VALVE_SUPPRESS_MARGIN = 30`; angewendet in `irrigation.py:129`), also
609 + 30 = 639 s statt bisher 600 + 30 = 630 s. Hier ist
`_sc_schedule_cleanup` in `_coord` ein Mock: der Task prüft die Argumente, nicht den echten Timer
(der kommt in Task 5/6). `_sc_schedule_cleanup` selbst bleibt unverändert (Batch und OpenSprinkler
teilen ihn).

- [ ] **Step 1: Fehlschlagende Tests schreiben**

In `tests/test_service_watch.py` den bestehenden Test `test_the_finish_backstop_is_armed_once`
(Klasse `TestAFullRunIsStillAFullRun`) ersetzen und direkt danach drei neue Klassen einfügen. Keine
neuen Importe nötig (`timedelta`, `AsyncMock`, `freeze_time`, `dt_util`, `const` sind da). So, wie
`black` die Datei formatiert:

Vorher:

```python
    async def test_the_finish_backstop_is_armed_once(self, hass):
        """Re-arming it from the observation would push it past the real close."""
        c = _coord(hass)
        await _dispatch(hass, c, _zone())

        assert c._sc_schedule_cleanup.call_count == 1
        assert c._sc_schedule_cleanup.call_args.args == (2, 600)


class TestTheWatcherNeverWritesAWateringRunOff:
```

Nachher:

```python
    async def test_the_finish_backstop_is_armed_once(self, hass):
        """Re-arming it from the observation would push it past the real close.

        Armed once, at dispatch, and already carrying a confirmed run's finish
        grace: the planned 600 s plus the 5 s debounce plus the default 4 s
        latency margin (#139). Armed at exactly the window, it beat the valve's
        own off report on every normal run.
        """
        c = _coord(hass)
        await _dispatch(hass, c, _zone())

        assert c._sc_schedule_cleanup.call_count == 1
        assert c._sc_schedule_cleanup.call_args.args == (2, 609)


class TestAConfirmedRunFreezesItsMarginAtDispatch:
    """The margin a run waits for is the one it was dispatched under (#139).

    Frozen into the record, so a margin edited mid-run cannot move a backstop
    that is already armed, and so a record without it (write-only, unverifiable,
    or persisted before this change) keeps the timing it started with.
    """

    async def test_the_default_margin_is_frozen_into_the_record(self, hass):
        c = _coord(hass)
        await _dispatch(hass, c, _zone())

        run = await c._sc_find_run(2)
        assert run[const.RUN_LATENCY_MARGIN] == 4

    async def test_the_zones_own_margin_is_frozen_into_the_record(self, hass):
        c = _coord(hass)
        await _dispatch(hass, c, _zone(**{const.ZONE_LATENCY_MARGIN: 7}))

        run = await c._sc_find_run(2)
        assert run[const.RUN_LATENCY_MARGIN] == 7

    async def test_a_write_only_run_carries_neither_margin_nor_valve_on(self, hass):
        """No confirm_entity: nothing reports the valve, nothing to wait for."""
        c = _coord(hass)
        await _dispatch(hass, c, _zone(confirm=None))

        run = await c._sc_find_run(2)
        assert const.RUN_LATENCY_MARGIN not in run
        assert const.RUN_VALVE_ON not in run

    async def test_an_unverifiable_run_carries_neither_margin_nor_valve_on(self, hass):
        """A confirm of None is "cannot verify": the run stays write-only."""
        c = _coord(hass)
        await _dispatch(hass, c, _zone(), valve_state="unavailable")

        run = await c._sc_find_run(2)
        assert const.RUN_LATENCY_MARGIN not in run
        assert const.RUN_VALVE_ON not in run


class TestTheValveOnReportIsClampedToTheDispatch:
    """RUN_VALVE_ON is the valve's own on report, never older than the dispatch.

    RUN_STARTED is stamped after the confirm poll returns, up to a poll after
    the water started. The valve's last_changed is closer, but a valve that was
    already open before the dispatch would drag the anchor back by however long
    it had been open, so the report is clamped to [dispatch, confirm return].
    """

    async def test_a_valve_already_open_is_anchored_at_the_dispatch(self, hass):
        started = dt_util.utcnow().replace(microsecond=0)
        with freeze_time(started):
            c = _coord(hass)
            zone = _zone()
            c._zones[2] = zone
            # on for an hour already: the confirm poll accepts it at first read
            hass.states.async_set(
                VALVE, "on", timestamp=(started - timedelta(hours=1)).timestamp()
            )
            await hass.async_block_till_done()

            assert await c.async_run_self_closing(zone, trigger="schedule")
            await hass.async_block_till_done()

        run = await c._sc_find_run(2)
        assert run[const.RUN_VALVE_ON] == started.isoformat()

    async def test_a_valve_reporting_on_after_the_dispatch_is_anchored_at_its_report(
        self, hass
    ):
        started = dt_util.utcnow().replace(microsecond=0)
        reported = started + timedelta(seconds=0.4)
        with freeze_time(started) as frozen:
            c = _coord(hass)
            zone = _zone()

            async def _slow_confirm(zone_id, entity_id, retry=True):
                # the valve reports on 0.4 s after the dispatch, and the poll
                # that sees it returns a whole second after the dispatch
                hass.states.async_set(entity_id, "on", timestamp=reported.timestamp())
                frozen.tick(timedelta(seconds=1))
                return True

            c._confirm_valve_running = AsyncMock(side_effect=_slow_confirm)
            await _dispatch(hass, c, zone, valve_state="off")

        run = await c._sc_find_run(2)
        assert run[const.RUN_VALVE_ON] == reported.isoformat()
        assert run[const.RUN_STARTED] == (started + timedelta(seconds=1)).isoformat()

    async def test_a_report_stamped_after_the_confirm_returned_is_clamped_to_it(
        self, hass
    ):
        started = dt_util.utcnow().replace(microsecond=0)
        with freeze_time(started) as frozen:
            c = _coord(hass)
            zone = _zone()

            async def _skewed_confirm(zone_id, entity_id, retry=True):
                stamp = (started + timedelta(seconds=5)).timestamp()
                hass.states.async_set(entity_id, "on", timestamp=stamp)
                frozen.tick(timedelta(seconds=1))
                return True

            c._confirm_valve_running = AsyncMock(side_effect=_skewed_confirm)
            await _dispatch(hass, c, zone, valve_state="off")

        run = await c._sc_find_run(2)
        assert run[const.RUN_VALVE_ON] == (started + timedelta(seconds=1)).isoformat()


class TestTheBackstopWaitsOnlyForAConfirmedValve:
    async def test_a_margin_of_zero_still_waits_out_the_debounce(self, hass):
        c = _coord(hass)
        await _dispatch(hass, c, _zone(**{const.ZONE_LATENCY_MARGIN: 0}))

        assert c._sc_schedule_cleanup.call_args.args == (2, 605)

    async def test_a_write_only_run_is_backstopped_at_exactly_its_window(self, hass):
        c = _coord(hass)
        await _dispatch(hass, c, _zone(confirm=None))

        assert c._sc_schedule_cleanup.call_args.args == (2, 600)

    async def test_an_unverifiable_run_is_backstopped_at_exactly_its_window(self, hass):
        c = _coord(hass)
        await _dispatch(hass, c, _zone(), valve_state="unavailable")

        assert c._sc_schedule_cleanup.call_args.args == (2, 600)


class TestTheWatcherNeverWritesAWateringRunOff:
```

Warum die Zeit-Tests so gebaut sind: `freeze_time(started)` macht `dispatched_at` und
`confirmed_at` exakt; `started` ohne Mikrosekunden hält die ISO-Vergleiche lesbar. Das „vorher
offene“ Ventil bekommt seinen alten `last_changed` über `hass.states.async_set(..., timestamp=...)`
(Signatur HA 2024.12.5) und wird OHNE `_dispatch` gesetzt, weil `_dispatch` den Zustand erneut
schreiben würde. Für die späte Meldung ersetzt ein `AsyncMock` den Confirm: er setzt „on“ mit
Zeitstempel Dispatch + 0,4 s und stellt die eingefrorene Uhr um 1 s vor, bevor er `True` liefert —
so liegen Meldung (0,4 s) und Confirm-Rückkehr (1 s) sicher auseinander. Keine echten Timer
(`_sc_schedule_cleanup` bleibt Mock), daher kein Lingering-Timer-Risiko.

- [ ] **Step 2: Tests laufen lassen, Fehlschlag bestätigen**

```bash
cd /d/Entwicklung/HASI/HAsmartirrigation
mkdir -p D:/Entwicklung/HASI/pr139-work/tmp D:/Entwicklung/HASI/pr139-work/npm-cache && export TEMP=D:/Entwicklung/HASI/pr139-work/tmp TMP=D:/Entwicklung/HASI/pr139-work/tmp TMPDIR=D:/Entwicklung/HASI/pr139-work/tmp npm_config_cache=D:/Entwicklung/HASI/pr139-work/npm-cache
./.venv/Scripts/python.exe -m pytest tests/test_service_watch.py -p _local_socket_unblock -q -k "armed_once or FreezesItsMargin or ClampedToTheDispatch or WaitsOnlyForAConfirmedValve"
```

Erwartet (real beobachtet; die vier grünen sind die write-only/nicht-prüfbar-Pins, die heute schon
gelten und nach dem Umbau gelten müssen):

```
E   assert (2, 600.0) == (2, 609)
E   KeyError: 'latency_margin'
E   KeyError: 'latency_margin'
E   KeyError: 'valve_on'
E   KeyError: 'valve_on'
E   KeyError: 'valve_on'
E   assert (2, 600.0) == (2, 605)
FAILED tests/test_service_watch.py::TestAFullRunIsStillAFullRun::test_the_finish_backstop_is_armed_once
FAILED tests/test_service_watch.py::TestAConfirmedRunFreezesItsMarginAtDispatch::test_the_default_margin_is_frozen_into_the_record
FAILED tests/test_service_watch.py::TestAConfirmedRunFreezesItsMarginAtDispatch::test_the_zones_own_margin_is_frozen_into_the_record
FAILED tests/test_service_watch.py::TestTheValveOnReportIsClampedToTheDispatch::test_a_valve_already_open_is_anchored_at_the_dispatch
FAILED tests/test_service_watch.py::TestTheValveOnReportIsClampedToTheDispatch::test_a_valve_reporting_on_after_the_dispatch_is_anchored_at_its_report
FAILED tests/test_service_watch.py::TestTheValveOnReportIsClampedToTheDispatch::test_a_report_stamped_after_the_confirm_returned_is_clamped_to_it
FAILED tests/test_service_watch.py::TestTheBackstopWaitsOnlyForAConfirmedValve::test_a_margin_of_zero_still_waits_out_the_debounce
================= 7 failed, 4 passed, 16 deselected in 2.16s ==================
```

- [ ] **Step 3: `self_closing.py` — Importe aus `.run_watch`**

Vorher:

```python
from .run_watch import (
    WatchPolicy,
    register_watch_policy,
    run_credit_ceiling,
    run_is_queue_bound,
    run_is_segmented,
)
```

Nachher:

```python
from .run_watch import (
    WatchPolicy,
    register_watch_policy,
    run_credit_ceiling,
    run_finish_grace_seconds,
    run_is_queue_bound,
    run_is_segmented,
    zone_latency_margin,
)
```

- [ ] **Step 4: `self_closing.py` — Helfer `_sc_valve_on_instant`**

Direkt nach `_sc_schedule_cleanup`, vor `async_run_self_closing`:

Vorher:

```python
        self._sc_cancel_cleanup(zone_id)
        self._sc_cleanup_timers()[zone_id] = async_call_later(
            self.hass, max(0.0, delay_seconds), _done
        )

    async def async_run_self_closing(
```

Nachher:

```python
        self._sc_cancel_cleanup(zone_id)
        self._sc_cleanup_timers()[zone_id] = async_call_later(
            self.hass, max(0.0, delay_seconds), _done
        )

    def _sc_valve_on_instant(self, entity_id, lower, upper) -> str:
        """The instant a confirmed valve reported itself on, as ISO-8601 UTC.

        Its state's last_changed, clamped to [lower, upper] = [dispatch, confirm
        return] (#139). RUN_STARTED is stamped after the confirm poll returns, up
        to a poll later than the water, so measuring the valve window from it
        would shorten every run by that poll. But last_changed alone is not safe
        either: _confirm_valve_running accepts a valve that was ALREADY on at its
        first read, whose last_changed can be hours old, and a report can never
        precede the command that caused it. Without a state (nothing to read) the
        confirm return is the only instant known to be on.
        """
        state = self.hass.states.get(entity_id)
        reported = state.last_changed if state else upper
        return min(max(reported, lower), upper).isoformat()

    async def async_run_self_closing(
```

- [ ] **Step 5: `self_closing.py` — `dispatched_at` unmittelbar vor dem Öffnen**

Vorher:

```python
        await self.async_master_acquire(self._sc_master_token(zone_id))

        await self._sc_dispatch_open(zone)
```

Nachher:

```python
        await self.async_master_acquire(self._sc_master_token(zone_id))

        # The earliest instant the valve can have opened BECAUSE of this run: the
        # lower bound of RUN_VALVE_ON (#139). Taken immediately before the open
        # is fired, so a valve that was already on before the dispatch is
        # anchored here and not at its hours-old last_changed.
        dispatched_at = dt_util.utcnow()
        await self._sc_dispatch_open(zone)
```

- [ ] **Step 6: `self_closing.py` — `confirmed_at` direkt nach der Confirm-Abfrage**

Vorher:

```python
            confirmed = (
                await self._confirm_valve_running(zone_id, confirm_target, retry=False)
                if confirm_target
                else None
            )
            if confirmed is False:
```

Nachher:

```python
            confirmed = (
                await self._confirm_valve_running(zone_id, confirm_target, retry=False)
                if confirm_target
                else None
            )
            # The upper bound of RUN_VALVE_ON (#139): the poll that saw the valve
            # on has just returned, so it cannot have reported on any later.
            # Stamped here and not at RUN_STARTED below, which follows the bucket
            # write and is later still. _confirm_valve_running keeps its boolean
            # return: three other callers compare it with `is False`.
            confirmed_at = dt_util.utcnow()
            if confirmed is False:
```

- [ ] **Step 7: `self_closing.py` — Marge und Ventil-Ein nur in den bestätigten Datensatz**

Vorher:

```python
            elif confirmed:
                # A service valve confirmed open is observable for the rest of its
                # run: persisted so a restart can re-adopt the subscription rather
                # than fall back to the clock. Only when it was actually confirmed
                # — a write-only run (no confirm_entity) has nothing to watch, and
                # the hardware still owns its close.
                record[const.RUN_WATCH_ENTITY] = confirm_target
            await self._sc_add_run(record)
```

Nachher:

```python
            elif confirmed:
                # A service valve confirmed open is observable for the rest of its
                # run: persisted so a restart can re-adopt the subscription rather
                # than fall back to the clock. Only when it was actually confirmed
                # — a write-only run (no confirm_entity) has nothing to watch, and
                # the hardware still owns its close.
                record[const.RUN_WATCH_ENTITY] = confirm_target
                # And the two things its finish is settled on (#139): the zone's
                # latency margin, frozen so a margin edited mid-run cannot move a
                # backstop that is already armed (and whose presence is what gives
                # this record a finish grace at all), and the valve's own on
                # report, the anchor of the window actual_s is measured over. Only
                # here: a write-only or unverifiable run has no valve reports, so
                # it keeps the backstop at exactly its window, as before.
                record[const.RUN_LATENCY_MARGIN] = zone_latency_margin(zone)
                record[const.RUN_VALVE_ON] = self._sc_valve_on_instant(
                    confirm_target, dispatched_at, confirmed_at
                )
            await self._sc_add_run(record)
```

- [ ] **Step 8: `self_closing.py` — Backstop wartet die Wartezeit des Datensatzes ab**

Vorher:

```python
            else:
                # The backstop is armed FIRST and stays the mode's own: the valve
                # is already open and its window already running, so the watcher
                # below must not re-arm it (WatchPolicy.opens_at_dispatch).
                self._sc_schedule_cleanup(zone_id, planned_seconds)
                if confirmed:
```

Nachher:

```python
            else:
                # The backstop is armed FIRST and stays the mode's own: the valve
                # is already open and its window already running, so the watcher
                # below must not re-arm it (WatchPolicy.opens_at_dispatch).
                #
                # For a confirmed run it waits the finish grace past the window:
                # the debounce plus the frozen latency margin (#139). Armed at
                # exactly the window it fired before the valve's off report on
                # every normal run (measured 2-3 s late on Tuya valves) or inside
                # the debounce, cancelling the watcher, so the run was never
                # settled on what the valve did. Added HERE and not inside
                # _sc_schedule_cleanup, which batch and OpenSprinkler share; a
                # record without the margin gets 0 and the window as before.
                self._sc_schedule_cleanup(
                    zone_id, planned_seconds + run_finish_grace_seconds(record)
                )
                if confirmed:
```

Der Backstop liest die Wartezeit aus dem DATENSATZ (`run_finish_grace_seconds(record)`), nicht aus
der Zone: bei nicht prüfbarem Confirm (`None`) hat die Zone zwar ein `confirm_entity`, der
Datensatz aber weder `RUN_WATCH_ENTITY` noch `RUN_LATENCY_MARGIN` — er bleibt bei `(2, 600)`.

- [ ] **Step 9: Tests grün**

```bash
cd /d/Entwicklung/HASI/HAsmartirrigation
mkdir -p D:/Entwicklung/HASI/pr139-work/tmp D:/Entwicklung/HASI/pr139-work/npm-cache && export TEMP=D:/Entwicklung/HASI/pr139-work/tmp TMP=D:/Entwicklung/HASI/pr139-work/tmp TMPDIR=D:/Entwicklung/HASI/pr139-work/tmp npm_config_cache=D:/Entwicklung/HASI/pr139-work/npm-cache
./.venv/Scripts/python.exe -m pytest tests/test_service_watch.py -p _local_socket_unblock -q -k "armed_once or FreezesItsMargin or ClampedToTheDispatch or WaitsOnlyForAConfirmedValve"
```

Erwartet (real beobachtet):

```
====================== 11 passed, 16 deselected in 1.31s ======================
```

- [ ] **Step 10: Lint**

```bash
cd /d/Entwicklung/HASI/HAsmartirrigation
uvx black custom_components/irrigation_plus/
uvx ruff check custom_components/irrigation_plus/
```

Erwartet (real beobachtet):

```
67 files left unchanged.
All checks passed!
```

Die Testdatei liegt außerhalb des CI-Lint-Umfangs; zusätzlich `uvx black tests/test_service_watch.py`
(real: `1 file reformatted.` — drei Testsignaturen auf eine Zeile gezogen; Step 1 zeigt bereits die
formatierte Fassung; `uvx black --check tests/test_service_watch.py` meldet danach real
`1 file would be left unchanged.`).

- [ ] **Step 11: Verwandte Suiten**

```bash
cd /d/Entwicklung/HASI/HAsmartirrigation
mkdir -p D:/Entwicklung/HASI/pr139-work/tmp D:/Entwicklung/HASI/pr139-work/npm-cache && export TEMP=D:/Entwicklung/HASI/pr139-work/tmp TMP=D:/Entwicklung/HASI/pr139-work/tmp TMPDIR=D:/Entwicklung/HASI/pr139-work/tmp npm_config_cache=D:/Entwicklung/HASI/pr139-work/npm-cache
./.venv/Scripts/python.exe -m pytest tests/test_service_watch.py tests/test_self_closing.py tests/test_credit_ceiling.py tests/test_master.py tests/test_service_chain.py tests/test_run_in_flight.py tests/test_finish_anchor_hardware_window.py tests/test_observed_watering.py -p _local_socket_unblock -q
```

Erwartet (real beobachtet):

```
======================= 230 passed, 4 errors in 16.81s ========================
```

Am Elternstand (Task 2) in denselben Dateien: `220 passed, 4 errors`. 230 = 220 + 10 neue
Tests (der angepasste Pin zählt in beiden). Die 4 Errors sind `Lingering timer` beim Teardown
(lokale HA 2024.12.5) und in beiden Läufen zeilengleich (`diff` der sortierten `ERROR`-Zeilen leer):

```
ERROR tests/test_finish_anchor_hardware_window.py::TestTheAnchorAndTheBatchQueueBookTheSameSeconds::test_a_fractional_seconds_batch_zone_is_anchored_at_what_it_books
ERROR tests/test_finish_anchor_hardware_window.py::TestTheAnchorAndTheBatchQueueBookTheSameSeconds::test_a_minutes_unit_batch_zone_is_anchored_at_what_the_queue_books
ERROR tests/test_service_chain.py::TestRotatingSlicesThem::test_absorption_holds_a_zone_back_from_its_next_slot
ERROR tests/test_service_watch.py::TestOneOffSampleIsNotEvidenceTheWaterStopped::test_the_run_is_not_settled_before_the_window_is_out
```

Die write-only-Pins in `tests/test_self_closing.py` bleiben unverändert grün:
`test_run_credits_bucket_persists_and_fires_started` `(2, 600.0)`,
`test_resume_finalises_overdue_and_reschedules_partial` `(2, 500.0)`,
`test_a_rounded_up_minute_run_is_recorded_and_backstopped_at_the_real_window` `(2, 300.0)`,
`test_a_seconds_unit_zone_is_untouched` `(2, 263.0)` — ihre Zonen haben kein `confirm_entity`. Der
`_coord` dort hat `hass.states.get → None`, mit dem `_sc_valve_on_instant` auf die Confirm-Rückkehr
fällt (kein `TypeError` gegen einen Mock-Zustand).

- [ ] **Step 12: Mutationsprobe**

Verfahren aus Task 0, Step 5: `mutate.py`, Suchtexte mit `\n`, Sicherung
`D:/Entwicklung/HASI/pr139-work/mut/t03-<probe>.bak` für `custom_components/irrigation_plus/self_closing.py`,
nach jeder Probe Wiederherstellung aus der `.bak` und SHA-256-Prüfung (Pflicht), `git diff --stat` wie vor
der Probe. Lauf je Probe: das `-k` aus der Tabelle auf `tests/test_service_watch.py`. Suchtext → Ersatz steht
je Probe wörtlich in der Tabelle; jeder Suchtext kommt am Commit dieses Tasks genau einmal vor.
`backstop-grace-from-zone` besteht aus zwei Ersetzungen nacheinander (eine Sicherung vor der ersten).

| Probe | Mutation in `self_closing.py` (Suchtext → Ersatz) | `-k` | Beobachtet |
|---|---|---|---|
| margin-record | `                record[const.RUN_LATENCY_MARGIN] = zone_latency_margin(zone)\n` → leer | `armed_once or default_margin_is_frozen or zones_own_margin or margin_of_zero` | FAIL (4) `assert (2, 600.0) == (2, 609)`, `KeyError: 'latency_margin'` (2×), `assert (2, 600.0) == (2, 605)` |
| margin-default | `record[const.RUN_LATENCY_MARGIN] = zone_latency_margin(zone)` → `record[const.RUN_LATENCY_MARGIN] = const.DEFAULT_LATENCY_MARGIN_SECONDS` | `zones_own_margin or margin_of_zero` | FAIL (2) `assert 4 == 7`, `assert (2, 609.0) == (2, 605)` |
| valve-on-record | `                record[const.RUN_VALVE_ON] = self._sc_valve_on_instant(\n                    confirm_target, dispatched_at, confirmed_at\n                )\n` → leer | `ClampedToTheDispatch` | FAIL (3) `KeyError: 'valve_on'` |
| clamp-lower | `min(max(reported, lower), upper)` → `min(reported, upper)` | `ClampedToTheDispatch` | FAIL (1: `already_open`) `'…T17:24:06+00:00' == '…T18:24:06+00:00'` |
| clamp-upper | `min(max(reported, lower), upper)` → `max(reported, lower)` | `ClampedToTheDispatch` | FAIL (1: `stamped_after_the_confirm`) `'…18:24:20+00:00' == '…18:24:16+00:00'` |
| report-ignored | `reported = state.last_changed if state else upper` → `reported = upper` | `ClampedToTheDispatch` | FAIL (1: `reporting_on_after`) `'…18:24:25+00:00' == '…400000+00:00'` |
| lower-is-confirm-return | `confirm_target, dispatched_at, confirmed_at` → `confirm_target, confirmed_at, confirmed_at` | `ClampedToTheDispatch` | FAIL (1: `reporting_on_after`) `'…18:24:33+00:00' == '…400000+00:00'` |
| upper-is-dispatch | `confirm_target, dispatched_at, confirmed_at` → `confirm_target, dispatched_at, dispatched_at` | `ClampedToTheDispatch` | FAIL (2: `reporting_on_after`, `stamped_after_the_confirm`) `'…18:24:41+00:00' == '…41.400000+00:00'` |
| backstop-no-grace | `planned_seconds + run_finish_grace_seconds(record)` → `planned_seconds` | `armed_once or WaitsOnlyForAConfirmedValve` | FAIL (2) `assert (2, 600.0) == (2, 609)`, `assert (2, 600.0) == (2, 605)` |
| backstop-grace-from-zone | 1. `planned_seconds + run_finish_grace_seconds(record)` → `planned_seconds + zone_finish_grace_seconds(zone)`; 2. im Importblock `    run_finish_grace_seconds,\n` → `    run_finish_grace_seconds,\n    zone_finish_grace_seconds,\n` (Task 3 importiert `zone_finish_grace_seconds` noch nicht) | `armed_once or WaitsOnlyForAConfirmedValve` | FAIL (1: `unverifiable_run_is_backstopped`) `assert (2, 609.0) == (2, 600)` |
| backstop-grace-always | `planned_seconds + run_finish_grace_seconds(record)` → `planned_seconds + const.SERVICE_WATCH_SETTLE_SECONDS + zone_latency_margin(zone)` | `armed_once or WaitsOnlyForAConfirmedValve` | FAIL (2: write-only, unverifiable) `assert (2, 609.0) == (2, 600)` |
| margin-for-every-record | `            await self._sc_add_run(record)\n` → `            record[const.RUN_LATENCY_MARGIN] = zone_latency_margin(zone)\n            await self._sc_add_run(record)\n` (Marge unbedingt vor dem Speichern) | `FreezesItsMargin` | FAIL (2) `assert 'latency_margin' not in {…}` |
| valve-on-for-unverifiable | `            await self._sc_add_run(record)\n` → `            if confirm_target and not is_opensprinkler:\n                record[const.RUN_VALVE_ON] = self._sc_valve_on_instant(\n                    confirm_target, dispatched_at, confirmed_at\n                )\n            await self._sc_add_run(record)\n` | `FreezesItsMargin` | FAIL (1: `unverifiable_run_carries`) `assert 'valve_on' not in {…}` |

13 von 13 Proben gefangen (Revisionslauf 2026-09-15 auf dem Commit von Task 3); jeder neue Test und
der angepasste Pin scheitert an mindestens einer Probe. Die vier Proben mit mehrzeiligem Suchtext
(`valve-on-record`, `backstop-grace-from-zone`, `margin-for-every-record`, `valve-on-for-unverifiable`) liefen
im Feinschliff mit genau den Suchtexten der Tabelle erneut am Commit `dbbb42fd` (real): `3 failed, 24 deselected`
(`KeyError: 'valve_on'`), `1 failed, 3 passed, 23 deselected` (`assert (2, 609.0) == (2, 600)`),
`2 failed, 2 passed, 23 deselected` (`assert 'latency_margin' not in {…}`) und
`1 failed, 3 passed, 23 deselected` (`assert 'valve_on' not in {…}`), dieselben Tests wie in der Tabelle,
SHA-256 nach jeder Wiederherstellung gleich. SHA-256 von `self_closing.py` nach jeder
Wiederherstellung gleich dem Ausgangsstand; `git diff` vor und nach den Proben identisch (leer, der
Stand war committet). Die Proben der Observed-Sperre stehen in Task 3b.

- [ ] **Step 13: Commit**

```bash
cd /d/Entwicklung/HASI/HAsmartirrigation
git add custom_components/irrigation_plus/self_closing.py tests/test_service_watch.py
git commit -F - <<'EOF'
feat(service): wait out the finish grace before a confirmed run's backstop

The backstop of a confirmed service run was armed at exactly the planned
window, so it beat the valve's own off report on every normal run (Tuya
valves report their close 2-3 s late) or fired inside the 5 s debounce and
cancelled the watcher (#139). The run was never settled on what the valve
did.

At dispatch a confirmed run now freezes the zone's latency margin into its
record and stores the valve's own on report, clamped to [dispatch, confirm
return]: RUN_STARTED is stamped a poll later than the water, and a valve
that was already on would otherwise anchor hours back. The backstop waits
planned + settle + margin, derived from the record so a write-only or
unverifiable run keeps exactly its window, and the grace is added at the
service call site rather than in _sc_schedule_cleanup, which batch and
OpenSprinkler share.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
```

Erwartet (real beobachtet): `2 files changed, 191 insertions(+), 2 deletions(-)`.

**Neue Test-Helfer:** keine neuen Modul-Helfer. Wiederverwendbares Muster für spätere Tasks in
`tests/test_service_watch.py`: ein Confirm-Ersatz
`c._confirm_valve_running = AsyncMock(side_effect=...)`, der innerhalb eines
`freeze_time(started) as frozen`-Blocks den Ventilzustand mit
`hass.states.async_set(entity_id, "on", timestamp=...)` setzt und vor `return True` mit
`frozen.tick(timedelta(seconds=1))` die Uhr vorstellt — damit liegen `RUN_VALVE_ON` (Meldung) und
`RUN_STARTED` (Confirm-Rückkehr) in einem Test deterministisch auseinander.

---

### Task 3b: Die Observed-Sperre trägt die Wartezeit eines bestätigten Laufs

**Files** (Zeilen auf `0b418644`):
- Modify: `custom_components/irrigation_plus/self_closing.py:27-28, 484-487` (Import `zone_finish_grace_seconds` aus `.run_watch`; in `async_run_self_closing` der `_note_si_valve`-Aufruf nach dem Single-Flight-Block samt Kommentar)
- Test: `tests/test_service_watch.py` (neue Klasse `TestTheObservedLockoutCoversTheGrace` direkt nach `TestTheBackstopWaitsOnlyForAConfirmedValve` aus Task 3, vor `TestTheWatcherNeverWritesAWateringRunOff`)

Ziel: Ein bestätigter Service-Lauf bleibt ab Task 3/5 bis zur Aus-Meldung seines Ventils plus
Entprellung über das geplante Fenster hinaus in Flug. Die Observed-Sperre (`_note_si_valve`) endete
bisher am geplanten Fenster, der Beobachter hätte diesen Nachlauf als externen Lauf gutschreiben
können. Der Dispatch übergibt deshalb `planned_seconds + zone_finish_grace_seconds(zone)`. Bepreist aus
der ZONE, nicht aus dem Datensatz: die Sperre wird vor dem Confirm gesetzt, der Datensatz existiert
noch nicht. Ein Lauf, der danach unbestätigt bleibt, ist 9 s zu lang gesperrt; das unterdrückt nur
eine Beobachtung, die niemand machen kann.

Eigener Task (Nutzerentscheidung 2026-09-15), damit er auf #139 unabhängig von Task 3 gestrichen
werden kann. Das Streichen dieses einen Commits ist im Revisions-Probelauf geprüft (konfliktfrei, danach
`226 passed, 1 error` in den sieben Service-Suiten; Befehl und Zahlen in Task 13, Step 8). Kein späterer
Task darf deshalb `zone_finish_grace_seconds` in `self_closing.py` voraussetzen oder die Testklasse dieses
Tasks als Einfügeanker nehmen. `_note_si_valve` ist im `_coord` von `tests/test_service_watch.py` ein Mock: die Tests
prüfen das ARGUMENT des Dispatch, nicht die Sperrdauer. Die Sperrdauer rechnet die echte Methode
(`irrigation.py:115`, `_note_si_valve`) daraus als `run_seconds + SI_VALVE_SUPPRESS_MARGIN`
(`irrigation.py:129`; `irrigation.py:68`: `SI_VALVE_SUPPRESS_MARGIN = 30`, auf `0b418644` und am
Commit dieses Tasks gleich). Für die Default-Zone mit `confirm_entity` wird das Argument 600 → 609,
die Sperre also 630 s → 609 + 30 = 639 s. Eine write-only-Zone behält Argument 600 und damit
600 + 30 = 630 s.

- [ ] **Step 1: Fehlschlagende Tests schreiben**

In `tests/test_service_watch.py` direkt nach der Klasse `TestTheBackstopWaitsOnlyForAConfirmedValve`
(Task 3) einfügen. Keine neuen Importe. So, wie `black` die Datei formatiert:

Vorher:

```python
    async def test_an_unverifiable_run_is_backstopped_at_exactly_its_window(self, hass):
        c = _coord(hass)
        await _dispatch(hass, c, _zone(), valve_state="unavailable")

        assert c._sc_schedule_cleanup.call_args.args == (2, 600)


class TestTheWatcherNeverWritesAWateringRunOff:
```

Nachher:

```python
    async def test_an_unverifiable_run_is_backstopped_at_exactly_its_window(self, hass):
        c = _coord(hass)
        await _dispatch(hass, c, _zone(), valve_state="unavailable")

        assert c._sc_schedule_cleanup.call_args.args == (2, 600)


class TestTheObservedLockoutCoversTheGrace:
    """_note_si_valve runs before the confirm, so it prices the zone, not the run.

    A zone with a confirm_entity may hold its valve up to the finish grace past
    the window; the observer must not credit that tail as an external run. An
    unconfirmed run of such a zone is locked out 9 s too long, which is harmless.

    These tests pin the argument the dispatch passes, not the lockout's length:
    _note_si_valve is a Mock here. Inside the real _note_si_valve the argument
    planned + grace becomes planned + grace + SI_VALVE_SUPPRESS_MARGIN
    (609 + 30 = 639 s; irrigation.py SI_VALVE_SUPPRESS_MARGIN), and a write-only
    zone's 600 becomes 630 s.
    """

    async def test_a_zone_with_a_confirm_entity_is_locked_out_for_the_grace(self, hass):
        c = _coord(hass)
        await _dispatch(hass, c, _zone())

        c._note_si_valve.assert_called_once_with(2, 609)

    async def test_a_write_only_zone_is_locked_out_for_its_window_only(self, hass):
        c = _coord(hass)
        await _dispatch(hass, c, _zone(confirm=None))

        c._note_si_valve.assert_called_once_with(2, 600)


class TestTheWatcherNeverWritesAWateringRunOff:
```

- [ ] **Step 2: Tests laufen lassen, Fehlschlag bestätigen**

```bash
cd /d/Entwicklung/HASI/HAsmartirrigation
mkdir -p D:/Entwicklung/HASI/pr139-work/tmp D:/Entwicklung/HASI/pr139-work/npm-cache && export TEMP=D:/Entwicklung/HASI/pr139-work/tmp TMP=D:/Entwicklung/HASI/pr139-work/tmp TMPDIR=D:/Entwicklung/HASI/pr139-work/tmp npm_config_cache=D:/Entwicklung/HASI/pr139-work/npm-cache
./.venv/Scripts/python.exe -m pytest tests/test_service_watch.py -p _local_socket_unblock -q -k "ObservedLockout"
```

Erwartet (real beobachtet; der write-only-Pin gilt heute schon und muss nach dem Umbau gelten):

```
E   AssertionError: expected call not found.
E   Expected: mock(2, 609)
E   Actual: mock(2, 600.0)
FAILED tests/test_service_watch.py::TestTheObservedLockoutCoversTheGrace::test_a_zone_with_a_confirm_entity_is_locked_out_for_the_grace
================= 1 failed, 1 passed, 27 deselected in 1.64s ==================
```

- [ ] **Step 3: `self_closing.py` — Import aus `.run_watch`**

Vorher (Stand nach Task 3):

```python
from .run_watch import (
    WatchPolicy,
    register_watch_policy,
    run_credit_ceiling,
    run_finish_grace_seconds,
    run_is_queue_bound,
    run_is_segmented,
    zone_latency_margin,
)
```

Nachher:

```python
from .run_watch import (
    WatchPolicy,
    register_watch_policy,
    run_credit_ceiling,
    run_finish_grace_seconds,
    run_is_queue_bound,
    run_is_segmented,
    zone_finish_grace_seconds,
    zone_latency_margin,
)
```

- [ ] **Step 4: `self_closing.py` — Observed-Sperre trägt die Wartezeit der Zone**

In `async_run_self_closing`, nach dem Single-Flight-Block:

Vorher:

```python
        # Observed-watering (opt-in) may watch this zone's observed_entity, which
        # our own run_service opens. Mark the run window as SI-driven so the
        # observer does not double-credit it (the run already credits the bucket).
        self._note_si_valve(int(zone.get(const.ZONE_ID)), planned_seconds)
```

Nachher:

```python
        # Observed-watering (opt-in) may watch this zone's observed_entity, which
        # our own run_service opens. Mark the run window as SI-driven so the
        # observer does not double-credit it (the run already credits the bucket).
        #
        # The window includes the finish grace a confirmed run may take past its
        # planned end (#139): the run stays in flight until its valve reports the
        # close plus the debounce, so a lockout that ended at the planned window
        # would let the observer credit that tail as an external run. Priced from
        # the ZONE, not the run, because the confirm has not happened yet; a run
        # that then turns out unconfirmed is locked out a few seconds too long,
        # which only suppresses an observation nothing could be making.
        self._note_si_valve(
            int(zone.get(const.ZONE_ID)),
            planned_seconds + zone_finish_grace_seconds(zone),
        )
```

- [ ] **Step 5: Tests grün**

```bash
cd /d/Entwicklung/HASI/HAsmartirrigation
mkdir -p D:/Entwicklung/HASI/pr139-work/tmp D:/Entwicklung/HASI/pr139-work/npm-cache && export TEMP=D:/Entwicklung/HASI/pr139-work/tmp TMP=D:/Entwicklung/HASI/pr139-work/tmp TMPDIR=D:/Entwicklung/HASI/pr139-work/tmp npm_config_cache=D:/Entwicklung/HASI/pr139-work/npm-cache
./.venv/Scripts/python.exe -m pytest tests/test_service_watch.py -p _local_socket_unblock -q -k "ObservedLockout"
```

Erwartet (real beobachtet):

```
====================== 2 passed, 27 deselected in 0.54s =======================
```

- [ ] **Step 6: Lint**

```bash
cd /d/Entwicklung/HASI/HAsmartirrigation
uvx black custom_components/irrigation_plus/
uvx ruff check custom_components/irrigation_plus/
uvx black --check tests/test_service_watch.py
```

Erwartet (real beobachtet):

```
67 files left unchanged.
All checks passed!
1 file would be left unchanged.
```

- [ ] **Step 7: Verwandte Suiten**

```bash
cd /d/Entwicklung/HASI/HAsmartirrigation
mkdir -p D:/Entwicklung/HASI/pr139-work/tmp D:/Entwicklung/HASI/pr139-work/npm-cache && export TEMP=D:/Entwicklung/HASI/pr139-work/tmp TMP=D:/Entwicklung/HASI/pr139-work/tmp TMPDIR=D:/Entwicklung/HASI/pr139-work/tmp npm_config_cache=D:/Entwicklung/HASI/pr139-work/npm-cache
./.venv/Scripts/python.exe -m pytest tests/test_service_watch.py tests/test_self_closing.py tests/test_credit_ceiling.py tests/test_master.py tests/test_service_chain.py tests/test_run_in_flight.py tests/test_finish_anchor_hardware_window.py tests/test_observed_watering.py -p _local_socket_unblock -q
```

Erwartet (real beobachtet):

```
======================= 232 passed, 4 errors in 16.59s ========================
```

Am Elternstand (Task 3) in denselben Dateien: `230 passed, 4 errors`. 232 = 230 + 2 neue Tests. Die
4 Errors sind in beiden Läufen dieselben `Lingering timer`-Teardowns (lokale HA 2024.12.5):

```
ERROR tests/test_service_watch.py::TestOneOffSampleIsNotEvidenceTheWaterStopped::test_the_run_is_not_settled_before_the_window_is_out
ERROR tests/test_service_chain.py::TestRotatingSlicesThem::test_absorption_holds_a_zone_back_from_its_next_slot
ERROR tests/test_finish_anchor_hardware_window.py::TestTheAnchorAndTheBatchQueueBookTheSameSeconds::test_a_minutes_unit_batch_zone_is_anchored_at_what_the_queue_books
ERROR tests/test_finish_anchor_hardware_window.py::TestTheAnchorAndTheBatchQueueBookTheSameSeconds::test_a_fractional_seconds_batch_zone_is_anchored_at_what_it_books
```

`tests/test_self_closing.py` hat keinen `_note_si_valve`-Pin; `tests/test_observed_watering.py` prüft
die Sperre über die echte Methode mit eigenen Fensterlängen und bleibt unverändert grün.

- [ ] **Step 8: Mutationsprobe**

Verfahren aus Task 0, Step 5: `mutate.py`, Suchtexte mit `\n`, Sicherung
`D:/Entwicklung/HASI/pr139-work/mut/t03b-<probe>.bak` für `custom_components/irrigation_plus/self_closing.py`,
nach jeder Probe Wiederherstellung aus der `.bak` und SHA-256-Prüfung (Pflicht), `git diff --stat` wie vor
der Probe. Lauf je Probe: `-k "ObservedLockout"` auf `tests/test_service_watch.py`. Suchtext aller drei
Proben ist `planned_seconds + zone_finish_grace_seconds(zone),` (am Commit dieses Tasks genau einmal), den
Ersatz nennt die Tabelle.

| Probe | Mutation in `self_closing.py` | Beobachtet |
|---|---|---|
| lockout-no-grace | `planned_seconds + zone_finish_grace_seconds(zone),` → `planned_seconds,` | FAIL (1: `confirm_entity_is_locked_out`) `Expected: mock(2, 609)` / `Actual: mock(2, 600.0)` |
| lockout-grace-always | → `planned_seconds + const.SERVICE_WATCH_SETTLE_SECONDS + zone_latency_margin(zone),` | FAIL (1: `write_only_zone`) `Expected: mock(2, 600)` / `Actual: mock(2, 609.0)` |
| lockout-grace-from-run-keys | → `planned_seconds + run_finish_grace_seconds(zone),` (Datensatz-Helfer auf die Zone: kein `RUN_WATCH_ENTITY` → 0) | FAIL (1: `confirm_entity_is_locked_out`) `Expected: mock(2, 609)` / `Actual: mock(2, 600.0)` |

3 von 3 Proben gefangen; jeder der beiden Tests scheitert an mindestens einer Probe. SHA-256 von
`self_closing.py` nach jeder Wiederherstellung gleich dem Ausgangsstand; `git diff` vor und nach den
Proben identisch.

- [ ] **Step 9: Commit**

```bash
cd /d/Entwicklung/HASI/HAsmartirrigation
git add custom_components/irrigation_plus/self_closing.py tests/test_service_watch.py
git commit -F - <<'EOF'
feat(service): keep the observed-watering lockout over a confirmed run's finish grace

A confirmed service run now stays in flight past its planned window until
its valve reports the close plus the debounce (#139). The observed-watering
lockout _note_si_valve still ended at the planned window, so the observer
could credit that tail as an external run on top of the run's own credit.

The dispatch now passes planned + zone_finish_grace_seconds(zone). Priced
from the zone, not the run record, because the confirm has not happened
yet when the lockout is set; a run that then turns out unconfirmed is
locked out a few seconds too long, which only suppresses an observation
nothing could be making.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
```

Erwartet (real beobachtet): `2 files changed, 40 insertions(+), 1 deletion(-)`.

---

### Task 4: Der Watcher zeichnet die Aus-Meldung des Ventils auf und löscht sie bei einem Blip

**Files** (Zeilen auf `0b418644`):
- Modify: `custom_components/irrigation_plus/run_watch.py:573-575, 576-577` (`_watch_state_changed` übergibt `previous_state=event.data.get("old_state")`; `_watch_evaluate` bekommt das Schlüsselwort `previous_state`), `:604-605` (Laufend-Zweig löscht `RUN_VALVE_OFF`), `:612-613` (Aus-Zweig zeichnet `RUN_VALVE_OFF` auf, nur nach einem laufenden Vorzustand)
- Test: `tests/test_service_watch.py` (neuer Modul-Helfer `_report` und neue Klasse `TestTheWatcherRecordsTheValvesOwnOffReport` direkt nach `TestOneOffSampleIsNotEvidenceTheWaterStopped`, vor `TestAWriteOnlyValveIsUntouched`)

Ziel: Das Ende des Ventil-Fensters, auf dem ein bestätigter Service-Lauf ab Task 5 abgerechnet
wird, landet als `RUN_VALVE_OFF` im Datensatz: die erste Aus-Meldung seit dem letzten „an“, aus
`state.last_changed` des Zustandsereignisses. Gelöscht wird es, sobald der Watcher das Ventil wieder
laufend sieht.

Aufgezeichnet wird nur aus einem Ereignis, dessen VORHERIGER Zustand laufend war (`on`/`open`/`opening`,
`RUNNING_STATES`), User-Entscheidung E6. Die Subscription reicht dazu `old_state` des Ereignisses als
`previous_state` an `_watch_evaluate` durch. Damit gilt wörtlich „erste Aus-Meldung, die direkt auf ein
an folgt“:
- nie aus der ersten Auswertung in `_watch_start` (kein Vorzustand; nach einem Neustart ist
  `last_changed` die Wiederkehr der Entität),
- nie aus `unavailable`/`unknown`/fehlend → `off`: nach einem Neustart melden die Zigbee-Ventile zuerst
  `unavailable`, und `last_changed` des folgenden `off` ist ebenfalls die Wiederkehr, nicht der Schluss,
- nie für Datensätze ohne Wartezeit (`run_has_finish_grace`, also ohne `RUN_LATENCY_MARGIN`, Batch,
  OpenSprinkler).

Bewusst in Kauf genommen: `on → unavailable → off` mitten im Lauf speichert nichts; der Lauf wird dann
nach E4 von der Uhr begrenzt (`min(jetzt − Anker, planned)`, Task 5/8). 10 Tage Recorder auf der
gemessenen Anlage zeigen keine solche Episode während eines Laufs.

Die Entprellung selbst rechnet in diesem Task noch nach alter Formel ab (`_watch_finish`,
`elapsed + 1 >= planned`). Deshalb prüft jeder Test VOR dem Ablauf der 5 s und ruft danach `_settle`,
damit kein Timer liegen bleibt. `_sc_schedule_cleanup` bleibt in `_coord` ein Mock, echte Backstop-Timer
gibt es hier nicht.

- [ ] **Step 1: Fehlschlagende Tests schreiben**

In `tests/test_service_watch.py` zwischen dem Ende von `TestOneOffSampleIsNotEvidenceTheWaterStopped`
und `class TestAWriteOnlyValveIsUntouched:` einfügen. Keine neuen Importe (`timedelta`, `dt_util`,
`const` sind da). So, wie `black` die Datei formatiert:

Vorher:

```python
    async def test_a_valve_that_stays_off_still_ends_the_run(self, hass):
        """The debounce is a debounce, not a licence to ignore the valve."""
        c = _coord(hass)
        await _dispatch(hass, c, _zone())

        await _off(hass)

        assert await c._sc_find_run(2) is None


class TestAWriteOnlyValveIsUntouched:
```

Nachher:

```python
    async def test_a_valve_that_stays_off_still_ends_the_run(self, hass):
        """The debounce is a debounce, not a licence to ignore the valve."""
        c = _coord(hass)
        await _dispatch(hass, c, _zone())

        await _off(hass)

        assert await c._sc_find_run(2) is None


async def _report(hass, state, when, attributes=None):
    """The valve reports ``state``, stamped ``when`` (the state's last_changed)."""
    hass.states.async_set(VALVE, state, attributes, timestamp=when.timestamp())
    await hass.async_block_till_done()


class TestTheWatcherRecordsTheValvesOwnOffReport:
    """RUN_VALVE_OFF is the first off report since the last on (#139).

    Read off the event's state.last_changed rather than stamped when the
    watcher gets round to it: the evaluate runs as a task, a poll or more after
    the report, and every later off update of the same valve (an attribute
    refresh, a link-quality tick) is an event of its own that would move a
    clock-stamped value. Recorded only from an event whose previous state was
    running: an off that follows unavailable, unknown or no state the watcher
    saw carries the entity's return in its last_changed, not the close. Each
    test asserts before the debounce runs out: the report is recorded at the
    event, not when the run is settled.
    """

    async def test_an_off_event_records_the_states_last_changed(self, hass):
        c = _coord(hass)
        await _dispatch(hass, c, _zone())
        closed = dt_util.utcnow().replace(microsecond=0) + timedelta(seconds=2.5)

        await _report(hass, "off", closed)

        run = await c._sc_find_run(2)
        assert run[const.RUN_VALVE_OFF] == closed.isoformat()
        c._record_run.assert_not_awaited()
        await _settle(hass)

    async def test_an_attribute_only_update_does_not_move_the_off_report(self, hass):
        """HA keeps last_changed while the state text stays the same."""
        c = _coord(hass)
        await _dispatch(hass, c, _zone())
        closed = dt_util.utcnow().replace(microsecond=0) + timedelta(seconds=2.5)

        await _report(hass, "off", closed)
        await _report(hass, "off", closed + timedelta(seconds=3), {"linkquality": 42})

        state = hass.states.get(VALVE)
        assert state.last_changed == closed
        assert state.last_updated == closed + timedelta(seconds=3)
        run = await c._sc_find_run(2)
        assert run[const.RUN_VALVE_OFF] == closed.isoformat()
        await _settle(hass)

    async def test_an_off_after_an_unavailable_spell_keeps_the_first_off_report(
        self, hass
    ):
        """unavailable is no information, not an on: the valve closed at the first.

        The first off follows the on and is the close. The off after the spell
        follows unavailable, not a running state, and moves nothing.
        """
        c = _coord(hass)
        await _dispatch(hass, c, _zone())
        closed = dt_util.utcnow().replace(microsecond=0) + timedelta(seconds=2.5)

        await _report(hass, "off", closed)
        await _report(hass, "unavailable", closed + timedelta(seconds=1))
        await _report(hass, "off", closed + timedelta(seconds=2))

        assert hass.states.get(VALVE).last_changed == closed + timedelta(seconds=2)
        run = await c._sc_find_run(2)
        assert run[const.RUN_VALVE_OFF] == closed.isoformat()
        await _settle(hass)

    async def test_an_off_after_an_unavailable_mid_run_records_nothing(self, hass):
        """on -> unavailable -> off: the off does not follow a running state.

        Its last_changed is when the entity came back, which can be any time
        after the valve really closed. Nothing is recorded; the run is bounded
        by the clock instead (accepted trade-off, #139).
        """
        c = _coord(hass)
        await _dispatch(hass, c, _zone())
        now = dt_util.utcnow().replace(microsecond=0)

        await _report(hass, "unavailable", now + timedelta(seconds=1))
        await _report(hass, "off", now + timedelta(seconds=3))

        # the off was evaluated: the debounce is running
        assert c._watchers()[2].finish_cancel is not None
        run = await c._sc_find_run(2)
        assert not run.get(const.RUN_VALVE_OFF)
        await _settle(hass)

    async def test_an_on_inside_the_debounce_clears_the_off_report(self, hass):
        """A blip is not a close: the next off starts a fresh window end."""
        c = _coord(hass)
        await _dispatch(hass, c, _zone())
        closed = dt_util.utcnow().replace(microsecond=0) + timedelta(seconds=2.5)
        await _report(hass, "off", closed)
        assert (await c._sc_find_run(2))[const.RUN_VALVE_OFF] == closed.isoformat()

        await _report(hass, "on", closed + timedelta(seconds=1))

        run = await c._sc_find_run(2)
        assert run is not None
        assert not run.get(const.RUN_VALVE_OFF)
        await _settle(hass)
        assert await c._sc_find_run(2) is not None
        c._record_run.assert_not_awaited()

    async def test_a_re_adopted_run_does_not_record_the_initial_off(self, hass):
        """After a restart last_changed is the entity's return, not the close.

        The watcher re-adopting the run evaluates the valve once, and finds it
        off. That evaluation must not stamp RUN_VALVE_OFF: the state it reads
        was restored when the entity came back, so its last_changed can be any
        time after the real close.
        """
        c = _coord(hass)
        await _dispatch(hass, c, _zone())
        c._run_watchers = {}  # the subscription lived in memory only
        await _report(
            hass, "off", dt_util.utcnow().replace(microsecond=0) + timedelta(seconds=2)
        )

        await c.async_resume_self_closing_runs()
        await hass.async_block_till_done()

        # the initial evaluate did see the off: the debounce is running
        assert c._watchers()[2].finish_cancel is not None
        run = await c._sc_find_run(2)
        assert not run.get(const.RUN_VALVE_OFF)
        await _settle(hass)

    async def test_a_re_adopted_run_does_not_record_an_off_after_unavailable(
        self, hass
    ):
        """The valve is unavailable when the run is re-adopted, then reports off.

        After a restart a Zigbee valve comes back as unavailable first. The off
        that follows is the first report the new subscription sees, but its
        previous state is unavailable: its last_changed is the entity's return,
        not the close.
        """
        c = _coord(hass)
        await _dispatch(hass, c, _zone())
        c._watch_cancel(2)  # the subscription lived in memory only
        now = dt_util.utcnow().replace(microsecond=0)
        await _report(hass, "unavailable", now + timedelta(seconds=1))

        await c.async_resume_self_closing_runs()
        await hass.async_block_till_done()
        assert c._watchers()[2].finish_cancel is None  # unavailable: no information

        await _report(hass, "off", now + timedelta(seconds=3))

        # the off was evaluated: the debounce is running
        assert c._watchers()[2].finish_cancel is not None
        run = await c._sc_find_run(2)
        assert not run.get(const.RUN_VALVE_OFF)
        await _settle(hass)

    async def test_a_record_from_before_the_update_records_nothing(self, hass):
        """No frozen margin, no finish grace: the run keeps the timing it had."""
        c = _coord(hass)
        await _dispatch(hass, c, _zone())
        for record in c._cfg[const.CONF_ACTIVE_VALVE_RUNS]:
            del record[const.RUN_LATENCY_MARGIN]

        await _report(
            hass, "off", dt_util.utcnow().replace(microsecond=0) + timedelta(seconds=2)
        )

        assert c._watchers()[2].finish_cancel is not None
        run = await c._sc_find_run(2)
        assert const.RUN_LATENCY_MARGIN not in run
        assert not run.get(const.RUN_VALVE_OFF)
        await _settle(hass)


class TestAWriteOnlyValveIsUntouched:
```

Warum die Tests so gebaut sind:
- **`_report`** setzt den Zustand mit explizitem Zeitstempel (`hass.states.async_set(..., timestamp=...)`,
  Signatur HA 2024.12.5). Der Zeitstempel liegt 2,5 s neben der Wanduhr, so dass ein aus der Uhr
  gestempelter Wert sichtbar abweicht. HA übernimmt `last_changed`, solange der Zustandstext gleich bleibt
  (`homeassistant/core.py:2330` `last_changed = old_state.last_changed if same_state else None`); die
  beiden `state.last_changed`/`last_updated`-Zusicherungen im Attribut-Test belegen das in der
  Testumgebung. Jede Zustandsänderung über `hass.states.async_set` feuert `state_changed` mit `old_state`,
  also sieht die Subscription den Vorzustand genau wie im Betrieb.
- **Positiv-Tests** (`records_the_states_last_changed`, `attribute_only_update`, `unavailable_spell`,
  `inside_the_debounce_clears`): `_dispatch` setzt das Ventil vor dem Dispatch auf „on“, die erste
  Aus-Meldung folgt also direkt auf „on“ und wird aufgezeichnet.
- **Unavailable-Spell** (`on → off → unavailable → off`): Die erste Aus-Meldung folgt auf „on“ und bleibt.
  Die zweite folgt auf `unavailable` und verschiebt nichts. Unter der Vorzustands-Regel wäre sie schon
  ohne die Schutzbedingung „nur wenn noch nicht gesetzt“ wirkungslos; der Test bleibt als Pin, dass der
  Schluss eine Unterbrechung der Erreichbarkeit übersteht.
- **Neu: mitten im Lauf `on → unavailable → off`** (`unavailable_mid_run_records_nothing`): kein
  `RUN_VALVE_OFF`. `finish_cancel is not None` belegt, dass das `off` den Aus-Zweig wirklich erreicht hat
  (sonst wäre der Test leer grün).
- **Neuaufnahme, Ventil „aus“** (`re_adopted_run_does_not_record_the_initial_off`): leert
  `c._run_watchers`, BEVOR das Ventil auf „aus“ geht. Die alte Subscription bleibt zwar bei `hass`
  registriert, `_watch_state_changed` findet aber keinen Watcher mehr, also sieht nur die erste Auswertung
  in `_watch_start` das „aus“ (ohne Vorzustand).
- **Neu: Neuaufnahme, Ventil `unavailable`, dann „aus“** (`re_adopted_run_does_not_record_an_off_after_unavailable`):
  `c._watch_cancel(2)` baut Subscription und Watcher ab wie das Prozessende. Die erste Auswertung sieht
  `unavailable` (keine Information, keine Entprellung: `finish_cancel is None`), das folgende `off` kommt
  über die NEUE Subscription mit Vorzustand `unavailable` und zeichnet nichts auf. Das ist das
  Neustart-Muster der Z2M-Ventile auf HA-Prod.
- **„vor dem Update“** löscht `RUN_LATENCY_MARGIN` direkt im persistierten Datensatz in `c._cfg`, denn
  `_sc_active_runs` liefert dieselben Dict-Objekte.

Fixture-Namen: `VALVE = "binary_sensor.beet_valve"` und die Zone `Beet` stehen upstream schon in der
Datei (E7: bestehende Namen bleiben); die neuen Tests führen keine neuen Namen ein.

- [ ] **Step 2: Tests laufen lassen, Fehlschlag bestätigen**

```bash
cd /d/Entwicklung/HASI/HAsmartirrigation
mkdir -p D:/Entwicklung/HASI/pr139-work/tmp D:/Entwicklung/HASI/pr139-work/npm-cache && export TEMP=D:/Entwicklung/HASI/pr139-work/tmp TMP=D:/Entwicklung/HASI/pr139-work/tmp TMPDIR=D:/Entwicklung/HASI/pr139-work/tmp npm_config_cache=D:/Entwicklung/HASI/pr139-work/npm-cache
./.venv/Scripts/python.exe -m pytest tests/test_service_watch.py -p _local_socket_unblock -q -k TestTheWatcherRecordsTheValvesOwnOffReport
```

Erwartet (real beobachtet im Probelauf: Tests aus Step 1 auf dem Produktionsstand von Task 3b). Grün
sind die vier Negativ-Pins (Neuaufnahme „aus“, Neuaufnahme `unavailable` → „aus“, mitten im Lauf
`unavailable` → „aus“, „vor dem Update“), die heute schon gelten, weil noch nichts aufgezeichnet wird, und
nach dem Umbau gelten müssen. Die 4 Errors sind `Lingering timer` der Entprellung, weil die
fehlschlagende Zusicherung vor dem abschließenden `_settle` abbricht:

```
E   Failed: Lingering timer after job <Job call_later 5 HassJobType.Coroutinefunction <function RunWatchMixin._watch_defer_finish.<locals>._decide at 0x...>>
E   KeyError: 'valve_off'
E   KeyError: 'valve_off'
E   KeyError: 'valve_off'
E   KeyError: 'valve_off'
FAILED tests/test_service_watch.py::TestTheWatcherRecordsTheValvesOwnOffReport::test_an_off_event_records_the_states_last_changed
FAILED tests/test_service_watch.py::TestTheWatcherRecordsTheValvesOwnOffReport::test_an_attribute_only_update_does_not_move_the_off_report
FAILED tests/test_service_watch.py::TestTheWatcherRecordsTheValvesOwnOffReport::test_an_off_after_an_unavailable_spell_keeps_the_first_off_report
FAILED tests/test_service_watch.py::TestTheWatcherRecordsTheValvesOwnOffReport::test_an_on_inside_the_debounce_clears_the_off_report
============ 4 failed, 4 passed, 29 deselected, 4 errors in 2.57s =============
```

Dass die vier Negativ-Pins beißen, zeigen die Proben in Step 9 (`initial-evaluate-records`,
`running-condition-removed`, `unavailable-accepted`, `grace-gate-removed`). Gegen die erste Fassung dieses
Tasks (Schlüsselwort `observed_transition`, jedes Subscription-`off` zeichnet auf) scheitern die zwei
neuen Tests real mit `AssertionError: assert not '2026-09-15T18:44:50+00:00'` bzw. `...:51+00:00`.

- [ ] **Step 3: `run_watch.py` — Subscription reicht den Vorzustand durch, `_watch_evaluate` bekommt das Schlüsselwort**

Vorher:

```python
            self.hass.async_create_task(
                self._watch_evaluate(zone_id, event.data.get("new_state"))
            )

    async def _watch_evaluate(self, zone_id, state) -> None:
        """Advance a watched run from one observation of its entity."""
        zid = int(zone_id)
```

Nachher:

```python
            self.hass.async_create_task(
                self._watch_evaluate(
                    zone_id,
                    event.data.get("new_state"),
                    previous_state=event.data.get("old_state"),
                )
            )

    async def _watch_evaluate(self, zone_id, state, *, previous_state=None) -> None:
        """Advance a watched run from one observation of its entity.

        ``previous_state`` is the state ``state`` replaced, passed only by the
        subscription (the event's old_state). The one-off read in
        ``_watch_start`` and a mode's own re-evaluation of the current state
        leave it None: they did not see the entity move, so they cannot say
        what ``state`` followed or when the valve moved.
        """
        zid = int(zone_id)
```

Die übrigen Aufrufer bleiben ohne Schlüsselwort und damit bei `None`: `_watch_start` (erste Auswertung,
`run_watch.py:664`), `batch.py:611` (`await self._watch_evaluate(zone_id, self.hass.states.get(entity))`)
und `opensprinkler.py:603` `_os_evaluate` (`await self._watch_evaluate(zone_id, state)`). Batch und
OpenSprinkler haben ohnehin keine Wartezeit (`settles_on_valve_window=False`). `RUNNING_STATES` steht im
selben Modul (`run_watch.py:47`), kein Import nötig.

- [ ] **Step 4: `run_watch.py` — Laufend-Zweig löscht die Aus-Meldung**

In `_watch_evaluate`:

Vorher:

```python
        if running:
            if observed_start is None:
                await self._watch_observed_start(zid, run)
            elif policy.segmented and run.get(const.RUN_SEGMENT_STARTED) is None:
                # Watering again after a pause: open the next segment.
                await self._watch_resume(zid, run)
            return
```

Nachher:

```python
        if running:
            if observed_start is None:
                await self._watch_observed_start(zid, run)
            elif policy.segmented and run.get(const.RUN_SEGMENT_STARTED) is None:
                # Watering again after a pause: open the next segment.
                await self._watch_resume(zid, run)
            if policy.settles_on_valve_window and run.get(const.RUN_VALVE_OFF):
                # The valve is on again, so the off report it made was a blip
                # and not the close (#139). Dropped rather than kept: the run's
                # window ends at the first off AFTER this on, and a stale value
                # would survive the next off unchanged (it is only recorded
                # when unset) and cut the window short by the blip's distance
                # from the real end.
                await self._watch_update_run(zid, {const.RUN_VALVE_OFF: None})
            return
```

- [ ] **Step 5: `run_watch.py` — Aus-Zweig zeichnet die erste Aus-Meldung nach „an“ auf**

In `_watch_evaluate`, nach der Pausen-Prüfung und vor der Entprell-Verzögerung:

Vorher:

```python
        if observed_start is not None:
            if await self._watch_paused(zid, run):
                # A pause, not the end. The controller is holding the remaining
                # time; bank what has been delivered and wait.
                await self._watch_pause(zid, run)
                return
            # The zone stopped. The controller ended the run, on time or early;
            # either way it is over now — unless this mode's pause indicator may
            # simply not have caught up yet, in which case decide in a moment.
            delay = await self._watch_finish_delay(zid, run)
```

Nachher:

```python
        if observed_start is not None:
            if await self._watch_paused(zid, run):
                # A pause, not the end. The controller is holding the remaining
                # time; bank what has been delivered and wait.
                await self._watch_pause(zid, run)
                return
            if (
                previous_state is not None
                and previous_state.state in RUNNING_STATES
                and run_has_finish_grace(run)
                and not run.get(const.RUN_VALVE_OFF)
            ):
                # The end of the valve window this run is settled on (#139): the
                # first off report since the last on, taken from the state's
                # last_changed and never from the clock. This evaluate runs as a
                # task a moment after the report, and the debounce below decides
                # seconds later still; both would stretch the window by their
                # latency. last_changed is also stable against the reports that
                # follow: HA keeps it while the state text stays "off", so an
                # attribute-only update (which is a state_changed event of its
                # own and restarts the debounce) cannot move it, and a value
                # already stored is never overwritten.
                #
                # The close is the first off that directly follows a running
                # state, so only that event records it. Never the initial
                # evaluate (no previous state: a watcher re-adopted after a
                # restart reads a state restored when the entity came back), and
                # never unavailable/unknown/None -> off: after a restart Zigbee
                # valves come back as unavailable first, and the last_changed of
                # the off that follows is the entity's return, not the close.
                # Either would stretch the window by the downtime. Do not widen
                # this to "any off the subscription delivered". Accepted
                # trade-off: on -> unavailable -> off mid-run records nothing,
                # and that run is bounded by the clock (min(now - anchor,
                # planned)) like one whose valve closed while HA was down.
                run = (
                    await self._watch_update_run(
                        zid, {const.RUN_VALVE_OFF: state.last_changed.isoformat()}
                    )
                    or run
                )
            # The zone stopped. The controller ended the run, on time or early;
            # either way it is over now — unless this mode's pause indicator may
            # simply not have caught up yet, in which case decide in a moment.
            delay = await self._watch_finish_delay(zid, run)
```

`run_has_finish_grace` steht im selben Modul (Task 2), kein Import nötig. `or run` hält den Lauf
für `_watch_defer_finish`/`_watch_finish` gültig, falls der Datensatz zwischenzeitlich abgerechnet
wurde (`_watch_update_run` liefert dann `None`). Die Bedingung `not run.get(const.RUN_VALVE_OFF)` ist unter
der Vorzustands-Regel in sequenzieller Verarbeitung nicht mehr beobachtbar (ein zweites Aufzeichnen
bräuchte einen laufenden Zustand dazwischen, und der löscht in Step 4); sie bleibt als Absicherung, dass ein
gespeicherter Schluss nie überschrieben wird (Probe `first-off-guard-removed`, Step 9).

- [ ] **Step 6: Tests grün**

```bash
cd /d/Entwicklung/HASI/HAsmartirrigation
mkdir -p D:/Entwicklung/HASI/pr139-work/tmp D:/Entwicklung/HASI/pr139-work/npm-cache && export TEMP=D:/Entwicklung/HASI/pr139-work/tmp TMP=D:/Entwicklung/HASI/pr139-work/tmp TMPDIR=D:/Entwicklung/HASI/pr139-work/tmp npm_config_cache=D:/Entwicklung/HASI/pr139-work/npm-cache
./.venv/Scripts/python.exe -m pytest tests/test_service_watch.py -p _local_socket_unblock -q -k TestTheWatcherRecordsTheValvesOwnOffReport
```

Erwartet (real beobachtet, ohne Errors: jeder Test endet mit `_settle`):

```
====================== 8 passed, 29 deselected in 1.41s =======================
```

- [ ] **Step 7: Lint**

```bash
cd /d/Entwicklung/HASI/HAsmartirrigation
uvx black custom_components/irrigation_plus/
uvx ruff check custom_components/irrigation_plus/
uvx black --check tests/test_service_watch.py
```

Erwartet (real beobachtet):

```
All done! ✨ 🍰 ✨
67 files left unchanged.
All checks passed!
All done! ✨ 🍰 ✨
1 file would be left unchanged.
```

Die Testdatei liegt außerhalb des CI-Lint-Umfangs; Step 1 ist bereits die formatierte Fassung.

- [ ] **Step 8: Verwandte Suiten**

```bash
cd /d/Entwicklung/HASI/HAsmartirrigation
mkdir -p D:/Entwicklung/HASI/pr139-work/tmp D:/Entwicklung/HASI/pr139-work/npm-cache && export TEMP=D:/Entwicklung/HASI/pr139-work/tmp TMP=D:/Entwicklung/HASI/pr139-work/tmp TMPDIR=D:/Entwicklung/HASI/pr139-work/tmp npm_config_cache=D:/Entwicklung/HASI/pr139-work/npm-cache
./.venv/Scripts/python.exe -m pytest tests/test_service_watch.py tests/test_run_watch.py tests/test_batch.py tests/test_opensprinkler.py tests/test_run_segments.py -p _local_socket_unblock -q
```

Erwartet (real beobachtet):

```
======================= 195 passed, 52 errors in 17.24s =======================
```

Am Elternstand (Task 3b, Revisions-Probelauf `dry2` nach dem Feinschliff, Commit `99c9272d`) in denselben fünf Dateien: `187 passed, 52 errors in 16.12s`.
195 = 187 + 8 neue Tests. Die 52 Errors sind ausnahmslos `Failed: Lingering timer after job ...` beim
Teardown (lokale HA 2024.12.5): 38 in `tests/test_batch.py`, 13 in `tests/test_opensprinkler.py` und 1 in
`tests/test_service_watch.py`
(`TestOneOffSampleIsNotEvidenceTheWaterStopped::test_the_run_is_not_settled_before_the_window_is_out`).
Dazu kommen in beiden Läufen je 6 `ERROR`-Logzeilen `custom_components.irrigation_plus.batch: Batch
irrigation: zone 1 was handed to the controller but its run could not be recorded`, die aus einem
Batch-Test stammen und keine Test-IDs sind. Die sortierten `FAILED`/`ERROR`-Zeilen beider Läufe sind
identisch (`diff` leer), `FAILED` gibt es in keinem. Batch- und OpenSprinkler-Tests laufen unverändert
durch den geänderten `_watch_evaluate` (ihre Aufrufer übergeben kein `previous_state`, und ihre Datensätze
bestehen `run_has_finish_grace` nie).

Vergleichslauf am Elternstand: Block aus Task 0, Step 6 mit `P=$(git rev-parse HEAD)` (vor dem Commit
dieses Tasks = Commit von Task 3b) und
`FILES="tests/test_service_watch.py tests/test_run_watch.py tests/test_batch.py tests/test_opensprinkler.py tests/test_run_segments.py"`;
erwartet `FAILED-ERROR-same`.

- [ ] **Step 9: Mutationsprobe**

Verfahren aus Task 0, Step 5: `mutate.py`, Suchtexte mit `\n`, Sicherung
`D:/Entwicklung/HASI/pr139-work/mut/t04-<probe>.bak` für `custom_components/irrigation_plus/run_watch.py`,
nach jeder Probe Wiederherstellung aus der `.bak` und SHA-256-Prüfung (Pflicht), `git diff --stat` wie vor
der Probe. Lauf je Probe: `-k TestTheWatcherRecordsTheValvesOwnOffReport` auf `tests/test_service_watch.py`.
Suchtext → Ersatz steht je Probe in der Tabelle; jeder Suchtext kommt am Commit dieses Tasks genau einmal
vor. „Zeile `X` entfernt“ ist die ganze Zeile mit Einrückung und `\n`, Ersatz leer: 20 Leerzeichen vor
`previous_state=event.data.get("old_state"),`, 16 vor den `and …`-Zeilen des Aus-Zweigs.
`initial-evaluate-records` ersetzt
`                previous_state is not None\n                and previous_state.state in RUNNING_STATES\n` durch
`                (previous_state is None or previous_state.state in RUNNING_STATES)\n`;
`guard-removed-and-last-updated` wendet die Ersetzungen von `first-off-guard-removed` und `last-updated`
nacheinander an (eine Sicherung vor der ersten). Die `Lingering timer`-Errors unter einer Mutation kommen von
Tests, die vor ihrem `_settle` abbrechen.

| Probe | Mutation in `run_watch.py` | Beobachtet |
|---|---|---|
| previous-state-not-passed | `_watch_state_changed`: Zeile `previous_state=event.data.get("old_state"),` entfernt | FAIL (4: `records_the_states_last_changed`, `attribute_only_update`, `unavailable_spell`, `inside_the_debounce_clears`) `KeyError: 'valve_off'` — `4 failed, 4 passed, 29 deselected, 4 errors` |
| initial-evaluate-records | `previous_state is not None and previous_state.state in RUNNING_STATES` → `(previous_state is None or previous_state.state in RUNNING_STATES)` (erste Auswertung zeichnet auf) | FAIL (1: `re_adopted_run_does_not_record_the_initial_off`) `AssertionError: assert not '2026-09-15T18:52:45+00:00'` |
| clock-not-last-changed | `state.last_changed.isoformat()` → `dt_util.utcnow().isoformat()` | FAIL (4: dieselben wie previous-state-not-passed) `assert '2026-09-15T1....472689+00:00' == '2026-09-15T1....500000+00:00'` |
| grace-gate-removed | Zeile `and run_has_finish_grace(run)` entfernt | FAIL (1: `before_the_update_records_nothing`) `AssertionError: assert not '2026-09-15T18:53:07+00:00'` |
| running-condition-removed | Zeile `and previous_state.state in RUNNING_STATES` entfernt (jedes Subscription-`off` zeichnet auf, die Regel der ersten Fassung) | FAIL (2: `unavailable_mid_run_records_nothing`, `re_adopted_run_does_not_record_an_off_after_unavailable`) `AssertionError: assert not '2026-09-15T18:54:19+00:00'`, `...:54:21+00:00` — `2 failed, 6 passed, 29 deselected, 2 errors` |
| unavailable-accepted | `previous_state.state in RUNNING_STATES` → `previous_state.state in (*RUNNING_STATES, "unavailable")` | FAIL (2: dieselben) `AssertionError: assert not '2026-09-15T18:54:30+00:00'`, `...:54:31+00:00` |
| clear-removed | `await self._watch_update_run(zid, {const.RUN_VALVE_OFF: None})` → `pass` | FAIL (1: `inside_the_debounce_clears`) `AssertionError: assert not '2026-09-15T18:53:37.500000+00:00'` |
| clear-gated-on-segmented | `if policy.settles_on_valve_window and run.get(...)` → `if policy.segmented and run.get(...)` | FAIL (1: `inside_the_debounce_clears`) `AssertionError: assert not '2026-09-15T18:53:48.500000+00:00'` |
| first-off-guard-removed (**äquivalent geworden**) | Zeile `and not run.get(const.RUN_VALVE_OFF)` entfernt | `8 passed, 29 deselected`. Im ersten Probelauf (Regel `observed_transition`) fing `unavailable_spell` diese Probe; unter der Vorzustands-Regel ist sie äquivalent: das zweite `off` folgt auf `unavailable` und wird schon deshalb nicht aufgezeichnet, ein reines Attribut-Update folgt auf `off`. Ein erneutes Aufzeichnen bräuchte einen laufenden Zustand dazwischen, und der löscht `RUN_VALVE_OFF` im Laufend-Zweig. Die Schutzbedingung bleibt als Absicherung gegen Überschreiben |
| guard-removed-and-last-updated (**äquivalent geworden**) | beide: Schutzzeile entfernt UND `state.last_changed` → `state.last_updated` | `8 passed, 29 deselected`. Im ersten Probelauf gefangen (2); jetzt äquivalent aus demselben Grund: aufgezeichnet wird nur bei einem echten Zustandswechsel aus „laufend“, und dort setzt HA `last_changed == last_updated` |
| last-updated (äquivalent) | nur `state.last_changed` → `state.last_updated` | `8 passed, 29 deselected`. Äquivalent: bei einem echten Zustandswechsel gilt `last_changed == last_updated`, und nur ein solcher (aus „laufend“) zeichnet auf. `last_changed` bleibt, weil es die dokumentierte Bedeutung „Zeitpunkt des Zustandswechsels“ trägt |
| clear-policy-gate-removed (äquivalent) | `policy.settles_on_valve_window and` im Laufend-Zweig entfernt | `8 passed, 29 deselected`. Äquivalent: `RUN_VALVE_OFF` wird nur für Läufe mit Wartezeit geschrieben (`run_has_finish_grace` verlangt dieselbe Policy-Flagge), ein Datensatz ohne sie hat den Schlüssel nie. Das Tor bleibt als Absicherung, dass der Laufend-Zweig für Batch/OpenSprinkler keinen Schreibpfad bekommt |

8 von 8 nicht-äquivalenten Proben gefangen, 4 äquivalente mit Begründung (davon 2 durch E6 äquivalent
geworden). Jeder der 8 Tests scheitert an mindestens einer Probe:
- `records_the_states_last_changed`, `attribute_only_update`, `unavailable_spell`: previous-state-not-passed, clock-not-last-changed
- `unavailable_mid_run_records_nothing`, `re_adopted_run_does_not_record_an_off_after_unavailable`: running-condition-removed, unavailable-accepted
- `inside_the_debounce_clears`: previous-state-not-passed, clock-not-last-changed, clear-removed, clear-gated-on-segmented
- `re_adopted_run_does_not_record_the_initial_off`: initial-evaluate-records
- `before_the_update_records_nothing`: grace-gate-removed

Die Proben `running-condition-removed` und `unavailable-accepted` fangen zusätzlich den Neustart-Test von
Task 8 (`test_a_valve_back_from_unavailable_after_the_restart_is_bounded`, dort Step 7).

Nach allen Proben meldete jede Wiederherstellung `restored=True` (SHA-256 gleich dem Ausgangsstand), und die
MD5 von `git diff` im Probe-Worktree (abgekoppelt am damaligen Commit dieses Tasks `6aef25d3`, vor dem
E7-Umbenennen der Store-Fixture; er unterscheidet sich vom Endstand-Commit nach dem Feinschliff `adcb6fba` nur in
`tests/test_store_self_closing.py` sowie im Kommentar von `RUN_VALVE_OFF` in `const.py` und in den Testdaten von
`tests/test_finish_grace_helpers.py` (beide aus Task 2), `run_watch.py` und `tests/test_service_watch.py` sind identisch) war vor und nach den
Proben `d41d8cd98f00b204e9800998ecf8427e` (leer).

- [ ] **Step 10: Commit**

```bash
cd /d/Entwicklung/HASI/HAsmartirrigation
git add custom_components/irrigation_plus/run_watch.py tests/test_service_watch.py
git commit -F - <<'EOF'
feat(run-watch): record a confirmed valve's own off report

A confirmed service run is to be settled on the window its valve reported
itself open (#139), so the watcher now stores the end of that window: the
first off report since the last on, as RUN_VALVE_OFF.

It is read off the event state's last_changed, not stamped from the clock:
the evaluate runs as a task after the report and the debounce decides
seconds later, and HA keeps last_changed across attribute-only updates of
a valve that is already off, which are state_changed events of their own.
An on seen again inside the debounce clears it, so a blip cannot cut the
window short.

It is only recorded from an event whose previous state was running, which
the subscription now passes to _watch_evaluate as previous_state. The
initial evaluate of a watcher re-adopted after a restart has no previous
state, and an off that follows unavailable or unknown carries the entity's
return in its last_changed, not the close: Zigbee valves come back from a
restart as unavailable first. Accepted trade-off: on -> unavailable -> off
mid-run records nothing and that run is bounded by the clock. Records
without a finish grace (write-only, batch, OpenSprinkler, persisted before
the update) record nothing; the settle itself is unchanged here.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
```

Erwartet (real beobachtet, Revisions-Probelauf `dry2` nach dem Feinschliff, Commit `adcb6fba`): `2 files changed, 233 insertions(+), 3 deletions(-)`.

**Neue Test-Helfer:** in `tests/test_service_watch.py` der Modul-Helfer
`_report(hass, state, when, attributes=None)`. Er setzt `VALVE` auf `state` mit
`last_changed = when` (`hass.states.async_set(..., timestamp=when.timestamp())`) und wartet
`async_block_till_done`. Spätere Tasks (5-8) nutzen ihn, um eine Meldung zu einem exakten Zeitpunkt zu
erzeugen, ohne die Wanduhr einzufrieren. Ein aufgezeichnetes `RUN_VALVE_OFF` ist dann `when.isoformat()`,
sofern die Meldung direkt auf einen laufenden Zustand folgt.

---

### Task 5: Abschluss nimmt `actual_s` an, der Watcher rechnet nach dem Ventil-Fenster ab

**Files** (Zeilen auf `0b418644`):
- Modify: `custom_components/irrigation_plus/self_closing.py:332, 337-338, 385, 710, 717-718, 764` (`_sc_finish_run` bekommt `actual_s`; `async_stop_self_closing` bekommt `actual_s`, `elapsed` nimmt ihn vor der Uhr)
- Modify: `custom_components/irrigation_plus/run_watch.py:817-818, 821-822` (neue Methoden `_watch_valve_window` und `_watch_settle_by_window` in `RunWatchMixin` direkt vor `_watch_finish`; `_watch_finish` leitet Läufe mit Wartezeit dorthin)
- Test: `tests/test_service_watch.py` (Pin `test_a_valve_off_at_the_planned_end_completes` auf eine eingefrorene Uhr umgestellt; neue Modul-Helfer `_advance` und `_run_until_the_valve_closes` und neue Klasse `TestAConfirmedRunIsSettledOnItsValveWindow` direkt nach `TestTheWatcherRecordsTheValvesOwnOffReport`, vor `TestAWriteOnlyValveIsUntouched`)

Ziel: Ein bestätigter Service-Lauf mit eingefrorener Marge (`run_has_finish_grace`) wird nach dem
Fenster abgerechnet, das sein Ventil selbst gemeldet hat: `RUN_VALVE_OFF − RUN_VALVE_ON`
(`valve_window_seconds`, Task 2; `RUN_VALVE_OFF` zeichnet der Watcher seit Task 4 auf). Abgeschlossen,
wenn `Fenster + max(1, Marge) >= planned` (`run_completion_tolerance`), sonst Teil-Lauf, beide mit
`actual_s = Fenster`. Die 5-s-Entprellung entscheidet nur noch, OB der Lauf endete. `_sc_finish_run`
schreibt den übergebenen Wert als `actual_s`, Zeitvolumen und Kalibrierprobe bleiben bei `planned_s`
(ein Test pinnt beides). `async_stop_self_closing` nutzt ihn für `delivered_frac`, Zeitvolumen und
`actual_s`. Ohne Wert verhalten sich beide wie bisher. In diesem Task nur der Parameterpfad
(`elapsed = actual_s if actual_s is not None else self._sc_run_elapsed(run)`); der Zweig
`run_has_finish_grace` für den manuellen Stopp kommt in Task 7. Datensätze ohne Marge (Batch,
OpenSprinkler, Service-Datensätze von vor dem Update) behalten `elapsed + 1 >= planned`. Ein Pin hält
fest, dass ein Lauf ohne Aus-Meldung, weil sein „off“ auf `unavailable` folgte (E6, Task 4), von der Uhr
begrenzt wird: `min(jetzt − RUN_VALVE_ON, planned)` zum Entscheidungszeitpunkt.
`_sc_schedule_cleanup` bleibt in `_coord` ein Mock: geprüft wird der Watcher-Pfad, der echte Backstop
kommt in Task 6. Echt ist nur der Entprell-Timer, und jeder Test läuft ihn ab.

- [ ] **Step 1: Fehlschlagende Tests schreiben**

In `tests/test_service_watch.py` zwei Stellen ändern. Keine neuen Importe (`pytest`, `timedelta`,
`freeze_time`, `dt_util`, `async_fire_time_changed`, `const` sind da). So, wie `black` die Datei
formatiert.

**1a) Pin in `TestAFullRunIsStillAFullRun` auf eine eingefrorene Uhr umstellen**

Vorher:

```python
    async def test_a_valve_off_at_the_planned_end_completes(self, hass):
        c = _coord(hass)
        started = dt_util.utcnow()
        await _dispatch(hass, c, _zone())

        with freeze_time(started + timedelta(seconds=600)):
            await _off(hass)

        kw = c._record_run.await_args.kwargs
        assert kw["result"] == const.RUN_RESULT_COMPLETED
        assert kw["actual_s"] == kw["planned_s"] == 600
```

Nachher:

```python
    async def test_a_valve_off_at_the_planned_end_completes(self, hass):
        """Completed, and recorded for the window the valve reported (#139).

        actual_s is now the off report minus the on report rather than planned_s.
        The dispatch runs under the same frozen clock as the close, so the on
        report (clamped to the dispatch) is ``started`` exactly and a close at
        the planned end is a window of exactly 600 s.
        """
        c = _coord(hass)
        started = dt_util.utcnow().replace(microsecond=0)
        with freeze_time(started) as frozen:
            await _dispatch(hass, c, _zone())

            frozen.tick(timedelta(seconds=600))
            await _off(hass)

        kw = c._record_run.await_args.kwargs
        assert kw["result"] == const.RUN_RESULT_COMPLETED
        assert kw["actual_s"] == kw["planned_s"] == 600
```

Warum sich dieser Pin ändert, und nur sein Aufbau: Die Zusicherung bleibt die von upstream,
`actual_s == planned_s == 600` exakt. Bisher dispatchte der Test mit der echten Uhr und fror sie erst
für das „off“ ein. Ab diesem Task ist `actual_s` aber `RUN_VALVE_OFF − RUN_VALVE_ON`. `_dispatch` setzt
das Ventil vor dem Dispatch auf „on“, also wird `RUN_VALVE_ON` auf `dispatched_at` geklemmt (Task 3),
einige Millisekunden echter Uhr nach `started`. Das Fenster wäre 600 s minus diese Millisekunden und
der exakte Vergleich fiele. Deshalb laufen Dispatch, Schluss und Entprellung jetzt in EINEM
`freeze_time(started) as frozen`-Block (Muster `_run_until_the_valve_closes`, unten): `RUN_VALVE_ON`
ist exakt `started`, `frozen.tick(600)` stellt die Uhr auf den Schluss, das „off“ trägt
`last_changed = started + 600`, und der Entprell-Timer wird auf derselben eingefrorenen Uhr gestellt,
auf der `_settle` ihn feuert. `started` ohne Mikrosekunden, damit die ISO-Stempel glatt sind. Kein
`approx` nötig.

Geprüft und unverändert gültig:
- `test_the_run_is_recorded_for_what_it_actually_watered`: Aus bei +100 s, Fenster ≈ 100 s →
  `partial`, `90 <= actual_s <= 110` hält. Vorher kam derselbe Wert aus `_sc_run_elapsed`, weil
  `_settle` die eingefrorene Uhr nicht vorstellt.
- `test_the_optimistic_credit_is_reconciled_down`: Aus bei +300 s, Fenster ≈ 300 s →
  `delivered_frac` 0,5 → letzter Eimer `approx(-10.0, abs=0.01)` hält (Abweichung durch die
  Dispatch-Millisekunden: 20 mm · δ/600).

**1b) Neuer Helfer und neue Klasse**

Zwischen dem Ende von `TestTheWatcherRecordsTheValvesOwnOffReport` und
`class TestAWriteOnlyValveIsUntouched:` einfügen.

Vorher:

```python
        assert c._watchers()[2].finish_cancel is not None
        run = await c._sc_find_run(2)
        assert const.RUN_LATENCY_MARGIN not in run
        assert not run.get(const.RUN_VALVE_OFF)
        await _settle(hass)


class TestAWriteOnlyValveIsUntouched:
```

Nachher:

```python
        assert c._watchers()[2].finish_cancel is not None
        run = await c._sc_find_run(2)
        assert const.RUN_LATENCY_MARGIN not in run
        assert not run.get(const.RUN_VALVE_OFF)
        await _settle(hass)


async def _advance(hass, frozen, seconds):
    """Move the frozen clock on by ``seconds`` and fire every timer now due."""
    frozen.tick(timedelta(seconds=seconds))
    async_fire_time_changed(hass, dt_util.utcnow())
    await hass.async_block_till_done()


async def _run_until_the_valve_closes(hass, c, zone, closed_after, *, before=None):
    """Dispatch, report the valve off ``closed_after`` s later, run out the debounce.

    All under one frozen clock: RUN_VALVE_ON is then the dispatch instant
    exactly, and the debounce timer is armed on the clock it is advanced on.
    The clock stands AT the close when the off is reported (stamped with that
    instant explicitly) and is moved PAST the debounce before the timer fires,
    so a run measured when the decision is taken, rather than at the off
    report, comes out visibly longer. ``before`` runs after the dispatch and
    before the close.
    """
    started = dt_util.utcnow().replace(microsecond=0)
    with freeze_time(started) as frozen:
        await _dispatch(hass, c, zone)
        if before is not None:
            before()
        frozen.tick(timedelta(seconds=closed_after))
        await _report(hass, "off", started + timedelta(seconds=closed_after))
        await _advance(hass, frozen, const.SERVICE_WATCH_SETTLE_SECONDS + 1)


class TestAConfirmedRunIsSettledOnItsValveWindow:
    """The debounce decides WHETHER the run ended; the reports say how long (#139).

    actual_s is the valve's off report minus its on report, and a close within
    the zone's latency margin of the planned end still completes. Before, the
    elapsed time was read when the debounce expired, 5 s after the close, and a
    completed run discarded it for planned_s, so neither the late Tuya close nor
    an early one was ever recorded as what the valve did.
    """

    async def test_a_close_just_after_the_window_completes_on_the_reported_window(
        self, hass
    ):
        """The Beet valve: it reports its close 2-3 s after the planned end."""
        c = _coord(hass)

        await _run_until_the_valve_closes(hass, c, _zone(), 602)

        assert await c._sc_find_run(2) is None
        kw = c._record_run.await_args.kwargs
        assert kw["result"] == const.RUN_RESULT_COMPLETED
        assert kw["planned_s"] == 600
        assert kw["actual_s"] == pytest.approx(602, abs=0.01)  # not 608, not 600
        # Only the recorded duration moves: the timed volume and the calibration
        # sample stay on the window the run was credited and sized for.
        assert c._timed_volume_l.call_args.args[1] == 600
        c._flow_calibration_check.assert_awaited_once()
        assert c._flow_calibration_check.await_args.args[2] == 600

    async def test_a_close_inside_the_margin_completes_on_the_reported_window(
        self, hass
    ):
        """3 s short with the default 4 s margin: a normal end, not a stop."""
        c = _coord(hass)

        await _run_until_the_valve_closes(hass, c, _zone(), 597)

        kw = c._record_run.await_args.kwargs
        assert kw["result"] == const.RUN_RESULT_COMPLETED
        assert kw["actual_s"] == pytest.approx(597, abs=0.01)

    async def test_a_close_beyond_the_margin_is_a_partial_credited_for_its_window(
        self, hass
    ):
        c = _coord(hass)

        await _run_until_the_valve_closes(hass, c, _zone(), 590)

        kw = c._record_run.await_args.kwargs
        assert kw["result"] == const.RUN_RESULT_PARTIAL
        assert kw["actual_s"] == pytest.approx(590, abs=0.01)  # not 596
        # 20 mm credited at dispatch from -20 mm; 590 of 600 s were delivered
        written = [ck.args[1] for ck in c.async_write_watered_bucket.await_args_list]
        assert written[-1] == pytest.approx(-20 + 20 * 590 / 600, abs=0.001)

    async def test_a_margin_of_zero_still_tolerates_one_second(self, hass):
        """max(1, margin): the old one-second slack is the floor, not the margin."""
        c = _coord(hass)

        await _run_until_the_valve_closes(
            hass, c, _zone(**{const.ZONE_LATENCY_MARGIN: 0}), 599.5
        )

        kw = c._record_run.await_args.kwargs
        assert kw["result"] == const.RUN_RESULT_COMPLETED
        assert kw["actual_s"] == pytest.approx(599.5, abs=0.01)

    async def test_a_margin_of_zero_settles_a_close_beyond_that_second_as_partial(
        self, hass
    ):
        c = _coord(hass)

        await _run_until_the_valve_closes(
            hass, c, _zone(**{const.ZONE_LATENCY_MARGIN: 0}), 598.5
        )

        kw = c._record_run.await_args.kwargs
        assert kw["result"] == const.RUN_RESULT_PARTIAL
        assert kw["actual_s"] == pytest.approx(598.5, abs=0.01)

    async def test_an_off_after_an_unavailable_mid_run_settles_on_the_clock(self, hass):
        """on -> unavailable -> off mid-run: no off report, the clock bounds the run.

        The off at +302 s follows unavailable, so its last_changed is the
        entity's return and not the close, and nothing is recorded. The run is
        then settled like one whose valve closed while HA was down: the window
        is min(now - on report, planned), read when the debounce decides
        (+308 s), and not the 302 s a recorded off would have given.
        """
        c = _coord(hass)
        started = dt_util.utcnow().replace(microsecond=0)
        with freeze_time(started) as frozen:
            await _dispatch(hass, c, _zone())
            frozen.tick(timedelta(seconds=300))
            await _report(hass, "unavailable", started + timedelta(seconds=300))
            frozen.tick(timedelta(seconds=2))
            await _report(hass, "off", started + timedelta(seconds=302))

            run = await c._sc_find_run(2)
            assert not run.get(const.RUN_VALVE_OFF)
            valve_on = dt_util.parse_datetime(run[const.RUN_VALVE_ON])

            await _advance(hass, frozen, const.SERVICE_WATCH_SETTLE_SECONDS + 1)
            decided = dt_util.utcnow()

        assert await c._sc_find_run(2) is None
        kw = c._record_run.await_args.kwargs
        assert kw["result"] == const.RUN_RESULT_PARTIAL
        assert kw["actual_s"] == pytest.approx(
            (decided - valve_on).total_seconds(), abs=0.01
        )  # 308 s, not 302

    async def test_a_record_from_before_the_update_keeps_the_old_rule(self, hass):
        """No frozen margin: elapsed at the decision + 1 >= planned, planned_s kept.

        Closed at 593.5 s, so the debounce decides at 599.5 s. The old rule
        completes that with actual_s == planned_s; the window rule would have
        recorded 599.5 s, so this pins that such a record is not routed there.
        """
        c = _coord(hass)

        def _strip_the_new_keys():
            for record in c._cfg[const.CONF_ACTIVE_VALVE_RUNS]:
                del record[const.RUN_LATENCY_MARGIN]
                del record[const.RUN_VALVE_ON]

        await _run_until_the_valve_closes(
            hass, c, _zone(), 593.5, before=_strip_the_new_keys
        )

        assert await c._sc_find_run(2) is None
        kw = c._record_run.await_args.kwargs
        assert kw["result"] == const.RUN_RESULT_COMPLETED
        assert kw["actual_s"] == kw["planned_s"] == 600


class TestAWriteOnlyValveIsUntouched:
```

Warum die Tests so gebaut sind: Dispatch, Aus-Meldung und Entprellung laufen in EINEM
`freeze_time(started) as frozen`-Block. So ist `RUN_VALVE_ON` exakt `started` (Ventil „on“ vor dem
Dispatch → Klemmung auf `dispatched_at`), und der Entprell-Timer wird auf der Uhr gestellt, die danach
vorgestellt wird. Die Uhr steht bei der Aus-Meldung auf der Schlusszeit, die Meldung trägt diesen
Zeitstempel explizit (`_report`, Task 4). Vor dem Feuern wird die Uhr um 6 s über die Entprellung
hinaus gestellt. Eine Messung zum Entscheidungszeitpunkt ergäbe also sichtbar Schluss + 6 s (608 statt
602). Die Grenzfälle mit Marge 0 liegen je 0,5 s neben der Toleranzgrenze (599,5 + 1 ≥ 600 bzw.
598,5 + 1 < 600), exakt dank der eingefrorenen Uhr. Den Test „vor dem Update“ legt der Schluss bei
593,5 s so, dass alte Regel und Fensterregel sich unterscheiden: Entscheidung bei 599,5 s, alt →
`actual_s == 600`, über das Fenster (ohne `RUN_VALVE_OFF`: `min(jetzt − Anker, planned)` = 599,5)
wären es 599,5. Er löscht `RUN_LATENCY_MARGIN` und `RUN_VALVE_ON` direkt in `c._cfg`, so wie ein
Datensatz von vor dem Update aussieht. Jeder Test endet abgerechnet, kein Timer bleibt liegen.

Der Test `test_an_off_after_an_unavailable_mid_run_settles_on_the_clock` pinnt den in der Spec bewusst in
Kauf genommenen Fall (Nutzerentscheidung E6, Abschnitt `RUN_VALVE_OFF`): `on → unavailable → off` mitten im
Lauf. Er baut den Ablauf selbst im eingefrorenen Block, weil vor dem „off“ ein `unavailable` gemeldet werden
muss, und nutzt nur `_coord`, `_zone`, `_dispatch` (upstream), `_report` (Task 4) und `_advance` (dieser
Task), nichts aus Task 6 oder 7; beide bleiben streichbar. Das Ventil meldet bei +300 s `unavailable` und
bei +302 s `off`. Der Vorzustand dieses „off“ ist nicht laufend, also zeichnet der Watcher keine
Aus-Meldung auf (vor der Entprellung geprüft). `_advance` stellt die Uhr um 6 s weiter, die Entprellung
entscheidet bei +308 s. Ohne `RUN_VALVE_OFF` ist das Fenster `min(jetzt − RUN_VALVE_ON, planned)`, also
`partial` mit `actual_s` = Entscheidungszeitpunkt − `RUN_VALVE_ON` = 308 s: nicht 302 s (das wäre die
Meldung nach `unavailable` als Schluss) und nicht 600 s (nur der Plan als Grenze). `RUN_VALVE_ON` liest der
Test aus dem Datensatz, `decided` ist `dt_util.utcnow()` direkt nach `_advance` im selben Block.

Der Test „+602“ pinnt zusätzlich, dass nur die aufgezeichnete Dauer wandert: Das Zeitvolumen
(`_sc_finish_flow` ist in `_coord` ohne Messwert, also rechnet `_sc_finish_run` zeitbasiert) und die
Kalibrierprobe bekommen weiter `planned_s` = 600, nicht das Fenster 602. `_timed_volume_l` ruft auch
der Dispatch auf (mit 600); `call_args` ist der letzte Aufruf, also der aus `_sc_finish_run`.
`_flow_calibration_check` ruft nur `_sc_finish_run` auf, das dritte Positionsargument ist die Dauer.

Namen (Nutzerentscheidung E7): Die Klasse nutzt die Fixture-Zone `Beet` aus `_zone()`, die upstream
auf `0b418644` schon so heißt (`tests/test_service_watch.py:73`); daher der Docstring „The Beet
valve“. „Tuya“ ist eine Gerätemarke und steht upstream schon in derselben Datei
(`tests/test_service_watch.py:256`). Keine neuen Namen der realen Installation.

- [ ] **Step 2: Tests laufen lassen, Fehlschlag bestätigen**

```bash
cd /d/Entwicklung/HASI/HAsmartirrigation
mkdir -p D:/Entwicklung/HASI/pr139-work/tmp D:/Entwicklung/HASI/pr139-work/npm-cache && export TEMP=D:/Entwicklung/HASI/pr139-work/tmp TMP=D:/Entwicklung/HASI/pr139-work/tmp TMPDIR=D:/Entwicklung/HASI/pr139-work/tmp npm_config_cache=D:/Entwicklung/HASI/pr139-work/npm-cache
./.venv/Scripts/python.exe -m pytest tests/test_service_watch.py -p _local_socket_unblock -q -k "TestAConfirmedRunIsSettledOnItsValveWindow or test_a_valve_off_at_the_planned_end_completes or TestAValveThatShutsMidRunEndsTheRun"
```

Erwartet (real beobachtet, Stand Task 4 plus die Tests aus Step 1). Grün bleiben: der Pin „vor dem
Update“, der schon heute gelten muss, der umgestellte Pin `test_a_valve_off_at_the_planned_end_completes`
(heute schreibt `_sc_finish_run` ohnehin `planned_s`), die vier Tests von
`TestAValveThatShutsMidRunEndsTheRun` und der Pin „`unavailable` mitten im Lauf“. Letzterer ist schon am
Elternstand grün, weil die alte Regel zum Entscheidungszeitpunkt ebenfalls die Uhr liest
(`_sc_run_elapsed` = 308 s, Teil-Lauf); er hält fest, dass die Fensterregel ohne Aus-Meldung dasselbe liefert,
und beißt an den Proben `window-planned-without-off` und `unavailable-accepted` (Step 9). Der Fehlschlag
zeigt genau den Messfehler: Abschluss mit `planned_s` (600,0) bzw. Teil-Lauf mit Uhr + 6 s (596,0):

```
E   assert 600.0 == 602 ± 1.0e-02
E   assert 600.0 == 597 ± 1.0e-02
E   assert 596.0 == 590 ± 1.0e-02
E   assert 600.0 == 599.5 ± 1.0e-02
E   AssertionError: assert 'completed' == 'partial'
FAILED tests/test_service_watch.py::TestAConfirmedRunIsSettledOnItsValveWindow::test_a_close_just_after_the_window_completes_on_the_reported_window
FAILED tests/test_service_watch.py::TestAConfirmedRunIsSettledOnItsValveWindow::test_a_close_inside_the_margin_completes_on_the_reported_window
FAILED tests/test_service_watch.py::TestAConfirmedRunIsSettledOnItsValveWindow::test_a_close_beyond_the_margin_is_a_partial_credited_for_its_window
FAILED tests/test_service_watch.py::TestAConfirmedRunIsSettledOnItsValveWindow::test_a_margin_of_zero_still_tolerates_one_second
FAILED tests/test_service_watch.py::TestAConfirmedRunIsSettledOnItsValveWindow::test_a_margin_of_zero_settles_a_close_beyond_that_second_as_partial
================= 5 failed, 7 passed, 32 deselected in 2.68s ==================
```

- [ ] **Step 3: `self_closing.py` — `_sc_finish_run` nimmt `actual_s`**

Vorher:

```python
    async def _sc_finish_run(self, zone_id) -> None:
        """Finalise a completed run: record actual usage, clear, fire finished.

        Idempotent: a no-op if the run is no longer active (e.g. the cleanup
        timer fires after an early stop already removed it), so usage is never
        double-counted.
        """
```

Nachher:

```python
    async def _sc_finish_run(self, zone_id, *, actual_s: float | None = None) -> None:
        """Finalise a completed run: record actual usage, clear, fire finished.

        Idempotent: a no-op if the run is no longer active (e.g. the cleanup
        timer fires after an early stop already removed it), so usage is never
        double-counted.

        ``actual_s`` is the window the valve itself reported open, passed by the
        watcher when it settles a confirmed service run on those reports (#139).
        Without it nothing observed the close (a backstop or restart with no off
        report on record, OpenSprinkler, batch) and the run is recorded for its
        plan.
        """
```

Weiter unten in derselben Methode, im `_record_run`-Aufruf:

Vorher:

```python
        await self._stamp_run_finalized(zone_id, volume_l)
        await self._record_run(
            zone_id,
            result=const.RUN_RESULT_COMPLETED,
            volume_l=volume_l,
            planned_s=planned_s,
            actual_s=planned_s,
            trigger=const.RUN_TRIGGER_SELF_CLOSING,
            add_to_total=True,
        )
```

Nachher:

```python
        await self._stamp_run_finalized(zone_id, volume_l)
        await self._record_run(
            zone_id,
            result=const.RUN_RESULT_COMPLETED,
            volume_l=volume_l,
            planned_s=planned_s,
            # The observed window when there is one (#139): a completed run used
            # to discard it for planned_s, so a valve closing 2-3 s late, or up
            # to its margin early, was recorded as exactly on time. Only the
            # recorded duration moves; the timed volume above and the
            # calibration probe below stay on planned_s, the window the run was
            # credited and sized for.
            actual_s=planned_s if actual_s is None else actual_s,
            trigger=const.RUN_TRIGGER_SELF_CLOSING,
            add_to_total=True,
        )
```

`volume_l = self._timed_volume_l(zone, planned_s)` und
`await self._flow_calibration_check(zone, measured, planned_s)` bleiben unverändert (gepinnt im Test
„+602“, Proben `finish-volume-on-actual` und `finish-calibration-on-actual`).

- [ ] **Step 4: `self_closing.py` — `async_stop_self_closing` nimmt `actual_s`**

Vorher:

```python
    async def async_stop_self_closing(
        self, zone_id, *, close_valve: bool = True, detail: str | None = None
    ) -> bool:
        """Stop a self-closing run early: close the valve + correct the bucket.

        ``close_valve=False`` settles the accounting without touching the
        hardware, for the case where the hardware has already ended the run
        itself — an OpenSprinkler station that stopped short of its window, or
        one that never opened at all. ``detail`` overrides the run-log marker.
        """
```

Nachher:

```python
    async def async_stop_self_closing(
        self,
        zone_id,
        *,
        close_valve: bool = True,
        detail: str | None = None,
        actual_s: float | None = None,
    ) -> bool:
        """Stop a self-closing run early: close the valve + correct the bucket.

        ``close_valve=False`` settles the accounting without touching the
        hardware, for the case where the hardware has already ended the run
        itself — an OpenSprinkler station that stopped short of its window, or
        one that never opened at all. ``detail`` overrides the run-log marker.
        ``actual_s`` is the delivered window when the caller measured it from
        the valve's own reports (#139); without it the run's elapsed time is
        read here, as before.
        """
```

Weiter unten in derselben Methode:

Vorher:

```python
        # Correct the bucket for the undelivered portion of the optimistic open credit.
        planned = float(run.get(const.RUN_PLANNED_SECONDS) or 0)
        planned_mm = float(run.get(const.RUN_PLANNED_MM) or 0)
        elapsed = self._sc_run_elapsed(run)
        delivered_frac = min(elapsed / planned, 1.0) if planned > 0 else 1.0
```

Nachher:

```python
        # Correct the bucket for the undelivered portion of the optimistic open credit.
        planned = float(run.get(const.RUN_PLANNED_SECONDS) or 0)
        planned_mm = float(run.get(const.RUN_PLANNED_MM) or 0)
        # A caller that measured the window at the valve's off report passes it
        # (#139). Reading the clock here instead is what put the debounce into
        # every watcher-settled partial: this runs 5 s after the close, and those
        # 5 s were credited, volumed and recorded as delivered. One value feeds
        # all three below, so the bucket, the volume and actual_s agree.
        elapsed = actual_s if actual_s is not None else self._sc_run_elapsed(run)
        delivered_frac = min(elapsed / planned, 1.0) if planned > 0 else 1.0
```

`elapsed` speist unverändert `delivered_frac`, `self._timed_volume_l(zone, elapsed)` und
`actual_s=elapsed` im `_record_run`-Aufruf.

- [ ] **Step 5: `run_watch.py` — `_watch_valve_window`, `_watch_settle_by_window`, Weiche in `_watch_finish`**

In `RunWatchMixin`, zwischen dem Ende von `_watch_defer_finish` und `_watch_finish`:

Vorher:

```python
        watcher.finish_cancel = async_call_later(self.hass, max(0.0, delay), _decide)

    async def _watch_finish(self, zone_id, run: dict) -> None:
        """Watering stopped. Settle the run against what it actually delivered."""
        zid = int(zone_id)
        self._watch_cancel(zid)
        planned = planned_seconds(run)
        elapsed = self._sc_run_elapsed(run)
```

Nachher:

```python
        watcher.finish_cancel = async_call_later(self.hass, max(0.0, delay), _decide)

    def _watch_valve_window(self, run: dict) -> float:
        """Seconds the run's valve reported itself open (see valve_window_seconds)."""
        return valve_window_seconds(run, dt_util.utcnow())

    async def _watch_settle_by_window(self, zone_id, run: dict) -> None:
        """Settle a run with a finish grace on the window its valve reported.

        The window is RUN_VALVE_OFF minus RUN_VALVE_ON, both taken from the
        valve's own reports, so it does not grow with whatever settles the run
        afterwards: the 5 s debounce, or a backstop further out still (#139).
        The run completes when that window falls short of the plan by no more
        than the tolerance, max(1 s, frozen margin): a valve's own reports land
        either side of the planned end (measured within 0.7 s on a seconds-unit
        valve, one normal run 0.67 s short), so the old one second left a third
        of a second between a normal end and a partial with its credit reversed.
        A shorter window was cut off and settles as a partial on that window.
        """
        zid = int(zone_id)
        self._watch_cancel(zid)
        window = self._watch_valve_window(run)
        if window + run_completion_tolerance(run) >= planned_seconds(run):
            await self._sc_finish_run(zid, actual_s=window)
        else:
            await self.async_stop_self_closing(zid, close_valve=False, actual_s=window)

    async def _watch_finish(self, zone_id, run: dict) -> None:
        """Watering stopped. Settle the run against what it actually delivered."""
        zid = int(zone_id)
        self._watch_cancel(zid)
        if run_has_finish_grace(run):
            # The valve reported both ends of this run, so it is settled on
            # them (#139). The clock read below comes after the debounce and
            # would count those 5 s as watering; it stays for every run without
            # a frozen margin (batch, OpenSprinkler, a service record persisted
            # before the margin existed), whose timing must not move.
            await self._watch_settle_by_window(zid, run)
            return
        planned = planned_seconds(run)
        elapsed = self._sc_run_elapsed(run)
```

Der Rest von `_watch_finish` (`elapsed + 1 >= planned`) bleibt unverändert. `valve_window_seconds`,
`run_completion_tolerance`, `run_has_finish_grace`, `planned_seconds` und `dt_util` stehen bereits im
Modul (Task 2), es ist kein Import nötig. `_watch_resume`, `_watch_observed_start` und `_watch_pause`
bleiben unverändert. Der doppelte `_watch_cancel` (in `_watch_finish` und in
`_watch_settle_by_window`) ist gewollt: Task 6 und Task 8 rufen `_watch_settle_by_window` direkt vom
Backstop bzw. vom Neustart auf, dort ist der Watcher noch aktiv. Auf einen schon entfernten Watcher
wirkt der zweite Aufruf nicht.

- [ ] **Step 6: Tests grün**

```bash
cd /d/Entwicklung/HASI/HAsmartirrigation
mkdir -p D:/Entwicklung/HASI/pr139-work/tmp D:/Entwicklung/HASI/pr139-work/npm-cache && export TEMP=D:/Entwicklung/HASI/pr139-work/tmp TMP=D:/Entwicklung/HASI/pr139-work/tmp TMPDIR=D:/Entwicklung/HASI/pr139-work/tmp npm_config_cache=D:/Entwicklung/HASI/pr139-work/npm-cache
./.venv/Scripts/python.exe -m pytest tests/test_service_watch.py -p _local_socket_unblock -q -k "TestAConfirmedRunIsSettledOnItsValveWindow or test_a_valve_off_at_the_planned_end_completes or TestAValveThatShutsMidRunEndsTheRun"
./.venv/Scripts/python.exe -m pytest tests/test_service_watch.py -p _local_socket_unblock -q
```

Erwartet (real beobachtet). Erster Befehl, ohne Errors:

```
====================== 12 passed, 32 deselected in 1.69s ======================
```

Zweiter Befehl (ganze Datei). Der eine Error ist der schon am Elternstand vorhandene `Lingering timer` in
`TestOneOffSampleIsNotEvidenceTheWaterStopped::test_the_run_is_not_settled_before_the_window_is_out`:

```
E   Failed: Lingering timer after job <Job call_later 5 HassJobType.Coroutinefunction <function RunWatchMixin._watch_defer_finish.<locals>._decide at 0x...>>
ERROR tests/test_service_watch.py::TestOneOffSampleIsNotEvidenceTheWaterStopped::test_the_run_is_not_settled_before_the_window_is_out
========================= 44 passed, 1 error in 4.79s =========================
```

- [ ] **Step 7: Lint**

```bash
cd /d/Entwicklung/HASI/HAsmartirrigation
uvx black custom_components/irrigation_plus/
uvx ruff check custom_components/irrigation_plus/
uvx black --check tests/test_service_watch.py
```

Erwartet (real beobachtet; die Testdatei liegt außerhalb des CI-Lint-Umfangs, Step 1 ist bereits die
formatierte Fassung):

```
67 files left unchanged.
All checks passed!
1 file would be left unchanged.
```

- [ ] **Step 8: Verwandte Suiten**

```bash
cd /d/Entwicklung/HASI/HAsmartirrigation
mkdir -p D:/Entwicklung/HASI/pr139-work/tmp D:/Entwicklung/HASI/pr139-work/npm-cache && export TEMP=D:/Entwicklung/HASI/pr139-work/tmp TMP=D:/Entwicklung/HASI/pr139-work/tmp TMPDIR=D:/Entwicklung/HASI/pr139-work/tmp npm_config_cache=D:/Entwicklung/HASI/pr139-work/npm-cache
./.venv/Scripts/python.exe -m pytest tests/test_service_watch.py tests/test_self_closing.py tests/test_opensprinkler.py tests/test_batch.py tests/test_credit_ceiling.py tests/test_run_segments.py tests/test_run_watch.py -p _local_socket_unblock -q
```

Erwartet (real beobachtet):

```
======================= 278 passed, 52 errors in 22.10s =======================
```

Am Elternstand (Task 4) mit derselben Befehlszeile: `271 passed, 52 errors in 21.57s`. 278 = 271 + 7 neue
Tests; der umgestellte Pin zählt in beiden Läufen. Die 52 Errors sind ausnahmslos
`Failed: Lingering timer after job ...` beim Teardown (lokale HA 2024.12.5): 38 in `tests/test_batch.py`,
13 in `tests/test_opensprinkler.py`, 1 in `tests/test_service_watch.py`. Die sortierten `FAILED`/`ERROR`-Zeilen
beider Läufe sind identisch (Vergleich im Probelauf: `True`), `FAILED` gibt es in keinem. Batch- und
OpenSprinkler-Tests laufen damit unverändert durch den geänderten `_watch_finish` (ihre Datensätze haben
keine Marge). Die Mock-Pins `c._sc_finish_run.assert_awaited_once_with(1)` (`tests/test_self_closing.py`)
und `c._sc_finish_run.assert_awaited_once()` (`tests/test_opensprinkler.py`) bleiben grün: Beide Pfade
rufen ohne `actual_s`. Die direkten Aufrufe `await c._sc_finish_run(...)` und
`await c.async_stop_self_closing(...)` in `tests/test_credit_ceiling.py` und `tests/test_self_closing.py`
nutzen die Defaults.

Vergleichslauf am Elternstand: Block aus Task 0, Step 6 mit `P=$(git rev-parse HEAD)` (vor dem Commit
dieses Tasks = Commit von Task 4, im Probelauf `adcb6fba`) und
`FILES="tests/test_service_watch.py tests/test_self_closing.py tests/test_opensprinkler.py tests/test_batch.py tests/test_credit_ceiling.py tests/test_run_segments.py tests/test_run_watch.py"`;
erwartet `FAILED-ERROR-same`. Im Revisions-Probelauf lief zusätzlich Step 2 in einem Worktree am Commit von
Task 4 mit der Testdatei aus diesem Task (`git show 8528d4d0:tests/test_service_watch.py`), danach
`git checkout -- tests/test_service_watch.py`. Lint am Commit dieses Tasks: `67 files left unchanged.` /
`All checks passed!` / `1 file would be left unchanged.`.

- [ ] **Step 9: Mutationsprobe**

Verfahren aus Task 0, Step 5: `mutate.py`, Suchtexte mit `\n`, Sicherung
`D:/Entwicklung/HASI/pr139-work/mut/t05-<probe>.bak`, nach jeder Probe Wiederherstellung aus der `.bak` und
SHA-256-Prüfung (Pflicht), `git diff --stat` wie vor der Probe. Suchtext → Ersatz steht je Probe wörtlich in
der Tabelle, jeder Suchtext kommt genau einmal vor. Für `never-routed`/`always-routed` deshalb mit Einrückung
und Zeilenende: `        if run_has_finish_grace(run):\n` → `        if False:\n` bzw. `        if True:\n`, weil
`run_has_finish_grace(run)` in `run_watch.py` auch in den Helfern und im Aus-Zweig steht. Lauf je Probe wie
im Block. Die erste Probe vollständig:

```bash
cd /d/Entwicklung/HASI/HAsmartirrigation
mkdir -p D:/Entwicklung/HASI/pr139-work/tmp D:/Entwicklung/HASI/pr139-work/npm-cache && export TEMP=D:/Entwicklung/HASI/pr139-work/tmp TMP=D:/Entwicklung/HASI/pr139-work/tmp TMPDIR=D:/Entwicklung/HASI/pr139-work/tmp npm_config_cache=D:/Entwicklung/HASI/pr139-work/npm-cache
F=custom_components/irrigation_plus/self_closing.py
B=D:/Entwicklung/HASI/pr139-work/mut/t05-finish-actual-dropped.bak
cp "$F" "$B"
S=$(sha256sum "$F" | cut -d' ' -f1)
./.venv/Scripts/python.exe D:/Entwicklung/HASI/pr139-work/mut/mutate.py "$F" 'actual_s=planned_s if actual_s is None else actual_s,' 'actual_s=planned_s,'
PYTHONDONTWRITEBYTECODE=1 ./.venv/Scripts/python.exe -m pytest tests/test_service_watch.py -p _local_socket_unblock -q -p no:cacheprovider -k "TestAConfirmedRunIsSettledOnItsValveWindow or test_a_valve_off_at_the_planned_end_completes"
cp "$B" "$F"
echo "$S  $F" | sha256sum -c -
git diff --stat
```

Real beobachtet im Revisions-Probelauf nach dem Feinschliff: am abgekoppelten Commit dieses Tasks (`8528d4d0`)
in einem temporären Prüf-Worktree, Ersetzung und Wiederherstellung per
`D:/Entwicklung/HASI/pr139-work/mut/r7_probes.py <worktree> t05` (Suchtext genau einmal, Sicherungen
`mut/r7-t05-<name>.bak`, `PYTHONDONTWRITEBYTECODE=1`). Die Proben `window-planned-without-off` und
`unavailable-accepted` sind neu mit dem Pin „`unavailable` mitten im Lauf“.

| Probe | Mutation | Beobachtet (real, am Commit dieses Tasks; 8 Tests ausgewählt, 36 abgewählt) |
|---|---|---|
| finish-actual-dropped | `self_closing.py`: `actual_s=planned_s if actual_s is None else actual_s,` → `actual_s=planned_s,` | FAIL 3 (`just_after_the_window`, `inside_the_margin`, `margin_of_zero_still_tolerates`): `assert 600.0 == 602 ± 1.0e-02`, `== 597`, `== 599.5` |
| stop-actual-dropped | `self_closing.py`: `elapsed = actual_s if actual_s is not None else self._sc_run_elapsed(run)` → `elapsed = self._sc_run_elapsed(run)` | FAIL 2 (`beyond_the_margin`, `beyond_that_second`): `assert 596.0 == 590 ± 1.0e-02`, `assert 604.5 == 598.5 ± 1.0e-02` |
| tolerance-one-second | `run_watch.py`: `if window + run_completion_tolerance(run) >= planned_seconds(run):` → `if window + 1 >= planned_seconds(run):` | FAIL 1 (`inside_the_margin`): `AssertionError: assert 'partial' == 'completed'` |
| tolerance-no-floor | dieselbe Zeile → `if window + float(run_latency_margin(run)) >= planned_seconds(run):` | FAIL 1 (`margin_of_zero_still_tolerates`): `AssertionError: assert 'partial' == 'completed'` |
| decide-time-window | `run_watch.py`: `return valve_window_seconds(run, dt_util.utcnow())` → `return valve_window_seconds({**run, const.RUN_VALVE_OFF: dt_util.utcnow().isoformat()}, dt_util.utcnow())` (Fenster zum Entscheidungszeitpunkt statt an der Aus-Meldung) | FAIL 5: `assert 608.0 == 602 ± 1.0e-02`, `assert 603.0 == 597 ± 1.0e-02`, `assert 'completed' == 'partial'` (590 → 596 + 4), `assert 605.5 == 599.5 ± 1.0e-02`, `assert 'completed' == 'partial'` (598,5 → 604,5) |
| finish-window-not-passed | `run_watch.py`: `await self._sc_finish_run(zid, actual_s=window)` → `await self._sc_finish_run(zid)` | FAIL 3: `assert 600.0 == 602 ± 1.0e-02`, `== 597`, `== 599.5` |
| stop-window-not-passed | `run_watch.py`: `await self.async_stop_self_closing(zid, close_valve=False, actual_s=window)` → `await self.async_stop_self_closing(zid, close_valve=False)` | FAIL 2: `assert 596.0 == 590 ± 1.0e-02`, `assert 604.5 == 598.5 ± 1.0e-02` |
| never-routed | `run_watch.py` `_watch_finish`: `if run_has_finish_grace(run):` → `if False:` | FAIL 5: `assert 600.0 == 602`, `assert 600.0 == 597`, `assert 596.0 == 590`, `assert 600.0 == 599.5`, `assert 'completed' == 'partial'` |
| always-routed | `run_watch.py` `_watch_finish`: `if run_has_finish_grace(run):` → `if True:` | FAIL 1 (`before_the_update_keeps_the_old_rule`): `assert 599.5 == 600.0` |
| finish-volume-on-actual | `self_closing.py` `_sc_finish_run`: `volume_l = self._timed_volume_l(zone, planned_s)` → `volume_l = self._timed_volume_l(zone, actual_s)` | FAIL 1 (`just_after_the_window`): `assert 602.0 == 600` |
| finish-calibration-on-actual | `self_closing.py` `_sc_finish_run`: `await self._flow_calibration_check(zone, measured, planned_s)` → `await self._flow_calibration_check(zone, measured, actual_s)` | FAIL 1 (`just_after_the_window`): `assert 602.0 == 600` |
| window-planned-without-off | `run_watch.py` `valve_window_seconds`: `    return max(0.0, min((now - anchor).total_seconds(), planned))` → `    return planned` (ohne Aus-Meldung nur der Plan als Grenze, nicht die Uhr; Task-2-Code) | FAIL 1 (`unavailable_mid_run_settles_on_the_clock`): `AssertionError: assert 'completed' == 'partial'` |
| unavailable-accepted | `run_watch.py` `_watch_evaluate`: `previous_state.state in RUNNING_STATES` → `previous_state.state in (*RUNNING_STATES, "unavailable")` (das „off“ nach `unavailable` wird als Schluss aufgezeichnet; Task-4-Code, E6) | FAIL 1 (`unavailable_mid_run_settles_on_the_clock`): `AssertionError: assert not '2026-09-15T21:13:20+00:00'` (+ `Lingering timer` der Entprellung, weil der Test vor `_advance` abbricht) |

13 von 13 Proben gefangen. Jeder neue Test scheitert an mindestens einer Probe: +602 an 6
(`finish-actual-dropped`, `decide-time-window`, `finish-window-not-passed`, `never-routed`,
`finish-volume-on-actual`, `finish-calibration-on-actual`), +597 an 5, +590 an 4, Marge 0 / +599,5 an 5,
Marge 0 / +598,5 an 4, „vor dem Update“ an `always-routed` und „`unavailable` mitten im Lauf“ an 2
(`window-planned-without-off`, `unavailable-accepted`). Dieser Pin fällt an keiner der elf übrigen Proben:
ohne Aus-Meldung liefern alte Regel, Fensterregel und Messung zum Entscheidungszeitpunkt dieselben 308 s. Der umgestellte Pin
`test_a_valve_off_at_the_planned_end_completes` fällt an keiner dieser Proben (auch `decide-time-window`
nicht: `_off` feuert die Entprellung per `_settle`, ohne die eingefrorene Uhr vorzustellen). Er ist kein
Mutationsziel dieses Tasks, sondern hält die upstream-Zusicherung „ein voller Lauf bleibt voll,
`actual_s == planned_s == 600` exakt“ auf dem neuen Weg fest. Nach jeder Wiederherstellung war die
SHA-256 gleich dem Ausgangsstand (`self_closing.py` `85f6f73d1d4e…`, `run_watch.py` `148719f84d57…`) und
`git status` sauber.

- [ ] **Step 10: Commit**

```bash
cd /d/Entwicklung/HASI/HAsmartirrigation
git add custom_components/irrigation_plus/self_closing.py custom_components/irrigation_plus/run_watch.py tests/test_service_watch.py
git commit -F - <<'EOF'
feat(run-watch): settle a confirmed service run on its valve window

The watcher read a confirmed service run's elapsed time only when the 5 s
debounce expired, and a completed run then discarded even that for
planned_s (#139). So a valve closing 2-3 s after its window, or a little
early, was recorded as exactly on time, and every watcher-settled partial
counted the debounce as watering: credited, volumed and recorded.

_watch_finish now routes a run with a finish grace through
_watch_settle_by_window: the window is the valve's own off report minus
its on report, and the run completes when that window is short of the
plan by no more than max(1 s, frozen margin), since a valve's reports
land either side of the planned end. _sc_finish_run and
async_stop_self_closing take that window as actual_s; without it both
behave as before, and the timed volume and calibration probe of a
completed run stay on planned_s. Records without a frozen margin (batch,
OpenSprinkler, service runs persisted before the update) keep the old
elapsed + 1 >= planned rule.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
```

Erwartet (real beobachtet, Revisions-Probelauf `dry2` nach dem Feinschliff, Commit `8528d4d0`): `3 files changed, 237 insertions(+), 7 deletions(-)` (`run_watch.py | 33`, `self_closing.py | 33`, `tests/test_service_watch.py | 178`).

**Neue Test-Helfer:** in `tests/test_service_watch.py`

`_advance(hass, frozen, seconds)` stellt die eingefrorene Uhr um `seconds` vor, feuert fällige Timer
(`async_fire_time_changed`, bis zu 0,5 s früh) und wartet `async_block_till_done`. Nur innerhalb des
`freeze_time(...) as frozen`-Blocks nutzen, in dem auch dispatcht wurde. Er steht in diesem Task und
nicht erst in Task 6, obwohl ihn hier nur `_run_until_the_valve_closes` benutzt: Task 6, Task 7 und
Task 8 brauchen ihn, und Task 6 und 7 müssen sich je allein streichen lassen (im Revisions-Probelauf
lieferte das Streichen von Task 6 und 7 mit dem Helfer in Task 6 `NameError: name '_advance' is not
defined` in vier Tests von Task 8).

`_run_until_the_valve_closes(hass, c, zone, closed_after, *, before=None)`. Er dispatcht unter einer
eingefrorenen Uhr (`RUN_VALVE_ON` = `started` ohne Mikrosekunden) und stellt die Uhr auf
`started + closed_after`. Dort meldet er „off“ mit genau diesem `last_changed` (über `_report`), stellt die
Uhr um `SERVICE_WATCH_SETTLE_SECONDS + 1` weiter und feuert den Entprell-Timer. Der optionale Rückruf
`before()` läuft zwischen Dispatch und Schluss, etwa um den Datensatz in `c._cfg` zu verändern. Der
Helfer arbeitet mit dem Mock-Backstop aus `_coord`. Ein Task mit echtem Backstop-Timer (Task 6) muss
`_sc_schedule_cleanup`/`_sc_cancel_cleanup` vor dem Dispatch entfernen, und zwar INNERHALB des
eingefrorenen Blocks, also mit eigenem Ablauf statt über diesen Helfer. Wer einen exakten
`actual_s`-Vergleich ohne `approx` braucht, dispatcht wie der umgestellte Pin im selben
`freeze_time(started)`-Block wie den Schluss.

---

### Task 6: Der Backstop rechnet einen Lauf mit gespeicherter Aus-Meldung nach dem Ventil-Fenster ab

**Files** (Zeilen auf `0b418644`; Einfügestellen hinter Zeilen aus Task 3 an ihrem Basis-Anker):
- Modify: `custom_components/irrigation_plus/self_closing.py:418, 430-431` (`_sc_schedule_cleanup`s inneres `_done` ruft `_sc_backstop_fired`; neue Methode `_sc_backstop_fired` direkt nach `_sc_schedule_cleanup`, vor `_sc_valve_on_instant`; kein neuer Import)
- Test: `tests/test_service_watch.py` (neuer Modul-Helfer `_with_the_real_backstop`, neue Klasse `TestTheBackstopWaitsForTheValve` direkt nach `TestAConfirmedRunIsSettledOnItsValveWindow`, vor `TestAWriteOnlyValveIsUntouched`)

Abtrennbar (Nutzerentscheidung 2026-09-15): Dieser Commit muss sich allein streichen lassen. Deshalb
importiert er nichts, was ein späterer Task braucht, und definiert keinen Helfer, den ein späterer Task
braucht. Das Tor ist `run_finish_grace_seconds(run)` (importiert seit Task 3) statt
`run_has_finish_grace(run)`: für jeden Datensatz gleichwertig, denn die Wartezeit enthält immer die 5 s
Entprellung und ist genau dann ungleich 0, wenn `run_has_finish_grace` gilt. `run_has_finish_grace`
importiert erst Task 7 für den manuellen Stopp. `_advance` kommt aus Task 5, weil ihn Task 7 und Task 8
auch brauchen.

Ziel: Feuert der Backstop eines bestätigten Service-Laufs, obwohl der Watcher schon eine Aus-Meldung
(`RUN_VALVE_OFF`, Task 4) gespeichert hat, wird der Lauf nach der Fensterregel abgerechnet
(`_watch_settle_by_window`, Task 5) und nicht mit `planned_s`. Das passiert, wenn das Ventil später als
seine Marge schließt: die Aus-Meldung landet dann in der 5-s-Entprellung, und der Backstop bei
`planned + 5 + Marge` (Task 3) kommt vor der Entscheidung. Ohne gespeicherte Aus-Meldung hat nichts den
Schluss beobachtet, dann bleibt es beim bisherigen `_sc_finish_run(zone_id)` mit `actual_s = planned_s`.
Die Verzögerungs-Arithmetik von `_sc_schedule_cleanup` bleibt unverändert. Batch und OpenSprinkler
teilen sie, ihre Datensätze tragen nie `RUN_LATENCY_MARGIN` und nehmen deshalb immer den bisherigen Pfad.
Batch und OpenSprinkler bekommen deshalb keinen eigenen Test hier, ihre Suiten laufen in Step 7 mit.

Die Tests arbeiten mit dem ECHTEN Backstop-Timer: nach `_coord(hass)` werden die Instanz-Mocks
`_sc_schedule_cleanup` und `_sc_cancel_cleanup` gelöscht (die Klassenmethoden kommen wieder zum Vorschein).
Dispatch und der ganze Ablauf laufen in EINEM `freeze_time(started) as frozen`-Block, weil freezegun
auch die Loop-Uhr einfriert: ein außerhalb gestellter Timer würde auf der innen vorgestellten Uhr nie
fällig. Jede Prüfung liegt mindestens 1 s neben einem Fälligkeitszeitpunkt, weil
`async_fire_time_changed` bis zu 0,5 s zu früh feuert. Jeder Test endet abgerechnet, kein Timer bleibt
liegen.

- [ ] **Step 1: Tests schreiben**

In `tests/test_service_watch.py` zwischen dem Ende von `TestAConfirmedRunIsSettledOnItsValveWindow` und
`class TestAWriteOnlyValveIsUntouched:` einfügen. Keine neuen Importe (`pytest`, `timedelta`,
`freeze_time`, `dt_util`, `const` sind da; `_coord`, `_zone`, `_dispatch`, `_report` (Task 4) und
`_advance` (Task 5) stammen aus früheren Tasks). So, wie `black` die Datei formatiert.

Vorher:

```python
        assert await c._sc_find_run(2) is None
        kw = c._record_run.await_args.kwargs
        assert kw["result"] == const.RUN_RESULT_COMPLETED
        assert kw["actual_s"] == kw["planned_s"] == 600


class TestAWriteOnlyValveIsUntouched:
```

Nachher:

```python
        assert await c._sc_find_run(2) is None
        kw = c._record_run.await_args.kwargs
        assert kw["result"] == const.RUN_RESULT_COMPLETED
        assert kw["actual_s"] == kw["planned_s"] == 600


def _with_the_real_backstop(c):
    """Drop _coord's backstop doubles, so the dispatch arms the real timer."""
    del c._sc_schedule_cleanup
    del c._sc_cancel_cleanup
    return c


class TestTheBackstopWaitsForTheValve:
    """The real backstop, armed at planned + debounce + margin (#139).

    _coord's doubles for _sc_schedule_cleanup/_sc_cancel_cleanup are removed, so
    the timer the dispatch arms is the one that fires. Dispatch and the whole
    run happen under one frozen clock: freezegun freezes the loop clock too, so
    a timer armed outside the block would not come due on the clock advanced
    inside it. Every check stays at least 1 s from a due time, because
    async_fire_time_changed fires up to 0.5 s early.
    """

    async def test_a_missed_close_is_completed_for_its_plan_after_the_grace(self, hass):
        """No off report ever: nothing observed the close, so the plan stands."""
        c = _with_the_real_backstop(_coord(hass))
        started = dt_util.utcnow().replace(microsecond=0)
        with freeze_time(started) as frozen:
            await _dispatch(hass, c, _zone())
            assert 2 in c._sc_cleanup_timers()

            await _advance(hass, frozen, 607.5)  # the backstop is due at 609

            assert await c._sc_find_run(2) is not None
            c._record_run.assert_not_awaited()

            await _advance(hass, frozen, 2.5)  # 610

            assert await c._sc_find_run(2) is None
            c._record_run.assert_awaited_once()
            kw = c._record_run.await_args.kwargs
            assert kw["result"] == const.RUN_RESULT_COMPLETED
            assert kw["actual_s"] == kw["planned_s"] == 600
            assert 2 not in c._sc_cleanup_timers()

    async def test_a_close_inside_the_grace_is_settled_by_the_watcher_once(self, hass):
        """The Beet valve: off 2 s late, settled by the debounce, not the backstop.

        At +606 the backstop of an ungraced run (600) or one that waited out only
        the debounce (605) would already have settled the run; the watcher's
        debounce is due at 607 and must be what settles it.
        """
        c = _with_the_real_backstop(_coord(hass))
        started = dt_util.utcnow().replace(microsecond=0)
        with freeze_time(started) as frozen:
            await _dispatch(hass, c, _zone())
            frozen.tick(timedelta(seconds=602))
            await _report(hass, "off", started + timedelta(seconds=602))

            await _advance(hass, frozen, 4)  # 606: debounce due at 607

            assert await c._sc_find_run(2) is not None
            c._record_run.assert_not_awaited()

            await _advance(hass, frozen, 2)  # 608: debounce out, backstop (609) not

            assert await c._sc_find_run(2) is None
            c._record_run.assert_awaited_once()
            kw = c._record_run.await_args.kwargs
            assert kw["result"] == const.RUN_RESULT_COMPLETED
            assert kw["actual_s"] == pytest.approx(602, abs=0.01)
            assert 2 not in c._sc_cleanup_timers()

            await _advance(hass, frozen, 3)  # 611: past where the backstop was due

            c._record_run.assert_awaited_once()

    async def test_a_close_later_than_the_margin_is_settled_on_its_window(self, hass):
        """Latency over the margin: the backstop fires inside the debounce.

        Margin 0 arms the backstop at 605. The valve reports off at 603, so the
        debounce would decide at 608, and the backstop gets there first. With an
        off report on record it settles on the window, not on the plan.
        """
        c = _with_the_real_backstop(_coord(hass))
        started = dt_util.utcnow().replace(microsecond=0)
        with freeze_time(started) as frozen:
            await _dispatch(hass, c, _zone(**{const.ZONE_LATENCY_MARGIN: 0}))
            frozen.tick(timedelta(seconds=603))
            await _report(hass, "off", started + timedelta(seconds=603))
            assert c._watchers()[2].finish_cancel is not None  # debounce running

            await _advance(hass, frozen, 3)  # 606: backstop due, debounce (608) not

            assert await c._sc_find_run(2) is None
            c._record_run.assert_awaited_once()
            kw = c._record_run.await_args.kwargs
            assert kw["result"] == const.RUN_RESULT_COMPLETED
            assert kw["actual_s"] == pytest.approx(603, abs=0.01)  # not 600
            assert 2 not in c._watchers()  # and the pending debounce with it
            assert 2 not in c._sc_cleanup_timers()

            await _advance(hass, frozen, 4)  # 610: past the debounce's due time

            c._record_run.assert_awaited_once()


class TestAWriteOnlyValveIsUntouched:
```

Warum die Tests so gebaut sind:
- **Verpasster Schluss:** Das Ventil meldet nie „aus“. Bei +607,5 (Feuern reicht bis 608,0) ist der
  Backstop bei 609 noch nicht fällig, der Lauf steht und nichts ist verbucht. Bei +610 hat der Backstop
  gefeuert: `completed` mit `actual_s == planned_s == 600`, und `_sc_finish_run` hat das Handle aus
  `c._sc_cleanup_timers()` entfernt.
- **Beet-Schluss in der Wartezeit:** „aus“ bei +602 legt die Entprellung auf 607. Die Prüfung bei +606
  belegt, dass der Backstop dem Watcher NICHT zuvorkommt: ein Backstop ohne Wartezeit (600) oder nur mit
  der Entprellung (605) hätte den Lauf dort schon abgerechnet. Bei +608 rechnet der Watcher ab
  (`actual_s ≈ 602`), das Backstop-Handle ist weg. Nach +611, also hinter 609, bleibt es bei genau
  einem `_record_run`.
- **Latenz über der Marge:** Marge 0, also Backstop bei 605. „aus“ bei +603 legt die Entprellung auf
  608. Bei +606 hat der Backstop gefeuert, mit gespeicherter Aus-Meldung: `completed` mit
  `actual_s ≈ 603` (Fenster, nicht 600; Toleranz max(1, 0) = 1, 603 + 1 ≥ 600). `2 not in c._watchers()`
  belegt, dass `_watch_settle_by_window` den Watcher samt Entprellung abgebaut hat. Nach +610, hinter
  608, bleibt es bei einem `_record_run`.

Im Test mit Watcher-Abschluss (Beet) baut `_watch_finish` den Watcher selbst ab. Im Test mit verpasstem
Schluss bleibt die Zustands-Subscription stehen, weil `_coord` `_os_cancel_watch` durch einen Mock
ersetzt. Das ist ein Listener und kein Timer, erzeugt also keinen `Lingering timer`.

- [ ] **Step 2: Tests laufen lassen, Fehlschlag bestätigen**

```bash
cd /d/Entwicklung/HASI/HAsmartirrigation
mkdir -p D:/Entwicklung/HASI/pr139-work/tmp D:/Entwicklung/HASI/pr139-work/npm-cache && export TEMP=D:/Entwicklung/HASI/pr139-work/tmp TMP=D:/Entwicklung/HASI/pr139-work/tmp TMPDIR=D:/Entwicklung/HASI/pr139-work/tmp npm_config_cache=D:/Entwicklung/HASI/pr139-work/npm-cache
./.venv/Scripts/python.exe -m pytest tests/test_service_watch.py -p _local_socket_unblock -q -k TestTheBackstopWaitsForTheValve
```

Erwartet (real beobachtet):

```
E   Failed: Lingering timer after job <Job call_later 5 HassJobType.Coroutinefunction <function RunWatchMixin._watch_defer_finish.<locals>._decide at 0x...>>
E   assert 600.0 == 603 ± 1.0e-02
FAILED tests/test_service_watch.py::TestTheBackstopWaitsForTheValve::test_a_close_later_than_the_margin_is_settled_on_its_window
ERROR tests/test_service_watch.py::TestTheBackstopWaitsForTheValve::test_a_close_later_than_the_margin_is_settled_on_its_window
============= 1 failed, 2 passed, 44 deselected, 1 error in 2.04s =============
```

Der Fehlschlag zeigt genau die Lücke: der Backstop rechnet trotz gespeicherter Aus-Meldung bei +603 mit
`planned_s` ab. Die zwei grünen Tests (verpasster Schluss, Beet-Schluss) sind Pins, die schon am
Elternstand gelten, weil die Backstop-Verzögerung seit Task 3 die Wartezeit trägt. Sie müssen nach dem
Umbau weiter gelten, und die Mutationsprobe in Step 8 zeigt, dass sie beißen. Der `Lingering timer`
entsteht, weil die Zusicherung vor dem letzten `_advance` abbricht. `_sc_finish_run` erreicht den
Watcher nur über den gemockten `_os_cancel_watch`, also bleibt die Entprellung scharf.

- [ ] **Step 3: `self_closing.py` — kein neuer Import**

Der Import-Block bleibt, wie Task 3 und Task 3b ihn hinterlassen. `run_finish_grace_seconds` ist seit
Task 3 importiert (Backstop-Verzögerung beim Dispatch). `run_has_finish_grace` wird hier bewusst NICHT
importiert: Task 7 braucht den Namen ebenfalls, und würde dieser Task ihn importieren, ließe sich
Task 6 nicht mehr allein streichen (im Revisions-Probelauf: Streichen von Task 6 → Konflikt in
`tests/test_service_watch.py`, danach `NameError`/ruff F821 in Task 7). Task 7 importiert ihn selbst.

- [ ] **Step 4: `self_closing.py` — `_done` ruft `_sc_backstop_fired`, neue Methode**

Vorher:

```python
    def _sc_schedule_cleanup(self, zone_id, delay_seconds: float) -> None:
        """Schedule the cosmetic finish after the run's planned duration."""

        async def _done(_now):
            await self._sc_finish_run(zone_id)

        # review finding D (sister of the I-1 interval overlap fix): a manual run that
        # overlaps an active scheduled run on the SAME zone replaces the persisted record
        # (_sc_add_run) and the interval sampler (_sc_start_flow_sampling), but the PRIOR
        # cleanup timer would otherwise linger and fire _sc_finish_run against the NEW run
        # — finalizing it early (false COMPLETED, actual_s=planned_s, dropped flow tail).
        # Cancel-and-replace the prior handle, exactly as the interval half does.
        self._sc_cancel_cleanup(zone_id)
        self._sc_cleanup_timers()[zone_id] = async_call_later(
            self.hass, max(0.0, delay_seconds), _done
        )

    def _sc_valve_on_instant(self, entity_id, lower, upper) -> str:
```

Nachher:

```python
    def _sc_schedule_cleanup(self, zone_id, delay_seconds: float) -> None:
        """Schedule the cosmetic finish after the run's planned duration."""

        async def _done(_now):
            await self._sc_backstop_fired(zone_id)

        # review finding D (sister of the I-1 interval overlap fix): a manual run that
        # overlaps an active scheduled run on the SAME zone replaces the persisted record
        # (_sc_add_run) and the interval sampler (_sc_start_flow_sampling), but the PRIOR
        # cleanup timer would otherwise linger and fire _sc_finish_run against the NEW run
        # — finalizing it early (false COMPLETED, actual_s=planned_s, dropped flow tail).
        # Cancel-and-replace the prior handle, exactly as the interval half does.
        self._sc_cancel_cleanup(zone_id)
        self._sc_cleanup_timers()[zone_id] = async_call_later(
            self.hass, max(0.0, delay_seconds), _done
        )

    async def _sc_backstop_fired(self, zone_id) -> None:
        """The finish backstop ran out: settle whatever run is still in flight.

        Without an off report on record nothing observed the close (the valve
        never reported it, or the run has no valve to watch), so the run is
        completed for its plan, as before. With one, the valve DID report its
        close and only the debounce was still deciding what it meant: a close
        later than the zone's latency margin lands inside the debounce, and the
        backstop gets there first (#139). Finishing that run for its plan would
        throw away the window the valve reported, so it takes the same window
        rule the watcher applies, which also cancels the pending debounce.

        The delay is not decided here: _sc_schedule_cleanup is shared with batch
        and OpenSprinkler, whose records never carry a latency margin and so
        always take the plain finish below.
        """
        run = await self._sc_find_run(zone_id)
        # The grace is non-zero exactly for a run with a finish grace (it always
        # holds the debounce), and zero for batch, OpenSprinkler, write-only and
        # pre-update records.
        if (
            run is not None
            and run_finish_grace_seconds(run)
            and run.get(const.RUN_VALVE_OFF)
        ):
            await self._watch_settle_by_window(zone_id, run)
            return
        await self._sc_finish_run(zone_id)

    def _sc_valve_on_instant(self, entity_id, lower, upper) -> str:
```

Abweichung vom Skelett (`run_has_finish_grace(run)` im Tor): gleichwertig, siehe Step 3 und die Probe
`grace-gate-dropped` in Step 8. `run_finish_grace_seconds` ist `policy.finish_settle_seconds` (Service:
`SERVICE_WATCH_SETTLE_SECONDS` = 5) plus eingefrorene Marge für einen Lauf mit Tor, sonst 0.0; dasselbe
Muster (`grace and run.get(const.RUN_VALVE_OFF)`) nutzt der Neustart in Task 8.

`_watch_settle_by_window` (Task 5, `RunWatchMixin`) liegt auf demselben Koordinator. Es baut zuerst den
Watcher samt Entprellung ab und ruft dann `_sc_finish_run(zid, actual_s=window)` oder
`async_stop_self_closing(zid, close_valve=False, actual_s=window)`. Beide entfernen das Backstop-Handle
über `_sc_cancel_cleanup`. Der Aufruf von `_sc_schedule_cleanup` im Dispatch (Task 3) und die übrigen
Aufrufer (`run_watch.py`, `opensprinkler.py`, Neustart) bleiben unverändert.

- [ ] **Step 5: Tests grün**

```bash
cd /d/Entwicklung/HASI/HAsmartirrigation
mkdir -p D:/Entwicklung/HASI/pr139-work/tmp D:/Entwicklung/HASI/pr139-work/npm-cache && export TEMP=D:/Entwicklung/HASI/pr139-work/tmp TMP=D:/Entwicklung/HASI/pr139-work/tmp TMPDIR=D:/Entwicklung/HASI/pr139-work/tmp npm_config_cache=D:/Entwicklung/HASI/pr139-work/npm-cache
./.venv/Scripts/python.exe -m pytest tests/test_service_watch.py -p _local_socket_unblock -q -k TestTheBackstopWaitsForTheValve
```

Erwartet (real beobachtet, ohne Errors):

```
====================== 3 passed, 44 deselected in 0.98s =======================
```

- [ ] **Step 6: Lint**

```bash
cd /d/Entwicklung/HASI/HAsmartirrigation
uvx black custom_components/irrigation_plus/
uvx ruff check custom_components/irrigation_plus/
```

Erwartet (real beobachtet):

```
67 files left unchanged.
All checks passed!
```

Die Testdatei liegt außerhalb des CI-Lint-Umfangs. Zusätzlich `uvx black tests/test_service_watch.py`
(real: `1 file reformatted.`, drei Testsignaturen auf eine Zeile gezogen; Step 1 zeigt bereits die
formatierte Fassung, `uvx black --check tests/test_service_watch.py` meldet danach real
`1 file would be left unchanged.`).

- [ ] **Step 7: Verwandte Suiten**

```bash
cd /d/Entwicklung/HASI/HAsmartirrigation
mkdir -p D:/Entwicklung/HASI/pr139-work/tmp D:/Entwicklung/HASI/pr139-work/npm-cache && export TEMP=D:/Entwicklung/HASI/pr139-work/tmp TMP=D:/Entwicklung/HASI/pr139-work/tmp TMPDIR=D:/Entwicklung/HASI/pr139-work/tmp npm_config_cache=D:/Entwicklung/HASI/pr139-work/npm-cache
./.venv/Scripts/python.exe -m pytest tests/test_service_watch.py tests/test_self_closing.py tests/test_opensprinkler.py tests/test_batch.py -p _local_socket_unblock -q
```

Erwartet (real beobachtet):

```
======================= 213 passed, 52 errors in 18.23s =======================
```

Am Elternstand (Task 5, Revisions-Probelauf `dry2` nach dem Feinschliff, Commit `8528d4d0`) in denselben vier Dateien: `210 passed, 52 errors in 17.92s`.
213 = 210 + 3 neue Tests. Die 52 Errors sind ausnahmslos `Failed: Lingering timer after job ...` beim
Teardown (lokale HA 2024.12.5; alle 52 `E`-Zeilen in beiden Läufen), verteilt auf 38 in
`tests/test_batch.py`, 13 in `tests/test_opensprinkler.py` und 1 in `tests/test_service_watch.py`
(`TestOneOffSampleIsNotEvidenceTheWaterStopped::test_the_run_is_not_settled_before_the_window_is_out`).
Die sortierten `FAILED`/`ERROR`-Zeilen beider Läufe sind identisch (`diff` leer), `FAILED` gibt es in
keinem. Batch und OpenSprinkler laufen damit unverändert durch den neuen `_done`. Ihre Datensätze tragen
keine Marge, `run_has_finish_grace` ist für sie falsch, und `_sc_backstop_fired` fällt auf
`_sc_finish_run(zone_id)` zurück. Die Mock-Pins auf `_sc_finish_run` in `tests/test_self_closing.py` und
`tests/test_opensprinkler.py` bleiben grün.

Vergleichslauf am Elternstand: Block aus Task 0, Step 6 mit `P=$(git rev-parse HEAD)` (vor dem Commit
dieses Tasks = Commit von Task 5) und
`FILES="tests/test_service_watch.py tests/test_self_closing.py tests/test_opensprinkler.py tests/test_batch.py"`;
erwartet `FAILED-ERROR-same`.

- [ ] **Step 8: Mutationsprobe**

Verfahren aus Task 0, Step 5: `mutate.py`, Suchtexte mit `\n`, Sicherung
`D:/Entwicklung/HASI/pr139-work/mut/t06-<probe>.bak` für `custom_components/irrigation_plus/self_closing.py`,
nach jeder Probe Wiederherstellung aus der `.bak` und SHA-256-Prüfung (Pflicht), `git diff --stat` wie vor
der Probe. Lauf je Probe: `-k TestTheBackstopWaitsForTheValve` auf `tests/test_service_watch.py`. Suchtext →
Ersatz steht je Probe wörtlich in der Tabelle; jeder Suchtext kommt am Commit dieses Tasks genau einmal vor.

| Probe | Mutation in `self_closing.py` | Beobachtet |
|---|---|---|
| backstop-always-finish | `_sc_backstop_fired`: `        if (\n            run is not None\n            and run_finish_grace_seconds(run)\n            and run.get(const.RUN_VALVE_OFF)\n        ):\n            await self._watch_settle_by_window(zone_id, run)\n            return\n` → leer (der Rumpf ruft danach nur noch `await self._sc_finish_run(zone_id)`) | FAIL (1: `later_than_the_margin`) `assert 600.0 == 603 ± 1.0e-02` (+ `Lingering timer` der nicht abgebauten Entprellung) |
| done-reverted | `_done`: `await self._sc_backstop_fired(zone_id)` → `await self._sc_finish_run(zone_id)` | FAIL (1: `later_than_the_margin`) `assert 600.0 == 603 ± 1.0e-02` (+ `Lingering timer`) |
| dispatch-no-grace | Dispatch: `zone_id, planned_seconds + run_finish_grace_seconds(record)` → `zone_id, planned_seconds` | FAIL (2: `missed_close`, `inside_the_grace`) `assert None is not None` (Lauf bei +607,5 bzw. +606 schon abgerechnet) |
| dispatch-settle-only | `zone_id, planned_seconds + run_finish_grace_seconds(record)` → `zone_id, planned_seconds + (const.SERVICE_WATCH_SETTLE_SECONDS if run_finish_grace_seconds(record) else 0)` (Marge vergessen) | FAIL (2: `missed_close`, `inside_the_grace`) `assert None is not None` |
| finish-keeps-handle | `_sc_finish_run`: `        self._sc_cancel_cleanup(zone_id)\n        # Same for the station subscription` → `        # Same for the station subscription` (Bestandscode, prüft die Handle-Zusicherungen) | FAIL (3) `assert 2 not in {2: <bound method TimerHandle.cancel ...>}` (+ `Lingering timer after job <Job call_later 609.0 ... _done>`) |
| off-gate-dropped (äquivalent) | Zeile `and run.get(const.RUN_VALVE_OFF)` entfernt | `3 passed, 43 deselected`. Äquivalent: Ohne Aus-Meldung liefert `valve_window_seconds` `min(jetzt − Anker, planned)`. Beim Backstop gilt `jetzt − RUN_VALVE_ON ≥ planned + Wartezeit`, denn `RUN_VALVE_ON` ist höchstens die Confirm-Rückkehr und der Backstop wird danach gestellt. Das Fenster ist also `planned`, und `_sc_finish_run(actual_s=planned)` schreibt dasselbe wie `_sc_finish_run()`. Der zusätzliche `_watch_cancel` entspricht in Produktion `_os_cancel_watch`. Das Tor bleibt, weil die Spec „ohne Aus-Meldung → `planned_s`“ ausdrücklich festlegt und es nicht vom Uhrvergleich abhängen soll. |
| grace-gate-dropped (äquivalent) | Zeile `and run_finish_grace_seconds(run)` entfernt | `3 passed, 43 deselected`. Äquivalent: `RUN_VALVE_OFF` schreibt der Watcher nur für Läufe mit `run_has_finish_grace` (Task 4), und für genau diese ist `run_finish_grace_seconds` ≥ 5; ein Datensatz mit Aus-Meldung besteht das Tor also immer. Das Tor bleibt als Absicherung, dass ein Batch- oder OpenSprinkler-Datensatz nie in die Fensterregel gerät. |

5 von 5 nicht-äquivalenten Proben gefangen, 2 äquivalente mit Begründung. Jeder neue Test scheitert an
mindestens einer Probe: verpasster Schluss an 3 (dispatch-no-grace, dispatch-settle-only,
finish-keeps-handle), Beet-Schluss an 3 (dieselben) und Latenz über der Marge an 3 (backstop-always-finish,
done-reverted, finish-keeps-handle).

Revisions-Probelauf nach dem Abtrennbarkeits-Umbau (Tor `run_finish_grace_seconds`, `_advance` aus Task 5):
alle sieben Proben erneut am abgekoppelten Commit dieses Tasks (`dfb796c3`, sauberer Baum), Sicherungen
`mut/t06r-<name>.bak`. Ergebnisse wie in der Tabelle: backstop-always-finish und done-reverted je
`1 failed, 2 passed, 43 deselected, 1 error` (`assert 600.0 == 603 ± 1.0e-02`), dispatch-no-grace und
dispatch-settle-only je `2 failed, 1 passed, 43 deselected` (`assert None is not None`),
finish-keeps-handle `3 failed, 43 deselected, 1 error` (`Lingering timer after job <Job call_later 609.0 … _done>`),
die zwei äquivalenten je `3 passed, 43 deselected`. Nach jeder Wiederherstellung war die SHA-256 von
`self_closing.py` gleich dem Ausgangsstand (`9b4b90e7fe83…`), die MD5 von `git diff` vor und nach allen
Proben `d41d8cd98f00b204e9800998ecf8427e` (leerer Diff).

Der Feinschliff (Kommentar und Testdaten in Task 2, ein zusätzlicher Test in der Klasse von Task 5) machte
aus diesem Commit `a3c220e5`. `self_closing.py` und die Testklasse `TestTheBackstopWaitsForTheValve` sind
gegenüber `dfb796c3` unverändert (`git diff --stat dfb796c3 a3c220e5`: nur `const.py`,
`tests/test_finish_grace_helpers.py`, `tests/test_service_watch.py` außerhalb dieser Klasse). Die Proben gelten
deshalb unverändert; am neuen Commit steht in jeder Zusammenfassung `44 deselected` statt `43`, wie in
Step 2 und Step 5. Im Feinschliff liefen `backstop-always-finish`, `finish-keeps-handle`, `off-gate-dropped`
und `grace-gate-dropped` mit genau den Suchtexten der Tabelle erneut am Commit `a3c220e5` (real):
`1 failed, 2 passed, 44 deselected, 1 error` (`assert 600.0 == 603 ± 1.0e-02`),
`3 failed, 44 deselected, 1 error` (`assert 2 not in {2: …}`) und zweimal `3 passed, 44 deselected`; SHA-256
nach jeder Wiederherstellung gleich.

- [ ] **Step 9: Commit**

```bash
cd /d/Entwicklung/HASI/HAsmartirrigation
git add custom_components/irrigation_plus/self_closing.py tests/test_service_watch.py
git commit -F - <<'EOF'
feat(service): let the backstop settle a reported close on its window

A confirmed service run's backstop waits planned + debounce + margin
(#139), but a valve that reports its close later than the margin still
lands inside the debounce, and the backstop gets there first. It then
finished the run for its plan and threw away the off report the watcher
had already recorded.

The backstop callback now goes through _sc_backstop_fired: a run with a
finish grace and a recorded off report is settled by
_watch_settle_by_window, the same window rule the watcher applies, which
also cancels the pending debounce. Every other run is finished for its
plan as before. The delay arithmetic of _sc_schedule_cleanup is
unchanged: batch and OpenSprinkler share it, and their records never
carry a latency margin.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
```

Erwartet (real beobachtet, Revisions-Probelauf `dry2` nach dem Feinschliff, Commit `a3c220e5`): `2 files changed, 132 insertions(+), 1 deletion(-)`.

**Neue Test-Helfer:** in `tests/test_service_watch.py`
- `_with_the_real_backstop(c)` löscht die Instanz-Mocks `_sc_schedule_cleanup` und `_sc_cancel_cleanup`
  aus `_coord` und gibt `c` zurück. Danach stellt der Dispatch den echten Backstop-Timer, sichtbar in
  `c._sc_cleanup_timers()`. Aufzurufen VOR dem Dispatch. Nur dieser Task benutzt ihn; ein späterer Task,
  der ihn braucht, würde Task 6 unstreichbar machen und muss ihn dann selbst definieren.
- `_advance(hass, frozen, seconds)` ist NICHT neu, er kommt aus Task 5.

---

### Task 7: Der manuelle Stopp misst ab der Ein-Meldung des Ventils

**Files** (Zeilen auf `0b418644`; die Stellen liegen in Zeilen, die Task 5 geändert hat):
- Modify: `custom_components/irrigation_plus/self_closing.py:23-28, 717-718, 763-764` (Import `run_has_finish_grace` aus `.run_watch`; `async_stop_self_closing`: Docstring-Satz zu `actual_s`, Auswahl von `elapsed` mit drei Zweigen)
- Test: `tests/test_service_watch.py` (neue Klasse `TestAManualStopMeasuresFromTheValvesOnReport` direkt nach `TestAWriteOnlyValveIsUntouched`, vor `TestTheSubscriptionSurvivesARestart`)

Abtrennbar (Nutzerentscheidung 2026-09-15): Task 6 und Task 7 lassen sich je allein streichen. Deshalb
importiert dieser Task `run_has_finish_grace` selbst (Task 6 kommt ohne den Namen aus), und die neue
Testklasse steht NICHT direkt unter der Klasse aus Task 6: dort würde das Streichen von Task 6 beim
Rebase einen Konflikt erzeugen (im Revisions-Probelauf so beobachtet), weil beide Einfügungen an
dieselbe Stelle grenzen. Zwischen beiden liegt jetzt die unveränderte Klasse `TestAWriteOnlyValveIsUntouched`.

Ziel: Ein manueller Stopp eines Service-Laufs mit Wartezeit (`run_has_finish_grace`) misst dasselbe
Fenster, nach dem der Watcher abrechnet (`_watch_valve_window`, Task 5). Die Auswahl in
`async_stop_self_closing` hat dann drei Stufen: zuerst der übergebene `actual_s` (Watcher und Backstop,
Task 5/6), sonst für Läufe mit Wartezeit das Ventil-Fenster, sonst wie bisher `_sc_run_elapsed(run)`.
Das Fenster läuft ab `RUN_VALVE_ON` bis zur gespeicherten Aus-Meldung. Ohne Aus-Meldung ist es auf
`planned` gedeckelt. Dafür gibt es drei Gründe:
- **Ein Anker für jedes Service-`actual_s`.** `_sc_run_elapsed` misst ab `RUN_OBSERVED_START`, das für
  Service gleich `RUN_STARTED` ist, also die Confirm-Rückkehr. Die kann bis zu einer Poll-Periode nach
  der Ein-Meldung liegen.
- **Kein Stopp in der Wartezeit bucht mehr als das geplante Fenster.** Solange das Ventil noch „an“
  meldet, wird auf `planned` gedeckelt.
- **Eine gespeicherte Aus-Meldung ist das echte Ende.** Die Sekunden zwischen ihr und dem Stopp waren
  keine Bewässerung.

Write-only-, Batch-, OpenSprinkler- und Service-Datensätze von vor dem Update tragen keine Marge und
bleiben bei `_sc_run_elapsed`. Das gilt auch für dessen Warteschlangen- und Segment-Logik.

Die Tests dispatchen und stoppen unter EINER eingefrorenen Uhr (`freeze_time(started) as frozen`). So
sind `RUN_VALVE_ON`, `RUN_STARTED` und der Stoppzeitpunkt exakt. Der Stopp ist ein direkter Aufruf
`await c.async_stop_self_closing(2)`. Der Backstop bleibt der Mock aus `_coord`. Echt ist nur die
Entprellung im Test „Stopp nach der Aus-Meldung“, und die wird am Testende abgelaufen.

- [ ] **Step 1: Tests schreiben**

In `tests/test_service_watch.py` zwischen dem Ende von `TestAWriteOnlyValveIsUntouched` (upstream) und
`class TestTheSubscriptionSurvivesARestart:` einfügen. Es sind keine neuen Importe nötig: `pytest`,
`timedelta`, `AsyncMock`, `freeze_time`, `dt_util` und `const` sind vorhanden. `_coord`, `_zone`,
`_dispatch`, `_report` (Task 4) und `_advance` (Task 5) stammen aus früheren Tasks, nichts aus Task 6.
Der Code steht so da, wie `black` die Datei formatiert.

Vorher:

```python
        await _dispatch(hass, c, _zone(), valve_state="unavailable")

        run = await c._sc_find_run(2)
        assert const.RUN_WATCH_ENTITY not in run
        assert not c._watchers()


class TestTheSubscriptionSurvivesARestart:
```

Nachher:

```python
        await _dispatch(hass, c, _zone(), valve_state="unavailable")

        run = await c._sc_find_run(2)
        assert const.RUN_WATCH_ENTITY not in run
        assert not c._watchers()


class TestAManualStopMeasuresFromTheValvesOnReport:
    """A manual stop books the same window the watcher would (#139).

    async_stop_self_closing read the clock from RUN_OBSERVED_START, which for a
    service run is RUN_STARTED, stamped when the confirm poll returned. So a
    stopped run was measured from a later instant than a watcher-settled one,
    and a stop inside the finish grace booked the grace as watering. A run with
    a finish grace is now measured on its valve window: from RUN_VALVE_ON, up to
    the stored off report, or capped at the planned window while the valve is
    still reporting on. Every stop happens under the dispatch's frozen clock,
    so the anchors are exact.
    """

    async def test_a_stop_mid_run_is_measured_from_the_valve_on_report(self, hass):
        """The valve was on before the dispatch: anchored at the dispatch."""
        c = _coord(hass)
        started = dt_util.utcnow().replace(microsecond=0)
        with freeze_time(started) as frozen:
            await _dispatch(hass, c, _zone())
            run = await c._sc_find_run(2)
            assert run[const.RUN_VALVE_ON] == started.isoformat()

            frozen.tick(timedelta(seconds=100))
            assert await c.async_stop_self_closing(2)
            await hass.async_block_till_done()

        assert await c._sc_find_run(2) is None
        kw = c._record_run.await_args.kwargs
        assert kw["result"] == const.RUN_RESULT_PARTIAL
        assert kw["planned_s"] == 600
        assert kw["actual_s"] == pytest.approx(100, abs=0.01)
        written = [ck.args[1] for ck in c.async_write_watered_bucket.await_args_list]
        assert written[-1] == pytest.approx(-20 + 20 * 100 / 600, abs=0.001)

    async def test_a_valve_reporting_on_after_the_dispatch_is_measured_from_its_report(
        self, hass
    ):
        """On reported 0.4 s after the dispatch, the confirm returning at 1 s.

        RUN_STARTED (and so RUN_OBSERVED_START) is the confirm return; measured
        from there the stop would book 99.0 s, 0.6 s less than the valve ran.
        """
        c = _coord(hass)
        started = dt_util.utcnow().replace(microsecond=0)
        reported = started + timedelta(seconds=0.4)
        with freeze_time(started) as frozen:

            async def _slow_confirm(zone_id, entity_id, retry=True):
                hass.states.async_set(entity_id, "on", timestamp=reported.timestamp())
                frozen.tick(timedelta(seconds=1))
                return True

            c._confirm_valve_running = AsyncMock(side_effect=_slow_confirm)
            await _dispatch(hass, c, _zone(), valve_state="off")
            run = await c._sc_find_run(2)
            assert run[const.RUN_VALVE_ON] == reported.isoformat()
            assert (
                run[const.RUN_OBSERVED_START]
                == (started + timedelta(seconds=1)).isoformat()
            )

            frozen.tick(timedelta(seconds=99))  # 100 s after the dispatch
            assert await c.async_stop_self_closing(2)
            await hass.async_block_till_done()

        kw = c._record_run.await_args.kwargs
        assert kw["result"] == const.RUN_RESULT_PARTIAL
        assert kw["actual_s"] == pytest.approx(99.6, abs=0.01)  # not 99.0

    async def test_a_stop_inside_the_grace_after_the_off_report_books_the_window(
        self, hass
    ):
        """Off reported at 601, stopped at 604 while the debounce still decides.

        The valve's own off report is the real end of the run: the three seconds
        between it and the stop were not watering.
        """
        c = _coord(hass)
        started = dt_util.utcnow().replace(microsecond=0)
        with freeze_time(started) as frozen:
            await _dispatch(hass, c, _zone())
            frozen.tick(timedelta(seconds=601))
            await _report(hass, "off", started + timedelta(seconds=601))
            frozen.tick(timedelta(seconds=3))  # 604: the debounce (606) not fired

            run = await c._sc_find_run(2)
            assert (
                run[const.RUN_VALVE_OFF]
                == (started + timedelta(seconds=601)).isoformat()
            )
            c._record_run.assert_not_awaited()

            assert await c.async_stop_self_closing(2)
            await hass.async_block_till_done()

            kw = c._record_run.await_args.kwargs
            assert kw["actual_s"] == pytest.approx(601, abs=0.01)  # not 604

            # _coord's _os_cancel_watch is a double, so the debounce is still
            # armed; run it out against the removed run, which it leaves alone.
            await _advance(hass, frozen, 3)  # 607

            c._record_run.assert_awaited_once()

    async def test_a_stop_inside_the_grace_with_the_valve_still_on_is_capped_at_the_plan(
        self, hass
    ):
        """No off report yet at 604: the grace is not watering the plan paid for.

        The cap is pinned on actual_s and on the seconds the timed volume is
        computed from. The bucket is deliberately not asserted: the delivered
        fraction is min(elapsed / planned, 1.0), so 600 s and an uncapped 604 s
        write the same bucket and such an assertion could not tell them apart.
        """
        c = _coord(hass)
        started = dt_util.utcnow().replace(microsecond=0)
        with freeze_time(started) as frozen:
            await _dispatch(hass, c, _zone())
            frozen.tick(timedelta(seconds=604))
            assert not (await c._sc_find_run(2)).get(const.RUN_VALVE_OFF)

            assert await c.async_stop_self_closing(2)
            await hass.async_block_till_done()

        kw = c._record_run.await_args.kwargs
        assert kw["actual_s"] == 600  # not 604
        assert c._timed_volume_l.call_args.args[1] == 600  # not 604

    async def test_a_write_only_run_keeps_the_elapsed_since_its_start(self, hass):
        """No valve reports, no finish grace: measured from RUN_STARTED as before."""
        c = _coord(hass)
        started = dt_util.utcnow().replace(microsecond=0)
        with freeze_time(started) as frozen:
            await _dispatch(hass, c, _zone(confirm=None))
            run = await c._sc_find_run(2)
            assert run[const.RUN_STARTED] == started.isoformat()
            assert const.RUN_VALVE_ON not in run

            frozen.tick(timedelta(seconds=100))
            assert await c.async_stop_self_closing(2)
            await hass.async_block_till_done()

        kw = c._record_run.await_args.kwargs
        assert kw["result"] == const.RUN_RESULT_PARTIAL
        assert kw["actual_s"] == pytest.approx(100, abs=0.01)


class TestTheSubscriptionSurvivesARestart:
```

Warum die Tests so gebaut sind:
- **Stopp mitten im Lauf, Ventil vorher an.** `_dispatch` setzt das Ventil vor dem Dispatch auf „on“.
  `RUN_VALVE_ON` wird deshalb auf `dispatched_at` = `started` geklemmt (Task 3), und die Zusicherung
  hält diese Vorbedingung fest. Stopp bei +100 s: `partial` mit `actual_s ≈ 100`. Der Eimer wird von
  −20 aus mit 100/600 von 20 mm gutgeschrieben; hier beißt die Eimer-Zusicherung, weil der Anteil
  unter 1 liegt. Der Test ist schon am Elternstand grün, weil dort `RUN_OBSERVED_START` = `RUN_STARTED`
  = `started` gilt. Er ist ein Pin dafür, dass der neue Zweig einen normalen Stopp nicht verändert.
  Dass er beißt, zeigt die Probe `graced-stop-books-plan`.
- **Späte Ein-Meldung.** Das Muster stammt aus Task 3: Der Confirm-Ersatz setzt „on“ mit Zeitstempel
  +0,4 s und stellt die Uhr um 1 s vor. Damit liegt `RUN_VALVE_ON` bei +0,4 s,
  `RUN_OBSERVED_START`/`RUN_STARTED` bei +1 s. Stopp 100 s nach dem Dispatch: das Fenster ist 99,6 s,
  ab `RUN_OBSERVED_START` wären es 99,0 s.
- **Stopp in der Wartezeit nach der Aus-Meldung.** „off“ bei +601 (Task 4 speichert `RUN_VALVE_OFF`,
  die Entprellung wird auf 606 gestellt). Danach geht die Uhr per `frozen.tick` OHNE Feuern auf 604,
  und dort wird gestoppt. `actual_s ≈ 601` statt 604. Weil `_coord` `_os_cancel_watch` durch einen Mock
  ersetzt, bleibt die Entprellung scharf. Das abschließende `_advance` auf 607 lässt sie gegen den schon
  entfernten Lauf laufen: `_decide` kehrt ohne Lauf sofort zurück, es gibt kein zweites `_record_run`
  und keinen `Lingering timer`.
- **Stopp in der Wartezeit ohne Aus-Meldung.** Das Ventil meldet bei +604 noch „an“. Der Deckel ist
  über zwei Werte gepinnt, die ihn wirklich sehen: `actual_s == 600` und das Zeitvolumen aus 600 s
  (`_timed_volume_l`, letzter Aufruf = der aus dem Stopp). Der Eimer wird bewusst NICHT geprüft:
  `delivered_frac = min(elapsed / planned, 1.0)` ist für 600 s und für ungedeckelte 604 s gleich 1,
  eine Eimer-Zusicherung könnte den Deckel also nicht von seinem Fehlen unterscheiden. Die erste
  Fassung dieses Tests prüfte den Eimer trotzdem; die Probe `bucket-only-vs-uncapped` unten zeigt, dass
  diese Zusicherung allein gegen den ungedeckelten Stopp grün bleibt. Der Docstring sagt das.
- **Write-only.** Ohne `confirm_entity` gibt es weder `RUN_VALVE_ON` noch Marge. Stopp bei +100:
  `actual_s ≈ 100` ab `RUN_STARTED`. Auch dieser Pin ist am Elternstand grün. Er beißt gegen einen
  Umbau, der den neuen Anker ohne Rückfall auf alle Läufe anwendet (Probe `else-anchored-on-valve-on`).

- [ ] **Step 2: Tests laufen lassen, Fehlschlag bestätigen**

```bash
cd /d/Entwicklung/HASI/HAsmartirrigation
mkdir -p D:/Entwicklung/HASI/pr139-work/tmp D:/Entwicklung/HASI/pr139-work/npm-cache && export TEMP=D:/Entwicklung/HASI/pr139-work/tmp TMP=D:/Entwicklung/HASI/pr139-work/tmp TMPDIR=D:/Entwicklung/HASI/pr139-work/tmp npm_config_cache=D:/Entwicklung/HASI/pr139-work/npm-cache
./.venv/Scripts/python.exe -m pytest tests/test_service_watch.py -p _local_socket_unblock -q -k TestAManualStopMeasuresFromTheValvesOnReport
```

Erwartet (real beobachtet, Stand Task 6 plus die Tests aus Step 1):

```
E   Failed: Lingering timer after job <Job call_later 5 HassJobType.Coroutinefunction <function RunWatchMixin._watch_defer_finish.<locals>._decide at 0x...>>
E   assert 99.0 == 99.6 ± 1.0e-02
E   assert 604.0 == 601 ± 1.0e-02
E   assert 604.0 == 600
FAILED tests/test_service_watch.py::TestAManualStopMeasuresFromTheValvesOnReport::test_a_valve_reporting_on_after_the_dispatch_is_measured_from_its_report
FAILED tests/test_service_watch.py::TestAManualStopMeasuresFromTheValvesOnReport::test_a_stop_inside_the_grace_after_the_off_report_books_the_window
FAILED tests/test_service_watch.py::TestAManualStopMeasuresFromTheValvesOnReport::test_a_stop_inside_the_grace_with_the_valve_still_on_is_capped_at_the_plan
ERROR tests/test_service_watch.py::TestAManualStopMeasuresFromTheValvesOnReport::test_a_stop_inside_the_grace_after_the_off_report_books_the_window
============= 3 failed, 2 passed, 47 deselected, 1 error in 2.10s =============
```

Die drei Fehlschläge zeigen genau die Lücke: 99,0 ab der Confirm-Rückkehr statt 99,6 ab der
Ein-Meldung, 604 statt der Aus-Meldung bei 601 und 604 statt des Deckels bei 600 (am `actual_s`; die
Zeitvolumen-Zusicherung dahinter wird gar nicht mehr erreicht). Grün sind die zwei Pins (Stopp mitten im
Lauf mit geklemmter Ein-Meldung, write-only). Der `Lingering timer` entsteht, weil die Zusicherung vor
dem letzten `_advance` abbricht und die Entprellung scharf bleibt.

- [ ] **Step 3: `self_closing.py` — Docstring von `async_stop_self_closing`**

Vorher:

```python
        ``actual_s`` is the delivered window when the caller measured it from
        the valve's own reports (#139); without it the run's elapsed time is
        read here, as before.
        """
```

Nachher:

```python
        ``actual_s`` is the delivered window when the caller measured it from
        the valve's own reports (#139). Without it a run with a finish grace is
        measured on its valve window here, and every other run on its elapsed
        time, as before.
        """
```

- [ ] **Step 4: `self_closing.py` — Import `run_has_finish_grace` und Auswahl von `elapsed` in `async_stop_self_closing`**

Import. Vorher (Stand nach Task 6; Task 6 importiert nichts):

```python
from .run_watch import (
    WatchPolicy,
    register_watch_policy,
    run_credit_ceiling,
    run_finish_grace_seconds,
    run_is_queue_bound,
    run_is_segmented,
    zone_finish_grace_seconds,
    zone_latency_margin,
)
```

Nachher:

```python
from .run_watch import (
    WatchPolicy,
    register_watch_policy,
    run_credit_ceiling,
    run_finish_grace_seconds,
    run_has_finish_grace,
    run_is_queue_bound,
    run_is_segmented,
    zone_finish_grace_seconds,
    zone_latency_margin,
)
```

Ohne Task 3b fehlt die Zeile `zone_finish_grace_seconds,`; das Einfügen von `run_has_finish_grace,`
bleibt davon unberührt (im Revisions-Probelauf konfliktfrei).

Auswahl von `elapsed`. Vorher:

```python
        # Correct the bucket for the undelivered portion of the optimistic open credit.
        planned = float(run.get(const.RUN_PLANNED_SECONDS) or 0)
        planned_mm = float(run.get(const.RUN_PLANNED_MM) or 0)
        # A caller that measured the window at the valve's off report passes it
        # (#139). Reading the clock here instead is what put the debounce into
        # every watcher-settled partial: this runs 5 s after the close, and those
        # 5 s were credited, volumed and recorded as delivered. One value feeds
        # all three below, so the bucket, the volume and actual_s agree.
        elapsed = actual_s if actual_s is not None else self._sc_run_elapsed(run)
        delivered_frac = min(elapsed / planned, 1.0) if planned > 0 else 1.0
```

Nachher:

```python
        # Correct the bucket for the undelivered portion of the optimistic open credit.
        planned = float(run.get(const.RUN_PLANNED_SECONDS) or 0)
        planned_mm = float(run.get(const.RUN_PLANNED_MM) or 0)
        # A caller that measured the window at the valve's off report passes it
        # (#139). Reading the clock here instead is what put the debounce into
        # every watcher-settled partial: this runs 5 s after the close, and those
        # 5 s were credited, volumed and recorded as delivered. One value feeds
        # all three below, so the bucket, the volume and actual_s agree.
        if actual_s is not None:
            elapsed = actual_s
        elif run_has_finish_grace(run):
            # A manual stop of a confirmed service run is measured on the same
            # valve window the watcher settles on, for three reasons. The same
            # anchor for every service actual_s: RUN_OBSERVED_START is the
            # confirm return, up to a poll after the valve's own on report, so a
            # stopped run would be measured shorter than a settled one. A stop
            # inside the finish grace with the valve still on must not book more
            # than the planned window: the grace is waiting for a report, not
            # watering the plan paid for. And a stored off report is the real
            # end: the seconds between it and the stop were not watering.
            # _sc_run_elapsed stays for every run without a frozen margin
            # (write-only, batch, OpenSprinkler, a pre-update service record),
            # whose queue-bound and segmented timing the window does not know.
            elapsed = self._watch_valve_window(run)
        else:
            elapsed = self._sc_run_elapsed(run)
        delivered_frac = min(elapsed / planned, 1.0) if planned > 0 else 1.0
```

`run_has_finish_grace` importiert dieser Task selbst (oben), `_watch_valve_window` liegt auf
`RunWatchMixin` desselben Koordinators (Task 5). `elapsed` speist wie
bisher `delivered_frac`, `self._timed_volume_l(zone, elapsed)` und `actual_s=elapsed` im
`_record_run`-Aufruf.

- [ ] **Step 5: Tests grün**

```bash
cd /d/Entwicklung/HASI/HAsmartirrigation
mkdir -p D:/Entwicklung/HASI/pr139-work/tmp D:/Entwicklung/HASI/pr139-work/npm-cache && export TEMP=D:/Entwicklung/HASI/pr139-work/tmp TMP=D:/Entwicklung/HASI/pr139-work/tmp TMPDIR=D:/Entwicklung/HASI/pr139-work/tmp npm_config_cache=D:/Entwicklung/HASI/pr139-work/npm-cache
./.venv/Scripts/python.exe -m pytest tests/test_service_watch.py -p _local_socket_unblock -q -k TestAManualStopMeasuresFromTheValvesOnReport
```

Erwartet (real beobachtet, ohne Errors):

```
====================== 5 passed, 47 deselected in 1.13s =======================
```

- [ ] **Step 6: Lint**

```bash
cd /d/Entwicklung/HASI/HAsmartirrigation
uvx black custom_components/irrigation_plus/
uvx ruff check custom_components/irrigation_plus/
uvx black --check tests/test_service_watch.py
```

Erwartet (real beobachtet):

```
67 files left unchanged.
All checks passed!
1 file would be left unchanged.
```

Die Testdatei liegt außerhalb des CI-Lint-Umfangs; Step 1 zeigt bereits die mit `uvx black` formatierte
Fassung (zwei Vergleiche mit `.isoformat()` in Klammern über drei Zeilen umbrochen).

- [ ] **Step 7: Verwandte Suiten**

```bash
cd /d/Entwicklung/HASI/HAsmartirrigation
mkdir -p D:/Entwicklung/HASI/pr139-work/tmp D:/Entwicklung/HASI/pr139-work/npm-cache && export TEMP=D:/Entwicklung/HASI/pr139-work/tmp TMP=D:/Entwicklung/HASI/pr139-work/tmp TMPDIR=D:/Entwicklung/HASI/pr139-work/tmp npm_config_cache=D:/Entwicklung/HASI/pr139-work/npm-cache
./.venv/Scripts/python.exe -m pytest tests/test_service_watch.py tests/test_self_closing.py tests/test_opensprinkler.py tests/test_batch.py tests/test_credit_ceiling.py -p _local_socket_unblock -q
```

Erwartet (real beobachtet):

```
======================= 256 passed, 52 errors in 21.04s =======================
```

Am Elternstand (Task 6) mit derselben Befehlszeile: `251 passed, 52 errors in 20.67s`. 256 = 251 + 5 neue
Tests. Die 52 Errors sind ausnahmslos `Failed: Lingering timer after job ...` beim Teardown (lokale HA
2024.12.5): 38 in `tests/test_batch.py`, 13 in `tests/test_opensprinkler.py` und 1 in
`tests/test_service_watch.py` (`TestOneOffSampleIsNotEvidenceTheWaterStopped::test_the_run_is_not_settled_before_the_window_is_out`).
Die sortierten `FAILED`/`ERROR`-Zeilen beider Läufe sind identisch (Vergleich im Probelauf: `True`),
`FAILED` gibt es in keinem. Die direkten Stopp-Aufrufe in `tests/test_self_closing.py`,
`tests/test_credit_ceiling.py` und `tests/test_opensprinkler.py` bleiben grün, weil ihre Datensätze keine
Marge tragen und in den `else`-Zweig fallen. Welche davon den neuen Tor-Zweig bewachen, zeigt die Probe
`grace-gate-dropped`.

Vergleichslauf am Elternstand: Block aus Task 0, Step 6 mit `P=$(git rev-parse HEAD)` (vor dem Commit
dieses Tasks = Commit von Task 6, im Probelauf nach dem Feinschliff `a3c220e5`) und
`FILES="tests/test_service_watch.py tests/test_self_closing.py tests/test_opensprinkler.py tests/test_batch.py tests/test_credit_ceiling.py"`;
erwartet `FAILED-ERROR-same`. Im Probelauf lief am Elternstand zusätzlich `tests/test_service_watch.py` ganz:
`47 passed, 1 error` (der vorbestehende `Lingering timer`), am Commit dieses Tasks (`b59fcdf9`)
`52 passed, 1 error`; Lint an beiden Commits `67 files would be left unchanged.` / `All checks passed!`. Jeder
der beiden Commits ist für sich grün.

- [ ] **Step 8: Mutationsprobe**

Verfahren aus Task 0, Step 5: `mutate.py`, Suchtexte mit `\n`, Sicherung
`D:/Entwicklung/HASI/pr139-work/mut/t07-<probe>.bak` für `custom_components/irrigation_plus/self_closing.py`,
nach jeder Probe Wiederherstellung aus der `.bak` und SHA-256-Prüfung (Pflicht), `git diff --stat` wie vor
der Probe. Suchtext → Ersatz steht je Probe in der Tabelle, jeder Suchtext kommt genau einmal vor. Zwei
Proben brauchen Nachbarzeilen, damit der Suchtext eindeutig ist: `else-anchored-on-valve-on` ersetzt
`        else:\n            elapsed = self._sc_run_elapsed(run)\n        delivered_frac` durch
`        else:\n            elapsed = self._sc_elapsed(run.get(const.RUN_VALVE_ON))\n        delivered_frac`,
`actual-s-after-grace` ersetzt `        if actual_s is not None:\n            elapsed = actual_s\n` durch
`        if actual_s is not None and not run_has_finish_grace(run):\n            elapsed = actual_s\n`.
`-k K` steht für `-k TestAManualStopMeasuresFromTheValvesOnReport` auf `tests/test_service_watch.py`. Die
erste Probe vollständig:

```bash
cd /d/Entwicklung/HASI/HAsmartirrigation
mkdir -p D:/Entwicklung/HASI/pr139-work/tmp D:/Entwicklung/HASI/pr139-work/npm-cache && export TEMP=D:/Entwicklung/HASI/pr139-work/tmp TMP=D:/Entwicklung/HASI/pr139-work/tmp TMPDIR=D:/Entwicklung/HASI/pr139-work/tmp npm_config_cache=D:/Entwicklung/HASI/pr139-work/npm-cache
F=custom_components/irrigation_plus/self_closing.py
B=D:/Entwicklung/HASI/pr139-work/mut/t07-stop-branch-reverted.bak
cp "$F" "$B"
S=$(sha256sum "$F" | cut -d' ' -f1)
./.venv/Scripts/python.exe D:/Entwicklung/HASI/pr139-work/mut/mutate.py "$F" 'elif run_has_finish_grace(run):' 'elif False:'
PYTHONDONTWRITEBYTECODE=1 ./.venv/Scripts/python.exe -m pytest tests/test_service_watch.py -p _local_socket_unblock -q -p no:cacheprovider -k TestAManualStopMeasuresFromTheValvesOnReport
cp "$B" "$F"
echo "$S  $F" | sha256sum -c -
git diff --stat
```

| Probe | Mutation in `self_closing.py` | Lauf | Beobachtet (real, am Commit dieses Tasks) |
|---|---|---|---|
| stop-branch-reverted | `elif run_has_finish_grace(run):` → `elif False:` (Stand vor dem Task) | `-k K` | FAIL 3 (`on_after_the_dispatch`, `after_the_off_report`, `still_on_is_capped`): `assert 99.0 == 99.6 ± 1.0e-02`, `assert 604.0 == 601 ± 1.0e-02`, `assert 604.0 == 600` (plus der `Lingering timer` des abgebrochenen Tests nach der Aus-Meldung) |
| graced-stop-books-plan | `elapsed = self._watch_valve_window(run)` → `elapsed = planned` (Stopp in der Wartezeit bucht immer das Fenster) | `-k K` | FAIL 3 (`mid_run`, `on_after_the_dispatch`, `after_the_off_report`): `assert 600.0 == 100 ± 1.0e-02`, `assert 600.0 == 99.6 ± 1.0e-02`, `assert 600.0 == 601 ± 1.0e-02` |
| graced-stop-ignores-off | dieselbe Zeile → `elapsed = self._watch_valve_window({**run, const.RUN_VALVE_OFF: None})` | `-k K` | FAIL 1 (`after_the_off_report`): `assert 600.0 == 601 ± 1.0e-02` |
| graced-stop-uncapped | dieselbe Zeile → `elapsed = self._sc_elapsed(run.get(const.RUN_VALVE_ON))` (richtiger Anker, ohne Aus-Meldung und Deckel) | `-k K` | FAIL 2 (`after_the_off_report`, `still_on_is_capped`): `assert 604.0 == 601 ± 1.0e-02`, `assert 604.0 == 600` |
| else-anchored-on-valve-on | `else`-Zweig: `elapsed = self._sc_run_elapsed(run)` → `elapsed = self._sc_elapsed(run.get(const.RUN_VALVE_ON))` (neuer Anker ohne Rückfall für alle Läufe; Suchtext mit Nachbarzeilen, siehe oben) | `-k K` | FAIL 1 (`write_only_run_keeps`): `assert 0.0 == 100 ± 1.0e-02`. Im Feinschliff mit dem Suchtext von oben am Endstand-Commit `b59fcdf9` erneut: `1 failed, 4 passed, 47 deselected`, derselbe Test, dieselbe Meldung |
| grace-gate-dropped | `elif run_has_finish_grace(run):` → `elif True:` (Fenster für jeden Lauf) | die fünf Dateien aus Step 7 | Die 5 neuen Tests bleiben grün (für Service-Datensätze äquivalent: Ein-Meldung und Marge kommen immer zusammen, write-only fällt auf `RUN_STARTED` zurück). Gefangen von bestehenden Tests: `6 failed, 249 passed, 52 errors in 20.28s`. FAILED: `test_self_closing.py::test_stop_calls_stop_service_and_corrects_bucket` und `::test_stop_without_stop_service_corrects_accounting_only` (`IndexError: list index out of range`), `::test_self_closing_early_stop_bucket_reconciles_from_pre_bucket` (`assert 0.0 == 15.0`), `test_opensprinkler.py::test_a_station_the_controller_drops_is_written_off_immediately` (`assert -4.999936586666666 == -5.0`, eine nie gestartete Station bekäme ab `RUN_STARTED` Wasser gutgeschrieben), `test_batch.py::TestGivingUp::test_a_zone_the_controller_never_reaches_is_written_off` (`AssertionError: expected await not found.` `Expected: mock(1, -20.0)` `Actual: mock(1, -19.999993326666665)`, uhrabhängig), `test_credit_ceiling.py::test_a_short_run_is_still_corrected_down_by_the_stop` (`assert 0.0 == -2.5 ± 1.0e-09`) |
| actual-s-after-grace (äquivalent) | `if actual_s is not None:` → `if actual_s is not None and not run_has_finish_grace(run):` (Fenster vor dem übergebenen Wert) | `tests/test_service_watch.py` ganz | `51 passed, 1 error in 5.27s` (der vorbestehende `Lingering timer`). Äquivalent: `actual_s` übergibt heute nur `_watch_settle_by_window` (Task 5/6), und das berechnet ihn aus demselben Datensatz im selben Moment mit `_watch_valve_window`. Die Reihenfolge bleibt, weil ein Aufrufer, der selbst gemessen hat, Vorrang haben soll. |
| bucket-only-vs-uncapped (Beleg, keine Produktionsprobe) | im Test `still_on_is_capped` die beiden Deckel-Zusicherungen (`actual_s`, Zeitvolumen) testweise durch die frühere Eimer-Zusicherung (`len(written) == 2`, `written[-1] == written[0] == approx(0.0)`) ersetzt; dazu die Mutation `graced-stop-uncapped` | nur `still_on_is_capped` | ohne Mutation `1 passed`, MIT Mutation ebenfalls `1 passed, 50 deselected in 0.65s`: die Eimer-Zusicherung allein fängt den fehlenden Deckel nicht. Deshalb ist sie entfernt. Testdatei und `self_closing.py` danach per SHA-256 wie vorher, `git status` sauber. |

5 von 5 gezielten Proben wurden von den neuen Tests gefangen. Die Tor-Probe fangen bestehende Suiten,
eine Probe ist äquivalent und begründet, und der Beleg `bucket-only-vs-uncapped` begründet, warum der
Test den Eimer nicht prüft. Jeder neue Test scheitert an mindestens einer Probe:
- Stopp mitten im Lauf: `graced-stop-books-plan`.
- Späte Ein-Meldung: `stop-branch-reverted`, `graced-stop-books-plan`.
- Stopp nach der Aus-Meldung: vier Proben (`stop-branch-reverted`, `graced-stop-books-plan`,
  `graced-stop-ignores-off`, `graced-stop-uncapped`).
- Gedeckelter Stopp: `stop-branch-reverted`, `graced-stop-uncapped`.
- Write-only: `else-anchored-on-valve-on`.

Nach allen Proben war die SHA-256 von `self_closing.py` nach jeder Wiederherstellung gleich dem
Ausgangsstand, und `git status` war sauber.

Die Proben liefen am Probe-Commit `69a9ee45`, dem damaligen Commit dieses Tasks vor dem Abtrennbarkeits-Umbau
und dem Feinschliff (Herkunft in Task 13, Step 7). Der Ausgangs-Hash `5ad804a2fe94…` ist der CRLF-Checkout von
`self_closing.py` an diesem Probe-Commit, nicht am Endstand-Commit `b59fcdf9`; dort ist er `94f6ec980374…`
(beide nachgerechnet mit
`git show <Commit>:custom_components/irrigation_plus/self_closing.py | sed 's/$/\r/' | sha256sum`).
`git diff --stat 69a9ee45 b59fcdf9` nennt vier Dateien: `const.py | 13` (Kommentar von `RUN_VALVE_OFF`,
Task 2), `self_closing.py | 5` (Tor von `_sc_backstop_fired` jetzt `run_finish_grace_seconds(run)` statt
`run_has_finish_grace(run)`, dazu drei Kommentarzeilen, Task 6), `tests/test_finish_grace_helpers.py | 8`
(neutrale Testdaten, Task 2) und `tests/test_service_watch.py | 96` (Position der Klasse und ein zusätzlicher
Test aus Task 5). Keine Probe dieses Tasks berührt diese Stellen, und die Testklasse ist gleich. `tests/test_service_watch.py` hat dort
einen Test mehr (Task 5): Zählungen über die ganze Datei oder mit Abwahl liegen um 1 höher, also
`52 passed, 1 error` statt `51` (actual-s-after-grace), `250 passed` statt `249` (grace-gate-dropped) und
`51 deselected` statt `50` (bucket-only-vs-uncapped), wie in Step 5 und Step 7 neu gemessen.

- [ ] **Step 9: Commit**

```bash
cd /d/Entwicklung/HASI/HAsmartirrigation
git add custom_components/irrigation_plus/self_closing.py tests/test_service_watch.py
git commit -F - <<'EOF'
feat(service): measure a manual stop on the valve's own window

A manual stop of a confirmed service run read its elapsed time from
RUN_OBSERVED_START, which for a service run is the confirm return, up to
a poll after the valve's own on report. So a stopped run was measured
from a later instant than one the watcher settles on its valve window
(#139), and a stop inside the finish grace booked the grace as watering:
past the planned window with the valve still on, or past the off report
the watcher had already stored.

async_stop_self_closing now takes, in order: the actual_s its caller
measured, else the valve window for a run with a finish grace (from
RUN_VALVE_ON to the stored off report, capped at the planned window while
the valve still reports on), else the run's elapsed time as before. The
last branch keeps every run without a frozen margin (write-only, batch,
OpenSprinkler, pre-update service records) on its queue-bound and
segmented timing.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
```

Erwartet (real beobachtet, Revisions-Probelauf `dry2` nach dem Feinschliff, Commit `b59fcdf9`): `2 files changed, 169 insertions(+), 3 deletions(-)`.

**Neue Test-Helfer:** keine. Die Klasse nutzt `_coord`, `_zone`, `_dispatch`, `_report` (Task 4) und
`_advance` (Task 5) sowie das Confirm-Ersatz-Muster aus Task 3. Für spätere Tasks mit Stopp und
scharfer Entprellung gilt: `_coord` ersetzt `_os_cancel_watch` durch einen Mock, `async_stop_self_closing`
baut den Watcher also nicht ab. Den Test deshalb mit einem `_advance` über den Fälligkeitszeitpunkt der
Entprellung beenden. `_decide` kehrt ohne Lauf zurück, und es bleibt kein `Lingering timer` liegen. Eine
Eimer-Zusicherung beißt nur, wenn der gelieferte Anteil unter 1 liegt; für einen Deckel am geplanten
Fenster `actual_s` und das Zeitvolumen prüfen.

---

### Task 8: Ein Neustart übernimmt die Wartezeit

**Files** (Zeilen auf `0b418644`):
- Modify: `custom_components/irrigation_plus/self_closing.py:860-861, 867, 870` (`async_resume_self_closing_runs`, Service-Zweig: `grace`, Sofort-Abschluss nach der Fensterregel, Backstop `planned + grace - elapsed`, Kommentar zur begrenzten Fenster-Abrechnung beim Neuaufnehmen)
- Test: `tests/test_service_watch.py` (neue Modul-Helfer `_ha_goes_down` und `_ha_comes_back`, neue Klasse `TestARestartCarriesTheFinishGrace` am Dateiende nach `TestTheSubscriptionSurvivesARestart`)
- Test (unverändert, läuft mit): `tests/test_self_closing.py::test_resume_finalises_overdue_and_reschedules_partial` (Pin `(2, 500.0)`)

Ziel: Nach einem Neustart bekommt ein bestätigter Service-Lauf dieselbe Wartezeit wie beim Dispatch (Task 3).
Bisher rechnete `async_resume_self_closing_runs` noch mit der alten Formel. Ein Lauf mit
`elapsed >= planned` wurde sofort mit `planned_s` abgeschlossen, sonst wurde der Backstop auf
`planned - elapsed` gestellt. Die Folgen:
- **Neustart in der Wartezeit** (z. B. bei +604): Der Lauf war sofort fertig, bevor eine späte
  Aus-Meldung ankommen konnte. Genau diesen Fehler soll die Wartezeit beheben.
- **Gespeicherte Aus-Meldung** (`RUN_VALVE_OFF`, Task 4) von vor dem Ausfall: Sie wurde für `planned_s`
  verworfen.

Neu: `grace = run_finish_grace_seconds(run)` (settle 5 + eingefrorene Marge, bei Default 9; 0 für jeden
Datensatz ohne Marge). Damit gelten die Zeilen aus Spec Abschnitt 5:

| Zustand beim Neustart | Verhalten |
|---|---|
| `elapsed >= planned + grace`, `RUN_VALVE_OFF` gespeichert | sofort `_watch_settle_by_window` (Fenster = Aus − Ein) |
| `elapsed >= planned + grace`, keine Aus-Meldung | sofort `_sc_finish_run(zone_id)`, `actual_s = planned_s` (wie bisher) |
| sonst | Pumpen-Freigabe neu, Backstop `planned + grace - elapsed`, Watcher neu aufnehmen |
| Watcher findet beim Neuaufnehmen „aus“, keine Aus-Meldung | Entprellung, dann Fenster = `min(jetzt − Anker, planned)` |
| Ventil beim Neuaufnehmen `unavailable`, danach „aus“ | wie die Zeile davor: keine Aus-Meldung, Fenster = `min(jetzt − Anker, planned)` |

Die letzten zwei Zeilen brauchen keinen eigenen Code. Task 4 zeichnet `RUN_VALVE_OFF` nur aus einem
Ereignis auf, dessen Vorzustand laufend war (E6): Die erste Auswertung in `_watch_start` hat keinen
Vorzustand (`previous_state=None`), und das `off`, das auf `unavailable` folgt, hat `unavailable` als
Vorzustand. Nach einem Neustart melden die Zigbee-Ventile genau so: erst `unavailable`, dann `off`, und
`last_changed` dieses `off` ist die Wiederkehr der Entität, nicht der Schluss. Die Entprellung endet in
`_watch_finish` → `_watch_settle_by_window` → `valve_window_seconds` ohne Aus-Meldung (Task 5).
„jetzt“ ist dabei der Moment der Entscheidung, also Meldung + 5 s Entprellung. Das Ventil hat den
Schluss nie gemeldet, darum wird auf diesen Zeitpunkt begrenzt und nicht geraten. Ausfallzeit über das
geplante Fenster hinaus bucht der Deckel `planned` nie.

Write-only-Datensätze und Service-Datensätze von vor dem Update tragen keine Marge. Für sie ist
`grace == 0`, und sie behalten die alte Formel. Den Pin dafür liefert `tests/test_self_closing.py:491`
`(2, 500.0)`. Batch und OpenSprinkler zweigen schon vorher ab (`_batch_resume_run`, `_os_resume_run`).

Die Tests nutzen das Neustart-Muster von `TestTheSubscriptionSurvivesARestart` als Helfer:
- `_ha_goes_down(c)` baut jeden Watcher mit `_watch_cancel` ab, also Subscription und eine laufende
  Entprellung, wie es das Prozessende tut. Danach leert es `c._run_watchers` und setzt die Mocks
  `_sc_schedule_cleanup` und `async_master_acquire` zurück.
- `_ha_comes_back(hass, c)` ruft `async_resume_self_closing_runs` und wartet `async_block_till_done`.

Dispatch, Ausfall und Neustart laufen in EINEM `freeze_time(started) as frozen`-Block, die Uhr geht per
`frozen.tick` bzw. `_advance` (Task 5) vor. Der Backstop bleibt der Mock aus `_coord`, sein Argument wird
direkt geprüft. Echt ist nur die Entprellung des neu aufgenommenen Watchers, und jeder Test mit
Entprellung läuft sie am Ende ab.

- [ ] **Step 1: Tests schreiben**

In `tests/test_service_watch.py` am Dateiende einfügen, direkt nach dem letzten Test von
`TestTheSubscriptionSurvivesARestart`. Neue Importe sind nicht nötig: `pytest`, `timedelta`,
`freeze_time`, `dt_util` und `const` sind vorhanden. `_coord`, `_zone`, `_dispatch`, `_report` (Task 4)
und `_advance` (Task 5) stammen aus früheren Tasks; nichts aus den abtrennbaren Tasks 3b, 6 und 7, damit
dieser Task auch ohne sie grün bleibt. Der Code steht so da, wie `black` die Datei formatiert.
Fixture-Namen: nur die upstream vorhandene Zone `Beet` aus `_zone()` (E7), keine neuen.

Vorher (Dateiende):

```python
    async def test_and_it_still_ends_the_run_on_a_valve_off(self, hass):
        c = _coord(hass)
        await _dispatch(hass, c, _zone())
        c._run_watchers = {}
        await c.async_resume_self_closing_runs()
        await hass.async_block_till_done()

        await _off(hass)

        assert await c._sc_find_run(2) is None
```

Nachher:

```python
    async def test_and_it_still_ends_the_run_on_a_valve_off(self, hass):
        c = _coord(hass)
        await _dispatch(hass, c, _zone())
        c._run_watchers = {}
        await c.async_resume_self_closing_runs()
        await hass.async_block_till_done()

        await _off(hass)

        assert await c._sc_find_run(2) is None


def _ha_goes_down(c):
    """HA stops: everything but the persisted run record lived in memory.

    _watch_cancel drops each watcher with its subscription and a pending
    debounce, as the process dying would; left armed, that debounce would fire
    into the watcher re-adopted after the restart and settle the run itself.
    The backstop and master doubles are reset so the restart's own calls are
    the only ones seen.
    """
    for zone_id in list(c._watchers()):
        c._watch_cancel(zone_id)
    c._run_watchers = {}
    c._sc_schedule_cleanup.reset_mock()
    c.async_master_acquire.reset_mock()


async def _ha_comes_back(hass, c):
    await c.async_resume_self_closing_runs()
    await hass.async_block_till_done()


class TestARestartCarriesTheFinishGrace:
    """A confirmed service run re-adopted after a restart keeps its grace (#139).

    The backstop is re-armed for planned + debounce + margin minus the time
    already elapsed since RUN_STARTED (downtime included), a run is finished
    outright only once that whole grace is out, and a run with a stored off
    report is settled on its window rather than on its plan. Dispatch, downtime
    and restart happen under one frozen clock; the backstop stays _coord's
    double, so the delay it is armed with is asserted directly.
    """

    async def test_a_run_inside_its_window_re_arms_the_backstop_with_the_grace(
        self, hass
    ):
        c = _coord(hass)
        started = dt_util.utcnow().replace(microsecond=0)
        with freeze_time(started) as frozen:
            await _dispatch(hass, c, _zone())
            _ha_goes_down(c)
            frozen.tick(timedelta(seconds=100))

            await _ha_comes_back(hass, c)

            c._sc_schedule_cleanup.assert_called_once_with(2, 509.0)  # 600 + 9 - 100
            c.async_master_acquire.assert_awaited_once()
            assert 2 in c._watchers()
            assert c._watchers()[2].finish_cancel is None
            assert await c._sc_find_run(2) is not None
            c._record_run.assert_not_awaited()

    async def test_a_restart_inside_the_grace_does_not_finish_a_valve_still_on(
        self, hass
    ):
        """+604 is past the plan but not past the grace: the close may still come."""
        c = _coord(hass)
        started = dt_util.utcnow().replace(microsecond=0)
        with freeze_time(started) as frozen:
            await _dispatch(hass, c, _zone())
            _ha_goes_down(c)
            frozen.tick(timedelta(seconds=604))

            await _ha_comes_back(hass, c)

            assert await c._sc_find_run(2) is not None
            c._record_run.assert_not_awaited()
            c._sc_schedule_cleanup.assert_called_once_with(2, 5.0)
            assert 2 in c._watchers()

    async def test_a_valve_found_off_inside_the_grace_completes_on_the_bounded_window(
        self, hass
    ):
        """Closed while HA was down: no off report, so the window is bounded.

        The re-adopted watcher's first evaluate sees the off but does not store
        it (its last_changed is the entity's return, not the close). After the
        debounce the window is min(now - RUN_VALVE_ON, planned) = min(610, 600).
        """
        c = _coord(hass)
        started = dt_util.utcnow().replace(microsecond=0)
        with freeze_time(started) as frozen:
            await _dispatch(hass, c, _zone())
            _ha_goes_down(c)
            frozen.tick(timedelta(seconds=604))
            await _report(hass, "off", started + timedelta(seconds=604))

            await _ha_comes_back(hass, c)

            assert await c._sc_find_run(2) is not None  # not finished outright
            c._record_run.assert_not_awaited()
            c._sc_schedule_cleanup.assert_called_once_with(2, 5.0)
            assert not (await c._sc_find_run(2)).get(const.RUN_VALVE_OFF)
            assert c._watchers()[2].finish_cancel is not None  # debounce due at 609

            await _advance(hass, frozen, 6)  # 610

            assert await c._sc_find_run(2) is None
            c._record_run.assert_awaited_once()
            kw = c._record_run.await_args.kwargs
            assert kw["result"] == const.RUN_RESULT_COMPLETED
            assert kw["actual_s"] == 600

    async def test_a_valve_back_from_unavailable_after_the_restart_is_bounded(
        self, hass
    ):
        """Restart at +604 with the valve unavailable; it reports off at +606.

        That off follows unavailable, not a running state: its last_changed is
        the valve's return, so it is not stored as the close. After the
        debounce the run completes on the bounded window
        min(now - RUN_VALVE_ON, planned) = min(612, 600), not on 606.
        """
        c = _coord(hass)
        started = dt_util.utcnow().replace(microsecond=0)
        with freeze_time(started) as frozen:
            await _dispatch(hass, c, _zone())
            _ha_goes_down(c)
            frozen.tick(timedelta(seconds=604))
            await _report(hass, "unavailable", started + timedelta(seconds=604))

            await _ha_comes_back(hass, c)

            assert await c._sc_find_run(2) is not None  # not finished outright
            c._sc_schedule_cleanup.assert_called_once_with(2, 5.0)
            assert c._watchers()[2].finish_cancel is None  # no information yet

            frozen.tick(timedelta(seconds=2))
            await _report(hass, "off", started + timedelta(seconds=606))

            assert not (await c._sc_find_run(2)).get(const.RUN_VALVE_OFF)
            assert c._watchers()[2].finish_cancel is not None  # debounce due at 611

            await _advance(hass, frozen, 6)  # 612

            assert await c._sc_find_run(2) is None
            c._record_run.assert_awaited_once()
            kw = c._record_run.await_args.kwargs
            assert kw["result"] == const.RUN_RESULT_COMPLETED
            assert kw["actual_s"] == 600  # bounded, not 606

    async def test_a_valve_found_off_mid_run_is_a_partial_up_to_the_decision(
        self, hass
    ):
        """Closed while HA was down, 400 s short: a partial on the bounded window.

        The close itself was never reported, so "now" at the debounce's
        decision is the window's end: restart at +200 plus the 5 s debounce.
        """
        c = _coord(hass)
        started = dt_util.utcnow().replace(microsecond=0)
        with freeze_time(started) as frozen:
            await _dispatch(hass, c, _zone())
            _ha_goes_down(c)
            frozen.tick(timedelta(seconds=200))
            await _report(hass, "off", started + timedelta(seconds=150))

            await _ha_comes_back(hass, c)

            c._sc_schedule_cleanup.assert_called_once_with(2, 409.0)  # 600 + 9 - 200
            assert c._watchers()[2].finish_cancel is not None  # debounce due at 205

            await _advance(hass, frozen, 5)  # 205

            assert await c._sc_find_run(2) is None
            kw = c._record_run.await_args.kwargs
            assert kw["result"] == const.RUN_RESULT_PARTIAL
            assert kw["actual_s"] == pytest.approx(205, abs=0.01)
            written = [
                ck.args[1] for ck in c.async_write_watered_bucket.await_args_list
            ]
            assert written[-1] == pytest.approx(-20 + 20 * 205 / 600, abs=0.001)

    async def test_a_stored_off_report_inside_the_grace_settles_on_its_window(
        self, hass
    ):
        """Off reported at +601, HA gone before the debounce decided (606)."""
        c = _coord(hass)
        started = dt_util.utcnow().replace(microsecond=0)
        with freeze_time(started) as frozen:
            await _dispatch(hass, c, _zone())
            frozen.tick(timedelta(seconds=601))
            await _report(hass, "off", started + timedelta(seconds=601))
            assert c._watchers()[2].finish_cancel is not None  # due at 606
            _ha_goes_down(c)  # the pending debounce dies with the process
            frozen.tick(timedelta(seconds=3))

            await _ha_comes_back(hass, c)  # +604

            run = await c._sc_find_run(2)
            assert (
                run[const.RUN_VALVE_OFF]
                == (started + timedelta(seconds=601)).isoformat()
            )
            c._record_run.assert_not_awaited()
            c._sc_schedule_cleanup.assert_called_once_with(2, 5.0)

            await _advance(hass, frozen, 6)  # 610: the re-adopted debounce (609) out

            assert await c._sc_find_run(2) is None
            c._record_run.assert_awaited_once()
            kw = c._record_run.await_args.kwargs
            assert kw["result"] == const.RUN_RESULT_COMPLETED
            assert kw["actual_s"] == pytest.approx(601, abs=0.01)  # not 600, not 610

    async def test_a_stored_off_report_past_the_grace_settles_on_its_window_at_once(
        self, hass
    ):
        c = _coord(hass)
        started = dt_util.utcnow().replace(microsecond=0)
        with freeze_time(started) as frozen:
            await _dispatch(hass, c, _zone())
            frozen.tick(timedelta(seconds=601))
            await _report(hass, "off", started + timedelta(seconds=601))
            _ha_goes_down(c)
            frozen.tick(timedelta(seconds=99))

            await _ha_comes_back(hass, c)  # +700

            assert await c._sc_find_run(2) is None
            c._record_run.assert_awaited_once()
            kw = c._record_run.await_args.kwargs
            assert kw["result"] == const.RUN_RESULT_COMPLETED
            assert kw["actual_s"] == pytest.approx(601, abs=0.01)  # not 600
            assert 2 not in c._watchers()
            c._sc_schedule_cleanup.assert_not_called()
            c.async_master_acquire.assert_not_awaited()

    async def test_no_off_report_past_the_grace_completes_for_the_plan_at_once(
        self, hass
    ):
        """Nothing observed the close: completed for its plan, as before."""
        c = _coord(hass)
        started = dt_util.utcnow().replace(microsecond=0)
        with freeze_time(started) as frozen:
            await _dispatch(hass, c, _zone())
            _ha_goes_down(c)
            frozen.tick(timedelta(seconds=700))
            await _report(hass, "off", started + timedelta(seconds=650))

            await _ha_comes_back(hass, c)

            assert await c._sc_find_run(2) is None
            c._record_run.assert_awaited_once()
            kw = c._record_run.await_args.kwargs
            assert kw["result"] == const.RUN_RESULT_COMPLETED
            assert kw["actual_s"] == kw["planned_s"] == 600
            assert 2 not in c._watchers()
            c._sc_schedule_cleanup.assert_not_called()
```

Warum die Tests so gebaut sind:
- **Anker exakt.** `_dispatch` setzt das Ventil vor dem Dispatch auf „on“, der echte Confirm bestätigt beim
  ersten Lesen, und die Uhr steht still. Also gilt `RUN_STARTED` = `RUN_VALVE_ON` = `started`, und
  `elapsed` ist nach `frozen.tick(n)` genau `n`. Deshalb sind die Backstop-Argumente exakt:
  509.0 = 600 + 9 − 100, 5.0 = 609 − 604, 409.0 = 609 − 200.
- **Warum `_watch_cancel` in `_ha_goes_down`.** Im Test mit gespeicherter Aus-Meldung bei +601 ist die
  Entprellung des alten Watchers scharf (fällig 606). Ein bloßes `c._run_watchers = {}` ließe den Timer
  liegen. Sein `_decide` holt den Watcher per Zone aus der Registry, bekäme also den NEU aufgenommenen und
  würde den Lauf selbst abrechnen, am Neustart vorbei. `_watch_cancel` bricht Timer und Subscription ab,
  wie das Prozessende. Eine Zustandsänderung „während des Ausfalls“ (die Aus-Meldung in den Tests „Ventil
  beim Neustart aus“, das `unavailable` im Test „zurück aus unavailable“) kommt NACH `_ha_goes_down`.
  Keine Subscription sieht sie, und sie steht beim Neustart nur als Zustand da, wie nach einem echten
  Ausfall.
- **+100, Ventil an:** Backstop `(2, 509.0)`, die Pumpen-Freigabe wird neu genommen, der Watcher ist
  neu aufgenommen und hat keine offene Entprellung. Nichts ist verbucht.
- **+604, Ventil an:** Der Lauf ist über dem Plan, aber in der Wartezeit. Er bleibt stehen, Backstop
  `(2, 5.0)`, Watcher neu aufgenommen. Am Elternstand wäre der Lauf sofort mit `planned_s` fertig.
- **+604, Ventil aus, keine Aus-Meldung:** Die erste Auswertung sieht „aus“, speichert aber nichts
  (`RUN_VALVE_OFF` leer, kein Vorzustand), und die Entprellung ist fällig bei 609. Bei +610 gilt
  `completed` mit `actual_s == 600` = `min(610, 600)`. Die Zusicherungen vor `_advance` fangen den
  Elternstand, der sofort abschließt.
- **Neu: +604, Ventil `unavailable`, „aus“ bei +606** (E6, Neustart-Muster der Z2M-Ventile): Die erste
  Auswertung sieht `unavailable` = keine Information, also keine Entprellung (`finish_cancel is None`).
  Das `off` bei +606 kommt über die neu aufgenommene Subscription mit Vorzustand `unavailable` und
  speichert kein `RUN_VALVE_OFF`, die Entprellung ist fällig bei 611. Bei +612 gilt `completed` mit
  `actual_s == 600` = `min(612, 600)`, nicht 606. Die Uhr steht bei der Meldung auf +606, so dass eine
  aufgezeichnete Meldung sichtbar als 606 herauskäme (Probe `unavailable-accepted`). Die Zusicherungen
  vor `_advance` fangen den Elternstand, der beim Neustart sofort abschließt.
- **+200, Ventil aus, keine Aus-Meldung:** Die Aus-Meldung ist mit +150 gestempelt, das „echte“ Ende, von
  dem der Watcher nichts weiß. Backstop `(2, 409.0)`, dann `_advance(hass, frozen, 5)` genau auf den
  Fälligkeitszeitpunkt 205. Die Uhr steht still, der Timer (Loop-Zeit + 5) wird bei 205 fällig und
  gefeuert. „jetzt“ in `valve_window_seconds` ist damit exakt 205 = Neustart + 5 s Entprellung:
  `partial` mit `actual_s ≈ 205` (nicht 150, weil der Schluss nie gemeldet wurde), Eimer
  −20 + 20 · 205/600. Der Abrechnungsteil gilt schon am Elternstand, dort leitet `_watch_finish` seit
  Task 5 über die Fensterregel. Fangen tut der Test das Backstop-Argument (dort `(2, 400.0)`) und das
  Neuaufnehmen des Watchers.
- **Aus-Meldung bei +601 gespeichert, Neustart +604:** `RUN_VALVE_OFF` hat den Ausfall überstanden (das
  `off` bei +601 folgte direkt auf „on“), Backstop `(2, 5.0)`. Die Entprellung des neu aufgenommenen
  Watchers ist fällig bei 609, bei +610 folgt `completed` mit `actual_s ≈ 601` (Fenster, nicht 600, nicht
  610). Am Elternstand wäre der Lauf beim Neustart schon mit `planned_s` fertig (`TypeError`, weil `run`
  `None` ist).
- **Aus-Meldung bei +601 gespeichert, Neustart +700:** sofort `completed` mit `actual_s ≈ 601`, ohne Watcher,
  Backstop und Pumpen-Freigabe.
- **Keine Aus-Meldung, Neustart +700:** sofort `completed` mit `actual_s == planned_s == 600`, wie bisher.
  Das ist ein Pin, er ist am Elternstand grün. Dass er beißt, zeigt die Probe `no-finish-without-off`.

- [ ] **Step 2: Tests laufen lassen, Fehlschlag bestätigen**

```bash
cd /d/Entwicklung/HASI/HAsmartirrigation
mkdir -p D:/Entwicklung/HASI/pr139-work/tmp D:/Entwicklung/HASI/pr139-work/npm-cache && export TEMP=D:/Entwicklung/HASI/pr139-work/tmp TMP=D:/Entwicklung/HASI/pr139-work/tmp TMPDIR=D:/Entwicklung/HASI/pr139-work/tmp npm_config_cache=D:/Entwicklung/HASI/pr139-work/npm-cache
./.venv/Scripts/python.exe -m pytest tests/test_service_watch.py -p _local_socket_unblock -q -k TestARestartCarriesTheFinishGrace
```

Erwartet (real beobachtet im Probelauf: Tests aus Step 1 auf dem Produktionsstand von Task 7):

```
E   Failed: Lingering timer after job <Job call_later 5 HassJobType.Coroutinefunction <function RunWatchMixin._watch_defer_finish.<locals>._decide at 0x...>>
E   AssertionError: expected call not found.
E   Expected: mock(2, 509.0)
E   Actual: mock(2, 500.0)
E   assert None is not None
E   assert None is not None
E   assert None is not None
E   AssertionError: expected call not found.
E   Expected: mock(2, 409.0)
E   Actual: mock(2, 400.0)
E   TypeError: 'NoneType' object is not subscriptable
E   assert 600.0 == 601 ± 1.0e-02
FAILED tests/test_service_watch.py::TestARestartCarriesTheFinishGrace::test_a_run_inside_its_window_re_arms_the_backstop_with_the_grace
FAILED tests/test_service_watch.py::TestARestartCarriesTheFinishGrace::test_a_restart_inside_the_grace_does_not_finish_a_valve_still_on
FAILED tests/test_service_watch.py::TestARestartCarriesTheFinishGrace::test_a_valve_found_off_inside_the_grace_completes_on_the_bounded_window
FAILED tests/test_service_watch.py::TestARestartCarriesTheFinishGrace::test_a_valve_back_from_unavailable_after_the_restart_is_bounded
FAILED tests/test_service_watch.py::TestARestartCarriesTheFinishGrace::test_a_valve_found_off_mid_run_is_a_partial_up_to_the_decision
FAILED tests/test_service_watch.py::TestARestartCarriesTheFinishGrace::test_a_stored_off_report_inside_the_grace_settles_on_its_window
FAILED tests/test_service_watch.py::TestARestartCarriesTheFinishGrace::test_a_stored_off_report_past_the_grace_settles_on_its_window_at_once
ERROR tests/test_service_watch.py::TestARestartCarriesTheFinishGrace::test_a_valve_found_off_mid_run_is_a_partial_up_to_the_decision
============= 7 failed, 1 passed, 52 deselected, 1 error in 2.70s =============
```

Die sieben Fehlschläge zeigen die Lücke genau:
- Backstop ohne Wartezeit (500 statt 509, 400 statt 409).
- Sofort-Abschluss in der Wartezeit (`assert None is not None` dreimal: Ventil an, Ventil aus, Ventil
  `unavailable`; `TypeError` bei gespeicherter Aus-Meldung).
- Eine gespeicherte Aus-Meldung wird für `planned_s` verworfen (600 statt 601).

Grün ist nur der Pin „keine Aus-Meldung, +700“. Der `Lingering timer` kommt aus dem Test mit +200: Die
Backstop-Zusicherung bricht vor dem `_advance` ab, und die Entprellung bleibt scharf.

- [ ] **Step 3: `self_closing.py` — Service-Zweig von `async_resume_self_closing_runs`**

Kein Import nötig: `run_finish_grace_seconds` importiert `self_closing.py` seit Task 3, und
`_watch_settle_by_window` liegt auf `RunWatchMixin` desselben Koordinators (Task 5).

Vorher:

```python
            elapsed = self._sc_elapsed(run.get(const.RUN_STARTED))
            if elapsed >= planned:
                await self._sc_finish_run(zone_id)
            else:
                # Still inside the hardware window: the valve is open but master
                # holds live only in memory and did not survive the restart.
                # Re-take it so the pump keeps running for the remainder.
                await self.async_master_acquire(self._sc_master_token(zone_id))
                self._sc_schedule_cleanup(zone_id, planned - elapsed)
                # The valve subscription did not survive either, and without it
                # the rest of this run is back to being timed blind. Re-adopt it
                # for the runs that recorded one (a confirmed service run).
                watch_entity = run.get(const.RUN_WATCH_ENTITY)
                if watch_entity:
                    await self._watch_start(
                        zone_id, watch_entity, planned, accepted=True
                    )
```

Nachher:

```python
            elapsed = self._sc_elapsed(run.get(const.RUN_STARTED))
            # A confirmed service run waits planned + debounce + margin for its
            # valve to report the close (#139), and a restart must not take that
            # away: finishing it at planned, or re-arming the backstop for
            # planned - elapsed, would settle a run inside its grace for its plan
            # before a late close had the chance to be seen, which is the defect
            # the grace exists to fix. 0 for every record without a frozen margin
            # (write-only, pre-update), which keeps the formula it had.
            grace = run_finish_grace_seconds(run)
            if elapsed >= planned + grace:
                if grace and run.get(const.RUN_VALVE_OFF):
                    # The watcher stored the valve's own off report before HA went
                    # down, and only the debounce was still deciding. That report
                    # is the end of the run; finishing for the plan would discard
                    # the window the valve reported, so the window rule settles it.
                    await self._watch_settle_by_window(zone_id, run)
                else:
                    # Nothing observed the close. Past the whole grace the bounded
                    # window min(now - anchor, planned) is the plan anyway, so this
                    # is the finish for the plan it always was.
                    await self._sc_finish_run(zone_id)
            else:
                # Still inside the hardware window: the valve is open but master
                # holds live only in memory and did not survive the restart.
                # Re-take it so the pump keeps running for the remainder.
                await self.async_master_acquire(self._sc_master_token(zone_id))
                self._sc_schedule_cleanup(zone_id, planned + grace - elapsed)
                # The valve subscription did not survive either, and without it
                # the rest of this run is back to being timed blind. Re-adopt it
                # for the runs that recorded one (a confirmed service run). A
                # valve that closed while HA was down is found off by the
                # watcher's first evaluate, or reports off after coming back as
                # unavailable; neither is stored as the off report (its
                # last_changed is the entity's return, not the close). With no
                # report of the close, the run is settled after the debounce on
                # the bounded window min(now - anchor, planned):
                # neither the downtime nor a close nobody saw is booked as
                # watering beyond what the plan allowed.
                watch_entity = run.get(const.RUN_WATCH_ENTITY)
                if watch_entity:
                    await self._watch_start(
                        zone_id, watch_entity, planned, accepted=True
                    )
```

`black` lässt den Kommentarblock so stehen (Kommentare werden nicht umbrochen; die kurze Zeile
`# the bounded window min(now - anchor, planned):` ist Absicht des Umbruchs vor dem Satzende).

- [ ] **Step 4: Tests grün, Write-only-Pin grün**

```bash
cd /d/Entwicklung/HASI/HAsmartirrigation
mkdir -p D:/Entwicklung/HASI/pr139-work/tmp D:/Entwicklung/HASI/pr139-work/npm-cache && export TEMP=D:/Entwicklung/HASI/pr139-work/tmp TMP=D:/Entwicklung/HASI/pr139-work/tmp TMPDIR=D:/Entwicklung/HASI/pr139-work/tmp npm_config_cache=D:/Entwicklung/HASI/pr139-work/npm-cache
./.venv/Scripts/python.exe -m pytest tests/test_service_watch.py -p _local_socket_unblock -q -k TestARestartCarriesTheFinishGrace
./.venv/Scripts/python.exe -m pytest tests/test_self_closing.py -p _local_socket_unblock -q -k test_resume_finalises_overdue_and_reschedules_partial
```

Erwartet (real beobachtet, ohne Errors):

```
====================== 8 passed, 52 deselected in 1.42s =======================
====================== 1 passed, 37 deselected in 0.69s =======================
```

Der Pin `c._sc_schedule_cleanup.assert_called_once_with(2, 500.0)` bleibt unverändert grün. Seine
Datensätze haben weder `RUN_MODE` noch `RUN_WATCH_ENTITY` noch Marge, `grace` ist 0.

- [ ] **Step 5: Lint**

```bash
cd /d/Entwicklung/HASI/HAsmartirrigation
uvx black custom_components/irrigation_plus/
uvx ruff check custom_components/irrigation_plus/
uvx black --check tests/test_service_watch.py
```

Erwartet (real beobachtet):

```
All done! ✨ 🍰 ✨
67 files left unchanged.
All checks passed!
All done! ✨ 🍰 ✨
1 file would be left unchanged.
```

Die Testdatei liegt außerhalb des CI-Lint-Umfangs; Step 1 zeigt bereits die formatierte Fassung.

- [ ] **Step 6: Verwandte Suiten**

```bash
cd /d/Entwicklung/HASI/HAsmartirrigation
mkdir -p D:/Entwicklung/HASI/pr139-work/tmp D:/Entwicklung/HASI/pr139-work/npm-cache && export TEMP=D:/Entwicklung/HASI/pr139-work/tmp TMP=D:/Entwicklung/HASI/pr139-work/tmp TMPDIR=D:/Entwicklung/HASI/pr139-work/tmp npm_config_cache=D:/Entwicklung/HASI/pr139-work/npm-cache
./.venv/Scripts/python.exe -m pytest tests/test_service_watch.py tests/test_self_closing.py tests/test_opensprinkler.py tests/test_batch.py tests/test_master.py -p _local_socket_unblock -q
```

Erwartet (real beobachtet):

```
======================= 245 passed, 52 errors in 20.65s =======================
```

Am Elternstand (Task 7, Revisions-Probelauf `dry2` nach dem Feinschliff, Commit `b59fcdf9`) liefen dieselben fünf Dateien mit `237 passed, 52 errors in 20.08s`.
245 = 237 + 8 neue Tests. Die 52 Errors sind ausnahmslos `Failed: Lingering timer after job ...` beim
Teardown (lokale HA 2024.12.5). Sie verteilen sich auf 38 in `tests/test_batch.py`, 13 in `tests/test_opensprinkler.py`, 1 in `tests/test_service_watch.py`
(`TestOneOffSampleIsNotEvidenceTheWaterStopped::test_the_run_is_not_settled_before_the_window_is_out`).

Die sortierten `FAILED`/`ERROR`-Zeilen beider Läufe sind identisch (`diff` leer). `FAILED` gibt es in keinem
Lauf. Batch- und OpenSprinkler-Wiederaufnahme zweigen vor dem geänderten Block ab und bleiben unberührt.

Vergleichslauf am Elternstand: Block aus Task 0, Step 6 mit `P=$(git rev-parse HEAD)` (vor dem Commit
dieses Tasks = Commit von Task 7) und
`FILES="tests/test_service_watch.py tests/test_self_closing.py tests/test_opensprinkler.py tests/test_batch.py tests/test_master.py"`;
erwartet `FAILED-ERROR-same`.

- [ ] **Step 7: Mutationsprobe**

Verfahren aus Task 0, Step 5: `mutate.py`, Suchtexte mit `\n`, Sicherung
`D:/Entwicklung/HASI/pr139-work/mut/t08-<probe>.bak` für die genannte Produktionsdatei, nach jeder Probe
Wiederherstellung aus der `.bak` und SHA-256-Prüfung (Pflicht), `git diff --stat` wie vor der Probe.
Suchtext → Ersatz steht je Probe in der Tabelle, jeder Suchtext kommt am Commit dieses Tasks genau einmal
vor. `-k K` steht für
`-k TestARestartCarriesTheFinishGrace` auf `tests/test_service_watch.py`, `-k K4|K` für
`-k "TestTheWatcherRecordsTheValvesOwnOffReport or TestARestartCarriesTheFinishGrace"`.

| Probe | Mutation | Lauf | Beobachtet |
|---|---|---|---|
| grace-reverted | `grace = run_finish_grace_seconds(run)` → `grace = 0.0` (Stand vor dem Task) | `-k K` | FAIL (7 von 8, alle außer `no_off_report_past_the_grace`) `Expected: mock(2, 509.0) Actual: mock(2, 500.0)`, `assert None is not None`, `Expected: mock(2, 409.0) Actual: mock(2, 400.0)` — `7 failed, 1 passed, 51 deselected, 1 error` |
| immediate-at-plan | `if elapsed >= planned + grace:` → `if elapsed >= planned:` | `-k K` | FAIL (4: `restart_inside_the_grace`, `found_off_inside_the_grace`, `back_from_unavailable`, `stored_off_report_inside_the_grace`) `assert None is not None`, `TypeError: 'NoneType' object is not subscriptable` — `4 failed, 4 passed` |
| backstop-without-grace | `self._sc_schedule_cleanup(zone_id, planned + grace - elapsed)` → `self._sc_schedule_cleanup(zone_id, planned - elapsed)` | `-k K` | FAIL (6: `re_arms_the_backstop`, `restart_inside_the_grace`, `found_off_inside_the_grace`, `back_from_unavailable`, `found_off_mid_run`, `stored_off_report_inside_the_grace`) `Expected: mock(2, 509.0) Actual: mock(2, 500.0)`, `Expected: mock(2, 5.0) Actual: mock(2, -4.0)`, `Expected: mock(2, 409.0)` — `6 failed, 2 passed, 3 errors` |
| stored-off-ignored | `if grace and run.get(const.RUN_VALVE_OFF):` → `if False:` | `-k K` | FAIL (1: `stored_off_report_past_the_grace`) `assert 600.0 == 601 ± 1.0e-02` |
| no-finish-without-off | `                    # is the finish for the plan it always was.\n                    await self._sc_finish_run(zone_id)\n` → `                    # is the finish for the plan it always was.\n                    pass\n` (`else`-Rumpf) | `-k K` | FAIL (1: `no_off_report_past_the_grace`) `AssertionError: assert {'ceiling': 0.0, 'credited': True, 'entity_id': 'script.irrigation_beet', 'latency_margin': 4, ...} is None` |
| watcher-not-readopted | `                if watch_entity:\n                    await self._watch_start(\n` → `                if False:\n                    await self._watch_start(\n` (Bestandscode, prüft, dass die Abrechnung nach dem Neustart über den neu aufgenommenen Watcher läuft) | `-k K` | FAIL (6: `re_arms_the_backstop`, `restart_inside_the_grace`, `found_off_inside_the_grace`, `back_from_unavailable`, `found_off_mid_run`, `stored_off_report_inside_the_grace`) `assert 2 in {}`, `KeyError: 2`, `assert {...} is None` |
| window-unbounded | `run_watch.py` `valve_window_seconds`: `return max(0.0, min((now - anchor).total_seconds(), planned))` → `return max(0.0, (now - anchor).total_seconds())` (Task-2-Code, prüft den Deckel beim Neuaufnehmen) | `-k K` | FAIL (2: `found_off_inside_the_grace` `assert 610.0 == 600`, `back_from_unavailable` `assert 612.0 == 600`) |
| running-condition-removed | `run_watch.py` `_watch_evaluate`: Zeile `and previous_state.state in RUNNING_STATES` entfernt (Task-4-Code, E6) | `-k K4\|K` | FAIL (3: `back_from_unavailable` `AssertionError: assert not '2026-09-15T19:06:27+00:00'`, dazu aus Task 4 `unavailable_mid_run_records_nothing` und `re_adopted_run_does_not_record_an_off_after_unavailable`) — `3 failed, 13 passed, 43 deselected, 3 errors` |
| unavailable-accepted | `run_watch.py`: `previous_state.state in RUNNING_STATES` → `previous_state.state in (*RUNNING_STATES, "unavailable")` (Task-4-Code, E6) | `-k K4\|K` | FAIL (3: dieselben) `AssertionError: assert not '2026-09-15T19:06:40+00:00'` — `3 failed, 13 passed, 43 deselected, 3 errors` |
| grace-for-every-record | `grace = run_finish_grace_seconds(run)` → `grace = float(const.SERVICE_WATCH_SETTLE_SECONDS + const.DEFAULT_LATENCY_MARGIN_SECONDS)` (Wartezeit auch ohne Marge im Datensatz) | `tests/test_self_closing.py::test_resume_finalises_overdue_and_reschedules_partial` und `-k K` | FAIL (1: der Pin) `Expected: mock(2, 500.0) Actual: mock(2, 509.0)` — `1 failed, 8 passed, 51 deselected`. Die 8 neuen Tests bleiben grün (Default-Marge 4 = eingefrorene Marge), der Write-only-Pin fängt es |
| settle-by-window-without-off (äquivalent) | `if grace and run.get(const.RUN_VALVE_OFF):` → `if grace:` | `-k K` | `8 passed, 51 deselected`. Äquivalent: Im Sofort-Zweig gilt `elapsed >= planned + grace`, und `RUN_VALVE_ON` liegt nie vor `RUN_STARTED`. Ohne Aus-Meldung ist also `min(jetzt − Anker, planned) = planned`, und `_watch_settle_by_window` schreibt `completed` mit `actual_s = planned`, dasselbe wie `_sc_finish_run(zone_id)`. Das Tor bleibt, weil die Spec „ohne Aus-Meldung → `planned_s`“ ausdrücklich festlegt, unabhängig vom Uhrvergleich (wie die Probe `off-gate-dropped` in Task 6). |

10 von 10 nicht-äquivalenten Proben wurden gefangen, eine Probe ist äquivalent und begründet. Jeder neue
Test scheitert an mindestens einer Probe:
- `re_arms_the_backstop` (+100): `grace-reverted`, `backstop-without-grace`, `watcher-not-readopted`.
- `restart_inside_the_grace` (+604 an): `grace-reverted`, `immediate-at-plan`, `backstop-without-grace`,
  `watcher-not-readopted`.
- `found_off_inside_the_grace` (+604 aus): `grace-reverted`, `immediate-at-plan`, `backstop-without-grace`,
  `watcher-not-readopted`, `window-unbounded`.
- `back_from_unavailable` (+604 `unavailable`, +606 aus): `grace-reverted`, `immediate-at-plan`,
  `backstop-without-grace`, `watcher-not-readopted`, `window-unbounded`, `running-condition-removed`,
  `unavailable-accepted`.
- `found_off_mid_run` (+200 aus): `grace-reverted`, `backstop-without-grace`, `watcher-not-readopted`.
- `stored_off_report_inside_the_grace` (+601/+604): `grace-reverted`, `immediate-at-plan`,
  `backstop-without-grace`, `watcher-not-readopted`.
- `stored_off_report_past_the_grace` (+601/+700): `grace-reverted`, `stored-off-ignored`.
- `no_off_report_past_the_grace` (+700): `no-finish-without-off`.
- Pin `(2, 500.0)`: `grace-for-every-record`.

Nach allen Proben meldete jede Wiederherstellung `restored=True` (SHA-256 gleich dem Ausgangsstand). Die
MD5 von `git diff` im Probe-Worktree war vor und nach den Proben `d41d8cd98f00b204e9800998ecf8427e` (leer).
Der Probe-Worktree war abgekoppelt am Probe-Commit `71f08c0d`, dem damaligen Commit dieses Tasks vor dem
Abtrennbarkeits-Umbau und dem Feinschliff. Gegen den Endstand-Commit `b503b663` nennt
`git diff --stat 71f08c0d b503b663` fünf Dateien (`5 files changed, 105 insertions(+), 59 deletions(-)`):

- `custom_components/irrigation_plus/const.py` (13 Zeilen): Kommentar von `RUN_VALVE_OFF` (Task 2).
- `custom_components/irrigation_plus/self_closing.py` (5 Zeilen): nur das Tor von `_sc_backstop_fired`,
  `run_finish_grace_seconds(run)` statt `run_has_finish_grace(run)` plus drei Kommentarzeilen (Task 6).
- `tests/test_finish_grace_helpers.py` (8 Zeilen): neutrale Testdaten (Task 2, E7).
- `tests/test_service_watch.py` (132 Zeilen): alles außerhalb der Testklasse
  `TestARestartCarriesTheFinishGrace`, die byte-gleich ist (MD5 `647136080e57…`); darunter ein zusätzlicher
  Test in der Klasse von Task 5.
- `tests/test_store_self_closing.py` (6 Zeilen): Fixture-Namen `Kirschlorbeer` → `Front`,
  `script.irrigation_kirschlorbeer` → `script.irrigation_front`, `valve.kirschlorbeer` → `valve.front`
  (Task 1, E7).

Keine Probe dieses Tasks berührt eine dieser Stellen.

Zählungen in der Tabelle stammen von `71f08c0d`. Am Endstand-Commit hat `tests/test_service_watch.py` einen
Test mehr (Task 5, außerhalb beider `-k`-Klassen); die Abwahl liegt dort um 1 höher (`52 deselected` statt
`51` bei `-k K`, `44 deselected` statt `43` bei `-k K4|K`), wie in Step 2 und Step 4 neu gemessen. Im
Feinschliff liefen `no-finish-without-off` und `watcher-not-readopted` mit genau den Suchtexten der Tabelle
erneut am Endstand-Commit `b503b663` (real): `1 failed, 7 passed, 52 deselected` bzw.
`6 failed, 2 passed, 52 deselected`, dieselben Tests und Meldungen wie in der Tabelle.

- [ ] **Step 8: Commit**

```bash
cd /d/Entwicklung/HASI/HAsmartirrigation
git add custom_components/irrigation_plus/self_closing.py tests/test_service_watch.py
git commit -F - <<'EOF'
feat(service): carry the finish grace across a restart

A confirmed service run waits planned + debounce + margin for its valve
to report the close (#139), but the restart reconcile still used the
old formula: a run past its plan was finished for the plan, and one
inside it re-armed the backstop for planned - elapsed. A restart inside
the grace therefore settled the run before a late close could be seen,
and an off report the watcher had stored before HA went down was thrown
away for planned_s.

async_resume_self_closing_runs now adds run_finish_grace_seconds to
both: a run is finished outright only once the whole grace is out, and
the re-armed backstop covers planned + grace - elapsed. Past the grace,
a run with a stored off report is settled on its window by
_watch_settle_by_window; without one nothing observed the close and it
completes for its plan as before. A valve found off when the watcher is
re-adopted, or one that comes back unavailable and then reports off, is
not stored as the off report (its last_changed is the entity's return),
so that run settles after the debounce on the bounded window
min(now - anchor, planned). Records without a frozen margin (write-only,
pre-update) keep grace 0 and the formula they had.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
```

Erwartet (real beobachtet, Revisions-Probelauf `dry2` nach dem Feinschliff, Commit `b503b663`): `2 files changed, 280 insertions(+), 4 deletions(-)`.

**Neue Test-Helfer:** in `tests/test_service_watch.py`
- `_ha_goes_down(c)` simuliert das Prozessende. Es baut jeden Watcher per `_watch_cancel` ab
  (Subscription und laufende Entprellung), leert `c._run_watchers` und setzt die Mocks
  `_sc_schedule_cleanup` und `async_master_acquire` zurück. Der persistierte Datensatz bleibt. Aufzurufen
  im selben `freeze_time`-Block wie der Dispatch. Eine Zustandsänderung „während des Ausfalls“ gehört
  zwischen `_ha_goes_down` und `_ha_comes_back`, dann sieht sie keine Subscription.
- `_ha_comes_back(hass, c)` ruft `async_resume_self_closing_runs` und `async_block_till_done`.

Beide passen zu `_coord`, das Backstop-Mocks hat. Mit `_with_the_real_backstop` (Task 6) bricht
`_ha_goes_down` den echten Backstop-Timer nicht ab, und `reset_mock` gibt es dort nicht. Ein späterer Test
mit echtem Backstop muss den alten Timer vorher selbst mit `c._sc_cancel_cleanup(zone_id)` abbrechen.

---

### Task 9: Das In-flight-Fenster trägt die Wartezeit

**Files** (Zeilen auf `0b418644`):
- Modify: `custom_components/irrigation_plus/run_state.py:38, 74-75, 93` (Import `run_finish_grace_seconds` aus `.run_watch`; `_self_closing_run_in_flight`: Docstring-Absatz und nicht-wartendes Fenster `planned + run_finish_grace_seconds(run)`)
- Test: `tests/test_run_in_flight.py` (neuer Modul-Helfer `_service_run`, drei neue Tests im Abschnitt „The lookup itself“ direkt nach `test_self_closing_record_past_its_window_does_not_count`)
- Test (unverändert, läuft mit): `tests/test_opensprinkler.py::test_a_queued_run_stays_in_flight_past_its_own_planned_window`, `tests/test_opensprinkler.py::test_once_watering_the_window_is_measured_from_the_observed_start`

Ziel: Ein bestätigter Service-Lauf zählt über sein geplantes Fenster hinaus als „in flight“, bis
seine Wartezeit vorbei ist (Spec Abschnitt 4, E3). Bisher endete das Fenster von
`_self_closing_run_in_flight` bei `planned`. Seit Task 3 lebt ein bestätigter Service-Lauf aber bis
`planned + 5 + Marge` (bei Default 609 s): Datensatz, Watcher und Backstop warten dort noch auf die
Aus-Meldung des Ventils. In dieser Lücke galt die Zone als frei. Ein zweiter Dispatch derselben Zone
passierte alle Wächter (`self_closing.py` `zone_run_in_flight`-Prüfung im Dispatch,
`irrigation.py`, `run_chain.py`, `batch.py`). Er ersetzte dann den noch nicht abgerechneten
Datensatz, oder der Backstop bzw. die Entprellung des alten Laufs rechnete ihn mitten in der
Confirm-Abfrage des neuen ab, mit dessen Pumpen-Freigabe und Zähler. Auch eine Berechnung in dieser
Zeit wurde nicht mehr aufgeschoben (`calculation.py`).

Neu: Das nicht-wartende Fenster ist `planned + run_finish_grace_seconds(run)`. Der Anker bleibt
unverändert (`RUN_OBSERVED_START`, sonst `RUN_STARTED`). Das Tor steckt vollständig in
`run_finish_grace_seconds` (Task 2): nur `RUN_MODE == service` UND `RUN_WATCH_ENTITY` UND
`RUN_LATENCY_MARGIN`. Write-only-Datensätze, Service-Datensätze von vor dem Update sowie Batch- und
OpenSprinkler-Datensätze bekommen 0 und behalten ihr Fenster. Der wartende Zweig
(`queue_deadline_seconds`) bleibt unberührt. Ein abgerechneter Lauf entfernt seinen Datensatz, die
Zone ist danach sofort frei.

Der Test-Harness der Datei baut den Koordinator mit `__new__` und einem `_FakeStore`. Die Uhr läuft
echt. Die Datensätze werden mit `dt_util.utcnow() - timedelta(...)` rückdatiert, wie im bestehenden
`test_self_closing_record_past_its_window_does_not_count`. Die Grenzen +605 und +610 liegen je mehr
als 1 s von 609 entfernt, die echte Laufzeit des Tests (Millisekunden) kann sie nicht kippen.

- [ ] **Step 1: Tests schreiben**

In `tests/test_run_in_flight.py` direkt nach `test_self_closing_record_past_its_window_does_not_count`
und vor `test_distributor_cycle_counts_for_its_members` einfügen. Neue Importe sind nicht nötig:
`dt_util` und `const` sind da, `timedelta` kommt wie im Bestand über `dt_util.dt.timedelta`. Der Code
steht so da, wie `black` die Datei formatiert (`uvx black tests/test_run_in_flight.py` meldete real
`1 file left unchanged.`).

Vorher:

```python
    coord.store.config.active_valve_runs = [stale]
    assert coord.zone_run_in_flight(1) is False


def test_distributor_cycle_counts_for_its_members(monkeypatch):
```

Nachher:

```python
    coord.store.config.active_valve_runs = [stale]
    assert coord.zone_run_in_flight(1) is False


def _service_run(started, *, watch_entity=None, margin=None):
    """A 600 s service record as dispatch persists it.

    A confirmed run carries RUN_WATCH_ENTITY and, since #139, the zone's
    latency margin frozen at dispatch; a write-only run carries neither, and a
    confirmed run persisted before the margin existed carries only the entity.
    """
    run = _sc_run(planned=600, started=started)
    run[const.RUN_MODE] = const.WATERING_MODE_SERVICE
    if watch_entity is not None:
        run[const.RUN_WATCH_ENTITY] = watch_entity
    if margin is not None:
        run[const.RUN_LATENCY_MARGIN] = margin
    return run


def test_a_confirmed_service_run_stays_in_flight_through_its_finish_grace(
    monkeypatch,
):
    """Past its plan, inside planned + debounce 5 + margin 4 = 609 (#139).

    The record, its watcher and its backstop all live through that grace; a
    zone reported idle inside it could be dispatched again, replacing the
    record that has not settled or having the old run finalised mid-confirm
    with the new run's pump hold and meter.
    """
    coord = _coord(monkeypatch)
    now = dt_util.utcnow()

    coord.store.config.active_valve_runs = [
        _service_run(
            now - dt_util.dt.timedelta(seconds=605),
            watch_entity="binary_sensor.flowing",
            margin=4,
        )
    ]
    assert coord.zone_run_in_flight(1) is True

    coord.store.config.active_valve_runs = [
        _service_run(
            now - dt_util.dt.timedelta(seconds=610),
            watch_entity="binary_sensor.flowing",
            margin=4,
        )
    ]
    assert coord.zone_run_in_flight(1) is False


def test_a_write_only_service_run_gets_no_finish_grace(monkeypatch):
    """Nothing watches a write-only valve close: its window is the plan."""
    coord = _coord(monkeypatch)
    coord.store.config.active_valve_runs = [
        _service_run(dt_util.utcnow() - dt_util.dt.timedelta(seconds=605))
    ]
    assert coord.zone_run_in_flight(1) is False


def test_a_service_run_persisted_before_the_margin_keeps_its_window(monkeypatch):
    """Confirmed, but dispatched by a build without the margin: no grace."""
    coord = _coord(monkeypatch)
    coord.store.config.active_valve_runs = [
        _service_run(
            dt_util.utcnow() - dt_util.dt.timedelta(seconds=605),
            watch_entity="binary_sensor.flowing",
        )
    ]
    assert coord.zone_run_in_flight(1) is False
```

Warum die Tests so gebaut sind:
- **Bestätigt, +605 / +610:** Der Lauf ist über dem Plan (600), aber in der Wartezeit (609), also in
  flight. Bei +610 ist er draußen. Die zweite Hälfte fängt eine zu lange Wartezeit (Probe
  `grace-doubled`).
- **Write-only, +605:** ohne `RUN_WATCH_ENTITY` und ohne Marge, so wie der Dispatch aus Task 3 ihn
  schreibt. Nicht in flight.
- **Vor dem Update, +605:** `RUN_WATCH_ENTITY` ohne Marge. Nicht in flight.
- Die beiden Negativ-Tests sind Pins, am Elternstand grün. Dass sie beißen, zeigt die Probe
  `grace-for-every-record`.
- Der wartende OpenSprinkler-Datensatz ist durch die bestehenden Tests in `tests/test_opensprinkler.py`
  gedeckt (Step 6).

- [ ] **Step 2: Tests laufen lassen, Fehlschlag bestätigen**

```bash
cd /d/Entwicklung/HASI/HAsmartirrigation
mkdir -p D:/Entwicklung/HASI/pr139-work/tmp D:/Entwicklung/HASI/pr139-work/npm-cache && export TEMP=D:/Entwicklung/HASI/pr139-work/tmp TMP=D:/Entwicklung/HASI/pr139-work/tmp TMPDIR=D:/Entwicklung/HASI/pr139-work/tmp npm_config_cache=D:/Entwicklung/HASI/pr139-work/npm-cache
./.venv/Scripts/python.exe -m pytest tests/test_run_in_flight.py -p _local_socket_unblock -q -k "finish_grace or write_only_service or persisted_before_the_margin"
```

Erwartet (real beobachtet):

```
E   assert False is True
E    +  where False = zone_run_in_flight(1)
FAILED tests/test_run_in_flight.py::test_a_confirmed_service_run_stays_in_flight_through_its_finish_grace
================= 1 failed, 2 passed, 19 deselected in 1.51s ==================
```

Der bestätigte Lauf gilt bei +605 als frei, das ist die Lücke. Grün sind nur die zwei Pins.

- [ ] **Step 3: `run_state.py` — Import, Docstring und Fenster**

Import. Vorher:

```python
from . import const
from .opensprinkler import queue_deadline_seconds
from .run_watch import run_is_queue_bound
```

Nachher:

```python
from . import const
from .opensprinkler import queue_deadline_seconds
from .run_watch import run_finish_grace_seconds, run_is_queue_bound
```

`run_state.py` importierte `.run_watch` schon vorher, es entsteht also kein neuer Importzyklus.

`_self_closing_run_in_flight`, Ende des Docstrings. Vorher:

```python
        accepted. So it measures from ``RUN_OBSERVED_START`` once the station is
        seen running, and until then treats the run as in flight for as long as it
        could plausibly still be waiting (:func:`queue_deadline_seconds`).
        """
        config = getattr(self.store, "config", None)
```

Nachher:

```python
        accepted. So it measures from ``RUN_OBSERVED_START`` once the station is
        seen running, and until then treats the run as in flight for as long as it
        could plausibly still be waiting (:func:`queue_deadline_seconds`).

        A confirmed service run stays in flight past its plan for its finish
        grace (debounce + frozen latency margin, :func:`run_finish_grace_seconds`,
        #139), because the run is not over when the window is: its record, its
        watcher and its backstop all live through that grace, waiting for the
        valve's own off report. A second dispatch inside it would replace the
        record that has not settled yet, or let the old run's backstop or
        debounce finalise it mid-confirm with the new run's pump hold and meter.
        Every other record (write-only, pre-update, batch, OpenSprinkler) has a
        grace of 0 and keeps its plain window.
        """
        config = getattr(self.store, "config", None)
```

Fenster. Vorher:

```python
            observed = run.get(const.RUN_OBSERVED_START)
            queued = run_is_queue_bound(run)
            window = queue_deadline_seconds(runs, run) if queued else planned
            anchor = dt_util.parse_datetime(
```

Nachher:

```python
            observed = run.get(const.RUN_OBSERVED_START)
            queued = run_is_queue_bound(run)
            window = (
                queue_deadline_seconds(runs, run)
                if queued
                else planned + run_finish_grace_seconds(run)
            )
            anchor = dt_util.parse_datetime(
```

- [ ] **Step 4: Tests grün**

```bash
cd /d/Entwicklung/HASI/HAsmartirrigation
mkdir -p D:/Entwicklung/HASI/pr139-work/tmp D:/Entwicklung/HASI/pr139-work/npm-cache && export TEMP=D:/Entwicklung/HASI/pr139-work/tmp TMP=D:/Entwicklung/HASI/pr139-work/tmp TMPDIR=D:/Entwicklung/HASI/pr139-work/tmp npm_config_cache=D:/Entwicklung/HASI/pr139-work/npm-cache
./.venv/Scripts/python.exe -m pytest tests/test_run_in_flight.py -p _local_socket_unblock -q
```

Erwartet (real beobachtet, ohne Errors):

```
============================= 22 passed in 1.63s ==============================
```

22 = 19 bestehende + 3 neue Tests.

- [ ] **Step 5: Lint**

```bash
cd /d/Entwicklung/HASI/HAsmartirrigation
uvx black custom_components/irrigation_plus/
uvx ruff check custom_components/irrigation_plus/
```

Erwartet (real beobachtet):

```
67 files left unchanged.
All checks passed!
```

Die Klammerung des Fensters in Step 3 ist schon die Form, die `black` erzeugt (die einzeilige Fassung
wäre länger als 88 Zeichen). ruff (I) akzeptiert die alphabetische Reihenfolge
`run_finish_grace_seconds, run_is_queue_bound`.

- [ ] **Step 6: Verwandte Suiten**

```bash
cd /d/Entwicklung/HASI/HAsmartirrigation
mkdir -p D:/Entwicklung/HASI/pr139-work/tmp D:/Entwicklung/HASI/pr139-work/npm-cache && export TEMP=D:/Entwicklung/HASI/pr139-work/tmp TMP=D:/Entwicklung/HASI/pr139-work/tmp TMPDIR=D:/Entwicklung/HASI/pr139-work/tmp npm_config_cache=D:/Entwicklung/HASI/pr139-work/npm-cache
./.venv/Scripts/python.exe -m pytest tests/test_run_in_flight.py tests/test_service_watch.py tests/test_self_closing.py tests/test_opensprinkler.py tests/test_observed_watering.py tests/test_service_chain.py -p _local_socket_unblock -q
```

Erwartet (real beobachtet):

```
======================= 246 passed, 15 errors in 19.35s =======================
```

Am Elternstand (Task 8, Revisions-Probelauf `dry2` nach dem Feinschliff, Commit `b503b663`) liefen dieselben sechs Dateien mit `243 passed, 15 errors in 19.03s`.
246 = 243 + 3 neue Tests. `FAILED` gibt es in keinem Lauf. Die 15 Errors sind ausnahmslos
`Failed: Lingering timer after job ...` beim Teardown (lokale HA 2024.12.5). Sie verteilen sich so:
- 13 in `tests/test_opensprinkler.py`
- 1 in `tests/test_service_chain.py`
- 1 in `tests/test_service_watch.py`

Die sortierten `FAILED`/`ERROR`-Zeilen beider Läufe sind identisch (`diff` leer). Die beiden
OpenSprinkler-In-flight-Tests (wartender Lauf über seinem Fenster, Fenster ab `RUN_OBSERVED_START`)
sind in beiden Läufen grün. Ihre Datensätze haben keine Marge, und die OpenSprinkler-Policy setzt
`settles_on_valve_window` nicht.

Vergleichslauf am Elternstand: Block aus Task 0, Step 6 mit `P=$(git rev-parse HEAD)` (vor dem Commit
dieses Tasks = Commit von Task 8) und
`FILES="tests/test_run_in_flight.py tests/test_service_watch.py tests/test_self_closing.py tests/test_opensprinkler.py tests/test_observed_watering.py tests/test_service_chain.py"`;
erwartet `FAILED-ERROR-same`.

- [ ] **Step 7: Mutationsprobe**

Verfahren aus Task 0, Step 5: `mutate.py`, Suchtexte mit `\n`, Sicherung
`D:/Entwicklung/HASI/pr139-work/mut/t09-<probe>.bak` für `custom_components/irrigation_plus/run_state.py`, nach
jeder Probe Wiederherstellung aus der `.bak` und SHA-256-Prüfung (Pflicht), `git diff --stat` wie vor der
Probe. Suchtext aller drei Proben ist `else planned + run_finish_grace_seconds(run)` (genau einmal in der
Datei), den Ersatz nennt die Tabelle. Lauf für alle Proben:
`tests/test_run_in_flight.py -k "finish_grace or write_only_service or persisted_before_the_margin"`.

| Probe | Mutation | Beobachtet |
|---|---|---|
| drop-grace | `else planned + run_finish_grace_seconds(run)` → `else planned` (Stand vor dem Task) | FAIL (1: `confirmed_service_run_stays_in_flight_through_its_finish_grace`) `assert False is True` |
| grace-for-every-record | → `else planned + float(const.SERVICE_WATCH_SETTLE_SECONDS + const.DEFAULT_LATENCY_MARGIN_SECONDS)` (Wartezeit auch ohne Tor) | FAIL (2: `write_only_service_run_gets_no_finish_grace`, `service_run_persisted_before_the_margin_keeps_its_window`) `assert True is False` (2×); der positive Test bleibt grün |
| grace-doubled | → `else planned + 2 * run_finish_grace_seconds(run)` (zu lange Wartezeit) | FAIL (1: `confirmed_service_run_stays_in_flight_through_its_finish_grace`, Hälfte +610) `assert True is False` |

3 von 3 Proben wurden gefangen. Jeder neue Test scheitert an mindestens einer Probe:
- `confirmed_service_run_stays_in_flight_through_its_finish_grace`: `drop-grace` (+605), `grace-doubled` (+610).
- `write_only_service_run_gets_no_finish_grace`: `grace-for-every-record`.
- `service_run_persisted_before_the_margin_keeps_its_window`: `grace-for-every-record`.

Nach allen Proben meldete jede Wiederherstellung `restored=True` (SHA-256 gleich dem Ausgangsstand,
`run_state.py` `14ebf9db…`). Die MD5 von `git diff` war vor und nach den Proben identisch
(`2833162248c6dc67bc7a18c398c160ba`), und `git diff --stat` zeigte wieder
`run_state.py | 18 ++++++-` und `tests/test_run_in_flight.py | 69 ++++++++++`.

- [ ] **Step 8: Commit**

```bash
cd /d/Entwicklung/HASI/HAsmartirrigation
git add custom_components/irrigation_plus/run_state.py tests/test_run_in_flight.py
git commit -F - <<'EOF'
feat(service): keep a confirmed run in flight through its finish grace

A confirmed service run now waits planned + debounce + margin for its
valve to report the close (#139), but _self_closing_run_in_flight still
ended the in-flight window at planned. Inside the grace the zone read as
idle while its record, watcher and backstop were all still live, so a
second dispatch passed every guard: it replaced the unsettled record, or
the old run's backstop or debounce finalised it mid-confirm with the new
run's pump hold and meter. A calculation landing there was no longer
deferred either.

The non-queued window is now planned + run_finish_grace_seconds(run).
Records without a frozen margin (write-only, pre-update) and batch or
OpenSprinkler records have grace 0 and keep their window; the queued
OpenSprinkler deadline is untouched.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
```

Erwartet (real beobachtet): `2 files changed, 85 insertions(+), 2 deletions(-)`.

**Neue Test-Helfer:** in `tests/test_run_in_flight.py`
- `_service_run(started, *, watch_entity=None, margin=None)` baut einen 600-s-Service-Datensatz auf
  `_sc_run` (`RUN_MODE = service`). Mit `watch_entity` und `margin` ist er bestätigt wie nach Task 3,
  ohne beide write-only, mit nur `watch_entity` ein Datensatz von vor dem Update. `started` ist ein
  `datetime` (UTC). Der Helfer passt zu `_coord(monkeypatch)` dieser Datei, nicht zu `_coord(hass)` aus
  `tests/test_service_watch.py`.

---

### Task 10: Der Zeitfenster-Preis trägt die Wartezeit

**Files** (Zeilen auf `0b418644`):
- Modify: `custom_components/irrigation_plus/run_window.py:38-39, 350-351, 358` (Import `zone_finish_grace_seconds` aus `.run_watch`; `zone_confirm_seconds`: Docstring-Absatz und Rückgabe des Self-Closing-Tracks mit `confirm_entity`)
- Test: `tests/test_confirm_reserve.py` (Pin in `test_a_self_closing_zone_pays_only_with_a_confirm_entity` angepasst; zwei neue Tests in `TestZoneConfirmSeconds`; ein neuer Test in `TestTheDialAgreesWithTheArm`)

Ziel: Der Zeitfenster-Preis rechnet bei einer bestätigten Service-Zone die Wartezeit mit (Spec
Abschnitt 4, E3, Test 11). `zone_confirm_seconds` bepreiste eine Service-Zone mit `confirm_entity`
bisher nur mit der Confirm-Abfrage (`VALVE_CONFIRM_TIMEOUT` = 30 s). Seit Task 3 bis 8 schließt ein
bestätigter Lauf aber erst bis zu Entprellung + Marge nach seinem geplanten Fenster ab. Der Watcher
wartet auf die Aus-Meldung des Ventils plus 5 s, der Backstop feuert bei `planned + 5 + Marge`. Eine
Service-Kette geht erst dann zur nächsten Zone weiter (`run_chain.py`). Finish-Anker und
Arm-Schranke (#140, `scheduler.py`) lesen diesen Preis über `ZoneRun.confirm_seconds`
(`run_window.py` `nominal_demand_seconds`, `irrigation.py` Plan-Aufbau). Unter `sequential` wird er
je Zone summiert, unter `parallel` gilt das Maximum. Ohne die Wartezeit war eine sequentielle
Service-Kette je Zone um 9 s (Default) unterbepreist, und die Deadline schnitt ihren Schwanz ab.

Abtrennbar (Nutzerentscheidung 2026-09-15): Dieser Commit lässt sich auf #139 allein streichen. Im
Revisions-Probelauf geprüft: konfliktfrei (Task 11 und 12 rebasen unverändert), danach `224 passed, 1 error`
in den sieben Service-Suiten; Befehl und Zahlen in Task 13, Step 8.

Neu: Der Self-Closing-Track mit `confirm_entity` liefert
`float(const.VALVE_CONFIRM_TIMEOUT) + zone_finish_grace_seconds(zone)`. Das Tor steckt in
`zone_finish_grace_seconds` (Task 2): nur `WATERING_MODE_SERVICE` UND `confirm_entity`, dann
`SERVICE_WATCH_SETTLE_SECONDS + zone_latency_margin(zone)` (Marge auf 0 bis 30 begrenzt). Station
und Batch zweigen in `zone_confirm_seconds` schon vorher mit 0 ab, eine klassische Zone erreicht den
Zweig nie. `run_window.py` importierte `self_closing` schon, und das importiert `run_watch`. Der neue
Import erzeugt also keinen Zyklus (`run_watch.py` importiert auf Modulebene nur `const`).

Pins aus der Spec (`tests/test_confirm_reserve.py` 193, 219, 264, 278, am Elternstand geprüft):
- **193** `test_a_classic_zone_pays_the_poll`: klassische Zone mit `linked_entity` → 30.
  **Unverändert.** Der Classic-Track bekommt keine Wartezeit, sein Runner schließt das Ventil selbst.
- **219** `test_a_self_closing_zone_pays_only_with_a_confirm_entity`: Service-Zone mit
  `confirm_entity`, ohne `latency_margin` → bisher 30, **neu 30 + 5 + 4 = 39**. Der Wert ohne
  Feld ist `DEFAULT_LATENCY_MARGIN_SECONDS` = 4. Einziger Pin, der sich ändert.
- **264** `test_the_dial_carries_the_confirm_too`: `_zone()` dieser Klasse ist klassisch
  (`WATERING_MODE_CLASSIC`, `linked_entity`) → 600 + 30. **Unverändert.**
- **278** `test_the_dial_prices_a_flow_zone_at_the_measured_rate`: dieselbe klassische Zone mit
  Durchflusssensor → 1200 + 30. **Unverändert.**

Die übrigen Test-Dateien, die `VALVE_CONFIRM_TIMEOUT` als Preis pinnen
(`test_nominal_demand_projection.py`, `test_run_plan_pricing.py`,
`test_live_estimate_replayed_balance.py`), benutzen keine Service-Zone mit `confirm_entity`. Das
belegt Step 6 (keine Änderung im Ergebnis). `test_finish_anchor_hardware_window.py` lässt
`confirm_entity` bei Service-Zonen absichtlich weg (Docstring von `_zone`). Seine Batch-Zonen tragen
eins, liegen aber auf `TRACK_BATCH`.

- [ ] **Step 1: Tests schreiben und den Pin anpassen**

In `tests/test_confirm_reserve.py`, Klasse `TestZoneConfirmSeconds`. Neue Importe sind nicht nötig
(`const` und `zone_confirm_seconds` sind da). Der Code steht so da, wie `black` die Datei formatiert
(`uvx black tests/test_confirm_reserve.py` meldete real `1 file left unchanged.`).

Vorher:

```python
    def test_a_self_closing_zone_pays_only_with_a_confirm_entity(self):
        """With none it is credited optimistically and nothing polls."""
        base = {
            const.ZONE_LINKED_ENTITY: "switch.z",
            const.ZONE_WATERING_MODE: const.WATERING_MODE_SERVICE,
        }
        assert zone_confirm_seconds(base) == 0.0
        assert (
            zone_confirm_seconds(
                {**base, const.ZONE_CONFIRM_ENTITY: "binary_sensor.flowing"}
            )
            == const.VALVE_CONFIRM_TIMEOUT
        )

    def test_every_track_has_an_answer(self):
```

Nachher:

```python
    def test_a_self_closing_zone_pays_only_with_a_confirm_entity(self):
        """With none it is credited optimistically and nothing polls, and
        nothing waits for its close either: 0, not the finish grace."""
        base = {
            const.ZONE_LINKED_ENTITY: "switch.z",
            const.ZONE_WATERING_MODE: const.WATERING_MODE_SERVICE,
        }
        assert zone_confirm_seconds(base) == 0.0
        assert (
            zone_confirm_seconds(
                {**base, const.ZONE_CONFIRM_ENTITY: "binary_sensor.flowing"}
            )
            == const.VALVE_CONFIRM_TIMEOUT
            + const.SERVICE_WATCH_SETTLE_SECONDS
            + const.DEFAULT_LATENCY_MARGIN_SECONDS
        )

    def test_a_confirmed_service_zone_carries_its_finish_grace(self):
        """The poll, then the debounce and the zone's latency margin (#139).

        A service chain moves on only when the run settles, and a confirmed run
        settles up to debounce + margin past its window: the watcher waits for
        the valve's own off report plus the debounce, the backstop for planned +
        debounce + margin. Priced at the poll alone, a sequential chain under a
        finish anchor overruns by that much per zone.
        """
        zone = {
            const.ZONE_LINKED_ENTITY: "switch.z",
            const.ZONE_WATERING_MODE: const.WATERING_MODE_SERVICE,
            const.ZONE_CONFIRM_ENTITY: "binary_sensor.flowing",
        }
        # 30 poll + 5 debounce + 4 default margin.
        assert zone_confirm_seconds(zone) == 39.0
        # Margin 0 still waits out the debounce: 30 + 5.
        assert zone_confirm_seconds({**zone, const.ZONE_LATENCY_MARGIN: 0}) == 35.0
        # The zone's own margin, not the default: 30 + 5 + 10.
        assert zone_confirm_seconds({**zone, const.ZONE_LATENCY_MARGIN: 10}) == 45.0

    def test_the_grace_stays_on_the_service_track(self):
        """Batch and station zones settle on their own policies, and a classic
        zone's runner closes the valve itself: a confirm_entity and a margin on
        any of them price exactly as before."""
        extra = {
            const.ZONE_LINKED_ENTITY: "switch.z",
            const.ZONE_CONFIRM_ENTITY: "binary_sensor.flowing",
            const.ZONE_LATENCY_MARGIN: 10,
        }
        batch = {**extra, const.ZONE_WATERING_MODE: const.WATERING_MODE_BATCH}
        station = {
            **extra,
            const.ZONE_WATERING_MODE: const.WATERING_MODE_OPENSPRINKLER,
        }
        classic = {**extra, const.ZONE_WATERING_MODE: const.WATERING_MODE_CLASSIC}
        assert zone_confirm_seconds(batch) == 0.0
        assert zone_confirm_seconds(station) == 0.0
        assert zone_confirm_seconds(classic) == const.VALVE_CONFIRM_TIMEOUT

    def test_every_track_has_an_answer(self):
```

In derselben Datei, Klasse `TestTheDialAgreesWithTheArm`. Vorher:

```python
    def test_the_dial_carries_the_confirm_too(self):
        one = self._nominal([self._zone()])
        assert one == 600 + const.VALVE_CONFIRM_TIMEOUT

    def test_the_dial_prices_a_flow_zone_at_the_measured_rate(self):
```

Nachher:

```python
    def test_the_dial_carries_the_confirm_too(self):
        one = self._nominal([self._zone()])
        assert one == 600 + const.VALVE_CONFIRM_TIMEOUT

    def test_the_dial_carries_a_confirmed_service_zones_finish_grace(self):
        """Two confirmed service zones in sequence each pay poll + grace."""
        service = {
            const.ZONE_WATERING_MODE: const.WATERING_MODE_SERVICE,
            const.ZONE_CONFIRM_ENTITY: "binary_sensor.flowing",
        }
        two = self._nominal(
            [self._zone(**service), self._zone(**{**service, const.ZONE_ID: 2})]
        )
        # 2 x (600 s water + 30 poll + 5 debounce + 4 margin).
        assert two == 2 * (600 + 39)

    def test_the_dial_prices_a_flow_zone_at_the_measured_rate(self):
```

Warum die Tests so gebaut sind:
- **Pin 219** rechnet mit den Konstanten und zeigt so die Herkunft der 39. Der neue Test nennt die
  Zahlen wörtlich (39,0 / 35,0 / 45,0), damit eine stille Änderung an einer Konstante auffällt.
- **Marge 0 und 10** belegen, dass die Marge der Zone gelesen wird und nicht der Default. Die 5 s
  Entprellung bleiben auch bei Marge 0.
- **`test_the_grace_stays_on_the_service_track`** ist ein Pin, am Elternstand grün. Batch, Station und
  klassische Zone tragen hier bewusst `confirm_entity` UND eine Marge. Die bestehenden Station- und
  Classic-Tests haben kein `confirm_entity`, sie fingen ein Durchsickern der Wartezeit nicht (Proben
  `grace-leaks-to-batch-station`, `grace-leaks-to-classic`).
- **Zifferblatt-Test**: zwei bestätigte Service-Zonen unter `sequential` (`_nominal` dieser Klasse)
  über `nominal_demand_seconds`, also denselben Weg wie Finish-Anker und Arm. Er zeigt, dass die
  Wartezeit je Zone summiert wird und die Service-Zone ohne `ZONE_DURATION_UNIT` nicht umgerechnet
  wird (600 s bleiben 600 s).

- [ ] **Step 2: Tests laufen lassen, Fehlschlag bestätigen**

```bash
cd /d/Entwicklung/HASI/HAsmartirrigation
mkdir -p D:/Entwicklung/HASI/pr139-work/tmp D:/Entwicklung/HASI/pr139-work/npm-cache && export TEMP=D:/Entwicklung/HASI/pr139-work/tmp TMP=D:/Entwicklung/HASI/pr139-work/tmp TMPDIR=D:/Entwicklung/HASI/pr139-work/tmp npm_config_cache=D:/Entwicklung/HASI/pr139-work/npm-cache
./.venv/Scripts/python.exe -m pytest tests/test_confirm_reserve.py -p _local_socket_unblock -q
```

Erwartet (real beobachtet):

```
E   AssertionError: assert 30.0 == ((30 + 5) + 4)
E   AssertionError: assert 30.0 == 39.0
E   assert 1260.0 == (2 * (600 + 39))
FAILED tests/test_confirm_reserve.py::TestZoneConfirmSeconds::test_a_self_closing_zone_pays_only_with_a_confirm_entity
FAILED tests/test_confirm_reserve.py::TestZoneConfirmSeconds::test_a_confirmed_service_zone_carries_its_finish_grace
FAILED tests/test_confirm_reserve.py::TestTheDialAgreesWithTheArm::test_the_dial_carries_a_confirmed_service_zones_finish_grace
======================== 3 failed, 22 passed in 2.55s =========================
```

Das Zifferblatt zeigt 1260 = 2 × (600 + 30): die Wartezeit fehlt je Zone. Grün ist der Pin
`test_the_grace_stays_on_the_service_track`.

- [ ] **Step 3: `run_window.py` — Import, Docstring und Rückgabe**

Import. Vorher:

```python
from .opensprinkler import is_opensprinkler_zone
from .self_closing import is_self_closing_zone
```

Nachher:

```python
from .opensprinkler import is_opensprinkler_zone
from .run_watch import zone_finish_grace_seconds
from .self_closing import is_self_closing_zone
```

`zone_confirm_seconds`, Ende des Docstrings und Self-Closing-Zweig. Vorher:

```python
    Zero for the dispatches that never poll. A station is opened by the
    controller, and one sitting in its queue is not running at +30s anyway, so
    the runner deliberately does not poll it. A self-closing valve with no
    confirm entity is credited optimistically, because the service that drives
    it is momentary and polling it would report off for the whole window.
    """
    track = track_for_zone(zone)
    if track in (TRACK_STATION, TRACK_BATCH):
        return 0.0
    if track == TRACK_SELF_CLOSING:
        if not zone.get(const.ZONE_CONFIRM_ENTITY):
            return 0.0
        return float(const.VALVE_CONFIRM_TIMEOUT)
    if not zone.get(const.ZONE_LINKED_ENTITY):
        return 0.0
    return float(const.VALVE_CONFIRM_TIMEOUT)
```

Nachher:

```python
    Zero for the dispatches that never poll. A station is opened by the
    controller, and one sitting in its queue is not running at +30s anyway, so
    the runner deliberately does not poll it. A self-closing valve with no
    confirm entity is credited optimistically, because the service that drives
    it is momentary and polling it would report off for the whole window.

    A confirmed service valve also carries its finish grace
    (:func:`zone_finish_grace_seconds`: debounce + the zone's latency margin,
    #139). A service chain moves on to the next zone only when the run settles,
    and a confirmed run settles up to that grace past its window: the watcher
    waits for the valve's own off report plus the debounce, the backstop for
    planned + debounce + margin. It is priced at that ceiling for the same reason
    the poll is. Batch and station zones branch off above, so the grace stays on
    the one track whose runs actually wait for it.
    """
    track = track_for_zone(zone)
    if track in (TRACK_STATION, TRACK_BATCH):
        return 0.0
    if track == TRACK_SELF_CLOSING:
        if not zone.get(const.ZONE_CONFIRM_ENTITY):
            return 0.0
        return float(const.VALVE_CONFIRM_TIMEOUT) + zone_finish_grace_seconds(zone)
    if not zone.get(const.ZONE_LINKED_ENTITY):
        return 0.0
    return float(const.VALVE_CONFIRM_TIMEOUT)
```

- [ ] **Step 4: Tests grün**

```bash
cd /d/Entwicklung/HASI/HAsmartirrigation
mkdir -p D:/Entwicklung/HASI/pr139-work/tmp D:/Entwicklung/HASI/pr139-work/npm-cache && export TEMP=D:/Entwicklung/HASI/pr139-work/tmp TMP=D:/Entwicklung/HASI/pr139-work/tmp TMPDIR=D:/Entwicklung/HASI/pr139-work/tmp npm_config_cache=D:/Entwicklung/HASI/pr139-work/npm-cache
./.venv/Scripts/python.exe -m pytest tests/test_confirm_reserve.py -p _local_socket_unblock -q
```

Erwartet (real beobachtet):

```
============================= 25 passed in 1.65s ==============================
```

25 = 22 bestehende + 3 neue Tests (der angepasste Pin zählt zu den bestehenden).

- [ ] **Step 5: Lint**

```bash
cd /d/Entwicklung/HASI/HAsmartirrigation
uvx black custom_components/irrigation_plus/
uvx ruff check custom_components/irrigation_plus/
```

Erwartet (real beobachtet):

```
67 files left unchanged.
All checks passed!
```

Die neue Rückgabezeile ist 83 Zeichen lang und bleibt unter der Grenze von 88. ruff (I) akzeptiert
`.run_watch` zwischen `.opensprinkler` und `.self_closing`.

- [ ] **Step 6: Verwandte Suiten**

Es gibt keine `tests/test_skip_conditions*.py`. Mitgenommen sind die beiden `test_scheduler*.py`
und jede Datei, die den Confirm-Preis pinnt oder `zone_confirm_seconds` indirekt über
`nominal_demand_seconds` bzw. den Plan-Aufbau erreicht:

```bash
cd /d/Entwicklung/HASI/HAsmartirrigation
mkdir -p D:/Entwicklung/HASI/pr139-work/tmp D:/Entwicklung/HASI/pr139-work/npm-cache && export TEMP=D:/Entwicklung/HASI/pr139-work/tmp TMP=D:/Entwicklung/HASI/pr139-work/tmp TMPDIR=D:/Entwicklung/HASI/pr139-work/tmp npm_config_cache=D:/Entwicklung/HASI/pr139-work/npm-cache
./.venv/Scripts/python.exe -m pytest tests/test_confirm_reserve.py tests/test_run_window.py tests/test_run_window_batch.py tests/test_finish_anchor_hardware_window.py tests/test_scheduler.py tests/test_scheduler_distributor.py tests/test_nominal_demand_projection.py tests/test_run_plan_pricing.py tests/test_sunrise_anchored_fitting.py tests/test_live_estimate_replayed_balance.py -p _local_socket_unblock -q
```

Erwartet (real beobachtet):

```
================= 399 passed, 8 warnings, 96 errors in 36.05s =================
```

Am Elternstand (Task 9, Revisions-Probelauf `dry2`, Commit `4703dc23` vor dem Feinschliff; `run_window.py` und
die zehn Testdateien sind am Commit nach dem Feinschliff `ce7a1d13` byte-gleich, `git diff --stat` leer) liefen dieselben zehn Dateien mit
`396 passed, 8 warnings, 96 errors in 35.43s`. Im Probelauf lief dieser Vergleich vor der Änderung am
selben, sauberen Worktree. Im echten Lauf: Vergleichslauf am Elternstand mit dem Block aus Task 0, Step 6,
`P=$(git rev-parse HEAD)` (vor dem Commit dieses Tasks = Commit von Task 9) und
`FILES="tests/test_confirm_reserve.py tests/test_run_window.py tests/test_run_window_batch.py tests/test_finish_anchor_hardware_window.py tests/test_scheduler.py tests/test_scheduler_distributor.py tests/test_nominal_demand_projection.py tests/test_run_plan_pricing.py tests/test_sunrise_anchored_fitting.py tests/test_live_estimate_replayed_balance.py"`;
erwartet `FAILED-ERROR-same`. 399 = 396 + 3 neue Tests. `FAILED` gibt es in keinem Lauf. Die sortierten
`FAILED`/`ERROR`-Zeilen beider Läufe sind identisch (`diff` leer). Alle 96 Errors sind
`Failed: Lingering timer after test ...` beim Teardown (lokale HA 2024.12.5, Timer
`_reset_event_fired_today`), per `--junitxml` ausgezählt:
- 94 in `tests/test_live_estimate_replayed_balance.py`
- 2 in `tests/test_finish_anchor_hardware_window.py`

Gegenprobe über die Service-Suiten, die `zone_confirm_seconds` über den Runner-Plan erreichen:

```bash
cd /d/Entwicklung/HASI/HAsmartirrigation
mkdir -p D:/Entwicklung/HASI/pr139-work/tmp D:/Entwicklung/HASI/pr139-work/npm-cache && export TEMP=D:/Entwicklung/HASI/pr139-work/tmp TMP=D:/Entwicklung/HASI/pr139-work/tmp TMPDIR=D:/Entwicklung/HASI/pr139-work/tmp npm_config_cache=D:/Entwicklung/HASI/pr139-work/npm-cache
./.venv/Scripts/python.exe -m pytest tests/test_run_in_flight.py tests/test_service_watch.py tests/test_self_closing.py tests/test_opensprinkler.py tests/test_observed_watering.py tests/test_service_chain.py -p _local_socket_unblock -q
```

Erwartet (real beobachtet):

```
======================= 246 passed, 15 errors in 19.36s =======================
```

Das ist genau der Stand aus Task 9 Step 6 (dort ebenfalls `246 passed, 15 errors`, alles
Lingering-Timer-Teardowns). Task 10 ändert dort nichts.

- [ ] **Step 7: Mutationsprobe**

Verfahren aus Task 0, Step 5: `mutate.py`, Suchtexte mit `\n`, Sicherung
`D:/Entwicklung/HASI/pr139-work/mut/t10-<probe>.bak` für `custom_components/irrigation_plus/run_window.py`,
nach jeder Probe Wiederherstellung aus der `.bak` und SHA-256-Prüfung (Pflicht), `git diff --stat` wie vor
der Probe. Lauf je Probe: `tests/test_confirm_reserve.py`. Suchtext → Ersatz steht je Probe in der Tabelle;
jeder Suchtext kommt genau einmal vor. Die zwei `grace-leaks`-Proben brauchen mehrzeilige bzw. mit Zeilenende
abgegrenzte Suchtexte: `grace-leaks-to-batch-station` ersetzt
`    if track in (TRACK_STATION, TRACK_BATCH):\n        return 0.0\n` durch
`    if track in (TRACK_STATION, TRACK_BATCH):\n        return zone_finish_grace_seconds({**zone, const.ZONE_WATERING_MODE: const.WATERING_MODE_SERVICE})\n`,
`grace-leaks-to-classic` ersetzt die letzte Zeile `    return float(const.VALVE_CONFIRM_TIMEOUT)\n` (vier
Leerzeichen, direkt `\n`; die Service-Zeile darüber hat acht Leerzeichen und ` + …`) durch
`    return float(const.VALVE_CONFIRM_TIMEOUT) + zone_finish_grace_seconds({**zone, const.ZONE_WATERING_MODE: const.WATERING_MODE_SERVICE})\n`.
Beide liefen im Feinschliff mit genau diesen Suchtexten erneut am Commit `8d7ebbed` (real):
`1 failed, 24 passed`, `assert 15.0 == 0.0` bzw. `assert 45.0 == 30`, wie in der Tabelle.

| Probe | Mutation | Beobachtet |
|---|---|---|
| revert-to-poll | `return float(const.VALVE_CONFIRM_TIMEOUT) + zone_finish_grace_seconds(zone)` → `return float(const.VALVE_CONFIRM_TIMEOUT)` (Stand vor dem Task, die alten 30) | FAIL (3: `self_closing_zone_pays_only_with_a_confirm_entity` `assert 30.0 == ((30 + 5) + 4)`, `confirmed_service_zone_carries_its_finish_grace` `assert 30.0 == 39.0`, `dial_carries_a_confirmed_service_zones_finish_grace` `assert 1260.0 == (2 * (600 + 39))`), `3 failed, 22 passed` |
| margin-ignored | dieselbe Zeile → `return float(const.VALVE_CONFIRM_TIMEOUT) + float(const.SERVICE_WATCH_SETTLE_SECONDS + const.DEFAULT_LATENCY_MARGIN_SECONDS)` (Default statt Marge der Zone) | FAIL (1: `confirmed_service_zone_carries_its_finish_grace`) `assert 39.0 == 35.0`, `1 failed, 24 passed` |
| grace-leaks-to-batch-station | `if track in (TRACK_STATION, TRACK_BATCH): return 0.0` → `return zone_finish_grace_seconds({**zone, const.ZONE_WATERING_MODE: const.WATERING_MODE_SERVICE})` (Wartezeit für Batch/Station mit `confirm_entity`) | FAIL (1: `the_grace_stays_on_the_service_track`) `assert 15.0 == 0.0`, `1 failed, 24 passed`; der bestehende Station-Test (ohne `confirm_entity`) bleibt grün |
| grace-leaks-to-classic | letzte Zeile `return float(const.VALVE_CONFIRM_TIMEOUT)` → `return float(const.VALVE_CONFIRM_TIMEOUT) + zone_finish_grace_seconds({**zone, const.ZONE_WATERING_MODE: const.WATERING_MODE_SERVICE})` (Wartezeit für klassische Zone mit `confirm_entity`) | FAIL (1: `the_grace_stays_on_the_service_track`) `assert 45.0 == 30`, `1 failed, 24 passed`; die klassischen Pins 193/264/278 (ohne `confirm_entity`) bleiben grün |

4 von 4 Proben wurden gefangen. Jeder neue bzw. geänderte Test scheitert an mindestens einer Probe:
- `self_closing_zone_pays_only_with_a_confirm_entity` (Pin 219): `revert-to-poll`.
- `confirmed_service_zone_carries_its_finish_grace`: `revert-to-poll`, `margin-ignored`.
- `the_grace_stays_on_the_service_track`: `grace-leaks-to-batch-station`, `grace-leaks-to-classic`.
- `dial_carries_a_confirmed_service_zones_finish_grace`: `revert-to-poll`.

Jede Wiederherstellung meldete `restored True` (SHA-256 gleich dem Ausgangsstand, `run_window.py`
`b701c42930e6…`). Die MD5 von `git diff` war vor und nach den Proben identisch
(`a152a1f9cdb5d8c574d5d2a1ab00f3a2`), und `git diff --stat` zeigte wieder
`run_window.py | 12 +++++-` und `tests/test_confirm_reserve.py | 57 ++++++++++++++++++++++++-`.

- [ ] **Step 8: Commit**

```bash
cd /d/Entwicklung/HASI/HAsmartirrigation
git add custom_components/irrigation_plus/run_window.py tests/test_confirm_reserve.py
git commit -F - <<'EOF'
feat(service): price a confirmed service zone's finish grace into the window

zone_confirm_seconds priced a confirmed service zone at the valve-confirm
poll alone. Since #139 a confirmed run settles up to debounce + latency
margin past its planned window (the watcher on the valve's off report
plus the debounce, the backstop at planned + debounce + margin), and a
service chain moves on to the next zone only once the run settles. The
finish anchor and the arm bound therefore under-priced a sequential
service chain by that grace per zone, and the deadline cut its tail.

The self-closing track with a confirm_entity now returns
VALVE_CONFIRM_TIMEOUT + zone_finish_grace_seconds(zone): 39 s at the
default margin of 4. Write-only service zones, batch, station and classic
zones price exactly as before.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
```

Erwartet (real beobachtet): `2 files changed, 67 insertions(+), 2 deletions(-)`.

**Neue Test-Helfer:** keine. Die Tests nutzen die vorhandenen Klassen-Harnesses von
`tests/test_confirm_reserve.py`: Zonen-Dicts direkt für `zone_confirm_seconds`, sowie
`TestTheDialAgreesWithTheArm._zone(**over)` und `_nominal(zones)` (sequentiell, 300-s-Slots, keine
Absorption, metrisch) für das Zifferblatt.

---

### Task 11: Panel-Feld „Latenz-Marge" + vitest-Sichtbarkeitstor

Das Zonenfeld `latency_margin` (Backend seit Task 1) bekommt eine Zeile im Service-Block der
Zoneneinstellungen, direkt unter `confirm_entity`. Sichtbar nur mit gesetztem `confirm_entity`
(ohne Confirm gibt das Backend keine Wartezeit, `zone_finish_grace_seconds` = 0). Eingabe ganze
Sekunden 0–30 wie die Backend-Klemme. Dieser Task committet NUR Quellen; Übersetzungen und dist
folgen in Task 12. Bis dahin liefert `localize` für die zwei neuen Schlüssel `undefined`
(`localize.ts:86-90`: Sprache → en → `undefined`, ohne args direkt zurückgegeben), lit rendert das
leer — die Überschrift zeigt nur „(s)". Kein Build-Fehler (Schlüssel sind Strings).

**Files** (Zeilen auf `0b418644`):
- Modify: `custom_components/irrigation_plus/frontend/src/const.ts:173-174`
- Modify: `custom_components/irrigation_plus/frontend/src/types.ts:348-349`
- Modify: `custom_components/irrigation_plus/frontend/src/views/zones/view-zone-settings.ts:69-70, 217-218, 1312-1313`
- Test: `custom_components/irrigation_plus/frontend/src/views/zones/view-zone-settings-latency-margin.test.ts` (neu)

- [ ] **Step 1: Frontend-Abhängigkeiten installieren und vitest-Basis messen**

```bash
cd /d/Entwicklung/HASI/HAsmartirrigation/custom_components/irrigation_plus/frontend
mkdir -p D:/Entwicklung/HASI/pr139-work/tmp D:/Entwicklung/HASI/pr139-work/npm-cache && export TEMP=D:/Entwicklung/HASI/pr139-work/tmp TMP=D:/Entwicklung/HASI/pr139-work/tmp TMPDIR=D:/Entwicklung/HASI/pr139-work/tmp npm_config_cache=D:/Entwicklung/HASI/pr139-work/npm-cache
npm ci && npm test
```

Erwartet (Basis `0b418644`, Node 24.15.0):

```
 Test Files  22 passed (22)
      Tests  614 passed (614)
```

- [ ] **Step 2: Fehlschlagenden Test schreiben**

Neue Datei `custom_components/irrigation_plus/frontend/src/views/zones/view-zone-settings-latency-margin.test.ts`
(gleiches Stub-Muster wie `view-zone-settings-flow-counter-type.test.ts`):

```ts
import { describe, it, expect, beforeAll } from "vitest";

beforeAll(() => {
  (globalThis as any).HTMLElement = class {};
  (globalThis as any).customElements = {
    define() {},
    get() {
      return undefined;
    },
    whenDefined: () => Promise.resolve(),
  };
  (globalThis as any).window = globalThis;
});

type ViewModule = typeof import("./view-zone-settings");
let View: ViewModule["SmartIrrigationViewZoneSettings"];
beforeAll(async () => {
  ({ SmartIrrigationViewZoneSettings: View } =
    await import("./view-zone-settings"));
});

// #139: the latency margin only shapes runs the watcher can confirm, so the row
// is shown ONLY for a service zone with a confirm_entity. These tests cover the
// two methods the row is built on: the gate _showLatencyMargin and the input
// clamp _clampLatencyMargin. They do not render the template, so they do not
// prove that render() wires both into the service block; that is checked by
// hand in the panel.
function make() {
  const el: any = new View();
  el.hass = { language: "en", states: {} };
  return el;
}

describe("view-zone-settings latency_margin visibility gate", () => {
  it("shows when a confirm_entity is set", () => {
    const el = make();
    expect(
      el._showLatencyMargin({ confirm_entity: "binary_sensor.valve_flowing" }),
    ).toBe(true);
  });

  it("hides when confirm_entity is null", () => {
    const el = make();
    expect(el._showLatencyMargin({ confirm_entity: null })).toBe(false);
  });

  it("hides when confirm_entity is an empty string", () => {
    const el = make();
    expect(el._showLatencyMargin({ confirm_entity: "" })).toBe(false);
  });

  it("hides when confirm_entity is missing", () => {
    const el = make();
    expect(el._showLatencyMargin({})).toBe(false);
    expect(el._showLatencyMargin({ confirm_entity: undefined })).toBe(false);
  });
});

describe("view-zone-settings latency_margin input clamp", () => {
  it("keeps a whole number inside the range", () => {
    const el = make();
    expect(el._clampLatencyMargin(4)).toBe(4);
    expect(el._clampLatencyMargin(0)).toBe(0);
    expect(el._clampLatencyMargin(30)).toBe(30);
  });

  it("rounds to whole seconds", () => {
    const el = make();
    expect(el._clampLatencyMargin(2.6)).toBe(3);
    expect(el._clampLatencyMargin(2.4)).toBe(2);
  });

  it("clamps below 0 and above 30", () => {
    const el = make();
    expect(el._clampLatencyMargin(-3)).toBe(0);
    expect(el._clampLatencyMargin(45)).toBe(30);
  });

  it("ignores an empty or invalid input (NaN)", () => {
    const el = make();
    expect(el._clampLatencyMargin(NaN)).toBeNull();
  });
});
```

Reichweite des Tests: Er deckt die zwei Methoden ab, auf denen die Zeile aufbaut, das Tor
`_showLatencyMargin` und die Klemme `_clampLatencyMargin`. Das Template rendert vitest hier nicht. Dass
`render()` die Zeile im Service-Block hinter dieses Tor setzt und `@input` über die Klemme speichert,
belegt der Test also NICHT; das prüft die Panel-Kontrolle im Live-Test (Task 15). Der Kommentar im Test
sagt das so, statt eine Abdeckung der Sichtbarkeitsregel zu behaupten.

- [ ] **Step 3: Test laufen lassen — muss fehlschlagen**

```bash
cd /d/Entwicklung/HASI/HAsmartirrigation/custom_components/irrigation_plus/frontend
mkdir -p D:/Entwicklung/HASI/pr139-work/tmp D:/Entwicklung/HASI/pr139-work/npm-cache && export TEMP=D:/Entwicklung/HASI/pr139-work/tmp TMP=D:/Entwicklung/HASI/pr139-work/tmp TMPDIR=D:/Entwicklung/HASI/pr139-work/tmp npm_config_cache=D:/Entwicklung/HASI/pr139-work/npm-cache
npm test -- src/views/zones/view-zone-settings-latency-margin.test.ts
```

Erwartet:

```
 FAIL  src/views/zones/view-zone-settings-latency-margin.test.ts > view-zone-settings latency_margin visibility gate > shows when a confirm_entity is set
TypeError: el._showLatencyMargin is not a function
 FAIL  src/views/zones/view-zone-settings-latency-margin.test.ts > view-zone-settings latency_margin input clamp > clamps below 0 and above 30
TypeError: el._clampLatencyMargin is not a function
 Test Files  1 failed (1)
      Tests  8 failed (8)
```

- [ ] **Step 4: `const.ts` — Schlüssel neben den anderen Service-Schlüsseln**

Vorher:

```ts
export const ZONE_CONFIRM_ENTITY = "confirm_entity";
export const ZONE_OBSERVED_ENTITY = "observed_entity";
```

Nachher:

```ts
export const ZONE_CONFIRM_ENTITY = "confirm_entity";
export const ZONE_LATENCY_MARGIN = "latency_margin";
export const ZONE_OBSERVED_ENTITY = "observed_entity";
```

- [ ] **Step 5: `types.ts` — Feld im Zonen-Interface (`SmartIrrigationZone`) neben `confirm_entity`**

Vorher (Zonen-Interface, NICHT das Verteiler-Interface weiter unten mit `confirm_entity?` vor `flow_sensor?`):

```ts
  confirm_entity?: string | null;
  // Observed-watering (opt-in): physical valve/switch watched for EXTERNAL runs
```

Nachher:

```ts
  confirm_entity?: string | null;
  // Seconds a confirmed service valve may report its own close after the planned
  // window (whole seconds, 0-30, backend default 4). See ZONE_LATENCY_MARGIN.
  latency_margin?: number;
  // Observed-watering (opt-in): physical valve/switch watched for EXTERNAL runs
```

- [ ] **Step 6: `view-zone-settings.ts` — Import**

Vorher (Import-Block aus `../../const`):

```ts
  ZONE_CONFIRM_ENTITY,
  ZONE_OBSERVED_ENTITY,
  ZONE_SOIL_MOISTURE_SENSOR,
```

Nachher:

```ts
  ZONE_CONFIRM_ENTITY,
  ZONE_LATENCY_MARGIN,
  ZONE_OBSERVED_ENTITY,
  ZONE_SOIL_MOISTURE_SENSOR,
```

- [ ] **Step 7: `view-zone-settings.ts` — Tor und Klemme als Methoden direkt nach `_flowSensorIsTotalizer`**

Vorher:

```ts
    if (!unit || unit.includes("/")) return false;
    return !["gpm", "lpm", "gph", "lph"].includes(unit.toLowerCase());
  }

  firstUpdated() {
```

Nachher:

```ts
    if (!unit || unit.includes("/")) return false;
    return !["gpm", "lpm", "gph", "lph"].includes(unit.toLowerCase());
  }

  // #139: the latency margin only widens the finish backstop of a run the
  // watcher CONFIRMED. Without a confirm_entity nothing reports the valve's own
  // close, the backend applies no grace and the field would be a dead knob, so
  // the row is hidden. MUST mirror the backend gate `zone_finish_grace_seconds`
  // in run_watch.py (confirm_entity truthy); keep the two in sync.
  private _showLatencyMargin(zone: any): boolean {
    return !!zone?.confirm_entity;
  }

  // Whole seconds in [0, 30], the same bounds the backend clamps to
  // (MAX_LATENCY_MARGIN_SECONDS in const.py). null = empty or invalid input
  // (valueAsNumber is NaN while the field is cleared); the handler ignores it
  // instead of saving 0 mid-typing, like the lead_time input.
  private _clampLatencyMargin(v: number): number | null {
    if (isNaN(v)) return null;
    return Math.max(0, Math.min(30, Math.round(v)));
  }

  firstUpdated() {
```

- [ ] **Step 8: `view-zone-settings.ts` — Zeile im SERVICE-Block unter `confirm_entity`**

Nur im Block `${zone.watering_mode === "service" ? html` ... ` : ""}`, NICHT im Batch-Block
(der Batch-Block hat ebenfalls einen `ZONE_CONFIRM_ENTITY`-Picker, aber mit `includeDomains`
ohne `"number"` und gefolgt von `batch_valve_missing`). Eindeutiger Anker: das Ende des
`confirm_entity`-Pickers direkt vor `${this.config?.observed_watering_enabled`.

Vorher:

```ts
                                allow-custom-entity
                                @value-changed="${(e: CustomEvent) =>
                                  this.handleEditZone(index, {
                                    ...zone,
                                    [ZONE_CONFIRM_ENTITY]:
                                      e.detail.value || null,
                                  })}"
                              ></ha-entity-picker>
                            </ha-settings-row>
                            ${this.config?.observed_watering_enabled
```

Nachher:

```ts
                                allow-custom-entity
                                @value-changed="${(e: CustomEvent) =>
                                  this.handleEditZone(index, {
                                    ...zone,
                                    [ZONE_CONFIRM_ENTITY]:
                                      e.detail.value || null,
                                  })}"
                              ></ha-entity-picker>
                            </ha-settings-row>
                            ${this._showLatencyMargin(zone)
                              ? html`
                                  <ha-settings-row>
                                    <span slot="heading"
                                      >${localize(
                                        "panels.zones.labels.latency_margin",
                                        this.hass.language,
                                      )}
                                      (${UNIT_SECONDS})</span
                                    >
                                    <span slot="description"
                                      >${localize(
                                        "panels.zones.labels.latency_margin_help",
                                        this.hass.language,
                                      )}</span
                                    >
                                    <input
                                      type="number"
                                      class="settings-input shortfield"
                                      step="1"
                                      min="0"
                                      max="30"
                                      inputmode="numeric"
                                      .value="${zone.latency_margin ?? 4}"
                                      @input="${(e: Event) => {
                                        const v = this._clampLatencyMargin(
                                          (e.target as HTMLInputElement)
                                            .valueAsNumber,
                                        );
                                        if (v !== null)
                                          this.handleEditZone(index, {
                                            ...zone,
                                            [ZONE_LATENCY_MARGIN]: v,
                                          });
                                      }}"
                                    />
                                  </ha-settings-row>
                                `
                              : ""}
                            ${this.config?.observed_watering_enabled
```

- [ ] **Step 9: Test laufen lassen — muss grün sein**

```bash
cd /d/Entwicklung/HASI/HAsmartirrigation/custom_components/irrigation_plus/frontend
mkdir -p D:/Entwicklung/HASI/pr139-work/tmp D:/Entwicklung/HASI/pr139-work/npm-cache && export TEMP=D:/Entwicklung/HASI/pr139-work/tmp TMP=D:/Entwicklung/HASI/pr139-work/tmp TMPDIR=D:/Entwicklung/HASI/pr139-work/tmp npm_config_cache=D:/Entwicklung/HASI/pr139-work/npm-cache
npm test -- src/views/zones/view-zone-settings-latency-margin.test.ts
```

Erwartet:

```
 Test Files  1 passed (1)
      Tests  8 passed (8)
```

- [ ] **Step 10: Lint**

Keine Python-Datei geändert → `uvx black` / `uvx ruff` entfallen für diesen Task. Frontend-Lint
(eslint + prettier-Plugin über `src/**/*.ts`, inklusive der neuen Testdatei) läuft als erster
Teil von `npm run build` in Step 12; ein prettier-Einwand bricht den Build.

- [ ] **Step 11: Verwandte Suite — gesamtes vitest**

```bash
cd /d/Entwicklung/HASI/HAsmartirrigation/custom_components/irrigation_plus/frontend
mkdir -p D:/Entwicklung/HASI/pr139-work/tmp D:/Entwicklung/HASI/pr139-work/npm-cache && export TEMP=D:/Entwicklung/HASI/pr139-work/tmp TMP=D:/Entwicklung/HASI/pr139-work/tmp TMPDIR=D:/Entwicklung/HASI/pr139-work/tmp npm_config_cache=D:/Entwicklung/HASI/pr139-work/npm-cache
npm test
```

Erwartet (Basis 22/614 + 1 Datei / 8 Tests):

```
 Test Files  23 passed (23)
      Tests  622 passed (622)
```

- [ ] **Step 12: Build (lint + rollup), danach dist zurücksetzen**

```bash
cd /d/Entwicklung/HASI/HAsmartirrigation/custom_components/irrigation_plus/frontend
mkdir -p D:/Entwicklung/HASI/pr139-work/tmp D:/Entwicklung/HASI/pr139-work/npm-cache && export TEMP=D:/Entwicklung/HASI/pr139-work/tmp TMP=D:/Entwicklung/HASI/pr139-work/tmp TMPDIR=D:/Entwicklung/HASI/pr139-work/tmp npm_config_cache=D:/Entwicklung/HASI/pr139-work/npm-cache
npm run build
```

Erwartet: `> eslint src/**/*.ts` ohne Meldung, dann viermal `created dist in …` (die zwei
bekannten `output.name`-Warnungen für IIFE-Bundles sind vorbestehend), Exit-Code 0. Die fehlenden
`latency_margin`-Schlüssel brechen den Build NICHT.

Der Build ändert alle vier dist-Bundles. Dieser Task committet nur Quellen, Task 12 baut dist nach
den Übersetzungen neu:

```bash
cd /d/Entwicklung/HASI/HAsmartirrigation
git checkout -- custom_components/irrigation_plus/frontend/dist
git status --short
```

Erwartet:

```
 M custom_components/irrigation_plus/frontend/src/const.ts
 M custom_components/irrigation_plus/frontend/src/types.ts
 M custom_components/irrigation_plus/frontend/src/views/zones/view-zone-settings.ts
?? custom_components/irrigation_plus/frontend/src/views/zones/view-zone-settings-latency-margin.test.ts
?? docs/SESSION-STAND.md
```

- [ ] **Step 13: Mutationsprobe**

Verfahren aus Task 0, Step 5: `mutate.py`, Suchtexte mit `\n`, Sicherung
`D:/Entwicklung/HASI/pr139-work/mut/t11-<probe>.bak` für
`custom_components/irrigation_plus/frontend/src/views/zones/view-zone-settings.ts`, Step 9 laufen lassen (muss
fehlschlagen), nach jeder Probe Wiederherstellung aus der `.bak` und SHA-256-Prüfung (Pflicht);
`git diff --stat` zeigt danach wieder nur `const.ts | 1 +`, `types.ts | 3 ++`, `view-zone-settings.ts | 58 +++`.
Suchtext → Ersatz steht je Probe in der Tabelle, jeder Suchtext kommt genau einmal vor; `clamp-no-lower` und
`clamp-no-round` ersetzen denselben Suchtext `Math.max(0, Math.min(30, Math.round(v)))` wie `clamp-no-upper`,
`clamp-no-nan-guard` ersetzt `    if (isNaN(v)) return null;\n` durch nichts.

| Probe | Änderung in `view-zone-settings.ts` | Beobachtet |
|---|---|---|
| `gate-always-true` | `return !!zone?.confirm_entity;` → `return true;` | FAIL: `hides when confirm_entity is null`, `… is an empty string`, `… is missing` — `3 failed \| 5 passed (8)` |
| `gate-ignores-empty` | `return !!zone?.confirm_entity;` → `return zone?.confirm_entity != null;` | FAIL: `hides when confirm_entity is an empty string` — `1 failed \| 7 passed (8)` |
| `clamp-no-upper` | `Math.max(0, Math.min(30, Math.round(v)))` → `Math.max(0, Math.round(v))` | FAIL: `clamps below 0 and above 30` — `1 failed \| 7 passed (8)` |
| `clamp-no-lower` | → `Math.min(30, Math.round(v))` | FAIL: `clamps below 0 and above 30` — `1 failed \| 7 passed (8)` |
| `clamp-no-round` | → `Math.max(0, Math.min(30, v))` | FAIL: `rounds to whole seconds` — `1 failed \| 7 passed (8)` |
| `clamp-no-nan-guard` | Zeile `if (isNaN(v)) return null;` entfernt | FAIL: `ignores an empty or invalid input (NaN)` — `1 failed \| 7 passed (8)` |

Nach dem letzten Zurückkopieren: Step 9 erneut → `Tests  8 passed (8)`.

Real beobachtet: im Revisions-Probelauf nach dem Feinschliff alle sechs Proben erneut am abgekoppelten Commit
dieses Tasks (`7c626143`, mit dem abgeschwächten Test-Kommentar), Ersetzung per
`D:/Entwicklung/HASI/pr139-work/mut/mutate.py` (Suchtext genau einmal), Sicherungen
`mut/r7-t11-<name>.bak`. Ergebnisse exakt wie in der Tabelle (`3 failed | 5 passed (8)` bzw. je
`1 failed | 7 passed (8)` mit denselben Testnamen); nach jeder Wiederherstellung SHA-256 von
`view-zone-settings.ts` gleich dem Ausgangsstand (`5492005a536b…`), `git status --short` danach leer.

- [ ] **Step 14: Commit (nur Quellen, explizite Dateiliste)**

```bash
cd /d/Entwicklung/HASI/HAsmartirrigation
git add custom_components/irrigation_plus/frontend/src/const.ts custom_components/irrigation_plus/frontend/src/types.ts custom_components/irrigation_plus/frontend/src/views/zones/view-zone-settings.ts custom_components/irrigation_plus/frontend/src/views/zones/view-zone-settings-latency-margin.test.ts
git commit -F - <<'EOF'
feat(panel): add latency margin field for confirmed service zones

Issue #139 gives a confirmed service run a finish grace of the watcher's
settle plus a per-zone latency margin, so the watcher and not the backstop
closes a normal run end. The margin needs a zone setting in the panel.

The row sits in the service block under the confirm entity and is shown
only when a confirm_entity is set: without one nothing reports the valve's
close, the backend applies no grace and the field would be a dead knob.
The input rounds and clamps to whole seconds 0-30, the same bounds the
backend enforces, and ignores an empty field instead of saving 0.

Sources only; the translations and the rebuilt dist bundles follow together.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
```

Erwartet (real beobachtet, Revisions-Probelauf `dry2` nach dem Feinschliff, Commit `7c626143`):
`4 files changed, 145 insertions(+)` (`const.ts | 1`, `types.ts | 3`, `view-zone-settings.ts | 58`,
`view-zone-settings-latency-margin.test.ts | 83`); `git status --short` danach leer bis auf
`?? docs/SESSION-STAND.md` (im Probelauf `dry2` ohne diese Datei: leer; dist unverändert,
`node_modules` ignoriert).

Keine Zeile der Nachricht beginnt mit `#`: git behandelt solche Zeilen als Kommentar und entfernt sie
stillschweigend, sobald die Nachricht erneut bearbeitet wird (Rebase mit Fixup/Reword). Deshalb
„Issue #139 gives …“ statt „#139 gives …“ am Zeilenanfang. Für sich geprüft am Commit (abgekoppelt):
vitest-Datei `8 passed (8)`, `npm test` `23 passed (23)` / `622 passed (622)`, `npm run build` Exit 0
(eslint ohne Meldung), danach `git checkout -- custom_components/irrigation_plus/frontend/dist`.

**Neue Test-Helfer:** keine gemeinsam genutzten. Task 12 braucht die Schlüssel
`panels.zones.labels.latency_margin` und `panels.zones.labels.latency_margin_help` in allen 8
`frontend/localize/languages/*.json`; danach zeigt die Überschrift „<Label> (s)" statt nur „(s)".

---

### Task 12: Übersetzungen „Latenz-Marge" in 8 Sprachen + Doku + dist

Die Panel-Zeile aus Task 11 zeigt bis hierher nur „(s)", weil `panels.zones.labels.latency_margin`
und `latency_margin_help` in keinem Katalog existieren. Dieser Task legt beide Schlüssel in allen 8
Panel-Sprachdateien an (echte Übersetzungen, Begriffe für Lauf/Ventil/Bestätigungs-Entität aus dem
jeweiligen `confirm_entity_help` derselben Datei), dokumentiert das Feld unter „Confirm entity" und
baut dist neu. Nur `en.json` steckt im Bundle (`frontend/localize/localize.ts:1`
`import * as en from "./languages/en.json"`); die übrigen Sprachen lädt `localize.ts:49` zur
Laufzeit per `fetch`. Deshalb ändern sich genau `irrigation-plus.js` (Panel, enthält auch den
Task-11-Code) und `irrigation-plus-card-impl.js`; `irrigation-plus-card.js` und
`irrigation-plus-card-legacy.js` bleiben inhaltlich gleich.

Der Backend-Katalog `translations/*.json` bekommt nichts (kein Bereich für Zonenfelder, siehe Spec
„Befunde gegen die Vorgabe, zu 6").

**Files** (Zeilen auf `0b418644`):
- Modify: `custom_components/irrigation_plus/frontend/localize/languages/en.json:628-629`
- Modify: `custom_components/irrigation_plus/frontend/localize/languages/de.json:409-410`
- Modify: `custom_components/irrigation_plus/frontend/localize/languages/es.json:409-410`
- Modify: `custom_components/irrigation_plus/frontend/localize/languages/fr.json:409-410`
- Modify: `custom_components/irrigation_plus/frontend/localize/languages/it.json:449-450`
- Modify: `custom_components/irrigation_plus/frontend/localize/languages/nl.json:409-410`
- Modify: `custom_components/irrigation_plus/frontend/localize/languages/no.json:409-410`
- Modify: `custom_components/irrigation_plus/frontend/localize/languages/sk.json:409-410`
- Modify: `docs/configuration-my-zones.md:92-93`
- Modify (Build-Ergebnis, `git add -f`): `custom_components/irrigation_plus/frontend/dist/irrigation-plus.js`, `custom_components/irrigation_plus/frontend/dist/irrigation-plus-card-impl.js`
- Test: `tests/test_i18n_completeness.py` (bestehend, unverändert: fehlende/verwaiste Schlüssel, englische Kopien ab 4 Prosa-Wörtern, Platzhalter)

- [ ] **Step 1: Wortlaut prüfen — vom User freigegeben am 2026-09-15; bei Änderung erneut vorlegen**

Alle 16 Strings wörtlich (so im
Dry-Run angewandt). Produktname im Hilfetext ist „Irrigation Plus"
(beide Namen „HASI" und „Irrigation Plus" kommen in den Panel-Katalogen bereits vor, je 7–8-mal).

| Sprache | `latency_margin` | `latency_margin_help` |
|---|---|---|
| en | Latency margin | How many seconds this valve may take after the end of its run to report that it closed. Irrigation Plus waits this long for the report before it settles the run without it, and a close reported within this margin before the end still counts as a complete run. Only used with a confirm entity. |
| de | Latenz-Marge | Wie viele Sekunden dieses Ventil nach dem Ende seines Laufs brauchen darf, bis es seinen Schluss meldet. Irrigation Plus wartet so lange auf die Meldung, bevor es den Lauf ohne sie abschließt, und ein Schluss, der innerhalb dieser Marge vor dem Ende gemeldet wird, zählt als vollständiger Lauf. Nur mit einer Bestätigungs-Entität wirksam. |
| es | Margen de latencia | Cuántos segundos puede tardar esta válvula, tras el final de su ejecución, en informar de que se ha cerrado. Irrigation Plus espera el aviso durante ese tiempo antes de dar por concluida la ejecución sin él, y un cierre informado dentro de este margen antes del final sigue contando como ejecución completa. Solo se usa con una entidad de confirmación. |
| fr | Marge de latence | Nombre de secondes dont cette vanne dispose après la fin de son exécution pour signaler sa fermeture. Irrigation Plus attend ce signalement pendant ce délai avant de clôturer l'exécution sans lui, et une fermeture signalée dans cette marge avant la fin compte toujours comme une exécution complète. Utilisé uniquement avec une entité de confirmation. |
| it | Margine di latenza | Quanti secondi può impiegare questa valvola, dopo la fine della sua esecuzione, per segnalare di essersi chiusa. Irrigation Plus attende la segnalazione per questo tempo prima di concludere l'esecuzione senza di essa, e una chiusura segnalata entro questo margine prima della fine conta comunque come esecuzione completa. Usato solo con un'entità di conferma. |
| nl | Latentiemarge | Hoeveel seconden deze klep na het einde van de beurt nodig mag hebben om het sluiten te melden. Irrigation Plus wacht zo lang op die melding voordat het de beurt zonder melding afrondt, en een sluiting die binnen deze marge vóór het einde wordt gemeld, telt nog steeds als een volledige beurt. Alleen gebruikt met een bevestigingsentiteit. |
| no | Latensmargin | Hvor mange sekunder denne ventilen kan bruke etter slutten av kjøringen på å melde at den har lukket seg. Irrigation Plus venter så lenge på meldingen før kjøringen avsluttes uten den, og en lukking som meldes innenfor denne marginen før slutten, teller fortsatt som en fullført kjøring. Brukes bare med en bekreftelses-entitet. |
| sk | Rezerva latencie | Koľko sekúnd môže tomuto ventilu po skončení behu trvať, kým nahlási, že sa zatvoril. Irrigation Plus čaká na hlásenie takto dlho a až potom beh uzavrie bez neho, pričom zatvorenie nahlásené v rámci tejto rezervy pred koncom sa stále počíta ako úplný beh. Používa sa len s overovacou entitou. |

Terminologie-Quelle je Datei (Service-Block `confirm_entity`/`confirm_entity_help`): es „ejecución",
„válvula", „entidad de confirmación", „informar"; fr „exécution", „vanne", „entité de confirmation";
it „esecuzione", „valvola", „entità di conferma", „segnalare"; nl „beurt", „klep",
„bevestigingsentiteit", „melden"; no „kjøring", „ventil", „bekreftelses-entitet", „melde"; sk „beh",
„ventil", „overovacia entita", „hlásiť". Wer einen dieser Texte ändern will, legt die Änderung dem
User erneut vor, bevor Step 2 und Step 4 sie anwenden; ohne Änderung gelten die Texte oben unverändert.

- [ ] **Step 2: Nur `en.json` ergänzen (Test soll danach fehlschlagen)**

Einfügeort in jeder Sprachdatei: im Service-Block `panels.zones.labels`, direkt nach der Zeile
`"confirm_entity_help": …` und direkt vor der Zeile `"observed_entity": …` (diese Zeile gibt es je
Datei genau einmal; der Verteiler-Block weiter unten hat ein eigenes `confirm_entity_help`, aber kein
`observed_entity`).

`custom_components/irrigation_plus/frontend/localize/languages/en.json` — vor der Zeile

```json
        "observed_entity": "Observed valve/switch (optional)",
```

diese zwei Zeilen einfügen:

```json
        "latency_margin": "Latency margin",
        "latency_margin_help": "How many seconds this valve may take after the end of its run to report that it closed. Irrigation Plus waits this long for the report before it settles the run without it, and a close reported within this margin before the end still counts as a complete run. Only used with a confirm entity.",
```

- [ ] **Step 3: i18n-Test laufen lassen — muss fehlschlagen**

```bash
cd /d/Entwicklung/HASI/HAsmartirrigation
mkdir -p D:/Entwicklung/HASI/pr139-work/tmp D:/Entwicklung/HASI/pr139-work/npm-cache && export TEMP=D:/Entwicklung/HASI/pr139-work/tmp TMP=D:/Entwicklung/HASI/pr139-work/tmp TMPDIR=D:/Entwicklung/HASI/pr139-work/tmp npm_config_cache=D:/Entwicklung/HASI/pr139-work/npm-cache
./.venv/Scripts/python.exe -m pytest tests/test_i18n_completeness.py -p _local_socket_unblock -q
```

Erwartet (Auszug):

```
E   AssertionError: de.json is missing 2 key(s) present in en.json; those strings will silently fall back to English: ['panels.zones.labels.latency_margin', 'panels.zones.labels.latency_margin_help']
...
FAILED tests/test_i18n_completeness.py::test_no_missing_keys[panel-de] - Asse...
FAILED tests/test_i18n_completeness.py::test_no_missing_keys[panel-es] - Asse...
FAILED tests/test_i18n_completeness.py::test_no_missing_keys[panel-fr] - Asse...
FAILED tests/test_i18n_completeness.py::test_no_missing_keys[panel-it] - Asse...
FAILED tests/test_i18n_completeness.py::test_no_missing_keys[panel-nl] - Asse...
FAILED tests/test_i18n_completeness.py::test_no_missing_keys[panel-no] - Asse...
FAILED tests/test_i18n_completeness.py::test_no_missing_keys[panel-sk] - Asse...
======================== 7 failed, 58 passed
```

(Basis vor Step 2: `65 passed`.)

- [ ] **Step 4: Die sieben übrigen Sprachen ergänzen**

Gleicher Einfügeort wie Step 2 (vor der jeweiligen `"observed_entity"`-Zeile).

`de.json` — vor

```json
        "observed_entity": "Beobachtetes Ventil/Schalter (optional)",
```

einfügen:

```json
        "latency_margin": "Latenz-Marge",
        "latency_margin_help": "Wie viele Sekunden dieses Ventil nach dem Ende seines Laufs brauchen darf, bis es seinen Schluss meldet. Irrigation Plus wartet so lange auf die Meldung, bevor es den Lauf ohne sie abschließt, und ein Schluss, der innerhalb dieser Marge vor dem Ende gemeldet wird, zählt als vollständiger Lauf. Nur mit einer Bestätigungs-Entität wirksam.",
```

`es.json` — vor

```json
        "observed_entity": "Válvula/interruptor observado (opcional)",
```

einfügen:

```json
        "latency_margin": "Margen de latencia",
        "latency_margin_help": "Cuántos segundos puede tardar esta válvula, tras el final de su ejecución, en informar de que se ha cerrado. Irrigation Plus espera el aviso durante ese tiempo antes de dar por concluida la ejecución sin él, y un cierre informado dentro de este margen antes del final sigue contando como ejecución completa. Solo se usa con una entidad de confirmación.",
```

`fr.json` — vor

```json
        "observed_entity": "Vanne/interrupteur observé (optionnel)",
```

einfügen:

```json
        "latency_margin": "Marge de latence",
        "latency_margin_help": "Nombre de secondes dont cette vanne dispose après la fin de son exécution pour signaler sa fermeture. Irrigation Plus attend ce signalement pendant ce délai avant de clôturer l'exécution sans lui, et une fermeture signalée dans cette marge avant la fin compte toujours comme une exécution complète. Utilisé uniquement avec une entité de confirmation.",
```

`it.json` — vor

```json
        "observed_entity": "Valvola/interruttore osservato (opzionale)",
```

einfügen:

```json
        "latency_margin": "Margine di latenza",
        "latency_margin_help": "Quanti secondi può impiegare questa valvola, dopo la fine della sua esecuzione, per segnalare di essersi chiusa. Irrigation Plus attende la segnalazione per questo tempo prima di concludere l'esecuzione senza di essa, e una chiusura segnalata entro questo margine prima della fine conta comunque come esecuzione completa. Usato solo con un'entità di conferma.",
```

`nl.json` — vor

```json
        "observed_entity": "Waargenomen klep/schakelaar (optioneel)",
```

einfügen:

```json
        "latency_margin": "Latentiemarge",
        "latency_margin_help": "Hoeveel seconden deze klep na het einde van de beurt nodig mag hebben om het sluiten te melden. Irrigation Plus wacht zo lang op die melding voordat het de beurt zonder melding afrondt, en een sluiting die binnen deze marge vóór het einde wordt gemeld, telt nog steeds als een volledige beurt. Alleen gebruikt met een bevestigingsentiteit.",
```

`no.json` — vor

```json
        "observed_entity": "Observert ventil/bryter (valgfritt)",
```

einfügen:

```json
        "latency_margin": "Latensmargin",
        "latency_margin_help": "Hvor mange sekunder denne ventilen kan bruke etter slutten av kjøringen på å melde at den har lukket seg. Irrigation Plus venter så lenge på meldingen før kjøringen avsluttes uten den, og en lukking som meldes innenfor denne marginen før slutten, teller fortsatt som en fullført kjøring. Brukes bare med en bekreftelses-entitet.",
```

`sk.json` — vor

```json
        "observed_entity": "Pozorovaný ventil/prepínač (voliteľné)",
```

einfügen:

```json
        "latency_margin": "Rezerva latencie",
        "latency_margin_help": "Koľko sekúnd môže tomuto ventilu po skončení behu trvať, kým nahlási, že sa zatvoril. Irrigation Plus čaká na hlásenie takto dlho a až potom beh uzavrie bez neho, pričom zatvorenie nahlásené v rámci tejto rezervy pred koncom sa stále počíta ako úplný beh. Používa sa len s overovacou entitou.",
```

- [ ] **Step 5: i18n-Test laufen lassen — muss grün sein**

```bash
cd /d/Entwicklung/HASI/HAsmartirrigation
mkdir -p D:/Entwicklung/HASI/pr139-work/tmp D:/Entwicklung/HASI/pr139-work/npm-cache && export TEMP=D:/Entwicklung/HASI/pr139-work/tmp TMP=D:/Entwicklung/HASI/pr139-work/tmp TMPDIR=D:/Entwicklung/HASI/pr139-work/tmp npm_config_cache=D:/Entwicklung/HASI/pr139-work/npm-cache
./.venv/Scripts/python.exe -m pytest tests/test_i18n_completeness.py -p _local_socket_unblock -q
```

Erwartet:

```
============================= 65 passed
```

- [ ] **Step 6: Doku — Punkt direkt unter „Confirm entity"**

`docs/configuration-my-zones.md`, Liste der Self-closing-service-Einstellungen. Direkt nach dem
Punkt `- **Confirm entity** *(optional)* — …`, dessen letzter Satz endet mit

```markdown
Do **not** point it at the run script: a fire-and-forget script returns to *off* immediately and is not a valid state signal.
```

diese Zeile einfügen (gleiche Einrückung, zwei Leerzeichen vor `-`):

```markdown
  - **Latency margin** *(seconds, default 4, 0–30; only with a confirm entity)* — how many seconds the valve may take after the end of its run to report that it closed. The integration waits this long for the confirm entity to report *off* before it settles the run without that report. Once *off* is reported (and holds for the 5 s debounce), the run is settled on the valve's own reports: its duration is the time between the valve's *on* and *off* reports, and a close reported within the margin before the planned end still counts as a complete run. A run whose close report never arrives is settled as complete at planned duration + 5 s + margin. Raise it for a valve that reports its close late (e.g. a sleepy Zigbee valve).
```

- [ ] **Step 7: Lint**

Keine Python-Datei geändert; zur Bestätigung trotzdem die zwei CI-Befehle:

```bash
cd /d/Entwicklung/HASI/HAsmartirrigation
uvx black custom_components/irrigation_plus/
uvx ruff check custom_components/irrigation_plus/
```

Erwartet:

```
67 files left unchanged.
All checks passed!
```

Frontend-Lint (eslint + prettier) läuft als erster Teil von `npm run build` in Step 8.

- [ ] **Step 8: dist bauen und nur die geänderten Bundles behalten**

```bash
cd /d/Entwicklung/HASI/HAsmartirrigation/custom_components/irrigation_plus/frontend
mkdir -p D:/Entwicklung/HASI/pr139-work/tmp D:/Entwicklung/HASI/pr139-work/npm-cache && export TEMP=D:/Entwicklung/HASI/pr139-work/tmp TMP=D:/Entwicklung/HASI/pr139-work/tmp TMPDIR=D:/Entwicklung/HASI/pr139-work/tmp npm_config_cache=D:/Entwicklung/HASI/pr139-work/npm-cache
npm run build
cd /d/Entwicklung/HASI/HAsmartirrigation
git diff --stat -- custom_components/irrigation_plus/frontend/dist
```

Erwartet: `> eslint src/**/*.ts` ohne Meldung, viermal `created dist in …` (die zwei bekannten
`output.name`-Warnungen für IIFE-Bundles sind vorbestehend), Exit-Code 0 (mit `set -o pipefail`
gemessen). Dann:

```
 .../frontend/dist/irrigation-plus-card-impl.js     |    2 +-
 .../frontend/dist/irrigation-plus.js               | 1601 ++++++++++----------
 2 files changed, 812 insertions(+), 791 deletions(-)
```

Ein zweiter Build liefert dieselbe Statistik (reproduzierbar). `irrigation-plus.js` ist minifiziert
(8071 Zeilen); die große Zeilenzahl kommt aus Task 11 (Panel-Code, dort ohne dist committet) plus
en.json. `git status --short` listet zusätzlich `irrigation-plus-card.js` und
`irrigation-plus-card-legacy.js`, aber `git diff --numstat` für beide ist leer (nur
LF/CRLF-Warnung) — zurücksetzen:

```bash
cd /d/Entwicklung/HASI/HAsmartirrigation
git checkout -- custom_components/irrigation_plus/frontend/dist/irrigation-plus-card.js custom_components/irrigation_plus/frontend/dist/irrigation-plus-card-legacy.js
```

Stichprobe, dass die Bundles das Richtige tragen (aus `custom_components/irrigation_plus/frontend/dist`):

```bash
cd /d/Entwicklung/HASI/HAsmartirrigation/custom_components/irrigation_plus/frontend/dist
grep -o "Latency margin" irrigation-plus.js | wc -l          # 1
grep -o "Latency margin" irrigation-plus-card-impl.js | wc -l # 1
grep -o "_showLatencyMargin" irrigation-plus.js | wc -l      # 2
grep -o "Latenz-Marge" irrigation-plus.js | wc -l            # 0 (de wird zur Laufzeit geladen)
```

- [ ] **Step 9: Verwandte Suiten**

```bash
cd /d/Entwicklung/HASI/HAsmartirrigation/custom_components/irrigation_plus/frontend
mkdir -p D:/Entwicklung/HASI/pr139-work/tmp D:/Entwicklung/HASI/pr139-work/npm-cache && export TEMP=D:/Entwicklung/HASI/pr139-work/tmp TMP=D:/Entwicklung/HASI/pr139-work/tmp TMPDIR=D:/Entwicklung/HASI/pr139-work/tmp npm_config_cache=D:/Entwicklung/HASI/pr139-work/npm-cache
npm test
```

Erwartet (Stand nach Task 11, unverändert):

```
 Test Files  23 passed (23)
      Tests  622 passed (622)
```

```bash
cd /d/Entwicklung/HASI/HAsmartirrigation
mkdir -p D:/Entwicklung/HASI/pr139-work/tmp D:/Entwicklung/HASI/pr139-work/npm-cache && export TEMP=D:/Entwicklung/HASI/pr139-work/tmp TMP=D:/Entwicklung/HASI/pr139-work/tmp TMPDIR=D:/Entwicklung/HASI/pr139-work/tmp npm_config_cache=D:/Entwicklung/HASI/pr139-work/npm-cache
./.venv/Scripts/python.exe -m pytest tests/test_panel.py tests/test_i18n_completeness.py -p _local_socket_unblock -q
```

Erwartet lokal (Windows):

```
FAILED tests/test_panel.py::TestSmartIrrigationPanel::test_async_register_panel_static_path_config
======================== 1 failed, 72 passed
```

Der eine Fehlschlag ist vorbestehend und nicht von diesem Task: auf `0b418644` (temporärer
detached Worktree) gibt `tests/test_panel.py` ebenfalls `1 failed, 7 passed` mit derselben
Testfunktion. Ursache ist der Windows-Pfadtrenner:
`assert 'frontend/dist/irrigation-plus.js' in '\\config\\irrigation_plus\\frontend\\dist\\irrigation-plus.js'`.

- [ ] **Step 10: Mutationsprobe**

Verfahren aus Task 0, Step 5: `mutate.py`, Suchtexte mit `\n`, Sicherung
`D:/Entwicklung/HASI/pr139-work/mut/t12-<probe>.bak` für die Sprachdatei, Step 5 laufen lassen (muss
fehlschlagen), nach jeder Probe Wiederherstellung aus der `.bak` und SHA-256-Prüfung (Pflicht). Nach beiden
Proben: Step 5 → `65 passed`, und `git diff --stat -- custom_components/irrigation_plus/frontend/localize docs`
zeigt wieder genau je `| 2 ++` für die 8 Sprachdateien und `docs/configuration-my-zones.md | 1 +`.
Suchtext → Ersatz steht je Probe in der Tabelle; die Zeile `"latency_margin_help": …` kommt je Datei genau
einmal vor.

| Probe | Änderung (Suchtext → Ersatz) | Beobachtet |
|---|---|---|
| `sk-help-missing` | in `sk.json` die ganze `latency_margin_help`-Zeile aus Step 4 (8 Leerzeichen Einrückung, bis einschließlich `,\n`) → leer | FAIL `test_no_missing_keys[panel-sk]`: `sk.json is missing 1 key(s) present in en.json; … ['panels.zones.labels.latency_margin_help']` — `1 failed, 64 passed` |
| `fr-help-english` | in `fr.json` die `latency_margin_help`-Zeile aus Step 4 → dieselbe Zeile mit dem englischen Wert aus Step 2 (Schlüssel, Einrückung und Komma bleiben) | FAIL `test_no_value_is_left_as_the_english_string[panel-fr]`: `fr.json has 1 value(s) identical to the English text: ['.panels.zones.labels.latency_margin_help']` — `1 failed, 64 passed` |

- [ ] **Step 11: Commit (explizite Dateiliste, dist mit `-f`)**

```bash
cd /d/Entwicklung/HASI/HAsmartirrigation
git add custom_components/irrigation_plus/frontend/localize/languages/de.json custom_components/irrigation_plus/frontend/localize/languages/en.json custom_components/irrigation_plus/frontend/localize/languages/es.json custom_components/irrigation_plus/frontend/localize/languages/fr.json custom_components/irrigation_plus/frontend/localize/languages/it.json custom_components/irrigation_plus/frontend/localize/languages/nl.json custom_components/irrigation_plus/frontend/localize/languages/no.json custom_components/irrigation_plus/frontend/localize/languages/sk.json docs/configuration-my-zones.md
git add -f custom_components/irrigation_plus/frontend/dist/irrigation-plus.js custom_components/irrigation_plus/frontend/dist/irrigation-plus-card-impl.js
git commit -F - <<'EOF'
feat(i18n): translate and document the latency margin zone field

Issue #139 gives confirmed service runs a per-zone latency margin. The
panel row added in the previous commit rendered only "(s)" because its
label and help keys did not exist in any catalogue yet.

Add panels.zones.labels.latency_margin and latency_margin_help to all eight
panel languages as real translations, using each file's existing terms for
run, valve and confirm entity. Document the setting under Confirm entity:
what it waits for, that a close reported within it counts as complete, and
that a run whose close report never arrives settles at planned + 5 s +
margin.

Rebuild the two bundles that embed en.json (irrigation-plus.js,
irrigation-plus-card-impl.js). The other languages are fetched at runtime,
so the card and legacy card bundles stay unchanged.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
git show --stat --format= HEAD
git status --short
```

Erwartet (real beobachtet, Revisions-Probelauf `dry2` nach dem Feinschliff, Commit `67301a8b`):
`11 files changed, 829 insertions(+), 791 deletions(-)` (2 dist-Bundles, 8 Sprachdateien je `2 +`, Doku
`1 +`); `git status --short` danach leer bis auf `?? docs/SESSION-STAND.md` (im Probelauf `dry2` ohne diese
Datei: leer).

Keine Zeile der Nachricht beginnt mit `#` („Issue #139 gives …“): git entfernt solche Zeilen als Kommentar,
sobald die Nachricht erneut bearbeitet wird. Genau so fehlte im Revisions-Probelauf dem Commit `ad3b697f`
nach einem Autosquash die erste Textzeile; der Feinschliff hat die Nachricht mit dem Text oben neu gesetzt.
Prüfung nach dem Commit: `git log -1 --format=%B | grep -c '^#'` → `0`.

**Neue Test-Helfer:** keine. Task 13 prüft `npm run build` erneut gegen diesen Commit (dist muss
unverändert bleiben) und nimmt den vorbestehenden `test_panel.py`-Fehlschlag in den Basisvergleich.

---

### Task 13: Schlussprüfung

Keine neue Produktionslogik. Dieser Task prüft den Gesamtstand von Task 1–12 (mit Task 3b) gegen die Basis
`0b418644`: Lint, volle Suite (inklusive der unveränderten Batch- und OpenSprinkler-Suiten), vitest,
Reproduzierbarkeit von dist, Schwester-Pfade, Text-Hygiene, die Mutationsproben aller Tasks und die
Abtrennbarkeit der vier optionalen Tasks. Deckt ein Schritt einen Defekt auf, wird er minimal behoben,
separat committet und hier nachgetragen.

Alle Zahlen unten sind real beobachtet im Revisions-Probelauf vom 2026-09-15: Worktree
`D:/Entwicklung/HASI/pr139-work/dry2`, Branch `dry2/backstop-grace`, Endstand `67301a8b`, Basis `0b418644`,
Python 3.12.0, HA 2024.12.5, Node 24.15.0. Der Endstand ist der Stand nach dem Feinschliff: E6-Regel im
Kommentar von `RUN_VALVE_OFF` (Task 2), neutrale Testdaten in `tests/test_finish_grace_helpers.py` (Task 2,
E7), Pin „`unavailable` mitten im Lauf“ in Task 5, abgeschwächter vitest-Kommentar (Task 11), Commit-Texte von
Task 11 und 12 ohne Zeile, die mit `#` beginnt. Der erste Probelauf auf `4e53caf4` (Branches
`dry/backstop-grace`, `dry/backstop-grace-frontend`) ist ersetzt; aus ihm stammen nur noch die Mutationsproben
von Task 9, 10 und 12 (Step 7 belegt, warum sie gelten). Im echten Lauf liegen alle Tasks auf
`fix/backstop-grace`.

**Files:** keine Änderung. Messdateien außerhalb des Repos unter `D:\Entwicklung\HASI\pr139-work\`.

- [ ] **Step 1: Stand prüfen**

```bash
cd /d/Entwicklung/HASI/HAsmartirrigation
git status --short
git log --oneline --reverse 0b418644..HEAD
for c in $(git rev-list --reverse 0b418644..HEAD); do git show --stat --format="%h %s" $c | sed -n '1p;$p'; done
git diff --stat 0b418644 HEAD | tail -1
```

Erwartet: `git status --short` leer bis auf `?? docs/SESSION-STAND.md`; 13 Commits, ältester zuerst, je
Task genau einer:

| Task | Probelauf-Commit | Betreff | `git show --stat` |
|---|---|---|---|
| 1 | `745e4bac` | `feat(service): add a per-zone latency margin setting for confirmed valves` | 5 files, +126 |
| 2 | `94cc3785` | `feat(run-watch): add the finish-grace run keys, policy flag and helpers` | 4 files, +427 |
| 3 | `dbbb42fd` | `feat(service): wait out the finish grace before a confirmed run's backstop` | 2 files, +191 −2 |
| 3b | `99c9272d` | `feat(service): keep the observed-watering lockout over a confirmed run's finish grace` | 2 files, +40 −1 |
| 4 | `adcb6fba` | `feat(run-watch): record a confirmed valve's own off report` | 2 files, +233 −3 |
| 5 | `8528d4d0` | `feat(run-watch): settle a confirmed service run on its valve window` | 3 files, +237 −7 |
| 6 | `a3c220e5` | `feat(service): let the backstop settle a reported close on its window` | 2 files, +132 −1 |
| 7 | `b59fcdf9` | `feat(service): measure a manual stop on the valve's own window` | 2 files, +169 −3 |
| 8 | `b503b663` | `feat(service): carry the finish grace across a restart` | 2 files, +280 −4 |
| 9 | `ce7a1d13` | `feat(service): keep a confirmed run in flight through its finish grace` | 2 files, +85 −2 |
| 10 | `8d7ebbed` | `feat(service): price a confirmed service zone's finish grace into the window` | 2 files, +67 −2 |
| 11 | `7c626143` | `feat(panel): add latency margin field for confirmed service zones` | 4 files, +145 |
| 12 | `67301a8b` | `feat(i18n): translate and document the latency margin zone field` | 11 files, +829 −791 |

Keine Commit-Nachricht hat eine Zeile, die mit `#` beginnt (geprüft mit
`for c in $(git rev-list 0b418644..HEAD); do git log -1 --format=%B $c | grep -q '^#' && echo $c; done`,
real: keine Ausgabe). Solche Zeilen entfernt git beim erneuten Bearbeiten einer Nachricht (Rebase, Fixup)
stillschweigend als Kommentar; im Revisions-Probelauf fehlte so dem Task-12-Commit `ad3b697f` nach einem
Autosquash die erste Textzeile. Der Feinschliff formulierte beide Nachrichten um („Issue #139 gives …“).

Gesamt-Diff: `28 files changed, 2958 insertions(+), 813 deletions(-)`, davon `+811 −790` im minifizierten
`irrigation-plus.js` und `+1 −1` in `irrigation-plus-card-impl.js`. Die SHAs ändern sich im echten Lauf; es
zählen Reihenfolge, Betreff und Statistik.

- [ ] **Step 2: Lint (nur prüfen, nichts umschreiben)**

```bash
cd /d/Entwicklung/HASI/HAsmartirrigation
uvx black --check custom_components/irrigation_plus/
uvx ruff check custom_components/irrigation_plus/
```

Erwartet (real):

```
All done! ✨ 🍰 ✨
67 files would be left unchanged.
All checks passed!
```

Meldet `black --check` eine Datei, ist ein Task-Commit unformatiert: `uvx black custom_components/irrigation_plus/`,
Diff lesen und als eigenen `style:`-Commit ablegen.

- [ ] **Step 3: Volle Suite messen und mit der Basis vergleichen**

Am selben Tag wie die Basis aus Task 0 (datumsabhängige Tests). Dauer ~4–5 min.

```bash
cd /d/Entwicklung/HASI/HAsmartirrigation
mkdir -p D:/Entwicklung/HASI/pr139-work/tmp D:/Entwicklung/HASI/pr139-work/npm-cache && export TEMP=D:/Entwicklung/HASI/pr139-work/tmp TMP=D:/Entwicklung/HASI/pr139-work/tmp TMPDIR=D:/Entwicklung/HASI/pr139-work/tmp npm_config_cache=D:/Entwicklung/HASI/pr139-work/npm-cache
./.venv/Scripts/python.exe -m pytest tests -p _local_socket_unblock -q -rfE -p no:cacheprovider > /d/Entwicklung/HASI/pr139-work/after-$(git rev-parse --short HEAD).txt 2>&1
B=/d/Entwicklung/HASI/pr139-work/baseline-0b418644.txt
A=/d/Entwicklung/HASI/pr139-work/after-$(git rev-parse --short HEAD).txt
grep -m1 "^collected" $B; grep -m1 "^collected" $A
tail -1 $B; tail -1 $A
diff <(grep "^FAILED" $B | sed 's/ - .*//' | sort -u) <(grep "^FAILED" $A | sed 's/ - .*//' | sort -u) && echo FAILED-same
diff <(grep "^ERROR" $B | sed 's/ - .*//' | sort -u) <(grep "^ERROR" $A | sed 's/ - .*//' | sort -u) && echo ERROR-same
grep -c "^ERROR" $A; grep "^ERROR" $A | sed 's/ - .*//' | sort -u | wc -l
```

Erwartet (real; Probelauf-Datei `after-polish.txt`, Basis `baseline-0b418644.txt` aus Task 0):

```
collected 2922 items
collected 3009 items
= 7 failed, 2906 passed, 9 skipped, 10 warnings, 320 errors in 249.45s (0:04:09) =
= 7 failed, 2993 passed, 9 skipped, 10 warnings, 320 errors in 241.80s (0:04:01) =
FAILED-same
ERROR-same
326
322
```

Die 7 FAILED-IDs sind dieselben wie in Task 0, Step 3 (Windows-Pfadtrenner in `test_panel.py`,
Setup-/Teardown-Vorbestand in `test_init.py`, `test_next_irrigation_sensor.py`,
`test_opensprinkler_teardown.py`). Die ERROR-Zeilen sind identisch: 326 Zeilen, 322 eindeutig, darunter 6
Log-Zeilen `ERROR … custom_components.irrigation_plus.batch …` (2 eindeutig), die keine Test-IDs sind; die
320 Errors der Zusammenfassung sind lokale `Lingering timer`-Teardowns unter HA 2024.12.5. Kein neuer FAILED,
kein neuer ERROR. Der einzige ERROR in `tests/test_service_watch.py`
(`TestOneOffSampleIsNotEvidenceTheWaterStopped::test_the_run_is_not_settled_before_the_window_is_out`) steht
schon in der Basis.

Delta `passed` +87 = `collected` +87 = neue Test-Items. Pro Datei gezählt aus den Fortschrittszeilen
(`.` = passed, `E` = Teardown-Error, `F` = failed; Fortsetzungszeilen ohne Dateiname zählen zur Datei davor):

```bash
cd /d/Entwicklung/HASI/HAsmartirrigation
mkdir -p D:/Entwicklung/HASI/pr139-work/tmp D:/Entwicklung/HASI/pr139-work/npm-cache && export TEMP=D:/Entwicklung/HASI/pr139-work/tmp TMP=D:/Entwicklung/HASI/pr139-work/tmp TMPDIR=D:/Entwicklung/HASI/pr139-work/tmp npm_config_cache=D:/Entwicklung/HASI/pr139-work/npm-cache
./.venv/Scripts/python.exe - /d/Entwicklung/HASI/pr139-work/baseline-0b418644.txt /d/Entwicklung/HASI/pr139-work/after-$(git rev-parse --short HEAD).txt <<'EOF'
import re, sys
P = re.compile(r"^(tests\S+\.py) ([.EFsxX]*) *\[ *\d+%\]\s*$"); C = re.compile(r"^([.EFsxX]+) *\[ *\d+%\]\s*$")
def parse(fn):
    d, cur = {}, None
    for l in open(fn, encoding="utf-8", errors="replace").read().splitlines():
        m = P.match(l)
        if m: cur = m.group(1).replace("\\", "/"); d[cur] = d.get(cur, "") + m.group(2); continue
        m = C.match(l)
        if m and cur: d[cur] += m.group(1)
    return d
b, a = parse(sys.argv[1]), parse(sys.argv[2]); k = lambda s: (s.count("."), s.count("E"), s.count("F"))
print("files", len(b), len(a))
for f in sorted(set(a) | set(b)):
    if f not in b or k(b[f]) != k(a[f]): print(f, k(b[f]) if f in b else "-", k(a[f]))
EOF
```

Erwartet (real):

```
files 150 151
tests/test_confirm_reserve.py (22, 0, 0) (25, 0, 0)
tests/test_distributor_integration.py (19, 0, 0) (20, 0, 0)
tests/test_finish_grace_helpers.py - (35, 0, 0)
tests/test_run_in_flight.py (19, 0, 0) (22, 0, 0)
tests/test_service_watch.py (17, 1, 0) (60, 1, 0)
tests/test_store_self_closing.py (6, 0, 0) (8, 0, 0)
```

| Datei | Basis | Endstand | + | Aus Task |
|---|---|---|---|---|
| `tests/test_finish_grace_helpers.py` (neu) | — | 35 | 35 | 2 |
| `tests/test_service_watch.py` | 17 (+1 E) | 60 (+1 E) | 43 | 3 (10), 3b (2), 4 (8), 5 (7), 6 (3), 7 (5), 8 (8) |
| `tests/test_confirm_reserve.py` | 22 | 25 | 3 | 10 |
| `tests/test_run_in_flight.py` | 19 | 22 | 3 | 9 |
| `tests/test_store_self_closing.py` | 6 | 8 | 2 | 1 |
| `tests/test_distributor_integration.py` | 19 | 20 | 1 | 1 |

Jede andere Datei ist gegen die Basis unverändert (das Skript listet sie nicht). Stichproben als Orakel für
„Batch, OpenSprinkler und Bestand unberührt“ (passed / E / F, Basis = Endstand, real):

| Datei | Basis = Endstand |
|---|---|
| `tests/test_batch.py` | 61 / 38 / 0 |
| `tests/test_opensprinkler.py` | 67 / 13 / 0 |
| `tests/test_opensprinkler_teardown.py` | 3 / 0 / 3 |
| `tests/test_self_closing.py` | 38 / 0 / 0 (Pins `(2, 500.0)` usw.) |
| `tests/test_credit_ceiling.py` | 38 / 0 / 0 |
| `tests/test_run_watch.py` | 14 / 0 / 0 |
| `tests/test_observed_watering.py` | 34 / 0 / 0 |
| `tests/test_service_chain.py` | 25 / 1 / 0 |
| `tests/test_master.py` | 19 / 0 / 0 |
| `tests/test_i18n_completeness.py` | 65 / 0 / 0 |
| `tests/test_panel.py` | 7 / 0 / 1 |

Neuer FAILED oder ERROR → nicht weiter, zuerst am Basisstand gegenprüfen: Block aus Task 0, Step 6 mit
`P=0b418644` und `FILES` = die Testdateien der neuen Zeilen. Druckt `diff` Zeilen statt `FAILED-ERROR-same`,
ist der Fehler neu und gilt als Defekt dieses Plans.

- [ ] **Step 4: Frontend — npm ci, Build, dist unverändert, vitest**

```bash
cd /d/Entwicklung/HASI/HAsmartirrigation/custom_components/irrigation_plus/frontend
mkdir -p D:/Entwicklung/HASI/pr139-work/tmp D:/Entwicklung/HASI/pr139-work/npm-cache && export TEMP=D:/Entwicklung/HASI/pr139-work/tmp TMP=D:/Entwicklung/HASI/pr139-work/tmp TMPDIR=D:/Entwicklung/HASI/pr139-work/tmp npm_config_cache=D:/Entwicklung/HASI/pr139-work/npm-cache
npm ci && npm run build
cd /d/Entwicklung/HASI/HAsmartirrigation
git status --short -- custom_components/irrigation_plus/frontend/dist
```

Erwartet (real): `npm ci` Exit 0 (die `npm audit`-Hinweise sind vorbestehend), dann
`> irrigation-plus@2026.09.16 build`, `> eslint src/**/*.ts` ohne Meldung und viermal `created dist in …`
(die zwei `output.name`-Warnungen der IIFE-Bundles sind vorbestehend), Exit 0. `git status --short` listet
danach ` M` für `irrigation-plus-card-impl.js`, `irrigation-plus-card-legacy.js` und `irrigation-plus-card.js`.

Das ist nur ein Zeilenende-Stempel: rollup schreibt LF, und `git ls-files --eol` zeigt für diese drei
`i/lf w/crlf attr/` (kein `eol`-Attribut, `core.autocrlf=true`), für `irrigation-plus.js` dagegen
`attr/text eol=lf`. Deshalb nach Inhalt entscheiden, und zwar DIREKT nach dem Build, vor jedem `git checkout`
(danach stehen die drei Card-Bundles mit CRLF im Baum, und ihr Roh-SHA weicht vom Blob ab, obwohl
`git status` sauber ist):

```bash
cd /d/Entwicklung/HASI/HAsmartirrigation
for f in irrigation-plus.js irrigation-plus-card-impl.js irrigation-plus-card.js irrigation-plus-card-legacy.js; do
  w=$(sha256sum custom_components/irrigation_plus/frontend/dist/$f | cut -c1-16)
  h=$(git show HEAD:custom_components/irrigation_plus/frontend/dist/$f | sha256sum | cut -c1-16)
  echo "$f worktree=$w head=$h"
done
```

Erwartet (real): je Datei `worktree` = `head`:

```
irrigation-plus.js worktree=15ae4345b0ec1670 head=15ae4345b0ec1670
irrigation-plus-card-impl.js worktree=8907ba3f56dda361 head=8907ba3f56dda361
irrigation-plus-card.js worktree=ca776b0a4d18b93f head=ca776b0a4d18b93f
irrigation-plus-card-legacy.js worktree=df654e9711f31a98 head=df654e9711f31a98
```

Alle vier gleich → dist ist aus den Quellen reproduziert. Die Status-Zeilen zurücksetzen (Inhalt identisch,
nichts geht verloren):

```bash
cd /d/Entwicklung/HASI/HAsmartirrigation
git checkout -- custom_components/irrigation_plus/frontend/dist/irrigation-plus-card-impl.js custom_components/irrigation_plus/frontend/dist/irrigation-plus-card-legacy.js custom_components/irrigation_plus/frontend/dist/irrigation-plus-card.js
git status --short
```

Erwartet: leer bis auf `?? docs/SESSION-STAND.md`. Weicht eine SHA ab, ist ein dist-Commit veraltet:
Bundle mit `git add -f` in einem eigenen `build(frontend):`-Commit nachziehen.

```bash
cd /d/Entwicklung/HASI/HAsmartirrigation/custom_components/irrigation_plus/frontend
mkdir -p D:/Entwicklung/HASI/pr139-work/tmp D:/Entwicklung/HASI/pr139-work/npm-cache && export TEMP=D:/Entwicklung/HASI/pr139-work/tmp TMP=D:/Entwicklung/HASI/pr139-work/tmp TMPDIR=D:/Entwicklung/HASI/pr139-work/tmp npm_config_cache=D:/Entwicklung/HASI/pr139-work/npm-cache
npm test
```

Erwartet (real; Basis Task 11, Step 1: `22 passed (22)` / `614 passed (614)`; +1 Datei / +8 Tests aus Task 11):

```
 Test Files  23 passed (23)
      Tests  622 passed (622)
```

- [ ] **Step 5: Schwester-Pfad-Check (nur lesend)**

```bash
cd /d/Entwicklung/HASI/HAsmartirrigation
grep -rnE "_sc_schedule_cleanup\(|_sc_finish_run\(|async_stop_self_closing\(|_watch_evaluate\(|zone_confirm_seconds\(|_note_si_valve\(|_self_closing_run_in_flight\(|_sc_backstop_fired\(|_watch_settle_by_window\(|_watch_valve_window\(" custom_components/irrigation_plus --include=*.py | grep -v "def "
grep -rn "previous_state" custom_components/irrigation_plus --include=*.py
grep -rnE "RUN_VALVE_OFF|RUN_VALVE_ON|RUN_LATENCY_MARGIN" custom_components/irrigation_plus --include=*.py | grep -v "irrigation_plus/const.py"
grep -rn "RUN_STARTED" custom_components/irrigation_plus --include=*.py
grep -nE "self\._sc_|self\._watch_|_note_si_valve|async_stop_self_closing" custom_components/irrigation_plus/distributor.py | wc -l
```

Jede Fundstelle eingeordnet (Zeilen = Endstand `67301a8b`, real gegrept; der Feinschliff änderte in
Produktionsdateien nur den Kommentar von `RUN_VALVE_OFF` in `const.py`, alle Zeilennummern unten gelten
unverändert, auch `const.py:944/960/980/984`). „Wartezeit“ = settle 5 s + Marge.
Tor = `run_has_finish_grace` (Service-Policy mit `settles_on_valve_window`, `RUN_WATCH_ENTITY`,
eingefrorene `RUN_LATENCY_MARGIN`); Batch- und OpenSprinkler-Datensätze bestehen es nie.

**`_sc_schedule_cleanup` (Backstop scharf)**

| Stelle | Pfad | Braucht die Wartezeit? | Stand |
|---|---|---|---|
| `self_closing.py:738` | Dispatch `async_run_self_closing` (Service + OpenSprinkler) | ja, bestätigter Service-Lauf | `planned + run_finish_grace_seconds(record)` (Task 3); OpenSprinkler/write-only/unbestätigt = 0 |
| `self_closing.py:1027` | Neustart, Service-Zweig | ja | `planned + grace - elapsed` (Task 8) |
| `self_closing.py:440` `_done` | Backstop-Rückruf, geteilt | nur Routing | `_sc_backstop_fired` → Fensterregel nur mit Wartezeit (`run_finish_grace_seconds(run)` ≠ 0, `:475`, gleichwertig zum Tor) + `RUN_VALVE_OFF` (`:476`, Task 6), sonst `_sc_finish_run` wie bisher |
| `run_watch.py:858` | `_watch_observed_start` | nein | nur `not opens_at_dispatch` = OpenSprinkler; Service öffnet beim Dispatch und armt dort. Unverändert |
| `run_watch.py:915` | `_watch_resume` | nein | nur `policy.segmented` = Batch; Pin `remaining_window_only` (Task 2), `remaining` ohne Wartezeit (`:909`). Unverändert |
| `opensprinkler.py:666` | OpenSprinkler-Neustart | nein | Unverändert |
| `run_window.py:267` | Docstring, kein Aufruf | — | — |

**`_sc_finish_run` (Abschluss `completed`)**

| Stelle | Pfad | Stand |
|---|---|---|
| `self_closing.py:480` | Backstop ohne Aus-Meldung | `actual_s = planned_s` wie bisher (Task 6) |
| `self_closing.py:1021` | Neustart hinter der Wartezeit, keine Aus-Meldung | `planned_s` wie bisher (Task 8) |
| `run_watch.py:994` | `_watch_settle_by_window` | `actual_s = window` (Task 5) |
| `run_watch.py:1017` | `_watch_finish` ohne Tor | alte Regel `elapsed + 1 >= planned`, unverändert (Probe `always-routed`, Task 5) |
| `batch.py:753` | Batch-Neustart | Batch, unverändert |
| `opensprinkler.py:660` | OpenSprinkler-Neustart | OpenSprinkler, unverändert |

**`async_stop_self_closing` (Teil-Lauf / Stopp)**

| Stelle | Pfad | Stand |
|---|---|---|
| `self_closing.py:1069` | `_sc_maybe_stop` = manueller Stopp (Service, OpenSprinkler) | mit Tor (`:891`): Ventilfenster `:904` (Task 7); ohne: `_sc_run_elapsed` wie bisher |
| `run_watch.py:996` | `_watch_settle_by_window`, Fenster zu kurz | `actual_s = window` (Task 5) |
| `run_watch.py:1019` | `_watch_finish` ohne Tor | unverändert |
| `run_watch.py:1033` | `_watch_give_up` | für Service unerreichbar: `acknowledges=False`, `arm_give_up_after_start=False`, `opens_at_dispatch=True` (`self_closing.py:54-73`) → kein Give-up-Timer. Nur OpenSprinkler, unverändert |
| `batch.py:557`, `batch.py:663` | Batch-Pausen-Schranke, Batch-Stopp | Batch, unverändert |
| `opensprinkler.py:499` | OpenSprinkler-Stopp | unverändert |

**`_watch_settle_by_window` und `_watch_valve_window` (neue Fensterregel)**

| Stelle | Aufrufer | Tor davor |
|---|---|---|
| `run_watch.py:1008` | `_watch_finish` | `run_has_finish_grace(run)` (`:1002`, Task 5) |
| `self_closing.py:478` | `_sc_backstop_fired` | Wartezeit ≠ 0 UND `RUN_VALVE_OFF` (Task 6) |
| `self_closing.py:1016` | Neustart, Sofort-Zweig | `grace and RUN_VALVE_OFF` (`:1011`, Task 8) |
| `run_watch.py:992` | `_watch_settle_by_window` selbst | — |
| `self_closing.py:904` | manueller Stopp | `elif run_has_finish_grace(run)` (`:891`, Task 7) |

**`_watch_evaluate` (Aus-Meldung stempeln) und das Schlüsselwort `previous_state`**

| Stelle | Pfad | Stand |
|---|---|---|
| `run_watch.py:674` / `:677` | Subscription `_watch_state_changed` | einziger Aufrufer, der `previous_state=event.data.get("old_state")` übergibt → stempelt `RUN_VALVE_OFF` (`:764`) nur, wenn der Vorzustand laufend war (`:734-737`, Task 4, E6); nie aus `unavailable`/`unknown`/fehlend → `off` (Tests `unavailable_mid_run_records_nothing`, `re_adopted_run_does_not_record_an_off_after_unavailable`, Task 4; `back_from_unavailable`, Task 8) |
| `run_watch.py:664` | erste Auswertung in `_watch_start` (auch Neustart) | `previous_state` Default `None` → stempelt nie (Test `re_adopted_run_does_not_record_the_initial_off`, Task 4) |
| `batch.py:611` | Batch-Neuauswertung (nur `RUN_MODE == batch`) | `previous_state` Default `None`, Tor ohnehin falsch. Unverändert |
| `opensprinkler.py:603` | `_os_evaluate` | `previous_state` Default `None`, Tor falsch. Unverändert |
| `run_watch.py:717`, `:724` | Laufend-Zweig löscht `RUN_VALVE_OFF` | nur `settles_on_valve_window` (Task 4) |

**`zone_confirm_seconds` (Zeitfenster-Preis)**

| Stelle | Pfad | Stand |
|---|---|---|
| `irrigation.py:2566` | Planung `ZoneRun` im Scheduler | über die Funktion (`run_window.py:368`): 30 + Wartezeit nur Service-Track mit `confirm_entity` (Task 10) |
| `run_window.py:906` | Nominal-Fenster (Zifferblatt) | dieselbe Funktion (Task 10, Test `dial_carries_…`) |

**`_note_si_valve` (Observed-Sperre)**

| Stelle | Pfad | Stand |
|---|---|---|
| `self_closing.py:562` | Service-/OpenSprinkler-Dispatch | `planned + zone_finish_grace_seconds(zone)` (`:564`, Task 3b); OpenSprinkler = 0 |
| `run_watch.py:836` | `_watch_observed_start` | nur `not opens_at_dispatch` (OpenSprinkler). Unverändert |
| `batch.py:330` | Batch | unverändert |
| `irrigation.py:1403`, `:1513`, `:1629`, `:1692`, `:2097` | klassische Ventile (metered, Flow-Slot, rotierend) | kein Watcher, kein Backstop. Unverändert |

**`_self_closing_run_in_flight`**: einziger Aufrufer `run_state.py:140` `zone_run_in_flight` → Fenster
`planned + run_finish_grace_seconds(run)` (`run_state.py:106`, Task 9); darüber laufen Kette,
Doppel-Dispatch-Wächter und aufgeschobene Berechnung.

**Leser der neuen Laufdaten-Schlüssel** (außer `const.py`): `RUN_LATENCY_MARGIN` nur `run_watch.py:294`
(`run_latency_margin`), geschrieben `self_closing.py:700`; `RUN_VALVE_ON` nur `run_watch.py:341`
(`valve_window_seconds`), geschrieben `self_closing.py:701`; `RUN_VALVE_OFF` gelesen `run_watch.py:348`,
`:717`, `:737`, `self_closing.py:476`, `:1011`, geschrieben/gelöscht nur `run_watch.py:724`, `:764`. Übrige
Treffer sind Kommentare/Docstrings (`run_watch.py:335`, `:980`, `self_closing.py:575`, `:622`).

**Leser von `RUN_STARTED`**

| Stelle | Leser | Stand |
|---|---|---|
| `irrigation.py:377` | Panel-Countdown `started_at`/`ends_at` | bewusst unverändert (Spec: Countdown bleibt Start + geplant) |
| `run_state.py:109` | In-flight-Anker | Anker unverändert, Fenster + Wartezeit (Task 9) |
| `self_closing.py:790` | `_sc_run_elapsed` | unverändert; der manuelle Stopp eines Laufs mit Tor umgeht ihn (Task 7) |
| `self_closing.py:1001` | Neustart-`elapsed` | Anker unverändert (inkl. Ausfallzeit), Schwelle + Wartezeit (Task 8) |
| `run_watch.py:343` | `valve_window_seconds` | letzter Rückfall-Anker nach `RUN_VALVE_ON`, `RUN_OBSERVED_START` (Task 2) |
| `run_watch.py:585` | `_watch_observed_start_iso` | Service: `RUN_OBSERVED_START = RUN_STARTED`, unverändert (OpenSprinkler überschreibt die Methode in `opensprinkler.py:605`) |
| `batch.py:352`, `self_closing.py:676` | Schreiber | — |
| `const.py:944/960/980/984`, `run_state.py:66`, `run_watch.py:49`, `self_closing.py:486/624/664/771/987` | Definition, Kommentare, Docstrings | — |

Verteiler: der letzte `grep` liefert `0` (ein loses `_watch_` trifft nur `_dist_watch_mode`) — eigener Pfad,
unberührt.

Ergebnis: kein vom Plan übersehener Pfad. Vorbestehend und NICHT von #139 (für `ToDo.md`, Task 14 Step 7,
nicht in den PR): nach einem Neustart setzt kein Pfad die Observed-Sperre für einen weiterlaufenden Service-Lauf
neu (`_si_driven_until` lebt nur im Speicher; `self_closing.py:1023-1030` ruft `_note_si_valve` nicht, und
`_watch_observed_start` wird wegen gespeichertem `RUN_OBSERVED_START` nicht erneut durchlaufen).

- [ ] **Step 6: Text-Hygiene im Gesamt-Diff**

```bash
cd /d/Entwicklung/HASI/HAsmartirrigation
git diff 0b418644 HEAD -- custom_components tests docs | grep -nE "HA-Prod|HA-Test|Eifel|192\.168|Kirschlorbeer|Beet|[0-9a-f]{8,}" | cut -c1-160
git diff 0b418644 HEAD -- custom_components tests docs ':!custom_components/irrigation_plus/frontend/dist' | grep -nE "^\+.*(Beet|beet|Kirschlorbeer|kirschlorbeer|Kirschbaum|Tuya|SONOFF|Sonoff)"
git diff 0b418644 HEAD -- custom_components tests docs ':!custom_components/irrigation_plus/frontend/dist' | grep -cE "^\+.*\b([0-9]{1,3}\.){3}[0-9]{1,3}\b"
git diff 0b418644 HEAD -- custom_components tests docs ':!custom_components/irrigation_plus/frontend/dist' | grep -cE "^\+.*(HA-Prod|HA-Test|Eifel|eifel)"
git diff 0b418644 HEAD -- custom_components tests docs ':!custom_components/irrigation_plus/frontend/dist' | grep -cE "^\+.*\b[0-9a-f]{7,40}\b"
git diff 0b418644 HEAD -- tests | grep -cE "^\+.*(2026, 9, 13|422\.9|423\.4|beet_flowing)"
```

Erwartet (real): 33 Treffer im ersten Befehl, alle beurteilt:

| Treffer | Beurteilung |
|---|---|
| 28× `index aaaaaaaa..bbbbbbbb` | git-Metadaten des Diffs, kein Inhalt |
| 2 Zeilen dist `irrigation-plus.js` (das `-`/`+`-Paar derselben minifizierten Zeile; Ziffernfolgen `2369362920544`, `0295299830714`, `264172052` stehen auf beiden Seiten) | Zahlen im Bundle, schon upstream, keine SHA |
| `tests/test_service_watch.py`: Docstrings „The Beet valve: …“ (2×) | Testtext zur Fixture-Zone, die upstream schon `Beet` heißt (`tests/test_service_watch.py:73` auf `0b418644`). Belassen |
| `tests/test_store_self_closing.py`: `"name": "Beet"` | Test-Fixture wie `:59` auf der Basis. Belassen |

Zweiter Befehl: 8 Zeilen. `const.py` und `self_closing.py` je ein Kommentar „measured … Tuya valves“,
`tests/test_service_watch.py` „late Tuya close“ und die zwei `Beet`-Docstrings, `tests/test_store_self_closing.py`
`"name": "Beet"`, `"run_service": "script.irrigation_beet"`, `"confirm_entity": "valve.beet"`. Beibehaltene
Namen mit upstream-Präzedenz auf `0b418644`:

| Name | Präzedenz upstream |
|---|---|
| `Tuya` (Gerätemarke im Kommentar) | `const.py:543`, `const.py:555`, `irrigation.py:733` |
| Zone `Beet`, `script.irrigation_beet` | `tests/test_service_watch.py:73/75`, `tests/test_store_self_closing.py:59/63`, `tests/test_credit_ceiling.py:53/55` |
| `valve.beet` | `tests/test_store_self_closing.py:66` |

`Kirschlorbeer`/`kirschlorbeer`/`Kirschbaum`: kein neuer Treffer (E7); die vorhandenen upstream-Stellen
(`irrigation.py:1262`, `tests/test_flow_calibration.py:196`, `tests/test_self_closing.py:140`) sind
unverändert. Die vier Zählbefehle geben je `0`: keine IP, kein `HA-Prod`/`HA-Test`/`Eifel`, keine
Hex-Folge (SHA) in einer neuen Zeile außerhalb von dist, und keine aus der Installation abgeleiteten Daten
in neuen Testzeilen. Der letzte Befehl sucht genau die Werte, die `tests/test_finish_grace_helpers.py` vor
dem Feinschliff trug: Entität `binary_sensor.beet_flowing`, Ankerdatum 2026-09-13 und das gemessene Fenster
422,9 s (Ein +0,5 s, Aus +423,4 s) eines echten Laufs. Jetzt `binary_sensor.valve_flowing`,
`T0` = 2026-01-10 10:00:00 UTC, Ein +0,5 s, Aus +420,5 s, Fenster 420,0 s.

- [ ] **Step 7: Mutationsproben aller Tasks (Konsolidierung)**

Zusammenfassung der in Task 1–12 beobachteten Ergebnisse; neu im Feinschliff sind nur die zwei Proben von
Task 5 zum Pin „`unavailable` mitten im Lauf“, dazu wurden die Proben von Task 2, 5 und 11 am jeweiligen
Endstand-Commit erneut gefahren. „gefangen“ = der genannte Test
scheiterte unter der Mutation und war nach dem Zurückkopieren wieder grün; „äquivalent“ = Verhalten
nachweislich gleich, Begründung im jeweiligen Task. Nach jeder Probe war die Produktionsdatei per SHA-256 bzw.
`git diff`-Prüfsumme wieder im Ausgangsstand (je Task belegt).

Herkunft der Proben (wo sie liefen, und warum das Ergebnis für den Endstand gilt):

| Task | Lauf | Commit der Probe | Unterschied zum Endstand-Commit |
|---|---|---|---|
| 1 | Revision | `745e4bac` | keiner |
| 2 | Revision nach dem Feinschliff | `94cc3785` | keiner (alle 22 Proben am Endstand-Commit erneut; patch-id wegen Kommentar und Testdaten neu) |
| 3 | Revision | `c445ec44` | `tests/test_store_self_closing.py` (E7-Namen); aus dem Feinschliff `const.py` (nur Kommentar von `RUN_VALVE_OFF`) und `tests/test_finish_grace_helpers.py` (Testdaten), beide von keiner Probe dieses Tasks berührt |
| 3b | Revision | `097d6690` | wie Task 3 |
| 4 | Revision | `6aef25d3` | wie Task 3 (`run_watch.py` und `tests/test_service_watch.py` gleich) |
| 5 | Revision nach dem Feinschliff | `8528d4d0` | keiner (alle 13 Proben am Endstand-Commit erneut) |
| 6 | Revision (nach dem Umbau erneut) | `dfb796c3` | `self_closing.py` und Testklasse gleich; aus dem Feinschliff `const.py` (Kommentar), `tests/test_finish_grace_helpers.py`, `tests/test_service_watch.py` (+1 Test in der Klasse von Task 5, daher `44 deselected` statt `43`) |
| 7 | Revision | `69a9ee45` | `self_closing.py` nur das Tor von `_sc_backstop_fired` (Task 6), `tests/test_service_watch.py` Klassenposition und +1 Test in Task 5; `const.py`-Kommentar und Helfer-Testdaten aus dem Feinschliff |
| 8 | Revision | `71f08c0d` | `git diff --stat 71f08c0d b503b663`: 5 Dateien — `const.py` (Kommentar von `RUN_VALVE_OFF`), `self_closing.py` (nur das Task-6-Tor), `tests/test_finish_grace_helpers.py` (Testdaten), `tests/test_service_watch.py` (Klasse `TestARestartCarriesTheFinishGrace` byte-gleich, Änderungen außerhalb, darunter +1 Test in Task 5), `tests/test_store_self_closing.py` (E7-Namen `Kirschlorbeer` → `Front`); keine davon berührt eine Probe dieses Tasks |
| 9 | erster Probelauf | `fd32d381` | patch-id gleich (`f7e9a2ffb269`, auch nach dem Feinschliff: `ce7a1d13`); Dateien upstream unberührt |
| 10 | erster Probelauf | `b7d7f0c5` | patch-id gleich (`3772c1840e46`, auch `8d7ebbed`); Dateien upstream unberührt |
| 11 | Revision nach dem Feinschliff | `7c626143` | keiner (alle 6 Proben erneut; patch-id wegen des Test-Kommentars neu) |
| 12 | erster Probelauf | `0c205e46` | patch-id ohne dist gleich (`6ea5e4ff0cd2`, auch `67301a8b`; der Feinschliff änderte nur die Nachricht); upstream änderte nur dist, das neu gebaut ist (Step 4) |

| Task | Probe | Datei | Ergebnis |
|---|---|---|---|
| 1 | load-line | store.py | gefangen (`test_latency_margin_survives_reload`) |
| 1 | load-default | store.py | gefangen (`…without_latency_margin_loads_the_default`) |
| 1 | const-default | const.py | gefangen (dito) |
| 1 | store-revert | store.py | gefangen (beide Store-Tests) |
| 1 | ws-coerce-removed | websockets.py | gefangen (`test_zone_view_coerces_latency_margin_to_int`) |
| 1 | ws-coerce-float | websockets.py | gefangen (dito) |
| 2 | zone-clamp | run_watch.py | gefangen |
| 2 | zone-round | run_watch.py | gefangen |
| 2 | zone-garbage | run_watch.py | gefangen |
| 2 | zone-default | run_watch.py | gefangen |
| 2 | zone-mode-gate | run_watch.py | gefangen |
| 2 | zone-confirm-gate | run_watch.py | gefangen |
| 2 | zone-grace-settle | run_watch.py | gefangen |
| 2 | run-margin-negative | run_watch.py | gefangen |
| 2 | run-grace-policy | run_watch.py | gefangen |
| 2 | run-grace-margin-gate | run_watch.py | gefangen |
| 2 | run-grace-watch-gate | run_watch.py | gefangen |
| 2 | run-grace-settle | run_watch.py | gefangen |
| 2 | tolerance-floor | run_watch.py | gefangen |
| 2 | tolerance-no-grace | run_watch.py | gefangen |
| 2 | window-off-clamp | run_watch.py | gefangen |
| 2 | window-plan-bound | run_watch.py | gefangen |
| 2 | window-anchor-valve-on | run_watch.py | gefangen |
| 2 | window-anchor-observed | run_watch.py | gefangen |
| 2 | window-no-anchor | run_watch.py | gefangen |
| 2 | policy-service-flag | self_closing.py | gefangen |
| 2 | policy-default-true | run_watch.py | gefangen |
| 2 | resume-adds-settle | run_watch.py | gefangen (`remaining_window_only`, Batch-Resume-Pin) |
| 3 | margin-record | self_closing.py | gefangen (inkl. Bestandstest `armed_once`) |
| 3 | margin-default | self_closing.py | gefangen |
| 3 | valve-on-record | self_closing.py | gefangen |
| 3 | clamp-lower | self_closing.py | gefangen |
| 3 | clamp-upper | self_closing.py | gefangen |
| 3 | report-ignored | self_closing.py | gefangen |
| 3 | lower-is-confirm-return | self_closing.py | gefangen |
| 3 | upper-is-dispatch | self_closing.py | gefangen |
| 3 | backstop-no-grace | self_closing.py | gefangen |
| 3 | backstop-grace-from-zone | self_closing.py | gefangen |
| 3 | backstop-grace-always | self_closing.py | gefangen |
| 3 | margin-for-every-record | self_closing.py | gefangen |
| 3 | valve-on-for-unverifiable | self_closing.py | gefangen |
| 3b | lockout-no-grace | self_closing.py | gefangen (`confirm_entity_is_locked_out`) |
| 3b | lockout-grace-always | self_closing.py | gefangen (`write_only_zone`) |
| 3b | lockout-grace-from-run-keys (neu in der Revision) | self_closing.py | gefangen (`confirm_entity_is_locked_out`) |
| 4 | previous-state-not-passed (neu, E6) | run_watch.py | gefangen (4 Tests) |
| 4 | initial-evaluate-records | run_watch.py | gefangen |
| 4 | clock-not-last-changed | run_watch.py | gefangen |
| 4 | grace-gate-removed | run_watch.py | gefangen |
| 4 | running-condition-removed (neu, E6) | run_watch.py | gefangen (`unavailable_mid_run_records_nothing`, `re_adopted_run_does_not_record_an_off_after_unavailable`) |
| 4 | unavailable-accepted (neu, E6) | run_watch.py | gefangen (dito) |
| 4 | clear-removed | run_watch.py | gefangen |
| 4 | clear-gated-on-segmented | run_watch.py | gefangen |
| 4 | first-off-guard-removed | run_watch.py | äquivalent seit E6 (im ersten Probelauf gefangen; ein zweites `off` ohne laufenden Vorzustand zeichnet ohnehin nicht auf) |
| 4 | guard-removed-and-last-updated | run_watch.py | äquivalent seit E6 (im ersten Probelauf gefangen; aufgezeichnet wird nur beim echten Wechsel aus „laufend“, dort `last_changed == last_updated`) |
| 4 | last-updated | run_watch.py | äquivalent (bei echtem Zustandswechsel `last_changed == last_updated`) |
| 4 | clear-policy-gate-removed | run_watch.py | äquivalent (`RUN_VALVE_OFF` entsteht nur für Läufe mit Tor) |
| 5 | finish-actual-dropped | self_closing.py | gefangen |
| 5 | stop-actual-dropped | self_closing.py | gefangen |
| 5 | tolerance-one-second | run_watch.py | gefangen |
| 5 | tolerance-no-floor | run_watch.py | gefangen |
| 5 | decide-time-window | run_watch.py | gefangen |
| 5 | finish-window-not-passed | run_watch.py | gefangen |
| 5 | stop-window-not-passed | run_watch.py | gefangen |
| 5 | never-routed | run_watch.py | gefangen |
| 5 | always-routed | run_watch.py | gefangen (`before_the_update_keeps_the_old_rule`) |
| 5 | finish-volume-on-actual (neu in der Revision) | self_closing.py | gefangen (`just_after_the_window`: Zeitvolumen bleibt auf `planned_s`) |
| 5 | finish-calibration-on-actual (neu in der Revision) | self_closing.py | gefangen (dito, Kalibrierprobe bleibt auf `planned_s`) |
| 5 | window-planned-without-off (neu im Feinschliff) | run_watch.py | gefangen (`unavailable_mid_run_settles_on_the_clock`: ohne Aus-Meldung begrenzt die Uhr, nicht nur der Plan) |
| 5 | unavailable-accepted (neu im Feinschliff) | run_watch.py | gefangen (dito: kein `RUN_VALVE_OFF` aus `unavailable` → `off`) |
| 6 | backstop-always-finish | self_closing.py | gefangen |
| 6 | done-reverted | self_closing.py | gefangen |
| 6 | dispatch-no-grace | self_closing.py | gefangen |
| 6 | dispatch-settle-only | self_closing.py | gefangen |
| 6 | finish-keeps-handle | self_closing.py | gefangen |
| 6 | off-gate-dropped | self_closing.py | äquivalent (ohne Aus-Meldung ist das Fenster beim Backstop = `planned`) |
| 6 | grace-gate-dropped | self_closing.py | äquivalent (`RUN_VALVE_OFF` nur mit Tor) |
| 7 | stop-branch-reverted | self_closing.py | gefangen |
| 7 | graced-stop-books-plan | self_closing.py | gefangen |
| 7 | graced-stop-ignores-off | self_closing.py | gefangen |
| 7 | graced-stop-uncapped | self_closing.py | gefangen |
| 7 | else-anchored-on-valve-on | self_closing.py | gefangen |
| 7 | grace-gate-dropped | self_closing.py | gefangen nur von bestehenden Suiten (`test_self_closing.py`, `test_opensprinkler.py`, `test_batch.py`, `test_credit_ceiling.py`), die neuen Tests bleiben grün |
| 7 | actual-s-after-grace | self_closing.py | äquivalent (`actual_s` kommt nur aus `_watch_settle_by_window`, gleicher Datensatz, gleicher Moment) |
| 8 | grace-reverted | self_closing.py | gefangen |
| 8 | immediate-at-plan | self_closing.py | gefangen |
| 8 | backstop-without-grace | self_closing.py | gefangen |
| 8 | stored-off-ignored | self_closing.py | gefangen |
| 8 | no-finish-without-off | self_closing.py | gefangen |
| 8 | watcher-not-readopted | self_closing.py | gefangen |
| 8 | window-unbounded | run_watch.py | gefangen |
| 8 | grace-for-every-record | self_closing.py | gefangen (Pin `test_resume_finalises_overdue_and_reschedules_partial`) |
| 8 | running-condition-removed (neu, E6) | run_watch.py | gefangen (`back_from_unavailable`, dazu die zwei Task-4-Tests) |
| 8 | unavailable-accepted (neu, E6) | run_watch.py | gefangen (dito) |
| 8 | settle-by-window-without-off | self_closing.py | äquivalent (Sofort-Zweig: Fenster ohne Aus-Meldung = `planned`) |
| 9 | drop-grace | run_state.py | gefangen |
| 9 | grace-for-every-record | run_state.py | gefangen |
| 9 | grace-doubled | run_state.py | gefangen |
| 10 | revert-to-poll | run_window.py | gefangen (inkl. Pin 219) |
| 10 | margin-ignored | run_window.py | gefangen |
| 10 | grace-leaks-to-batch-station | run_window.py | gefangen |
| 10 | grace-leaks-to-classic | run_window.py | gefangen |
| 11 | gate-always-true | view-zone-settings.ts | gefangen (vitest) |
| 11 | gate-ignores-empty | view-zone-settings.ts | gefangen (vitest) |
| 11 | clamp-no-upper | view-zone-settings.ts | gefangen (vitest) |
| 11 | clamp-no-lower | view-zone-settings.ts | gefangen (vitest) |
| 11 | clamp-no-round | view-zone-settings.ts | gefangen (vitest) |
| 11 | clamp-no-nan-guard | view-zone-settings.ts | gefangen (vitest) |
| 12 | sk-help-missing | sk.json | gefangen (`test_no_missing_keys[panel-sk]`) |
| 12 | fr-help-english | fr.json | gefangen (`test_no_value_is_left_as_the_english_string[panel-fr]`) |

Dazu in Task 7 ein Beleg ohne Produktionsprobe (`bucket-only-vs-uncapped`): die frühere Eimer-Zusicherung
allein fing `graced-stop-uncapped` nicht, deshalb prüft `still_on_is_capped` `actual_s` und Zeitvolumen. Er
zählt unten nicht mit.

Summe je Task (Proben / gefangen / äquivalent): T1 6/6/0, T2 22/22/0, T3 13/13/0, T3b 3/3/0, T4 12/8/4,
T5 13/13/0, T6 7/5/2, T7 7/6/1 (davon 1 nur durch bestehende Suiten), T8 11/10/1, T9 3/3/0, T10 4/4/0,
T11 6/6/0, T12 2/2/0. **Gesamt 109 Proben: 101 gefangen, 8 äquivalent mit Begründung, 0 überlebende
nicht-äquivalente Mutation.** Jeder neue oder geänderte Test scheiterte an mindestens einer Probe (je Task
belegt).

Streichen JustChrs Antworten Tasks (Step 8), fallen deren Zeilen weg: ohne 3b −3, ohne 6 −7 (−2 äquivalent),
ohne 7 −7 (−1 äquivalent), ohne 10 −4; ohne alle vier 88 Proben (83 gefangen, 5 äquivalent).

- [ ] **Step 8: Abtrennbare Tasks**

Der Nutzer fragt JustChr auf #139, ob vier Teile in den Fix gehören (Task 14, „Umfang“). Jeder muss sich durch
Streichen GENAU EINES Commits entfernen lassen, ohne Konflikt und ohne rote Tests in den späteren Tasks.

| Task | Commit (Betreff) | Was der Fix ohne ihn verliert |
|---|---|---|
| 3b | `feat(service): keep the observed-watering lockout over a confirmed run's finish grace` | Die Observed-Sperre endet wie bisher bei geplantem Fenster + 30 s (`SI_VALVE_SUPPRESS_MARGIN`) ab Dispatch statt zusätzlich nach der Wartezeit, sodass bei aktivem Observed-Watering ein Nachlauf, der über diese 30 s hinausreicht (hohe Marge plus Confirm-Verzögerung), als externer Lauf gutgeschrieben werden könnte. |
| 6 | `feat(service): let the backstop settle a reported close on its window` | Schließt ein Ventil später als seine Marge, sodass der Backstop in die Entprellung fällt, wird der Lauf mit `actual_s = planned_s` abgeschlossen und die gespeicherte Aus-Meldung verworfen (nur die aufgezeichnete Dauer weicht ab, der Lauf bleibt `completed`). |
| 7 | `feat(service): measure a manual stop on the valve's own window` | Ein manueller Stopp misst wie bisher ab `RUN_OBSERVED_START` (Confirm-Rückkehr) bis zum Stopp: bis zu eine Poll-Periode zu kurz, und ein Stopp in der Wartezeit bucht über das geplante Fenster bzw. über die gespeicherte Aus-Meldung hinaus (`actual_s` und Zeitvolumen). |
| 10 | `feat(service): price a confirmed service zone's finish grace into the window` | Der Zeitfenster-Preis einer bestätigten Service-Zone bleibt bei 30 s Confirm-Reserve, eine sequentielle Service-Kette ist also je Zone um Entprellung + Marge (Default 9 s) unterbepreist und kann Finish-Anker und Arm-Schranke um so viel überziehen. |

Streichen (auf dem noch nicht gepushten Arbeitsbranch; nach einem Push stattdessen auf einem neuen Branch,
kein Rebase auf gepushten Branches). Der Commit wird über seinen Betreff gefunden, weil sich die SHAs mit
jedem Rebase ändern. Beispiel Task 6, für die anderen den Betreff aus der Tabelle einsetzen:

```bash
cd /d/Entwicklung/HASI/HAsmartirrigation
git status --short
T=$(git log --format='%h %s' 0b418644..HEAD | grep -F "feat(service): let the backstop settle a reported close on its window" | cut -d' ' -f1)
echo "$T"
git rebase --onto "$T^" "$T"
```

Alle vier auf einmal: nacheinander in der Reihenfolge Task 10, 7, 6, 3b (jüngster zuerst). Ein Rebase
schreibt nur die Commits NACH dem gestrichenen um, die SHAs der älteren bleiben gültig.

Danach, in jedem Fall:

```bash
cd /d/Entwicklung/HASI/HAsmartirrigation
mkdir -p D:/Entwicklung/HASI/pr139-work/tmp D:/Entwicklung/HASI/pr139-work/npm-cache && export TEMP=D:/Entwicklung/HASI/pr139-work/tmp TMP=D:/Entwicklung/HASI/pr139-work/tmp TMPDIR=D:/Entwicklung/HASI/pr139-work/tmp npm_config_cache=D:/Entwicklung/HASI/pr139-work/npm-cache
uvx black --check custom_components/irrigation_plus/
uvx ruff check custom_components/irrigation_plus/
./.venv/Scripts/python.exe -m pytest tests/test_service_watch.py tests/test_finish_grace_helpers.py tests/test_run_in_flight.py tests/test_confirm_reserve.py tests/test_self_closing.py tests/test_run_watch.py tests/test_observed_watering.py -p _local_socket_unblock -q
```

Real beobachtet im Revisions-Probelauf nach dem Feinschliff (`dry2`, Endstand `67301a8b`; je ein temporärer Branch
`tmp/drop-<Task>` von `dry2/backstop-grace`, `git rebase --onto <Task>^ <Task>`, danach gelöscht). Jeder
Rebase meldete `Successfully rebased and updated refs/heads/tmp/drop-…` ohne Konflikt, Lint jedes Mal
`67 files would be left unchanged.` / `All checks passed!`:

| Gestrichen | Probelauf-Commit | Rebase | pytest (7 Dateien) | Differenz |
|---|---|---|---|---|
| nichts (Endstand) | — | — | `228 passed, 1 error` | — |
| Task 3b | `99c9272d` | 9 Commits neu | `226 passed, 1 error` | −2 (Tests von 3b) |
| Task 6 | `a3c220e5` | 6 Commits neu | `225 passed, 1 error` | −3 (Tests von 6) |
| Task 7 | `b59fcdf9` | 5 Commits neu | `223 passed, 1 error` | −5 (Tests von 7) |
| Task 10 | `8d7ebbed` | 2 Commits neu | `225 passed, 1 error` | −3 (Tests von 10) |
| alle vier (10, 7, 6, 3b) | wie oben | 2 + 4 + 4 + 6 | `215 passed, 1 error` | −13 |

Der eine Error ist jedes Mal der vorbestehende `Lingering timer` in
`tests/test_service_watch.py::TestOneOffSampleIsNotEvidenceTheWaterStopped::test_the_run_is_not_settled_before_the_window_is_out`
(steht schon in der Basis). Kein FAILED. Task 11 und 12 (Panel, Übersetzungen, Doku, dist) berühren keinen
der vier Tasks und rebasen unverändert; der Doku-Punkt beschreibt nur Marge, Entprellung und Backstop-Zeitpunkt
(Task 3/5), nichts aus 3b, 6, 7 oder 10.

Damit das gilt, wurde der Plan im Revisions-Probelauf umgebaut. Vorher: Streichen von Task 6 → Rebase-Konflikt
in `tests/test_service_watch.py` beim Anwenden von Task 7; Streichen aller vier → `NameError: name '_advance'
is not defined` in vier Tests von Task 8 (`4 failed, 210 passed, 5 errors`). Umbau per Fixup-Commits +
Autosquash:
- `_advance` steht in Task 5 (benutzt dort von `_run_until_the_valve_closes`), nicht mehr in Task 6.
- Task 6 importiert nichts: Tor `run_finish_grace_seconds(run)` (seit Task 3 importiert, für jeden Datensatz
  gleichwertig zu `run_has_finish_grace`); Task 7 importiert `run_has_finish_grace` selbst.
- Die Testklasse von Task 7 steht unter `TestAWriteOnlyValveIsUntouched`, nicht direkt unter der von Task 6.
- Task 8 benutzt nur `_advance` (Task 5), nichts aus 3b, 6 oder 7.

Einschränkung, kein Test-Bruch: Werden Task 3b UND Task 10 gestrichen, hat `zone_finish_grace_seconds`
(Task 2) keinen Aufrufer im Produktionscode mehr (nur `tests/test_finish_grace_helpers.py`; heute
`self_closing.py:564` aus 3b und `run_window.py:368` aus 10), und sein Docstring nennt noch „the window pricing
and the observed-watering lockout at dispatch“. Dann den Docstring in Task 2 von Hand anpassen oder den Helfer
samt seiner Tests streichen (ruff meldet unbenutzte Funktionen nicht).

- [ ] **Step 9: Kein Commit**

Dieser Task committet nichts. Hat ein Schritt einen Defekt aufgedeckt, gilt dafür ein eigener Commit mit Test
nach dem Muster der Tasks 1–10, und Step 2–4 laufen danach erneut. Im Revisions-Probelauf deckte Task 13 keinen
Defekt auf.

**Neue Test-Helfer:** keine.

---

### Task 14: PR-Text, Kommentar auf #139, Design-Historie, Befunde — jeder Außenschritt mit eigener Freigabe

**Files:**
- Create (außerhalb des Repos): `D:\Entwicklung\HASI\pr139-work\pr-body.md`, `D:\Entwicklung\HASI\pr139-work\comment-139.md`
- Modify: `D:\Entwicklung\HASI\ToDo.md`, `HAsmartirrigation/docs/SESSION-STAND.md` (untracked)
- Archiv: `docs/superpowers/specs/2026-09-15-backstop-grace-design.md`, `docs/superpowers/plans/2026-09-15-backstop-grace.md` auf `archive/design-history`

Regeln: globale `CLAUDE.md` „Text-Freigabe“ und „Alles, was nach außen geht … nur nach expliziter
Freigabe“; Skill `pr-workflow`; Memory `workflow-agent-hygiene` (alle Zahlen im PR-Text auf dem
Endstand nachmessen, nicht aus Zwischenständen übernehmen); Memory `no-branch-shas-in-upstream-comments`.

**Umfang folgt JustChrs Antwort auf #139.** Die Scope-Frage (Kommentar vom 2026-09-15: Zeitfenster-Preis,
Observed-Sperre, Backstop mit gespeicherter Aus-Meldung, manueller Stopp) entscheidet, welche der vier
abtrennbaren Tasks im PR bleiben. Sagt er, ein Teil gehört nicht in den Fix, wird VOR Step 1 genau dessen
Commit gestrichen: Task 10 (Zeitfenster-Preis), Task 3b (Observed-Sperre), Task 6 (Backstop mit
Aus-Meldung), Task 7 (manueller Stopp), mit den im Probelauf geprüften Befehlen aus Task 13, Step 8
(Commit über den Betreff finden, `git rebase --onto "$T^" "$T"`, bei mehreren jüngster zuerst: 10, 7, 6, 3b;
danach Lint und die sieben Testdateien von dort). Danach Task 13, Step 2–4 erneut auf dem neuen Endstand.
Werden 3b UND 10 gestrichen, gilt die Einschränkung aus Task 13, Step 8 (Docstring bzw. Helfer
`zone_finish_grace_seconds`). Keine Antwort, kein Streichen: der PR geht mit allen vier. Die Antwort
selbst entscheidet der Plan nicht.

- [ ] **Step 1: Zahlen auf dem Endstand nachmessen**

Aus Task 13 (Endstand nach einem etwaigen Streichen, nicht Probelauf): Suite vorher/nachher, Zahl neuer
Test-Items, vitest vorher/nachher, Mutationsproben gesamt/gefangen/äquivalent. Jede Zahl im PR-Text muss aus
diesen Ausgaben stammen. Zur Orientierung der Probelauf mit allen vier Tasks (Task 13, Step 3, 4 und 7):
`2906` → `2993 passed` bei identischen 7 FAILED und 320 Errors (+87 Items), vitest `614` → `622`,
109 Mutationsproben (101 gefangen, 8 äquivalent). Jeder gestrichene Task senkt diese Zahlen.

- [ ] **Step 2: PR-Text entwerfen** (`pr139-work/pr-body.md`, Englisch)

Pflichtabschnitte, in dieser Reihenfolge:
1. `## Problem` — Backstop ohne Zuschlag pre-emptet die Entprellung; Messungen (Beet −2,03 s nach
   `e9f2da51`; Kirschlorbeer +0,57/+1,13 s in die Entprellung); `_watch_finish` erreicht nie ein normales
   Ende; `actual_s` +4 s auf Teil-Läufen; Start ~0,9 s hinter der Ein-Meldung.
2. `## Fix` — Wartezeit = settle + Latenz-Marge je Zone (nur bestätigte Service-Läufe); `actual_s` =
   Aus-Meldung − Ein-Meldung (`last_changed`, geklemmt); Toleranz max(1 s, Marge); Backstop mit
   gespeicherter Aus-Meldung rechnet nach dem Fenster ab; Neustart; In-flight, Zeitfenster-Preis und
   Observed-Sperre ziehen die Wartezeit mit; Zonenfeld `latency_margin` (Default 4 s, 0–30) mit
   Begründung aus den Recorder-Daten (Tuya 2,08–2,90 s roh, nötig max. 2,03 s; SONOFF max. 1,13 s).
   Gestrichene Tasks (siehe „Umfang“) fallen hier und in Abschnitt 3 heraus.
3. `## Behaviour changes not behind the setting` — die Liste aus der Spec, Abschnitt „Reichweite“, jede
   Zeile mit Reichweite (welche Zonen, was sichtbar wird).
4. `## Where this differs from the shape on #139` — (a) `_watch_resume` für Service unerreichbar
   (`segmented=False`), Test ersetzt durch Neustart-Tests + Pin, dass Batch `remaining` behält;
   (b) Backend-Katalog hat keinen Zonenfeld-Bereich, #125 hat nur Panel-Kataloge geändert.
5. `## Untouched` — Batch, OpenSprinkler, Verteiler, write-only Service-Zonen (ausdrücklich, wie gewünscht).
6. `## Testing` — Suite vorher/nachher mit identischen FAILED-Namen, neue Items, vitest, Mutationsproben
   (Tabelle kompakt), black/ruff, dist unter Node 24 = Node-22-CI reproduziert. Als geänderte
   Bestands-Pins nennt der Abschnitt genau zwei: `tests/test_service_watch.py`
   `test_the_finish_backstop_is_armed_once` `(2, 600)` → `(2, 609)` (Task 3; bleibt auch, wenn 3b/6/7/10
   gestrichen werden) und `tests/test_confirm_reserve.py` 219
   (`test_a_self_closing_zone_pays_only_with_a_confirm_entity`: 30 → 30 + 5 + 4 = 39, Task 10; entfällt,
   wenn Task 10 gestrichen ist). `test_a_valve_off_at_the_planned_end_completes` (Task 5) behält seine
   Erwartung `actual_s == planned_s == 600` und läuft nur unter eingefrorener Uhr — kein geänderter Pin.
7. `## Re-measure` — nach dem Merge beide Zonen nachmessen, Kriterien aus Task 15.
8. Footer `🤖 Generated with [Claude Code](https://claude.com/claude-code)`.

Keine IP-Adressen, keine Branch-SHAs, keine Zwischenstände.

- [ ] **Step 3: Text im Chat vorlegen und Freigabe abwarten.** Ohne ausdrückliches „ja“ kein Push, kein `gh`.

- [ ] **Step 4: Push und PR (nur nach Freigabe)**

```bash
cd /d/Entwicklung/HASI/HAsmartirrigation
git push -u origin fix/backstop-grace
gh pr create --repo JustChr/HAsmartirrigation --base master --head Eifel-Joe:fix/backstop-grace \
  --title "Let the service watcher settle a normal run end: a finish grace with a per-zone latency margin" \
  --body-file /d/Entwicklung/HASI/pr139-work/pr-body.md
```

Erwartet: PR-URL. Danach `mcp__ccd_pr__get_status` für CI statt `gh` zu pollen.

- [ ] **Step 5: Kommentar auf #139 entwerfen, vorlegen, nach Freigabe posten**

Kurz: PR-Link, die zwei Abweichungen in je einem Satz, Default-Marge mit Datengrundlage, Zusage der
Nachmessung, und welcher der vier abtrennbaren Teile nach seiner Antwort drin ist bzw. gestrichen wurde.
Posten nur nach Freigabe:

```bash
cd /d/Entwicklung/HASI/HAsmartirrigation
gh issue comment 139 --repo JustChr/HAsmartirrigation --body-file /d/Entwicklung/HASI/pr139-work/comment-139.md
```

- [ ] **Step 6: Design-Historie archivieren (Regel P1; Push nur nach Freigabe)**

Spec und Plan liegen als Commits auf dem lokalen Branch `archive/design-history` (aus der
Planungssitzung). Zuerst prüfen, wo der Branch ausgecheckt ist — ein Branch kann nur in EINEM Worktree
stehen:

```bash
cd /d/Entwicklung/HASI/HAsmartirrigation
git worktree list | grep "archive/design-history"
git log --oneline -3 archive/design-history
git rev-list --count origin/archive/design-history..archive/design-history
```

- Listet `git worktree list` einen Worktree (z. B. aus dem Scratchpad der Planungssitzung): diesen als
  `WT` verwenden. Sonst `WT=/d/Entwicklung/HASI/pr139-work/archive-wt` und
  `git worktree add "$WT" archive/design-history`.
- Den Plan-Kopf in `"$WT"/docs/superpowers/plans/2026-09-15-backstop-grace.md` um die Zeile
  „Umsetzung abgeschlossen am <Datum>, PR #<Nummer>“ ergänzen und den Spec-Nachtrag
  „Umsetzung“ (Abweichungen vom Plan, gestrichene Tasks, Endzahlen) anhängen.

Stand am Ende der Planungssitzung: der Archiv-Worktree liegt unter `D:/Entwicklung/HASI/pr139-work/archive-wt`.
`WT` wird im selben Befehlsblock gesetzt, der ihn benutzt (Shell-Zustand überlebt keinen neuen Aufruf):

```bash
cd /d/Entwicklung/HASI/HAsmartirrigation
WT=$(git worktree list | awk '/\[archive\/design-history\]/{print $1}')
if [ -z "$WT" ]; then WT=/d/Entwicklung/HASI/pr139-work/archive-wt; git worktree add "$WT" archive/design-history; fi
echo "$WT"
git -C "$WT" add docs/superpowers/specs/2026-09-15-backstop-grace-design.md docs/superpowers/plans/2026-09-15-backstop-grace.md
git -C "$WT" commit -m "docs: record how the #139 finish backstop grace was carried out"
git -C "$WT" push origin archive/design-history
git -C /d/Entwicklung/HASI/HAsmartirrigation worktree remove "$WT"
git worktree list
```

Erwartet: Push übernimmt alle lokalen Archiv-Commits (Spec + Plan + Nachtrag), danach kein Archiv-Worktree mehr.

- [ ] **Step 7: Vorbestehende Befunde in `D:\Entwicklung\HASI\ToDo.md` prüfen** (in der Planungssitzung am 2026-09-16 bereits als Block „Befunde aus der Planung von #139“ eingetragen; nur ergänzen, falls die Umsetzung weitere findet)

1. `async_unload` bricht weder Backstop-Timer noch Durchfluss-Sampler ab (`__init__.py` ~2196-2294).
2. Fehlerbehandlung des Dispatch lässt Backstop und gespeicherten Datensatz stehen (`self_closing.py` ~640-647).
3. Nach Neustart mitten in der Bewässerung übernommener Batch-Lauf bekommt keinen Backstop (`batch.py` ~741-756).
4. Observed-Doppelgutschrift, wenn der Dispatch auf ein extern geöffnetes Ventil trifft (`observed_watering.py` ~146, ~157-172).
5. Veralteter Docstring `get_total_irrigation_duration` (`skip_conditions.py` ~410-415).
6. Unbenutzter Parameter `planned` in `_watch_start` (`run_watch.py` ~491-563).
7. Nach einem Neustart nimmt kein Pfad die Observed-Sperre für einen weiterlaufenden Service-Lauf neu
   (`_si_driven_until` lebt nur im Speicher; `async_resume_self_closing_runs` ruft `_note_si_valve`
   nicht, `_watch_observed_start` wird wegen gespeichertem `RUN_OBSERVED_START` nicht erneut betreten;
   Task 13, Step 5).

- [ ] **Step 8: Aufräumen und Übergabe**

```bash
cd /d/Entwicklung/HASI/HAsmartirrigation
git worktree list
git worktree remove --force /d/Entwicklung/HASI/pr139-work/dry-backend
git worktree remove --force /d/Entwicklung/HASI/pr139-work/dry-frontend
git worktree remove --force /d/Entwicklung/HASI/pr139-work/dry2
git branch -D dry/backstop-grace dry/backstop-grace-frontend dry2/backstop-grace
git branch --list "worktree-*" "tmp/*"
git worktree prune
git worktree list
```

Erwartet: nur Hauptbaum (und ggf. Archiv-Worktree bis Step 6) in `git worktree list`, keine
`worktree-*`- und keine `tmp/*`-Branches. `docs/SESSION-STAND.md` und Memory `hasi-backstop-has-no-grace`
fortschreiben.

---

### Task 15: Live-Test — zuerst HA-Test mit dem Sonoff-Emulator, dann Nachmessung auf HA-Prod

**Files:** keine Code-Änderung. Protokoll in `docs/SESSION-STAND.md` und auf #139.

Voraussetzungen und Freigaben:
- Eigene Freigabe des Users für jeden Schritt, der auf HA-Test oder HA-Prod schreibt (Zonenkonfiguration,
  Dienstaufruf, Update). HA-Neustart nur mit ausdrücklicher Freigabe (Memory `ha-no-auto-restart`).
- Vor jedem schreibenden MCP-Aufruf die Instanz nennen; Routing strikt per Präfix
  `mcp__HA-Test__` / `mcp__HA-Prod__` (Memory `verify-ha-system`).
- Bewässerungs-Hardware schalten wurde am 2026-09-11 vom Auto-Modus-Klassifikator blockiert — den
  Lauf-Auslöser ggf. vom User drücken lassen.

- [ ] **Step 1: Pre-Release-Branch bauen (User-Entscheidung 2026-09-15: Fork-Pre-Release über HACS)**

Präzedenz: Fork-Pre-Releases `v2026.09.02`/`v2026.09.05` — normale Kalender-Version, Titel mit
„(pre-release)“, Flag Pre-release. Basis ist `production` (inhaltlich upstream/master + Branding),
darauf der fertige `fix/backstop-grace`. `production` selbst wird NICHT angefasst.

Umfang (User-Entscheidungen 2026-09-15): `production` + `fix/backstop-grace`. Weil der Branch auf
`0b418644` (upstream v2026.09.16) steht, kommen #144 und #145 mit — beide sind upstream gemergt, der Fork
fährt damit exakt den Code des PR und keine Rückport-Variante. #146 kommt NICHT hinein; dessen Live-Test
(Plan `2026-09-13-rain-guard-run-date.md`, Task 12) folgt danach in einem eigenen Pre-Release.

> **Entschieden 2026-09-15 (User): #144/#145 kommen mit ins Pre-Release.** Hintergrund, warum die
> Vorabprüfung deren Dateien zulassen muss:
> `fix/backstop-grace` steht jetzt auf `0b418644` (upstream v2026.09.16) und enthält damit #144
> (`8efee4f9`) und #145 (`8dbc0223`). `origin/production` (`bf2b38b7`, v2026.09.17) enthält keinen der
> beiden (geprüft mit `git merge-base --is-ancestor`). Der Merge unten brächte sie mit, und die
> `diff --stat`-Prüfung zeigte dann zusätzlich deren Dateien (`git diff --name-only bf2b38b7 0b418644`
> ohne dist, außer Branding/Versionen: `const.py` (FORECAST_DAY_*-Block), `websockets.py`,
> `weathermodules/OpenMeteoClient.py`, `MetOfficeClient.py`, `OWMClient.py`, `PirateWeatherClient.py`).
> Ohne die Freigabe dieser Dateien in der Vorabprüfung unten hätte das STOPP gegriffen; die frühere
> Umfangs-Entscheidung „NUR `production` + #139“ wäre auf der neuen Basis nur mit einem Rückport erfüllbar
> gewesen und ist durch die obige Entscheidung ersetzt.

```bash
cd /d/Entwicklung/HASI/HAsmartirrigation
git fetch origin upstream
gh release list --repo Eifel-Joe/HAsmartirrigation --limit 3
git ls-remote --tags upstream "v2026.09.*"
git rev-list --left-right --count origin/production...fix/backstop-grace
git diff --stat origin/production fix/backstop-grace -- custom_components/irrigation_plus ':!custom_components/irrigation_plus/frontend/dist'
git checkout -b test/backstop-grace origin/production
git merge --no-ff fix/backstop-grace -m "merge: #139 finish backstop grace for the HA-Test pre-release"
git status --short
```

Versionsnummer: die nächste freie Fork-Kalendernummer nach dem neuesten Release (am 2026-09-15 wäre das
`v2026.09.18`); ist sie als Fork-Release schon vergeben, die nächste nehmen. Kollision mit einem
upstream-Tag gleichen Namens ist erlaubt, dann aber zwingend ZIP aus dem SHA (Memory
`hasi-production-on-upstream`, Tag-Kollisions-Falle). Vorabprüfung: `production` trägt #140/#141 als
Einzelcommits, `fix/backstop-grace` die Squash-Commits von upstream. Die `diff --stat` darf außer den
#139-Dateien, den Versions-/Branding-Dateien (`manifest.json`, `package.json`, `const.py` VERSION,
README, `brand/`) und den Dateien von #144/#145 (`const.py` `FORECAST_DAY_*`-Block, `websockets.py`
`websocket_get_weather_forecast`, `weathermodules/OpenMeteoClient.py`, `MetOfficeClient.py`, `OWMClient.py`,
`PirateWeatherClient.py`, `tests/test_weather_modules.py`, `tests/test_pirateweather_daily.py`,
`tests/test_websocket_get_weather_forecast.py`) nichts zeigen; zeigt sie weitere Dateien (z. B. `run_window.py`, `calcmodules/pyeto`),
ist `production` inhaltlich nicht mehr gleich upstream — STOPP und dem User zeigen. Merge-Konflikte in
den dist-Bundles (beide Seiten gebaut): `git checkout --theirs -- <bundle>`, sie werden unten ohnehin neu
gebaut. Konflikte in Dateien, die beide Seiten inhaltsgleich geändert haben (#140/#141), mit
`git diff` prüfen und nur dann übernehmen, wenn der Inhalt beider Seiten identisch ist. Jeder andere
Konflikt: STOPP und dem User zeigen.

- [ ] **Step 2: Versionen synchron setzen, bauen, prüfen, committen**

Alle DREI Dateien (Beispiel `v2026.09.18`):
- `custom_components/irrigation_plus/manifest.json`: `"version": "v2026.09.18"`
- `custom_components/irrigation_plus/frontend/package.json`: `"version": "2026.09.18"` (ohne `v`)
- `custom_components/irrigation_plus/const.py`: `VERSION = "v2026.09.18"`

```bash
cd /d/Entwicklung/HASI/HAsmartirrigation/custom_components/irrigation_plus/frontend
mkdir -p D:/Entwicklung/HASI/pr139-work/tmp D:/Entwicklung/HASI/pr139-work/npm-cache && export TEMP=D:/Entwicklung/HASI/pr139-work/tmp TMP=D:/Entwicklung/HASI/pr139-work/tmp TMPDIR=D:/Entwicklung/HASI/pr139-work/tmp npm_config_cache=D:/Entwicklung/HASI/pr139-work/npm-cache
npm ci && npm run build
cd /d/Entwicklung/HASI/HAsmartirrigation
uvx black --check custom_components/irrigation_plus/
uvx ruff check custom_components/irrigation_plus/
./.venv/Scripts/python.exe -m pytest tests/test_service_watch.py tests/test_finish_grace_helpers.py tests/test_i18n_completeness.py -p _local_socket_unblock -q
grep -c "https://github.com" custom_components/irrigation_plus/translations/en.json
grep -h '"version"\|^VERSION' custom_components/irrigation_plus/manifest.json custom_components/irrigation_plus/frontend/package.json custom_components/irrigation_plus/const.py
git diff --stat -- custom_components/irrigation_plus/frontend/dist
git add custom_components/irrigation_plus/manifest.json custom_components/irrigation_plus/frontend/package.json custom_components/irrigation_plus/const.py
git add -f custom_components/irrigation_plus/frontend/dist/irrigation-plus.js custom_components/irrigation_plus/frontend/dist/irrigation-plus-card-impl.js custom_components/irrigation_plus/frontend/dist/irrigation-plus-card.js
git commit -F - <<'EOF'
build: v2026.09.18 (pre-release) — #139 finish backstop grace, for HA-Test

Production plus the finish backstop grace, so the watcher path can be
checked against the valve emulator on the test instance before the PR
lands upstream. Not a production release.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
```

Erwartet: black/ruff sauber, Tests grün, `grep -c` = `0`, drei gleiche Versionen. Nur Bundles stagen, die
`git diff --stat` tatsächlich listet (die Liste oben ist die Obermenge).

- [ ] **Step 3: Push, Pre-Release und ZIP (Freigabe: nach außen)**

```bash
cd /d/Entwicklung/HASI/HAsmartirrigation
git push -u origin test/backstop-grace
SHA=$(git rev-parse HEAD)
git archive --format=zip -o /d/Entwicklung/HASI/pr139-work/irrigation_plus.zip "$SHA":custom_components/irrigation_plus
unzip -p /d/Entwicklung/HASI/pr139-work/irrigation_plus.zip run_watch.py | grep -c "def valve_window_seconds"
unzip -p /d/Entwicklung/HASI/pr139-work/irrigation_plus.zip manifest.json | grep version
gh release create v2026.09.18 --repo Eifel-Joe/HAsmartirrigation --prerelease --target "$SHA" \
  --title "v2026.09.18 (pre-release) — #139 finish backstop grace, for HA-Test" \
  --notes "Test build for the valve emulator on the test instance: production plus the finish backstop grace of JustChr/HAsmartirrigation#139. Not for production use."
gh release upload v2026.09.18 /d/Entwicklung/HASI/pr139-work/irrigation_plus.zip --repo Eifel-Joe/HAsmartirrigation
gh api repos/Eifel-Joe/HAsmartirrigation/releases/tags/v2026.09.18 --jq '.assets[].name'
curl -sIL https://github.com/Eifel-Joe/HAsmartirrigation/releases/download/v2026.09.18/irrigation_plus.zip | grep -m1 -E "^HTTP/.* 200"
git fetch origin --tags
git tag -f v2026.09.18 "$SHA"
```

Erwartet: `grep -c` = `1`, Manifest `v2026.09.18`, Asset `irrigation_plus.zip`, HTTP 200. `--target` braucht
den vollen SHA (Kurz-SHA gibt HTTP 422).

- [ ] **Step 4: Auf HA-Test installieren (Freigabe; Neustart nur mit ausdrücklicher Freigabe)**

Vorher lesend: installierte Version auf HA-Test (`mcp__HA-Test__ha_get_integration` für `irrigation_plus`
bzw. das HACS-Update-Entity). Dann über `mcp__HA-Test__ha_manage_hacs` die Repository-Information für
`Eifel-Joe/HAsmartirrigation` aktualisieren und gezielt Version `v2026.09.18` herunterladen (Pre-Releases
werden nur mit expliziter Version bzw. Beta-Anzeige angeboten). Danach HA-Test neu starten (Freigabe),
~1 min 502 vom MCP-Add-on abwarten, dann prüfen: Integration geladen, Version `v2026.09.18`, keine
`irrigation_plus`-Fehler in `mcp__HA-Test__ha_get_logs`.

- [ ] **Step 5: Emulator prüfen (nur lesend)**

`mcp__HA-Test__ha_get_state` für `input_boolean.sonoff_emu_valve`, `input_boolean.sonoff_emu_fault`,
`binary_sensor.sonoff_emu_flowing`, `script.sonoff_emu_run`. Erwartet: alle vorhanden, Ventil `off`,
Fehler `off` (Stand 2026-09-15 so gelesen).

- [ ] **Step 6: Testzone einrichten (schreibend auf HA-Test, Freigabe)**

Service-Zone: `run_service` = `script.sonoff_emu_run`, `duration_field` = `seconds`, Einheit Sekunden,
`confirm_entity` = `binary_sensor.sonoff_emu_flowing`, `latency_margin` 4 (Panel-Zeile muss unter
„Confirm entity“ erscheinen und ohne Confirm-Entität verschwinden — Sichtprüfung im Panel), Dauer 120 s.

- [ ] **Step 7: Ein Lauf (Freigabe; ggf. User löst aus)**

`irrigation_plus.run_zone` für die Testzone oder „Jetzt bewässern“ im Panel.

- [ ] **Step 8: Auswerten (nur lesend)**

- `mcp__HA-Test__ha_get_history` für `input_boolean.sonoff_emu_valve` und
  `binary_sensor.sonoff_emu_flowing` über den Lauf: Zeit an, Zeit aus → Fenster.
- `sensor.irrigation_plus_<zone>_last_irrigation`-Wechsel = Abschlusszeitpunkt.
- Letzter Verlaufseintrag der Zone (Diagnostics `data.store` Zone `run_log`): `result`, `planned_s`, `actual_s`.

Bestanden, wenn alle drei gelten:
1. `result` = `completed`;
2. `actual_s` = Fenster aus dem Recorder ±1 s (gerundet gespeichert);
3. Abschluss = Aus + 5 s ±0,5 s, also über den Watcher und nicht bei Start + 120 + 9 s.
Dazu keine Exception von `irrigation_plus` im Log (`mcp__HA-Test__ha_get_logs`).

Grenze (Spec): das Emulator-Ventil schließt ohne Latenz; eine Tuya-artige Latenz und eine Latenz über
der Marge werden hier nicht belegt.

- [ ] **Step 9: Optional Fehlerfall (Freigabe)**

`input_boolean.sonoff_emu_fault` vor dem Lauf an → Confirm bleibt aus → Lauf abgebrochen,
`valve_did_not_open`, kein Datensatz, keine Wartezeit. Danach Fehler-Schalter wieder aus.

- [ ] **Step 10: Ergebnis HA-Test festhalten und Test-Branch aufräumen**

Ergebnis (drei Kriterien mit den gemessenen Zahlen) in `docs/SESSION-STAND.md`. Das Pre-Release
`v2026.09.18` bleibt als Beleg stehen; HA-Test bleibt darauf bis zum nächsten regulären Fork-Release.
Den lokalen Branch erst löschen, wenn er über den Tag erhalten ist:

```bash
cd /d/Entwicklung/HASI/HAsmartirrigation
git checkout fix/backstop-grace
git tag --contains test/backstop-grace
git branch -D test/backstop-grace
```

Der Remote-Branch `origin/test/backstop-grace` wird nur nach Freigabe gelöscht
(`git push origin --delete test/backstop-grace`); der Tag hält den Commit.

- [ ] **Step 11: HA-Prod-Nachmessung nach Merge und Release**

Erst wenn der PR bei JustChr gemergt und ein Fork-Release nach Memory `hasi-production-on-upstream`
gebaut und nach Freigabe auf HA-Prod installiert und neu gestartet ist: die nächsten natürlichen Läufe von
Beet und Kirschlorbeer (Kirschbaum beim nächsten Lauf, nur Ventil-Timing verwertbar) mit denselben drei
Kriterien aus dem Recorder auswerten (`switch.wasser_beet_valve_l1`, `switch.wasser_vorne`,
`switch.wasser_hinten`, `sensor.irrigation_plus_*_last_irrigation`). Keine Läufe erzwingen (Lehrgeld
2026-09-11). Ergebnis als Kommentar auf #139 entwerfen, vorlegen, nach Freigabe posten.
