"""Project management operations.

Handles project initialization, validation, listing, and template scaffolding.
Integrates with ECOS Gateway for cross-repo coordination.
"""

import os
import json
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime, timezone

from ..core.template_registry import TemplateRegistry
from ..core.config_validator import ConfigValidator, ValidationResult


@dataclass
class ProjectConfig:
    """Project configuration model."""
    
    name: str
    version: str
    template: str
    description: str = ""
    author: str = ""
    license: str = "MIT"
    repository: str = ""
    created_at: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProjectConfig":
        return cls(**{k: v for k, v in data.items() if k in cls.__annotations__})


class ProjectManager:
    """Manage project lifecycle operations."""
    
    def __init__(self, workspace_root: Optional[Path] = None):
        self.workspace_root = workspace_root or Path.cwd()
        self.template_registry = TemplateRegistry()
        self.config_validator = ConfigValidator()
        self.ecos_gateway_timeout = 30  # seconds
    
    def init_project(
        self,
        name: str,
        template: str,
        path: Optional[Path] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Initialize new project from template.
        
        Returns:
            Dict with status (PENDING/SUCCESS/FAILED), phi_delta, intent_hash
        """
        project_path = path or self.workspace_root / name
        
        # Validate template exists
        template_obj = self.template_registry.get(template)
        if not template_obj:
            return {
                "status": "FAILED",
                "error": f"Template not found: {template}",
                "available_templates": self.template_registry.list_templates(),
            }
        
        # Create project directory
        try:
            project_path.mkdir(parents=True, exist_ok=False)
        except FileExistsError:
            return {
                "status": "FAILED",
                "error": f"Project directory already exists: {project_path}",
            }
        
        # Create project config
        config = ProjectConfig(
            name=name,
            version="0.1.0",
            template=template,
            description=kwargs.get("description", template_obj.description),
            author=kwargs.get("author", ""),
            license=kwargs.get("license", "MIT"),
            repository=kwargs.get("repository", ""),
            created_at=datetime.now(timezone.utc).isoformat() + "Z",
        )
        
        # Write project config
        config_path = project_path / "kiva.json"
        with open(config_path, "w") as f:
            json.dump(config.to_dict(), f, indent=2)
        
        # Scaffold template files
        for file_path, content in template_obj.files.items():
            file_full_path = project_path / file_path
            file_full_path.parent.mkdir(parents=True, exist_ok=True)
            with open(file_full_path, "w") as f:
                f.write(content)
        
        # Create additional directories
        (project_path / "tests").mkdir(exist_ok=True)
        (project_path / "docs").mkdir(exist_ok=True)
        
        # Delegate to ECOS Gateway for WAL tracking
        intent_hash = self._delegate_to_ecos_gateway(
            action="project_init",
            payload={
                "project_name": name,
                "template": template,
                "path": str(project_path),
            },
        )
        
        return {
            "status": "SUCCESS",
            "project_path": str(project_path),
            "template": template,
            "files_created": len(template_obj.files) + 1,  # +1 for kiva.json
            "intent_hash": intent_hash,
            "phi_delta": 0.002,  # Small contribution
        }
    
    def list_projects(self, workspace: Optional[Path] = None) -> Dict[str, Any]:
        """List all projects in workspace.
        
        Returns:
            Dict with projects list and status
        """
        workspace = workspace or self.workspace_root
        projects = []
        
        for item in workspace.iterdir():
            if item.is_dir():
                config_path = item / "kiva.json"
                if config_path.exists():
                    try:
                        with open(config_path, "r") as f:
                            config_data = json.load(f)
                        config = ProjectConfig.from_dict(config_data)
                        projects.append({
                            "name": config.name,
                            "template": config.template,
                            "version": config.version,
                            "path": str(item),
                            "created_at": config.created_at,
                        })
                    except (json.JSONDecodeError, KeyError):
                        # Skip invalid configs
                        continue
        
        return {
            "status": "SUCCESS",
            "workspace": str(workspace),
            "projects": projects,
            "total_count": len(projects),
        }
    
    def validate_project(self, path: Path) -> Dict[str, Any]:
        """Validate project configuration (Base-3).
        
        Returns:
            Dict with validation result (UNKNOWN/VALID/INVALID)
        """
        config_path = path / "kiva.json"
        
        if not config_path.exists():
            return {
                "status": "INVALID",
                "error": f"Project config not found: {config_path}",
            }
        
        result = self.config_validator.validate_file(config_path, schema_type="project")
        
        return {
            "status": result.status,
            "errors": result.errors,
            "warnings": result.warnings,
            "confidence": result.confidence,
            "path": str(config_path),
        }
    
    def list_templates(self) -> Dict[str, Any]:
        """List available project templates.
        
        Returns:
            Dict with templates list
        """
        templates = self.template_registry.get_all()
        
        return {
            "status": "SUCCESS",
            "templates": [
                {
                    "name": t.name,
                    "language": t.language,
                    "framework": t.framework,
                    "description": t.description,
                    "docker_support": t.docker_support,
                    "ci_cd_support": t.ci_cd_support,
                }
                for t in templates.values()
            ],
            "total_count": len(templates),
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
                # ECOS CLI not available, skip delegation
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
                # Gateway delegation failed, log but continue
                return None
        
        except (subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError):
            # ECOS CLI not available or timeout, continue without gateway
            return None
