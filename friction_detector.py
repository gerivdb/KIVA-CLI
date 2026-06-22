#!/usr/bin/env python3
"""
Friction Detector v1.0 — Scan automatique post-implémentation
IntentHash: 0xFRICTION_DETECTOR_20260615

Usage:
    python friction_detector.py [--fix] [--repo <path>]
"""

import ast
import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field

# Fix Windows encoding
if sys.stdout.encoding != "utf-8":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

import ast
import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field

# ─────────────────────────────────────────────────────────────
# Friction definitions
# ─────────────────────────────────────────────────────────────

@dataclass
class Friction:
    id: str
    name: str
    severity: str  # "critical" | "warning" | "info"
    description: str
    check_fn: object  # callable(repo_path: Path) -> List[str]]
    fix_fn: object = None  # callable(repo_path: Path) -> bool


def check_f3_precommit_shebang(repo_path: Path) -> List[str]:
    """F3: Hook pre-commit has #!python instead of #!/usr/bin/env python3"""
    hook = repo_path / ".githooks" / "pre-commit"
    if not hook.exists():
        return []
    content = hook.read_text(encoding="utf-8", errors="replace")
    if content.startswith("#!python\n") or content.startswith("#!python\r"):
        return [f"{hook}: shebang is '#!python' — should be '#!/usr/bin/env python3'"]
    return []


def check_f8_message_context_as_dataclass(repo_path: Path) -> List[str]:
    issues = []
    for py_file in repo_path.rglob("*.py"):
        if "__pycache__" in str(py_file):
            continue
        # Skip self-referential files
        if py_file.name in ("friction_detector.py", "post_implement_check.py"):
        try:
            content = py_file.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue

        # Search for MessageContext(source= or MessageContext(
        # followed by named args — this is wrong since it's an Enum
        if "MessageContext(" in content:
            # Check if it's used with named arguments (wrong)
            pattern = r'MessageContext\s*\(\s*(?:source|destination|priority|payload_size|timestamp)\s*='
            matches = list(re.finditer(pattern, content))
            for m in matches:
                line_num = content[:m.start()].count("\n") + 1
                issues.append(
                    f"{py_file}:{line_num}: MessageContext() called with named args — "
                    f"it's an Enum, not a dataclass"
                )
    return issues


def check_f8_nonexistent_method(repo_path: Path) -> List[str]:
    """F8: calculate_optimal_route doesn't exist on IntelligentRouter."""
    issues = []
    for py_file in repo_path.rglob("*.py"):
        if "__pycache__" in str(py_file):
            continue
        try:
            content = py_file.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        if "calculate_optimal_route" in content:
            line_num = content[:content.index("calculate_optimal_route")].count("\n") + 1
            issues.append(
                f"{py_file}:{line_num}: calls calculate_optimal_route() — "
                f"method doesn't exist on IntelligentRouter"
            )
    return issues


def check_f9_circular_import(repo_path: Path) -> List[str]:
    """F9: dispatch_anything.py has circular fallback import."""
    issues = []
    dispatch_file = repo_path / "cli_tools" / "anything" / "dispatch_anything.py"
    if dispatch_file.exists():
        content = dispatch_file.read_text(encoding="utf-8", errors="replace")
        if "from .transport import bdcp_transport" in content:
            issues.append(
                f"{dispatch_file}: circular fallback import "
                f"'from .transport import bdcp_transport'"
            )
    return issues


def check_f10_no_tests(repo_path: Path) -> List[str]:
    """F10: No test file for anything-cli tools."""
    test_file = repo_path / "tests" / "test_anything_cli.py"
    if not test_file.exists():
        return [f"tests/test_anything_cli.py not found — no tests for anything-cli tools"]
    return []


def check_hook_executable(repo_path: Path) -> List[str]:
    """Additional: Hook pre-commit not executable on disk."""
    hook = repo_path / ".githooks" / "pre-commit"
    if hook.exists():
        if not os.access(str(hook), os.X_OK):
            return [f"{hook}: not executable — chmod +x needed"]
    return []


# ─────────────────────────────────────────────────────────────
# Fix functions
# ─────────────────────────────────────────────────────────────

def fix_f3_precommit_shebang(hook_path: Path) -> bool:
    """Fix F3: Replace #!python with #!/usr/bin/env python3."""
    try:
        content = hook_path.read_text(encoding="utf-8")
        if content.startswith("#!python"):
            content = content.replace("#!python", "#!/usr/bin/env python3", 1)
            hook_path.write_text(content, encoding="utf-8")
            return True
    except Exception:
        pass
    return False


def fix_hook_executable(hook_path: Path) -> bool:
    """Make hook executable."""
    try:
        os.chmod(str(hook_path), 0o755)
        return True
    except Exception:
        return False


# ─────────────────────────────────────────────────────────────
# Registry
# ─────────────────────────────────────────────────────────────

FRICTIONS: List[Friction] = [
    Friction("F3", "pre-commit shebang", "critical",
             "Hook pre-commit has invalid shebang #!python",
             check_f3_precommit_shebang, fix_f3_precommit_shebang),
    Friction("F8a", "MessageContext as dataclass", "critical",
             "MessageContext (Enum) called with named arguments",
             check_f8_message_context_as_dataclass, None),
    Friction("F8b", "calculate_optimal_route missing", "critical",
             "Method calculate_optimal_route doesn't exist on IntelligentRouter",
             check_f8_nonexistent_method, None),
    Friction("F9", "circular import dispatch", "warning",
             "dispatch_anything.py has circular fallback import",
             check_f9_circular_import, None),
    Friction("F10", "no unit tests", "warning",
             "No test file for anything-cli tools",
             check_f10_no_tests, None),
    Friction("FX1", "hook not executable", "warning",
             "Pre-commit hook not executable on disk",
             check_hook_executable, fix_hook_executable),
]


def scan_repo(repo_path: Path, fix: bool = False) -> Dict[str, List[str]]:
    """Scan a repo for all known frictions."""
    results = {}
    for friction in FRICTIONS:
        issues = friction.check_fn(repo_path)
        if issues:
            results[friction.id] = {
                "name": friction.name,
                "severity": friction.severity,
                "issues": issues,
                "fixed": False,
            }
            if fix and friction.fix_fn:
                # Try to fix each issue
                for issue_path in issues:
                    file_path = Path(issue_path.split(":")[0])
                    if file_path.exists():
                        if friction.fix_fn(file_path):
                            results[friction.id]["fixed"] = True
    return results


def main():
    import argparse
    parser = argparse.ArgumentParser(prog="friction-detector")
    parser.add_argument("--repo", type=str, default=".", help="Repo path to scan")
    parser.add_argument("--fix", action="store_true", help="Auto-fix detected issues")
    args = parser.parse_args()

    repo_path = Path(args.repo).resolve()
    if not repo_path.exists():
        print(f"ERROR: {repo_path} does not exist")
        sys.exit(1)

    print(f"[FRICTION-DETECTOR] Scanning: {repo_path}")
    print(f"[FRICTION-DETECTOR] Auto-fix: {'ON' if args.fix else 'OFF'}")
    print("=" * 60)

    results = scan_repo(repo_path, fix=args.fix)

    if not results:
        print("[OK] No frictions detected.")
        sys.exit(0)

    critical = 0
    warnings = 0
    for fid, data in sorted(results.items()):
        sev = data["severity"]
        icon = "[CRIT]" if sev == "critical" else "[WARN]"
        print(f"\n{icon} [{fid}] {data['name']} ({sev})")
        for issue in data["issues"]:
            print(f"   -> {issue}")
        if data.get("fixed"):
            print(f"   [FIXED]")
        if sev == "critical":
            critical += 1
        else:
            warnings += 1

    print(f"\n{'='*60}")
    print(f"Summary: {critical} critical, {warnings} warnings")

    if critical > 0:
        print("Run with --fix to auto-correct where possible.")
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
