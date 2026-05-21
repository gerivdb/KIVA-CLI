"""KIVA-CLI: Project & Application Orchestration CLI

Autonomous orchestrator for project initialization, deployment management,
and cross-repo coordination with ECOS ecosystem integration.

Architecture:
- Gateway pattern: Delegates to specialized CLIs (ECOS, BRAIN, FLUENCE)
- Base-3 state: PENDING (0), SUCCESS (1), FAILED (2)
- φ-CPS tracking: Global coherence validation
- IntentHash¹¹: Cryptographic integrity

Usage:
    kiva project init --template fastapi --name my-api
    kiva deploy staging --env production
    kiva rollback --deployment-id abc123
"""

__version__ = "0.1.0-alpha"
__author__ = "ECOS Ecosystem - H0 Autonomous"
__mode__ = "H0_AUTONOMOUS_BASE3_NO_HITL"

from typing import Literal

# =============================================================================
# SHARED TYPES REGISTRY (PRD-KIVA-004)
# Re-export canonical types at package level for convenience.
# Prefer importing from kiva_cli.core.types for new code.
# =============================================================================
from .core.types import (
    ValidationState,
    LifecycleState,
    KivaResult,
    FrameworkType,
    ProjectConfig,
    IntentHash,
    Status,  # re-exported alias
)

# Legacy aliases (kept for backward compat)
Lifecycle = Literal["GENESIS", "ACTIVE", "DEPRECATED", "ARCHIVED"]  # prefer LifecycleState

__all__ = [
    "ValidationState",
    "LifecycleState",
    "KivaResult",
    "FrameworkType",
    "ProjectConfig",
    "IntentHash",
    "Status",
    "Lifecycle",
]
