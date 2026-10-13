now = (await call_tool("ha_eval_template", {"template": "{{ now().isoformat() }}"})).get("result")
maps = (await ws_send({"type": "irrigation_plus/mappings"})).get("result") or []
issues = (await ws_send({"type": "repairs/list_issues"})).get("result") or {}
ours = [
    {"issue_id": i.get("issue_id"), "translation_key": i.get("translation_key"), "placeholders": i.get("translation_placeholders"), "created": i.get("created")}
    for i in (issues.get("issues") or [])
    if i.get("domain") == "irrigation_plus"
]
cfg = (await ws_send({"type": "irrigation_plus/config"})).get("result") or {}
{
    "now": now,
    "hourlycalculation": cfg.get("hourlycalculation"),
    "groups": [{"id": m.get("id"), "name": m.get("name"), "on_silent_sensor": m.get("on_silent_sensor"), "outages": m.get("sensor_outages")} for m in maps if m.get("id") in (2, 3, 4)],
    "issues": ours,
}
