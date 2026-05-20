"""
PipelineManager - DAG-based workflow automation with SkillManager integration
(UPDATE: Added SKILL_EXECUTION step type support)
"""

import sqlite3
import json
from typing import Dict, List, Optional, Any
from enum import Enum
from datetime import datetime
from pathlib import Path

class ValidationState(Enum):
    """Base-3 ternary validation states"""
    PENDING = "PENDING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"

class PipelineType(Enum):
    """Pipeline execution strategies"""
    SEQUENTIAL = "SEQUENTIAL"
    PARALLEL = "PARALLEL"

class StepType(Enum):
    """Supported pipeline step types"""
    FILE_CREATE = "FILE_CREATE"
    FILE_UPDATE = "FILE_UPDATE"
    FILE_DELETE = "FILE_DELETE"
    GITHUB_COMMIT = "GITHUB_COMMIT"
    GITHUB_PR = "GITHUB_PR"
    GITHUB_ISSUE = "GITHUB_ISSUE"
    SKILL_EXECUTION = "SKILL_EXECUTION"  # NEW: Execute registered skill
    DAEMON_START = "DAEMON_START"
    DAEMON_STOP = "DAEMON_STOP"
    VALIDATION = "VALIDATION"
    NOTIFICATION = "NOTIFICATION"

class LifecycleState(Enum):
    """Base-4 lifecycle states"""
    GENESIS = "GENESIS"
    ACTIVE = "ACTIVE"
    DEPRECATED = "DEPRECATED"
    ARCHIVED = "ARCHIVED"

class ExecutionState(Enum):
    """Pipeline execution states"""
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"

class PipelineManager:
    """Manages DAG-based pipelines with SQLite persistence"""
    
    def __init__(self, db_path: str = "pipelines.db"):
        self.db_path = db_path
        self._init_db()
        self._skill_manager = None  # Lazy load to avoid circular import
    
    def _init_db(self):
        """Initialize SQLite schema"""
        conn = sqlite3.connect(self.db_path)
        
        conn.execute("""
            CREATE TABLE IF NOT EXISTS pipelines (
                pipeline_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT,
                pipeline_type TEXT NOT NULL,
                status TEXT DEFAULT 'PENDING',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                started_at TEXT,
                completed_at TEXT
            )
        """)
        
        conn.execute("""
            CREATE TABLE IF NOT EXISTS steps (
                step_id INTEGER PRIMARY KEY AUTOINCREMENT,
                pipeline_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                step_type TEXT NOT NULL,
                config TEXT,
                dependencies TEXT,
                status TEXT DEFAULT 'PENDING',
                result TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                started_at TEXT,
                completed_at TEXT,
                FOREIGN KEY (pipeline_id) REFERENCES pipelines(pipeline_id)
            )
        """)
        
        conn.commit()
        conn.close()
    
    def create_pipeline(self, name: str, description: str, pipeline_type: PipelineType) -> int:
        """Create a new pipeline"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute(
            "INSERT INTO pipelines (name, description, pipeline_type) VALUES (?, ?, ?)",
            (name, description, pipeline_type.value)
        )
        pipeline_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return pipeline_id
    
    def add_step(
        self,
        pipeline_id: int,
        name: str,
        step_type: StepType,
        config: Dict[str, Any],
        dependencies: Optional[List[int]] = None
    ) -> int:
        """Add a step to pipeline"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute(
            """INSERT INTO steps (pipeline_id, name, step_type, config, dependencies) 
               VALUES (?, ?, ?, ?, ?)""",
            (
                pipeline_id,
                name,
                step_type.value,
                json.dumps(config),
                json.dumps(dependencies or [])
            )
        )
        step_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return step_id
    
    def get_step(self, step_id: int) -> Optional[Dict[str, Any]]:
        """Get step details"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.execute("SELECT * FROM steps WHERE step_id = ?", (step_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            step = dict(row)
            step['config'] = json.loads(step['config']) if step['config'] else {}
            step['dependencies'] = json.loads(step['dependencies']) if step['dependencies'] else []
            step['result'] = json.loads(step['result']) if step['result'] else None
            return step
        return None
    
    def update_step_status(self, step_id: int, status: ValidationState, result: Optional[Dict[str, Any]] = None):
        """Update step status and result"""
        conn = sqlite3.connect(self.db_path)
        timestamp = datetime.now().isoformat()
        
        if status == ValidationState.PENDING:
            conn.execute(
                "UPDATE steps SET status = ?, started_at = ? WHERE step_id = ?",
                (status.value, timestamp, step_id)
            )
        else:
            conn.execute(
                "UPDATE steps SET status = ?, result = ?, completed_at = ? WHERE step_id = ?",
                (status.value, json.dumps(result) if result else None, timestamp, step_id)
            )
        
        conn.commit()
        conn.close()
    
    def execute_step(self, step_id: int) -> Dict[str, Any]:
        """Execute a single step (with SkillManager integration)"""
        step = self.get_step(step_id)
        if not step:
            return {"validation_state": ValidationState.FAILED, "error": "Step not found"}
        
        step_type = StepType(step['step_type'])
        config = step['config']
        
        # Handle SKILL_EXECUTION step type
        if step_type == StepType.SKILL_EXECUTION:
            skill_name = config.get('skill_name')
            skill_args = config.get('skill_args', {})
            
            if not skill_name:
                return {
                    "validation_state": ValidationState.FAILED,
                    "error": "skill_name required in config"
                }
            
            # Lazy load SkillManager
            if self._skill_manager is None:
                from tools.ecosystem.skill_manager import SkillManager
                self._skill_manager = SkillManager()
            
            # Execute skill
            result = self._skill_manager.execute_skill(skill_name, skill_args)
            
            # Update step with result
            status = result['validation_state']
            self.update_step_status(step_id, status, result)
            
            return result
        
        # Other step types (FILE_CREATE, GITHUB_COMMIT, etc.)
        # Implementation placeholder - extend as needed
        return {
            "validation_state": ValidationState.PENDING,
            "message": f"Step type {step_type.value} execution not yet implemented"
        }
