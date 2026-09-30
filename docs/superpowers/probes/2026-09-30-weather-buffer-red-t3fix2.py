"""RED by mutation for the second review fix after Task 3 (the weather-entity reader) -- on a COPY.

    python t3fix2_red.py

Builds `review/t3fix2/copy` from the worktree's HEAD (`git archive`), then for two variants of
the test files -- "committed" (HEAD's) and "new" (the worktree's edited, uncommitted ones) --
runs tests/test_live_estimate_time_provenance.py and tests/test_time_provenance.py under TZ=UTC, once
unmutated and once per mutant, and prints the summary line and the failing test names.
Each mutant is restored byte for byte before the next (checked by sha256).
"""

import hashlib
import os
import pathlib
import re
import shutil
import subprocess
import sys

ROOT = pathlib.Path("D:/Entwicklung/HASI/issue22-work")
WT = ROOT / "wt"
COPY = ROOT / "review" / "t3fix2" / "copy"
PY = "D:/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe"
WA = "custom_components/irrigation_plus/weather_aggregate.py"
H = "custom_components/irrigation_plus/helpers.py"
TESTS = ["tests/test_live_estimate_time_provenance.py", "tests/test_time_provenance.py"]
LE = "custom_components/irrigation_plus/live_estimate.py"
# The first of three identical lines is the weather-entity reader (_read_hourly_forecast).
CLIENT = "                when = coerce_stamp(when, STAMP_FROM_CLIENT)\n"

# (id, file, old, new, which occurrence of old; None = it must be unique)
MUTANTS = [
    ("E1 the entity reader drops an aware row's zone", LE, CLIENT,
     "                when = when.replace(tzinfo=None)\n", 0),
    ("E2 the entity reader reads an aware row at UTC wall time", LE, CLIENT,
     "                when = dt_util.as_utc(when).replace(tzinfo=None)\n", 0),
    ("E3 the entity reader leaves an aware row aware", LE, CLIENT,
     "                when = when\n", 0),
]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_copy():
    if COPY.exists():
        shutil.rmtree(COPY)
    COPY.mkdir(parents=True)
    archive = subprocess.run(["git", "-C", str(WT), "archive", "HEAD"], capture_output=True,
                             check=True).stdout
    subprocess.run(["tar", "-x", "-C", str(COPY)], input=archive, check=True)
    shutil.copy(WT / "_local_socket_unblock.py", COPY / "_local_socket_unblock.py")


def apply(rel, old, new, nth):
    path = COPY / rel
    raw = path.read_bytes().decode("utf-8")
    crlf = "\r\n" in raw
    text = raw.replace("\r\n", "\n")
    starts = [m.start() for m in re.finditer(re.escape(old), text)]
    if nth is None:
        if len(starts) != 1:
            sys.exit(f"{rel}: expected 1x, found {len(starts)}x: {old[:60]!r}")
        nth = 0
    at = starts[nth]
    text = text[:at] + new + text[at + len(old):]
    path.write_bytes((text.replace("\n", "\r\n") if crlf else text).encode("utf-8"))


def run():
    env = {**os.environ, "TZ": "UTC"}
    out = subprocess.run(
        [PY, "-m", "pytest", *TESTS, "-p", "_local_socket_unblock", "-q", "--no-header",
         "--tb=no", "-rf", "-p", "no:cacheprovider"],
        cwd=COPY, env=env, capture_output=True, text=True, encoding="utf-8", errors="replace",
        timeout=600,
    ).stdout
    summary = [ln for ln in out.splitlines() if re.match(r"^=+ .* in [\d.]+s", ln)]
    failed = sorted(set(re.findall(r"^FAILED (\S+)", out, re.M)))
    return (summary[-1] if summary else "NO SUMMARY -- nothing collected?"), failed


def main():
    build_copy()
    committed = {t: (COPY / t).read_bytes() for t in TESTS}
    new = {t: (WT / t).read_bytes() for t in TESTS}
    for variant, files in (("committed", committed), ("new", new)):
        for t, data in files.items():
            (COPY / t).write_bytes(data)
        print(f"=== {variant} tests")
        summary, failed = run()
        print(f"  unmutated: {summary}")
        for name in failed:
            print(f"      FAILED {name}")
        for mid, rel, old, new_text, nth in MUTANTS:
            before = sha(COPY / rel)
            backup = (COPY / rel).read_bytes()
            apply(rel, old, new_text, nth)
            try:
                summary, failed = run()
            finally:
                (COPY / rel).write_bytes(backup)
            restored = sha(COPY / rel) == before
            print(f"  {mid}: {summary} restored={restored}")
            for name in failed:
                print(f"      FAILED {name}")
    shutil.rmtree(COPY)


main()
