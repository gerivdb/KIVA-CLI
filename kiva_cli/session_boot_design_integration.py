#!/usr/bin/env python3
"""
Integration module for session-boot-design design in KIVA-CLI.
Wraps the standalone implementation for use in KIVA-CLI commands.
"""

import sys
from pathlib import Path

# Add PRD directory to path for imports
prd_dir = Path(__file__).parent.parent / "PRD"
sys.path.insert(0, str(prd_dir))

from session_boot_design import SessionBoot, run_session_boot


class SessionBootDesignIntegration:
    """Integration wrapper for session-boot-design."""

    def __init__(self):
        self.session_boot_design = SessionBoot()

    def validate(self, context: dict) -> dict:
        """Validate using session-boot-design."""
        return self.session_boot_design.run_boot_checks(context)

    def check_and_execute(self, context: dict, action_func) -> dict:
        """Check session-boot-design then execute action if allowed."""
        validation = self.validate(context)
        if validation.get("all_ok"):
            result = action_func(context)
            return {"validation": validation, "execution": result}
        else:
            return {"validation": validation, "execution": None}


# Singleton
_session_boot_design_integration = None


def get_session_boot_design_integration() -> SessionBootDesignIntegration:
    """Get or create singleton instance."""
    global _session_boot_design_integration
    if _session_boot_design_integration is None:
        _session_boot_design_integration = SessionBootDesignIntegration()
    return _session_boot_design_integration
