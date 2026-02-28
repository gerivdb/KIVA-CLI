#!/usr/bin/env python3
"""KIVA CLI - Project & Application Orchestration

Main CLI entrypoint for KIVA operations.
Delegates to ProjectManager and DeploymentManager.

Usage:
    kiva project init --template fastapi --name my-api
    kiva project list
    kiva deploy --environment staging --target k8s-cluster-1
    kiva rollback --deployment-id abc12345
"""

import sys
import json
import argparse
from pathlib import Path
from typing import Optional

from kiva_cli import __version__, __mode__
from kiva_cli.managers import ProjectManager, DeploymentManager


def cmd_project_init(args: argparse.Namespace) -> int:
    """Initialize new project from template."""
    manager = ProjectManager(workspace_root=args.workspace)
    
    result = manager.init_project(
        name=args.name,
        template=args.template,
        path=args.path,
        description=args.description,
        author=args.author,
        license=args.license,
    )
    
    print(json.dumps(result, indent=2))
    return 0 if result["status"] == "SUCCESS" else 1


def cmd_project_list(args: argparse.Namespace) -> int:
    """List projects in workspace."""
    manager = ProjectManager(workspace_root=args.workspace)
    
    result = manager.list_projects()
    
    print(json.dumps(result, indent=2))
    return 0


def cmd_project_validate(args: argparse.Namespace) -> int:
    """Validate project configuration."""
    manager = ProjectManager()
    
    result = manager.validate_project(args.path)
    
    print(json.dumps(result, indent=2))
    return 0 if result["status"] == "VALID" else 1


def cmd_project_templates(args: argparse.Namespace) -> int:
    """List available templates."""
    manager = ProjectManager()
    
    result = manager.list_templates()
    
    print(json.dumps(result, indent=2))
    return 0


def cmd_deploy(args: argparse.Namespace) -> int:
    """Execute deployment."""
    manager = DeploymentManager()
    
    result = manager.deploy(
        project_path=args.project_path,
        environment=args.environment,
        target=args.target,
        strategy=args.strategy,
        replicas=args.replicas,
    )
    
    print(json.dumps(result, indent=2))
    return 0 if result["status"] == "SUCCESS" else 1


def cmd_rollback(args: argparse.Namespace) -> int:
    """Rollback deployment."""
    manager = DeploymentManager()
    
    result = manager.rollback(deployment_id=args.deployment_id)
    
    print(json.dumps(result, indent=2))
    return 0 if result["status"] == "SUCCESS" else 1


def cmd_deployment_list(args: argparse.Namespace) -> int:
    """List deployments."""
    manager = DeploymentManager()
    
    result = manager.list_deployments(
        environment=args.environment,
        project_name=args.project,
    )
    
    print(json.dumps(result, indent=2))
    return 0


def cmd_deployment_get(args: argparse.Namespace) -> int:
    """Get deployment details."""
    manager = DeploymentManager()
    
    result = manager.get_deployment(deployment_id=args.deployment_id)
    
    print(json.dumps(result, indent=2))
    return 0 if result["status"] == "SUCCESS" else 1


def main() -> int:
    """Main CLI entrypoint."""
    parser = argparse.ArgumentParser(
        prog="kiva",
        description="KIVA CLI - Project & Application Orchestration",
        epilog=f"Version: {__version__} | Mode: {__mode__}",
    )
    parser.add_argument("--version", action="version", version=f"kiva {__version__}")
    
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # Project commands
    project_parser = subparsers.add_parser("project", help="Project management")
    project_subparsers = project_parser.add_subparsers(dest="subcommand")
    
    # project init
    init_parser = project_subparsers.add_parser("init", help="Initialize new project")
    init_parser.add_argument("--name", required=True, help="Project name")
    init_parser.add_argument("--template", required=True, help="Template name")
    init_parser.add_argument("--path", type=Path, help="Project path")
    init_parser.add_argument("--description", default="", help="Project description")
    init_parser.add_argument("--author", default="", help="Author name")
    init_parser.add_argument("--license", default="MIT", help="License")
    init_parser.add_argument("--workspace", type=Path, help="Workspace root")
    init_parser.set_defaults(func=cmd_project_init)
    
    # project list
    list_parser = project_subparsers.add_parser("list", help="List projects")
    list_parser.add_argument("--workspace", type=Path, help="Workspace root")
    list_parser.set_defaults(func=cmd_project_list)
    
    # project validate
    validate_parser = project_subparsers.add_parser("validate", help="Validate project")
    validate_parser.add_argument("--path", type=Path, required=True, help="Project path")
    validate_parser.set_defaults(func=cmd_project_validate)
    
    # project templates
    templates_parser = project_subparsers.add_parser("templates", help="List templates")
    templates_parser.set_defaults(func=cmd_project_templates)
    
    # Deploy command
    deploy_parser = subparsers.add_parser("deploy", help="Execute deployment")
    deploy_parser.add_argument("--project-path", type=Path, required=True, help="Project path")
    deploy_parser.add_argument("--environment", required=True, choices=["development", "staging", "production"], help="Environment")
    deploy_parser.add_argument("--target", required=True, help="Deployment target")
    deploy_parser.add_argument("--strategy", default="rolling", choices=["rolling", "blue-green", "canary"], help="Deployment strategy")
    deploy_parser.add_argument("--replicas", type=int, default=1, help="Number of replicas")
    deploy_parser.set_defaults(func=cmd_deploy)
    
    # Rollback command
    rollback_parser = subparsers.add_parser("rollback", help="Rollback deployment")
    rollback_parser.add_argument("--deployment-id", required=True, help="Deployment ID")
    rollback_parser.set_defaults(func=cmd_rollback)
    
    # Deployment commands
    deployment_parser = subparsers.add_parser("deployment", help="Deployment management")
    deployment_subparsers = deployment_parser.add_subparsers(dest="subcommand")
    
    # deployment list
    deployment_list_parser = deployment_subparsers.add_parser("list", help="List deployments")
    deployment_list_parser.add_argument("--environment", help="Filter by environment")
    deployment_list_parser.add_argument("--project", help="Filter by project name")
    deployment_list_parser.set_defaults(func=cmd_deployment_list)
    
    # deployment get
    deployment_get_parser = deployment_subparsers.add_parser("get", help="Get deployment details")
    deployment_get_parser.add_argument("--deployment-id", required=True, help="Deployment ID")
    deployment_get_parser.set_defaults(func=cmd_deployment_get)
    
    # Parse args
    args = parser.parse_args()
    
    if not hasattr(args, "func"):
        parser.print_help()
        return 1
    
    try:
        return args.func(args)
    except KeyboardInterrupt:
        print("\n[!] Interrupted by user", file=sys.stderr)
        return 130
    except Exception as e:
        print(f"[!] Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
