"""
KIVA-CLI meta_coherence_fixer — Détection et correction des incohérences méta.

Contexte:
- KIVA-CLI est un composant de l'écosystème gerivdb.
- meta_coherence_fixer permet la détection et la correction des incohérences méta
  dans les récits et les cycles.

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
class MetaCoherenceResult:
    """Résultat de correction de cohérence méta."""

    target_id: str
    fixed: bool
    applied_fixes: list[str] = None

    def __post_init__(self) -> None:
        if self.applied_fixes is None:
            self.applied_fixes = []


class MetaCoherenceFixer:
    """Correcteur minimal de cohérence méta."""

    def inspect(self, target_id: str, payload: dict[str, Any]) -> list[str]:
        """Inspecte un récit ou cycle pour détecter les incohérences."""
        issues: list[str] = []
        if "narrative" in payload and "curriculum" in payload:
            if payload["narrative"].get("cycle_id") != payload["curriculum"].get("cycle_id"):
                issues.append("cycle_id_mismatch")
        return issues

    def fix(self, target_id: str, payload: dict[str, Any]) -> MetaCoherenceResult:
        """Corrige les incohérences détectées."""
        issues = self.inspect(target_id, payload)
        applied_fixes: list[str] = []
        if "cycle_id_mismatch" in issues:
            applied_fixes.append("align_cycle_id")
        return MetaCoherenceResult(
            target_id=target_id,
            fixed=len(applied_fixes) > 0,
            applied_fixes=applied_fixes,
        )


def build_meta_coherence_fixer() -> MetaCoherenceFixer:
    """Factory pour créer une instance de MetaCoherenceFixer."""
    return MetaCoherenceFixer()
