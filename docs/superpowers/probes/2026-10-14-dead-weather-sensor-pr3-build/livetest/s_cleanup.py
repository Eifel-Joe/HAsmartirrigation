zs = (await ws_send({"type": "irrigation_plus/zones"})).get("result") or []
maps = (await ws_send({"type": "irrigation_plus/mappings"})).get("result") or []
mods = (await ws_send({"type": "irrigation_plus/modules"})).get("result") or []
out = {"removed": []}
for z in zs:
    if str(z.get("name") or "").startswith("Livetest PR3"):
        r = await api_post("/irrigation_plus/zones", {"id": z.get("id"), "remove": True})
        out["removed"].append(["zone", z.get("id"), str(r)[:40]])
for m in maps:
    if str(m.get("name") or "").startswith("Livetest PR3"):
        r = await api_post("/irrigation_plus/mappings", {"id": m.get("id"), "remove": True})
        out["removed"].append(["group", m.get("id"), str(r)[:40]])
for m in mods:
    if m.get("description") == "Livetest PR3 (measured sun)":
        r = await api_post("/irrigation_plus/modules", {"id": m.get("id"), "remove": True})
        out["removed"].append(["module", m.get("id"), str(r)[:40]])
r = await api_post("/irrigation_plus/config", {"hourlycalculation": False, "live_estimate_enabled": False})
out["config_post"] = str(r)[:60]
cfg = (await ws_send({"type": "irrigation_plus/config"})).get("result") or {}
out["config_after"] = {k: cfg.get(k) for k in ["hourlycalculation", "live_estimate_enabled", "continuousupdates", "autoupdateinterval", "calctime"]}
out["zones_left"] = [[z.get("id"), z.get("name")] for z in ((await ws_send({"type": "irrigation_plus/zones"})).get("result") or [])]
out["groups_left"] = [[m.get("id"), m.get("name"), m.get("on_silent_sensor")] for m in ((await ws_send({"type": "irrigation_plus/mappings"})).get("result") or [])]
out["modules_left"] = [[m.get("id"), m.get("name"), m.get("description")] for m in ((await ws_send({"type": "irrigation_plus/modules"})).get("result") or [])]
out
