"""PhiCPSValidator - φ-CPS drift validation."""

from typing import Dict, Any


class PhiCPSValidator:
    """Validate φ-CPS drift against threshold."""

    def __init__(self, drift_threshold: float = 0.05):
        self.drift_threshold = drift_threshold

    def validate(self, baseline: float, current: float, delta: float) -> Dict[str, Any]:
        """Validate φ-CPS drift."""
        drift_percentage = abs(delta / baseline * 100) if baseline != 0 else 0.0
        if drift_percentage > self.drift_threshold * 100:
            return {"status": "INVALID", "drift_percentage": drift_percentage}
        return {"status": "VALID", "drift_percentage": drift_percentage}
