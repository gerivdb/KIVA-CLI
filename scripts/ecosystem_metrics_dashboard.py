#!/usr/bin/env python3
"""
Ecosystem Metrics Dashboard Generator
Generates comprehensive metrics dashboard for ecosystem-1.
"""

import json
import sqlite3
import argparse
import subprocess
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class EcosystemMetricsDashboard:
    """
    Generate comprehensive metrics dashboard for ecosystem-1.
    
    Metrics tracked:
    - φ-CPS evolution
    - Commit activity
    - Issue tracking
    - IntentHash chain integrity
    - Repository health
    - Cross-repo dependencies
    """
    
    def __init__(self, root_dir: Path, ecos_root_path: Path):
        """
        Initialize dashboard generator.
        
        Args:
            root_dir: Root directory containing all repos
            ecos_root_path: Path to ECOS_ROOT.json
        """
        self.root_dir = Path(root_dir)
        self.ecos_root_path = Path(ecos_root_path)
        self.metrics: Dict[str, Any] = {}
        
    def load_ecos_root(self) -> Dict[str, Any]:
        """
        Load ECOS_ROOT.json configuration.
        
        Returns:
            Dict containing ECOS_ROOT data
        """
        if not self.ecos_root_path.exists():
            logger.error(f"ECOS_ROOT.json not found: {self.ecos_root_path}")
            return {}
        
        with open(self.ecos_root_path, 'r') as f:
            return json.load(f)
    
    def collect_repo_metrics(self, repo_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Collect metrics for a single repository.
        
        Args:
            repo_config: Repository configuration from ECOS_ROOT
            
        Returns:
            Dict containing repo metrics
        """
        repo_name = repo_config['name']
        repo_path = self.root_dir / repo_name
        
        metrics = {
            "name": repo_name,
            "status": repo_config.get('status', 'UNKNOWN'),
            "role": repo_config.get('role', 'unknown'),
            "exists": repo_path.exists()
        }
        
        if not repo_path.exists():
            logger.warning(f"Repository not found: {repo_path}")
            return metrics
        
        try:
            # Git commit count
            result = subprocess.run(
                ['git', 'rev-list', '--count', 'HEAD'],
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=10
            )
            metrics['commit_count'] = int(result.stdout.strip()) if result.returncode == 0 else 0
            
            # Last commit info
            result = subprocess.run(
                ['git', 'log', '-1', '--format=%aI|%s|%an'],
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0 and result.stdout.strip():
                parts = result.stdout.strip().split('|')
                metrics['last_commit'] = {
                    "timestamp": parts[0] if len(parts) > 0 else None,
                    "message": parts[1] if len(parts) > 1 else None,
                    "author": parts[2] if len(parts) > 2 else None
                }
            
            # Commits in last 7 days
            week_ago = (datetime.now() - timedelta(days=7)).isoformat()
            result = subprocess.run(
                ['git', 'rev-list', '--count', f'--since="{week_ago}"', 'HEAD'],
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=10
            )
            metrics['commits_last_7_days'] = int(result.stdout.strip()) if result.returncode == 0 else 0
            
            # Count files
            result = subprocess.run(
                ['git', 'ls-files'],
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=10
            )
            metrics['file_count'] = len(result.stdout.strip().split('\n')) if result.returncode == 0 else 0
            
            # Repository size
            result = subprocess.run(
                ['du', '-sh', '.git'],
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                metrics['repo_size'] = result.stdout.split()[0]
            
        except Exception as e:
            logger.error(f"Failed to collect metrics for {repo_name}: {e}")
        
        return metrics
    
    def analyze_phi_cps_evolution(self, ecos_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze φ-CPS evolution across ecosystem.
        
        Args:
            ecos_data: ECOS_ROOT data
            
        Returns:
            Dict with φ-CPS analysis
        """
        phi_genesis = ecos_data.get('phi_cps_genesis', 4.092)
        phi_current = ecos_data.get('phi_cps_current', phi_genesis)
        
        analysis = {
            "phi_genesis": phi_genesis,
            "phi_current": phi_current,
            "delta_total": phi_current - phi_genesis,
            "delta_percent": ((phi_current - phi_genesis) / phi_genesis) * 100,
            "drift_threshold": 0.05,
            "drift_acceptable": abs(phi_current - phi_genesis) < 0.05
        }
        
        # Per-repo φ-CPS
        repos = ecos_data.get('repositories', [])
        analysis['repos'] = [
            {
                "name": repo['name'],
                "phi_cps": repo.get('phi_cps', phi_genesis),
                "phi_delta": repo.get('phi_delta_total', 0.0)
            }
            for repo in repos
        ]
        
        # Calculate statistics
        phi_values = [r['phi_cps'] for r in analysis['repos']]
        if phi_values:
            analysis['phi_avg'] = sum(phi_values) / len(phi_values)
            analysis['phi_min'] = min(phi_values)
            analysis['phi_max'] = max(phi_values)
            analysis['phi_range'] = analysis['phi_max'] - analysis['phi_min']
        
        return analysis
    
    def analyze_wal_integrity(self, wal_path: Optional[Path] = None) -> Dict[str, Any]:
        """
        Analyze WAL database integrity.
        
        Args:
            wal_path: Path to global_wal.db
            
        Returns:
            Dict with WAL analysis
        """
        if wal_path is None:
            # Try common locations
            wal_paths = [
                Path.home() / ".kiva" / "global_wal.db",
                self.root_dir / "KIVA-CLI" / "global_wal.db",
                self.root_dir / "ECOYSTEM" / "global_wal.db"
            ]
            for path in wal_paths:
                if path.exists():
                    wal_path = path
                    break
        
        if not wal_path or not wal_path.exists():
            logger.warning("WAL database not found")
            return {"available": False}
        
        try:
            conn = sqlite3.connect(wal_path)
            cursor = conn.cursor()
            
            analysis = {
                "available": True,
                "path": str(wal_path),
                "size_bytes": wal_path.stat().st_size
            }
            
            # Count events
            cursor.execute("SELECT COUNT(*) FROM wal_events")
            analysis['total_events'] = cursor.fetchone()[0]
            
            # Events by status
            cursor.execute("""
                SELECT status, COUNT(*) 
                FROM wal_events 
                GROUP BY status
            """)
            analysis['events_by_status'] = dict(cursor.fetchall())
            
            # Events by repo
            cursor.execute("""
                SELECT repo_name, COUNT(*) 
                FROM wal_events 
                GROUP BY repo_name
            """)
            analysis['events_by_repo'] = dict(cursor.fetchall())
            
            # Recent events
            cursor.execute("""
                SELECT timestamp, repo_name, event_type, action, phi_delta
                FROM wal_events
                ORDER BY timestamp DESC
                LIMIT 10
            """)
            analysis['recent_events'] = [
                {
                    "timestamp": row[0],
                    "repo": row[1],
                    "type": row[2],
                    "action": row[3],
                    "phi_delta": row[4]
                }
                for row in cursor.fetchall()
            ]
            
            # Total φ impact
            cursor.execute("SELECT SUM(phi_delta) FROM wal_events")
            result = cursor.fetchone()
            analysis['total_phi_impact'] = result[0] if result[0] is not None else 0.0
            
            conn.close()
            
            return analysis
            
        except Exception as e:
            logger.error(f"Failed to analyze WAL: {e}")
            return {"available": False, "error": str(e)}
    
    def generate_dashboard_markdown(self) -> str:
        """
        Generate Markdown dashboard.
        
        Returns:
            Markdown formatted dashboard
        """
        ecos_data = self.load_ecos_root()
        
        if not ecos_data:
            return "# Error: ECOS_ROOT.json not found\n"
        
        timestamp = datetime.utcnow().isoformat() + 'Z'
        
        dashboard = f"""# Ecosystem-1 Metrics Dashboard

**Generated**: {timestamp}  
**Ecosystem ID**: {ecos_data.get('ecosystem_id', 'unknown')}  
**Manifest Version**: {ecos_data.get('manifest_version', 'unknown')}

---

## 🎯 φ-CPS Evolution

"""
        
        # φ-CPS Analysis
        phi_analysis = self.analyze_phi_cps_evolution(ecos_data)
        
        dashboard += f"""
**Genesis**: {phi_analysis['phi_genesis']:.4f}  
**Current**: {phi_analysis['phi_current']:.4f}  
**Δφ Total**: +{phi_analysis['delta_total']:.4f} ({phi_analysis['delta_percent']:.2f}%)  
**Drift Status**: {'✅ ACCEPTABLE' if phi_analysis['drift_acceptable'] else '⚠️ THRESHOLD EXCEEDED'}

### Per-Repository φ-CPS

| Repository | φ-CPS | Δφ Total | Status |
|------------|-------|----------|--------|
"""
        
        for repo in phi_analysis['repos']:
            status = "✅" if abs(repo['phi_delta']) < 0.05 else "⚠️"
            dashboard += f"| {repo['name']} | {repo['phi_cps']:.4f} | +{repo['phi_delta']:.4f} | {status} |\n"
        
        dashboard += f"""

**Statistics**:
- Average: {phi_analysis.get('phi_avg', 0):.4f}
- Range: {phi_analysis.get('phi_min', 0):.4f} - {phi_analysis.get('phi_max', 0):.4f} ({phi_analysis.get('phi_range', 0):.4f})

---

## 📊 Repository Metrics

"""
        
        # Collect repo metrics
        repos = ecos_data.get('repositories', [])
        total_commits = 0
        active_repos = 0
        
        dashboard += "| Repository | Role | Status | Commits | Last 7d | Files |\n"
        dashboard += "|------------|------|--------|---------|---------|-------|\n"
        
        for repo in repos:
            metrics = self.collect_repo_metrics(repo)
            
            if metrics.get('exists', False):
                active_repos += 1
                commits = metrics.get('commit_count', 0)
                total_commits += commits
                recent = metrics.get('commits_last_7_days', 0)
                files = metrics.get('file_count', 0)
                
                dashboard += f"| {metrics['name']} | {metrics['role']} | {metrics['status']} | {commits} | {recent} | {files} |\n"
            else:
                dashboard += f"| {metrics['name']} | {metrics['role']} | NOT FOUND | - | - | - |\n"
        
        dashboard += f"""

**Totals**:
- Active Repositories: {active_repos}/{len(repos)}
- Total Commits: {total_commits}

---

## 🔗 WAL Database Analysis

"""
        
        wal_analysis = self.analyze_wal_integrity()
        
        if wal_analysis.get('available'):
            dashboard += f"""
**Status**: ✅ OPERATIONAL  
**Path**: `{wal_analysis['path']}`  
**Size**: {wal_analysis['size_bytes']:,} bytes  
**Total Events**: {wal_analysis['total_events']}  
**Total φ Impact**: +{wal_analysis['total_phi_impact']:.4f}

### Events by Status

"""
            for status, count in wal_analysis.get('events_by_status', {}).items():
                dashboard += f"- {status}: {count}\n"
            
            dashboard += "\n### Events by Repository\n\n"
            for repo, count in wal_analysis.get('events_by_repo', {}).items():
                dashboard += f"- {repo}: {count}\n"
            
            dashboard += "\n### Recent Events (Last 10)\n\n"
            dashboard += "| Timestamp | Repo | Type | Action | Δφ |\n"
            dashboard += "|-----------|------|------|--------|-----|\n"
            
            for event in wal_analysis.get('recent_events', []):
                dashboard += f"| {event['timestamp'][:19]} | {event['repo']} | {event['type']} | {event['action']} | +{event['phi_delta']:.4f} |\n"
        else:
            dashboard += "**Status**: ❌ NOT AVAILABLE\n"
            if 'error' in wal_analysis:
                dashboard += f"**Error**: {wal_analysis['error']}\n"
        
        dashboard += """

---

## 📈 Global Metrics Summary

"""
        
        global_metrics = ecos_data.get('global_metrics', {})
        
        dashboard += f"""
| Metric | Value |
|--------|-------|
| Total Repositories | {global_metrics.get('total_repositories', 0)} |
| Active Repositories | {global_metrics.get('active_repositories', 0)} |
| Total Commits | {global_metrics.get('total_commits', 0)} |
| Open Issues | {global_metrics.get('total_open_issues', 0)} |
| Closed Issues | {global_metrics.get('total_closed_issues', 0)} |
| Cumulative Δφ | +{global_metrics.get('cumulative_phi_delta', 0):.4f} |
| Average φ-CPS | {global_metrics.get('avg_phi_cps', 0):.4f} |

---

**Dashboard Generated by**: ECOS-AUTO Metrics Dashboard  
**Mode**: H0 Autonomous  
**Last Updated**: {ecos_data.get('last_updated', 'unknown')}
"""
        
        return dashboard
    
    def generate_dashboard_json(self) -> Dict[str, Any]:
        """
        Generate JSON dashboard data.
        
        Returns:
            Dict with dashboard metrics
        """
        ecos_data = self.load_ecos_root()
        
        return {
            "generated_at": datetime.utcnow().isoformat() + 'Z',
            "ecosystem_id": ecos_data.get('ecosystem_id', 'unknown'),
            "phi_cps_analysis": self.analyze_phi_cps_evolution(ecos_data),
            "wal_analysis": self.analyze_wal_integrity(),
            "global_metrics": ecos_data.get('global_metrics', {}),
            "repositories": [
                self.collect_repo_metrics(repo)
                for repo in ecos_data.get('repositories', [])
            ]
        }


def main():
    """
    CLI entry point for dashboard generator.
    """
    parser = argparse.ArgumentParser(
        description="Generate ecosystem-1 metrics dashboard"
    )
    parser.add_argument(
        '--root',
        type=str,
        default='..',
        help='Root directory containing all repos (default: ..)'
    )
    parser.add_argument(
        '--ecos-root',
        type=str,
        default='ECOS_ROOT.json',
        help='Path to ECOS_ROOT.json (default: ECOS_ROOT.json)'
    )
    parser.add_argument(
        '--format',
        type=str,
        choices=['markdown', 'json'],
        default='markdown',
        help='Output format (default: markdown)'
    )
    parser.add_argument(
        '--output',
        type=str,
        help='Output file (default: stdout)'
    )
    
    args = parser.parse_args()
    
    dashboard = EcosystemMetricsDashboard(
        Path(args.root),
        Path(args.ecos_root)
    )
    
    if args.format == 'markdown':
        output = dashboard.generate_dashboard_markdown()
    else:
        output = json.dumps(dashboard.generate_dashboard_json(), indent=2)
    
    if args.output:
        with open(args.output, 'w') as f:
            f.write(output)
        logger.info(f"Dashboard written to {args.output}")
    else:
        print(output)


if __name__ == '__main__':
    main()
