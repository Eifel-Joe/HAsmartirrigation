---
layout: default
title: Configuration: Schedules
---
# Schedules

> Main page: [Configuration](configuration.md)<br/>
> Previous: [Zone configuration](configuration-zones.md)<br/>
> Next: [Seasonal Adjustments](configuration-adjustments.md)

The **Schedules** tab lets you create recurring schedules that automatically calculate, update, or irrigate your zones — no Home Assistant automations needed.

## Creating a schedule

Click **Add Schedule** to open the schedule dialog. Fill in the following fields:

### Name
A descriptive name for the schedule, e.g. "Daily morning irrigation".

### Schedule type

| Type | Description |
|---|---|
| **Daily** | Runs every day at a specified time |
| **Weekly** | Runs on selected days of the week at a specified time |
| **Monthly** | Runs on a specific day of the month at a specified time |
| **Every N hours** | Runs at a fixed interval (e.g. every 6 hours) |

### Time (HH:MM)
For daily, weekly, and monthly schedules, specify the time of day to run (24-hour format).

### Days of week (weekly only)
Select one or more days of the week the schedule should fire.

### Day of month (monthly only)
The day of the month (1–31) the schedule should fire.

### Interval (interval type only)
The number of hours between runs.

### Action

| Action | What it does |
|---|---|
| **Calculate** | Runs the irrigation duration calculation for the selected zones. Updates the duration sensor without controlling any valves. |
| **Update** | Collects fresh weather data for the selected zones' sensor groups. |
| **Irrigate** | Fires the `smart_irrigation_start_irrigation_all_zones` event **and** directly controls all [linked entities](configuration-zones.md#linked-entity) for zones with duration > 0. |

### Zones
Choose **All zones** or select specific zones by name. For the `irrigate` action, only zones with a [linked entity](configuration-zones.md#linked-entity) and a calculated duration > 0 will actually open their valve.

### Enabled
Toggle a schedule on or off without deleting it. Disabled schedules are not tracked.

### Start date / End date (optional)
Limit the schedule to a date range. Leave empty for no restriction.

## Managing schedules

Each existing schedule is shown as a card with a summary of its settings. Use the **Edit** button to modify it or **Delete** to remove it.

## Tips

- Use a **Calculate** schedule at your normal calculation time (e.g. 23:00) and a separate **Irrigate** schedule timed to start after calculation finishes.
- For seasonal use, set a **start date** and **end date** so schedules only fire during your irrigation season.
- Combine with [Seasonal Adjustments](configuration-adjustments.md) to automatically adapt irrigation intensity by month.

> Main page: [Configuration](configuration.md)<br/>
> Previous: [Zone configuration](configuration-zones.md)<br/>
> Next: [Seasonal Adjustments](configuration-adjustments.md)
