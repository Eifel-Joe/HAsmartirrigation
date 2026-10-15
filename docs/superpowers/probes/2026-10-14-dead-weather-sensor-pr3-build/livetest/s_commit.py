zs = (await ws_send({"type": "irrigation_plus/zones"})).get("result") or []
ours = [z.get("id") for z in zs if str(z.get("name") or "").startswith("Livetest PR3")]
out = {"zones": ours, "before": {}, "calc": [], "after": []}
for z in zs:
    if z.get("id") in ours:
        out["before"][str(z.get("id"))] = {"bucket": z.get("bucket"), "last_consumed_at": z.get("last_consumed_at")}
for zid in ours:
    r = await api_post("/irrigation_plus/zones", {"id": zid, "calculate": True})
    out["calc"].append([zid, str(r)[:60]])
zs = (await ws_send({"type": "irrigation_plus/zones"})).get("result") or []
for z in zs:
    if z.get("id") in ours:
        out["after"].append({
            "id": z.get("id"), "name": z.get("name"), "bucket": z.get("bucket"), "delta": z.get("delta"),
            "last_consumed_at": z.get("last_consumed_at"), "last_calculated": z.get("last_calculated"),
            "explanation": z.get("explanation"),
        })
out
