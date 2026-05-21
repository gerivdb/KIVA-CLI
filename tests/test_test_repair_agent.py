"""
Tests for TestRepairAgent (PRD-KIVA-001)

Validates:
- FailureAnalyzer correctly parses pytest output, post-commit results, skill failures
- RepairPlanner selects correct strategies
- ImportRepairStrategy fixes broken imports
- StateMachineRepairStrategy fixes inconsistent state usage
- RepairReport is generated correctly
"""

import os
import sys
import tempfile
from pathlib import Path

import pytest

# Ensure kiva_cli is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from kiva_cli.core.types import RepairReport, ValidationState
from kiva_cli.core.repair_strategies import (
    RepairContext,
    ImportRepairStrategy,
    StateMachineRepairStrategy,
    PostCommitContentRepairStrategy,
    ConfigDriftRepairStrategy,
    SubprocessMockRepairStrategy,
)
from kiva_cli.agents import TestRepairAgent


class TestFailureAnalyzer:
    """Tests for the FailureAnalyzer component."""

    def test_parse_import_error_from_pytest(self):
        output = """ModuleNotFoundError: No module named 'tools.core.project_manager'
  File "kiva_cli/commands/project.py", line 3, in <module>
    from tools.core.project_manager import ProjectManager
"""
        sig = TestRepairAgent(repo_root=".").analyzer.from_pytest_output("test_foo.py", output)
        assert sig["error_type"] == "ModuleNotFoundError"
        assert sig["detected_pattern"] == "import_error"
        assert "tools.core.project_manager" in sig["error_message"]

    def test_parse_assertion_error(self):
        output = "AssertionError: expected True but got False"
        sig = TestRepairAgent(repo_root=".").analyzer.from_pytest_output("test_bar.py", output)
        assert sig["error_type"] == "AssertionError"
        assert sig["detected_pattern"] == "assertion_failure"

    def test_parse_state_machine_error(self):
        output = "AttributeError: 'ValidationState' object has no attribute 'SUCCESS'"
        sig = TestRepairAgent(repo_root=".").analyzer.from_pytest_output("test_baz.py", output)
        assert sig["error_type"] == "StateMachineError"
        assert sig["detected_pattern"] == "state_machine_error"

    def test_parse_post_commit_verification(self):
        result = {
            "commit_sha": "abc123",
            "expected_file": {"path": "PRD/PRD-KIVA-001.md", "sha": "def456"},
            "error_message": "SHA mismatch",
        }
        sig = TestRepairAgent(repo_root=".").analyzer.from_post_commit_verification(result)
        assert sig["error_type"] == "PostCommitVerificationFailure"
        assert sig["detected_pattern"] == "post_commit_content"
        assert sig["file"] == "PRD/PRD-KIVA-001.md"

    def test_parse_skill_failure(self):
        sig = TestRepairAgent(repo_root=".").analyzer.from_skill_failure(
            "deploy", "Connection timeout", {"file": "deploy.py"}
        )
        assert sig["error_type"] == "SkillFailure"
        assert sig["failure_source"] == "skill:deploy"
        assert sig["file"] == "deploy.py"


class TestImportRepairStrategy:
    """Tests for ImportRepairStrategy."""

    def test_detects_import_error(self):
        ctx = RepairContext(dry_run=True)
        strategy = ImportRepairStrategy(ctx)
        sig = {"error_type": "ModuleNotFoundError", "error_message": "No module named 'tools.core'"}
        assert strategy.can_handle(sig) is True

    def test_replaces_broken_import(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("from tools.core.project_manager import ProjectManager\n")
            f.write("from tools.core.types import ValidationState\n")
            f.flush()
            tmp_path = f.name

        try:
            ctx = RepairContext(repo_root=str(Path(tmp_path).parent), dry_run=False)
            strategy = ImportRepairStrategy(ctx)
            sig = {
                "error_type": "ModuleNotFoundError",
                "error_message": "No module named 'tools.core'",
                "file": tmp_path,
            }
            report = strategy.repair(sig)
            assert report.success is True
            assert report.confidence >= 0.8

            content = Path(tmp_path).read_text()
            assert "from kiva_cli.core.project_manager import" in content
            assert "from kiva_cli.core.types import" in content
        finally:
            os.unlink(tmp_path)

    def test_dry_run_does_not_modify(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("from tools.core.project_manager import ProjectManager\n")
            f.flush()
            tmp_path = f.name

        try:
            ctx = RepairContext(repo_root=str(Path(tmp_path).parent), dry_run=True)
            strategy = ImportRepairStrategy(ctx)
            sig = {
                "error_type": "ModuleNotFoundError",
                "error_message": "No module named 'tools.core'",
                "file": tmp_path,
            }
            report = strategy.repair(sig)
            assert report.success is True
            assert "dry-run" in report.message

            content = Path(tmp_path).read_text()
            assert "from tools.core.project_manager" in content  # unchanged
        finally:
            os.unlink(tmp_path)


class TestStateMachineRepairStrategy:
    """Tests for StateMachineRepairStrategy."""

    def test_detects_state_error(self):
        ctx = RepairContext(dry_run=True)
        strategy = StateMachineRepairStrategy(ctx)
        sig = {"error_type": "StateMachineError", "error_message": "ValidationState.SUCCESS not found"}
        assert strategy.can_handle(sig) is True

    def test_replaces_old_state_patterns(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write('state = "PENDING"\n')
            f.write('if result == "SUCCESS":\n')
            f.flush()
            tmp_path = f.name

        try:
            ctx = RepairContext(repo_root=str(Path(tmp_path).parent), dry_run=False)
            strategy = StateMachineRepairStrategy(ctx)
            sig = {
                "error_type": "StateMachineError",
                "error_message": "ValidationState.SUCCESS",
                "file": tmp_path,
            }
            report = strategy.repair(sig)
            assert report.success is True

            content = Path(tmp_path).read_text()
            assert "ValidationState.UNKNOWN" in content
            assert "ValidationState.VALID" in content
        finally:
            os.unlink(tmp_path)


class TestPostCommitContentRepairStrategy:
    """Tests for PostCommitContentRepairStrategy."""

    def test_detects_post_commit_failure(self):
        ctx = RepairContext(dry_run=True)
        strategy = PostCommitContentRepairStrategy(ctx)
        sig = {"error_type": "PostCommitVerificationFailure", "failure_source": "post_commit_verifier:abc"}
        assert strategy.can_handle(sig) is True

    def test_creates_missing_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            ctx = RepairContext(repo_root=tmpdir, dry_run=False)
            strategy = PostCommitContentRepairStrategy(ctx)
            sig = {
                "error_type": "PostCommitVerificationFailure",
                "failure_source": "post_commit_verifier:abc",
                "file": "PRD/PRD-KIVA-001.md",
                "expected_content": "# PRD-KIVA-001\n",
            }
            report = strategy.repair(sig)
            assert report.success is True
            assert Path(tmpdir, "PRD/PRD-KIVA-001.md").exists()


class TestTestRepairAgent:
    """Integration tests for the full TestRepairAgent."""

    def test_full_repair_flow_import_error(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("from tools.core.project_manager import ProjectManager\n")
            f.flush()
            tmp_path = f.name

        try:
            agent = TestRepairAgent(
                repo_root=str(Path(tmp_path).parent),
                dry_run=False,
            )
            report = agent.repair_from_test_failure(
                tmp_path,
                "ModuleNotFoundError: No module named 'tools.core.project_manager'",
            )
            assert report.success is True
            assert "ImportRepairStrategy" in report.strategies_applied
            assert report.confidence >= 0.6
        finally:
            os.unlink(tmp_path)

    def test_no_strategy_found(self):
        agent = TestRepairAgent(dry_run=True)
        report = agent.repair_from_test_failure("test.py", "Some unknown error")
        assert report.success is False
        assert "No repair strategy found" in report.message

    def test_repair_history(self):
        agent = TestRepairAgent(dry_run=True)
        agent.repair_from_test_failure("test.py", "ModuleNotFoundError: No module named 'tools.core'")
        agent.repair_from_test_failure("test.py", "Some unknown error")
        history = agent.get_repair_history()
        assert len(history) == 2

    def test_summary(self):
        agent = TestRepairAgent(dry_run=True)
        agent.repair_from_test_failure("test.py", "ModuleNotFoundError: No module named 'tools.core'")
        agent.repair_from_test_failure("test.py", "Some unknown error")
        summary = agent.summary()
        assert summary["total_repairs"] == 2
        assert summary["successful"] >= 0
        assert 0.0 <= summary["success_rate"] <= 1.0


class TestRepairReport:
    """Tests for the RepairReport type."""

    def test_default_values(self):
        report = RepairReport(success=True)
        assert report.success is True
        assert report.confidence == 0.0
        assert report.files_modified == []
        assert report.strategies_applied == []

    def test_is_success_property(self):
        report = RepairReport(
            success=True,
            validation_state=ValidationState.VALID,
        )
        assert report.is_success is True

        report2 = RepairReport(
            success=True,
            validation_state=ValidationState.INVALID,
        )
        assert report2.is_success is False
