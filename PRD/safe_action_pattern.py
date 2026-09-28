#!/usr/bin/env python3
"""
ACT-010: Implémentation centrale safe-action-pattern.
Tâche atomique SLM : un fichier, une action, résultat vérifiable.
"""

from pathlib import Path
from datetime import datetime, timezone


class SafeActionGate:
    """Gate de sécurité pour les actions mutantes."""

    def __init__(self, context: dict | None = None):
        self.context = context or {}
        self.validation_time = datetime.now(timezone.utc).isoformat()

    def validate(self, context: dict | None = None) -> dict:
        """Valide que l'action peut être exécutée."""
        if context:
            self.context = context

        # Validation minimale : présence d'un intent_hash
        intent_hash = self.context.get("intent_hash")
        if not intent_hash:
            return {
                "state": "DENY",
                "reason": "Missing intent_hash",
                "timestamp": self.validation_time,
            }

        # Validation : présence d'un consumer
        consumer = self.context.get("consumer")
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

    def verify(self, context: dict | None = None) -> dict:
        """Alias pour validate."""
        return self.validate(context)


def run_safe_action(context: dict) -> dict:
    """Point d'entrée principal."""
    gate = SafeActionGate()
    return gate.validate(context)


if __name__ == "__main__":
    test_context = {
        "intent_hash": "0xTEST_20260928",
        "consumer": "TEST",
    }
    result = run_safe_action(test_context)
    print(f"[ACT-010] safe-action-pattern validation: {result['state']}")
    if result["state"] == "DENY":
        print(f"  Reason: {result['reason']}")
