async def zone(zid):
    zs = (await ws_send({"type": "irrigation_plus/zones"})).get("result") or []
    return [z for z in zs if z.get("id") == zid][0]

out = {}
for zid in (9, 11):
    before = await zone(zid)
    r = await api_post("/irrigation_plus/zones", {"id": zid, "calculate": True})
    after = await zone(zid)
    expl = after.get("explanation") or ""
    i = expl.find("Sensor stumm")
    out[zid] = {
        "calc": str(r)[:60],
        "watermark_before": before.get("last_consumed_at"),
        "watermark_after": after.get("last_consumed_at"),
        "bucket": after.get("bucket"),
        "delta": after.get("delta"),
        "explanation": expl,
    }
out
