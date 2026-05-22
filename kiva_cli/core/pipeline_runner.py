"""KIVA-009 -- pipeline_runner: group-aware walker + on_failure intra-group.

Public API:
    run_pipeline(pipeline, dry_run, verbose) -> PipelineResult

Walker logic:
    Steps execute in topological order (pipeline.steps).
    When the first step of a parallel_group is encountered, the entire
    group is dispatched to ParallelGroupExecutor, on_failure is applied
    per member, and the group is marked processed.  Subsequent steps
    that belong to the same group are skipped by the walker (already
    appended via the group execution path).
    Sequential steps (not in any group) follow the original logic.
"""
from __future__ import annotations

import os
import subprocess
import time
from typing import Optional

import click

from kiva_cli.core.pipeline_types import (
    CI_SAFE,
    Pipeline,
    PipelineResult,
    Step,
    StepResult,
)


# ---------------------------------------------------------------------------
# WAL helper (soft-import)
# ---------------------------------------------------------------------------

def _emit_wal_event(event_type: str, payload: dict) -> None:
    try:
        from kiva_cli.core.global_wal_manager import GlobalWALManager
        wal = GlobalWALManager()
        fn = getattr(wal, "append_event", None) or getattr(wal, "log_event", None)
        if fn:
            fn(event_type=event_type, payload=payload)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# phi_delta hook (soft-import)
# ---------------------------------------------------------------------------

def _phi_delta_record(step_name: str, duration_s: float, status: str) -> None:
    try:
        from kiva_cli.core.phi_tracker import PhiTracker
        PhiTracker().record(
            label=f"pipeline.step.{step_name}",
            value=duration_s,
            unit="s",
            status=status,
        )
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
# on_failure helper (shared: sequential + parallel paths)
# ---------------------------------------------------------------------------

def _apply_on_failure(
    sr: StepResult,
    step: Step,
    aborted: bool,
    abort_reason: str,
) -> tuple[bool, str]:
    """Apply on_failure policy to a FAILED StepResult.

    Returns updated (aborted, abort_reason).
    Mutates sr.status for 'continue' policy (FAILED -> SKIPPED).
    Emits click output for visibility.
    """
    if sr.status != "FAILED":
        click.echo(f" {sr.status} ({sr.duration_s:.2f}s)")
        return aborted, abort_reason

    if step.on_failure == "abort":
        click.echo(f" FAILED ({sr.duration_s:.2f}s) -- ABORTING pipeline")
        if sr.error_message:
            click.echo(f"     {sr.error_message}", err=True)
        return True, step.name
    elif step.on_failure == "warn":
        click.echo(f" FAILED ({sr.duration_s:.2f}s) [warn, continuing]")
        if sr.error_message:
            click.echo(f"  [WARN] {sr.error_message}")
        return aborted, abort_reason
    else:  # continue
        click.echo(f" FAILED ({sr.duration_s:.2f}s) [continue, suppressed]")
        sr.status = "SKIPPED"
        return aborted, abort_reason


# ---------------------------------------------------------------------------
# Parallel group executor (soft-import with sequential fallback)
# ---------------------------------------------------------------------------

def _run_group(
    group_steps: list[Step],
    step_map: dict[str, Step],
    dry_run: bool,
    verbose: bool,
    max_workers: int,
) -> tuple[list[StepResult], float]:
    """Run a group of steps in parallel.

    Returns (list[StepResult], wall_clock_seconds).
    Falls back to sequential execution if ParallelGroupExecutor is unavailable.
    """
    t0 = time.monotonic()
    try:
        from kiva_cli.core.parallel_executor import ParallelGroupExecutor
        executor = ParallelGroupExecutor(max_workers=max_workers)
        step_results = executor.run_group(
            steps=group_steps,
            dry_run=dry_run,
            verbose=verbose,
        )
        wall = time.monotonic() - t0
        return step_results, wall
    except ImportError:
        # Graceful fallback: run sequentially
        results: list[StepResult] = []
        for s in group_steps:
            results.append(_run_step(s, dry_run=dry_run, verbose=verbose))
        return results, time.monotonic() - t0


# ---------------------------------------------------------------------------
# Pipeline executor
# ---------------------------------------------------------------------------

def run_pipeline(
    pipeline: Pipeline,
    dry_run: bool = False,
    verbose: bool = False,
) -> PipelineResult:
    """Execute all steps of a Pipeline in topological order.

    Group-aware walker:
    - parallel_groups are dispatched to ParallelGroupExecutor.
    - on_failure is applied per step result after group completion:
        abort    -> pipeline ABORTED; all remaining steps SKIPPED.
        warn     -> FAILED recorded, warning emitted, execution continues.
        continue -> step SKIPPED silently, execution continues.
    - Sequential steps (not in any group) use the original path.
    - Graceful fallback to sequential if ParallelGroupExecutor missing.

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

    # -- Build group index map ------------------------------------------------
    # step_to_group_idx[step_name] = index into pipeline.parallel_groups
    step_to_group_idx: dict[str, int] = {}
    for idx, group in enumerate(pipeline.parallel_groups):
        for name in group:
            step_to_group_idx[name] = idx

    # step_map for O(1) lookup by name
    step_map: dict[str, Step] = {s.name: s for s in pipeline.steps}

    # Track which group indices have already been executed
    processed_groups: set[int] = set()
    # Track which step names were handled via a group (skip in sequential path)
    group_handled_steps: set[str] = set()

    aborted = False
    abort_reason = ""
    max_workers = getattr(pipeline, "max_workers", 4)

    # -- Walker ---------------------------------------------------------------
    for step in pipeline.steps:

        # Skip steps already handled as part of a group
        if step.name in group_handled_steps:
            continue

        # Skip with SKIPPED result if pipeline is aborted
        if aborted:
            result.steps.append(StepResult(
                step_name=step.name,
                status="SKIPPED",
                error_message=f"Skipped due to abort: {abort_reason}",
            ))
            continue

        group_idx = step_to_group_idx.get(step.name)

        # -- Parallel group path ---------------------------------------------
        if group_idx is not None and group_idx not in processed_groups:
            group_names = pipeline.parallel_groups[group_idx]
            group_steps = [step_map[n] for n in group_names if n in step_map]

            click.echo(f"  [P{group_idx}] Running {len(group_steps)} steps in parallel...")

            step_results, wall_clock = _run_group(
                group_steps=group_steps,
                step_map=step_map,
                dry_run=dry_run,
                verbose=verbose,
                max_workers=max_workers,
            )

            # Apply on_failure per member; collect results
            for sr in step_results:
                member_step = step_map.get(sr.step_name)
                if member_step is None:
                    result.steps.append(sr)
                    continue

                click.echo(f"    >> {sr.step_name} ...", nl=False)
                _phi_delta_record(sr.step_name, sr.duration_s, sr.status)

                if sr.status == "FAILED":
                    aborted, abort_reason = _apply_on_failure(
                        sr, member_step, aborted, abort_reason
                    )
                else:
                    click.echo(f" {sr.status} ({sr.duration_s:.2f}s)")

                result.steps.append(sr)

            # Update parallel stats
            result.parallel_groups_executed += 1
            result.total_parallel_wall_clock += wall_clock

            # Mark all group members as handled
            processed_groups.add(group_idx)
            for n in group_names:
                group_handled_steps.add(n)

            # If abort triggered inside the group, SKIP remaining group
            # members that were not executed (already appended above)
            if aborted:
                # SKIP any group steps that were not returned by executor
                executed_names = {sr.step_name for sr in step_results}
                for n in group_names:
                    if n not in executed_names:
                        result.steps.append(StepResult(
                            step_name=n,
                            status="SKIPPED",
                            error_message=f"Skipped due to group abort: {abort_reason}",
                        ))

        # -- Sequential path -------------------------------------------------
        elif group_idx is None:
            click.echo(f"  >> {step.name} ...", nl=False)
            sr = _run_step(step, dry_run=dry_run, verbose=verbose)
            result.steps.append(sr)
            _phi_delta_record(step.name, sr.duration_s, sr.status)

            if sr.status == "FAILED":
                aborted, abort_reason = _apply_on_failure(
                    sr, step, aborted, abort_reason
                )
            else:
                click.echo(f" {sr.status} ({sr.duration_s:.2f}s)")

    # -- Final status --------------------------------------------------------
    result.ended_at = time.time()

    statuses = {sr.status for sr in result.steps}
    if aborted or "ABORTED" in statuses:
        result.status = "ABORTED"
    elif "FAILED" in statuses:
        result.status = "PARTIAL"
    else:
        result.status = "SUCCESS"

    # -- WAL -----------------------------------------------------------------
    _emit_wal_event(
        event_type="PIPELINE_RUN",
        payload={
            "pipeline_name": pipeline.name,
            "intent_hash": intent_hash,
            "status": result.status,
            "duration_s": round(result.duration_s, 3),
            "dry_run": dry_run,
            "parallel_groups_executed": result.parallel_groups_executed,
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
