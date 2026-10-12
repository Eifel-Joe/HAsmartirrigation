import re
START = "2026-10-11 16:21:09"
PAGE = 100
MAXPAGES = 25
ANSI = re.compile(r"\x1b\[[0-9;]*m")
TS = re.compile(r"^(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d\.\d{3}) (\w+) \(([^)]*)\)")
KINDS = [
    ("OWMClient get_data called API", "real_get_data"),
    ("OWMClient get_forecast_data called API", "real_get_forecast_data"),
    ("Returning cached OWM forecastdata", "cached_forecast"),
    ("Returning cached OWM data", "cached_data"),
    ("Connection pool is full", "pool_full"),
    ("Error reading from OWM forecast", "owm_forecast_error"),
    ("Cannot interact with OWM API", "owm_http_error"),
]
events = []
seen = []
oldest = None
newest = None
scanned = 0
page = 0
done = False
while page < MAXPAGES and not done:
    r = await call_tool("ha_get_logs", {"source": "error_log", "limit": PAGE, "order": "newest", "offset": page * PAGE})
    txt = r.get("log") if isinstance(r, dict) else str(r)
    r = None
    lines = (txt or "").split("\n")
    txt = None
    page += 1
    for ln in lines:
        head = ANSI.sub("", ln[:260])
        m = TS.match(head)
        if not m:
            continue
        scanned += 1
        ts = m.group(1)
        if oldest is None or ts < oldest:
            oldest = ts
        if newest is None or ts > newest:
            newest = ts
        if ts < START:
            done = True
            continue
        for marker, kind in KINDS:
            if marker in head:
                key = ts + "|" + kind + "|" + m.group(3)
                if key not in seen:
                    seen.append(key)
                    events.append([ts, m.group(2), m.group(3), kind])
                break
    lines = None
events.sort()
counts = {}
for e in events:
    counts[e[3]] = counts.get(e[3], 0) + 1
{"pages": page, "scanned_heads": scanned, "oldest_seen": oldest, "newest_seen": newest, "reached_start": done, "counts": counts, "events": events}
