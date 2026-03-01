"""
CLI commands for PipelineManager operations
"""

import click
import json
from pathlib import Path
from tabulate import tabulate
from tools.core.pipeline_manager import (
    PipelineManager, PipelineType, StepType,
    ValidationState, LifecycleState, ExecutionState
)

@click.group()
def pipeline():
    """Pipeline workflow management commands"""
    pass

@pipeline.command()
@click.option('--name', required=True, help='Pipeline name')
@click.option('--type', 'pipeline_type', type=click.Choice(['SEQUENTIAL', 'PARALLEL', 'DAG', 'CONDITIONAL', 'LOOP', 'HYBRID']), required=True)
@click.option('--description', default='', help='Pipeline description')
def register(name: str, pipeline_type: str, description: str):
    """Register a new pipeline"""
    manager = PipelineManager()
    pipeline_id = manager.register_pipeline(
        name=name,
        pipeline_type=PipelineType[pipeline_type],
        description=description
    )
    click.echo(f"✅ Pipeline registered: {pipeline_id}")
    click.echo(f"   Name: {name}")
    click.echo(f"   Type: {pipeline_type}")

@pipeline.command()
@click.option('--pipeline-id', required=True, help='Pipeline ID')
@click.option('--name', required=True, help='Step name')
@click.option('--type', 'step_type', type=click.Choice([
    'SKILL_EXECUTION', 'DAEMON_START', 'API_CALL', 'SCRIPT_RUN',
    'VALIDATION', 'NOTIFICATION', 'CONDITION', 'TRANSFORM'
]), required=True)
@click.option('--config', default='{}', help='Step config (JSON string)')
@click.option('--order', default=0, type=int, help='Step order index')
@click.option('--max-retries', default=3, type=int)
@click.option('--timeout', default=300, type=int)
def add_step(pipeline_id: str, name: str, step_type: str, config: str, order: int, max_retries: int, timeout: int):
    """Add a step to a pipeline"""
    manager = PipelineManager()
    config_dict = json.loads(config)
    step_id = manager.add_step(
        pipeline_id=pipeline_id,
        name=name,
        step_type=StepType[step_type],
        config=config_dict,
        order_index=order,
        max_retries=max_retries,
        timeout_seconds=timeout
    )
    click.echo(f"✅ Step added: {step_id}")
    click.echo(f"   Pipeline: {pipeline_id}")
    click.echo(f"   Name: {name}")
    click.echo(f"   Type: {step_type}")

@pipeline.command()
@click.option('--pipeline-id', required=True)
@click.option('--from-step', required=True)
@click.option('--to-step', required=True)
@click.option('--condition', default=None)
def add_edge(pipeline_id: str, from_step: str, to_step: str, condition: str):
    """Add DAG edge between steps"""
    manager = PipelineManager()
    edge_id = manager.add_dag_edge(
        pipeline_id=pipeline_id,
        from_step_id=from_step,
        to_step_id=to_step,
        condition=condition
    )
    click.echo(f"✅ Edge added: {edge_id}")
    click.echo(f"   {from_step} → {to_step}")

@pipeline.command()
@click.option('--pipeline-id', required=True)
@click.option('--context', default='{}', help='Execution context (JSON)')
@click.option('--async/--sync', default=False)
def execute(pipeline_id: str, context: str, async_: bool):
    """Execute a pipeline"""
    manager = PipelineManager()
    context_dict = json.loads(context)
    execution_id = manager.execute_pipeline(
        pipeline_id=pipeline_id,
        context=context_dict,
        async_mode=async_
    )
    click.echo(f"✅ Pipeline execution started: {execution_id}")
    click.echo(f"   Mode: {'Async' if async_ else 'Sync'}")

@pipeline.command()
@click.option('--pipeline-id', required=True)
def validate(pipeline_id: str):
    """Validate pipeline configuration"""
    manager = PipelineManager()
    state = manager.validate_pipeline(pipeline_id)
    
    icons = {
        ValidationState.VALID: '✅',
        ValidationState.INVALID: '❌',
        ValidationState.UNKNOWN: '⚪'
    }
    
    click.echo(f"{icons[state]} Pipeline validation: {state.value}")

@pipeline.command()
@click.option('--type', 'pipeline_type', type=click.Choice(['SEQUENTIAL', 'PARALLEL', 'DAG', 'CONDITIONAL', 'LOOP', 'HYBRID']))
@click.option('--validation', type=click.Choice(['UNKNOWN', 'VALID', 'INVALID']))
@click.option('--lifecycle', type=click.Choice(['GENESIS', 'ACTIVE', 'DEPRECATED', 'ARCHIVED']))
def list(pipeline_type: str, validation: str, lifecycle: str):
    """List pipelines"""
    manager = PipelineManager()
    
    filters = {}
    if pipeline_type:
        filters['pipeline_type'] = PipelineType[pipeline_type]
    if validation:
        filters['validation_state'] = ValidationState[validation]
    if lifecycle:
        filters['lifecycle_state'] = LifecycleState[lifecycle]
    
    pipelines = manager.list_pipelines(**filters)
    
    if not pipelines:
        click.echo("No pipelines found")
        return
    
    table_data = []
    for p in pipelines:
        table_data.append([
            p['id'][:12],
            p['name'],
            p['type'],
            p['validation_state'],
            p['lifecycle_state'],
            p['execution_state'],
            f"{p['phi_cps']:.3f}"
        ])
    
    click.echo(tabulate(
        table_data,
        headers=['ID', 'Name', 'Type', 'Validation', 'Lifecycle', 'Execution', 'φ-CPS'],
        tablefmt='grid'
    ))

@pipeline.command()
@click.option('--execution-id', required=True)
def status(execution_id: str):
    """Get execution status"""
    manager = PipelineManager()
    status = manager.get_execution_status(execution_id)
    
    if not status:
        click.echo(f"❌ Execution {execution_id} not found")
        return
    
    state_icons = {
        'PENDING': '⚪',
        'RUNNING': '🔵',
        'SUCCESS': '✅',
        'FAILED': '❌',
        'CANCELLED': '⚠️',
        'ROLLED_BACK': '↩️'
    }
    
    icon = state_icons.get(status['execution_state'], '?')
    click.echo(f"{icon} Execution: {execution_id}")
    click.echo(f"   Pipeline: {status['pipeline_id']}")
    click.echo(f"   State: {status['execution_state']}")
    click.echo(f"   Started: {status['started_at']}")
    if status['completed_at']:
        click.echo(f"   Completed: {status['completed_at']}")
        click.echo(f"   Duration: {status['duration_ms']}ms")
    
    if status['steps']:
        click.echo(f"\n   Steps ({len(status['steps'])}):")
        for step in status['steps']:
            step_icon = state_icons.get(step['execution_state'], '?')
            click.echo(f"   {step_icon} {step['name']} ({step['execution_state']})")
