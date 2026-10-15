"""ha_config_set_yaml on HA-Test through tools/mcp_test.py (endpoint never printed).

Usage:
  python yaml_step.py preview add            -> preview of adding mqtt-e.yaml under `mqtt`
  python yaml_step.py apply add <token>      -> apply that preview
  python yaml_step.py preview remove / apply remove <token>
Prints only the tool's own answer; the best-practice key is read fresh and not printed.
"""
import json
import pathlib
import re
import sys

sys.path.insert(0, r"D:\Entwicklung\HASI\tools")
from mcp_test import call  # noqa: E402

HERE = pathlib.Path(__file__).parent


def text_of(res):
    return "\n".join(i.get("text", "") for i in (res.get("result") or {}).get("content", []))


def bp_key():
    guide = text_of(call("ha_get_skill_guide", {}))
    m = re.search(r"Acknowledgment key:\s*([A-Za-z0-9-]+)", guide)
    if not m:
        raise SystemExit("no BestPracticeKey found in the skill guide")
    return m.group(1)


mode, action = sys.argv[1], sys.argv[2]
args = {"yaml_path": "mqtt", "action": action, "BestPracticeKey": bp_key(), "MandatoryBPS": False}
if action == "add":
    args["content"] = (HERE / "mqtt-e.yaml").read_text(encoding="utf-8")
if mode == "apply":
    args["confirm_token"] = sys.argv[3]
res = call("ha_config_set_yaml", args)
out = text_of(res)
try:
    print(json.dumps(json.loads(out), ensure_ascii=False, indent=1))
except Exception:
    print(out)
if "error" in res:
    print("ERROR", res["error"])
