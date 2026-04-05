"""KIVA CLI - Deployment Manager
Manages deployment operations with strategies, health checks, and ITAD EnvGuard.

Integrates Infrastructure Topology-Aware Design (ITAD) for environment-aware
deployments. All deployments are validated against environment constraints
before execution via EnvGuard.
"""

from dataclasses import dataclass
from typing import Optional, Dict, Any, List
from enum import Enum
import subprocess
import time
import logging

logger = logging.getLogger(__name__)

# ITAD EnvGuard import for environment constraint validation
from kiva_cli.core.env_guard import EnvGuard, EnvGuardResult, quick_check


class DeploymentStrategy(Enum):
    """Deployment strategies."""
    ROLLING = "rolling"
    BLUE_GREEN = "blue-green"
    CANARY = "canary"
    RECREATE = "recreate"


@dataclass
class DeploymentResult:
    """Result object for deployment operations."""
    success: bool
    version: Optional[str] = None
    deployment_url: Optional[str] = None
    strategy: Optional[str] = None
    duration_seconds: Optional[float] = None
    health_check_passed: bool = False
    error: Optional[str] = None
    warnings: Optional[List[str]] = None


class DeploymentManager:
    """Manages deployment operations with ITAD EnvGuard integration.
    
    All deployments are validated against environment constraints before
    execution. If EnvGuard returns DEPLOY_BLOCKED, the deployment is
    rejected with a clear error message.
    """
    
    def __init__(self, topology_path: Optional[str] = None):
        self.deployments: Dict[str, Any] = {}
        self.env_guard = EnvGuard(topology_path=topology_path)
    
    def validate_env_compatibility(
        self,
        citizen: Any,
        target_env: str
    ) -> EnvGuardResult:
        """
        Validate citizen compatibility with target environment.
        
        This method implements the ITAD β-CONSTRAIN axiom:
        "Tout composant hérite contraintes ENV"
        
        Args:
            citizen: The citizen/component to validate
            target_env: Target environment ID (ENV1, ENV2, etc.)
        
        Returns:
            EnvGuardResult with compatibility status
        
        Raises:
            ValueError: If deployment is blocked by EnvGuard
        """
        result = self.env_guard.check(citizen, target_env)
        
        if not result.can_deploy:
            violation_msgs = [v.message for v in result.violations]
            raise ValueError(
                f"ITAD EnvGuard blocked deployment to {target_env}: "
                f"{'; '.join(violation_msgs)}"
            )
        
        if result.warnings:
            for warning in result.warnings:
                logger.warning(f"ITAD EnvGuard warning: {warning}")
        
        logger.info(f"ITAD EnvGuard validation passed for {target_env}: {result.verdict}")
        return result
    
    def deploy_with_itad(
        self,
        target: str,
        citizen: Any,
        target_env: str,
        strategy: str = "rolling",
        dry_run: bool = False,
        health_check: bool = True
    ) -> DeploymentResult:
        """
        Deploy with ITAD EnvGuard validation.
        
        This is the primary deployment method for ITAD-compliant deployments.
        It validates the citizen against the target environment before
        proceeding with the deployment.
        
        Args:
            target: Deployment target
            citizen: Citizen/component to deploy (must have env_requirements)
            target_env: Target environment ID (ENV1, ENV2, etc.)
            strategy: Deployment strategy
            dry_run: Simulate deployment
            health_check: Run health checks
        
        Returns:
            DeploymentResult with operation status
        
        Raises:
            ValueError: If EnvGuard blocks the deployment
        """
        # Step 1: ITAD EnvGuard validation (β-CONSTRAIN axiom)
        logger.info(f"ITAD: Validating {target} for {target_env}...")
        self.validate_env_compatibility(citizen, target_env)
        
        # Step 2: Proceed with deployment
        logger.info(f"ITAD: Validation passed, proceeding with deployment...")
        return self.deploy(
            target=target,
            env=target_env,
            strategy=strategy,
            dry_run=dry_run,
            health_check=health_check
        )
    
    def deploy(
        self, 
        target: str, 
        env: str = "staging",
        strategy: str = "rolling",
        dry_run: bool = False,
        health_check: bool = True
    ) -> DeploymentResult:
        """Execute deployment.
        
        Args:
            target: Deployment target (api, frontend, etc.)
            env: Environment (staging, production)
            strategy: Deployment strategy
            dry_run: Simulate deployment
            health_check: Run health checks
            
        Returns:
            DeploymentResult with operation status
        """
        try:
            start_time = time.time()
            warnings = []
            
            if dry_run:
                logger.info(f"DRY RUN: Deploying {target} to {env}")
                return DeploymentResult(
                    success=True,
                    version="v1.0.0-dry",
                    deployment_url=f"https://{env}.example.com/{target}",
                    strategy=strategy,
                    duration_seconds=0.1,
                    health_check_passed=True
                )
            
            # Validate strategy
            if strategy not in [s.value for s in DeploymentStrategy]:
                return DeploymentResult(
                    success=False,
                    error=f"Invalid strategy: {strategy}"
                )
            
            # Execute deployment (simplified)
            version = f"v1.0.{int(time.time() % 1000)}"
            deployment_url = f"https://{env}.example.com/{target}"
            
            logger.info(f"Deploying {target} to {env} using {strategy}")
            
            # Strategy-specific logic
            if strategy == DeploymentStrategy.ROLLING.value:
                warnings.append("Rolling deployment: gradual rollout over 5 minutes")
            elif strategy == DeploymentStrategy.BLUE_GREEN.value:
                warnings.append("Blue-green deployment: instant switchover after validation")
            elif strategy == DeploymentStrategy.CANARY.value:
                warnings.append("Canary deployment: 10% traffic to new version")
            
            # Health check
            health_passed = True
            if health_check:
                health_passed = self._health_check(deployment_url)
                if not health_passed:
                    warnings.append("Health check failed - deployment may be unstable")
            
            duration = time.time() - start_time
            
            # Store deployment info
            deployment_id = f"{target}-{version}"
            self.deployments[deployment_id] = {
                "target": target,
                "env": env,
                "version": version,
                "url": deployment_url,
                "strategy": strategy,
                "timestamp": time.time()
            }
            
            return DeploymentResult(
                success=True,
                version=version,
                deployment_url=deployment_url,
                strategy=strategy,
                duration_seconds=duration,
                health_check_passed=health_passed,
                warnings=warnings if warnings else None
            )
        
        except Exception as e:
            logger.error(f"Deployment failed: {e}", exc_info=True)
            return DeploymentResult(success=False, error=str(e))
    
    def rollback(
        self,
        deployment_id: str,
        to_version: str
    ) -> DeploymentResult:
        """Rollback deployment to previous version.
        
        Args:
            deployment_id: Deployment identifier
            to_version: Target version
            
        Returns:
            DeploymentResult with rollback status
        """
        try:
            if deployment_id not in self.deployments:
                return DeploymentResult(
                    success=False,
                    error=f"Deployment not found: {deployment_id}"
                )
            
            deployment = self.deployments[deployment_id]
            logger.info(f"Rolling back {deployment_id} to {to_version}")
            
            # Execute rollback
            # In production: kubectl rollout undo, docker stack rollback, etc.
            
            return DeploymentResult(
                success=True,
                version=to_version,
                deployment_url=deployment['url'],
                warnings=[f"Rolled back from {deployment['version']} to {to_version}"]
            )
        
        except Exception as e:
            logger.error(f"Rollback failed: {e}", exc_info=True)
            return DeploymentResult(success=False, error=str(e))
    
    def _health_check(self, url: str, timeout: int = 5) -> bool:
        """Perform health check on deployment."""
        try:
            # In production: HTTP request to /health endpoint
            logger.debug(f"Health check: {url}")
            return True  # Simplified
        except Exception as e:
            logger.warning(f"Health check failed: {e}")
            return False
    
    def get_deployment_status(self, deployment_id: str) -> Optional[Dict[str, Any]]:
        """Get deployment status."""
        return self.deployments.get(deployment_id)
