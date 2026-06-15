#!/usr/bin/env python3
"""
KIVA-CLI Anything-CLI Suite v1.0
IntentHash: 0xKIVA_ANYTHING_CLI_SUITE_20260615

Lazy-loading package: tools are imported only when called.
"""

__version__ = "1.0.0"
__intent_hash__ = "0xKIVA_ANYTHING_CLI_SUITE_20260615"

TOOL_MAP = {
    "schedule-anything": "schedule_anything",
    "run-anything": "run_anything",
    "wal-anything": "wal_anything",
    "citizen-anything": "citizen_anything",
    "skill-anything": "skill_anything",
    "deploy-anything": "deploy_anything",
    "phi-anything": "phi_anything",
    "rollback-anything": "rollback_anything",
}

__all__ = list(TOOL_MAP.keys()) + ["TOOL_MAP"]
