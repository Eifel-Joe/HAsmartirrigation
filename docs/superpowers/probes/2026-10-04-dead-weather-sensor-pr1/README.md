# Probelauf Plan PR 1, Revision 2 — stummer Wettersensor (2026-10-04)

Prüft den an JustChrs Antwort angepassten Plan
`docs/superpowers/plans/2026-10-03-dead-weather-sensor-common.md` (Revision 2) gegen `upstream/master` = `e9c79ec4`.

## Weg

1. Wegwerf-Worktree auf `e9c79ec4`, darauf `../2026-10-03-dead-weather-sensor-probe.patch` (der getestete Stand von
   Revision 1) — passte sauber.
2. `probe_rev2.py <worktree>`: die Revision-2-Änderungen (Konstanten-Kommentar, Modul-Docstring, Log-Warnung,
   Hinweistext in 8 Sprachen, Doku-Abschnitt). Jeder Anker passte genau einmal; das Skript prüft zusätzlich, dass die
   Panel-Beschriftung der Quelle „statisch“ je Sprache im Text steht.
3. Neue Datei `tests/test_sensor_liveness_repair.py` (JustChrs drei Hinweis-Tests), dann `black` auf die vier
   Liveness-Testdateien.
4. Baseline in einem zweiten, sauberen Worktree auf `e9c79ec4` gemessen.
5. `probe_mutate2.py <worktree>`: 20 Mutationen, jede gegen alle vier Liveness-Testdateien.
6. `check_plan_blocks.py`: jeder Python-/JSON-/Markdown-Block des Plans gegen den getesteten Stand.
7. Endstand als `probe-2026-10-04.patch` (19 Dateien, +1769/−5); `git apply --check` auf sauberem `e9c79ec4` passt.

## Ergebnis

- 75 neue Tests grün (40 rein, 6 Store, 26 Koordinator, 3 Hinweis-Tests gegen echte Issue-Registry und echten Store).
- black + ruff sauber auf `custom_components/irrigation_plus/`; die vier Testdateien black-sauber; i18n-Tests 67 grün.
- Volle Suite (`TZ=UTC`): 7 failed / 3693 passed / 9 skipped / 415 errors gegen die Baseline 7 / 3618 / 9 / 415;
  die 422 FAILED/ERROR-Namen identisch (`names-baseline-1004.txt` = `names-probe-1004.txt`), 3618 + 75 = 3693. Die
  Baseline ist identisch mit der von `issue9-work` auf demselben Commit.
- 20/20 Mutationen getötet, jeder Lauf mit gesammelten Tests (`mutate-1004.txt`). M17–M20 (Erholung, Neustart,
  Löschen, Rückladen der Liste) fallen auf JustChrs Hinweis-Tests.
- Plan-Blöcke: 46 wörtlich im getesteten Stand, 2 Ersetzungsvorlagen nur in der Basis, 5 inkrementelle Blöcke
  abschnittsweise vollständig (einzige Abweichung: ein Einzelimport, den der Endstand in eine Sammel-Importliste zieht).

## Befund nebenbei

Die MQTT-Integration von HA-Test hängt am Broker auf dem HA-Prod-Host. Deshalb läuft der Live-Test (Plan, Task 15) mit
YAML-MQTT-Sensoren unter eigenem Topic-Präfix und ohne Discovery; vom User am 2026-10-04 so freigegeben (Variante 1).
