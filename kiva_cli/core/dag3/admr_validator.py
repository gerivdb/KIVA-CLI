#!/usr/bin/env python3
"""
ADMR Validator - Adjunction-driven Merge Request Validator

Valide les merge requests basés sur des adjonctions structurelles.
Un ADMR vérifie que le merge respecte les contraintes d'adjonction
entre modules, classes et fonctions.

IntentHash: 0xADMR_VALIDATOR_20260718
"""

from typing import Dict, List, Set, Tuple, Optional
from dataclasses import dataclass, field
from enum import Enum
import json
import subprocess
from pathlib import Path
import re


class ADMRStatus(Enum):
    """Status of ADMR validation."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    NEEDS_HITL = "needs_hitl"


class ConstraintType(Enum):
    """Types of constraints for ADMR validation."""
    CYCLE = "cycle"
    DEPENDENCY = "dependency"
    INTERFACE = "interface"
    ARCHITECTURE = "architecture"
    SECURITY = "security"
    PERFORMANCE = "performance"


@dataclass
class ConstraintViolation:
    """Represents a constraint violation."""
    constraint_type: ConstraintType
    message: str
    severity: str  # "low", "medium", "high", "critical"
    affected_files: List[str] = field(default_factory=list)
    suggested_fix: str = ""


@dataclass
class ADMRValidationResult:
    """Result of ADMR validation."""
    status: ADMRStatus
    branch: str
    target: str
    violations: List[ConstraintViolation] = field(default_factory=list)
    phi_cps_impact: float = 0.0
    hitl_required: bool = False
    recommendations: List[str] = field(default_factory=list)
    validation_timestamp: str = ""


class ADMRValidator:
    """
    Adjunction-driven Merge Request Validator.
    
    Validates merge requests based on structural adjunctions between
    code entities (modules, classes, functions).
    
    Usage:
        validator = ADMRValidator(repo_path="/path/to/repo")
        result = validator.validate_merge("feature-branch", "main")
        if result.status == ADMRStatus.APPROVED:
            print("Merge approved!")
    """

    def __init__(self, repo_path: str = ".", commit_range: str = ""):
        """
        Initialize ADMR Validator.
        
        Args:
            repo_path: Path to the repository
            commit_range: Range of commits to analyze (e.g., "main..feature-branch")
        """
        self.repo_path = Path(repo_path)
        self.commit_range = commit_range
        self.branch_changes: Dict[str, Set[str]] = {}
        self.adjunctions: Dict[str, List[str]] = {}  # entity -> adjoined entities
        
    def analyze_commit_range(self, source_branch: str, target_branch: str) -> Dict:
        """
        Analyze changes in a commit range.
        
        Args:
            source_branch: Source branch name
            target_branch: Target branch name
            
        Returns:
            Dictionary with analysis results
        """
        try:
            # Get changed files
            result = subprocess.run(
                ["git", "diff", "--name-only", f"{target_branch}..{source_branch}"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True
            )
            
            changed_files = set(result.stdout.strip().split("\n")) if result.stdout.strip() else set()
            
            # Get changed Python files specifically
            python_files = {f for f in changed_files if f.endswith(".py")}
            
            # Get commit messages
            result = subprocess.run(
                ["git", "log", "--oneline", f"{target_branch}..{source_branch}"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True
            )
            
            commit_messages = result.stdout.strip().split("\n") if result.stdout.strip() else []
            
            return {
                "changed_files": changed_files,
                "python_files": python_files,
                "commit_messages": commit_messages,
                "commit_count": len(commit_messages)
            }
            
        except subprocess.CalledProcessError as e:
            return {
                "changed_files": set(),
                "python_files": set(),
                "commit_messages": [],
                "commit_count": 0,
                "error": str(e)
            }

    def detect_adjunctions(self, file_path: str) -> List[str]:
        """
        Detect adjunctions in a Python file.
        
        An adjunction is a structural relationship between entities.
        
        Args:
            file_path: Path to Python file
            
        Returns:
            List of adjoined entities
        """
        adjoined = []
        full_path = self.repo_path / file_path
        
        try:
            content = full_path.read_text(encoding="utf-8")
            
            # Detect class definitions and their methods
            classes = re.findall(r'^class\s+(\w+)', content, re.MULTILINE)
            for cls in classes:
                adjoined.append(f"class:{cls}")
            
            # Detect function definitions
            functions = re.findall(r'^def\s+(\w+)', content, re.MULTILINE)
            for func in functions:
                adjoined.append(f"function:{func}")
            
            # Detect imports (external adjunctions)
            imports = re.findall(r'^(?:import|from)\s+(\w+)', content, re.MULTILINE)
            for imp in imports:
                if not imp.startswith("_"):  # Skip private imports
                    adjoined.append(f"import:{imp}")
                    
        except Exception:
            pass
        
        return adjoined

    def check_cycle_constraints(self, source_branch: str, target_branch: str) -> List[ConstraintViolation]:
        """Check for cycle-related constraints."""
        violations = []
        
        # Use ACM detector to check for cycles
        try:
            from .acm_detector import ACMDetector
            
            detector = ACMDetector(repo_path=str(self.repo_path))
            result = detector.detect_cycles()
            
            if result.has_cycles:
                for cycle in result.cycles[:3]:  # Limit to 3 cycles
                    violations.append(ConstraintViolation(
                        constraint_type=ConstraintType.CYCLE,
                        message=f"Cycle detected: {' -> '.join(cycle)}",
                        severity="high",
                        suggested_fix="Refactor to break the cycle"
                    ))
        except ImportError:
            # ACM detector not available, skip cycle check
            pass
        
        return violations

    def check_dependency_constraints(self, source_branch: str, target_branch: str) -> List[ConstraintViolation]:
        """Check for dependency-related constraints."""
        violations = []
        analysis = self.analyze_commit_range(source_branch, target_branch)
        
        for file_path in analysis.get("python_files", []):
            adjunctions = self.detect_adjunctions(file_path)
            self.adjunctions[file_path] = adjunctions
            
            # Check for dangerous imports (external repos, etc.)
            for adj in adjunctions:
                if adj.startswith("import:"):
                    module = adj.split(":")[1]
                    # Add checks for external dependencies
                    if module in ["requests", "numpy", "pandas"]:
                        # These might need HITL approval
                        violations.append(ConstraintViolation(
                            constraint_type=ConstraintType.DEPENDENCY,
                            message=f"External dependency added: {module}",
                            severity="medium",
                            affected_files=[file_path],
                            suggested_fix="Verify external dependency is necessary"
                        ))
        
        return violations

    def check_interface_constraints(self, source_branch: str, target_branch: str) -> List[ConstraintViolation]:
        """Check for interface/ABI constraints."""
        violations = []
        
        # Check for public API changes
        analysis = self.analyze_commit_range(source_branch, target_branch)
        
        for file_path in analysis.get("python_files", []):
            if "cli" in file_path.lower() or "commands" in file_path.lower():
                # CLI changes might affect downstream users
                violations.append(ConstraintViolation(
                    constraint_type=ConstraintType.INTERFACE,
                    message=f"CLI interface change detected in {file_path}",
                    severity="low",
                    affected_files=[file_path],
                    suggested_fix="Verify backward compatibility"
                ))
        
        return violations

    def check_architecture_constraints(self, source_branch: str, target_branch: str) -> List[ConstraintViolation]:
        """Check for architecture-level constraints."""
        violations = []
        
        # Check for changes in core architecture files
        analysis = self.analyze_commit_range(source_branch, target_branch)
        
        core_files = {"__init__.py", "core", "manager", "handler", "pipeline"}
        
        for file_path in analysis.get("python_files", []):
            for core in core_files:
                if core in file_path.lower():
                    violations.append(ConstraintViolation(
                        constraint_type=ConstraintType.ARCHITECTURE,
                        message=f"Core architecture change in {file_path}",
                        severity="high",
                        affected_files=[file_path],
                        suggested_fix="Architecture review required"
                    ))
                    break
        
        return violations

    def check_security_constraints(self, source_branch: str, target_branch: str) -> List[ConstraintViolation]:
        """Check for security-related constraints."""
        violations = []
        analysis = self.analyze_commit_range(source_branch, target_branch)
        
        security_patterns = [
            (r'password\s*=\s*["\']', "Hardcoded password"),
            (r'api_key\s*=\s*["\']', "Hardcoded API key"),
            (r'secret\s*=\s*["\']', "Hardcoded secret"),
            (r'eval\s*\(', "Use of eval()"),
            (r'exec\s*\(', "Use of exec()"),
        ]
        
        for file_path in analysis.get("python_files", []):
            full_path = self.repo_path / file_path
            try:
                content = full_path.read_text(encoding="utf-8")
                for pattern, desc in security_patterns:
                    if re.search(pattern, content, re.IGNORECASE):
                        violations.append(ConstraintViolation(
                            constraint_type=ConstraintType.SECURITY,
                            message=f"Security issue: {desc} in {file_path}",
                            severity="critical",
                            affected_files=[file_path],
                            suggested_fix="Remove hardcoded credentials and use secure alternatives"
                        ))
            except Exception:
                pass
        
        return violations

    def check_performance_constraints(self, source_branch: str, target_branch: str) -> List[ConstraintViolation]:
        """Check for performance-related constraints."""
        violations = []
        analysis = self.analyze_commit_range(source_branch, target_branch)
        
        for file_path in analysis.get("python_files", []):
            full_path = self.repo_path / file_path
            try:
                content = full_path.read_text(encoding="utf-8")
                
                # Check for potential performance issues
                if "while True:" in content:
                    violations.append(ConstraintViolation(
                        constraint_type=ConstraintType.PERFORMANCE,
                        message=f"Potential infinite loop in {file_path}",
                        severity="medium",
                        affected_files=[file_path],
                        suggested_fix="Add loop termination condition"
                    ))
                
                if "time.sleep" in content:
                    violations.append(ConstraintViolation(
                        constraint_type=ConstraintType.PERFORMANCE,
                        message=f"Blocking sleep in {file_path}",
                        severity="low",
                        affected_files=[file_path],
                        suggested_fix="Use async sleep or remove if unnecessary"
                    ))
            except Exception:
                pass
        
        return violations

    def validate(self, source_branch: str, target_branch: str = "main") -> ADMRValidationResult:
        """
        Validate a merge request using ADMR rules.
        
        Args:
            source_branch: Source branch name
            target_branch: Target branch name
            
        Returns:
            ADMRValidationResult with validation outcome
        """
        from datetime import datetime, timezone
        
        result = ADMRValidationResult(
            status=ADMRStatus.PENDING,
            branch=source_branch,
            target=target_branch,
            validation_timestamp=datetime.now(timezone.utc).isoformat()
        )
        
        # Run all constraint checks
        all_violations = []
        
        # Cycle constraints
        cycle_violations = self.check_cycle_constraints(source_branch, target_branch)
        all_violations.extend(cycle_violations)
        
        # Dependency constraints
        dep_violations = self.check_dependency_constraints(source_branch, target_branch)
        all_violations.extend(dep_violations)
        
        # Interface constraints
        interface_violations = self.check_interface_constraints(source_branch, target_branch)
        all_violations.extend(interface_violations)
        
        # Architecture constraints
        arch_violations = self.check_architecture_constraints(source_branch, target_branch)
        all_violations.extend(arch_violations)
        
        # Security constraints
        security_violations = self.check_security_constraints(source_branch, target_branch)
        all_violations.extend(security_violations)
        
        # Performance constraints
        perf_violations = self.check_performance_constraints(source_branch, target_branch)
        all_violations.extend(perf_violations)
        
        result.violations = all_violations
        
        # Calculate φ-CPS impact based on violations
        phi_impact = 0.0
        for v in all_violations:
            if v.severity == "critical":
                phi_impact += 0.5
            elif v.severity == "high":
                phi_impact += 0.3
            elif v.severity == "medium":
                phi_impact += 0.1
            else:
                phi_impact += 0.05
        
        result.phi_cps_impact = min(phi_impact, 1.0)
        
        # Determine status
        critical_violations = [v for v in all_violations if v.severity == "critical"]
        high_violations = [v for v in all_violations if v.severity == "high"]
        
        if critical_violations:
            result.status = ADMRStatus.REJECTED
            result.hitl_required = False
        elif high_violations:
            result.status = ADMRStatus.NEEDS_HITL
            result.hitl_required = True
        elif len(all_violations) > 5:
            result.status = ADMRStatus.NEEDS_HITL
            result.hitl_required = True
        else:
            result.status = ADMRStatus.APPROVED
            result.hitl_required = False
        
        # Generate recommendations
        result.recommendations = self._generate_recommendations(all_violations)
        
        return result

    def _generate_recommendations(self, violations: List[ConstraintViolation]) -> List[str]:
        """Generate recommendations based on violations."""
        recommendations = []
        
        if not violations:
            recommendations.append("No violations detected - merge ready")
            return recommendations
        
        # Group by constraint type
        by_type = {}
        for v in violations:
            if v.constraint_type not in by_type:
                by_type[v.constraint_type] = []
            by_type[v.constraint_type].append(v)
        
        for ctype, viols in by_type.items():
            if ctype == ConstraintType.CYCLE:
                recommendations.append("[ADMR-CYCLE] Refactor to break dependency cycles")
            elif ctype == ConstraintType.SECURITY:
                recommendations.append("[ADMR-SECURITY] Address security vulnerabilities immediately")
            elif ctype == ConstraintType.ARCHITECTURE:
                recommendations.append("[ADMR-ARCH] Architecture review required before merge")
            elif ctype == ConstraintType.DEPENDENCY:
                recommendations.append("[ADMR-DEP] Review external dependency additions")
            elif ctype == ConstraintType.INTERFACE:
                recommendations.append("[ADMR-IFACE] Verify interface compatibility")
            elif ctype == ConstraintType.PERFORMANCE:
                recommendations.append("[ADMR-PERF] Address potential performance issues")
        
        return recommendations


def main():
    """CLI entry point for ADMR validation."""
    import argparse
    
    parser = argparse.ArgumentParser(description="ADMR Validator - Validate merge requests")
    parser.add_argument("--repo-path", "-r", default=".", help="Repository path")
    parser.add_argument("--source", "-s", required=True, help="Source branch name")
    parser.add_argument("--target", "-t", default="main", help="Target branch name")
    parser.add_argument("--output", "-o", default="", help="Output JSON file")
    
    args = parser.parse_args()
    
    validator = ADMRValidator(repo_path=args.repo_path)
    result = validator.validate(args.source, args.target)
    
    print(f"[ADMR] Validation result: {result.status.value}")
    print(f"[ADMR] Branch: {result.branch} -> {result.target}")
    print(f"[ADMR] φ-CPS impact: {result.phi_cps_impact:.3f}")
    
    if result.violations:
        print(f"[ADMR] Violations found: {len(result.violations)}")
        for v in result.violations[:5]:  # Limit output
            print(f"  [{v.severity.upper()}] {v.message}")
    
    if result.recommendations:
        print("[ADMR] Recommendations:")
        for rec in result.recommendations:
            print(f"  {rec}")
    
    if args.output:
        output_data = {
            "status": result.status.value,
            "branch": result.branch,
            "target": result.target,
            "violations": [
                {
                    "type": v.constraint_type.value,
                    "message": v.message,
                    "severity": v.severity,
                    "affected_files": v.affected_files
                }
                for v in result.violations
            ],
            "phi_cps_impact": result.phi_cps_impact,
            "hitl_required": result.hitl_required,
            "recommendations": result.recommendations,
            "timestamp": result.validation_timestamp
        }
        Path(args.output).write_text(json.dumps(output_data, indent=2), encoding="utf-8")
        print(f"[ADMR] Results exported to {args.output}")
    
    return 0 if result.status == ADMRStatus.APPROVED else 1


if __name__ == "__main__":
    exit(main())