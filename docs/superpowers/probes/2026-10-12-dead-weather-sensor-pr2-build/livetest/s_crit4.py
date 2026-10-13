async def zone(zid):
    zs = (await ws_send({"type": "irrigation_plus/zones"})).get("result") or []
    return [z for z in zs if z.get("id") == zid][0]

out = {}
z0 = await zone(10)
out["before"] = {"last_consumed_at": z0.get("last_consumed_at"), "bucket": z0.get("bucket")}
out["on"] = str(await api_post("/irrigation_plus/config", {"hourlycalculation": True}))[:60]
out["calc"] = str(await api_post("/irrigation_plus/zones", {"id": 10, "calculate": True}))[:120]
z1 = await zone(10)
expl = z1.get("explanation") or ""
out["after"] = {
    "last_consumed_at": z1.get("last_consumed_at"),
    "last_calculated": z1.get("last_calculated"),
    "bucket": z1.get("bucket"),
    "has_silent_sentence": ("Sensor stumm" in expl) or ("sensor silent" in expl),
    "has_share_sentence": ("des Zeitraums gebucht" in expl) or ("of the period" in expl),
    "explanation_len": len(expl),
}
out["off"] = str(await api_post("/irrigation_plus/config", {"hourlycalculation": False}))[:60]
out["hourly_now"] = ((await ws_send({"type": "irrigation_plus/config"})).get("result") or {}).get("hourlycalculation")
out["now"] = (await call_tool("ha_eval_template", {"template": "{{ now().isoformat() }}"})).get("result")
out
