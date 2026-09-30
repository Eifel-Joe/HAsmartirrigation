"""Build the throwaway pre-release commit and its ZIP for the live test (local only).

    python build_prerelease.py <fix-branch-head-sha> <version-without-v>

1. `git worktree add -b prerelease/v<version> pre-wt <sha>` next to this script's parent.
2. In the seven files that carry the release version (manifest.json, const.py, package.json,
   the four dist bundles), replace upstream's "2026.09.28" by <version> -- exactly one
   occurrence each, bytes and line endings kept -- and check that each file then equals its
   <sha> content with only that replaced.
3. Commit (the bundles need `git add -f`: dist/ is ignored as a directory) and check 7 files.
4. `git archive --format=zip` from the commit SHA (never from a tag name: upstream uses the same
   tag names) of custom_components/irrigation_plus, then check the ZIP: the version in
   manifest.json and const.py, no raw URL in translations/en.json, the fix present
   (STORAGE_MINOR_VERSION = 2, local_naive_now, lift_legacy_stamp), the file count.
Nothing is pushed.
"""

import hashlib
import pathlib
import subprocess
import sys
import zipfile

SHA, VERSION = sys.argv[1], sys.argv[2]
ROOT = pathlib.Path("D:/Entwicklung/HASI/issue22-work")
REPO = pathlib.Path("D:/Entwicklung/HASI/HAsmartirrigation")
PRE = ROOT / "pre-wt"
BRANCH = f"prerelease/v{VERSION}"
PKG = "custom_components/irrigation_plus/"
FILES = [
    PKG + "manifest.json",
    PKG + "const.py",
    PKG + "frontend/package.json",
    PKG + "frontend/dist/irrigation-plus.js",
    PKG + "frontend/dist/irrigation-plus-card.js",
    PKG + "frontend/dist/irrigation-plus-card-legacy.js",
    PKG + "frontend/dist/irrigation-plus-card-impl.js",
]
OLD = b"2026.09.28"


def git(*args, cwd=PRE, check=True):
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, check=check).stdout


def main():
    subprocess.run(["git", "worktree", "add", "-b", BRANCH, str(PRE), SHA], cwd=REPO, check=True)
    for rel in FILES:
        path = PRE / rel
        data = path.read_bytes()
        if data.count(OLD) != 1:
            sys.exit(f"{rel}: {data.count(OLD)} occurrences of {OLD!r}")
        path.write_bytes(data.replace(OLD, VERSION.encode()))
        committed = git("show", f"{SHA}:{rel}")
        # The working copy may be CRLF where the blob is LF; compare normalised.
        norm = lambda b: b.replace(b"\r\n", b"\n")
        if norm(path.read_bytes()) != norm(committed.replace(OLD, VERSION.encode())):
            sys.exit(f"{rel}: differs from {SHA} by more than the version")
    subprocess.run(["git", "add", "-f", *FILES], cwd=PRE, check=True)
    staged = git("diff", "--cached", "--name-only").decode().split()
    if sorted(staged) != sorted(FILES):
        sys.exit(f"staged {staged}")
    msg = (
        f"chore(prerelease): throwaway build v{VERSION} for the weather-buffer migration live test\n\n"
        "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>\n"
    )
    subprocess.run(["git", "commit", "-q", "-F", "-"], cwd=PRE, input=msg.encode(), check=True)
    commit = git("rev-parse", "HEAD").decode().strip()
    zpath = ROOT / "live" / "irrigation_plus.zip"
    if zpath.exists():
        zpath.unlink()
    subprocess.run(["git", "archive", "--format=zip", "-o", str(zpath),
                    f"{commit}:custom_components/irrigation_plus"], cwd=PRE, check=True)
    with zipfile.ZipFile(zpath) as z:
        names = z.namelist()
        read = lambda n: z.read(n).decode("utf-8")
        checks = {
            "manifest version": f'"v{VERSION}"' in read("manifest.json"),
            "const VERSION": f'VERSION = "v{VERSION}"' in read("const.py"),
            "en.json without raw URLs": "https://github.com" not in read("translations/en.json"),
            "STORAGE_MINOR_VERSION = 2": "STORAGE_MINOR_VERSION = 2" in read("store.py"),
            "local_naive_now": "def local_naive_now" in read("helpers.py"),
            "lift_legacy_stamp": "def lift_legacy_stamp" in read("helpers.py"),
            "files at the ZIP root": "manifest.json" in names and "__init__.py" in names,
        }
    digest = hashlib.sha256(zpath.read_bytes()).hexdigest()
    print(f"branch {BRANCH} commit {commit}")
    print(f"zip {zpath} files={len(names)} sha256={digest}")
    for name, ok in checks.items():
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}")
    if not all(checks.values()):
        sys.exit("ZIP check failed")


main()
