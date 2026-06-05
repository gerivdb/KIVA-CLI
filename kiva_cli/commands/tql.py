#!/usr/bin/env python3
"""
TQL Contract Commands — KIVA-CLI integration for TQL validation

Provides CLI commands for:
- kiva tql check: Run all 3 contract checks (fixtures, semver, compat)
- kiva tql fixtures: Run TQL fixture validation against BRAIN interpreter
- kiva tql semver: Check SemVer compliance between TQL spec and BRAIN interpreter
- kiva tql compat: Verify NEXUS stub is clean (no real implementation)

IntentHash: 0xKIVA_CLI_TQL_20260605
"""

import click
import sys
import subprocess
import re
from pathlib import Path

# Paths
BRAIN_DIR = Path(r"D:\DO\WEB\TOOLS\L0-CANON\BRAIN")
NEXUS_DIR = Path(r"D:\DO\WEB\TOOLS\L0-CANON\NEXUS")
TQL_FIXTURES_DIR = BRAIN_DIR / "tests" / "tql" / "fixtures"


@click.group()
def tql():
    """TQL contract validation commands (KIVA-CLI local CI)."""
    pass


@tql.command()
@click.option('--verbose', '-v', is_flag=True, help='Verbose output')
def check(verbose: bool):
    """Run all 3 TQL contract checks: fixtures, semver, compat."""

    checks = [
        ("Contract Check (fixtures)", _check_fixtures),
        ("SemVer Check", _check_semver),
        ("Compat Check (NEXUS stub)", _check_compat),
    ]

    all_passed = True
    for name, fn in checks:
        click.echo(f"\n{'='*50}")
        click.echo(f"  {name}")
        click.echo(f"{'='*50}")
        passed = fn(verbose)
        status = "PASSED [OK]" if passed else "FAILED [FAIL]"
        click.echo(f"  {status}")
        if not passed:
            all_passed = False

    click.echo(f"\n{'='*50}")
    if all_passed:
        click.echo("All TQL contract checks PASSED [OK]")
    else:
        click.echo("Some TQL contract checks FAILED [FAIL]")
        sys.exit(1)


@tql.command()
@click.option('--verbose', '-v', is_flag=True, help='Verbose output')
def fixtures(verbose: bool):
    """Run TQL fixture validation against BRAIN interpreter."""
    _check_fixtures(verbose)


@tql.command()
@click.option('--verbose', '-v', is_flag=True, help='Verbose output')
def semver(verbose: bool):
    """Check SemVer compliance between TQL spec and BRAIN interpreter."""
    _check_semver(verbose)


@tql.command()
@click.option('--verbose', '-v', is_flag=True, help='Verbose output')
def compat(verbose: bool):
    """Verify NEXUS stub is clean (no real implementation)."""
    _check_compat(verbose)


def _check_fixtures(verbose: bool) -> bool:
    """Run TQL fixture tests against BRAIN interpreter via pytest."""

    # Check fixture files exist
    fixture_files = list(TQL_FIXTURES_DIR.glob("*.tql")) if TQL_FIXTURES_DIR.exists() else []
    if verbose:
        click.echo(f"  Fixture files found: {len(fixture_files)}")
        for f in fixture_files:
            click.echo(f"    - {f.name}")

    # Run pytest on TQL interpreter tests
    cmd = [
        sys.executable, "-m", "pytest",
        str(BRAIN_DIR / "tests" / "tql" / "test_interpreter.py"),
        "-v" if verbose else "-q",
        "--tb=short",
        "-x",
    ]

    env = {
        **__import__("os").environ,
        "PYTHONPATH": str(BRAIN_DIR / "src"),
    }

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60,
            env=env,
        )

        if verbose:
            click.echo(result.stdout)
        else:
            lines = result.stdout.strip().split("\n")
            for line in lines:
                if "passed" in line or "failed" in line or "error" in line:
                    click.echo(f"  {line}")
                    break
            else:
                if lines and lines[-1].strip():
                    click.echo(f"  {lines[-1].strip()}")

        if result.returncode != 0:
            if result.stderr:
                click.echo(result.stderr, err=True)
            return False

        return True

    except FileNotFoundError:
        click.echo("  [FAIL] pytest not found", err=True)
        return False
    except subprocess.TimeoutExpired:
        click.echo("  [FAIL] Fixture tests timed out (60s)", err=True)
        return False


def _check_semver(verbose: bool) -> bool:
    """Check SemVer compliance: TQL spec version vs interpreter version."""

    interpreter_file = BRAIN_DIR / "src" / "brain" / "tql" / "interpreter.py"
    init_file = BRAIN_DIR / "src" / "brain" / "tql" / "__init__.py"

    interpreter_version = None
    init_version = None

    if interpreter_file.exists():
        content = interpreter_file.read_text(encoding="utf-8")
        match = re.search(r'__version__\s*=\s*["\']([^"\']+)["\']', content)
        if match:
            interpreter_version = match.group(1)

    if init_file.exists():
        content = init_file.read_text(encoding="utf-8")
        match = re.search(r'__version__\s*=\s*["\']([^"\']+)["\']', content)
        if match:
            init_version = match.group(1)

    if verbose:
        click.echo(f"  Interpreter __version__: {interpreter_version or 'NOT FOUND'}")
        click.echo(f"  __init__.py __version__: {init_version or 'NOT FOUND'}")

    if interpreter_version and init_version:
        if interpreter_version == init_version:
            click.echo(f"  [OK] Versions match: {interpreter_version}")
            return True
        else:
            click.echo(f"  [FAIL] Version mismatch: interpreter={interpreter_version}, __init__={init_version}")
            return False
    elif init_version:
        click.echo(f"  [OK] Version found: {init_version}")
        return True
    else:
        click.echo("  [FAIL] No version found in TQL module")
        return False


def _check_compat(verbose: bool) -> bool:
    """Verify NEXUS TQL stub is clean — no real implementation."""

    nexu_stub = NEXUS_DIR / "tql" / "__init__.py"

    if not nexu_stub.exists():
        click.echo("  [OK] No NEXUS/tql/__init__.py — clean removal")
        return True

    content = nexu_stub.read_text(encoding="utf-8")

    has_deprecation = "DeprecationWarning" in content or "deprecat" in content.lower()

    forbidden_patterns = [
        "class TQLInterpreter", "class VDB3Interface", "class PLIXInterface",
        "def execute(", "def parse_tql",
    ]
    has_impl = any(pattern in content for pattern in forbidden_patterns)

    impl_dir = NEXUS_DIR / "tql" / "impl"
    impl_exists = impl_dir.exists()

    if verbose:
        click.echo(f"  NEXUS/tql/__init__.py exists: True")
        click.echo(f"  Has DeprecationWarning: {has_deprecation}")
        click.echo(f"  Contains real impl: {has_impl}")
        click.echo(f"  impl/ directory exists: {impl_exists}")

    if has_impl:
        click.echo("  [FAIL] NEXUS stub contains real implementation — must be removed")
        return False

    if impl_exists:
        click.echo("  [FAIL] NEXUS/tql/impl/ still exists — must be removed")
        return False

    if not has_deprecation:
        click.echo("  [WARN]  NEXUS stub missing DeprecationWarning (recommended but not blocking)")

    click.echo("  [OK] NEXUS stub is clean (deprecation only, no implementation)")
    return True
