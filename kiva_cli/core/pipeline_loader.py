"""KIVA-008 — Pipeline YAML loader + DAG resolver (Sprint 1).

Public API:
    load_pipeline(path)          -> Pipeline
    resolve_order(steps)         -> List[Step]   (topological sort)
    detect_cycles(steps)         -> List[str]    ([] if DAG is valid)
"""
from __future__ import annotations

import graphlib
from pathlib import Path
from typing import Dict, List

try:
    import yaml
except ImportError as exc:  # pragma: no cover
    raise ImportError(
        "PyYAML is required for pipeline support: pip install pyyaml"
    ) from exc

from kiva_cli.core.pipeline_types import Pipeline, Step


# ---------------------------------------------------------------------------
# Loader
# ---------------------------------------------------------------------------

def load_pipeline(path: str | Path) -> Pipeline:
    """Parse a YAML pipeline definition and return a resolved Pipeline.

    Expected YAML shape::

        name: build
        description: "Build, lint, test"
        version: "1"
        nexus_status: DRAFT
        steps:
          - name: lint
            command: "kiva gate lint"
            on_failure: abort
          - name: test
            command: "kiva gate test"
            depends_on: [lint]
            on_failure: warn
          - name: deploy
            command: "kiva deploy --env prod"
            depends_on: [test]
            when: "last_status == 'SUCCESS' and not dry_run"
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Pipeline definition not found: {path}")

    with path.open(encoding="utf-8") as fh:
        raw = yaml.safe_load(fh) or {}

    if not isinstance(raw, dict):
        raise ValueError(f"Invalid pipeline YAML (expected mapping): {path}")

    raw_steps: list = raw.get("steps") or []
    steps_unordered: List[Step] = [_parse_step(s) for s in raw_steps]
    ordered = resolve_order(steps_unordered)

    # Validate pipeline-level on_failure (KIVA-010 S4)
    pf = raw.get("on_failure", "abort")
    if pf not in ("abort", "warn", "continue", "notify"):
        raise ValueError(
            f"Pipeline '{raw.get('name', path.stem)}': on_failure must be 'abort', 'warn', 'continue' or 'notify'; got '{pf}'."
        )

    return Pipeline(
        name=raw.get("name", path.stem),
        steps=ordered,
        description=raw.get("description", ""),
        version=str(raw.get("version", "1")),
        nexus_status=raw.get("nexus_status", "DRAFT"),
        parallel_groups=raw.get("parallel_groups") or [],
        max_workers=int(raw.get("max_workers", 4)),
        on_failure=pf,
        raw=raw,
    )


def _parse_step(raw_step: dict) -> Step:
    """Convert a raw YAML dict to a Step dataclass."""
    if not isinstance(raw_step, dict):
        raise ValueError(f"Step must be a YAML mapping, got: {type(raw_step)}")
    name = raw_step.get("name", "")
    if not name:
        raise ValueError("Each pipeline step must have a non-empty 'name' field.")

    on_failure = raw_step.get("on_failure", "abort")
    if on_failure not in ("abort", "warn", "continue", "notify"):
        raise ValueError(
            f"Step '{name}': on_failure must be 'abort', 'warn', 'continue' or 'notify'; got '{on_failure}'."
        )

    return Step(
        name=name,
        command=raw_step.get("command", ""),
        depends_on=list(raw_step.get("depends_on") or []),
        on_failure=on_failure,
        env=dict(raw_step.get("env") or {}),
        timeout=raw_step.get("timeout"),
        retry=int(raw_step.get("retry", 0)),
        description=raw_step.get("description", ""),
        when=str(raw_step.get("when") or ""),  # KIVA-011: empty string = always run
    )


# ---------------------------------------------------------------------------
# DAG resolution
# ---------------------------------------------------------------------------

def resolve_order(steps: List[Step]) -> List[Step]:
    """Topologically sort steps, raising CycleError if the DAG is cyclic.

    Uses stdlib :mod:`graphlib.TopologicalSorter` (Python ≥ 3.9).
    """
    by_name: Dict[str, Step] = {s.name: s for s in steps}

    # Validate that all depends_on references exist
    for step in steps:
        for dep in step.depends_on:
            if dep not in by_name:
                raise ValueError(
                    f"Step '{step.name}' depends on unknown step '{dep}'."
                )

    graph: Dict[str, set] = {s.name: set(s.depends_on) for s in steps}
    try:
        ts = graphlib.TopologicalSorter(graph)
        ordered_names = list(ts.static_order())
    except graphlib.CycleError as exc:
        cycle_nodes = exc.args[1] if len(exc.args) > 1 else "?"
        raise graphlib.CycleError(
            f"Pipeline contains a dependency cycle: {cycle_nodes}"
        ) from None

    return [by_name[n] for n in ordered_names]


def detect_cycles(steps: List[Step]) -> List[str]:
    """Return list of nodes involved in a cycle, or [] if the DAG is valid.

    Non-raising convenience wrapper used by validation commands.
    """
    try:
        resolve_order(steps)
        return []
    except graphlib.CycleError as exc:
        nodes = exc.args[1] if len(exc.args) > 1 else []
        return list(nodes) if nodes else ["<unknown cycle>"]
