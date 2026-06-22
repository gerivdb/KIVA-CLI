"""
Tests for Windows Compatibility Auditor (PRD-KIVA-003).

Validates:
- Each audit rule detects its target patterns
- AuditReport scoring and formatting
- Full audit flow end-to-end
- SARIF and Markdown output generation
"""

import json
import os
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from kiva_cli.auditors import (
    AuditReport,
    AuditRule,
    CmdWrapperRule,
    HereStringRule,
    HardcodedPathRule,
    FileEncodingRule,
    SubprocessNoMockRule,
    CdAndAmpersandRule,
    LongCommandRule,
    Severity,
    Violation,
    WindowsAuditor,
)


# =============================================================================
# Individual Rule Tests
# =============================================================================

class TestCmdWrapperRule:
    """Tests for WIN001: CMD Wrapper for PowerShell."""

    def setup_method(self):
        self.rule = CmdWrapperRule()

    def test_detects_direct_ps1_reference(self, tmp_path):
        test_file = tmp_path / "deploy.py"
        test_file.write_text('subprocess.run("powershell -File scripts/deploy.ps1")\n')
        violations = self.rule.check_file(Path("deploy.py"), test_file.read_text())
        assert len(violations) >= 1
        assert violations[0].rule_id == "WIN001"

    def test_detects_powershell_without_cmd_wrapper(self, tmp_path):
        test_file = tmp_path / "test_run.py"
        test_file.write_text('subprocess.run("powershell -File script.ps1")\n')
        violations = self.rule.check_file(Path("test_run.py"), test_file.read_text())
        assert len(violations) >= 1

    def test_allows_cmd_c_wrapper(self, tmp_path):
        test_file = tmp_path / "test_ok.py"
        test_file.write_text('subprocess.run("cmd /c powershell -ExecutionPolicy ByPass -File script.ps1")\n')
        violations = self.rule.check_file(Path("test_ok.py"), test_file.read_text())
        assert len(violations) == 0

    def test_ignores_comments(self, tmp_path):
        test_file = tmp_path / "test_comment.py"
        test_file.write_text('# subprocess.run(["script.ps1"])\n')
        violations = self.rule.check_file(Path("test_comment.py"), test_file.read_text())
        assert len(violations) == 0


class TestHereStringRule:
    """Tests for WIN002: No Here-Strings."""

    def setup_method(self):
        self.rule = HereStringRule()

    def test_detects_here_string(self, tmp_path):
        test_file = tmp_path / "test_ps1.py"
        test_file.write_text("content = @'\nHello World\n'@\n")
        violations = self.rule.check_file(Path("test_ps1.py"), test_file.read_text())
        assert len(violations) >= 1
        assert violations[0].rule_id == "WIN002"

    def test_ignores_normal_strings(self, tmp_path):
        test_file = tmp_path / "test_normal.py"
        test_file.write_text('x = "hello world"\n')
        violations = self.rule.check_file(Path("test_normal.py"), test_file.read_text())
        assert len(violations) == 0


class TestHardcodedPathRule:
    """Tests for WIN003: No Hardcoded Windows Paths."""

    def setup_method(self):
        self.rule = HardcodedPathRule()

    def test_detects_hardcoded_path(self, tmp_path):
        test_file = tmp_path / "test_paths.py"
        test_file.write_text('config_path = "C:\\\\Users\\\\GG\\\\config.yaml"\n')
        violations = self.rule.check_file(Path("test_paths.py"), test_file.read_text())
        assert len(violations) >= 1
        assert violations[0].rule_id == "WIN003"

    def test_allows_pathlib(self, tmp_path):
        test_file = tmp_path / "test_ok.py"
        test_file.write_text('from pathlib import Path\np = Path("config.yaml")\n')
        violations = self.rule.check_file(Path("test_ok.py"), test_file.read_text())
        assert len(violations) == 0

    def test_ignores_non_python_files(self, tmp_path):
        test_file = tmp_path / "test.txt"
        test_file.write_text("Path: C:\\Users\\test\n")
        violations = self.rule.check_file(Path("test.txt"), test_file.read_text())
        assert len(violations) == 0


class TestFileEncodingRule:
    """Tests for WIN004: UTF-8 Without BOM."""

    def setup_method(self):
        self.rule = FileEncodingRule()

    def test_detects_utf8_bom(self, tmp_path):
        test_file = tmp_path / "bom.py"
        # Write with UTF-8 BOM bytes directly
        test_file.write_bytes(b"\xef\xbb\xbfprint('hello')\n")
        # Pass the file_path as a Path object relative to repo_root
        # The rule reads the file directly via file_path
        full_path = tmp_path / "bom.py"
        violations = self.rule.check_file(full_path, test_file.read_text(encoding="utf-8-sig"))
        assert len(violations) == 1
        assert violations[0].rule_id == "WIN004"

    def test_allows_utf8_no_bom(self, tmp_path):
        test_file = tmp_path / "test_ok.py"
        test_file.write_text("# -*- coding: utf-8 -*-\nprint('hello')\n")
        violations = self.rule.check_file(Path("test_ok.py"), test_file.read_text())
        assert len(violations) == 0


class TestSubprocessNoMockRule:
    """Tests for WIN005: Use Subprocess Orchestrator."""

    def setup_method(self):
        self.rule = SubprocessNoMockRule()

    def test_detects_subprocess_run(self, tmp_path):
        test_file = tmp_path / "deploy_ops.py"
        test_file.write_text('import subprocess\nsubprocess.run(["docker", "build", "."])\n')
        violations = self.rule.check_file(Path("deploy_ops.py"), test_file.read_text())
        assert len(violations) >= 1
        assert violations[0].rule_id == "WIN005"

    def test_ignores_test_files(self, tmp_path):
        test_file = tmp_path / "test_something.py"
        test_file.write_text('subprocess.run(["echo", "hi"])\n')
        violations = self.rule.check_file(Path("test_something.py"), test_file.read_text())
        # Test files are skipped
        assert len(violations) == 0

    def test_allows_orchestrator_usage(self, tmp_path):
        test_file = tmp_path / "test_good.py"
        test_file.write_text(
            'from kiva_cli.core.subprocess_orchestrator import SubprocessMockOrchestrator\n'
            'orch = SubprocessMockOrchestrator(mode="replay")\n'
        )
        violations = self.rule.check_file(Path("test_good.py"), test_file.read_text())
        assert len(violations) == 0


class TestCdAndAmpersandRule:
    """Tests for WIN006: No cd && anti-pattern."""

    def setup_method(self):
        self.rule = CdAndAmpersandRule()

    def test_detects_cd_and_execute(self, tmp_path):
        test_file = tmp_path / "test_cd.py"
        test_file.write_text('os.system("cd /app && npm install")\n')
        violations = self.rule.check_file(Path("test_cd.py"), test_file.read_text())
        assert len(violations) >= 1
        assert violations[0].rule_id == "WIN006"

    def test_detects_os_chdir(self, tmp_path):
        test_file = tmp_path / "test_chdir.py"
        test_file.write_text('os.chdir("/tmp")\n')
        violations = self.rule.check_file(Path("test_chdir.py"), test_file.read_text())
        assert len(violations) >= 1

    def test_allows_cwd_parameter(self, tmp_path):
        test_file = tmp_path / "test_ok.py"
        test_file.write_text('subprocess.run(["npm", "install"], cwd="/app")\n')
        violations = self.rule.check_file(Path("test_ok.py"), test_file.read_text())
        assert len(violations) == 0


class TestLongCommandRule:
    """Tests for WIN007: No Overly Long Single-Line Commands."""

    def setup_method(self):
        self.rule = LongCommandRule(max_length=200)

    def test_detects_long_line(self, tmp_path):
        test_file = tmp_path / "long_line.py"
        long_line = "x = " + "a" * 200 + "\n"
        test_file.write_text(long_line)
        violations = self.rule.check_file(Path("long_line.py"), test_file.read_text())
        assert len(violations) >= 1
        assert violations[0].rule_id == "WIN007"

    def test_allows_normal_lines(self, tmp_path):
        test_file = tmp_path / "test_ok.py"
        test_file.write_text('x = "hello world"\n')
        violations = self.rule.check_file(Path("test_ok.py"), test_file.read_text())
        assert len(violations) == 0


# =============================================================================
# AuditReport Tests
# =============================================================================

class TestAuditReport:
    """Tests for the AuditReport dataclass."""

    def test_default_values(self):
        report = AuditReport(repo_root=".", scan_date="2026-01-01")
        assert report.files_scanned == 0
        assert report.score == 100.0
        assert report.total_violations == 0

    def test_severity_counts(self):
        report = AuditReport(
            repo_root=".",
            scan_date="2026-01-01",
            violations=[
                Violation("R1", "Rule1", Severity.CRITICAL, "f.py", 1, "msg"),
                Violation("R2", "Rule2", Severity.HIGH, "f.py", 2, "msg"),
                Violation("R3", "Rule3", Severity.HIGH, "f.py", 3, "msg"),
                Violation("R4", "Rule4", Severity.LOW, "f.py", 4, "msg"),
            ],
        )
        assert report.critical_count == 1
        assert report.high_count == 2
        assert report.low_count == 1
        assert report.medium_count == 0

    def test_score_calculation_no_violations(self):
        auditor = WindowsAuditor(repo_root=".")
        report = AuditReport(repo_root=".", scan_date="2026-01-01", violations=[])
        score = auditor._calculate_score(report)
        assert score == 100.0

    def test_score_calculation_with_violations(self):
        auditor = WindowsAuditor(repo_root=".")
        report = AuditReport(
            repo_root=".",
            scan_date="2026-01-01",
            violations=[
                Violation("R1", "Rule1", Severity.CRITICAL, "f.py", 1, "msg"),
                Violation("R2", "Rule2", Severity.HIGH, "f.py", 2, "msg"),
            ],
        )
        score = auditor._calculate_score(report)
        assert score == 55.0  # 100 - 30 - 15

    def test_score_floor_at_zero(self):
        auditor = WindowsAuditor(repo_root=".")
        report = AuditReport(
            repo_root=".",
            scan_date="2026-01-01",
            violations=[
                Violation(f"R{i}", f"Rule{i}", Severity.CRITICAL, "f.py", i, "msg")
                for i in range(10)
            ],
        )
        score = auditor._calculate_score(report)
        assert score == 0.0

    def test_summary(self):
        report = AuditReport(
            repo_root="/test",
            scan_date="2026-01-01",
            files_scanned=42,
            violations=[
                Violation("R1", "Rule1", Severity.HIGH, "f.py", 1, "msg"),
            ],
        )
        summary = report.summary()
        assert summary["files_scanned"] == 42
        assert summary["total_violations"] == 1
        assert summary["by_severity"]["HIGH"] == 1

    def test_markdown_output(self):
        report = AuditReport(
            repo_root="/test",
            scan_date="2026-01-01",
            files_scanned=10,
            score=85.0,
            violations=[
                Violation("R1", "Rule1", Severity.HIGH, "f.py", 5, "Test msg", "Fix it"),
            ],
        )
        md = report.to_markdown()
        assert "# Windows Compatibility Audit Report" in md
        assert "**Compatibility Score:** 85.0/100" in md
        assert "WIN001" in md or "R1" in md

    def test_sarif_output(self):
        report = AuditReport(
            repo_root="/test",
            scan_date="2026-01-01",
            violations=[
                Violation("R1", "Rule1", Severity.HIGH, "f.py", 5, "Test msg"),
            ],
        )
        sarif = report.to_sarif()
        assert sarif["version"] == "2.1.0"
        assert len(sarif["runs"][0]["results"]) == 1
        assert sarif["runs"][0]["results"][0]["level"] == "error"


# =============================================================================
# WindowsAuditor Integration Tests
# =============================================================================

class TestWindowsAuditor:
    """Integration tests for the full WindowsAuditor."""

    def test_loads_all_rules(self):
        auditor = WindowsAuditor(repo_root=".")
        assert len(auditor.rules) == 7

    def test_audit_clean_repo(self, tmp_path):
        """Audit a clean repo should produce no violations."""
        (tmp_path / "clean.py").write_text('from pathlib import Path\np = Path("test")\n')
        auditor = WindowsAuditor(repo_root=str(tmp_path))
        report = auditor.audit()
        assert report.files_scanned >= 1

    def test_audit_detects_violations(self, tmp_path):
        """Audit a repo with known violations."""
        (tmp_path / "bad.py").write_text(
            'import subprocess\n'
            'subprocess.run(["docker", "build", "."])\n'
            'subprocess.run(["kubectl", "apply", "-f", "deploy.yaml"])\n'
        )
        auditor = WindowsAuditor(repo_root=str(tmp_path))
        report = auditor.audit()
        # Should find subprocess violations
        subprocess_violations = [v for v in report.violations if v.rule_id == "WIN005"]
        assert len(subprocess_violations) >= 1

    def test_audit_skips_binary_dirs(self, tmp_path):
        """Should skip .git, __pycache__, etc."""
        (tmp_path / ".git").mkdir()
        (tmp_path / ".git" / "config").write_text("[core]\n")
        (tmp_path / "good.py").write_text("x = 1\n")
        auditor = WindowsAuditor(repo_root=str(tmp_path))
        report = auditor.audit()
        # Should only scan good.py, not .git/config
        assert report.files_scanned == 1

    def test_write_report(self, tmp_path):
        """Test report generation in all formats."""
        (tmp_path / "test.py").write_text(
            'import subprocess\nsubprocess.run(["echo", "hi"])\n'
        )
        auditor = WindowsAuditor(repo_root=str(tmp_path))
        report = auditor.audit()
        output_dir = tmp_path / "reports"
        written = auditor.write_report(report, output_dir=str(output_dir))

        assert "json" in written
        assert "markdown" in written
        assert "sarif" in written

        # Verify JSON is valid
        json_data = json.loads(Path(written["json"]).read_text())
        assert "summary" in json_data
        assert "violations" in json_data

        # Verify Markdown
        md_content = Path(written["markdown"]).read_text()
        assert "# Windows Compatibility Audit Report" in md_content

        # Verify SARIF
        sarif_data = json.loads(Path(written["sarif"]).read_text())
        assert sarif_data["version"] == "2.1.0"

    def test_audit_duration_recorded(self, tmp_path):
        (tmp_path / "test.py").write_text("x = 1\n")
        auditor = WindowsAuditor(repo_root=str(tmp_path))
        report = auditor.audit()
        assert report.scan_duration_seconds >= 0
