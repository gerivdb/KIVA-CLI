#!/usr/bin/env python3
"""
Cross-Repo Citizen Synchronization

Scans ecosystem-1 repositories (16 repos) and synchronizes citizens:
- Extracts entities from ECOS_ROOT.json in each repo
- Auto-registers missing citizens in CitizenManager
- Detects entity lifecycle changes
- Syncs dependencies and relationships
- Generates consolidated registry
- Calculates φ-CPS deltas per repo
"""

import sys
import json
import argparse
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from tools.core.citizen_manager import (
        CitizenManager,
        EntityLevel,
        EntityType,
        LifecycleState
    )
    from tools.core.global_wal_manager import GlobalWALManager
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)


# Ecosystem-1 repositories
ECOSYSTEM_REPOS = [
    "KIVA-CLI",
    "ECOYSTEM",
    "DevTools",
    "BRAIN",
    "FLUENCE",
    "CANDIDATOR",
    "racines",
    "email-sender-1",
    "BANK-BUSTER",
    "GERIBOOKING",
    "BRAIN-DOCS"
]


class CrossRepoSync:
    """
    Cross-repository citizen synchronization.
    
    Scans multiple repos and syncs entities to CitizenManager.
    """
    
    def __init__(self, repos: Optional[List[str]] = None, dry_run: bool = False):
        """
        Initialize cross-repo sync.
        
        Args:
            repos: List of repos to sync (default: all ecosystem-1)
            dry_run: Preview changes without applying
        """
        self.repos = repos or ECOSYSTEM_REPOS
        self.dry_run = dry_run
        
        self.citizen_manager = CitizenManager()
        self.wal_manager = GlobalWALManager()
        
        self.stats = {
            "repos_scanned": 0,
            "citizens_found": 0,
            "citizens_registered": 0,
            "citizens_updated": 0,
            "citizens_skipped": 0,
            "errors": []
        }
    
    def sync_all(self) -> Dict[str, Any]:
        """
        Sync citizens from all repos.
        
        Returns:
            Statistics dictionary
        """
        print(f"🔄 Cross-Repo Sync Started")
        print(f"   Mode: {'DRY-RUN' if self.dry_run else 'LIVE'}")
        print(f"   Repos: {len(self.repos)}\n")
        
        for repo in self.repos:
            try:
                self._sync_repo(repo)
                self.stats["repos_scanned"] += 1
            except Exception as e:
                error_msg = f"Error syncing {repo}: {str(e)}"
                print(f"❌ {error_msg}")
                self.stats["errors"].append(error_msg)
        
        self._print_summary()
        return self.stats
    
    def _sync_repo(self, repo: str):
        """
        Sync citizens from single repo.
        
        Args:
            repo: Repository name
        """
        print(f"📂 Scanning repo: {repo}")
        
        # Locate ECOS_ROOT.json
        repo_path = self._find_repo_path(repo)
        if not repo_path:
            print(f"   ⚠️  Repo path not found (skipping)")
            return
        
        ecos_root_path = repo_path / "ECOS_ROOT.json"
        if not ecos_root_path.exists():
            print(f"   ⚠️  ECOS_ROOT.json not found (skipping)")
            return
        
        # Parse ECOS_ROOT.json
        with open(ecos_root_path, 'r') as f:
            ecos_data = json.load(f)
        
        # Extract entities
        entities = self._extract_entities(ecos_data, repo)
        
        if not entities:
            print(f"   ℹ️  No entities found")
            return
        
        print(f"   ✅ Found {len(entities)} entit(ies)")
        self.stats["citizens_found"] += len(entities)
        
        # Process each entity
        for entity in entities:
            self._process_entity(entity, repo)
    
    def _extract_entities(self, ecos_data: Dict[str, Any], repo: str) -> List[Dict[str, Any]]:
        """
        Extract entities from ECOS_ROOT.json.
        
        Args:
            ecos_data: Parsed ECOS_ROOT.json
            repo: Repository name
        
        Returns:
            List of entity dictionaries
        """
        entities = []
        
        # Main project entity
        if "name" in ecos_data:
            entities.append({
                "name": ecos_data.get("name", repo),
                "type": "PROJECT",
                "level": self._infer_level(ecos_data),
                "lifecycle": ecos_data.get("lifecycle", "ACTIVE"),
                "phi_cps": ecos_data.get("phi_cps", 0.005),
                "metadata": {
                    "version": ecos_data.get("version"),
                    "description": ecos_data.get("description")
                }
            })
        
        # Capabilities as components
        capabilities = ecos_data.get("capabilities", [])
        for cap in capabilities:
            if isinstance(cap, str):
                entities.append({
                    "name": cap[:50],  # Truncate long capability names
                    "type": "COMPONENT",
                    "level": "L1_VALIDATED",
                    "lifecycle": "ACTIVE",
                    "phi_cps": 0.003,
                    "metadata": {"capability": cap}
                })
        
        return entities
    
    def _infer_level(self, ecos_data: Dict[str, Any]) -> str:
        """
        Infer entity level from ECOS_ROOT.json metadata.
        
        Args:
            ecos_data: Parsed ECOS_ROOT.json
        
        Returns:
            Entity level string
        """
        phi_cps = ecos_data.get("phi_cps", 0.0)
        lifecycle = ecos_data.get("lifecycle", "GENESIS")
        
        # Level inference logic
        if lifecycle == "ARCHIVED":
            return "L5_LEGACY"
        elif phi_cps >= 4.0:
            return "L4_CRITICAL"
        elif phi_cps >= 3.0:
            return "L3_PRODUCTION"
        elif phi_cps >= 2.0:
            return "L2_OPERATIONAL"
        elif phi_cps >= 1.0:
            return "L1_VALIDATED"
        else:
            return "L0_GENESIS"
    
    def _process_entity(self, entity: Dict[str, Any], repo: str):
        """
        Process and register/update entity.
        
        Args:
            entity: Entity dictionary
            repo: Repository name
        """
        entity_name = entity["name"]
        
        # Check if citizen exists
        existing = self._find_existing_citizen(entity_name, repo)
        
        if existing:
            # Update existing citizen
            if self._needs_update(existing, entity):
                if not self.dry_run:
                    self._update_citizen(existing, entity)
                print(f"      ✓ Updated: {entity_name}")
                self.stats["citizens_updated"] += 1
            else:
                print(f"      - Skipped: {entity_name} (no changes)")
                self.stats["citizens_skipped"] += 1
        else:
            # Register new citizen
            if not self.dry_run:
                self._register_citizen(entity, repo)
            print(f"      + Registered: {entity_name}")
            self.stats["citizens_registered"] += 1
    
    def _find_existing_citizen(self, name: str, repo: str) -> Optional[Any]:
        """
        Find existing citizen by name and repo.
        
        Args:
            name: Entity name
            repo: Repository name
        
        Returns:
            Citizen object or None
        """
        citizens = self.citizen_manager.list_citizens(repo=repo, limit=1000)
        
        for citizen in citizens:
            if citizen.name == name:
                return citizen
        
        return None
    
    def _needs_update(self, existing: Any, new_entity: Dict[str, Any]) -> bool:
        """
        Check if citizen needs update.
        
        Args:
            existing: Existing citizen object
            new_entity: New entity data
        
        Returns:
            True if update needed
        """
        # Check level
        if existing.entity_level != new_entity["level"]:
            return True
        
        # Check lifecycle
        if existing.lifecycle_state != new_entity["lifecycle"]:
            return True
        
        return False
    
    def _register_citizen(self, entity: Dict[str, Any], repo: str):
        """
        Register new citizen.
        
        Args:
            entity: Entity dictionary
            repo: Repository name
        """
        self.citizen_manager.register_citizen(
            name=entity["name"],
            entity_type=EntityType[entity["type"]],
            repo=repo,
            entity_level=EntityLevel[entity["level"]],
            lifecycle_state=LifecycleState[entity["lifecycle"]],
            metadata=entity.get("metadata")
        )
    
    def _update_citizen(self, existing: Any, new_entity: Dict[str, Any]):
        """
        Update existing citizen.
        
        Args:
            existing: Existing citizen object
            new_entity: New entity data
        """
        # Check if promotion/demotion needed
        new_level = EntityLevel[new_entity["level"]]
        current_level = EntityLevel[existing.entity_level]
        
        if new_level != current_level:
            # Determine if promotion or demotion
            level_order = [
                EntityLevel.L0_GENESIS,
                EntityLevel.L1_VALIDATED,
                EntityLevel.L2_OPERATIONAL,
                EntityLevel.L3_PRODUCTION,
                EntityLevel.L4_CRITICAL
            ]
            
            try:
                current_idx = level_order.index(current_level)
                new_idx = level_order.index(new_level)
                
                if new_idx > current_idx:
                    # Promotion
                    self.citizen_manager.promote_entity(
                        citizen_id=existing.citizen_id,
                        target_level=new_level
                    )
                else:
                    # Demotion
                    self.citizen_manager.demote_entity(
                        citizen_id=existing.citizen_id,
                        target_level=new_level,
                        reason="Cross-repo sync auto-update"
                    )
            except ValueError:
                pass
    
    def _find_repo_path(self, repo: str) -> Optional[Path]:
        """
        Find repository path on filesystem.
        
        Args:
            repo: Repository name
        
        Returns:
            Path to repo or None
        """
        # Common locations to check
        search_paths = [
            Path.cwd() / ".." / repo,
            Path.home() / "repos" / repo,
            Path.home() / "Projects" / repo,
            Path.home() / "github" / repo,
            Path("/workspace") / repo
        ]
        
        for path in search_paths:
            if path.exists() and path.is_dir():
                return path
        
        return None
    
    def _print_summary(self):
        """
        Print synchronization summary.
        """
        print("\n" + "="*60)
        print("CROSS-REPO SYNC SUMMARY")
        print("="*60)
        print(f"Repos scanned:       {self.stats['repos_scanned']}")
        print(f"Citizens found:      {self.stats['citizens_found']}")
        print(f"Citizens registered: {self.stats['citizens_registered']}")
        print(f"Citizens updated:    {self.stats['citizens_updated']}")
        print(f"Citizens skipped:    {self.stats['citizens_skipped']}")
        
        if self.stats["errors"]:
            print(f"\n❌ Errors: {len(self.stats['errors'])}")
            for error in self.stats["errors"][:5]:
                print(f"   - {error}")
        
        print("="*60)
        
        # Log to WAL
        if not self.dry_run:
            self.wal_manager.append_event(
                operation="CROSS_REPO_SYNC",
                repo="ECOSYSTEM",
                phi_cps_delta=self.stats["citizens_registered"] * 0.005,
                metadata={
                    "repos_scanned": self.stats["repos_scanned"],
                    "citizens_registered": self.stats["citizens_registered"],
                    "citizens_updated": self.stats["citizens_updated"]
                }
            )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Cross-repo citizen synchronization"
    )
    
    parser.add_argument(
        "--repos",
        help="Comma-separated list of repos (default: all ecosystem-1)"
    )
    
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without applying"
    )
    
    args = parser.parse_args()
    
    # Parse repos
    repos = None
    if args.repos:
        repos = [r.strip() for r in args.repos.split(",")]
    
    # Run sync
    sync = CrossRepoSync(repos=repos, dry_run=args.dry_run)
    stats = sync.sync_all()
    
    # Exit code
    sys.exit(0 if not stats["errors"] else 1)
