# KIVA-CLI Architecture

## Overview

KIVA-CLI is a project and application orchestration CLI built on Base-3 ternary logic with φ-CPS global coherence validation. It follows the Gateway pattern to delegate specialized operations to ECOS ecosystem CLIs.

## System Architecture

```
┌────────────────────────────────┐
│         KIVA CLI                 │
│  (Project & App Orchestration)  │
└──────────┬─────────────────────┘
           │
           │ Gateway Delegation
           │
    ┌──────┼──────┐
    │           │       │
┌───┴───┐  ┌──┴───┐  ┌─┴───┐
│ ECOS  │  │ BRAIN │  │FLUENCE│
│  CLI  │  │  CLI  │  │ CLI  │
└───────┘  └───────┘  └───────┘
```

## Components

### ProjectManager

**Responsibilities**:
- Initialize projects from templates
- List projects in workspace
- Validate project configurations
- Manage project metadata (kiva.json)

**Operations**:
- `init_project()`: Create new project from template
- `list_projects()`: Enumerate projects in workspace
- `validate_project()`: Base-3 validation of config
- `list_templates()`: Show available templates

**State Flow**:
```
PENDING → [Initialize] → SUCCESS/FAILED
```

### DeploymentManager

**Responsibilities**:
- Execute deployments to target environments
- Manage deployment lifecycle
- Rollback failed deployments
- Track deployment history

**Operations**:
- `deploy()`: Execute deployment strategy
- `rollback()`: Revert to previous version
- `list_deployments()`: Query deployment history
- `get_deployment()`: Fetch deployment details

**State Flow**:
```
PENDING → [Deploy] → SUCCESS/FAILED
SUCCESS → [Rollback] → SUCCESS/FAILED
```

### TemplateRegistry

**Responsibilities**:
- Register and manage project templates
- Provide template scaffolding
- Support custom template registration

**Built-in Templates**:
- **FastAPI**: Python REST API with SQLAlchemy
- **React**: TypeScript SPA with Vite
- **Go Service**: Microservice with Gin framework
- **Rust Service**: Async service with Actix-Web

**Template Structure**:
```python
Template(
    name: str,
    language: str,
    framework: Optional[str],
    files: Dict[str, str],  # path -> content
    dependencies: List[str],
    scripts: Dict[str, str],
    env_vars: List[str],
    docker_support: bool,
    ci_cd_support: bool,
)
```

### ConfigValidator

**Responsibilities**:
- Validate project configurations
- Validate deployment manifests
- Provide Base-3 validation results

**Validation States** (Base-3 Extended):
- **UNKNOWN** (0.0): Cannot determine validity
- **VALID** (0.5): Valid with warnings
- **VALID** (1.0): Fully valid, no warnings
- **INVALID** (1.0): Failed validation

**Schemas**:
- Project: `name`, `version`, `template` (required)
- Deployment: `environment`, `target`, `strategy` (required)

## Base-3 State Machine

### States

```python
Status = Literal["PENDING", "SUCCESS", "FAILED"]

PENDING  = 0  # Operation queued or in progress
SUCCESS  = 1  # Operation completed successfully
FAILED   = 2  # Operation encountered error
```

### Transition Rules

```
INIT → PENDING
PENDING → SUCCESS (on success)
PENDING → FAILED (on error)
FAILED → PENDING (on retry, max 2x)
```

### Return Format

All operations return:
```python
{
    "status": "SUCCESS | FAILED | PENDING",
    "data": {...},  # Operation-specific data
    "phi_delta": float,  # φ-CPS contribution
    "intent_hash": str,  # IntentHash¹¹
    "error": str,  # Only on FAILED
}
```

## φ-CPS Validation

### Formula

φ_post = φ_pre + Σ(semantic_weight × confidence)

Where:
- **φ_pre**: Previous coherence score (baseline: 4.092)
- **semantic_weight**: Operation complexity (0.001-0.01)
- **confidence**: Success probability (0.0-1.0)

### Weights by Operation

| Operation | Semantic Weight |
|-----------|----------------|
| project_init | 0.002 |
| deployment_execute | 0.005 |
| deployment_rollback | 0.003 |
| validate_config | 0.001 |

### Thresholds

- **Alert**: Δφ > 0.05 (5% drift)
- **Critical**: Δφ > 0.10 (10% drift)
- **Action**: Auto-rollback on critical

### Tracking

Every operation:
1. Calculates `phi_delta`
2. Appends to Global WAL (via ECOS Gateway)
3. Validates against threshold
4. Triggers rollback if breach detected

## ECOS Gateway Integration

### Delegation Pattern

```python
def _delegate_to_ecos_gateway(
    action: str,
    payload: Dict[str, Any],
) -> Optional[str]:
    """Delegate operation to ECOS Gateway."""
    cmd = [
        "ecos-cli",
        "gateway",
        "delegate",
        "--source", "kiva-cli",
        "--action", action,
        "--payload", json.dumps(payload),
    ]
    result = subprocess.run(cmd, capture_output=True, timeout=60)
    return result.intent_hash if result.returncode == 0 else None
```

### Delegated Actions

- `project_init`: Track project creation in Global WAL
- `deployment_execute`: Record deployment in ECOS_ROOT
- `deployment_rollback`: Log rollback event

### Fallback Strategy

If ECOS Gateway unavailable:
1. Log warning
2. Continue operation (graceful degradation)
3. Return `None` for `intent_hash`
4. Skip WAL tracking

## Error Handling

### Retry Policy

- **Max Retries**: 2
- **Strategy**: Exponential backoff
- **Base Delay**: 1 second
- **Max Delay**: 10 seconds

### Conflict Resolution

- **Git Conflicts**: Apply "ours" strategy
- **Test Failures**: Retry 2x, then skip with WARNING
- **Rate Limits**: Switch to Browser Comet (not implemented in phase 1A)

### Logging

- **Level**: INFO (normal), WARNING (retries), ERROR (failures)
- **Destination**: stderr (console), Global WAL (ECOS Gateway)
- **Format**: JSON structured logs

## Security

### IntentHash¹¹

Cryptographic integrity for all operations:
```python
intent_hash = sha256(
    operation_type +
    timestamp +
    payload +
    phi_delta
).hexdigest()[:16]
```

### Permissions

- **File Creation**: User's filesystem permissions
- **Deployments**: Target environment credentials (not managed by KIVA)
- **ECOS Gateway**: Subprocess execution (requires `ecos-cli` in PATH)

## Performance

### Benchmarks (Phase 1A)

- `project_init`: <1s (template scaffolding)
- `list_projects`: <100ms (workspace scan)
- `deploy`: 2-5s (subprocess + validation)
- `validate_config`: <50ms (JSON schema check)

### Optimization Targets (Phase 1B)

- Template hot-reload: <200ms
- Multi-repo orchestration: <3s (parallel)
- Deployment health checks: <500ms/service

## Extension Points

### Custom Templates

```python
registry = TemplateRegistry()
registry.register(Template(
    name="custom-template",
    language="python",
    framework="Django",
    files={...},
    dependencies=[...],
))
```

### Custom Validators

```python
class CustomValidator(ConfigValidator):
    def validate_custom(self, config: Dict) -> ValidationResult:
        # Custom validation logic
        pass
```

### Gateway Plugins (Phase 1B)

Pluggable delegation backends:
- ECOS CLI (subprocess)
- HTTP API (REST)
- gRPC service
- Message queue (RabbitMQ)

## Testing Strategy

### Unit Tests

- **Scope**: Single function/class
- **Mocking**: All I/O (filesystem, subprocess)
- **Coverage**: >90% for core logic

### Integration Tests

- **Scope**: Multiple components
- **Fixtures**: Temporary workspace, mock ECOS CLI
- **Coverage**: >80% for workflows

### E2E Tests (Phase 1B)

- **Scope**: Full CLI invocation
- **Environment**: Docker container
- **Scenarios**: Real projects, actual deployments

## Future Enhancements

### Phase 1B

- Multi-repo orchestration
- Template hot-reload from GitHub
- Deployment health monitoring
- Rollback history visualization (web UI)

### Phase 2

- Kubernetes native integration
- Terraform provider
- GitOps workflows (Flux, ArgoCD)
- Observability dashboard (Grafana)

### Phase 3

- AI-powered error diagnosis
- Auto-scaling based on φ-CPS drift
- Predictive rollback triggers
- Multi-cloud orchestration
