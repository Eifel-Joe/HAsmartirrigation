vals = [("hasi_livetest/a/temperature", "18.5"), ("hasi_livetest/a/dewpoint", "12.0"), ("hasi_livetest/a/wind", "2.0"), ("hasi_livetest/a/pressure", "1013.0"), ("hasi_livetest/b/rain", "5.0")]
for topic, payload in vals:
    await call_tool("ha_call_service", {"domain": "mqtt", "service": "publish", "data": {"topic": topic, "payload": payload, "retain": False}})
t = "{% for e in ['sensor.hasi_livetest_a_livetest_a_temperature','sensor.hasi_livetest_a_livetest_a_dewpoint','sensor.hasi_livetest_a_livetest_a_wind','sensor.hasi_livetest_a_livetest_a_pressure','sensor.hasi_livetest_b_livetest_b_rain'] %}{{ e }}={{ states(e) }} @ {{ states[e].last_reported.astimezone(now().tzinfo).isoformat() }}\n{% endfor %}"
(await call_tool("ha_eval_template", {"template": t})).get("result")
