#!/usr/bin/env python3
"""
Integration module for ecosystem-meta-coherence-gate design in KIVA-CLI.
Wraps the standalone implementation for use in KIVA-CLI commands.
"""

import sys
from pathlib import Path

# Add PRD directory to path for imports
prd_dir = Path(__file__).parent.parent / "PRD"
sys.path.insert(0, str(prd_dir))

from ecosystem_meta_coherence_gate import EcosystemMetaCoherenceGate, verify_meta_coherence_gate


class EcosystemMetaCoherenceGateIntegration:
    """Integration wrapper for ecosystem-meta-coherence-gate."""

    def __init__(self):
        self.ecosystem_meta_coherence_gate = EcosystemMetaCoherenceGate()

    def validate(self, context: dict) -> dict:
        """Validate using ecosystem-meta-coherence-gate."""
        return self.ecosystem_meta_coherence_gate.verify(context)

    def check_and_execute(self, context: dict, action_func) -> dict:
        """Check ecosystem-meta-coherence-gate then execute action if allowed."""
        validation = self.validate(context)
        if validation.get("state") == "ALLOW":
            result = action_func(context)
            return {"validation": validation, "execution": result}
        else:
            return {"validation": validation, "execution": None}


# Singleton
_ecosystem_meta_coherence_gate_integration = None


def get_ecosystem_meta_coherence_gate_integration() -> EcosystemMetaCoherenceGateIntegration:
    """Get or create singleton instance."""
    global _ecosystem_meta_coherence_gate_integration
    if _ecosystem_meta_coherence_gate_integration is None:
        _ecosystem_meta_coherence_gate_integration = EcosystemMetaCoherenceGateIntegration()
    return _ecosystem_meta_coherence_gate_integration
