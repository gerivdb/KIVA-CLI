#!/usr/bin/env python3
"""
Entity Path Mapper - KIVA CLI

Links KIVA citizens to local repository paths.
Provides entity-aware path resolution for multi-repo ECOS ecosystem.
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Any

import yaml


class CitizenInfo:
    """Information about a KIVA citizen."""
    def __init__(self, data: Dict[str, Any]):
        self.id = data.get("id", "")
        self.slug = data.get("slug", "")
        self.role_type = data.get("role_type", "")
        self.tier = data.get("tier", "")
        self.layer = data.get("layer", "")
        self.criticality = data.get("criticality", "")
        self.level = data.get("level", "")
        self.status = data.get("status", "")
        self.repos_served = data.get("repos_served", [])
        self.local_paths = data.get("local_paths", {})
        self.skills = data.get("skills", [])
        self.raw_data = data


class EntityPathMapper:
    """Maps KIVA citizens to local repository paths."""

    def __init__(self, citizens_dir: Optional[str] = None):
        if citizens_dir is None:
            citizens_dir = "D:\\DO\\WEB\\TOOLS\\ECOYSTEM\\.citizens"
        self.citizens_dir = Path(citizens_dir)
        self.citizens: Dict[str, CitizenInfo] = {}
        self._load_citizens()

    def _load_citizens(self):
        """Load all citizen definitions from YAML files."""
        if not self.citizens_dir.exists():
            return
        
        for yaml_file in self.citizens_dir.glob("*.yml"):
            try:
                with open(yaml_file, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f)
                if data and "id" in data:
                    citizen = CitizenInfo(data)
                    self.citizens[citizen.id] = citizen
            except (yaml.YAMLError, IOError) as e:
                print(f"Warning: Could not load {yaml_file}: {e}")

    def get_citizen(self, citizen_id: str) -> Optional[CitizenInfo]:
        """Get citizen by ID."""
        return self.citizens.get(citizen_id)

    def list_citizens(self, repo_filter: Optional[str] = None) -> List[CitizenInfo]:
        """List all citizens, optionally filtered by repo."""
        if repo_filter:
            return [
                c for c in self.citizens.values()
                if repo_filter in c.repos_served
            ]
        return list(self.citizens.values())

    def get_local_paths(self, citizen_id: str) -> Dict[str, str]:
        """Get local paths for a citizen."""
        citizen = self.get_citizen(citizen_id)
        if citizen:
            return citizen.local_paths
        return {}

    def locate_citizen(self, citizen_id: str, repo_name: Optional[str] = None) -> Optional[str]:
        """
        Get the local path for a citizen in a specific repo.
        
        Args:
            citizen_id: Citizen ID
            repo_name: Repository name (optional, returns first path if not specified)
        
        Returns:
            Local path or None
        """
        paths = self.get_local_paths(citizen_id)
        if not paths:
            return None
        
        if repo_name and repo_name in paths:
            return paths[repo_name]
        
        # Return first path if no repo specified
        return next(iter(paths.values()), None)

    def sync_citizens(self) -> int:
        """
        Re-sync citizens from YAML files.
        
        Returns:
            Number of citizens loaded
        """
        self.citizens.clear()
        self._load_citizens()
        return len(self.citizens)

    def get_citizens_for_repo(self, repo_name: str) -> List[CitizenInfo]:
        """Get all citizens that serve a specific repository."""
        return [
            c for c in self.citizens.values()
            if repo_name in c.repos_served
        ]

    def export_registry(self) -> Dict[str, Any]:
        """Export the full citizen registry as a dictionary."""
        return {
            cid: {
                "id": c.id,
                "slug": c.slug,
                "role_type": c.role_type,
                "tier": c.tier,
                "layer": c.layer,
                "status": c.status,
                "repos_served": c.repos_served,
                "local_paths": c.local_paths,
            }
            for cid, c in self.citizens.items()
        }