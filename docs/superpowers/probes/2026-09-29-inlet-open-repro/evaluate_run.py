"""Read-only evaluation of an Eifel-Joe#66 reproduction run on HA-Test.

Usage: python evaluate_run.py <start ISO UTC, e.g. 2026-09-29T12:29:00Z> [zone ids...]
Prints every state change of the valve, the stored-position sensor, the distributor's
watering_now, the master and the flow probe since <start>, then the newest run-log
entries and totals of the given zones, the distributor's stored state, and the
integration's log lines since <start>.
"""
import json
import sys

sys.path.insert(0, r"D:\Entwicklung\HASI\pr146-work\live")
import mcp_test  # noqa: E402
import hasi_read  # noqa: E402

ENTITIES = [
    "input_boolean.sonoff_emu_valve",
    "sensor.irrigation_plus_distributor_gardena1_current_outlet",
    "binary_sensor.irrigation_plus_distributor_gardena1_watering_now",
    "input_boolean.test_pumpe",
    "input_number.hasi_flow_probe",
    "script.sonoff_emu_run",
]


def _payload(res):
    if "error" in res:
        raise SystemExit(f"MCP error: {res['error']}")
    text = "".join(i.get("text", "") for i in (res.get("result") or {}).get("content", []))
    return json.loads(text)


def history(start):
    rows = []
    for eid in ENTITIES:
        p = _payload(
            mcp_test.call(
                "ha_get_history",
                {"entity_ids": eid, "start_time": start, "order": "asc", "limit": 200,
                 "significant_changes_only": False},
            )
        )
        # Response shape: {"data": {"entities": [{"entity_id", "states": [...]}, ...]}}.
        ent = (p.get("data") or p).get("entities") or []
        states = next((e.get("states") for e in ent if e.get("entity_id") == eid), [])
        for s in states or []:
            ts = s.get("last_changed") or s.get("lu") or s.get("last_updated")
            rows.append((ts, eid.split(".", 1)[1][:40], s.get("state") or s.get("s")))
    for ts, eid, st in sorted(rows, key=lambda r: r[0] or ""):
        print(f"{ts}  {eid:<42} {st}")


def zones(ids, n=3):
    for z in hasi_read.diag("data.store.zones"):
        if str(z.get("id")) in ids:
            print(f"zone {z['id']} {z['name']}: bucket={z.get('bucket')} "
                  f"water_used_total={z.get('water_used_total')} duration={z.get('duration')}")
            log = sorted(z.get("run_log") or [], key=lambda e: e.get("ts") or "", reverse=True)
            for e in log[:n]:
                print("   ", json.dumps(e, ensure_ascii=False))


def distributor():
    d = [x for x in hasi_read.diag("data.store.distributors") if x.get("id") == 0][0]
    print("distributor:", json.dumps({k: d.get(k) for k in (
        "current_outlet", "position_state", "commissioning_confirmed", "watch_mode", "active_cycle")}))


def logs():
    p = _payload(mcp_test.call("ha_get_logs", {"source": "error_log", "search": "irrigation_plus",
                                               "limit": 60, "order": "oldest", "hours_back": 1}))
    text = p.get("log") or p.get("lines") or p.get("entries") or p
    if isinstance(text, list):
        for line in text:
            print("   ", line if isinstance(line, str) else json.dumps(line, ensure_ascii=False)[:400])
    else:
        print(str(text)[:6000])


if __name__ == "__main__":
    start = sys.argv[1]
    ids = sys.argv[2:] or ["5", "6"]
    print("=== state changes since", start)
    history(start)
    print("=== zones")
    zones(ids)
    print("=== store")
    distributor()
    print("=== integration log lines (last hour)")
    logs()
