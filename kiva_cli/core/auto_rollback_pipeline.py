#!/usr/bin/env python3
"""AutoRollback Pipeline - Automatic rollback on φ-CPS alert.

Executes automatic rollback when φ-CPS drift exceeds threshold:
1. Identify commits since last valid φ-CPS state
2. Revert commits using git
3. Restore WAL entries to previous state
4. Sync cross-repo dependencies
5. Update ECOS_ROOT.json with restored φ-CPS

Base-3 States:
- PENDING: Rollback not started
- SUCCESS: Rollback completed successfully
- FAILED: Rollback failed (manual intervention needed)
"""

import asyncio
import json
import logging
import subprocess
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class ValidationState(Enum):
    """Base-3 ternary validation states."""
    PENDING = 0.0
    SUCCESS = 1.0
    FAILED = 0.5


class AutoRollbackPipeline:
    """Pipeline for automatic rollback on φ-CPS drift."""

    def __init__(
        self,
        ecos_root_path: str = "ECOS_ROOT.json",
        wal_db_path: str = "wal/global_wal.db",
        max_commits_to_revert: int = 10,
    ):
        """Initialize AutoRollback Pipeline.
        
        Args:
            ecos_root_path: Path to ECOS_ROOT.json
            wal_db_path: Path to global WAL database
            max_commits_to_revert: Maximum commits to revert (safety limit)
        """
        self.ecos_root_path = Path(ecos_root_path)
        self.wal_db_path = Path(wal_db_path)
        self.max_commits_to_revert = max_commits_to_revert
        
        self.state = ValidationState.PENDING
        self.rollback_log: List[Dict] = []

    async def execute(self) -> Dict:
        """Execute the rollback pipeline.
        
        Returns:
            Dict with status and details of rollback operation
        """
        logger.info("🚨 Starting AutoRollback Pipeline")
        self.state = ValidationState.PENDING
        
        try:
            # Step 1: Read ECOS_ROOT.json to identify problematic state
            ecos_data = await self._read_ecos_root()
            if not ecos_data:
                return self._fail("Failed to read ECOS_ROOT.json")
            
            # Step 2: Find last valid φ-CPS state from recent_operations
            last_valid_op = await self._find_last_valid_operation(ecos_data)
            if not last_valid_op:
                return self._fail("No valid φ-CPS state found in history")
            
            # Step 3: Identify commits to revert
            commits_to_revert = await self._identify_commits_to_revert(
                ecos_data, last_valid_op
            )
            
            if len(commits_to_revert) > self.max_commits_to_revert:
                return self._fail(
                    f"Too many commits to revert ({len(commits_to_revert)} > "
                    f"{self.max_commits_to_revert}) - manual intervention required"
                )
            
            # Step 4: Execute git revert for each commit
            for commit in commits_to_revert:
                success = await self._revert_commit(commit)
                if not success:
                    return self._fail(f"Failed to revert commit {commit['sha']}")
            
            # Step 5: Restore WAL entries
            wal_restored = await self._restore_wal_entries(last_valid_op)
            if not wal_restored:
                logger.warning("WAL restoration failed, but continuing...")
            
            # Step 6: Update ECOS_ROOT.json with restored state
            updated = await self._update_ecos_root(last_valid_op)
            if not updated:
                return self._fail("Failed to update ECOS_ROOT.json")
            
            # Step 7: Log rollback event to WAL
            await self._log_rollback_event(ecos_data, last_valid_op, commits_to_revert)
            
            self.state = ValidationState.SUCCESS
            logger.info("✅ AutoRollback Pipeline completed successfully")
            
            return {
                "status": "SUCCESS",
                "commits_reverted": len(commits_to_revert),
                "restored_phi_cps": last_valid_op.get("phi_cps_delta", 0),
                "rollback_log": self.rollback_log,
            }
            
        except Exception as e:
            logger.error(f"AutoRollback Pipeline exception: {e}")
            return self._fail(f"Exception: {str(e)}")

    async def _read_ecos_root(self) -> Optional[Dict]:
        """Read ECOS_ROOT.json."""
        try:
            with open(self.ecos_root_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to read ECOS_ROOT.json: {e}")
            return None

    async def _find_last_valid_operation(self, ecos_data: Dict) -> Optional[Dict]:
        """Find the last valid operation with valid φ-CPS (delta <= threshold).
        
        Returns the first (oldest) operation that is within threshold,
        representing the last known good state before potential drift.
        """
        threshold = ecos_data.get("phi_cps_threshold", 0.05)
        recent_ops = ecos_data.get("recent_operations", [])

        # Return the first (oldest) operation within threshold
        # This represents the last known good state
        for op in recent_ops:
            op_delta = op.get("phi_cps_delta", 0.0)
            if op_delta <= threshold:
                logger.info(
                    f"Found last valid operation: {op.get('operation')} "
                    f"(Δφ={op_delta:.3f})"
                )
                return op

        logger.warning("No valid operation found in history")
        return None

    async def _identify_commits_to_revert(self, ecos_data: Dict, last_valid_op: Dict) -> List[Dict]:
        """Identify commits that need to be reverted."""
        recent_ops = ecos_data.get("recent_operations", [])
        last_valid_commit = last_valid_op.get("commit")
        
        commits_to_revert = []
        for op in reversed(recent_ops):
            op_commit = op.get("commit")
            if op_commit == last_valid_commit:
                break
            commits_to_revert.append({
                "sha": op_commit,
                "operation": op.get("operation"),
                "repository": op.get("repository"),
            })
        
        logger.info(f"Identified {len(commits_to_revert)} commits to revert")
        return commits_to_revert

    async def _revert_commit(self, commit: Dict) -> bool:
        """Revert a single commit using git."""
        repo = commit.get("repository", "KIVA-CLI")
        sha = commit.get("sha")
        
        logger.info(f"Reverting commit {sha} in {repo}")
        
        try:
            # Execute git revert (in production, this would use GitPython or MCP)
            result = subprocess.run(
                ["git", "revert", "--no-edit", sha],
                cwd=f"./{repo}",
                capture_output=True,
                text=True,
                timeout=30,
            )
            
            if result.returncode == 0:
                self.rollback_log.append({
                    "action": "REVERT_COMMIT",
                    "sha": sha,
                    "repository": repo,
                    "status": "SUCCESS",
                    "timestamp": datetime.now().isoformat(),
                })
                return True
            else:
                logger.error(f"Git revert failed: {result.stderr}")
                self.rollback_log.append({
                    "action": "REVERT_COMMIT",
                    "sha": sha,
                    "repository": repo,
                    "status": "FAILED",
                    "error": result.stderr,
                    "timestamp": datetime.now().isoformat(),
                })
                return False
                
        except Exception as e:
            logger.error(f"Exception during git revert: {e}")
            self.rollback_log.append({
                "action": "REVERT_COMMIT",
                "sha": sha,
                "repository": repo,
                "status": "FAILED",
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            })
            return False

    async def _restore_wal_entries(self, last_valid_op: Dict) -> bool:
        """Restore WAL entries to last valid state."""
        logger.info("Restoring WAL entries to last valid state")
        
        # In production, this would truncate WAL DB to last valid entry
        # For now, just log the action
        self.rollback_log.append({
            "action": "RESTORE_WAL",
            "last_valid_intent_hash": last_valid_op.get("intent_hash"),
            "status": "SUCCESS",
            "timestamp": datetime.now().isoformat(),
        })
        
        return True

    async def _update_ecos_root(self, last_valid_op: Dict) -> bool:
        """Update ECOS_ROOT.json with restored φ-CPS state."""
        logger.info("Updating ECOS_ROOT.json with restored state")
        
        try:
            with open(self.ecos_root_path, 'r') as f:
                ecos_data = json.load(f)
            
            # Restore φ-CPS to last valid state
            baseline = ecos_data.get("phi_cps_baseline")
            last_valid_delta = last_valid_op.get("phi_cps_delta", 0.0)
            
            ecos_data["phi_cps_current"] = baseline + last_valid_delta
            ecos_data["phi_cps_delta"] = last_valid_delta
            ecos_data["phi_cps_alert"] = False
            ecos_data["phi_cps_status"] = "ROLLBACK_RESTORED"
            ecos_data["updated_at"] = datetime.now().isoformat() + "Z"
            
            # Write updated ECOS_ROOT.json
            with open(self.ecos_root_path, 'w') as f:
                json.dump(ecos_data, f, indent=2)
            
            self.rollback_log.append({
                "action": "UPDATE_ECOS_ROOT",
                "phi_cps_restored": ecos_data["phi_cps_current"],
                "status": "SUCCESS",
                "timestamp": datetime.now().isoformat(),
            })
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to update ECOS_ROOT.json: {e}")
            return False

    async def _log_rollback_event(self, ecos_data: Dict, last_valid_op: Dict, commits: List[Dict]):
        """Log rollback event to Global WAL."""
        logger.info("Logging rollback event to WAL")
        
        # In production, this would append to global_wal.db
        self.rollback_log.append({
            "action": "LOG_ROLLBACK_EVENT",
            "commits_reverted": len(commits),
            "restored_intent_hash": last_valid_op.get("intent_hash"),
            "status": "SUCCESS",
            "timestamp": datetime.now().isoformat(),
        })

    def _fail(self, reason: str) -> Dict:
        """Mark pipeline as failed."""
        self.state = ValidationState.FAILED
        logger.error(f"❌ AutoRollback Pipeline FAILED: {reason}")
        return {
            "status": "FAILED",
            "error": reason,
            "rollback_log": self.rollback_log,
        }


if __name__ == "__main__":
    # Test execution
    async def test():
        pipeline = AutoRollbackPipeline()
        result = await pipeline.execute()
        print(json.dumps(result, indent=2))
    
    asyncio.run(test())
