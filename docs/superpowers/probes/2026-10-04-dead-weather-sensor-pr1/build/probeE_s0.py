"""Counter-probe for commit E in the dry-run copy probeE/: with the scheduled save
disabled, the restart test must fail; restored, it must pass."""

import hashlib
import os
import pathlib
import subprocess

ROOT = pathlib.Path("D:/Entwicklung/HASI/issue8-work/probeE")
PY = "D:/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe"
STORE = ROOT / "custom_components/irrigation_plus/store.py"
TARGET = (
    "tests/test_sensor_liveness_repair.py::"
    "test_the_notice_survives_a_restart_in_the_middle_of_an_outage"
)
OLD = "        self._store.async_delay_save(self._data_to_save_scheduled, SAVE_DELAY)\n"


def run():
    proc = subprocess.run(
        [PY, "-m", "pytest", TARGET, "-p", "_local_socket_unblock", "-q",
         "--no-header", "-p", "no:cacheprovider"],
        cwd=ROOT, env=dict(os.environ, TZ="UTC"), capture_output=True,
        text=True, encoding="utf-8", errors="replace", timeout=300,
    )
    lines = [l for l in proc.stdout.splitlines() if l.strip()]
    return lines[-1], [l for l in lines if l.startswith("E ")][:2]


original = STORE.read_bytes()
before = hashlib.sha256(original).hexdigest()
text = original.decode("utf-8")
old = OLD.replace("\n", "\r\n") if "\r\n" in text else OLD
assert text.count(old) == 1
try:
    STORE.write_bytes(text.replace(old, old[: len(old) - len(old.lstrip())] + "return" + old[len(old.rstrip()):]).encode("utf-8"))
    print("S0  :", *run())
finally:
    STORE.write_bytes(original)
print("back:", *run())
print("store.py restored:", hashlib.sha256(STORE.read_bytes()).hexdigest() == before)
