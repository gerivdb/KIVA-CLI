"""KIVA-008 — Pipeline chain types (Sprint 1).

Dataclasses for Pipeline, Step, StepResult, PipelineResult.
All runtime behaviour (execution, WAL events) lives in pipeline_manager.py (Sprint 2).
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

    description: str = ""
    """Human-readable label shown in `kiva pipeline status`."""


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


@dataclass
class PipelineResult:
    """Aggregate outcome of a full pipeline run."""

    pipeline_name: str
    intent_hash: str
    """sha256(pipeline_name + iso_timestamp)[:32] — stable run identifier for WAL."""

    status: Literal["SUCCESS", "PARTIAL", "FAILED", "ABORTED"]
    steps: List[StepResult] = field(default_factory=list)
    started_at: float = field(default_factory=time.time)
    ended_at: Optional[float] = None

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
