"""Condition Evaluator for pipeline steps (KIVA-009 F1 + KIVA-011).

Two modes supported:
1. Structured `WhenCondition` objects (legacy path — KIVA-009)
2. Simple string expressions via `evaluate_when(when, context)` — primary for KIVA-011 `when: "..."`

Safe sandboxed evaluation (no arbitrary code execution).
"""

from __future__ import annotations

import ast
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from kiva_cli.core.pipeline_types import (
    WhenCondition,
    WhenEvaluationResult,
    ConditionType,
)


# ---------------------------------------------------------------------------
# Safe expression evaluator (for type="expr" and KIVA-011 string when:)
# ---------------------------------------------------------------------------

_ALLOWED_NODES = (
    ast.Expression,
    ast.Constant,
    ast.Name,
    ast.Load,
    ast.Compare,
    ast.BinOp,
    ast.UnaryOp,
    ast.BoolOp,
    ast.IfExp,
    ast.Call,
    ast.Attribute,
    ast.Subscript,
    ast.List,
    ast.Tuple,
    ast.Dict,
    ast.Set,
    ast.comprehension,
    ast.ListComp,
    ast.DictComp,
    ast.SetComp,
    ast.GeneratorExp,
    ast.NameConstant,  # Python < 3.8
    ast.Num,
    ast.Str,
    ast.Bytes,
    ast.Ellipsis,
    ast.And,
    ast.Or,
    ast.Not,
    ast.Eq,
    ast.NotEq,
    ast.Lt,
    ast.LtE,
    ast.Gt,
    ast.GtE,
    ast.Is,
    ast.IsNot,
    ast.In,
    ast.NotIn,
    ast.Add,
    ast.Sub,
    ast.Mult,
    ast.Div,
    ast.FloorDiv,
    ast.Mod,
    ast.Pow,
    ast.LShift,
    ast.RShift,
    ast.BitOr,
    ast.BitXor,
    ast.BitAnd,
    ast.MatMult,
    ast.Invert,
    ast.UAdd,
    ast.USub,
)

_ALLOWED_NAMES = {
    "True", "False", "None",
    "len", "str", "int", "float", "bool", "abs", "min", "max",
    "any", "all", "sorted", "sum", "enumerate",
}

_ALLOWED_ATTRS = {
    "lower", "upper", "strip", "startswith", "endswith", "split",
    "replace", "count", "find", "index", "get",
}

_SAFE_BUILTINS = {name: __builtins__[name] for name in _ALLOWED_NAMES if name in __builtins__}  # type: ignore[index]


def _safe_eval_expr(expr: str, context: Dict[str, Any]) -> Any:
    """Evaluate a Python expression in a very restricted sandbox.

    Only allows the nodes and names listed above.
    No imports, no attribute access outside allowlist, no arbitrary calls.
    """
    try:
        tree = ast.parse(expr, mode="eval")
    except SyntaxError as e:
        raise ValueError(f"Invalid expression syntax: {e}") from e

    for node in ast.walk(tree):
        if not isinstance(node, _ALLOWED_NODES):
            raise ValueError(f"Disallowed AST node: {type(node).__name__}")

        if isinstance(node, ast.Name) and node.id not in _ALLOWED_NAMES and node.id not in context:
            raise ValueError(f"Name not allowed: {node.id}")

        if isinstance(node, ast.Attribute):
            if node.attr not in _ALLOWED_ATTRS:
                raise ValueError(f"Attribute access not allowed: .{node.attr}")

        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id not in _ALLOWED_NAMES:
                raise ValueError(f"Function call not allowed: {node.func.id}")

    safe_globals = {"__builtins__": {}}
    safe_locals = {k: v for k, v in context.items() if not k.startswith("__")}
    safe_locals.update(_SAFE_BUILTINS)

    return eval(  # nosec: B307 — AST validated above
        compile(tree, "<condition_expr>", "eval"),
        safe_globals,
        safe_locals,
    )


# ---------------------------------------------------------------------------
# Main Evaluator (structured WhenCondition — legacy KIVA-009 path)
# ---------------------------------------------------------------------------

class ConditionEvaluator:
    """Evaluates a list of WhenCondition objects against a runtime context."""

    def __init__(self, context: Optional[Dict[str, Any]] = None):
        self.context = context or {}

    def evaluate(self, conditions: List[WhenCondition]) -> List[WhenEvaluationResult]:
        """Evaluate all conditions. Returns one result per condition (AND semantics)."""
        return [self._evaluate_one(cond) for cond in conditions]

    def all_pass(self, conditions: List[WhenCondition]) -> bool:
        """Return True only if every condition passes."""
        return all(r.passed for r in self.evaluate(conditions))

    def _evaluate_one(self, cond: WhenCondition) -> WhenEvaluationResult:
        try:
            dispatch = {
                "env": self._eval_env,
                "file_exists": self._eval_file_exists,
                "file_changed": self._eval_file_changed,
                "phi_cps": self._eval_phi_cps,
                "step_output": self._eval_step_output,
                "expr": self._eval_expr,
            }
            handler = dispatch.get(cond.type)
            if handler is None:
                return WhenEvaluationResult(
                    condition_type=cond.type,
                    passed=False,
                    reason=f"Unknown condition type: {cond.type}",
                )
            return handler(cond)
        except Exception as e:
            return WhenEvaluationResult(
                condition_type=cond.type,
                passed=False,
                reason=f"Evaluation error: {e}",
            )

    # -----------------------------------------------------------------------
    # Individual evaluators
    # -----------------------------------------------------------------------

    def _eval_env(self, cond: WhenCondition) -> WhenEvaluationResult:
        var_name = cond.var
        if not var_name:
            return WhenEvaluationResult(condition_type="env", passed=False, reason="No variable specified")

        actual = os.environ.get(var_name, "")

        if cond.equals is not None:
            passed = actual == str(cond.equals)
            reason = f"env[{var_name}]=={cond.equals!r} (actual={actual!r})"
        elif cond.not_equals is not None:
            passed = actual != str(cond.not_equals)
            reason = f"env[{var_name}]!={cond.not_equals!r} (actual={actual!r})"
        else:
            passed = bool(actual)
            reason = f"env[{var_name}] is {'set' if passed else 'unset'}"

        return WhenEvaluationResult(condition_type="env", passed=passed, reason=reason)

    def _eval_file_exists(self, cond: WhenCondition) -> WhenEvaluationResult:
        if not cond.path:
            return WhenEvaluationResult(condition_type="file_exists", passed=False, reason="No path specified")
        exists = Path(cond.path).exists()
        return WhenEvaluationResult(
            condition_type="file_exists",
            passed=exists,
            reason=f"file_exists({cond.path!r}) = {exists}",
        )

    def _eval_file_changed(self, cond: WhenCondition) -> WhenEvaluationResult:
        if not cond.path:
            return WhenEvaluationResult(condition_type="file_changed", passed=False, reason="No path specified")
        p = Path(cond.path)
        if not p.exists():
            return WhenEvaluationResult(condition_type="file_changed", passed=False, reason=f"{cond.path!r} not found")
        import time
        age = time.time() - p.stat().st_mtime
        since = cond.since_seconds or 0.0
        passed = age <= since
        return WhenEvaluationResult(
            condition_type="file_changed",
            passed=passed,
            reason=f"file_changed({cond.path!r}): age={age:.1f}s <= {since}s = {passed}",
        )

    def _eval_phi_cps(self, cond: WhenCondition) -> WhenEvaluationResult:
        current = float(self.context.get("current_phi_cps", 0.0))
        threshold = float(cond.value) if cond.value is not None else 0.0
        op = cond.op or "eq"
        ops = {"gt": current > threshold, "lt": current < threshold,
               "gte": current >= threshold, "lte": current <= threshold,
               "eq": abs(current - threshold) < 1e-6}
        passed = ops.get(op, False)
        return WhenEvaluationResult(
            condition_type="phi_cps",
            passed=passed,
            reason=f"phi_cps {op} {threshold} (current={current})",
        )

    def _eval_step_output(self, cond: WhenCondition) -> WhenEvaluationResult:
        if not cond.step:
            return WhenEvaluationResult(condition_type="step_output", passed=False, reason="No step name specified")
        step_results = self.context.get("step_results", {})
        step_res = step_results.get(cond.step)
        if step_res is None:
            return WhenEvaluationResult(condition_type="step_output", passed=False, reason=f"step {cond.step!r} not found")
        if cond.exit_code is not None:
            passed = step_res.returncode == int(cond.exit_code)
            reason = f"step_output({cond.step!r}).returncode == {cond.exit_code}"
        elif cond.stdout_contains:
            actual = (step_res.stdout or "") + (step_res.stderr or "")
            passed = cond.stdout_contains in actual
            reason = f"step_output({cond.step!r}) contains {cond.stdout_contains!r}"
        else:
            passed = False
            reason = "No exit_code or stdout_contains specified"
        return WhenEvaluationResult(condition_type="step_output", passed=passed, reason=reason)

    def _eval_expr(self, cond: WhenCondition) -> WhenEvaluationResult:
        if not cond.expr:
            return WhenEvaluationResult(condition_type="expr", passed=False, reason="No expression provided")
        try:
            result = _safe_eval_expr(cond.expr, self.context)
            return WhenEvaluationResult(
                condition_type="expr",
                passed=bool(result),
                reason=f"expr: {cond.expr!r} => {result}",
            )
        except Exception as e:
            return WhenEvaluationResult(condition_type="expr", passed=False, reason=f"expr failed: {e}")


def evaluate_conditions(
    conditions: List[WhenCondition], context: Optional[Dict[str, Any]] = None
) -> List[WhenEvaluationResult]:
    """Convenience function for structured WhenCondition list (legacy KIVA-009 path)."""
    return ConditionEvaluator(context or {}).evaluate(conditions)


# ---------------------------------------------------------------------------
# KIVA-011 — Primary string expression API
# ---------------------------------------------------------------------------

def evaluate_when(when: str, context: Optional[Dict[str, Any]] = None) -> bool:
    """Evaluate a `when:` string expression from a pipeline Step (KIVA-011).

    Returns True if the step should run, False if it should be SKIPPED.

    Rules:
    - Empty / whitespace-only when → True (always execute, backward-compatible)
    - Uses safe AST sandbox (_safe_eval_expr) — same as structured 'expr' conditions
    - On any error (syntax, unknown name, etc.) → False + silent skip (no crash)

    Context variables available in expressions:
      last_status              : str   — 'SUCCESS' | 'FAILED' | 'PARTIAL' | 'ABORTED'
      dry_run                  : bool  — True if pipeline running in dry-run mode
      parallel_groups_executed : int   — number of parallel groups completed so far
      env                      : dict  — os.environ proxy (use env.get('VAR'))
      Any custom key/value passed in the context dict

    Examples:
      evaluate_when("")                              # → True
      evaluate_when("last_status == 'SUCCESS'")
      evaluate_when("not dry_run")
      evaluate_when("parallel_groups_executed > 0 and last_status == 'SUCCESS'")
      evaluate_when("env.get('CI') == '1'", {"env": dict(os.environ)})
    """
    if not when or not when.strip():
        return True

    ctx = context or {}
    try:
        result = _safe_eval_expr(when, ctx)
        return bool(result)
    except Exception:
        # Conservative: on any error, skip the step rather than crashing the pipeline
        return False
