#!/usr/bin/env python3
"""Bisect test script for INTENT-017 acceleration toolchain.

Returns 0 if all target tests pass, 1 otherwise.
Target: 62 failing tests across legacy refactored test files.
"""

import subprocess
import sys

# Target test files that should pass after fix
TARGET_TESTS = [
    "tests/test_kiva_cli.py",
    "tests/test_pipeline_retry.py",
    "tests/test_parallel_on_failure.py",
    "tests/test_parallel_executor.py",
    "tests/test_neurosymbolic_bridge.py",
    "tests/test_integration.py",
    "tests/test_ecos_kiva_integration.py",
    "tests/test_auto_chain_manager.py",
    "tests/test_citizen_commands.py",
    "tests/test_commit_ir.py",
    "tests/test_pipeline_manager.py",
    "tests/legacy_root_tests/test_registry_full_cmd.py",
    "tests/legacy_root_tests/test_registry_step.py",
]


def run_tests():
    """Run target tests and return True if all pass."""
    cmd = [
        sys.executable,
        "-m", "pytest",
        "-q",
        "--tb=no",
        "--no-cov",
        "-x",
    ] + TARGET_TESTS
    
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=300,
    )
    
    # Print summary for bisect log
    print(result.stdout[-500:] if len(result.stdout) > 500 else result.stdout)
    if result.stderr:
        print(result.stderr[-500:] if len(result.stderr) > 500 else result.stderr)
    
    return result.returncode == 0


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
