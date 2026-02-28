"""Configuration validation using JSON schemas.

Validates project configs, deployment manifests, and environment settings.
Supports Base-3 validation: UNKNOWN/VALID/INVALID.
"""

import json
from pathlib import Path
from typing import Dict, Any, Tuple, List, Optional
from dataclasses import dataclass


@dataclass
class ValidationResult:
    """Base-3 validation result."""
    
    status: str  # UNKNOWN, VALID, INVALID
    errors: List[str]
    warnings: List[str]
    confidence: float  # [0.0, 0.5, 1.0]
    
    @property
    def is_valid(self) -> bool:
        return self.status == "VALID"
    
    @property
    def is_invalid(self) -> bool:
        return self.status == "INVALID"
    
    @property
    def is_unknown(self) -> bool:
        return self.status == "UNKNOWN"


class ConfigValidator:
    """Validate configuration files against schemas."""
    
    REQUIRED_PROJECT_FIELDS = ["name", "version", "template"]
    REQUIRED_DEPLOY_FIELDS = ["environment", "target", "strategy"]
    
    def __init__(self):
        self.schemas: Dict[str, Dict[str, Any]] = {
            "project": self._project_schema(),
            "deployment": self._deployment_schema(),
        }
    
    def _project_schema(self) -> Dict[str, Any]:
        """Project configuration JSON schema."""
        return {
            "type": "object",
            "required": ["name", "version", "template"],
            "properties": {
                "name": {"type": "string", "pattern": "^[a-z0-9-]+$"},
                "version": {"type": "string", "pattern": "^\\d+\\.\\d+\\.\\d+"},
                "template": {"type": "string"},
                "description": {"type": "string"},
                "author": {"type": "string"},
                "license": {"type": "string"},
                "repository": {"type": "string"},
            },
        }
    
    def _deployment_schema(self) -> Dict[str, Any]:
        """Deployment manifest JSON schema."""
        return {
            "type": "object",
            "required": ["environment", "target", "strategy"],
            "properties": {
                "environment": {"enum": ["development", "staging", "production"]},
                "target": {"type": "string"},
                "strategy": {"enum": ["rolling", "blue-green", "canary"]},
                "replicas": {"type": "integer", "minimum": 1, "maximum": 100},
                "health_check": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string"},
                        "interval": {"type": "integer"},
                        "timeout": {"type": "integer"},
                    },
                },
            },
        }
    
    def validate_project(self, config: Dict[str, Any]) -> ValidationResult:
        """Validate project configuration (Base-3)."""
        errors = []
        warnings = []
        
        # Check required fields
        for field in self.REQUIRED_PROJECT_FIELDS:
            if field not in config:
                errors.append(f"Missing required field: {field}")
        
        # Validate name format
        if "name" in config:
            name = config["name"]
            if not isinstance(name, str) or not name.replace("-", "").replace("_", "").isalnum():
                errors.append(f"Invalid project name: {name}")
        
        # Validate version format (semver)
        if "version" in config:
            version = config["version"]
            parts = version.split(".")
            if len(parts) != 3 or not all(p.isdigit() for p in parts):
                errors.append(f"Invalid version format: {version} (expected semver)")
        
        # Warnings for optional fields
        if "description" not in config:
            warnings.append("Missing optional field: description")
        if "license" not in config:
            warnings.append("Missing optional field: license")
        
        # Determine status (Base-3)
        if errors:
            status = "INVALID"
            confidence = 1.0
        elif warnings:
            status = "VALID"
            confidence = 0.5
        else:
            status = "VALID"
            confidence = 1.0
        
        return ValidationResult(
            status=status,
            errors=errors,
            warnings=warnings,
            confidence=confidence,
        )
    
    def validate_deployment(self, config: Dict[str, Any]) -> ValidationResult:
        """Validate deployment manifest (Base-3)."""
        errors = []
        warnings = []
        
        # Check required fields
        for field in self.REQUIRED_DEPLOY_FIELDS:
            if field not in config:
                errors.append(f"Missing required field: {field}")
        
        # Validate environment
        if "environment" in config:
            env = config["environment"]
            if env not in ["development", "staging", "production"]:
                errors.append(f"Invalid environment: {env}")
        
        # Validate strategy
        if "strategy" in config:
            strategy = config["strategy"]
            if strategy not in ["rolling", "blue-green", "canary"]:
                errors.append(f"Invalid deployment strategy: {strategy}")
        
        # Validate replicas
        if "replicas" in config:
            replicas = config["replicas"]
            if not isinstance(replicas, int) or replicas < 1 or replicas > 100:
                errors.append(f"Invalid replicas count: {replicas} (must be 1-100)")
        
        # Warnings
        if "health_check" not in config:
            warnings.append("Missing health check configuration")
        
        # Determine status
        if errors:
            status = "INVALID"
            confidence = 1.0
        elif warnings:
            status = "VALID"
            confidence = 0.5
        else:
            status = "VALID"
            confidence = 1.0
        
        return ValidationResult(
            status=status,
            errors=errors,
            warnings=warnings,
            confidence=confidence,
        )
    
    def validate_file(self, path: Path, schema_type: str = "project") -> ValidationResult:
        """Validate configuration file."""
        try:
            with open(path, "r") as f:
                config = json.load(f)
            
            if schema_type == "project":
                return self.validate_project(config)
            elif schema_type == "deployment":
                return self.validate_deployment(config)
            else:
                return ValidationResult(
                    status="UNKNOWN",
                    errors=[f"Unknown schema type: {schema_type}"],
                    warnings=[],
                    confidence=0.0,
                )
        except json.JSONDecodeError as e:
            return ValidationResult(
                status="INVALID",
                errors=[f"JSON parse error: {str(e)}"],
                warnings=[],
                confidence=1.0,
            )
        except FileNotFoundError:
            return ValidationResult(
                status="UNKNOWN",
                errors=[f"File not found: {path}"],
                warnings=[],
                confidence=0.0,
            )
