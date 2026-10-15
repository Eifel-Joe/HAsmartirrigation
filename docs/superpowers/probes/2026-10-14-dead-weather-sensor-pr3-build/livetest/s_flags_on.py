r = await api_post("/irrigation_plus/config", {"hourlycalculation": True, "live_estimate_enabled": True})
cfg = (await ws_send({"type": "irrigation_plus/config"})).get("result") or {}
{
    "post": str(r)[:60],
    "after": {k: cfg.get(k) for k in ["hourlycalculation", "live_estimate_enabled", "continuousupdates", "autoupdateinterval", "calctime"]},
}
