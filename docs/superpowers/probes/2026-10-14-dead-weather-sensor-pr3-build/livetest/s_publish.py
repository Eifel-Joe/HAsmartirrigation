vals = {"temperature": "15.0", "humidity": "70", "wind": "2.0", "solar": "350"}
before = (await call_tool("ha_eval_template", {"template": "{{ now().isoformat() }}"})).get("result")
for f, v in vals.items():
    await api_post("/services/mqtt/publish", {"topic": "hasi_livetest/e/" + f, "payload": v})
{"published_after": before, "values": vals}
