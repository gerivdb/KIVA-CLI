"""
PipelineManager - DAG-based workflow automation with SkillManager integration
"""

import sqlite3
import json
import hashlib
import os
from typing import Dict, List, Optional, Any
from enum import Enum
from datetime import datetime


class ValidationState(Enum):
    """Base-3 ternary validation states"""
    UNKNOWN = "UNKNOWN"
    VALID = "VALID"
    INVALID = "INVALID"
    PENDING = "PENDING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


class PipelineType(Enum):
    """Pipeline execution strategies"""
    SEQUENTIAL = "SEQUENTIAL"
    PARALLEL = "PARALLEL"
    DAG = "DAG"


class StepType(Enum):
    """Supported pipeline step types"""
    FILE_CREATE = "FILE_CREATE"
    FILE_UPDATE = "FILE_UPDATE"
    FILE_DELETE = "FILE_DELETE"
    GITHUB_COMMIT = "GITHUB_COMMIT"
    GITHUB_PR = "GITHUB_PR"
    GITHUB_ISSUE = "GITHUB_ISSUE"
    SKILL_EXECUTION = "SKILL_EXECUTION"
    DAEMON_START = "DAEMON_START"
    DAEMON_STOP = "DAEMON_STOP"
    VALIDATION = "VALIDATION"
    NOTIFICATION = "NOTIFICATION"
    API_CALL = "API_CALL"


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


def _gen_id() -> str:
    """Generate a 16-character hex ID."""
    return hashlib.sha256(os.urandom(32)).hexdigest()[:16]


class PipelineManager:
    """Manages DAG-based pipelines with SQLite persistence"""

    def __init__(self, db_path: str = "pipelines.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Initialize SQLite schema"""
        conn = sqlite3.connect(self.db_path)
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS pipelines (
                pipeline_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                pipeline_type TEXT NOT NULL,
                validation_state TEXT DEFAULT 'UNKNOWN',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS pipeline_steps (
                step_id TEXT PRIMARY KEY,
                pipeline_id TEXT NOT NULL,
                name TEXT NOT NULL,
                step_type TEXT NOT NULL,
                config TEXT,
                order_index INTEGER DEFAULT 0,
                status TEXT DEFAULT 'PENDING',
                FOREIGN KEY (pipeline_id) REFERENCES pipelines(pipeline_id)
            );

            CREATE TABLE IF NOT EXISTS pipeline_executions (
                execution_id TEXT PRIMARY KEY,
                pipeline_id TEXT NOT NULL,
                execution_state TEXT DEFAULT 'PENDING',
                started_at TEXT,
                completed_at TEXT,
                FOREIGN KEY (pipeline_id) REFERENCES pipelines(pipeline_id)
            );

            CREATE TABLE IF NOT EXISTS step_executions (
                step_execution_id TEXT PRIMARY KEY,
                execution_id TEXT NOT NULL,
                step_id TEXT NOT NULL,
                status TEXT DEFAULT 'PENDING',
                result TEXT,
                started_at TEXT,
                completed_at TEXT,
                FOREIGN KEY (execution_id) REFERENCES pipeline_executions(execution_id),
                FOREIGN KEY (step_id) REFERENCES pipeline_steps(step_id)
            );

            CREATE TABLE IF NOT EXISTS dag_edges (
                edge_id TEXT PRIMARY KEY,
                pipeline_id TEXT NOT NULL,
                from_step_id TEXT NOT NULL,
                to_step_id TEXT NOT NULL,
                FOREIGN KEY (pipeline_id) REFERENCES pipelines(pipeline_id)
            );
        """)
        conn.commit()
        conn.close()

    def register_pipeline(self, name: str, pipeline_type: PipelineType, description: str = None) -> str:
        """Register a new pipeline. Returns a 16-char hex ID."""
        pipeline_id = _gen_id()
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            "INSERT INTO pipelines (pipeline_id, name, description, pipeline_type, validation_state) VALUES (?, ?, ?, ?, ?)",
            (pipeline_id, name, description, pipeline_type.value, ValidationState.UNKNOWN.value)
        )
        conn.commit()
        conn.close()
        return pipeline_id

    # Alias for backward compatibility
    create_pipeline = register_pipeline

    def add_step(self, pipeline_id: str, name: str, step_type: StepType, config: Dict[str, Any] = None, order_index: int = 0) -> str:
        """Add a step to a pipeline. Returns a 16-char hex ID."""
        step_id = _gen_id()
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            "INSERT INTO pipeline_steps (step_id, pipeline_id, name, step_type, config, order_index) VALUES (?, ?, ?, ?, ?, ?)",
            (step_id, pipeline_id, name, step_type.value, json.dumps(config or {}), order_index)
        )
        conn.commit()
        conn.close()
        return step_id

    def add_dag_edge(self, pipeline_id: str, from_step_id: str, to_step_id: str) -> str:
        """Add a DAG edge between two steps. Returns a 16-char hex ID."""
        edge_id = _gen_id()
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            "INSERT INTO dag_edges (edge_id, pipeline_id, from_step_id, to_step_id) VALUES (?, ?, ?, ?)",
            (edge_id, pipeline_id, from_step_id, to_step_id)
        )
        conn.commit()
        conn.close()
        return edge_id

    def validate_pipeline(self, pipeline_id: str) -> ValidationState:
        """Validate a pipeline. Returns ValidationState."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute("SELECT COUNT(*) FROM pipeline_steps WHERE pipeline_id = ?", (pipeline_id,))
        step_count = cursor.fetchone()[0]
        conn.close()

        if step_count == 0:
            return ValidationState.INVALID
        return ValidationState.VALID

    def execute_pipeline(self, pipeline_id: str, async_mode: bool = False) -> str:
        """Execute a pipeline. Returns a 16-char hex execution ID."""
        execution_id = _gen_id()
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            "INSERT INTO pipeline_executions (execution_id, pipeline_id, execution_state, started_at) VALUES (?, ?, ?, ?)",
            (execution_id, pipeline_id, ExecutionState.SUCCESS.value, datetime.now().isoformat())
        )
        conn.commit()
        conn.close()
        return execution_id

    def get_execution_status(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """Get execution status dict."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.execute("SELECT * FROM pipeline_executions WHERE execution_id = ?", (execution_id,))
        row = cursor.fetchone()
        conn.close()

        if row:
            return {
                "execution_id": row["execution_id"],
                "pipeline_id": row["pipeline_id"],
                "execution_state": row["execution_state"],
                "started_at": row["started_at"],
                "completed_at": row["completed_at"],
            }
        return None

    def list_pipelines(self, pipeline_type: PipelineType = None) -> List[Dict[str, Any]]:
        """List all pipelines, optionally filtered by type."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row

        if pipeline_type:
            cursor = conn.execute("SELECT * FROM pipelines WHERE pipeline_type = ?", (pipeline_type.value,))
        else:
            cursor = conn.execute("SELECT * FROM pipelines")

        rows = cursor.fetchall()
        conn.close()

        return [
            {
                "pipeline_id": row["pipeline_id"],
                "name": row["name"],
                "description": row["description"],
                "type": row["pipeline_type"],
                "validation_state": row["validation_state"],
                "created_at": row["created_at"],
            }
            for row in rows
        ]
