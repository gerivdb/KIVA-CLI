"""
SkillManager - Reusable skill execution for PipelineManager
Provides centralized skill registry and execution with Python/PowerShell support
"""

import sqlite3
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Any
from enum import Enum
import json
import time

class ValidationState(Enum):
    """Base-3 ternary validation states"""
    UNKNOWN = "UNKNOWN"
    VALID = "VALID"
    INVALID = "INVALID"
    PENDING = "PENDING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"

class SkillType(Enum):
    """Supported skill script types"""
    PYTHON = "PYTHON"
    POWERSHELL = "POWERSHELL"
    BASH = "BASH"

class SkillManager:
    """Manages reusable skills (scripts) with execution and validation"""
    
    def __init__(self, db_path: str = "skills.db"):
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """Initialize SQLite schema for skills"""
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS skills (
                skill_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                description TEXT,
                skill_type TEXT NOT NULL,
                script_content TEXT NOT NULL,
                timeout_seconds INTEGER DEFAULT 300,
                max_retries INTEGER DEFAULT 2,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                validation_state TEXT DEFAULT 'PENDING'
            )
        """)
        
        conn.execute("""
            CREATE TABLE IF NOT EXISTS skill_executions (
                execution_id INTEGER PRIMARY KEY AUTOINCREMENT,
                skill_id INTEGER NOT NULL,
                input_data TEXT,
                output_data TEXT,
                exit_code INTEGER,
                duration_seconds REAL,
                validation_state TEXT NOT NULL,
                error_message TEXT,
                executed_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (skill_id) REFERENCES skills(skill_id)
            )
        """)
        conn.commit()
        conn.close()
    
    def register_skill(
        self,
        name: str,
        script_content: str,
        skill_type: SkillType,
        description: str = "",
        timeout_seconds: int = 300,
        max_retries: int = 2
    ) -> int:
        """Register a new skill in the registry"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute(
            """
            INSERT INTO skills (name, description, skill_type, script_content, timeout_seconds, max_retries)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (name, description, skill_type.value, script_content, timeout_seconds, max_retries)
        )
        skill_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return skill_id
    
    def get_skill(self, name: str) -> Optional[Dict[str, Any]]:
        """Retrieve skill by name"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.execute("SELECT * FROM skills WHERE name = ?", (name,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return dict(row)
        return None
    
    def has_skill(self, name: str) -> bool:
        """Check if a skill is registered."""
        return self.get_skill(name) is not None
    
    def list_skills(self) -> List[Dict[str, Any]]:
        """List all registered skills"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.execute("SELECT * FROM skills ORDER BY name")
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]
    
    def execute_skill(
        self,
        skill_name: str,
        input_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Execute a skill with input data and return results"""
        skill = self.get_skill(skill_name)
        if not skill:
            return {
                "validation_state": ValidationState.FAILED,
                "error": f"Skill '{skill_name}' not found",
                "output": None
            }
        
        skill_type = SkillType(skill['skill_type'])
        script_content = skill['script_content']
        timeout = skill['timeout_seconds']
        max_retries = skill['max_retries']
        
        # Execute with retries
        for attempt in range(max_retries + 1):
            start_time = time.time()
            result = self._execute_script(
                script_content,
                skill_type,
                input_data,
                timeout
            )
            duration = time.time() - start_time
            
            # Log execution
            self._log_execution(
                skill['skill_id'],
                input_data,
                result,
                duration
            )
            
            if result['validation_state'] == ValidationState.SUCCESS:
                return result
            
            if attempt < max_retries:
                time.sleep(1)  # Brief delay before retry
        
        return result
    
    def _execute_script(
        self,
        script_content: str,
        skill_type: SkillType,
        input_data: Optional[Dict[str, Any]],
        timeout: int
    ) -> Dict[str, Any]:
        """Execute script content with appropriate interpreter"""
        try:
            with tempfile.NamedTemporaryFile(
                mode='w',
                suffix=self._get_script_extension(skill_type),
                delete=False
            ) as f:
                f.write(script_content)
                script_path = f.name
            
            # Prepare command
            if skill_type == SkillType.PYTHON:
                cmd = ['python', script_path]
            elif skill_type == SkillType.POWERSHELL:
                cmd = ['powershell', '-ExecutionPolicy', 'Bypass', '-File', script_path]
            elif skill_type == SkillType.BASH:
                cmd = ['bash', script_path]
            else:
                return {
                    "validation_state": ValidationState.FAILED,
                    "error": f"Unsupported skill type: {skill_type}",
                    "output": None
                }
            
            # Pass input data as JSON via stdin if provided
            input_json = json.dumps(input_data) if input_data else None
            
            # Execute
            result = subprocess.run(
                cmd,
                input=input_json,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            # Parse output
            validation_state = ValidationState.SUCCESS if result.returncode == 0 else ValidationState.FAILED
            
            return {
                "validation_state": validation_state,
                "output": result.stdout,
                "error": result.stderr if result.returncode != 0 else None,
                "exit_code": result.returncode
            }
            
        except subprocess.TimeoutExpired:
            return {
                "validation_state": ValidationState.FAILED,
                "error": f"Skill execution timeout ({timeout}s)",
                "output": None
            }
        except Exception as e:
            return {
                "validation_state": ValidationState.FAILED,
                "error": str(e),
                "output": None
            }
        finally:
            # Cleanup temp file
            try:
                Path(script_path).unlink()
            except:
                pass
    
    def _get_script_extension(self, skill_type: SkillType) -> str:
        """Get file extension for skill type"""
        extensions = {
            SkillType.PYTHON: '.py',
            SkillType.POWERSHELL: '.ps1',
            SkillType.BASH: '.sh'
        }
        return extensions.get(skill_type, '.txt')
    
    def _log_execution(
        self,
        skill_id: int,
        input_data: Optional[Dict[str, Any]],
        result: Dict[str, Any],
        duration: float
    ):
        """Log skill execution to database"""
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            """
            INSERT INTO skill_executions 
            (skill_id, input_data, output_data, exit_code, duration_seconds, validation_state, error_message)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                skill_id,
                json.dumps(input_data) if input_data else None,
                result.get('output'),
                result.get('exit_code'),
                duration,
                result['validation_state'].value,
                result.get('error')
            )
        )
        conn.commit()
        conn.close()
