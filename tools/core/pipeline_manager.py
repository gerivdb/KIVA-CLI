"""
PipelineManager: Multi-step workflow automation with DAG scheduling, parallel execution,
and rollback capabilities. Supports Base-3 ternary validation and Base-4 lifecycle states.
"""

import sqlite3
import json
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
import threading
import time

class PipelineType(Enum):
    """Pipeline execution types"""
    SEQUENTIAL = "SEQUENTIAL"
    PARALLEL = "PARALLEL"
    DAG = "DAG"
    CONDITIONAL = "CONDITIONAL"
    LOOP = "LOOP"
    HYBRID = "HYBRID"

class StepType(Enum):
    """Pipeline step types"""
    SKILL_EXECUTION = "SKILL_EXECUTION"
    DAEMON_START = "DAEMON_START"
    API_CALL = "API_CALL"
    SCRIPT_RUN = "SCRIPT_RUN"
    VALIDATION = "VALIDATION"
    NOTIFICATION = "NOTIFICATION"
    CONDITION = "CONDITION"
    TRANSFORM = "TRANSFORM"

class ValidationState(Enum):
    """Base-3 ternary validation states"""
    UNKNOWN = "UNKNOWN"
    VALID = "VALID"
    INVALID = "INVALID"

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
    ROLLED_BACK = "ROLLED_BACK"

class PipelineManager:
    """Manages multi-step workflow pipelines with DAG scheduling"""
    
    def __init__(self, db_path: Optional[str] = None):
        """Initialize PipelineManager with SQLite persistence"""
        self.db_path = db_path or str(Path.home() / ".kiva" / "pipelines.db")
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
        self._executor_threads: Dict[str, threading.Thread] = {}
        self._running_pipelines: Dict[str, bool] = {}
    
    def _init_db(self):
        """Initialize SQLite database schema"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Pipelines table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS pipelines (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                type TEXT NOT NULL,
                validation_state TEXT NOT NULL,
                lifecycle_state TEXT NOT NULL,
                execution_state TEXT NOT NULL,
                config TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                intent_hash TEXT,
                phi_cps REAL DEFAULT 0.0
            )
        """)
        
        # Pipeline steps table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS pipeline_steps (
                id TEXT PRIMARY KEY,
                pipeline_id TEXT NOT NULL,
                name TEXT NOT NULL,
                step_type TEXT NOT NULL,
                config TEXT,
                dependencies TEXT,
                retry_count INTEGER DEFAULT 0,
                max_retries INTEGER DEFAULT 3,
                timeout_seconds INTEGER DEFAULT 300,
                rollback_script TEXT,
                order_index INTEGER NOT NULL,
                FOREIGN KEY (pipeline_id) REFERENCES pipelines(id)
            )
        """)
        
        # Pipeline executions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS pipeline_executions (
                id TEXT PRIMARY KEY,
                pipeline_id TEXT NOT NULL,
                execution_state TEXT NOT NULL,
                started_at TEXT NOT NULL,
                completed_at TEXT,
                duration_ms INTEGER,
                error_message TEXT,
                context TEXT,
                rollback_performed INTEGER DEFAULT 0,
                FOREIGN KEY (pipeline_id) REFERENCES pipelines(id)
            )
        """)
        
        # Step executions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS step_executions (
                id TEXT PRIMARY KEY,
                execution_id TEXT NOT NULL,
                step_id TEXT NOT NULL,
                execution_state TEXT NOT NULL,
                started_at TEXT NOT NULL,
                completed_at TEXT,
                duration_ms INTEGER,
                output TEXT,
                error_message TEXT,
                retry_attempt INTEGER DEFAULT 0,
                FOREIGN KEY (execution_id) REFERENCES pipeline_executions(id),
                FOREIGN KEY (step_id) REFERENCES pipeline_steps(id)
            )
        """)
        
        # DAG edges table (for dependencies)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS dag_edges (
                id TEXT PRIMARY KEY,
                pipeline_id TEXT NOT NULL,
                from_step_id TEXT NOT NULL,
                to_step_id TEXT NOT NULL,
                condition TEXT,
                FOREIGN KEY (pipeline_id) REFERENCES pipelines(id),
                FOREIGN KEY (from_step_id) REFERENCES pipeline_steps(id),
                FOREIGN KEY (to_step_id) REFERENCES pipeline_steps(id)
            )
        """)
        
        conn.commit()
        conn.close()
    
    def register_pipeline(
        self,
        name: str,
        pipeline_type: PipelineType,
        description: str = "",
        config: Optional[Dict[str, Any]] = None
    ) -> str:
        """Register a new pipeline"""
        pipeline_id = self._generate_id(f"pipeline_{name}_{datetime.utcnow().isoformat()}")
        intent_hash = self._generate_intent_hash(pipeline_id, name, pipeline_type.value)
        phi_cps = self._calculate_phi_cps(ValidationState.UNKNOWN)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO pipelines (
                id, name, description, type, validation_state, lifecycle_state,
                execution_state, config, created_at, updated_at, intent_hash, phi_cps
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            pipeline_id, name, description, pipeline_type.value,
            ValidationState.UNKNOWN.value, LifecycleState.GENESIS.value,
            ExecutionState.PENDING.value, json.dumps(config or {}),
            datetime.utcnow().isoformat(), datetime.utcnow().isoformat(),
            intent_hash, phi_cps
        ))
        
        conn.commit()
        conn.close()
        
        return pipeline_id
    
    def add_step(
        self,
        pipeline_id: str,
        name: str,
        step_type: StepType,
        config: Dict[str, Any],
        dependencies: Optional[List[str]] = None,
        order_index: int = 0,
        max_retries: int = 3,
        timeout_seconds: int = 300,
        rollback_script: Optional[str] = None
    ) -> str:
        """Add a step to a pipeline"""
        step_id = self._generate_id(f"step_{pipeline_id}_{name}_{datetime.utcnow().isoformat()}")
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO pipeline_steps (
                id, pipeline_id, name, step_type, config, dependencies,
                retry_count, max_retries, timeout_seconds, rollback_script, order_index
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            step_id, pipeline_id, name, step_type.value, json.dumps(config),
            json.dumps(dependencies or []), 0, max_retries, timeout_seconds,
            rollback_script, order_index
        ))
        
        conn.commit()
        conn.close()
        
        return step_id
    
    def add_dag_edge(
        self,
        pipeline_id: str,
        from_step_id: str,
        to_step_id: str,
        condition: Optional[str] = None
    ) -> str:
        """Add a DAG edge (dependency) between steps"""
        edge_id = self._generate_id(f"edge_{from_step_id}_{to_step_id}")
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO dag_edges (id, pipeline_id, from_step_id, to_step_id, condition)
            VALUES (?, ?, ?, ?, ?)
        """, (edge_id, pipeline_id, from_step_id, to_step_id, condition))
        
        conn.commit()
        conn.close()
        
        return edge_id
    
    def execute_pipeline(
        self,
        pipeline_id: str,
        context: Optional[Dict[str, Any]] = None,
        async_mode: bool = False
    ) -> str:
        """Execute a pipeline (sync or async)"""
        execution_id = self._generate_id(f"exec_{pipeline_id}_{datetime.utcnow().isoformat()}")
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO pipeline_executions (
                id, pipeline_id, execution_state, started_at, context
            ) VALUES (?, ?, ?, ?, ?)
        """, (
            execution_id, pipeline_id, ExecutionState.RUNNING.value,
            datetime.utcnow().isoformat(), json.dumps(context or {})
        ))
        
        conn.commit()
        conn.close()
        
        if async_mode:
            thread = threading.Thread(
                target=self._execute_pipeline_thread,
                args=(execution_id, pipeline_id, context)
            )
            thread.daemon = True
            thread.start()
            self._executor_threads[execution_id] = thread
            self._running_pipelines[execution_id] = True
        else:
            self._execute_pipeline_thread(execution_id, pipeline_id, context)
        
        return execution_id
    
    def _execute_pipeline_thread(
        self,
        execution_id: str,
        pipeline_id: str,
        context: Optional[Dict[str, Any]]
    ):
        """Execute pipeline in thread (internal)"""
        start_time = datetime.utcnow()
        
        try:
            # Get pipeline type
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT type FROM pipelines WHERE id = ?", (pipeline_id,))
            row = cursor.fetchone()
            conn.close()
            
            if not row:
                raise ValueError(f"Pipeline {pipeline_id} not found")
            
            pipeline_type = PipelineType(row[0])
            
            # Execute based on type
            if pipeline_type == PipelineType.SEQUENTIAL:
                self._execute_sequential(execution_id, pipeline_id, context)
            elif pipeline_type == PipelineType.PARALLEL:
                self._execute_parallel(execution_id, pipeline_id, context)
            elif pipeline_type == PipelineType.DAG:
                self._execute_dag(execution_id, pipeline_id, context)
            else:
                raise NotImplementedError(f"Pipeline type {pipeline_type.value} not implemented")
            
            # Mark execution as SUCCESS
            end_time = datetime.utcnow()
            duration_ms = int((end_time - start_time).total_seconds() * 1000)
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE pipeline_executions
                SET execution_state = ?, completed_at = ?, duration_ms = ?
                WHERE id = ?
            """, (ExecutionState.SUCCESS.value, end_time.isoformat(), duration_ms, execution_id))
            conn.commit()
            conn.close()
            
        except Exception as e:
            # Mark execution as FAILED
            end_time = datetime.utcnow()
            duration_ms = int((end_time - start_time).total_seconds() * 1000)
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE pipeline_executions
                SET execution_state = ?, completed_at = ?, duration_ms = ?, error_message = ?
                WHERE id = ?
            """, (ExecutionState.FAILED.value, end_time.isoformat(), duration_ms, str(e), execution_id))
            conn.commit()
            conn.close()
        
        finally:
            if execution_id in self._running_pipelines:
                del self._running_pipelines[execution_id]
    
    def _execute_sequential(self, execution_id: str, pipeline_id: str, context: Optional[Dict[str, Any]]):
        """Execute pipeline steps sequentially"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, name, step_type, config, max_retries, timeout_seconds
            FROM pipeline_steps
            WHERE pipeline_id = ?
            ORDER BY order_index ASC
        """, (pipeline_id,))
        steps = cursor.fetchall()
        conn.close()
        
        for step in steps:
            step_id, name, step_type, config_json, max_retries, timeout = step
            self._execute_step(execution_id, step_id, name, step_type, config_json, max_retries, timeout, context)
    
    def _execute_parallel(self, execution_id: str, pipeline_id: str, context: Optional[Dict[str, Any]]):
        """Execute pipeline steps in parallel"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, name, step_type, config, max_retries, timeout_seconds
            FROM pipeline_steps
            WHERE pipeline_id = ?
        """, (pipeline_id,))
        steps = cursor.fetchall()
        conn.close()
        
        threads = []
        for step in steps:
            step_id, name, step_type, config_json, max_retries, timeout = step
            thread = threading.Thread(
                target=self._execute_step,
                args=(execution_id, step_id, name, step_type, config_json, max_retries, timeout, context)
            )
            thread.start()
            threads.append(thread)
        
        for thread in threads:
            thread.join()
    
    def _execute_dag(self, execution_id: str, pipeline_id: str, context: Optional[Dict[str, Any]]):
        """Execute pipeline steps as DAG (topological sort)"""
        # Get all steps and edges
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, name, step_type, config, max_retries, timeout_seconds
            FROM pipeline_steps
            WHERE pipeline_id = ?
        """, (pipeline_id,))
        steps = {row[0]: row for row in cursor.fetchall()}
        
        cursor.execute("""
            SELECT from_step_id, to_step_id
            FROM dag_edges
            WHERE pipeline_id = ?
        """, (pipeline_id,))
        edges = cursor.fetchall()
        conn.close()
        
        # Build adjacency list and in-degree map
        adj = {step_id: [] for step_id in steps.keys()}
        in_degree = {step_id: 0 for step_id in steps.keys()}
        
        for from_id, to_id in edges:
            adj[from_id].append(to_id)
            in_degree[to_id] += 1
        
        # Topological sort with Kahn's algorithm
        queue = [step_id for step_id, degree in in_degree.items() if degree == 0]
        executed = []
        
        while queue:
            # Execute steps with no dependencies in parallel
            threads = []
            for step_id in queue:
                step_data = steps[step_id]
                _, name, step_type, config_json, max_retries, timeout = step_data
                thread = threading.Thread(
                    target=self._execute_step,
                    args=(execution_id, step_id, name, step_type, config_json, max_retries, timeout, context)
                )
                thread.start()
                threads.append(thread)
            
            for thread in threads:
                thread.join()
            
            executed.extend(queue)
            
            # Update queue with next steps
            next_queue = []
            for step_id in queue:
                for neighbor in adj[step_id]:
                    in_degree[neighbor] -= 1
                    if in_degree[neighbor] == 0:
                        next_queue.append(neighbor)
            
            queue = next_queue
    
    def _execute_step(
        self,
        execution_id: str,
        step_id: str,
        name: str,
        step_type: str,
        config_json: str,
        max_retries: int,
        timeout: int,
        context: Optional[Dict[str, Any]]
    ):
        """Execute a single pipeline step with retries"""
        step_exec_id = self._generate_id(f"step_exec_{step_id}_{datetime.utcnow().isoformat()}")
        start_time = datetime.utcnow()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO step_executions (
                id, execution_id, step_id, execution_state, started_at
            ) VALUES (?, ?, ?, ?, ?)
        """, (step_exec_id, execution_id, step_id, ExecutionState.RUNNING.value, start_time.isoformat()))
        conn.commit()
        conn.close()
        
        retry_attempt = 0
        last_error = None
        
        while retry_attempt <= max_retries:
            try:
                # Simulate step execution (in real implementation, would call actual services)
                config = json.loads(config_json)
                output = {"step": name, "type": step_type, "config": config, "context": context}
                time.sleep(0.1)  # Simulate work
                
                # Mark as SUCCESS
                end_time = datetime.utcnow()
                duration_ms = int((end_time - start_time).total_seconds() * 1000)
                
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE step_executions
                    SET execution_state = ?, completed_at = ?, duration_ms = ?, output = ?, retry_attempt = ?
                    WHERE id = ?
                """, (ExecutionState.SUCCESS.value, end_time.isoformat(), duration_ms, json.dumps(output), retry_attempt, step_exec_id))
                conn.commit()
                conn.close()
                
                return
            
            except Exception as e:
                last_error = str(e)
                retry_attempt += 1
                if retry_attempt <= max_retries:
                    time.sleep(1 * retry_attempt)  # Exponential backoff
        
        # Mark as FAILED after exhausting retries
        end_time = datetime.utcnow()
        duration_ms = int((end_time - start_time).total_seconds() * 1000)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE step_executions
            SET execution_state = ?, completed_at = ?, duration_ms = ?, error_message = ?, retry_attempt = ?
            WHERE id = ?
        """, (ExecutionState.FAILED.value, end_time.isoformat(), duration_ms, last_error, retry_attempt, step_exec_id))
        conn.commit()
        conn.close()
        
        raise RuntimeError(f"Step {name} failed after {max_retries} retries: {last_error}")
    
    def validate_pipeline(self, pipeline_id: str) -> ValidationState:
        """Validate pipeline configuration"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Check pipeline exists
        cursor.execute("SELECT id FROM pipelines WHERE id = ?", (pipeline_id,))
        if not cursor.fetchone():
            conn.close()
            return ValidationState.INVALID
        
        # Check has steps
        cursor.execute("SELECT COUNT(*) FROM pipeline_steps WHERE pipeline_id = ?", (pipeline_id,))
        step_count = cursor.fetchone()[0]
        
        conn.close()
        
        if step_count == 0:
            return ValidationState.INVALID
        
        validation_state = ValidationState.VALID
        phi_cps = self._calculate_phi_cps(validation_state)
        
        # Update pipeline
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE pipelines
            SET validation_state = ?, lifecycle_state = ?, phi_cps = ?, updated_at = ?
            WHERE id = ?
        """, (validation_state.value, LifecycleState.ACTIVE.value, phi_cps, datetime.utcnow().isoformat(), pipeline_id))
        conn.commit()
        conn.close()
        
        return validation_state
    
    def list_pipelines(
        self,
        pipeline_type: Optional[PipelineType] = None,
        validation_state: Optional[ValidationState] = None,
        lifecycle_state: Optional[LifecycleState] = None
    ) -> List[Dict[str, Any]]:
        """List pipelines with optional filters"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        query = "SELECT * FROM pipelines WHERE 1=1"
        params = []
        
        if pipeline_type:
            query += " AND type = ?"
            params.append(pipeline_type.value)
        
        if validation_state:
            query += " AND validation_state = ?"
            params.append(validation_state.value)
        
        if lifecycle_state:
            query += " AND lifecycle_state = ?"
            params.append(lifecycle_state.value)
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        
        pipelines = []
        for row in rows:
            pipelines.append({
                "id": row[0],
                "name": row[1],
                "description": row[2],
                "type": row[3],
                "validation_state": row[4],
                "lifecycle_state": row[5],
                "execution_state": row[6],
                "config": json.loads(row[7]),
                "created_at": row[8],
                "updated_at": row[9],
                "intent_hash": row[10],
                "phi_cps": row[11]
            })
        
        return pipelines
    
    def get_execution_status(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """Get execution status"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM pipeline_executions WHERE id = ?", (execution_id,))
        row = cursor.fetchone()
        
        if not row:
            conn.close()
            return None
        
        # Get step executions
        cursor.execute("""
            SELECT se.*, ps.name
            FROM step_executions se
            JOIN pipeline_steps ps ON se.step_id = ps.id
            WHERE se.execution_id = ?
            ORDER BY se.started_at ASC
        """, (execution_id,))
        step_rows = cursor.fetchall()
        
        conn.close()
        
        steps = []
        for step_row in step_rows:
            steps.append({
                "id": step_row[0],
                "step_id": step_row[2],
                "name": step_row[10],
                "execution_state": step_row[3],
                "started_at": step_row[4],
                "completed_at": step_row[5],
                "duration_ms": step_row[6],
                "error_message": step_row[8],
                "retry_attempt": step_row[9]
            })
        
        return {
            "id": row[0],
            "pipeline_id": row[1],
            "execution_state": row[2],
            "started_at": row[3],
            "completed_at": row[4],
            "duration_ms": row[5],
            "error_message": row[6],
            "context": json.loads(row[7]),
            "rollback_performed": bool(row[8]),
            "steps": steps
        }
    
    def _generate_id(self, seed: str) -> str:
        """Generate unique ID from seed"""
        return hashlib.sha256(seed.encode()).hexdigest()[:16]
    
    def _generate_intent_hash(self, pipeline_id: str, name: str, pipeline_type: str) -> str:
        """Generate IntentHash for pipeline"""
        data = f"{pipeline_id}:{name}:{pipeline_type}:{datetime.utcnow().isoformat()}"
        hash_bytes = hashlib.sha256(data.encode()).digest()
        return "0x" + hash_bytes[:8].hex().upper()
    
    def _calculate_phi_cps(self, validation_state: ValidationState) -> float:
        """Calculate φ-CPS contribution based on validation state"""
        phi_map = {
            ValidationState.UNKNOWN: 0.010,
            ValidationState.VALID: 0.025,
            ValidationState.INVALID: 0.003
        }
        return phi_map.get(validation_state, 0.0)
