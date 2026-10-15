E = "sensor.hasi_livetest_e_livetest_e_"
fields = {
    "Temperature": {"source": "sensor", "sensorentity": E + "temperature", "unit": "°C"},
    "Humidity": {"source": "sensor", "sensorentity": E + "humidity", "unit": "%"},
    "Windspeed": {"source": "sensor", "sensorentity": E + "wind", "unit": "km/h"},
    "Solar Radiation": {"source": "sensor", "sensorentity": E + "solar", "unit": "W/m2"},
    "Dewpoint": {"source": "none", "sensorentity": "", "unit": ""},
    "Pressure": {"source": "none", "sensorentity": "", "unit": ""},
    "Precipitation": {"source": "none", "sensorentity": "", "unit": ""},
    "Current Precipitation": {"source": "none", "sensorentity": "", "unit": ""},
    "Evapotranspiration": {"source": "none", "sensorentity": "", "unit": ""},
}
rp = await api_post(
    "/irrigation_plus/mappings",
    {"name": "Livetest PR3 Pause", "on_silent_sensor": "pause", "mappings": fields},
)
rk = await api_post(
    "/irrigation_plus/mappings",
    {"name": "Livetest PR3 Keep", "on_silent_sensor": "keep", "mappings": fields},
)
maps = (await ws_send({"type": "irrigation_plus/mappings"})).get("result") or []
{
    "post_pause": rp,
    "post_keep": rk,
    "groups": [
        {
            "id": m.get("id"),
            "name": m.get("name"),
            "on_silent_sensor": m.get("on_silent_sensor"),
            "sensors": sorted(
                [
                    f + "=" + str(c.get("sensorentity"))
                    for f, c in (m.get("mappings") or {}).items()
                    if isinstance(c, dict) and c.get("source") == "sensor"
                ]
            ),
        }
        for m in maps
    ],
}
