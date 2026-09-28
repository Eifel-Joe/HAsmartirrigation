# A rotating zone watered elsewhere between its turns

Design for `Eifel-Joe#45`. Base: `master` = `6acfc819`.

`JustChr#165` fixed the *sequential* half of this defect and half of the rotating one.
This document is about the half that is left, and about why it is not an extension of
either guard but a missing record.

## The defect, measured

Rotating, two zones, slot 300 s, one variable — whether the foreign run is still going
when the rotation reaches the zone:

| foreign run at zone 2's turn | master's behaviour |
|---|---|
| **still running** | `writing off zone 2 and its remaining 600s, another run took it over while it waited` — no second slot |
| **already finished** | `dispatched: [(1, 300.0), (2, 300.0)]`, `remaining[2]` 600 → **300** |

The second row is the defect: zone 2 was watered in full by Irrigate-now, its run
finalised, and the rotation hands it another 300 s slot — a second bucket credit for a
zone that already had its water.

## Why a better guard cannot fix it

The existing guard in `_chain_rotation_advance` asks `zone_run_in_flight(zone_id)`. That
predicate reads the persisted run record, and `_sc_finish_run` calls `_sc_remove_run`
**before** advancing the chain. Once the foreign run has finalised there is nothing left
in the store to read: the predicate answers `False`, correctly, and the guard never
fires.

Nor can the rotation reconstruct it from what it carries. `Rotation` holds
`slot, absorption, order, remaining, last_finish, cursor`. `last_finish` records *when* a
zone last stopped — it drives the absorption wait — and is stamped for **any** run of a
zone the rotation holds, including a foreign one. It does not record *who* watered, so it
cannot tell the rotation's own slot ending from a take-over ending.

`_chain_advance(mode, finished_zone_id)` is the one moment the rotation hears "a run of
zone X in this chain's mode has ended". It stamps `last_finish[X]` and discards the rest
of what it knows. The information needed is available exactly there and nowhere later.

## The fix

Give the rotation the one fact it is missing: which run is its own.

`Rotation` gains a single field:

```python
in_flight: int | None = None
```

the zone whose slot the rotation itself dispatched and is waiting for.

1. **`_chain_rotation_advance`** sets `in_flight` to the zone id immediately before
   `async_run_self_closing` — before, not after, because a run that finalised inside that
   await would otherwise find no record and have its own slot written off.

   It is **not** cleared when the dispatch is refused, and that is a decision rather than
   an omission. A refusal sets `remaining[zone] = 0.0`, and only building a fresh
   `Rotation` restores it — which starts `in_flight` at `None` again. A value left
   pointing at a refused zone can therefore only suppress a write-off for a zone whose
   remainder is already nil. Clearing it would be a line with no observable behaviour and
   no test that could fail for it; a comment carries the reasoning instead. That a
   refusal does not shadow a later take-over is pinned by its own test.
2. **`_chain_advance`**, in the block that already stamps `last_finish`:
   - `finished_zone_id == in_flight` → the rotation's own slot ended. Clear `in_flight`,
     carry on exactly as today.
   - otherwise, and the zone is one this rotation holds with water left → something else
     watered it this round. Write off its remainder (`remaining[zid] = 0.0`), hand back the
     live-run marker, and log the take-over — in the same shape as the two write-off
     branches that already exist in `_chain_rotation_advance`.

The write-off, not a separate "already watered" set, is deliberate: `remaining = 0.0`
already means "no more turns" and is what `_chain_forfeit_queue` reads when it reports
what a stop abandoned. A second field would be a second truth about the same thing.

### Why a new field rather than `cursor`

`order[cursor]` is the zone dispatched last, so it *looks* like it could serve. It cannot:
`cursor` means "where the turn order resumes" and keeps pointing at a zone after that
zone's slot has ended. A foreign run landing in an absorption window would then be read as
the rotation's own. Overloading `cursor` with a second meaning is the same implicit
coupling that produced this defect.

### Alternatives rejected

- **Compare the run record.** `async_run_self_closing` returns a bool, so the rotation
  would have to re-read the store after dispatching to learn which record was its own —
  a round trip with its own race, for a fact it could simply have written down.
- **Compare `RUN_TRIGGER`.** A trigger is not an identity. A scheduled run started outside
  the chain carries the same one the chain uses, and a rotation started by "irrigate all
  now" would classify a genuine Irrigate-now take-over as its own slot.

## Reach

`run_chain.py` is shared by the service chain and the OpenSprinkler chain, so both
geometries are covered by the one change. In `custom_components/` the only live caller
that carries a finished zone id is `_chain_advance_for_run`; `_os_chain_advance` has no
production caller (tests mock it). The detection sits in `_chain_advance` regardless,
because that is where every such report arrives.

The sequential geometry needs nothing: `_chain_forget_finished` already takes a zone out
of the queue when a run of it finalises, and its docstring's "a rotation keeps `zones`
empty, so it is unaffected" stays true — the rotating geometry is served by `remaining`,
which is what this change writes to.

### The other rotation, and why it cannot have this defect

`irrigation.py`'s `_irrigate_zones_rotating` is a second, independent rotation — the
classic linked-entity path, which walks its slots inline inside one coroutine instead of
being driven by finalisation callbacks. It is immune, and for a reason worth stating
rather than assuming:

`_claim_chain_zones` registers **every** zone of the cycle in `_active_runs` as
`queued=True` for the whole rotation, not at valve-open, and `_classic_run_in_flight` is
plain membership of that registry. A zone merely waiting its turn there therefore answers
`True` to `zone_run_in_flight`, so the duplicate-dispatch guard refuses an Irrigate-now
on it and the take-over never happens.

That claim is exactly the invariant the self-closing chain lacks: its waiting zones live
in `rotation.remaining`, which nothing consults. The same asymmetry the issue describes
for the sequential queue — one geometry gets the fact for free, the other has to be
given it.

## Explicitly not in scope

- **Proportional deduction** of what the foreign run delivered. Decided 2026-09-28: the
  whole remainder is written off, symmetric with the branch that already handles the
  still-running case. Deducting only `RUN_PLANNED_SECONDS` would make the same take-over
  end differently depending on whether the foreign run happened to outlast the slot.
- **The sequential geometry** — already fixed.
- **Surviving a restart.** The rotation lives in memory today and continues to.
- **The pricing mirrors** in `run_window.py` and `irrigation.py`. They size a cycle up
  front; this is a decision taken at a zone's turn.
- **A take-over by observed watering.** Found during review, and a real second source of
  the same defect rather than a variant of it: `observed_watering.py` credits an
  externally-opened zone through `_record_run` and `async_write_watered_bucket` and never
  calls `_sc_finish_run` or `_chain_advance_for_run`. The chain therefore does not hear
  about it at all — neither the existing guard at the turn, which reads
  `zone_run_in_flight`, nor the write-off added here, which needs a finalisation to fire
  on. A rotating zone with an `observed_entity`, opened by hand between its turns, is
  still dispatched another slot and credited twice.

  Left out on purpose. Covering it means giving observed watering a route into the chain,
  which is a change to a second subsystem and its own piece of work. It gets its own
  issue; this change is not weakened by stopping here, because every take-over that does
  reach the chain is now caught.

## End-to-end criterion

Rotating, two zones, slot 300 s. Zone 2 is watered in full by a run dispatched outside
the chain (`async_run_self_closing(zone, trigger="manual")`, the path Irrigate-now uses)
which finalises **before** zone 1's slot ends. At zone 2's turn the rotation must dispatch
nothing for it, `remaining[2]` must be `0.0`, and the log must name the take-over.

Measured on `6acfc819` as the exact opposite:

```
after the take-over: dispatched=[(1, 300.0), (2, 600.0)]   remaining={1: 300.0, 2: 600.0}
at zone 2's turn:   dispatched later=[(2, 300.0)]          remaining={1: 300.0, 2: 300.0}
```

## A note on the probe this issue shipped with

`Eifel-Joe#45` links a two-case probe as "already the RED test a fix needs". Its first
case — the take-over still running at the turn — is a sound control for the half
`JustChr#165` fixed, and is kept verbatim.

Its second case is not usable as written. It marks the take-over only in a comment and
expresses it by stubbing `zone_run_in_flight` to `False` — but that predicate already
answers `False` in an ordinary rotation, so the stub changes nothing. Measured at the
decision point:

```
ORDINARY (test_two_zones_take_turns)  dispatched: [(1,60),(2,60)]  remaining: {1:120, 2:120}
PROBE case 2                          dispatched: [(1,60),(2,60)]  remaining: {1:120, 2:120}
```

The two states are identical, and `test_two_zones_take_turns` asserts the opposite
outcome (`[1, 2, 1, 2, 1, 2]`) from it. Any implementation that made the probe's second
case green as written would have to stop dispatching the second zone of a normal
rotation. The case is therefore rebuilt to inject the run it describes — dispatch it,
finalise it — which is also what makes the fix's signal observable at all.

Decided with the user, 2026-09-28.
