zones = (await ws_send({"type": "irrigation_plus/zones"})).get("result") or []
maps = (await ws_send({"type": "irrigation_plus/mappings"})).get("result") or []
issues = (await ws_send({"type": "repairs/list_issues"})).get("result") or {}
cfg = (await ws_send({"type": "irrigation_plus/config"})).get("result") or {}
{
    "zones": [[z.get("id"), z.get("name")] for z in zones],
    "groups": [[m.get("id"), m.get("name"), m.get("on_silent_sensor")] for m in maps],
    "irrigation_issues": [i.get("issue_id") for i in (issues.get("issues") or []) if i.get("domain") == "irrigation_plus"],
    "config": {k: cfg.get(k) for k in ("hourlycalculation", "autoupdateinterval", "autoupdateschedule", "autoupdateenabled", "calctime")},
}
