## English

**Finding (2026-10-06, live on HA-Test, Home Assistant 2026.9.4, pre-release v2026.10.06b1).** After the config entry
is reloaded (options saved, or "Reload"), the entities of an existing distributor stay `unavailable` until Home
Assistant restarts. Observed for distributor "Gardena1": `current_outlet`, `outlet_1_zone` … `outlet_6_zone`,
`commissioned`, `watering_now` — all nine went `unavailable` at the moment of the reload and came back only with a
restart. Zone entities are not affected. Pre-existing upstream; not caused by the device-registry PR during whose live
test it showed up (that PR touches neither the platform files nor `async_unload`).

**Cause.** `SmartIrrigationCoordinator.async_unload` (`__init__.py`) clears the per-zone entity trackers in
`hass.data[DOMAIN]` (`zones`, `bucket_sensors`, `multiplier_numbers`, `zone_extra_sensors`, `zone_binary_sensors`,
`zone_buttons`) — its comment describes exactly this failure for the zone trackers — but not the three distributor
trackers: `distributor_sensors` (`sensor.py`), `distributor_binary_sensors` (`binary_sensor.py`) and
`distributor_buttons` (`button.py`). `hass.data[DOMAIN]` survives a reload, so after it each platform's add callback
finds the distributor already registered with the unloaded entity objects and adds nothing.

**Impact.** Only installations with a distributor, and only until the next restart: the distributor's sensors, its
`watering_now`/`commissioned` binary sensors and its buttons are unavailable (automations on `watering_now` see
`unavailable`). HA-Prod has no distributor.

**Fix idea.** Clear the three distributor trackers in `async_unload` alongside the zone trackers, and pin it with a
reload test as for the zones.

**Former designations:** none (new finding).

## Deutsch

**Befund (2026-10-06, live auf HA-Test, Home Assistant 2026.9.4, Pre-Release v2026.10.06b1).** Nach einem Reload des
Config-Eintrags (Optionen gespeichert oder „Neu laden“) bleiben die Entities eines bestehenden Verteilers
`unavailable`, bis Home Assistant neu startet. Beobachtet am Verteiler „Gardena1“: `current_outlet`, `outlet_1_zone` …
`outlet_6_zone`, `commissioned`, `watering_now` — alle neun wurden im Moment des Reloads `unavailable` und kamen erst
mit einem Neustart zurück. Zonen-Entities sind nicht betroffen. Vorbestehend upstream; nicht verursacht durch den
Geräte-Registry-PR, in dessen Live-Test es auffiel (der PR berührt weder die Plattform-Dateien noch `async_unload`).

**Ursache.** `SmartIrrigationCoordinator.async_unload` (`__init__.py`) leert die Zonen-Tracker in `hass.data[DOMAIN]`
(`zones`, `bucket_sensors`, `multiplier_numbers`, `zone_extra_sensors`, `zone_binary_sensors`, `zone_buttons`) — sein
Kommentar beschreibt genau diesen Fehler für die Zonen-Tracker —, aber nicht die drei Verteiler-Tracker:
`distributor_sensors` (`sensor.py`), `distributor_binary_sensors` (`binary_sensor.py`) und `distributor_buttons`
(`button.py`). `hass.data[DOMAIN]` überlebt einen Reload; danach findet jeder Plattform-Callback den Verteiler mit den
entladenen Entity-Objekten schon registriert und legt nichts an.

**Wirkung.** Nur Installationen mit Verteiler, und nur bis zum nächsten Neustart: die Sensoren des Verteilers, seine
Binärsensoren `watering_now`/`commissioned` und seine Knöpfe sind `unavailable` (Automationen auf `watering_now` sehen
`unavailable`). HA-Prod hat keinen Verteiler.

**Lösungsidee.** Die drei Verteiler-Tracker in `async_unload` mit den Zonen-Trackern leeren und mit einem Reload-Test
pinnen, wie bei den Zonen.

**Frühere Bezeichnungen:** keine (neuer Befund).
