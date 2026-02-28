# Contributing to KIVA-CLI

Thank you for your interest in contributing to KIVA-CLI! This document provides guidelines and workflows for contributors.

## 📜 Table of Contents

- [Development Setup](#development-setup)
- [Coding Standards](#coding-standards)
- [Testing Guidelines](#testing-guidelines)
- [Commit Conventions](#commit-conventions)
- [Pull Request Process](#pull-request-process)
- [Base-3 Logic](#base-3-logic)
- [φ-CPS Validation](#φ-cps-validation)

## 🛠️ Development Setup

### Prerequisites

- Python 3.11 or higher
- pip
- git

### Local Setup

```bash
# Clone repository
git clone https://github.com/gerivdb/KIVA-CLI.git
cd KIVA-CLI

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in editable mode with dev dependencies
pip install -e ".[dev]"

# Verify installation
kiva --version
pytest --version
```

## 📝 Coding Standards

### Python Style

- **Formatter**: Black (line length: 88)
- **Linter**: Ruff (pycodestyle + pyflakes + isort)
- **Type Hints**: Required for public APIs
- **Docstrings**: Google style

```python
def example_function(param: str) -> Dict[str, Any]:
    """Short description.
    
    Longer description with details.
    
    Args:
        param: Description of parameter.
    
    Returns:
        Dict with status and data.
    
    Raises:
        ValueError: If param is invalid.
    """
    pass
```

### Code Organization

- **Modules**: One class per file (exceptions for small helpers)
- **Managers**: `kiva_cli/managers/` - Business logic
- **Core**: `kiva_cli/core/` - Utilities (templates, validation)
- **Tests**: Mirror source structure (`tests/unit/`, `tests/integration/`)

## 🧪 Testing Guidelines

### Test Categories

- **Unit Tests** (`@pytest.mark.unit`): Fast, no I/O, mock external dependencies
- **Integration Tests** (`@pytest.mark.integration`): Filesystem, subprocess, real scenarios

### Writing Tests

```python
import pytest
from kiva_cli.managers import ProjectManager

@pytest.mark.unit
def test_template_registry():
    """Test template retrieval."""
    manager = ProjectManager()
    templates = manager.list_templates()
    assert templates["status"] == "SUCCESS"
    assert len(templates["templates"]) >= 4

@pytest.mark.integration
def test_project_init(temp_workspace, mock_ecos_cli):
    """Test project initialization (integration)."""
    manager = ProjectManager(workspace_root=temp_workspace)
    result = manager.init_project(name="test", template="fastapi")
    assert result["status"] == "SUCCESS"
```

### Running Tests

```bash
# All tests
pytest

# Unit tests only
pytest -m unit

# Integration tests only
pytest -m integration

# With coverage
pytest --cov=kiva_cli --cov-report=html

# Specific file
pytest tests/unit/test_template_registry.py -v
```

### Coverage Requirements

- **Minimum**: 80% overall coverage
- **Target**: 90% for core modules
- **Exclusions**: CLI wrappers, external integrations (ECOS Gateway)

## 📝 Commit Conventions

### Format

```
[ECOS-AUTO] <type>(<scope>): <subject>

<body>

<footer>
```

### Types

- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation only
- `test`: Adding/updating tests
- `refactor`: Code restructuring
- `perf`: Performance improvement
- `chore`: Maintenance tasks

### Examples

```bash
[ECOS-AUTO] feat(managers): Add ProjectManager with template scaffolding

- Initialize projects from templates (FastAPI, React, Go, Rust)
- Create kiva.json config file
- Scaffold directory structure
- Integrate with ECOS Gateway for WAL tracking

IntentHash: 0xH1_KIVA_PROJECT_MANAGER_INIT
φ-CPS: +0.002

---

[ECOS-AUTO] fix(deployment): Handle missing health_check gracefully

Validation now treats health_check as optional with warning.

Closes: #42
```

## 🔀 Pull Request Process

### Before Submitting

1. **Run Tests**: Ensure all tests pass
   ```bash
   pytest
   ```

2. **Lint Code**: Fix all linting errors
   ```bash
   ruff check . && black --check .
   ```

3. **Update Docs**: Add/update relevant documentation

4. **Add Tests**: New features require tests (unit + integration)

### Submission

1. **Create Branch**: `feature/<name>` or `fix/<name>`
   ```bash
   git checkout -b feature/add-terraform-template
   ```

2. **Commit Changes**: Follow commit conventions
   ```bash
   git commit -m "[ECOS-AUTO] feat(templates): Add Terraform template"
   ```

3. **Push Branch**:
   ```bash
   git push origin feature/add-terraform-template
   ```

4. **Open PR**: Use PR template, link related issues

### Review Process

- **Automated Checks**: CI must pass (tests, linting, coverage)
- **Code Review**: At least one approval required
- **φ-CPS Validation**: Ensure delta < 0.05
- **Merge Strategy**: Squash and merge

## 🔺 Base-3 Logic

### State Machine

All operations return Base-3 states:

- **PENDING** (0): Queued or in progress
- **SUCCESS** (1): Completed successfully
- **FAILED** (2): Encountered error

### Implementation

```python
from typing import Literal

Status = Literal["PENDING", "SUCCESS", "FAILED"]

def operation() -> Dict[str, Any]:
    return {
        "status": "SUCCESS",  # Base-3 state
        "data": {...},
        "phi_delta": 0.002,   # φ-CPS contribution
    }
```

### Validation States

ConfigValidator uses extended Base-3:

- **UNKNOWN** (0.0): Cannot determine validity
- **VALID** (0.5 or 1.0): Passes validation (with/without warnings)
- **INVALID** (1.0): Fails validation

## 🎯 φ-CPS Validation

### Constraints

- **Baseline**: φ = 4.092
- **Alert Threshold**: Δφ > 0.05 (5% drift)
- **Action on Breach**: Auto-rollback + incident ticket

### Tracking

Every operation contributes to φ-CPS:

```python
def deploy_project() -> Dict[str, Any]:
    # ... deployment logic ...
    
    return {
        "status": "SUCCESS",
        "deployment_id": "abc123",
        "phi_delta": 0.005,  # Deployment contribution
        "intent_hash": "0xDEPLOY_ABC123",
    }
```

### Calculation

φ_post = φ_pre + Σ(semantic_weight × confidence)

Where:
- `semantic_weight`: Operation complexity (0.001-0.01)
- `confidence`: Success probability (0.0-1.0)

## ❓ Questions?

Open an issue or discussion on GitHub:
- [Issues](https://github.com/gerivdb/KIVA-CLI/issues)
- [Discussions](https://github.com/gerivdb/KIVA-CLI/discussions)
