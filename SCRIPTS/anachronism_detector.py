#!/usr/bin/env python3
"""
Ontology-aware Anachronism Detector - définit ce qu'est temporellement anachronique.
"""

from pathlib import Path
from datetime import datetime
from typing import Literal


# Types d'anachronisme définis sur 5 dimensions (triadiques)
AnachronismType = Literal["AN-A", "AN-B", "AN-C", "AN-D", "AN-E"]


class AnachronismDetector:
    """Détecteur ontologique des anomalies temporelles."""
    
    # SOT des concepts temporels valides
    TEMPORAL_CONCEPTS = {
        "consciousness": {"requires": ["memory", "dag3", "243_states"], "created": "2026-07-07"},
        "selina_sync": {"requires": ["known_repositories"], "created": "2026-07-07"},
        "managerizer": {"requires": ["fragility_scores", "243_space"], "created": "2026-07-07"},
        "responsabilizer": {"requires": ["profiles", "ternary_distance"], "created": "2026-07-07"}
    }
    
    def __init__(self, registry_path: Path):
        self.registry = registry_path
        self.timeline = []
    
    def detect(self, operation: str, prerequisites: list[str]) -> AnachronismType | None:
        """
        Détecte si une opération est anachronique.
        
        Args:
            operation: Nom de l'opération
            prerequisites: Concepts requis avant exécution
            
        Returns:
            Type d'anachronisme ou None si OK
        """
        # Check SOT registry
        if not self._concept_exists(operation):
            return "AN-B"  # Concept non défini
        
        # Check temporal ordering
        for prereq in prerequisites:
            if not self._prerequisite_met(prereq):
                return "AN-A"  # Prerequis non créé
            
        return None  # OK
    
    def _concept_exists(self, concept: str) -> bool:
        """Vérifie que le concept existe dans SOT."""
        return concept in self.TEMPORAL_CONCEPTS
    
    def _prerequisite_met(self, prereq: str) -> bool:
        """Vérifie que le prerequis a été créé avant."""
        prereq_date = self.TEMPORAL_CONCEPTS.get(prereq, {}).get("created")
        if not prereq_date:
            return False
        return datetime.fromisoformat(prereq_date) < datetime.utcnow()


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Anachronism Detector")
    parser.add_argument("--operation", required=True, help="Operation to check")
    parser.add_argument("--requires", nargs="*", help="Prerequisites")
    args = parser.parse_args()
    
    detector = AnachronismDetector(
        Path("D:/DO/WEB/TOOLS/L0-CANON/GOVERNANCE-HUB/known_repositories.yaml")
    )
    
    anachronism = detector.detect(args.operation, args.requires or [])
    
    if anachronism:
        print(f"ANACHRONISM DETECTED: {anachronism}")
        exit(1)
    print("TEMPORAL_OK")


if __name__ == "__main__":
    main()