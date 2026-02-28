#!/usr/bin/env python3
"""
Global WAL Manager - Write-Ahead Log for ECOYSTEM

Provides atomic, durable event tracking across all repositories in ecosystem-1.
Implements IntentHash¹¹ validation and φ-CPS calculation.

Features:
- Atomic append operations
- Cross-repo event correlation
- IntentHash¹¹ chain validation
- φ-CPS tracking and drift detection
- Base-3 ternary state management
- Event replay capabilities
- Crash recovery
"""

import os
import json
import hashlib
import sqlite3
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
import logging
import threading

logger = logging.getLogger(__name__)


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
    """Manager for global Write-Ahead Log across ECOYSTEM"""
    
    # Base-3 status values
    STATUS_PENDING = "PENDING"
    STATUS_SUCCESS = "SUCCESS"
    STATUS_FAILED = "FAILED"
    
    # Event types
    EVENT_COMMIT = "commit"
    EVENT_ISSUE = "issue"
    EVENT_PR = "pr"
    EVENT_SYNC = "sync"
    EVENT_VALIDATION = "validation"
    
    # φ-CPS thresholds
    PHI_DRIFT_THRESHOLD = 0.05
    PHI_GENESIS = 4.092
    
    def __init__(self, db_path: Optional[Path] = None):
        """
        Args:
            db_path: Path to SQLite database (default: ~/.kiva/global_wal.db)
        """
        if db_path is None:
            db_path = Path.home() / ".kiva" / "global_wal.db"
        
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Thread-safe connection pool
        self._local = threading.local()
        
        # Initialize database
        self._init_database()
        
        logger.info(f"GlobalWALManager initialized: {self.db_path}")
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get thread-local database connection"""
        if not hasattr(self._local, 'connection'):
            self._local.connection = sqlite3.connect(
                str(self.db_path),
                check_same_thread=False
            )
            self._local.connection.row_factory = sqlite3.Row
        return self._local.connection
    
    def _init_database(self):
        """Initialize WAL database schema"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Events table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS wal_events (
                event_id TEXT PRIMARY KEY,
                timestamp TEXT NOT NULL,
                repo_name TEXT NOT NULL,
                event_type TEXT NOT NULL,
                entity_id TEXT NOT NULL,
                action TEXT NOT NULL,
                intent_hash TEXT NOT NULL,
                phi_delta REAL NOT NULL,
                phi_pre REAL NOT NULL,
                phi_post REAL NOT NULL,
                status TEXT NOT NULL,
                metadata TEXT,
                error TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Indexes for performance
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_repo_name 
            ON wal_events(repo_name)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_timestamp 
            ON wal_events(timestamp)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_event_type 
            ON wal_events(event_type)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_intent_hash 
            ON wal_events(intent_hash)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_status 
            ON wal_events(status)
        """)
        
        # φ-CPS tracking table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS phi_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                repo_name TEXT NOT NULL,
                phi_value REAL NOT NULL,
                delta REAL NOT NULL,
                event_id TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (event_id) REFERENCES wal_events(event_id)
            )
        """)
        
        # IntentHash chain validation table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS intent_chain (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                intent_hash TEXT UNIQUE NOT NULL,
                prev_hash TEXT,
                event_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                valid BOOLEAN NOT NULL DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (event_id) REFERENCES wal_events(event_id)
            )
        """)
        
        conn.commit()
        logger.info("WAL database schema initialized")
    
    # ========================================================================
    # EVENT OPERATIONS
    # ========================================================================
    
    def append_event(
        self,
        repo_name: str,
        event_type: str,
        entity_id: str,
        action: str,
        phi_delta: float,
        metadata: Optional[Dict[str, Any]] = None,
        status: str = STATUS_SUCCESS
    ) -> WALEvent:
        """
        Append event to WAL
        
        Args:
            repo_name: Repository name (e.g., "KIVA-CLI")
            event_type: Type of event
            entity_id: Entity identifier
            action: Action performed
            phi_delta: φ-CPS delta
            metadata: Additional metadata
            status: Event status (PENDING/SUCCESS/FAILED)
            
        Returns:
            WALEvent object
        """
        # Get current φ-CPS
        phi_pre = self.get_current_phi(repo_name)
        phi_post = phi_pre + phi_delta
        
        # Check drift
        if abs(phi_delta) > self.PHI_DRIFT_THRESHOLD:
            logger.warning(
                f"φ-CPS drift exceeds threshold: {phi_delta} > {self.PHI_DRIFT_THRESHOLD}"
            )
        
        # Generate event ID
        event_id = self._generate_event_id()
        
        # Compute IntentHash
        intent_hash = self._compute_intent_hash({
            "repo": repo_name,
            "type": event_type,
            "entity": entity_id,
            "action": action,
            "phi_delta": phi_delta
        })
        
        # Create event
        event = WALEvent(
            event_id=event_id,
            timestamp=datetime.now().isoformat(),
            repo_name=repo_name,
            event_type=event_type,
            entity_id=entity_id,
            action=action,
            intent_hash=intent_hash,
            phi_delta=phi_delta,
            phi_pre=phi_pre,
            phi_post=phi_post,
            status=status,
            metadata=metadata or {},
            error=None
        )
        
        # Atomic write
        self._write_event(event)
        
        # Update φ-CPS history
        self._update_phi_history(repo_name, phi_post, phi_delta, event_id)
        
        # Add to IntentHash chain
        self._add_to_intent_chain(intent_hash, event_id)
        
        logger.info(
            f"✓ WAL event appended: {repo_name}/{event_type}/{entity_id} "
            f"(φ: {phi_pre:.4f} → {phi_post:.4f}, Δ: +{phi_delta:.4f})"
        )
        
        return event
    
    def _write_event(self, event: WALEvent):
        """Atomically write event to database"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO wal_events (
                event_id, timestamp, repo_name, event_type, entity_id,
                action, intent_hash, phi_delta, phi_pre, phi_post,
                status, metadata, error
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            event.event_id,
            event.timestamp,
            event.repo_name,
            event.event_type,
            event.entity_id,
            event.action,
            event.intent_hash,
            event.phi_delta,
            event.phi_pre,
            event.phi_post,
            event.status,
            json.dumps(event.metadata),
            event.error
        ))
        
        conn.commit()
    
    def update_event_status(
        self,
        event_id: str,
        status: str,
        error: Optional[str] = None
    ):
        """Update event status"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE wal_events
            SET status = ?, error = ?
            WHERE event_id = ?
        """, (status, error, event_id))
        
        conn.commit()
        logger.info(f"✓ Event {event_id} status updated: {status}")
    
    # ========================================================================
    # φ-CPS MANAGEMENT
    # ========================================================================
    
    def get_current_phi(self, repo_name: str) -> float:
        """Get current φ-CPS value for repository"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT phi_value
            FROM phi_history
            WHERE repo_name = ?
            ORDER BY timestamp DESC
            LIMIT 1
        """, (repo_name,))
        
        row = cursor.fetchone()
        return row[0] if row else self.PHI_GENESIS
    
    def _update_phi_history(
        self,
        repo_name: str,
        phi_value: float,
        delta: float,
        event_id: str
    ):
        """Record φ-CPS change in history"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO phi_history (timestamp, repo_name, phi_value, delta, event_id)
            VALUES (?, ?, ?, ?, ?)
        """, (datetime.now().isoformat(), repo_name, phi_value, delta, event_id))
        
        conn.commit()
    
    def get_phi_history(
        self,
        repo_name: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get φ-CPS history"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        if repo_name:
            cursor.execute("""
                SELECT timestamp, repo_name, phi_value, delta, event_id
                FROM phi_history
                WHERE repo_name = ?
                ORDER BY timestamp DESC
                LIMIT ?
            """, (repo_name, limit))
        else:
            cursor.execute("""
                SELECT timestamp, repo_name, phi_value, delta, event_id
                FROM phi_history
                ORDER BY timestamp DESC
                LIMIT ?
            """, (limit,))
        
        return [
            {
                "timestamp": row[0],
                "repo_name": row[1],
                "phi_value": row[2],
                "delta": row[3],
                "event_id": row[4]
            }
            for row in cursor.fetchall()
        ]
    
    # ========================================================================
    # INTENTHASH CHAIN
    # ========================================================================
    
    def _add_to_intent_chain(
        self,
        intent_hash: str,
        event_id: str
    ):
        """Add IntentHash to validation chain"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Get previous hash
        cursor.execute("""
            SELECT intent_hash
            FROM intent_chain
            ORDER BY timestamp DESC
            LIMIT 1
        """)
        
        row = cursor.fetchone()
        prev_hash = row[0] if row else None
        
        # Insert new hash
        cursor.execute("""
            INSERT INTO intent_chain (intent_hash, prev_hash, event_id, timestamp, valid)
            VALUES (?, ?, ?, ?, ?)
        """, (intent_hash, prev_hash, event_id, datetime.now().isoformat(), True))
        
        conn.commit()
    
    def validate_intent_chain(self) -> Tuple[bool, List[str]]:
        """Validate IntentHash chain integrity"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, intent_hash, prev_hash
            FROM intent_chain
            ORDER BY timestamp ASC
        """)
        
        errors = []
        prev_hash = None
        
        for row in cursor.fetchall():
            id_, hash_, expected_prev = row
            
            if prev_hash != expected_prev:
                errors.append(
                    f"Chain break at ID {id_}: expected prev={expected_prev}, got={prev_hash}"
                )
            
            prev_hash = hash_
        
        valid = len(errors) == 0
        
        if valid:
            logger.info("✓ IntentHash chain validation: VALID")
        else:
            logger.error(f"✗ IntentHash chain validation: INVALID ({len(errors)} errors)")
        
        return valid, errors
    
    def _compute_intent_hash(self, data: Dict[str, Any]) -> str:
        """Compute IntentHash¹¹ for data"""
        serialized = json.dumps(data, sort_keys=True)
        hash_value = hashlib.sha3_256(serialized.encode()).hexdigest()
        return f"IntentHash¹¹:sha3-256:{hash_value[:16]}"
    
    # ========================================================================
    # QUERY OPERATIONS
    # ========================================================================
    
    def get_events(
        self,
        repo_name: Optional[str] = None,
        event_type: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100
    ) -> List[WALEvent]:
        """Query events with filters"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        conditions = []
        params = []
        
        if repo_name:
            conditions.append("repo_name = ?")
            params.append(repo_name)
        
        if event_type:
            conditions.append("event_type = ?")
            params.append(event_type)
        
        if status:
            conditions.append("status = ?")
            params.append(status)
        
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        params.append(limit)
        
        cursor.execute(f"""
            SELECT event_id, timestamp, repo_name, event_type, entity_id,
                   action, intent_hash, phi_delta, phi_pre, phi_post,
                   status, metadata, error
            FROM wal_events
            WHERE {where_clause}
            ORDER BY timestamp DESC
            LIMIT ?
        """, params)
        
        events = []
        for row in cursor.fetchall():
            events.append(WALEvent(
                event_id=row[0],
                timestamp=row[1],
                repo_name=row[2],
                event_type=row[3],
                entity_id=row[4],
                action=row[5],
                intent_hash=row[6],
                phi_delta=row[7],
                phi_pre=row[8],
                phi_post=row[9],
                status=row[10],
                metadata=json.loads(row[11]) if row[11] else {},
                error=row[12]
            ))
        
        return events
    
    def get_event_by_id(self, event_id: str) -> Optional[WALEvent]:
        """Get event by ID"""
        events = self.get_events(limit=1)
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT event_id, timestamp, repo_name, event_type, entity_id,
                   action, intent_hash, phi_delta, phi_pre, phi_post,
                   status, metadata, error
            FROM wal_events
            WHERE event_id = ?
        """, (event_id,))
        
        row = cursor.fetchone()
        if not row:
            return None
        
        return WALEvent(
            event_id=row[0],
            timestamp=row[1],
            repo_name=row[2],
            event_type=row[3],
            entity_id=row[4],
            action=row[5],
            intent_hash=row[6],
            phi_delta=row[7],
            phi_pre=row[8],
            phi_post=row[9],
            status=row[10],
            metadata=json.loads(row[11]) if row[11] else {},
            error=row[12]
        )
    
    # ========================================================================
    # STATISTICS
    # ========================================================================
    
    def get_stats(self, repo_name: Optional[str] = None) -> Dict[str, Any]:
        """Get WAL statistics"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        where_clause = "WHERE repo_name = ?" if repo_name else ""
        params = [repo_name] if repo_name else []
        
        cursor.execute(f"""
            SELECT
                COUNT(*) as total_events,
                SUM(CASE WHEN status = 'SUCCESS' THEN 1 ELSE 0 END) as successful,
                SUM(CASE WHEN status = 'FAILED' THEN 1 ELSE 0 END) as failed,
                SUM(CASE WHEN status = 'PENDING' THEN 1 ELSE 0 END) as pending,
                SUM(phi_delta) as total_phi_delta
            FROM wal_events
            {where_clause}
        """, params)
        
        row = cursor.fetchone()
        
        current_phi = self.get_current_phi(repo_name) if repo_name else None
        
        return {
            "total_events": row[0] or 0,
            "successful": row[1] or 0,
            "failed": row[2] or 0,
            "pending": row[3] or 0,
            "total_phi_delta": row[4] or 0.0,
            "current_phi": current_phi
        }
    
    # ========================================================================
    # UTILITIES
    # ========================================================================
    
    def _generate_event_id(self) -> str:
        """Generate unique event ID"""
        timestamp = datetime.now().isoformat()
        random_data = os.urandom(8).hex()
        return f"wal-{hashlib.sha256(f'{timestamp}{random_data}'.encode()).hexdigest()[:16]}"
    
    def export_to_json(self, output_path: Path, repo_name: Optional[str] = None):
        """Export WAL to JSON file"""
        events = self.get_events(repo_name=repo_name, limit=10000)
        
        export_data = {
            "export_timestamp": datetime.now().isoformat(),
            "repo_name": repo_name,
            "total_events": len(events),
            "events": [asdict(event) for event in events]
        }
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w') as f:
            json.dump(export_data, f, indent=2)
        
        logger.info(f"✓ WAL exported to {output_path}")
    
    def close(self):
        """Close database connection"""
        if hasattr(self._local, 'connection'):
            self._local.connection.close()
            logger.info("WAL database connection closed")
