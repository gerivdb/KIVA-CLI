"""
PhiCPSCalculator: Calculateur de φ-CPS (Phi Cognitive Performance Score)
Mesure la performance cognitive et maturité des composants écosystème
"""

from typing import Dict, Any, Optional
from enum import Enum
import math


class PhiCPSLevel(Enum):
    """Niveaux φ-CPS selon maturité cognitive"""

    GENESIS = 4.092  # Niveau initial
    EMERGENT = 4.398  # Niveau émergent
    CONSCIOUS = 4.701  # Niveau conscient
    AUTONOMOUS = 5.000  # Niveau autonome


class PhiCPSCalculator:
    """Calculateur φ-CPS pour évaluation cognitive des composants"""

    # Constantes φ-CPS
    PHI_GENESIS = 4.092
    PHI_EMERGENT = 4.398
    PHI_CONSCIOUS = 4.701
    PHI_AUTONOMOUS = 5.000

    # Poids des métriques
    WEIGHTS = {
        "complexity": 0.25,  # Complexité algorithmique
        "autonomy": 0.20,  # Niveau d'autonomie
        "adaptability": 0.20,  # Capacité d'adaptation
        "reliability": 0.15,  # Fiabilité opérationnelle
        "efficiency": 0.10,  # Efficacité énergétique
        "evolution": 0.10,  # Capacité d'évolution
    }

    def __init__(self):
        self.baseline_phi = self.PHI_GENESIS

    def calculate_phi_cps(self, metrics: Dict[str, Any]) -> float:
        """
        Calcule le score φ-CPS d'un composant

        Args:
            metrics: Dictionnaire des métriques du composant

        Returns:
            float: Score φ-CPS calculé
        """
        phi_score = self.baseline_phi

        # Appliquer les poids des métriques
        for metric_name, weight in self.WEIGHTS.items():
            if metric_name in metrics:
                metric_value = self._normalize_metric(metrics[metric_name])
                phi_score += weight * metric_value * 0.5  # Impact max 0.5 par métrique

        # Limiter à φ-AUTONOMOUS max
        return min(phi_score, self.PHI_AUTONOMOUS)

    def calculate_phi_delta(self, phi_pre: float, phi_post: float) -> float:
        """
        Calcule le delta φ entre deux états

        Args:
            phi_pre: Score φ avant changement
            phi_post: Score φ après changement

        Returns:
            float: Delta φ (positif = amélioration)
        """
        return phi_post - phi_pre

    def assess_maturity_level(self, phi_score: float) -> PhiCPSLevel:
        """
        Évalue le niveau de maturité cognitive

        Args:
            phi_score: Score φ-CPS

        Returns:
            PhiCPSLevel: Niveau de maturité
        """
        if phi_score >= self.PHI_AUTONOMOUS:
            return PhiCPSLevel.AUTONOMOUS
        elif phi_score >= self.PHI_CONSCIOUS:
            return PhiCPSLevel.CONSCIOUS
        elif phi_score >= self.PHI_EMERGENT:
            return PhiCPSLevel.EMERGENT
        else:
            return PhiCPSLevel.GENESIS

    def _normalize_metric(self, value: Any) -> float:
        """
        Normalise une métrique en valeur 0-1

        Args:
            value: Valeur brute de la métrique

        Returns:
            float: Valeur normalisée 0-1
        """
        if isinstance(value, bool):
            return 1.0 if value else 0.0
        elif isinstance(value, (int, float)):
            # Assumer échelle 0-100 ou 0-10, normaliser à 0-1
            if value >= 100:
                return min(value / 100.0, 1.0)
            elif value >= 10:
                return min(value / 10.0, 1.0)
            else:
                return min(max(value, 0.0), 1.0)
        elif isinstance(value, str):
            # Conversion qualitative
            qualitative_map = {
                "low": 0.2,
                "medium": 0.5,
                "high": 0.8,
                "excellent": 1.0,
                "poor": 0.1,
                "good": 0.7,
                "excellent": 1.0,
            }
            return qualitative_map.get(value.lower(), 0.5)
        else:
            return 0.5  # Valeur par défaut

    def predict_evolution_trajectory(
        self, current_phi: float, trends: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Prédit la trajectoire d'évolution φ-CPS

        Args:
            current_phi: Score φ actuel
            trends: Tendances observées

        Returns:
            Dict avec prédictions et recommandations
        """
        trajectory = {
            "current_level": self.assess_maturity_level(current_phi),
            "predicted_next_level": None,
            "time_to_next_level": None,
            "recommendations": [],
        }

        # Prédiction basée sur tendances
        improvement_rate = trends.get("improvement_rate", 0.1)

        if current_phi < self.PHI_EMERGENT:
            trajectory["predicted_next_level"] = PhiCPSLevel.EMERGENT
            trajectory["time_to_next_level"] = math.ceil(
                (self.PHI_EMERGENT - current_phi) / improvement_rate
            )
            trajectory["recommendations"].append("Augmenter l'autonomie décisionnelle")
        elif current_phi < self.PHI_CONSCIOUS:
            trajectory["predicted_next_level"] = PhiCPSLevel.CONSCIOUS
            trajectory["time_to_next_level"] = math.ceil(
                (self.PHI_CONSCIOUS - current_phi) / improvement_rate
            )
            trajectory["recommendations"].append("Développer capacités d'adaptation")
        elif current_phi < self.PHI_AUTONOMOUS:
            trajectory["predicted_next_level"] = PhiCPSLevel.AUTONOMOUS
            trajectory["time_to_next_level"] = math.ceil(
                (self.PHI_AUTONOMOUS - current_phi) / improvement_rate
            )
            trajectory["recommendations"].append("Implémenter apprentissage autonome")

        return trajectory
