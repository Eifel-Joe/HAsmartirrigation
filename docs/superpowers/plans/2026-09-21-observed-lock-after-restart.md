# Observed-Sperre nach Neustart — Implementierungsplan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or
> superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Die drei Restart-Resume-Pfade nehmen das Observed-Unterdrückungsfenster mit der **Restlaufzeit**
neu, damit es nach einem Neustart dasselbe absolute Ende hat wie im Normalbetrieb.

**Architecture:** Drei Aufrufe von `_note_si_valve(zone_id, planned - elapsed)`, je neben dem dort schon
vorhandenen Backstop-/Watcher-Aufruf. Keine Signaturänderung, keine neue Funktion.

**Spec:** `docs/superpowers/specs/2026-09-21-observed-lock-after-restart-design.md`
**Issue:** `Eifel-Joe#23`
**Basis:** `fix/observed-lock-after-restart` von `upstream/master` = `965a4f9d`.
Vorbestand: **7 failed, 3191 passed, 9 skipped, 320 errors**
(`D:/Entwicklung/HASI/prA-work/baseline-965a4f9d.txt`, Namen in `baseline-names.txt`).

**Testbefehl:**

```bash
./.venv/Scripts/python.exe -m pytest tests -p _local_socket_unblock -q
```

---

## Dateien

| Datei | Rolle |
|---|---|
| `custom_components/irrigation_plus/self_closing.py` | **Ändern**, eine Zeile im Inline-Zweig von `async_resume_self_closing_runs` |
| `custom_components/irrigation_plus/opensprinkler.py` | **Ändern**, eine Zeile in `_os_resume_run` |
| `custom_components/irrigation_plus/batch.py` | **Ändern**, eine Zeile in `_batch_resume_run` |
| `tests/test_self_closing.py` | **Ergänzen** um zwei Tests |
| `tests/test_opensprinkler.py` | **Ergänzen** um einen Test |
| `tests/test_batch.py` | **Ergänzen** um einen Test |

⚠️ **Nur der Service-Pfad kann einen negativen Rest erzeugen.** Sein Abschluss-Test ist
`elapsed >= planned + grace`, zwischen `planned` und `planned + grace` ist `planned − elapsed` also negativ.
OpenSprinkler (`elapsed >= planned`) und Batch (`_sc_run_elapsed(run) >= planned`) kehren vorher zurück,
dort ist der Rest immer positiv.

---

## Task 1: Service-Pfad

**Files:**
- Modify: `custom_components/irrigation_plus/self_closing.py` (Zeile 1087, im Inline-Zweig)
- Test: `tests/test_self_closing.py`

- [ ] **Step 1: Die zwei Tests schreiben**

Hinter `test_resume_finalises_overdue_and_reschedules_partial` (endet Zeile 494):

```python
async def test_resume_retakes_the_observed_suppression_window():
    """After a restart the marker has to end where a normal dispatch would have
    put it: start + planned + 30. The resume knows `elapsed`, so it re-takes with
    the REMAINDER — handing it the neighbouring cleanup's expression would
    overshoot by the finish grace."""
    c = _coord()
    c._si_driven_until = {}
    c.hass.loop.time = Mock(return_value=1000.0)
    c._watch_start = AsyncMock()  # a confirmed record re-adopts its watcher
    run = {
        const.RUN_ZONE_ID: 2,
        const.RUN_STARTED: "2026-06-30T08:00:00+00:00",
        const.RUN_PLANNED_SECONDS: 600.0,
        const.RUN_MODE: const.WATERING_MODE_SERVICE,
        const.RUN_WATCH_ENTITY: "binary_sensor.confirm",
        const.RUN_LATENCY_MARGIN: 4,  # grace = settle 5 + 4 = 9
    }
    c.store.async_get_config = AsyncMock(
        return_value={const.CONF_ACTIVE_VALVE_RUNS: [run]}
    )
    c._sc_elapsed = Mock(side_effect=[100.0, 100.0])

    await c.async_resume_self_closing_runs()

    # 600 - 100 remaining, plus the marker's own 30. NOT 609 - 100 (that would be
    # the cleanup's expression) and NOT 630 - 100 (that counts the margin twice).
    assert c._si_driven_until[2] == pytest.approx(1000.0 + 500.0 + 30.0)
    c._sc_schedule_cleanup.assert_called_once_with(2, 509.0)


async def test_resume_inside_the_grace_keeps_a_window_shorter_than_the_margin():
    """A run resumed past its plan but still inside its finish grace has a
    NEGATIVE remainder, and it must be passed raw. Flooring it at 0 would stretch
    the window past what a normal dispatch gives and swallow a genuine external
    run afterwards — the mirror of what the two close-side re-notes prevent."""
    c = _coord()
    c._si_driven_until = {}
    c.hass.loop.time = Mock(return_value=1000.0)
    c._watch_start = AsyncMock()
    run = {
        const.RUN_ZONE_ID: 3,
        const.RUN_STARTED: "2026-06-30T08:00:00+00:00",
        const.RUN_PLANNED_SECONDS: 600.0,
        const.RUN_MODE: const.WATERING_MODE_SERVICE,
        const.RUN_WATCH_ENTITY: "binary_sensor.confirm",
        const.RUN_LATENCY_MARGIN: 4,
    }
    c.store.async_get_config = AsyncMock(
        return_value={const.CONF_ACTIVE_VALVE_RUNS: [run]}
    )
    # 605 s in: past the plan, still inside the 9 s grace, so not finalised.
    c._sc_elapsed = Mock(side_effect=[605.0])

    await c.async_resume_self_closing_runs()

    # remainder -5, so the window is 25 s, not the full 30.
    assert c._si_driven_until[3] == pytest.approx(1000.0 - 5.0 + 30.0)
```

`pytest`, `AsyncMock` und `Mock` sind in der Datei bereits importiert; `pytest` **prüfen** und bei Bedarf
ergänzen.

- [ ] **Step 2: RED sehen**

```bash
./.venv/Scripts/python.exe -m pytest tests/test_self_closing.py -p _local_socket_unblock -q -k "retakes_the_observed or inside_the_grace_keeps"
```

Erwartung: **2 failed**, beide mit `KeyError: 2` bzw. `KeyError: 3` — der Marker wird gar nicht gesetzt.

- [ ] **Step 3: Den Nachzug einsetzen**

In `custom_components/irrigation_plus/self_closing.py`, unmittelbar vor
`self._sc_schedule_cleanup(zone_id, planned + grace - elapsed)`:

```python
                # The marker lived in memory only, so the restart dropped it and
                # nothing else re-takes it: _watch_observed_start is gated on a
                # record with NO observed start, which a resumed run has. Without
                # this the observer is only held off to planned + grace, where a
                # normal dispatch holds it to planned + 30, and an off -> on in
                # that difference credits the bucket for water the run already
                # accounts for. The REMAINDER, not the cleanup's expression: that
                # one carries the grace and would overshoot by it. Passed raw —
                # a run resumed inside its grace has a negative remainder, and
                # flooring it at 0 would over-extend the window instead.
                self._note_si_valve(zone_id, planned - elapsed)
                self._sc_schedule_cleanup(zone_id, planned + grace - elapsed)
```

- [ ] **Step 4: GREEN sehen**

```bash
./.venv/Scripts/python.exe -m pytest tests/test_self_closing.py -p _local_socket_unblock -q
```

Erwartung: alle grün, insbesondere `test_resume_finalises_overdue_and_reschedules_partial` unverändert.

- [ ] **Step 5: Commit**

```bash
git add custom_components/irrigation_plus/self_closing.py tests/test_self_closing.py
git commit -F - <<'EOF'
fix(observed): re-take the suppression window when a service run resumes

The marker lives in memory, so a restart drops it, and no resume path re-takes
it. A still-running service run is then held off only to planned + grace where a
normal dispatch holds to planned + 30, and an off -> on inside that difference
credits the bucket for water the run already accounts for.

Re-take with the remainder so the window ends where a normal dispatch would have
put it.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
```

---

## Task 2: OpenSprinkler

**Files:**
- Modify: `custom_components/irrigation_plus/opensprinkler.py` (`_os_resume_run`)
- Test: `tests/test_opensprinkler.py`

- [ ] **Step 1: Den Test schreiben**

Vorlage ist `test_restart_mid_run_arms_from_after_the_master_settle` (`tests/test_opensprinkler.py:1340`,
Körper bis 1371) — **erst lesen**, die Datei nutzt `freezegun` statt gestubter `_sc_elapsed`. Den neuen Test
danach anhängen, mit einem Datensatz, der `RUN_OBSERVED_START` trägt und noch innerhalb von `planned` liegt,
und der Zusicherung `_si_driven_until[zid] == loop.time() + (planned - elapsed) + 30`.

⚠️ Prüfen, ob die dortige Vorrichtung `_si_driven_until` setzt und ob `hass.loop.time` unter `freeze_time`
eine echte Zahl liefert — sonst ist `_note_si_valve` durch seinen `getattr`-Schutz ein No-op und der Test
grün aus dem falschen Grund.

- [ ] **Step 2: RED sehen** — Marker fehlt.

- [ ] **Step 3: Den Nachzug einsetzen**

In `_os_resume_run`, im Zweig `observed_start is not None`, unmittelbar vor
`self._sc_schedule_cleanup(zone_id, planned - elapsed)`:

```python
            # Same reason as the service path: the marker did not survive, and
            # _watch_observed_start will not re-take it for a record that already
            # carries an observed start. A station's grace is 0, so the gap here
            # is the full 30 s rather than 21.
            self._note_si_valve(zone_id, planned - elapsed)
```

- [ ] **Step 4: GREEN sehen**, ganze Datei.

- [ ] **Step 5: Commit** (`fix(observed): re-take the suppression window when a station run resumes`)

---

## Task 3: Batch

**Files:**
- Modify: `custom_components/irrigation_plus/batch.py` (`_batch_resume_run`)
- Test: `tests/test_batch.py`

⚠️ **Hier gibt es keine lokale Variable `elapsed`** — der Zweig prüft `self._sc_run_elapsed(run)` inline.
Der Wert muss einmal in eine lokale Variable gelesen werden, damit Prüfung und Nachzug denselben nehmen.

- [ ] **Step 1: Den Test schreiben**, Vorlage aus `tests/test_batch.py` (Resume-Tests dort erst lesen).
  ⚠️ `tests/test_batch.py:53` setzt `c._note_si_valve = Mock()` in der Vorrichtung — für diesen Test muss
  das **echte** `_note_si_valve` laufen, sonst prüft der Test die Attrappe.

- [ ] **Step 2: RED sehen.**

- [ ] **Step 3: Den Nachzug einsetzen**

```python
        elapsed = self._sc_run_elapsed(run)
        if elapsed >= planned:
            await self._sc_finish_run(zone_id)
            return

        # Same reason as the service and station paths; a batch record's grace is
        # 0, so the gap is the full 30 s.
        self._note_si_valve(zone_id, planned - elapsed)
        await self._watch_start(zone_id, watch_entity, planned, accepted=True)
```

- [ ] **Step 4: GREEN sehen**, ganze Datei.

- [ ] **Step 5: Commit** (`fix(observed): re-take the suppression window when a batch run resumes`)

---

## Task 4: Schluss

- [ ] **Step 1: Lint**

```bash
uvx black custom_components/irrigation_plus/
uvx ruff check custom_components/irrigation_plus/
```

- [ ] **Step 2: Volle Suite gegen den Vorbestand**

```bash
./.venv/Scripts/python.exe -m pytest tests -p _local_socket_unblock -q > /d/Entwicklung/HASI/pr23-work/after.txt 2>&1
tail -1 /d/Entwicklung/HASI/pr23-work/after.txt
grep -E "^(FAILED|ERROR) tests/" /d/Entwicklung/HASI/pr23-work/after.txt | sort > /d/Entwicklung/HASI/pr23-work/after-names.txt
diff /d/Entwicklung/HASI/prA-work/baseline-names.txt /d/Entwicklung/HASI/pr23-work/after-names.txt && echo IDENTISCH
```

Erwartung: `3191 + 4 = 3195 passed` und `IDENTISCH`.

- [ ] **Step 3: Das Messskript aus dem Issue erneut fahren** (Spec, Abschnitt 7). Erwartung: der Beobachter
  stellt sich **nicht** mehr scharf, die Schließen-Flanke plant keine Gutschrift.

- [ ] **Step 4: Mutationsproben**

| # | Probe | Muss sterben an |
|---|---|---|
| M1 | Nachzug im Service-Pfad löschen | beide Service-Tests |
| M2 | `planned - elapsed` → `planned + grace - elapsed` | `..._retakes_the_observed_suppression_window` |
| M3 | `planned - elapsed` → `max(0.0, planned - elapsed)` | `..._inside_the_grace_keeps_a_window_shorter_than_the_margin` |
| M4 | Nachzug in `_os_resume_run` löschen | der OpenSprinkler-Test |
| M5 | Nachzug in `_batch_resume_run` löschen | der Batch-Test |

- [ ] **Step 5: Design-Historie** auf `archive/design-history` (Regel P1), **vor** dem PR und außerhalb des
  PR-Diffs. `git diff --stat upstream/master..HEAD` muss **sechs** Dateien zeigen, kein `docs/`.

- [ ] **Step 6: PR-Body entwerfen und im Chat zur Freigabe vorlegen.** Push und `gh pr create` erst danach.

---

## Selbstprüfung des Plans

**Spec-Abdeckung.** Anforderung 1 → Task 1–3 mit der Restlaufzeit. Anforderung 2 → drei Tasks. Anforderung 3
(nicht länger als normal) → T1 prüft den exakten Wert, M2 und M3 sind die Gegenproben. Anforderung 4 →
Task 4 Step 2 mit Namensvergleich. Spec-Abschnitt 5 (nicht dazu) → keine Änderung an `_watch_start` oder den
wartenden Zweigen.

**Platzhalter.** Zwei bewusst offene Stellen: die Testkörper für OpenSprinkler und Batch stehen nicht
ausformuliert da, weil beide Dateien andere Zeitsteuerung nutzen (freezegun statt gestubtem `_sc_elapsed`)
und die Vorlage erst gelesen werden muss. Beide Tasks sagen das ausdrücklich und nennen die Fundstelle.

**Namensgleichheit.** `_note_si_valve`, `_si_driven_until`, `_sc_elapsed`, `_sc_run_elapsed`,
`_sc_schedule_cleanup`, `planned`, `elapsed`, `grace` — in allen Tasks gleich geschrieben.

---

## Umsetzungsnachtrag (2026-09-21)

Branch `fix/observed-lock-after-restart`, vier Commits auf `upstream/master` = `965a4f9d`:
`0309985f` Service · `c2db72ef` OpenSprinkler · `cdbe4633` Batch · `3deec545` Ende-zu-Ende-Pin.
PR-Diff **sechs Dateien**, +232/−1.

### Was gegenüber dem Plan anders lief

**Ein fünfter Test kam dazu.** Der Plan sah vier vor (drei Werte + Floor-Pin). Beim Ausführen zeigte sich,
dass das **Messskript aus dem Issue als Nachmessung untauglich** ist: es baut den Zustand von Hand und ruft
den Resume-Pfad nie, meldet also auch gegen den gefixten Stand „weiter offen". Kein Widerspruch — es misst
die Reaktion des Beobachters auf einen leeren Marker, und die bleibt richtig; der Fix verhindert, dass
dieser Zustand nach einem Neustart überhaupt **entsteht**. Als tragendes Kriterium deshalb
`test_after_a_resume_the_observer_stays_silent_in_the_old_gap`: Resume fahren, dann die Entität in der
Lücke einschalten, prüfen dass der Beobachter stumm bleibt. Spec, Abschnitt 7 entsprechend korrigiert.

**Der erste RED-Versuch für diesen Test war wertlos.** `git stash -- <datei>` bewirkt nichts, wenn der Fix
bereits **committet** ist; der Test lief grün und wäre beinahe als Beleg durchgegangen. Erst das echte
Entfernen der Zeile zeigte `assert 2 not in {2: datetime(...)}`.

**T5 aus dem Plan entfiel.** „Pin gegen die Überdehnung" ist keine eigene Zusicherung — T1 prüft den
exakten Wert und schließt `planned + grace − elapsed` damit bereits aus. Mutationsprobe M2 belegt das.

### Belege

- **RED gesehen** für alle fünf Tests, jeweils mit der vorhergesagten Meldung (`KeyError` für die
  Wert-Tests, `assert 2 not in {...}` für den Ende-zu-Ende-Test).
- **Volle Suite:** Vorbestand 7 / **3191** / 320 → Endstand 7 / **3196** / 320, FAILED-/ERROR-Namen
  `diff`-identisch (`pr23-work/final-names.txt`).
- **Lint:** `uvx black --check` 68 Dateien unverändert, `uvx ruff check` All checks passed.
- **Mutationsproben 5 / 5 gefangen / 0 überlebt** — M1 von drei Tests, M2 von zweien, M3 nur vom Floor-Pin,
  M4 und M5 je von ihrem Pfad-Test.
- **Nachbardateien** gegen den Vorbestand geprüft: keine neuen Fehler.

### Falle für die Zukunft

Die npm-Cache-Umleitung `npm_config_cache=D:\…` wird unter MSYS mit zerhackten Backslashes als
**relativer** Pfad gelesen — es landeten 33 MB unter `custom_components/irrigation_plus/frontend/
EntwicklungHASIprA-npm-cache/`. Untracked, also nie committet, aber ein `git add .` hätte es eingesammelt.
Entfernt; künftig den Cache-Pfad mit Vorwärtsschrägstrichen setzen.
