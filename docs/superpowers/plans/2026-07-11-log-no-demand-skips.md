# Log "no demand" skips in the run history — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** When the user opts in, a scheduled run that does not water a zone / distributor member purely because it has no water demand leaves one `skipped` run-history entry with reason `no_demand`, instead of vanishing silently.

**Architecture:** New opt-in `Config.log_no_demand` flag (default off). A shared coordinator helper `_record_no_demand_skips(zone_ids)` writes one `skipped`/`no_demand` run-log entry per zone, gated on the flag, suppressed under rain-delay, de-duplicated to one entry per zone per calendar day. Wired into the normal-zone scheduler path (`_irrigate_linked_entities`) and the distributor cycle. Frontend gets a Setup toggle + the localized reason label in 8 languages.

**Tech Stack:** Python (attrs/Home Assistant coordinator), Lit/TypeScript frontend, pytest + vitest. Reference spec: `docs/superpowers/specs/2026-07-11-log-no-demand-skips-design.md`.

**Dev branch:** `local/log-no-demand` (already checked out; carries the spec commit). Production stays clean until the final delivery task.

---

## File Structure

**Backend**
- `custom_components/smart_irrigation/const.py` — new constants `CONF_LOG_NO_DEMAND`, `CONF_DEFAULT_LOG_NO_DEMAND`, `SKIP_REASON_NO_DEMAND`.
- `custom_components/smart_irrigation/store.py` — `Config.log_no_demand` attr field + load default.
- `custom_components/smart_irrigation/websockets.py` — accept `log_no_demand` in the config-update schema.
- `custom_components/smart_irrigation/irrigation.py` — the shared `_record_no_demand_skips` helper + normal-zone wiring.
- `custom_components/smart_irrigation/distributor.py` — `_dist_no_demand_members` helper + cycle wiring.

**Frontend**
- `frontend/src/const.ts` — `CONF_LOG_NO_DEMAND` constant.
- `frontend/src/types.ts` — `log_no_demand: boolean` on the config type + default.
- `frontend/src/views/general/view-general.ts` — the Setup toggle (new card).
- `frontend/localize/languages/{en,de,es,fr,it,nl,no,sk}.json` — reason label `panels.zones.outlook.checks.no_demand` + toggle card strings.

**Tests**
- `tests/test_no_demand_logging.py` — new: helper, normal-zone wiring, dedup, gating, distributor member set.

**Version / build (delivery task only)**
- `const.py` VERSION, `frontend/package.json`, `manifest.json`, rebuilt `frontend/dist/*`.

---

## Task 1: Config flag `log_no_demand` (backend plumbing)

**Files:**
- Modify: `custom_components/smart_irrigation/const.py` (after line 82; near line 107)
- Modify: `custom_components/smart_irrigation/store.py` (const import block; after line 316; after line 686)
- Modify: `custom_components/smart_irrigation/websockets.py` (after line 117)
- Test: `tests/test_no_demand_logging.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_no_demand_logging.py`:

```python
"""No-demand run-log transparency (opt-in).

When ``Config.log_no_demand`` is on, a scheduled run that skips a zone/member
purely because it has no water demand records one ``skipped`` / ``no_demand``
run-log entry (deduped per zone per calendar day, suppressed under rain delay).
Coordinators are built with ``__new__`` like the other runner tests.
"""

import attr
import homeassistant.util.dt as dt_util
from types import SimpleNamespace
from unittest.mock import Mock

from homeassistant.util.unit_system import METRIC_SYSTEM

from custom_components.smart_irrigation import SmartIrrigationCoordinator, const
from custom_components.smart_irrigation.store import Config


def test_config_defaults_log_no_demand_off():
    assert const.CONF_DEFAULT_LOG_NO_DEMAND is False
    field = attr.fields_dict(Config)["log_no_demand"]
    assert field.default == const.CONF_DEFAULT_LOG_NO_DEMAND
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_no_demand_logging.py::test_config_defaults_log_no_demand_off -v`
Expected: FAIL — `KeyError: 'log_no_demand'` (field not defined yet).

- [ ] **Step 3: Add the constants**

In `const.py`, after line 82 (`CONF_DEFAULT_DISTRIBUTORS_ENABLED = False`):

```python
# Opt-in run-history transparency (2026-07-11): when on, a scheduled run that
# does NOT water a zone/member purely because it has no water demand (bucket
# satisfied / duration 0) leaves one "skipped: no_demand" run-log entry instead
# of vanishing silently. Default off so existing installs stay byte-identical.
CONF_LOG_NO_DEMAND = "log_no_demand"
CONF_DEFAULT_LOG_NO_DEMAND = False
```

In `const.py`, directly after `SKIP_REASON_SOIL_MOISTURE = "soil_moisture"` (line 107):

```python
# No-demand skip (opt-in, CONF_LOG_NO_DEMAND): the zone/member simply had no
# deficit this run. Localized in the run-log via panels.zones.outlook.checks.
SKIP_REASON_NO_DEMAND = "no_demand"
```

- [ ] **Step 4: Add the Config field + load default**

In `store.py` const import block, add `CONF_DEFAULT_LOG_NO_DEMAND` and `CONF_LOG_NO_DEMAND` (isort will place them; keep alphabetical near `CONF_DISTRIBUTORS_ENABLED`).

After line 316 (`distributors_enabled = attr.ib(...)`):

```python
    log_no_demand = attr.ib(type=bool, default=CONF_DEFAULT_LOG_NO_DEMAND)
```

In `async_load`, after the `distributors_enabled=data["config"].get(...)` block (ends line 686):

```python
                log_no_demand=data["config"].get(
                    CONF_LOG_NO_DEMAND,
                    CONF_DEFAULT_LOG_NO_DEMAND,
                ),
```

(No `STORAGE_VERSION` bump / migration needed — the load path defaults missing
keys, exactly as `distributors_enabled` does. `async_update_config` already
filters to valid attr fields, so CRUD needs no change.)

- [ ] **Step 5: Accept the key in the websocket schema**

In `websockets.py`, after line 117 (`vol.Optional(const.CONF_DISTRIBUTORS_ENABLED): cv.boolean,`):

```python
                vol.Optional(const.CONF_LOG_NO_DEMAND): cv.boolean,
```

- [ ] **Step 6: Run test to verify it passes**

Run: `python -m pytest tests/test_no_demand_logging.py::test_config_defaults_log_no_demand_off -v`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add custom_components/smart_irrigation/const.py custom_components/smart_irrigation/store.py custom_components/smart_irrigation/websockets.py tests/test_no_demand_logging.py
git commit -m "feat(store): add opt-in log_no_demand config flag"
```

---

## Task 2: Shared `_record_no_demand_skips` helper

**Files:**
- Modify: `custom_components/smart_irrigation/irrigation.py` (after `_record_skipped_run`, ~line 1402)
- Test: `tests/test_no_demand_logging.py`

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_no_demand_logging.py` a fake store + coord (mirrors `test_rain_delay.py`) and helper tests:

```python
class _FakeStore:
    def __init__(self, zones=None, config=None):
        self.zones = {int(z[const.ZONE_ID]): dict(z) for z in (zones or [])}
        self.config = config

    def get_zone(self, zone_id):
        z = self.zones.get(int(zone_id))
        return dict(z) if z is not None else None

    async def async_update_zone(self, zone_id, changes):
        self.zones.setdefault(int(zone_id), {const.ZONE_ID: int(zone_id)}).update(changes)
        return dict(self.zones[int(zone_id)])

    async def async_get_zones(self):
        return [dict(z) for z in self.zones.values()]


def _cfg(**over):
    base = dict(
        rain_delay_until=None,
        zone_sequencing=const.CONF_ZONE_SEQUENCING_PARALLEL,
        live_estimate_enabled=False,
        log_no_demand=True,
    )
    base.update(over)
    return SimpleNamespace(**base)


def _coord(monkeypatch, zones=None, config=None, units=METRIC_SYSTEM):
    monkeypatch.setattr(
        "custom_components.smart_irrigation.irrigation.async_dispatcher_send", Mock()
    )
    coord = SmartIrrigationCoordinator.__new__(SmartIrrigationCoordinator)
    hass = Mock()
    hass.config = Mock()
    hass.config.units = units
    coord.hass = hass
    coord.store = _FakeStore(zones, config or _cfg())
    return coord


def _zone(**over):
    z = {const.ZONE_ID: 1, const.ZONE_RUN_LOG: []}
    z.update(over)
    return z


async def test_helper_records_when_enabled(monkeypatch):
    coord = _coord(monkeypatch, [_zone()])
    await coord._record_no_demand_skips([1])
    log = coord.store.zones[1][const.ZONE_RUN_LOG]
    assert len(log) == 1
    assert log[0]["result"] == const.RUN_RESULT_SKIPPED
    assert log[0]["detail"] == const.SKIP_REASON_NO_DEMAND
    assert log[0]["volume_l"] == 0.0


async def test_helper_noop_when_disabled(monkeypatch):
    coord = _coord(monkeypatch, [_zone()], config=_cfg(log_no_demand=False))
    await coord._record_no_demand_skips([1])
    assert coord.store.zones[1][const.ZONE_RUN_LOG] == []


async def test_helper_suppressed_under_rain_delay(monkeypatch):
    future = (dt_util.now() + dt_util.dt.timedelta(hours=2)).isoformat()
    coord = _coord(monkeypatch, [_zone()], config=_cfg(rain_delay_until=future))
    await coord._record_no_demand_skips([1])
    assert coord.store.zones[1][const.ZONE_RUN_LOG] == []


async def test_helper_dedups_same_day(monkeypatch):
    today_entry = {
        "ts": dt_util.now().isoformat(),
        "result": const.RUN_RESULT_SKIPPED,
        "detail": const.SKIP_REASON_NO_DEMAND,
        "volume_l": 0.0,
    }
    coord = _coord(monkeypatch, [_zone(run_log=[today_entry])])
    await coord._record_no_demand_skips([1])
    assert len(coord.store.zones[1][const.ZONE_RUN_LOG]) == 1  # unchanged
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_no_demand_logging.py -k helper -v`
Expected: FAIL — `AttributeError: ... has no attribute '_record_no_demand_skips'`.

- [ ] **Step 3: Implement the helper**

In `irrigation.py`, immediately after `_record_skipped_run` (ends ~line 1402):

```python
    async def _record_no_demand_skips(self, zone_ids) -> None:
        """Record a per-zone "no demand" skip in the run history, if opted in.

        Opt-in via ``config.log_no_demand`` (default off, so existing installs
        are byte-identical). Suppressed while a rain delay is active — that path
        already logs ``paused`` for the targeted zones and would otherwise
        double-log. De-duplicated to at most one ``no_demand`` entry per zone per
        calendar day, so multiple schedules in a day do not spam the run log.

        ``add_to_total=False`` — a skip delivers no water.
        siehe test_no_demand_logging.py::test_helper_records_when_enabled et al.
        """
        if not getattr(self.store.config, "log_no_demand", False):
            return
        if self._rain_delay_active():
            return
        today = dt_util.now().date().isoformat()
        for zid in zone_ids:
            zone = self.store.get_zone(int(zid)) or {}
            log = zone.get(const.ZONE_RUN_LOG) or []
            if log:
                last = log[0]
                if (
                    last.get("result") == const.RUN_RESULT_SKIPPED
                    and last.get("detail") == const.SKIP_REASON_NO_DEMAND
                    and str(last.get("ts") or "")[:10] == today
                ):
                    continue
            await self._record_run(
                int(zid),
                result=const.RUN_RESULT_SKIPPED,
                detail=const.SKIP_REASON_NO_DEMAND,
                trigger="schedule",
                add_to_total=False,
            )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_no_demand_logging.py -k helper -v`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add custom_components/smart_irrigation/irrigation.py tests/test_no_demand_logging.py
git commit -m "feat(runner): _record_no_demand_skips helper (opt-in, deduped)"
```

---

## Task 3: Normal-zone wiring in `_irrigate_linked_entities`

**Files:**
- Modify: `custom_components/smart_irrigation/irrigation.py` (lines 452-504)
- Test: `tests/test_no_demand_logging.py`

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_no_demand_logging.py`:

```python
def _linked_zone(**over):
    z = {
        const.ZONE_ID: 1,
        const.ZONE_NAME: "Lawn",
        const.ZONE_LINKED_ENTITY: "switch.valve",
        const.ZONE_STATE: const.ZONE_STATE_AUTOMATIC,
        const.ZONE_DURATION: 0,          # no demand
        const.ZONE_BUCKET: 0.0,
        const.ZONE_BUCKET_THRESHOLD: 0.0,  # 0 < 0 is False -> not due
        const.ZONE_RUN_LOG: [],
    }
    z.update(over)
    return z


async def test_no_demand_zone_logged_via_scheduler(monkeypatch):
    coord = _coord(monkeypatch, [_linked_zone()])
    await coord._irrigate_linked_entities()
    log = coord.store.zones[1][const.ZONE_RUN_LOG]
    assert [e["detail"] for e in log] == [const.SKIP_REASON_NO_DEMAND]


async def test_no_demand_zone_not_logged_when_disabled(monkeypatch):
    coord = _coord(monkeypatch, [_linked_zone()], config=_cfg(log_no_demand=False))
    await coord._irrigate_linked_entities()
    assert coord.store.zones[1][const.ZONE_RUN_LOG] == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_no_demand_logging.py -k scheduler_or_disabled -v` (use `-k "scheduler or disabled"`)
Expected: FAIL — no `no_demand` entry written (the zone is silently dropped today).

- [ ] **Step 3: Split the candidate filter + add the classic call site**

In `irrigation.py`, replace the single `zones_to_irrigate = [...]` comprehension (lines 452-474) with a split that first materializes the targeted-eligible set, then applies the demand gate (behavior for `zones_to_irrigate` is byte-identical):

```python
        # Targeted + automatic-eligible zones this scheduled run is responsible
        # for, BEFORE the demand gate. Splitting the old single comprehension in
        # two lets the no-demand transparency log (below) name exactly the zones
        # that were evaluated but had no deficit. Same predicate as before, minus
        # the demand clause; distributor members are excluded (own cycle drives).
        targeted_eligible = [
            z
            for z in zones
            if z.get(const.ZONE_DISTRIBUTOR_ID) is None
            and (z.get(const.ZONE_LINKED_ENTITY) or self._sc_is_self_closing(z))
            and z.get(const.ZONE_STATE) != const.ZONE_STATE_DISABLED
            and (target is None or int(z.get(const.ZONE_ID)) in target)
        ]
        zones_to_irrigate = [
            z
            for z in targeted_eligible
            if live_gate
            or (
                (z.get(const.ZONE_DURATION) or 0) > 0
                and (z.get(const.ZONE_BUCKET) or 0)
                < (z.get(const.ZONE_BUCKET_THRESHOLD) or 0)
            )
        ]

        # Opt-in transparency (classic gate): every targeted-eligible zone that
        # is NOT due had no demand. Log it here — BEFORE the "nothing due" return
        # — so the satisfied-bucket case leaves a trace. The helper is gated on
        # config + rain-delay + same-day dedup, so paused runs never double-log.
        # Under live_gate the demand decision is deferred to _apply_live_durations,
        # so that set is logged there instead (see below).
        if not live_gate:
            _watered_ids = {int(z.get(const.ZONE_ID)) for z in zones_to_irrigate}
            await self._record_no_demand_skips(
                [
                    int(z.get(const.ZONE_ID))
                    for z in targeted_eligible
                    if int(z.get(const.ZONE_ID)) not in _watered_ids
                ]
            )
```

- [ ] **Step 4: Add the live-estimate call site**

In `irrigation.py`, immediately after `zones_to_irrigate = await self._apply_live_durations(zones_to_irrigate)` (line 501) and BEFORE its `if not zones_to_irrigate:` guard:

```python
        # Opt-in transparency (live-estimate gate): the zones the live estimate
        # dropped for no live deficit. Exclude soil-vetoed zones (they already
        # logged soil_moisture at _apply_soil_moisture_veto above).
        if live_gate:
            _vetoed_ids = set(self.get_zone_skips().keys())
            _watered_ids = {int(z.get(const.ZONE_ID)) for z in zones_to_irrigate}
            await self._record_no_demand_skips(
                [
                    int(z.get(const.ZONE_ID))
                    for z in targeted_eligible
                    if int(z.get(const.ZONE_ID)) not in _watered_ids
                    and int(z.get(const.ZONE_ID)) not in _vetoed_ids
                ]
            )
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m pytest tests/test_no_demand_logging.py -v`
Expected: PASS (all Task 1-3 tests).

- [ ] **Step 6: Full runner regression (no behavior drift)**

Run: `python -m pytest tests/test_rain_delay.py tests/test_soil_moisture_veto.py tests/test_run_history.py tests/test_run_zone.py -v`
Expected: PASS — the filter split must not change existing watering/skip behavior.

- [ ] **Step 7: Commit**

```bash
git add custom_components/smart_irrigation/irrigation.py tests/test_no_demand_logging.py
git commit -m "feat(runner): log no-demand zone skips on the scheduled path"
```

---

## Task 4: Distributor member wiring

**Files:**
- Modify: `custom_components/smart_irrigation/distributor.py` (scheduled cycle branch, ~lines 913-923)
- Test: `tests/test_no_demand_logging.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_no_demand_logging.py`:

```python
def _member(zid, duration):
    return {
        const.ZONE_ID: zid,
        const.ZONE_STATE: const.ZONE_STATE_AUTOMATIC,
        const.ZONE_DURATION: duration,
        const.ZONE_RUN_LOG: [],
    }


def test_dist_no_demand_members_selects_non_due(monkeypatch):
    coord = _coord(monkeypatch)
    members = [_member(1, 300), _member(2, 0), _member(3, 0)]  # 1 due, 2 & 3 not
    ids = coord._dist_no_demand_members(members, None)
    assert sorted(ids) == [2, 3]


def test_dist_no_demand_members_respects_allow(monkeypatch):
    coord = _coord(monkeypatch)
    members = [_member(1, 300), _member(2, 0), _member(3, 0)]
    ids = coord._dist_no_demand_members(members, {2})
    assert ids == [2]  # 3 is non-due but not in this cycle's target
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_no_demand_logging.py -k dist_no_demand -v`
Expected: FAIL — `AttributeError: ... '_dist_no_demand_members'`.

- [ ] **Step 3: Add the member helper**

In `distributor.py`, near `_dist_needs_water` (~line 588), add:

```python
    def _dist_no_demand_members(self, members, allow):
        """Member ids this cycle evaluates but will not water for lack of demand.

        ``allow`` is the cycle's target subset (``None`` = the whole ring). A
        member with no demand (``_dist_needs_water`` False) never enters the
        soil-veto path, so this is the no_demand set — mirror of the normal-zone
        targeted-eligible-minus-due set in _irrigate_linked_entities.
        siehe test_no_demand_logging.py::test_dist_no_demand_members_selects_non_due
        """
        return [
            int(m.get(const.ZONE_ID))
            for m in members
            if (allow is None or int(m.get(const.ZONE_ID)) in allow)
            and not self._dist_needs_water(m)
        ]
```

- [ ] **Step 4: Wire it into the scheduled cycle branch**

In `distributor.py`, in the scheduled (`else`) branch, right after `allow = None if only_zone_ids is None else {int(z) for z in only_zone_ids}` (line 913) and BEFORE `candidates = [...]`:

```python
            # Opt-in transparency: log the members this cycle evaluates but will
            # not water for lack of demand — before the empty-`to_water` return
            # below, so a fully-satisfied ring still leaves a trace. Scheduled
            # branch only (test-run / manual force are not demand evaluations);
            # rain delay already returned above.
            await self._record_no_demand_skips(
                self._dist_no_demand_members(members, allow)
            )
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m pytest tests/test_no_demand_logging.py -v`
Expected: PASS (all tests).

- [ ] **Step 6: Distributor regression**

Run: `python -m pytest tests/test_distributor_cycle.py tests/test_distributor_dispatch.py tests/test_scheduler_distributor.py -v`
Expected: PASS — the added call must not change cycle behavior (helper is gated off by default in those fixtures).

- [ ] **Step 7: Commit**

```bash
git add custom_components/smart_irrigation/distributor.py tests/test_no_demand_logging.py
git commit -m "feat(distributor): log no-demand member skips per cycle"
```

---

## Task 5: Reason label i18n + Setup toggle (frontend)

**Files:**
- Modify: `frontend/src/const.ts` (after line 45)
- Modify: `frontend/src/types.ts` (after line 90; after line 136)
- Modify: `frontend/src/views/general/view-general.ts` (new card + render call)
- Modify: `frontend/localize/languages/{en,de,es,fr,it,nl,no,sk}.json`

- [ ] **Step 1: Frontend constant + type**

`const.ts`, after line 45 (`export const CONF_DISTRIBUTORS_ENABLED = ...`):

```typescript
export const CONF_LOG_NO_DEMAND = "log_no_demand";
```

`types.ts`, after line 90 (`distributors_enabled: boolean;`):

```typescript
  log_no_demand: boolean;
```

`types.ts`, after line 136 (`this.distributors_enabled = false;`):

```typescript
    this.log_no_demand = false;
```

- [ ] **Step 2: Reason label in all 8 languages**

In each `frontend/localize/languages/<lang>.json`, add a `no_demand` key to the `panels.zones.outlook.checks` object (alongside `soil_moisture`). Translations:

- en: `"no_demand": "No water demand"`
- de: `"no_demand": "Kein Bedarf"`
- es: `"no_demand": "Sin necesidad de riego"`
- fr: `"no_demand": "Aucun besoin d'eau"`
- it: `"no_demand": "Nessun fabbisogno idrico"`
- nl: `"no_demand": "Geen waterbehoefte"`
- no: `"no_demand": "Ingen vannbehov"`
- sk: `"no_demand": "Žiadna potreba zálievky"`

- [ ] **Step 3: Toggle card strings in all 8 languages**

In each `<lang>.json`, add a card under `panels.general.cards` (alongside `automatic-duration-calculation`):

```json
"run-history-logging": {
  "header": "<Run history logging>",
  "description": "<When on, a scheduled run that skips a zone because it currently has no water demand is recorded in that zone's history. Off by default; existing history is unaffected.>",
  "labels": {
    "log-no-demand": "<Log 'no demand' skips in the run history>"
  }
}
```

en header "Run history logging" / label "Log \"no demand\" skips in the run history"; de header "Verlaufs-Protokollierung" / description "Wenn aktiv, wird ein geplanter Lauf, der eine Zone mangels Bedarf überspringt, im Verlauf der Zone protokolliert. Standardmäßig aus; bestehender Verlauf bleibt unberührt." / label "„Kein Bedarf"-Übersprünge im Verlauf protokollieren". Translate the other 6 in the same register as their neighbouring card strings.

- [ ] **Step 4: Render the toggle card**

In `view-general.ts`, add a `_renderRunHistoryLoggingCard()` method mirroring `_renderAutoUpdateCard` (ha-card header + one `setting-row` with an `ha-switch`), and invoke it from the same place the other general cards render:

```typescript
  private _renderRunHistoryLoggingCard(): TemplateResult {
    if (!this.hass || !this.config) return html``;
    return html`
      <ha-card
        header="${localize(
          "panels.general.cards.run-history-logging.header",
          this.hass.language,
        )}"
      >
        <div class="card-content description-text">
          ${localize(
            "panels.general.cards.run-history-logging.description",
            this.hass.language,
          )}
        </div>
        <div class="card-content">
          <div class="setting-row">
            <label>
              ${localize(
                "panels.general.cards.run-history-logging.labels.log-no-demand",
                this.hass.language,
              )}
            </label>
            <ha-switch
              .checked="${this.config.log_no_demand}"
              @change="${(e: Event) =>
                this.handleConfigChange({
                  log_no_demand: (e.target as HTMLInputElement).checked,
                })}"
            ></ha-switch>
          </div>
        </div>
      </ha-card>
    `;
  }
```

Add `${this._renderRunHistoryLoggingCard()}` to `render()` next to the other card calls (e.g. after the automatic-calculation card).

- [ ] **Step 5: Lint + typecheck**

Run (in `frontend/`): `npm run lint`
Expected: no errors (config typed, localize keys are strings).

- [ ] **Step 6: Commit** (dist rebuilt in Task 6)

```bash
git add custom_components/smart_irrigation/frontend/src custom_components/smart_irrigation/frontend/localize
git commit -m "feat(frontend): no_demand reason label + run-history logging toggle (8 langs)"
```

> **Note (no silent gap):** `view-general.ts` has no existing unit-test harness (its other toggles — `autoupdateenabled`, `skip_on_temp_enabled` — are untested too), and there is no run-history render test in `views/zones`. This task therefore ships without new frontend unit tests; the reason label + toggle are verified by the build (Task 6) and the live test (Task 7). The behavior itself is fully covered by the backend tests.

---

## Task 6: Regression, review, sister-path check, build

- [ ] **Step 1: Full backend suite**

Run: `python -m pytest tests/ -q`
Expected: PASS, no regressions.

- [ ] **Step 2: black + ruff (match JustChr CI exactly)**

Run: `black custom_components/smart_irrigation/` then `ruff check custom_components/smart_irrigation/`
Expected: "All done" / no findings. (CI runs latest black + `ruff check`; run them to avoid the I001/format surprises seen on PR #54.)

- [ ] **Step 3: Frontend build (regenerate dist)**

Run (in `frontend/`): `npm test` then `npm run build`
Expected: vitest green; `dist/*` rebuilt.

- [ ] **Step 4: REGEL-8 sister-path check**

Re-read `_irrigate_linked_entities` and the distributor cycle end-to-end. Confirm:
- every early-return that represents "evaluated, not watered" is covered (classic nothing-due return; live all-satisfied return; distributor empty-`to_water` return);
- no path can emit BOTH `no_demand` and `paused`/`soil_moisture` for the same zone/run;
- manual (`force_water`) and `test_run` distributor paths do NOT log no_demand.
Document findings inline (comments already added) or fix.

- [ ] **Step 5: Code review**

Dispatch the `superpowers:code-reviewer` subagent over the diff `production..local/log-no-demand` (feature commits only). Address findings.

- [ ] **Step 6: Commit the rebuilt dist**

```bash
git add -f custom_components/smart_irrigation/frontend/dist
git commit -m "build(frontend): rebuild dist with no-demand logging"
```

---

## Task 7: Delivery (production merge + PR branch prepared, NOT opened)

> Gated on user approval per REGEL 5 (release text) and the standing HA-restart rule. HACS pulls the README/release from the installed version, so this must be a real release on the Eifel-Joe fork to reach production.

- [ ] **Step 1: Live test on HA-Test first**
Build the release zip / point HA-Test at the branch, enable the toggle, run a scheduled evaluation with a satisfied zone, confirm one `no_demand` row appears in that zone's history and none when the toggle is off. (HA-Test restart only — never Prod without approval.)

- [ ] **Step 2: Merge into production + version bump**
`git checkout production && git merge --no-ff local/log-no-demand` (feature commits only — the `docs/superpowers` spec/plan are excluded from production; they live on the dev branch and get archived per the standing archive-branch rule). Bump `const.py` VERSION, `frontend/package.json`, `manifest.json` to the next version (v2026.07.13). Rebuild dist. Show the release notes to the user for approval, then create the release.

- [ ] **Step 3: Prepare the clean upstream PR branch (do NOT open the PR)**
From `upstream/master`, create `feature/log-no-demand-skips`, cherry-pick/apply ONLY the feature commits (no branding, no version bump, no `docs/superpowers`), rebuild dist, push to `origin` (Eifel-Joe). Stop there — no `gh pr create`. Report the branch is ready for the user to open when they decide.

- [ ] **Step 4: Archive design docs**
Ensure `docs/superpowers/specs/2026-07-11-log-no-demand-skips-design.md` and this plan are preserved on an archive branch (`archive/no-demand-logging-design-history`) per the standing preference, before the dev branch is eventually cleaned up.

---

## Self-Review

**Spec coverage:** toggle (Task 1/5) ✓; reason token (Task 1/5) ✓; per-zone normal path incl. nothing-due + mutual-exclusion + dedup (Task 2/3) ✓; distributor members (Task 4) ✓; opt-in default-off byte-identical (gating in Task 2, verified Task 3 step 6 / Task 4 step 6) ✓; 8-language i18n (Task 5) ✓; process = production-first, PR branch prepared not opened (Task 7) ✓.

**Placeholders:** i18n strings for 6 of 8 languages in Task 5 are marked `<...>` where a faithful translation must be produced by the implementer in the neighbouring card's register — these are content-to-write, not logic gaps; en/de are given verbatim.

**Type consistency:** `log_no_demand` (snake_case) used identically across const.py / store.py / websockets.py / const.ts / types.ts; `SKIP_REASON_NO_DEMAND == "no_demand"` matches the `panels.zones.outlook.checks.no_demand` localize key; `_record_no_demand_skips(zone_ids)` signature is called identically from irrigation.py and distributor.py.
