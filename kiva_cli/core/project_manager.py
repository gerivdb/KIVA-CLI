# KIVA CLI - ProjectManager
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

@dataclass
class ProjectResult:
    success: bool
    project_path: Optional[Path] = None
    files_created: Optional[List[Path]] = None
    error: Optional[str] = None

class ProjectManager:
    TEMPLATES = {
        'fastapi': {'files': ['main.py', 'requirements.txt'], 'dirs': ['app', 'tests']},
        'react': {'files': ['package.json', 'tsconfig.json'], 'dirs': ['src', 'public']}
    }
    
    def init_project(self, template: str, name: str, path: str = '.') -> ProjectResult:
        if template not in self.TEMPLATES:
            return ProjectResult(success=False, error=f"Unknown template: {template}")
        project_path = Path(path) / name
        project_path.mkdir(parents=True, exist_ok=True)
        return ProjectResult(success=True, project_path=project_path)
