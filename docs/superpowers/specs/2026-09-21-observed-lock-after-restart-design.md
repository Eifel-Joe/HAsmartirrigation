# Observed-Sperre nach Neustart: der Resume-Pfad nimmt den Marker nicht neu

Datum: 2026-09-21 · Issue **`Eifel-Joe#23`** („Three self-closing restart resume paths skip the
observed-entity lock fix", früher ToDo-Punkt ➀)
· Basis `upstream/master` = `965a4f9d` · Arbeitsbranch `fix/observed-lock-after-restart`
· Vorbestand der Suite auf dieser Basis: **7 failed, 3191 passed, 9 skipped, 320 errors**
(`D:/Entwicklung/HASI/prA-work/baseline-965a4f9d.txt`, Namen in `baseline-names.txt` — dieselbe Basis wie
`Eifel-Joe#1`)

**Zeilenangaben** gelten für `965a4f9d`.

**Quellen.** Messung vom 21.09. im
[Kommentar auf `Eifel-Joe#23`](https://github.com/Eifel-Joe/HAsmartirrigation/issues/23#issuecomment-5762950614).
Kartierung der drei Resume-Pfade: Workflow `wf_4d03229e-c51` (4 Leser + 4 Gegenprüfer, 63 Urteile — 50
bestätigt, 13 beanstandet, davon 11 Zeilenversatz und 2 falsche Testfundstellen; **keine gekippte
Sachaussage**). Die zwei tragenden Behauptungen habe ich selbst am Code nachgelesen: die Einsetzstelle in
`self_closing.py` und die Torbedingung in `run_watch.py:601` / `:700`.

---

## 1. Problem

Die Observed-Sperre hat zwei Mechanismen: den **In-Memory-Marker** `_si_driven_until[zone]`, den
`_note_si_valve` (`irrigation.py:115-131`) bei jedem Dispatch auf `now + run_seconds + 30` setzt, und
`zone_run_in_flight` (`run_state.py`), das für einen Service-Lauf den **persistierten** Datensatz liest und
bis `planned + run_finish_grace_seconds(run)` wahr ist.

Ein Neustart leert `_si_driven_until` (`__init__.py:678`), und **kein Resume-Pfad ruft `_note_si_valve`**.
Ein weiterlaufender Lauf ist danach nur noch bis `planned + grace` geschützt statt bis `planned + 30`.

**Gemessen am Code** (nicht geschätzt): Restdifferenz `30 − grace` = **+21 s** bei Vorgabewerten,
+25 s bei Marge 0, **+30 s** für einen write-only-Datensatz, 0 s bei Marge 25, **−5 s** bei Marge 30.
Erreichbarkeit reproduziert: Datensatz `planned + 10 s` alt → `zone_run_in_flight` False, beide Marker
leer, Beobachter stellt sich scharf, Schließen-Flanke plant die Gutschrift.

### 1.1 Batch und OpenSprinkler trifft es härter, nicht schwächer

Ihre Policies setzen `settles_on_valve_window` nicht, ihre Grace ist also **0**: `zone_run_in_flight` endet
exakt bei `observed_start + planned`, **volle 30 s** zu früh.

Und sie heilen sich **nicht** von selbst. `_watch_observed_start` (`run_watch.py:798`) nimmt den Marker für
warteschlangen-gebundene Läufe neu — aber **beide** Aufrufstellen sind darauf gegated, dass noch **kein**
`RUN_OBSERVED_START` gespeichert ist (`run_watch.py:601` `not run.get(const.RUN_OBSERVED_START)` und
`:700` `if observed_start is None`). Ein wiederaufgenommener Lauf, der vor dem Neustart schon wässerte,
trägt den Stempel bereits — das Tor sperrt ihn also aus. Der Nachzug kommt nie.

---

## 2. Anforderungen

1. Nach einem Neustart muss das Unterdrückungsfenster eines weiterlaufenden Laufs **demselben absoluten
   Ende** entsprechen, das der Normalbetrieb gesetzt hätte.
2. Alle drei Resume-Pfade, nicht nur der Service-Pfad.
3. Das Fenster darf **nicht länger** werden als im Normalbetrieb (siehe Abschnitt 4.2).
4. Kein vorhandener Test darf rot werden; insbesondere nicht die Pins der beiden
   `_note_si_valve(zone_id, 0)`-Verkürzungen.

---

## 3. Optionen

### Option 1 — `_watch_start` als einziger Fixpunkt (VERWORFEN)

Alle drei Pfade adoptieren den Watcher über `_watch_start` (`run_watch.py:579`), direkt oder über den
1:1-Wrapper `_os_start_watch`. Verlockend als Einzelstelle.

Verworfen, weil die Signatur nur `planned` kennt, **nicht `elapsed`** — die Restlaufzeit ließe sich dort
nicht bilden, ohne sie zusätzlich durchzureichen. Und `_watch_start` läuft auch auf dem **Normalpfad**, wo
der Marker bereits korrekt steht; ein Nachzug dort setzte ihn ein zweites Mal.

### Option 2 — an den drei Resume-Stellen (GEWÄHLT)

`self._note_si_valve(zone_id, planned - elapsed)` neben dem jeweils schon vorhandenen
`_sc_schedule_cleanup`-Aufruf. Die Werte liegen dort bereits im Zugriff, und jeder Pfad bekommt die für ihn
richtige Restlaufzeit.

---

## 4. Entscheidung

**Option 2**, an drei Stellen:

| Pfad | Stelle | Zweig |
|---|---|---|
| Service / self-closing | `self_closing.py:1087` | neben `_sc_schedule_cleanup(zone_id, planned + grace - elapsed)` |
| OpenSprinkler | `_os_resume_run`, `opensprinkler.py` | Zweig „`observed_start` gesetzt, läuft noch" |
| Batch | `_batch_resume_run`, `batch.py` | der entsprechende „wässert bereits"-Zweig |

### 4.1 Das Argument ist `planned - elapsed`, roh

`_note_si_valve` addiert die 30 selbst. Das Normalbetriebs-Fenster endet absolut bei
`started + planned + 30`; beim Resume gilt `now = started + elapsed`, also löst
`now + x + 30 = started + planned + 30` nach **`x = planned − elapsed`**.

Die beiden naheliegenden Fehlgriffe:
- den Ausdruck der Nachbarzeile nehmen (`planned + grace − elapsed`) → **überschießt um die Grace**;
- `planned + 30 − elapsed` → **zählt die Marge doppelt**.

### 4.2 Kein Floor bei 0 — und das ist die eigentliche Falle

Die Stelle wird nur erreicht, wenn `elapsed < planned + grace`; der Wert fällt also nie unter `−grace`.
Ein `max(0, …)` überdehnte das Fenster um bis zu 35 s und brächte **genau den Spiegelfehler zurück**,
gegen den die beiden `_note_si_valve(zone_id, 0)`-Verkürzungen (`irrigation.py:1523` und `:1702`)
geschrieben wurden: ein zu lang unterdrückter Schwanz verschluckt einen echten externen Lauf.

Das Risiko liegt asymmetrisch beim Übertreiben: der Marker hat **genau einen Leser**
(`observed_watering.py:138-140`), und nur an der **Öffnen**-Flanke. Ein zu langes Fenster verliert deshalb
den **ganzen** externen Lauf, nicht einen Teil — die Schließen-Flanke steigt bei `started is None` aus.
Ein Nachzug mit dem vollen `planned` würde nach einem Neustart eine Minute vor Ende eines 30-Minuten-Laufs
noch ~29 Minuten über das Schließen hinaus unterdrücken.

---

## 5. Ausdrücklich NICHT Teil dieser Arbeit

- **Die wartenden Zweige** von Batch und OpenSprinkler (kein `RUN_OBSERVED_START`). Sie heilen sich selbst:
  dort greift genau das Tor, das den wiederaufgenommenen Lauf aussperrt — beginnt das Wasser später, ruft
  `_watch_observed_start` den Nachzug mit `planned`.
- **`_watch_start` umbauen** (Abschnitt 3, Option 1).
- **Den Marker je löschbar machen.** Er läuft nur ab, wird nie geleert. Das ist bestehendes Verhalten und
  für diesen Fix ohne Belang, solange das Fenster nicht überdehnt wird.
- **Frontend, `dist`, i18n** — reiner Python-Fix ohne neue Zeichenkette.

---

## 6. Tests

| # | Datei | Was gepinnt wird | Heute |
|---|---|---|---|
| **T1** | `tests/test_self_closing.py` | Resume eines laufenden Service-Laufs setzt `_si_driven_until` auf `loop.time() + (planned − elapsed) + 30` | **RED**: Marker bleibt leer |
| **T2** | `tests/test_opensprinkler.py` | dasselbe für einen wiederaufgenommenen Stationslauf mit `RUN_OBSERVED_START` | **RED** |
| **T3** | `tests/test_batch.py` | dasselbe für einen wiederaufgenommenen Batch-Lauf, der bereits wässert | **RED** |
| **T4** | `tests/test_self_closing.py` | **Pin gegen den Floor:** ein innerhalb der Grace überfälliger Lauf bekommt ein Fenster **kleiner** als 30 s — beweist, dass der negative Rest roh durchgeht | **RED** |
| **T5** | `tests/test_self_closing.py` | **Pin gegen die Überdehnung:** der Nachzug entspricht dem Normalbetrieb, nicht `planned + grace` | **RED** |

Vorlage steht: `test_resume_finalises_overdue_and_reschedules_partial`
(`tests/test_self_closing.py:469-494`) baut den Datensatz, stubt `_sc_elapsed` mit einer festen Wertefolge
(zweiter Wert = Neulesung nach `async_master_acquire`) und prüft `_sc_schedule_cleanup`.
⚠️ Die Vorrichtung `_coord()` setzt **weder `_si_driven_until` noch eine echte Zahl für `hass.loop.time`** —
ohne beides ist `_note_si_valve` durch seinen `getattr`-Schutz ein No-op und der Test grün aus dem falschen
Grund.

**Schwester-Pfad-Prüfung:** die drei Resume-Zweige sind die Schwester-Pfade zueinander; alle drei gehören
in denselben Commit. `_watch_observed_start` bleibt unangetastet (Abschnitt 5).

**Testbefehl:** `./.venv/Scripts/python.exe -m pytest tests -p _local_socket_unblock -q`

---

## 7. Ende-zu-Ende-Kriterium

**Automatisiert:** T1–T5 fallen vorher und sind danach grün, bei unverändertem Vorbestand
(FAILED-/ERROR-Namen `diff`-identisch zu `baseline-names.txt`).

**⚠️ Korrektur (21.09., beim Ausführen bemerkt): das Messskript aus dem Issue-Kommentar taugt als
Nachmessung NICHT.** Es baut den Koordinatorzustand von Hand (`_si_driven_until = {}`) und ruft den
Resume-Pfad **nie** — es kann den nachgezogenen Marker also gar nicht sehen und meldet auch gegen den
gefixten Stand „weiter offen". Das ist kein Widerspruch: es misst die Reaktion des Beobachters auf einen
leeren Marker, und die ist unverändert richtig. Was der Fix ändert, ist, dass dieser Zustand nach einem
Neustart nicht mehr entsteht.

**Das tragende Kriterium ist stattdessen ein Ende-zu-Ende-Test**
(`test_after_a_resume_the_observer_stays_silent_in_the_old_gap`): den Resume wirklich fahren, dann die
beobachtete Entität in der Lücke einschalten — nach `planned + grace`, vor `planned + Marge` — und prüfen,
dass der Beobachter sich **nicht** scharf stellt. Ohne den Nachzug fällt er mit
`assert 2 not in {2: datetime(...)}`.

**Live:** nicht vorgesehen. Ein Feldnachweis bräuchte einen Neustart mitten im Lauf und ein `off → on` in
einem 21-Sekunden-Fenster; der Aufwand steht nicht im Verhältnis, und das Kriterium ist code-seitig
vollständig prüfbar. Falls JustChr einen Feldbeleg verlangt, ist das ein eigener Schritt.
