#!/usr/bin/env python3
"""
Skill Installer - KIVA CLI

Handles installation, update, and removal of skills from the SKILLS marketplace.
"""

import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Any

import yaml


class SkillPackage:
    """Represents a skill package."""
    def __init__(self, data: Dict[str, Any]):
        self.name = data.get("name", "")
        self.version = data.get("version", "1.0.0")
        self.description = data.get("description", "")
        self.author = data.get("author", "")
        self.repository = data.get("repository", "")  # GitHub URL
        self.dependencies = data.get("dependencies", [])
        self.install_path = data.get("install_path", "")
        self.files = data.get("files", [])


class SkillInstaller:
    """Manages skill installation, updates, and removal."""

    def __init__(self, skills_dir: Optional[str] = None, registry_path: Optional[str] = None):
        if skills_dir is None:
            skills_dir = "D:\\DO\\WEB\\TOOLS\\SKILLS\\installed"
        if registry_path is None:
            registry_path = "D:\\DO\\WEB\\TOOLS\\SKILLS\\registry.json"
        
        self.skills_dir = Path(skills_dir)
        self.registry_path = Path(registry_path)
        self.installed_skills: Dict[str, SkillPackage] = {}
        self.available_skills: List[Dict[str, Any]] = []
        self._load_installed()
        self._load_registry()

    def _load_installed(self):
        """Load installed skills."""
        if self.skills_dir.exists():
            for skill_dir in self.skills_dir.iterdir():
                if skill_dir.is_dir():
                    metadata_file = skill_dir / "skill.json"
                    if metadata_file.exists():
                        try:
                            with open(metadata_file, 'r', encoding='utf-8') as f:
                                data = json.load(f)
                            skill = SkillPackage(data)
                            skill.install_path = str(skill_dir)
                            self.installed_skills[skill.name] = skill
                        except (json.JSONDecodeError, IOError):
                            pass

    def _load_registry(self):
        """Load available skills from registry."""
        if self.registry_path.exists():
            try:
                with open(self.registry_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self.available_skills = data.get("skills", [])
            except (json.JSONDecodeError, IOError):
                pass

    def list_installed(self) -> List[SkillPackage]:
        """List all installed skills."""
        return list(self.installed_skills.values())

    def list_available(self) -> List[Dict[str, Any]]:
        """List all available skills from registry."""
        return self.available_skills

    def install_skill(self, skill_name: str, version: Optional[str] = None) -> bool:
        """
        Install a skill from the registry.
        
        Args:
            skill_name: Name of the skill to install
            version: Specific version to install (default: latest)
        
        Returns:
            True if successful
        """
        # Check if already installed
        if skill_name in self.installed_skills:
            print(f"Skill '{skill_name}' is already installed.")
            return False
        
        # Find skill in registry
        skill_data = None
        for s in self.available_skills:
            if s.get("name") == skill_name:
                skill_data = s
                break
        
        if not skill_data:
            print(f"Skill '{skill_name}' not found in registry.")
            return False
        
        # Clone or download skill
        install_path = self.skills_dir / skill_name
        repo_url = skill_data.get("repository", "")
        
        if repo_url:
            # Clone from GitHub
            if not repo_url.startswith("https://"):
                repo_url = f"https://github.com/{repo_url}.git"
            
            try:
                subprocess.run(
                    ["git", "clone", repo_url, str(install_path)],
                    check=True,
                    capture_output=True,
                    timeout=60
                )
            except subprocess.CalledProcessError as e:
                print(f"Failed to clone skill: {e}")
                return False
            except subprocess.TimeoutExpired:
                print("Clone timed out.")
                return False
        else:
            # Create empty directory for local skill
            install_path.mkdir(parents=True, exist_ok=True)
        
        # Save metadata
        skill = SkillPackage(skill_data)
        skill.install_path = str(install_path)
        metadata_file = install_path / "skill.json"
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(skill_data, f, indent=2, ensure_ascii=False)
        
        self.installed_skills[skill_name] = skill
        print(f"Skill '{skill_name}' installed successfully.")
        return True

    def update_skill(self, skill_name: str) -> bool:
        """
        Update an installed skill.
        
        Args:
            skill_name: Name of the skill to update
        
        Returns:
            True if successful
        """
        if skill_name not in self.installed_skills:
            print(f"Skill '{skill_name}' is not installed.")
            return False
        
        skill = self.installed_skills[skill_name]
        install_path = Path(skill.install_path)
        
        # Pull latest from git
        if (install_path / ".git").exists():
            try:
                subprocess.run(
                    ["git", "pull"],
                    cwd=str(install_path),
                    check=True,
                    capture_output=True,
                    timeout=30
                )
                print(f"Skill '{skill_name}' updated successfully.")
                return True
            except subprocess.CalledProcessError as e:
                print(f"Failed to update skill: {e}")
                return False
        else:
            print(f"Skill '{skill_name}' is not a git repository.")
            return False

    def remove_skill(self, skill_name: str) -> bool:
        """
        Remove an installed skill.
        
        Args:
            skill_name: Name of the skill to remove
        
        Returns:
            True if successful
        """
        if skill_name not in self.installed_skills:
            print(f"Skill '{skill_name}' is not installed.")
            return False
        
        skill = self.installed_skills[skill_name]
        install_path = Path(skill.install_path)
        
        try:
            shutil.rmtree(install_path)
            del self.installed_skills[skill_name]
            print(f"Skill '{skill_name}' removed successfully.")
            return True
        except Exception as e:
            print(f"Failed to remove skill: {e}")
            return False

    def get_skill_info(self, skill_name: str) -> Optional[SkillPackage]:
        """Get information about an installed skill."""
        return self.installed_skills.get(skill_name)