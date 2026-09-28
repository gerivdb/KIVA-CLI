#!/usr/bin/env python3
"""
Integration module for design-ops-loop design in KIVA-CLI.
Wraps the standalone implementation for use in CLI commands.
"""

import sys
from pathlib import Path

# Add PRD directory to path for imports
prd_dir = Path(__file__).parent.parent / "PRD"
sys.path.insert(0, str(prd_dir))

from design_ops_loop import DesignOpsLoop, run_design_ops_loop


class DesignOpsLoopIntegration:
    """Integration wrapper for design-ops-loop."""

    def __init__(self):
        self.loop = DesignOpsLoop()

    def think(self, context: dict) -> dict:
        """Phase THINK : analyser le besoin."""
        return self.loop.think(context)

    def do(self, context: dict) -> dict:
        """Phase DO : exécuter la correction."""
        return self.loop.do(context)

    def check(self, context: dict) -> dict:
        """Phase CHECK : vérifier la cohérence."""
        return self.loop.check(context)

    def run(self, context: dict) -> dict:
        """Exécute la boucle complète THINK/DO/CHECK."""
        return self.loop.run(context)


# Singleton
_design_ops_loop = None


def get_design_ops_loop() -> DesignOpsLoopIntegration:
    """Get or create singleton instance."""
    global _design_ops_loop
    if _design_ops_loop is None:
        _design_ops_loop = DesignOpsLoopIntegration()
    return _design_ops_loop
