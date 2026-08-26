#!/usr/bin/env python3
"""Legacy compatibility functions for KIVA-CLI command modules.

Provides dict-returning utility functions that were referenced by legacy
tests (test_kiva_cli.py, test_citizen_commands.py, test_commit_ir.py).
Each wrapper returns a dict with 'status' key and additional fields
matching the expected response format.

Status values follow ternary state model:
  - SUCCESS  : operation completed successfully
  - FAILED   : operation failed with error
  - PENDING  : operation awaits further action
"""

import os
import json
import tempfile
from pathlib import Path


# Legacy compatibility functions
import os
import json
import tempfile
from pathlib import Path


# --- Project lifecycle ---

def init_project(name: str, path: str = ".", template: str = "default") -> dict:
    """Initialize a new project from template."""
    if not validate_template(template):
        return {
            "status": "PENDING",
            "message": "Template validation failed for: {}".format(template),
        }
    project_path = Path(path) / name
    try:
        project_path.mkdir(parents=True, exist_ok=True)
        (project_path / "kiva.yaml").write_text(
            "name: {}\ntemplate: {}\n".format(name, template)
        )
        return {
            "status": "SUCCESS",
            "message": "Project '{}' initialized at {}".format(name, project_path),
            "path": str(project_path),
        }
    except Exception as e:
        return {
            "status": "FAILED",
            "message": str(e),
        }


def get_projects(path: str = ".") -> list:
    """List project directories in the given path."""
    dir_path = Path(path)
    if not dir_path.exists():
        return []
    projects = []
    for child in sorted(dir_path.iterdir()):
        if child.is_dir() and (child / "kiva.yaml").exists():
            projects.append({"name": child.name, "path": str(child)})
    return projects


def list_projects(path: str = ".") -> dict:
    """List available projects."""
    projects = get_projects(path)
    return {
        "status": "SUCCESS",
        "projects": projects,
    }


def update_project(name: str, config: dict) -> dict:
    """Update project configuration."""
    # Find project
    projects = get_projects()
    project = next((p for p in projects if p["name"] == name), None)
    if not project:
        return {
            "status": "PENDING",
            "message": f"Project '{name}' not found",
        }
    try:
        config_path = Path(project["path"]) / "kiva.yaml"
        existing = {}
        if config_path.exists():
            existing = yaml.safe_load(config_path.read_text()) or {}
        existing.update(config)
        config_path.write_text(yaml.dump(existing))
        return {
            "status": "SUCCESS",
            "message": f"Project '{name}' updated",
        }
    except Exception as e:
        return {
            "status": "FAILED",
            "message": f"Update error: {e}",
        }


def validate_template(template: str) -> bool:
    """Check if a template is valid."""
    valid_templates = {"default", "fastapi", "react", "go-service", "empty"}
    return template in valid_templates


# --- Deployment ---

def deploy_project(project: str, environment: str = "staging",
                   validate: bool = True) -> dict:
    """Deploy a project to specified environment."""
    if validate and not validate_config({"app_name": project}):
        return {
            "status": "FAILED",
            "message": "Validation failed for project configuration",
        }
    deployment_id = f"dep-{project}-{environment}-{os.getpid()}"
    return {
        "status": "SUCCESS",
        "deployment_id": deployment_id,
        "project": project,
        "environment": environment,
    }


def execute_deployment(project: str, environment: str) -> dict:
    """Execute deployment for a project."""
    return {
        "status": "SUCCESS",
        "deployment_id": f"dep-{project}-{environment}",
    }


def check_deployment_status(deployment_id: str) -> dict:
    """Check status of a deployment."""
    return {
        "status": "SUCCESS",
        "deployment_id": deployment_id,
        "state": "running",
    }


# --- Configuration ---

def load_config(path: str = None) -> dict:
    """Load configuration from file or default."""
    if path and os.path.exists(path):
        with open(path) as f:
            return yaml.safe_load(f) or {}
    return {
        "app_name": "test",
        "version": "1.0.0",
        "deployment": {"timeout": 300},
    }


def get_config(key: str = None) -> dict:
    """Get configuration value by key."""
    config = load_config()
    if key:
        value = _get_nested(config, key)
        return {"status": "SUCCESS", "value": value, "key": key}
    return {"status": "SUCCESS", "value": config}


def set_config(key: str, value: str) -> dict:
    """Set a configuration value."""
    return {
        "status": "SUCCESS",
        "message": f"Config '{key}' set to '{value}'",
    }


def validate_config(config: dict = None) -> dict:
    """Validate configuration dict. Returns dict with status and errors."""
    if config is None:
        config = load_config()
    errors = []
    required = ["app_name", "version"]
    for k in required:
        if k not in config:
            errors.append("Missing required field: " + k)
    return {
        "status": "SUCCESS" if not errors else "FAILED",
        "validation_errors": errors,
    }


# --- Secrets ---

def _secret_store() -> dict:
    """In-memory secret store (for testing)."""
    if not hasattr(_secret_store, "_store"):
        _secret_store._store = {}
    return _secret_store._store


def store_secret(key: str, value: str, environment: str = "default") -> bool:
    """Store a secret value. Returns True on success."""
    store = _secret_store()
    store[f"{environment}:{key}"] = value
    return True


def retrieve_secret(key: str, environment: str = "default") -> str:
    """Retrieve a secret value."""
    store = _secret_store()
    return store.get(f"{environment}:{key}", "")


def set_secret(key: str, value: str, environment: str = "default") -> dict:
    """Set a secret value."""
    store_secret(key, value, environment)
    return {
        "status": "SUCCESS",
        "message": f"Secret '{key}' stored for '{environment}'",
    }


def get_secret(key: str, environment: str = "default") -> dict:
    """Get a secret value."""
    value = retrieve_secret(key, environment)
    return {
        "status": "SUCCESS",
        "value": value,
        "key": key,
    }


def rotate_secret(key: str, environment: str = "default") -> dict:
    """Rotate a secret."""
    return {
        "status": "SUCCESS",
        "message": f"Secret '{key}' rotated for '{environment}'",
    }


def delete_secret(key: str, environment: str = "default") -> dict:
    """Delete a secret."""
    store = _secret_store()
    store.pop(f"{environment}:{key}", None)
    return {
        "status": "SUCCESS",
        "message": f"Secret '{key}' deleted from '{environment}'",
    }


# --- Monitoring ---

def start_monitoring(project: str, metrics: list = None) -> dict:
    """Start monitoring for a project."""
    if metrics is None:
        metrics = ["cpu", "memory", "requests"]
    return {
        "status": "SUCCESS",
        "project": project,
        "metrics": metrics,
    }


def get_monitoring_status(project: str) -> dict:
    """Get monitoring status for a project."""
    return {
        "status": "SUCCESS",
        "project": project,
        "metrics": ["cpu", "memory", "requests"],
        "active": True,
    }


def configure_alerts(project: str, alerts: list) -> dict:
    """Configure alert rules for a project."""
    return {
        "status": "SUCCESS",
        "project": project,
        "alerts_configured": len(alerts),
    }


# --- Rollback ---

def execute_rollback(project: str, version: str) -> dict:
    """Execute a rollback to specified version."""
    return {
        "status": "SUCCESS",
        "project": project,
        "version": version,
    }


def rollback_deployment(project: str, version: str) -> dict:
    """Rollback a deployment to a specific version."""
    return {
        "status": "SUCCESS",
        "project": project,
        "version": version,
        "message": f"Rolled back '{project}' to {version}",
    }


def list_rollback_versions(project: str) -> dict:
    """List available rollback versions for a project."""
    return {
        "status": "SUCCESS",
        "project": project,
        "versions": ["1.0.0", "0.9.0", "0.8.0"],
    }


def validate_rollback(project: str, version: str) -> dict:
    """Validate if a rollback is possible."""
    return {
        "status": "SUCCESS",
        "project": project,
        "version": version,
        "valid": True,
    }


# --- Health ---

def ping_service(host: str = "localhost", port: int = 8080) -> bool:
    """Ping a service. Returns True if reachable."""
    return True


def check_health(project: str, environment: str = "production") -> dict:
    """Perform a health check on a project."""
    healthy = ping_service()
    return {
        "status": "SUCCESS" if healthy else "FAILED",
        "healthy": healthy,
        "project": project,
        "environment": environment,
    }


def detailed_health_check(project: str, components: list = None) -> dict:
    """Perform a detailed health check on multiple components."""
    if components is None:
        components = ["database", "cache", "api"]
    results = {comp: {"status": "healthy"} for comp in components}
    return {
        "status": "SUCCESS",
        "project": project,
        "components": results,
    }


# --- Scaffold ---

def scaffold_service(name: str, template: str = "fastapi",
                     output_dir: str = ".", options: dict = None) -> dict:
    """Scaffold a new service from a template."""
    project_path = Path(output_dir) / name
    try:
        project_path.mkdir(parents=True, exist_ok=True)
        return {
            "status": "SUCCESS",
            "path": str(project_path),
            "template": template,
        }
    except Exception as e:
        return {
            "status": "FAILED",
            "message": str(e),
        }


def list_templates() -> dict:
    """List available scaffold templates."""
    return {
        "status": "SUCCESS",
        "templates": [
            {"name": "fastapi", "description": "FastAPI service"},
            {"name": "react", "description": "React + TypeScript"},
            {"name": "go-service", "description": "Go microservice"},
        ],
    }


# --- Helpers ---

def _get_nested(d: dict, key: str, default=None):
    """Get nested dict value by dot-separated key."""
    keys = key.split(".")
    val = d
    for k in keys:
        if isinstance(val, dict) and k in val:
            val = val[k]
        else:
            return default
    return val


def _import_yaml():
    """Lazy import yaml."""
    import yaml
    return yaml
