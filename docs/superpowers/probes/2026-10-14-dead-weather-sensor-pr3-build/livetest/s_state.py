T = "{{ now().isoformat() }}|{% for f in ['temperature','humidity','wind','solar'] %}{% set s = states['sensor.hasi_livetest_e_livetest_e_' ~ f] %}{{ f }}={{ s.state if s else 'none' }}@{{ s.last_reported.isoformat() if s else '' }};{% endfor %}"
probe = (await call_tool("ha_eval_template", {"template": T})).get("result")
cfg = (await ws_send({"type": "irrigation_plus/config"})).get("result") or {}
maps = (await ws_send({"type": "irrigation_plus/mappings"})).get("result") or []
issues = (await ws_send({"type": "repairs/list_issues"})).get("result") or {}
zs = (await ws_send({"type": "irrigation_plus/zones"})).get("result") or []
# HA hands a new zone the entity id of a deleted zone with the same number, so
# the live sensors are found by unique id (zone id), not by name.
ours = [z.get("id") for z in zs if str(z.get("name") or "").startswith("Livetest PR3")]
want = ["irrigation_plus_" + str(i) + "_live_deficit" for i in ours]
reg = (await ws_send({"type": "config/entity_registry/list"})).get("result") or []
live_ids = [e.get("entity_id") for e in reg if e.get("platform") == "irrigation_plus" and e.get("unique_id") in want]
live = {}
for eid in live_ids:
    s = await api_get("/states/" + eid)
    a = s.get("attributes") or {}
    live[eid] = {
        "state": s.get("state"),
        "method": a.get("method"),
        "et_since": a.get("et_since_calculation"),
        "precip_since": a.get("precipitation_since_calculation"),
        "drainage_since": a.get("drainage_since_calculation"),
        "as_of": a.get("as_of"),
        "balance_form": a.get("balance_form"),
        "forecast_tier": a.get("forecast_tier"),
        "reason": a.get("unavailable_reason"),
    }
{
    "probe": probe,
    "hourlycalculation": cfg.get("hourlycalculation"),
    "live_estimate_enabled": cfg.get("live_estimate_enabled"),
    "groups": [
        {"id": m.get("id"), "name": m.get("name"), "on_silent_sensor": m.get("on_silent_sensor"), "outages": m.get("sensor_outages")}
        for m in maps if str(m.get("name") or "").startswith("Livetest PR3")
    ],
    "issues": [
        {"issue_id": i.get("issue_id"), "translation_key": i.get("translation_key"), "placeholders": i.get("translation_placeholders"), "created": i.get("created")}
        for i in (issues.get("issues") or []) if i.get("domain") == "irrigation_plus"
    ],
    "zones": [
        {"id": z.get("id"), "name": z.get("name"), "bucket": z.get("bucket"), "last_consumed_at": z.get("last_consumed_at"), "last_calculated": z.get("last_calculated")}
        for z in zs if str(z.get("name") or "").startswith("Livetest PR3")
    ],
    "live": live,
}
