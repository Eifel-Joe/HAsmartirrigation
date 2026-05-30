---
layout: default
title: Configuration: Seasonal Adjustments
---
# Seasonal Adjustments

> Main page: [Configuration](configuration.md)<br/>
> Previous: [Schedules](configuration-schedules.md)<br/>
> Next: [Sensor groups](configuration-sensor-groups.md)

The **Adjustments** tab lets you define month-range adjustments that automatically adapt irrigation intensity for different seasons — without any automations or blueprints.

## How it works

When a zone is calculated, the integration checks whether any active seasonal adjustments apply to it. If the current month falls within an adjustment's month range and the adjustment is enabled, the adjustment is applied before the final duration is computed:

- A **multiplier adjustment** scales the zone's multiplier (e.g. 1.5× = 50% more irrigation in summer)
- A **threshold adjustment** shifts the zone's bucket by a fixed number of mm (e.g. +5 mm = zone starts drier, requiring more irrigation)

Multiple adjustments can apply at the same time and they stack.

## Creating an adjustment

Click **Add Adjustment** to open the dialog:

### Name
A descriptive name, e.g. "Summer boost" or "Winter reduction".

### From month / To month
The inclusive month range during which this adjustment is active. To span a year boundary (e.g. November through February), set From = November and To = February — the integration handles cross-year ranges correctly.

### Multiplier adjustment
Multiplies the zone's multiplier during the active period. Examples:

| Value | Effect |
|---|---|
| 1.0 | No change (default) |
| 1.5 | 50% more irrigation |
| 0.7 | 30% less irrigation |

### Bucket threshold adjustment (mm)
Added to the zone's bucket at calculation time. A **positive** value means the zone starts with more water (less irrigation needed). A **negative** value means the zone starts drier (more irrigation needed). Use this if your soil dries out faster or slower in certain seasons.

### Zones
Choose **All zones** or select specific zones by name.

### Enabled
Toggle an adjustment on or off without deleting it.

## Managing adjustments

Each existing adjustment is shown as a card. Use **Edit** to modify or **Delete** to remove it.

## Example: typical seasonal setup

| Adjustment | Months | Multiplier | Threshold |
|---|---|---|---|
| Spring boost | March – May | 1.2 | 0 |
| Summer boost | June – August | 1.5 | 0 |
| Autumn reduction | September – November | 0.8 | 0 |
| Winter pause | December – February | 0.3 | 0 |

> Main page: [Configuration](configuration.md)<br/>
> Previous: [Schedules](configuration-schedules.md)<br/>
> Next: [Sensor groups](configuration-sensor-groups.md)
