"""Probe run of the seasonal-outlook plan against a throwaway worktree.

Reads every "Ersetze in `F`:" / "durch:" pair and every "Hänge an `F` an:" block
from the plan, verbatim, and applies them task by task to the probe worktree:
test edits first (expect the stated RED), then the code edits (expect GREEN),
then the whole calendar and i18n test files must be green.

Usage: python probe_plan.py <plan.md> <worktree>
"""

import re
import subprocess
import sys
from pathlib import Path

PY = r"D:\Entwicklung\HASI\HAsmartirrigation\.venv\Scripts\python.exe"

# Task -> (-k expression, RED (failed, passed), GREEN passed, teardown errors)
# Locally every test on the ``coordinator`` fixture also ERRORs at teardown with a
# lingering timer (pre-existing: all eleven base calendar tests are in the baseline
# that way); the call phase carries RED/GREEN, the error count stays the same.
EXPECT = {
    1: ("carries_no_rain or subtracted_once", (2, 0), 2, 2),
    2: ("kc_scales or kc_is_none or module_without_rain", (2, 1), 3, 3),
    3: ("static_demand or static_surplus", (2, 0), 2, 2),
    4: ("own_number_of_days", (1, 0), 1, 1),
    5: ("TestTheClimateCurves", (2, 1), 3, 3),
    6: ("comes_from_latitude", (1, 0), 1, 1),
    7: ("service_description", (1, 0), 1, 0),
    8: ("illustration_note", (1, 0), 1, 0),
}

TASK_RE = re.compile(r"^### Task (\d+):")
REPLACE_RE = re.compile(r"^\*\*Ersetze in `([^`]+)`:\*\*\s*$")
WITH_RE = re.compile(r"^\*\*durch:\*\*\s*$")
APPEND_RE = re.compile(r"^\*\*Hänge an `([^`]+)` an:\*\*\s*$")
FENCE_RE = re.compile(r"^```")


def read_block(lines, i):
    """Return (content, next index) of the fenced block starting at or after i."""
    while not FENCE_RE.match(lines[i]):
        if lines[i].strip():
            raise SystemExit(f"expected a fence at plan line {i + 1}, got {lines[i]!r}")
        i += 1
    i += 1
    body = []
    while not FENCE_RE.match(lines[i]):
        body.append(lines[i])
        i += 1
    return "\n".join(body) + "\n", i + 1


def parse(plan_text):
    lines = plan_text.split("\n")
    tasks = {}
    task = None
    i = 0
    while i < len(lines):
        m = TASK_RE.match(lines[i])
        if m:
            task = int(m.group(1))
            tasks.setdefault(task, [])
            i += 1
            continue
        m = REPLACE_RE.match(lines[i])
        if m:
            old, i = read_block(lines, i + 1)
            while not WITH_RE.match(lines[i]):
                if lines[i].strip():
                    raise SystemExit(f"expected **durch:** at plan line {i + 1}")
                i += 1
            new, i = read_block(lines, i + 1)
            tasks[task].append(("replace", m.group(1), old, new))
            continue
        m = APPEND_RE.match(lines[i])
        if m:
            body, i = read_block(lines, i + 1)
            tasks[task].append(("append", m.group(1), body, None))
            continue
        i += 1
    return tasks


def apply(worktree, edit):
    kind, rel, a, b = edit
    path = worktree / rel
    raw = path.read_bytes().decode("utf-8")
    crlf = "\r\n" in raw
    text = raw.replace("\r\n", "\n")
    if kind == "replace":
        count = text.count(a)
        if count != 1:
            raise SystemExit(f"ANCHOR {rel}: found {count}x\n{a}")
        text = text.replace(a, b)
    else:
        if not text.endswith("\n"):
            text += "\n"
        text += a
    if crlf:
        text = text.replace("\n", "\r\n")
    path.write_bytes(text.encode("utf-8"))


def pytest(worktree, *args):
    cmd = [PY, "-m", "pytest", *args, "-p", "_local_socket_unblock", "-q", "--no-header", "-rfE"]
    out = subprocess.run(
        cmd, cwd=worktree, capture_output=True, text=True, encoding="utf-8",
        errors="replace", timeout=900,
    ).stdout
    tail = [ln for ln in out.splitlines() if re.search(r"\d+ (passed|failed|error)", ln)]
    summary = tail[-1] if tail else out[-400:]
    failed = int(m.group(1)) if (m := re.search(r"(\d+) failed", summary)) else 0
    passed = int(m.group(1)) if (m := re.search(r"(\d+) passed", summary)) else 0
    errors = int(m.group(1)) if (m := re.search(r"(\d+) error", summary)) else 0
    # Every error must be the known teardown one, never a setup or call error.
    teardown = out.count("ERROR at teardown of")
    lingering = out.count("Lingering timer after test")
    if errors and not (teardown == errors and lingering >= errors):
        summary += f"  [!! {errors} errors, {teardown} at teardown, {lingering} lingering]"
        errors = -errors
    return failed, passed, errors, summary, out


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    plan = Path(sys.argv[1]).read_text(encoding="utf-8")
    worktree = Path(sys.argv[2])
    tasks = parse(plan)
    ok = True
    for task in sorted(tasks):
        edits = tasks[task]
        if not edits:
            continue
        tests = [e for e in edits if e[1].startswith("tests/")]
        code = [e for e in edits if not e[1].startswith("tests/")]
        print(f"== Task {task}: {len(tests)} test edit(s), {len(code)} code edit(s)")
        for e in tests:
            apply(worktree, e)
        if task in EXPECT:
            expr, (red_f, red_p), green_p, td = EXPECT[task]
            f, p, err, summary, out = pytest(worktree, "tests/test_watering_calendar.py", "-k", expr)
            verdict = "OK" if (f, p, err) == (red_f, red_p, td) else "MISMATCH"
            ok &= verdict == "OK"
            print(f"   RED   expect {red_f} failed/{red_p} passed -> {summary.strip()} [{verdict}]")
            for line in out.splitlines():
                if line.startswith("E ") and ("assert" in line or "Error" in line):
                    print("        " + line[:150])
        for e in code:
            apply(worktree, e)
        if task in EXPECT:
            f, p, err, summary, _ = pytest(worktree, "tests/test_watering_calendar.py", "-k", expr)
            verdict = "OK" if (f, p, err) == (0, green_p, td) else "MISMATCH"
            ok &= verdict == "OK"
            print(f"   GREEN expect {green_p} passed -> {summary.strip()} [{verdict}]")
        f, p, err, summary, out = pytest(
            worktree, "tests/test_watering_calendar.py", "tests/test_watering_calendar_api.py",
            "tests/test_i18n_completeness.py",
        )
        verdict = "OK" if f == 0 and err >= 0 else "MISMATCH"
        ok &= verdict == "OK"
        print(f"   FILES {summary.strip()} [{verdict}]")
        if verdict != "OK":
            print(out[-3000:])
    print("PROBE", "OK" if ok else "HAS MISMATCHES")


if __name__ == "__main__":
    main()
