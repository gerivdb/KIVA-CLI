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

# Parallel execution (KIVA-009 F2 + on_failure intra-groupe)
from kiva_cli.core.parallel_executor import (
    ParallelGroupExecutor,
    validate_parallel_groups,
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
# Retry wrapper (KIVA-010 S2)
# ---------------------------------------------------------------------------

def _run_step_with_retry(
    step: Step, dry_run: bool = False, verbose: bool = False
) -> StepResult:
    """Execute a step with automatic retries.

    Total attempts = step.retry + 1.
    Returns as soon as a SUCCESS is obtained.
    The returned StepResult.attempts contains the actual number of attempts made.
    """
    max_attempts = (step.retry or 0) + 1
    last_result: StepResult | None = None

    for attempt in range(1, max_attempts + 1):
        result = _run_step(step, dry_run=dry_run, verbose=verbose)
        result.attempts = attempt
        last_result = result

        if result.status == "SUCCESS":
            return result

        # If this was the last attempt, we return the failure
        if attempt == max_attempts:
            break

        # Optional: could add a small sleep here in future (backoff)
        # For now we retry immediately

    assert last_result is not None
    return last_result


# ---------------------------------------------------------------------------
# On-failure policy applicator (shared by sequential and parallel paths)
# ---------------------------------------------------------------------------

def _apply_on_failure(
    sr: StepResult,
    step: Step,
    click_echo: bool = True,
) -> bool:
    """Apply the step's on_failure policy to a (possibly just-failed) StepResult.

    Returns True if the policy decided to abort the rest of the pipeline.
    Mutates sr.status in the 'continue' case (FAILED -> SKIPPED).
    """
    import click

    if sr.status != "FAILED":
        return False

    aborted = False
    if step.on_failure == "abort":
        if click_echo:
            click.echo(f" FAILED ({sr.duration_s:.2f}s) -- ABORTING pipeline")
            if sr.error_message:
                click.echo(f"     {sr.error_message}", err=True)
        aborted = True
    elif step.on_failure == "warn":
        if click_echo:
            click.echo(f" FAILED ({sr.duration_s:.2f}s) [warn, continuing]")
            if sr.error_message:
                click.echo(f"  [WARN] {sr.error_message}")
    else:  # "continue"
        if click_echo:
            click.echo(f" FAILED ({sr.duration_s:.2f}s) [continue, suppressed]")
        sr.status = "SKIPPED"

    return aborted


def _to_step_result(raw: Any, default_name: str) -> StepResult:
    """Normalize whatever the parallel executor returns (StepResult or error dict) into a StepResult."""
    if isinstance(raw, StepResult):
        return raw
    if isinstance(raw, dict):
        return StepResult(
            step_name=raw.get("step_name", default_name),
            status="FAILED" if raw.get("__error__") or raw.get("status") == "failed" else "SUCCESS",
            returncode=raw.get("exit_code", raw.get("returncode", -1)),
            stdout=raw.get("stdout", ""),
            stderr=raw.get("stderr", ""),
            duration_s=raw.get("duration", 0.0),
            error_message=str(raw.get("exception", ""))[:200],
        )
    # Fallback
    return StepResult(step_name=default_name, status="FAILED", error_message="unknown result type")


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

    import click  # hoisted to avoid repeated imports inside the walker

    # Validate parallel_groups early (no-op if empty). Raises on conflicts.
    if pipeline.parallel_groups:
        validate_parallel_groups(pipeline.steps, pipeline.parallel_groups)

    # Build quick lookup: step_name -> (group_idx or None)
    step_to_group: dict[str, int | None] = {}
    for gidx, grp in enumerate(pipeline.parallel_groups):
        for name in grp:
            step_to_group[name] = gidx
    # Steps not in any group stay None (sequential)

    # Executor for parallel groups (only instantiated if needed)
    parallel_executor = (
        ParallelGroupExecutor(max_workers=pipeline.max_workers)
        if pipeline.parallel_groups else None
    )
    processed_groups: set[int] = set()

    aborted = False
    abort_reason = ""

    # === Group-aware execution walker (supports on_failure inside parallel groups) ===
    steps = pipeline.steps
    i = 0
    n = len(steps)

    while i < n:
        step = steps[i]

        if aborted:
            result.steps.append(StepResult(
                step_name=step.name,
                status="SKIPPED",
                error_message=f"Skipped due to abort: {abort_reason}",
            ))
            i += 1
            continue

        gidx = step_to_group.get(step.name)

        if gidx is not None and gidx not in processed_groups and parallel_executor is not None:
            # --- Execute entire parallel group at once ---
            group_names = pipeline.parallel_groups[gidx]
            group_steps = [s for s in steps if s.name in set(group_names)]

            def _run_one(s: Step) -> StepResult:
                return _run_step_with_retry(s, dry_run=dry_run, verbose=verbose)

            group_res = parallel_executor.run_group(gidx, group_steps, _run_one)

            # Record parallel stats on the PipelineResult
            result.parallel_groups_executed += 1
            result.total_parallel_wall_clock += group_res.wall_clock_seconds

            # Process every member: echo + phi + on_failure policy
            for s in group_steps:
                raw = group_res.step_results.get(s.name)
                sr = _to_step_result(raw, s.name)
                result.steps.append(sr)
                result.total_retries_used += max(0, sr.attempts - 1)
                _phi_delta_record(s.name, sr.duration_s, sr.status)

                click.echo(f"  >> {s.name} ...", nl=False)
                if sr.status in ("SUCCESS", "SKIPPED"):
                    click.echo(f" {sr.status} ({sr.duration_s:.2f}s)")
                else:
                    if _apply_on_failure(sr, s):
                        aborted = True
                        abort_reason = s.name

            processed_groups.add(gidx)
            i += len(group_steps)
            continue

        # --- Normal sequential step (or already-processed group member) ---
        click.echo(f"  >> {step.name} ...", nl=False)

        sr = _run_step_with_retry(step, dry_run=dry_run, verbose=verbose)
        result.steps.append(sr)
        result.total_retries_used += max(0, sr.attempts - 1)
        _phi_delta_record(step.name, sr.duration_s, sr.status)

        if sr.status in ("SUCCESS", "SKIPPED"):
            click.echo(f" {sr.status} ({sr.duration_s:.2f}s)")
        else:
            if _apply_on_failure(sr, step):
                aborted = True
                abort_reason = step.name

        i += 1

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
