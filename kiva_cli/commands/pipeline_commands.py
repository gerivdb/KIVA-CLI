"""KIVA-009 Sprint 4 — kiva pipeline commands (enriched show + run stats).

Group: kiva pipeline
Commands:
  list                  List discovered pipeline YAML definitions
  validate <name>       Validate DAG (cycle check + schema)
  show <name>           Show detailed step table (with when: + parallel_groups)
  run <name>            Execute a pipeline (subprocess per step)
  history               Show last N PIPELINE_RUN WAL events
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

import click

from kiva_cli.core.pipeline_loader import detect_cycles, load_pipeline, resolve_order
from kiva_cli.core.pipeline_types import HAS_PIPELINE, StepResult
from kiva_cli.core.auto_chain_manager import AutoChainManager, get_auto_chain_manager


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

DEFAULT_PIPELINES_DIR = Path(".kiva") / "pipelines"

# ASCII-safe replacements (cp1252 / Windows console compatibility)
_SEP   = "-"   # table separator
_PIPE  = "|"
_ARROW = "->"  # step description

# High-level orchestrator (PRD-KIVA-008)
_manager = get_auto_chain_manager()


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


def _when_summary(when: str) -> str:
    """Produce a compact human-readable summary of a step's when: expression.

    KIVA-011: when is now a plain string expression.
    - Empty / falsy  -> "-"   (always runs)
    - Non-empty      -> truncated to 28 chars (with ".." suffix if truncated)

    Examples:
      -
      last_status == 'SUCCESS'
      not dry_run
      parallel_groups_executed > 0..
    """
    if not when or not when.strip():
        return "-"
    expr = when.strip()
    return (expr[:26] + "..") if len(expr) > 28 else expr


def _parallel_group_index(step_name: str, parallel_groups: list) -> str:
    """Return 'P<idx>' if step_name is in a parallel group, else 'SEQ'."""
    for idx, group in enumerate(parallel_groups):
        if step_name in group:
            return f"P{idx}"
    return "SEQ"


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
    """List all named declarative pipelines (KIVA-008)."""
    names = _manager.list_pipelines()
    if not names:
        click.echo("No pipelines found.")
        click.echo(f"Add YAML files in {_manager.pipelines_dir}")
        return

    click.echo(f"Available pipelines ({len(names)}):")
    for name in names:
        try:
            p = _manager.get_pipeline(name)
            pg_hint = f"  [{len(getattr(p, 'parallel_groups', []))} group(s)]" if getattr(p, 'parallel_groups', None) else ""
            desc = getattr(p, 'description', '') or ''
            click.echo(f"  {name:<24} {len(p.steps)} steps{pg_hint}   {desc[:52]}")
        except Exception as e:
            click.echo(f"  {name:<24} [ERROR] {e}")
        except Exception as exc:
            click.echo(f"  {y.stem:<24} [PARSE ERROR] {exc}")


# ---------------------------------------------------------------------------
# validate
# ---------------------------------------------------------------------------

@pipeline_cli.command("validate")
@click.argument("name")
def pipeline_validate(name: str):
    """Validate a named declarative pipeline (KIVA-008)."""
    result = _manager.validate(name)
    if not result.valid:
        click.echo(f"[FAIL] Pipeline '{name}' is invalid:", err=True)
        for e in result.errors:
            click.echo(f"  - {e}", err=True)
        raise SystemExit(1)

    click.echo(f"[OK] Pipeline '{name}' is valid.")
    if result.warnings:
        for w in result.warnings:
            click.echo(f"  [WARN] {w}")
        click.echo(f"  {s.name:<24} on_failure={s.on_failure:<8}{deps}{when_hint}")


# ---------------------------------------------------------------------------
# show  (Sprint 4 enriched + KIVA-011 when: str)
# ---------------------------------------------------------------------------

@pipeline_cli.command("show")
@click.argument("name")
@click.option("--no-when", is_flag=True, default=False, help="Hide when: column.")
@click.option("--no-groups", is_flag=True, default=False, help="Hide parallel groups section.")
def pipeline_show(name: str, no_when: bool, no_groups: bool):
    """Show detailed step table for a pipeline.

    Displays when: expression per step and parallel_groups layout.
    Use --no-when / --no-groups to suppress those sections.
    """
    path = _find_yaml(name)
    if path is None:
        click.echo(f"[ERROR] Pipeline not found: '{name}'", err=True)
        raise SystemExit(1)

    try:
        p = load_pipeline(path)
    except Exception as exc:
        click.echo(f"[ERROR] {exc}", err=True)
        raise SystemExit(1)

    has_parallel = bool(p.parallel_groups)
    # KIVA-011: when is a str; truthy if non-empty
    has_when = any(s.when for s in p.steps)

    # == Header ==============================================================
    click.echo(f"Pipeline : {p.name}")
    click.echo(f"Version  : {p.version}")
    click.echo(f"Status   : {p.nexus_status}")
    if p.description:
        click.echo(f"Desc     : {p.description}")
    click.echo(f"Failure  : {getattr(p, 'on_failure', 'abort')} (pipeline default)")
    if has_parallel:
        workers = getattr(p, "max_workers", 4)
        click.echo(f"Parallel : {len(p.parallel_groups)} group(s) - max_workers={workers}")
    click.echo("")

    # == Step table ==========================================================
    show_when_col = has_when and not no_when
    show_group_col = has_parallel and not no_groups

    W_IDX = 4
    W_NAME = 24
    W_CMD = 34
    W_FAIL = 9
    W_DEP = 20
    W_GROUP = 6
    W_WHEN = 30   # KIVA-011: string expression truncated to 28 chars
    W_RETRY = 6

    header = f"{'#':<{W_IDX}} {'Step':<{W_NAME}} {'Command':<{W_CMD}} {'Failure':<{W_FAIL}} {'Depends on':<{W_DEP}}"
    if show_group_col:
        header += f" {'GROUP':<{W_GROUP}}"
    if show_when_col:
        header += f" {'WHEN':<{W_WHEN}}"
    header += f" {'RETRY':<{W_RETRY}}"
    sep_len = len(header)
    click.echo(header)
    click.echo(_SEP * sep_len)

    for i, s in enumerate(p.steps, 1):
        deps = ", ".join(s.depends_on) if s.depends_on else "-"
        if len(deps) > W_DEP:
            deps = deps[:W_DEP - 2] + ".."
        cmd = s.command
        if len(cmd) > W_CMD:
            cmd = cmd[:W_CMD - 2] + ".."

        row = (
            f"{i:<{W_IDX}} "
            f"{s.name:<{W_NAME}} "
            f"{cmd:<{W_CMD}} "
            f"{s.on_failure:<{W_FAIL}} "
            f"{deps:<{W_DEP}}"
        )
        if show_group_col:
            grp = _parallel_group_index(s.name, p.parallel_groups)
            row += f" {grp:<{W_GROUP}}"
        if show_when_col:
            # KIVA-011: s.when is a str
            row += f" {_when_summary(s.when):<{W_WHEN}}"
        row += f" {s.retry:<{W_RETRY}}"
        click.echo(row)

        if s.description:
            indent = " " * (W_IDX + 1 + W_NAME + 1)
            desc = s.description[:W_CMD + W_FAIL + W_DEP + W_GROUP + W_WHEN]
            click.echo(f"{indent}{_ARROW} {desc}")

    # == Parallel groups section =============================================
    if has_parallel and not no_groups:
        click.echo("")
        click.echo("Parallel groups")
        click.echo(_SEP * 50)
        for idx, group in enumerate(p.parallel_groups):
            members = "  ".join(f"{m}" for m in group)
            click.echo(f"  P{idx}  {_PIPE}  {members}")
        workers = getattr(p, "max_workers", 4)
        click.echo(f"       max_workers = {workers}")
        click.echo("")
        all_in_groups = {name for grp in p.parallel_groups for name in grp}
        seq_steps = [s.name for s in p.steps if s.name not in all_in_groups]
        if seq_steps:
            click.echo(f"  SEQ  {_PIPE}  {'  '.join(seq_steps)}")


# ---------------------------------------------------------------------------
# run
# ---------------------------------------------------------------------------

@pipeline_cli.command("run")
@click.argument("name", required=False, default=None)
@click.option("--steps", "steps_list", default=None, help="Comma-separated list of shell commands for ad-hoc execution (KIVA-007 compatibility).")
@click.option("--dry-run", is_flag=True, default=False, help="Simulate execution without running commands.")
@click.option("--verbose", "-v", is_flag=True, default=False, help="Show stdout/stderr per step.")
@click.option("--ci", is_flag=True, default=False, help="Force CI-safe mode (no interactive prompts).")
@click.option("--from", "-f", "from_step", default=None, help="Resume execution from this step (previous steps are marked SKIPPED).")
def pipeline_run(name: Optional[str], steps_list: Optional[str], dry_run: bool, verbose: bool, ci: bool, from_step: Optional[str]):
    """Execute a pipeline by NAME.

    Steps run in topological order. Behaviour on non-zero exit
    is controlled by each step's on_failure field.

    Use --from / -f to resume a previous run from a specific step.
    All steps before the target are reported as SKIPPED with reason
    "resumed from <step>".
    """
    if ci:
        os.environ["KIVA_CI"] = "1"

    # --- KIVA-008: ad-hoc mode via --steps (KIVA-007 compatibility) ---
    if steps_list:
        steps = [s.strip() for s in steps_list.split(",") if s.strip()]
        if not steps:
            click.echo("[ERROR] --steps requires at least one command", err=True)
            raise SystemExit(1)

        result = _manager.run_adhoc(steps, dry_run=dry_run, verbose=verbose)

        # Minimal reporting for ad-hoc mode
        click.echo(f"\nAd-hoc chain finished: {result.status}")
        for sr in result.steps:
            click.echo(f"  {sr.step_name:<30} {_status_icon(sr.status)}")
        if result.status == "FAILED":
            raise SystemExit(1)
        return  # done for ad-hoc case
    # --- end ad-hoc ---

    if name is None:
        click.echo("[ERROR] Either provide a pipeline NAME or use --steps", err=True)
        raise SystemExit(1)

    path = _find_yaml(name)
    if path is None:
        click.echo(f"[ERROR] Pipeline not found: '{name}' in {_pipelines_dir()}", err=True)
        raise SystemExit(1)

    try:
        p = load_pipeline(path)
    except Exception as exc:
        click.echo(f"[ERROR] Failed to parse pipeline '{name}': {exc}", err=True)
        raise SystemExit(1)

    # --- KIVA-008: --from support (resume execution) ---
    pre_skipped_results: list[StepResult] = []

    if from_step:
        try:
            ordered = resolve_order(p.steps)
            step_names = [s.name for s in ordered]

            if from_step not in step_names:
                click.echo(f"[ERROR] Step '{from_step}' not found in pipeline '{name}'", err=True)
                raise SystemExit(1)

            start_idx = step_names.index(from_step)

            # Pre-build skipped results for the prefix
            for s in ordered[:start_idx]:
                pre_skipped_results.append(
                    StepResult(
                        step_name=s.name,
                        status="SKIPPED",
                        skip_reason=f"resumed from {from_step}",
                        duration_s=0.0,
                    )
                )

            # Create a temporary pipeline with only the suffix steps
            # (avoids mutating the original p)
            from dataclasses import replace
            suffix_steps = ordered[start_idx:]
            p_to_run = replace(p, steps=suffix_steps)

        except Exception as e:
            click.echo(f"[ERROR] Failed to process --from {from_step}: {e}", err=True)
            raise SystemExit(1)
    else:
        p_to_run = p

    from kiva_cli.core.pipeline_runner import run_pipeline

    result = run_pipeline(p_to_run, dry_run=dry_run, verbose=verbose)

    # Merge pre-skipped results at the beginning
    if pre_skipped_results:
        result.steps = pre_skipped_results + list(result.steps)

    click.echo("")
    click.echo(f"Pipeline '{result.pipeline_name}' finished: {result.status}")
    click.echo(f"intent_hash : {result.intent_hash}")
    click.echo(f"duration    : {result.duration_s:.2f}s")

    pg_exec = getattr(result, "parallel_groups_executed", 0)
    if pg_exec > 0:
        wall = getattr(result, "total_parallel_wall_clock", 0.0)
        click.echo(f"parallel    : {pg_exec} group(s) ran - wall_clock={wall:.2f}s")

    click.echo("")
    click.echo(f"total_retries_used: {getattr(result, 'total_retries_used', 0)}")

    click.echo("")
    click.echo(f"{'Step':<24} {'Status':<10} {'Duration':>8}  {'Group':<6}  {'Retry':>5}  {'Skipped reason / Command'}")
    click.echo("-" * 100)
    for sr in result.steps:
        cmd_hint = ""
        grp = "SEQ"
        retry = 0
        for s in p.steps:
            if s.name == sr.step_name:
                cmd_hint = s.command[:34]
                grp = _parallel_group_index(s.name, p.parallel_groups)
                retry = s.retry
                break

        # KIVA-011: show skip_reason instead of command for SKIPPED steps
        if sr.status == "SKIPPED" and sr.skip_reason:
            detail = f"(when: {sr.skip_reason[:40]})"
        else:
            detail = cmd_hint

        click.echo(
            f"{sr.step_name:<24} {_status_icon(sr.status):<10} {sr.duration_s:>7.2f}s  {grp:<6}  {retry:>5}x  {detail}"
        )
        if verbose and sr.status != "SKIPPED" and (sr.stdout or sr.stderr):
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
    """Show last N PIPELINE_RUN events from WAL."""
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
