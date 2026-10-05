"""Counter-probe for commit F in the dry-run copy probeF/: M60 (the mapped entity's
own integration no longer vouches where another integration owns the device) must
fail the new test and nothing else that passes now; restored, all pass again."""

import hashlib
import os
import pathlib
import subprocess

ROOT = pathlib.Path("D:/Entwicklung/HASI/issue8-work/probeF")
PY = "D:/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe"
SL = ROOT / "custom_components/irrigation_plus/sensor_liveness.py"
OLD = "    vouching = {entry.config_entry_id, owner} - {None}\n"
NEW = "    vouching = ({entry.config_entry_id} if owner is None else {owner}) - {None}\n"
TESTS = [
    "tests/test_sensor_liveness.py",
    "tests/test_sensor_liveness_store.py",
    "tests/test_sensor_liveness_coordinator.py",
    "tests/test_sensor_liveness_repair.py",
]


def run():
    proc = subprocess.run(
        [PY, "-m", "pytest", *TESTS, "-p", "_local_socket_unblock", "-q",
         "--no-header", "-rfE", "-p", "no:cacheprovider"],
        cwd=ROOT, env=dict(os.environ, TZ="UTC"), capture_output=True,
        text=True, encoding="utf-8", errors="replace", timeout=300,
    )
    lines = [l for l in proc.stdout.splitlines() if l.strip()]
    failed = [l.split(" ")[1].split("::")[-1] for l in lines if l.startswith(("FAILED ", "ERROR "))]
    return lines[-1], failed


original = SL.read_bytes()
before = hashlib.sha256(original).hexdigest()
text = original.decode("utf-8")
crlf = "\r\n" in text
old, new = (OLD.replace("\n", "\r\n"), NEW.replace("\n", "\r\n")) if crlf else (OLD, NEW)
assert text.count(old) == 1
try:
    SL.write_bytes(text.replace(old, new).encode("utf-8"))
    print("M60 :", *run())
finally:
    SL.write_bytes(original)
print("back:", *run())
print("sensor_liveness.py restored:", hashlib.sha256(SL.read_bytes()).hexdigest() == before)
