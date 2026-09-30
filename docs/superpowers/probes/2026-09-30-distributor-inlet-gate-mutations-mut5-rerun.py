"""Re-run mutation 5 alone, with the one test it deadlocks deselected.

Without the in-flight guard, test_second_concurrent_cycle_rejected_by_single_flight_lock
starts its second cycle into the same release.wait() as the first one and never
returns (measured: the first matrix run hung there and was killed). Deselecting
that one test lets the run finish, so the kill is read from named failures.
"""

import io
import os
import subprocess
import sys

WT = sys.argv[1] if len(sys.argv) > 1 else r"D:\Entwicklung\HASI\issue66-work\wt"
PY = r"D:\Entwicklung\HASI\HAsmartirrigation\.venv\Scripts\python.exe"
TMP = r"D:\Entwicklung\HASI\issue66-work\tmp"
DIST = os.path.join(WT, "custom_components", "irrigation_plus", "distributor.py")
SUITES = [
    "tests/test_distributor_inlet_gate.py",
    "tests/test_distributor.py",
    "tests/test_distributor_cycle.py",
    "tests/test_distributor_dispatch.py",
    "tests/test_distributor_integration.py",
]
HANGS = "tests/test_distributor_cycle.py::test_second_concurrent_cycle_rejected_by_single_flight_lock"
OLD = "        if dist_id in inflight:\n            return False\n"


def run():
    env = dict(os.environ)
    env.update(TMPDIR=TMP, TEMP=TMP, TMP=TMP, TZ="UTC")
    proc = subprocess.run(
        [PY, "-m", "pytest", *SUITES, "-p", "_local_socket_unblock", "-q",
         "--deselect", HANGS],
        cwd=WT, env=env, capture_output=True, text=True, timeout=600,
    )
    names = sorted({ln.split(" - ")[0].strip() for ln in (proc.stdout + proc.stderr).splitlines()
                    if ln.startswith(("FAILED tests/", "ERROR tests/"))})
    tail = [ln for ln in proc.stdout.splitlines() if " passed" in ln or " failed" in ln]
    return names, (tail[-1] if tail else "NO SUMMARY LINE")


raw = io.open(DIST, "rb").read()
crlf = b"\r\n" in raw
text = raw.decode("utf-8").replace("\r\n", "\n")
assert text.count(OLD) == 1, text.count(OLD)
ref_names, ref_summary = run()
print("reference (deselected):", ref_summary, "| failures:", len(ref_names))
mutated = text.replace(OLD, "", 1)
out = mutated.replace("\n", "\r\n") if crlf else mutated
io.open(DIST + ".tmp", "wb").write(out.encode("utf-8"))
os.replace(DIST + ".tmp", DIST)
try:
    names, summary = run()
finally:
    io.open(DIST + ".tmp", "wb").write(raw)
    os.replace(DIST + ".tmp", DIST)
print("mutated:", summary)
for n in sorted(set(names) - set(ref_names)):
    print("  KILLED BY", n.split("::", 1)[-1])
print("restored byte-for-byte:", io.open(DIST, "rb").read() == raw)
