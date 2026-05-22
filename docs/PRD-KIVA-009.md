# PRD-KIVA-009 — Pipeline Conditions (`when:`) & Parallelism (`parallel:`)

**Status:** APPROVED — ready for Sprint 1
**Version:** 1.0.0
**Date:** 2026-05-22
**Author:** gerivdb
**Repo:** [gerivdb/KIVA-CLI](https://github.com/gerivdb/KIVA-CLI)
**Prerequisite PRDs:** KIVA-008 (✅ closed), P2.7 DEPENDENCY_MATRIX (✅ closed)
**Supersedes:** nothing (extends KIVA-008)
**Next:** KIVA-010 (remote registry, scheduled pipelines)

---

## 1. Context & Motivation

KIVA-008 delivered declarative DAG pipelines with `on_failure` policies, WAL tracing, and
full CLI (`run`, `list`, `show`, `validate`). The engine is sequential: every step runs in
order, unconditionally.

Two gaps block production use on real ECOS workflows:

1. **No conditional execution.** Steps always run. There is no way to skip a step when a
   precondition fails (e.g., skip `deploy` when not on `main`, skip `lint` when files
   haven't changed, skip `phi_check` when CPS is healthy).

2. **No parallelism.** Independent steps (e.g., `test-unit` and `test-integration`) run
   sequentially even when they share no data dependency. This inflates wall-clock time
   on multi-step pipelines.

KIVA-009 adds both capabilities as first-class YAML fields, fully backward-compatible
with all KIVA-008 pipelines.

---

## 2. Goals

| # | Goal |
|---|------|
| G1 | `when:` field on any step — evaluates to bool, skips step if false |
| G2 | Multiple condition types: `env`, `file_exists`, `phi_cps`, `step_output`, `expr` |
| G3 | `parallel:` field on step groups — runs non-dependent steps concurrently |
| G4 | `max_workers:` global pipeline option (default: 4) |
| G5 | WAL records skip events + parallel execution metadata |
| G6 | `--dry-run` shows resolved `when:` values and parallel groups |
| G7 | Full backward compatibility — existing KIVA-008 pipelines run unchanged |
| G8 | TDD: ≥ 20 new tests (unit + integration), all passing |

### Out of scope (KIVA-010)
- Remote registry / pipeline fetch from URL
- Cron / scheduled triggers
- Cross-repo pipeline chaining (depends on `kiva nexus drift`)
- `output:` capture piped between steps

---

## 3. Feature Specifications

### F1 — `when:` Conditional Step Execution

#### 3.1 YAML Schema

```yaml
# Per-step field (optional). If omitted or true → step runs. If false → step skipped.
steps:
  - name: deploy
    command: "./scripts/deploy.sh"
    when:
      type: env          # condition type (see §3.2)
      var: DEPLOY_ENV    # type-specific param
      equals: production # type-specific param
```

Shorthand (bool literal — always skip / always run):
```yaml
    when: false   # always skip (useful for debugging)
    when: true    # explicit always-run (default behaviour)
```

#### 3.2 Condition Types

| Type | Description | Required params | Example |
|------|-------------|----------------|---------|
| `env` | Check environment variable | `var`, `equals` or `not_equals` or `exists` | Skip deploy unless `DEPLOY_ENV=production` |
| `file_exists` | Check if a path exists on disk | `path` | Skip lint if `src/` doesn't exist |
| `file_changed` | Check if path modified since last WAL event | `path`, `since` (WAL event type) | Skip rebuild if no file changed |
| `phi_cps` | Compare φ-CPS value from WAL | `repo`, `op` (`gt`/`lt`/`gte`/`lte`/`eq`), `value` | Skip phi_check if CPS > 3.0 |
| `step_output` | Check exit code or stdout of a prior step | `step` (name), `exit_code` or `contains` | Skip deploy if test step failed |
| `expr` | Raw Python bool expression (sandboxed eval) | `expression` | `"env.get('CI') == 'true' and not env.get('SKIP')"` |

#### 3.3 Evaluation Rules

- Conditions are evaluated **just before** the step would start.
- If `when` evaluates to `False`: step status = `SKIPPED`, duration = 0, WAL event emitted.
- A `SKIPPED` step counts as **not failed** — it does not trigger `on_failure: abort`.
- `on_failure: abort` only fires on `FAILED` (non-zero exit code).
- `dry-run` mode resolves all conditions and prints `[WOULD SKIP]` or `[WOULD RUN]`.
- `expr` type: evaluated in a sandboxed namespace with `{env: os.environ, step_results: dict}`.
  No imports, no builtins except `str`, `int`, `bool`, `len`, `not`, `and`, `or`.

#### 3.4 PipelineStep type extension

```python
@dataclass
class WhenCondition:
    type: str                          # env | file_exists | file_changed | phi_cps | step_output | expr
    # env
    var: str | None = None
    equals: str | None = None
    not_equals: str | None = None
    exists: bool | None = None         # just checks var is set
    # file
    path: str | None = None
    since: str | None = None           # WAL event type
    # phi_cps
    repo: str | None = None
    op: str | None = None              # gt | lt | gte | lte | eq
    value: float | None = None
    # step_output
    step: str | None = None
    exit_code: int | None = None
    contains: str | None = None
    # expr
    expression: str | None = None

# PipelineStep gains:
    when: WhenCondition | bool | None = None  # None = always run
```

#### 3.5 StepStatus extension

```python
class StepStatus(str, Enum):
    PENDING   = "pending"
    RUNNING   = "running"
    SUCCESS   = "success"
    FAILED    = "failed"
    SKIPPED   = "skipped"    # NEW — when: evaluated False
    ABORTED   = "aborted"
```

---

### F2 — `parallel:` Step Group Execution

#### 3.6 YAML Schema

Parallel groups are declared at the pipeline level. Each group is a list of step names
that may run concurrently. Steps not in any group remain sequential.

```yaml
name: blo-full
max_workers: 4        # global thread pool size (default: 4)
steps:
  - name: setup
    command: "pip install -e ."
  - name: test-unit
    command: "pytest tests/unit -q"
  - name: test-integration
    command: "pytest tests/integration -q"
  - name: lint
    command: "ruff check src/"
  - name: deploy
    command: "./scripts/deploy.sh"
    depends_on: [test-unit, test-integration, lint]

parallel_groups:
  - [test-unit, test-integration, lint]  # these three run concurrently after setup
  # deploy is sequential (has depends_on, runs after group finishes)
```

#### 3.7 Execution Model

- Parallel groups are **resolved after** DAG `resolve_order()` validates no cycles.
- Steps within a group must have **no inter-dependencies** (validated at load time; raises `ParallelConflictError` if violated).
- All steps in a group start simultaneously via `ThreadPoolExecutor(max_workers=max_workers)`.
- A group is considered complete when **all** its steps finish (SUCCESS or SKIPPED).
- If any step in a group FAILS:
  - The other running steps in the group are **not cancelled** (they complete naturally).
  - `on_failure` policy is applied after the group completes.
- Steps after a parallel group start only when the group is fully done.
- `max_workers` defaults to `4`; capped at `os.cpu_count()` at runtime.

#### 3.8 PipelineDefinition type extension

```python
@dataclass
class PipelineDefinition:
    # existing fields unchanged
    name: str
    steps: list[PipelineStep]
    description: str = ""
    on_failure: str = "abort"
    timeout: int | None = None
    # NEW
    max_workers: int = 4
    parallel_groups: list[list[str]] = field(default_factory=list)
```

#### 3.9 PipelineResult extension

```python
@dataclass
class PipelineResult:
    # existing fields unchanged
    # NEW
    skipped_steps: list[str] = field(default_factory=list)
    parallel_groups_executed: int = 0
    wall_clock_seconds: float = 0.0
```

---

## 4. CLI Changes

### `kiva pipeline run <name> [--dry-run] [-v]`
- No new flags needed for KIVA-009 core.
- `--dry-run` output extended:
  ```
  [DRY-RUN] Step: test-unit     | when: <not set>       → WOULD RUN
  [DRY-RUN] Step: deploy        | when: env.DEPLOY_ENV=production → WOULD SKIP (env=staging)
  [DRY-RUN] Parallel group 0:   [test-unit, test-integration, lint] → 3 steps concurrent
  ```

### `kiva pipeline show <name>`
- Extended table shows `when` condition type and `parallel_group` index per step.

### `kiva pipeline validate <name>`
- New validations:
  - `ParallelConflictError` if steps in the same group have inter-dependencies.
  - `UnknownStepError` if `parallel_groups` references a step not in `steps:`.
  - `WhenTypeError` if `when.type` is not one of the 6 known types.
  - `ExprSyntaxError` if `when.type=expr` expression fails `compile()` check.

---

## 5. Acceptance Criteria

### Sprint 1 — `when:` Core (F1)

| # | AC | Test |
|---|----|------|
| AC-1.1 | Step with `when: false` is SKIPPED, overall = SUCCESS | `test_when_literal_false_skips` |
| AC-1.2 | Step with `when: true` runs normally | `test_when_literal_true_runs` |
| AC-1.3 | `when.type=env, equals` skips if var mismatch | `test_when_env_equals_skip` |
| AC-1.4 | `when.type=env, equals` runs if var matches | `test_when_env_equals_run` |
| AC-1.5 | `when.type=env, exists` skips if var not set | `test_when_env_exists_skip` |
| AC-1.6 | `when.type=file_exists` skips if path missing | `test_when_file_missing_skip` |
| AC-1.7 | `when.type=file_exists` runs if path present | `test_when_file_present_run` |
| AC-1.8 | SKIPPED step does not trigger `on_failure: abort` | `test_skipped_no_abort` |
| AC-1.9 | WAL emits `step_skipped` event with `when` metadata | `test_wal_skip_event` |
| AC-1.10 | `dry-run` prints `[WOULD SKIP]` for false conditions | `test_dry_run_would_skip` |
| AC-1.11 | Existing KIVA-008 pipelines (no `when:`) run unchanged | `test_kiva008_compat` |

### Sprint 2 — `when:` Advanced + `parallel:` (F1 advanced + F2)

| # | AC | Test |
|---|----|------|
| AC-2.1 | `when.type=phi_cps` skips if CPS > threshold | `test_when_phi_cps_skip` |
| AC-2.2 | `when.type=step_output, exit_code` evaluates prior step result | `test_when_step_output_exit` |
| AC-2.3 | `when.type=expr` evaluates sandboxed expression | `test_when_expr_eval` |
| AC-2.4 | `when.type=expr` with disallowed builtin raises `ExprSyntaxError` | `test_when_expr_sandbox` |
| AC-2.5 | Steps in `parallel_groups` run concurrently (wall_clock < sum_sequential) | `test_parallel_wall_clock` |
| AC-2.6 | `ParallelConflictError` raised if group steps have inter-deps | `test_parallel_conflict_error` |
| AC-2.7 | Failed step in group applies `on_failure` after group completes | `test_parallel_on_failure` |
| AC-2.8 | SKIPPED step in group does not block other group steps | `test_parallel_skip_no_block` |
| AC-2.9 | `max_workers` respected (mock ThreadPoolExecutor) | `test_max_workers_respected` |
| AC-2.10 | `kiva pipeline validate` catches `ParallelConflictError` | `test_validate_parallel_conflict` |
| AC-2.11 | `kiva pipeline show` displays parallel group index | `test_show_parallel_group` |
| AC-2.12 | `PipelineResult.wall_clock_seconds` populated | `test_result_wall_clock` |

### Sprint 3 — BLO integration pipeline + hardening

| # | AC | Test |
|---|----|------|
| AC-3.1 | BLO pipeline `blo-validate.yaml` uses `when:` + `parallel:` | `test_blo_pipeline_e2e` |
| AC-3.2 | `when.type=file_changed` correctly detects no-change → skip | `test_when_file_changed_nochange` |
| AC-3.3 | Pipeline with all steps SKIPPED → `overall_status=SUCCESS` | `test_all_skipped_success` |
| AC-3.4 | `PipelineResult.skipped_steps` contains all skipped step names | `test_result_skipped_list` |
| AC-3.5 | `kiva pipeline run --dry-run -v` shows parallel group layout | `test_dry_run_parallel_verbose` |

---

## 6. Architecture & File Changes

```
kiva_cli/
  pipeline/
    pipeline_types.py        ← ADD: WhenCondition, StepStatus.SKIPPED, extend PipelineDefinition/Result
    condition_evaluator.py   ← NEW: evaluate_when(condition, context) → bool
    parallel_executor.py     ← NEW: ParallelGroupExecutor(ThreadPoolExecutor)
    pipeline_runner.py       ← MODIFY: integrate condition_evaluator + parallel_executor
    pipeline_loader.py       ← MODIFY: parse when: + parallel_groups: from YAML
    pipeline_manager.py      ← MODIFY: pass WhenContext to runner

tests/
  test_when_conditions.py    ← NEW (Sprint 1: AC-1.x)
  test_parallel_executor.py  ← NEW (Sprint 2: AC-2.x)
  test_blo_pipeline.py       ← NEW (Sprint 3: AC-3.x)
  fixtures/
    pipelines/
      blo-validate.yaml      ← NEW: BLO validation pipeline using when: + parallel:
```

### New module: `condition_evaluator.py`

```python
# kiva_cli/pipeline/condition_evaluator.py

from dataclasses import dataclass
from typing import Any
import os
from pathlib import Path
from .pipeline_types import WhenCondition, StepResult


@dataclass
class WhenContext:
    """Runtime context passed to condition evaluator."""
    env: dict[str, str]              # os.environ snapshot at pipeline start
    step_results: dict[str, StepResult]  # results of already-run steps
    wal_reader: Any | None = None    # optional: for file_changed, phi_cps


def evaluate_when(
    condition: WhenCondition | bool | None,
    context: WhenContext,
) -> bool:
    """Return True (run step) or False (skip step)."""
    if condition is None or condition is True:
        return True
    if condition is False:
        return False

    t = condition.type

    if t == "env":
        val = context.env.get(condition.var, None)
        if condition.exists is not None:
            return (val is not None) == condition.exists
        if condition.equals is not None:
            return val == condition.equals
        if condition.not_equals is not None:
            return val != condition.not_equals
        return val is not None

    if t == "file_exists":
        return Path(condition.path).exists()

    if t == "file_changed":
        # delegate to WAL reader; fallback = always True (run)
        if context.wal_reader is None:
            return True
        return context.wal_reader.has_changed_since(
            condition.path, condition.since
        )

    if t == "phi_cps":
        if context.wal_reader is None:
            return True
        cps = context.wal_reader.get_phi_cps(condition.repo)
        return _compare(cps, condition.op, condition.value)

    if t == "step_output":
        result = context.step_results.get(condition.step)
        if result is None:
            return True  # step hasn't run yet: don't skip
        if condition.exit_code is not None:
            return result.exit_code == condition.exit_code
        if condition.contains is not None:
            return condition.contains in (result.stdout or "")
        return True

    if t == "expr":
        return _eval_expr(condition.expression, context)

    raise ValueError(f"Unknown when condition type: {t!r}")


def _compare(value: float, op: str, threshold: float) -> bool:
    ops = {"gt": ">", "lt": "<", "gte": ">=", "lte": "<=", "eq": "=="}
    return eval(f"{value} {ops[op]} {threshold}")  # noqa: S307 — controlled


_SAFE_BUILTINS = {"str": str, "int": int, "bool": bool, "len": len, "True": True, "False": False, "None": None}


def _eval_expr(expression: str, context: WhenContext) -> bool:
    """Sandboxed eval — only safe builtins + env + step_results."""
    try:
        code = compile(expression, "<when:expr>", "eval")
    except SyntaxError as e:
        raise ValueError(f"ExprSyntaxError in when.expr: {e}") from e
    ns = {
        "__builtins__": _SAFE_BUILTINS,
        "env": context.env,
        "step_results": context.step_results,
    }
    result = eval(code, ns)  # noqa: S307
    return bool(result)
```

### New module: `parallel_executor.py`

```python
# kiva_cli/pipeline/parallel_executor.py

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Callable
from .pipeline_types import PipelineStep, StepResult, StepStatus


class ParallelConflictError(Exception):
    """Raised when steps in a parallel group have inter-dependencies."""


def validate_parallel_groups(
    steps: list[PipelineStep],
    parallel_groups: list[list[str]],
) -> None:
    """Raise ParallelConflictError if any group has intra-group deps."""
    step_map = {s.name: s for s in steps}
    for group in parallel_groups:
        group_set = set(group)
        for name in group:
            step = step_map.get(name)
            if step is None:
                raise ValueError(f"parallel_groups references unknown step: {name!r}")
            for dep in (step.depends_on or []):
                if dep in group_set:
                    raise ParallelConflictError(
                        f"Step {name!r} depends on {dep!r} — both in same parallel group"
                    )


def run_parallel_group(
    steps: list[PipelineStep],
    run_step_fn: Callable[[PipelineStep], StepResult],
    max_workers: int = 4,
) -> dict[str, StepResult]:
    """Run steps concurrently. Returns {step_name: StepResult}."""
    results: dict[str, StepResult] = {}
    with ThreadPoolExecutor(max_workers=min(max_workers, len(steps))) as pool:
        futures = {pool.submit(run_step_fn, step): step.name for step in steps}
        for future in as_completed(futures):
            name = futures[future]
            results[name] = future.result()
    return results
```

---

## 7. BLO Validation Pipeline (Sprint 3 target)

```yaml
# .kiva/pipelines/blo-validate.yaml
name: blo-validate
description: "BLO validation pipeline — when: + parallel: prototype (KIVA-009)"
max_workers: 3
on_failure: warn

steps:
  - name: check-env
    command: "python -c \"import sys; print(sys.version)\""

  - name: lint
    command: "ruff check src/ --quiet"
    depends_on: [check-env]
    when:
      type: file_exists
      path: "src/"

  - name: test-unit
    command: "pytest tests/ -q --tb=short"
    depends_on: [check-env]
    when:
      type: env
      var: SKIP_TESTS
      not_equals: "true"

  - name: phi-check
    command: "python -m kiva_cli.kiva phi-cps report BLO"
    depends_on: [check-env]
    when:
      type: phi_cps
      repo: BLO
      op: lt
      value: 2.0

  - name: nexus-tracking
    command: "python -m kiva_cli.kiva nexus tracking init BLO --dry-run"
    depends_on: [lint, test-unit]
    when:
      type: env
      var: NEXUS_SYNC
      equals: "true"

parallel_groups:
  - [lint, test-unit, phi-check]   # all run after check-env, concurrently
```

---

## 8. Sprint Plan

| Sprint | Scope | Deliverables | ACs |
|--------|-------|-------------|-----|
| **Sprint 1** | `when:` core (F1 basic) | `WhenCondition`, `condition_evaluator.py`, `StepStatus.SKIPPED`, loader, runner integration | AC-1.1 → 1.11 (11 tests) |
| **Sprint 2** | `when:` advanced + `parallel:` (F1 full + F2) | `parallel_executor.py`, advanced condition types (phi_cps, step_output, expr), validate extended | AC-2.1 → 2.12 (12 tests) |
| **Sprint 3** | BLO pipeline + hardening | `blo-validate.yaml`, `test_blo_pipeline.py`, `wall_clock_seconds`, `kiva pipeline show` extended | AC-3.1 → 3.5 (5 tests) |

**Total new tests: 28** (all must pass with 0 failures)

---

## 9. Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| `expr` sandbox escape | HIGH | Restrict `__builtins__` to explicit allowlist; run `compile()` pre-check; add fuzzing test |
| Thread safety in WAL append during parallel execution | MEDIUM | WAL `append_event` must be mutex-protected; use `threading.Lock` in WAL writer |
| Parallel group test flakiness (timing) | MEDIUM | Use `sleep`-based mock commands; assert `wall_clock < sum * 0.8` (not exact) |
| `file_changed` WAL dependency | LOW | Fallback = always True if WAL unavailable (safe default = run) |

---

## 10. Definition of Done

- [ ] All 28 ACs green (`pytest -q` passes)
- [ ] `kiva pipeline run blo-validate --dry-run -v` shows `[WOULD SKIP]` / parallel layout
- [ ] `kiva pipeline validate blo-validate` passes with no errors
- [ ] WAL emits `step_skipped` events with `reason: when_condition`
- [ ] `PipelineResult` includes `skipped_steps`, `wall_clock_seconds`, `parallel_groups_executed`
- [ ] Existing KIVA-008 test suite (21 tests) still passes (backward compat)
- [ ] `PRD-KIVA-009.md` marked `Status: CLOSED` in git history
- [ ] `DEPENDENCY_MATRIX.yaml` unchanged (no new deps introduced)
