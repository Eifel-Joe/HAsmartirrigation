devs = (await ws_send({"type": "config/device_registry/list"})).get("result") or []
ents = (await ws_send({"type": "config/entity_registry/list"})).get("result") or []
{"devices_left": [[d.get("id"), d.get("name")] for d in devs if "livetest" in str(d.get("name") or "").lower()], "entities_left": [e.get("entity_id") for e in ents if "livetest" in str(e.get("entity_id") or "")]}
