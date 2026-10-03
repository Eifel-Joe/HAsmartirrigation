# Entladen räumt die Self-Closing-Timer ab — Implementierungsplan

> **Für agentische Ausführung:** PFLICHT-SKILL: `superpowers:subagent-driven-development` (empfohlen) oder
> `superpowers:executing-plans`, Task für Task. Schritte nutzen Checkboxen (`- [ ]`).

**Ziel:** Nach jedem Entladen feuert kein Self-Closing-Abtaster, kein Backstop und kein anstehender
Master-Aus-Timer des alten Koordinators mehr; ein Deaktivieren stoppt und bucht die laufenden Service-Läufe und
schaltet den Master ab, ein Entfernen schickt den Stopp ohne Buchung.

**Architektur:** Drei Bausteine nach Hausmuster. (1) `async_unload` ruft einen neuen Abbau der beiden
Self-Closing-Tabellen, und `_master_release_all` kündigt den Aus-Timer mit. (2) Für die Fälle, die nichts
übernimmt, kommt der Service-Zwilling von `async_abort_opensprinkler_runs` dazu, dazu „alle Ketten freigeben“
und „Master-Zyklus jetzt beenden“. (3) `async_unload_entry` (Deaktivieren) und `async_remove_entry` (Entfernen)
rufen sie in fester Reihenfolge. Keine Store-Änderung, kein Frontend.

**Tech-Stack:** Python 3.12 (lokale Test-Env), Home Assistant 2024.12.5 über
`pytest-homeassistant-custom-component`, `freezegun`; echte `hass`-Fixture für alle Szenen mit Timern.

**Spec:** `docs/superpowers/specs/2026-10-03-unload-self-closing-teardown-design.md` (vom User freigegeben).
Issue: `Eifel-Joe#9`.

**Probelauf (2026-10-03, gegen `e9c79ec4`):** Der Endstand aller Tasks wurde in einem Wegwerf-Worktree umgesetzt
(jeder Anker dieses Plans passte genau einmal) und geprüft:
- **33 neue Tests grün**; black und ruff sauber, auch auf der Testdatei.
- **RED:** einmal für alle 33 Tests gemessen, bevor die erste Zeile Produktionscode stand; die Ursache je Test
  gelesen (die in den Steps genannten Meldungen). Rot war jeder außer dem Pin `test_a_reload_stops_nothing`.
  Die Ursache hängt nirgends an einem früheren Task: In Task 2 ist der Abbau aus Task 1 noch nicht verdrahtet, in
  Task 8 fehlt die Verdrahtung der Einstiege. Danach Task für Task GREEN.
- **Volle Suite:** 7 failed / 3651 passed / 9 skipped / 415 errors. Die FAILED/ERROR-Namen (422) sind per `diff`
  identisch mit der Baseline auf `e9c79ec4` (7 / 3618 / 9 / 415), und 3618 + 33 = 3651.
- **21/21 Mutationen getötet**, jede von den in Task 10 genannten Tests.
- **Plantext gegen den getesteten Stand geprüft** (`D:\Entwicklung\HASI\issue9-work\check_plan_blocks.py`): jeder
  „durch“- und „einfügen“-Block steht wörtlich im Probe-Code, jeder „ersetze“-Block wörtlich in `e9c79ec4`, und die
  Testdatei ist genau die Folge der Test-Blöcke dieses Plans, mit zwei Leerzeilen dazwischen.
- Der getestete Endstand liegt als Patch vor: `D:\Entwicklung\HASI\issue9-work\probe-2026-10-03.patch` (6 Dateien,
  +956/−38). **Weicht ein Snippet dieses Plans vom Patch ab, gilt der Patch** (er ist der getestete Stand); die
  Abweichung dann im Plan berichtigen. Skripte daneben: `probe_mutate.py`, `check_plan_blocks.py`.

---

## Rahmen

- **Basis:** Alle Zeilenangaben beziehen sich auf `upstream/master` = `e9c79ec4`. Hat sich `master` bewegt,
  vor Task 1 jede Anker-Stelle per `grep -n` neu suchen; die Anker sind wörtlich zitiert und passen auf
  `e9c79ec4` je genau einmal.
- **Keine Verweise auf unsere Issues, Specs oder Plan-Kürzel** in Code, Kommentaren, Tests und
  Commit-Messages (Memory `no-own-issue-refs-upstream`). Die Testdatei gliedert sich mit beschreibenden
  Abschnittstiteln, **nicht** mit Task-Nummern.
- **Testbefehl** (aus dem Worktree; es gibt dort kein eigenes `.venv`):
  `TZ=UTC /d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest <pfad> -p _local_socket_unblock -q`
- **Kein Frontend, kein dist, keine Versionsnummern** (nur Python, Tests, eine Doku-Zeile).
- **„Tests anhängen“** heißt: ans Ende von `tests/test_self_closing_teardown.py`, mit zwei Leerzeilen Abstand
  (black). Die Datei ist danach genau die Folge der Test-Blöcke aus Task 1 bis 8.
- **Commit-Messages** englisch, WAS und WARUM, mehrzeilig per Heredoc (`git commit -F - <<'EOF' … EOF`), Schluss
  `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- **Liefer-Regel:** nichts pushen und keinen PR öffnen, bevor der PR-Text (erst deutsch, dann englisch) im
  Chat freigegeben ist. production bekommt den Fix nach dem Bau sofort (User-Regel), ein HA-Prod-Update ist ein
  eigener, freigabepflichtiger Schritt.
- **Bekannte Windows-Altlasten:** In `tests/test_init.py`, `tests/test_opensprinkler_teardown.py`,
  `tests/test_batch.py` u. a. stehen rote Tests, die schon in der Baseline rot sind (aiodns braucht unter
  Windows eine andere Event-Loop). Maßstab ist immer der Namensvergleich gegen die Baseline aus Task 0.

## Dateien

| Datei | Verantwortung |
|---|---|
| `custom_components/irrigation_plus/self_closing.py` | `async_teardown_self_closing_handles`, `_sc_dispatch_stop` (aus `async_stop_self_closing` gezogen), `async_abort_self_closing_runs` |
| `custom_components/irrigation_plus/master.py` | `_master_release_all` kündigt den Aus-Timer; `async_master_end_cycle_now` |
| `custom_components/irrigation_plus/run_chain.py` | `_chain_release(mode, why)`; `async_release_all_chains` |
| `custom_components/irrigation_plus/__init__.py` | `async_unload` ruft den Abbau; Deaktivieren in `async_unload_entry`; `async_remove_entry` |
| `docs/configuration-my-zones.md` | ein Satz zum Stop service |
| neu: `tests/test_self_closing_teardown.py` | alle neuen Tests (Einheiten, Einstiege, Szenen auf der echten `hass`) |

---

### Task 0: Arbeitsumgebung und Baseline

**Files:** keine Codeänderung.

- [ ] **Step 1: Worktree von `upstream/master` anlegen** (ohne Tracking auf upstream, Memory `hasi-pr-build-recipe`)

```bash
cd /d/Entwicklung/HASI/HAsmartirrigation
git fetch upstream
git worktree add --no-track -b fix/unload-self-closing-handles /d/Entwicklung/HASI/issue9-work/wt upstream/master
cp _local_socket_unblock.py /d/Entwicklung/HASI/issue9-work/wt/
cd /d/Entwicklung/HASI/issue9-work/wt && git log --oneline -1
```

Erwartet: eine Zeile mit dem aktuellen `master`-Stand. Ist es nicht `e9c79ec4`, die Anker neu suchen, etwa
`grep -n "async def async_resume_self_closing_runs" custom_components/irrigation_plus/self_closing.py`.

- [ ] **Step 2: Baseline der vollen Suite auf diesem Commit** (Memory `rebaseline-when-the-base-moves`)

```bash
cd /d/Entwicklung/HASI/issue9-work/wt
TZ=UTC /d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests -p _local_socket_unblock -q --no-header -rfE > ../suite-baseline.txt 2>&1
tr '\r' '\n' < ../suite-baseline.txt | grep -E "^(FAILED|ERROR) tests" | sed -E 's/ - .*//' | sort > ../names-baseline.txt
tail -c 300 ../suite-baseline.txt
```

Erwartet auf `e9c79ec4`: `7 failed, 3618 passed, 9 skipped, … 415 errors` (rund 5 min), 422 Namen. Die Datei
erst nach Laufende lesen; währenddessen nichts im Worktree ändern.

---

### Task 1: Der Abbau der beiden Tabellen

**Files:**
- Create: `tests/test_self_closing_teardown.py`
- Modify: `custom_components/irrigation_plus/self_closing.py` (vor `async def async_resume_self_closing_runs`, `self_closing.py:1180`)

- [ ] **Step 1: Testdatei anlegen** — Kopf, Importe und Helfer für alle folgenden Tasks auf einmal (ruff prüft
`tests/` in CI nicht; am Ende ist jeder Import benutzt), dazu die erste Klasse:

```python
"""What an unload leaves behind, and what a disable or a removal has to stop.

A self-closing run owns two timers per zone: the flow sampler, a 15 s interval,
and the backstop, an async_call_later. async_unload cancelled neither, so both
stayed armed against the coordinator being torn down:

* on a reload the new coordinator re-arms a backstop of its own
  (async_resume_self_closing_runs) and settles the run. The old backstop then
  finds no record and returns before it ever reaches its sampler, which ticks on
  until Home Assistant restarts -- and holds the whole dead coordinator;
* a run ending while the reload is under way was settled by the DEAD
  coordinator, its chain, its deferred calculation and its master included.

Cancelling them is right for a reload, which a successor adopts. It is not
enough for an unload nothing adopts: the dead backstop was, by accident, what
settled a run after a disable and released its master, whose off timer then
switched a "master off after" pump off. So a disable now stops and settles what
the integration started, as OpenSprinkler and batch already do, and a removal
sends the stop without settling. The master is ended directly, because its own
off timer is cancelled with the rest.

The scenes run on the real ``hass``: a timer that fires is the defect, and a
double replaces exactly the thing under test.
"""

import logging
from datetime import timedelta
from unittest.mock import AsyncMock, Mock, patch

import pytest
from freezegun import freeze_time
from homeassistant.config_entries import ConfigEntryDisabler
from homeassistant.const import EVENT_CALL_SERVICE
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import (
    async_capture_events,
    async_fire_time_changed,
    async_mock_service,
)

from custom_components.irrigation_plus import (
    SmartIrrigationCoordinator,
    async_remove_entry,
    async_unload_entry,
    const,
)
from tests.test_master import _mcoord
from tests.test_service_chain import ROTATING, SEQUENTIAL, _finish, _register
from tests.test_service_chain import _coord as _chain_coord
from tests.test_service_chain import _dispatch as _chain_dispatch
from tests.test_service_chain import _ids as _chain_ids
from tests.test_service_chain import _zone as _chain_zone
from tests.test_service_watch import (
    RATE,
    VALVE,
    _advance,
    _coord,
    _dispatch,
    _flow,
    _litres,
    _metered,
    _metered_zone,
    _report,
    _set,
    _the_real_backstop_from_here,
    _walk,
    _zone,
)

DISABLED = "the Irrigation Plus config entry is being disabled"
REMOVED = "the Irrigation Plus config entry is being removed"


def _unloadable(c):
    """Give a test host what async_unload reads without a guard.

    The trackers and _subscriptions are set by __init__, which these hosts skip;
    observed watering is not under test. _os_cancel_watch goes back to the real
    method, so the unload drops the run's watcher as it does in production.
    """
    c.hass.data.setdefault(const.DOMAIN, {})
    c._pending_track_update_unsub = None
    c._track_auto_update_time_unsub = None
    c._track_auto_calc_time_unsub = None
    c._track_midnight_time_unsub = None
    c._track_buffer_flush_unsub = None
    c.async_teardown_observed_watering = Mock()
    c._dist_inlet_watchers = {}
    c._subscriptions = []
    del c._os_cancel_watch
    return c


def _real_master(c, hass, *, off_after=True):
    """Swap the host's master doubles for the real refcount on a mocked pump."""
    del c.async_master_acquire
    del c.async_master_release
    c.store.config.master_entity = "switch.pump"
    c.store.config.master_off_after = off_after
    c.store.config.master_settle_seconds = 0
    c.store.config.master_kick_enabled = False
    c.store.config.master_kick_pause_seconds = 0
    async_mock_service(hass, "switch", "turn_on")
    async_mock_service(hass, "switch", "turn_off")


def _stops(calls):
    return [
        e.data["service_data"]
        for e in calls
        if e.data["service"] == "stop_irrigation_beet"
    ]


def _opened(calls):
    return [
        e.data["service_data"]["zone_id"]
        for e in calls
        if e.data["service"] == "irrigation_beet"
    ]


def _pump_offs(calls):
    return [
        e
        for e in calls
        if e.data["domain"] == "switch" and e.data["service"] == "turn_off"
    ]


def _called(coordinator):
    return [name for name, _args, _kwargs in coordinator.mock_calls]


def _unload_patches(hass):
    return (
        patch("custom_components.irrigation_plus.remove_panel"),
        patch.object(
            hass.config_entries,
            "async_forward_entry_unload",
            new=AsyncMock(return_value=True),
        ),
    )


# --------------------------------------------------------------------------- #
# The teardown itself
# --------------------------------------------------------------------------- #
class TestTheTeardownCancelsBothTimers:
    """async_teardown_self_closing_handles: cancel, empty, touch nothing else."""

    async def test_both_timers_are_cancelled_and_both_tables_emptied(self, hass):
        c = _coord(hass)
        _the_real_backstop_from_here(c)
        sampler, backstop = Mock(), Mock()
        c._sc_meters()[2] = (Mock(), sampler, 120.0, dt_util.utcnow())
        c._sc_cleanup_timers()[2] = backstop

        c.async_teardown_self_closing_handles()

        sampler.assert_called_once_with()
        backstop.assert_called_once_with()
        assert c._sc_meters() == {}
        assert c._sc_cleanup_timers() == {}

    async def test_nothing_is_read_settled_or_written(self, hass):
        """The successor owns the run: no final read, no settle, no write."""
        c = _coord(hass)
        _the_real_backstop_from_here(c)
        meter = Mock()
        c._sc_meters()[2] = (meter, Mock(), 120.0, dt_util.utcnow())
        c._sc_cleanup_timers()[2] = Mock()

        c.async_teardown_self_closing_handles()

        meter.sample.assert_not_called()
        meter.delivered.assert_not_called()
        c._sc_finish_flow.assert_not_called()
        c.store.async_update_config.assert_not_awaited()
        c.store.async_update_zone.assert_not_awaited()
        c._record_run.assert_not_awaited()

    def test_a_coordinator_that_never_ran_one_tears_down_cleanly(self):
        c = SmartIrrigationCoordinator.__new__(SmartIrrigationCoordinator)

        c.async_teardown_self_closing_handles()

        assert c._sc_meters() == {}
        assert c._sc_cleanup_timers() == {}
```

- [ ] **Step 2: Rot sehen**

Run: `TZ=UTC … -m pytest "tests/test_self_closing_teardown.py::TestTheTeardownCancelsBothTimers" -p _local_socket_unblock -q`
Expected: `3 failed`, je `AttributeError: 'SmartIrrigationCoordinator' object has no attribute 'async_teardown_self_closing_handles'`.

- [ ] **Step 3: Implementieren** — in `self_closing.py` direkt vor `    async def async_resume_self_closing_runs(self) -> None:` einfügen:

```python
    def async_teardown_self_closing_handles(self) -> None:
        """Cancel every flow sampler and backstop this coordinator armed (unload).

        Both close over THIS coordinator. A reload leaves the run itself in the
        store for async_resume_self_closing_runs, which arms a backstop of its
        own. Left armed, the old backstop then finds no record and returns
        before it ever reaches its sampler, which ticks on until Home Assistant
        restarts and keeps the dead coordinator alive; and a run that ends while
        the reload is under way is settled through the dead coordinator.

        Cancel only: no final read, nothing settled, nothing written. The
        successor owns the run. The meter's litres are lost across a reload as
        they are across a restart, and the run is booked by time.
        """
        meters = self._sc_meters()
        for zone_id in list(meters):
            meters.pop(zone_id)[1]()  # the interval's cancel handle
        for zone_id in list(self._sc_cleanup_timers()):
            self._sc_cancel_cleanup(zone_id)

```

- [ ] **Step 4: Grün sehen** — derselbe Befehl: `3 passed`.

- [ ] **Step 5: Commit**

```bash
git add tests/test_self_closing_teardown.py custom_components/irrigation_plus/self_closing.py
git commit -F - <<'EOF'
fix(self-closing): a teardown for the sampler and the backstop a run owns

Both are per-zone timers closing over the coordinator that armed them, and
nothing cancelled them when that coordinator went away. The teardown cancels
them without a final read and without settling anything: on a reload the
successor adopts the run, as it does after a restart.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
```

---

### Task 2: Der Abbau läuft bei jedem Entladen

**Files:**
- Modify: `custom_components/irrigation_plus/__init__.py` (in `async_unload`, nach `self.async_teardown_batch_watchers()`, `__init__.py:2244`)
- Test: `tests/test_self_closing_teardown.py`

- [ ] **Step 1: Failing tests anhängen**

```python
# --------------------------------------------------------------------------- #
# A reload in the middle of a run
# --------------------------------------------------------------------------- #
class TestAReloadMidRun:
    """The old coordinator unloads, the new one adopts the run from the store."""

    async def test_the_run_is_booked_once_by_the_new_coordinator(self, hass):
        """And the old sampler stops: it used to tick until the next restart.

        The meter does not cross the reload, exactly as it does not cross a
        restart: the new coordinator books the run by time (1 L in this host).
        """
        old = _unloadable(_coord(hass))
        _metered(old)
        _the_real_backstop_from_here(old)
        started = dt_util.utcnow().replace(microsecond=0)
        with freeze_time(started) as frozen:
            await _flow(hass, RATE)
            await _dispatch(hass, old, _metered_zone(600))
            await _walk(hass, frozen, 300)
            old._sc_sample_flow = Mock(wraps=old._sc_sample_flow)
            await old.async_unload()

            new = _coord(hass)
            new.store = old.store  # one store, as across a real reload
            _metered(new)
            _the_real_backstop_from_here(new)
            await new.async_resume_self_closing_runs()
            await hass.async_block_till_done()

            await _walk(hass, frozen, 300)  # 600: the valve closes
            await _flow(hass, 0)
            await _report(hass, "off", started + timedelta(seconds=600))
            await _advance(hass, frozen, const.SERVICE_WATCH_SETTLE_SECONDS + 1)
            await _walk(hass, frozen, 60)  # past where the old backstop was due

        assert await new._sc_find_run(2) is None
        new._record_run.assert_awaited_once()
        assert _litres(new) == 1.0
        old._record_run.assert_not_awaited()
        old._sc_sample_flow.assert_not_called()
        assert old._sc_meters() == {}
        assert old._sc_cleanup_timers() == {}

    async def test_a_run_ending_during_the_reload_waits_for_the_successor(self, hass):
        """The old backstop used to settle it through the dead coordinator."""
        old = _unloadable(_coord(hass))
        _the_real_backstop_from_here(old)
        started = dt_util.utcnow().replace(microsecond=0)
        with freeze_time(started) as frozen:
            await _dispatch(hass, old, _zone())
            await _advance(hass, frozen, 300)
            await old.async_unload()
            await _advance(hass, frozen, 400)  # 700: past plan and grace

            assert await old._sc_find_run(2) is not None
            old._record_run.assert_not_awaited()

            new = _coord(hass)
            new.store = old.store
            await new.async_resume_self_closing_runs()
            await hass.async_block_till_done()

        assert await new._sc_find_run(2) is None
        new._record_run.assert_awaited_once()
        assert new._record_run.await_args.kwargs["planned_s"] == 600
        old._record_run.assert_not_awaited()
```

- [ ] **Step 2: Rot sehen**

Run: `TZ=UTC … -m pytest "tests/test_self_closing_teardown.py::TestAReloadMidRun" -p _local_socket_unblock -q`
Expected: `2 failed, 1 error`. Der erste Test: `AssertionError: Expected 'mock' to not have been called. Called 24
times.` (der alte Abtaster tickt nach dem Entladen weiter), dazu ein Error im Teardown, weil sein Intervall noch
scharf ist (lingering timer). Der zweite: `assert None is not None` (der tote Backstop hat den Lauf gebucht).

- [ ] **Step 3: Implementieren** — in `__init__.py`, `async_unload`, ersetze

```python
        # Same for the batch controller: its paused-indicator subscription and
        # any pending pause bound would otherwise fire against a dead coordinator.
        self.async_teardown_batch_watchers()
```

durch

```python
        # Same for the batch controller: its paused-indicator subscription and
        # any pending pause bound would otherwise fire against a dead coordinator.
        self.async_teardown_batch_watchers()
        # And every self-closing flow sampler and backstop. Left armed, the
        # backstop settles a run the new coordinator has adopted, or finds it
        # already gone and strands its sampler, which ticks until Home
        # Assistant restarts. The run itself stays for the resume path.
        self.async_teardown_self_closing_handles()
```

- [ ] **Step 4: Grün sehen** — derselbe Befehl: `2 passed`. Dazu die vorhandenen Entlade-Tests:
`TZ=UTC … -m pytest tests/test_init.py tests/test_run_lifecycle_safety.py tests/test_opensprinkler_teardown.py -p _local_socket_unblock -q -rfE`
→ die roten Namen sind dieselben wie in `../names-baseline.txt` (Windows-Altlasten), keine neuen.

- [ ] **Step 5: Commit**

```bash
git add tests/test_self_closing_teardown.py custom_components/irrigation_plus/__init__.py
git commit -F - <<'EOF'
fix(unload): cancel the self-closing sampler and backstop with the coordinator

A reload left both armed. The new coordinator adopts the run and settles it,
so the old backstop found no record and returned before it reached its
sampler, which then ticked every 15 s until Home Assistant restarted. A run
that ended while the reload was under way was settled by the old coordinator.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
```

---

### Task 3: `_master_release_all` kündigt den Aus-Timer

**Files:**
- Modify: `custom_components/irrigation_plus/master.py:145-147`
- Test: `tests/test_self_closing_teardown.py`

- [ ] **Step 1: Failing test anhängen**

```python
# --------------------------------------------------------------------------- #
# The master's off timer goes with the coordinator
# --------------------------------------------------------------------------- #
class TestTheMasterOffTimerGoesWithTheCoordinator:
    async def test_release_all_cancels_a_pending_off(self, monkeypatch):
        """Left armed it read the emptied holds as "nothing running"."""
        c = _mcoord(master_off_after=True)
        cancel = Mock()
        monkeypatch.setattr(
            "custom_components.irrigation_plus.master.async_call_later",
            Mock(return_value=cancel),
        )
        await c.async_master_acquire("sc:2")
        await c.async_master_release("sc:2")  # the last hold: the off timer
        assert c._master_off_cancel is cancel

        c._master_release_all()

        cancel.assert_called_once_with()
        assert c._master_off_cancel is None
        assert c.master_holds() == set()
```

- [ ] **Step 2: Rot sehen**

Run: `TZ=UTC … -m pytest "tests/test_self_closing_teardown.py::TestTheMasterOffTimerGoesWithTheCoordinator" -p _local_socket_unblock -q`
Expected: `1 failed`, `AssertionError: Expected 'mock' to be called once. Called 0 times.`

- [ ] **Step 3: Implementieren** — in `master.py` ersetze

```python
    def _master_release_all(self) -> None:
        """Drop every hold without touching the hardware (unload/reset only)."""
        self._master_hold_set().clear()
```

durch

```python
    def _master_release_all(self) -> None:
        """Drop every hold and the pending off timer, without touching the
        hardware (unload/reset only).

        The timer closes over this coordinator and reads its holds. Left armed
        across a reload it fired against the emptied holds of a dead
        coordinator, read them as "nothing running" and, with master_off_after,
        switched the master off under a run the new coordinator had just started.
        """
        self._master_hold_set().clear()
        cancel = getattr(self, "_master_off_cancel", None)
        if cancel is not None:
            cancel()
            self._master_off_cancel = None
```

Zweiter Aufrufer ist die Boot-Bereinigung (`master.py:246`); dort steht nie ein Timer an, sie ändert sich nicht.

- [ ] **Step 4: Grün sehen** — derselbe Befehl: `1 passed`; dazu `tests/test_master.py` grün.

- [ ] **Step 5: Commit**

```bash
git add tests/test_self_closing_teardown.py custom_components/irrigation_plus/master.py
git commit -F - <<'EOF'
fix(master): the pending off timer goes with the holds on unload

_master_release_all emptied the holds and left the off timer armed. After a
reload that timer fired against the dead coordinator, read its emptied holds
as "nothing running" and, with master_off_after, could switch the master off
under a run the new coordinator had just started.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
```

---

### Task 4: Master-Zyklus jetzt beenden

**Files:**
- Modify: `custom_components/irrigation_plus/master.py` (neue Methode direkt nach `_master_release_all`)
- Test: `tests/test_self_closing_teardown.py`

- [ ] **Step 1: Failing tests anhängen**

```python
# --------------------------------------------------------------------------- #
# Ending the master cycle at once
# --------------------------------------------------------------------------- #
def _cycle_ending(c, cancel):
    """A cycle whose last hold just went: master on, off timer pending."""
    c._master_on = True
    c._master_off_deadline = dt_util.utcnow() + timedelta(seconds=5)
    c._master_off_cancel = cancel


class TestEndingTheMasterCycleNow:
    async def test_a_master_we_switched_on_is_switched_off(self):
        c = _mcoord(master_off_after=True)
        cancel = Mock()
        _cycle_ending(c, cancel)

        await c.async_master_end_cycle_now()

        c.hass.services.async_call.assert_awaited_once_with(
            "switch", "turn_off", {"entity_id": "switch.pump"}
        )
        cancel.assert_called_once_with()
        assert c._master_off_cancel is None
        assert c._master_on is False
        assert c._master_off_deadline is None

    async def test_a_stay_on_pump_is_left_on(self):
        c = _mcoord(master_off_after=False)
        cancel = Mock()
        _cycle_ending(c, cancel)

        await c.async_master_end_cycle_now()

        c.hass.services.async_call.assert_not_awaited()
        cancel.assert_called_once_with()
        assert c._master_on is False

    async def test_a_master_we_did_not_switch_on_is_left_alone(self):
        c = _mcoord(master_off_after=True)
        c._master_on = False

        await c.async_master_end_cycle_now()

        c.hass.services.async_call.assert_not_awaited()

    async def test_a_hold_still_taken_leaves_the_cycle_to_its_owner(self):
        """A classic run runs on as a task and ends the cycle as it releases."""
        c = _mcoord(master_off_after=True)
        cancel = Mock()
        _cycle_ending(c, cancel)
        c._master_hold_set().add("seq:abcd1234")

        await c.async_master_end_cycle_now()

        c.hass.services.async_call.assert_not_awaited()
        cancel.assert_not_called()
        assert c._master_on is True

    async def test_without_a_master_nothing_happens(self):
        c = _mcoord(master_entity=None, master_off_after=True)
        c._master_on = True

        await c.async_master_end_cycle_now()

        c.hass.services.async_call.assert_not_awaited()
        assert c._master_on is True

    async def test_a_switch_that_raises_does_not_block_the_unload(self, caplog):
        c = _mcoord(master_off_after=True)
        _cycle_ending(c, Mock())
        c.hass.services.async_call = AsyncMock(side_effect=RuntimeError("zigbee"))

        await c.async_master_end_cycle_now()  # must not raise

        assert "Could not end the master cycle" in caplog.text
```

- [ ] **Step 2: Rot sehen**

Run: `TZ=UTC … -m pytest "tests/test_self_closing_teardown.py::TestEndingTheMasterCycleNow" -p _local_socket_unblock -q`
Expected: `6 failed`, je `AttributeError: '_MasterHost' object has no attribute 'async_master_end_cycle_now'`.

- [ ] **Step 3: Implementieren** — in `master.py` direkt nach `_master_release_all` (also vor
`    def _master_note_run(self, seconds: float):`) einfügen:

```python
    async def async_master_end_cycle_now(self) -> None:
        """End the cycle at once, for an unload nothing comes back from.

        A disable or a removal tears the coordinator down, and with it the off
        timer the release of the last hold armed: nothing would switch a
        master_off_after master off any more. So the cycle ends here, while the
        coordinator still lives: the off timer cancelled and, iff
        master_off_after is set and a cycle of ours is up, the master switched
        off, the same end _fire gives it.

        Left alone while a hold remains: a classic run, or a distributor sweep,
        runs on as a task and ends the cycle itself when it releases. Never
        raises: a failure here must not be able to block an unload.
        """
        try:
            if not self._master_configured() or self._master_hold_set():
                return
            cancel = getattr(self, "_master_off_cancel", None)
            if cancel is not None:
                cancel()
                self._master_off_cancel = None
            if getattr(self, "_master_on", False) and getattr(
                self._master_cfg(), const.CONF_MASTER_OFF_AFTER, False
            ):
                await self._master_turn(False)
            self._master_on = False
            self._master_off_deadline = None
        except Exception:  # noqa: BLE001
            _LOGGER.exception("Could not end the master cycle")

```

- [ ] **Step 4: Grün sehen** — derselbe Befehl: `6 passed`.

- [ ] **Step 5: Commit**

```bash
git add tests/test_self_closing_teardown.py custom_components/irrigation_plus/master.py
git commit -F - <<'EOF'
feat(master): end the cycle at once for an unload nothing comes back from

A disable or a removal cancels the off timer with the rest of the
coordinator, so nothing would switch a master_off_after master off any more.
async_master_end_cycle_now ends the cycle the way the timer would have:
master off iff master_off_after is set and a cycle of ours is up. A remaining
hold leaves the cycle to its owner, a classic run that runs on as a task.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
```

---

### Task 5: Alle Ketten freigeben

**Files:**
- Modify: `custom_components/irrigation_plus/run_chain.py:667-681` (`_chain_release`) und neue Methode vor `def _chain_teardown(self)` (`run_chain.py:683`)
- Test: `tests/test_self_closing_teardown.py`

- [ ] **Step 1: Failing tests anhängen**

```python
# --------------------------------------------------------------------------- #
# Releasing every chain
# --------------------------------------------------------------------------- #
class TestReleasingEveryChain:
    """A chain holds the master for its whole cycle, pauses included."""

    async def test_a_rotation_absorbing_between_slots_hands_back_its_hold(
        self, hass, caplog
    ):
        caplog.set_level(logging.INFO)
        c = _chain_coord(hass, ROTATING, slot=1, absorb=10)
        await _chain_dispatch(c, _register(c, _chain_zone(1, duration=180)))
        await _finish(c, 1)
        state = c._chain_state(const.WATERING_MODE_SERVICE)
        token = state.token
        assert state.absorb is not None and token is not None

        await c.async_release_all_chains(DISABLED)

        assert state.absorb is None
        assert state.rotation is None
        assert state.token is None
        c.async_master_release.assert_any_await(token)
        assert DISABLED in caplog.text

    async def test_a_sequential_queue_starts_nothing_after_its_release(self, hass):
        c = _chain_coord(hass, SEQUENTIAL)
        await _chain_dispatch(c, _register(c, _chain_zone(1), _chain_zone(2)))
        assert _chain_ids(c) == [1]

        await c.async_release_all_chains(DISABLED)
        await _finish(c, 1)

        assert _chain_ids(c) == [1]
        assert c._chain_state(const.WATERING_MODE_SERVICE).zones == []

    async def test_an_idle_coordinator_releases_nothing(self, hass):
        c = _chain_coord(hass, SEQUENTIAL)

        await c.async_release_all_chains(DISABLED)

        c.async_master_release.assert_not_awaited()

    async def test_one_chain_that_raises_does_not_stop_the_others(self, hass, caplog):
        c = _chain_coord(hass, SEQUENTIAL)
        c._chain_state(const.WATERING_MODE_SERVICE)
        c._chain_state(const.WATERING_MODE_OPENSPRINKLER)
        c._chain_release = AsyncMock(side_effect=[RuntimeError("boom"), None])

        await c.async_release_all_chains(DISABLED)  # must not raise

        assert c._chain_release.await_count == 2
        assert "Could not release" in caplog.text
```

- [ ] **Step 2: Rot sehen**

Run: `TZ=UTC … -m pytest "tests/test_self_closing_teardown.py::TestReleasingEveryChain" -p _local_socket_unblock -q`
Expected: `4 failed, 1 error`, je `AttributeError: 'SmartIrrigationCoordinator' object has no attribute
'async_release_all_chains'`; der Error ist der Absorptions-Timer des ersten Tests, der scharf bleibt.

- [ ] **Step 3: Implementieren** — in `run_chain.py` ersetze in `_chain_release`

```python
    async def _chain_release(self, mode) -> None:
        """Drop this chain and its master hold.

        Also names whatever the cycle still had queued or mid-rotation and
        hands back any live-estimate marker those zones hold — see
        :meth:`_chain_forfeit_queue`.
        """
        state = self._chain_state(mode)
        self._chain_cancel_absorption(mode)
        self._chain_forfeit_queue(mode, "the cycle was stopped")
```

durch

```python
    async def _chain_release(self, mode, why: str = "the cycle was stopped") -> None:
        """Drop this chain and its master hold.

        Also names whatever the cycle still had queued or mid-rotation and
        hands back any live-estimate marker those zones hold — see
        :meth:`_chain_forfeit_queue`. ``why`` is the reason it names.
        """
        state = self._chain_state(mode)
        self._chain_cancel_absorption(mode)
        self._chain_forfeit_queue(mode, why)
```

und füge direkt vor `    def _chain_teardown(self) -> None:` ein:

```python
    async def async_release_all_chains(self, why: str) -> None:
        """Release every chain and its master hold (an unload nothing adopts).

        A chain holds the master for its whole cycle, the gaps between its runs
        and a rotation's absorption waits included (_chain_take_hold).
        _chain_teardown drops the chains without that release, which a reload
        can afford: its successor reconciles the master on the way back up. A
        disable has no successor. Caught in such a pause, with no run in
        flight for an abort to find, the hold would keep the master up after
        the cycle is gone. Never raises.
        """
        for mode in list(self._chains()):
            try:
                await self._chain_release(mode, why)
            except Exception:  # noqa: BLE001
                _LOGGER.exception("Could not release the %s chain", mode)

```

- [ ] **Step 4: Grün sehen** — derselbe Befehl: `4 passed`; dazu `tests/test_service_chain.py`,
`tests/test_chain_carries_its_plan.py`, `tests/test_opensprinkler.py` ohne neue rote Namen gegenüber der Baseline.

- [ ] **Step 5: Commit**

```bash
git add tests/test_self_closing_teardown.py custom_components/irrigation_plus/run_chain.py
git commit -F - <<'EOF'
feat(chain): release every chain and its master hold in one call

A chain holds the master for its whole cycle, the pauses between its runs
included. Teardown drops the chains without releasing that hold, which a
reload can afford because its successor reconciles the master; a disable has
no successor. _chain_release takes the reason it logs for the queue it drops.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
```

---

### Task 6: Der Stopp-Befehl als eigene Funktion

**Files:**
- Modify: `custom_components/irrigation_plus/self_closing.py` (neue Methode nach `_sc_find_run`, `self_closing.py:964-968`; Aufruf in `async_stop_self_closing`, `self_closing.py:1002-1031`)
- Test: `tests/test_self_closing_teardown.py`

- [ ] **Step 1: Failing tests anhängen**

```python
# --------------------------------------------------------------------------- #
# The stop instruction on its own
# --------------------------------------------------------------------------- #
class TestTheStopInstruction:
    async def test_the_stop_service_gets_a_zero_duration_under_its_field(self, hass):
        c = _coord(hass)
        calls = async_capture_events(hass, EVENT_CALL_SERVICE)

        sent = await c._sc_dispatch_stop(2, _zone())
        await hass.async_block_till_done()

        assert sent is True
        assert _stops(calls) == [{"zone_id": 2, "dauer": 0}]

    async def test_a_zone_without_a_stop_service_sends_nothing(self, hass):
        c = _coord(hass)
        calls = async_capture_events(hass, EVENT_CALL_SERVICE)
        zone = _zone()
        del zone[const.ZONE_STOP_SERVICE]

        sent = await c._sc_dispatch_stop(2, zone)
        await hass.async_block_till_done()

        assert sent is False
        assert calls == []

    async def test_an_opensprinkler_zone_stops_through_its_station(self, hass):
        c = _coord(hass)
        c._os_dispatch_stop = AsyncMock()
        zone = _zone(**{const.ZONE_WATERING_MODE: const.WATERING_MODE_OPENSPRINKLER})

        sent = await c._sc_dispatch_stop(2, zone)

        assert sent is True
        c._os_dispatch_stop.assert_awaited_once_with(zone)
```

- [ ] **Step 2: Rot sehen**

Run: `TZ=UTC … -m pytest "tests/test_self_closing_teardown.py::TestTheStopInstruction" -p _local_socket_unblock -q`
Expected: `3 failed`, je `AttributeError: 'SmartIrrigationCoordinator' object has no attribute '_sc_dispatch_stop'`.

- [ ] **Step 3: Implementieren** — in `self_closing.py` direkt nach `_sc_find_run` (vor
`    async def async_stop_self_closing(`) einfügen:

```python
    async def _sc_dispatch_stop(self, zone_id, zone: dict) -> bool:
        """Send the zone's stop instruction; True if one went out.

        False only for a zone nothing can close: not OpenSprinkler, and no
        stop_service. What to say about that is the caller's, because a stop
        that settles the run and one that only closes it (a removal) mean
        different things by it.
        """
        if is_opensprinkler_zone(zone):
            # opensprinkler.stop is entity-targeted; the stop_service adapter
            # below sends a zone_id that its schema rejects.
            await self._os_dispatch_stop(zone)
            return True
        stop_svc = zone.get(const.ZONE_STOP_SERVICE)
        if not stop_svc:
            return False
        domain, service = self._sc_split_service(stop_svc)
        data = {}
        data["zone_id"] = zone_id
        # A zero duration IS the stop instruction for the shipped
        # blueprints, which run one script for both directions and
        # branch on it. It was documented but never actually sent, so
        # the script received no `duration` at all and a template
        # reading it raised instead of closing the valve — the call is
        # not blocking, so that surfaced only in the log while the run
        # was settled as stopped and the valve went on watering to the
        # end of its hardware countdown. Sent under the zone's own
        # duration field, the same key the open uses.
        field = zone.get(const.ZONE_DURATION_FIELD) or "duration"
        data[field] = 0
        await self.hass.services.async_call(domain, service, data)
        return True

```

und ersetze in `async_stop_self_closing` den Block

```python
        if close_valve:
            if is_opensprinkler_zone(zone):
                # opensprinkler.stop is entity-targeted; the stop_service adapter
                # below sends a zone_id that its schema rejects.
                await self._os_dispatch_stop(zone)
            elif stop_svc := zone.get(const.ZONE_STOP_SERVICE):
                domain, service = self._sc_split_service(stop_svc)
                data = {}
                data["zone_id"] = zone_id
                # A zero duration IS the stop instruction for the shipped
                # blueprints, which run one script for both directions and
                # branch on it. It was documented but never actually sent, so
                # the script received no `duration` at all and a template
                # reading it raised instead of closing the valve — the call is
                # not blocking, so that surfaced only in the log while the run
                # was settled as stopped and the valve went on watering to the
                # end of its hardware countdown. Sent under the zone's own
                # duration field, the same key the open uses.
                field = zone.get(const.ZONE_DURATION_FIELD) or "duration"
                data[field] = 0
                await self.hass.services.async_call(domain, service, data)
            else:
                _LOGGER.warning(
                    "Zone %s stopped in self-closing mode without a stop_service; "
                    "cannot close the valve, correcting accounting only",
                    zone_id,
                )
```

durch

```python
        if close_valve and not await self._sc_dispatch_stop(zone_id, zone):
            _LOGGER.warning(
                "Zone %s stopped in self-closing mode without a stop_service; "
                "cannot close the valve, correcting accounting only",
                zone_id,
            )
```

Verhalten unverändert: OpenSprinkler über die Station, sonst Stop service mit Dauer 0, sonst dieselbe Warnung.

- [ ] **Step 4: Grün sehen** — derselbe Befehl: `3 passed`. Dann die Stopp-Pfade ohne neue rote Namen:

```bash
TZ=UTC /d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests/test_self_closing.py tests/test_service_watch.py tests/test_opensprinkler.py tests/test_batch.py -p _local_socket_unblock -q --no-header -rfE 2>&1 | tr '\r' '\n' | grep -E "^(FAILED|ERROR) tests" | sed -E 's/ - .*//' | sort > ../names-t6.txt
grep -E "tests/test_(self_closing|service_watch|opensprinkler|batch)\.py" ../names-baseline.txt | sort | diff - ../names-t6.txt && echo identical
```

Expected: `identical` (im Probelauf 52 Altlasten-Errors, namensgleich; 271 passed).

- [ ] **Step 5: Commit**

```bash
git add tests/test_self_closing_teardown.py custom_components/irrigation_plus/self_closing.py
git commit -F - <<'EOF'
refactor(self-closing): the stop instruction as a function of its own

Moved out of async_stop_self_closing unchanged, so a caller can close a valve
without settling the run: the abort on removal, whose store is deleted next.
It reports whether a stop went out; the warning for a zone without a stop
service stays where it was.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
```

---

### Task 7: Service-Läufe abbrechen

**Files:**
- Modify: `custom_components/irrigation_plus/self_closing.py` (neue Methode direkt vor `async_teardown_self_closing_handles` aus Task 1)
- Test: `tests/test_self_closing_teardown.py`

- [ ] **Step 1: Failing tests anhängen**

```python
# --------------------------------------------------------------------------- #
# Aborting the service runs
# --------------------------------------------------------------------------- #
async def _a_run_halfway(hass, c, frozen, zone=None):
    await _dispatch(hass, c, zone or _zone())
    await _advance(hass, frozen, 300)


class TestAbortingTheServiceRuns:
    """The service twin of async_abort_opensprinkler_runs."""

    async def test_a_service_run_is_stopped_and_settled(self, hass):
        c = _coord(hass)
        calls = async_capture_events(hass, EVENT_CALL_SERVICE)
        started = dt_util.utcnow().replace(microsecond=0)
        with freeze_time(started) as frozen:
            await _a_run_halfway(hass, c, frozen)
            stopped = await c.async_abort_self_closing_runs(DISABLED)
            await hass.async_block_till_done()

        assert stopped is True
        assert _stops(calls) == [{"zone_id": 2, "dauer": 0}]
        assert await c._sc_find_run(2) is None
        kw = c._record_run.await_args.kwargs
        assert kw["result"] == const.RUN_RESULT_PARTIAL
        assert kw["actual_s"] == pytest.approx(300, abs=1)
        c.async_master_release.assert_awaited_once_with("sc:2")

    async def test_a_record_without_a_mode_is_a_service_run(self, hass):
        """The resume path reads it as one, so the abort does too."""
        c = _coord(hass)
        calls = async_capture_events(hass, EVENT_CALL_SERVICE)
        c._zones[2] = _zone()
        c._cfg[const.CONF_ACTIVE_VALVE_RUNS] = [
            {
                const.RUN_ZONE_ID: 2,
                const.RUN_PLANNED_SECONDS: 600,
                const.RUN_PLANNED_MM: 10.0,
                const.RUN_STARTED: dt_util.utcnow().isoformat(),
                const.RUN_PRE_BUCKET: -20.0,
            }
        ]

        assert await c.async_abort_self_closing_runs(DISABLED) is True
        await hass.async_block_till_done()

        assert _stops(calls) == [{"zone_id": 2, "dauer": 0}]
        assert await c._sc_find_run(2) is None

    async def test_opensprinkler_and_batch_runs_are_left_to_their_own_abort(self, hass):
        c = _coord(hass)
        calls = async_capture_events(hass, EVENT_CALL_SERVICE)
        runs = [
            {const.RUN_ZONE_ID: 5, const.RUN_MODE: const.WATERING_MODE_OPENSPRINKLER},
            {const.RUN_ZONE_ID: 6, const.RUN_MODE: const.WATERING_MODE_BATCH},
        ]
        c._cfg[const.CONF_ACTIVE_VALVE_RUNS] = [dict(r) for r in runs]
        c._chain_release = AsyncMock()

        assert await c.async_abort_self_closing_runs(DISABLED) is False
        await hass.async_block_till_done()

        assert calls == []
        assert c._cfg[const.CONF_ACTIVE_VALVE_RUNS] == runs
        c._chain_release.assert_not_awaited()

    async def test_the_chain_is_released_before_the_first_stop(self, hass):
        """Otherwise the settled stop advances the chain and opens the next zone."""
        c = _coord(hass)
        c.store.config.zone_sequencing = SEQUENTIAL
        c.store.config.zone_sequencing_max_consecutive_duration = 5
        c.store.config.zone_sequencing_min_absorption_time = 0
        calls = async_capture_events(hass, EVENT_CALL_SERVICE)
        first, second = _zone(), _zone(3, confirm=None)
        c._zones[2], c._zones[3] = first, second
        await _set(hass, VALVE, "on")
        await c.async_dispatch_chained_zones(
            [first, second], mode=const.WATERING_MODE_SERVICE, trigger="schedule"
        )
        await hass.async_block_till_done()
        assert _opened(calls) == [2]

        await c.async_abort_self_closing_runs(DISABLED)
        await hass.async_block_till_done()

        assert _opened(calls) == [2]
        assert c._chain_state(const.WATERING_MODE_SERVICE).zones == []

    async def test_without_settling_only_the_stop_goes_out(self, hass):
        c = _coord(hass)
        calls = async_capture_events(hass, EVENT_CALL_SERVICE)
        started = dt_util.utcnow().replace(microsecond=0)
        with freeze_time(started) as frozen:
            await _a_run_halfway(hass, c, frozen)
            stopped = await c.async_abort_self_closing_runs(REMOVED, settle=False)
            await hass.async_block_till_done()

        assert stopped is True
        assert _stops(calls) == [{"zone_id": 2, "dauer": 0}]
        assert await c._sc_find_run(2) is not None  # the store is deleted next
        c._record_run.assert_not_awaited()
        c.async_master_release.assert_not_awaited()
        c.async_teardown_opensprinkler_watchers()  # the run's watcher, still armed

    async def test_a_zone_without_a_stop_service_is_still_settled(self, hass, caplog):
        c = _coord(hass)
        calls = async_capture_events(hass, EVENT_CALL_SERVICE)
        zone = _zone()
        del zone[const.ZONE_STOP_SERVICE]
        started = dt_util.utcnow().replace(microsecond=0)
        with freeze_time(started) as frozen:
            await _a_run_halfway(hass, c, frozen, zone)
            assert await c.async_abort_self_closing_runs(DISABLED) is True
            await hass.async_block_till_done()

        assert _stops(calls) == []
        assert c._record_run.await_args.kwargs["result"] == const.RUN_RESULT_PARTIAL
        assert "without a stop_service" in caplog.text

    async def test_a_stop_that_raises_does_not_stop_the_rest(self, hass, caplog):
        c = _coord(hass)
        c._cfg[const.CONF_ACTIVE_VALVE_RUNS] = [
            {const.RUN_ZONE_ID: 2, const.RUN_MODE: const.WATERING_MODE_SERVICE},
            {const.RUN_ZONE_ID: 4, const.RUN_MODE: const.WATERING_MODE_SERVICE},
        ]
        c.async_stop_self_closing = AsyncMock(side_effect=[RuntimeError("boom"), True])

        assert await c.async_abort_self_closing_runs(DISABLED) is True

        stopped = [ck.args[0] for ck in c.async_stop_self_closing.await_args_list]
        assert stopped == [2, 4]
        assert "could not stop its self-closing run" in caplog.text

    async def test_an_unreadable_store_stops_nothing_and_does_not_raise(
        self, hass, caplog
    ):
        c = _coord(hass)
        c.store.async_get_config = AsyncMock(side_effect=RuntimeError("store gone"))

        assert await c.async_abort_self_closing_runs(DISABLED) is False

        assert "Could not read active runs" in caplog.text

    async def test_nothing_in_flight_stops_nothing(self, hass):
        c = _coord(hass)

        assert await c.async_abort_self_closing_runs(DISABLED) is False
```

- [ ] **Step 2: Rot sehen**

Run: `TZ=UTC … -m pytest "tests/test_self_closing_teardown.py::TestAbortingTheServiceRuns" -p _local_socket_unblock -q`
Expected: `9 failed`, je `AttributeError: 'SmartIrrigationCoordinator' object has no attribute
'async_abort_self_closing_runs'`.

- [ ] **Step 3: Implementieren** — in `self_closing.py` direkt vor
`    def async_teardown_self_closing_handles(self) -> None:` einfügen:

```python
    async def async_abort_self_closing_runs(self, reason: str, *, settle=True) -> bool:
        """Stop every service run this coordinator started, and settle it.

        The service twin of ``async_abort_opensprinkler_runs``, for the cases
        where nothing will ever adopt the run: the entry being disabled or
        removed. Unload cancels the run's backstop, and that backstop was, by
        accident, the one thing still settling a disabled entry's run and
        releasing its master. So the run is settled here, while the coordinator
        still lives: closed through its stop service, its bucket and its usage
        priced on what it watered, its master hold released.

        Deliberately NOT called from a plain reload or a restart. Those are
        adopted by ``async_resume_self_closing_runs``, and cutting the run
        short there would waste water on every options change.

        A service run is what the resume path treats as one: every persisted
        run that is neither OpenSprinkler nor batch, including a record from
        before ``RUN_MODE`` existed. Those two modes have aborts of their own.

        ``settle=False`` only sends the stop, for a removal: the store is
        deleted right after, so the reconciliation would be pointless.

        Returns True if anything was stopped. Never raises: a failure here must
        not be able to block an unload.
        """
        try:
            runs = await self._sc_active_runs()
        except Exception:  # noqa: BLE001
            _LOGGER.exception("Could not read active runs to stop self-closing valves")
            return False

        targets = [
            r
            for r in runs
            if r.get(const.RUN_MODE)
            not in (const.WATERING_MODE_OPENSPRINKLER, const.WATERING_MODE_BATCH)
            and r.get(const.RUN_ZONE_ID) is not None
        ]
        if not targets:
            return False

        # Before any stop, so a settled run cannot advance the chain and
        # dispatch the next zone on the way out.
        await self._chain_release(const.WATERING_MODE_SERVICE, reason)

        stopped = False
        for run in targets:
            zone_id = run.get(const.RUN_ZONE_ID)
            _LOGGER.warning(
                "Zone %s: stopping its self-closing run because %s", zone_id, reason
            )
            try:
                if settle:
                    if await self.async_stop_self_closing(zone_id):
                        stopped = True
                elif await self._sc_dispatch_stop(
                    zone_id, self.store.get_zone(zone_id) or {}
                ):
                    stopped = True
                else:
                    _LOGGER.warning(
                        "Zone %s has no stop_service; its valve runs on to the "
                        "end of its own countdown",
                        zone_id,
                    )
            except Exception:  # noqa: BLE001
                _LOGGER.exception(
                    "Zone %s: could not stop its self-closing run; it may still "
                    "be watering",
                    zone_id,
                )
        return stopped

```

- [ ] **Step 4: Grün sehen** — derselbe Befehl: `9 passed`.

- [ ] **Step 5: Commit**

```bash
git add tests/test_self_closing_teardown.py custom_components/irrigation_plus/self_closing.py
git commit -F - <<'EOF'
feat(self-closing): stop and settle the service runs nothing will adopt

The service twin of async_abort_opensprinkler_runs. For a disable it closes
each run through its stop service and prices bucket and usage on what was
watered; for a removal it only sends the stop. The service chain is released
first, so a settled stop cannot dispatch the next zone on the way out. A
record without a mode is a service run, as the resume path reads it.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
```

---

### Task 8: Deaktivieren und Entfernen verdrahten

**Files:**
- Modify: `custom_components/irrigation_plus/__init__.py:475-481` (Zweig „deaktiviert“ in `async_unload_entry`) und `:508-511` (`async_remove_entry`)
- Test: `tests/test_self_closing_teardown.py`

- [ ] **Step 1: Failing tests anhängen**

```python
# --------------------------------------------------------------------------- #
# The entry paths
# --------------------------------------------------------------------------- #
class TestTheEntryPaths:
    """Which unload stops what, and in which order (mock coordinator)."""

    @staticmethod
    def _coordinator(hass):
        coordinator = AsyncMock()
        hass.data[const.DOMAIN] = {"coordinator": coordinator}
        return coordinator

    async def test_a_reload_stops_nothing(self, hass, mock_config_entry):
        """A pin: green before the change too. The successor adopts the runs."""
        coordinator = self._coordinator(hass)
        panel, forward = _unload_patches(hass)
        with panel, forward:
            assert await async_unload_entry(hass, mock_config_entry) is True

        assert _called(coordinator) == ["async_unload"]

    async def test_disabling_stops_everything_before_the_unload(
        self, hass, mock_config_entry
    ):
        coordinator = self._coordinator(hass)
        mock_config_entry.disabled_by = ConfigEntryDisabler.USER
        panel, forward = _unload_patches(hass)
        with panel, forward:
            assert await async_unload_entry(hass, mock_config_entry) is True

        assert _called(coordinator) == [
            "async_release_all_chains",
            "async_abort_opensprinkler_runs",
            "async_abort_batch_runs",
            "async_abort_self_closing_runs",
            "async_master_end_cycle_now",
            "async_unload",
        ]
        coordinator.async_release_all_chains.assert_awaited_once_with(DISABLED)
        coordinator.async_abort_self_closing_runs.assert_awaited_once_with(DISABLED)

    async def test_removal_stops_without_settling_before_the_delete(
        self, hass, mock_config_entry
    ):
        """The master's configuration lives in the store that is deleted last."""
        coordinator = self._coordinator(hass)
        with (
            patch("custom_components.irrigation_plus.remove_panel"),
            patch(
                "custom_components.irrigation_plus.async_remove_card_resource",
                new=AsyncMock(),
            ),
        ):
            await async_remove_entry(hass, mock_config_entry)

        assert _called(coordinator) == [
            "async_abort_opensprinkler_runs",
            "async_abort_batch_runs",
            "async_abort_self_closing_runs",
            "async_master_end_cycle_now",
            "async_delete_config",
        ]
        coordinator.async_abort_self_closing_runs.assert_awaited_once_with(
            REMOVED, settle=False
        )


class TestDisablingMidRun:
    """The whole disable, through async_unload_entry, on the real hass."""

    async def test_the_run_is_stopped_and_booked_and_the_pump_switched_off(
        self, hass, mock_config_entry
    ):
        """600 s plan, a queued second zone, disabled at 300 s.

        Measured 50 L (10 L/min for 300 s): not the 1 L this host books by
        time, not the 100 L of the plan. The queued zone never opens.
        """
        c = _unloadable(_coord(hass))
        _metered(c)
        _the_real_backstop_from_here(c)
        _real_master(c, hass)
        c.store.config.zone_sequencing = SEQUENTIAL
        c.store.config.zone_sequencing_max_consecutive_duration = 5
        c.store.config.zone_sequencing_min_absorption_time = 0
        hass.data[const.DOMAIN] = {"coordinator": c}
        mock_config_entry.disabled_by = ConfigEntryDisabler.USER
        calls = async_capture_events(hass, EVENT_CALL_SERVICE)
        first, second = _metered_zone(600), _zone(3, confirm=None)
        c._zones[2], c._zones[3] = first, second
        started = dt_util.utcnow().replace(microsecond=0)
        with freeze_time(started) as frozen:
            await _flow(hass, RATE)
            await _set(hass, VALVE, "on")
            await c.async_dispatch_chained_zones(
                [first, second], mode=const.WATERING_MODE_SERVICE, trigger="schedule"
            )
            await hass.async_block_till_done()
            await _walk(hass, frozen, 300)
            panel, forward = _unload_patches(hass)
            with panel, forward:
                assert await async_unload_entry(hass, mock_config_entry) is True
            await hass.async_block_till_done()
            await _walk(hass, frozen, 600)  # past the plan, any grace, any off timer

        assert _stops(calls) == [{"zone_id": 2, "dauer": 0}]
        c._record_run.assert_awaited_once()
        kw = c._record_run.await_args.kwargs
        assert kw["result"] == const.RUN_RESULT_PARTIAL
        assert kw["volume_l"] == pytest.approx(RATE * 300 / 60, abs=0.01)
        assert _opened(calls) == [2]
        assert len(_pump_offs(calls)) == 1
        assert c._sc_meters() == {}
        assert c._sc_cleanup_timers() == {}

    async def test_a_disable_in_an_absorption_pause_switches_the_pump_off(
        self, hass, mock_config_entry
    ):
        """No run in flight, so no abort releases the chain; its hold would stay."""
        c = _unloadable(_chain_coord(hass, ROTATING, slot=1, absorb=10))
        _real_master(c, hass)
        hass.data[const.DOMAIN] = {"coordinator": c}
        mock_config_entry.disabled_by = ConfigEntryDisabler.USER
        calls = async_capture_events(hass, EVENT_CALL_SERVICE)
        await _chain_dispatch(c, _register(c, _chain_zone(1, duration=180)))
        await _finish(c, 1)
        state = c._chain_state(const.WATERING_MODE_SERVICE)
        assert state.absorb is not None and state.token is not None

        panel, forward = _unload_patches(hass)
        with panel, forward:
            assert await async_unload_entry(hass, mock_config_entry) is True
        await hass.async_block_till_done()
        async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=30))
        await hass.async_block_till_done()

        assert state.absorb is None and state.token is None
        assert len(_pump_offs(calls)) == 1
        assert _chain_ids(c) == [1]  # no second slot
```

- [ ] **Step 2: Rot sehen**

Run: `TZ=UTC … -m pytest "tests/test_self_closing_teardown.py::TestTheEntryPaths" "tests/test_self_closing_teardown.py::TestDisablingMidRun" -p _local_socket_unblock -q`
Expected: `4 failed, 1 passed`. Grün ist nur der Pin `test_a_reload_stops_nothing`. Rot: die beiden
Reihenfolge-Tests (`assert ['async_abort...async_unload'] == ['async_relea...async_unload']` bzw. `…elete_config`),
die Szene mitten im Lauf (`assert [] == [{'dauer': 0, 'zone_id': 2}]`: kein Stopp) und die Absorptionspause
(`assert 0 == 1`: die Pumpe wird nicht abgeschaltet).

- [ ] **Step 3: Implementieren** — in `__init__.py`, `async_unload_entry`, ersetze

```python
        if entry.disabled_by is not None:
            await coordinator.async_abort_opensprinkler_runs(
                "the Irrigation Plus config entry is being disabled"
            )
            await coordinator.async_abort_batch_runs(
                "the Irrigation Plus config entry is being disabled"
            )
        await coordinator.async_unload()
```

durch

```python
        if entry.disabled_by is not None:
            why = "the Irrigation Plus config entry is being disabled"
            # Every chain first. One caught in a pause between its runs holds
            # the master with no run in flight for an abort below to find.
            await coordinator.async_release_all_chains(why)
            await coordinator.async_abort_opensprinkler_runs(why)
            await coordinator.async_abort_batch_runs(why)
            # A service run as well: async_unload cancels its backstop, which
            # was what still settled it after a disable and released its master.
            await coordinator.async_abort_self_closing_runs(why)
            # Its off timer goes with the unload, so the cycle ends here.
            await coordinator.async_master_end_cycle_now()
        await coordinator.async_unload()
```

und in `async_remove_entry` ersetze

```python
            await coordinator.async_abort_batch_runs(
                "the Irrigation Plus config entry is being removed", settle=False
            )
            await coordinator.async_delete_config()
```

durch

```python
            await coordinator.async_abort_batch_runs(
                "the Irrigation Plus config entry is being removed", settle=False
            )
            await coordinator.async_abort_self_closing_runs(
                "the Irrigation Plus config entry is being removed", settle=False
            )
            # Before the delete: the master's configuration lives in the store.
            await coordinator.async_master_end_cycle_now()
            await coordinator.async_delete_config()
```

- [ ] **Step 4: Grün sehen** — derselbe Befehl: `5 passed`; dann die ganze neue Datei: `33 passed`; dazu
`tests/test_opensprinkler_teardown.py` und `tests/test_init.py` ohne neue rote Namen gegenüber der Baseline.

- [ ] **Step 5: Commit**

```bash
git add tests/test_self_closing_teardown.py custom_components/irrigation_plus/__init__.py
git commit -F - <<'EOF'
fix(unload): a disable stops what the integration started, a removal too

The unload now cancels a self-closing run's backstop, and that backstop was
what still settled a disabled entry's run and released its master. A disable
therefore releases every chain, aborts the service runs as it already did the
OpenSprinkler and batch ones, and ends the master cycle before unloading. A
removal sends the service stops without settling and ends the master before
the store, which holds its configuration, is deleted. A reload is unchanged:
the successor adopts the runs.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
```

---

### Task 9: Doku

**Files:**
- Modify: `docs/configuration-my-zones.md:91`

- [ ] **Step 1: Satz ergänzen** — ersetze

```markdown
  - **Stop service** *(optional)* — closes the valve if you stop a run early (while HA is up).
```

durch

```markdown
  - **Stop service** *(optional)* — closes the valve if you stop a run early (while HA is up), and when the integration is disabled or removed in the middle of a run. Without one, the valve waters on to the end of its own countdown.
```

- [ ] **Step 2: Commit**

```bash
git add docs/configuration-my-zones.md
git commit -F - <<'EOF'
docs(zones): the stop service also closes a run on disable and removal

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
```

---

### Task 10: Lint, volle Suite, Mutationen, Review, Stand

**Files:** keine neuen.

- [ ] **Step 1: Lint** (CLAUDE.md, verbatim; dazu black auf die neue Testdatei, damit sie zum Rest passt)

```bash
uvx black custom_components/irrigation_plus/
uvx ruff check custom_components/irrigation_plus/
uvx black --check tests/test_self_closing_teardown.py
git status --short
```

Expected: `All checks passed!`, black ohne Änderung (die Snippets dieses Plans sind black-formatiert).

- [ ] **Step 2: Volle Suite, Namensvergleich gegen die Baseline aus Task 0**

```bash
TZ=UTC /d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests -p _local_socket_unblock -q --no-header -rfE > ../suite-after.txt 2>&1
tr '\r' '\n' < ../suite-after.txt | grep -E "^(FAILED|ERROR) tests" | sed -E 's/ - .*//' | sort > ../names-after.txt
diff ../names-baseline.txt ../names-after.txt && echo "identical"
tail -c 300 ../suite-after.txt
```

Expected: `identical`; `passed` um genau 33 höher als in der Baseline.

- [ ] **Step 3: Mutationsmatrix** — mit dem Skript aus dem Probelauf (`D:\Entwicklung\HASI\issue9-work\probe_mutate.py`, aus
dem Worktree-Wurzelverzeichnis: `python ../probe_mutate.py`). Jede Mutation ersetzt einen Anker, der genau einmal
vorkommen muss, lässt `tests/test_self_closing_teardown.py` laufen, notiert die roten Tests und stellt die Datei
wieder her (Zeitgrenze 600 s, bei Hang `taskkill /T`). Jede Mutation muss mindestens einen Test rot machen; ein
Überlebender heißt zuerst: Test zu schwach (Memory `mutation-survivor-suspects-the-test`).

| # | Mutation | Rot im Probelauf (Killer) |
|---|---|---|
| 1 | `async_unload` ruft den Abbau nicht | beide Tests in `TestAReloadMidRun` |
| 2 | Abbau kündigt nur die Abtaster | `test_both_timers_are_cancelled_and_both_tables_emptied`, beide `TestAReloadMidRun` |
| 3 | Abbau kündigt nur die Backstops | `test_both_timers_…`, `test_the_run_is_booked_once_by_the_new_coordinator` |
| 4 | Abbau finalisiert den Zähler (`_sc_finish_flow` statt Kündigen) | `test_nothing_is_read_settled_or_written`, `test_both_timers_…` |
| 5 | `_master_release_all` lässt den Aus-Timer stehen | `test_release_all_cancels_a_pending_off` |
| 6 | Abbruch gibt die Service-Kette nicht vor dem ersten Stopp frei | `test_the_chain_is_released_before_the_first_stop` |
| 7 | Deaktivieren gibt die Ketten nicht frei | `test_a_disable_in_an_absorption_pause_switches_the_pump_off`, `test_disabling_stops_everything_before_the_unload` |
| 8 | Abbruch filtert `== WATERING_MODE_SERVICE` | `test_a_record_without_a_mode_is_a_service_run` |
| 9 | auch ein Neuladen bricht ab | `test_a_reload_stops_nothing` (der Pin), `test_disabling_…` |
| 10 | `settle=False` bucht trotzdem | `test_without_settling_only_the_stop_goes_out` |
| 11 | Master-Ende übergeht einen übrigen Hold | `test_a_hold_still_taken_leaves_the_cycle_to_its_owner` |
| 12 | Master-Ende übergeht `_master_on` | `test_a_master_we_did_not_switch_on_is_left_alone` |
| 13 | Master-Ende übergeht `master_off_after` | `test_a_stay_on_pump_is_left_on` |
| 14 | Entfernen beendet den Master erst nach `async_delete_config` | `test_removal_stops_without_settling_before_the_delete` |
| 15 | Master-Ende lässt eine Ausnahme durch | `test_a_switch_that_raises_does_not_block_the_unload` |
| 16 | Abbruch lässt die Ausnahme eines Laufs durch | `test_a_stop_that_raises_does_not_stop_the_rest` |
| 17 | Ketten-Freigabe lässt die Ausnahme einer Kette durch | `test_one_chain_that_raises_does_not_stop_the_others` |
| 18 | Deaktivieren bricht die Service-Läufe nicht ab | `test_the_run_is_stopped_and_booked_and_the_pump_switched_off`, `test_disabling_…` |
| 19 | Deaktivieren beendet den Master nicht | beide `TestDisablingMidRun`, `test_disabling_…` |
| 20 | `_chain_release` ignoriert `why` | `test_a_rotation_absorbing_between_slots_hands_back_its_hold` |
| 21 | Stopp-Befehl ignoriert das Dauer-Feld der Zone | 5 Tests, u. a. `test_the_stop_service_gets_a_zero_duration_under_its_field` |

Probelauf: 21/21 getötet. Hat ein Lauf **keine Tests gesammelt** oder hängt er (`HANG`), ist das kein Verdikt.

- [ ] **Step 4: Greps vor jedem Push** (Memory `no-own-issue-refs-upstream`)

```bash
git diff upstream/master..HEAD -- custom_components/ tests/ docs/ | grep "^+" | grep -nE "Eifel-Joe|spec D[0-9]|spec §|Task [0-9]|M[0-9][a-z]?:|PR [A-T]\b"
git log upstream/master..HEAD --format='%H%n%B' | grep -n "Eifel-Joe#"
```

Expected: beides leer.

- [ ] **Step 5: Review** — `superpowers:requesting-code-review` über den Diff `upstream/master..HEAD` mit Spec und
diesem Plan; Rückmeldungen über `superpowers:receiving-code-review` prüfen.

- [ ] **Step 6: Stand festhalten** — `docs/SESSION-STAND.md` ergänzen, Häkchen in diesem Plan setzen. **Nicht pushen,
keinen PR öffnen**, bevor der PR-Text freigegeben ist (deutsch, dann englisch). Danach Live-Test auf HA-Test nach
dem Ende-zu-Ende-Kriterium der Spec (Pre-Release, RED-Seite vorher auf dem installierten Stand). Alles Weitere —
PR, P2 auf Eifel-Joe#9 und #42, production, die neuen Issues, P1-Archiv — steht in der Spec unter *Lieferung*.

---

## Selbstprüfung gegen die Spec

| Spec-Anforderung | Task |
|---|---|
| 1 Nach jedem Entladen feuert kein Abtaster, kein Backstop, kein anstehender Master-Aus-Timer; nichts gelesen oder geschrieben | 1, 2, 3 |
| 2 Neuladen: Läufe bleiben stehen, genau eine Buchung durch den neuen Koordinator | 2, 8 (Pin) |
| 3 Deaktivieren: Service-Läufe (auch ohne Modus) stoppen und buchen, keine Kette startet etwas, Ketten-Holds gelöst, Master aus unter den vier Bedingungen | 4, 5, 7, 8 |
| 4 Entfernen: Stopp ohne Buchung, Master wie 3, beides vor dem Löschen | 6, 7, 8 |
| 5 Nichts blockiert ein Entladen oder Entfernen | 4, 5, 7 (je ein Test mit werfendem Schritt) |
| 6 Neustart und echtes Herunterfahren unverändert | kein Code daran; `tests/test_opensprinkler_teardown.py::TestShutdown` unverändert |
| 7 `master_off_after = false`: Master bleibt | 4 |
| Doku Stop service | 9 |
| Schwester: Master-Aus-Timer | 3 |
