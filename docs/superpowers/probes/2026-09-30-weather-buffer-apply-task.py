"""Apply one task of the plan to the dry-run worktree, using the plan's own code blocks.

    python apply_task.py <task> [<step>]

Every edit takes its text from the plan (plan_blocks.py numbering), never from a copy.
Each anchor must match exactly the stated number of times, or nothing is written.
Files keep their line endings (the working copy is CRLF).
"""
import importlib.util
import pathlib
import re
import sys

import os  # noqa: E402

WT = pathlib.Path(os.environ.get("APPLY_WT", "D:/Entwicklung/HASI/issue22-work/probe-wt"))
PKG = "custom_components/irrigation_plus/"

_spec = importlib.util.spec_from_file_location(
    "plan_blocks", pathlib.Path(__file__).with_name("2026-09-30-weather-buffer-apply-plan-blocks.py")
)
pb = importlib.util.module_from_spec(_spec)
sys.argv_backup = sys.argv
sys.argv = ["plan_blocks.py", "noop"]
_spec.loader.exec_module(pb)
sys.argv = sys.argv_backup

BLOCKS = {}
for task, lang, body in pb.blocks():
    BLOCKS.setdefault(task, []).append(body)


def B(task, index):
    return BLOCKS[task][index]


class Files:
    def __init__(self):
        self.cache = {}

    def get(self, rel):
        if rel not in self.cache:
            path = WT / rel
            raw = path.read_bytes().decode("utf-8") if path.exists() else ""
            self.cache[rel] = [raw.replace("\r\n", "\n"), "\r\n" in raw]
        return self.cache[rel][0]

    def set(self, rel, text):
        self.get(rel)
        self.cache[rel][0] = text

    def write(self):
        for rel, (text, crlf) in self.cache.items():
            data = text.replace("\n", "\r\n") if crlf else text
            (WT / rel).write_bytes(data.encode("utf-8"))


F = Files()


def fail(msg):
    sys.exit("APPLY FAILED: " + msg)


def replace(rel, old, new, count=1):
    text = F.get(rel)
    n = text.count(old)
    if n != count:
        fail(f"{rel}: expected {count}x, found {n}x: {old[:80]!r}")
    F.set(rel, text.replace(old, new))


def strip_block(block):
    """A replacement block without its final newline, to splice into running text."""
    return block[:-1] if block.endswith("\n") else block


def insert_before(rel, anchor, block):
    replace(rel, anchor, block + anchor)


def insert_after(rel, anchor, block):
    replace(rel, anchor, anchor + block)


def top_level_def_span(text, name):
    """Start and end offsets of a module-level ``def name`` incl. trailing blank lines."""
    m = re.search(rf"^(async )?def {re.escape(name)}\(", text, re.M)
    if not m:
        fail(f"def {name} not found")
    start = m.start()
    nxt = re.compile(r"^(?:def |async def |class |@)", re.M)
    m2 = nxt.search(text, m.end())
    end = m2.start() if m2 else len(text)
    return start, end


def replace_def(rel, name, block):
    text = F.get(rel)
    start, end = top_level_def_span(text, name)
    # keep the two blank lines that separate top-level definitions
    new = block.rstrip("\n") + "\n\n\n"
    F.set(rel, text[:start] + new + text[end:])


def docstring_span(text, def_name):
    m = re.search(rf"^\s*(async )?def {re.escape(def_name)}\(", text, re.M)
    if not m:
        fail(f"def {def_name} not found for its docstring")
    q = text.index('"""', m.end())
    q_end = text.index('"""', q + 3) + 3
    line_start = text.rindex("\n", 0, q) + 1
    return line_start, q_end


def replace_docstring(rel, def_name, block):
    text = F.get(rel)
    start, end = docstring_span(text, def_name)
    F.set(rel, text[:start] + strip_block(block) + text[end:])


def replace_module_docstring(rel, block):
    text = F.get(rel)
    if not text.startswith('"""'):
        fail(f"{rel} does not start with a docstring")
    end = text.index('"""', 3) + 3
    F.set(rel, strip_block(block) + text[end:])


def replace_range(rel, start_marker, end_marker, block):
    """From the unique start marker to the first end marker after it."""
    text = F.get(rel)
    if text.count(start_marker) != 1:
        fail(f"{rel}: start marker found {text.count(start_marker)}x")
    s = text.index(start_marker)
    e = text.find(end_marker, s)
    if e < 0:
        fail(f"{rel}: no end marker after the start")
    F.set(rel, text[:s] + block + text[e:])


def write_new(rel, block):
    path = WT / rel
    if path.exists():
        fail(f"{rel} exists already")
    path.write_text(block, encoding="utf-8", newline="\n")


def delete_line_starting(rel, prefix):
    text = F.get(rel)
    lines = text.split("\n")
    hits = [i for i, line in enumerate(lines) if line.startswith(prefix)]
    if len(hits) != 1:
        fail(f"{rel}: {len(hits)} lines start with {prefix!r}")
    del lines[hits[0]]
    F.set(rel, "\n".join(lines))


H = PKG + "helpers.py"
S = PKG + "store.py"
C = PKG + "calculation.py"
U = PKG + "continuous_update.py"
I = PKG + "__init__.py"
W = PKG + "weather_aggregate.py"
L = PKG + "live_estimate.py"


def task1():
    write_new("tests/test_weather_buffer_one_frame.py", B(1, 0))


def task2_tests():
    t = "tests/test_time_provenance.py"
    insert_after(t, "import pytest\n", B(2, 0))
    text = F.get(t)
    start, end = top_level_def_span(
        text, "test_a_naive_value_is_returned_unchanged_under_either_provenance"
    )
    F.set(t, text[:end] + B(2, 1).rstrip("\n") + "\n\n\n" + text[end:])


def task2_impl():
    replace(H, B(2, 3), B(2, 4))
    replace(H, B(2, 5), B(2, 6))
    insert_before(H, "class CannotConnect(exceptions.HomeAssistantError):", B(2, 7))


def task3_tests():
    t = "tests/test_time_provenance.py"
    replace_module_docstring(t, B(3, 0))
    replace_def(t, "test_the_same_instant_coerces_differently_per_provenance", B(3, 1))
    replace_docstring(t, "test_a_naive_value_is_returned_unchanged_under_either_provenance", B(3, 2))
    t = "tests/test_live_estimate_time_provenance.py"
    replace_module_docstring(t, B(3, 3))
    replace_def(t, "test_a_stored_stamp_is_still_read_in_ha_local_today", B(3, 4))
    replace_docstring(t, "test_a_naive_stored_stamp_passes_through_either_way", B(3, 5))
    t = "tests/test_weather_aggregate.py"
    insert_after(t, "import pytest\n", B(3, 6))
    replace_range(
        t,
        "class TestSelectWindowAcceptsBothTimestampForms:",
        "class TestSelectWindow:",
        B(3, 7),
    )


def task3_impl():
    replace(H, B(3, 9), B(3, 10))
    text = F.get(H)
    start, end = top_level_def_span(text, "coerce_stamp")
    F.set(H, text[:start] + B(3, 11).rstrip("\n") + "\n\n\n" + text[end:])
    replace_docstring(W, "_parse", B(3, 12))
    replace_docstring(L, "_parse_stored_as_ha_local", B(3, 13))


def task4_tests():
    write_new("tests/test_store_stamp_migration.py", B(4, 0))


def task4_impl():
    insert_before(H, "class CannotConnect(exceptions.HomeAssistantError):", B(4, 2))
    replace(S, B(4, 3), B(4, 4))
    insert_after(S, "STORAGE_VERSION = 14\n", B(4, 5))
    insert_before(S, "class MigratableStore(Store):", B(4, 6))
    replace(S, B(4, 7), B(4, 8))
    replace(S, strip_block(B(4, 9)), strip_block(B(4, 10)))


def task5_tests():
    t = "tests/test_continuous_update.py"
    insert_after(
        t,
        "from homeassistant.const import CONF_ELEVATION, STATE_UNAVAILABLE, STATE_UNKNOWN\n",
        B(5, 0),
    )
    replace(t, B(5, 1), B(5, 2))
    t = "tests/test_store_operations.py"
    replace(t, B(5, 3), B(5, 4))
    replace(t, B(5, 5), B(5, 6))
    t = "tests/test_zone_view_save.py"
    insert_after(t, "from freezegun import freeze_time\n", B(5, 7))
    replace(t, B(5, 8), B(5, 9))


def task5_impl():
    replace(C, "from datetime import datetime, timedelta\n", B(5, 11))
    replace(C, "from .helpers import convert_between, loadModules\n", B(5, 12))
    replace(C, "= datetime.now()", "= local_naive_now()", 5)
    replace(U, "from datetime import datetime, timedelta\n", B(5, 13))
    replace(U, B(5, 14), B(5, 15))
    replace(U, B(5, 16), B(5, 17))
    replace(U, "= datetime.now()", "= local_naive_now()", 2)
    replace(S, B(5, 18), B(5, 19))
    replace(S, "last_consumed_at=datetime.datetime.now()", "last_consumed_at=local_naive_now()")
    replace(I, B(5, 20), B(5, 21))
    replace(I, B(5, 22), B(5, 23))
    replace(I, B(5, 24), B(5, 25))
    replace(I, "dt_datetime.now()", "local_naive_now()", 6)
    replace(W, "from .helpers import STAMP_FROM_STORE, coerce_stamp\n", B(5, 26))
    replace(W, B(5, 27), B(5, 28), 3)


def task6():
    replace(C, B(6, 0), B(6, 1))
    replace(C, B(6, 2), B(6, 3))
    replace(C, B(6, 4), B(6, 5))
    replace(C, B(6, 6), B(6, 7))
    replace(PKG + "auto_calc.py", B(6, 8), B(6, 9))
    replace(PKG + "sensor.py", B(6, 10), B(6, 11))
    replace(PKG + "const.py", B(6, 12), B(6, 13))
    replace(S, B(6, 14), B(6, 15))
    replace(W, B(6, 16), B(6, 17))
    replace_range(
        "docs/usage-troubleshooting.md",
        "## Docker or Core: the container's time zone {#container-timezone}",
        "> Main page: [Usage](usage.md)<br/>",
        B(6, 18),
    )
    delete_line_starting(
        "docs/installation-download.md", "5. If you run Home Assistant in **Docker**"
    )


STEPS = {
    "1": task1,
    "2t": task2_tests,
    "2i": task2_impl,
    "3t": task3_tests,
    "3i": task3_impl,
    "4t": task4_tests,
    "4i": task4_impl,
    "5t": task5_tests,
    "5i": task5_impl,
    "6": task6,
}

STEPS[sys.argv[1]]()
F.write()
print(f"applied {sys.argv[1]}")
