#!/usr/bin/env python3
"""KIVA-CLI main entry point.

ECOS-CLI unified command-line interface for:
- Project scaffolding (ProjectManager)
- Event tracking (GlobalWALManager)
- Entity lifecycle (CitizenManager)
- Skill registry (SkillManager)
- Script maturation (ScriptMaturationManager)
- Path resolution (PathResolver)
- Context management (ContextManager)
- Entity path mapping (EntityPathMapper)
- NEXUS governance (.nexus/ tracking per repo)
- Pipeline chain execution (KIVA-008)
- Branch Routing & Governance System (BRGS) audit
"""

import sys
from pathlib import Path
# Fix: ensure KIVA-CLI root is first in sys.path to avoid shadowing by NEXUS/tools
_kiva_root = str(Path(__file__).resolve().parent.parent)
# Remove any cached 'tools' module that may have been loaded from another path
for _mod in list(sys.modules.keys()):
    if _mod == 'tools' or _mod.startswith('tools.'):
        del sys.modules[_mod]
# Remove NEXUS and other conflicting paths that contain a 'tools' package
sys.path = [p for p in sys.path if 'NEXUS' not in p and 'L0-CANON' not in p]
if _kiva_root in sys.path:
    sys.path.remove(_kiva_root)
sys.path.insert(0, _kiva_root)

import click
from kiva_cli.commands.project_commands import project_cli
from kiva_cli.commands.wal_commands import wal_cli
from kiva_cli.commands.citizen_commands import citizen_cli
from kiva_cli.commands.skill_commands import skill_cli
from kiva_cli.commands.script_commands import script_cli
from kiva_cli.commands.path_commands import path_cli
from kiva_cli.commands.context_commands import context_cli
from kiva_cli.commands.explorer_commands import explorer_cli
from kiva_cli.commands.entity_commands import entity_cli
from kiva_cli.commands.repo_commands import repo_cli
from kiva_cli.commands.skill_discovery_commands import skill_discovery_cli
from kiva_cli.commands.skill_marketplace_commands import skill_market_cli
from kiva_cli.commands.phi_cps_commands import phi_cps_cli
from kiva_cli.commands.cicd_commands import cicd_cli
from kiva_cli.commands.security_commands import security_cli
from kiva_cli.commands.service_commands import service_cli
from kiva_cli.commands.autoscale_commands import autoscale_cli
from kiva_cli.commands.wal_dist_commands import wal_dist_cli
from kiva_cli.commands.cluster_commands import cluster_cli
from kiva_cli.commands.lxc_commands import lxc_cli
from kiva_cli.commands.dashboard_commands import dashboard_cli
from kiva_cli.commands.kvcache_commands import kvcache_cli
from kiva_cli.commands.tql import tql
from kiva_cli.commands.zvec_commands import zvec_cli
from kiva_cli.commands.epic_commands import epic_cli
from kiva_cli.commands.gate_command import gate_cli
from kiva_cli.commands.nexus_commands import nexus_cli
from kiva_cli.commands.pipeline_commands import pipeline_cli
from kiva_cli.commands.audit_commands import audit
from kiva_cli.commands.mc_rnn_ci import mc_rnn_ci
from kiva_cli.commands.merge_commands import merge_cli


@click.group()
@click.version_option(version="0.25.0", prog_name="KIVA-CLI")
def cli():
    """KIVA-CLI - ECOS unified command-line interface.

    Provides:
    - Project scaffolding and management
    - Event tracking (GlobalWALManager)
    - Entity lifecycle (CitizenManager)
    - Skill registry (SkillManager)
    - Script maturation (Skeleton -> Production)
    - Path resolution (local <-> remote)
    - Context management (active repo)
    - Windows Explorer integration
    - Entity path mapping
    - Repository discovery
    - Skill discovery & registration
    - Skill marketplace (install/update/remove)
    - phi-CPS analytics and drift detection
    - Merge gate (phi-CPS drift gate for all ECOS repos)
    - CI/CD integration and pipeline management
    - Security hardening and audit
    - Service discovery and management
    - Auto-scaling policy management
    - Distributed WAL management
    - Multi-host cluster management
    - LXC/LXD container orchestration
    - Web UI dashboard
    - KVCache integration
    - zvec vector database
    - EPIC-centric development mode
    - NEXUS governance (.nexus/ tracking per repo)
    - Pipeline chain execution (KIVA-008: DAG, on_failure, WAL, phi_delta)
    - Branch Routing & Governance System (BRGS) audit
    """
    pass


# Register command groups
cli.add_command(project_cli, name="project")
cli.add_command(wal_cli, name="wal")
cli.add_command(citizen_cli, name="citizen")
cli.add_command(skill_cli, name="skill")
cli.add_command(script_cli, name="script")
cli.add_command(path_cli, name="path")
cli.add_command(context_cli, name="context")
cli.add_command(explorer_cli, name="explorer")
cli.add_command(entity_cli, name="entity")
cli.add_command(repo_cli, name="repo")
cli.add_command(skill_discovery_cli, name="skill-discovery")
cli.add_command(skill_market_cli, name="skill-market")
cli.add_command(phi_cps_cli, name="phi-cps")
cli.add_command(gate_cli, name="gate")
cli.add_command(cicd_cli, name="cicd")
cli.add_command(security_cli, name="security")
cli.add_command(service_cli, name="service")
cli.add_command(autoscale_cli, name="autoscale")
cli.add_command(wal_dist_cli, name="wal-dist")
cli.add_command(cluster_cli, name="cluster")
cli.add_command(lxc_cli, name="lxc")
cli.add_command(dashboard_cli, name="dashboard")
cli.add_command(kvcache_cli, name="kvcache")
cli.add_command(tql, name="tql")
cli.add_command(zvec_cli, name="zvec")
cli.add_command(epic_cli, name="epic")
cli.add_command(nexus_cli, name="nexus")
cli.add_command(pipeline_cli, name="pipeline")
cli.add_command(audit, name='audit')
cli.add_command(mc_rnn_ci, name='mc-rnn-ci')
cli.add_command(merge_cli, name='merge')


def main():
    """Main entry point for KIVA-CLI"""
    cli()


if __name__ == "__main__":
    main()
