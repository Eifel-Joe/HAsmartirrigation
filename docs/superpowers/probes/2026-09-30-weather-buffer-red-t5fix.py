"""RED by mutation for the criterion-file fix after Task 5 -- on a COPY, never the worktree.

    python t5fix_red.py

Builds `review/t5fix/copy` from the worktree's HEAD; runs the criterion file with HEAD's
version ("committed") and with the worktree's edited one ("new"), each unmutated and under
four mutants of the production code; restores each mutant byte for byte (sha256).
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
COPY = ROOT / "review" / "t5fix" / "copy"
PY = "D:/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe"
PKG = "custom_components/irrigation_plus/"
TEST = "tests/test_weather_buffer_one_frame.py"

MUTANTS = [
    ("LIVE the live refresh reads the process clock", PKG + "live_estimate.py",
     "        now = dt_util.now()\n        offset = now.utcoffset()\n",
     "        now = datetime.datetime.now()\n        offset = now.utcoffset()\n"),
    ("CLEAR clearing the weather data does not stamp the watermark", PKG + "calculation.py",
     "                {\n                    const.ZONE_LAST_CONSUMED: now,\n",
     "                {\n"),
    ("SWITCH a source switch does not stamp the watermark", PKG + "__init__.py",
     "                        {\n                            const.ZONE_LAST_CONSUMED: now,\n",
     "                        {\n"),
    ("CENSUS a utcnow() call in live_estimate.py", PKG + "live_estimate.py",
     "def _window_anchor(zone):\n",
     "def _census_probe():\n    return datetime.datetime.utcnow()\n\n\ndef _window_anchor(zone):\n"),
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


def apply(rel, old, new):
    path = COPY / rel
    raw = path.read_bytes().decode("utf-8")
    crlf = "\r\n" in raw
    text = raw.replace("\r\n", "\n")
    if text.count(old) != 1:
        sys.exit(f"{rel}: expected 1x, found {text.count(old)}x: {old[:60]!r}")
    text = text.replace(old, new)
    path.write_bytes((text.replace("\n", "\r\n") if crlf else text).encode("utf-8"))


def run():
    env = {**os.environ, "TZ": "UTC"}
    out = subprocess.run(
        [PY, "-m", "pytest", TEST, "-p", "_local_socket_unblock", "-q", "--no-header",
         "--tb=no", "-rf", "-p", "no:cacheprovider"],
        cwd=COPY, env=env, capture_output=True, text=True, encoding="utf-8", errors="replace",
        timeout=600,
    ).stdout
    summary = [ln for ln in out.splitlines() if re.match(r"^=+ .* in [\d.]+s", ln)]
    failed = sorted(set(re.findall(r"^FAILED (\S+)", out, re.M)))
    return (summary[-1] if summary else "NO SUMMARY -- nothing collected?"), failed


def main():
    build_copy()
    for variant in ("committed", "new"):
        if variant == "new":
            shutil.copy(WT / TEST, COPY / TEST)
        print(f"=== {variant}")
        summary, failed = run()
        print(f"  unmutated: {summary}")
        for name in failed:
            print(f"      FAILED {name}")
        for mid, rel, old, new in MUTANTS:
            before = sha(COPY / rel)
            backup = (COPY / rel).read_bytes()
            apply(rel, old, new)
            try:
                summary, failed = run()
            finally:
                (COPY / rel).write_bytes(backup)
            print(f"  {mid}: {summary} restored={sha(COPY / rel) == before}")
            for name in failed:
                print(f"      FAILED {name}")
    shutil.rmtree(COPY)


main()
