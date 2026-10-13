## Problem

Since #190 the integration notices when a sensor of a sensor group falls silent, and says so. It still calculates with that sensor's last value for as long as the outage lasts, though (#188). This is the second of the three PRs you asked for on #188: the cut in the daily path.

## Fix

- **A setting per sensor group**, "When a sensor goes silent": *Pause* or *Keep the last value*. As you asked, every existing group loads as *keep* and calculates and explains byte-identically to before; only newly created groups (panel and first setup) pause. A missing or unknown stored value counts as *keep*. No storage version change; an older panel that does not send the key leaves the setting as it is.
- **The cut, only in the daily path and only while "Hourly evapotranspiration" is off.** For a pausing group the commit blocks each field from the outage start + 3 h to its end (half-open; an open outage up to the commit's `now`). It reads only the outage record from #190 and runs no check of its own. The aggregate reduces a blocked field over its valid time only: a frozen row inside the block does not count, a value is not held into a block, and after it the value from before holds again. A cumulative rain gauge (`delta`) is never blocked; a rain rate is.
- **Only the measured share is booked.** Each module names its required fields (PyETO's daily form: temperature, dewpoint, wind speed, pressure; Passthrough: its ET sensor). ET is multiplied by the share of the window in which all required fields were valid together. If a required field is blocked for the whole window, the module is not asked: 0 ET, no "missing" WARNING, no Passthrough ERROR, and the window counts as consumed. Rain is still booked in full. A silent field the module does without (humidity, solar radiation) leaves the share unchanged.
- **What the user sees:**
  - The zone's explanation names the silent time ("No values from Dewpoint, Pressure … from … to … (sensor silent).") and the share booked in whole percent, between 1 and 99 unless it is exactly 0 or 1.
  - The repair issue from #190 has a variant for a group that actually cuts: pausing, without the hourly calculation, and with an open outage on a field that is cut. It says that the values are no longer used and that, where the calculation cannot do without them, no ET is booked. Every other group keeps the text from #190. The issue is brought in line when the setting, the hourly calculation or the group's mapping changes; the WARNING at the start follows the same rule.
  - Panel: a choice in the sensor group's card, all texts in 8 languages. The sensor groups page of the docs explains both settings. It also warns that, under *Pause*, a sensor without a device that reports only on change (such as the wind template on the same page) is left out on a calm night.
- The two records (`_record_window_amplitude`, `_record_window_radiation`) skip a window in which their field was blocked.

**Where the build differs from my proposal on #188:**

1. **The explanation** has two sentences instead of one: the block and the share booked.
2. **The whole mean × share.** In the daily form the mean of weather and forecast days is multiplied by the share as a whole, not just its weather part.
3. **Partial days are a known limit.** The daily form averages a paused field over the hours in which it reported, so which part of the day was missing shifts the result. Free of that limit is the hourly form, which the third PR cuts as well. The docs say so.
4. **The hourly form and the live estimate do not cut yet** (third PR). With the hourly calculation on, everything stays as it is today, the notice text included. The live estimate can therefore size a run during an outage on more ET than the commit books afterwards; the docs and the code say so.
5. **Going back to an older build:** a *Pause* setting is lost (the older build writes the group without the key) and reads as *keep* after upgrading again. No data is lost.

## Testing

- 106 new pytest cases: 94 in four new test files, 12 in `tests/test_sensor_liveness_coordinator.py`; plus 2 vitest cases for the panel's save. Among them: byte-identical calculation and explanation for a *keep* group, offset stamps in the outage record, buffer rows behind `now`, a Static zone in a pausing group, a zone without a group or with a deleted one, a rain gauge on its own, the rounding of the share.
- 37 mutations of the load-bearing checks, each run against all five test files: every one caught by at least one test.
- Full suite locally (Python 3.12, HA 2024.12): the failing tests are the same by name as on `master`, passed 3819 → 3925. On top come 36 teardown ERRORs "Lingering timer" of new tests that build a real coordinator; 430 existing tests show the same local pattern, CI does not. `black` clean; `ruff` (0.16.10, the version of your last CI run) clean.
- PR 1 ran on my own installation (one EcoWitt station, 8 sensors) from 5 to 12 October without a single false alarm, including days at 95–99 % humidity and a restart.
- Live on a test instance (HA 2026.10.0) with MQTT sensors we control: one device with temperature, dewpoint, wind speed and pressure, a rain gauge on a second device; three groups (pause, keep, and pause with only the rain gauge); 3½ h of silence.
  - After 3 h: the pausing group shows the new notice variant and the WARNING with the cut text. The keeping group, and the pausing group whose only silent sensor is the rain gauge, show the text from #190.
  - "Hourly evapotranspiration" on: the pausing group shows the text from #190 too, and a calculation of its zone has no sentence. Off again: the variant comes back.
  - After the return, the pausing group's zone books 84 % of the ET, exactly the share computed beforehand from the stored times (window 3 h 42 min, blocked 36½ min). The keeping group's zone books in full and has no sentence.
  - Found along the way: a device's fields return milliseconds apart, so each outage ends at its own instant, and the explanation wrote four identical sentences instead of one. It now groups by the span as the sentence shows it (a commit of its own, with tests for this case and for the order of the sentences).

🤖 Generated with [Claude Code](https://claude.com/claude-code)
