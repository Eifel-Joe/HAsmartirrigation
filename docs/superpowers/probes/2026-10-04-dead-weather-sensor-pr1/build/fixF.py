"""Fix commit F from the review of commit E (F1, F2, F3).

One list of exact replacements feeds both the implementer's prompt section
(prompts/fixes-F-edits.md) and the expected end tree (expected-F-tree.sha), so the
two cannot drift. Anchors are checked against HEAD's blobs (LF, as stored); each
must occur exactly once. HEAD must be b321c0bb.

Usage: python fixF.py
"""

import os
import pathlib
import subprocess
import tempfile

WT = "D:/Entwicklung/HASI/issue8-work/wt"
WORK = pathlib.Path("D:/Entwicklung/HASI/issue8-work")
BASE = "b321c0bba00dcd7b00ed88b246814dcdac258afe"

COORD = "tests/test_sensor_liveness_coordinator.py"
GROUPS = "docs/configuration-sensor-groups.md"
EVENTS = "docs/usage-events.md"

KILLER_TEST = '''async def test_the_mapped_sensors_own_integration_vouches_on_a_shared_device(hass):
    """The device belongs to one integration, a sensor of another sits on it: that
    other integration's second sensor vouches for it, next to the owner's."""
    owner = MockConfigEntry(domain="test")
    owner.add_to_hass(hass)
    other = MockConfigEntry(domain="other")
    other.add_to_hass(hass)
    device = dr.async_get(hass).async_get_or_create(
        config_entry_id=owner.entry_id,
        identifiers={("test", "station")},
        name="Station",
    )
    registry = er.async_get(hass)
    mapped = registry.async_get_or_create(
        "sensor", "other", "rain", device_id=device.id, config_entry=other
    )
    twin = registry.async_get_or_create(
        "sensor", "other", "wind", device_id=device.id, config_entry=other
    )
    station = registry.async_get_or_create(
        "sensor", "test", "temp", device_id=device.id, config_entry=owner
    )

    device_id, siblings = _entities_of_device(hass, mapped.entity_id)

    assert device_id == device.id
    assert sorted(siblings) == sorted([twin.entity_id, station.entity_id])
'''

EVENT_LINE = 'EVENT = f"{const.DOMAIN}_{const.EVENT_WEATHER_STALE}"\n'

OLD_GROUPS_2 = (
    "A sensor without a device whose value does not change for three hours looks "
    "silent too, such as a template sensor, or a utility meter set up in YAML that "
    "counts rain on a dry day; one set up in the UI belongs to its source's device "
    'and is covered by it. If a value is meant to be fixed, use the "Static value" '
    "source instead.\n"
)
NEW_GROUPS_2 = (
    "A sensor without a device that reports only when its value changes, such as a "
    "template sensor or a utility meter set up in YAML that counts rain, looks silent "
    "too once the value has stayed the same for three hours, on a dry day for "
    "instance. A utility meter set up in the UI belongs to its source's device, if "
    "the source has one, and is covered by it. If a value is meant to be fixed, use "
    'the "Static value" source instead.\n'
)

FIXES = [
    ("F3", COORD, EVENT_LINE, KILLER_TEST + "\n\n" + EVENT_LINE),
    ("F1", GROUPS, OLD_GROUPS_2, NEW_GROUPS_2),
    (
        "F2",
        EVENTS,
        "or a helper mapped from that device, is not stale.",
        "or a helper attached to that device, is not stale.",
    ),
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
    head = git("rev-parse", "HEAD").decode().strip()
    if head != BASE:
        raise SystemExit(f"HEAD is {head}, expected {BASE}")
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
    (WORK / "expected-F-tree.sha").write_text(tree + "\n", encoding="utf-8")
    print("expected tree after F:", tree)

    out = []
    for name, path, old, new in FIXES:
        out.append(f"### Änderung {name} — `{path}`\n")
        out.append("Ersetze exakt (einmal vorhanden):\n")
        out.append("~~~~text\n" + old + ("" if old.endswith("\n") else "\n") + "~~~~\n")
        out.append("durch:\n")
        out.append("~~~~text\n" + new + ("" if new.endswith("\n") else "\n") + "~~~~\n")
    (WORK / "prompts" / "fixes-F-edits.md").write_text("\n".join(out), encoding="utf-8")
    print("edits written:", len(FIXES))


main()
