#!/usr/bin/env python3
"""
Integration module for meta-design-self-healing design in KIVA-CLI.
Wraps the standalone implementation for use in KIVA-CLI commands.
"""

import sys
from pathlib import Path

# Add PRD directory to path for imports
prd_dir = Path(__file__).parent.parent / "PRD"
sys.path.insert(0, str(prd_dir))

from meta_design_self_healing import MetaDesignSelfHealing, scan_self_healing


class MetaDesignSelfHealingIntegration:
    """Integration wrapper for meta-design-self-healing."""

    def __init__(self):
        self.meta_design_self_healing = MetaDesignSelfHealing()

    def validate(self, context: dict) -> dict:
        """Validate using meta-design-self-healing."""
        return self.meta_design_self_healing.scan(context)

    def check_and_execute(self, context: dict, action_func) -> dict:
        """Check meta-design-self-healing then execute action if allowed."""
        validation = self.validate(context)
        if validation.get("status") == "OK":
            result = action_func(context)
            return {"validation": validation, "execution": result}
        else:
            return {"validation": validation, "execution": None}


# Singleton
_meta_design_self_healing_integration = None


def get_meta_design_self_healing_integration() -> MetaDesignSelfHealingIntegration:
    """Get or create singleton instance."""
    global _meta_design_self_healing_integration
    if _meta_design_self_healing_integration is None:
        _meta_design_self_healing_integration = MetaDesignSelfHealingIntegration()
    return _meta_design_self_healing_integration
