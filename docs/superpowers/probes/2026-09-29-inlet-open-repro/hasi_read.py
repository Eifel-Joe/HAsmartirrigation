"""Read-only probes of HA-Test for the Eifel-Joe#66 reproduction.

Uses the minimal MCP client from pr146-work (endpoint read from its secrets file,
never printed). Prints only selected fields -- never the config entry's options,
which carry an API key.

Usage:
  python hasi_read.py zones            # members + key fields of every zone
  python hasi_read.py dist             # distributors (position, mode, cycle)
  python hasi_read.py runlog <zone_id> [n]   # last n run-log entries of a zone
"""
import json
import sys

sys.path.insert(0, r"D:\Entwicklung\HASI\pr146-work\live")
import mcp_test  # noqa: E402

ENTRY = "01M20AD0AWZJ15ZXSF1ECVJZN3"


def diag(path):
    res = mcp_test.call(
        "ha_get_integration",
        {"entry_id": ENTRY, "include_diagnostics": True, "diagnostics_data_path": path},
    )
    if "error" in res:
        raise SystemExit(f"MCP error: {res['error']}")
    text = "".join(
        item.get("text", "") for item in (res.get("result") or {}).get("content", [])
    )
    payload = json.loads(text)
    return payload["diagnostics"]["data"]


def zones():
    keep = (
        "id", "name", "state", "duration", "bucket", "maximum_bucket",
        "water_used_total", "linked_entity", "observed_entity", "run_service",
        "watering_mode",
    )
    for z in diag("data.store.zones"):
        row = {k: z.get(k) for k in keep if k in z}
        row.update({k: v for k, v in z.items() if "distributor" in k or "outlet" in k or "soil" in k})
        row["run_log_len"] = len(z.get("run_log") or [])
        print(json.dumps(row, ensure_ascii=False))


def dist():
    for d in diag("data.store.distributors"):
        print(json.dumps(d, ensure_ascii=False))


def runlog(zone_id, n=5):
    for z in diag("data.store.zones"):
        if int(z.get("id")) == int(zone_id):
            log = z.get("run_log") or []
            # Order is not assumed: print the n entries with the newest timestamps.
            for e in sorted(log, key=lambda e: e.get("ts") or "", reverse=True)[: int(n)]:
                print(json.dumps(e, ensure_ascii=False))
            return
    print(f"zone {zone_id} not found")


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "zones":
        zones()
    elif cmd == "dist":
        dist()
    elif cmd == "runlog":
        runlog(*sys.argv[2:])
    else:
        raise SystemExit(__doc__)
