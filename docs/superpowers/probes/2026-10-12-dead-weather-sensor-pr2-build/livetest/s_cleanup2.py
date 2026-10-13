ents = (await ws_send({"type": "config/entity_registry/list"})).get("result") or []
mine = [e for e in ents if str(e.get("entity_id", "")).startswith("sensor.hasi_livetest_")]
out = {"entities_before": [e.get("entity_id") for e in mine]}
removed = []
for e in mine:
    r = await ws_send({"type": "config/entity_registry/remove", "entity_id": e.get("entity_id")})
    removed.append([e.get("entity_id"), r.get("success")])
out["entities_removed"] = removed
devs = (await ws_send({"type": "config/device_registry/list"})).get("result") or []
mydevs = [d for d in devs if str(d.get("name") or "").startswith("HASI Livetest")]
out["devices_before"] = [[d.get("id"), d.get("name"), d.get("config_entries")] for d in mydevs]
drem = []
for d in mydevs:
    for ce in (d.get("config_entries") or []):
        r = await ws_send({"type": "config/device_registry/remove_config_entry", "device_id": d.get("id"), "config_entry_id": ce})
        drem.append([d.get("name"), ce, r.get("success"), str(r.get("error"))[:80]])
out["devices_removed"] = drem
devs2 = (await ws_send({"type": "config/device_registry/list"})).get("result") or []
ents2 = (await ws_send({"type": "config/entity_registry/list"})).get("result") or []
out["devices_left"] = [d.get("name") for d in devs2 if "livetest" in str(d.get("name") or "").lower()]
out["entities_left"] = [e.get("entity_id") for e in ents2 if "livetest" in str(e.get("entity_id") or "")]
out
