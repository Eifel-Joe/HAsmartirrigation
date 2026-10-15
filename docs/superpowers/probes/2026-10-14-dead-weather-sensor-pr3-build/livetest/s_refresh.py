before = (await call_tool("ha_eval_template", {"template": "{{ now().isoformat() }}"})).get("result")
r = await api_post("/services/irrigation_plus/update_all_zones", {})
{"called_after": before, "result": str(r)[:120]}
