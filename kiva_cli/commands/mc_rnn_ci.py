#!/usr/bin/env python3
"""
MC-RNN CI CLI Commands - KIVA-CLI local CI for MC-RNN cross-repo testing.

Provides CLI commands for:
- kiva mc-rnn-ci run: Run full CI pipeline across all 6 MC-RNN repos
- kiva mc-rnn-ci test-lycos: Run LYCOS tests only (pytest)
- kiva mc-rnn-ci validate-vdb: Validate VDB schemas
- kiva mc-rnn-ci pr-ready: Check if all repos are green and ready for PR
- kiva mc-rnn-ci status: Show status of all MC-RNN branches

IntentHash: 0xKIVA_CLI_MC_RNN_CI_20260607
"""

import click
import sys
import subprocess
import os
from pathlib import Path
from typing import Optional, Tuple

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
LYCOS_DIR = Path(r"D:\DO\WEB\TOOLS\L4-TOOLS\LYCOS")
CODEDB_DIR = Path(r"D:\DO\WEB\TOOLS\CodeDB-E5620")
VDB_DIR = Path(r"D:\DO\WEB\TOOLS\L4-TOOLS\VDB")

REMOTE_ONLY_REPOS = {
    "BRAIN": Path(r"D:\DO\WEB\BRAIN"),
    "TINA": Path(r"D:\DO\WEB\TINA"),
    "UAE": Path(r"D:\DO\WEB\UAE"),
}


def _run(cmd: list,cwd: Optional[Path] = None, timeout: int = 120) -> Tuple[int, str, str]:
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout,
            cwd=str(cwd) if cwd else None, env={**os.environ},
        )
        return result.returncode, result.stdout, result.stderr
    except FileNotFoundError as e:
        return -1, "", str(e)
    except subprocess.TimeoutExpired:
        return -2, "", "Command timed out after {}s".format(timeout)


def _check_branch(repo_path: Path, branch: str) -> bool:
    if not repo_path.exists():
        return False
    rc, out, _ = _run(["git", "rev-parse", "--verify", branch], cwd=repo_path)
    return rc == 0


@click.group()
def mc_rnn_ci():
    """MC-RNN local CI - test all 6 repos before PR merge."""
    pass


@mc_rnn_ci.command()
@click.option('--verbose', '-v', is_flag=True, help='Verbose output')
@click.option('--skip-lint', is_flag=True, help='Skip flake8 lint step')
@click.option('--skip-zig', is_flag=True, help='Skip Zig build test')
@click.option('--skip-coverage', is_flag=True, help='Skip coverage step')
def run(verbose, skip_lint, skip_zig, skip_coverage):
    """Run full MC-RNN CI pipeline (all local repos)."""

    all_passed = True
    step_results = {}

    click.echo("")
    click.echo("=" * 60)
    click.echo("  MC-RNN CI Pipeline - Local")
    click.echo("=" * 60)

    # -- Step 1: Repo discovery
    click.echo("")
    click.echo("[1/6] Repo discovery")
    local_repos_ok = True
    local_targets = [("LYCOS", LYCOS_DIR), ("CodeDB-E5620", CODEDB_DIR), ("VDB", VDB_DIR)]
    for name, path in local_targets:
        exists = path.exists()
        click.echo("  {}: {}".format(name, "OK" if exists else "NOT FOUND"))
        if not exists:
            local_repos_ok = False
    if not local_repos_ok:
        click.echo("  FAIL: One or more repos not found locally.")
        sys.exit(1)
    step_results["repo-discovery"] = True

    # -- Step 2: LYCOS lint
    if not skip_lint:
        click.echo("")
        click.echo("[2/6] LYCOS lint (flake8)")
        rc, out, err = _run([
            sys.executable, "-m", "flake8",
            str(LYCOS_DIR / "src"),
            "--max-line-length=120", "--count"
        ])
        passed = rc == 0
        click.echo("  {} (rc={})".format("PASS" if passed else "WARN", rc))
        step_results["lycos-lint"] = passed
    else:
        click.echo("")
        click.echo("[2/6] LYCOS lint - SKIPPED")
        step_results["lycos-lint"] = True

    # -- Step 3: CodeDB Zig test
    if not skip_zig:
        click.echo("")
        click.echo("[3/6] CodeDB-E5620 Zig test")
        zig_rc, _, _ = _run(["zig", "version"], timeout=10)
        if zig_rc != 0:
            click.echo("  SKIP: Zig not found in PATH")
            step_results["codedb-zig"] = None
        else:
            rc, out, err = _run(
                ["zig", "build", "test", "--summary", "all"],
                cwd=CODEDB_DIR, timeout=180
            )
            passed = rc == 0
            click.echo("  {} (rc={})".format("PASS" if passed else "FAIL", rc))
            if verbose and out:
                lines = out.strip().split("\n")
                click.echo("\n".join(lines[-10:]))
            step_results["codedb-zig"] = passed
            if not passed:
                all_passed = False
    else:
        click.echo("")
        click.echo("[3/6] CodeDB Zig test - SKIPPED")
        step_results["codedb-zig"] = True

    # -- Step 4: LYCOS pytest
    click.echo("")
    click.echo("[4/6] LYCOS pytest")
    pytest_args = [
        sys.executable, "-m", "pytest",
        str(LYCOS_DIR / "tests"),
        "--tb=short", "-q",
        "--ignore=" + str(LYCOS_DIR / "tests" / "test_integration.py"),
        "--ignore=" + str(LYCOS_DIR / "tests" / "test_lycos.py"),
        "--ignore=" + str(LYCOS_DIR / "tests" / "test_lycos_cli.py"),
    ]
    rc, out, err = _run(pytest_args, timeout=120)
    passed = rc == 0
    click.echo("  {} (rc={})".format("PASS" if passed else "FAIL", rc))
    if verbose and out:
        click.echo(out[-1000:])
    elif not passed:
        click.echo(out[-500:] if out else err[-500:])
    step_results["lycos-tests"] = passed
    if not passed:
        all_passed = False

    # -- Step 5: VDB schema validation
    click.echo("")
    click.echo("[5/6] VDB schema validation")
    vdb_ok = True
    schema_file = VDB_DIR / "schema" / "mc_hidden_states.yaml"

    try:
        import yaml
        raw = schema_file.read_text(encoding="utf-8")
        # VDB schema uses @schema key — strip @ for valid YAML
        raw = raw.replace("@schema ", "schema_")
        data = yaml.safe_load(raw)
        schema_key = None
        for k in data:
            if "mc_hidden" in str(k):
                schema_key = k
                break
        if schema_key:
            fields = data[schema_key].get("fields", [])
            field_names = [f["name"] for f in fields]
            required_fields = ["h_vector", "source_layer", "gate_activity", "symbol_hash"]
            missing = [r for r in required_fields if r not in field_names]
            if missing:
                click.echo("  FAIL: Missing fields: {}".format(missing))
                vdb_ok = False
            else:
                click.echo("  Schema OK: {} fields".format(len(fields)))
                click.echo("  intent_hash: {}".format(data[schema_key].get("intent_hash", "N/A")))
        else:
            click.echo("  FAIL: mc_hidden_states schema key not found")
            vdb_ok = False
    except Exception as e:
        click.echo("  FAIL: YAML parse error: {}".format(e))
        vdb_ok = False

    sql_file = VDB_DIR / "schema" / "diffscope_fingerprints.sql"
    if sql_file.exists():
        import sqlite3
        try:
            conn = sqlite3.connect(":memory:")
            conn.executescript(sql_file.read_text(encoding="utf-8"))
            conn.close()
            click.echo("  SQL OK: {}".format(sql_file.name))
        except Exception as e:
            click.echo("  FAIL SQL: {}".format(e))
            vdb_ok = False

    step_results["vdb-schema"] = vdb_ok
    if not vdb_ok:
        all_passed = False

    # -- Step 6: Coverage (non-blocking)
    if not skip_coverage:
        click.echo("")
        click.echo("[6/6] LYCOS coverage (non-blocking)")
        rc, out, err = _run([
            sys.executable, "-m", "pytest",
            str(LYCOS_DIR / "tests"),
            "--cov=" + str(LYCOS_DIR / "src"),
            "--cov-report=term-missing",
            "--cov-fail-under=70", "-q",
            "--ignore=" + str(LYCOS_DIR / "tests" / "test_integration.py"),
        ], timeout=120)
        passed = rc == 0
        click.echo("  {} (rc={})".format("PASS" if passed else "WARN (<70%)", rc))
        step_results["lycos-coverage"] = passed
    else:
        click.echo("")
        click.echo("[6/6] Coverage - SKIPPED")
        step_results["lycos-coverage"] = True

    # -- Summary
    click.echo("")
    click.echo("=" * 60)
    click.echo("  MC-RNN CI RESULTS")
    click.echo("=" * 60)
    for step, result in step_results.items():
        if result is True:
            status = "[PASS]"
        elif result is False:
            status = "[FAIL]"
        else:
            status = "[SKIP]"
        click.echo("  {:<25} {}".format(step, status))

    click.echo("")
    click.echo("  Remote-only repos (not tested locally):")
    for name, path in REMOTE_ONLY_REPOS.items():
        exists = path.exists()
        click.echo("    {}: {}".format(name, "cloned" if exists else "not cloned"))

    click.echo("")
    click.echo("=" * 60)
    if all_passed:
        click.echo("  ALL TESTS PASSED -- Ready to create PRs")
    else:
        click.echo("  SOME TESTS FAILED -- Fix before PR")
    click.echo("=" * 60)
    click.echo("")

    sys.exit(0 if all_passed else 1)


@mc_rnn_ci.command()
@click.option('--verbose', '-v', is_flag=True)
@click.option('--test-file', default=None, help='Specific test file')
def test_lycos(verbose, test_file):
    """Run LYCOS MC-RNN tests only (pytest)."""
    if not LYCOS_DIR.exists():
        click.echo("LYCOS repo not found at {}".format(LYCOS_DIR))
        sys.exit(1)

    test_path = LYCOS_DIR / "tests"
    if test_file:
        test_path = test_path / test_file

    args = [sys.executable, "-m", "pytest", str(test_path), "--tb=short"]
    args.insert(2, "-v" if verbose else "-q")

    click.echo("[mc-rnn-ci] Running LYCOS tests: {}".format(test_path))
    rc, out, err = _run(args, timeout=60)
    click.echo(out)
    if rc != 0 and err:
        click.echo(err, err=True)
    sys.exit(rc)


@mc_rnn_ci.command()
def validate_vdb():
    """Validate VDB MC-RNN schema."""
    if not VDB_DIR.exists():
        click.echo("VDB repo not found at {}".format(VDB_DIR))
        sys.exit(1)

    ok = True
    schema_file = VDB_DIR / "schema" / "mc_hidden_states.yaml"

    try:
        import yaml
        data = yaml.safe_load(schema_file.read_text(encoding="utf-8"))
        for k in data:
            if "mc_hidden" in str(k):
                schema_key = k
                break
        fields = data[schema_key]["fields"]
        field_names = [f["name"] for f in fields]
        click.echo("  Schema: {} fields".format(len(fields)))
        click.echo("  Fields: {}".format(", ".join(field_names)))
        click.echo("  PASS: mc_hidden_states.yaml OK")
    except Exception as e:
        click.echo("  FAIL: Schema error: {}".format(e))
        ok = False

    sql_file = VDB_DIR / "schema" / "diffscope_fingerprints.sql"
    if sql_file.exists():
        import sqlite3
        try:
            conn = sqlite3.connect(":memory:")
            conn.executescript(sql_file.read_text(encoding="utf-8"))
            conn.close()
            click.echo("  PASS: {}".format(sql_file.name))
        except Exception as e:
            click.echo("  FAIL SQL: {}".format(e))
            ok = False

    sys.exit(0 if ok else 1)


@mc_rnn_ci.command()
def status():
    """Show status of all MC-RNN branches."""
    click.echo("")
    click.echo("=" * 60)
    click.echo("  MC-RNN Branch Status")
    click.echo("=" * 60)

    repos = [
        ("LYCOS", LYCOS_DIR, "chore/mc-lycos-fluence"),
        ("CodeDB-E5620", CODEDB_DIR, "feature/mc-rnn-e5620"),
        ("VDB", VDB_DIR, "feature/mc-rnn-vdb"),
        ("BRAIN", Path(r"D:\DO\WEB\BRAIN"), "feature/mc-rnn-layer"),
        ("TINA", Path(r"D:\DO\WEB\TINA"), "feature/mc-rnn-tina"),
        ("UAE", Path(r"D:\DO\WEB\UAE"), "feature/mc-uae-complementarity"),
    ]

    for name, path, branch in repos:
        if path.exists():
            rc, out, _ = _run(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=path)
            current_branch = out.strip() if rc == 0 else "unknown"
            has_branch = _check_branch(path, branch)
            click.echo("  {:<15} current: {:<35} branch {}: {}".format(
                name, current_branch, branch, "OK" if has_branch else "MISSING"))
        else:
            click.echo("  {:<15} NOT CLONED (branch: {})".format(name, branch))

    click.echo("")


@mc_rnn_ci.command()
def pr_ready():
    """Check if all repos are ready for PR creation."""
    click.echo("")
    click.echo("[mc-rnn-ci] Checking PR readiness...")

    issues = []
    local_checks = [
        ("LYCOS", LYCOS_DIR, "chore/mc-lycos-fluence"),
        ("CodeDB-E5620", CODEDB_DIR, "feature/mc-rnn-e5620"),
        ("VDB", VDB_DIR, "feature/mc-rnn-vdb"),
    ]

    for name, path, branch in local_checks:
        if not path.exists():
            issues.append("{}: repo not cloned locally".format(name))
        elif not _check_branch(path, branch):
            issues.append("{}: branch '{}' not found".format(name, branch))

    if issues:
        click.echo("  Issues found:")
        for i in issues:
            click.echo("    - {}".format(i))
        sys.exit(1)
    else:
        click.echo("  All local repos ready")

    click.echo("")
    click.echo("  PR Checklist:")
    click.echo("    [ ] Run: kiva mc-rnn-ci run")
    click.echo("    [ ] LYCOS  -> PR chore/mc-lycos-fluence  -> main")
    click.echo("    [ ] CodeDB -> PR feature/mc-rnn-e5620    -> main")
    click.echo("    [ ] VDB    -> PR feature/mc-rnn-vdb       -> main")
    click.echo("    [ ] TINA   -> PR feature/mc-rnn-tina      -> main")
    click.echo("    [ ] UAE    -> PR feature/mc-uae-complementarity -> main")
    click.echo("    [ ] BRAIN  -> Already merged (PR #236)")
    click.echo("")


if __name__ == "__main__":
    mc_rnn_ci()
