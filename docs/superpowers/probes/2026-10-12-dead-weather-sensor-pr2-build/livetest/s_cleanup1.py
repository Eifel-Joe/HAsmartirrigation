out = {}
zones_now = [z.get("id") for z in ((await ws_send({"type": "irrigation_plus/zones"})).get("result") or [])]
for zid in (9, 10, 11):
    if zid in zones_now:
        r = await api_post("/irrigation_plus/zones", {"id": zid, "remove": True})
        out["zone_" + str(zid)] = str(r)[:60]
groups_now = [m.get("id") for m in ((await ws_send({"type": "irrigation_plus/mappings"})).get("result") or [])]
for gid in (2, 3, 4):
    if gid in groups_now:
        r = await api_post("/irrigation_plus/mappings", {"id": gid, "remove": True})
        out["group_" + str(gid)] = str(r)[:60]
zones = (await ws_send({"type": "irrigation_plus/zones"})).get("result") or []
maps = (await ws_send({"type": "irrigation_plus/mappings"})).get("result") or []
issues = (await ws_send({"type": "repairs/list_issues"})).get("result") or {}
cfg = (await ws_send({"type": "irrigation_plus/config"})).get("result") or {}
out["zones_left"] = [z.get("id") for z in zones]
out["groups_left"] = [[m.get("id"), m.get("name"), m.get("on_silent_sensor")] for m in maps]
out["irrigation_issues"] = [i.get("issue_id") for i in (issues.get("issues") or []) if i.get("domain") == "irrigation_plus"]
out["config"] = {k: cfg.get(k) for k in ("hourlycalculation", "autoupdateinterval", "autoupdateschedule", "autoupdateenabled", "calctime")}
out
