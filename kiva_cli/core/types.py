"""
KIVA-CLI Shared Types Registry — Single Source of Truth

This module consolidates all canonical type definitions for the KIVA-CLI ecosystem.

All modules SHOULD import from here instead of redefining:
- Base-3 validation states
- Base-4 lifecycle states
- Result contracts
- Domain models (Project, Framework, Template, etc.)
- Type aliases (IntentHash, PhiCPS, etc.)

Version: 1.0.0 (PRD-KIVA-004)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import IntEnum
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Tuple


# =============================================================================
# BASE-3 TERNARY VALIDATION
# =============================================================================

class ValidationState(IntEnum):
    """
    Base-3 semantic validation state.

    Used across the entire KIVA ecosystem for consistent state machines.
    """
    UNKNOWN = 0   # Not yet validated / pending
    VALID = 1     # Successfully validated
    INVALID = -1  # Failed validation

    @property
    def is_valid(self) -> bool:
        return self == ValidationState.VALID

    @property
    def is_invalid(self) -> bool:
        return self == ValidationState.INVALID

    @property
    def is_unknown(self) -> bool:
        return self == ValidationState.UNKNOWN

    @classmethod
    def from_str(cls, value: str) -> "ValidationState":
        """Convert string to ValidationState (case-insensitive)."""
        mapping = {
            "unknown": cls.UNKNOWN,
            "valid": cls.VALID,
            "invalid": cls.INVALID,
            "0": cls.UNKNOWN,
            "1": cls.VALID,
            "-1": cls.INVALID,
        }
        return mapping.get(str(value).lower(), cls.UNKNOWN)

    def __str__(self) -> str:
        return self.name


# Backward-compatible string alias (used in some older code)
ValidationStateStr = Literal["UNKNOWN", "VALID", "INVALID"]


# =============================================================================
# BASE-4 LIFECYCLE
# =============================================================================

class LifecycleState(IntEnum):
    """
    Base-4 project / entity lifecycle management.
    """
    GENESIS = 0      # Just created / initialized
    ACTIVE = 1       # In active use / development
    DEPRECATED = 2   # Marked for retirement
    ARCHIVED = 3     # Read-only / historical

    @classmethod
    def from_str(cls, value: str) -> "LifecycleState":
        mapping = {
            "genesis": cls.GENESIS,
            "active": cls.ACTIVE,
            "deprecated": cls.DEPRECATED,
            "archived": cls.ARCHIVED,
        }
        return mapping.get(str(value).lower(), cls.GENESIS)


# =============================================================================
# COMMON RESULT CONTRACTS
# =============================================================================

@dataclass
class KivaResult:
    """Base result contract used by most KIVA operations."""
    success: bool
    validation_state: ValidationState = ValidationState.UNKNOWN
    message: str = ""
    intent_hash: Optional[str] = None
    phi_cps_delta: float = 0.0
    artifacts: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    @property
    def is_success(self) -> bool:
        return self.success and self.validation_state == ValidationState.VALID


@dataclass
class ConfigResult(KivaResult):
    """Result of configuration validation / generation."""
    config_data: Optional[Dict[str, Any]] = None


@dataclass
class ValidationResult(KivaResult):
    """Detailed validation result (used by ConfigValidator, etc.)."""
    confidence: float = 0.0  # 0.0 to 1.0


@dataclass
class DeploymentResult(KivaResult):
    """Result of a deployment operation."""
    target: str = ""
    deployment_id: Optional[str] = None


@dataclass
class RepairReport(KivaResult):
    """Result of a repair operation (PRD-KIVA-001)."""
    repair_id: str = ""
    failure_source: str = ""       # e.g. "post_commit_verifier:abc123"
    detected_pattern: str = ""
    strategies_applied: List[str] = field(default_factory=list)
    files_modified: List[str] = field(default_factory=list)
    confidence: float = 0.0        # 0.0 to 1.0
    before_state: Dict[str, Any] = field(default_factory=dict)
    after_state: Dict[str, Any] = field(default_factory=dict)
    wal_event_id: str = ""


# =============================================================================
# DOMAIN TYPES
# =============================================================================

class FrameworkType(IntEnum):
    """Supported project framework templates."""
    FASTAPI = 0
    REACT = 1
    GO_SERVICE = 2
    PYTHON_LIB = 3
    DOCKER_COMPOSE = 4
    LXC_CONTAINER = 5
    RUST_SERVICE = 6

    @classmethod
    def from_str(cls, value: str) -> "FrameworkType":
        mapping = {
            "fastapi": cls.FASTAPI,
            "react": cls.REACT,
            "go_service": cls.GO_SERVICE,
            "go": cls.GO_SERVICE,
            "python_lib": cls.PYTHON_LIB,
            "docker_compose": cls.DOCKER_COMPOSE,
            "lxc_container": cls.LXC_CONTAINER,
            "lxc": cls.LXC_CONTAINER,
            "rust": cls.RUST_SERVICE,
            "rust_service": cls.RUST_SERVICE,
        }
        return mapping.get(str(value).lower(), cls.FASTAPI)


@dataclass
class ProjectConfig:
    """Canonical project configuration metadata."""
    name: str
    framework: str
    repo_path: Path
    lifecycle_state: LifecycleState = LifecycleState.GENESIS
    validation_state: ValidationState = ValidationState.UNKNOWN
    intent_hash: Optional[str] = None
    phi_cps_delta: float = 0.0
    created_at: str = ""
    updated_at: str = ""
    dependencies: List[str] = field(default_factory=list)
    deployment_targets: List[str] = field(default_factory=list)

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        self.updated_at = datetime.now().isoformat()


@dataclass
class Template:
    """Project template definition (used by TemplateRegistry)."""
    name: str
    language: str
    framework: Optional[str] = None
    description: str = ""
    files: Dict[str, str] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)
    dev_dependencies: List[str] = field(default_factory=list)
    scripts: Dict[str, str] = field(default_factory=dict)
    env_vars: List[str] = field(default_factory=list)
    docker_support: bool = True
    ci_cd_support: bool = True


class DeploymentStrategy(IntEnum):
    """Standard deployment strategies."""
    ROLLING = 0
    BLUE_GREEN = 1
    CANARY = 2


# =============================================================================
# TYPE ALIASES (for clarity and documentation)
# =============================================================================

IntentHash = str                    # "0x..."
PhiCPSValue = float
RepoPath = Path
EntityId = str
Status = Literal["PENDING", "SUCCESS", "FAILED"]  # Legacy Base-3 string status


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    # Base-3
    "ValidationState",
    "ValidationStateStr",
    # Base-4
    "LifecycleState",
    # Results
    "KivaResult",
    "ConfigResult",
    "ValidationResult",
    "DeploymentResult",
    # Repair (PRD-KIVA-001)
    "RepairReport",
    # Domain
    "FrameworkType",
    "ProjectConfig",
    "Template",
    "DeploymentStrategy",
    # Aliases
    "IntentHash",
    "PhiCPSValue",
    "RepoPath",
    "EntityId",
    "Status",
]
