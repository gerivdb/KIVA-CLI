#!/usr/bin/env python3
"""
BDCP Status Check - Vérifie l'état BDCP avant opérations git.

Usage:
    python scripts/bdcp-status-check.py
    python scripts/bdcp-status-check.py --gateway-url http://localhost:18000

Refs: INTENT-088, KiloRule ecos-cli-launcher.md BDCP section
"""
from __future__ import annotations

import argparse
import json
import urllib.error
import urllib.request
import sys


DEFAULT_GATEWAY = "http://localhost:18000"


def check_bdcp(gateway_url: str) -> dict:
    try:
        req = urllib.request.Request(
            f"{gateway_url}/clapet/status",
            headers={"Accept": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())
            return {"ok": True, "status": data.get("status"), "data": data}
    except urllib.error.URLError as e:
        return {"ok": False, "error": f"Cannot reach gateway: {e.reason}"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def main() -> int:
    parser = argparse.ArgumentParser(description="BDCP Status Check")
    parser.add_argument("--gateway-url", default=DEFAULT_GATEWAY, help="Gateway Manager URL")
    args = parser.parse_args()

    result = check_bdcp(args.gateway_url)

    if not result["ok"]:
        print(f"[ERR] {result['error']}")
        print("[ACTION] Check Gateway Manager or use explicit BDCP mode")
        return 1

    status = result.get("status", "unknown")
    if status in ("closed", "bdcp"):
        print(f"[OK] BDCP mode active (clapet={status})")
        return 0

    print(f"[WARN] BDCP mode NOT active (clapet={status})")
    print("[ACTION] Return to BDCP: POST /clapet/close")
    return 1


if __name__ == "__main__":
    exit(main())
