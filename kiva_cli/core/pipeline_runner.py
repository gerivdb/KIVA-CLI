"""KIVA-008 Sprint 3 — pipeline_runner: subprocess executor + on_failure logic + WAL.

Public API:
    run_pipeline(pipeline, dry_run, verbose) -> PipelineResult
"""
from __future__ import annotations

import os
import subprocess
import time
from typing import Optional

from kiva_cli.core.pipeline_types import (
    CI_SAFE,
    Pipeline,
    PipelineResult,
    Step,
    StepResult,
)


# ---------------------------------------------------------------------------
# WAL helper (soft-import: KIVA-CLI may run without WAL in minimal envs)
# ---------------------------------------------------------------------------

def _emit_wal_event(event_type: str, payload: dict) -> None:
    """Append a WAL event if GlobalWALManager is available; silently skip otherwise."""
    try:
        from kiva_cli.core.global_wal_manager import GlobalWALManager
        wal = GlobalWALManager()
        # Prefer append_event; fall back to log_event for older builds
        fn = getattr(wal, "append_event", None) or getattr(wal, "log_event", None)
        if fn:
            fn(event_type=event_type, payload=payload)
    except Exception:
        pass  # WAL is best-effort; never block pipeline execution


# ---------------------------------------------------------------------------
# phi_delta hook (soft-import)
# ---------------------------------------------------------------------------

def _phi_delta_record(step_name: str, duration_s: float, status: str) -> None:
    """Record step timing in phi_tracker if available."""
    try:
        from kiva_cli.core.phi_tracker import PhiTracker
        PhiTracker().record(label=f"pipeline.step.{step_name}", value=duration_s, unit="s", status=status)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Step executor
# ---------------------------------------------------------------------------

def _run_step(step: Step, dry_run: bool = False, verbose: bool = False) -> StepResult:
    """Execute a single step and return its StepResult."""
    t0 = time.monotonic()

    if dry_run:
        return StepResult(
            step_name=step.name,
            status="SUCCESS",
            returncode=0,
            stdout=f"[DRY-RUN] {step.command}",
            duration_s=0.0,
        )

    if not step.command.strip():
        return StepResult(
            step_name=step.name,
            status="SKIPPED",
            returncode=0,
            stdout="(empty command, skipped)",
            duration_s=0.0,
        )

    # Merge step env on top of current env
    env = {**os.environ, **step.env}

    try:
        proc = subprocess.run(
            step.command,
            shell=True,
            capture_output=True,
            text=True,
            env=env,
            timeout=step.timeout,
        )
        duration = time.monotonic() - t0
        status: str = "SUCCESS" if proc.returncode == 0 else "FAILED"
        return StepResult(
            step_name=step.name,
            status=status,
            returncode=proc.returncode,
            stdout=proc.stdout,
            stderr=proc.stderr,
            duration_s=duration,
            error_message=proc.stderr[:200] if status == "FAILED" else "",
        )
    except subprocess.TimeoutExpired:
        duration = time.monotonic() - t0
        return StepResult(
            step_name=step.name,
            status="FAILED",
            returncode=-1,
            error_message=f"Step '{step.name}' timed out after {step.timeout}s",
            duration_s=duration,
        )
    except Exception as exc:
        duration = time.monotonic() - t0
        return StepResult(
            step_name=step.name,
            status="FAILED",
            returncode=-1,
            error_message=str(exc),
            duration_s=duration,
        )


# ---------------------------------------------------------------------------
# Pipeline executor
# ---------------------------------------------------------------------------

def run_pipeline(
    pipeline: Pipeline,
    dry_run: bool = False,
    verbose: bool = False,
) -> PipelineResult:
    """Execute all steps of a Pipeline in topological order.

    Respects on_failure per step:
    - abort    : stop pipeline; remaining steps are SKIPPED.
    - warn     : mark FAILED, emit warning, continue.
    - continue : mark SKIPPED, continue silently.

    Emits a PIPELINE_RUN WAL event on completion.
    Records phi_delta per step.
    """
    intent_hash = PipelineResult.make_intent_hash(pipeline.name)
    result = PipelineResult(
        pipeline_name=pipeline.name,
        intent_hash=intent_hash,
        status="PENDING",
        started_at=time.time(),
    )

    aborted = False
    abort_reason = ""

    for step in pipeline.steps:
        if aborted:
            result.steps.append(StepResult(
                step_name=step.name,
                status="SKIPPED",
                error_message=f"Skipped due to abort: {abort_reason}",
            ))
            continue

        import click
        click.echo(f"  >> {step.name} ...", nl=False)

        sr = _run_step(step, dry_run=dry_run, verbose=verbose)
        result.steps.append(sr)

        # phi_delta
        _phi_delta_record(step.name, sr.duration_s, sr.status)

        if sr.status == "SUCCESS" or sr.status == "SKIPPED":
            click.echo(f" {sr.status} ({sr.duration_s:.2f}s)")
        else:
            # FAILED
            if step.on_failure == "abort":
                click.echo(f" FAILED ({sr.duration_s:.2f}s) -- ABORTING pipeline")
                if sr.error_message:
                    click.echo(f"     {sr.error_message}", err=True)
                aborted = True
                abort_reason = step.name
            elif step.on_failure == "warn":
                click.echo(f" FAILED ({sr.duration_s:.2f}s) [warn, continuing]")
                if sr.error_message:
                    click.echo(f"  [WARN] {sr.error_message}")
            else:  # continue
                click.echo(f" FAILED ({sr.duration_s:.2f}s) [continue, suppressed]")
                sr.status = "SKIPPED"

    result.ended_at = time.time()

    # Determine final status
    statuses = {sr.status for sr in result.steps}
    if aborted or "ABORTED" in statuses:
        result.status = "ABORTED"
    elif "FAILED" in statuses:
        result.status = "PARTIAL"
    else:
        result.status = "SUCCESS"

    # Emit WAL
    _emit_wal_event(
        event_type="PIPELINE_RUN",
        payload={
            "pipeline_name": pipeline.name,
            "intent_hash": intent_hash,
            "status": result.status,
            "duration_s": round(result.duration_s, 3),
            "dry_run": dry_run,
            "steps": [
                {
                    "name": sr.step_name,
                    "status": sr.status,
                    "returncode": sr.returncode,
                    "duration_s": round(sr.duration_s, 3),
                }
                for sr in result.steps
            ],
        },
    )

    return result
