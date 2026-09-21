# Observed-Doppelgutschrift — Implementierungsplan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or
> superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ein SI-Dispatch auf ein bereits extern offenes Ventil darf die Observed-Gutschrift für dieses
Fenster nicht stehen lassen — sonst bucht die spätere Schließen-Flanke das Wasser des SI-Laufs ein zweites Mal.

**Architecture:** Eine einzige Änderung in `IrrigationRunnerMixin._note_si_valve`
(`custom_components/irrigation_plus/irrigation.py:115-131`), die von allen acht Dispatch-Pfaden durchlaufen
wird: neben dem bestehenden Unterdrückungsfenster wird der Marker `_observed_on_since[zone]` verworfen und
`_observed_cancel_meter(zone)` gerufen. Keine Änderung an der Schließen-Flanke (siehe Spec, Option 1),
kein Neu-Scharfstellen am Laufende (Option 3), kein Verteiler-Code.

**Tech Stack:** Python 3.12, pytest + pytest-asyncio, Home-Assistant-Custom-Component. Kein Frontend, kein
`dist`, keine i18n.

**Spec:** `docs/superpowers/specs/2026-09-21-observed-double-credit-design.md`

**Basis:** Branch `fix/observed-credit-si-takeover` von `upstream/master` = `965a4f9d`.
Vorbestand der Suite auf dieser Basis: **7 failed, 3191 passed, 9 skipped, 320 errors**
(`D:/Entwicklung/HASI/prA-work/baseline-965a4f9d.txt`; die 327 FAILED-/ERROR-Namen sortiert in
`D:/Entwicklung/HASI/prA-work/baseline-names.txt`).

**Testbefehl (kanonisch, immer dieser):**

```bash
./.venv/Scripts/python.exe -m pytest tests -p _local_socket_unblock -q
```

---

## Dateien

| Datei | Rolle |
|---|---|
| `custom_components/irrigation_plus/irrigation.py` | **Ändern**, nur `_note_si_valve` (Zeilen 115-131). Einzige Produktivcode-Änderung. |
| `tests/test_experimental_features.py` | **Ergänzen** um vier Tests, ans Ende des Abschnitts „Observed watering" (hinter `test_observed_long_run_flap_stays_suppressed`, Zeile 308-325). Vorrichtung `_observer_coordinator` (Zeile 201-231) und `_event` (Zeile 234-244) bestehen bereits. |
| `tests/test_observed_watering.py` | **Ergänzen** um einen Test, hinter `test_reopen_cancels_prior_sampler` (Zeile 476-491). Vorrichtung `_sampler_coord` (Zeile 166-179) und `_state_event` (Zeile 258-264) bestehen bereits. |

Keine neuen Dateien. Keine Änderung an `observed_watering.py` — der dortige Schließen-Zweig hat den Fall
`started is None` bereits (`:163-166`), und der Fix führt ihn nur herbei.

---

## Task 1: Den Marker beim Anspruch verwerfen

**Files:**
- Modify: `custom_components/irrigation_plus/irrigation.py:115-131`
- Test: `tests/test_experimental_features.py` (ergänzen hinter Zeile 325)

- [x] **Step 1: Die vier Tests schreiben**

Ans Ende des Abschnitts „Observed watering" in `tests/test_experimental_features.py`, direkt hinter
`test_observed_long_run_flap_stays_suppressed` (endet Zeile 325):

```python
def test_si_dispatch_onto_an_already_open_valve_drops_the_external_window(monkeypatch):
    """SI dispatching onto a valve a hand already opened leaves nothing for the
    close edge to credit — the runner accounts for its own run.

    The open edge is the observer's only gate, and it never fires here: the
    entity is already "on", so there is no state transition to judge.
    """
    coord = _observer_coordinator(monkeypatch, loop_time=1000.0)
    # The user opens the tap by hand: no SI run in flight, no suppression window.
    coord._observed_state_changed(_event("switch.valve", "on", "off"))
    assert 1 in coord._observed_on_since

    # Hours later SI dispatches its own 10-minute run on the same valve.
    coord._note_si_valve(1, 600)

    # The valve finally goes off.
    coord._observed_state_changed(_event("switch.valve", "off", "on"))

    coord.hass.async_create_task.assert_not_called()


def test_a_flap_after_the_takeover_credits_nothing(monkeypatch):
    """`unavailable` is a CLOSE edge, so a Zigbee dropout mid-run would credit
    the stretch since the external open — a partial double credit that needs no
    particular ordering of the run's end and the valve's close."""
    coord = _observer_coordinator(monkeypatch, loop_time=1000.0)
    coord._observed_state_changed(_event("switch.valve", "on", "off"))
    coord._note_si_valve(1, 600)

    coord._observed_state_changed(_event("switch.valve", "unavailable", "on"))

    coord.hass.async_create_task.assert_not_called()


def test_the_takeover_drops_the_marker_for_a_string_zone_id(monkeypatch):
    """Both marker dicts are keyed by int, and not every caller of
    _note_si_valve normalises its id (irrigation.py does not, batch.py does).
    A raw-key drop would silently miss."""
    coord = _observer_coordinator(monkeypatch, loop_time=1000.0)
    coord._observed_state_changed(_event("switch.valve", "on", "off"))
    assert 1 in coord._observed_on_since

    coord._note_si_valve("1", 600)

    assert 1 not in coord._observed_on_since


def test_the_takeover_does_not_outlive_the_tightened_window(monkeypatch):
    """Regression pin for the unconditional drop. The two close-side re-notes
    (_run_valve_metered, _irrigate_zone_flow_slot) call _note_si_valve with
    run_seconds=0 to SHRINK the window so a genuine external open after the run
    is tracked again. Dropping the marker there must not turn that into a
    permanent block."""
    coord = _observer_coordinator(monkeypatch, loop_time=1000.0)
    coord._note_si_valve(1, 0)  # run end: window = now + SI_VALVE_SUPPRESS_MARGIN
    assert coord._si_driven_until[1] == pytest.approx(1030.0)

    coord.hass.loop.time = Mock(return_value=1031.0)
    coord._observed_state_changed(_event("switch.valve", "on", "off"))

    assert 1 in coord._observed_on_since
```

`pytest`, `Mock` und `_event` sind in dieser Datei bereits importiert bzw. definiert — nichts nachzuziehen.

- [x] **Step 2: RED sehen**

```bash
./.venv/Scripts/python.exe -m pytest tests/test_experimental_features.py -p _local_socket_unblock -q -k "already_open_valve or flap_after_the_takeover or string_zone_id or tightened_window"
```

Erwartung: **3 failed, 1 passed**.
- `..._already_open_valve_drops_the_external_window` → `AssertionError: Expected 'async_create_task' to not have been called. Called once.`
- `test_a_flap_after_the_takeover_credits_nothing` → dieselbe Meldung.
- `test_the_takeover_drops_the_marker_for_a_string_zone_id` → `AssertionError: assert 1 not in {1: datetime...}`
- `test_the_takeover_does_not_outlive_the_tightened_window` → **passed** (Regressions-Pin, grün vor und nach dem Fix).

- [x] **Step 3: Den Marker verwerfen**

In `custom_components/irrigation_plus/irrigation.py`, Körper von `_note_si_valve` (heute Zeilen 127-130)
ersetzen durch:

```python
        zid = int(zone_id)
        until = getattr(self, "_si_driven_until", None)
        if until is not None:
            window = (run_seconds or 0.0) + SI_VALVE_SUPPRESS_MARGIN
            until[zid] = self.hass.loop.time() + window
        # The open edge is the observer's ONLY gate, and a dispatch onto a valve
        # a hand already opened produces no open edge at all — the state does not
        # change, so the gate is never consulted and the external run's marker
        # survives into SI's own run. Drop it as SI claims the valve.
        # ``getattr`` for the same reason as ``_si_driven_until`` above: the
        # runner-only test fixtures build the coordinator with __new__ and set
        # neither. ``int`` because both marker dicts are keyed by int and not
        # every caller normalises its zone id.
        pending = getattr(self, "_observed_on_since", None)
        if pending is not None:
            pending.pop(zid, None)
```

- [x] **Step 4: GREEN sehen**

```bash
./.venv/Scripts/python.exe -m pytest tests/test_experimental_features.py -p _local_socket_unblock -q -k "already_open_valve or flap_after_the_takeover or string_zone_id or tightened_window"
```

Erwartung: **4 passed**.

- [x] **Step 5: Die zwei Dateien mit den echten Aufrufern gegenprüfen**

Diese drei Dateien bauen den Koordinator mit `__new__` und lassen das **echte** `_note_si_valve` laufen; sie
setzen `_observed_on_since` nicht. Sie müssen grün bleiben — das ist der Beweis für den `getattr`-Schutz:

```bash
./.venv/Scripts/python.exe -m pytest tests/test_metered_run.py tests/test_self_closing.py tests/test_opensprinkler.py -p _local_socket_unblock -q
```

Erwartung: keine neuen Fehler gegenüber dem Vorbestand; insbesondere **kein** `AttributeError:
'SmartIrrigationCoordinator' object has no attribute '_observed_on_since'`.

- [x] **Step 6: Commit**

```bash
git add custom_components/irrigation_plus/irrigation.py tests/test_experimental_features.py
git commit -F - <<'EOF'
fix(observed): drop the external-run marker when SI claims the valve

The observed-watering observer suppresses Irrigation Plus's own runs only on
the OPEN edge. A dispatch onto a valve that is already open externally produces
no open edge at all, so the gate is never consulted: the external run's marker
survives into SI's run and the close edge credits the whole external+SI window
on top of the runner's own credit.

Drop the marker as the runner claims the valve, which is the one instant at
which the question has a single answer. The distributor already excludes SI
this way at its cycle claim.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
```

---

## Task 2: Den Fluss-Sampler des externen Laufs abbrechen

**Files:**
- Modify: `custom_components/irrigation_plus/irrigation.py` (`_note_si_valve`, eine Zeile mehr)
- Test: `tests/test_observed_watering.py` (ergänzen hinter Zeile 491)

- [x] **Step 1: Den Test schreiben**

In `tests/test_observed_watering.py`, direkt hinter `test_reopen_cancels_prior_sampler` (endet Zeile 491):

```python
async def test_si_takeover_cancels_an_external_flow_sampler(monkeypatch):
    """Claiming a valve that is already open externally must also cancel that
    run's sampler. Otherwise its 15-s timer keeps ticking until the valve
    happens to close, and the volume it measures is credited nowhere."""
    zone = {
        const.ZONE_ID: 2,
        const.ZONE_FLOW_SENSOR: "sensor.flow",
        const.ZONE_FLOW_COUNTER_TYPE: "lifetime",
        const.ZONE_SIZE: 5.0,
    }
    coord = _sampler_coord(zone)
    cancels = []
    monkeypatch.setattr(
        "custom_components.irrigation_plus.observed_watering.async_track_time_interval",
        lambda *a, **k: (cancels.append(Mock()) or cancels[-1]),
    )
    coord._observed_zone_by_entity = {"valve.x": 2}
    coord._si_driven_until = {}
    coord.hass.loop.time = Mock(return_value=1000.0)
    coord.zone_run_in_flight = Mock(return_value=False)
    coord._observed_state_changed(_state_event("valve.x", old="closed", new="open"))
    assert 2 in coord._observed_meters()

    coord._note_si_valve(2, 600)

    cancels[0].assert_called_once()
    assert coord._observed_meters() == {}
    assert 2 not in coord._observed_on_since
```

- [x] **Step 2: RED sehen**

```bash
./.venv/Scripts/python.exe -m pytest tests/test_observed_watering.py -p _local_socket_unblock -q -k "si_takeover_cancels"
```

Erwartung: **1 failed** — `AssertionError: Expected 'mock' to have been called once. Called 0 times.`
(Der Marker ist nach Task 1 schon weg, der Meter nicht.)

- [x] **Step 3: Den Sampler abbrechen**

In `_note_si_valve`, hinter dem `pending.pop(...)` aus Task 1:

```python
        # Cancel its sampler in the same breath, or the 15-s interval timer
        # keeps polling a run nobody will credit. Idempotent, and safe on a
        # coordinator whose observed state was never built: _observed_meters()
        # heals itself.
        self._observed_cancel_meter(zid)
```

- [x] **Step 4: GREEN sehen**

```bash
./.venv/Scripts/python.exe -m pytest tests/test_observed_watering.py -p _local_socket_unblock -q -k "si_takeover_cancels"
```

Erwartung: **1 passed**.

- [x] **Step 5: Die drei Observer-Dateien komplett**

```bash
./.venv/Scripts/python.exe -m pytest tests/test_observed_watering.py tests/test_experimental_features.py tests/test_observed_distributor_members.py -p _local_socket_unblock -q
```

Erwartung: **76 passed** (71 vorher + 5 neue).

- [x] **Step 6: Commit**

```bash
git add custom_components/irrigation_plus/irrigation.py tests/test_observed_watering.py
git commit -F - <<'EOF'
fix(observed): cancel the external run's flow sampler on the same claim

Dropping the marker alone leaves the sampler's 15-s interval timer polling a
run whose measurement is now credited nowhere, until the valve happens to
close.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
```

---

## Task 3: Docstring und NOT-TO-DO-Notiz (Skill `code-doku`)

**Files:**
- Modify: `custom_components/irrigation_plus/irrigation.py` (`_note_si_valve`, nur Docstring)

- [x] **Step 1: Docstring ersetzen**

Die heutige Docstring beschreibt nur das Fenster. Sie muss jetzt beide Wirkungen tragen, die verworfenen
Alternativen benennen und die bewusste Unter-Gutschrift offenlegen. Ersetze sie durch:

```python
        """Claim this zone's valve for Irrigation Plus.

        Two effects, because they are one statement: the runner drives this
        valve now, so the observed-watering observer (ObservedWateringMixin)
        must not credit the bucket for water the runner already accounts for.

        1. Arm the suppression window. ``run_seconds`` is how long this run/slot
           holds the valve open; the window spans that plus a fixed grace, so a
           valve that flaps (on -> unavailable -> on) or reports "open" slowly
           mid-run stays suppressed for the whole run instead of only the first
           30s. The OPEN edge consults that window.
        2. Discard any external-run marker for this zone, and its flow sampler.
           The open edge is the observer's ONLY gate, and a dispatch onto a valve
           a hand already opened produces no open edge: the state does not
           change, so the gate is never consulted and the marker survives into
           this run. The close edge decides on the marker alone, so it would
           then credit the whole external+SI window on top of the run's own
           credit.

        Why here and not at the close edge: a close-edge test would have to ask
        "is the runner driving this valve right now", and that question has two
        answers. A valve held open past the run closes after the window has
        lapsed -> the test says no and credits the run's own water twice. A
        valve that closes on time closes inside it -> the test says yes and
        silently discards a genuinely external prefix. At claim time the
        question is "did the runner take this window over", which has one
        answer and does not depend on timing. The distributor excludes the
        runner the same way at its cycle claim, for the same reason.

        NOT re-armed when the run ends. The external water before the takeover —
        and, on a valve held open past the run, after it — is credited nowhere.
        Deliberate: that under-credits, leaving the bucket low so the next run
        waters more, which is the milder direction this module already chose for
        its substituted ceiling. Re-arming would have to reproduce BOTH halves
        of the open edge, marker and sampler; with the marker alone a flow-sensor
        zone falls back to time x throughput, which is the phantom-open class.

        Unconditional, so it also runs at the two close-side re-notes
        (``run_seconds=0``, after the runner's own turn_off). Those are no-ops:
        the window still holds the whole run at that instant, so no external open
        could have armed a marker in between. A ``run_seconds > 0`` gate would be
        a branch with no reachable case.

        siehe test_experimental_features.py::
        test_si_dispatch_onto_an_already_open_valve_drops_the_external_window
        und test_observed_watering.py::test_si_takeover_cancels_an_external_flow_sampler
        """
```

- [x] **Step 2: Lint**

```bash
uvx black custom_components/irrigation_plus/
uvx ruff check custom_components/irrigation_plus/
```

Erwartung: `black` meldet höchstens `1 file reformatted` für `irrigation.py`, `ruff` meldet
`All checks passed!`. Formatiert `black` die Datei um, die Umformatierung mit committen.

- [x] **Step 3: Volle Suite gegen den Vorbestand**

```bash
./.venv/Scripts/python.exe -m pytest tests -p _local_socket_unblock -q > /d/Entwicklung/HASI/prA-work/after-fix.txt 2>&1
tail -1 /d/Entwicklung/HASI/prA-work/after-fix.txt
grep -E "^(FAILED|ERROR) tests/" /d/Entwicklung/HASI/prA-work/after-fix.txt | sort > /d/Entwicklung/HASI/prA-work/after-names.txt
diff /d/Entwicklung/HASI/prA-work/baseline-names.txt /d/Entwicklung/HASI/prA-work/after-names.txt && echo "IDENTISCH"
```

Erwartung: `7 failed, 3196 passed, 9 skipped, 320 errors` (3191 + 5 neue) und `IDENTISCH` —
`diff` ohne Ausgabe. Jede Abweichung ist eine Regression und stoppt den Plan.

- [x] **Step 4: Commit**

```bash
git add custom_components/irrigation_plus/irrigation.py
git commit -F - <<'EOF'
docs(observed): say why the exclusion sits at the claim, not at the close

Records the two rejected shapes (a close-edge predicate, and re-arming at the
run's end) and the credit this fix deliberately forgoes, so the next reader does
not re-derive them.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
```

---

## Task 4: Mutationsproben

Kein Produktivcode-Commit. Jede Probe wird von Hand gesetzt, die Suite läuft, die Probe wird
zurückgenommen (`git checkout -- custom_components/irrigation_plus/irrigation.py`).

**Files:**
- Temporär: `custom_components/irrigation_plus/irrigation.py`

- [x] **Step 1: Die fünf Proben fahren**

| # | Probe | Muss sterben an |
|---|---|---|
| M1 | `pending.pop(zid, None)` löschen | `..._already_open_valve_drops_the_external_window`, `..._flap_after_the_takeover...`, `..._string_zone_id` |
| M2 | `pending.pop(zid, None)` → `pending.pop(zone_id, None)` | `..._string_zone_id` |
| M3 | `self._observed_cancel_meter(zid)` löschen | `test_si_takeover_cancels_an_external_flow_sampler` |
| M4 | `self._observed_cancel_meter(zid)` → `self._observed_cancel_meter(zone_id)` | `test_si_takeover_cancels_an_external_flow_sampler` |
| M5 | Das Verwerfen auf `if run_seconds:` gaten | `..._does_not_outlive_the_tightened_window`? **Nein — erwartet ÜBERLEBEND.** Siehe Step 2. |

Je Probe:

```bash
./.venv/Scripts/python.exe -m pytest tests/test_experimental_features.py tests/test_observed_watering.py -p _local_socket_unblock -q
git checkout -- custom_components/irrigation_plus/irrigation.py
```

- [x] **Step 2: M5 als bewusst äquivalent protokollieren**

M5 (das verworfene `run_seconds > 0`-Gate) **überlebt erwartungsgemäß**: die Spec, Abschnitt 4.1(c), belegt,
dass der Fall an den zwei Schließ-seitigen Aufrufen nicht erreichbar ist — ein Test dafür wäre ein Test für
einen Zustand, den der Produktivcode nicht herstellen kann. Als **äquivalente Mutante** protokollieren, nicht
durch einen konstruierten Test totschlagen. Ergebnis in `D:/Entwicklung/HASI/prA-work/mutations.md` festhalten:
Zahl der Proben, gefangen, äquivalent, überlebend.

Erwartung: **5 Proben, 4 gefangen, 1 äquivalent, 0 unerklärt überlebend.**

---

## Task 5: Design-Historie archivieren (Regel P1)

**Files:**
- Push: `docs/superpowers/specs/2026-09-21-observed-double-credit-design.md`,
  `docs/superpowers/plans/2026-09-21-observed-double-credit.md` auf `archive/design-history`

- [ ] **Step 1: Worktree, Commit, lokal bleiben**

```bash
git worktree add /d/Entwicklung/HASI/prA-work/archive-wt archive/design-history
cp docs/superpowers/specs/2026-09-21-observed-double-credit-design.md \
   /d/Entwicklung/HASI/prA-work/archive-wt/docs/superpowers/specs/
cp docs/superpowers/plans/2026-09-21-observed-double-credit.md \
   /d/Entwicklung/HASI/prA-work/archive-wt/docs/superpowers/plans/
git -C /d/Entwicklung/HASI/prA-work/archive-wt add docs/superpowers
git -C /d/Entwicklung/HASI/prA-work/archive-wt commit -F - <<'EOF'
docs: PR A — observed double credit when SI takes over an open valve

Spec und Plan der Arbeitseinheit A aus der Arbeitsreihenfolge vom 2026-09-21.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
```

- [ ] **Step 2: Prüfen, dass nichts davon im PR-Diff liegt**

```bash
git diff --stat upstream/master..fix/observed-credit-si-takeover
```

Erwartung: **genau drei Dateien** — `custom_components/irrigation_plus/irrigation.py`,
`tests/test_experimental_features.py`, `tests/test_observed_watering.py`. **Kein** `docs/`-Eintrag.
`docs/superpowers/` ist nicht gitignored; ein `git add .` wäre hier fatal.

- [ ] **Step 3: Push erst nach Freigabe**

`git push origin archive/design-history` und `git push -u origin fix/observed-credit-si-takeover` gehen nach
außen und brauchen die ausdrückliche Freigabe des Users im Chat (globale Regel). Nicht ungefragt.

---

## Task 6: Live-Test HA-Test

Kein Code. Der Beweis, dass es an der Anlage wirkt.

- [ ] **Step 1: Freigabe und Zielwahl einholen**

Auf HA-Test steht der Sonoff-Emulator (`*sonoff_emu*`: Ventil, Fehler, Fluss-Binary,
Self-Closing-Run-Script). Vor jedem schreibenden Call die Instanz ausdrücklich benennen (Projekt-`CLAUDE.md`).
Ob der Test mit dem installierten Stand gefahren wird oder einen Pre-Release braucht, mit dem User klären —
der Fix liegt nur auf dem PR-Branch.

- [ ] **Step 2: Messen**

1. Eimerstand und Verlauf der Testzone notieren.
2. Emulator-Ventil von Hand öffnen, ~2 min offen lassen.
3. **Bei offenem Ventil** einen SI-Lauf auf dieselbe Zone auslösen.
4. Lauf auslaufen lassen, Ventil schließen lassen.
5. Verlauf lesen.

Erwartung **nach** dem Fix: **genau ein** Verlaufseintrag für das Fenster (der des Läufers), **kein**
`RUN_RESULT_OBSERVED`. Eimerdelta = die Gutschrift des Laufs, nicht deren Summe mit der externen Spanne.

- [ ] **Step 3: HA-Prod ist ein eigener Schritt**

Nur mit ausdrücklicher Freigabe; Neustart ebenso (Memory `ha-no-auto-restart`). Der Fix ist ohnehin erst
nach einem Upstream-Merge und einem Produktiv-Rebuild dort.

---

## Task 7: ToDo-Nachträge (gewichtet, User-Auftrag 2026-09-21)

**Files:**
- Modify: `D:/Entwicklung/HASI/ToDo.md`

- [ ] **Step 1: Zeile A als erledigt markieren, mit Beleg**

In der Tabelle „🔴 Schwere hoch" Zeile **A** mit dem PR-Link, der Suite-Zahl und den Mutationszahlen
ergänzen. Nicht vor Task 3 Step 3.

- [ ] **Step 2: Die zwei aufgeschobenen Punkte gewichtet eintragen**

In den Abschnitt „🟢 Schwere niedrig" bzw. — je nach Gewicht — an die passende Stelle:

- **Externer Kopf und Schwanz eines übernommenen Ventils werden nicht gutgeschrieben** —
  Schwere **niedrig**, Größe **M**, Service-/Self-Closing-Zonen. Unter-Gutschrift (Eimer zu niedrig → SI
  gießt mehr). Braucht ein Neu-Scharfstellen an fünf Laufende-Stellen **plus** Sampler-Neustart, sonst fällt
  eine Flusssensor-Zone auf Zeit × Durchsatz zurück (Phantom-offen-Klasse, #95); dazu eine Entscheidung, ob
  ein physischer Hand-Lauf zwei `RUN_RESULT_OBSERVED`-Einträge erzeugen darf. Bewusst aus PR A gehalten.
- **➀ Marker-Nachzug nach Neustart** — Schwere **niedrig-mittel**, Größe **S**, **auf Prod scharf**.
  Restdifferenz `30 − grace`: 21 s bei Vorgabewerten, 25 s bei Marge 0, 30 s ohne `confirm_entity`, 0 s bei
  Marge 25, −5 s bei Marge 30. Kein Resume-Pfad ruft `_note_si_valve`. Fix = Einzeiler neben
  `self_closing.py:1087`. **Erst nach der Nachmessung** (Task 6 bzw. ein eigener Test) einsortieren.
- **Observer-Entitätskarte filtert Verteiler-Member nicht** — Schwere **niedrig**, Größe **S**, theoretischer
  Konfigurations-Drift ohne belegten Auftritt. `observed_watering.py:56-69` hat keinen
  `ZONE_DISTRIBUTOR_ID`-Filter, anders als `irrigation.py:835`; nichts löscht ein übrig gebliebenes
  `linked_entity`/`observed_entity` einer Member-Zone.

---

## Selbstprüfung des Plans

**Spec-Abdeckung.** Anforderung 1 → Task 1. Anforderung 2 → Task 2. Anforderung 3 (acht Pfade ohne acht
Änderungen) → die Änderung sitzt in der gemeinsamen Funktion; Task 1 Step 5 belegt, dass die Runner-Tests
sie durchlaufen. Anforderung 4 → T5 in Task 1. Anforderung 5 → Task 1 Step 5. Anforderung 6 → keine
Verteiler-Datei wird angefasst, Task 5 Step 2 prüft den Diff. Spec-Abschnitt 5 (NOT-TO-DO) → Task 3
Docstring. Spec-Abschnitt 7 (Ende-zu-Ende) → Task 3 Step 3 automatisiert, Task 6 live, ➀-Nachmessung in
Task 7 Step 2.

**Platzhalter.** Keine. Jeder Test- und Codeschritt trägt den vollständigen Text.

**Namensgleichheit.** `_note_si_valve`, `_observed_on_since`, `_observed_cancel_meter`,
`_observed_meters()`, `_si_driven_until`, `SI_VALVE_SUPPRESS_MARGIN`, `zid` — in Task 1, 2, 3 und 4 überall
gleich geschrieben. Testnamen in Task 1/2 stimmen mit denen in Task 4 und in der Docstring aus Task 3 überein.

---

## Umsetzungsnachtrag (2026-09-21)

Branch `fix/observed-credit-si-takeover`, vier Commits auf `upstream/master` = `965a4f9d`:

| Commit | Inhalt |
|---|---|
| `d1e6c9d6` | `fix(observed): drop the external-run marker when SI claims the valve` — Task 1 |
| `42dc9edb` | `fix(observed): cancel the external run's flow sampler on the same claim` — Task 2 |
| `a85aaccb` | `docs(observed): say why the exclusion sits at the claim, not at the close` — Task 3 |
| `582a0e02` | `test(observed): pin the meter cancel on the normalised zone id` — Nachtrag aus Task 4 |

PR-Diff: **drei Dateien**, `custom_components/irrigation_plus/irrigation.py`,
`tests/test_experimental_features.py`, `tests/test_observed_watering.py`. Kein `docs/`, kein Frontend,
kein `dist`.

### Was gegenüber dem Plan anders lief

**Probe M4 war eine echte Testlücke, kein äquivalenter Mutant.** Der Plan hatte sie als „muss sterben"
gelistet, sie überlebte aber im ersten Lauf: `test_si_takeover_cancels_an_external_flow_sampler` übergab
die Zonen-ID als `int`, dort sind `zid` und `zone_id` derselbe Wert. Der Meter-Dict ist jedoch wie der
Marker-Dict auf den `int` aus dem Speicher geschlüsselt, und der klassische wie der rotierende Läufer
reichen ihre ID unnormalisiert durch. Geschlossen mit RED zuerst (M4 gesetzt → Test fällt → M4 zurück →
grün), eigener Commit `582a0e02`. Protokoll: `D:/Entwicklung/HASI/prA-work/mutations.md`.

**Der M5-Anker im Proben-Skript saß daneben** (Anzahl 0, also gar nicht angewendet) — als eigene Probe
`scratchpad/mutate_m5.py` nachgeholt. Ergebnis wie erwartet: überlebt, äquivalent.

**Der Inline-Kommentar wurde nach der Docstring gekürzt.** Beide trugen dieselbe Begründung; das „Warum"
steht jetzt einmal in der Docstring, der Kommentar nur noch die zwei mechanischen Gründe (`getattr`, `int`).

### Belege

- **RED gesehen** für alle fünf Tests, jeweils mit der im Plan vorhergesagten Meldung. Der Kern-Test fiel
  mit `Expected 'async_create_task' to not have been called. Called 1 times. Calls: [call(<coroutine object
  ObservedWateringMixin._credit_observed_watering …>)]` — die Doppelgutschrift beim Einplanen erwischt.
- **Volle Suite:** Vorbestand `965a4f9d` = 7 failed / **3191** passed / 9 skipped / 320 errors →
  Endstand 7 failed / **3196** passed / 9 skipped / 320 errors. Die 327 FAILED-/ERROR-Namen sind
  `diff`-identisch (`prA-work/baseline-names.txt` gegen `prA-work/final-names.txt`).
- **`getattr`-Schutz belegt:** `tests/test_metered_run.py`, `tests/test_self_closing.py`,
  `tests/test_opensprinkler.py`, `tests/test_batch.py` laufen mit dem echten `_note_si_valve` und ohne
  `_observed_on_since` — 194 passed, 51 Fehler, alle im Vorbestand, **kein** `AttributeError`.
- **Lint:** `uvx black --check` → 68 Dateien unverändert; `uvx ruff check` → All checks passed.
- **Mutationsproben:** 5 Proben, 4 gefangen, 1 äquivalent, 0 unerklärt überlebend.

### Offen

Task 6 (Live-Test HA-Test) und Task 7 (ToDo-Nachträge) stehen noch aus. Push von Branch und
Archiv-Branch braucht die Freigabe des Users.
