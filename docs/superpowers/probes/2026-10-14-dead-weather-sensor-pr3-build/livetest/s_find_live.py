ents = (await ws_send({"type": "config/entity_registry/list"})).get("result") or []
hits = [
    [e.get("entity_id"), e.get("unique_id"), e.get("disabled_by"), e.get("translation_key")]
    for e in ents
    if e.get("platform") == "irrigation_plus" and ("livetest" in str(e.get("entity_id") or "") or "live" in str(e.get("unique_id") or ""))
]
hits
