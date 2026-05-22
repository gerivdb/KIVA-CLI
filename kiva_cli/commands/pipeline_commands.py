"""KIVA-009 Sprint 4b — kiva pipeline commands (Windows cp1252 safe).

Group: kiva pipeline
Commands:
  list                  List discovered pipeline YAML definitions
  validate <name>       Validate DAG (cycle check + schema)
  show <name>           Show detailed step table (with when: + parallel_groups)
  run <name>            Execute a pipeline (subprocess per step)
  history               Show last N PIPELINE_RUN WAL events

Windows note: all box-drawing / Unicode chars replaced with ASCII
equivalents so cp1252 / legacy PowerShell / cmd terminals work.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

import click

from kiva_cli.core.pipeline_loader import detect_cycles, load_pipeline
from kiva_cli.core.pipeline_types import HAS_PIPELINE


# ---------------------------------------------------------------------------
# ASCII-safe decoration constants
# All chars here MUST be in cp1252 / ASCII.  No Unicode box-drawing.
# ---------------------------------------------------------------------------

_SEP  = "-"   # table column separator  (was u2500 box-drawing dash)
_PIPE = "|"   # group divider           (was u2551 double vertical)
_ARROW = "->" # step description indent (was u21b3 downward arrow)


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


def _when_summary(when_list: list) -> str:
    """Produce a compact human-readable summary of a step's when: conditions.

    Examples (ASCII-safe, no ellipsis char):
      env:SKIP_TESTS!=true
      file_exists:src/
      phi_cps:BLO<2.0
      expr:(custom)
      env:ENV=prod + file_exists:src/   (AND, multiple conditions)
    """
    if not when_list:
        return "-"

    parts: list[str] = []
    for w in when_list:
        t = getattr(w, "type", "?")
        if t == "env":
            var = getattr(w, "var", "") or ""
            eq = getattr(w, "equals", None)
            neq = getattr(w, "not_equals", None)
            if eq is not None:
                parts.append(f"env:{var}={eq}")
            elif neq is not None:
                parts.append(f"env:{var}!={neq}")
            else:
                parts.append(f"env:{var}")
        elif t == "file_exists":
            path = getattr(w, "path", "") or ""
            parts.append(f"file_exists:{path}")
        elif t == "file_changed":
            path = getattr(w, "path", "") or ""
            since = getattr(w, "since_seconds", None)
            s = f"file_changed:{path}"
            if since is not None:
                s += f"<{since}s"
            parts.append(s)
        elif t == "phi_cps":
            repo = getattr(w, "repo", "") or ""
            op = getattr(w, "op", "") or ""
            val = getattr(w, "value", "")
            op_sym = {"lt": "<", "gt": ">", "lte": "<=", "gte": ">=", "eq": "=="}.get(op, op)
            parts.append(f"phi_cps:{repo}{op_sym}{val}")
        elif t == "step_output":
            step = getattr(w, "step", "") or ""
            ec = getattr(w, "exit_code", None)
            sc = getattr(w, "stdout_contains", None)
            s = f"step:{step}"
            if ec is not None:
                s += f"[rc={ec}]"
            if sc:
                s += f"[~{sc[:10]}]"
            parts.append(s)
        elif t == "expr":
            expr = getattr(w, "expr", "") or ""
            # ASCII-safe: use '..' instead of u2026
            parts.append(f"expr:{expr[:12]}.." if len(expr) > 12 else f"expr:{expr}")
        else:
            parts.append(t)

    summary = " + ".join(parts)
    # Truncate to 28 chars; ASCII-safe truncation marker '..'
    return summary[:26] + ".." if len(summary) > 28 else summary


def _parallel_group_index(step_name: str, parallel_groups: list[list[str]]) -> str:
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
            pg_hint = f"  [{len(p.parallel_groups)} group(s)]" if p.parallel_groups else ""
            click.echo(f"  {p.name:<24} {len(p.steps)} steps{pg_hint}   {p.description[:52]}")
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
# show  (Sprint 4b -- Windows cp1252 safe)
# ---------------------------------------------------------------------------

@pipeline_cli.command("show")
@click.argument("name")
@click.option("--no-when", is_flag=True, default=False, help="Hide when: column.")
@click.option("--no-groups", is_flag=True, default=False, help="Hide parallel groups section.")
def pipeline_show(name: str, no_when: bool, no_groups: bool):
    """Show detailed step table for a pipeline.

    Displays when: conditions per step and parallel_groups layout.
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
    has_when = any(getattr(s, "when", []) for s in p.steps)

    # -- Header ----------------------------------------------------------
    click.echo(f"Pipeline : {p.name}")
    click.echo(f"Version  : {p.version}")
    click.echo(f"Status   : {p.nexus_status}")
    if p.description:
        click.echo(f"Desc     : {p.description}")
    click.echo(f"Failure  : {getattr(p, 'on_failure', 'abort')} (pipeline default)")
    if has_parallel:
        workers = getattr(p, "max_workers", 4)
        # ASCII-safe: use ' -' instead of em-dash
        click.echo(f"Parallel : {len(p.parallel_groups)} group(s) - max_workers={workers}")
    click.echo("")

    # -- Step table ------------------------------------------------------
    show_when_col = has_when and not no_when
    show_group_col = has_parallel and not no_groups

    W_IDX  = 4
    W_NAME = 24
    W_CMD  = 34
    W_FAIL = 9
    W_DEP  = 20
    W_GROUP = 6
    W_WHEN  = 30

    header = (
        f"{'#':<{W_IDX}} {'Step':<{W_NAME}} {'Command':<{W_CMD}} "
        f"{'Failure':<{W_FAIL}} {'Depends on':<{W_DEP}}"
    )
    if show_group_col:
        header += f" {'GROUP':<{W_GROUP}}"
    if show_when_col:
        header += f" {'WHEN':<{W_WHEN}}"

    sep_len = len(header)
    click.echo(header)
    click.echo(_SEP * sep_len)  # ASCII '-' only

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
            when_list = getattr(s, "when", []) or []
            row += f" {_when_summary(when_list):<{W_WHEN}}"

        click.echo(row)

        if s.description:
            indent = " " * (W_IDX + 1 + W_NAME + 1)
            desc = s.description[:W_CMD + W_FAIL + W_DEP + W_GROUP + W_WHEN]
            click.echo(f"{indent}{_ARROW} {desc}")  # ASCII '->'

    # -- Parallel groups section -----------------------------------------
    if has_parallel and not no_groups:
        click.echo("")
        click.echo("Parallel groups")
        click.echo(_SEP * 50)  # ASCII '-' only
        for idx, group in enumerate(p.parallel_groups):
            members = "  ".join(group)
            click.echo(f"  P{idx}  {_PIPE}  {members}")  # ASCII '|'
        workers = getattr(p, "max_workers", 4)
        click.echo(f"       max_workers = {workers}")
        click.echo("")
        all_in_groups = {n for grp in p.parallel_groups for n in grp}
        seq_steps = [s.name for s in p.steps if s.name not in all_in_groups]
        if seq_steps:
            for sn in seq_steps:
                click.echo(f"  SEQ  {_PIPE}  {sn}")  # one per line, ASCII '|'


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

    from kiva_cli.core.pipeline_runner import run_pipeline

    result = run_pipeline(p, dry_run=dry_run, verbose=verbose)

    click.echo("")
    click.echo(f"Pipeline '{result.pipeline_name}' finished: {result.status}")
    click.echo(f"intent_hash : {result.intent_hash}")
    click.echo(f"duration    : {result.duration_s:.2f}s")

    # Sprint 4: parallel stats footer (ASCII-safe: ' -' not em-dash)
    pg_exec = getattr(result, "parallel_groups_executed", 0)
    if pg_exec > 0:
        wall = getattr(result, "total_parallel_wall_clock", 0.0)
        click.echo(f"parallel    : {pg_exec} group(s) ran - wall_clock={wall:.2f}s")

    click.echo("")
    click.echo(f"{'Step':<24} {'Status':<10} {'Duration':>8}  {'Group':<6}  Command")
    click.echo("-" * 88)  # plain ASCII
    for sr in result.steps:
        cmd_hint = ""
        grp = "SEQ"
        for s in p.steps:
            if s.name == sr.step_name:
                cmd_hint = s.command[:34]
                grp = _parallel_group_index(s.name, p.parallel_groups)
                break
        click.echo(
            f"{sr.step_name:<24} {_status_icon(sr.status):<10} {sr.duration_s:>7.2f}s  {grp:<6}  {cmd_hint}"
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
