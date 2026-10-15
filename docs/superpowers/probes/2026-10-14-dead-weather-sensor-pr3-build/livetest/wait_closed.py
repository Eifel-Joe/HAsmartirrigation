"""Poll HA-Test until both livetest groups' outages are closed; print one line then exit."""
import json
import pathlib
import sys
import time

sys.path.insert(0, r"D:\Entwicklung\HASI\tools")
from mcp_test import call  # noqa: E402

code = (pathlib.Path(__file__).parent / "s_state.py").read_text(encoding="utf-8")
deadline = time.time() + 900
while time.time() < deadline:
    try:
        res = call("ha_manage_custom_tool", {"code": code, "justification": "Read-only: poll the livetest groups' outage records on HA-Test"})
        text = "".join(i.get("text", "") for i in (res.get("result") or {}).get("content", []))
        d = json.loads(text)
        d = (d.get("data") or d).get("result")
        outs = [o for g in d["groups"] for o in g["outages"]]
        if outs and all(o.get("end") for o in outs):
            print("CLOSED", d["probe"][:32], json.dumps([[o["fields"][0], o["end"]] for o in outs]), flush=True)
            sys.exit(0)
    except Exception as exc:  # one failed poll must not end the watch
        print("POLL-ERROR", type(exc).__name__, str(exc)[:120], flush=True)
    time.sleep(30)
print("TIMEOUT still open", flush=True)
