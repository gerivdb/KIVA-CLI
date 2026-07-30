#!/usr/bin/env python3
"""
IRIS - Investigateur en Récupération d'Informations Systémiques
Service de surveillance proactive des dépôts upstream.
"""

import asyncio
import aiohttp
import json
import yaml
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

# Configuration
IRIS_CONFIG = {
    "targets": [
        "superdesigndev/loopany-platform",
        "gerivdb/ECOYSTEM",
        "gerivdb/BRAIN"
    ],
    "poll_interval": 86400,  # 24h en secondes
    "github_token": None,  # À configurer via variable d'environnement
    "output_format": "MUD",
    "wal_path": "/wal/iris_signals"
}


class MudSignal:
    """Format MUD (Métadonnées Universelles de Déploiement)"""
    
    def __init__(self, repo: str):
        self.version = "1.0"
        self.timestamp = datetime.utcnow().isoformat() + "Z"
        self.source = "IRIS"
        self.repo = repo
        self.signals = {
            "commits": {"count": 0, "authors": [], "last_commit": None, "commit_velocity": 0.0},
            "releases": {"count": 0, "latest": None, "last_release": None, "release_frequency": 0.0},
            "issues": {"open": 0, "closed": 0, "created": None, "resolution_rate": 0.0},
            "pull_requests": {"open": 0, "merged": 0, "last_pr": None, "merge_rate": 0.0},
            "contributors": {"count": 0, "last_contributor": None, "contributor_growth": 0.0}
        }
        self.health_indicators = {
            "activity_score": 0.0,
            "stability_score": 0.0,
            "community_score": 0.0
        }
    
    def to_dict(self) -> Dict:
        return {
            "version": self.version,
            "timestamp": self.timestamp,
            "source": self.source,
            "repo": self.repo,
            "signals": self.signals,
            "health_indicators": self.health_indicators
        }


class IrisService:
    """Service IRIS pour la collecte des signaux GitHub"""
    
    def __init__(self, config: Dict = None):
        self.config = config or IRIS_CONFIG
        self.headers = {"Accept": "application/vnd.github.v3+json"}
        if self.config.get("github_token"):
            self.headers["Authorization"] = f"token {self.config['github_token']}"
    
    async def fetch_github_data(self, session: aiohttp.ClientSession, url: str) -> Optional[Dict]:
        """Fetch data from GitHub API with rate limiting handling"""
        try:
            async with session.get(url, headers=self.headers) as response:
                if response.status == 200:
                    return await response.json()
                elif response.status == 403:
                    print(f"[IRIS] Rate limit exceeded for {url}")
                    return None
                else:
                    print(f"[IRIS] Error {response.status} for {url}")
                    return None
        except Exception as e:
            print(f"[IRIS] Exception fetching {url}: {e}")
            return None
    
    async def collect_signals(self, repo: str) -> MudSignal:
        """Collect all signals for a repository"""
        signal = MudSignal(repo)
        owner, repo_name = repo.split("/")
        
        async with aiohttp.ClientSession() as session:
            # Fetch commits (last 30 days)
            commits_url = f"https://api.github.com/repos/{repo}/commits?per_page=100"
            commits = await self.fetch_github_data(session, commits_url)
            if commits:
                signal.signals["commits"]["count"] = len(commits)
                signal.signals["commits"]["authors"] = list(set(c["commit"]["author"]["name"] for c in commits if c.get("commit", {}).get("author")))
                if commits:
                    signal.signals["commits"]["last_commit"] = commits[0]["commit"]["author"]["date"]
            
            # Fetch releases
            releases_url = f"https://api.github.com/repos/{repo}/releases?per_page=10"
            releases = await self.fetch_github_data(session, releases_url)
            if releases:
                signal.signals["releases"]["count"] = len(releases)
                signal.signals["releases"]["latest"] = releases[0]["tag_name"] if releases else None
                signal.signals["releases"]["last_release"] = releases[0]["published_at"] if releases else None
            
            # Fetch issues
            issues_url = f"https://api.github.com/repos/{repo}/issues?state=all&per_page=100"
            issues = await self.fetch_github_data(session, issues_url)
            if issues:
                open_issues = [i for i in issues if i.get("state") == "open"]
                closed_issues = [i for i in issues if i.get("state") == "closed"]
                signal.signals["issues"]["open"] = len(open_issues)
                signal.signals["issues"]["closed"] = len(closed_issues)
            
            # Fetch pull requests
            prs_url = f"https://api.github.com/repos/{repo}/pulls?state=all&per_page=100"
            prs = await self.fetch_github_data(session, prs_url)
            if prs:
                open_prs = [p for p in prs if p.get("state") == "open"]
                merged_prs = [p for p in prs if p.get("merged_at")]
                signal.signals["pull_requests"]["open"] = len(open_prs)
                signal.signals["pull_requests"]["merged"] = len(merged_prs)
            
            # Fetch contributors
            contrib_url = f"https://api.github.com/repos/{repo}/contributors?per_page=10"
            contributors = await self.fetch_github_data(session, contrib_url)
            if contributors:
                signal.signals["contributors"]["count"] = len(contributors)
        
        # Calculate health indicators
        signal.health_indicators["activity_score"] = self._calculate_activity_score(signal)
        signal.health_indicators["stability_score"] = self._calculate_stability_score(signal)
        signal.health_indicators["community_score"] = self._calculate_community_score(signal)
        
        return signal
    
    def _calculate_activity_score(self, signal: MudSignal) -> float:
        """Calculate activity score based on commits and releases"""
        commits = signal.signals["commits"]["count"]
        releases = signal.signals["releases"]["count"]
        # Normalize: 0-100 commits = 0-1, 0-10 releases = 0-1
        activity = min((commits / 100) * 0.7 + (releases / 10) * 0.3, 1.0)
        return round(activity, 3)
    
    def _calculate_stability_score(self, signal: MudSignal) -> float:
        """Calculate stability score based on issue resolution"""
        open_issues = signal.signals["issues"]["open"]
        closed_issues = signal.signals["issues"]["closed"]
        total = open_issues + closed_issues
        if total == 0:
            return 0.5
        resolution_rate = closed_issues / total
        return round(resolution_rate, 3)
    
    def _calculate_community_score(self, signal: MudSignal) -> float:
        """Calculate community score based on contributors"""
        contributors = signal.signals["contributors"]["count"]
        # Normalize: 0-20 contributors = 0-1
        return round(min(contributors / 20, 1.0), 3)
    
    async def run(self):
        """Main IRIS service loop"""
        print(f"[IRIS] Starting service for {len(self.config['targets'])} targets")
        
        while True:
            for repo in self.config["targets"]:
                print(f"[IRIS] Collecting signals for {repo}")
                signal = await self.collect_signals(repo)
                
                # Output as JSON to stdout (for queue consumption)
                print(json.dumps(signal.to_dict()))
                
                # TODO: Write to NEXUS WAL
                # self._write_to_wal(signal)
            
            print(f"[IRIS] Sleeping for {self.config['poll_interval']} seconds")
            await asyncio.sleep(self.config["poll_interval"])


if __name__ == "__main__":
    service = IrisService()
    asyncio.run(service.run())