"""Fold the per-task history of fix/stale-weather-sensor into four feature commits.

Each changed file lands in exactly one commit, in its final version (taken from TIP);
the commits are built on BASE with git plumbing, so the working tree is never touched.
The last folded commit's tree must equal TIP's tree. Messages describe the final state.

Usage: python fold.py <TIP sha>   -> prints the folded commit SHAs, writes fold-result.txt
"""

import os
import pathlib
import subprocess
import sys
import tempfile

WT = "D:/Entwicklung/HASI/issue8-work/wt"
WORK = pathlib.Path("D:/Entwicklung/HASI/issue8-work")
BASE = "e9c79ec480fb07284312b7a751f490f88bfff512"
TIP = sys.argv[1]

IP = "custom_components/irrigation_plus"
LANGS = ["de", "en", "es", "fr", "it", "nl", "no", "sk"]
TRAILER = "\n\nCo-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>\n"

COMMITS = [
    (
        [f"{IP}/const.py", f"{IP}/store.py", "tests/test_sensor_liveness_store.py"],
        "feat(liveness): two fields on the sensor group, for outages and signs of life\n"
        "\n"
        "A sensor group keeps a record of its sensors' outages (sensor_outages)\n"
        "and each sensor's last sign of life (sensor_last_seen), stored like\n"
        "radiation_calibration with no storage version change; a store without\n"
        "them loads, and a last-seen value that is not a dictionary is replaced\n"
        "on load. The signs of life are refreshed in memory without a save of their\n"
        "own and ride along with the next one; a clean shutdown writes them when\n"
        "they changed, as it already does for unwritten buffer rows. The\n"
        "constants of the check sit in const.py: a fixed limit of three hours, a\n"
        "check every five minutes, ten minutes of grace after setup, closed\n"
        "outages kept for seven days.",
    ),
    (
        [f"{IP}/sensor_liveness.py"]
        + [f"{IP}/translations/{lang}.json" for lang in LANGS]
        + ["tests/test_sensor_liveness.py"],
        "feat(liveness): the rules of the check, and the repair notice in eight languages\n"
        "\n"
        "sensor_liveness.py holds the rules of the check as plain functions and\n"
        "the coordinator's part as a mixin. A sensor field is alive while a\n"
        "sensor of its Home Assistant device has reported within the limit. Only\n"
        "sensors and binary sensors of the integration that owns the device, or\n"
        "of the mapped entity's own integration, vouch for it, so neither a\n"
        "helper attached to the device nor an update entity keeps a dead station\n"
        "alive. A field whose own entity is unavailable or unknown is silent\n"
        "whatever its device does, and input_number values are never watched.\n"
        "An outage starts at the last sign of life and ends at the field's own\n"
        "return; a field that does not change when it comes back takes the\n"
        "earliest change of a vouching sensor. The repair notice names the\n"
        "silent sensors and since when, and says that the last reported values\n"
        "are still used. The event carries both stamps with Home Assistant's UTC\n"
        "offset; stored stamps are naive on Home Assistant's clock.",
    ),
    (
        [
            f"{IP}/__init__.py",
            f"{IP}/calculation.py",
            "tests/test_sensor_liveness_coordinator.py",
            "tests/test_sensor_liveness_repair.py",
        ],
        "feat(liveness): the check runs in the coordinator\n"
        "\n"
        "Every five minutes, after ten minutes of grace at setup, the\n"
        "coordinator checks each sensor group, one at a time so that a broken\n"
        "group cannot stop the others. It keeps the repair notice and the\n"
        "outage record current, fires irrigation_plus_weather_stale when an\n"
        "outage starts and when it ends, logs a WARNING at the start and an INFO\n"
        "at the end, and schedules a save only when the record changes. At setup\n"
        "an outage that is still open shows its notice at once, so the notice\n"
        "survives a restart. Replacing a sensor, deleting the group and \"reset\n"
        "weather data\" end open outages with their end event and empty the\n"
        "record but keep the signs of life, so a sensor the group still reads\n"
        "and that is still silent is reported again with its real start. The\n"
        "docstring of _prune_mapping_buffer now says that a field's last row\n"
        "survives the retention cap on purpose.",
    ),
    (
        ["docs/configuration-sensor-groups.md", "docs/usage-events.md"],
        "docs(liveness): when a sensor goes silent, and the weather_stale event\n"
        "\n"
        "The sensor-group page explains the check, the fixed three hours and\n"
        "the false alarms that come with them: an integration that updates less\n"
        "often, such as a cloud service polled every six hours, and a sensor\n"
        "without a device that writes only on change while its value stays the\n"
        "same. The events page lists irrigation_plus_weather_stale with its\n"
        "fields.",
    ),
]


def git(*args, stdin=None, env=None):
    out = subprocess.run(
        ["git", "-C", WT, *args], input=stdin, capture_output=True, check=True, env=env
    ).stdout
    return out.decode("utf-8").strip()


def main():
    changed = set(git("diff", "--name-only", BASE, TIP).splitlines())
    planned = [f for files, _ in COMMITS for f in files]
    if len(planned) != len(set(planned)):
        raise SystemExit("a file is planned twice")
    if set(planned) != changed:
        raise SystemExit(
            f"planned vs changed differ: missing {sorted(changed - set(planned))}, "
            f"extra {sorted(set(planned) - changed)}"
        )
    index = pathlib.Path(tempfile.mkdtemp(dir=WORK)) / "index"
    env = dict(os.environ, GIT_INDEX_FILE=str(index))
    git("read-tree", BASE, env=env)
    parent = BASE
    shas = []
    for files, message in COMMITS:
        for path in files:
            entry = git("ls-tree", TIP, "--", path)  # "<mode> blob <sha>\t<path>"
            mode, _, rest = entry.partition(" ")
            sha = rest.split()[1]
            git("update-index", "--add", "--cacheinfo", f"{mode},{sha},{path}", env=env)
        tree = git("write-tree", env=env)
        parent = git(
            "commit-tree", tree, "-p", parent, "-F", "-",
            stdin=(message + TRAILER).encode("utf-8"),
        )
        shas.append(parent)
    index.unlink()
    index.parent.rmdir()
    final_tree = git("rev-parse", f"{parent}^{{tree}}")
    tip_tree = git("rev-parse", f"{TIP}^{{tree}}")
    print("folded:", " ".join(s[:8] for s in shas))
    print("final tree", final_tree, "tip tree", tip_tree, "EQUAL" if final_tree == tip_tree else "DIFFER")
    (WORK / "fold-result.txt").write_text(
        f"tip {TIP}\nfolded {' '.join(shas)}\nfinal_tree {final_tree}\ntip_tree {tip_tree}\n",
        encoding="utf-8",
    )
    if final_tree != tip_tree:
        raise SystemExit(1)


main()
