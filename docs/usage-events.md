---
layout: default
title: Usage: Events
---

# Events

> Main page: [Usage](usage.md)<br/>
> Previous: [Services](usage-services.md)<br/>
> Next: [Automations](usage-automations.md)

The integration fires the following Home Assistant events:

| Event | When it fires |
| --- | --- |
|`smart_irrigation_start_irrigation_all_zones`|When a [recurring schedule](configuration-schedules.md) with the irrigate action runs. The event carries the schedule name and the targeted zones. Listen to this event if you control your valves with your own [automations](usage-automations.md) instead of [linked entities](configuration-my-zones.md#linked-entity).|
|`smart_irrigation_recurring_schedule_triggered`|Whenever any recurring schedule fires (before the action runs); carries the schedule details.|

> **Important:** the start event is fired **only by schedules** — if you have no irrigate schedule, it never fires. To reproduce the classic "irrigation finishes right at sunrise" behaviour, create a schedule of type **Sunrise** with the time anchor set to **Finish** (see [Schedules](configuration-schedules.md#time-anchor)); the schedule computes the start time from the estimated total duration for you.

Note that **Irrigate Now** (the dashboard button) does **not** fire the start event — it controls the linked entities directly. Zones without a linked entity are unaffected by it.

> Main page: [Usage](usage.md)<br/>
> Previous: [Services](usage-services.md)<br/>
> Next: [Automations](usage-automations.md)
