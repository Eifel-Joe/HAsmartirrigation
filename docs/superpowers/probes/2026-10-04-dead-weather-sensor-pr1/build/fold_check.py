"""Check each folded commit on its own: extract its tree, run the liveness tests that exist
at that commit plus test_store_buffers.py, and black/ruff on the package.

Usage: python fold_check.py   (reads fold-result.txt)
"""

import os
import pathlib
import shutil
import subprocess
import tarfile

WORK = pathlib.Path("D:/Entwicklung/HASI/issue8-work")
WT = WORK / "wt"
PY = "D:/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe"
TESTS = [
    "tests/test_sensor_liveness.py",
    "tests/test_sensor_liveness_store.py",
    "tests/test_sensor_liveness_coordinator.py",
    "tests/test_sensor_liveness_repair.py",
    "tests/test_store_buffers.py",
]

result = dict(
    line.split(" ", 1) for line in (WORK / "fold-result.txt").read_text().splitlines()
)
for n, sha in enumerate(result["folded"].split(), 1):
    root = WORK / f"fold-c{n}"
    shutil.rmtree(root, ignore_errors=True)
    root.mkdir()
    tar = WORK / f"fold-c{n}.tar"
    subprocess.run(["git", "-C", str(WT), "archive", "--format=tar", sha, "-o", str(tar)], check=True)
    with tarfile.open(tar) as archive:
        archive.extractall(root, filter="data")
    tar.unlink()
    shutil.copy(WT / "_local_socket_unblock.py", root)
    present = [t for t in TESTS if (root / t).exists()]
    proc = subprocess.run(
        [PY, "-m", "pytest", *present, "-p", "_local_socket_unblock", "-q", "--no-header",
         "-p", "no:cacheprovider"],
        cwd=root, env=dict(os.environ, TZ="UTC"), capture_output=True, text=True,
        encoding="utf-8", errors="replace", timeout=600,
    )
    summary = [l for l in proc.stdout.splitlines() if l.strip()][-1]
    black = subprocess.run(
        ["uvx", "black", "--check", "custom_components/irrigation_plus/"],
        cwd=root, capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    ruff = subprocess.run(
        ["uvx", "ruff", "check", "custom_components/irrigation_plus/"],
        cwd=root, capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    print(f"c{n} {sha[:8]}: {len(present)} test files -> {summary.strip('= ')} | "
          f"black exit {black.returncode} | ruff exit {ruff.returncode}")
    shutil.rmtree(root, ignore_errors=True)
