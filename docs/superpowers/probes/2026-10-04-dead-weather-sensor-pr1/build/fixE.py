"""Polish commit E from the final review (M1, M2, M4, M5 and three nits).

One list of exact replacements feeds both the implementer's prompt section
(prompts/fixes-E-edits.md) and the expected end tree (expected-E-tree.sha), so the
two cannot drift. Anchors are checked against HEAD's blobs (LF, as stored);
each must occur exactly once.

Usage: python fixE.py
"""

import os
import pathlib
import subprocess
import tempfile

WT = "D:/Entwicklung/HASI/issue8-work/wt"
WORK = pathlib.Path("D:/Entwicklung/HASI/issue8-work")

TEST = "tests/test_sensor_liveness_repair.py"
SL = "custom_components/irrigation_plus/sensor_liveness.py"
CONST = "custom_components/irrigation_plus/const.py"
GROUPS = "docs/configuration-sensor-groups.md"
EVENTS = "docs/usage-events.md"

OLD_GROUPS_1 = (
    "Irrigation Plus checks every five minutes whether the sensors of a sensor group "
    "still report. What counts is a sensor's Home Assistant device: as long as any "
    "sensor of that device from the same integration reports, a value that merely "
    "stays the same, such as a rain gauge on a dry day, counts as alive. Helpers "
    "attached to the device, such as a utility meter, do not count. A sensor without "
    "a device counts for itself. A sensor whose state is `unavailable` or `unknown` "
    "counts as silent whatever its device does. Values from an `input_number` helper "
    "never count as silent.\n"
)
NEW_GROUPS_1 = (
    "Irrigation Plus checks every five minutes whether the sensors of a sensor group "
    "still report. What counts is a sensor's Home Assistant device: as long as any "
    "sensor of that device reports, a value that merely stays the same, such as a "
    "rain gauge on a dry day, counts as alive. Only sensors of the device's own "
    "integration count: a helper attached to the device, such as a utility meter, "
    "does not keep the device alive, but a helper you map yourself is covered by the "
    "device's sensors. A sensor without a device counts for itself. A sensor whose "
    "state is `unavailable` or `unknown` counts as silent whatever its device does. "
    "Values from an `input_number` helper never count as silent.\n"
)
OLD_GROUPS_2 = (
    "A template sensor without a device whose value never changes looks silent too. "
    'If a value is meant to be fixed, use the "Static value" source instead.\n'
)
NEW_GROUPS_2 = (
    "A sensor without a device whose value does not change for three hours looks "
    "silent too, such as a template sensor, or a utility meter set up in YAML that "
    "counts rain on a dry day; one set up in the UI belongs to its source's device "
    'and is covered by it. If a value is meant to be fixed, use the "Static value" '
    "source instead.\n"
)
OLD_EVENT = (
    "Its HA device counts: while any sensor of that device from the same integration "
    "reports, a quiet value such as a rain gauge on a dry day is not stale. Carries "
    "`mapping_id`, `mapping`, `entity_id`, `device_id` (null without a device), "
    "`fields`, `since` (its last sign of life), `until` (null while it is silent; "
    "both in Home Assistant's time zone, with offset) and `stale` "
)
NEW_EVENT = (
    "Its HA device counts: while any sensor of the device's own integration reports, "
    "a quiet value such as a rain gauge on a dry day, or a helper mapped from that "
    "device, is not stale. Carries `mapping_id`, `mapping`, `entity_id`, `device_id` "
    "(null without a device), `fields`, `since` (its last sign of life) and `until` "
    "(null while it is silent), both in Home Assistant's time zone with offset, and "
    "`stale` "
)

FIXES = [
    (
        "1a",
        TEST,
        "from homeassistant.core import callback\n",
        "from homeassistant.const import (\n"
        "    EVENT_HOMEASSISTANT_FINAL_WRITE,\n"
        "    EVENT_HOMEASSISTANT_STOP,\n"
        ")\n"
        "from homeassistant.core import CoreState, callback\n",
    ),
    (
        "1b",
        TEST,
        "    await coord.store.async_save()\n",
        "    # A clean stop as Home Assistant runs it, with nothing saved by hand: what\n"
        "    # reaches the disk is the store's pending write, flushed at FINAL_WRITE.\n"
        "    hass.set_state(CoreState.stopping)\n"
        "    hass.bus.async_fire(EVENT_HOMEASSISTANT_STOP)\n"
        "    await hass.async_block_till_done()\n"
        "    hass.set_state(CoreState.final_write)\n"
        "    hass.bus.async_fire(EVENT_HOMEASSISTANT_FINAL_WRITE)\n"
        "    await hass.async_block_till_done()\n"
        "    hass.set_state(CoreState.running)\n",
    ),
    (
        "2a",
        SL,
        "    ``start`` is its last sign of life, ``end`` its first report afterwards (None\n"
        "    while it is still silent). Stored as ISO strings on HA's clock: the frame the\n"
        "    reading buffer's row stamps are in.\n",
        "    ``start`` is its last sign of life, ``end`` its first report afterwards, or\n"
        "    the moment its group stopped reading it (None while it is still silent).\n"
        "    Stored as ISO strings on HA's clock: the frame the reading buffer's row\n"
        "    stamps are in.\n",
    ),
    (
        "2b",
        SL,
        "    ``start``. This only dates a return; whether the outage has ended is\n"
        "    ``last_sign_of_life``'s call.\n",
        "    ``start``. This only dates a return; whether the outage has ended,\n"
        "    ``advance_outages`` decides from the field's last sign of life.\n",
    ),
    (
        "2c",
        SL,
        "    where another integration owns the device (MQTT ranks low) or no owner is\n"
        "    recorded.",
        "    where the device is shared and another integration owns it, or no owner is\n"
        "    recorded.",
    ),
    (
        "3",
        CONST,
        "# --- Weather-sensor liveness (#188) -------------------------------------------\n",
        "",
    ),
    ("4a", GROUPS, OLD_GROUPS_1, NEW_GROUPS_1),
    ("4b", GROUPS, OLD_GROUPS_2, NEW_GROUPS_2),
    ("5", EVENTS, OLD_EVENT, NEW_EVENT),
]


def git(*args, stdin=None, env=None):
    return subprocess.run(
        ["git", "-C", WT, *args],
        input=stdin,
        capture_output=True,
        check=True,
        env=env,
    ).stdout


def main():
    blobs = {}
    for _, path, _, _ in FIXES:
        if path not in blobs:
            blobs[path] = git("cat-file", "blob", f"HEAD:{path}").decode("utf-8")
    bad = 0
    for name, path, old, new in FIXES:
        text = blobs[path]
        if "\r\n" in text:
            raise SystemExit(f"{path}: blob holds CRLF, anchors are LF")
        count = text.count(old)
        if count != 1:
            bad += 1
            print(f"{name}: anchor found {count}x in {path}")
            continue
        blobs[path] = text.replace(old, new)
    if bad:
        raise SystemExit(f"{bad} anchors not found exactly once")

    index = pathlib.Path(tempfile.mkdtemp(dir=WORK)) / "index"
    env = dict(os.environ, GIT_INDEX_FILE=str(index))
    git("read-tree", "HEAD", env=env)
    for path, text in blobs.items():
        sha = git("hash-object", "-w", "--stdin", stdin=text.encode("utf-8"))
        sha = sha.decode().strip()
        git("update-index", "--cacheinfo", f"100644,{sha},{path}", env=env)
    tree = git("write-tree", env=env).decode().strip()
    index.unlink()
    index.parent.rmdir()
    (WORK / "expected-E-tree.sha").write_text(tree + "\n", encoding="utf-8")
    print("expected tree after E:", tree)

    out = []
    for name, path, old, new in FIXES:
        out.append(f"### Änderung {name} — `{path}`\n")
        out.append("Ersetze exakt (einmal vorhanden):\n")
        out.append("~~~~text\n" + old + ("" if old.endswith("\n") else "\n") + "~~~~\n")
        if new:
            out.append("durch:\n")
            out.append("~~~~text\n" + new + ("" if new.endswith("\n") else "\n") + "~~~~\n")
        else:
            out.append("durch NICHTS (die ganze Zeile entfällt, samt Zeilenende).\n")
    (WORK / "prompts" / "fixes-E-edits.md").write_text("\n".join(out), encoding="utf-8")
    print("edits written:", len(FIXES))


main()
