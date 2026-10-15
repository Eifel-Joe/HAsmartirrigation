mods = (await ws_send({"type": "irrigation_plus/modules"})).get("result") or []
maps = (await ws_send({"type": "irrigation_plus/mappings"})).get("result") or []
mid = [m.get("id") for m in mods if m.get("description") == "Livetest PR3 (measured sun)"][0]
pid = [m.get("id") for m in maps if m.get("name") == "Livetest PR3 Pause"][0]
kid = [m.get("id") for m in maps if m.get("name") == "Livetest PR3 Keep"][0]
rp = await api_post(
    "/irrigation_plus/zones",
    {
        "name": "Livetest PR3 Pause Zone", "size": 10, "throughput": 10, "state": "automatic",
        "mapping": pid, "module": mid,
        "duration": 0, "bucket": 0, "delta": 0, "explanation": "", "multiplier": 1,
        "lead_time": 0, "current_drainage": 0,
    },
)
rk = await api_post(
    "/irrigation_plus/zones",
    {
        "name": "Livetest PR3 Keep Zone", "size": 10, "throughput": 10, "state": "automatic",
        "mapping": kid, "module": mid,
        "duration": 0, "bucket": 0, "delta": 0, "explanation": "", "multiplier": 1,
        "lead_time": 0, "current_drainage": 0,
    },
)
zs = (await ws_send({"type": "irrigation_plus/zones"})).get("result") or []
{
    "module": mid, "pause_group": pid, "keep_group": kid, "post_pause": rp, "post_keep": rk,
    "zones": [
        {"id": z.get("id"), "name": z.get("name"), "mapping": z.get("mapping"), "module": z.get("module"), "state": z.get("state")}
        for z in zs
    ],
}
