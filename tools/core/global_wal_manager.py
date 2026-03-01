#!/usr/bin/env python3
"""
Global WAL (Write-Ahead Log) Manager

Cross-repo event tracking with IntentHash¹¹ chain validation + φ-CPS drift monitoring.
Provides complete audit trail for ECOS H0 operations across ecosystem-1.
"""

import sqlite3
import json
import hashlib
import secrets
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum


class ValidationState(Enum):
    """Base-3 ternary validation states."""
    UNKNOWN = "UNKNOWN"
    VALID = "VALID"
    INVALID = "INVALID"


class EventStatus(Enum):
    """Event execution status (ternary)."""
    PENDING = "PENDING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


@dataclass
class WALEvent:
    """Single WAL event entry."""
    event_id: str
    timestamp: str
    operation: str
    repo: str
    intent_hash: str
    phi_cps_delta: float
    phi_cps_current: float
    validation_state: str
    status: str
    commit_sha: Optional[str] = None
    parent_intent_hash: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None


class GlobalWALManager:
    """
    Global Write-Ahead Log Manager for ECOS H0.
    
    Provides:
    - Cross-repo event persistence
    - IntentHash¹¹ L0-L1-L2 chain validation
    - φ-CPS cumulative drift tracking
    - Automatic rollback detection
    - Complete audit trail
    """
    
    def __init__(self, db_path: Optional[Path] = None):
        """
        Initialize Global WAL Manager.
        
        Args:
            db_path: Path to SQLite database (default: ~/.kiva/global_wal.db)
        """
        if db_path is None:
            kiva_dir = Path.home() / ".kiva"
            kiva_dir.mkdir(exist_ok=True)
            db_path = kiva_dir / "global_wal.db"
        
        self.db_path = db_path
        self.phi_cps_threshold = 0.05  # 5% drift threshold
        self._init_database()
    
    def _init_database(self):
        """Initialize SQLite database schema."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Main events table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS wal_events (
                event_id TEXT PRIMARY KEY,
                timestamp TEXT NOT NULL,
                operation TEXT NOT NULL,
                repo TEXT NOT NULL,
                intent_hash TEXT NOT NULL,
                parent_intent_hash TEXT,
                phi_cps_delta REAL NOT NULL,
                phi_cps_current REAL NOT NULL,
                validation_state TEXT NOT NULL,
                status TEXT NOT NULL,
                commit_sha TEXT,
                metadata TEXT,
                error_message TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Indexes for efficient queries
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_timestamp 
            ON wal_events(timestamp)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_repo 
            ON wal_events(repo)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_intent_hash 
            ON wal_events(intent_hash)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_operation 
            ON wal_events(operation)
        """)
        
        # Rollback points table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS rollback_points (
                rollback_id TEXT PRIMARY KEY,
                timestamp TEXT NOT NULL,
                phi_cps_snapshot REAL NOT NULL,
                event_count INTEGER NOT NULL,
                reason TEXT,
                metadata TEXT
            )
        """)
        
        conn.commit()
        conn.close()
    
    def append_event(
        self,
        operation: str,
        repo: str,
        phi_cps_delta: float,
        commit_sha: Optional[str] = None,
        parent_intent_hash: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        validation_state: ValidationState = ValidationState.VALID,
        status: EventStatus = EventStatus.SUCCESS,
        error_message: Optional[str] = None
    ) -> WALEvent:
        """
        Append new event to WAL.
        
        Args:
            operation: Operation type (e.g., 'SCAFFOLD_PROJECT', 'DEPLOY_DOCKER')
            repo: Repository name (e.g., 'KIVA-CLI')
            phi_cps_delta: φ-CPS delta for this operation
            commit_sha: Git commit SHA (if applicable)
            parent_intent_hash: Previous IntentHash for chain continuity
            metadata: Additional operation metadata
            validation_state: Base-3 ternary validation state
            status: Event execution status
            error_message: Error details (if status=FAILED)
        
        Returns:
            WALEvent object with generated IntentHash
        """
        # Generate unique event ID
        event_id = self._generate_event_id()
        
        # Generate IntentHash (L0-L1-L2 chain)
        intent_hash = self._generate_intent_hash(
            operation=operation,
            repo=repo,
            parent_hash=parent_intent_hash
        )
        
        # Get current φ-CPS
        phi_cps_current = self._get_current_phi_cps() + phi_cps_delta
        
        # Create event
        event = WALEvent(
            event_id=event_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            operation=operation,
            repo=repo,
            intent_hash=intent_hash,
            parent_intent_hash=parent_intent_hash,
            phi_cps_delta=phi_cps_delta,
            phi_cps_current=phi_cps_current,
            validation_state=validation_state.value,
            status=status.value,
            commit_sha=commit_sha,
            metadata=metadata,
            error_message=error_message
        )
        
        # Persist to database
        self._persist_event(event)
        
        # Check drift threshold
        if self._check_drift_threshold(phi_cps_current):
            self._trigger_drift_alert(phi_cps_current)
        
        return event
    
    def validate_chain(
        self,
        intent_hash: str,
        parent_intent_hash: Optional[str] = None
    ) -> Tuple[bool, str]:
        """
        Validate IntentHash chain continuity.
        
        Args:
            intent_hash: Current IntentHash
            parent_intent_hash: Expected parent IntentHash
        
        Returns:
            (is_valid, message)
        """
        if parent_intent_hash is None:
            # L0 event (no parent)
            return (True, "L0 event (genesis)")
        
        # Query parent event
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT intent_hash, validation_state FROM wal_events WHERE intent_hash = ?",
            (parent_intent_hash,)
        )
        
        result = cursor.fetchone()
        conn.close()
        
        if not result:
            return (False, f"Parent IntentHash not found: {parent_intent_hash}")
        
        parent_hash, parent_validation = result
        
        if parent_validation != ValidationState.VALID.value:
            return (
                False,
                f"Parent event invalid: {parent_hash} [{parent_validation}]"
            )
        
        return (True, f"Chain validated: {parent_hash} → {intent_hash}")
    
    def get_drift(self) -> Dict[str, Any]:
        """
        Calculate cumulative φ-CPS drift.
        
        Returns:
            Dictionary with drift metrics
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get baseline (first event or last rollback)
        cursor.execute("""
            SELECT phi_cps_current FROM rollback_points
            ORDER BY timestamp DESC LIMIT 1
        """)
        
        baseline_result = cursor.fetchone()
        
        if baseline_result:
            baseline_phi = baseline_result[0]
        else:
            # Use first event as baseline
            cursor.execute("""
                SELECT phi_cps_current FROM wal_events
                ORDER BY timestamp ASC LIMIT 1
            """)
            first_event = cursor.fetchone()
            baseline_phi = first_event[0] if first_event else 4.092
        
        # Get current φ-CPS
        current_phi = self._get_current_phi_cps()
        
        # Calculate drift
        absolute_drift = current_phi - baseline_phi
        relative_drift = absolute_drift / baseline_phi if baseline_phi > 0 else 0
        
        # Count events since baseline
        cursor.execute("""
            SELECT COUNT(*) FROM wal_events
            WHERE phi_cps_current >= ?
        """, (baseline_phi,))
        
        event_count = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            "baseline_phi": baseline_phi,
            "current_phi": current_phi,
            "absolute_drift": absolute_drift,
            "relative_drift": relative_drift,
            "threshold": self.phi_cps_threshold,
            "threshold_exceeded": relative_drift > self.phi_cps_threshold,
            "events_since_baseline": event_count
        }
    
    def query_events(
        self,
        repo: Optional[str] = None,
        operation: Optional[str] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        status: Optional[EventStatus] = None,
        limit: int = 100
    ) -> List[WALEvent]:
        """
        Query WAL events with filters.
        
        Args:
            repo: Filter by repository name
            operation: Filter by operation type
            start_time: ISO timestamp (inclusive)
            end_time: ISO timestamp (inclusive)
            status: Filter by event status
            limit: Maximum results (default: 100)
        
        Returns:
            List of WALEvent objects
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Build query
        query = "SELECT * FROM wal_events WHERE 1=1"
        params = []
        
        if repo:
            query += " AND repo = ?"
            params.append(repo)
        
        if operation:
            query += " AND operation = ?"
            params.append(operation)
        
        if start_time:
            query += " AND timestamp >= ?"
            params.append(start_time)
        
        if end_time:
            query += " AND timestamp <= ?"
            params.append(end_time)
        
        if status:
            query += " AND status = ?"
            params.append(status.value)
        
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        
        # Convert to WALEvent objects
        events = []
        for row in rows:
            metadata = json.loads(row[11]) if row[11] else None
            
            event = WALEvent(
                event_id=row[0],
                timestamp=row[1],
                operation=row[2],
                repo=row[3],
                intent_hash=row[4],
                parent_intent_hash=row[5],
                phi_cps_delta=row[6],
                phi_cps_current=row[7],
                validation_state=row[8],
                status=row[9],
                commit_sha=row[10],
                metadata=metadata,
                error_message=row[12]
            )
            events.append(event)
        
        return events
    
    def create_rollback_point(
        self,
        reason: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Create rollback point (snapshot).
        
        Args:
            reason: Reason for rollback point creation
            metadata: Additional metadata
        
        Returns:
            Rollback point ID
        """
        rollback_id = self._generate_event_id()
        current_phi = self._get_current_phi_cps()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Count events
        cursor.execute("SELECT COUNT(*) FROM wal_events")
        event_count = cursor.fetchone()[0]
        
        # Insert rollback point
        cursor.execute("""
            INSERT INTO rollback_points
            (rollback_id, timestamp, phi_cps_snapshot, event_count, reason, metadata)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            rollback_id,
            datetime.now(timezone.utc).isoformat(),
            current_phi,
            event_count,
            reason,
            json.dumps(metadata) if metadata else None
        ))
        
        conn.commit()
        conn.close()
        
        return rollback_id
    
    def export_audit(
        self,
        output_path: Path,
        format: str = "json"
    ) -> bool:
        """
        Export audit trail to file.
        
        Args:
            output_path: Output file path
            format: Output format ('json' or 'csv')
        
        Returns:
            Success status
        """
        events = self.query_events(limit=10000)
        
        if format == "json":
            audit_data = {
                "export_timestamp": datetime.now(timezone.utc).isoformat(),
                "total_events": len(events),
                "drift_metrics": self.get_drift(),
                "events": [asdict(e) for e in events]
            }
            
            with open(output_path, 'w') as f:
                json.dump(audit_data, f, indent=2)
        
        elif format == "csv":
            import csv
            
            with open(output_path, 'w', newline='') as f:
                if events:
                    writer = csv.DictWriter(f, fieldnames=asdict(events[0]).keys())
                    writer.writeheader()
                    for event in events:
                        writer.writerow(asdict(event))
        
        else:
            return False
        
        return True
    
    def _generate_event_id(self) -> str:
        """Generate unique event ID."""
        return f"evt_{secrets.token_hex(8)}"
    
    def _generate_intent_hash(
        self,
        operation: str,
        repo: str,
        parent_hash: Optional[str] = None
    ) -> str:
        """
        Generate IntentHash (L0-L1-L2 chain).
        
        Format: 0x<16-char HEX>
        """
        # Combine operation + repo + parent + timestamp
        data = f"{operation}|{repo}|{parent_hash or 'L0'}|{datetime.now().isoformat()}"
        
        # SHA256 hash
        hash_obj = hashlib.sha256(data.encode())
        
        # Take first 8 bytes (16 hex chars)
        intent_hash = "0x" + hash_obj.hexdigest()[:16].upper()
        
        return intent_hash
    
    def _get_current_phi_cps(self) -> float:
        """Get current φ-CPS from latest event."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT phi_cps_current FROM wal_events
            ORDER BY timestamp DESC LIMIT 1
        """)
        
        result = cursor.fetchone()
        conn.close()
        
        return result[0] if result else 4.092  # Default baseline
    
    def _check_drift_threshold(self, current_phi: float) -> bool:
        """Check if drift exceeds threshold."""
        drift_metrics = self.get_drift()
        return drift_metrics["threshold_exceeded"]
    
    def _trigger_drift_alert(self, current_phi: float):
        """Trigger drift alert (log + create rollback point)."""
        drift_metrics = self.get_drift()
        
        print(f"⚠️  φ-CPS DRIFT THRESHOLD EXCEEDED!")
        print(f"   Current: {current_phi:.4f}")
        print(f"   Baseline: {drift_metrics['baseline_phi']:.4f}")
        print(f"   Drift: {drift_metrics['relative_drift']:.2%} (> {self.phi_cps_threshold:.0%})")
        print(f"\n   🛑 Auto-rollback recommended")
        
        # Create automatic rollback point
        self.create_rollback_point(
            reason="AUTO_DRIFT_THRESHOLD_EXCEEDED",
            metadata=drift_metrics
        )
    
    def _persist_event(self, event: WALEvent):
        """Persist event to SQLite database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO wal_events
            (event_id, timestamp, operation, repo, intent_hash, parent_intent_hash,
             phi_cps_delta, phi_cps_current, validation_state, status,
             commit_sha, metadata, error_message)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            event.event_id,
            event.timestamp,
            event.operation,
            event.repo,
            event.intent_hash,
            event.parent_intent_hash,
            event.phi_cps_delta,
            event.phi_cps_current,
            event.validation_state,
            event.status,
            event.commit_sha,
            json.dumps(event.metadata) if event.metadata else None,
            event.error_message
        ))
        
        conn.commit()
        conn.close()


# Convenience functions
def get_global_wal() -> GlobalWALManager:
    """Get singleton Global WAL Manager instance."""
    return GlobalWALManager()


if __name__ == "__main__":
    # Test implementation
    wal = GlobalWALManager()
    
    # Append test event
    event = wal.append_event(
        operation="TEST_OPERATION",
        repo="KIVA-CLI",
        phi_cps_delta=0.01,
        metadata={"test": "data"}
    )
    
    print(f"✅ Event appended: {event.intent_hash}")
    print(f"   φ-CPS: {event.phi_cps_current:.4f}")
    
    # Query events
    events = wal.query_events(repo="KIVA-CLI", limit=5)
    print(f"\n📊 Recent events: {len(events)}")
    
    # Check drift
    drift = wal.get_drift()
    print(f"\n📈 Drift metrics:")
    print(f"   Baseline: {drift['baseline_phi']:.4f}")
    print(f"   Current: {drift['current_phi']:.4f}")
    print(f"   Drift: {drift['relative_drift']:.2%}")
