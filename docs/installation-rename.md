---
layout: default
title: Installation: Moving from Smart Irrigation to Irrigation Plus
---
# Moving from Smart Irrigation to Irrigation Plus

> Main page: [Installation](installation.md)

This integration used to be called **Smart Irrigation** and used the
`smart_irrigation` domain. It is now **Irrigation Plus**, on `irrigation_plus`.

If you are installing for the first time, none of this applies to you — go to
[Download](installation-download.md).

## Why

This project is a community fork of
[jeroenterheerdt/HAsmartirrigation](https://github.com/jeroenterheerdt/HAsmartirrigation).
It kept the original `smart_irrigation` domain, and so does the
[upstream project that is maintained again](https://github.com/altmenorg/HAsmartirrigation).
Two integrations claiming one domain cannot coexist: they install into the same
folder, produce the same entity IDs, and register the same Lovelace card type —
so whichever loaded second silently lost, with no error anywhere.
[Issue #120](https://github.com/JustChr/HAsmartirrigation/issues/120) asked us to
stop sharing it, and we agreed. Renaming was the fork's job, not theirs.

## Do this in the right order

**Add Irrigation Plus BEFORE you remove Smart Irrigation.**

This is the opposite of what most integration guides tell you, and it matters:

- Your **weather service API key** lives in Smart Irrigation's *config entry*,
  not in its storage file. Removing the integration through the Home Assistant
  UI deletes that entry, and the key with it.
- Removing it also **deletes its storage file** (`.storage/smart_irrigation.storage`),
  which is where your zones, buckets, schedules and run history live.
- Your **history and long-term statistics** can only be carried across while the
  old entity registry entries still exist.

Delete the folder if you like — that leaves the config entry intact. But do not
remove the integration from **Settings → Devices & Services** until the new one
is set up and you are happy with it.

If you already deleted the folder *and* removed the entry that then showed as
broken, your storage file is still on disk and Irrigation Plus will import it —
zones, buckets, schedules and history all come back.

**Your API key does not.** It lives only in Smart Irrigation's config entry, and
nothing else on your system holds a copy, so once that entry is gone the key is
gone with it. v2026.09.06 was meant to stage a copy into the storage file for
exactly this case and never actually wrote one ([#128]); that release is tagged
and cannot be corrected, and the domain it shipped under now belongs to the
upstream project again, so there is no version of this that recovers it. The
import will tell you which service needs its key re-entered, and everything else
comes across untouched.

This is why the order above is not a convenience — it is the only path that
keeps the key.

[#128]: https://github.com/JustChr/HAsmartirrigation/issues/128

### Keep that window short, and pause watering before you open it

While both integrations are loaded, they are two complete, independently
scheduling irrigation controllers pointed at the same valves. They do not know
about each other. The single-flight claim on a distributor and the master/pump
reference count each live in memory **per integration**, and nothing in the
watering path ever asks whether the other domain is running. Your schedules were
copied, so both fire on the same second.

On a real garden that means:

- **The distributor ring loses its place.** Two sweeps drive one inlet valve, so
  the ring advances twice as far as either integration believes. Both keep
  reporting `synced`, and every later cycle builds on the wrong position.
- **The pump stops mid-run.** Whichever cycle finishes first releases its own
  master hold and switches the pump off seconds later — while the other still
  has valves open.
- **Both buckets book the full amount.** A zone without a flow sensor is credited
  from elapsed time, not from water actually observed. Where the two runs
  overlapped on one valve, both copies read "watered" while the plants got a
  fraction of it.

The last one is the dangerous one, and it is a drought rather than a flood: the
next day shows no demand, so nothing corrects it, and nothing in the log says a
word.

**So pause the old integration before you add the new one.** On Smart
Irrigation's **Zones** page, use **Pause watering → Delay 24 h**; for a longer
hold, call `smart_irrigation.set_rain_delay` with `hours` or `until`. The pause
is part of the stored configuration, so the import copies it and **both** copies
stay held. Manual runs are deliberately exempt from it, which is exactly what you
want for testing the new install. Once the old integration is gone and you have
restarted, release it with **Resume** on the new panel, or
`irrigation_plus.clear_rain_delay`.

If you would rather not pause anything: keep both installed for minutes rather
than days, and do it at a time of day when no schedule can fire.

## Steps

1. **Pause Smart Irrigation** — set a rain delay reaching past the end of the
   migration. See the section above for why this matters more than it sounds
   like it does.
2. **Update through HACS as normal.** HACS reads the new domain from the
   manifest and installs into `custom_components/irrigation_plus/`.
3. **Restart Home Assistant.**
4. Go to **Settings → Devices & Services → Add Integration** and add
   **Irrigation Plus**.
5. The first step of the setup asks whether to **import your existing Smart
   Irrigation installation**. Say yes.
6. Check the panel: your zones, schedules, buckets and history should all be
   there. Compare it against the old one — in this session, not next week. (If
   the sidebar panel or the card looks stale, hard-reload the browser with
   Ctrl-Shift-R — that is a cached frontend, not a failed import.)
7. **Let the repair finish the job.** Once your zones are across, a repair
   appears under **Settings → System → Repairs** offering to remove the old
   installation for you. It removes the Smart Irrigation integration entry
   first, then deletes the leftover `custom_components/smart_irrigation/`
   folder — in that order, because Home Assistant can only shut the old
   integration down properly while its files are still present.

   **Then restart, before you do anything else.** This restart is not
   housekeeping. Smart Irrigation never unregisters its services, so its 24
   `smart_irrigation.*` names survive the removal of its own config entry and
   its folder — pointing at an integration that is no longer there. Until you
   restart, an automation calling one of them does not fall through to the
   compatibility alias, because the alias could not be registered while the name
   was taken. The restart is what clears the dead names and puts the working
   aliases in their place.

   The repair is only offered when the migration demonstrably worked (your
   zones are here) and the folder belongs to this project rather than to the
   upstream one. Otherwise you get an informational notice instead, and the
   manual route below.
8. **Or do it by hand**, if you would rather: remove the integration at
   **Settings → Devices & Services → Smart Irrigation → ⋮ → Delete**, then
   delete `custom_components/smart_irrigation/` and restart. HACS does not
   remove that folder when an integration changes folder, and Home Assistant
   will otherwise load it as a second integration — two of every sensor, and
   two of every scheduled run.

## What is carried across automatically

| | |
|---|---|
| Zones, buckets, schedules, modules, sensor groups | ✅ imported |
| Run history and flow-learning state | ✅ imported |
| Weather service settings | ✅ imported |
| Your weather API key | ⚠️ only while the old config entry still exists — see [above](#do-this-in-the-right-order) |
| Recorded history (the graphs on each entity) | ✅ follows the new entity IDs |
| Long-term statistics | ✅ follows the new entity IDs |
| Zone device **area** assignments | ✅ copied onto the new devices |
| Lovelace cards using `custom:smart-irrigation-zones-card` | ✅ keep working; a repair offers to repoint them |
| `smart_irrigation.*` service calls in your automations | ⚠️ only once you have finished and restarted — see below |
| Per-entity settings you changed yourself (enabled/hidden, custom name, icon, display precision) | ❌ not carried — see below |

A **safety copy** of your old storage file is written to
`.storage/smart_irrigation.storage.pre-irrigation_plus.bak` before anything
else. Keep it until you are satisfied; it is the only copy that survives step 7.

## What you have to change yourself

### Entity IDs

Every entity ID changed. History and statistics follow, but an entity ID you
have typed into **your own** automations, scripts, templates or dashboards does
not — and nothing in Home Assistant rewrites those. A template pointing at an old
ID quietly renders `unknown` rather than raising an error, which is why this is
worth doing deliberately rather than waiting to notice.

The exact old → new table for **your** install is written to
`irrigation_plus_renamed_entities.md` next to your `configuration.yaml`, and a
repair notice points at it. **Use that table, not a global search-and-replace.**

Swapping `smart_irrigation` for `irrigation_plus` everywhere looks like it should
work, and for most zones it does. It breaks on any zone you have **renamed since
you created it**. Entity IDs are assigned once, when the entity is first created,
and Home Assistant does not rewrite them when you rename the zone — so the old
IDs still carry the zone's *original* name, while the new entities take its
*current* one. A zone created as "Cherry tree" and later renamed to "Bed 1" goes
from `sensor.smart_irrigation_cherry_tree` to `sensor.irrigation_plus_bed_1`, and
a blind replace leaves you pointing at `sensor.irrigation_plus_cherry_tree`,
which does not exist. That is the silent `unknown` this section exists to prevent.

The generated table has the real mapping for both halves of the name. Work
through it, then dismiss the notice.

### Entity settings you changed yourself

The migration creates fresh entities, so anything you set on the **old** ones in
the entity registry stays behind: whether an entity was enabled or hidden, a
custom name or icon, display precision, voice aliases, labels. Zone device
**areas** are copied onto the new devices; entity-level settings are not.

Most installs never touch these. The one that catches people is the per-zone
diagnostic sensors — *Last calculated*, *Last weather update*, *Weather data
points*, *Drainage*. They ship disabled, so if you switched some of them on, they
come back switched off. Re-enable them under the zone's device page.

### Event names

Automations triggered by `smart_irrigation_start_irrigation_all_zones` (or any
other `smart_irrigation_*` event) will **not** fire any more. Rename the trigger
to `irrigation_plus_start_irrigation_all_zones`. Unlike services, events are not
aliased — a mirrored event would fire a second time on any machine where both
integrations are installed, which is the collision this rename removed.

### Service calls (eventually)

Once the migration is finished and you have restarted, `smart_irrigation.reset_bucket`
and every other old service name works again: it forwards to
`irrigation_plus.reset_bucket` and logs a deprecation warning the first time it is
used. **This is a temporary compatibility layer and will be removed in a future
release**, so repoint your automations while you are already in there for the
entity IDs.

**During the migration itself, those names do not mean what you expect**, and it
is worth knowing which of the two it is at any moment:

| While… | `smart_irrigation.run_zone` reaches… |
|---|---|
| both integrations are installed | the **old** integration, and credits the **old** copy of your data |
| the old one is removed but you have not restarted | nothing usable — a dead handler |
| after the restart | the alias, forwarding to `irrigation_plus.run_zone` |

The alias can only be registered when the name is free, and the old integration
holds all 24 of them for as long as it is loaded — and, because it never
unregisters them, for the rest of that Home Assistant session after it is
removed. This is the whole reason step 7 insists on the restart.

The aliases are switched off permanently if a *different* `smart_irrigation`
integration is installed alongside this one — that project owns those names, and
claiming them would recreate the original collision.

### Blueprints

The bundled valve blueprints are now installed to
`config/blueprints/script/irrigation_plus/`. The old copies in
`config/blueprints/script/smart_irrigation/` are left alone on purpose: any
script you already created from one is still backed by that file. You will see
both sets in the blueprint list until you delete the old folder, which is safe
to do once no script depends on it.

## Running both integrations side by side

That is now supported, and is the point of the rename. This means **a different
project** on the `smart_irrigation` domain — not the old copy of *this* one,
which is what the migration window above is about, and which you should close
promptly. If you install the upstream `smart_irrigation` integration as well:

- The old Lovelace card type `custom:smart-irrigation-zones-card` belongs to
  **that** integration. Switch your cards to
  `custom:irrigation-plus-zones-card`; the repair notice will offer to do it.
- The `smart_irrigation.*` service aliases are not registered, so your
  automations must use `irrigation_plus.*`.

## If something went wrong

- **The panel is empty after importing.** Do not remove the old integration.
  Check the log for a line naming
  `.storage/smart_irrigation.storage.pre-irrigation_plus.bak` and
  [open an issue](https://github.com/Eifel-Joe/HAsmartirrigation/issues) with your
  diagnostics file — the backup still holds your configuration.
- **Two of every sensor.** The old `custom_components/smart_irrigation/` folder
  is still there. Delete it and restart — and treat it as urgent rather than
  cosmetic: two loaded integrations also means two schedulers on your valves.
- **`smart_irrigation.*` services stopped working, and the old integration is
  gone.** You have not restarted since the cleanup. Restart; the compatibility
  aliases are registered on the next start.
- **A zone's watering looks like it happened but the ground is dry.** If both
  integrations were loaded over a scheduled run, they overlapped on one valve and
  both credited the full amount. Correct the affected zones with
  `irrigation_plus.set_bucket`, or reset them and let the next daily calculation
  rebuild from the weather.
- **Weather updates are switched off after importing.** The API key could not be
  recovered, because the old config entry was already gone when the import ran
  and that entry is the only place the key ever lived. The setup flow says so at
  the time, naming the service. Everything else imported: re-enter the key under
  **Setup → Weather service** and it resumes.
- **Graphs start from scratch on one or two entities.** The recorder rename is
  applied per entity and any that failed are named in the log. The integration is
  fine; only those entities' history stays under the old ID.
- **The card shows a config error.** A stale cached frontend. Hard-reload
  (Ctrl-Shift-R) or restart Home Assistant.

---

> Looking for the old **V1 (0.0.X) to V2** guide? It is still at
> [Migrating from V1 to V2](installation-migration.md).
