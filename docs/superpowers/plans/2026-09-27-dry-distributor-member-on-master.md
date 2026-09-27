# A dry distributor member run is not a delivery — on master (Phase M)

Successor plan to `plans/2026-09-26-dry-distributor-member.md`. That plan was
executed against base `418ab8a0` and its history carries our tracker numbers in
20 of 21 commit messages, so **the history is recreated rather than rebased**.
The design is `specs/2026-09-26-dry-distributor-member-design.md`, whose §10 and
§10.1 already record what the sister merge changed. **Nothing from those two
documents is repeated here** — this plan is only the work that is new because the
base moved.

## The base, measured

| | |
|---|---|
| base commit | **`1c071cf0`** (`build: release v2026.09.25`), = `upstream/master` at 2026-09-27 18:38 |
| new branch | `fix-a-dry-member-run-is-not-a-delivery`, worktree `D:/Entwicklung/HASI/issue53b-work/wt` |
| old branch, kept as a mark | `issue53-granular` (was `fix-a-dry-member-run-is-not-a-delivery`, tip `dc56b1fb`), worktree `issue53-work/wt` |
| baseline | **374 non-green names** — 7 failed / 3366 passed / 9 skipped / 367 errors |
| baseline file | `D:/Entwicklung/HASI/issue53b-work/baseline-1c071cf0.txt` |

**The baseline is byte-identical to `issue21-work/baseline-fa863aa9.txt`** —
`diff` empty, 374 = 374. The release commit only bumps four dist bundles and
three version strings, so it moved no test. Measured, not assumed
(`rebaseline-when-the-base-moves`).

**Name filter, anchored on `tests/`** — `batch.py` writes its own log lines
beginning with `ERROR`, and a wider filter pulled six of them in:

```bash
grep -E '^(FAILED|ERROR) tests/' <run>.txt | sed 's/ - .*//' | sort
```

## What master already carries (do not build, do not re-derive)

- `FlowMeter.metered_the_run()` in the **three**-condition form
  `_saw_report_after_open and _priced and not _declined`
  (`flow_metering.py:324-345`), and `sample(value, unit, state_class,
  reported_at=None, *, at)`.
- Both `distributor.py` `at=` conversions.
- `irrigation.py::_read_flow_sample` already returns `state.last_reported` as a
  fourth element, with the docstring that explains why.
- `FAULT_FLOW_NEVER_STARTED` and its label in all eight languages.
  **No `npm run build`, no dist bundles.**

So the old branch's **`flow_metering.py` part (+41 lines) comes out whole**, and
with it the textual conflict §4.3 had accepted. §4.3 is overholt.

## What is new because of that, and is the expensive half

Design §10.1, re-measured on **this** base rather than taken from the archive.
Probe: `docs/superpowers/probes/2026-09-27-distributor-witness.py`, run against
`issue53b-work/base`:

```
feed                                   delivered()   metered_the_run()  guard fires?
as distributor.py does today           0.0           False              YES -> time-based credit (fix is a no-op)
with a report per poll                 0.0           True               no  -> dry verdict stands
```

`_dist_read_flow` (`distributor.py:643`) returns a three-tuple and its two
`sample()` calls pass no report, so `_saw_report_after_open` is never set and
`metered_the_run()` is **constant `False`** on this path. §3.1's guard would
collapse to `delivered <= 0` — what master already does — and the suite would
agree, because a test that issues no reports sees the same `False`.

**Scope decided (user, 2026-09-27): the report plumbing goes in the SAME PR as
the guard.** Measured reason: `_dist_read_flow` has exactly three references in
the package (definition + `distributor.py:692` + `:735`), all in
`distributor.py` — the same file as the guard — and its only test stub is
`tests/test_distributor_dispatch.py:1914`, a file the guard's own tests already
touch. The diff grows by **no** file. Rejected: a behaviour-neutral plumbing PR
first, whose only justification would be work not yet submitted.

## Test command (verbatim, from a worktree — there is no `.venv` here)

```bash
/d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest <pfad> -p _local_socket_unblock
```

## File structure

| file | what changes |
|---|---|
| `custom_components/irrigation_plus/distributor.py` | the report, the `isfinite` guard, the evidence test, `detail=`, the sweep's dry branch, the calibration gate |
| `tests/test_distributor.py` | `_state` grows a report; the window-level pins |
| `tests/test_distributor_dispatch.py` | the `_dist_read_flow` stub widens; the sweep-level pins; credit stubs take `**_kw` |
| `tests/test_distributor_cycle.py` | two credit stubs take `**_kw` |

`flow_metering.py` and `tests/test_flow_meter.py`: **untouched.**
`docs/superpowers/**` is untracked on this branch and **never** committed to it
(rule P1 — it goes to `archive/design-history`). Never `git add docs`:
`py_compile` drops `__pycache__` in there.

---

### Task M1: the test state double says when the sensor last spoke

Enabling, no production change. `tests/test_distributor.py::_state` builds a
`Mock()`, so `state.last_reported` is an auto-attribute — not a `datetime`, so
`sample()`'s `isinstance` check reads it as *no report*. Every distributor test
therefore models a sensor that has gone quiet, which is the trap §10.1 names.

- **Test file:** `tests/test_distributor.py`
- **RED expectation:** none — this task adds no assertion of its own. It is the
  fixture change the next task's RED needs; run the three distributor files
  before and after and the **same** tests pass (master's `_dist_read_flow` does
  not read the field yet, so nothing can move).
- **Implementation:** mirror `tests/test_self_closing.py::_flow_state`
  (master, lines 60-80) — an advancing `last_reported` by default, a `reported=`
  override for a sensor that is deliberately quiet. Advancing is the honest
  default: HA writes a new `State` exactly when a sensor sends a value.
- **GREEN expectation:** `test_distributor.py`, `test_distributor_dispatch.py`,
  `test_distributor_cycle.py` — same pass/fail names as before the edit.

### Task M2: the meter is told when the sensor spoke

- **Test file:** `tests/test_distributor.py`
- **RED expectation:**
  - `test_read_flow_reports_when_the_sensor_last_spoke` — `_dist_read_flow`
    returns a **four**-tuple whose fourth element is `state.last_reported`.
    RED: `IndexError`/length 3.
  - `test_measure_window_tells_the_meter_when_the_sensor_spoke` — captures the
    `FlowMeter` the window builds (patch `distributor.FlowMeter`) and asserts
    `metered_the_run()` is **True** after a live-but-dry window. RED: `False`,
    which is §10.1's starved witness. **This is the pin that keeps the whole fix
    from silently becoming a no-op again** — without it, a regression in the two
    call sites shows up only as "the guard does not fire", one level away from
    its cause.
- **Implementation:** `_dist_read_flow` returns
  `value, unit, state_class, state.last_reported` and its docstring says so and
  why (the same reason `_read_flow_sample`'s does: `hass.states.get` hands back
  the same `State` object while the sensor is quiet). Both call sites pass the
  fourth element — `meter.sample(reading[0], reading[1], reading[2], reading[3],
  at=0.0)` and `meter.sample(r[0], r[1], r[2], r[3], at=elapsed)`.
  Widen `tests/test_distributor_dispatch.py:1914`'s stub to a four-tuple; it
  keeps a **constant** report on purpose — that test is about `cap` bounding the
  metering loop and documents a time-based credit, and a quiet sensor is what
  keeps it on that path. Say so in its docstring.
- **GREEN expectation:** both new tests pass; the three distributor files show
  no new failure.

### Task M3: a non-numeric reading is not a flow reading

Unchanged from the old plan's Task 4. `float("nan")`/`float("inf")` parse, so a
function whose docstring promises `None` for non-numeric returned a tuple.

- **Test file:** `tests/test_distributor.py`
- **RED:** `test_read_flow_rejects_non_finite` — `nan`, `inf`, `-inf` each give
  `None`; a finite value still gives a tuple.
  `test_measure_window_nan_after_open_read_is_not_dry`.
- **Implementation:** `if not math.isfinite(value): return None`, with the
  measured justification in the comment (the dead-meter extend guard reads the
  same tuples: window 30 / cap 600 held the shared inlet **600 s** with a `nan`
  sensor, **30 s** with the guard).
- **GREEN:** both pass.

### Task M4: a `0.0` is an answer only when the meter measured the run

The design's §3.1, with `metered_the_run()` now inherited from master.

- **Test file:** `tests/test_distributor.py`
- **RED expectation** — spec §8's window-level pins, each with **advancing
  reports** so it pins the behaviour and not the starved witness:
  - T1 `test_measure_window_zero_flow_live_meter_measures_zero` — a live sensor
    reading 0 every poll measures `0.0`, not `None`. **This inverts an existing
    master test** (`test_measure_window_zero_flow_healthy_sensor_is_unreliable`);
    the inversion must be named in the PR body.
  - T3 `test_measure_window_sensor_dead_after_open_read_is_not_dry`
  - T4 `test_measure_window_totalizer_reset_is_not_dry` (`100, 100, 5, 7`)
  - T8 `test_measure_window_rate_gap_wider_than_max_gap_is_not_dry`
  - T9 `test_measure_window_totalizer_below_retained_baseline_is_not_dry`
  - T10 `test_measure_window_per_run_reset_above_near_zero_is_not_dry`
  - T11 `test_measure_window_a_priced_zero_is_still_dry` (rate 0 every poll;
    totalizer holding `100`; and `12, 0, 0, 0…` — the surge is the seed)
  - `test_measure_window_an_early_priced_interval_does_not_excuse_the_window`
  - **new on this base:** `test_measure_window_a_quiet_sensor_is_not_dry` — a
    sensor whose `last_reported` never advances keeps its time-based credit.
    That is §11.1's defect one path over, and on master it is the *only* thing
    `_saw_report_after_open` buys us here.
- **Implementation:** `if delivered is not None and delivered <= 0 and not
  meter.metered_the_run(): delivered = None`, after `stopped_early` is bound
  from the raw value. Docstring of `_dist_measure_window` updated: `0.0` is a
  measurement, `None` is "nothing was measured".
- **GREEN:** all of the above; `test_distributor.py` otherwise unmoved.

### Task M5: `_dist_credit_zone` carries a run-log detail

- **Test file:** `tests/test_distributor.py`
- **RED:** `test_credit_zone_passes_detail_to_record_run`,
  `test_credit_zone_dry_leaves_the_bucket_and_the_total_alone`.
- **Implementation:** one keyword-only `detail: str | None = None`, passed
  straight to `_record_run` (which already takes it). Widen the credit stubs in
  `test_distributor_dispatch.py` and `test_distributor_cycle.py` with `**_kw`.
- **GREEN:** both pass, no stub raises `TypeError`.

### Task M6: the sweep records a dry member run as failed and credits nothing

- **Test file:** `tests/test_distributor_dispatch.py`
- **RED:** `test_sweep_records_a_dry_member_run_as_failed`,
  `…_without_a_target` (T2 — the dry test must not mention `target`),
  `test_sweep_treats_a_negative_measurement_as_dry`,
  and T6 `…_a_measured_run_is_still_completed_and_a_short_one_partial`
  (Review-M-1 unbroken).
- **Implementation:** `dry = measured is not None and measured <= 0`, tested
  **before** the `PARTIAL` branch; `measured_l=0.0 if dry else measured`;
  `detail=const.FAULT_FLOW_NEVER_STARTED if dry else None`. **No zone fault**
  (design D2: nothing on this path clears one).
- **GREEN:** all pass.

### Task M7: the sweep says in the log that it wrote a run off

- **Test file:** `tests/test_distributor_dispatch.py`
- **RED:** `test_sweep_warns_when_it_writes_a_member_run_off` (caplog).
- **Implementation:** one `_LOGGER.warning` naming distributor, outlet, zone and
  the window it watched. A warning is all that reaches a user who does not read
  the run log, because no fault may be raised here.
- **GREEN:** passes.

### Task M8: a dry run is not a calibration sample

- **Test file:** `tests/test_distributor_dispatch.py`
- **RED:** `test_sweep_does_not_offer_a_dry_run_as_a_calibration_sample`.
- **Implementation:** `not dry` into the advisory gate.
- **GREEN:** passes.

### Task M9: full suite, name diff, lint

**Only the full run with a name diff decides** — never a subset. On 2026-09-27
five distributor/flow files were green while `tests/test_valve_verification.py`
was red, a file no subset had touched.

```bash
/d/Entwicklung/HASI/HAsmartirrigation/.venv/Scripts/python.exe -m pytest tests/ -p _local_socket_unblock -q > branch-run.txt 2>&1
grep -E '^(FAILED|ERROR) tests/' branch-run.txt | sed 's/ - .*//' | sort > branch-names.txt
diff /d/Entwicklung/HASI/issue53b-work/baseline-1c071cf0.txt branch-names.txt
uvx black custom_components/irrigation_plus/
uvx ruff check custom_components/irrigation_plus/
```

- **Expectation:** name diff **empty**; passed count = 3366 + the number of
  tests added, **counted by definition**, never inferred from the difference.

### Task M10: mutation matrix

Each mutation must kill at least one **named** test. Revert every one with
`git checkout -- <file>`, and check the tree is clean before the next.
A survivor is **first a suspicion against the test** — five of five on
2026-09-27 were weak tests — but check the mutation itself too: one killed
nothing because the lines were placed *before* the assignment they were meant to
break. Print the flags one at a time, not just the end result.

**Two mutations are new on this base and are the ones §10.1 exists for:**

| # | mutation | must kill |
|---|---|---|
| M-a | seed call site drops `reading[3]` | `…_tells_the_meter_when_the_sensor_spoke`, T1 |
| M-b | poll call site drops `r[3]` | T1 (the seed alone is the baseline, never evidence) |
| M-c | `_dist_read_flow` returns the three-tuple again | both of the above |

and the old matrix carried over: drop the whole guard · reduce
`metered_the_run()` to `_priced` alone · reduce it to `_delivered > 0` · flip the
sweep's `<= 0` to `== 0` · move the dry test after `PARTIAL` · drop `not dry`
from the calibration gate · pass `measured` instead of a hard `0.0` · remove the
`isfinite` guard · downgrade the warning.

**Recorded as surviving, with the reason:** the guard's own `<= 0`. A meter that
accounted for nothing has delivered exactly `0.0`, never a negative, so `== 0`
is indistinguishable there. The comparison earns its keep one level up, in the
sweep's `dry`.

### Task M11: the three reference checks

**Chained with `;`, never `&&`** — `grep -c` exits 1 on zero matches and would
break the chain in a way that looks like a pass. The only permitted hit is the
author line.

```bash
git diff 1c071cf0 > /tmp/d.txt; grep -cE 'Eifel-Joe|§' /tmp/d.txt
git log 1c071cf0..HEAD --format=%B > /tmp/m.txt; grep -cE 'Eifel-Joe|§' /tmp/m.txt
for s in $(git rev-list 1c071cf0..HEAD); do echo "$s $(git show $s | grep -cE 'Eifel-Joe|§')"; done
```

Per-commit must be **exactly 1** (the `Co-Authored-By` line contains no `§`, so
the 1 is `Author:`); diff and messages must be **0**. Also: no branch SHAs and no
doc shorthand in anything that goes upstream.

### Task M12: live test on HA-Test

Design §8's four observable values, on the **distributor** path. Detail in the
handover; what this plan fixes:

- The flow sensor must hang on distributor **`Gardena1`**, not on a zone. It
  carries `sensor.wasser_3_flow`, which is **quiet** — and on this base a quiet
  sensor is deliberately *not* dry, so it proves nothing. A controllable
  `input_number` with unit `L/min` is needed (`set_value` with the **same** value
  advances `last_reported`; a state-based template sensor may not).
- Only the **panel** can change distributor and zone fields — MCP is read-only
  there, so the user does it. Name them the old value to note down and the field
  label from `frontend/localize/languages/de.json`, never a guessed one.
- Two runs, one variable: sensor reporting 0 during the run → `failed` /
  `flow_never_started`; sensor quiet → keeps its time-based credit. **The second
  run is the one the old form would have failed.**
- `run_zone` with `duration` (MINUTES, min 1) is the weather-independent way;
  `calculate_zone` dies on PirateWeather 429 on HA-Test. The diagnostics print
  the Pirate Weather key in clear — never into a file, an issue or a commit.
- After a restart, HTTP 200 is **not** proof: check
  `update.smart_irrigation_update` → `installed_version` **and** the config
  entry `loaded`.

## After the plan

1. Review — `superpowers:requesting-code-review`, then
   `superpowers:receiving-code-review`. Point the reviewer at spec §4 and §10.1.
2. Live test (M12).
3. **Archive** spec + this plan onto `archive/design-history` (rule P1), before
   any branch deletion. The local archive commit `d1508e4a` is still unpushed.
4. Push / PR / issue comment — **each needs chat approval**, and a text changed
   after its approval is shown again. The PR body must name: the inverted test,
   that `flow_metering.py` is **not** touched (the report shape it needs is
   already on master), and that the report plumbing mirrors what the merged
   sister fix did to `_read_flow_sample`.

---

## Measured results (2026-09-27, evening)

### Commits on the branch

Nine, base `1c071cf0`. Every one lint-clean at the time of its commit.

| # | commit | task |
|---|---|---|
| 1 | `test(distributor): the state double says when the sensor last spoke` | M1 |
| 2 | `fix(distributor): tell the meter when the inlet sensor spoke` | M2 |
| 3 | `fix(distributor): a nan reading is not a flow reading` | M3 |
| 4 | `fix(distributor): a live meter's 0.0 is an answer, not a missing measurement` | M4 |
| 5 | `feat(distributor): let a member run record why it failed` | M5 |
| 6 | `fix(distributor): a dry member run is recorded failed, not credited` | M6 |
| 7 | `fix(distributor): say a member run was written off, and do not learn from it` | M7/M8 |
| 8 | `test(distributor): two pins the mutation matrix found missing` | M10 fallout |
| 9 | `docs(distributor): the reader's docstring says what this path does with the report` | — |

### Suite

| | base `1c071cf0` | branch |
|---|---|---|
| | 7 failed / **3366** passed / 9 skipped / 367 errors | 7 failed / **3388** passed / 9 skipped / 367 errors |
| non-green names | 374 | 374 — **`diff` empty** |

`+22` counted **by definition**, not inferred: 2 (M2) + 2 (M3) + 8 (M4 net: 9 new,
1 replaced) + 2 (M5) + 4 (M6) + 2 (M7/M8) + 2 (the matrix's two pins).
Files: `issue53b-work/{baseline-1c071cf0,branch-names,base-run,branch-run2}.txt`.
Lint: `black` 69 files unchanged, `ruff` clean.

### Mutation matrix — 17 mutations, 16 killed, 1 documented survivor

Driver `scratchpad/mutate.py`; each mutation reverted with `git checkout --` and the
tree verified clean before and after. Raw verdicts in `issue53b-work/mutations.json`.

| # | mutation | verdict / killed by |
|---|---|---|
| M-a | seed site drops the report | KILLED — `…one_poll_counts_the_seed_report_as_the_baseline` (**survived the first pass**) |
| M-b | poll site drops the report | KILLED — `…tells_the_meter_when_the_sensor_spoke`, T1 |
| M-c | reader returns a three-tuple again | KILLED — 20 tests |
| M1 | drop the whole guard | KILLED — 7 tests |
| M2 | `metered_the_run()` → `_priced` alone | KILLED — `…a_quiet_sensor_is_not_dry` + 8 |
| M3 | `metered_the_run()` → `delivered > 0` | KILLED — 6 tests |
| M4 | drop `_saw_report_after_open` | KILLED — `…a_quiet_sensor_is_not_dry` + 3 |
| M5 | drop `not _declined` | KILLED — 5 tests |
| M6 | guard's own `<= 0` → `== 0` | **SURVIVED, by design** — see below |
| M7 | sweep's `<= 0` → `== 0` | KILLED — `…treats_a_negative_measurement_as_dry` |
| M8 | sweep's dry test gated on `target` | KILLED — 5 tests |
| M9 | dry tested AFTER partial | KILLED — `…as_failed_with_a_target_set` (**survived the first pass**) |
| M10 | credit passes `measured`, not `0.0` | KILLED — `…treats_a_negative_measurement_as_dry` |
| M11 | no `detail` on a dry run | KILLED — 2 tests |
| M12 | `not dry` dropped from the calibration gate | KILLED — `…as_a_calibration_sample` |
| M13 | the dry warning downgraded to debug | KILLED — `…warns_when_it_writes_a_member_run_off` |
| M14 | `isfinite` guard removed | KILLED — 2 tests |

**M6 survives for a stated reason**, not a missing test: a meter that accounted for
nothing has delivered exactly `0.0`, never a negative, so `<= 0` and `== 0` are
indistinguishable *there*. The comparison earns its keep one level up, in the sweep's
`dry`, where M7 kills it.

### What the matrix found — two coverage gaps, both real

Both survivors of the first pass were weak coverage, not redundant code, and in both
cases the mutation itself was checked first:

1. **M9.** No test had a dry run with a **bound** target, and that is the only shape
   in which the ordering can go wrong — the sweep binds `target` only for a
   flow-metered *can-stop* member (`flow_sensor and tv > 0 and can_stop`). Every
   existing dry test had `target None`, so none of them could tell. The claim in the
   comment was an assertion, not a measurement, until the new test.
2. **M-a.** Every window under test had at least two live polls, so dropping the
   seed's report still left the *first poll* as the baseline and the *second* as
   newer. A **single-poll** window is what separates them: there the seed's report is
   what makes that one poll a change rather than a first sighting. The asymmetry is
   deliberate (no readable seed ⇒ keep the time-based credit) and now pinned.

### Reference checks — all three, chained with `;`

Diff **0**, commit messages **0**, per commit **exactly 1** and in every one it is the
`Author:` line. An extra scan over the **added** lines only, for `#NNN`, branch SHAs
and doc shorthand: nothing.

### Sister-path check

- `_dist_measure_window` has **one** consumer; `_dist_credit_zone` has two and the
  other (`:993`, the observed-inlet path) passes no `measured_l` at all, so it cannot
  carry this defect.
- `metered_the_run()` is read at exactly **two** places in the package —
  `self_closing.py:420` and now `distributor.py:847` — and after this change **all
  four** metered paths feed `sample()` a report. No starved witness remains.
- `end_rate_at` is called only from `self_closing.py`, so the design's
  "read the accessor before `end_rate_at`" warning does not apply here.

### ⚠️ The earlier live test does NOT carry over

`reconstructed/2026-09-27-dry-distributor-member-live.md` proved this fix on build
`v2026.09.27b1` against the **two**-condition witness, using `sensor.wasser_3_flow`
and arguing "`metered_the_run()` is true". Under master's three-condition form that
sensor is the **quiet** case: measured on HA-Test, `last_reported 2026-09-27T13:42:37`
and unchanged for hours. The same run on this build keeps its time-based credit —
correctly. So that protocol's dry row proves the old form, not the landed one, and the
live test has to be redone with a source that reports.

`input_number.hasi_flow_probe` from the sister fix's live test **no longer exists** on
HA-Test (checked).

**Better design than the plan's M12 above — two runs, ONE panel change:** point
`Gardena1`'s flow-sensor field at a fresh `input_number` (unit `L/min`, held at 0) and
leave it there for both runs. Run A drives `input_number.set_value(0)` every few
seconds *during* the run (same value, `last_reported` advances — measured 244 s apart
on the sister test) ⇒ must be `failed` / `flow_never_started`. Run B calls nothing ⇒
the sensor is quiet ⇒ must keep its time-based credit. Same zone, same sensor, same
reading, same window; the only variable is whether the sensor spoke.

The distributor field is labelled **„Durchflusssensor (optional)"** in German — *not*
the zone field's „Durchflussmesser-Sensor (optional)". Checked in
`frontend/localize/languages/de.json:877` rather than reused from memory.
`Gardena1` currently holds `sensor.wasser_3_flow` — the value to note down before
changing it.

`run_zone` on a member zone with a `duration` routes through
`_dispatch_distributor_cycles([zone_id], duration_override=…)` into this exact block
(`irrigation.py:3446`), so the weather-independent path really does reach the change.
