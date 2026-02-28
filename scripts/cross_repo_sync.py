#!/usr/bin/env python3
"""
Cross-Repository Synchronization Script
Syncs ECOS_ROOT.json, WAL entries, and metrics across ecosystem-1 repositories.
"""

import json
import sqlite3
import argparse
import subprocess
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class CrossRepoSync:
    """
    Cross-repository synchronization manager for ecosystem-1.
    
    Capabilities:
    - Sync ECOS_ROOT.json to ECOYSTEM repo
    - Propagate WAL entries across repos
    - Update metrics dashboards
    - Validate IntentHash chains
    - Detect φ-CPS drift
    """
    
    def __init__(self, root_dir: Path, repos_config: Dict[str, str]):
        """
        Initialize cross-repo sync manager.
        
        Args:
            root_dir: Root directory containing all repos
            repos_config: Dict mapping repo names to paths
        """
        self.root_dir = Path(root_dir)
        self.repos_config = repos_config
        self.sync_results: List[Dict[str, Any]] = []
        
    def sync_ecos_root(self, source_repo: str, target_repos: List[str]) -> Dict[str, Any]:
        """
        Sync ECOS_ROOT.json from source to target repositories.
        
        Args:
            source_repo: Source repository name (e.g., 'KIVA-CLI')
            target_repos: List of target repository names
            
        Returns:
            Dict with sync results
        """
        logger.info(f"Syncing ECOS_ROOT.json from {source_repo} to {len(target_repos)} repos")
        
        source_path = self.root_dir / self.repos_config[source_repo] / "ECOS_ROOT.json"
        
        if not source_path.exists():
            logger.error(f"Source ECOS_ROOT.json not found: {source_path}")
            return {"success": False, "error": "Source file not found"}
        
        with open(source_path, 'r') as f:
            ecos_data = json.load(f)
        
        # Update timestamp
        ecos_data['last_updated'] = datetime.utcnow().isoformat() + 'Z'
        
        results = []
        for target_repo in target_repos:
            try:
                target_path = self.root_dir / self.repos_config[target_repo]
                
                # Check if repo directory exists
                if not target_path.exists():
                    logger.warning(f"Target repo not found: {target_path}")
                    results.append({
                        "repo": target_repo,
                        "success": False,
                        "error": "Repository directory not found"
                    })
                    continue
                
                # Write ECOS_ROOT.json
                target_file = target_path / "ECOS_ROOT.json"
                with open(target_file, 'w') as f:
                    json.dump(ecos_data, f, indent=2)
                
                logger.info(f"✓ Synced ECOS_ROOT.json to {target_repo}")
                results.append({
                    "repo": target_repo,
                    "success": True,
                    "path": str(target_file)
                })
                
            except Exception as e:
                logger.error(f"Failed to sync to {target_repo}: {e}")
                results.append({
                    "repo": target_repo,
                    "success": False,
                    "error": str(e)
                })
        
        success_count = sum(1 for r in results if r['success'])
        return {
            "success": success_count > 0,
            "total": len(target_repos),
            "succeeded": success_count,
            "failed": len(target_repos) - success_count,
            "results": results
        }
    
    def sync_wal_database(self, source_repo: str, target_repo: str) -> Dict[str, Any]:
        """
        Sync WAL database from source to target.
        
        Args:
            source_repo: Source repository name
            target_repo: Target repository name
            
        Returns:
            Dict with sync results
        """
        logger.info(f"Syncing WAL database from {source_repo} to {target_repo}")
        
        # Typical WAL paths
        source_wal_paths = [
            self.root_dir / self.repos_config[source_repo] / "global_wal.db",
            Path.home() / ".kiva" / "global_wal.db"
        ]
        
        source_wal = None
        for path in source_wal_paths:
            if path.exists():
                source_wal = path
                break
        
        if not source_wal:
            logger.warning("Source WAL database not found")
            return {"success": False, "error": "Source WAL not found"}
        
        target_path = self.root_dir / self.repos_config[target_repo]
        if not target_path.exists():
            logger.error(f"Target repo not found: {target_path}")
            return {"success": False, "error": "Target repo not found"}
        
        target_wal = target_path / "global_wal.db"
        
        try:
            # Copy WAL database
            shutil.copy2(source_wal, target_wal)
            logger.info(f"✓ Synced WAL database to {target_repo}")
            
            # Verify copy
            if target_wal.exists():
                return {
                    "success": True,
                    "source": str(source_wal),
                    "target": str(target_wal),
                    "size_bytes": target_wal.stat().st_size
                }
            else:
                return {"success": False, "error": "Copy verification failed"}
                
        except Exception as e:
            logger.error(f"Failed to sync WAL: {e}")
            return {"success": False, "error": str(e)}
    
    def update_repo_metrics(self, repo_name: str) -> Dict[str, Any]:
        """
        Update repository metrics in ECOS_ROOT.json.
        
        Args:
            repo_name: Repository name
            
        Returns:
            Dict with updated metrics
        """
        logger.info(f"Updating metrics for {repo_name}")
        
        repo_path = self.root_dir / self.repos_config[repo_name]
        
        if not repo_path.exists():
            logger.warning(f"Repository not found: {repo_path}")
            return {"success": False, "error": "Repository not found"}
        
        try:
            # Get git commit count
            result = subprocess.run(
                ['git', 'rev-list', '--count', 'HEAD'],
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                commit_count = int(result.stdout.strip())
            else:
                commit_count = 0
            
            # Get last commit timestamp
            result = subprocess.run(
                ['git', 'log', '-1', '--format=%aI'],
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            last_commit = result.stdout.strip() if result.returncode == 0 else None
            
            return {
                "success": True,
                "repo": repo_name,
                "total_commits": commit_count,
                "last_commit": last_commit,
                "last_sync": datetime.utcnow().isoformat() + 'Z'
            }
            
        except Exception as e:
            logger.error(f"Failed to update metrics for {repo_name}: {e}")
            return {"success": False, "error": str(e)}
    
    def validate_phi_cps_consistency(self) -> Dict[str, Any]:
        """
        Validate φ-CPS consistency across ecosystem.
        
        Returns:
            Dict with validation results
        """
        logger.info("Validating φ-CPS consistency across repos")
        
        phi_values = {}
        
        for repo_name, repo_rel_path in self.repos_config.items():
            repo_path = self.root_dir / repo_rel_path
            ecos_file = repo_path / "ECOS_ROOT.json"
            
            if ecos_file.exists():
                try:
                    with open(ecos_file, 'r') as f:
                        data = json.load(f)
                        phi_values[repo_name] = data.get('phi_cps_current', 0.0)
                except Exception as e:
                    logger.warning(f"Failed to read φ-CPS from {repo_name}: {e}")
        
        if not phi_values:
            return {"success": False, "error": "No φ-CPS values found"}
        
        # Check for consistency (all values should be similar)
        unique_values = set(phi_values.values())
        max_drift = max(unique_values) - min(unique_values) if unique_values else 0
        
        return {
            "success": True,
            "phi_values": phi_values,
            "unique_values": len(unique_values),
            "max_drift": max_drift,
            "drift_acceptable": max_drift < 0.05
        }
    
    def generate_sync_report(self) -> str:
        """
        Generate Markdown sync report.
        
        Returns:
            Markdown formatted report
        """
        timestamp = datetime.utcnow().isoformat() + 'Z'
        
        report = f"""# Cross-Repository Sync Report

**Date**: {timestamp}  
**Ecosystem**: ecosystem-1  
**Mode**: BATCH NO-HITL

---

## Sync Summary

"""
        
        if self.sync_results:
            report += "### Completed Operations\n\n"
            for result in self.sync_results:
                status = "✅" if result.get('success') else "❌"
                report += f"- {status} {result.get('operation', 'Unknown')}\n"
                if 'details' in result:
                    report += f"  - {result['details']}\n"
        else:
            report += "*No sync operations performed*\n"
        
        report += "\n---\n\n"
        report += "**Generated by**: ECOS-AUTO Cross-Repo Sync\n"
        report += "**Mode**: H0 Autonomous\n"
        
        return report
    
    def execute_full_sync(self, source_repo: str = "KIVA-CLI") -> Dict[str, Any]:
        """
        Execute full sync workflow.
        
        Args:
            source_repo: Source repository for sync
            
        Returns:
            Dict with complete sync results
        """
        logger.info(f"Starting full sync from {source_repo}")
        
        results = {
            "timestamp": datetime.utcnow().isoformat() + 'Z',
            "source_repo": source_repo,
            "operations": []
        }
        
        # 1. Sync ECOS_ROOT.json to ECOYSTEM
        ecos_sync = self.sync_ecos_root(source_repo, ["ECOYSTEM"])
        results['operations'].append({
            "operation": "sync_ecos_root",
            "success": ecos_sync['success'],
            "details": f"Synced to {ecos_sync['succeeded']}/{ecos_sync['total']} repos"
        })
        self.sync_results.append(results['operations'][-1])
        
        # 2. Sync WAL database to ECOYSTEM
        wal_sync = self.sync_wal_database(source_repo, "ECOYSTEM")
        results['operations'].append({
            "operation": "sync_wal_database",
            "success": wal_sync['success'],
            "details": f"WAL size: {wal_sync.get('size_bytes', 0)} bytes" if wal_sync['success'] else wal_sync.get('error', '')
        })
        self.sync_results.append(results['operations'][-1])
        
        # 3. Validate φ-CPS consistency
        phi_validation = self.validate_phi_cps_consistency()
        results['operations'].append({
            "operation": "validate_phi_cps",
            "success": phi_validation['success'],
            "details": f"Max drift: {phi_validation.get('max_drift', 0):.4f}" if phi_validation['success'] else phi_validation.get('error', '')
        })
        self.sync_results.append(results['operations'][-1])
        
        # Generate report
        results['report'] = self.generate_sync_report()
        results['success'] = all(op['success'] for op in results['operations'])
        
        return results


def main():
    """
    CLI entry point for cross-repo sync.
    """
    parser = argparse.ArgumentParser(
        description="Cross-repository synchronization for ecosystem-1"
    )
    parser.add_argument(
        '--root',
        type=str,
        default='..',
        help='Root directory containing all repos (default: ..)'
    )
    parser.add_argument(
        '--source',
        type=str,
        default='KIVA-CLI',
        help='Source repository for sync (default: KIVA-CLI)'
    )
    parser.add_argument(
        '--operation',
        type=str,
        choices=['ecos_root', 'wal', 'metrics', 'validate', 'full'],
        default='full',
        help='Sync operation to perform (default: full)'
    )
    parser.add_argument(
        '--output',
        type=str,
        help='Output file for sync report (default: stdout)'
    )
    
    args = parser.parse_args()
    
    # Define repos config (relative paths from root)
    repos_config = {
        "KIVA-CLI": "KIVA-CLI",
        "ECOYSTEM": "ECOYSTEM",
        "DevTools": "DevTools",
        "CANDIDATOR": "CANDIDATOR",
        "racines": "racines",
        "email-sender-1": "email-sender-1",
        "FLUENCE": "FLUENCE",
        "BRAIN": "BRAIN",
        "BANK-BUSTER": "BANK-BUSTER",
        "GERIBOOKING": "GERIBOOKING",
        "BRAIN-DOCS": "BRAIN-DOCS"
    }
    
    syncer = CrossRepoSync(Path(args.root), repos_config)
    
    if args.operation == 'full':
        results = syncer.execute_full_sync(args.source)
        print(json.dumps(results, indent=2))
        
        if args.output:
            with open(args.output, 'w') as f:
                f.write(results['report'])
            logger.info(f"Report written to {args.output}")
    
    elif args.operation == 'ecos_root':
        results = syncer.sync_ecos_root(args.source, ["ECOYSTEM"])
        print(json.dumps(results, indent=2))
    
    elif args.operation == 'wal':
        results = syncer.sync_wal_database(args.source, "ECOYSTEM")
        print(json.dumps(results, indent=2))
    
    elif args.operation == 'validate':
        results = syncer.validate_phi_cps_consistency()
        print(json.dumps(results, indent=2))


if __name__ == '__main__':
    main()
