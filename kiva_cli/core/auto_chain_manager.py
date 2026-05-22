"""
AutoChainManager — KIVA-008

High-level orchestrator for declarative named pipelines + ad-hoc chaining.

This is the central class for PRD-KIVA-008 "kiva pipeline chain / AutoChainManager".
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from kiva_cli.core.pipeline_loader import load_pipeline, detect_cycles, resolve_order
from kiva_cli.core.pipeline_types import Pipeline, Step, PipelineResult, HAS_PIPELINE
from kiva_cli.core.pipeline_runner import run_pipeline


@dataclass
class ValidationResult:
    name: str
    valid: bool
    errors: List[str]
    warnings: List[str]


class AutoChainManager:
    """
    Main orchestrator for declarative pipelines (KIVA-008) + ad-hoc mode.
    """

    def __init__(self, pipelines_dir: Optional[Path] = None):
        self.pipelines_dir = pipelines_dir or self._default_pipelines_dir()
        self._cache: Dict[str, Pipeline] = {}

    def _default_pipelines_dir(self) -> Path:
        import os
        env = os.environ.get("KIVA_PIPELINES_DIR")
        if env:
            return Path(env)
        return Path(".kiva") / "pipelines"

    # ------------------------------------------------------------------
    # Discovery & Loading
    # ------------------------------------------------------------------
    def list_pipelines(self) -> List[str]:
        if not self.pipelines_dir.exists():
            return []
        names: List[str] = []
        for suffix in (".yaml", ".yml"):
            for f in self.pipelines_dir.glob(f"*{suffix}"):
                names.append(f.stem)
        return sorted(set(names))

    def get_pipeline(self, name: str) -> Pipeline:
        if name in self._cache:
            return self._cache[name]

        candidate = None
        for suffix in (".yaml", ".yml"):
            path = self.pipelines_dir / f"{name}{suffix}"
            if path.exists():
                candidate = path
                break

        if candidate is None:
            raise FileNotFoundError(f"Pipeline not found: {name}")

        pipeline = load_pipeline(candidate)
        self._cache[name] = pipeline
        return pipeline

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------
    def validate(self, name: str) -> ValidationResult:
        try:
            pipeline = self.get_pipeline(name)
        except Exception as e:
            return ValidationResult(name=name, valid=False, errors=[str(e)], warnings=[])

        errors: List[str] = []
        warnings: List[str] = []

        cycles = detect_cycles(pipeline.steps)
        if cycles:
            errors.append(f"Circular dependency detected: {' -> '.join(cycles)}")

        for step in pipeline.steps:
            if not step.name:
                errors.append("Step without name found")
            if not getattr(step, "command", None):
                warnings.append(f"Step '{step.name}' has no command")

        return ValidationResult(name=name, valid=len(errors) == 0, errors=errors, warnings=warnings)

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------
    def run(self, name: str, **context: Any) -> PipelineResult:
        if not HAS_PIPELINE:
            raise RuntimeError("Pipeline support is disabled (KIVA_HAS_PIPELINE=0)")

        pipeline = self.get_pipeline(name)
        validation = self.validate(name)
        if not validation.valid:
            raise ValueError(f"Pipeline '{name}' is invalid: {validation.errors}")

        return run_pipeline(pipeline, **context)

    def run_adhoc(self, steps: List[str], **context: Any) -> PipelineResult:
        """
        Execute an ad-hoc list of steps (KIVA-007 compatibility).

        Builds a synthetic Pipeline on the fly and delegates to the existing
        runner. This gives us full support for on_failure, when:, retries, etc.
        even in ad-hoc mode.
        """
        if not HAS_PIPELINE:
            raise RuntimeError("Pipeline support is disabled (KIVA_HAS_PIPELINE=0)")

        synthetic_steps = [
            Step(name=f"step_{i}", command=step.strip())
            for i, step in enumerate(steps)
        ]

        synthetic_pipeline = Pipeline(
            name="adhoc",
            steps=synthetic_steps,
            description="Ad-hoc chain",
            version="1",
            nexus_status="ADHOC",
        )

        return run_pipeline(synthetic_pipeline, **context)

    def clear_cache(self) -> None:
        self._cache.clear()


# Singleton
_default_manager: Optional[AutoChainManager] = None

def get_auto_chain_manager() -> AutoChainManager:
    global _default_manager
    if _default_manager is None:
        _default_manager = AutoChainManager()
    return _default_manager
