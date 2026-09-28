# A service zone's watering_now sensor can never turn on (2026-09-28)

No spec of its own: a one-expression fix found live, not designed. Recorded because the
*finding* is the interesting part and because the test nearly proved nothing.

- **Our issue:** `Eifel-Joe#63` · **Upstream:** `JustChr#178`
- **Branch:** `fix-a-service-zone-shows-when-it-is-watering`, one commit on `1c071cf0`,
  worktree `issue63-work/wt`

## How it was found

The user reported, on the production installation, that irrigation was running but the
entities did not show it, and named the cherry-tree zone as the open one.

Two separate things came out of looking, and the first one was not a defect:

1. **That zone was not open.** Its valve had closed 44 s earlier and its run was already
   recorded. The valve that *was* open belonged to the next zone in the sequential
   chain, which had started one second after the first finished. It closed itself
   4 min 33 s later — the calculated 273 s rounded up to 5 minutes, because that valve
   takes minutes — and its run was recorded 5 s after that. Watched from open to close
   to record before saying anything about it.
2. **The reported symptom was real and was a different thing:** all three
   `watering_now` sensors had `last_changed` frozen at the boot timestamp, through four
   runs.

## The defect

`SmartIrrigationZoneWateringNowSensor` mirrors one entity and subscribes to it, reading
`zone_watch_entity`, which reads only `linked_entity`. A service/self-closing zone has
none — it runs through `run_service` — so the sensor subscribes to nothing and `is_on`
returns `False` unconditionally. Structural, not stale.

Confirmed at the stored config rather than inferred from the symptom:

```json
"watering_mode": "service", "run_service": "script.…",
"linked_entity": null, "confirm_entity": "valve.…", "observed_entity": "valve.…"
```

The information was never missing. `observed_watering.py` already falls back to
`observed_entity` for exactly this case, and `store.py` records the reason on the field
itself. The fix gives the sensor the same expression — an existing rule applied to the
one consumer that lacked it.

## The measurement

| zone | valve closed | run recorded | volume |
|---|---|---|---|
| Kirschlorbeer | 04:46:09Z | 04:46:14Z | 48.0 L |
| Kirschbaum | 04:49:02Z | 04:49:07Z | 26.0 L |
| Beet | 04:54:11Z | 04:54:16Z | 15.5 L |

Every run recorded, every counter advanced, no fault. Only the display dead — which is
what made it survive: nothing else looks wrong.

## ⚠️ The test nearly proved nothing

`is_on` reads `self.hass`, which HA assigns when the entity is added to a platform — not
the `hass` passed to `__init__`. A sensor built in a test and never added reports
`False` **whatever it mirrors**, so the first green run was green for the wrong reason
and all four assertions would have passed against a broken implementation.

And the consequence that is easy to skip: after fixing the fixture, the earlier RED no
longer applied to the current test. It was re-established properly — source reset to
master, `assert None == 'valve.…'`, then restored, 4 passed. `verification-must-exercise-the-change`,
one layer up: it is not enough that a test failed once; it has to have failed in the
shape it is now in.

## Evidence

`3366 → 3370` passed, name diff against `1c071cf0` empty (374 = 374), `+4` by
definition. `black`/`ruff` clean. Reference checks: added lines 0, messages 0, per
commit 1.

**Mutation matrix 4/3.** Dropping the fallback, swapping the precedence, and reading
`confirm_entity` instead each kill a named test. Dropping `or None` survives
deliberately: that term is master's own and is unobservable, since `zone.get` returns
`None` for a missing key anyway and an empty string is falsy everywhere downstream.
Recorded rather than covered by a test pinning an implementation detail.

## Noted in passing, not acted on

`flow_calibration_advised` is `true` on the cherry-tree zone. That zone is blocked as a
throughput measurement source — its hose is defective and delivers more than the
configured rate — so the advisory must not be accepted. See
`hasi-kirschbaum-hose-defect`.
