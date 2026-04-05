#!/usr/bin/env python3
"""
OpenSandbox Manager - KIVA CLI

Secure sandbox execution environment for skills, scripts, and agents.
Based on Alibaba OpenSandbox (https://github.com/alibaba/OpenSandbox).
"""

import json
import os
import subprocess
import tempfile
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Any


class SandboxResult:
    def __init__(self, success: bool, stdout: str, stderr: str, exit_code: int):
        self.success = success
        self.stdout = stdout
        self.stderr = stderr
        self.exit_code = exit_code


class OpenSandboxManager:
    """OpenSandbox Manager for secure execution."""

    def __init__(self, sandbox_dir: Optional[str] = None):
        if sandbox_dir is None:
            sandbox_dir = "C:\\DevTools\\data\\sandbox"
        self.sandbox_dir = Path(sandbox_dir)
        self.sandbox_dir.mkdir(parents=True, exist_ok=True)
        self.work_dir = self.sandbox_dir / "work"
        self.work_dir.mkdir(exist_ok=True)
        self.logs_dir = self.sandbox_dir / "logs"
        self.logs_dir.mkdir(exist_ok=True)

    def execute_script(self, script_path: str, timeout: int = 60) -> SandboxResult:
        script = Path(script_path)
        if not script.exists():
            return SandboxResult(False, "", f"Script not found: {script_path}", -1)
        
        work_path = self.work_dir / f"sandbox_{os.getpid()}"
        work_path.mkdir(exist_ok=True)
        
        try:
            sandbox_script = work_path / script.name
            shutil.copy2(script, sandbox_script)
            
            if script.suffix == '.ps1':
                cmd = ["powershell", "-ExecutionPolicy", "Bypass", "-File", str(sandbox_script)]
            elif script.suffix == '.py':
                cmd = ["python", str(sandbox_script)]
            elif script.suffix == '.sh':
                cmd = ["bash", str(sandbox_script)]
            else:
                return SandboxResult(False, "", f"Unsupported script type: {script.suffix}", -1)
            
            result = subprocess.run(cmd, cwd=str(work_path), capture_output=True, text=True, timeout=timeout, env=self._get_restricted_env())
            
            sandbox_result = SandboxResult(success=result.returncode == 0, stdout=result.stdout, stderr=result.stderr, exit_code=result.exit_code)
            self._log_execution(script.name, sandbox_result)
            return sandbox_result
        except subprocess.TimeoutExpired:
            return SandboxResult(False, "", f"Execution timed out after {timeout}s", -2)
        except Exception as e:
            return SandboxResult(False, "", str(e), -3)
        finally:
            shutil.rmtree(work_path, ignore_errors=True)

    def execute_command(self, command: str, args: List[str] = None, timeout: int = 30) -> SandboxResult:
        work_path = self.work_dir / f"cmd_{os.getpid()}"
        work_path.mkdir(exist_ok=True)
        
        try:
            cmd = [command] + (args or [])
            result = subprocess.run(cmd, cwd=str(work_path), capture_output=True, text=True, timeout=timeout, env=self._get_restricted_env())
            return SandboxResult(success=result.returncode == 0, stdout=result.stdout, stderr=result.stderr, exit_code=result.exit_code)
        except subprocess.TimeoutExpired:
            return SandboxResult(False, "", f"Command timed out after {timeout}s", -2)
        except Exception as e:
            return SandboxResult(False, "", str(e), -3)
        finally:
            shutil.rmtree(work_path, ignore_errors=True)

    def _get_restricted_env(self) -> Dict[str, str]:
        env = os.environ.copy()
        env["PATH"] = "C:\\Windows\\System32;C:\\Windows"
        for key in ["PASSWORD", "SECRET", "API_KEY", "TOKEN"]:
            env.pop(key, None)
        return env

    def _log_execution(self, script_name: str, result: SandboxResult):
        log_entry = {"script": script_name, "success": result.success, "exit_code": result.exit_code}
        log_file = self.logs_dir / f"sandbox_{os.getpid()}.json"
        with open(log_file, 'w', encoding='utf-8') as f:
            json.dump(log_entry, f, indent=2)

    def get_stats(self) -> Dict[str, Any]:
        log_count = len(list(self.logs_dir.glob("*.json")))
        return {"sandbox_dir": str(self.sandbox_dir), "executions": log_count}

    def cleanup(self):
        shutil.rmtree(self.work_dir, ignore_errors=True)
        shutil.rmtree(self.logs_dir, ignore_errors=True)
        self.work_dir.mkdir(exist_ok=True)
        self.logs_dir.mkdir(exist_ok=True)