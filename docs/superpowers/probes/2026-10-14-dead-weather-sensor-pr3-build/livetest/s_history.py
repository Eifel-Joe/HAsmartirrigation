ids = ["sensor.irrigation_plus_lt_wegwerf_zone_live_deficit", "sensor.irrigation_plus_hasi61_b_live_deficit"]
r = await ws_send({
    "type": "history/history_during_period",
    "start_time": "2026-10-15T07:29:00+00:00",
    "end_time": "2026-10-15T13:30:00+00:00",
    "entity_ids": ids,
    "minimal_response": False,
    "no_attributes": False,
    "significant_changes_only": False,
})
res = r.get("result") or {}
out = {}
for eid in ids:
    rows = []
    last_a = {}
    for s in (res.get(eid) or []):
        a = s.get("a") or last_a
        last_a = a
        rows.append([s.get("lu"), s.get("s"), a.get("method"), a.get("et_since_calculation"), a.get("as_of")])
    out[eid] = rows
out
