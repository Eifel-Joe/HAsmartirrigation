## Problem

Since #197 a sensor group set to *Pause* leaves out a silent sensor's time, but only in the daily calculation and only while "Hourly evapotranspiration" is off. With the hourly calculation on, the commit still books the frozen value. The live estimate cuts in neither form, so in the daily form it can size a run during an outage on more ET than is booked afterwards (#188). This is the third of the three PRs you asked for on #188: the hourly path and the live estimate. Rebased onto the merged master as announced, so the 14 commits are only the new ones.

## Fix

### Part A — the commit

- **One function cuts a zone's window for every caller** (`zone_blocked_spans` in `sensor_liveness.py`, taking the store, the zone and the window explicitly), so the commit and the live estimate get the same spans. The condition "only while the hourly calculation is off" is gone.
- **Hourly rows:** In each hour a blocked field is averaged over its own valid time only and never held into a span; after one, the value from before holds again, as in the daily form. Each hour is charged only for the time in which temperature, humidity, wind and the sun were all measured. An hour with no such time stays a row without readings and without ET: the hourly series stays complete, so a silent sensor does not send the window to the daily form. If a field is missing for any other reason, today's path to the daily form stays. Pressure is not required; where it is blocked, the altitude pressure steps in as today.
- **Clearness ratio:** A reading stamped inside a span counts neither as a measurement of its hour nor as the source of a ratio; after the span, the ratio from before holds until the next reading.
- **Replayed balance (sub-steps):** ET is placed only in measured time (blocked parts get sun weight 0; a dark hour spreads its share over its measured part). Only the placement moves, not the total. A blocked rain rate adds only its measured parts, so the steps still reconcile with the aggregate's rain, which is why #197 left the hourly form out.
- **The share follows the form that ran** (`required_sensor_fields`, shared with the live estimate): the hourly form needs temperature, humidity, wind and the sun, the daily form what it needed in #197. The hourly total already holds only the measured part and is not scaled again; the explanation names the time share with the same sentence as in #197.
- **What the user sees:** The notice variant and the WARNING from #197 no longer depend on the hourly calculation, and switching it no longer rewrites open notices. The panel help drops its last sentence, "Applies only while "Hourly evapotranspiration" (Experimental features) is off.", in all 8 languages (2 of the 4 bundles rebuilt). The docs name the fields each form needs, say what the hourly form does with a partly measured hour, and that the percentage counts time.

### Part B — the live estimate

- **The same spans at every reader:** computed once per refresh, from the estimate's anchor to its `now`, and handed to the aggregate and its rain, the hourly rows, the replayed balance and the current temperature; the latter is not read from a sensor that is silent right now.
- **Source chain:** A window emptied by a span yields 0 ET instead of `None`, so a span never sends the chain on to a weather service's hourly series, a source the commit never books from. The daily mirror books the share the commit books; a window silent throughout books 0 even when no usable forecast is at hand.
- **Projection to the decision point:** from the cut aggregate; whether the sensor will return is not assumed either way.
- **Carry and refresh:** The key of the completed-hour carry includes the group's outage records and its setting (the records, not the spans cut from them; an open span would otherwise change the key every minute). The liveness check refreshes the estimates once when an outage of a pausing group opens or closes, and unthrottled: a silent station sends no row afterwards that would make up for a swallowed refresh.
- A group set to *Keep the last value* is estimated as before.

### Where the build departs from, or pins down, my proposal on #188

1. **Clearness ratio:** The proposal said the held ratio does not bridge a span. As built, no reading inside a span counts, and after it the ratio from before holds. Otherwise the night hours after an evening span would not count.
2. **A required field of the hourly form blocked for the whole window:** the hourly form stays and books 0 ET instead of falling back to the daily form, which with a silent sun would have booked the full estimated day.
3. **The percentage counts time, not amount:** solar radiation silent at night lowers it while costing hardly any ET. An amount share would have had to price the blocked hours with the frozen value. The docs say so.
4. **Limit:** for Passthrough zones the live estimate has no sensor ET; there only a blocked rain rate is cut.

## Testing

- **80 new pytest cases**, 60 in five new test files and 20 in four existing ones; four tests that pinned the interim state of #197 are turned round or removed. Among them: byte-identical hourly rows, sub-steps, explanation and live result for *Keep the last value*, for no or empty spans and for spans of other fields (compared with `==`); a span at the start, in the middle and at the end of an hour, across a whole hour and across the whole window; a window that starts inside a span; only the pressure silent; offset stamps in the outage record; live bucket = booked bucket after an outage in both forms; the live estimate on its own mixin, without the calculation's.
- **37 mutations** of the load-bearing checks, each caught.
- **Full suite locally** (Python 3.12, HA 2024.12): the failing tests are the same by name as on `master`, passed 3925 → 4001. 32 of the new tests build a real coordinator and end locally with a teardown ERROR "Lingering timer"; 466 existing tests show the same local pattern, CI does not. `black` clean, `ruff` 0.17.1 (your new pin) clean; a fresh build of the bundles is byte-identical to the committed ones.
- **Live on a test instance**, hourly calculation and live estimate on, PyETO with measured sun, one MQTT device with temperature, humidity, wind and sun, one pausing and one keeping group on that device:
  - After 3 h the pausing group shows the notice variant from #197 although the hourly calculation is on; the keeping group shows the text from #190.
  - The pausing zone's live ET stopped growing from start + 3 h; its source throughout was the hourly sensor calculation, never the weather service. The keeping zone's kept growing.
  - After the return the pausing zone books 56 % of the ET, exactly the share computed beforehand from the stored times (window 5 h 34 min, 2 h 28 min of it blocked), with one sentence for all four fields and the water balance in 7 sub-steps. Just before the commit the live bucket was within 0.0001 mm of the booked one. The keeping zone books in full, with no sentence.
  - The sensors were silent for 5½ instead of the planned 3½ hours; the checks hold unchanged.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
