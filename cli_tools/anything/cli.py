#!/usr/bin/env python3
"""
KIVA-CLI Anything-CLI — Point d'entrée unifié
IntentHash: 0xKIVA_ANYTHING_CLI_UNIFIED_20260615

Usage:
    python -m cli_tools.anything.cli --tool schedule-anything --args '{"name": "test"}'
    python -m cli_tools.anything.cli --list
"""
import json, sys, argparse
from typing import Dict, Any
from . import TOOL_MAP, __version__, __intent_hash__

def list_tools():
    return {"version": __version__, "intent_hash": __intent_hash__,
            "tools": {k: v.replace("_", " ") for k, v in TOOL_MAP.items()}}

def execute_tool(tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
    if tool_name not in TOOL_MAP:
        return {"tool": tool_name, "status": "error", "intent_hash": "0xUNKNOWN",
                "result": {"message": f"Unknown tool: {tool_name}", "available": list(TOOL_MAP.keys())},
                "timestamp": __import__("time").strftime("%Y-%m-%dT%H:%M:%S%z"), "phi_cps": 4.092}
    try:
        import importlib
        mod = importlib.import_module(f"cli_tools.anything.{TOOL_MAP[tool_name]}")
        return getattr(mod, TOOL_MAP[tool_name])(**args)
    except Exception as e:
        return {"tool": tool_name, "status": "error", "intent_hash": "0xERR",
                "result": {"message": str(e)}, "timestamp": __import__("time").strftime("%Y-%m-%dT%H:%M:%S%z"), "phi_cps": 4.092}

def main():
    p = argparse.ArgumentParser(prog="kiva-anything", description="KIVA-CLI Anything-CLI v1.0")
    p.add_argument("--tool", "-t", type=str, help="Tool to execute")
    p.add_argument("--args", "-a", type=str, default="{}", help="JSON arguments")
    p.add_argument("--json", "-j", action="store_true", help="Raw JSON output")
    p.add_argument("--list", "-l", action="store_true", help="List tools")
    args = p.parse_args()
    if args.list:
        print(json.dumps(list_tools(), indent=2 if not args.json else None)); return
    if not args.tool:
        p.print_help(); sys.exit(1)
    try:
        tool_args = json.loads(args.args)
    except json.JSONDecodeError as e:
        print(json.dumps({"status": "error", "message": f"Invalid JSON: {e}"})); sys.exit(1)
    result = execute_tool(args.tool, tool_args)
    print(json.dumps(result, indent=2 if not args.json else None, default=str))
    sys.exit(0 if result.get("status") == "success" else 1)

if __name__ == "__main__":
    main()
