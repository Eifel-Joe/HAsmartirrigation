**Background.** Since #191 the seasonal outlook follows the daily calculation's rules and says it is an illustration. The climate behind it is still synthetic: a fixed yearly curve per latitude band; only the air pressure comes from the elevation. Every installation at 45° north or beyond gets the same year — January 0 °C and 120 mm of rain, July a monthly mean of 30 °C and 60 mm (mirrored in the south) — and all zones of an installation get the same climate. In the PR I offered real climate data as the next step; you wanted an issue for it first, to decide the shape here. No watering decision reads the outlook; this is only about the card, the service and the API.

**Goal.** The outlook works from real monthly values for the location wherever there are any, and says where they come from. Where there are none, the illustration stays as the fallback.

**Possible sources**

1. **A climate archive for the installation's coordinates**, e.g. Open-Meteo's Historical Weather API: reanalysis (ERA5 from 1940), daily values including maximum and minimum temperature, precipitation and FAO-56 ET0. No key is needed for non-commercial use, and Open-Meteo's terms explicitly count personal home automation as such; the data is licensed CC BY 4.0. Build monthly means over a reference period once, store them, refresh rarely.
   - For: twelve months at once for every installation, whether its zones use sensors or a weather service; Open-Meteo is already one of the integration's weather services.
   - Against: a new outgoing request carrying the coordinates, also from installations that call no service today; a grid of roughly 10 to 25 km depending on the model, so no microclimate; the source has to be credited.
2. **The long-term statistics of the sensors in a sensor group.** For sensors with a `state_class`, Home Assistant keeps hourly means, minima and maxima (sums for counters), never purges that table, and can return it per month.
   - For: no network, the installation's own readings taken on site, and per sensor group — zones with different sensor groups would get their own climate.
   - Against: only for values a sensor group takes from sensors, not from a weather service; every such sensor needs a `state_class`, and the rain a counter; only after a full year are all twelve months real, and until then a month without data falls back to the illustration.
3. **Both, in tiers:** the sensor statistics where a month has data, otherwise the archive, otherwise the illustration. The most complete, but also the most code and the most tests.

**To decide**

- Which source: 1, 2 or 3?
- For 1: a setting that stays off until switched on, or on as soon as Open-Meteo is the weather service? And which reference period, e.g. the last ten full years or 1991–2020?
- Should the card show per month where its values come from (archive with its period, own sensors, illustration)?

Without a preference on your side I would start with 1 as a setting; 2 could later be put in front of it. Happy to build it once the shape is settled.
