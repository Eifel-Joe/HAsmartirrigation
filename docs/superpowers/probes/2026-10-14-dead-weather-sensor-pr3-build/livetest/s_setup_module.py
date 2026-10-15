r = await api_post(
    "/irrigation_plus/modules",
    {
        "name": "PyETO",
        "description": "Livetest PR3 (measured sun)",
        "config": {"coastal": False, "solrad_behavior": "3", "forecast_days": 0},
    },
)
mods = (await ws_send({"type": "irrigation_plus/modules"})).get("result") or []
{
    "post": r,
    "modules": [
        {"id": m.get("id"), "name": m.get("name"), "description": m.get("description"), "config": m.get("config")}
        for m in mods
    ],
}
