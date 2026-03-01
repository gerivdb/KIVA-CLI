#!/usr/bin/env python3
"""
Citizen Manager - Entity Lifecycle & Validation

Manages entities (citizens) across L0-L5 hierarchy with base-3 ternary validation,
base-4 lifecycle states, and φ-CPS tracking. Provides cross-repo entity registry
with dependency tracking and automatic promotion/demotion.
"""

import sqlite3
import json
import secrets
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum

try:
    from tools.core.global_wal_manager import (
        GlobalWALManager,
        ValidationState,
        EventStatus
    )
except ImportError:
    # Fallback for standalone usage
    GlobalWALManager = None
    ValidationState = None
    EventStatus = None


class EntityLevel(Enum):
    """Entity hierarchy levels (L0-L5)."""
    L0_GENESIS = "L0_GENESIS"           # Unvalidated, just created
    L1_VALIDATED = "L1_VALIDATED"       # Basic validation passed
    L2_OPERATIONAL = "L2_OPERATIONAL"   # Deployed and operational
    L3_PRODUCTION = "L3_PRODUCTION"     # Stable production use
    L4_CRITICAL = "L4_CRITICAL"         # Mission-critical entity
    L5_LEGACY = "L5_LEGACY"             # Archived/deprecated


class EntityType(Enum):
    """Entity types in ecosystem."""
    PROJECT = "PROJECT"
    SERVICE = "SERVICE"
    COMPONENT = "COMPONENT"
    TOOL = "TOOL"
    LIBRARY = "LIBRARY"
    FRAMEWORK = "FRAMEWORK"
    WORKFLOW = "WORKFLOW"
    AGENT = "AGENT"


class LifecycleState(Enum):
    """Base-4 lifecycle states."""
    GENESIS = "GENESIS"
    ACTIVE = "ACTIVE"
    DEPRECATED = "DEPRECATED"
    ARCHIVED = "ARCHIVED"


@dataclass
class Citizen:
    """Entity (citizen) in ECOS ecosystem."""
    citizen_id: str
    name: str
    entity_type: str
    entity_level: str
    lifecycle_state: str
    validation_state: str
    repo: str
    phi_cps: float
    intent_hash: str
    created_at: str
    updated_at: str
    metadata: Optional[Dict[str, Any]] = None
    dependencies: Optional[List[str]] = None
    parent_citizen_id: Optional[str] = None


class CitizenManager:
    """
    Citizen Manager - Entity Lifecycle & Validation.
    
    Provides:
    - L0-L5 entity hierarchy management
    - Base-3 ternary validation (UNKNOWN/VALID/INVALID)
    - Base-4 lifecycle states (GENESIS/ACTIVE/DEPRECATED/ARCHIVED)
    - φ-CPS per-entity tracking
    - IntentHash verification
    - Entity dependency graph
    - Automatic promotion/demotion
    """
    
    def __init__(self, db_path: Optional[Path] = None):
        """
        Initialize Citizen Manager.
        
        Args:
            db_path: Path to SQLite database (default: ~/.kiva/citizens.db)
        """
        if db_path is None:
            kiva_dir = Path.home() / ".kiva"
            kiva_dir.mkdir(exist_ok=True)
            db_path = kiva_dir / "citizens.db"
        
        self.db_path = db_path
        self._init_database()
        
        # Initialize WAL Manager if available
        self.wal = None
        if GlobalWALManager:
            try:
                self.wal = GlobalWALManager()
            except Exception:
                pass
    
    def _init_database(self):
        """Initialize SQLite database schema."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Citizens table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS citizens (
                citizen_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                entity_type TEXT NOT NULL,
                entity_level TEXT NOT NULL,
                lifecycle_state TEXT NOT NULL,
                validation_state TEXT NOT NULL,
                repo TEXT NOT NULL,
                phi_cps REAL NOT NULL,
                intent_hash TEXT NOT NULL,
                parent_citizen_id TEXT,
                metadata TEXT,
                dependencies TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Indexes
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_entity_level 
            ON citizens(entity_level)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_repo 
            ON citizens(repo)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_lifecycle 
            ON citizens(lifecycle_state)
        """)
        
        # Entity relationships table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS entity_relationships (
                relationship_id TEXT PRIMARY KEY,
                source_citizen_id TEXT NOT NULL,
                target_citizen_id TEXT NOT NULL,
                relationship_type TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (source_citizen_id) REFERENCES citizens(citizen_id),
                FOREIGN KEY (target_citizen_id) REFERENCES citizens(citizen_id)
            )
        """)
        
        # Entity history table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS entity_history (
                history_id TEXT PRIMARY KEY,
                citizen_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                from_level TEXT,
                to_level TEXT,
                phi_cps_delta REAL,
                intent_hash TEXT,
                timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
                metadata TEXT,
                FOREIGN KEY (citizen_id) REFERENCES citizens(citizen_id)
            )
        """)
        
        conn.commit()
        conn.close()
    
    def register_citizen(
        self,
        name: str,
        entity_type: EntityType,
        repo: str,
        entity_level: EntityLevel = EntityLevel.L0_GENESIS,
        lifecycle_state: LifecycleState = LifecycleState.GENESIS,
        metadata: Optional[Dict[str, Any]] = None,
        dependencies: Optional[List[str]] = None,
        parent_citizen_id: Optional[str] = None
    ) -> Citizen:
        """
        Register new citizen (entity).
        
        Args:
            name: Entity name
            entity_type: Type of entity (PROJECT, SERVICE, etc.)
            repo: Repository name
            entity_level: Initial level (default: L0_GENESIS)
            lifecycle_state: Initial lifecycle (default: GENESIS)
            metadata: Additional entity metadata
            dependencies: List of dependent citizen IDs
            parent_citizen_id: Parent entity ID (if hierarchical)
        
        Returns:
            Citizen object
        """
        # Generate citizen ID
        citizen_id = self._generate_citizen_id()
        
        # Generate IntentHash
        intent_hash = self._generate_intent_hash(name, repo, entity_type.value)
        
        # Initial φ-CPS (based on level)
        phi_cps = self._calculate_initial_phi_cps(entity_level)
        
        # Create citizen
        citizen = Citizen(
            citizen_id=citizen_id,
            name=name,
            entity_type=entity_type.value,
            entity_level=entity_level.value,
            lifecycle_state=lifecycle_state.value,
            validation_state=ValidationState.UNKNOWN.value if ValidationState else "UNKNOWN",
            repo=repo,
            phi_cps=phi_cps,
            intent_hash=intent_hash,
            created_at=datetime.now(timezone.utc).isoformat(),
            updated_at=datetime.now(timezone.utc).isoformat(),
            metadata=metadata,
            dependencies=dependencies,
            parent_citizen_id=parent_citizen_id
        )
        
        # Persist to database
        self._persist_citizen(citizen)
        
        # Log to history
        self._log_history(
            citizen_id=citizen_id,
            event_type="REGISTER",
            to_level=entity_level.value,
            intent_hash=intent_hash
        )
        
        # Append to WAL if available
        if self.wal:
            self.wal.append_event(
                operation="CITIZEN_REGISTER",
                repo=repo,
                phi_cps_delta=phi_cps,
                metadata={
                    "citizen_id": citizen_id,
                    "name": name,
                    "entity_type": entity_type.value,
                    "entity_level": entity_level.value
                }
            )
        
        return citizen
    
    def promote_entity(
        self,
        citizen_id: str,
        target_level: EntityLevel
    ) -> Tuple[bool, str, Optional[Citizen]]:
        """
        Promote entity to higher level (L0→L1→L2→L3→L4).
        
        Args:
            citizen_id: Citizen ID to promote
            target_level: Target entity level
        
        Returns:
            (success, message, updated_citizen)
        """
        # Fetch current citizen
        citizen = self.get_citizen(citizen_id)
        if not citizen:
            return (False, f"Citizen not found: {citizen_id}", None)
        
        current_level = EntityLevel(citizen.entity_level)
        
        # Validate promotion path
        if not self._is_valid_promotion(current_level, target_level):
            return (
                False,
                f"Invalid promotion: {current_level.value} → {target_level.value}",
                None
            )
        
        # Calculate φ-CPS delta
        phi_delta = self._calculate_promotion_delta(current_level, target_level)
        
        # Update citizen
        updated_citizen = self._update_citizen(
            citizen_id=citizen_id,
            updates={
                "entity_level": target_level.value,
                "phi_cps": citizen.phi_cps + phi_delta,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
        )
        
        # Log to history
        self._log_history(
            citizen_id=citizen_id,
            event_type="PROMOTE",
            from_level=current_level.value,
            to_level=target_level.value,
            phi_cps_delta=phi_delta
        )
        
        # Append to WAL
        if self.wal:
            self.wal.append_event(
                operation="CITIZEN_PROMOTE",
                repo=citizen.repo,
                phi_cps_delta=phi_delta,
                metadata={
                    "citizen_id": citizen_id,
                    "from_level": current_level.value,
                    "to_level": target_level.value
                }
            )
        
        return (
            True,
            f"Promoted {citizen.name}: {current_level.value} → {target_level.value}",
            updated_citizen
        )
    
    def demote_entity(
        self,
        citizen_id: str,
        target_level: EntityLevel,
        reason: str
    ) -> Tuple[bool, str, Optional[Citizen]]:
        """
        Demote entity to lower level or archive (L5).
        
        Args:
            citizen_id: Citizen ID to demote
            target_level: Target entity level
            reason: Reason for demotion
        
        Returns:
            (success, message, updated_citizen)
        """
        citizen = self.get_citizen(citizen_id)
        if not citizen:
            return (False, f"Citizen not found: {citizen_id}", None)
        
        current_level = EntityLevel(citizen.entity_level)
        
        # Calculate φ-CPS delta (negative for demotion)
        phi_delta = -self._calculate_promotion_delta(target_level, current_level)
        
        # Update citizen
        updated_citizen = self._update_citizen(
            citizen_id=citizen_id,
            updates={
                "entity_level": target_level.value,
                "phi_cps": citizen.phi_cps + phi_delta,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
        )
        
        # Log to history
        self._log_history(
            citizen_id=citizen_id,
            event_type="DEMOTE",
            from_level=current_level.value,
            to_level=target_level.value,
            phi_cps_delta=phi_delta,
            metadata={"reason": reason}
        )
        
        # Append to WAL
        if self.wal:
            self.wal.append_event(
                operation="CITIZEN_DEMOTE",
                repo=citizen.repo,
                phi_cps_delta=phi_delta,
                metadata={
                    "citizen_id": citizen_id,
                    "from_level": current_level.value,
                    "to_level": target_level.value,
                    "reason": reason
                }
            )
        
        return (
            True,
            f"Demoted {citizen.name}: {current_level.value} → {target_level.value}",
            updated_citizen
        )
    
    def validate_entity(
        self,
        citizen_id: str,
        validation_state: ValidationState
    ) -> Tuple[bool, str]:
        """
        Update entity validation state (base-3 ternary).
        
        Args:
            citizen_id: Citizen ID
            validation_state: UNKNOWN/VALID/INVALID
        
        Returns:
            (success, message)
        """
        citizen = self.get_citizen(citizen_id)
        if not citizen:
            return (False, f"Citizen not found: {citizen_id}")
        
        self._update_citizen(
            citizen_id=citizen_id,
            updates={
                "validation_state": validation_state.value if hasattr(validation_state, 'value') else validation_state,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
        )
        
        return (True, f"Validation updated: {validation_state}")
    
    def get_citizen(self, citizen_id: str) -> Optional[Citizen]:
        """Retrieve citizen by ID."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT * FROM citizens WHERE citizen_id = ?",
            (citizen_id,)
        )
        
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
        
        return self._row_to_citizen(row)
    
    def list_citizens(
        self,
        repo: Optional[str] = None,
        entity_level: Optional[EntityLevel] = None,
        lifecycle_state: Optional[LifecycleState] = None,
        limit: int = 100
    ) -> List[Citizen]:
        """List citizens with filters."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        query = "SELECT * FROM citizens WHERE 1=1"
        params = []
        
        if repo:
            query += " AND repo = ?"
            params.append(repo)
        
        if entity_level:
            query += " AND entity_level = ?"
            params.append(entity_level.value)
        
        if lifecycle_state:
            query += " AND lifecycle_state = ?"
            params.append(lifecycle_state.value)
        
        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        
        return [self._row_to_citizen(row) for row in rows]
    
    def export_registry(
        self,
        output_path: Path,
        format: str = "json"
    ) -> bool:
        """Export citizen registry to file."""
        citizens = self.list_citizens(limit=10000)
        
        if format == "json":
            registry_data = {
                "export_timestamp": datetime.now(timezone.utc).isoformat(),
                "total_citizens": len(citizens),
                "citizens": [asdict(c) for c in citizens]
            }
            
            with open(output_path, 'w') as f:
                json.dump(registry_data, f, indent=2)
        
        elif format == "csv":
            import csv
            
            with open(output_path, 'w', newline='') as f:
                if citizens:
                    writer = csv.DictWriter(f, fieldnames=asdict(citizens[0]).keys())
                    writer.writeheader()
                    for citizen in citizens:
                        writer.writerow(asdict(citizen))
        
        else:
            return False
        
        return True
    
    def _generate_citizen_id(self) -> str:
        """Generate unique citizen ID."""
        return f"ctz_{secrets.token_hex(8)}"
    
    def _generate_intent_hash(self, name: str, repo: str, entity_type: str) -> str:
        """Generate IntentHash for entity."""
        import hashlib
        data = f"{name}|{repo}|{entity_type}|{datetime.now().isoformat()}"
        hash_obj = hashlib.sha256(data.encode())
        return "0x" + hash_obj.hexdigest()[:16].upper()
    
    def _calculate_initial_phi_cps(self, entity_level: EntityLevel) -> float:
        """Calculate initial φ-CPS based on level."""
        phi_map = {
            EntityLevel.L0_GENESIS: 0.005,
            EntityLevel.L1_VALIDATED: 0.010,
            EntityLevel.L2_OPERATIONAL: 0.015,
            EntityLevel.L3_PRODUCTION: 0.020,
            EntityLevel.L4_CRITICAL: 0.030,
            EntityLevel.L5_LEGACY: 0.002
        }
        return phi_map.get(entity_level, 0.005)
    
    def _is_valid_promotion(self, current: EntityLevel, target: EntityLevel) -> bool:
        """Check if promotion path is valid."""
        level_order = [
            EntityLevel.L0_GENESIS,
            EntityLevel.L1_VALIDATED,
            EntityLevel.L2_OPERATIONAL,
            EntityLevel.L3_PRODUCTION,
            EntityLevel.L4_CRITICAL
        ]
        
        try:
            current_idx = level_order.index(current)
            target_idx = level_order.index(target)
            return target_idx > current_idx
        except ValueError:
            return False
    
    def _calculate_promotion_delta(self, from_level: EntityLevel, to_level: EntityLevel) -> float:
        """Calculate φ-CPS delta for promotion."""
        deltas = {
            (EntityLevel.L0_GENESIS, EntityLevel.L1_VALIDATED): 0.008,
            (EntityLevel.L1_VALIDATED, EntityLevel.L2_OPERATIONAL): 0.010,
            (EntityLevel.L2_OPERATIONAL, EntityLevel.L3_PRODUCTION): 0.012,
            (EntityLevel.L3_PRODUCTION, EntityLevel.L4_CRITICAL): 0.015
        }
        return deltas.get((from_level, to_level), 0.005)
    
    def _persist_citizen(self, citizen: Citizen):
        """Persist citizen to database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO citizens
            (citizen_id, name, entity_type, entity_level, lifecycle_state,
             validation_state, repo, phi_cps, intent_hash, parent_citizen_id,
             metadata, dependencies, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            citizen.citizen_id,
            citizen.name,
            citizen.entity_type,
            citizen.entity_level,
            citizen.lifecycle_state,
            citizen.validation_state,
            citizen.repo,
            citizen.phi_cps,
            citizen.intent_hash,
            citizen.parent_citizen_id,
            json.dumps(citizen.metadata) if citizen.metadata else None,
            json.dumps(citizen.dependencies) if citizen.dependencies else None,
            citizen.created_at,
            citizen.updated_at
        ))
        
        conn.commit()
        conn.close()
    
    def _update_citizen(self, citizen_id: str, updates: Dict[str, Any]) -> Optional[Citizen]:
        """Update citizen fields."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        set_clause = ", ".join([f"{k} = ?" for k in updates.keys()])
        values = list(updates.values()) + [citizen_id]
        
        cursor.execute(
            f"UPDATE citizens SET {set_clause} WHERE citizen_id = ?",
            values
        )
        
        conn.commit()
        conn.close()
        
        return self.get_citizen(citizen_id)
    
    def _log_history(self, citizen_id: str, event_type: str, **kwargs):
        """Log event to entity history."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        history_id = f"hist_{secrets.token_hex(8)}"
        
        cursor.execute("""
            INSERT INTO entity_history
            (history_id, citizen_id, event_type, from_level, to_level,
             phi_cps_delta, intent_hash, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            history_id,
            citizen_id,
            event_type,
            kwargs.get('from_level'),
            kwargs.get('to_level'),
            kwargs.get('phi_cps_delta'),
            kwargs.get('intent_hash'),
            json.dumps(kwargs.get('metadata')) if kwargs.get('metadata') else None
        ))
        
        conn.commit()
        conn.close()
    
    def _row_to_citizen(self, row: tuple) -> Citizen:
        """Convert database row to Citizen object."""
        metadata = json.loads(row[10]) if row[10] else None
        dependencies = json.loads(row[11]) if row[11] else None
        
        return Citizen(
            citizen_id=row[0],
            name=row[1],
            entity_type=row[2],
            entity_level=row[3],
            lifecycle_state=row[4],
            validation_state=row[5],
            repo=row[6],
            phi_cps=row[7],
            intent_hash=row[8],
            parent_citizen_id=row[9],
            metadata=metadata,
            dependencies=dependencies,
            created_at=row[12],
            updated_at=row[13]
        )


if __name__ == "__main__":
    # Test implementation
    manager = CitizenManager()
    
    # Register test citizen
    citizen = manager.register_citizen(
        name="test-api",
        entity_type=EntityType.PROJECT,
        repo="KIVA-CLI",
        metadata={"framework": "fastapi"}
    )
    
    print(f"✅ Citizen registered: {citizen.citizen_id}")
    print(f"   Name: {citizen.name}")
    print(f"   Level: {citizen.entity_level}")
    print(f"   φ-CPS: {citizen.phi_cps:.4f}")
    print(f"   IntentHash: {citizen.intent_hash}")
    
    # Promote to L1
    success, msg, updated = manager.promote_entity(
        citizen_id=citizen.citizen_id,
        target_level=EntityLevel.L1_VALIDATED
    )
    
    if success:
        print(f"\n✅ {msg}")
        print(f"   New φ-CPS: {updated.phi_cps:.4f}")
