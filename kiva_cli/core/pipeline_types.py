"""KIVA-009 — Pipeline chain types (Sprint 3).

Dataclasses for Pipeline, Step, StepResult, PipelineResult.
All runtime behaviour (execution, WAL events) lives in pipeline_runner.py.

Changelog:
  Sprint 1 (KIVA-008): Step, Pipeline, StepResult, PipelineResult baseline.
  Sprint 2 (KIVA-009): WhenCondition, WhenEvaluationResult added to Step.
  Sprint 3 (KIVA-009): PipelineResult.parallel_groups_executed / total_parallel_wall_clock.
"""
from __future__ import annotations

import hashlib
import os
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional

# ---------------------------------------------------------------------------
# Feature flags
# ---------------------------------------------------------------------------

HAS_PIPELINE: bool = os.environ.get("KIVA_HAS_PIPELINE", "1") != "0"
"""Master switch — set KIVA_HAS_PIPELINE=0 to disable pipeline commands entirely."""

CI_SAFE: bool = os.environ.get("KIVA_CI", "") != ""
"""When truthy, monkey-patches click.confirm/prompt so pipelines never block in CI."""

if CI_SAFE:
    try:
        import click as _click
        _click.confirm = lambda msg, default=True, **kw: default  # type: ignore[assignment]
        _click.prompt = lambda msg, default=None, **kw: default  # type: ignore[assignment]
    except ImportError:
        pass


# ---------------------------------------------------------------------------
# When conditions (F1 — KIVA-009 Sprint 1/2)
# ---------------------------------------------------------------------------

ConditionType = Literal["env", "file_exists", "file_changed", "phi_cps", "step_output", "expr"]


@dataclass
class WhenCondition:
    """A single guard condition on a Step.

    Evaluated by condition_evaluator.ConditionEvaluator before the step runs.
    All conditions in a step's `when` list must pass (AND semantics).
    """

    type: ConditionType
    """Discriminator — selects the evaluation strategy."""

    # --- env / step_output / phi_cps common fields ---
    var: Optional[str] = None
    """env: environment variable name to inspect."""
    equals: Optional[str] = None
    """env: expected value (skip step if env != equals)."""
    not_equals: Optional[str] = None
    """env: skip step if env == not_equals."""

    # --- file_exists / file_changed ---
    path: Optional[str] = None
    """file_exists: path that must exist. file_changed: path to check mtime delta."""
    since_seconds: Optional[float] = None
    """file_changed: skip step if file mtime is older than this many seconds."""

    # --- phi_cps ---
    repo: Optional[str] = None
    """phi_cps: repo identifier (e.g. 'BLO') looked up via WAL CPS store."""
    op: Optional[Literal["lt", "gt", "lte", "gte", "eq"]] = None
    """phi_cps: comparison operator."""
    value: Optional[float] = None
    """phi_cps: threshold to compare current CPS against."""

    # --- step_output ---
    step: Optional[str] = None
    """step_output: name of the upstream step whose result to inspect."""
    exit_code: Optional[int] = None
    """step_output: expected exit code (None = any)."""
    stdout_contains: Optional[str] = None
    """step_output: required substring in upstream step stdout."""

    # --- expr ---
    expr: Optional[str] = None
    """expr: Python expression string evaluated in AST sandbox.
    Allowed names: env, files, steps, phi. No imports permitted.
    """


@dataclass
class WhenEvaluationResult:
    """Result of evaluating one WhenCondition."""

    condition_type: ConditionType
    passed: bool
    reason: str = ""
    """Human-readable explanation of why the condition passed or failed."""


# ---------------------------------------------------------------------------
# Step
# ---------------------------------------------------------------------------

@dataclass
class Step:
    """A single unit of work inside a Pipeline."""

    name: str
    """Unique identifier within the pipeline (used as DAG node key)."""

    command: str
    """Shell command or KIVA sub-command string to execute."""

    depends_on: List[str] = field(default_factory=list)
    """Names of steps that must complete successfully before this step runs."""

    on_failure: Literal["abort", "warn", "continue"] = "abort"
    """Behaviour when this step exits non-zero:
    - abort   : stop the whole pipeline immediately (default).
    - warn    : log a warning, mark step FAILED, continue remaining steps.
    - continue: silently swallow the error, treat step as SKIPPED.
    """

    env: Dict[str, str] = field(default_factory=dict)
    """Extra environment variables injected for this step only."""

    timeout: Optional[int] = None
    """Maximum wall-clock seconds; None = no limit."""

    retry: int = 0
    """Number of automatic retries on failure (total attempts = retry + 1).
    KIVA-010 S1.
    """

    description: str = ""
    """Human-readable label shown in `kiva pipeline status`."""

    when: List[WhenCondition] = field(default_factory=list)
    """Guard conditions (F1 — KIVA-009). All must pass for the step to run.
    Empty list = always run (default behaviour, backward-compatible).
    """


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------

@dataclass
class Pipeline:
    """A named, ordered DAG of Steps loaded from a YAML definition."""

    name: str
    """Pipeline identifier (matches the YAML filename stem by convention)."""

    steps: List[Step]
    """Ordered list of steps AFTER topological sort (set by pipeline_loader)."""

    description: str = ""
    version: str = "1"
    nexus_status: str = "DRAFT"
    """Informational only — authoritative status lives in .nexus/STATUS.yaml."""

    parallel_groups: List[List[str]] = field(default_factory=list)
    """F2 — KIVA-009 Sprint 2. Each inner list is a set of step names to run
    concurrently. Validated at load time by validate_parallel_groups().
    Steps NOT listed here are run sequentially in topological order.
    """

    max_workers: int = 4
    """F2 — thread pool cap for parallel groups (capped at cpu_count at runtime)."""

    on_failure: Literal["abort", "warn", "continue"] = "abort"
    """Pipeline-level default on_failure; overridden per-step."""

    raw: Dict[str, Any] = field(default_factory=dict)
    """Original parsed YAML dict, preserved for debugging."""


# ---------------------------------------------------------------------------
# Run results
# ---------------------------------------------------------------------------

@dataclass
class StepResult:
    """Outcome of a single step execution."""

    step_name: str
    status: Literal["SUCCESS", "FAILED", "SKIPPED", "ABORTED"]
    returncode: int = 0
    stdout: str = ""
    stderr: str = ""
    duration_s: float = 0.0
    error_message: str = ""
    attempts: int = 1
    """Number of execution attempts (1 + retries). KIVA-010."""


@dataclass
class PipelineResult:
    """Aggregate outcome of a full pipeline run.

    Sprint 3 additions (backward-compat, zero-default):
      parallel_groups_executed  — number of parallel groups that ran.
      total_parallel_wall_clock — cumulative wall-clock across all groups (seconds).
    """

    pipeline_name: str
    intent_hash: str
    """sha256(pipeline_name + iso_timestamp)[:32] — stable run identifier for WAL."""

    status: Literal["SUCCESS", "PARTIAL", "FAILED", "ABORTED"]
    steps: List[StepResult] = field(default_factory=list)
    started_at: float = field(default_factory=time.time)
    ended_at: Optional[float] = None

    # F2 parallel stats — populated by pipeline_runner when parallel_groups ran
    parallel_groups_executed: int = 0
    total_parallel_wall_clock: float = 0.0

    # KIVA-010 S1 — retry governance
    total_retries_used: int = 0
    """Total number of retry attempts used across the whole pipeline run."""

    @property
    def duration_s(self) -> float:
        if self.ended_at is None:
            return 0.0
        return self.ended_at - self.started_at

    @staticmethod
    def make_intent_hash(pipeline_name: str) -> str:
        ts = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
        raw = f"{pipeline_name}::{ts}"
        return hashlib.sha256(raw.encode()).hexdigest()[:32]
