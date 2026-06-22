"""
Windows Compatibility Auditor (PRD-KIVA-003)

Scans a repository for Windows compatibility issues and KiloCode rule violations.
Produces JSON + Markdown + SARIF reports.

Usage:
    auditor = WindowsAuditor(repo_root=".")
    report = auditor.audit()
    print(report.summary())
    auditor.write_report(report, output_dir="reports/")

Rules audited:
    - CMD wrapper usage (harmonisation-v8)
    - Here-strings in PowerShell
    - Hardcoded Windows paths vs Path usage
    - File encoding (UTF-8 BOM)
    - Direct subprocess calls vs orchestrator
    - Long bash commands (SLM Fragmented)
    - cd + && anti-pattern
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from kiva_cli.core.types import ValidationState

logger = logging.getLogger(__name__)


class Severity(str, Enum):
    """Violation severity levels."""
    CRITICAL = "CRITICAL"   # Blocks merge
    HIGH = "HIGH"           # Should fix immediately
    MEDIUM = "MEDIUM"       # Should fix soon
    LOW = "LOW"             # Nice to fix
    INFO = "INFO"           # Informational


@dataclass
class Violation:
    """A single rule violation found during audit."""
    rule_id: str
    rule_name: str
    severity: Severity
    file_path: str
    line_number: int
    message: str
    suggestion: str = ""
    snippet: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class AuditReport:
    """Complete audit report for a repository."""
    repo_root: str
    scan_date: str
    files_scanned: int = 0
    violations: List[Violation] = field(default_factory=list)
    score: float = 100.0  # 0-100 compatibility score
    scan_duration_seconds: float = 0.0

    @property
    def critical_count(self) -> int:
        return sum(1 for v in self.violations if v.severity == Severity.CRITICAL)

    @property
    def high_count(self) -> int:
        return sum(1 for v in self.violations if v.severity == Severity.HIGH)

    @property
    def medium_count(self) -> int:
        return sum(1 for v in self.violations if v.severity == Severity.MEDIUM)

    @property
    def low_count(self) -> int:
        return sum(1 for v in self.violations if v.severity == Severity.LOW)

    @property
    def total_violations(self) -> int:
        return len(self.violations)

    def summary(self) -> Dict[str, Any]:
        return {
            "repo_root": self.repo_root,
            "scan_date": self.scan_date,
            "files_scanned": self.files_scanned,
            "score": self.score,
            "scan_duration_seconds": self.scan_duration_seconds,
            "total_violations": self.total_violations,
            "by_severity": {
                "CRITICAL": self.critical_count,
                "HIGH": self.high_count,
                "MEDIUM": self.medium_count,
                "LOW": self.low_count,
            },
            "rules_checked": self._rules_checked(),
        }

    def _rules_checked(self) -> List[str]:
        """Return unique rule IDs checked."""
        return list(set(v.rule_id for v in self.violations))

    def to_markdown(self) -> str:
        """Generate a Markdown report."""
        lines = [
            "# Windows Compatibility Audit Report",
            "",
            f"**Repo:** `{self.repo_root}`",
            f"**Scan Date:** {self.scan_date}",
            f"**Files Scanned:** {self.files_scanned}",
            f"**Scan Duration:** {self.scan_duration_seconds:.2f}s",
            f"**Compatibility Score:** {self.score:.1f}/100",
            "",
            "## Summary",
            "",
            f"| Severity | Count |",
            f"|----------|-------|",
            f"| CRITICAL | {self.critical_count} |",
            f"| HIGH | {self.high_count} |",
            f"| MEDIUM | {self.medium_count} |",
            f"| LOW | {self.low_count} |",
            f"| **Total** | **{self.total_violations}** |",
            "",
        ]

        if not self.violations:
            lines.append("## Result: PASS")
            lines.append("")
            lines.append("No violations found. Repository is Windows-compatible.")
        else:
            lines.append("## Violations")
            lines.append("")

            for severity in [Severity.CRITICAL, Severity.HIGH, Severity.MEDIUM, Severity.LOW, Severity.INFO]:
                sev_violations = [v for v in self.violations if v.severity == severity]
                if sev_violations:
                    lines.append(f"### {severity.value} ({len(sev_violations)})")
                    lines.append("")
                    for v in sev_violations:
                        lines.append(f"#### `{v.rule_id}` — {v.rule_name}")
                        lines.append(f"- **File:** `{v.file_path}:{v.line_number}`")
                        lines.append(f"- **Message:** {v.message}")
                        if v.suggestion:
                            lines.append(f"- **Suggestion:** {v.suggestion}")
                        if v.snippet:
                            lines.append(f"- **Snippet:** `{v.snippet}`")
                        lines.append("")

        lines.append("---")
        lines.append(f"*Generated by KIVA Windows Compatibility Auditor*")
        return "\n".join(lines)

    def to_sarif(self) -> Dict[str, Any]:
        """Generate SARIF (Static Analysis Results Interchange Format) for GitHub."""
        results = []
        for v in self.violations:
            results.append({
                "ruleId": v.rule_id,
                "level": self._sarif_level(v.severity),
                "message": {"text": v.message},
                "locations": [{
                    "physicalLocation": {
                        "artifactLocation": {"uri": v.file_path},
                        "region": {"startLine": v.line_number},
                    }
                }],
            })

        return {
            "$schema": "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/master/Schemata/sarif-schema-2.1.0.json",
            "version": "2.1.0",
            "runs": [{
                "tool": {
                    "driver": {
                        "name": "KIVA Windows Compatibility Auditor",
                        "version": "1.0.0",
                        "rules": self._sarif_rules(),
                    }
                },
                "results": results,
            }],
        }

    def _sarif_level(self, severity: Severity) -> str:
        return {
            Severity.CRITICAL: "error",
            Severity.HIGH: "error",
            Severity.MEDIUM: "warning",
            Severity.LOW: "note",
            Severity.INFO: "note",
        }.get(severity, "warning")

    def _sarif_rules(self) -> List[Dict[str, Any]]:
        """Generate SARIF rule definitions from violations."""
        seen = set()
        rules = []
        for v in self.violations:
            if v.rule_id not in seen:
                rules.append({
                    "id": v.rule_id,
                    "name": v.rule_name,
                    "shortDescription": {"text": v.rule_name},
                })
                seen.add(v.rule_id)
        return rules


# =============================================================================
# Audit Rules
# =============================================================================

class AuditRule:
    """Base class for audit rules."""

    def __init__(self, rule_id: str, rule_name: str, description: str):
        self.rule_id = rule_id
        self.rule_name = rule_name
        self.description = description

    def check_file(self, file_path: Path, content: str) -> List[Violation]:
        """Check a file for violations. Override in subclasses."""
        return []


class CmdWrapperRule(AuditRule):
    """
    Rule: PowerShell scripts should use CMD wrapper.
    Pattern from harmonisation-v8.md:
    Recommended: cmd /c powershell -ExecutionPolicy ByPass -File <script.ps1>
    Anti-pattern: & "path\\to\\script.ps1" or direct powershell calls in Python.
    """

    def __init__(self):
        super().__init__(
            "WIN001",
            "CMD Wrapper for PowerShell",
            "PowerShell scripts should be invoked via CMD wrapper to avoid encoding issues.",
        )
        # Pattern: direct powershell invocation without cmd /c wrapper
        self._patterns = [
            (
                re.compile(r'["\'].*?\.ps1["\']', re.IGNORECASE),
                "Direct .ps1 file reference without CMD wrapper",
            ),
            (
                re.compile(r'powershell\s+-', re.IGNORECASE),
                "Direct powershell invocation without cmd /c wrapper",
            ),
        ]

    def check_file(self, file_path: Path, content: str) -> List[Violation]:
        violations = []
        # Only check Python and shell files
        if file_path.suffix not in (".py", ".sh", ".ps1", ".bat", ".cmd"):
            return violations

        for line_num, line in enumerate(content.splitlines(), 1):
            # Skip cmd /c patterns (they're correct)
            if "cmd /c" in line or "cmd.exe /c" in line:
                continue
            # Skip comments
            stripped = line.strip()
            if stripped.startswith("#") or stripped.startswith("//"):
                continue

            for pattern, message in self._patterns:
                match = pattern.search(line)
                if match:
                    # Check if it's a powershell -File call (anti-pattern)
                    if re.search(r'powershell\s+-(?:File|Command|ExecutionPolicy)', line, re.IGNORECASE):
                        if "cmd /c" not in line:
                            violations.append(Violation(
                                rule_id=self.rule_id,
                                rule_name=self.rule_name,
                                severity=Severity.HIGH,
                                file_path=str(file_path),
                                line_number=line_num,
                                message=message,
                                suggestion="Use: cmd /c powershell -ExecutionPolicy ByPass -File <script.ps1>",
                                snippet=stripped[:100],
                            ))
        return violations


class HereStringRule(AuditRule):
    """
    Rule: No here-strings in PowerShell or bash.
    Here-strings cause encoding/parsing issues on Windows.
    """

    def __init__(self):
        super().__init__(
            "WIN002",
            "No Here-Strings",
            "Here-strings (@'...'@ or @\"...\"@) cause encoding issues on Windows.",
        )
        self._pattern = re.compile(r"@['\"]", re.MULTILINE)

    def check_file(self, file_path: Path, content: str) -> List[Violation]:
        violations = []
        if file_path.suffix not in (".py", ".sh", ".bat", ".cmd"):
            # Also check .ps1 files
            if file_path.suffix != ".ps1":
                return violations

        for line_num, line in enumerate(content.splitlines(), 1):
            if self._pattern.search(line):
                snippet = line.strip()
                # Check if it looks like a here-string start
                if re.search(r"@\s*['\"]", snippet):
                    violations.append(Violation(
                        rule_id=self.rule_id,
                        rule_name=self.rule_name,
                        severity=Severity.MEDIUM,
                        file_path=str(file_path),
                        line_number=line_num,
                        message="Here-string detected — causes encoding issues on Windows",
                        suggestion="Replace here-strings with regular string concatenation or file reads",
                        snippet=snippet[:100],
                    ))
        return violations


class HardcodedPathRule(AuditRule):
    """
    Rule: No hardcoded Windows paths. Use Path from pathlib.
    """

    def __init__(self):
        super().__init__(
            "WIN003",
            "No Hardcoded Windows Paths",
            "Hardcoded Windows paths (C:\\\\\\...) should use pathlib.Path for cross-platform compatibility.",
        )
        # Match hardcoded Windows-style paths outside strings that are clearly paths
        self._patterns = [
            re.compile(r"[A-Z]:\\[^\s\"')]+"),  # C:\path\...
        ]

    def check_file(self, file_path: Path, content: str) -> List[Violation]:
        violations = []
        if file_path.suffix != ".py":
            return violations

        for line_num, line in enumerate(content.splitlines(), 1):
            # Skip imports and comments
            stripped = line.strip()
            if stripped.startswith(("import ", "from ", "#")):
                continue
            # Skip Path() usage (correct)
            if "Path(" in stripped:
                continue

            for pattern in self._patterns:
                match = pattern.search(stripped)
                if match:
                    # Exclude if it's in a string that's already using Path
                    if not re.search(r"Path\(", stripped):
                        violations.append(Violation(
                            rule_id=self.rule_id,
                            rule_name=self.rule_name,
                            severity=Severity.LOW,
                            file_path=str(file_path),
                            line_number=line_num,
                            message=f"Hardcoded Windows path: {match.group()[:50]}",
                            suggestion="Use Path() from pathlib for cross-platform compatibility",
                            snippet=stripped[:100],
                        ))
        return violations


class FileEncodingRule(AuditRule):
    """
    Rule: Files should be UTF-8 without BOM.
    UTF-8 BOM causes issues with Python shebangs and PowerShell execution.
    """

    def __init__(self):
        super().__init__(
            "WIN004",
            "UTF-8 Without BOM",
            "Files should use UTF-8 encoding without BOM for cross-platform compatibility.",
        )

    def check_file(self, file_path: Path, content: str) -> List[Violation]:
        violations = []
        # Only check text files
        if file_path.suffix not in (".py", ".sh", ".ps1", ".bat", ".cmd", ".md", ".yml", ".yaml", ".json", ".toml"):
            return violations

        try:
            raw = file_path.read_bytes()
            # Check for UTF-8 BOM (EF BB BF)
            if raw.startswith(b"\xef\xbb\xbf"):
                violations.append(Violation(
                    rule_id=self.rule_id,
                    rule_name=self.rule_name,
                    severity=Severity.MEDIUM,
                    file_path=str(file_path),
                    line_number=1,
                    message="File has UTF-8 BOM — should be UTF-8 without BOM",
                    suggestion="Re-save file as UTF-8 without BOM (most editors have this option)",
                ))
            # Check for UTF-16 LE BOM (FF FE)
            elif raw.startswith(b"\xff\xfe") or raw.startswith(b"\xfe\xff"):
                violations.append(Violation(
                    rule_id=self.rule_id,
                    rule_name=self.rule_name,
                    severity=Severity.HIGH,
                    file_path=str(file_path),
                    line_number=1,
                    message=f"File uses UTF-16 encoding — should be UTF-8 without BOM",
                    suggestion="Re-save file as UTF-8 without BOM",
                ))
        except (OSError, PermissionError):
            pass  # Can't read file, skip

        return violations


class SubprocessNoMockRule(AuditRule):
    """
    Rule: Direct subprocess.run() calls should use the orchestrator.
    """

    def __init__(self):
        super().__init__(
            "WIN005",
            "Use Subprocess Orchestrator",
            "Direct subprocess.run() calls should be replaced with SubprocessMockOrchestrator for testability.",
        )
        self._pattern = re.compile(r"subprocess\.run\(|subprocess\.Popen\(|subprocess\.call\(")

    def check_file(self, file_path: Path, content: str) -> List[Violation]:
        violations = []
        if file_path.suffix != ".py":
            return violations
        # Skip test files (they're allowed to mock)
        if "test_" in file_path.name or file_path.name.startswith("conftest"):
            return violations
        # Skip the orchestrator itself
        if "subprocess_orchestrator" in str(file_path):
            return violations

        for line_num, line in enumerate(content.splitlines(), 1):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            if self._pattern.search(stripped):
                if "mock" not in stripped.lower() and "orchestrator" not in stripped.lower():
                    violations.append(Violation(
                        rule_id=self.rule_id,
                        rule_name=self.rule_name,
                        severity=Severity.MEDIUM,
                        file_path=str(file_path),
                        line_number=line_num,
                        message="Direct subprocess call — should use SubprocessMockOrchestrator (PRD-KIVA-005)",
                        suggestion="from kiva_cli.core.subprocess_orchestrator import SubprocessMockOrchestrator",
                        snippet=stripped[:100],
                    ))
        return violations


class CdAndAmpersandRule(AuditRule):
    """
    Rule: No 'cd foo && bar' pattern. Use cwd parameter instead.
    """

    def __init__(self):
        super().__init__(
            "WIN006",
            "No cd && anti-pattern",
            "'cd foo && bar' should be replaced with subprocess.run(..., cwd='foo') or powershell -File.",
        )
        self._patterns = [
            re.compile(r"cd\s+\S+\s*&&\s*\S+"),
            re.compile(r"os\.chdir\("),
        ]

    def check_file(self, file_path: Path, content: str) -> List[Violation]:
        violations = []
        if file_path.suffix not in (".py", ".sh", ".bat", ".cmd", ".ps1"):
            return violations

        for line_num, line in enumerate(content.splitlines(), 1):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue

            for pattern in self._patterns:
                match = pattern.search(stripped)
                if match:
                    violations.append(Violation(
                        rule_id=self.rule_id,
                        rule_name=self.rule_name,
                        severity=Severity.HIGH if file_path.suffix == ".py" else Severity.MEDIUM,
                        file_path=str(file_path),
                        line_number=line_num,
                        message=f"cd-and-execute anti-pattern detected: {match.group()[:50]}",
                        suggestion="Use subprocess.run(..., cwd='path') for Python, or powershell -File for PS1",
                        snippet=stripped[:100],
                    ))
        return violations


class LongCommandRule(AuditRule):
    """
    Rule: No very long single-line commands (SLM Fragmented approach).
    Commands > 200 chars on one line should be broken down.
    """

    def __init__(self, max_length: int = 200):
        super().__init__(
            "WIN007",
            "No Overly Long Single-Line Commands",
            "Single-line commands exceeding 200 chars violate SLM Fragmented approach and should be decomposed.",
        )
        self.max_length = max_length

    def check_file(self, file_path: Path, content: str) -> List[Violation]:
        violations = []
        if file_path.suffix not in (".py", ".sh", ".bat", ".cmd"):
            return violations

        for line_num, line in enumerate(content.splitlines(), 1):
            if len(line) > self.max_length:
                stripped = line.strip()
                if not stripped.startswith("#"):
                    violations.append(Violation(
                        rule_id=self.rule_id,
                        rule_name=self.rule_name,
                        severity=Severity.LOW,
                        file_path=str(file_path),
                        line_number=line_num,
                        message=f"Line too long ({len(line)} chars) — violates SLM Fragmented approach",
                        suggestion="Break into multiple atomic commands (one action = one tool = one result)",
                        snippet=stripped[:100] + "...",
                    ))
        return violations


# =============================================================================
# Windows Auditor (Main)
# =============================================================================

class WindowsAuditor:
    """
    Scans a repository for Windows compatibility issues and rule violations.

    Usage:
        auditor = WindowsAuditor(repo_root=".")
        report = auditor.audit()
        print(report.summary())
        auditor.write_report(report, output_dir="reports/")
    """

    def __init__(self, repo_root: str = "."):
        self.repo_root = Path(repo_root).resolve()
        self.rules: List[AuditRule] = [
            CmdWrapperRule(),
            HereStringRule(),
            HardcodedPathRule(),
            FileEncodingRule(),
            SubprocessNoMockRule(),
            CdAndAmpersandRule(),
            LongCommandRule(),
        ]
        # Directories to skip
        self._skip_dirs = {
            ".git", "__pycache__", "node_modules", ".venv", "venv",
            "htmlcov", ".pytest_cache", ".mypy_cache", "generated",
        }

    def audit(self) -> AuditReport:
        """Run full audit on the repository."""
        import time
        start = time.time()

        report = AuditReport(
            repo_root=str(self.repo_root),
            scan_date=datetime.now().isoformat(),
        )

        files_to_scan = self._collect_files()
        report.files_scanned = len(files_to_scan)

        for file_path in files_to_scan:
            try:
                content = file_path.read_text(encoding="utf-8", errors="replace")
            except (OSError, PermissionError):
                continue

            for rule in self.rules:
                try:
                    violations = rule.check_file(file_path.relative_to(self.repo_root), content)
                    report.violations.extend(violations)
                except Exception as e:
                    logger.warning(f"Rule {rule.rule_id} failed on {file_path}: {e}")

        # Calculate score (100 - deductions)
        report.score = self._calculate_score(report)
        report.scan_duration_seconds = round(time.time() - start, 2)

        return report

    def _collect_files(self) -> List[Path]:
        """Collect all scannable files in the repository."""
        files = []
        for root, dirs, filenames in os.walk(self.repo_root):
            # Skip unwanted directories
            dirs[:] = [d for d in dirs if d not in self._skip_dirs and not d.startswith(".")]
            for filename in filenames:
                file_path = Path(root) / filename
                if self._should_scan(file_path):
                    files.append(file_path)
        return files

    def _should_scan(self, file_path: Path) -> bool:
        """Check if a file should be scanned."""
        suffix = file_path.suffix.lower()
        return suffix in {
            ".py", ".sh", ".ps1", ".bat", ".cmd", ".md",
            ".yml", ".yaml", ".json", ".toml",
        }

    def _calculate_score(self, report: AuditReport) -> float:
        """Calculate compatibility score (0-100) from violations."""
        deductions = {
            Severity.CRITICAL: 30,
            Severity.HIGH: 15,
            Severity.MEDIUM: 5,
            Severity.LOW: 2,
            Severity.INFO: 0,
        }
        total_deductions = sum(
            deductions.get(v.severity, 0) for v in report.violations
        )
        return max(0.0, 100.0 - total_deductions)

    def write_report(
        self,
        report: AuditReport,
        output_dir: str = "reports",
    ) -> Dict[str, str]:
        """Write audit reports in all formats. Returns paths of written files."""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        written = {}

        # JSON
        json_path = output_path / "windows_audit.json"
        json_data = {
            "summary": report.summary(),
            "violations": [v.to_dict() for v in report.violations],
        }
        json_path.write_text(json.dumps(json_data, indent=2), encoding="utf-8")
        written["json"] = str(json_path)

        # Markdown
        md_path = output_path / "windows_audit.md"
        md_path.write_text(report.to_markdown(), encoding="utf-8")
        written["markdown"] = str(md_path)

        # SARIF
        sarif_path = output_path / "windows_audit.sarif"
        sarif_path.write_text(json.dumps(report.to_sarif(), indent=2), encoding="utf-8")
        written["sarif"] = str(sarif_path)

        return written
