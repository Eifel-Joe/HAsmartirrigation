zs = (await ws_send({"type": "irrigation_plus/zones"})).get("result") or []
ours = [z.get("id") for z in zs if str(z.get("name") or "").startswith("Livetest PR3")]
out = {"zones": ours, "steps": []}
for zid in ours:
    r = await api_post("/irrigation_plus/zones", {"id": zid, "update": True})
    out["steps"].append(["update", zid, str(r)[:60]])
for zid in ours:
    r = await api_post("/irrigation_plus/zones", {"id": zid, "calculate": True})
    out["steps"].append(["calculate", zid, str(r)[:60]])
zs = (await ws_send({"type": "irrigation_plus/zones"})).get("result") or []
out["after"] = [
    {"id": z.get("id"), "name": z.get("name"), "bucket": z.get("bucket"), "last_consumed_at": z.get("last_consumed_at"), "last_calculated": z.get("last_calculated"), "explanation": z.get("explanation")}
    for z in zs if z.get("id") in ours
]
out
