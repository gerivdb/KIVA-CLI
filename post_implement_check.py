#!/usr/bin/env python3
"""
POST-IMPLEMENT CHECK v1.0 -- HOTL (Human-Out-The-Loop)
IntentHash: 0xPOST_IMPL_CHECK_20260615
Alias note (PRD-MOC GEN-009): "Human-Out-The-Loop" = niveau A3 (HOTL inactif)
de l'echelle AXE-0 -- ONTOLOGY/concepts/autonomy-ladder.md.
"""

import argparse
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Fix Windows encoding
if sys.stdout.encoding != "utf-8":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# ASCII-safe checkmarks
OK = "[OK]"
FAIL = "[FAIL]"
WARN = "[WARN]"

# MOX path
MOX_PATH = Path(r"D:\DO\WEB\TOOLS\L2-PLATFORM\MOX\mox.py")
VALIDATOR_PATH = Path(r"D:\DO\WEB\TOOLS\L2-PLATFORM\MOX\validator.py")


# -------------------------------------------------------------
# Friction checks (same as friction_detector.py, inlined for autonomy)
# -------------------------------------------------------------

def check_f3_precommit_shebang(repo_path: Path) -> List[str]:
    hook = repo_path / ".githooks" / "pre-commit"
    if not hook.exists():
        return []
    content = hook.read_text(encoding="utf-8", errors="replace")
    if content.startswith("#!python") and not content.startswith("#!/usr/bin/env python3"):
        return [str(hook)]
    return []


def fix_f3(repo_path: Path) -> bool:
    hook = repo_path / ".githooks" / "pre-commit"
    if not hook.exists():
        return False
    content = hook.read_text(encoding="utf-8")
    if content.startswith("#!python"):
        content = content.replace("#!python", "#!/usr/bin/env python3", 1)
        hook.write_text(content, encoding="utf-8")
        return True
    return False


def check_f8_message_context(repo_path: Path) -> List[str]:
    issues = []
    for py_file in repo_path.rglob("*.py"):
        if "__pycache__" in str(py_file):
            continue
        # Skip self (this file and friction_detector.py contain the pattern in their checks)
        if py_file.name in ("post_implement_check.py", "friction_detector.py"):
            continue
        try:
            content = py_file.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        if "MessageContext(" in content:
            pattern = r'MessageContext\s*\(\s*(?:source|destination|priority|payload_size|timestamp)\s*='
            for i, line in enumerate(content.split("\n"), 1):
                if re.search(pattern, line):
                    issues.append(f"{py_file}:{i}")
    return issues


def check_f8_nonexistent_method(repo_path: Path) -> List[str]:
    issues = []
    for py_file in repo_path.rglob("*.py"):
        if "__pycache__" in str(py_file):
            continue
        # Skip self
        if py_file.name in ("post_implement_check.py", "friction_detector.py"):
            continue
        try:
            content = py_file.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        if "calculate_optimal_route" in content:
            for i, line in enumerate(content.split("\n"), 1):
                if "calculate_optimal_route" in line:
                    issues.append(f"{py_file}:{i}")
    return issues


def check_f9_circular_import(repo_path: Path) -> List[str]:
    dispatch = repo_path / "cli_tools" / "anything" / "dispatch_anything.py"
    if dispatch.exists():
        content = dispatch.read_text(encoding="utf-8", errors="replace")
        if "from .transport import bdcp_transport" in content:
            return [str(dispatch)]
    return []


def check_f10_no_tests(repo_path: Path) -> List[str]:
    test_file = repo_path / "tests" / "test_anything_cli.py"
    if not test_file.exists():
        return ["tests/test_anything_cli.py missing"]
    return []


def check_hook_executable(repo_path: Path) -> List[str]:
    hook = repo_path / ".githooks" / "pre-commit"
    if hook.exists() and not os.access(str(hook), os.X_OK):
        return [str(hook)]
    return []


def fix_hook_executable(repo_path: Path) -> bool:
    hook = repo_path / ".githooks" / "pre-commit"
    if hook.exists():
        try:
            os.chmod(str(hook), 0o755)
            return True
        except Exception:
            pass
    return False


def check_anything_init_completeness(repo_path: Path) -> List[str]:
    """Check that __init__.py exports all tools in TOOL_MAP."""
    init_file = repo_path / "cli_tools" / "anything" / "__init__.py"
    if not init_file.exists():
        return ["cli_tools/anything/__init__.py missing"]
    content = init_file.read_text(encoding="utf-8", errors="replace")
    if "TOOL_MAP" not in content:
        return ["TOOL_MAP not found in __init__.py"]
    return []


def check_cli_entry_point(repo_path: Path) -> List[str]:
    """Check that cli.py has --list, --tool, --args, --json flags."""
    cli_file = repo_path / "cli_tools" / "anything" / "cli.py"
    if not cli_file.exists():
        return ["cli_tools/anything/cli.py missing"]
    content = cli_file.read_text(encoding="utf-8", errors="replace")
    required_flags = ["--list", "--tool", "--args", "--json"]
    missing = [f for f in required_flags if f not in content]
    if missing:
        return [f"cli.py missing flags: {', '.join(missing)}"]
    return []


# MOX validation check
MOX_PATH = Path(r"D:\DO\WEB\TOOLS\L2-PLATFORM\MOX\mox.py")
VALIDATOR_PATH = Path(r"D:\DO\WEB\TOOLS\L2-PLATFORM\MOX\validator.py")

def check_mox_valid(repo_path: Path) -> List[str]:
    """Validate MOX generates and validates PRD-MOC correctly."""
    issues = []
    if not MOX_PATH.exists():
        return [f"MOX not found at {MOX_PATH}"]
    if not VALIDATOR_PATH.exists():
        return [f"MOX validator not found at {VALIDATOR_PATH}"]
    try:
        # Test MOX generation
        result = subprocess.run(
            [sys.executable, str(MOX_PATH), "generate", "PLIX"],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode != 0:
            issues.append(f"mox.py generate failed: {result.stderr}")
        # Validate the actual PRD-MOC.md in the repo
        moc_file = repo_path / "PRD-MOC.md"
        if not moc_file.exists():
            issues.append(f"PRD-MOC.md not found in repo: {moc_file}")
        else:
            result = subprocess.run(
                [sys.executable, str(VALIDATOR_PATH), str(moc_file)],
                capture_output=True, text=True, timeout=30,
            )
            if result.returncode != 0:
                issues.append(f"MOX validator failed: {result.stderr}")
    except subprocess.TimeoutExpired:
        issues.append("MOX check timeout (>30s)")
    except Exception as e:
        issues.append(f"MOX check error: {e}")
    return issues


# -------------------------------------------------------------
# Registry
# -------------------------------------------------------------

CHECKS = [
    ("F3", "pre-commit shebang", "critical", check_f3_precommit_shebang, fix_f3),
    ("F8a", "MessageContext as dataclass", "critical", check_f8_message_context, None),
    ("F8b", "calculate_optimal_route missing", "critical", check_f8_nonexistent_method, None),
    ("F9", "circular import dispatch", "warning", check_f9_circular_import, None),
    ("F10", "no unit tests", "warning", check_f10_no_tests, None),
    ("FX1", "hook not executable", "warning", check_hook_executable, fix_hook_executable),
    ("CX1", "__init__.py TOOL_MAP", "critical", check_anything_init_completeness, None),
    ("CX2", "cli.py entry point flags", "critical", check_cli_entry_point, None),
    ("MOX", "MOX generate + validate", "critical", check_mox_valid, None),
]


def run_tests(repo_path: Path) -> Tuple[bool, str]:
    """Run pytest on the anything-cli tests."""
    test_file = repo_path / "tests" / "test_anything_cli.py"
    if not test_file.exists():
        return False, "No test file found"
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pytest", str(test_file), "-v", "--tb=short"],
            capture_output=True, text=True, timeout=60,
            cwd=str(repo_path),
        )
        passed = result.returncode == 0
        output = result.stdout + result.stderr
        return passed, output
    except subprocess.TimeoutExpired:
        return False, "Test timeout (>60s)"
    except Exception as e:
        return False, f"Test execution error: {e}"


def main():
    parser = argparse.ArgumentParser(prog="post-implement-check")
    parser.add_argument("--repo", type=str, default=".", help="Repo path")
    parser.add_argument("--fix", action="store_true", help="Auto-fix where possible")
    parser.add_argument("--test", action="store_true", help="Run unit tests")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    args = parser.parse_args()

    repo_path = Path(args.repo).resolve()
    print(f"[POST-IMPL] Repo: {repo_path}")
    print(f"[POST-IMPL] Auto-fix: {'ON' if args.fix else 'OFF'}")
    print(f"[POST-IMPL] Run tests: {'ON' if args.test else 'OFF'}")
    print("=" * 60)

    # -- Phase 1: Friction scan --
    print("\n[Phase 1] Friction scan...")
    total_issues = 0
    auto_fixed = 0
    manual_needed = 0

    for fid, name, severity, check_fn, fix_fn in CHECKS:
        issues = check_fn(repo_path)
        if issues:
            total_issues += len(issues)
            icon = FAIL if severity == "critical" else WARN
            print(f"  {icon} [{fid}] {name}: {len(issues)} issue(s)")
            if args.verbose:
                for issue in issues:
                    print(f"       -> {issue}")
            if args.fix and fix_fn:
                if fix_fn(repo_path):
                    print(f"       [FIXED] Auto-corrected")
                    auto_fixed += 1
                else:
                    print(f"       [WARN] Fix attempted but failed")
                    manual_needed += 1
            else:
                manual_needed += 1
        else:
            print(f"  {OK} [{fid}] {name}: OK")

    # -- Phase 2: Unit tests --
    test_passed = None
    test_output = ""
    if args.test:
        print(f"\n[Phase 2] Running unit tests...")
        test_passed, test_output = run_tests(repo_path)
        if test_passed:
            print(f"  {OK} All tests passed")
        else:
            print(f"  {FAIL} Tests failed")
            if args.verbose:
                for line in test_output.split("\n")[-20:]:
                    print(f"       {line}")

    # -- Phase 3: Summary --
    print(f"\n{'='*60}")
    print(f"[SUMMARY]")
    print(f"  Frictions found: {total_issues}")
    print(f"  Auto-fixed:      {auto_fixed}")
    print(f"  Manual needed:   {manual_needed}")
    if test_passed is not None:
        print(f"  Tests:           {'PASS' if test_passed else 'FAIL'}")

    if total_issues == 0 and (test_passed is None or test_passed):
        print(f"\n{OK} POST-IMPLEMENT CHECK PASSED -- No frictions detected.")
        sys.exit(0)
    elif manual_needed == 0 and auto_fixed > 0 and (test_passed is None or test_passed):
        print(f"\n{OK} POST-IMPLEMENT CHECK PASSED -- All frictions auto-fixed.")
        sys.exit(0)
    else:
        print(f"\n{FAIL} POST-IMPLEMENT CHECK FAILED -- {manual_needed} issue(s) need attention.")
        if not args.fix:
            print("  Re-run with --fix to auto-correct where possible.")
        sys.exit(1)


if __name__ == "__main__":
    main()
