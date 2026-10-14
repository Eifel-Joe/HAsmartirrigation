"""Build the PR 3 plan from the hand-written skeleton and the probe's task commits.

Every code and test block in the plan is taken from the probe commit of its task
(`probe T<n>: ...` on the probe worktree), so the plan carries exactly what ran
green there. Usage:

    python make_plan.py <probe-worktree> <out.md>
"""

import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
WT = Path(sys.argv[1])
OUT = Path(sys.argv[2])
BASE = "6fa424e8"

COUNTS = {"T1": 25, "T2": 17, "T3": 9, "T4": 10, "T6": 8}


def git(*args):
    return subprocess.run(
        ["git", "-C", str(WT), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    ).stdout


def task_commits():
    out = {}
    for line in git("log", "--format=%H %s", f"{BASE}..HEAD").splitlines():
        sha, subject = line.split(" ", 1)
        m = re.match(r"probe (T\d+):", subject)
        if m:
            out[m.group(1)] = sha
    return out


def changed(sha):
    """``[(status, path)]`` of one commit."""
    rows = git("diff-tree", "--no-commit-id", "--name-status", "-r", sha).splitlines()
    return [tuple(row.split("\t", 1)) for row in rows]


def diff_of(sha, path):
    text = git("show", "--format=", "--unified=3", sha, "--", path)
    return text.rstrip("\n")


def file_at(sha, path):
    return git("show", f"{sha}:{path}").rstrip("\n")


def block(kind, sha, entries):
    parts = []
    for status, path in entries:
        if status == "A":
            parts.append(f"Create `{path}`:\n\n```python\n{file_at(sha, path)}\n```")
        else:
            parts.append(f"Modify `{path}`:\n\n```diff\n{diff_of(sha, path)}\n```")
    return "\n\n".join(parts) if parts else f"_(keine {kind}-Änderung in diesem Task)_"


def main():
    skeleton = (HERE / "plan-skeleton.md").read_text(encoding="utf-8")
    tasks = (HERE / "plan-tasks.md").read_text(encoding="utf-8")
    commits = task_commits()
    missing = [f"T{n}" for n in range(1, 10) if f"T{n}" not in commits]
    if missing:
        sys.exit(f"probe commits missing: {missing}")
    for name, sha in commits.items():
        entries = changed(sha)
        tests = [e for e in entries if e[1].startswith("tests/")]
        docs = [e for e in entries if e[1].startswith("docs/")]
        code = [
            e
            for e in entries
            if e[1].startswith("custom_components/")
            and "/frontend/dist/" not in e[1]
            and "/frontend/localize/" not in e[1]
        ]
        tasks = tasks.replace(f"@@TEST {name}@@", block("Test", sha, tests))
        tasks = tasks.replace(f"@@CODE {name}@@", block("Code", sha, code))
        tasks = tasks.replace(f"@@DOCS {name}@@", block("Doku", sha, docs))
        if name in COUNTS:
            tasks = tasks.replace(f"@@COUNT {name}@@", str(COUNTS[name]))
    strip_help = (HERE / "strip_help.py").read_text(encoding="utf-8").rstrip("\n")
    tasks = tasks.replace("@@STRIP_HELP@@", strip_help)
    left = re.findall(r"@@[A-Z_]+(?: T\d)?@@", tasks)
    if left:
        sys.exit(f"unresolved placeholders in tasks: {sorted(set(left))}")
    plan = skeleton.replace("@@TASKS@@", tasks)
    for key in ("SUITE", "MUTATIONS", "SELFCHECK"):
        value = (HERE / f"plan-{key.lower()}.md").read_text(encoding="utf-8").strip()
        plan = plan.replace(f"@@{key}@@", value)
    left = re.findall(r"@@[A-Z_]+@@", plan)
    if left:
        sys.exit(f"unresolved placeholders in plan: {sorted(set(left))}")
    OUT.write_text(plan, encoding="utf-8", newline="\n")
    print(f"written {OUT} ({plan.count(chr(10))} lines)")


if __name__ == "__main__":
    main()
