"""Impact probe for Eifel-Joe#22 variant B: apply every production change, rename the 24
direct migrate calls, nothing else. Measures how the existing suite reacts.

Edits D:/Entwicklung/HASI/issue22-work/probe-wt in place. The working copy is CRLF
(core.autocrlf=true): each file is matched as LF and written back in its own ending.
Every replacement must match exactly the stated number of times, or nothing is written.
"""
import pathlib
import re
import sys

WT = pathlib.Path("D:/Entwicklung/HASI/issue22-work/probe-wt")
PKG = WT / "custom_components/irrigation_plus"

edits = {}  # path -> list of (old, new, count)


def rep(path, old, new, count=1):
    edits.setdefault(path, []).append((old, new, count))


# --- helpers.py --------------------------------------------------------------
H = PKG / "helpers.py"
rep(H, "\nfrom homeassistant import exceptions\n",
    "\nfrom dateutil import tz as dateutil_tz\nfrom homeassistant import exceptions\n")
rep(H, "\n    return datetime.now().astimezone().tzinfo\n",
    "\n    return dateutil_tz.tzlocal()\n")
rep(H, """    if parsed.tzinfo is None:
        return parsed
    if provenance == STAMP_FROM_STORE:
        return parsed.astimezone(_process_timezone()).replace(tzinfo=None)
    return dt_util.as_local(parsed).replace(tzinfo=None)
""", """    if parsed.tzinfo is None:
        return parsed
    return dt_util.as_local(parsed).replace(tzinfo=None)


def local_naive_now() -> datetime:
    \"\"\"HA's wall clock, naive.\"\"\"
    return dt_util.now().replace(tzinfo=None)


def lift_legacy_stamp(value):
    \"\"\"One stored stamp from the process's clock onto HA's, string in, string out.\"\"\"
    if not isinstance(value, str):
        return value
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return value
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=_process_timezone())
    return dt_util.as_local(parsed).replace(tzinfo=None).isoformat()
""")

# --- store.py ------------------------------------------------------------------
S = PKG / "store.py"
rep(S, "\nfrom .helpers import as_datetime, loadModules, zone_depth_default\n",
    "\nfrom .helpers import (\n    as_datetime,\n    lift_legacy_stamp,\n    loadModules,\n"
    "    local_naive_now,\n    zone_depth_default,\n)\n")
rep(S, "\nSTORAGE_VERSION = 14\n", "\nSTORAGE_VERSION = 14\nSTORAGE_MINOR_VERSION = 2\n")
rep(S, "\n    async def _async_migrate_func(self, old_version, data: dict):\n",
    """
    async def _async_migrate_func(self, old_major_version, old_minor_version, data):
        \"\"\"HA's three-argument hook: the major steps, then the minor ones.\"\"\"
        data = await self._async_migrate_major(old_major_version, data)
        if (old_major_version, old_minor_version) < (14, 2):
            _lift_legacy_stamps(data)
        return data

    async def _async_migrate_major(self, old_version, data: dict):
""")
rep(S, "\ndef _as_buffer(value) -> list:\n", """
def _lift_legacy_stamps(data: dict) -> None:
    \"\"\"The five weather-buffer stamps of a pre-14.2 store, onto HA's clock.\"\"\"
    for zone in data.get("zones") or []:
        if not isinstance(zone, dict):
            continue
        for key in ("last_calculated", "last_consumed_at", "last_updated"):
            if key in zone:
                zone[key] = lift_legacy_stamp(zone[key])
    for mapping in data.get("mappings") or []:
        if not isinstance(mapping, dict):
            continue
        if "data_last_updated" in mapping:
            mapping["data_last_updated"] = lift_legacy_stamp(mapping["data_last_updated"])
        rows = mapping.get("data")
        if isinstance(rows, list):
            for row in rows:
                if isinstance(row, dict) and "retrieved" in row:
                    row["retrieved"] = lift_legacy_stamp(row["retrieved"])


def _as_buffer(value) -> list:
""")
rep(S, "\n        self._store = MigratableStore(hass, STORAGE_VERSION, STORAGE_KEY)\n",
    "\n        self._store = MigratableStore(\n            hass, STORAGE_VERSION, STORAGE_KEY, "
    "minor_version=STORAGE_MINOR_VERSION\n        )\n")
rep(S, "last_consumed_at=datetime.datetime.now())", "last_consumed_at=local_naive_now())")

# --- calculation.py --------------------------------------------------------------
C = PKG / "calculation.py"
rep(C, "\nfrom datetime import datetime, timedelta\n", "\nfrom datetime import timedelta\n")
rep(C, "\nfrom .helpers import convert_between, loadModules\n",
    "\nfrom .helpers import convert_between, loadModules, local_naive_now\n")
rep(C, "\n        now = datetime.now()\n", "\n        now = local_naive_now()\n", 2)  # :267, :432
rep(C, "\n            now = datetime.now()\n", "\n            now = local_naive_now()\n", 3)  # :379 :498 :934

# --- continuous_update.py ----------------------------------------------------------
U = PKG / "continuous_update.py"
rep(U, "\nfrom datetime import datetime, timedelta\n", "\nfrom datetime import timedelta\n")
rep(U, "\n    convert_mapping_to_metric,\n    resolve_sensor_unit,\n",
    "\n    convert_mapping_to_metric,\n    local_naive_now,\n    resolve_sensor_unit,\n")
rep(U, "\n        timestamp = datetime.now()\n", "\n        timestamp = local_naive_now()\n", 2)  # :252 :378
rep(U, "\n        now = datetime.now()\n", "\n        now = local_naive_now()\n")  # :521

# --- __init__.py ---------------------------------------------------------------------
I = PKG / "__init__.py"
rep(I, """
# NB: alias the stdlib datetime class. This package ships a ``datetime.py``
# platform module (the rain-delay DateTimeEntity); importing that platform sets
# the ``datetime`` attribute on this package — which IS this module's global
# namespace — clobbering a global literally named ``datetime`` and breaking
# ``dt_datetime.now()`` at runtime. The alias keeps our global name collision-free.
from datetime import datetime as dt_datetime
from datetime import timedelta
""", "\nfrom datetime import timedelta\n")
rep(I, "\n    corrected_azimuth_bearing,\n    loadModules,\n",
    "\n    corrected_azimuth_bearing,\n    loadModules,\n    local_naive_now,\n")
rep(I, "dt_datetime.now()", "local_naive_now()", 7)

# --- weather_aggregate.py ----------------------------------------------------------------
W = PKG / "weather_aggregate.py"
rep(W, "\nfrom .helpers import STAMP_FROM_STORE, coerce_stamp\n",
    "\nfrom .helpers import STAMP_FROM_STORE, coerce_stamp, local_naive_now\n")
rep(W, "\n        else datetime.datetime.now()\n", "\n        else local_naive_now()\n", 3)

# --- tests: the 24 direct two-argument calls -------------------------------------------
TESTS = WT / "tests"
call = re.compile(r"\._async_migrate_func\(")


def read(path):
    raw = path.read_bytes().decode("utf-8")
    return raw.replace("\r\n", "\n"), "\r\n" in raw


def write(path, text, crlf):
    path.write_bytes((text.replace("\n", "\r\n") if crlf else text).encode("utf-8"))


out = {}
for path, items in edits.items():
    text, crlf = read(path)
    for old, new, count in items:
        n = text.count(old)
        if n != count:
            sys.exit(f"{path.name}: expected {count}x, found {n}x: {old[:70]!r}")
        text = text.replace(old, new)
    out[path] = (text, crlf)

renamed = 0
files = 0
for p in sorted(TESTS.glob("test_*.py")):
    text, crlf = read(p)
    n = len(call.findall(text))
    if n:
        files += 1
        renamed += n
        out[p] = (call.sub("._async_migrate_major(", text), crlf)

for path, (text, crlf) in out.items():
    write(path, text, crlf)
print(f"production files: {len(edits)}; test files renamed: {files}; calls: {renamed}")
