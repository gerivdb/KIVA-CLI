#!/usr/bin/env python3
"""
ACT-019: Implémentation centrale safe-action-gate.
"""

from pathlib import Path
from datetime import datetime, timezone


class SafeActionGate:
    """Gate de validation des actions mutantes."""

    def __init__(self, context: dict | None = None):
        self.context = context or {}
        self.validation_time = datetime.now(timezone.utc).isoformat()

    def verify(self, context: dict | None = None) -> dict:
        """Vérifie que l'action peut être exécutée."""
        if context:
            self.context = context

        intent_hash = self.context.get("intent_hash")
        consumer = self.context.get("consumer")

        if not intent_hash:
            return {
                "state": "DENY",
                "reason": "Missing intent_hash",
                "timestamp": self.validation_time,
            }

        if not consumer:
            return {
                "state": "DENY",
                "reason": "Missing consumer",
                "timestamp": self.validation_time,
            }

        return {
            "state": "ALLOW",
            "reason": "Safe-action gate passed",
            "intent_hash": intent_hash,
            "consumer": consumer,
            "timestamp": self.validation_time,
        }

    def validate(self, context: dict | None = None) -> dict:
        """Alias pour verify."""
        return self.verify(context)


def verify_safe_action_gate(context: dict) -> dict:
    """Point d'entrée principal."""
    gate = SafeActionGate()
    return gate.verify(context)


if __name__ == "__main__":
    test_context = {
        "intent_hash": "0xTEST_20260928",
        "consumer": "TEST",
    }
    result = verify_safe_action_gate(test_context)
    print(f"[ACT-019] safe-action-gate validation: {result['state']}")
