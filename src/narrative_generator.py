"""
KIVA-CLI narrative_generator — Générateur de récits narratifs pour les cycles et expériences.

Contexte:
- KIVA-CLI est un composant de l'écosystème gerivdb.
- narrative_generator permet la génération de récits narratifs pour les cycles et les expériences.

Intégration:
- GOVERNANCE-HUB: SOT, ADR, PRD-MOC, hooks
- KG-L / VERSES: connaissances et ontologie
- TALEX: moteur narratif
- KIVA-CLI: orchestrateur git
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Narrative:
    """Récit narratif généré."""

    cycle_id: str
    title: str
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)


class NarrativeGenerator:
    """Générateur minimal de récits narratifs."""

    def generate(self, cycle_id: str, context: dict[str, Any]) -> Narrative:
        """Génère un récit narratif pour un cycle."""
        return Narrative(
            cycle_id=cycle_id,
            title=context.get("title", f"Cycle {cycle_id}"),
            content=context.get("content", ""),
            metadata=context.get("metadata", {}),
        )


def build_narrative_generator() -> NarrativeGenerator:
    """Factory pour créer une instance de NarrativeGenerator."""
    return NarrativeGenerator()
