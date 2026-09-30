"""
KIVA-CLI causal_validator — Validateur de liens causaux et relations de cause à effet.

Contexte:
- KIVA-CLI est un composant de l'écosystème gerivdb.
- causal_validator permet la validation des liens causaux et des relations de cause à effet.

Intégration:
- GOVERNANCE-HUB: SOT, ADR, PRD-MOC, hooks
- KG-L / VERSES: connaissances et ontologie
- ARGUS: évaluateur de gaps et contradictions
- KIVA-CLI: orchestrateur git
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class CausalValidationResult:
    """Résultat de validation causale."""

    relation_id: str
    valid: bool
    confidence: float
    issues: list[str] = None

    def __post_init__(self) -> None:
        if self.issues is None:
            self.issues = []


class CausalValidator:
    """Validateur minimal de liens causaux."""

    def validate(self, relation_id: str, payload: dict[str, Any]) -> CausalValidationResult:
        """Valide un lien causal."""
        confidence = float(payload.get("confidence", 0.0))
        issues: list[str] = []
        if confidence < 0.5:
            issues.append("low_confidence")
        return CausalValidationResult(
            relation_id=relation_id,
            valid=confidence >= 0.5,
            confidence=confidence,
            issues=issues,
        )


def build_causal_validator() -> CausalValidator:
    """Factory pour créer une instance de CausalValidator."""
    return CausalValidator()
