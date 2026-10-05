"""Probe for review point M1: does the restart test, stopped through HA's shutdown
events instead of a hand-made save, see (a) the Task 7 loss of signs of life and
(b) a broken scheduled-save path? Runs in the throwaway copy m1probe/ only."""

import hashlib
import os
import pathlib
import subprocess

ROOT = pathlib.Path("D:/Entwicklung/HASI/issue8-work/m1probe")
PY = "D:/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe"
STORE = ROOT / "custom_components/irrigation_plus/store.py"
NEW = ROOT / "tests/test_sensor_liveness_repair.py"
OLD = ROOT / "tests/test_zz_old_restart.py"
NOFW = ROOT / "tests/test_zz_nofw_restart.py"
TEST = "test_the_notice_survives_a_restart_in_the_middle_of_an_outage"

MUTATIONS = {
    "none": None,
    "T7 flush only on buffers": (
        "        if not (self._buffers_dirty or self._last_seen_dirty):\n",
        "        if not self._buffers_dirty:\n",
    ),
    "S0 scheduled save is a no-op": (
        "        self._store.async_delay_save(self._data_to_save_scheduled, SAVE_DELAY)\n",
        "        return\n",
    ),
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(target):
    env = dict(os.environ, TZ="UTC")
    proc = subprocess.Popen(
        [PY, "-m", "pytest", target, "-p", "_local_socket_unblock", "-q", "-x",
         "--no-header", "-p", "no:cacheprovider"],
        cwd=ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, encoding="utf-8", errors="replace",
    )
    try:
        out, _ = proc.communicate(timeout=300)
    except subprocess.TimeoutExpired:
        subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                       capture_output=True)
        return "HANG", ""
    last = [l for l in out.splitlines() if l.strip()][-1]
    fail = [l for l in out.splitlines() if l.startswith("E ")][:3]
    return last, "\n      ".join(fail)


def main():
    head = subprocess.run(
        ["git", "-C", "D:/Entwicklung/HASI/issue8-work/wt", "show",
         "HEAD:tests/test_sensor_liveness_repair.py"],
        capture_output=True, text=True, encoding="utf-8", check=True,
    ).stdout
    OLD.write_text(head, encoding="utf-8", newline="")
    new_text = NEW.read_bytes().decode("utf-8")
    drop = (
        "    hass.bus.async_fire(EVENT_HOMEASSISTANT_FINAL_WRITE)\n"
        "    await hass.async_block_till_done()\n"
    )
    if "\r\n" in new_text:
        drop = drop.replace("\n", "\r\n")
    assert new_text.count(drop) == 1, "FINAL_WRITE anchor"
    NOFW.write_text(new_text.replace(drop, ""), encoding="utf-8", newline="")

    original = STORE.read_bytes()
    before = sha(STORE)
    try:
        for name, mutation in MUTATIONS.items():
            text = original.decode("utf-8")
            if mutation is not None:
                old, new = mutation
                if "\r\n" in text:
                    old, new = old.replace("\n", "\r\n"), new.replace("\n", "\r\n")
                assert text.count(old) == 1, f"anchor of {name}"
                STORE.write_bytes(text.replace(old, new).encode("utf-8"))
            print(f"== mutation: {name}")
            for label, path in (("new test", NEW), ("old test (HEAD)", OLD),
                                ("new test without FINAL_WRITE", NOFW)):
                last, fail = run(f"tests/{path.name}::{TEST}")
                print(f"   {label:30s} {last}")
                if fail:
                    print(f"      {fail}")
            if name == "T7 flush only on buffers":
                last, fail = run("tests/test_sensor_liveness_store.py")
                print(f"   {'store tests':30s} {last}")
            STORE.write_bytes(original)
    finally:
        STORE.write_bytes(original)
        OLD.unlink(missing_ok=True)
        NOFW.unlink(missing_ok=True)
    print("store.py restored:", sha(STORE) == before)


main()
