#!/usr/bin/env python3
"""
Integration module for ecosystem-meta-coherence design in KIVA-CLI.
Wraps the standalone implementation for use in KIVA-CLI commands.
"""

import sys
from pathlib import Path

# Add PRD directory to path for imports
prd_dir = Path(__file__).parent.parent / "PRD"
sys.path.insert(0, str(prd_dir))

from ecosystem_meta_coherence import EcosystemMetaCoherence, verify_meta_coherence


class EcosystemMetaCoherenceIntegration:
    """Integration wrapper for ecosystem-meta-coherence."""

    def __init__(self):
        self.ecosystem_meta_coherence = EcosystemMetaCoherence()

    def validate(self, context: dict) -> dict:
        """Validate using ecosystem-meta-coherence."""
        return self.ecosystem_meta_coherence.verify(context)

    def check_and_execute(self, context: dict, action_func) -> dict:
        """Check ecosystem-meta-coherence then execute action if allowed."""
        validation = self.validate(context)
        if validation.get("state") == "ALLOW":
            result = action_func(context)
            return {"validation": validation, "execution": result}
        else:
            return {"validation": validation, "execution": None}


# Singleton
_ecosystem_meta_coherence_integration = None


def get_ecosystem_meta_coherence_integration() -> EcosystemMetaCoherenceIntegration:
    """Get or create singleton instance."""
    global _ecosystem_meta_coherence_integration
    if _ecosystem_meta_coherence_integration is None:
        _ecosystem_meta_coherence_integration = EcosystemMetaCoherenceIntegration()
    return _ecosystem_meta_coherence_integration
