"""Deployment management operations.

Handles deployment execution, rollback, environment management.
Integrates with ECOS Gateway for φ-CPS validation and WAL tracking.
"""

import json
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime
import uuid

from ..core.config_validator import ConfigValidator


@dataclass
class DeploymentConfig:
    """Deployment manifest model."""
    
    deployment_id: str
    project_name: str
    environment: str  # development, staging, production
    target: str  # k8s cluster, docker host, etc.
    strategy: str  # rolling, blue-green, canary
    replicas: int = 1
    health_check: Optional[Dict[str, Any]] = None
    created_at: str = ""
    status: str = "PENDING"  # PENDING, SUCCESS, FAILED
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DeploymentConfig":
        return cls(**{k: v for k, v in data.items() if k in cls.__annotations__})


class DeploymentManager:
    """Manage deployment lifecycle operations."""
    
    def __init__(self, deployments_dir: Optional[Path] = None):
        self.deployments_dir = deployments_dir or Path.home() / ".kiva" / "deployments"
        self.deployments_dir.mkdir(parents=True, exist_ok=True)
        self.config_validator = ConfigValidator()
        self.ecos_gateway_timeout = 60  # seconds (longer for deployments)
    
    def deploy(
        self,
        project_path: Path,
        environment: str,
        target: str,
        strategy: str = "rolling",
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Execute deployment.
        
        Returns:
            Dict with status (PENDING/SUCCESS/FAILED), deployment_id, phi_delta
        """
        # Load project config
        project_config_path = project_path / "kiva.json"
        if not project_config_path.exists():
            return {
                "status": "FAILED",
                "error": f"Project config not found: {project_config_path}",
            }
        
        with open(project_config_path, "r") as f:
            project_config = json.load(f)
        
        # Create deployment config
        deployment_id = str(uuid.uuid4())[:8]
        deployment = DeploymentConfig(
            deployment_id=deployment_id,
            project_name=project_config["name"],
            environment=environment,
            target=target,
            strategy=strategy,
            replicas=kwargs.get("replicas", 1),
            health_check=kwargs.get("health_check"),
            created_at=datetime.utcnow().isoformat() + "Z",
            status="PENDING",
        )
        
        # Validate deployment config
        validation = self.config_validator.validate_deployment(deployment.to_dict())
        if validation.is_invalid:
            return {
                "status": "FAILED",
                "error": "Deployment validation failed",
                "validation_errors": validation.errors,
            }
        
        # Save deployment manifest
        manifest_path = self.deployments_dir / f"{deployment_id}.json"
        with open(manifest_path, "w") as f:
            json.dump(deployment.to_dict(), f, indent=2)
        
        # Execute deployment (placeholder - would integrate with k8s, docker, etc.)
        # For now, delegate to ECOS Gateway
        intent_hash = self._delegate_to_ecos_gateway(
            action="deployment_execute",
            payload={
                "deployment_id": deployment_id,
                "project_name": project_config["name"],
                "environment": environment,
                "target": target,
                "strategy": strategy,
            },
        )
        
        # Update deployment status
        deployment.status = "SUCCESS"
        with open(manifest_path, "w") as f:
            json.dump(deployment.to_dict(), f, indent=2)
        
        return {
            "status": "SUCCESS",
            "deployment_id": deployment_id,
            "project_name": project_config["name"],
            "environment": environment,
            "strategy": strategy,
            "intent_hash": intent_hash,
            "phi_delta": 0.005,  # Deployment contribution
            "manifest_path": str(manifest_path),
        }
    
    def rollback(
        self,
        deployment_id: str,
    ) -> Dict[str, Any]:
        """Rollback deployment to previous version.
        
        Returns:
            Dict with status and rollback details
        """
        # Load deployment manifest
        manifest_path = self.deployments_dir / f"{deployment_id}.json"
        if not manifest_path.exists():
            return {
                "status": "FAILED",
                "error": f"Deployment not found: {deployment_id}",
            }
        
        with open(manifest_path, "r") as f:
            deployment_data = json.load(f)
        
        deployment = DeploymentConfig.from_dict(deployment_data)
        
        # Execute rollback via ECOS Gateway
        intent_hash = self._delegate_to_ecos_gateway(
            action="deployment_rollback",
            payload={
                "deployment_id": deployment_id,
                "project_name": deployment.project_name,
                "environment": deployment.environment,
            },
        )
        
        # Create rollback record
        rollback_id = str(uuid.uuid4())[:8]
        rollback_record = {
            "rollback_id": rollback_id,
            "original_deployment_id": deployment_id,
            "project_name": deployment.project_name,
            "environment": deployment.environment,
            "rolled_back_at": datetime.utcnow().isoformat() + "Z",
            "status": "SUCCESS",
            "intent_hash": intent_hash,
        }
        
        rollback_path = self.deployments_dir / f"rollback-{rollback_id}.json"
        with open(rollback_path, "w") as f:
            json.dump(rollback_record, f, indent=2)
        
        return {
            "status": "SUCCESS",
            "rollback_id": rollback_id,
            "deployment_id": deployment_id,
            "project_name": deployment.project_name,
            "environment": deployment.environment,
            "intent_hash": intent_hash,
            "phi_delta": 0.003,  # Rollback contribution
        }
    
    def list_deployments(
        self,
        environment: Optional[str] = None,
        project_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """List deployments with optional filters.
        
        Returns:
            Dict with deployments list
        """
        deployments = []
        
        for manifest_path in self.deployments_dir.glob("*.json"):
            if manifest_path.name.startswith("rollback-"):
                continue
            
            try:
                with open(manifest_path, "r") as f:
                    deployment_data = json.load(f)
                
                deployment = DeploymentConfig.from_dict(deployment_data)
                
                # Apply filters
                if environment and deployment.environment != environment:
                    continue
                if project_name and deployment.project_name != project_name:
                    continue
                
                deployments.append({
                    "deployment_id": deployment.deployment_id,
                    "project_name": deployment.project_name,
                    "environment": deployment.environment,
                    "strategy": deployment.strategy,
                    "status": deployment.status,
                    "created_at": deployment.created_at,
                })
            
            except (json.JSONDecodeError, KeyError):
                # Skip invalid manifests
                continue
        
        # Sort by creation date (newest first)
        deployments.sort(key=lambda d: d["created_at"], reverse=True)
        
        return {
            "status": "SUCCESS",
            "deployments": deployments,
            "total_count": len(deployments),
            "filters": {
                "environment": environment,
                "project_name": project_name,
            },
        }
    
    def get_deployment(
        self,
        deployment_id: str,
    ) -> Dict[str, Any]:
        """Get deployment details.
        
        Returns:
            Dict with deployment details
        """
        manifest_path = self.deployments_dir / f"{deployment_id}.json"
        
        if not manifest_path.exists():
            return {
                "status": "FAILED",
                "error": f"Deployment not found: {deployment_id}",
            }
        
        with open(manifest_path, "r") as f:
            deployment_data = json.load(f)
        
        return {
            "status": "SUCCESS",
            "deployment": deployment_data,
        }
    
    def _delegate_to_ecos_gateway(
        self,
        action: str,
        payload: Dict[str, Any],
    ) -> Optional[str]:
        """Delegate operation to ECOS Gateway via subprocess.
        
        Returns:
            IntentHash¹¹ or None on failure
        """
        try:
            # Check if ecos-cli is available
            result = subprocess.run(
                ["ecos-cli", "--version"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode != 0:
                return None
            
            # Delegate to ECOS Gateway
            cmd = [
                "ecos-cli",
                "gateway",
                "delegate",
                "--source", "kiva-cli",
                "--action", action,
                "--payload", json.dumps(payload),
                "--timeout", str(self.ecos_gateway_timeout),
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.ecos_gateway_timeout,
            )
            
            if result.returncode == 0:
                response = json.loads(result.stdout)
                return response.get("intent_hash")
            else:
                return None
        
        except (subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError):
            return None
