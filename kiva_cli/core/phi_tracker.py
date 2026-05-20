"""Phi-CPS impact tracker for KIVA CLI operations."""

from typing import Dict, Any


class PhiCPSTracker:
    """Tracks φ-CPS (Phi-Causal Pipeline Score) impact of operations."""

    def __init__(self):
        self._baseline = 4.092
        self._current = 4.092
        self._threshold = 0.05

    def calculate_impact(self, operation: str, success: bool, complexity: float = 1.0) -> float:
        """Calculate φ-CPS impact of an operation.

        Returns a positive float representing the impact magnitude.
        """
        base_weights = {
            "deploy": 0.012,
            "configure": 0.008,
            "scaffold": 0.015,
            "rollback": 0.020,
        }
        weight = base_weights.get(operation, 0.010)
        impact = weight * complexity
        if not success:
            impact *= 2.0
        return round(impact, 6)

    def get_current_phi(self) -> float:
        """Get current φ-CPS value."""
        return self._current

    def get_drift(self) -> float:
        """Get current drift from baseline."""
        return round(abs(self._current - self._baseline), 6)

    def is_within_threshold(self) -> bool:
        """Check if current drift is within threshold."""
        return self.get_drift() <= self._threshold
