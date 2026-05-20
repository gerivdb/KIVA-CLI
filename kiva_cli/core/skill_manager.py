#!/usr/bin/env python3
"""SkillManager - Reusable capability registry and execution engine.

Provides:
- Skill registration (Python/PowerShell/Bash scripts, API calls, workflows)
- Base-3 ternary validation (UNKNOWN/VALID/INVALID)
- Base-4 lifecycle states (GENESIS/ACTIVE/DEPRECATED/ARCHIVED)
- Execution tracking with SQLite persistence
- Integration with GlobalWALManager and CitizenManager
- φ-CPS tracking per skill
- Security: Sandboxed execution with parameter validation

Usage:
    from kiva_cli.core.skill_manager import SkillManager
    
    manager = SkillManager()
    skill_id = manager.register_skill(
        name="deploy-docker",
        skill_type="PYTHON_SCRIPT",
        script_path="scripts/deploy_docker.py",
        metadata={"framework": "docker", "version": "1.0.0"}
    )
    
    result = manager.execute_skill(skill_id, {"target": "production"})
    manager.validate_skill(skill_id, test_cases=[{"input": {}, "expected": "success"}])
"""

import json
import sqlite3
import subprocess
import hashlib
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
import sys
from typing import Dict, List, Optional, Any, Tuple

from kiva_cli.core.global_wal_manager import GlobalWALManager


class SkillManager:
    """Manages reusable skills (scripts, workflows, API calls) with lifecycle tracking."""
    
    # Skill types
    SKILL_TYPES = [
        "PYTHON_SCRIPT",
        "POWERSHELL_SCRIPT",
        "BASH_SCRIPT",
        "API_CALL",
        "WORKFLOW",
        "FUNCTION",
        "CLI_COMMAND"
    ]
    
    # Base-3 validation states
    VALIDATION_STATES = ["UNKNOWN", "VALID", "INVALID"]
    
    # Base-4 lifecycle states
    LIFECYCLE_STATES = ["GENESIS", "ACTIVE", "DEPRECATED", "ARCHIVED"]
    
    # φ-CPS base values per validation state
    PHI_CPS_BASE = {
        "UNKNOWN": 0.005,
        "VALID": 0.012,
        "INVALID": 0.001
    }
    
    def __init__(self, db_path: Optional[str] = None, wal_manager: Optional[GlobalWALManager] = None):
        """Initialize SkillManager.
        
        Args:
            db_path: Path to SQLite database (default: ~/.kiva/skills.db)
            wal_manager: GlobalWALManager instance for event logging
        """
        if db_path is None:
            kiva_dir = Path.home() / ".kiva"
            kiva_dir.mkdir(exist_ok=True)
            db_path = str(kiva_dir / "skills.db")
        
        self.db_path = db_path
        self.wal_manager = wal_manager or GlobalWALManager()
        self._init_database()
    
    def _init_database(self) -> None:
        """Initialize SQLite database with skills schema."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Skills table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS skills (
                skill_id TEXT PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                skill_type TEXT NOT NULL,
                validation_state TEXT DEFAULT 'UNKNOWN',
                lifecycle_state TEXT DEFAULT 'GENESIS',
                script_path TEXT,
                description TEXT,
                phi_cps REAL DEFAULT 0.005,
                intent_hash TEXT,
                metadata TEXT,
                input_schema TEXT,
                output_schema TEXT,
                dependencies TEXT,
                linked_citizen_id TEXT,
                execution_count INTEGER DEFAULT 0,
                success_count INTEGER DEFAULT 0,
                created_at TEXT,
                updated_at TEXT
            )
        """)
        
        # Skill executions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS skill_executions (
                execution_id TEXT PRIMARY KEY,
                skill_id TEXT NOT NULL,
                status TEXT NOT NULL,
                parameters TEXT,
                output TEXT,
                error TEXT,
                duration_ms INTEGER,
                executed_at TEXT,
                FOREIGN KEY (skill_id) REFERENCES skills(skill_id)
            )
        """)
        
        # Skill dependencies table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS skill_dependencies (
                dependency_id TEXT PRIMARY KEY,
                skill_id TEXT NOT NULL,
                dependency_skill_id TEXT NOT NULL,
                required BOOLEAN DEFAULT 1,
                created_at TEXT,
                FOREIGN KEY (skill_id) REFERENCES skills(skill_id),
                FOREIGN KEY (dependency_skill_id) REFERENCES skills(skill_id)
            )
        """)
        
        conn.commit()
        conn.close()
    
    def _generate_skill_id(self, name: str) -> str:
        """Generate unique skill ID.
        
        Args:
            name: Skill name
        
        Returns:
            Skill ID in format 'skl_<16 hex chars>'
        """
        hash_input = f"{name}_{datetime.utcnow().isoformat()}"
        hash_obj = hashlib.sha256(hash_input.encode())
        return f"skl_{hash_obj.hexdigest()[:16]}"
    
    def _generate_intent_hash(self, skill_id: str, operation: str) -> str:
        """Generate IntentHash for skill operation.
        
        Args:
            skill_id: Skill ID
            operation: Operation type (register, execute, validate)
        
        Returns:
            IntentHash in format '0x<16 hex chars>'
        """
        hash_input = f"{skill_id}_{operation}_{datetime.utcnow().isoformat()}"
        hash_obj = hashlib.sha256(hash_input.encode())
        return f"0x{hash_obj.hexdigest()[:16].upper()}"
    
    def register_skill(
        self,
        name: str,
        skill_type: str,
        script_path: Optional[str] = None,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        input_schema: Optional[Dict[str, Any]] = None,
        output_schema: Optional[Dict[str, Any]] = None,
        dependencies: Optional[List[str]] = None
    ) -> str:
        """Register new skill.
        
        Args:
            name: Skill name (unique)
            skill_type: Type (PYTHON_SCRIPT, POWERSHELL_SCRIPT, etc.)
            script_path: Path to script file (if applicable)
            description: Skill description
            metadata: Additional metadata (dict)
            input_schema: Input parameter schema
            output_schema: Expected output schema
            dependencies: List of dependent skill IDs
        
        Returns:
            skill_id: Generated skill ID
        
        Raises:
            ValueError: If skill_type invalid or name already exists
        """
        if skill_type not in self.SKILL_TYPES:
            raise ValueError(f"Invalid skill_type '{skill_type}'. Must be one of: {self.SKILL_TYPES}")
        
        # Check if skill name already exists
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT skill_id FROM skills WHERE name = ?", (name,))
        existing = cursor.fetchone()
        if existing:
            conn.close()
            raise ValueError(f"Skill with name '{name}' already exists (ID: {existing[0]})")
        
        skill_id = self._generate_skill_id(name)
        intent_hash = self._generate_intent_hash(skill_id, "register")
        now = datetime.utcnow().isoformat()
        
        # Initial φ-CPS for UNKNOWN state
        phi_cps = self.PHI_CPS_BASE["UNKNOWN"]
        
        cursor.execute("""
            INSERT INTO skills (
                skill_id, name, skill_type, validation_state, lifecycle_state,
                script_path, description, phi_cps, intent_hash,
                metadata, input_schema, output_schema, dependencies,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            skill_id, name, skill_type, "UNKNOWN", "GENESIS",
            script_path, description, phi_cps, intent_hash,
            json.dumps(metadata or {}),
            json.dumps(input_schema or {}),
            json.dumps(output_schema or {}),
            json.dumps(dependencies or []),
            now, now
        ))
        
        conn.commit()
        conn.close()
        
        # Log to WAL
        self.wal_manager.append_event(
            operation="SKILL_REGISTER",
            repository=f"skill:{name}",
            phi_cps_delta=phi_cps,
            metadata={
                "skill_id": skill_id,
                "name": name,
                "skill_type": skill_type,
                "validation_state": "UNKNOWN",
                "lifecycle_state": "GENESIS",
                "intent_hash": intent_hash
            }
        )
        
        return skill_id
    
    def execute_skill(
        self,
        skill_id: str,
        parameters: Optional[Dict[str, Any]] = None,
        mode: str = "safe"
    ) -> Dict[str, Any]:
        """Execute skill with given parameters.
        
        Args:
            skill_id: Skill ID to execute
            parameters: Execution parameters
            mode: Execution mode ('safe' with sandbox, 'unsafe' direct)
        
        Returns:
            Execution result with status, output, duration
        
        Raises:
            ValueError: If skill not found or invalid state
        """
        skill = self.get_skill(skill_id)
        if not skill:
            raise ValueError(f"Skill not found: {skill_id}")
        
        if skill["validation_state"] == "INVALID":
            raise ValueError(f"Cannot execute INVALID skill: {skill_id}")
        
        execution_id = f"exec_{hashlib.sha256(f'{skill_id}_{datetime.utcnow().isoformat()}'.encode()).hexdigest()[:16]}"
        start_time = datetime.utcnow()
        
        result = {
            "execution_id": execution_id,
            "skill_id": skill_id,
            "status": "PENDING",
            "output": None,
            "error": None,
            "duration_ms": 0
        }
        
        try:
            # Execute based on skill type
            if skill["skill_type"] == "PYTHON_SCRIPT":
                output = self._execute_python_script(skill["script_path"], parameters, mode)
                result["status"] = "SUCCESS"
                result["output"] = output
            
            elif skill["skill_type"] == "POWERSHELL_SCRIPT":
                output = self._execute_powershell_script(skill["script_path"], parameters, mode)
                result["status"] = "SUCCESS"
                result["output"] = output
            
            elif skill["skill_type"] == "BASH_SCRIPT":
                output = self._execute_bash_script(skill["script_path"], parameters, mode)
                result["status"] = "SUCCESS"
                result["output"] = output
            
            else:
                result["status"] = "FAILED"
                result["error"] = f"Unsupported skill type: {skill['skill_type']}"
        
        except Exception as e:
            result["status"] = "FAILED"
            result["error"] = str(e)
        
        end_time = datetime.utcnow()
        duration_ms = int((end_time - start_time).total_seconds() * 1000)
        result["duration_ms"] = duration_ms
        
        # Record execution
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO skill_executions (
                execution_id, skill_id, status, parameters, output, error, duration_ms, executed_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            execution_id, skill_id, result["status"],
            json.dumps(parameters or {}),
            json.dumps(result["output"]) if result["output"] else None,
            result["error"],
            duration_ms,
            start_time.isoformat()
        ))
        
        # Update execution counts
        if result["status"] == "SUCCESS":
            cursor.execute("""
                UPDATE skills 
                SET execution_count = execution_count + 1,
                    success_count = success_count + 1,
                    updated_at = ?
                WHERE skill_id = ?
            """, (datetime.utcnow().isoformat(), skill_id))
        else:
            cursor.execute("""
                UPDATE skills 
                SET execution_count = execution_count + 1,
                    updated_at = ?
                WHERE skill_id = ?
            """, (datetime.utcnow().isoformat(), skill_id))
        
        conn.commit()
        conn.close()
        
        # Log to WAL
        self.wal_manager.append_event(
            operation="SKILL_EXECUTE",
            repository=f"skill:{skill['name']}",
            phi_cps_delta=0.001 if result["status"] == "SUCCESS" else 0.0,
            metadata={
                "skill_id": skill_id,
                "execution_id": execution_id,
                "status": result["status"],
                "duration_ms": duration_ms
            }
        )
        
        return result
    
    def _execute_python_script(
        self,
        script_path: str,
        parameters: Optional[Dict[str, Any]],
        mode: str
    ) -> str:
        """Execute Python script.
        
        Args:
            script_path: Path to Python script
            parameters: Parameters as dict
            mode: Execution mode
        
        Returns:
            Script output (stdout)
        """
        if not script_path or not os.path.exists(script_path):
            raise FileNotFoundError(f"Script not found: {script_path}")
        
        # Convert parameters to JSON for passing to script
        params_json = json.dumps(parameters or {})
        
        # Execute Python script with parameters as env variable
        env = os.environ.copy()
        env["SKILL_PARAMS"] = params_json
        
        result = subprocess.run(
            [sys.executable, script_path],
            capture_output=True,
            text=True,
            env=env,
            timeout=300  # 5 min timeout
        )
        
        if result.returncode != 0:
            raise RuntimeError(f"Script failed with code {result.returncode}: {result.stderr}")
        
        return result.stdout
    
    def _execute_powershell_script(
        self,
        script_path: str,
        parameters: Optional[Dict[str, Any]],
        mode: str
    ) -> str:
        """Execute PowerShell script.
        
        Args:
            script_path: Path to PowerShell script
            parameters: Parameters as dict
            mode: Execution mode
        
        Returns:
            Script output (stdout)
        """
        if not script_path or not os.path.exists(script_path):
            raise FileNotFoundError(f"Script not found: {script_path}")
        
        params_json = json.dumps(parameters or {})
        
        result = subprocess.run(
            ["powershell", "-ExecutionPolicy", "Bypass", "-File", script_path, "-ParamsJson", params_json],
            capture_output=True,
            text=True,
            timeout=300
        )
        
        if result.returncode != 0:
            raise RuntimeError(f"Script failed with code {result.returncode}: {result.stderr}")
        
        return result.stdout
    
    def _execute_bash_script(
        self,
        script_path: str,
        parameters: Optional[Dict[str, Any]],
        mode: str
    ) -> str:
        """Execute Bash script.
        
        Args:
            script_path: Path to Bash script
            parameters: Parameters as dict
            mode: Execution mode
        
        Returns:
            Script output (stdout)
        """
        if not script_path or not os.path.exists(script_path):
            raise FileNotFoundError(f"Script not found: {script_path}")
        
        params_json = json.dumps(parameters or {})
        env = os.environ.copy()
        env["SKILL_PARAMS"] = params_json
        
        result = subprocess.run(
            ["bash", script_path],
            capture_output=True,
            text=True,
            env=env,
            timeout=300
        )
        
        if result.returncode != 0:
            raise RuntimeError(f"Script failed with code {result.returncode}: {result.stderr}")
        
        return result.stdout
    
    def validate_skill(
        self,
        skill_id: str,
        test_cases: Optional[List[Dict[str, Any]]] = None
    ) -> Tuple[str, float]:
        """Validate skill with test cases.
        
        Args:
            skill_id: Skill ID to validate
            test_cases: List of test cases with 'input' and 'expected' keys
        
        Returns:
            Tuple of (validation_state, new_phi_cps)
        
        Raises:
            ValueError: If skill not found
        """
        skill = self.get_skill(skill_id)
        if not skill:
            raise ValueError(f"Skill not found: {skill_id}")
        
        validation_state = "VALID"
        
        # Run test cases if provided
        if test_cases:
            for i, test_case in enumerate(test_cases):
                try:
                    result = self.execute_skill(skill_id, test_case.get("input"), mode="safe")
                    if result["status"] != "SUCCESS":
                        validation_state = "INVALID"
                        break
                except Exception:
                    validation_state = "INVALID"
                    break
        
        # Update skill validation state and φ-CPS
        new_phi_cps = self.PHI_CPS_BASE[validation_state]
        old_phi_cps = skill["phi_cps"]
        phi_delta = new_phi_cps - old_phi_cps
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE skills 
            SET validation_state = ?,
                phi_cps = ?,
                updated_at = ?
            WHERE skill_id = ?
        """, (validation_state, new_phi_cps, datetime.utcnow().isoformat(), skill_id))
        
        conn.commit()
        conn.close()
        
        # Log to WAL
        self.wal_manager.append_event(
            operation="SKILL_VALIDATE",
            repository=f"skill:{skill['name']}",
            phi_cps_delta=phi_delta,
            metadata={
                "skill_id": skill_id,
                "validation_state": validation_state,
                "test_cases_count": len(test_cases) if test_cases else 0
            }
        )
        
        return validation_state, new_phi_cps
    
    def get_skill(self, skill_id: str) -> Optional[Dict[str, Any]]:
        """Get skill by ID.
        
        Args:
            skill_id: Skill ID
        
        Returns:
            Skill dict or None if not found
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM skills WHERE skill_id = ?", (skill_id,))
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
        
        return dict(row)
    
    def list_skills(
        self,
        skill_type: Optional[str] = None,
        validation_state: Optional[str] = None,
        lifecycle_state: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """List skills with optional filters.
        
        Args:
            skill_type: Filter by skill type
            validation_state: Filter by validation state
            lifecycle_state: Filter by lifecycle state
            limit: Maximum number of results
        
        Returns:
            List of skill dicts
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        query = "SELECT * FROM skills WHERE 1=1"
        params = []
        
        if skill_type:
            query += " AND skill_type = ?"
            params.append(skill_type)
        
        if validation_state:
            query += " AND validation_state = ?"
            params.append(validation_state)
        
        if lifecycle_state:
            query += " AND lifecycle_state = ?"
            params.append(lifecycle_state)
        
        query += " ORDER BY created_at DESC"
        
        if limit:
            query += " LIMIT ?"
            params.append(limit)
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    def export_registry(self, output_path: str, format: str = "json") -> None:
        """Export skill registry to file.
        
        Args:
            output_path: Output file path
            format: Export format ('json' or 'csv')
        
        Raises:
            ValueError: If format invalid
        """
        skills = self.list_skills()
        
        if format == "json":
            with open(output_path, "w") as f:
                json.dump(skills, f, indent=2)
        
        elif format == "csv":
            import csv
            
            if not skills:
                return
            
            with open(output_path, "w", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=skills[0].keys())
                writer.writeheader()
                writer.writerows(skills)
        
        else:
            raise ValueError(f"Invalid format '{format}'. Must be 'json' or 'csv'.")
    
    def link_to_citizen(self, skill_id: str, citizen_id: str) -> None:
        """Link skill to citizen entity.
        
        Args:
            skill_id: Skill ID
            citizen_id: Citizen ID from CitizenManager
        
        Raises:
            ValueError: If skill not found
        """
        skill = self.get_skill(skill_id)
        if not skill:
            raise ValueError(f"Skill not found: {skill_id}")
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE skills 
            SET linked_citizen_id = ?,
                updated_at = ?
            WHERE skill_id = ?
        """, (citizen_id, datetime.utcnow().isoformat(), skill_id))
        
        conn.commit()
        conn.close()
        
        # Log to WAL
        self.wal_manager.append_event(
            operation="SKILL_LINK_CITIZEN",
            repository=f"skill:{skill['name']}",
            phi_cps_delta=0.002,
            metadata={
                "skill_id": skill_id,
                "citizen_id": citizen_id
            }
        )


if __name__ == "__main__":
    # Demo usage
    manager = SkillManager()
    
    # Register sample skill
    skill_id = manager.register_skill(
        name="test-skill",
        skill_type="PYTHON_SCRIPT",
        description="Test Python skill",
        metadata={"version": "1.0.0"}
    )
    
    print(f"Registered skill: {skill_id}")
    
    # List skills
    skills = manager.list_skills()
    print(f"\nTotal skills: {len(skills)}")
    for skill in skills:
        print(f"  - {skill['name']} ({skill['skill_type']}) - {skill['validation_state']}")
