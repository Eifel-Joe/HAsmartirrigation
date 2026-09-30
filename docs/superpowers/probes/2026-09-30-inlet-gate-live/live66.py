"""Live test of the distributor inlet gate on HA-Test ONLY (pr146-work's MCP client).

Never prints the MCP endpoint or the config entry's options (they carry an API key).
Every line carries HA's own clock (ha=HH:MM:SS.mmm) next to the local wall clock.

Usage (python live66.py <cmd> [args]):
  snap                      one snapshot line
  notifs                    the integration's persistent notifications
  runlog ZONE [N]           newest N run-log entries of a zone
  dist                      Gardena1's stored state
  set_outlet N              distributor_set_outlet(0, N), waits until the sensor shows N
  logger LEVEL              logger.set_level for custom_components.irrigation_plus
  open ENTITY               turn the valve on (+ flow probe 10 L/min)
  close ENTITY              turn the valve off (+ flow probe 0)
  hold ENTITY SECONDS       keep the flow probe reporting 10 while ENTITY is on
  irrigate ZONE [SECONDS]   irrigation_plus/irrigate_now, then one snapshot a second
  l1                        L1 sequence (count): declare 4, foreign open, irrigate zone 6, close
  l4                        L4 sequence: declare 5, irrigate zone 6, feed the probe through the leg
  l5a                       L5a sequence (grace wiring must be in place)
  l5b                       L5b sequence (grace wiring must be in place)
"""
import json
import sys
import time


class _Tee:
    """Print to the console and append to live/session.log (the protocol's raw record)."""

    def __init__(self, stream, path):
        self.stream, self.file = stream, open(path, "a", encoding="utf-8")

    def write(self, text):
        self.stream.write(text)
        self.file.write(text)

    def flush(self):
        self.stream.flush()
        self.file.flush()


sys.stdout.reconfigure(encoding="utf-8")
sys.stdout = _Tee(sys.stdout, r"D:\Entwicklung\HASI\issue66-work\live\session.log")
print(f"##### {time.strftime('%Y-%m-%d %H:%M:%S')} live66.py {' '.join(sys.argv[1:])}", flush=True)

sys.path.insert(0, r"D:\Entwicklung\HASI\pr146-work\live")
sys.path.insert(0, r"D:\Entwicklung\HASI\issue66-work")
import mcp_test  # noqa: E402
import hasi_read  # noqa: E402

SONOFF = "input_boolean.sonoff_emu_valve"
GRACE = "input_boolean.grace_emu_valve"
PROBE = "input_number.hasi_flow_probe"
OUTLET = "sensor.irrigation_plus_distributor_gardena1_current_outlet"
WATERING = "binary_sensor.irrigation_plus_distributor_gardena1_watering_now"
MASTER = "input_boolean.test_pumpe"
RUN = "script.sonoff_emu_run"
GRUN = "script.grace_emu_run"
NOOP = "script.grace_emu_noop"
FLOW = 10.0

_SNAP = (
    '{"now":"{{ now().isoformat() }}",'
    '"sonoff":"{{ states(\'SONOFF\') }}","sonoff_lc":"{{ states.SONOFF.last_changed.isoformat() }}",'
    '"grace":"{{ states(\'GRACE\') }}","grace_lc":"{{ states.GRACE.last_changed.isoformat() }}",'
    '"outlet":"{{ states(\'OUTLET\') }}","outlet_lc":"{{ states.OUTLET.last_changed.isoformat() }}",'
    '"watering":"{{ states(\'WATERING\') }}","watering_lc":"{{ states.WATERING.last_changed.isoformat() }}",'
    '"master":"{{ states(\'MASTER\') }}",'
    '"run":"{{ states(\'RUN\') }}","run_lt":"{{ state_attr(\'RUN\', \'last_triggered\') }}",'
    '"grun":"{{ states(\'GRUN\') }}","grun_lt":"{{ state_attr(\'GRUN\', \'last_triggered\') }}",'
    '"noop_lt":"{{ state_attr(\'NOOP\', \'last_triggered\') }}",'
    '"probe":"{{ states(\'PROBE\') }}"}'
)
for _k, _v in (("SONOFF", SONOFF), ("GRACE", GRACE), ("OUTLET", OUTLET), ("WATERING", WATERING),
               ("MASTER", MASTER), ("GRUN", GRUN), ("RUN", RUN), ("NOOP", NOOP), ("PROBE", PROBE)):
    _SNAP = _SNAP.replace(_k, _v)


def _text(res):
    if "error" in res:
        raise SystemExit(f"MCP error: {res['error']}")
    return "".join(i.get("text", "") for i in (res.get("result") or {}).get("content", []))


def snap():
    payload = json.loads(_text(mcp_test.call("ha_eval_template", {"template": _SNAP})))
    result = payload["result"]
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


def _t(iso):
    """HH:MM:SS.mmm in local time (HA renders last_changed/last_triggered in UTC, now() local)."""
    if not iso or iso == "None" or len(iso) < 19:
        return iso
    from datetime import datetime
    from zoneinfo import ZoneInfo

    return datetime.fromisoformat(iso).astimezone(ZoneInfo("Europe/Berlin")).strftime("%H:%M:%S.%f")[:12]


def log(label, s=None):
    s = s or snap()
    print(
        f"{time.strftime('%H:%M:%S')} {label:<30} ha={_t(s['now'])} sonoff={s['sonoff']}(lc {_t(s['sonoff_lc'])}) "
        f"grace={s['grace']}(lc {_t(s['grace_lc'])}) outlet={s['outlet']}(lc {_t(s['outlet_lc'])}) "
        f"watering={s['watering']}(lc {_t(s['watering_lc'])}) master={s['master']} "
        f"run={s['run']}(lt {_t(s['run_lt'])}) grun={s['grun']}(lt {_t(s['grun_lt'])}) "
        f"noop_lt={_t(s['noop_lt'])} probe={s['probe']}",
        flush=True,
    )
    return s


def notifs():
    out = ws("persistent_notification/get", {})
    items = out.get("result") or out.get("data") or []
    if isinstance(items, dict):
        items = items.get("result") or items.get("notifications") or []
    found = [n for n in items if str(n.get("notification_id", "")).startswith("irrigation_plus")]
    for n in found:
        print(json.dumps({k: n.get(k) for k in ("notification_id", "created_at", "title", "message")},
                         ensure_ascii=False), flush=True)
    if not found:
        print("(no irrigation_plus notification)", flush=True)
    return found


def dist():
    d = [x for x in hasi_read.diag("data.store.distributors") if x.get("id") == 0][0]
    keep = ("current_outlet", "position_state", "commissioning_confirmed", "watch_mode", "active_cycle",
            "inlet_entity", "run_service", "stop_service", "duration_field", "watering_mode")
    print("distributor:", json.dumps({k: d.get(k) for k in keep}), flush=True)
    return d


def set_outlet(n):
    service("irrigation_plus", "distributor_set_outlet", data={"distributor_id": 0, "outlet": int(n)})
    for _ in range(8):
        s = log(f"after set_outlet {n}")
        if s["outlet"] == str(n):
            return s
        time.sleep(1)
    raise SystemExit("set_outlet did not take effect")


def probe(value):
    service("input_number", "set_value", entity_id=PROBE, data={"value": float(value)})


def open_valve(entity):
    service("input_boolean", "turn_on", entity_id=entity, wait=True)
    probe(FLOW)
    return log(f"{entity.split('.')[1]} ON + probe")


def close_valve(entity):
    service("input_boolean", "turn_off", entity_id=entity, wait=True)
    probe(0.0)
    return log(f"{entity.split('.')[1]} OFF + probe 0")


def hold(entity, seconds):
    end = time.monotonic() + float(seconds)
    while time.monotonic() < end:
        s = snap()
        key = "sonoff" if entity == SONOFF else "grace"
        if s[key] == "on":
            probe(FLOW)
        log(f"hold {entity.split('.')[1]}", s)
        time.sleep(max(0.0, min(8.0, end - time.monotonic())))


def irrigate(zone, seconds=12):
    ws("irrigation_plus/irrigate_now", {"zone_id": str(zone)})
    first = log(f"irrigate_now zone {zone} sent")
    for _ in range(int(seconds)):
        time.sleep(1)
        log(f"after irrigate zone {zone}")
    return first


def l1():
    s = log("L1 baseline")
    if s["sonoff"] != "off" or s["watering"] != "off":
        raise SystemExit("precondition failed: valve off, not watering")
    d = dist()
    if d.get("watch_mode") != "count" or d.get("position_state") != "synced" or d.get("active_cycle"):
        raise SystemExit("precondition failed: count, synced, no active cycle")
    set_outlet(4)
    open_valve(SONOFF)
    t0 = time.monotonic()
    for _ in range(4):
        s = log("after foreign ON")
        if s["outlet"] != "4":
            break
        time.sleep(1)
    time.sleep(3)
    irrigate(6, seconds=12)
    while time.monotonic() - t0 < 42:
        time.sleep(min(8, max(0.5, 42 - (time.monotonic() - t0))))
        probe(FLOW)
        log("foreign open, probe live")
    close_valve(SONOFF)
    for _ in range(4):
        time.sleep(1)
        log("after foreign OFF")
    dist()
    notifs()


def wait_up(max_s=300):
    """Poll until HA-Test answers again and the integration's outlet sensor has a number."""
    t0 = time.monotonic()
    while time.monotonic() - t0 < max_s:
        try:
            s = snap()
            if s["outlet"].isdigit():
                return log("HA-Test back", s)
        except (SystemExit, Exception) as err:  # MCP errors while HA restarts
            print(f"{time.strftime('%H:%M:%S')} waiting for HA-Test ({type(err).__name__})", flush=True)
        time.sleep(5)
    raise SystemExit("HA-Test did not come back")


def l3post(member_zone):
    """After an HA-Test restart with the grace inlet left open: irrigate zone 6 (expected: refused),
    close the inlet, and show what the close did to the position and to the member at the
    outlet that flowed (`member_zone`)."""
    s = wait_up()
    dist()
    if s["grace"] != "on":
        raise SystemExit("the grace inlet did not stay on across the restart")
    notifs()
    irrigate(6, seconds=8)
    hold(GRACE, 4)
    close_valve(GRACE)
    for _ in range(3):
        time.sleep(1)
        log("after close")
    dist()
    notifs()
    for z in ("6", str(member_zone)):
        print(f"--- zone {z} newest", flush=True)
        hasi_read.runlog(z, 2)


def l3b_open(start):
    """Declare `start`, then open the grace inlet in count mode (the edge is seen)."""
    set_outlet(start)
    open_valve(GRACE)
    for _ in range(4):
        time.sleep(1)
        log("after seen ON")
    dist()


def _feed_cycle(valve_key, until, label, max_s=200):
    """Poll once a second, keep the probe reporting while the valve is on, return on until(s)."""
    started = time.monotonic()
    last_feed = 0.0
    fed_off = True
    while time.monotonic() - started < max_s:
        s = snap()
        if s[valve_key] == "on" and time.monotonic() - last_feed > 4:
            probe(FLOW)
            last_feed = time.monotonic()
            fed_off = False
        elif s[valve_key] == "off" and not fed_off:
            probe(0.0)
            fed_off = True
        log(label, s)
        if until(s):
            return s
        time.sleep(1)
    raise SystemExit(f"{label}: timed out")


def l4():
    s = log("L4 baseline")
    if s["sonoff"] != "off" or s["watering"] != "off":
        raise SystemExit("precondition failed")
    set_outlet(5)
    irrigate(6, seconds=2)
    state = {"seen_on": False, "off_at": None}

    def done(s):
        if s["sonoff"] == "on":
            state["seen_on"] = True
        if state["seen_on"] and s["sonoff"] == "off" and state["off_at"] is None:
            state["off_at"] = time.monotonic()
        return (state["off_at"] is not None and s["watering"] == "off" and s["master"] == "off"
                and time.monotonic() - state["off_at"] > 5)

    _feed_cycle("sonoff", done, "L4 cycle")
    probe(0.0)
    dist()


def _wait_stamp(before, label):
    """Wait for the no-op stop_service to be triggered (the integration's own close)."""
    def seen(s):
        return s["noop_lt"] not in (before, "None", None)
    return _feed_cycle("grace", seen, label)


def _ha_seconds(iso):
    from datetime import datetime
    return datetime.fromisoformat(iso).timestamp()


def _fire_after_stamp(s, offset, zone):
    """Send irrigate_now `offset` seconds after the stamp, by HA's clock."""
    elapsed = _ha_seconds(s["now"]) - _ha_seconds(s["noop_lt"])
    wait = offset - elapsed
    print(f"   stamp at ha={_t(s['noop_lt'])}; seen {elapsed:.2f} s after it; sending zone {zone} in {wait:.2f} s",
          flush=True)
    end = time.monotonic() + wait
    while time.monotonic() < end - 4.5:
        probe(FLOW)
        log("waiting in the grace window")
        time.sleep(min(4.0, max(0.0, end - 4.5 - time.monotonic())))
    time.sleep(max(0.0, end - time.monotonic()))
    ws("irrigation_plus/irrigate_now", {"zone_id": str(zone)})
    after = log(f"irrigate_now zone {zone} sent")
    print(f"   sent at ha={_t(after['now'])}, {_ha_seconds(after['now']) - _ha_seconds(s['noop_lt']):.2f} s "
          f"after the stamp (upper bound; the claim ran before this snapshot)", flush=True)
    return after


def l5a():
    s = log("L5a baseline")
    if s["grace"] != "off" or s["watering"] != "off":
        raise SystemExit("precondition failed: grace valve off, not watering")
    set_outlet(2)
    before = s["noop_lt"]
    irrigate(3, seconds=1)
    s = _wait_stamp(before, "L5a cycle 1")
    grun_first = s["grun_lt"]
    after = _fire_after_stamp(s, 10.0, 4)
    for _ in range(12):
        time.sleep(1)
        s = log("after 2nd irrigate (L5a)")
    print(f"   run script re-triggered: {s['grun_lt'] != grun_first} ({_t(grun_first)} -> {_t(s['grun_lt'])})",
          flush=True)
    stamp2_before = s["noop_lt"]
    _wait_stamp(stamp2_before, "L5a cycle 2")
    _feed_cycle("grace", lambda x: x["grace"] == "off" and x["watering"] == "off", "L5a tail")
    probe(0.0)
    dist()
    notifs()


def l5b():
    s = log("L5b baseline")
    if s["grace"] != "off" or s["watering"] != "off":
        raise SystemExit("precondition failed: grace valve off, not watering")
    set_outlet(6)
    before = s["noop_lt"]
    irrigate(7, seconds=1)
    s = _wait_stamp(before, "L5b cycle 1")
    grun_first = s["grun_lt"]
    _feed_cycle("grace", lambda x: x["watering"] == "off" and x["master"] == "off", "L5b cycle 1 end")
    after = _fire_after_stamp(s, 35.0, 2)
    if after["grace"] != "on":
        print("   WARNING: grace valve no longer on at the second irrigate_now", flush=True)
    for _ in range(10):
        time.sleep(1)
        x = log("after 2nd irrigate (L5b)")
    print(f"   run script re-triggered: {x['grun_lt'] != grun_first}", flush=True)
    _feed_cycle("grace", lambda x: x["grace"] == "off", "L5b tail")
    probe(0.0)
    dist()
    notifs()


if __name__ == "__main__":
    cmd, args = sys.argv[1], sys.argv[2:]
    if cmd == "snap":
        log("snap")
    elif cmd == "notifs":
        notifs()
    elif cmd == "runlog":
        hasi_read.runlog(*args)
    elif cmd == "dist":
        dist()
    elif cmd == "set_outlet":
        set_outlet(args[0])
    elif cmd == "logger":
        service("logger", "set_level", data={"custom_components.irrigation_plus": args[0]})
        print("logger set", args[0])
    elif cmd == "open":
        open_valve(args[0])
    elif cmd == "close":
        close_valve(args[0])
    elif cmd == "hold":
        hold(args[0], args[1])
    elif cmd == "irrigate":
        irrigate(args[0], *(int(a) for a in args[1:]))
    elif cmd in ("l1", "l4", "l5a", "l5b"):
        globals()[cmd]()
    elif cmd == "noop_create":
        out = json.loads(_text(mcp_test.call("ha_config_set_script", {
            "script_id": "grace_emu_noop",
            "BestPracticeKey": args[0],
            "MandatoryBPS": False,
            "config": {"alias": "Grace Emu Noop (inlet gate live test, delete afterwards)",
                       "sequence": [{"delay": {"seconds": 0}}], "mode": "parallel"},
        })))
        print(json.dumps(out, ensure_ascii=False)[:600])
    elif cmd == "noop_delete":
        out = json.loads(_text(mcp_test.call("ha_config_remove_script", {"script_id": "grace_emu_noop"})))
        print(json.dumps(out, ensure_ascii=False)[:600])
    elif cmd == "dismiss":
        service("persistent_notification", "dismiss", data={"notification_id": args[0]})
        notifs()
    elif cmd == "off_delay":
        service("input_number", "set_value", entity_id="input_number.grace_emu_off_delay",
                data={"value": float(args[0])})
        payload = json.loads(_text(mcp_test.call("ha_eval_template", {
            "template": "{{ states('input_number.grace_emu_off_delay') }}"})))
        print("grace_emu_off_delay =", payload["result"])
    elif cmd == "l3post":
        l3post(args[0])
    elif cmd == "l3b_open":
        l3b_open(args[0])
    else:
        raise SystemExit(__doc__)
