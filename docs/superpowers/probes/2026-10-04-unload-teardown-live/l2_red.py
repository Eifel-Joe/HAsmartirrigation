"""L2 RED dump D5 (v2026.09.30b2, entry disabled after the dead backstop booked) -> both grids."""
import sys
from datetime import datetime, timezone

import green_grid as g

sys.stdout.reconfigure(encoding="utf-8")
starts = {
    "L1-RED-Lauf 07:39:37.053": datetime(2026, 10, 4, 5, 39, 37, 53010, tzinfo=timezone.utc),
    "L2-RED-Lauf 07:49:24.962": datetime(2026, 10, 4, 5, 49, 24, 961809, tzinfo=timezone.utc),
}
dumps = {
    "D5 07:53:17.814 (Eintrag deaktiviert, nach der Buchung des toten Backstops)": [
        1122342.962379309, 1122645.841417883, 1123546.54452065, 1122643.959856963, 1122345.954796837,
        1123544.383621887, 1123542.787277489, 1122344.18614947, 1130745.502905785, 1173945.489467832,
        1173945.4896246758, 1173942.516369549, 1122043.523105716, 1122044.607473908, 1122044.819665226,
        1130745.50280031, 1122046.982820791, 1122019.717636992, 1122016.043586193],
}
g.report("L2 RED (v2026.09.30b2), Deaktivieren mitten im Lauf", starts, dumps)
