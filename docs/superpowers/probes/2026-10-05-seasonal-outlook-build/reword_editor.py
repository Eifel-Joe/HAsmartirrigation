"""GIT_EDITOR for `git commit --fixup=reword:<sha>`: writes the new message.

git opens the editor with "amend! <subject>" followed by the old message. This
script keeps the first line and replaces the rest with the LAST
"**Commit-Message:**" block in deviations.md whose subject equals <subject>,
complete with its trailer. Unknown subject: exit 1, so git aborts the commit.

Usage: GIT_EDITOR="python D:/Entwicklung/HASI/issue10-work/reword_editor.py" \
       git commit --fixup=reword:<sha>
"""

import sys
from pathlib import Path

DEVIATIONS = Path(__file__).parent / "deviations.md"


def messages():
    """subject -> full message (last block wins), from the Commit-Message blocks."""
    out = {}
    lines = DEVIATIONS.read_text(encoding="utf-8").split("\n")
    i = 0
    while i < len(lines):
        if lines[i].strip() == "**Commit-Message:**":
            i += 1
            while not lines[i].startswith("```"):
                i += 1
            i += 1
            body = []
            while not lines[i].startswith("```"):
                body.append(lines[i])
                i += 1
            text = "\n".join(body).strip("\n")
            out[text.split("\n", 1)[0]] = text
        i += 1
    return out


def main():
    path = Path(sys.argv[1])
    first = path.read_text(encoding="utf-8").split("\n", 1)[0]
    if not first.startswith("amend! "):
        sys.stderr.write(f"reword_editor: unexpected first line {first!r}\n")
        sys.exit(1)
    subject = first[len("amend! "):]
    new = messages().get(subject)
    if new is None:
        sys.stderr.write(f"reword_editor: no Commit-Message block for {subject!r}\n")
        sys.exit(1)
    path.write_text(f"{first}\n\n{new}\n", encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
