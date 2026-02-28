""" KIVA CLI - Project Manager
Manages project lifecycle operations: init, scaffold, list, clean.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Any, Optional
import subprocess
import logging

logger = logging.getLogger(__name__)


@dataclass
class ProjectResult:
    """Result object for project operations."""
    success: bool
    project_path: Optional[Path] = None
    files_created: Optional[List[Path]] = None
    error: Optional[str] = None
    warnings: Optional[List[str]] = None


class ProjectManager:
    """Manages project lifecycle operations."""
    
    TEMPLATES = {
        'fastapi': {
            'files': ['main.py', 'requirements.txt', '.env.example', 'Dockerfile', '.gitignore', 'README.md'],
            'dirs': ['app', 'tests', 'docs']
        },
        'react': {
            'files': ['package.json', 'tsconfig.json', 'vite.config.ts', 'index.html', '.gitignore'],
            'dirs': ['src', 'src/components', 'public', 'tests']
        }
    }
    
    def init_project(self, template: str, name: str, path: str = ".", options: Optional[Dict[str, Any]] = None) -> ProjectResult:
        """Initialize new project from template."""
        try:
            if template not in self.TEMPLATES:
                return ProjectResult(success=False, error=f"Unknown template: {template}")
            
            project_path = Path(path) / name
            if project_path.exists():
                return ProjectResult(success=False, error=f"Directory exists: {project_path}")
            
            project_path.mkdir(parents=True)
            files_created = []
            
            # Create dirs
            for dir_name in self.TEMPLATES[template]['dirs']:
                (project_path / dir_name).mkdir(parents=True, exist_ok=True)
            
            # Create files (simplified)
            for file_name in self.TEMPLATES[template]['files']:
                file_path = project_path / file_name
                file_path.write_text(f"# {file_name} for {name}\n")
                files_created.append(file_path)
            
            # Git init
            try:
                subprocess.run(['git', 'init'], cwd=project_path, capture_output=True, timeout=5, check=True)
                subprocess.run(['git', 'add', '.'], cwd=project_path, capture_output=True, timeout=5, check=True)
                subprocess.run(['git', 'commit', '-m', f'[KIVA-AUTO] init: {name}'], cwd=project_path, capture_output=True, timeout=5, check=True)
            except Exception:
                pass
            
            return ProjectResult(success=True, project_path=project_path, files_created=files_created)
        
        except Exception as e:
            return ProjectResult(success=False, error=str(e))
    
    def scaffold_element(self, element_type: str, name: str, typescript: bool = False, project_path: Optional[str] = None) -> ProjectResult:
        """Scaffold project element."""
        try:
            base_path = Path(project_path or ".")
            files_created = []
            
            if element_type == "component":
                component_dir = base_path / "src" / "components" / name
                component_dir.mkdir(parents=True, exist_ok=True)
                ext = "tsx" if typescript else "jsx"
                component_file = component_dir / f"{name}.{ext}"
                component_file.write_text(f"// {name} Component\nexport const {name} = () => {{\n  return <div>{name}</div>;\n}};\n")
                files_created.append(component_file)
            
            return ProjectResult(success=True, files_created=files_created)
        
        except Exception as e:
            return ProjectResult(success=False, error=str(e))
