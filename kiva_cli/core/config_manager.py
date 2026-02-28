""" KIVA CLI - Config Manager
Manages configuration validation and schema enforcement.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Dict, Any, List
import yaml
import json
import logging

logger = logging.getLogger(__name__)


@dataclass
class ConfigResult:
    """Result object for config operations."""
    success: bool
    config_data: Optional[Dict[str, Any]] = None
    errors: Optional[List[str]] = None
    warnings: Optional[List[str]] = None


class ConfigManager:
    """Manages configuration validation."""
    
    # Basic schema for KIVA config
    KIVA_SCHEMA = {
        "type": "object",
        "required": ["name", "version"],
        "properties": {
            "name": {"type": "string"},
            "version": {"type": "string"},
            "environment": {"type": "string", "enum": ["development", "staging", "production"]},
            "deployment": {
                "type": "object",
                "properties": {
                    "strategy": {"type": "string"},
                    "replicas": {"type": "integer", "minimum": 1}
                }
            }
        }
    }
    
    def validate_config(
        self,
        file: str,
        strict: bool = True,
        schema: Optional[str] = None
    ) -> ConfigResult:
        """Validate configuration file.
        
        Args:
            file: Path to config file (YAML/JSON)
            strict: Enforce strict validation
            schema: Optional custom schema file
            
        Returns:
            ConfigResult with validation status
        """
        try:
            file_path = Path(file)
            if not file_path.exists():
                return ConfigResult(
                    success=False,
                    errors=[f"File not found: {file}"]
                )
            
            # Load config
            content = file_path.read_text(encoding='utf-8')
            
            if file.endswith('.yaml') or file.endswith('.yml'):
                config_data = yaml.safe_load(content)
            elif file.endswith('.json'):
                config_data = json.loads(content)
            else:
                return ConfigResult(
                    success=False,
                    errors=["Unsupported file format (use .yaml or .json)"]
                )
            
            errors = []
            warnings = []
            
            # Basic validation
            if not isinstance(config_data, dict):
                errors.append("Config must be a dictionary")
                return ConfigResult(success=False, errors=errors)
            
            # Validate required fields
            required_fields = ["name", "version"]
            for field in required_fields:
                if field not in config_data:
                    if strict:
                        errors.append(f"Missing required field: {field}")
                    else:
                        warnings.append(f"Missing recommended field: {field}")
            
            # Environment validation
            if "environment" in config_data:
                valid_envs = ["development", "staging", "production"]
                if config_data["environment"] not in valid_envs:
                    warnings.append(f"Unknown environment: {config_data['environment']}")
            
            # Deployment config
            if "deployment" in config_data:
                if "replicas" in config_data["deployment"]:
                    if config_data["deployment"]["replicas"] < 1:
                        errors.append("Deployment replicas must be >= 1")
            
            if errors:
                return ConfigResult(
                    success=False,
                    config_data=config_data,
                    errors=errors,
                    warnings=warnings if warnings else None
                )
            
            return ConfigResult(
                success=True,
                config_data=config_data,
                warnings=warnings if warnings else None
            )
        
        except yaml.YAMLError as e:
            return ConfigResult(
                success=False,
                errors=[f"YAML parsing error: {e}"]
            )
        except json.JSONDecodeError as e:
            return ConfigResult(
                success=False,
                errors=[f"JSON parsing error: {e}"]
            )
        except Exception as e:
            logger.error(f"Config validation failed: {e}", exc_info=True)
            return ConfigResult(
                success=False,
                errors=[str(e)]
            )
    
    def generate_config(
        self,
        name: str,
        version: str = "0.1.0",
        output_file: str = "kiva.yaml"
    ) -> ConfigResult:
        """Generate default config file.
        
        Args:
            name: Project name
            version: Project version
            output_file: Output filename
            
        Returns:
            ConfigResult with generation status
        """
        try:
            config = {
                "name": name,
                "version": version,
                "environment": "development",
                "deployment": {
                    "strategy": "rolling",
                    "replicas": 1,
                    "health_check": {
                        "enabled": True,
                        "path": "/health",
                        "timeout_seconds": 5
                    }
                },
                "monitoring": {
                    "enabled": True,
                    "metrics_port": 9090
                }
            }
            
            output_path = Path(output_file)
            
            if output_file.endswith('.yaml') or output_file.endswith('.yml'):
                content = yaml.dump(config, default_flow_style=False, sort_keys=False)
            else:
                content = json.dumps(config, indent=2)
            
            output_path.write_text(content, encoding='utf-8')
            logger.info(f"Generated config: {output_file}")
            
            return ConfigResult(
                success=True,
                config_data=config
            )
        
        except Exception as e:
            logger.error(f"Config generation failed: {e}", exc_info=True)
            return ConfigResult(
                success=False,
                errors=[str(e)]
            )
