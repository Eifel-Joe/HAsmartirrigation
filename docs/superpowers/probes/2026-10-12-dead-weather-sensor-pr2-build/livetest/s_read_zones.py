zs = (await ws_send({"type": "irrigation_plus/zones"})).get("result") or []
{str(z.get("id")): {"last_consumed_at": z.get("last_consumed_at"), "last_calculated": z.get("last_calculated"), "bucket": z.get("bucket"), "delta": z.get("delta"), "explanation": z.get("explanation")} for z in zs if z.get("id") in (9, 10, 11)}
