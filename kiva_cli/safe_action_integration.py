#!/usr/bin/env python3
"""
Integration module for safe-action-pattern design in KIVA-CLI.
Wraps the standalone implementation for use in CLI commands.
"""

import sys
from pathlib import Path

# Add PRD directory to path for imports
prd_dir = Path(__file__).parent.parent / "PRD"
sys.path.insert(0, str(prd_dir))

from safe_action_pattern import SafeActionGate, run_safe_action


class SafeActionIntegration:
    """Integration wrapper for safe-action-pattern."""

    def __init__(self):
        self.gate = SafeActionGate()

    def validate_action(self, action_context: dict) -> dict:
        """Validate a KIVA-CLI action before execution."""
        return self.gate.validate(action_context)

    def check_and_execute(self, action_context: dict, action_func) -> dict:
        """Check safe-action gate then execute action if allowed."""
        validation = self.validate_action(action_context)
        if validation["state"] == "ALLOW":
            result = action_func(action_context)
            return {"validation": validation, "execution": result}
        else:
            return {"validation": validation, "execution": None}


# Singleton
_safe_action = None

def get_safe_action() -> SafeActionIntegration:
    """Get or create singleton instance."""
    global _safe_action
    if _safe_action is None:
        _safe_action = SafeActionIntegration()
    return _safe_action
