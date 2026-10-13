"""Run a sandbox snippet on HA-Test through tools/mcp_test.py (HA-Test only; endpoint never printed).

Usage: python run_code.py <snippet.py> "<justification>"
"""
import json
import pathlib
import sys

sys.path.insert(0, r"D:\Entwicklung\HASI\tools")
from mcp_test import call  # noqa: E402

code = pathlib.Path(sys.argv[1]).read_text(encoding="utf-8")
res = call("ha_manage_custom_tool", {"code": code, "justification": sys.argv[2]})
for item in (res.get("result") or {}).get("content", []):
    text = item.get("text", "")
    try:
        data = json.loads(text)
        print(json.dumps(data.get("data", data), ensure_ascii=False, indent=1))
    except Exception:
        print(text)
if "error" in res:
    print("ERROR", res["error"])
