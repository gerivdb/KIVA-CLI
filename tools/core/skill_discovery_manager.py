#!/usr/bin/env python3
"""
Skill Discovery Manager - KIVA CLI

Discovers new skills, verifies their existence in the ecosystem,
registers them in the SKILLS registry, and creates issues/EPICs
in concerned repositories.

Ontology:
- Skill.repos_served ∩ Repo.name ≠ ∅ → Repo is concerned
- Skill.capabilities ∩ Repo.needs ≠ ∅ → Repo is concerned
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Any, Set

import yaml


class SkillInfo:
    """Information about a skill."""
    def __init__(self, data: Dict[str, Any]):
        self.name = data.get("name", "")
        self.description = data.get("description", "")
        self.capabilities = data.get("capabilities", [])
        self.repos_served = data.get("repos_served", [])
        self.version = data.get("version", "1.0.0")
        self.status = data.get("status", "active")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "capabilities": self.capabilities,
            "repos_served": self.repos_served,
            "version": self.version,
            "status": self.status
        }


class RepoInfo:
    """Information about a repository."""
    def __init__(self, data: Dict[str, Any]):
        self.name = data.get("name", "")
        self.local_path = data.get("local_path", "")
        self.remote_url = data.get("remote_url", "")
        self.needs = data.get("needs", [])

    def is_concerned_by(self, skill: SkillInfo) -> bool:
        """
        Check if this repo is concerned by a skill.
        
        Concerned iff:
        - skill.repos_served contains this repo name, OR
        - skill.capabilities intersects with repo.needs
        """
        if self.name in skill.repos_served:
            return True
        
        skill_caps = set(skill.capabilities)
        repo_needs = set(self.needs)
        return bool(skill_caps & repo_needs)


class SkillDiscoveryManager:
    """Manages skill discovery, verification, registration, and issue creation."""

    def __init__(self, skills_registry_path: Optional[str] = None, repos_path: Optional[str] = None):
        if skills_registry_path is None:
            skills_registry_path = "D:\\DO\\WEB\\TOOLS\\SKILLS\\registry.json"
        if repos_path is None:
            repos_path = "D:\\DO\\WEB\\TOOLS\\ECOYSTEM\\registry\\repos.json"
        
        self.skills_registry_path = Path(skills_registry_path)
        self.repos_path = Path(repos_path)
        self.skills: Dict[str, SkillInfo] = {}
        self.repos: Dict[str, RepoInfo] = {}
        self._load_registry()
        self._load_repos()

    def _load_registry(self):
        """Load skills registry."""
        if self.skills_registry_path.exists():
            try:
                with open(self.skills_registry_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                for skill_data in data.get("skills", []):
                    skill = SkillInfo(skill_data)
                    self.skills[skill.name] = skill
            except (json.JSONDecodeError, IOError) as e:
                print(f"Warning: Could not load skills registry: {e}")

    def _load_repos(self):
        """Load repository information."""
        if self.repos_path.exists():
            try:
                with open(self.repos_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                for repo_data in data.get("repos", []):
                    repo = RepoInfo(repo_data)
                    self.repos[repo.name] = repo
            except (json.JSONDecodeError, IOError) as e:
                print(f"Warning: Could not load repos: {e}")

    def discover_skills(self) -> List[SkillInfo]:
        """
        Discover potential skills from the ecosystem.
        
        Scans:
        - Existing commands in KIVA-CLI
        - Tools in DevTools
        - Citizen definitions
        
        Returns:
            List of discovered skills
        """
        discovered = []
        
        # Scan KIVA-CLI commands
        kiva_cli_path = Path("D:\\DO\\WEB\\TOOLS\\KIVA-CLI\\kiva_cli\\commands")
        if kiva_cli_path.exists():
            for cmd_file in kiva_cli_path.glob("*_commands.py"):
                skill_name = cmd_file.stem.replace("_commands", "")
                if skill_name not in self.skills:
                    skill = SkillInfo({
                        "name": skill_name,
                        "description": f"Auto-discovered: {skill_name} commands",
                        "capabilities": [f"{skill_name}_operations"],
                        "repos_served": ["KIVA-CLI"]
                    })
                    discovered.append(skill)
        
        return discovered

    def verify_skill(self, skill_name: str) -> bool:
        """Check if a skill exists in the registry."""
        return skill_name in self.skills

    def register_skill(self, skill: SkillInfo) -> bool:
        """Register a skill in the SKILLS registry."""
        if skill.name in self.skills:
            return False
        
        self.skills[skill.name] = skill
        self._save_registry()
        return True

    def _save_registry(self):
        """Save skills registry."""
        data = {
            "skills": [skill.to_dict() for skill in self.skills.values()]
        }
        os.makedirs(os.path.dirname(self.skills_registry_path), exist_ok=True)
        with open(self.skills_registry_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def find_concerned_repos(self, skill: SkillInfo) -> List[RepoInfo]:
        """
        Find repositories concerned by a skill.
        
        Uses ontology:
        - skill.repos_served ∩ repo.name ≠ ∅
        - skill.capabilities ∩ repo.needs ≠ ∅
        """
        return [repo for repo in self.repos.values() if repo.is_concerned_by(skill)]

    def get_skill_capabilities(self, skill_name: str) -> List[str]:
        """Get capabilities of a skill."""
        skill = self.skills.get(skill_name)
        return skill.capabilities if skill else []

    def get_repo_needs(self, repo_name: str) -> List[str]:
        """Get needs of a repository."""
        repo = self.repos.get(repo_name)
        return repo.needs if repo else []

    def export_skill_ontology(self, output_path: str):
        """Export skill ontology as YAML."""
        ontology = {
            "skills": {name: skill.to_dict() for name, skill in self.skills.items()},
            "repos": {name: {"name": repo.name, "needs": repo.needs} for name, repo in self.repos.items()}
        }
        with open(output_path, 'w', encoding='utf-8') as f:
            yaml.dump(ontology, f, default_flow_style=False, allow_unicode=True)