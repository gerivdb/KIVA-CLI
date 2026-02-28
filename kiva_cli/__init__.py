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

# Base-3 Status Enum
Status = Literal["PENDING", "SUCCESS", "FAILED"]

# Base-4 Lifecycle Enum
Lifecycle = Literal["GENESIS", "ACTIVE", "DEPRECATED", "ARCHIVED"]
