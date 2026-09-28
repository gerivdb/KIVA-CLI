#!/usr/bin/env python3
"""
Integration module for safe-action-gate design in KIVA-CLI.
Wraps the standalone implementation for use in CLI commands.
"""

import sys
from pathlib import Path

# Add PRD directory to path for imports
prd_dir = Path(__file__).parent.parent / "PRD"
sys.path.insert(0, str(prd_dir))

from safe_action_gate import SafeActionGate, verify_safe_action_gate


class SafeActionGateIntegration:
    """Integration wrapper for safe-action-gate."""

    def __init__(self):
        self.gate = SafeActionGate()

    def verify_before_command(self, command: str, context: dict) -> dict:
        """Verify safe-action-gate before executing a command."""
        full_context = {
            "command": command,
            **context,
        }
        return self.gate.verify(full_context)

    def check_and_execute(self, command: str, context: dict, action_func) -> dict:
        """Check safe-action-gate then execute action if allowed."""
        validation = self.verify_before_command(command, context)
        if validation["state"] == "ALLOW":
            result = action_func(context)
            return {"validation": validation, "execution": result}
        else:
            return {"validation": validation, "execution": None}


# Singleton
_safe_action_gate = None


def get_safe_action_gate() -> SafeActionGateIntegration:
    """Get or create singleton instance."""
    global _safe_action_gate
    if _safe_action_gate is None:
        _safe_action_gate = SafeActionGateIntegration()
    return _safe_action_gate
