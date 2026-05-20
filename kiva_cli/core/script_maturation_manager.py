#!/usr/bin/env python3
"""
Script Maturation Manager - KIVA CLI

Manages progressive script maturation from Skeleton to Production level.
Handles queue management, worker orchestration, and script promotion.
"""

import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


class ScriptMaturationManager:
    """Manages script maturation queue and promotion logic."""

    MATURITY_LEVELS = {
        0: "Skeleton",
        1: "Stub",
        2: "Prototype",
        3: "Functional",
        4: "Production"
    }

    def __init__(self, queue_dir: Optional[str] = None):
        if queue_dir is None:
            queue_dir = "C:\\DevTools\\data\\maturation-queue"
        self.queue_dir = Path(queue_dir)
        self.queue_file = self.queue_dir / "queue.json"
        self.worker_pid_file = self.queue_dir / "worker.pid"
        self.log_file = self.queue_dir / "maturation.log"
        self._ensure_queue_dir()

    def _ensure_queue_dir(self):
        """Ensure queue directory exists."""
        self.queue_dir.mkdir(parents=True, exist_ok=True)
        if not self.queue_file.exists():
            self._save_queue_data({
                "queue": [],
                "processing": None,
                "completed": []
            })

    def _load_queue_data(self) -> Dict[str, Any]:
        """Load queue data from JSON file."""
        if self.queue_file.exists():
            try:
                with open(self.queue_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                pass
        return {"queue": [], "processing": None, "completed": []}

    def _save_queue_data(self, data: Dict[str, Any]):
        """Save queue data to JSON file."""
        with open(self.queue_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def _log(self, message: str, level: str = "INFO"):
        """Log message to file and console."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"{timestamp} [{level}] {message}\n"
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(log_entry)
        print(f"[{level}] {message}")

    def get_script_level(self, script_name: str, scripts_path: str = "C:\\DevTools\\bin") -> int:
        """Determine current maturity level of a script."""
        script_path = Path(scripts_path) / script_name
        if not script_path.exists():
            return 0

        try:
            content = script_path.read_text(encoding='utf-8')
        except IOError:
            return 0

        level = 0
        if len(content) > 50:
            level = 1
        if "param(" in content and "Write-Host" in content:
            level = 2
        if "try {" in content and "catch {" in content and len(content) > 500:
            level = 3
        if "Export-ModuleMember" in content or (Path(scripts_path).parent / "tests" / f"{script_name}.tests.ps1").exists():
            level = 4

        return level

    def add_to_queue(self, script_name: str, target_level: int = 4) -> bool:
        """Add script to maturation queue."""
        queue_data = self._load_queue_data()

        # Check if already in queue
        for item in queue_data["queue"]:
            if item["script"] == script_name:
                self._log(f"Script already in queue: {script_name}", "WARN")
                return False

        queue_data["queue"].append({
            "script": script_name,
            "targetLevel": target_level,
            "addedAt": datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "status": "pending"
        })

        self._save_queue_data(queue_data)
        self._log(f"Added to queue: {script_name} -> Level {target_level}", "SUCCESS")
        return True

    def remove_from_queue(self, script_name: str) -> bool:
        """Remove script from queue."""
        queue_data = self._load_queue_data()
        original_count = len(queue_data["queue"])
        queue_data["queue"] = [
            item for item in queue_data["queue"]
            if item["script"] != script_name
        ]

        if len(queue_data["queue"]) < original_count:
            self._save_queue_data(queue_data)
            self._log(f"Removed from queue: {script_name}")
            return True
        return False

    def promote_script(self, script_name: str, target_level: int, scripts_path: str = "C:\\DevTools\\bin") -> bool:
        """Promote script to target maturity level."""
        script_path = Path(scripts_path) / script_name
        if not script_path.exists():
            self._log(f"Script not found: {script_name}", "ERROR")
            return False

        current_level = self.get_script_level(script_name, scripts_path)

        if current_level >= target_level:
            self._log(f"{script_name} already at level {current_level}", "INFO")
            return True

        self._log(f"Promoting {script_name} from level {current_level} to {target_level}...")

        try:
            content = script_path.read_text(encoding='utf-8')
            new_content = content

            # Level 2: Add param block
            if current_level < 2 and target_level >= 2:
                if not content.strip().startswith("param("):
                    param_block = "param(\n    [Parameter(Mandatory=$false)]\n    [string]$ParamName = \"\"\n)\n\n"
                    new_content = param_block + new_content

            # Level 3: Add error handling
            if current_level < 3 and target_level >= 3:
                new_content = f"$ErrorActionPreference = \"Stop\"\n\ntry {{\n{new_content}\n}} catch {{\n    Write-Error $_.Exception.Message\n    exit 1\n}}\n"

            # Level 4: Add Export-ModuleMember
            if current_level < 4 and target_level >= 4:
                if "Export-ModuleMember" not in new_content:
                    new_content += "\n\n# Production Level\nExport-ModuleMember -Function * -ErrorAction SilentlyContinue"

            script_path.write_text(new_content, encoding='utf-8')
            self._log(f"Promoted {script_name} to level {target_level}", "SUCCESS")
            return True

        except Exception as e:
            self._log(f"Failed to promote {script_name}: {e}", "ERROR")
            return False

    def process_queue(self, scripts_path: str = "C:\\DevTools\\bin") -> bool:
        """Process next item in queue."""
        queue_data = self._load_queue_data()

        if not queue_data["queue"]:
            self._log("Queue empty, nothing to process", "INFO")
            return False

        item = queue_data["queue"][0]
        script_name = item["script"]
        target_level = item["targetLevel"]

        self._log(f"Processing: {script_name}")

        # Move from queue to processing
        queue_data["processing"] = item
        queue_data["queue"] = queue_data["queue"][1:]
        self._save_queue_data(queue_data)

        # Promote script
        success = self.promote_script(script_name, target_level, scripts_path)

        # Update completed or re-queue
        queue_data = self._load_queue_data()
        if success:
            queue_data["completed"].append({
                "script": script_name,
                "targetLevel": target_level,
                "completedAt": datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
                "status": "success"
            })
        else:
            item["status"] = "failed"
            queue_data["queue"].insert(0, item)

        queue_data["processing"] = None
        self._save_queue_data(queue_data)

        return success

    def get_worker_status(self) -> Dict[str, Any]:
        """Get worker process status."""
        if self.worker_pid_file.exists():
            try:
                pid = int(self.worker_pid_file.read_text().strip())
                # Check if process is running (Windows)
                result = subprocess.run(
                    ["tasklist", "/FI", f"PID eq {pid}", "/NH"],
                    capture_output=True, text=True
                )
                if str(pid) in result.stdout:
                    return {"running": True, "pid": pid}
            except (ValueError, IOError, subprocess.SubprocessError):
                pass
        return {"running": False, "pid": None}

    def start_worker(self) -> bool:
        """Start background maturation worker."""
        worker_status = self.get_worker_status()
        if worker_status["running"]:
            self._log(f"Worker already running (PID: {worker_status['pid']})", "WARN")
            return False

        worker_script = Path(__file__).parent.parent.parent / "bin" / "script-maturation-queue.ps1"
        if not worker_script.exists():
            self._log("Worker script not found", "ERROR")
            return False

        try:
            proc = subprocess.Popen(
                ["powershell", "-ExecutionPolicy", "Bypass", "-File", str(worker_script), "-RunOnce"],
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            self.worker_pid_file.write_text(str(proc.pid))
            self._log(f"Worker started (PID: {proc.pid})", "SUCCESS")
            return True
        except Exception as e:
            self._log(f"Failed to start worker: {e}", "ERROR")
            return False

    def stop_worker(self) -> bool:
        """Stop background maturation worker."""
        worker_status = self.get_worker_status()
        if not worker_status["running"]:
            self._log("Worker not running", "WARN")
            return False

        try:
            subprocess.run(
                ["taskkill", "/F", "/PID", str(worker_status["pid"])],
                capture_output=True
            )
            self.worker_pid_file.unlink(missing_ok=True)
            self._log("Worker stopped", "SUCCESS")
            return True
        except Exception as e:
            self._log(f"Failed to stop worker: {e}", "ERROR")
            return False

    def get_queue_status(self) -> Dict[str, Any]:
        """Get current queue status."""
        queue_data = self._load_queue_data()
        worker_status = self.get_worker_status()

        return {
            "worker": worker_status,
            "queue_count": len(queue_data["queue"]),
            "processing": queue_data["processing"],
            "completed_count": len(queue_data["completed"]),
            "pending": queue_data["queue"],
            "completed": queue_data["completed"][-5:] if queue_data["completed"] else []
        }
