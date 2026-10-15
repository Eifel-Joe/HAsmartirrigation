o = (await ws_send({"type": "irrigation_plus/irrigation_outlook"})).get("result") or {}
est = o.get("zone_estimates") or {}
{
    "keys": sorted(list(o.keys())),
    "est_keys": sorted(list(est.keys())) if isinstance(est, dict) else str(type(est)),
    "z9": est.get("9") if isinstance(est, dict) else None,
    "z10": est.get("10") if isinstance(est, dict) else None,
}
