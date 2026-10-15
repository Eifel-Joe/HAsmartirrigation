r = await api_post("/services/mqtt/reload", {})
ents = (await ws_send({"type": "config/entity_registry/list"})).get("result") or []
mine = [e for e in ents if "livetest_e" in str(e.get("entity_id") or "")]
T = "{% for s in states.sensor if 'livetest_e' in s.entity_id %}{{ s.entity_id }}={{ s.state }} [{{ s.attributes.unit_of_measurement }}] dev={{ device_attr(s.entity_id, 'name') }};{% endfor %}"
{
    "reload": str(r)[:60],
    "registry": [[e.get("entity_id"), e.get("device_id"), e.get("config_entry_id"), e.get("unique_id")] for e in mine],
    "states": (await call_tool("ha_eval_template", {"template": T})).get("result"),
}
