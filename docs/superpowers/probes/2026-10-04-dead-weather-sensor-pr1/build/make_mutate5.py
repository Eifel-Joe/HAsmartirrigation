"""probe_mutate5.py = probe_mutate4.py plus M60 from the review of commit E (F3): the
mapped entity's own integration no longer vouches where another integration owns
the device. Verifies every anchor exactly once against the given root before writing.

Usage: python make_mutate5.py <root to verify against>
"""

import ast
import pathlib
import sys

WORK = pathlib.Path("D:/Entwicklung/HASI/issue8-work")
ROOT = pathlib.Path(sys.argv[1])
src = (WORK / "probe_mutate4.py").read_text(encoding="utf-8")
tree = ast.parse(src)
node = next(
    n
    for n in tree.body
    if isinstance(n, ast.Assign) and getattr(n.targets[0], "id", "") == "MUTATIONS"
)
lines = src.split("\n")
# The list's closing bracket is on its own line (end_lineno, 1-based).
assert lines[node.end_lineno - 1].strip() == "]", lines[node.end_lineno - 1]
m60 = (
    "    (60, SL, "
    + repr("    vouching = {entry.config_entry_id, owner} - {None}\n")
    + ", "
    + repr("    vouching = ({entry.config_entry_id} if owner is None else {owner}) - {None}\n")
    + "),"
)
lines.insert(node.end_lineno - 1, m60)
out = "\n".join(lines)
out = out.replace(
    "build worktree. Anchors as of the end of fix round C.",
    "build worktree. Anchors as of the end of fix round C; M60 from the review of the\n"
    "polish commit (the mapped entity's own integration on a shared device).",
)
(WORK / "probe_mutate5.py").write_text(out, encoding="utf-8")

final = ast.parse(out)
mnode = next(
    n
    for n in final.body
    if isinstance(n, ast.Assign) and getattr(n.targets[0], "id", "") == "MUTATIONS"
)
files = {
    "SL": "custom_components/irrigation_plus/sensor_liveness.py",
    "INIT": "custom_components/irrigation_plus/__init__.py",
    'IP / "calculation.py"': "custom_components/irrigation_plus/calculation.py",
    'IP / "store.py"': "custom_components/irrigation_plus/store.py",
    'IP / "const.py"': "custom_components/irrigation_plus/const.py",
}
bad = 0
for elt in mnode.value.elts:
    number = elt.elts[0].value
    rel = files[ast.get_source_segment(out, elt.elts[1])]
    anchor = ast.literal_eval(elt.elts[2])
    text = (ROOT / rel).read_bytes().decode("utf-8").replace("\r\n", "\n")
    if text.count(anchor) != 1:
        bad += 1
        print(f"M{number:02d}: anchor found {text.count(anchor)}x in {rel}")
print(f"{len(mnode.value.elts)} mutations, {bad} anchors not found exactly once")
