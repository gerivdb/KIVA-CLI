"""KIVA-008 — kiva pipeline commands (Sprint 2+3).

Group: kiva pipeline
Commands:
  list                  List discovered pipeline YAML definitions
  validate <name>       Validate DAG (cycle check + schema)
  show <name>           Show detailed step table for a pipeline
  run <name>            Execute a pipeline (subprocess per step)
  history               Show last N PIPELINE_RUN WAL events
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

import click

from kiva_cli.core.pipeline_loader import detect_cycles, load_pipeline
from kiva_cli.core.pipeline_types import HAS_PIPELINE


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

DEFAULT_PIPELINES_DIR = Path(".kiva") / "pipelines"


def _pipelines_dir() -> Path:
    """Resolve pipeline YAML directory (cwd-relative or env override)."""
    env = os.environ.get("KIVA_PIPELINES_DIR")
    return Path(env) if env else DEFAULT_PIPELINES_DIR


def _find_yaml(name: str) -> Optional[Path]:
    """Locate <name>.yaml in the pipelines directory."""
    base = _pipelines_dir()
    for suffix in (".yaml", ".yml"):
        candidate = base / f"{name}{suffix}"
        if candidate.exists():
            return candidate
    return None


def _status_icon(status: str) -> str:
    icons = {
        "SUCCESS": "[OK]",
        "FAILED": "[FAIL]",
        "SKIPPED": "[SKIP]",
        "ABORTED": "[STOP]",
        "PENDING": "[...]",
    }
    return icons.get(status, f"[{status}]")


# ---------------------------------------------------------------------------
# Group
# ---------------------------------------------------------------------------

@click.group("pipeline", short_help="Pipeline chain execution (KIVA-008)")
def pipeline_cli():
    """Manage and execute KIVA pipeline chains.

    Pipelines are YAML files stored in .kiva/pipelines/.
    Each pipeline defines an ordered DAG of shell steps with
    dependency resolution via graphlib.TopologicalSorter.

    Override pipeline directory: KIVA_PIPELINES_DIR env var.
    CI mode (no interactive prompts): KIVA_CI=1 env var.
    """
    if not HAS_PIPELINE:
        click.echo("[pipeline] Feature disabled (KIVA_HAS_PIPELINE=0). Aborting.", err=True)
        raise SystemExit(1)


# ---------------------------------------------------------------------------
# list
# ---------------------------------------------------------------------------

@pipeline_cli.command("list")
def pipeline_list():
    """List all pipeline YAML definitions discovered in .kiva/pipelines/."""
    base = _pipelines_dir()
    if not base.exists():
        click.echo(f"No pipelines directory found: {base}")
        click.echo("Create .kiva/pipelines/ and add YAML definitions to get started.")
        return

    yamls = sorted(base.glob("*.yaml")) + sorted(base.glob("*.yml"))
    if not yamls:
        click.echo(f"No pipeline definitions found in {base}")
        return

    click.echo(f"Pipelines in {base}:")
    for y in yamls:
        try:
            p = load_pipeline(y)
            click.echo(f"  {p.name:<24} {len(p.steps)} steps   {p.description[:60]}")
        except Exception as exc:
            click.echo(f"  {y.stem:<24} [PARSE ERROR] {exc}")


# ---------------------------------------------------------------------------
# validate
# ---------------------------------------------------------------------------

@pipeline_cli.command("validate")
@click.argument("name")
def pipeline_validate(name: str):
    """Validate a pipeline DAG: schema check + cycle detection.

    NAME is the pipeline stem (e.g. 'build' for .kiva/pipelines/build.yaml).
    """
    path = _find_yaml(name)
    if path is None:
        click.echo(f"[ERROR] Pipeline not found: '{name}' in {_pipelines_dir()}", err=True)
        raise SystemExit(1)

    try:
        p = load_pipeline(path)
    except Exception as exc:
        click.echo(f"[ERROR] Failed to parse pipeline '{name}': {exc}", err=True)
        raise SystemExit(1)

    cycles = detect_cycles(p.steps)
    if cycles:
        click.echo(f"[FAIL] Pipeline '{name}' has a dependency cycle: {cycles}", err=True)
        raise SystemExit(1)

    click.echo(f"[OK] Pipeline '{name}' is valid ({len(p.steps)} steps)")
    for s in p.steps:
        deps = f"  <- {', '.join(s.depends_on)}" if s.depends_on else ""
        click.echo(f"  {s.name:<24} on_failure={s.on_failure:<8}{deps}")


# ---------------------------------------------------------------------------
# show
# ---------------------------------------------------------------------------

@pipeline_cli.command("show")
@click.argument("name")
def pipeline_show(name: str):
    """Show detailed step table for a pipeline (Sprint 3)."""
    path = _find_yaml(name)
    if path is None:
        click.echo(f"[ERROR] Pipeline not found: '{name}'", err=True)
        raise SystemExit(1)

    try:
        p = load_pipeline(path)
    except Exception as exc:
        click.echo(f"[ERROR] {exc}", err=True)
        raise SystemExit(1)

    click.echo(f"Pipeline : {p.name}")
    click.echo(f"Version  : {p.version}")
    click.echo(f"Status   : {p.nexus_status}")
    if p.description:
        click.echo(f"Desc     : {p.description}")
    click.echo("")
    click.echo(f"{'#':<4} {'Step':<24} {'Command':<36} {'on_failure':<10} {'Depends on'}")
    click.echo("-" * 90)
    for i, s in enumerate(p.steps, 1):
        deps = ", ".join(s.depends_on) if s.depends_on else "-"
        cmd = s.command[:34] + ".." if len(s.command) > 36 else s.command
        click.echo(f"{i:<4} {s.name:<24} {cmd:<36} {s.on_failure:<10} {deps}")


# ---------------------------------------------------------------------------
# run
# ---------------------------------------------------------------------------

@pipeline_cli.command("run")
@click.argument("name")
@click.option("--dry-run", is_flag=True, default=False, help="Simulate execution without running commands.")
@click.option("--verbose", "-v", is_flag=True, default=False, help="Show stdout/stderr per step.")
@click.option("--ci", is_flag=True, default=False, help="Force CI-safe mode (no interactive prompts).")
def pipeline_run(name: str, dry_run: bool, verbose: bool, ci: bool):
    """Execute a pipeline by NAME.

    Steps run in topological order. Behaviour on non-zero exit
    is controlled by each step's on_failure field:
      abort    (default) -- stop immediately
      warn     -- log warning, continue
      continue -- silently skip and continue
    """
    if ci:
        os.environ["KIVA_CI"] = "1"

    path = _find_yaml(name)
    if path is None:
        click.echo(f"[ERROR] Pipeline not found: '{name}' in {_pipelines_dir()}", err=True)
        raise SystemExit(1)

    try:
        p = load_pipeline(path)
    except Exception as exc:
        click.echo(f"[ERROR] Failed to parse pipeline '{name}': {exc}", err=True)
        raise SystemExit(1)

    # Import runner here to keep boot-time import cost zero when not used
    from kiva_cli.core.pipeline_runner import run_pipeline

    result = run_pipeline(p, dry_run=dry_run, verbose=verbose)

    click.echo("")
    click.echo(f"Pipeline '{result.pipeline_name}' finished: {result.status}")
    click.echo(f"intent_hash : {result.intent_hash}")
    click.echo(f"duration    : {result.duration_s:.2f}s")
    click.echo("")
    click.echo(f"{'Step':<24} {'Status':<10} {'Duration':>8}  Command")
    click.echo("-" * 80)
    for sr in result.steps:
        cmd_hint = ""
        for s in p.steps:
            if s.name == sr.step_name:
                cmd_hint = s.command[:36]
                break
        click.echo(
            f"{sr.step_name:<24} {_status_icon(sr.status):<10} {sr.duration_s:>7.2f}s  {cmd_hint}"
        )
        if verbose and (sr.stdout or sr.stderr):
            if sr.stdout:
                click.echo(f"  stdout: {sr.stdout[:200]}")
            if sr.stderr:
                click.echo(f"  stderr: {sr.stderr[:200]}")

    if result.status == "FAILED":
        raise SystemExit(1)


# ---------------------------------------------------------------------------
# history
# ---------------------------------------------------------------------------

@pipeline_cli.command("history")
@click.option("--limit", "-n", default=20, show_default=True, help="Max WAL events to show.")
def pipeline_history(limit: int):
    """Show last N PIPELINE_RUN events from WAL (Sprint 3)."""
    try:
        from kiva_cli.core.global_wal_manager import GlobalWALManager
        wal = GlobalWALManager()
        events = wal.get_events(event_type="PIPELINE_RUN", limit=limit)
    except Exception as exc:
        click.echo(f"[WARN] WAL unavailable: {exc}")
        click.echo("No pipeline history available.")
        return

    if not events:
        click.echo("No PIPELINE_RUN events found in WAL.")
        return

    click.echo(f"Last {len(events)} PIPELINE_RUN events:")
    click.echo(f"{'Timestamp':<22} {'Pipeline':<24} {'Status':<10} {'intent_hash'}")
    click.echo("-" * 80)
    for ev in events:
        payload = ev.get("payload") or ev.get("data") or {}
        ts = ev.get("timestamp", ev.get("created_at", "-"))
        pname = payload.get("pipeline_name", payload.get("name", "-"))
        status = payload.get("status", "-")
        ihash = payload.get("intent_hash", "-")
        click.echo(f"{str(ts)[:21]:<22} {pname:<24} {status:<10} {ihash}")
