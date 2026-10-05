"""Mechanical spec check for the seasonal-outlook plan, task by task.

The plan dictates every edit verbatim, so the expected state after task N is
"base + the plan's blocks of tasks 1..N". This script compares the committed
tree with that state byte for byte (LF), checks that nothing else changed,
that each task is exactly one commit with the plan's message, that the
working tree is clean, and that no text points at our own tracker.

The bundles cannot be derived from plan blocks; from task 8 on they are
compared with the probe patch's post-image blob ids, and so is every other
file once task 9 is done (the probe patch is the tested end state).

Usage:
  python spec_check.py precheck   # plan blocks (all tasks) vs probe patch, no worktree state used
  python spec_check.py <N>        # committed state after task N
"""

import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
from probe_plan import parse  # noqa: E402

PLAN = Path(r"D:\Entwicklung\HASI\HAsmartirrigation\docs\superpowers\plans\2026-10-05-seasonal-outlook.md")
WT = HERE / "wt"
BASE = "bbf2e151"
PROBE = HERE / "probe-2026-10-05.patch"
DEVIATIONS = HERE / "deviations.md"
BUNDLES = [
    "custom_components/irrigation_plus/frontend/dist/irrigation-plus.js",
    "custom_components/irrigation_plus/frontend/dist/irrigation-plus-card-impl.js",
]
TRACKER = re.compile(r"Eifel-Joe|spec D[0-9]|spec §|Task [0-9]|M[0-9][a-z]?:|PR [A-T]\b")


def git(*args, input_bytes=None):
    proc = subprocess.run(["git", "-C", str(WT), *args], capture_output=True, input=input_bytes)
    if proc.returncode != 0:
        raise SystemExit(f"git {' '.join(args)} failed: {proc.stderr.decode(errors='replace')}")
    return proc.stdout


def show(rev, path):
    return git("show", f"{rev}:{path}").decode("utf-8").replace("\r\n", "\n")


def blob_id(text):
    return git("hash-object", "--stdin", input_bytes=text.encode("utf-8")).decode().strip()


def probe_post_images():
    """path -> post-image blob id (abbreviated) from the probe patch."""
    out = {}
    path = None
    for line in PROBE.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^diff --git a/(\S+) b/", line)
        if m:
            path = m.group(1)
            continue
        m = re.match(r"^index [0-9a-f]+\.\.([0-9a-f]+)", line)
        if m and path:
            out[path] = m.group(1)
            path = None
    return out


def plan_messages(plan_text):
    """task -> commit message from the plan's heredoc (trailer lines dropped)."""
    msgs = {}
    task = None
    lines = plan_text.split("\n")
    i = 0
    while i < len(lines):
        m = re.match(r"^### Task (\d+):", lines[i])
        if m:
            task = int(m.group(1))
        if lines[i].startswith("git commit -F - <<'EOF'"):
            body = []
            i += 1
            while lines[i] != "EOF":
                body.append(lines[i])
                i += 1
            msgs[task] = strip_trailers("\n".join(body))
        i += 1
    return msgs


def deviation_messages():
    """task -> commit message from a '**Commit-Message:**' block in deviations.md."""
    if not DEVIATIONS.exists():
        return {}
    msgs = {}
    task = None
    lines = DEVIATIONS.read_text(encoding="utf-8").split("\n")
    i = 0
    while i < len(lines):
        m = re.match(r"^### Task (\d+):", lines[i])
        if m:
            task = int(m.group(1))
        if lines[i].strip() == "**Commit-Message:**":
            i += 1
            while not lines[i].startswith("```"):
                i += 1
            i += 1
            body = []
            while not lines[i].startswith("```"):
                body.append(lines[i])
                i += 1
            msgs[task] = strip_trailers("\n".join(body))
        i += 1
    return msgs


def strip_trailers(msg):
    kept = [ln for ln in msg.strip().split("\n") if not ln.startswith("Co-Authored-By:")]
    return "\n".join(kept).strip()


def expected_state(tasks, upto, deviations=None):
    """base + the plan's blocks of tasks 1..upto, each task followed by its deviation blocks."""
    deviations = deviations or {}
    state = {}
    for task in sorted(set(tasks) | set(deviations)):
        if task > upto:
            break
        for kind, rel, a, b in tasks.get(task, []) + deviations.get(task, []):
            if rel not in state:
                state[rel] = show(BASE, rel)
            text = state[rel]
            if kind == "replace":
                count = text.count(a)
                if count != 1:
                    raise SystemExit(f"ANCHOR task {task} {rel}: {count}x")
                text = text.replace(a, b)
            else:
                if not text.endswith("\n"):
                    text += "\n"
                text += a
            state[rel] = text
    return state


def precheck(tasks):
    probe = probe_post_images()
    state = expected_state(tasks, 99)
    bad = 0
    for rel, text in sorted(state.items()):
        want = probe.get(rel)
        got = blob_id(text)
        ok = want is not None and got.startswith(want)
        bad += not ok
        print(f"{'OK  ' if ok else 'DIFF'} {rel} plan={got[:8]} probe={want}")
    missing = sorted(set(probe) - set(state) - set(BUNDLES))
    for rel in missing:
        bad += 1
        print(f"MISS {rel} in probe, not in plan blocks")
    print("PRECHECK", "OK" if not bad else f"{bad} PROBLEM(S)")


def check(tasks, upto):
    problems = []
    deviations = parse(DEVIATIONS.read_text(encoding="utf-8")) if DEVIATIONS.exists() else {}
    deviated = {rel for t, edits in deviations.items() if t <= upto for _k, rel, _a, _b in edits}
    state = expected_state(tasks, upto, deviations)

    # 1. every planned file: committed == base + blocks, worktree == committed
    for rel, text in sorted(state.items()):
        committed = show("HEAD", rel)
        if committed != text:
            problems.append(f"CONTENT {rel}: HEAD differs from base + plan blocks")
        work = (WT / rel).read_bytes().decode("utf-8").replace("\r\n", "\n")
        if work != committed:
            problems.append(f"WORKTREE {rel}: differs from HEAD")

    # 2. nothing else changed
    changed = set(git("diff", "--name-only", BASE, "HEAD").decode().split())
    allowed = set(state) | (set(BUNDLES) if upto >= 8 else set())
    for rel in sorted(changed - allowed):
        problems.append(f"EXTRA {rel} changed but not in the plan up to task {upto}")
    for rel in sorted(allowed - changed):
        problems.append(f"MISSING {rel} not changed")

    # 3. bundles (task 8+) and, after task 9, everything == probe end state.
    # A deviation in the frontend sources changes the bundles on purpose; then
    # their freshness is proven by a rebuild (npm run build -> no diff), not here.
    probe = probe_post_images()
    # Only the view sources and the English catalogue are bundled; the other
    # catalogues are fetched at runtime (frontend/localize/localize.ts).
    frontend_deviated = any(
        "/frontend/src/" in rel or rel.endswith("/frontend/localize/languages/en.json")
        for rel in deviated
    )
    if upto >= 8 and frontend_deviated:
        print("bundles: probe comparison skipped (frontend deviation) -- prove freshness by rebuild")
    elif upto >= 8:
        for rel in BUNDLES:
            got = git("rev-parse", f"HEAD:{rel}").decode().strip()
            if not got.startswith(probe[rel]):
                problems.append(f"BUNDLE {rel}: {got[:8]} != probe {probe[rel]}")
    if upto >= 9:
        for rel, want in sorted(probe.items()):
            if rel in deviated or (frontend_deviated and rel in BUNDLES):
                continue  # checked above against base + plan + deviations
            got = git("rev-parse", f"HEAD:{rel}").decode().strip()
            if not got.startswith(want):
                problems.append(f"PROBE {rel}: {got[:8]} != probe {want}")
    if deviated:
        print(f"deviations applied (tasks <= {upto}): {sorted(deviated)}")

    # 4. one commit per task, message as in the plan (trailers aside)
    msgs = plan_messages(PLAN.read_text(encoding="utf-8"))
    msgs.update(deviation_messages())
    shas = git("rev-list", "--reverse", f"{BASE}..HEAD").decode().split()
    if len(shas) != upto:
        problems.append(f"COMMITS {len(shas)} on top of {BASE}, expected {upto}")
    for task, sha in zip(range(1, upto + 1), shas):
        body = git("log", "-1", "--format=%B", sha).decode("utf-8")
        if strip_trailers(body) != msgs[task]:
            problems.append(f"MESSAGE task {task} ({sha[:8]}) differs from the plan")
            print(f"--- plan task {task}:\n{msgs[task]}\n--- commit:\n{strip_trailers(body)}")

    # 5. clean tree
    status = git("status", "--porcelain").decode().strip()
    if status:
        problems.append(f"DIRTY\n{status}")

    # 6. no pointer to our tracker, neither in the diff nor in messages
    diff = git("diff", BASE, "HEAD", "--", "custom_components/", "tests/", "docs/").decode(
        "utf-8", errors="replace")
    for ln in diff.splitlines():
        if ln.startswith("+") and not ln.startswith("+++") and TRACKER.search(ln):
            problems.append(f"TRACKER diff: {ln[:120]}")
    log = git("log", f"{BASE}..HEAD", "--format=%B").decode("utf-8")
    if "Eifel-Joe#" in log:
        problems.append("TRACKER commit message mentions Eifel-Joe#")

    print(f"HEAD {git('rev-parse', '--short', 'HEAD').decode().strip()}, task {upto}, "
          f"{len(state)} planned file(s), {len(changed)} changed")
    for p in problems:
        print(p)
    print("SPEC CHECK", "OK" if not problems else f"{len(problems)} PROBLEM(S)")


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    tasks = parse(PLAN.read_text(encoding="utf-8"))
    if sys.argv[1] == "precheck":
        precheck(tasks)
    else:
        check(tasks, int(sys.argv[1]))


if __name__ == "__main__":
    main()
