#!/usr/bin/env python3
"""
Project Manager - KIVA-CLI Project Lifecycle Orchestrator

Manages project scaffolding, deployment, configuration with:
- Base-3 ternary semantic validation (UNKNOWN/VALID/INVALID)
- Base-4 lifecycle states (GENESIS/ACTIVE/DEPRECATED/ARCHIVED)
- IntentHash L0-L1 verification
- φ-CPS drift tracking per operation
- Global WAL integration
"""

import os
import sys
import json
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum
import subprocess
import hashlib

try:
    from .global_wal_manager import GlobalWALManager, WALEvent
    from .intent_hash_validator import IntentHashValidator, ValidationResult
    from .phi_cps_calculator import PhiCPSCalculator
except ImportError:
    # Fallback for standalone execution
    sys.path.insert(0, str(Path(__file__).parent))
    from global_wal_manager import GlobalWALManager, WALEvent
    from intent_hash_validator import IntentHashValidator, ValidationResult
    from phi_cps_calculator import PhiCPSCalculator


# ========================================
# BASE-3 TERNARY VALIDATION STATES
# ========================================

class ValidationState(Enum):
    """Base-3 ternary semantic validation."""
    UNKNOWN = 0   # Pending validation
    VALID = 1     # Validated successfully
    INVALID = -1  # Failed validation


# ========================================
# BASE-4 LIFECYCLE STATES
# ========================================

class LifecycleState(Enum):
    """Base-4 project lifecycle management."""
    GENESIS = 0       # Project created
    ACTIVE = 1        # In active development
    DEPRECATED = 2    # Marked for retirement
    ARCHIVED = 3      # Archived/read-only


# ========================================
# PROJECT FRAMEWORK TYPES
# ========================================

class FrameworkType(Enum):
    """Supported project framework templates."""
    FASTAPI = "fastapi"
    REACT = "react"
    GO_SERVICE = "go_service"
    PYTHON_LIB = "python_lib"
    DOCKER_COMPOSE = "docker_compose"
    LXC_CONTAINER = "lxc_container"


# ========================================
# DATA STRUCTURES
# ========================================

@dataclass
class ProjectConfig:
    """Project configuration metadata."""
    name: str
    framework: str
    repo_path: Path
    lifecycle_state: str = "GENESIS"
    validation_state: str = "UNKNOWN"
    intent_hash: Optional[str] = None
    phi_cps_delta: float = 0.0
    created_at: str = ""
    updated_at: str = ""
    dependencies: List[str] = None
    deployment_targets: List[str] = None
    
    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []
        if self.deployment_targets is None:
            self.deployment_targets = []
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        self.updated_at = datetime.now().isoformat()


@dataclass
class DeploymentResult:
    """Deployment operation result."""
    success: bool
    target: str
    validation_state: ValidationState
    phi_cps_delta: float
    intent_hash: str
    message: str
    artifacts: List[str] = None
    
    def __post_init__(self):
        if self.artifacts is None:
            self.artifacts = []


# ========================================
# PROJECT MANAGER CORE
# ========================================

class ProjectManager:
    """Project lifecycle orchestrator with base-3/4 validation."""
    
    def __init__(self, workspace_root: Optional[Path] = None):
        self.workspace_root = workspace_root or Path.cwd()
        self.projects_dir = self.workspace_root / "projects"
        self.projects_dir.mkdir(exist_ok=True)
        
        # Configuration storage
        self.config_dir = self.workspace_root / ".kiva" / "projects"
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        # Integration components
        self.wal_manager = GlobalWALManager()
        self.intent_validator = IntentHashValidator()
        self.phi_calculator = PhiCPSCalculator()
        
        # Framework templates registry
        self.templates_dir = Path(__file__).parent.parent.parent / "templates"
        
    def _generate_intent_hash(self, operation: str, project_name: str, framework: str) -> str:
        """Generate L0-L1 IntentHash for project operation."""
        payload = f"{operation}:{project_name}:{framework}:{datetime.now().isoformat()}"
        return "0x" + hashlib.sha256(payload.encode()).hexdigest()[:20].upper()
    
    def _calculate_phi_delta(self, operation: str, complexity: float = 1.0) -> float:
        """Calculate expected φ-CPS delta for operation."""
        # Base semantic weights
        operation_weights = {
            "scaffold": 0.015,
            "deploy": 0.012,
            "configure": 0.008,
            "transition": 0.005
        }
        
        base_weight = operation_weights.get(operation, 0.010)
        return base_weight * complexity
    
    def _save_project_config(self, config: ProjectConfig) -> None:
        """Save project configuration to registry."""
        config_file = self.config_dir / f"{config.name}.json"
        config_dict = asdict(config)
        config_dict['repo_path'] = str(config.repo_path)
        
        with open(config_file, 'w') as f:
            json.dump(config_dict, f, indent=2)
    
    def _load_project_config(self, project_name: str) -> Optional[ProjectConfig]:
        """Load project configuration from registry."""
        config_file = self.config_dir / f"{project_name}.json"
        
        if not config_file.exists():
            return None
        
        with open(config_file) as f:
            config_dict = json.load(f)
        
        config_dict['repo_path'] = Path(config_dict['repo_path'])
        return ProjectConfig(**config_dict)
    
    def _validate_project_structure(self, project_path: Path, framework: str) -> ValidationState:
        """Base-3 ternary validation of project structure."""
        required_files = {
            "fastapi": ["main.py", "requirements.txt"],
            "react": ["package.json", "src/App.js"],
            "go_service": ["main.go", "go.mod"],
            "python_lib": ["setup.py", "pyproject.toml"],
            "docker_compose": ["docker-compose.yml"],
            "lxc_container": ["lxc.conf"]
        }
        
        if framework not in required_files:
            return ValidationState.UNKNOWN
        
        for required_file in required_files[framework]:
            if not (project_path / required_file).exists():
                return ValidationState.INVALID
        
        return ValidationState.VALID
    
    def scaffold_project(
        self,
        name: str,
        framework: FrameworkType,
        additional_deps: Optional[List[str]] = None
    ) -> Tuple[bool, ProjectConfig, str]:
        """Scaffold new project from framework template."""
        project_path = self.projects_dir / name
        
        # Check existing
        if project_path.exists():
            return False, None, f"Project '{name}' already exists"
        
        # Generate IntentHash
        intent_hash = self._generate_intent_hash("scaffold", name, framework.value)
        
        # Calculate φ-CPS delta
        phi_delta = self._calculate_phi_delta("scaffold", complexity=1.2)
        
        try:
            # Create project directory
            project_path.mkdir(parents=True)
            
            # Apply framework template
            template_dir = self.templates_dir / framework.value
            
            if template_dir.exists():
                # Copy template files
                shutil.copytree(template_dir, project_path, dirs_exist_ok=True)
            else:
                # Fallback: create basic structure
                self._create_basic_structure(project_path, framework)
            
            # Create project config
            config = ProjectConfig(
                name=name,
                framework=framework.value,
                repo_path=project_path,
                lifecycle_state=LifecycleState.GENESIS.name,
                validation_state=ValidationState.UNKNOWN.name,
                intent_hash=intent_hash,
                phi_cps_delta=phi_delta,
                dependencies=additional_deps or []
            )
            
            # Validate structure
            validation = self._validate_project_structure(project_path, framework.value)
            config.validation_state = validation.name
            
            # Save configuration
            self._save_project_config(config)
            
            # WAL event
            self.wal_manager.append_event(WALEvent(
                event_type="project_scaffold",
                repo="KIVA-CLI",
                data={
                    "project_name": name,
                    "framework": framework.value,
                    "intent_hash": intent_hash,
                    "validation_state": validation.name,
                    "phi_delta": phi_delta
                }
            ))
            
            return True, config, f"Project '{name}' scaffolded successfully"
            
        except Exception as e:
            return False, None, f"Scaffold failed: {str(e)}"
    
    def _create_basic_structure(self, project_path: Path, framework: FrameworkType) -> None:
        """Create basic project structure when template unavailable."""
        if framework == FrameworkType.FASTAPI:
            (project_path / "main.py").write_text(
                'from fastapi import FastAPI\n\napp = FastAPI()\n\n@app.get("/")\ndef root():\n    return {"status": "ok"}\n'
            )
            (project_path / "requirements.txt").write_text("fastapi>=0.100.0\nuvicorn>=0.23.0\n")
        
        elif framework == FrameworkType.REACT:
            (project_path / "package.json").write_text(
                json.dumps({
                    "name": project_path.name,
                    "version": "0.1.0",
                    "dependencies": {"react": "^18.2.0"}
                }, indent=2)
            )
            src_dir = project_path / "src"
            src_dir.mkdir()
            (src_dir / "App.js").write_text('function App() { return <div>Hello</div>; }\nexport default App;\n')
        
        elif framework == FrameworkType.GO_SERVICE:
            (project_path / "main.go").write_text(
                'package main\n\nimport "fmt"\n\nfunc main() {\n    fmt.Println("Service running")\n}\n'
            )
            (project_path / "go.mod").write_text(f"module {project_path.name}\n\ngo 1.21\n")
        
        elif framework == FrameworkType.PYTHON_LIB:
            (project_path / "setup.py").write_text(
                f'from setuptools import setup\n\nsetup(name="{project_path.name}", version="0.1.0")\n'
            )
            (project_path / "pyproject.toml").write_text(
                f'[project]\nname = "{project_path.name}"\nversion = "0.1.0"\n'
            )
        
        # Create README
        (project_path / "README.md").write_text(
            f"# {project_path.name}\n\nFramework: {framework.value}\nGenerated by KIVA-CLI ProjectManager\n"
        )
    
    def deploy_project(
        self,
        project_name: str,
        target: str = "docker",
        dry_run: bool = False
    ) -> DeploymentResult:
        """Deploy project to target environment."""
        # Load project config
        config = self._load_project_config(project_name)
        
        if not config:
            return DeploymentResult(
                success=False,
                target=target,
                validation_state=ValidationState.INVALID,
                phi_cps_delta=0.0,
                intent_hash="",
                message=f"Project '{project_name}' not found"
            )
        
        # Generate deployment IntentHash
        intent_hash = self._generate_intent_hash("deploy", project_name, target)
        
        # Validate current state
        validation = self._validate_project_structure(config.repo_path, config.framework)
        
        if validation != ValidationState.VALID:
            return DeploymentResult(
                success=False,
                target=target,
                validation_state=validation,
                phi_cps_delta=0.0,
                intent_hash=intent_hash,
                message=f"Project validation failed: {validation.name}"
            )
        
        # Calculate φ-CPS delta
        phi_delta = self._calculate_phi_delta("deploy", complexity=1.0)
        
        if dry_run:
            return DeploymentResult(
                success=True,
                target=target,
                validation_state=ValidationState.VALID,
                phi_cps_delta=phi_delta,
                intent_hash=intent_hash,
                message=f"[DRY-RUN] Deployment to {target} validated"
            )
        
        # Execute deployment
        try:
            if target == "docker":
                self._deploy_docker(config)
            elif target == "kubernetes":
                self._deploy_kubernetes(config)
            elif target == "lxc":
                self._deploy_lxc(config)
            else:
                return DeploymentResult(
                    success=False,
                    target=target,
                    validation_state=ValidationState.INVALID,
                    phi_cps_delta=0.0,
                    intent_hash=intent_hash,
                    message=f"Unknown target: {target}"
                )
            
            # Update config
            if target not in config.deployment_targets:
                config.deployment_targets.append(target)
            config.lifecycle_state = LifecycleState.ACTIVE.name
            config.phi_cps_delta += phi_delta
            self._save_project_config(config)
            
            # WAL event
            self.wal_manager.append_event(WALEvent(
                event_type="project_deploy",
                repo="KIVA-CLI",
                data={
                    "project_name": project_name,
                    "target": target,
                    "intent_hash": intent_hash,
                    "phi_delta": phi_delta
                }
            ))
            
            return DeploymentResult(
                success=True,
                target=target,
                validation_state=ValidationState.VALID,
                phi_cps_delta=phi_delta,
                intent_hash=intent_hash,
                message=f"Deployed to {target} successfully",
                artifacts=[f"{target}-deployment.yml"]
            )
            
        except Exception as e:
            return DeploymentResult(
                success=False,
                target=target,
                validation_state=ValidationState.INVALID,
                phi_cps_delta=0.0,
                intent_hash=intent_hash,
                message=f"Deployment failed: {str(e)}"
            )
    
    def _deploy_docker(self, config: ProjectConfig) -> None:
        """Deploy project as Docker container."""
        dockerfile = config.repo_path / "Dockerfile"
        
        if not dockerfile.exists():
            # Generate Dockerfile
            if config.framework == "fastapi":
                dockerfile.write_text(
                    "FROM python:3.11-slim\nWORKDIR /app\nCOPY requirements.txt .\n"
                    "RUN pip install -r requirements.txt\nCOPY . .\nCMD [\"uvicorn\", \"main:app\", \"--host\", \"0.0.0.0\"]\n"
                )
        
        # Build image
        subprocess.run(
            ["docker", "build", "-t", f"{config.name}:latest", str(config.repo_path)],
            check=True
        )
    
    def _deploy_kubernetes(self, config: ProjectConfig) -> None:
        """Deploy project to Kubernetes cluster."""
        k8s_manifest = config.repo_path / "k8s-deployment.yml"
        
        if not k8s_manifest.exists():
            # Generate basic K8s manifest
            manifest = {
                "apiVersion": "apps/v1",
                "kind": "Deployment",
                "metadata": {"name": config.name},
                "spec": {
                    "replicas": 1,
                    "selector": {"matchLabels": {"app": config.name}},
                    "template": {
                        "metadata": {"labels": {"app": config.name}},
                        "spec": {"containers": [{"name": config.name, "image": f"{config.name}:latest"}]}
                    }
                }
            }
            k8s_manifest.write_text(json.dumps(manifest, indent=2))
        
        subprocess.run(["kubectl", "apply", "-f", str(k8s_manifest)], check=True)
    
    def _deploy_lxc(self, config: ProjectConfig) -> None:
        """Deploy project as LXC container."""
        lxc_config = config.repo_path / "lxc.conf"
        
        if not lxc_config.exists():
            lxc_config.write_text(
                f"lxc.rootfs.path = dir:/var/lib/lxc/{config.name}/rootfs\n"
                f"lxc.uts.name = {config.name}\n"
            )
        
        subprocess.run(["lxc-create", "-n", config.name, "-f", str(lxc_config)], check=True)
        subprocess.run(["lxc-start", "-n", config.name], check=True)
    
    def transition_lifecycle(
        self,
        project_name: str,
        new_state: LifecycleState
    ) -> Tuple[bool, str]:
        """Transition project lifecycle state (base-4)."""
        config = self._load_project_config(project_name)
        
        if not config:
            return False, f"Project '{project_name}' not found"
        
        old_state = LifecycleState[config.lifecycle_state]
        
        # Validate transition
        valid_transitions = {
            LifecycleState.GENESIS: [LifecycleState.ACTIVE, LifecycleState.ARCHIVED],
            LifecycleState.ACTIVE: [LifecycleState.DEPRECATED, LifecycleState.ARCHIVED],
            LifecycleState.DEPRECATED: [LifecycleState.ARCHIVED, LifecycleState.ACTIVE],
            LifecycleState.ARCHIVED: []  # Terminal state
        }
        
        if new_state not in valid_transitions.get(old_state, []):
            return False, f"Invalid transition: {old_state.name} → {new_state.name}"
        
        # Update config
        config.lifecycle_state = new_state.name
        phi_delta = self._calculate_phi_delta("transition")
        config.phi_cps_delta += phi_delta
        self._save_project_config(config)
        
        # WAL event
        self.wal_manager.append_event(WALEvent(
            event_type="project_lifecycle_transition",
            repo="KIVA-CLI",
            data={
                "project_name": project_name,
                "old_state": old_state.name,
                "new_state": new_state.name,
                "phi_delta": phi_delta
            }
        ))
        
        return True, f"Transitioned {project_name}: {old_state.name} → {new_state.name}"
    
    def list_projects(self) -> List[ProjectConfig]:
        """List all registered projects."""
        projects = []
        
        for config_file in self.config_dir.glob("*.json"):
            project_name = config_file.stem
            config = self._load_project_config(project_name)
            if config:
                projects.append(config)
        
        return projects
    
    def get_project_status(self, project_name: str) -> Optional[Dict[str, Any]]:
        """Get comprehensive project status."""
        config = self._load_project_config(project_name)
        
        if not config:
            return None
        
        # Current validation
        validation = self._validate_project_structure(config.repo_path, config.framework)
        
        return {
            "name": config.name,
            "framework": config.framework,
            "lifecycle_state": config.lifecycle_state,
            "validation_state": validation.name,
            "intent_hash": config.intent_hash,
            "phi_cps_delta": config.phi_cps_delta,
            "deployment_targets": config.deployment_targets,
            "created_at": config.created_at,
            "updated_at": config.updated_at
        }


if __name__ == "__main__":
    # Quick test
    pm = ProjectManager()
    success, config, msg = pm.scaffold_project(
        "test-api",
        FrameworkType.FASTAPI,
        additional_deps=["pytest", "httpx"]
    )
    print(f"Scaffold: {msg}")
    if success:
        result = pm.deploy_project("test-api", target="docker", dry_run=True)
        print(f"Deploy: {result.message}")
