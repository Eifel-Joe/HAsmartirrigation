devs = (await ws_send({"type": "config/device_registry/list"})).get("result") or []
ents = (await ws_send({"type": "config/entity_registry/list"})).get("result") or []
issues = (await ws_send({"type": "repairs/list_issues"})).get("result") or {}
cfg = (await ws_send({"type": "irrigation_plus/config"})).get("result") or {}
T = "{{ states | selectattr('entity_id', 'search', 'livetest') | map(attribute='entity_id') | list }}"
{
    "devices_livetest": [d.get("name") for d in devs if "livetest" in str(d.get("name") or "").lower()],
    "entities_livetest": [e.get("entity_id") for e in ents if "livetest" in str(e.get("entity_id") or "")],
    "states_livetest": (await call_tool("ha_eval_template", {"template": T})).get("result"),
    "zone_9_10_entities": [[e.get("entity_id"), e.get("unique_id")] for e in ents if e.get("platform") == "irrigation_plus" and (str(e.get("unique_id") or "").startswith("irrigation_plus_9_") or str(e.get("unique_id") or "").startswith("irrigation_plus_10_"))],
    "issues": [i.get("issue_id") for i in (issues.get("issues") or []) if i.get("domain") == "irrigation_plus"],
    "config": {k: cfg.get(k) for k in ["hourlycalculation", "live_estimate_enabled", "continuousupdates", "autoupdateinterval", "calctime", "weather_service"]},
}
