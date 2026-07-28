#!/usr/bin/env python3
"""
KIVA-CLI CI commands.

Provides:
- ci run <repo> [--steps build,test,lint,bench] [--dry-run]
- ci status <repo>
- ci history [--limit N]
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Optional

import click

from kiva_cli.core.pipeline_loader import load_pipeline
from kiva_cli.core.pipeline_runner import run_pipeline
from kiva_cli.core.auto_chain_manager import get_auto_chain_manager


def _pipelines_dir() -> Path:
    env = os.environ.get("KIVA_PIPELINES_DIR")
    return Path(env) if env else Path(".kiva") / "pipelines"


def _find_yaml(name: str) -> Optional[Path]:
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


def _write_wal_entry(repo: str, pipeline_name: str, result: dict) -> None:
    try:
        from kiva_cli.core.global_wal_manager import GlobalWALManager
        wal = GlobalWALManager()
        wal.log_event(
            event_type="CI_RUN",
            payload={
                "repo": repo,
                "pipeline": pipeline_name,
                "status": result.get("status", "UNKNOWN"),
                "intent_hash": result.get("intent_hash", ""),
                "duration_s": result.get("duration_s", 0.0),
                "steps": [
                    {
                        "name": sr.step_name,
                        "status": sr.status,
                        "duration_s": sr.duration_s,
                    }
                    for sr in result.get("steps", [])
                ],
            },
        )
    except Exception:
        pass


def _generate_proof_hex(result: dict) -> str:
    raw = json.dumps(result, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha3_256(raw).hexdigest()


@click.group("ci")
def ci_cli():
    """Local CI orchestration via KIVA pipelines + SPIDX proofs."""
    pass


@ci_cli.command("run")
@click.argument("repo")
@click.option("--steps", "steps_list", default=None, help="Comma-separated steps (override pipeline).")
@click.option("--dry-run", is_flag=True, default=False, help="Simulate execution without running commands.")
@click.option("--verbose", "-v", is_flag=True, default=False, help="Show stdout/stderr per step.")
@click.option("--ci", "ci_mode", is_flag=True, default=False, help="Force CI-safe mode.")
def ci_run(repo: str, steps_list: Optional[str], dry_run: bool, verbose: bool, ci_mode: bool):
    """Run the local CI pipeline for REPO."""
    if ci_mode:
        os.environ["KIVA_CI"] = "1"

    pipeline_name = repo.lower()

    if steps_list:
        steps = [s.strip() for s in steps_list.split(",") if s.strip()]
        if not steps:
            click.echo("[ERROR] --steps requires at least one command", err=True)
            raise SystemExit(1)
        manager = get_auto_chain_manager()
        result = manager.run_adhoc(steps, dry_run=dry_run, verbose=verbose)
        result.pipeline_name = pipeline_name
    else:
        path = _find_yaml(pipeline_name)
        if path is None:
            click.echo(f"[ERROR] Pipeline not found: '{pipeline_name}' in {_pipelines_dir()}", err=True)
            raise SystemExit(1)
        try:
            p = load_pipeline(path)
        except Exception as exc:
            click.echo(f"[ERROR] Failed to parse pipeline '{pipeline_name}': {exc}", err=True)
            raise SystemExit(1)
        result = run_pipeline(p, dry_run=dry_run, verbose=verbose)

    _write_wal_entry(repo, pipeline_name, result)

    proof_hex = _generate_proof_hex({
        "repo": repo,
        "pipeline": pipeline_name,
        "status": result.status,
        "steps": [sr.step_name for sr in result.steps],
    })

    click.echo("")
    click.echo(f"CI pipeline '{pipeline_name}' finished: {result.status}")
    click.echo(f"intent_hash : {result.intent_hash}")
    click.echo(f"proof_hex   : {proof_hex}")
    click.echo(f"duration    : {result.duration_s:.2f}s")
    click.echo("")
    click.echo(f"{'Step':<24} {'Status':<10} {'Duration':>8}")
    click.echo("-" * 50)
    for sr in result.steps:
        click.echo(f"{sr.step_name:<24} {_status_icon(sr.status):<10} {sr.duration_s:>7.2f}s")
        if verbose and sr.stdout:
            click.echo(f"  stdout: {sr.stdout[:200]}")
        if verbose and sr.stderr:
            click.echo(f"  stderr: {sr.stderr[:200]}")

    if result.status == "FAILED":
        raise SystemExit(1)


@ci_cli.command("status")
@click.argument("repo")
def ci_status(repo: str):
    """Show last CI run status for REPO."""
    try:
        from kiva_cli.core.global_wal_manager import GlobalWALManager
        wal = GlobalWALManager()
        events = wal.get_events(event_type="CI_RUN", limit=20)
    except Exception as exc:
        click.echo(f"[WARN] WAL unavailable: {exc}")
        return

    repo_events = [e for e in events if (e.get("payload") or {}).get("repo") == repo]
    if not repo_events:
        click.echo(f"No CI runs found for '{repo}'.")
        return

    click.echo(f"Last CI runs for '{repo}':")
    for ev in repo_events[:5]:
        payload = ev.get("payload") or {}
        click.echo(f"  {payload.get('status', '-')}  {payload.get('pipeline', '-')}  {ev.get('timestamp', '-')}")


@ci_cli.command("history")
@click.option("--limit", "-n", default=20, show_default=True, help="Max CI events to show.")
def ci_history(limit: int):
    """Show last N CI runs from WAL."""
    try:
        from kiva_cli.core.global_wal_manager import GlobalWALManager
        wal = GlobalWALManager()
        events = wal.get_events(event_type="CI_RUN", limit=limit)
    except Exception as exc:
        click.echo(f"[WARN] WAL unavailable: {exc}")
        return

    if not events:
        click.echo("No CI runs found in WAL.")
        return

    click.echo(f"Last {len(events)} CI runs:")
    click.echo(f"{'Repo':<16} {'Pipeline':<24} {'Status':<10} {'Timestamp'}")
    click.echo("-" * 80)
    for ev in events:
        payload = ev.get("payload") or {}
        click.echo(
            f"{payload.get('repo', '-'):<16} {payload.get('pipeline', '-'):<24} {payload.get('status', '-'):<10} {ev.get('timestamp', '-')}"
        )
