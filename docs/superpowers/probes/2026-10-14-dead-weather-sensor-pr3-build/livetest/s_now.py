cfg = (await ws_send({"type": "irrigation_plus/config"})).get("result") or {}
{
    "now": (await call_tool("ha_eval_template", {"template": "{{ now().isoformat() }}"})).get("result"),
    "hourlycalculation": cfg.get("hourlycalculation"),
    "live_estimate_enabled": cfg.get("live_estimate_enabled"),
}
