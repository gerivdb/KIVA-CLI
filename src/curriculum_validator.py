"""
KIVA-CLI curriculum_validator — Validateur de curriculums et parcours d'apprentissage.

Contexte:
- KIVA-CLI est un composant de l'écosystème gerivdb.
- curriculum_validator permet la validation des curriculums et des parcours d'apprentissage.

Intégration:
- GOVERNANCE-HUB: SOT, ADR, PRD-MOC, hooks
- KG-L / VERSES: connaissances et ontologie
- CURX: curriculum et validation
- KIVA-CLI: orchestrateur git
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class CurriculumValidationResult:
    """Résultat de validation d'un curriculum."""

    curriculum_id: str
    valid: bool
    issues: list[str] = None

    def __post_init__(self) -> None:
        if self.issues is None:
            self.issues = []


class CurriculumValidator:
    """Validateur minimal de curriculums."""

    def validate(self, curriculum_id: str, payload: dict[str, Any]) -> CurriculumValidationResult:
        """Valide un curriculum."""
        issues: list[str] = []
        if "title" not in payload:
            issues.append("missing_title")
        if "steps" not in payload:
            issues.append("missing_steps")
        return CurriculumValidationResult(
            curriculum_id=curriculum_id,
            valid=len(issues) == 0,
            issues=issues,
        )


def build_curriculum_validator() -> CurriculumValidator:
    """Factory pour créer une instance de CurriculumValidator."""
    return CurriculumValidator()
