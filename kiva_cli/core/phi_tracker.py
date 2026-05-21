"""Phi-CPS impact tracker for KIVA CLI operations."""

from typing import Dict, Any


class PhiCPSTracker:
    """Tracks φ-CPS (Phi-Causal Pipeline Score) impact of operations."""

    def __init__(self):
        self._baseline = 4.092
        self._current = 4.092
        self._threshold = 0.05

    def calculate_impact(self, operation: str = None, success: bool = True, complexity: float = 1.0, type: str = None) -> float:
        """Calculate φ-CPS impact of an operation.

        Returns a positive float representing the impact magnitude.
        """
        op = type or operation or "unknown"
        base_weights = {
            "deploy": 0.012,
            "configure": 0.008,
            "scaffold": 0.015,
            "rollback": 0.020,
            "config_update": 0.008,
            "health_check": 0.005,
        }
        weight = base_weights.get(op, 0.010)
        impact = weight * complexity
        if not success:
            impact *= 2.0
        return round(impact, 6)

    def calculate_drift(self, baseline: float, current: float) -> float:
        """Calculate absolute drift between baseline and current."""
        return round(abs(current - baseline), 6)

    def should_rollback(self, baseline: float, current: float) -> bool:
        """Check if rollback should be triggered based on drift."""
        if baseline == 0:
            return False
        drift_percent = abs(current - baseline) / baseline * 100
        return drift_percent > 2.0

    def calculate_workflow_impact(self, result: Dict[str, Any]) -> float:
        """Calculate total φ-CPS impact from a workflow result."""
        steps = result.get("steps", [])
        total = 0.0
        for step in steps:
            step_name = step.get("step", step.get("id", "unknown"))
            success = step.get("status") == "SUCCESS"
            total += self.calculate_impact(operation=step_name, success=success)
        return round(total, 6)

    def get_current_phi(self) -> float:
        """Get current φ-CPS value."""
        return self._current

    def get_drift(self) -> float:
        """Get current drift from baseline."""
        return round(abs(self._current - self._baseline), 6)

    def is_within_threshold(self) -> bool:
        """Check if current drift is within threshold."""
        return self.get_drift() <= self._threshold
