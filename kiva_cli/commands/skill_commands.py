#!/usr/bin/env python3
"""CLI commands for SkillManager.

Provides:
- ecos skill register: Register new skill
- ecos skill execute: Execute skill with parameters
- ecos skill validate: Validate skill with test cases
- ecos skill list: List skills with filters
- ecos skill export: Export skill registry
- ecos skill link: Link skill to citizen
- ecos skill info: Show skill details
- ecos skill delete: Archive skill
"""

import click
import json
import sys
from pathlib import Path
from typing import Optional
from tabulate import tabulate

# Add parent directory to path

from kiva_cli.core.skill_manager import SkillManager


@click.group(name="skill")
def skill_cli():
    """SkillManager commands - Reusable capability registry."""
    pass


@skill_cli.command(name="register")
@click.option("--name", required=True, help="Skill name (unique)")
@click.option("--type", "skill_type", required=True, 
              type=click.Choice(["PYTHON_SCRIPT", "POWERSHELL_SCRIPT", "BASH_SCRIPT", "API_CALL", "WORKFLOW", "FUNCTION", "CLI_COMMAND"]),
              help="Skill type")
@click.option("--script-path", help="Path to script file")
@click.option("--description", help="Skill description")
@click.option("--metadata", help="Metadata as JSON string")
@click.option("--input-schema", help="Input schema as JSON string")
@click.option("--output-schema", help="Output schema as JSON string")
@click.option("--dependencies", help="Comma-separated skill IDs")
def register_skill(
    name: str,
    skill_type: str,
    script_path: Optional[str],
    description: Optional[str],
    metadata: Optional[str],
    input_schema: Optional[str],
    output_schema: Optional[str],
    dependencies: Optional[str]
):
    """Register new skill in SkillManager.
    
    Example:
        ecos skill register --name deploy-docker --type PYTHON_SCRIPT \\
            --script-path scripts/deploy_docker.py \\
            --description "Deploy to Docker" \\
            --metadata '{"version": "1.0.0"}'
    """
    manager = SkillManager()
    
    try:
        # Parse JSON fields
        metadata_dict = json.loads(metadata) if metadata else None
        input_schema_dict = json.loads(input_schema) if input_schema else None
        output_schema_dict = json.loads(output_schema) if output_schema else None
        dependencies_list = dependencies.split(",") if dependencies else None
        
        skill_id = manager.register_skill(
            name=name,
            skill_type=skill_type,
            script_path=script_path,
            description=description,
            metadata=metadata_dict,
            input_schema=input_schema_dict,
            output_schema=output_schema_dict,
            dependencies=dependencies_list
        )
        
        click.echo(f"✅ Skill registered successfully")
        click.echo(f"   Skill ID: {skill_id}")
        click.echo(f"   Name: {name}")
        click.echo(f"   Type: {skill_type}")
        click.echo(f"   Validation: UNKNOWN (run 'ecos skill validate {skill_id}' to validate)")
    
    except json.JSONDecodeError as e:
        click.echo(f"❌ Error: Invalid JSON in metadata/schema: {e}", err=True)
        sys.exit(1)
    
    except ValueError as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)


@skill_cli.command(name="execute")
@click.argument("skill_id")
@click.option("--params", help="Execution parameters as JSON string")
@click.option("--mode", default="safe", type=click.Choice(["safe", "unsafe", "dry-run"]),
              help="Execution mode (default: safe)")
def execute_skill(skill_id: str, params: Optional[str], mode: str):
    """Execute skill with given parameters.
    
    Example:
        ecos skill execute skl_abc123 --params '{"target": "production"}'
    """
    manager = SkillManager()
    
    try:
        params_dict = json.loads(params) if params else {}
        
        if mode == "dry-run":
            skill = manager.get_skill(skill_id)
            if not skill:
                click.echo(f"❌ Skill not found: {skill_id}", err=True)
                sys.exit(1)
            
            click.echo(f"🔍 Dry-run mode: Would execute skill '{skill['name']}'")
            click.echo(f"   Type: {skill['skill_type']}")
            click.echo(f"   Script: {skill['script_path']}")
            click.echo(f"   Parameters: {json.dumps(params_dict, indent=2)}")
            return
        
        click.echo(f"⏳ Executing skill {skill_id}...")
        result = manager.execute_skill(skill_id, params_dict, mode=mode)
        
        if result["status"] == "SUCCESS":
            click.echo(f"✅ Execution successful")
            click.echo(f"   Execution ID: {result['execution_id']}")
            click.echo(f"   Duration: {result['duration_ms']}ms")
            if result["output"]:
                click.echo(f"   Output:\n{result['output']}")
        else:
            click.echo(f"❌ Execution failed", err=True)
            click.echo(f"   Error: {result['error']}", err=True)
            sys.exit(1)
    
    except json.JSONDecodeError as e:
        click.echo(f"❌ Error: Invalid JSON in params: {e}", err=True)
        sys.exit(1)
    
    except ValueError as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)


@skill_cli.command(name="validate")
@click.argument("skill_id")
@click.option("--test-cases", help="Test cases as JSON string (array of {input, expected})")
def validate_skill(skill_id: str, test_cases: Optional[str]):
    """Validate skill with test cases.
    
    Example:
        ecos skill validate skl_abc123 --test-cases '[{"input": {}, "expected": "success"}]'
    """
    manager = SkillManager()
    
    try:
        test_cases_list = json.loads(test_cases) if test_cases else None
        
        click.echo(f"⏳ Validating skill {skill_id}...")
        validation_state, phi_cps = manager.validate_skill(skill_id, test_cases_list)
        
        if validation_state == "VALID":
            click.echo(f"✅ Skill validated successfully")
        elif validation_state == "INVALID":
            click.echo(f"❌ Skill validation failed", err=True)
        else:
            click.echo(f"⚠️  Skill validation: {validation_state}")
        
        click.echo(f"   Validation state: {validation_state}")
        click.echo(f"   φ-CPS: {phi_cps:.3f}")
        click.echo(f"   Test cases: {len(test_cases_list) if test_cases_list else 0}")
    
    except json.JSONDecodeError as e:
        click.echo(f"❌ Error: Invalid JSON in test-cases: {e}", err=True)
        sys.exit(1)
    
    except ValueError as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)


@skill_cli.command(name="list")
@click.option("--type", "skill_type", help="Filter by skill type")
@click.option("--validation", "validation_state", help="Filter by validation state")
@click.option("--lifecycle", "lifecycle_state", help="Filter by lifecycle state")
@click.option("--limit", type=int, help="Maximum number of results")
@click.option("--format", "output_format", default="table", type=click.Choice(["table", "json"]),
              help="Output format (default: table)")
def list_skills(
    skill_type: Optional[str],
    validation_state: Optional[str],
    lifecycle_state: Optional[str],
    limit: Optional[int],
    output_format: str
):
    """List skills with optional filters.
    
    Example:
        ecos skill list --type PYTHON_SCRIPT --validation VALID
    """
    manager = SkillManager()
    
    skills = manager.list_skills(
        skill_type=skill_type,
        validation_state=validation_state,
        lifecycle_state=lifecycle_state,
        limit=limit
    )
    
    if not skills:
        click.echo("No skills found.")
        return
    
    if output_format == "json":
        click.echo(json.dumps(skills, indent=2))
    else:
        # Table format
        headers = ["Skill ID", "Name", "Type", "Validation", "Lifecycle", "Executions", "φ-CPS"]
        rows = []
        for skill in skills:
            rows.append([
                skill["skill_id"][:12] + "...",
                skill["name"],
                skill["skill_type"],
                skill["validation_state"],
                skill["lifecycle_state"],
                f"{skill['success_count']}/{skill['execution_count']}",
                f"{skill['phi_cps']:.3f}"
            ])
        
        click.echo(tabulate(rows, headers=headers, tablefmt="grid"))
        click.echo(f"\nTotal: {len(skills)} skill(s)")


@skill_cli.command(name="export")
@click.argument("output_path")
@click.option("--format", "export_format", default="json", type=click.Choice(["json", "csv"]),
              help="Export format (default: json)")
def export_registry(output_path: str, export_format: str):
    """Export skill registry to file.
    
    Example:
        ecos skill export skills_registry.json
        ecos skill export skills_registry.csv --format csv
    """
    manager = SkillManager()
    
    try:
        manager.export_registry(output_path, format=export_format)
        click.echo(f"✅ Skill registry exported to {output_path}")
    
    except ValueError as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)


@skill_cli.command(name="link")
@click.argument("skill_id")
@click.argument("citizen_id")
def link_to_citizen(skill_id: str, citizen_id: str):
    """Link skill to citizen entity.
    
    Example:
        ecos skill link skl_abc123 ctz_def456
    """
    manager = SkillManager()
    
    try:
        manager.link_to_citizen(skill_id, citizen_id)
        click.echo(f"✅ Skill {skill_id} linked to citizen {citizen_id}")
    
    except ValueError as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)


@skill_cli.command(name="info")
@click.argument("skill_id")
def show_skill_info(skill_id: str):
    """Show detailed skill information.
    
    Example:
        ecos skill info skl_abc123
    """
    manager = SkillManager()
    
    skill = manager.get_skill(skill_id)
    if not skill:
        click.echo(f"❌ Skill not found: {skill_id}", err=True)
        sys.exit(1)
    
    click.echo(f"📋 Skill Information")
    click.echo(f"   ID: {skill['skill_id']}")
    click.echo(f"   Name: {skill['name']}")
    click.echo(f"   Type: {skill['skill_type']}")
    click.echo(f"   Validation: {skill['validation_state']}")
    click.echo(f"   Lifecycle: {skill['lifecycle_state']}")
    click.echo(f"   φ-CPS: {skill['phi_cps']:.3f}")
    click.echo(f"   Script Path: {skill['script_path'] or 'N/A'}")
    click.echo(f"   Description: {skill['description'] or 'N/A'}")
    click.echo(f"   Executions: {skill['success_count']}/{skill['execution_count']}")
    click.echo(f"   Linked Citizen: {skill['linked_citizen_id'] or 'None'}")
    click.echo(f"   Created: {skill['created_at']}")
    click.echo(f"   Updated: {skill['updated_at']}")
    
    if skill['metadata']:
        click.echo(f"   Metadata: {skill['metadata']}")
    
    if skill['dependencies']:
        click.echo(f"   Dependencies: {skill['dependencies']}")


@skill_cli.command(name="delete")
@click.argument("skill_id")
@click.option("--confirm", is_flag=True, help="Skip confirmation prompt")
def delete_skill(skill_id: str, confirm: bool):
    """Archive skill (soft delete).
    
    Example:
        ecos skill delete skl_abc123 --confirm
    """
    manager = SkillManager()
    
    skill = manager.get_skill(skill_id)
    if not skill:
        click.echo(f"❌ Skill not found: {skill_id}", err=True)
        sys.exit(1)
    
    if not confirm:
        click.confirm(f"Archive skill '{skill['name']}'?", abort=True)
    
    # Archive by setting lifecycle to ARCHIVED
    import sqlite3
    from datetime import datetime
    
    conn = sqlite3.connect(manager.db_path)
    cursor = conn.cursor()
    
    cursor.execute("""
        UPDATE skills 
        SET lifecycle_state = 'ARCHIVED',
            updated_at = ?
        WHERE skill_id = ?
    """, (datetime.utcnow().isoformat(), skill_id))
    
    conn.commit()
    conn.close()
    
    # Log to WAL
    manager.wal_manager.append_event(
        operation="SKILL_ARCHIVE",
        repository=f"skill:{skill['name']}",
        phi_cps_delta=-0.003,
        metadata={"skill_id": skill_id}
    )
    
    click.echo(f"✅ Skill {skill_id} archived successfully")
