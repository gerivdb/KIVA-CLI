"""State manager for KIVA CLI ternary state validation."""

from typing import Dict, Optional, List, Any
from copy import deepcopy


class StateManager:
    """Manages ternary state transitions for KIVA CLI operations."""

    VALID_TRANSITIONS = {
        "PENDING": {"SUCCESS", "FAILED"},
        "SUCCESS": {"FAILED"},
        "FAILED": {"PENDING"},
        "UNKNOWN": {"PENDING", "SUCCESS", "FAILED"},
    }

    def __init__(self):
        self._states: Dict[str, str] = {}
        self._checkpoints: Dict[str, Dict[str, Any]] = {}
        self._history: Dict[str, List[Dict[str, str]]] = {}

    def set_state(self, key: str, state: str):
        """Set state for a key."""
        self._states[key] = state
        if key not in self._history:
            self._history[key] = []
        self._history[key].append({"state": state})

    def save_checkpoint(self, key: str, data: Dict[str, Any]):
        """Save a checkpoint for rollback."""
        self._checkpoints[key] = deepcopy(data)

    def restore_checkpoint(self, key: str) -> Optional[Dict[str, Any]]:
        """Restore a checkpoint."""
        return deepcopy(self._checkpoints.get(key))

    def get_state_history(self, key: str) -> List[Dict[str, str]]:
        """Get state transition history for a key."""
        return list(self._history.get(key, []))

    def get_state(self, key: str) -> Optional[str]:
        """Get state for a key."""
        return self._states.get(key)

    def transition_state(self, key: str, new_state: str):
        """Transition state for a key. Raises ValueError for invalid transitions."""
        current = self._states.get(key)
        if current is None:
            self._states[key] = new_state
            if key not in self._history:
                self._history[key] = []
            self._history[key].append({"state": new_state})
            return
        allowed = self.VALID_TRANSITIONS.get(current, set())
        if new_state not in allowed:
            raise ValueError(f"Invalid transition: {current} -> {new_state}")
        self._states[key] = new_state
        self._history[key].append({"state": new_state})

    def get_all_states(self) -> Dict[str, str]:
        """Get all states."""
        return dict(self._states)
