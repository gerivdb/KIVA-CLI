# KIVA-CLI API Reference

## ProjectManager

### `init_project()`

Initialize new project from template.

**Signature**:
```python
def init_project(
    name: str,
    template: str,
    path: Optional[Path] = None,
    **kwargs: Any,
) -> Dict[str, Any]
```

**Parameters**:
- `name` (str): Project name (lowercase, alphanumeric + hyphens)
- `template` (str): Template identifier (fastapi, react, go-service, rust-service)
- `path` (Path, optional): Target directory (defaults to `workspace_root/name`)
- `**kwargs`: Additional config (description, author, license)

**Returns**:
```python
{
    "status": "SUCCESS | FAILED",
    "project_path": str,
    "template": str,
    "files_created": int,
    "intent_hash": str,
    "phi_delta": float,
}
```

**Example**:
```python
manager = ProjectManager()
result = manager.init_project(
    name="my-api",
    template="fastapi",
    description="My REST API",
    author="John Doe",
)
assert result["status"] == "SUCCESS"
```

---

### `list_projects()`

List all projects in workspace.

**Signature**:
```python
def list_projects(
    workspace: Optional[Path] = None,
) -> Dict[str, Any]
```

**Parameters**:
- `workspace` (Path, optional): Workspace root (defaults to instance workspace)

**Returns**:
```python
{
    "status": "SUCCESS",
    "workspace": str,
    "projects": [
        {
            "name": str,
            "template": str,
            "version": str,
            "path": str,
            "created_at": str,
        },
        ...
    ],
    "total_count": int,
}
```

---

### `validate_project()`

Validate project configuration (Base-3).

**Signature**:
```python
def validate_project(path: Path) -> Dict[str, Any]
```

**Parameters**:
- `path` (Path): Project directory

**Returns**:
```python
{
    "status": "UNKNOWN | VALID | INVALID",
    "errors": List[str],
    "warnings": List[str],
    "confidence": float,  # 0.0, 0.5, or 1.0
    "path": str,
}
```

---

### `list_templates()`

List available project templates.

**Signature**:
```python
def list_templates() -> Dict[str, Any]
```

**Returns**:
```python
{
    "status": "SUCCESS",
    "templates": [
        {
            "name": str,
            "language": str,
            "framework": Optional[str],
            "description": str,
            "docker_support": bool,
            "ci_cd_support": bool,
        },
        ...
    ],
    "total_count": int,
}
```

---

## DeploymentManager

### `deploy()`

Execute deployment.

**Signature**:
```python
def deploy(
    project_path: Path,
    environment: str,
    target: str,
    strategy: str = "rolling",
    **kwargs: Any,
) -> Dict[str, Any]
```

**Parameters**:
- `project_path` (Path): Project directory
- `environment` (str): Environment (development, staging, production)
- `target` (str): Deployment target (k8s cluster, docker host)
- `strategy` (str): Strategy (rolling, blue-green, canary)
- `**kwargs`: Additional config (replicas, health_check)

**Returns**:
```python
{
    "status": "SUCCESS | FAILED",
    "deployment_id": str,
    "project_name": str,
    "environment": str,
    "strategy": str,
    "intent_hash": str,
    "phi_delta": float,
    "manifest_path": str,
}
```

---

### `rollback()`

Rollback deployment.

**Signature**:
```python
def rollback(deployment_id: str) -> Dict[str, Any]
```

**Parameters**:
- `deployment_id` (str): Deployment identifier (8-char UUID prefix)

**Returns**:
```python
{
    "status": "SUCCESS | FAILED",
    "rollback_id": str,
    "deployment_id": str,
    "project_name": str,
    "environment": str,
    "intent_hash": str,
    "phi_delta": float,
}
```

---

### `list_deployments()`

List deployments with optional filters.

**Signature**:
```python
def list_deployments(
    environment: Optional[str] = None,
    project_name: Optional[str] = None,
) -> Dict[str, Any]
```

**Parameters**:
- `environment` (str, optional): Filter by environment
- `project_name` (str, optional): Filter by project

**Returns**:
```python
{
    "status": "SUCCESS",
    "deployments": [
        {
            "deployment_id": str,
            "project_name": str,
            "environment": str,
            "strategy": str,
            "status": str,
            "created_at": str,
        },
        ...
    ],
    "total_count": int,
    "filters": {"environment": str, "project_name": str},
}
```

---

### `get_deployment()`

Get deployment details.

**Signature**:
```python
def get_deployment(deployment_id: str) -> Dict[str, Any]
```

**Parameters**:
- `deployment_id` (str): Deployment identifier

**Returns**:
```python
{
    "status": "SUCCESS | FAILED",
    "deployment": {
        "deployment_id": str,
        "project_name": str,
        "environment": str,
        "target": str,
        "strategy": str,
        "replicas": int,
        "health_check": Optional[Dict],
        "created_at": str,
        "status": str,
    },
}
```

---

## TemplateRegistry

### `register()`

Register custom template.

**Signature**:
```python
def register(template: Template) -> None
```

**Parameters**:
- `template` (Template): Template object

---

### `get()`

Retrieve template by name.

**Signature**:
```python
def get(name: str) -> Optional[Template]
```

**Parameters**:
- `name` (str): Template identifier

**Returns**:
- `Template` or `None`

---

### `list_templates()`

List all template names.

**Signature**:
```python
def list_templates() -> List[str]
```

**Returns**:
- List of template names

---

## ConfigValidator

### `validate_project()`

Validate project configuration.

**Signature**:
```python
def validate_project(config: Dict[str, Any]) -> ValidationResult
```

**Parameters**:
- `config` (dict): Project configuration

**Returns**:
```python
ValidationResult(
    status: str,  # UNKNOWN, VALID, INVALID
    errors: List[str],
    warnings: List[str],
    confidence: float,  # 0.0, 0.5, 1.0
)
```

---

### `validate_deployment()`

Validate deployment manifest.

**Signature**:
```python
def validate_deployment(config: Dict[str, Any]) -> ValidationResult
```

**Parameters**:
- `config` (dict): Deployment configuration

**Returns**:
- `ValidationResult` (same structure as `validate_project`)

---

### `validate_file()`

Validate configuration file.

**Signature**:
```python
def validate_file(
    path: Path,
    schema_type: str = "project",
) -> ValidationResult
```

**Parameters**:
- `path` (Path): Configuration file path
- `schema_type` (str): Schema type (project, deployment)

**Returns**:
- `ValidationResult`

---

## CLI Commands

### `kiva project init`

```bash
kiva project init --name <name> --template <template> [OPTIONS]
```

**Options**:
- `--name` (required): Project name
- `--template` (required): Template identifier
- `--path`: Custom project path
- `--description`: Project description
- `--author`: Author name
- `--license`: License (default: MIT)
- `--workspace`: Workspace root

---

### `kiva project list`

```bash
kiva project list [--workspace <path>]
```

---

### `kiva project validate`

```bash
kiva project validate --path <path>
```

---

### `kiva project templates`

```bash
kiva project templates
```

---

### `kiva deploy`

```bash
kiva deploy --project-path <path> --environment <env> --target <target> [OPTIONS]
```

**Options**:
- `--project-path` (required): Project directory
- `--environment` (required): Environment (development, staging, production)
- `--target` (required): Deployment target
- `--strategy`: Strategy (rolling, blue-green, canary)
- `--replicas`: Replica count (default: 1)

---

### `kiva rollback`

```bash
kiva rollback --deployment-id <id>
```

---

### `kiva deployment list`

```bash
kiva deployment list [--environment <env>] [--project <name>]
```

---

### `kiva deployment get`

```bash
kiva deployment get --deployment-id <id>
```
