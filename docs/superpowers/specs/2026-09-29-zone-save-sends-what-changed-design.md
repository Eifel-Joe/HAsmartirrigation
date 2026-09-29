# A zone save sends what the edit changed

Design for `Eifel-Joe#5`. Base: `upstream/master` = `1876aa03` (v2026.09.27).
Former designations: `PR D` (work order of 2026-09-21), finding `N1` (altmenorg comparison,
2026-09-21). Every `file:line` below was read on `1876aa03`.

## The defect, traced

1. The zone settings page saves automatically: 500 ms after any input it posts the **whole**
   zone object it holds (`view-zone-settings.ts:405-434`, `saveToHA` → `saveZone` at `:502-505`).
2. The page re-reads its zones only when the websocket command it subscribes to
   (`irrigation_plus_config_updated`, `view-zone-settings.ts:267-282`) fires, and that command
   forwards the dispatcher signal **`_update_frontend`**, not `_config_updated`
   (`websockets.py:83-105`).
3. A run credits through `async_write_watered_bucket` (`irrigation.py:2828-2876`), called from
   `_commit_run_progress`, which then dispatches only `_config_updated` (`irrigation.py:2903`);
   `_record_run` likewise (`:3022`). An open page therefore never learns of the credit. It is
   refreshed only by something else: a calculation (`calculation.py:315`, `:561`), a fault being
   raised or cleared (`irrigation.py:628-637`), or a zone post (`websockets.py:388`).
4. The next edit of **any** field posts the pre-run copy. The strip list (`websockets.py:366-382`,
   11 fields) lets `bucket` through on purpose, because the form edits it. The store writes it,
   and `_book_asserted_bucket` (`__init__.py:1967-2026`) sees a changed level and takes the stale
   value for a hand-set: `last_consumed_at` moves to the save time and `pending_bucket_events` is
   emptied.

Recorded in the issue: a run writes 0.0, a save from a 23:00 snapshot puts it back to −6.2,
empties the ledger and moves the watermark to the save time. The run's credit is gone, so the
zone is watered again.

## Reach: more than the bucket

Field inventory: `docs/superpowers/probes/2026-09-29-zone-save-field-inventory.py`, result in
`docs/superpowers/probes/2026-09-29-zone-save-field-inventory.txt`. `ZoneEntry` has 49 fields; the form edits 31 of them
through 35 `handleEditZone` calls, the strip list holds 11, no field is in both. Seven are in
neither: `id` and six the server writes.

| field | written by | read by |
|---|---|---|
| `days_since_irrigation` | reset to 0 **in the same write as every credit** (`irrigation.py:2875`), counted up at midnight (`skip_conditions.py:643`) | the days-between skip (`skip_conditions.py:314-317`, `:689`) |
| `irrigation_target_bucket` | the calculation (`calculation.py:1611-1616`) | sizing a run (`irrigation.py:191`) |
| `delta`, `explanation`, `current_drainage`, `number_of_data_points` | the calculation and the buffer counters | display, run-log `detail` |

A stale save therefore also undoes the days-between wait that the run restarted.

Fields the form edits **and** something else writes are reverted the same way, and no list can
protect them because the form owns them: `multiplier` from the number entity (`number.py:125`),
whatever `set_zone` / `set_bucket` write (`services.py:222`), and `duration`, which the store
zeroes when a credit brings an automatic zone's bucket to 0 (`store.py:1691-1697`).

## Why the issue's proposed shape does not fix it

The issue asks for an allowlist of the fields the form edits, in place of the strip list.
`bucket` has its own input on the form (`view-zone-settings.ts:1608-1627`), so it is on any such
allowlist and the stale value still passes. An allowlist protects only fields the form does not
edit, and those six are protected just as well by adding them to the strip list.

## Prior art

altmenorg carries the same fix in two steps. `913b1cf6` (2026-09-04) adds the strip list; its
message says it was found by reading JustChr's fork. `11ed18d2` (2026-09-21) is this finding: the panel sends only the fields
an edit changed. The strip list stays as the net for a panel still cached in a browser and is
extended by the calculation's outputs. Their store reads a missing bucket or maximum from the
zone. On the way they fixed a save timer shared by all zones, and a cleared field that
vanished from the JSON; both neighbours exist here too. The design below takes that shape
and departs from it in two places (D1, D2).

## Requirements

- **R1** An edit on the zone settings page sends the fields that edit sets, and no other field
  of the zone.
- **R2** Edits to several zones inside one debounce window are all saved.
- **R3** A field the form clears is sent as `null`, so the clear is stored.
- **R4** A whole-zone post (a panel still cached in a browser, or any other client) does not
  write any of the 17 server-owned fields.
- **R5** The bucket/maximum clamp of a panel save behaves as it does for a whole-zone post
  today, whether one or both values are posted.
- **R6** The store funnel behaves as before for every other writer.
- **R7** A deliberate bucket edit stays an assertion (`JustChr#138`).

## Options considered

| | panel | backend | old cached panel |
|---|---|---|---|
| **A** | sends the change | allowlist, plus a test that every `ZoneEntry` field is classified exactly once | bucket, duration, multiplier can still be reverted once |
| **B** ✅ | sends the change | strip list + 6 fields | same as A |
| **C** | sends the change; the bucket field sends `new_bucket_value` | A, and a zone save never writes `bucket` | bucket closed; REST contract changes, `bucket` in a zone post is ignored |
| issue | unchanged | allowlist | does not fix the reported defect (above) |

**Decision: B** (user, 2026-09-29). Smallest backend change, the same user-facing fix as A.

Two decisions inside B depart from altmenorg:

- **D1: the call sites name their change; no difference helper.** The page's copy is the thing
  that goes stale, and a difference against it drops an intended write whose value equals the
  stale copy. The state select sets `{state, duration: 0}` (`view-zone-settings.ts:963-968`). If
  the page still shows `duration: 0` while the server has a calculated duration, the difference
  finds no change and the reset is never sent. Two open tabs do the same with plant type → `kc`.
- **D2: the clamp's missing value is filled in at the view, not in the store.** The store is the
  funnel every bucket writer passes: credits, the calculation, a unit-system flip. That is what
  the NOT-TO-DO in `_book_asserted_bucket` (`__init__.py:1988-1997`) protects. Reading the missing
  value there would change their behaviour. `set_all_buckets`, for one, posts `new_bucket_value`
  without a maximum (`_async_set_all_buckets`, `__init__.py:2316-2326`) and is not clamped
  today; with the store reading the maximum, it would be.

## The design

### Panel: `view-zone-settings.ts`

- `handleEditZone(index, changes: Partial<SmartIrrigationZone>)`. Each of the 35 call sites
  drops `...zone,` from its object and passes only what it sets. Five can set more than one
  field: distributor + outlet (two sites), plant type (+ `kc` unless "custom"), `kc` + plant
  type, state + duration.
- The displayed copy is updated at once, as today: `{...zone, ...changes}`.
- Pending changes are collected **per zone id** and merged; `undefined` becomes `null` on
  merge. That covers the three fields cleared to `undefined` today: `module`, `mapping`,
  `duration_field` (`:1017`, `:1041`, `:1218`). The other nine clearable fields already send
  `null`.
- One debounce timer, 500 ms as today. When it fires, every zone with pending changes is posted
  as `{id, ...changes}`. The collection is emptied before posting, so input during a save goes
  into the next round.
- "Saved" appears once every post of the round has settled. A failure shows the toast, as today.
- The module and mapping selects bind `zone.module !== undefined ? String(zone.module) : ""`.
  A stored `null` would show as the text `"null"`, so both test `!= null` instead. `None` is the
  `ZoneEntry` default for both (`store.py:246`, `:249`), and `duration_field` is read with
  `or "duration"` everywhere (`self_closing.py:191`, `:1023`).
- Unchanged: creating a zone (`handleAddZone` posts the whole new object; a new object has no
  stale state), the distributor page (already posts `{id, distributor_id, outlet_number}`,
  `view-distributor-settings.ts:461-470`), and the setup wizard (creates).

### Backend

- **Strip list** (`websockets.py:366-382`): add `days_since_irrigation`,
  `irrigation_target_bucket`, `delta`, `explanation`, `current_drainage`,
  `number_of_data_points`. The schema keeps accepting them, so they are accepted and ignored.
  Rejecting a field a panel sends fails the whole save with a 400, which is how altmenorg's
  v2026.8.3 broke every zone edit.
- **Clamp at the panel boundary** (zone view): when a post for an existing zone carries exactly
  one of `bucket` and `maximum_bucket`, the view adds the other from the stored zone before
  calling `async_update_zone_config`. The store's clamp (`store.py:1680-1690`) then sees both,
  as with a whole-zone post today. The consequences are today's:
  - a bucket above the maximum is clamped;
  - a maximum lowered below the current level clamps the level, and `_book_asserted_bucket`
    counts that as an assertion;
  - a maximum that leaves the level alone moves nothing.
- **Comments, per `code-doku`**: three places describe the whole-zone post as a given. They
  are the `_book_asserted_bucket` docstring ("which the panel's whole-zone save always does",
  `__init__.py:2003-2007`), the zone view's comment block (`websockets.py:347-365`), and "review
  finding J" in the store (`store.py:1681-1682`). They will say that the panel sends the change,
  and that the strip list is the net for a panel still cached in a browser.

## Explicitly not in this work

1. **Refreshing the open page after a run.** The page shows pre-run values until the next
   `_update_frontend`, at the latest its own first save. It no longer writes them back.
   Refreshing on every store write would re-render inputs while someone types, because the
   live estimate writes often. No issue filed.
2. **Allowlist and completeness test** (option A), **the bucket as an explicit statement**
   (option C): not chosen.
3. **Fields the form cannot clear**, e.g. `maximum_duration`: an emptied input is `NaN` and the
   handler ignores it (`view-zone-settings.ts:1736`). UX, no data loss. No issue filed.
4. **The store funnel** (D2).

## Residual risk

A page left open across the update keeps running the old bundle and posts whole zones. The
extended strip list protects the 17 server-owned fields from it, but not the 31 the form edits.
`bucket`, `duration` and `multiplier` can still be reverted once, until that page is reloaded.
This happens once per update. The PR says so.

## Tests

Every new test is run against `1876aa03` first and **seen** RED, or declared a pin.

**Panel** (vitest, pattern of `view-zone-settings-latency-margin.test.ts`: the element is built
without rendering, with fake timers and a `callApi` that records). Bodies are compared after
`JSON.parse(JSON.stringify(…))`, i.e. what goes over the wire.

| | setup | expected | on `1876aa03` |
|---|---|---|---|
| F1 | page copy stale (bucket −6.2), edit name | exactly `{id, name}` | whole zone incl. bucket → RED |
| F2 | two zones edited within 500 ms | two posts, one per zone | one post → RED |
| F3 | two fields of one zone within 500 ms | one post carrying both | whole zone → RED |
| F4 | clear the module | `{id, module: null}` | key missing → RED |
| F5 | change state, page copy already has `duration: 0` | `{id, state, duration: 0}` | whole zone → RED; also stops a later difference helper (D1) |
| F1b | edit the name | the displayed copy has the new name and keeps every other field | copy replaced by the change → RED |
| F3b | edit, let it post, edit again | two posts; the second carries only the second edit | whole zone → RED |
| F6 | `_selectValue(null / undefined / 3 / 0)` | `"" / "" / "3" / "0"` | method missing → RED |

**The call-site pin is a pytest test, not a vitest one:** CI's frontend job runs `npm ci`
and `npm run build` only, never the panel tests, while the pytest job gates every PR. The pin
reads `view-zone-settings.ts` and fails while any `handleEditZone` call spreads `...zone`
(35 on `1876aa03`). It is the test that fails at the root of the defect; F1–F6 only test what
`handleEditZone` does with the change it is given.

**Backend** (pytest, `hass` fixture, under `TZ=UTC`)

| | setup | expected | on `1876aa03` |
|---|---|---|---|
| B1 | whole-zone post carrying stale values of the six new fields | stored values unchanged | overwritten → RED |
| B2 | `{id, bucket: 50}`, stored maximum 30 | bucket 30 | 50 → RED |
| B3 | `{id, maximum_bucket: 10}`, stored bucket 20 | bucket 10, watermark moved | bucket stays 20 → RED |
| B4 | `{id, maximum_bucket: 40}`, stored bucket 20 | nothing moves, no assertion | green, **pin** against a spurious assertion from the fill-in |
| B5 | a real credit, then `{id, name}` | bucket, `last_consumed_at`, ledger as the run left them | green, **pin** (the backend already merges a partial post) |
| B6 | `set_all_buckets` above the maximum (a writer through the store funnel) | not clamped | green, **pin** for D2 |
| B7 | create a zone with a bucket and no maximum, no id (what the wizard and "add zone" post) | the zone is created | green, **pin**: `store.get_zone(None)` raises, so the completion must skip a create |

Must stay green: `test_zone_view_ignores_server_owned_fields`, `tests/test_manual_bucket_assertion.py`
(R7), the distributor partial-save tests, every panel test.

**Gates**

- The full suite under `TZ=UTC` against `issue22-work\measure\baseline-1876aa03-tzutc.txt`
  (7 failed / 3455 passed / 9 skipped / 367 errors); only the difference counts. If
  `upstream/master` has moved, measure again first.
- `npm test`, `npx tsc --noEmit -p .` (0 errors on the base), then `npm run build`. Only
  `dist/irrigation-plus.js` changes content (the card bundles do not import this view); stage
  it with `-f` and count.
- `uvx black`, `uvx ruff check`.
- Before any push, `grep -rn "Eifel-Joe" custom_components/ tests/` must be empty.

## Probe run and sister paths (2026-09-29, after the design was agreed)

The plan was run once on a throwaway worktree on `1876aa03` before it was handed over. Every
new test failed on the base for the reason it names, or passed as a declared pin. With the
change:
- the full suite under `TZ=UTC` was 7 failed / 3462 passed / 9 skipped / 367 errors against
  the baseline's 7 / 3455 / 9 / 367, with identical FAILED/ERROR names;
- vitest went from 629 to 637;
- `tsc` and the build were clean;
- the mutation matrix killed 15 of 15.

Three things changed on the way, all folded into this document:
- the call-site pin moved to pytest;
- a 40-character window in its first regex found only 23 of the 35 spreads;
- test file imports of `node:fs` would print one TS2591 warning per bundle.

Sister paths, per the global rule: every other panel page that posts to the backend was read.
None posts a copy carrying fields the server writes:
- distributor settings: `_configPayload`, an explicit list of config fields;
- general settings: a `pick` of 8 settings;
- sensor groups: `{id, name, mappings}`;
- schedules: the server writes nothing into a schedule.

The zone page is the only one.

## End-to-end criterion

Live on HA-Test.

1. **On today's build `v2026.09.27b3`**:
   - open the zone settings page and leave it open;
   - water a zone with `run_zone` and a `duration`;
   - before touching the page, confirm it still shows the pre-run bucket. If something
     refreshed it in between, the run proves nothing, so repeat it;
   - on the still-open page, change the zone's name.

   Expected: the bucket snaps back. That is the **live RED**; the issue's evidence was taken
   below the panel.
2. **On a throwaway build carrying the fix**, the same sequence. Bucket, `last_consumed_at` and
   the pending ledger stay as the run left them.
3. **Also on the fix build**:
   - two zones edited in quick succession are both stored after a reload;
   - a cleared module stays empty after a reload and shows the empty option, not `"null"`;
   - setting the bucket by hand still moves the watermark (R7).

The test zone is restored afterwards.

## Delivery

One PR to JustChr: the fix, its tests and the rebuilt `dist/`. It is a singleton, so nothing
rides along. Its text names no issue of this fork. The `Eifel-Joe#5` body proposes the
allowlist, so the issue gets a comment on why the build differs, plus label `upstream:gemeldet`
once the PR is open.
