"""
Budget allocator for T⁸ hierarchical strata.
Allocates the global mutation budget (100/cycle) across 8 strata with adaptive rules.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

BUDGET_TOTAL = 100

STRATES = [
    ("L0", 0.10, "cell_state"),
    ("L1", 0.08, "registres"),
    ("L2", 0.12, "composition"),
    ("L3", 0.20, "output_gate"),
    ("L4", 0.15, "input_gate"),
    ("L5", 0.03, "forget_gate"),
    ("L6", 0.18, "hidden_state"),
    ("L7", 0.14, "attention"),
]


@dataclass(frozen=True)
class StrataBudget:
    stratum: str
    base_pct: float
    role: str
    allocated: int
    instabilite: float


def allocate_budget(instabilite: Dict[str, float]) -> Dict[str, StrataBudget]:
    """
    Allocate the global mutation budget across 8 strata.

    Rules:
    - Unstable stratum (∇H high) gets +50% budget, capped at 25% of total.
    - Stable stratum gets base allocation.
    - Budget is renormalized to exactly BUDGET_TOTAL.
    """
    if not instabilite:
        instabilite = {s: 0.0 for s, _, _ in STRATES}

    budget: Dict[str, StrataBudget] = {}
    total_allocated = 0.0

    for stratum, base_pct, role in STRATES:
        base = BUDGET_TOTAL * base_pct
        score = instabilite.get(stratum, 0.0)
        if score > 0.7:
            allocated = min(base * 1.5, BUDGET_TOTAL * 0.25)
        else:
            allocated = base
        budget[stratum] = StrataBudget(
            stratum=stratum,
            base_pct=base_pct,
            role=role,
            allocated=int(allocated),
            instabilite=score,
        )
        total_allocated += allocated

    if total_allocated > BUDGET_TOTAL:
        factor = BUDGET_TOTAL / total_allocated
        raw = {
            s: b.allocated * factor
            for s, b in budget.items()
        }
        # Distribuer le reste pour que la somme fasse exactement BUDGET_TOTAL
        base_ints = {s: int(v) for s, v in raw.items()}
        remainder = BUDGET_TOTAL - sum(base_ints.values())
        # Ajouter 1 aux strates avec la plus grande fraction restante
        fractions = {s: raw[s] - base_ints[s] for s in raw}
        for s, _ in sorted(fractions.items(), key=lambda x: x[1], reverse=True)[:remainder]:
            base_ints[s] += 1
        budget = {
            s: StrataBudget(
                stratum=b.stratum,
                base_pct=b.base_pct,
                role=b.role,
                allocated=base_ints[s],
                instabilite=b.instabilite,
            )
            for s, b in budget.items()
        }

    return budget


def transfer_residual(src: str, dst: str, amount: int) -> None:
    """
    Transfer unused budget from src stratum to dst stratum.
    This is a no-op here; actual transfer is done by re-running allocate_budget().
    """
    if amount <= 0:
        return
    # In a real implementation, this would adjust the next cycle's allocation.
    # For now, it documents the intended behavior.
    print(f"[BUDGET] Transfer {amount} mutations from {src} to {dst}")
