# The chain carries its plan, and never loses a queued zone in silence

**Issue:** `Eifel-Joe#2` (+ `Eifel-Joe#43`, opened out of this analysis)
**Branch:** `fix/chain-carries-zone-snapshots`, from `upstream/master` = `965a4f9d`
**Worktree:** `D:/Entwicklung/HASI/issue2-work/wt`
**Date:** 2026-09-22

---

## 1. Problem

`run_chain.py` serialises self-closing runs for two watering modes, `service` and
`opensprinkler` (the latter is a thin delegate, `opensprinkler.py:525-541`). Under
`zone_sequencing = sequential` it dispatches one zone and holds the rest back in
`Chain.zones`.

It holds them back as **bare integers**:

```python
run_chain.py:189   state.zones = [int(z.get(const.ZONE_ID)) for z in zones[1:]]
```

and picks them up again by re-reading the **stored** zone:

```python
run_chain.py:243   zone = self.store.get_zone(zone_id) or {}
```

Everything the dispatching cycle decided about those zones is dropped on the floor
between those two lines, and nothing outside the module can see that they are
waiting at all.

### 1.1 What was measured, not read

Nine assertions against `upstream/master` = `965a4f9d`, all green, i.e. every one of
them describes real behaviour today. They live in `tests/test_zz_repro_issue2.py`
(throwaway; the load-bearing ones become real tests during implementation) and reuse
the existing fixtures from `tests/test_service_chain.py`, whose `_coord` spy already
records `(zone_id, duration)` per dispatch.

| Finding | Measurement | Result |
| --- | --- | --- |
| **F1(a)** | stored 600 s, live estimate re-sized to 300 s, two zones | zone 1 → `300.0`, **zone 2 → `600.0`** — twice the water |
| **F1(b)** | zone 2 stored 0 s, live 300 s | `_dispatched == [(1, 600.0)]`; zone 2 never waters, **no log line names it** |
| **F1(c)** | `_live_run_zones = {1, 2}`, zone 2 skipped | marker 1 consumed, **marker 2 still armed** → the next run of zone 2 gets a `maximum_bucket` ceiling it did not earn |
| **F3** | dispatch `[1,2,3]`, then `[4,5]` | `state.zones` goes `[2,3]` → `[5]`; zones 2 and 3 are lost silently, and zone 4's valve opens **while zone 1 still waters**, under `sequential` |
| **F3** | same | chain token unchanged — `_chain_take_hold` returns early (`run_chain.py:209-210`), so the second cycle rides the first cycle's master hold and dies when *that* one releases |
| **F4** | zone 2 queued | `zone_run_in_flight(2) is False` **while zone 2 sits in `state.zones`** |
| **F4** | recalculation mid-chain writes 120 s | zone 2 delivered at `120.0`, not the promised 600 s |
| **F4** | recalculation mid-chain writes 0 s | `_dispatched == [(1, 600.0)]` — the whole run is gone |
| **M1** | Irrigate-now on a queued zone, then both finalise | `[(1, 600.0), (2, 600.0), (2, 600.0)]` — **zone 2 waters twice** |

### 1.2 Scope corrections established during verification

- The **rotating** branch is **not** affected by F1. `run_chain.py:334-340` reads the
  duration off the passed copies into `rotation.remaining`, and `:433-434` dispatches
  slices of that live total. Only the `sequential` branch loses it.
- `zones[0]` is **not** affected: `run_chain.py:198` passes the copy object itself.
- The **classic** linked-entity path is not affected: it claims its queued zones
  (`irrigation.py:1762`, `:3095` → `_claim_chain_zones`) and re-prices them before
  their turn (`irrigation.py:3207-3230`).
- Both settings needed for F1(a)/(b) are **non-default** (`const.py:629`
  `CONF_DEFAULT_ZONE_SEQUENCING = PARALLEL`; `const.py:92`
  `CONF_DEFAULT_LIVE_ESTIMATE_ENABLED = False`). They are both on for this
  installation, which is why the issue carries `prod-scharf`.
- The store re-read at `:243` has a **flag-independent** exposure as well:
  `calculation.py:1507` writes a recomputed duration, possibly 0, and nothing holds it
  off a queued zone.

### 1.3 M1, the finding the issue did not have

`ToDo.md:141` recorded that double-watering of the *same* zone "bleibt unbelegt".
It is now proven, and the mechanism is structural rather than incidental:

- `_sc_finish_run` removes the persisted run record **first** (`self_closing.py:387`)
  and advances the chain **after** (`:477`).
- For a self-closing zone, `zone_run_in_flight` reads exactly that list
  (`run_state.py:55-113` ← `self_closing.py:211-214`).
- Therefore the guard at `run_chain.py:248-249` reads a list the finaliser has just
  emptied. **It is structurally dead at the only moment it is consulted.**

`async_run_zone`'s own guard (`irrigation.py:3356`) is blind to a merely-queued zone,
so a manual run on one is accepted; its record carries
`RUN_MODE: service` (`self_closing.py:689`), so the chain's mode gate at
`run_chain.py:265` passes. The queued zone is then popped and watered a second time,
with a second bucket credit — the `#88` surplus class, on a run that did deliver.

This is tracked as its own issue, `Eifel-Joe#43`, and fixed in this PR (user decision,
2026-09-22): the Schwester-Pfad rule puts mirror bugs of the same function into the
same change, and the guard M1 indicts is being rewritten here anyway.

---

## 2. The two roots

The issue body says the old "Bündel A" note is half refuted and that there are two
roots rather than one, without naming them. They are:

1. **The chain forgets the plan.** What the dispatching cycle decided — the live
   duration, the live-estimate marker — does not survive the queue. The queue holds
   ids and re-reads the store on waking.
   → F1(a), and the duration half of F4.

2. **The chain conceals its waiters.** To the rest of the system they do not exist:
   not to `zone_run_in_flight` (`run_state.py:132-142`), not to the log, not to a
   second dispatch arriving at `run_chain.py:188-190`.
   → F1(b), F1(c), F3, M1, and the deferral half of F4.

F4 sits on both, which is why the old note "F4 falls out of the F3 fix" is wrong:
both F4 measurements run with a **single** dispatch, so an entry guard never touches
them.

---

## 3. Requirements

1. A zone the cycle planned waters for the duration the cycle planned, or is dropped
   **audibly**, handing back every marker it holds.
2. No zone is watered twice by the same cycle.
3. A second dispatch does not destroy a live queue.
4. The ledger anchor (`RUN_PRE_BUCKET`) stays as fresh as it is today. **No change may
   make it older.**
5. Every failure mode of the new mechanism degrades to *today's* behaviour, never to a
   new defect.
6. Upstream-shaped: general-purpose, pure Python, no new dependency, and the
   OpenSprinkler suite keeps passing unchanged as the engine's oracle.

---

## 4. Options considered

### 4.1 Queue representation

| Option | Verdict |
| --- | --- |
| **A. Zone dicts in `state.zones`** (the issue body's literal wording) | **Rejected.** It forces rewriting `run_chain.py:282` (`int(z) != zid`) — the first statement of `async_stop_zone` (`irrigation.py:499`). A `TypeError` there disables the user's Stop button for as long as any queue is non-empty. It also breaks `tests/test_service_chain.py:333` (`assert service.zones == [2]`), the one oracle assertion that pins the element type. |
| **B. A `QueuedZone` dataclass in `state.zones`** | **Rejected**, same exposure at `:282`, larger surface. |
| **C. Ints stay, a sibling `Chain.planned` dict carries the plan** | **Chosen.** |

C is not an invention: `Rotation` already splits exactly this way — `order: list` of
ints (`run_chain.py:338-339`) beside `remaining: dict` (`:340`). The module already
contains the pattern; the sequential half is being made to match its own rotating half.

### 4.2 How much of the zone to freeze

**Rejected: a full zone snapshot.** `async_run_self_closing` reads everything off the
dict it is handed (`self_closing.py:517-720`) — including

```python
self_closing.py:657   pre_bucket = float(zone.get(const.ZONE_BUCKET) or 0)
```

which is the **absolute reconcile anchor** for the whole run (`:654-656`, and
`run_state.py:9-19` for why the reconcile is absolute). A zone dispatched forty
minutes into a cycle would anchor on a forty-minute-old bucket, and everything that
moved it in between — a calculation's ET consumption, rain, `set_bucket`, an observed
credit — would be silently undone at finalisation. That is the bug class of our own
`JustChr#138`, and it is *worse* than the bug being fixed: F1 waters the wrong
length; a stale anchor corrupts the ledger.

**Chosen: overlay one field, re-read the rest.** Exactly what the rotation already
does at `:407` (fresh store read) and `:433-434` (`dict(zone, **{ZONE_DURATION: slot})`).

### 4.3 Second dispatch onto a live chain

| Option | Verdict |
| --- | --- |
| **Refuse and log** | Rejected (user decision). A scheduled cycle arriving during a manual one would be dropped in full, and Irrigate-now would visibly do nothing for service zones. |
| **Append and log** | **Chosen.** Nothing is lost: the live cycle keeps its queue, the new zones join the back of it, duplicates are skipped. |
| **Trigger-dependent** | Rejected: `trigger` is not a behaviour switch anywhere today, and making it one is the hardest rule for a reviewer to accept. |

**Accepted cost, to be named in the PR body:** a finish-fitted schedule that queues
behind a live cycle finishes late by that cycle's remainder. Nothing re-fits and
nothing warns — `async_dispatch_chained_zones` does not even accept a deadline
(`run_chain.py:158`), and `irrigation.py:982-987` states that self-closing zones
cannot honour one. Water is not lost; punctuality is.

---

## 5. Design

### 5.1 State

```python
@dataclass(frozen=True)
class ZonePlan:
    """What the dispatching cycle decided for a zone still waiting its turn."""
    seconds: float   # the duration the cycle priced, not what the store holds
    live: bool       # live-estimate sized, so its ceiling is maximum_bucket


@dataclass
class Chain:
    zones: list = field(default_factory=list)      # unchanged: bare ints
    planned: dict = field(default_factory=dict)    # NEW: zone_id -> ZonePlan
    ...
```

**The drift rule, load-bearing:** a **missing** plan means "use the stored duration" —
today's behaviour — and never "drop the zone". Any divergence between `zones` and
`planned` therefore degrades to today rather than into F1(b). This is the precise
point on which the runner-up design was rejected: there a missing key fed
`if planned <= 0: continue`, so drift *became* the bug being fixed.

`planned` is kept in step wherever `zones` is mutated: `run_chain.py:189`, `:242`,
`:282` (`_chain_drop_zone`), `:288` (`_chain_release`), `:301` (`_chain_teardown`),
`:345` (`_chain_start_rotation`).

### 5.2 Commits

**Commit 1 — the carrier.** `ZonePlan` and `Chain.planned`; build it at `:189` from
`zones[1:]`; at `:241-251` overlay the planned duration onto the freshly read zone.
Closes F1(a) and F4's duration half.

**Commit 2 — the marker travels with the plan.** `ZonePlan.live` records whether the
zone was in `_live_run_zones` when the cycle dispatched. Immediately before the chain
calls `async_run_self_closing` for that zone, and only when `plan.live` is true, the
zone id is **put back into `_live_run_zones`** so `_run_ceiling`
(`irrigation.py:2745-2749`) finds and consumes it as it would have on the first pass.
Without this the marker is simply gone: `_apply_live_durations` rebinds the whole set
on every scheduled call (`irrigation.py:2292`, `:2296`; sole caller `:903`), so any
second cycle strips a queued zone's marker and the zone is then clamped at
`max(target, pre_bucket)` instead of `maximum_bucket` — an under-credit.

Symmetrically, `_drop_live_run_marker` (`irrigation.py:201-210`) is called at every
drop site, so a zone that never reaches a dispatch hands its marker back instead of
leaving it armed for the next run. Closes F1(c).

**Commit 3 — nothing vanishes in silence.** A log line at every drop: `:244-245`,
`:246-247`, `:248-249`, the refusal fall-through at `:252`, and the rotation's
Schwester-Pfade `:407-412` and `:433-439`. The merged condition at `:408` is split so
the line can say which of the two fired. `_chain_release` and `_chain_teardown`
narrate an abandoned queue and hand back its markers. Closes F1(b).

**Commit 4 — `Eifel-Joe#43`.** A zone still present in `state.zones` when a run of it
finalises can only have been watered by **something other than this cycle** — because
the cycle pops its own zone at `:242` *before* dispatching it. So on finalisation,
drop that zone from `zones` and `planned`. No new state field is needed; the
invariant already exists.

**Do not fix M1 by reordering the finaliser.** The obvious alternative — advance the
chain *before* removing the record, so the guard at `:248` still sees it — would undo
a deliberate decision. `self_closing.py:470` carries the comment "Ordered AFTER
`_sc_remove_run` above so the calculation no longer sees a run", and `:1004` says the
same for the stop path. The ordering exists so the deferred calculation can run. The
fix above is ordering-independent and leaves that decision intact.

### 5.3 Second PR — the append guard (F3)

Separate, because it is the only change that alters **when** a valve opens. A live
chain is appended to rather than replaced; duplicates are skipped; a log line says so.

Two traps, both verified:

- The guard sits **below** the `parallel` / single-zone returns (`:183-186`). Placed
  above them it would refuse `parallel` dispatches that are correct today.
- `self._chain_state(mode)` **creates** the `Chain` (`:147-149`). Hoisting it above
  those returns flips `mode not in self._chains()` at `:265`, so
  `_chain_advance_for_run` would begin running for parallel-mode runs.

A rotating dispatch arriving on a live sequential queue (or the reverse) is a geometry
mismatch and cannot be merged; it is refused with a log line.

---

## 6. Explicitly not in scope

Each becomes its own issue. None is left unrecorded.

- **Porting `_resize_queued_zone`** (`irrigation.py:3165`) so queued zones are re-priced
  against rain falling mid-cycle. Today the store re-read does this by accident and in
  both directions; after the fix the chain is rain-deaf. That is a feature, and it does
  not belong in a `fix(chain)` PR.
- **Run-log rows and the eight language files** for skipped zones. Keeping them out
  keeps this a pure-Python upstream diff. Second reason: `store.py:1650` indexes bare
  (`old = self.zones[zone_id]`), so a deleted zone raises `KeyError` inside
  `_record_run` (`irrigation.py:2964`), on a path `_sc_finish_run` wraps in no
  `try/except` (`self_closing.py:368-477`) — and the oracle cannot catch it, because
  `tests/test_service_chain.py:50` mocks `_record_run` away.
- **F4 residue R1:** a calculation landing mid-chain is still not deferred, because
  `calculation.py:504-505` gates on `zone_run_in_flight`. After commit 1 it costs no
  water, only a discarded calculation. Named in the PR body.
- **M3:** four `await`s sit between the dispatch and `_sc_add_run`
  (`self_closing.py:580`, `:587`, `:598`, `~:626`), and no guard covers that window.
  It exists identically today, so it is not a regression of this change.
- **`ZONE_STATE_DISABLED`** is not re-checked mid-cycle at `:244-249`, today or after.
- **`async_stop_zone` on a merely-queued zone** confirms nothing to the user
  (`irrigation.py:499-501`, `self_closing.py:1117-1130`).
- **A dangling docstring reference:** `irrigation.py:206` points at
  `_reprice_before_turn`, which exists nowhere in the package; the function is
  `_resize_queued_zone` at `irrigation.py:3165`. One line, fixed in passing.

---

## 7. End-to-end criterion

1. The nine measurements of §1.1 flip from asserting the bug to asserting the fix, and
   enter the suite as real tests.
2. `tests/test_opensprinkler.py` — the engine's declared oracle
   (`run_chain.py:17-19`) — passes **unchanged**. In particular
   `test_sequential_holds_the_second_station_until_the_first_finishes` is the
   mechanical proof that the forbidden `_claim_chain_zones` route was not taken: it
   goes red the instant the chain's own queued zones are registered as in-flight.
3. Full suite unchanged at **7 failed / 3191 passed / 9 skipped / 320 errors**, with a
   `diff`-identical name list against `issue2-work/baseline-names.txt` (327 names,
   captured on `965a4f9d`).
4. `uvx black --check` and `uvx ruff check` on `custom_components/irrigation_plus/`.

---

## 8. Traps

- **`_claim_chain_zones` is forbidden**, and the reason is mechanical, not stylistic:
  after such a claim `run_chain.py:248` would `continue` past every waiting zone, and
  `:408-412` would set `rotation.remaining[zone_id] = 0.0` on the first pass, deleting
  the entire rotation. Verified at the code.
- **`_chain_drop_zone` loops every mode's chain** (`:278`) and `irrigation.py:499`
  calls it for every stop, including classic zones, before the mode is known. Anything
  hung on it must be gated on the zone actually being found.
- **The test double is incomplete** for some of this: `tests/test_service_chain.py:44-49`
  builds `c.store.config` as a `Mock` with four named attributes only.
- **`_note_si_valve`** (`self_closing.py:573`) is set *after* the in-flight check at
  `:562-568` and is leaked by the confirm-abort at `:636-649` and the exception path at
  `:759-766`, both of which do drop the live marker. Adjacent, not part of this change.
- **`git stash -- <file>` does nothing once the fix is committed** — the RED step has to
  be run before the commit, or against a real revert.
- **MSYS heredocs break on quotes in the text.** Use the Write tool for markdown.

---

## 9. Decisions taken

| Decision | By whom, when |
| --- | --- |
| M1 gets its own issue (`Eifel-Joe#43`) and is fixed in this PR | User, 2026-09-22 |
| Second dispatch **appends**, it does not refuse | User, 2026-09-22 |
| `state.zones` stays `list[int]`; the plan lives in a sibling dict | This analysis, §4.1 |
| One field overlaid at dispatch; the store re-read stays | This analysis, §4.2 |
| The append guard ships as a **second** PR | This analysis, §5.3 |
