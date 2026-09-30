"""RED by mutation for the review fix after Task 4 -- on COPIES, never the worktree.

    python t4fix_red.py

"committed": a copy of the worktree's HEAD (code and tests as committed), with each mutant
written for HEAD's code. "new": the same copy with the worktree's edited, uncommitted files
laid over it (production AND tests), with each mutant written for the fixed code. Both run
the three test files below under TZ=UTC, once unmutated and once per mutant; every mutant is
restored byte for byte (sha256) before the next.
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
COPY = ROOT / "review" / "t4fix" / "copy"
PY = "D:/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe"
H = "custom_components/irrigation_plus/helpers.py"
S = "custom_components/irrigation_plus/store.py"
LE = "custom_components/irrigation_plus/live_estimate.py"
TESTS = [
    "tests/test_store_stamp_migration.py",
    "tests/test_time_provenance.py",
    "tests/test_live_estimate_time_provenance.py",
]
CHANGED = [H, S, LE, *TESTS]

# The store step's decisions; the text is the same before and after the fix.
STORE_MUTANTS = [
    ("S2 the stamp step checks the minor only", S,
     "        if (old_major_version, old_minor_version) < (14, 2):\n",
     "        if old_minor_version < 2:\n"),
    ("S5 no dict guard for a zone", S,
     "    for zone in data.get(\"zones\") or []:\n        if not isinstance(zone, dict):\n"
     "            continue\n",
     "    for zone in data.get(\"zones\") or []:\n"),
    ("S6 no dict guard for a mapping", S,
     "    for mapping in data.get(\"mappings\") or []:\n        if not isinstance(mapping, dict):\n"
     "            continue\n",
     "    for mapping in data.get(\"mappings\") or []:\n"),
]

MUTANTS = {
    "committed": [
        ("H3 an aware stamp re-read in the process zone", H,
         "    if parsed.tzinfo is None:\n        parsed = parsed.replace(tzinfo=_process_timezone())\n",
         "    if True:\n        parsed = parsed.replace(tzinfo=_process_timezone())\n"),
        ("H7 the microseconds dropped", H,
         "    return dt_util.as_local(parsed).replace(tzinfo=None).isoformat()\n",
         "    return dt_util.as_local(parsed).replace(tzinfo=None).isoformat(timespec=\"seconds\")\n"),
        *STORE_MUTANTS,
    ],
    "new": [
        ("H3 an aware stamp re-read in the process zone", H,
         "        if parsed.tzinfo is None:\n            parsed = parsed.replace(tzinfo=_process_timezone())\n",
         "        if True:\n            parsed = parsed.replace(tzinfo=_process_timezone())\n"),
        ("H7 the microseconds dropped", H,
         "        return dt_util.as_local(parsed).replace(tzinfo=None).isoformat()\n",
         "        return dt_util.as_local(parsed).replace(tzinfo=None).isoformat(timespec=\"seconds\")\n"),
        *STORE_MUTANTS,
        ("G1 lift_legacy_stamp lets the conversion raise", H,
         "    except (ValueError, OverflowError, OSError):\n        return value\n",
         "    except ValueError:\n        return value\n"),
        ("G2 coerce_stamp lets the conversion raise", H,
         "    try:\n        return dt_util.as_local(parsed).replace(tzinfo=None)\n"
         "    except OverflowError:\n",
         "    if True:\n        return dt_util.as_local(parsed).replace(tzinfo=None)\n"
         "    if False:\n"),
        ("G3 _parse_stored_as_ha_local lets the conversion raise", LE,
         "            try:\n                return dt_util.as_local(value).replace(tzinfo=None)\n"
         "            except OverflowError:\n",
         "            if True:\n                return dt_util.as_local(value).replace(tzinfo=None)\n"
         "            if False:\n"),
    ],
}


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
    for variant in [v for v in ("committed", "new") if v in os.environ.get("T4FIX_ONLY", "committed,new")]:
        if variant == "new":
            for rel in CHANGED:
                shutil.copy(WT / rel, COPY / rel)
        print(f"=== {variant}")
        summary, failed = run()
        print(f"  unmutated: {summary}")
        for name in failed:
            print(f"      FAILED {name}")
        for mid, rel, old, new in MUTANTS[variant]:
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
