"""
GlobalWALManager: Cross-repository Write-Ahead Log for event tracking,
φ-CPS validation, and IntentHash management across ecosystem-1.
"""

import sqlite3
import json
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
import threading
from dataclasses import dataclass


class EventType(Enum):
    """Event types for WAL entries"""

    COMPONENT_IMPLEMENTATION = "COMPONENT_IMPLEMENTATION"
    VALIDATION = "VALIDATION"
    DEPLOYMENT = "DEPLOYMENT"
    INCIDENT = "INCIDENT"


class Severity(Enum):
    """Event severity levels"""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class ValidationState(Enum):
    """Ternary validation states"""

    UNKNOWN = "UNKNOWN"
    VALID = "VALID"
    INVALID = "INVALID"
    PENDING = "PENDING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


class EventStatus(Enum):
    """Event execution status"""

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


@dataclass
class WALEvent:
    """Write-Ahead Log event record"""

    event_id: str
    timestamp: str
    repo_name: str
    event_type: str  # commit, issue, pr, sync, validation
    entity_id: str
    action: str  # create, update, delete, sync, validate
    intent_hash: str  # IntentHash¹¹ value
    phi_delta: float
    phi_pre: float
    phi_post: float
    status: str  # PENDING, SUCCESS, FAILED
    metadata: Dict[str, Any]
    error: Optional[str] = None


class GlobalWALManager:
    """Manages cross-repository Write-Ahead Log with φ-CPS tracking"""

    def __init__(self, db_path: Optional[str] = None):
        """Initialize GlobalWALManager with SQLite persistence"""
        self.db_path = db_path or str(Path.home() / ".kiva" / "global_wal.db")
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._init_db()

    def _init_db(self):
        """Initialize SQLite database schema"""
        conn = sqlite3.connect(self.db_path, timeout=30)
        conn.execute("PRAGMA journal_mode=DELETE")
        conn.execute("PRAGMA busy_timeout=5000")
        cursor = conn.cursor()

        # Events table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS events (
                event_id TEXT PRIMARY KEY,
                timestamp TEXT NOT NULL,
                event_type TEXT NOT NULL,
                severity TEXT NOT NULL,
                ecosystem_id TEXT NOT NULL,
                repositories TEXT NOT NULL,
                intent_hash TEXT NOT NULL,
                parent_intent_hash TEXT,
                phi_cps_baseline REAL NOT NULL,
                phi_cps_current REAL NOT NULL,
                phi_cps_delta REAL NOT NULL,
                phi_cps_threshold REAL NOT NULL,
                phi_cps_alert INTEGER NOT NULL,
                validation_state TEXT NOT NULL,
                auto_approved INTEGER NOT NULL,
                rollback_performed INTEGER DEFAULT 0,
                description TEXT,
                metadata TEXT,
                created_at TEXT NOT NULL
            )
        """)

        # Operations table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS operations (
                operation_id TEXT PRIMARY KEY,
                event_id TEXT NOT NULL,
                operation_type TEXT NOT NULL,
                repository TEXT NOT NULL,
                path TEXT,
                commit_sha TEXT,
                status TEXT NOT NULL,
                duration_ms INTEGER,
                error_message TEXT,
                FOREIGN KEY (event_id) REFERENCES events(event_id)
            )
        """)

        # Dependencies table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS dependencies (
                dependency_id TEXT PRIMARY KEY,
                event_id TEXT NOT NULL,
                from_repo TEXT NOT NULL,
                to_repo TEXT NOT NULL,
                dependency_type TEXT NOT NULL,
                version TEXT,
                FOREIGN KEY (event_id) REFERENCES events(event_id)
            )
        """)

        # Rollbacks table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS rollbacks (
                rollback_id TEXT PRIMARY KEY,
                event_id TEXT NOT NULL,
                rollback_timestamp TEXT NOT NULL,
                rollback_reason TEXT NOT NULL,
                commits_reverted TEXT,
                phi_cps_before REAL NOT NULL,
                phi_cps_after REAL NOT NULL,
                success INTEGER NOT NULL,
                FOREIGN KEY (event_id) REFERENCES events(event_id)
            )
        """)

        # Indices for performance
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events(timestamp)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_events_ecosystem ON events(ecosystem_id)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_events_type ON events(event_type)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_operations_event ON operations(event_id)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_operations_repo ON operations(repository)"
        )

        conn.commit()
        conn.close()

    def append_event(
        self,
        event_type: EventType = None,
        ecosystem_id: str = "",
        repositories: List[str] = None,
        phi_cps_baseline: float = 0.0,
        phi_cps_current: float = 0.0,
        parent_intent_hash: Optional[str] = None,
        severity: Severity = Severity.INFO,
        phi_cps_threshold: float = 0.05,
        description: str = "",
        metadata: Optional[Dict[str, Any]] = None,
        auto_approved: bool = True,
        operation: Optional[str] = None,
        repository: Optional[str] = None,
        phi_cps_delta: Optional[float] = None,
    ) -> str:
        """Append a new event to the WAL"""
        with self._lock:
            # Handle alternate calling convention from skill_manager
            if event_type is None and operation is not None:
                event_type = EventType.DEPLOYMENT
            if event_type is None:
                event_type = EventType.DEPLOYMENT
            if repositories is None and repository is not None:
                repositories = [repository]
            if repositories is None:
                repositories = []

            event_id = self._generate_id(
                f"event_{ecosystem_id}_{datetime.utcnow().isoformat()}"
            )
            intent_hash = self._generate_intent_hash(
                event_id, event_type.value, repositories, parent_intent_hash
            )

            # Handle alternate phi_cps_delta parameter
            if phi_cps_delta is not None:
                computed_delta = round(phi_cps_delta, 10)
            else:
                computed_delta = round(phi_cps_current - phi_cps_baseline, 10)
            phi_cps_alert = abs(computed_delta) > phi_cps_threshold

            validation_state = (
                ValidationState.PENDING if phi_cps_alert else ValidationState.SUCCESS
            )

            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT INTO events (
                    event_id, timestamp, event_type, severity, ecosystem_id,
                    repositories, intent_hash, parent_intent_hash,
                    phi_cps_baseline, phi_cps_current, phi_cps_delta,
                    phi_cps_threshold, phi_cps_alert, validation_state,
                    auto_approved, description, metadata, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    event_id,
                    datetime.utcnow().isoformat(),
                    event_type.value,
                    severity.value,
                    ecosystem_id,
                    json.dumps(repositories),
                    intent_hash,
                    parent_intent_hash,
                    phi_cps_baseline,
                    phi_cps_current,
                    computed_delta,
                    phi_cps_threshold,
                    int(phi_cps_alert),
                    validation_state.value,
                    int(auto_approved),
                    description,
                    json.dumps(metadata or {}),
                    datetime.utcnow().isoformat(),
                ),
            )

            conn.commit()
            conn.close()

            return event_id

    def add_operation(
        self,
        event_id: str,
        operation_type: str,
        repository: str,
        status: ValidationState,
        path: Optional[str] = None,
        commit_sha: Optional[str] = None,
        duration_ms: Optional[int] = None,
        error_message: Optional[str] = None,
    ) -> str:
        """Add an operation to an event"""
        with self._lock:
            operation_id = self._generate_id(
                f"op_{event_id}_{repository}_{datetime.utcnow().isoformat()}"
            )

            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT INTO operations (
                    operation_id, event_id, operation_type, repository,
                    path, commit_sha, status, duration_ms, error_message
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    operation_id,
                    event_id,
                    operation_type,
                    repository,
                    path,
                    commit_sha,
                    status.value,
                    duration_ms,
                    error_message,
                ),
            )

            conn.commit()
            conn.close()

            return operation_id

    def add_dependency(
        self,
        event_id: str,
        from_repo: str,
        to_repo: str,
        dependency_type: str,
        version: Optional[str] = None,
    ) -> str:
        """Add a cross-repo dependency"""
        with self._lock:
            dependency_id = self._generate_id(
                f"dep_{from_repo}_{to_repo}_{datetime.utcnow().isoformat()}"
            )

            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT INTO dependencies (
                    dependency_id, event_id, from_repo, to_repo,
                    dependency_type, version
                ) VALUES (?, ?, ?, ?, ?, ?)
            """,
                (dependency_id, event_id, from_repo, to_repo, dependency_type, version),
            )

            conn.commit()
            conn.close()

            return dependency_id

    def perform_rollback(
        self,
        event_id: str,
        reason: str,
        commits_reverted: List[str],
        phi_cps_before: float,
        phi_cps_after: float,
        success: bool = True,
    ) -> str:
        """Record a rollback operation"""
        with self._lock:
            rollback_id = self._generate_id(
                f"rollback_{event_id}_{datetime.utcnow().isoformat()}"
            )

            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT INTO rollbacks (
                    rollback_id, event_id, rollback_timestamp, rollback_reason,
                    commits_reverted, phi_cps_before, phi_cps_after, success
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    rollback_id,
                    event_id,
                    datetime.utcnow().isoformat(),
                    reason,
                    json.dumps(commits_reverted),
                    phi_cps_before,
                    phi_cps_after,
                    int(success),
                ),
            )

            # Update event
            cursor.execute(
                """
                UPDATE events
                SET rollback_performed = 1, validation_state = ?
                WHERE event_id = ?
            """,
                (ValidationState.FAILED.value, event_id),
            )

            conn.commit()
            conn.close()

            return rollback_id

    def get_event(self, event_id: str) -> Optional[Dict[str, Any]]:
        """Get event details"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM events WHERE event_id = ?", (event_id,))
        row = cursor.fetchone()

        if not row:
            conn.close()
            return None

        # Get operations
        cursor.execute("SELECT * FROM operations WHERE event_id = ?", (event_id,))
        operations = cursor.fetchall()

        # Get dependencies
        cursor.execute("SELECT * FROM dependencies WHERE event_id = ?", (event_id,))
        dependencies = cursor.fetchall()

        # Get rollbacks
        cursor.execute("SELECT * FROM rollbacks WHERE event_id = ?", (event_id,))
        rollbacks = cursor.fetchall()

        conn.close()

        return {
            "event_id": row[0],
            "timestamp": row[1],
            "event_type": row[2],
            "severity": row[3],
            "ecosystem_id": row[4],
            "repositories": json.loads(row[5]),
            "intent_hash": row[6],
            "parent_intent_hash": row[7],
            "phi_cps_baseline": row[8],
            "phi_cps_current": row[9],
            "phi_cps_delta": row[10],
            "phi_cps_threshold": row[11],
            "phi_cps_alert": bool(row[12]),
            "validation_state": row[13],
            "auto_approved": bool(row[14]),
            "rollback_performed": bool(row[15]),
            "description": row[16],
            "metadata": json.loads(row[17]),
            "created_at": row[18],
            "operations": [
                {
                    "operation_id": op[0],
                    "operation_type": op[2],
                    "repository": op[3],
                    "path": op[4],
                    "commit_sha": op[5],
                    "status": op[6],
                    "duration_ms": op[7],
                    "error_message": op[8],
                }
                for op in operations
            ],
            "dependencies": [
                {
                    "dependency_id": dep[0],
                    "from_repo": dep[2],
                    "to_repo": dep[3],
                    "dependency_type": dep[4],
                    "version": dep[5],
                }
                for dep in dependencies
            ],
            "rollbacks": [
                {
                    "rollback_id": rb[0],
                    "rollback_timestamp": rb[2],
                    "rollback_reason": rb[3],
                    "commits_reverted": json.loads(rb[4]),
                    "phi_cps_before": rb[5],
                    "phi_cps_after": rb[6],
                    "success": bool(rb[7]),
                }
                for rb in rollbacks
            ],
        }

    def query_events(
        self,
        ecosystem_id: Optional[str] = None,
        event_type: Optional[EventType] = None,
        severity: Optional[Severity] = None,
        repository: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        phi_cps_alert_only: bool = False,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Query events with filters"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        query = "SELECT * FROM events WHERE 1=1"
        params = []

        if ecosystem_id:
            query += " AND ecosystem_id = ?"
            params.append(ecosystem_id)

        if event_type:
            query += " AND event_type = ?"
            params.append(event_type.value)

        if severity:
            query += " AND severity = ?"
            params.append(severity.value)

        if repository:
            query += " AND repositories LIKE ?"
            params.append(f"%{repository}%")

        if start_date:
            query += " AND timestamp >= ?"
            params.append(start_date)

        if end_date:
            query += " AND timestamp <= ?"
            params.append(end_date)

        if phi_cps_alert_only:
            query += " AND phi_cps_alert = 1"

        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)

        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        events = []
        for row in rows:
            events.append(
                {
                    "event_id": row[0],
                    "timestamp": row[1],
                    "event_type": row[2],
                    "severity": row[3],
                    "ecosystem_id": row[4],
                    "repositories": json.loads(row[5]),
                    "intent_hash": row[6],
                    "parent_intent_hash": row[7],
                    "phi_cps_baseline": row[8],
                    "phi_cps_current": row[9],
                    "phi_cps_delta": row[10],
                    "phi_cps_threshold": row[11],
                    "phi_cps_alert": bool(row[12]),
                    "validation_state": row[13],
                    "auto_approved": bool(row[14]),
                    "rollback_performed": bool(row[15]),
                    "description": row[16],
                    "created_at": row[18],
                }
            )

        return events

    def get_statistics(
        self,
        ecosystem_id: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get WAL statistics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Build base query
        where_clause = "WHERE 1=1"
        params = []

        if ecosystem_id:
            where_clause += " AND ecosystem_id = ?"
            params.append(ecosystem_id)

        if start_date:
            where_clause += " AND timestamp >= ?"
            params.append(start_date)

        if end_date:
            where_clause += " AND timestamp <= ?"
            params.append(end_date)

        # Total events
        cursor.execute(f"SELECT COUNT(*) FROM events {where_clause}", params)
        total_events = cursor.fetchone()[0]

        # Events by type
        cursor.execute(
            f"SELECT event_type, COUNT(*) FROM events {where_clause} GROUP BY event_type",
            params,
        )
        events_by_type = {row[0]: row[1] for row in cursor.fetchall()}

        # Events by severity
        cursor.execute(
            f"SELECT severity, COUNT(*) FROM events {where_clause} GROUP BY severity",
            params,
        )
        events_by_severity = {row[0]: row[1] for row in cursor.fetchall()}

        # φ-CPS alerts
        cursor.execute(
            f"SELECT COUNT(*) FROM events {where_clause} AND phi_cps_alert = 1", params
        )
        phi_cps_alerts = cursor.fetchone()[0]

        # Rollbacks
        cursor.execute(
            f"SELECT COUNT(*) FROM events {where_clause} AND rollback_performed = 1",
            params,
        )
        rollbacks = cursor.fetchone()[0]

        # Average φ-CPS delta
        cursor.execute(f"SELECT AVG(phi_cps_delta) FROM events {where_clause}", params)
        avg_phi_delta = cursor.fetchone()[0] or 0.0

        # Success rate
        cursor.execute(
            f"SELECT validation_state, COUNT(*) FROM events {where_clause} GROUP BY validation_state",
            params,
        )
        validation_states = {row[0]: row[1] for row in cursor.fetchall()}
        success_count = validation_states.get(ValidationState.SUCCESS.value, 0)
        success_rate = success_count / total_events if total_events > 0 else 0.0

        conn.close()

        return {
            "total_events": total_events,
            "events_by_type": events_by_type,
            "events_by_severity": events_by_severity,
            "phi_cps_alerts": phi_cps_alerts,
            "rollbacks": rollbacks,
            "avg_phi_delta": avg_phi_delta,
            "validation_states": validation_states,
            "success_rate": success_rate,
        }

    def export_audit(
        self,
        output_path: Optional[str] = None,
        format: str = "json",
        **query_params
    ) -> bool:
        """Export audit trail to file.
        
        Args:
            output_path: Path to output file
            format: Export format ('json', 'csv')
            **query_params: Additional query filters
            
        Returns:
            True if export succeeded
        """
        try:
            path = output_path or str(Path.home() / ".kiva" / f"audit.{format}")
            self.export_events(format=format, output_path=path, **query_params)
            return True
        except Exception:
            return False

    def export_events(
        self, format: str = "json", output_path: Optional[str] = None, **query_params
    ) -> str:
        """Export events to JSON/CSV/Markdown"""
        events = self.query_events(**query_params)

        if format == "json":
            content = json.dumps(events, indent=2, ensure_ascii=False)
        elif format == "csv":
            import csv
            import io

            output = io.StringIO()
            if events:
                writer = csv.DictWriter(output, fieldnames=events[0].keys())
                writer.writeheader()
                writer.writerows(events)
            content = output.getvalue()
        elif format == "markdown":
            lines = ["# WAL Events Export\n"]
            for event in events:
                lines.append(f"## {event['event_id']}")
                lines.append(f"- **Timestamp**: {event['timestamp']}")
                lines.append(f"- **Type**: {event['event_type']}")
                lines.append(f"- **Severity**: {event['severity']}")
                lines.append(f"- **Repositories**: {', '.join(event['repositories'])}")
                lines.append(f"- **φ-CPS Delta**: {event['phi_cps_delta']:.4f}")
                lines.append(f"- **Validation**: {event['validation_state']}")
                lines.append("")
            content = "\n".join(lines)
        else:
            raise ValueError(f"Unsupported format: {format}")

        if output_path:
            Path(output_path).write_text(content, encoding="utf-8")
            return output_path

        return content

    def get_drift(self) -> Dict[str, Any]:
        """Calculate φ-CPS drift across all events"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Get baseline (oldest event)
        cursor.execute(
            "SELECT phi_cps_baseline FROM events ORDER BY timestamp ASC LIMIT 1"
        )
        row = cursor.fetchone()
        baseline_phi = row[0] if row else 1.0

        # Get current (newest event)
        cursor.execute(
            "SELECT phi_cps_current FROM events ORDER BY timestamp DESC LIMIT 1"
        )
        row = cursor.fetchone()
        current_phi = row[0] if row else baseline_phi

        # Count events since baseline
        cursor.execute("SELECT COUNT(*) FROM events")
        total_events = cursor.fetchone()[0]

        # Count alerts
        cursor.execute("SELECT COUNT(*) FROM events WHERE phi_cps_alert = 1")
        alert_count = cursor.fetchone()[0]

        conn.close()

        absolute_drift = current_phi - baseline_phi
        relative_drift = absolute_drift / baseline_phi if baseline_phi != 0 else 0.0
        threshold = 0.05

        return {
            "baseline_phi": baseline_phi,
            "current_phi": current_phi,
            "absolute_drift": absolute_drift,
            "relative_drift": relative_drift,
            "threshold": threshold,
            "threshold_exceeded": abs(relative_drift) > threshold,
            "events_since_baseline": total_events,
            "alert_count": alert_count,
        }

    def query_events(
        self,
        repo: Optional[str] = None,
        operation: Optional[str] = None,
        start_time: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 20,
        ecosystem_id: Optional[str] = None,
        event_type: Optional[EventType] = None,
        phi_cps_alert_only: bool = False,
    ) -> List[Dict[str, Any]]:
        """Query WAL events with optional filters"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        query = "SELECT * FROM events WHERE 1=1"
        params: list = []

        if repo:
            query += " AND repositories LIKE ?"
            params.append(f"%{repo}%")
        if operation:
            query += " AND event_type = ?"
            params.append(operation)
        if start_time:
            query += " AND timestamp >= ?"
            params.append(start_time)
        if status:
            query += " AND validation_state = ?"
            params.append(status)
        if ecosystem_id:
            query += " AND ecosystem_id = ?"
            params.append(ecosystem_id)
        if event_type:
            query += " AND event_type = ?"
            params.append(event_type.value if hasattr(event_type, 'value') else str(event_type))
        if phi_cps_alert_only:
            query += " AND phi_cps_delta > phi_cps_threshold"

        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)

        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        events = []
        for row in rows:
            events.append({
                "event_id": row[0],
                "timestamp": row[1],
                "event_type": row[2],
                "severity": row[3],
                "ecosystem_id": row[4],
                "repositories": json.loads(row[5]),
                "intent_hash": row[6],
                "parent_intent_hash": row[7],
                "phi_cps_baseline": row[8],
                "phi_cps_current": row[9],
                "phi_cps_delta": row[10],
                "phi_cps_threshold": row[11],
                "phi_cps_alert": bool(row[12]),
                "validation_state": row[13],
                "auto_approved": bool(row[14]),
                "rollback_performed": bool(row[15]),
                "description": row[16],
                "metadata": json.loads(row[17]) if row[17] else {},
            })
        return events

    def validate_chain(
        self,
        intent_hash: str,
        parent_intent_hash: Optional[str] = None,
    ) -> Tuple[bool, str]:
        """Verify IntentHash chain continuity"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Find the event by intent_hash
        cursor.execute(
            "SELECT * FROM events WHERE intent_hash = ?", (intent_hash,)
        )
        row = cursor.fetchone()

        if not row:
            conn.close()
            return False, f"Event with intent_hash {intent_hash} not found"

        # If parent specified, verify linkage
        if parent_intent_hash:
            cursor.execute(
                "SELECT * FROM events WHERE intent_hash = ?",
                (parent_intent_hash,),
            )
            parent_row = cursor.fetchone()
            if not parent_row:
                conn.close()
                return False, f"Parent event {parent_intent_hash} not found"
            # Verify the event's parent_intent_hash matches
            if row[7] != parent_intent_hash:
                conn.close()
                return False, f"Chain broken: event parent {row[7]} != expected {parent_intent_hash}"

        conn.close()
        return True, f"Chain valid for {intent_hash}"

    def __del__(self):
        """Cleanup on deletion."""
        # Force release of any remaining connections
        try:
            import sys
            if sys.meta_path is not None:
                import gc
                gc.collect()
        except Exception:
            pass

    def _generate_id(self, seed: str) -> str:
        """Generate unique ID from seed"""
        return hashlib.sha256(seed.encode()).hexdigest()[:16]

    def _generate_intent_hash(
        self,
        event_id: str,
        event_type: str,
        repositories: List[str],
        parent_hash: Optional[str],
    ) -> str:
        """Generate IntentHash¹¹ for event"""
        data = f"{event_id}:{event_type}:{','.join(sorted(repositories))}"
        if parent_hash:
            data += f":{parent_hash}"
        data += f":{datetime.utcnow().isoformat()}"

        hash_bytes = hashlib.sha256(data.encode()).digest()
        return "0x" + hash_bytes[:8].hex().upper()
