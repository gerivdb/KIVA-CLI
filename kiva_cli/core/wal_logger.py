"""WAL (Write-Ahead Log) logger for KIVA CLI operations."""

import hashlib
import os
from typing import Dict, Any, Optional


class WALLogger:
    """Logs events to the Write-Ahead Log."""

    def __init__(self):
        self._events = []

    def log_event(
        self,
        event_type: str,
        project: str,
        status: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Log an event. Returns event ID."""
        event_id = hashlib.sha256(
            f"{event_type}:{project}:{status}:{os.urandom(16).hex()}".encode()
        ).hexdigest()[:16]

        event = {
            "event_id": event_id,
            "event_type": event_type,
            "project": project,
            "status": status,
            "metadata": metadata or {},
        }
        self._events.append(event)
        return event_id

    def get_events(self, project: str = None) -> list:
        """Get logged events, optionally filtered by project."""
        if project:
            return [e for e in self._events if e["project"] == project]
        return list(self._events)
