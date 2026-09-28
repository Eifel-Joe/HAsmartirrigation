# Evidence for specs/2026-09-28-weather-buffer-one-frame-design.md (Revision 4).
# Run against a checkout of upstream 1876aa03; adjust the sys.path line below to it.
"""Probe, not a test: does the plan's Task 1 fix the LIVE path, and do Tasks 4-6
mix naive and aware on the internal comparisons?

Runs the REAL functions of the worktree (1876aa03), swapping only coerce_stamp for
the plan's Task-1 body where a variant says so. Nothing in the repo is modified.

Scenario: process at UTC (container without TZ=), HA at Europe/Berlin.
Last calculation at 10:00Z (= 12:00 Berlin). Readings at 10:00Z, 10:30Z, 11:00Z.
The user's clock now reads 13:00 Berlin (= 11:00Z). Real elapsed window: 1.0 h.
"""

import asyncio
import datetime
import sys
import zoneinfo

sys.path.insert(0, r"D:/Entwicklung/HASI/issue22-work/wt")

from homeassistant.util import dt as dt_util  # noqa: E402

from custom_components.irrigation_plus import (  # noqa: E402
    calculation,
    const,
    helpers,
    live_estimate,
    store as store_mod,
    weather_aggregate as wa,
)

UTC = datetime.timezone.utc
BERLIN = zoneinfo.ZoneInfo("Europe/Berlin")
ORIGINAL_COERCE = helpers.coerce_stamp


def task1_coerce(value, provenance):
    """Verbatim the plan's Task 1 Step 5 body."""
    if provenance not in (helpers.STAMP_FROM_STORE, helpers.STAMP_FROM_CLIENT):
        raise ValueError(provenance)
    if value is None:
        return None
    try:
        parsed = helpers.as_datetime(value)
    except (ValueError, TypeError):
        return None
    if not isinstance(parsed, datetime.datetime):
        return None
    if provenance == helpers.STAMP_FROM_STORE and parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=helpers._process_timezone())
    if parsed.tzinfo is None:
        return parsed
    return dt_util.as_local(parsed).replace(tzinfo=None)


def use(coerce):
    helpers.coerce_stamp = coerce
    wa.coerce_stamp = coerce  # imported by name there


def reading(stamp, t):
    return {
        const.RETRIEVED_AT: stamp,
        const.MAPPING_TEMPERATURE: t,
        const.MAPPING_HUMIDITY: 50.0,
        const.MAPPING_WINDSPEED: 2.0,
        const.MAPPING_SOLRAD: 2.5,
    }


def legacy_store():
    """Stamps as a UTC process wrote them with a bare datetime.now()."""
    zone = {
        const.ZONE_LAST_CALCULATED: "2026-07-15T10:00:00",
        const.ZONE_LAST_CONSUMED: "2026-07-15T10:00:00",
    }
    rows = [
        reading(datetime.datetime(2026, 7, 15, 10, 0), 20.0),
        reading(datetime.datetime(2026, 7, 15, 10, 30), 20.5),
        reading(datetime.datetime(2026, 7, 15, 11, 0), 21.0),
    ]
    return zone, rows


def aware_store():
    """The same instants as the plan's Tasks 4-6 writers (dt_util.now()) store them."""
    zone = {
        const.ZONE_LAST_CALCULATED: "2026-07-15T12:00:00+02:00",
        const.ZONE_LAST_CONSUMED: "2026-07-15T12:00:00+02:00",
    }
    rows = [
        reading(datetime.datetime(2026, 7, 15, 12, 0, tzinfo=BERLIN), 20.0),
        reading(datetime.datetime(2026, 7, 15, 12, 30, tzinfo=BERLIN), 20.5),
        reading(datetime.datetime(2026, 7, 15, 13, 0, tzinfo=BERLIN), 21.0),
    ]
    return zone, rows


def live_path(zone, rows):
    """Exactly the live estimate's call shape: anchor from _window_anchor, now_local
    = coerce_stamp(dt_util.now(), STAMP_FROM_CLIENT), i.e. naive HA-local."""
    anchor = live_estimate._window_anchor(zone)
    now_local = datetime.datetime(2026, 7, 15, 13, 0)
    agg = wa.aggregate_window(rows, anchor, {}, now=now_local)
    hrs = wa.build_hourly_rows(
        rows, anchor, {}, now=now_local,
        latitude=50.0, longitude=6.0, elevation=200.0, tz=BERLIN,
    )
    window_h = agg[const.MAPPING_DATA_MULTIPLIER] * 24 if agg else None
    hours = [(r["hour"], round(r["coverage_h"], 2), r["tz_offset_h"]) for r in hrs] if hrs else hrs
    return anchor, window_h, hours


def section(title):
    print("\n" + "=" * 78 + "\n" + title + "\n" + "=" * 78)


helpers._process_timezone = lambda: UTC
dt_util.set_default_time_zone(BERLIN)

section("P1  live-estimate path, real aggregate_window + build_hourly_rows")
print("real elapsed: 1.0 h; correct row: hour 12.5 (12:00-13:00 Berlin), offset +2.0")
for label, coerce in (("1876aa03 coerce_stamp", ORIGINAL_COERCE), ("plan Task-1 coerce_stamp", task1_coerce)):
    use(coerce)
    for store_label, make in (("legacy naive store", legacy_store), ("aware store (after Tasks 4-6)", aware_store)):
        zone, rows = make()
        try:
            anchor, window_h, hours = live_path(zone, rows)
            print(f"[{label:25}] [{store_label:30}] anchor={anchor}  window={window_h} h  rows(hour,cov,off)={hours}")
        except Exception as e:  # noqa: BLE001
            print(f"[{label:25}] [{store_label:30}] RAISED {type(e).__name__}: {e}")

section("P2  real _prune_mapping_buffer after Task 5 (now = dt_util.now(), aware), legacy store")
use(task1_coerce)


class FakeStore:
    def __init__(self, rows, watermarks):
        self._rows, self._wm = rows, watermarks
        self.written = None

    def get_mapping(self, mapping_id):
        return {"id": mapping_id}

    def get_mapping_buffer(self, mapping_id):
        return list(self._rows)

    def get_enabled_zone_watermarks(self, mapping_id):
        return list(self._wm), False

    def set_mapping_buffer(self, mapping_id, kept):
        self.written = kept


class FakeCalc:
    pass


_, legacy_rows = legacy_store()
fake = FakeCalc()
fake.store = FakeStore(legacy_rows, [datetime.datetime(2026, 7, 15, 10, 0)])
try:
    asyncio.run(calculation.CalculationMixin._prune_mapping_buffer(fake, 1, now=dt_util.now()))
    print("returned without error; written =", fake.store.written)
except Exception as e:  # noqa: BLE001
    print(f"RAISED {type(e).__name__}: {e}")

section("P3  real merge_or_append_mapping_reading after Task 5 (aware timestamp), legacy newest row")
st = object.__new__(store_mod.SmartIrrigationStorage)
st.mappings = {1: {}}
st.buffers = {1: [dict(legacy_rows[-1])]}
st._buffers_dirty = False
aware_ts = dt_util.now()
try:
    ok = st.merge_or_append_mapping_reading(
        1,
        {const.RETRIEVED_AT: aware_ts, const.MAPPING_PRESSURE: 1013.0},
        coalesce_before=aware_ts - datetime.timedelta(seconds=2),
        min_watermark=None,
    )
    print("returned", ok)
except Exception as e:  # noqa: BLE001
    print(f"RAISED {type(e).__name__}: {e}")

dt_util.set_default_time_zone(UTC)

# ---------------------------------------------------------------------------
dt_util.set_default_time_zone(BERLIN)
section("P4  DAILY-calc path (calculation.py call shape): watermark = _as_datetime(raw), real aggregate_window")
print("real elapsed: 1.0 h. 'pre-Task-5' now = naive process clock 11:00; 'post-Task-5' now = dt_util.now() at 11:00Z")
now_pre = datetime.datetime(2026, 7, 15, 11, 0)                    # bare datetime.now() on a UTC process
now_post = datetime.datetime(2026, 7, 15, 13, 0, tzinfo=BERLIN)    # dt_util.now() at the same instant
for label, coerce in (("1876aa03 coerce_stamp", ORIGINAL_COERCE), ("plan Task-1 coerce_stamp", task1_coerce)):
    use(coerce)
    for store_label, make in (("legacy naive store", legacy_store), ("aware store (after Tasks 4-6)", aware_store)):
        zone, rows = make()
        watermark = calculation._as_datetime(zone[const.ZONE_LAST_CONSUMED])
        for now_label, now in (("pre-Task-5 now", now_pre), ("post-Task-5 now", now_post)):
            try:
                agg = wa.aggregate_window(rows, watermark, {}, now=now)
                window_h = agg[const.MAPPING_DATA_MULTIPLIER] * 24 if agg else None
                print(f"[{label:25}] [{store_label:30}] [{now_label:15}] window={window_h} h")
            except Exception as e:  # noqa: BLE001
                print(f"[{label:25}] [{store_label:30}] [{now_label:15}] RAISED {type(e).__name__}: {e}")
dt_util.set_default_time_zone(UTC)
