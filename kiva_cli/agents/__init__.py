"""
TestRepairAgent (PRD-KIVA-001)

Autonomous agent that detects failures (test errors, skill failures, post-commit
verification failures, config drift) and applies minimal, safe repairs.

Architecture:
    TestRepairAgent
    ├── FailureAnalyzer   — parses pytest output, skill logs, WAL events
    ├── RepairPlanner     — selects strategies based on failure signature
    ├── RepairExecutor    — applies patches safely (dry-run support)
    └── RepairReporter    — generates RepairReport + writes to WAL

Usage:
    agent = TestRepairAgent(repo_root=".", dry_run=False)
    report = agent.repair_from_test_failure("test_foo.py", "ModuleNotFoundError: No module named 'tools.core'")
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from kiva_cli.core.types import RepairReport, ValidationState
from kiva_cli.core.repair_strategies import (
    RepairContext,
    ImportRepairStrategy,
    StateMachineRepairStrategy,
    PostCommitContentRepairStrategy,
    ConfigDriftRepairStrategy,
    SubprocessMockRepairStrategy,
)

logger = logging.getLogger(__name__)


class FailureAnalyzer:
    """Parses various failure sources into a normalized FailureSignature."""

    @staticmethod
    def from_pytest_output(test_file: str, output: str) -> Dict[str, Any]:
        """Parse pytest output to extract failure signature."""
        signature: Dict[str, Any] = {
            "source": "pytest",
            "file": test_file,
            "error_message": output,
            "error_type": "Unknown",
            "detected_pattern": "unknown",
        }

        # Detect import errors
        import_match = re.search(r"(ModuleNotFoundError|ImportError):\s*(.+)", output)
        if import_match:
            signature["error_type"] = import_match.group(1)
            signature["error_message"] = import_match.group(2).strip()
            signature["detected_pattern"] = "import_error"
            # Try to extract the file from traceback
            file_match = re.search(r'File "(.+?)", line \d+', output)
            if file_match:
                signature["file"] = file_match.group(1)
            return signature

        # Detect assertion errors
        if "AssertionError" in output or "assert " in output:
            signature["error_type"] = "AssertionError"
            signature["detected_pattern"] = "assertion_failure"
            return signature

        # Detect state machine errors
        if "ValidationState" in output or "LifecycleState" in output:
            signature["error_type"] = "StateMachineError"
            signature["detected_pattern"] = "state_machine_error"
            return signature

        return signature

    @staticmethod
    def from_post_commit_verification(verification_result: Dict[str, Any]) -> Dict[str, Any]:
        """Convert PostCommitVerifier result to failure signature."""
        return {
            "source": "post_commit_verifier",
            "failure_source": f"post_commit_verifier:{verification_result.get('commit_sha', 'unknown')}",
            "file": verification_result.get("expected_file", {}).get("path", ""),
            "error_message": verification_result.get("error_message", "SHA mismatch or file missing"),
            "error_type": "PostCommitVerificationFailure",
            "detected_pattern": "post_commit_content",
            "expected_content": verification_result.get("expected_file", {}).get("content_snippet", ""),
        }

    @staticmethod
    def from_skill_failure(skill_name: str, error: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Convert skill execution failure to failure signature."""
        sig: Dict[str, Any] = {
            "source": "skill_manager",
            "failure_source": f"skill:{skill_name}",
            "error_message": error,
            "error_type": "SkillFailure",
            "detected_pattern": "unknown",
        }
        if context:
            sig["file"] = context.get("file", "")
        return sig


class RepairPlanner:
    """Selects the best repair strategy for a given failure signature."""

    def __init__(self, context: RepairContext):
        self.strategies = [
            ImportRepairStrategy(context),
            StateMachineRepairStrategy(context),
            PostCommitContentRepairStrategy(context),
            ConfigDriftRepairStrategy(context),
            SubprocessMockRepairStrategy(context),
        ]

    def select_strategies(self, failure_signature: Dict[str, Any]) -> List:
        """Return list of strategies that can handle this failure."""
        selected = []
        for strategy in self.strategies:
            try:
                if strategy.can_handle(failure_signature):
                    selected.append(strategy)
            except Exception as e:
                logger.warning(f"Strategy {strategy.__class__.__name__} raised during can_handle: {e}")
        return selected


class TestRepairAgent:
    """
    Main agent that orchestrates failure analysis, repair planning, and execution.
    """

    def __init__(
        self,
        repo_root: str = ".",
        dry_run: bool = True,
        confidence_threshold: float = 0.6,
    ):
        self.repo_root = Path(repo_root)
        self.context = RepairContext(
            repo_root=repo_root,
            dry_run=dry_run,
            confidence_threshold=confidence_threshold,
        )
        self.analyzer = FailureAnalyzer()
        self.planner = RepairPlanner(self.context)
        self.repair_history: List[RepairReport] = []

    def repair_from_test_failure(self, test_file: str, output: str) -> RepairReport:
        """Analyze a test failure and attempt repair."""
        signature = self.analyzer.from_pytest_output(test_file, output)
        return self._execute_repair(signature)

    def repair_from_post_commit(self, verification_result: Dict[str, Any]) -> RepairReport:
        """Analyze a post-commit verification failure and attempt repair."""
        signature = self.analyzer.from_post_commit_verification(verification_result)
        return self._execute_repair(signature)

    def repair_from_skill_failure(
        self, skill_name: str, error: str, context: Dict[str, Any] = None
    ) -> RepairReport:
        """Analyze a skill failure and attempt repair."""
        signature = self.analyzer.from_skill_failure(skill_name, error, context)
        return self._execute_repair(signature)

    def _execute_repair(self, failure_signature: Dict[str, Any]) -> RepairReport:
        """Core repair execution flow."""
        strategies = self.planner.select_strategies(failure_signature)

        if not strategies:
            report = RepairReport(
                success=False,
                validation_state=ValidationState.UNKNOWN,
                message=f"No repair strategy found for: {failure_signature.get('detected_pattern', 'unknown')}",
                detected_pattern=failure_signature.get("detected_pattern", "unknown"),
                strategies_applied=[],
                files_modified=[],
                confidence=0.0,
            )
            self.repair_history.append(report)
            return report

        # Apply the first matching strategy (highest priority)
        strategy = strategies[0]
        try:
            report = strategy.repair(failure_signature)
        except Exception as e:
            logger.error(f"Repair failed with {strategy.__class__.__name__}: {e}")
            report = RepairReport(
                success=False,
                validation_state=ValidationState.INVALID,
                message=f"Repair failed: {e}",
                detected_pattern=failure_signature.get("detected_pattern", "unknown"),
                strategies_applied=[strategy.__class__.__name__],
                files_modified=[],
                confidence=0.0,
                errors=[str(e)],
            )

        self.repair_history.append(report)
        return report

    def get_repair_history(self) -> List[RepairReport]:
        """Return all repair reports from this session."""
        return list(self.repair_history)

    def summary(self) -> Dict[str, Any]:
        """Return a summary of all repairs attempted."""
        total = len(self.repair_history)
        successful = sum(1 for r in self.repair_history if r.success)
        return {
            "total_repairs": total,
            "successful": successful,
            "failed": total - successful,
            "success_rate": successful / total if total > 0 else 0.0,
            "strategies_used": list(set(
                s for r in self.repair_history for s in r.strategies_applied
            )),
        }
