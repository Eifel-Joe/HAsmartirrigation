"""Eifel-Joe#66 reproduction, count mode, on HA-Test ONLY (via pr146-work's MCP client).

Sequence: foreign inlet open -> wait > 2*skip_pulse -> irrigate_now(member at the
advanced position) -> watch the cycle -> close the flow probe. Prints a timeline with
HA's own timestamps. Writes: logger level, the emulator valve, the flow probe, and the
irrigate_now websocket command. Never prints the endpoint or the config entry options.
"""
import json
import sys
import time

sys.path.insert(0, r"D:\Entwicklung\HASI\pr146-work\live")
import mcp_test  # noqa: E402
import hasi_read  # noqa: E402

VALVE = "input_boolean.sonoff_emu_valve"
PROBE = "input_number.hasi_flow_probe"
OUTLET = "sensor.irrigation_plus_distributor_gardena1_current_outlet"
WATERING = "binary_sensor.irrigation_plus_distributor_gardena1_watering_now"
MASTER = "input_boolean.test_pumpe"
SCRIPT = "script.sonoff_emu_run"
TARGET_ZONE = "6"  # Test5, outlet 5 (Test4 carries a soil-moisture veto)
START_OUTLET = 4  # declared physical start (the emulator has no ring)
FOREIGN_SECONDS = 40  # > 2 * skip_pulse_seconds (15) so the stash would be creditable
FLOW = 10.0

SNAP = (
    '{"now":"{{ now().isoformat() }}",'
    '"valve":"{{ states(\'%s\') }}","valve_lc":"{{ states.%s.last_changed.isoformat() }}",'
    '"outlet":"{{ states(\'%s\') }}","outlet_lc":"{{ states.%s.last_changed.isoformat() }}",'
    '"watering":"{{ states(\'%s\') }}","master":"{{ states(\'%s\') }}",'
    '"script":"{{ states(\'%s\') }}","probe":"{{ states(\'%s\') }}"}'
) % (VALVE, VALVE, OUTLET, OUTLET, WATERING, MASTER, SCRIPT, PROBE)


def _text(res):
    if "error" in res:
        raise SystemExit(f"MCP error: {res['error']}")
    return "".join(i.get("text", "") for i in (res.get("result") or {}).get("content", []))


def snap():
    payload = json.loads(_text(mcp_test.call("ha_eval_template", {"template": SNAP})))
    result = payload["result"]
    # HA's template engine already parses JSON-looking output into a dict.
    return result if isinstance(result, dict) else json.loads(result)


def service(domain, name, entity_id=None, data=None, wait=False):
    args = {"domain": domain, "service": name, "wait": wait}
    if entity_id:
        args["entity_id"] = entity_id
    if data:
        args["data"] = data
    out = json.loads(_text(mcp_test.call("ha_call_service", args)))
    if not out.get("success", False):
        raise SystemExit(f"service {domain}.{name} failed: {out}")


def ws(command, data):
    out = json.loads(_text(mcp_test.call("ha_call_service", {"ws_command": command, "data": data})))
    if not out.get("success", False):
        raise SystemExit(f"ws {command} failed: {out}")
    return out


def log(label, s=None):
    s = s or snap()
    print(
        f"{time.strftime('%H:%M:%S')} {label:<28} ha_now={s['now'][11:23]} valve={s['valve']}"
        f"(lc {s['valve_lc'][11:23]}) outlet={s['outlet']}(lc {s['outlet_lc'][11:23]}) "
        f"watering={s['watering']} master={s['master']} script={s['script']} probe={s['probe']}",
        flush=True,
    )
    return s


def target_due():
    for z in hasi_read.diag("data.store.zones"):
        if str(z.get("id")) == TARGET_ZONE:
            return z.get("duration"), z.get("bucket"), z.get("state")
    return None, None, None


def main():
    s = log("baseline")
    if s["valve"] != "off" or s["watering"] != "off":
        raise SystemExit("precondition failed: need valve off, not watering")
    service("irrigation_plus", "distributor_set_outlet", data={"distributor_id": 0, "outlet": START_OUTLET})
    for _ in range(5):
        s = log("after set_outlet")
        if s["outlet"] == str(START_OUTLET):
            break
        time.sleep(1)
    else:
        raise SystemExit("set_outlet did not take effect")
    d = [x for x in hasi_read.diag("data.store.distributors") if x.get("id") == 0][0]
    if d.get("active_cycle") or d.get("position_state") != "synced" or d.get("watch_mode") != "count":
        raise SystemExit(f"precondition failed: distributor {d.get('position_state')} {d.get('watch_mode')} {d.get('active_cycle')}")
    print("target zone before:", target_due(), flush=True)

    service("logger", "set_level", data={"custom_components.irrigation_plus": "info"})

    # --- foreign open ---------------------------------------------------------
    service("input_boolean", "turn_on", entity_id=VALVE, wait=True)
    t0 = time.monotonic()
    service("input_number", "set_value", entity_id=PROBE, data={"value": FLOW})
    log("foreign ON + probe")
    for _ in range(8):
        s = log("after foreign ON")
        if s["outlet"] != str(START_OUTLET):
            break
        time.sleep(1)

    while time.monotonic() - t0 < FOREIGN_SECONDS:
        time.sleep(8)
        service("input_number", "set_value", entity_id=PROBE, data={"value": FLOW})
        log("foreign open, probe kept live")

    dur, bucket, state = target_due()
    print("target zone at trigger:", (dur, bucket, state), flush=True)
    if not dur or dur <= 0 or bucket is None or bucket >= 0 or state == "disabled":
        print("ABORT: target not due; closing the foreign run", flush=True)
        service("input_boolean", "turn_off", entity_id=VALVE, wait=True)
        service("input_number", "set_value", entity_id=PROBE, data={"value": 0.0})
        log("aborted")
        return

    # --- trigger --------------------------------------------------------------
    ws("irrigation_plus/irrigate_now", {"zone_id": TARGET_ZONE})
    log("irrigate_now sent")

    valve_off_seen = None
    last_probe = time.monotonic()
    started = time.monotonic()
    while time.monotonic() - started < 120:
        time.sleep(1)
        s = log("cycle")
        if s["valve"] == "on" and time.monotonic() - last_probe > 4:
            service("input_number", "set_value", entity_id=PROBE, data={"value": FLOW})
            last_probe = time.monotonic()
        if s["valve"] == "off" and valve_off_seen is None:
            valve_off_seen = time.monotonic()
            service("input_number", "set_value", entity_id=PROBE, data={"value": 0.0})
            log("valve OFF -> probe 0")
        if (
            valve_off_seen is not None
            and s["watering"] == "off"
            and s["master"] == "off"
            and time.monotonic() - valve_off_seen > 10
        ):
            break
    log("end")
    d = [x for x in hasi_read.diag("data.store.distributors") if x.get("id") == 0][0]
    print(
        "distributor after:",
        json.dumps({k: d.get(k) for k in ("current_outlet", "position_state", "commissioning_confirmed", "active_cycle")}),
        flush=True,
    )


if __name__ == "__main__":
    main()
