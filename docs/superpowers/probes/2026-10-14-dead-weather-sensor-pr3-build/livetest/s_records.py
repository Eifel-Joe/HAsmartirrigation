out = {}
for mid in (2, 3):
    r = await ws_send({"type": "irrigation_plus/weather_records", "mapping_id": mid, "limit": 50})
    res = r.get("result")
    if isinstance(res, list):
        out[str(mid)] = [[x.get("retrieval_time") or x.get("timestamp"), x.get("temperature"), x.get("humidity"), x.get("wind_speed") or x.get("windspeed"), x.get("solar_radiation") or x.get("solarradiation"), sorted(list(x.keys()))[:12]] for x in res]
    else:
        out[str(mid)] = {"type": str(type(res)), "error": str(r.get("error"))[:200], "keys": sorted(list(res.keys()))[:20] if isinstance(res, dict) else None}
out
