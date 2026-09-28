# A second dispatch joins the running cycle — PR 2 of the run_chain series (2026-09-28)

No spec of its own: this is the second half of
`plans/2026-09-22-chain-carries-its-plan.md`, built at the same time and held back
until the first half merged. Recorded here because its execution produced findings the
plan does not contain.

- **Upstream:** [`JustChr#176`](https://github.com/JustChr/HAsmartirrigation/pull/176)
- **Our issues:** `Eifel-Joe#62` (the append, newly opened — `Eifel-Joe#2` was closed
  with the first half, so rule P2 required a new one rather than a reopened one) and
  `Eifel-Joe#46` (the geometry flip).
- **Branch:** `fix-a-second-dispatch-joins-the-running-cycle`, one commit on `1c071cf0`,
  worktree `issue2b-work/wt`. The old stacked pair stays at `issue2-work/`
  (`fix/chain-carries-zone-snapshots` `f1c8c937`, `fix/second-dispatch-joins-the-queue`
  `1b3cc7d5`).

## What the rebase turned out to be

`JustChr#165` took our first half **byte-identically**: `git diff upstream/master
f1c8c937` over `run_chain.py` and `test_chain_carries_its_plan.py` is empty. So the
rebase reduced to cherry-picking the one commit on top, which applied clean.

## Three findings from the execution

1. **The 2026-09-25 commit carried three references to our own tracker in its
   CONTENT** (`Eifel-Joe#48` twice, `Eifel-Joe#2` once) plus the `F1`/`F3` doc
   shorthand. Written before the rule got its grep discipline. A repair commit on top
   would still have left them inside the commit's content, so the history was recreated
   as one clean commit — the same lesson `JustChr#174` cost a rebuild for.

2. **One reference is live in the maintainer's master.**
   `tests/test_chain_carries_its_plan.py:1` carries `Eifel-Joe#2`, landed via
   `JustChr#165`. Exactly one hit in the whole tree (`git grep` over
   `custom_components tests docs`). This PR touches that file anyway, so it was removed
   here rather than left; the PR body says so in one line.

3. **The commit message claimed something untrue and was corrected before the push.**
   It said "one existing test is inverted … it asserted that a second dispatch replaced
   the queue", taken from a memory's looser wording. No such test exists on master —
   checked. What actually happened: `test_starting_a_rotation_clears_a_sequential_plan`
   reached its state by dispatching a rotation over a live sequential cycle, and the new
   behaviour **refuses** that, so its **fixture** was rebuilt, not its assertion. That is
   a more interesting thing to tell a reviewer than an inversion.

## Mutation matrix — 12 mutations, 12 killed

⚠️ **The first run of it was broken and looked like a result.** It reported
`0 killed, 12 survived`, because the test list named `tests/test_rotation.py`, which
does not exist: pytest aborts on the missing path and every mutation reads
`no tests ran in 0.01s`. Read as a verdict that is twelve uncovered lines. The driver
now refuses to report a verdict unless the summary shows collected tests, and the list
is run once un-mutated first. Recorded in `mutation-survivor-suspects-the-test`.

On the corrected run, one mutation genuinely survived: **dropping
`state.rotation is not None` from `_chain_is_live`**. It is redundant against the code
as it stands, because `_chain_take_hold` sets the token whether or not a master entity
exists, so a live rotation always has one. The clause is kept anyway — a rotation nobody
holds the master for is still a running cycle — and the sibling clause
`bool(state.zones)` was already documented as redundant-but-kept with a hand-built drift
test. The rotation clause had neither the justification nor the pin. Both now have both,
and the docstring says the second test exists because its mutation survived.

## Evidence

`3366 → 3386` passed, name diff against `1c071cf0` **empty** (374 = 374).
`+20` counted by definition: 19 in the new file plus the drift pin.
`black` clean, `ruff` clean. Reference checks: added lines 0, messages 0, per commit 1.

## The product decision this PR took, which its issue had deferred

`Eifel-Joe#46` is labelled `typ:produktentscheidung` and its body asks whether a
geometry change should end the running cycle, let it finish, or take over. **This PR
answers "let it finish"** — the refusal — without that having been decided in the issue.
Disclosed in a comment there and confirmed by the user on 2026-09-28. The reasoning:
taking over is the defect itself; ending the cycle means closing an open valve and
abandoning zones that were promised water, on a settings change the user may not have
connected to the running cycle; letting it finish is the only one of the three that
cannot make things worse than not having touched the setting.

Deliberately **not** guarded, and named in the code: a second *rotating* dispatch onto a
live rotation still replaces it. That is one geometry rather than two, and merging two
rotations means deciding whose slot size and whose captured totals win.
