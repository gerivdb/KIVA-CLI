"""KIVA CLI - EnvGuard
Infrastructure Topology-Aware Design (ITAD) - Environment Guard

Validates deployment compatibility with target environment constraints
before any deployment operation. Implements the β-CONSTRAIN axiom of ITAD.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class EnvID(str, Enum):
    """Environment identifiers."""
    ENV1 = "ENV1"  # DEV COMET - cloud AI
    ENV2 = "ENV2"  # Z600 - local workstation
    ENV3 = "ENV3"  # cloud_burst - optional overflow
    ENV4 = "ENV4"  # FLUENCE main - production
    ENV5 = "ENV5"  # APPFLOWY - knowledge base
    ENV6 = "ENV6"  # TEST - sandbox


class ViolationSeverity(Enum):
    """Severity of constraint violations."""
    BLOCKING = "blocking"  # Deployment must be blocked
    WARNING = "warning"    # Deployment allowed with warnings
    INFO = "info"          # Informational only


@dataclass
class EnvConstraint:
    """Constraint definition for an environment."""
    name: str
    description: str
    severity: ViolationSeverity
    check_fn: str  # Method name to call for check


@dataclass
class EnvProfile:
    """Environment profile with constraints."""
    env_id: EnvID
    alias: str
    env_type: str  # cloud_ai, local_workstation, cloud_optional, production
    constraints: Dict[str, Any] = field(default_factory=dict)
    forbidden_patterns: List[str] = field(default_factory=list)
    required_capabilities: List[str] = field(default_factory=list)


@dataclass
class Violation:
    """A constraint violation."""
    constraint: str
    message: str
    severity: ViolationSeverity
    current_value: Any = None
    required_value: Any = None


@dataclass
class EnvGuardResult:
    """Result of environment guard check."""
    compatible: bool
    env_id: EnvID
    violations: List[Violation] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    verdict: str = "DEPLOY_OK"  # DEPLOY_OK, DEPLOY_BLOCKED, DEPLOY_WITH_WARNINGS

    @property
    def can_deploy(self) -> bool:
        """Check if deployment can proceed."""
        return self.verdict in ["DEPLOY_OK", "DEPLOY_WITH_WARNINGS"]


class EnvGuard:
    """
    Infrastructure Topology-Aware Design (ITAD) - Environment Guard
    
    Validates deployment compatibility with target environment constraints.
    Implements the β-CONSTRAIN axiom: "Tout composant hérite contraintes ENV"
    
    Usage:
        guard = EnvGuard(topology_path="architecture/ecos_topology.json")
        result = guard.check(citizen, target_env="ENV2")
        if not result.can_deploy:
            print(f"Deployment blocked: {result.violations}")
    """

    # Default environment profiles (can be overridden by topology file)
    DEFAULT_PROFILES: Dict[str, EnvProfile] = {
        "ENV1": EnvProfile(
            env_id=EnvID.ENV1,
            alias="DEV COMET",
            env_type="cloud_ai",
            constraints={
                "ram_max_mb": None,  # Unlimited
                "vram_max_mb": None,
                "local_inference": False,
                "cloud_required": True,
            },
            forbidden_patterns=[],
            required_capabilities=["cloud_api"],
        ),
        "ENV2": EnvProfile(
            env_id=EnvID.ENV2,
            alias="Z600",
            env_type="local_workstation",
            constraints={
                "ram_max_mb": 8192,
                "vram_max_mb": 4096,
                "ram_runtime_max_mb": 8192,
                "local_inference": True,
                "docker_forbidden": False,
                "cloud_required": False,
                "sovereignty_target": 0.70,
            },
            forbidden_patterns=["cloud_api_mandatory", "docker_required"],
            required_capabilities=["local_inference_capable", "python_gte_311"],
        ),
        "ENV3": EnvProfile(
            env_id=EnvID.ENV3,
            alias="cloud_burst",
            env_type="cloud_optional",
            constraints={
                "ram_max_mb": None,
                "vram_max_mb": None,
                "use_only_if": "ENV2_overloaded",
            },
            forbidden_patterns=[],
            required_capabilities=[],
        ),
        "ENV4": EnvProfile(
            env_id=EnvID.ENV4,
            alias="FLUENCE main",
            env_type="production",
            constraints={
                "ram_max_mb": 16384,
                "vram_max_mb": 8192,
                "high_availability": True,
                "backup_required": True,
            },
            forbidden_patterns=["experimental"],
            required_capabilities=["production_ready", "monitoring_enabled"],
        ),
        "ENV5": EnvProfile(
            env_id=EnvID.ENV5,
            alias="APPFLOWY",
            env_type="knowledge_base",
            constraints={
                "ram_max_mb": 4096,
                "sync_required": True,
            },
            forbidden_patterns=[],
            required_capabilities=["sync_capable"],
        ),
        "ENV6": EnvProfile(
            env_id=EnvID.ENV6,
            alias="TEST",
            env_type="sandbox",
            constraints={
                "ram_max_mb": 2048,
                "ephemeral": True,
            },
            forbidden_patterns=["production_data"],
            required_capabilities=[],
        ),
    }

    def __init__(self, topology_path: Optional[str] = None):
        """
        Initialize EnvGuard.
        
        Args:
            topology_path: Path to ecos_topology.json for custom profiles
        """
        self.profiles: Dict[str, EnvProfile] = dict(self.DEFAULT_PROFILES)
        self.topology_path = topology_path
        
        if topology_path:
            self._load_topology(topology_path)
    
    def _load_topology(self, path: str) -> None:
        """Load environment profiles from topology file."""
        try:
            topology_file = Path(path)
            if not topology_file.exists():
                logger.warning(f"Topology file not found: {path}")
                return
            
            with open(topology_file, 'r', encoding='utf-8') as f:
                topology = json.load(f)
            
            environments = topology.get("environments", {})
            for env_id, env_config in environments.items():
                if env_id in self.profiles:
                    # Update existing profile
                    profile = self.profiles[env_id]
                    profile.constraints.update(env_config.get("constraints", {}))
                    if "forbidden" in env_config:
                        profile.forbidden_patterns.extend(env_config["forbidden"])
                    if "required" in env_config:
                        profile.required_capabilities.extend(env_config["required"])
            
            logger.info(f"Loaded topology from {path}: {len(environments)} environments")
            
        except Exception as e:
            logger.error(f"Failed to load topology: {e}")
    
    def check(
        self,
        citizen: Any,
        target_env: str,
        deployment_config: Optional[Dict[str, Any]] = None
    ) -> EnvGuardResult:
        """
        Check if a citizen/component is compatible with target environment.
        
        Args:
            citizen: The citizen/component to check (must have env_requirements attr)
            target_env: Target environment ID (ENV1, ENV2, etc.)
            deployment_config: Optional deployment configuration
        
        Returns:
            EnvGuardResult with compatibility status and violations
        """
        if target_env not in self.profiles:
            return EnvGuardResult(
                compatible=False,
                env_id=target_env,  # type: ignore
                violations=[Violation(
                    constraint="env_exists",
                    message=f"Unknown environment: {target_env}",
                    severity=ViolationSeverity.BLOCKING
                )],
                verdict="DEPLOY_BLOCKED"
            )
        
        profile = self.profiles[target_env]
        violations: List[Violation] = []
        warnings: List[str] = []
        
        # Get citizen requirements
        requirements = getattr(citizen, "env_requirements", {})
        ram_mb = requirements.get("ram_mb", 0)
        vram_mb = requirements.get("vram_mb", 0)
        capabilities = requirements.get("capabilities", [])
        patterns = requirements.get("patterns", [])
        
        # Check RAM constraint
        ram_max = profile.constraints.get("ram_max_mb")
        if ram_max and ram_mb > ram_max:
            violations.append(Violation(
                constraint="ram_limit",
                message=f"RAM {ram_mb}MB exceeds limit {ram_max}MB for {target_env}",
                severity=ViolationSeverity.BLOCKING,
                current_value=ram_mb,
                required_value=ram_max
            ))
        
        # Check VRAM constraint
        vram_max = profile.constraints.get("vram_max_mb")
        if vram_max and vram_mb > vram_max:
            violations.append(Violation(
                constraint="vram_limit",
                message=f"VRAM {vram_mb}MB exceeds limit {vram_max}MB for {target_env}",
                severity=ViolationSeverity.BLOCKING,
                current_value=vram_mb,
                required_value=vram_max
            ))
        
        # Check forbidden patterns
        for pattern in patterns:
            if pattern in profile.forbidden_patterns:
                violations.append(Violation(
                    constraint="forbidden_pattern",
                    message=f"Pattern '{pattern}' is forbidden in {target_env}",
                    severity=ViolationSeverity.BLOCKING,
                    current_value=pattern
                ))
        
        # Check required capabilities
        for cap in profile.required_capabilities:
            if cap not in capabilities:
                violations.append(Violation(
                    constraint="required_capability",
                    message=f"Capability '{cap}' is required for {target_env}",
                    severity=ViolationSeverity.BLOCKING,
                    required_value=cap
                ))
        
        # Check cloud requirements
        if profile.constraints.get("cloud_required") and not requirements.get("cloud_capable", False):
            violations.append(Violation(
                constraint="cloud_required",
                message=f"Cloud capability required for {target_env}",
                severity=ViolationSeverity.BLOCKING
            ))
        
        # Check local inference requirements
        if profile.constraints.get("local_inference") and not requirements.get("local_inference_capable", False):
            violations.append(Violation(
                constraint="local_inference_required",
                message=f"Local inference capability required for {target_env}",
                severity=ViolationSeverity.BLOCKING
            ))
        
        # Determine verdict
        blocking_violations = [v for v in violations if v.severity == ViolationSeverity.BLOCKING]
        warning_violations = [v for v in violations if v.severity == ViolationSeverity.WARNING]
        
        if blocking_violations:
            verdict = "DEPLOY_BLOCKED"
        elif warning_violations:
            verdict = "DEPLOY_WITH_WARNINGS"
            warnings = [v.message for v in warning_violations]
        else:
            verdict = "DEPLOY_OK"
        
        return EnvGuardResult(
            compatible=len(blocking_violations) == 0,
            env_id=target_env,  # type: ignore
            violations=violations,
            warnings=warnings,
            verdict=verdict
        )
    
    def get_profile(self, env_id: str) -> Optional[EnvProfile]:
        """Get environment profile by ID."""
        return self.profiles.get(env_id)
    
    def list_environments(self) -> List[str]:
        """List all available environment IDs."""
        return list(self.profiles.keys())
    
    def validate_installation_citizen(self, citizen: Any) -> bool:
        """
        Validate an InstallationCitizen against its declared environment.
        
        This is the primary validation method for ITAD compliance.
        Axiom β-CONSTRAIN: "Tout composant hérite contraintes ENV"
        
        Args:
            citizen: InstallationCitizen with env_id and constraints
        
        Returns:
            True if citizen complies with environment constraints
        """
        if not hasattr(citizen, "env_id"):
            logger.error("Citizen has no env_id attribute")
            return False
        
        if not hasattr(citizen, "validate_env_compliance"):
            logger.error("Citizen has no validate_env_compliance method")
            return False
        
        return citizen.validate_env_compliance()


# Convenience function for quick checks
def quick_check(
    ram_mb: int = 0,
    vram_mb: int = 0,
    capabilities: List[str] = None,
    patterns: List[str] = None,
    target_env: str = "ENV2",
    topology_path: Optional[str] = None
) -> EnvGuardResult:
    """
    Quick environment compatibility check.
    
    Args:
        ram_mb: RAM requirement in MB
        vram_mb: VRAM requirement in MB
        capabilities: List of capabilities
        patterns: List of patterns
        target_env: Target environment ID
        topology_path: Path to topology file
    
    Returns:
        EnvGuardResult with compatibility status
    """
    guard = EnvGuard(topology_path=topology_path)
    
    # Create a simple citizen-like object
    class SimpleCitizen:
        env_requirements = {
            "ram_mb": ram_mb,
            "vram_mb": vram_mb,
            "capabilities": capabilities or [],
            "patterns": patterns or [],
        }
    
    return guard.check(SimpleCitizen(), target_env)