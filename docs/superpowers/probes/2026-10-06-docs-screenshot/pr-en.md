## Problem

The screenshot in `docs/configuration-weather-location.md` dates from June. The Seasonal outlook card in it lacks the note line that calls its figures an illustration, and it shows the figures from before #191: the ET with the month's rain in it, and the rain peaking in July.

## Change

Only the image `docs/assets/images/configuration-weather-location-1.png`, at the same path, the same width (2288 px) and the same crop: Forecast, Weather Records and the Seasonal outlook with its note line. The test instance has two sensor groups, hence two tables. I left the page's text alone; it already describes the card as it is now.

## Testing

Taken on my test instance, which runs the same integration code as v2026.10.05: English UI, light theme, double pixel density. The card's twelve rows match the answer of `irrigation_plus/watering_calendar`, rounded to one decimal. The PNG carries no metadata and, at 222 kB, is smaller than the old one (288 kB).

## The card on a Static zone

You asked for this in the v2026.10.05 release notes. The card takes the monthly values of the first zone in the calendar, i.e. the enabled zone with the lowest id (`view-weather-data.ts`: "the climate columns are identical across zones, so take the first zone's monthly estimates"). That holds for rain and temperature. The ET column, however, depends on that zone's module: PyETO gives the reference ET, Static the zone's rate times the days of the month, Passthrough `average_daily_et` times the days (a simple seasonal curve of 2 to 4 mm a day).

On my test instance the first zone is a Static zone with no rate. There the card showed **ET 0.0 mm** in all twelve months, with rain and temperature as in the screenshot. For the screenshot I disabled the two Static zones for a few minutes so that a PyETO zone came first, and switched them back on afterwards. The instance has no Passthrough zone; I only read the Passthrough case in the code and did not look at it. I can't contribute anything on the southern hemisphere.

The page and the note line call the values derived from the latitude. With a Static zone first, that does not hold for the ET column. Shall I send a small PR so the column does not depend on which zone comes first? The shape is your call, for example the first PyETO zone, or an ET series that depends on no zone.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
