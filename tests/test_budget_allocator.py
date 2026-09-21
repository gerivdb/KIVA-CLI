"""
Tests for budget_allocator.py — T⁸ hierarchical budget allocation.
"""

from __future__ import annotations

import pytest

from kiva_cli.cli.budget_allocator import allocate_budget, BUDGET_TOTAL, STRATES


def test_default_allocation_sums_to_total():
    budget = allocate_budget({})
    assert sum(b.allocated for b in budget.values()) == BUDGET_TOTAL


def test_all_strata_present():
    budget = allocate_budget({})
    assert set(budget.keys()) == {s[0] for s in STRATES}


def test_unstable_stratum_gets_more():
    instabilite = {"L6": 0.9}
    budget = allocate_budget(instabilite)
    assert budget["L6"].allocated > BUDGET_TOTAL * 0.18


def test_stable_stratum_keeps_base():
    instabilite = {"L6": 0.1}
    budget = allocate_budget(instabilite)
    assert budget["L6"].allocated == int(BUDGET_TOTAL * 0.18)


def test_renormalization_keeps_total():
    instabilite = {s[0]: 0.9 for s in STRATES}
    budget = allocate_budget(instabilite)
    total = sum(b.allocated for b in budget.values())
    assert total == BUDGET_TOTAL
