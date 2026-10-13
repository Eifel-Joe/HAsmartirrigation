async def keys():
    issues = (await ws_send({"type": "repairs/list_issues"})).get("result") or {}
    return {i.get("issue_id"): i.get("translation_key") for i in (issues.get("issues") or []) if i.get("domain") == "irrigation_plus"}

async def hourly():
    return ((await ws_send({"type": "irrigation_plus/config"})).get("result") or {}).get("hourlycalculation")

out = {"before": {"hourly": await hourly(), "keys": await keys()}}
r_on = await api_post("/irrigation_plus/config", {"hourlycalculation": True})
out["on"] = {"post": str(r_on)[:60], "hourly": await hourly(), "keys": await keys()}
r_off = await api_post("/irrigation_plus/config", {"hourlycalculation": False})
out["off"] = {"post": str(r_off)[:60], "hourly": await hourly(), "keys": await keys()}
out["now"] = (await call_tool("ha_eval_template", {"template": "{{ now().isoformat() }}"})).get("result")
out
