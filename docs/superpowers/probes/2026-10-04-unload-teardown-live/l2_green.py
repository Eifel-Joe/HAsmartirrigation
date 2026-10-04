"""L2 GREEN dump (v2026.10.04b1, entry disabled mid-run) -> sampler grids."""
import sys
from datetime import datetime, timezone

import green_grid as g

sys.stdout.reconfigure(encoding="utf-8")
starts = {
    "L1-GREEN-Lauf 07:58:08.857": datetime(2026, 10, 4, 5, 58, 8, 856558, tzinfo=timezone.utc),
    "L2-GREEN-Lauf 08:02:55.557": datetime(2026, 10, 4, 6, 2, 55, 556652, tzinfo=timezone.utc),
}
dumps = {
    "D4' 08:04:43.456 (Eintrag deaktiviert, 47 s nach dem Stopp)": [
        1143785.442830658, 1208579.994031816, 1123984.141218075, 1294985.44282591, 1294985.442816523,
        1125786.386069551, 1122785.444302225, 1143785.442845169, 1122780.305391488, 1122782.007458079,
        1123085.436046899, 1122782.383110073, 1123081.767923034, 1122781.10289906, 1123980.300597265,
        1122705.900102933, 1122785.442839167, 1122779.988740466],
}
g.report("L2 GREEN (v2026.10.04b1), Deaktivieren mitten im Lauf", starts, dumps)
