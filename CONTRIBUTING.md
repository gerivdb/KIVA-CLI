# Contributing to KIVA-CLI

## Development Setup

```bash
# Clone repository
git clone https://github.com/gerivdb/KIVA-CLI.git
cd KIVA-CLI

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\\Scripts\\activate

# Install dev dependencies
pip install -r requirements.txt
pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install
```

## Coding Standards

### Python Style
- **PEP 8** compliance (enforced by flake8)
- **Black** formatting (line length: 100)
- **Type hints** for all functions
- **Docstrings** (Google style)

### Commit Messages
Format: `[ECOS-AUTO] <type>: <description>`

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `test`: Test additions/modifications
- `refactor`: Code restructuring
- `chore`: Maintenance tasks

Example:
```
[ECOS-AUTO] feat: Add canary deployment strategy

Intent-Hash: 0x4A7C9E2B5F8D1A63
φ-CPS: +0.003
```

## Testing Requirements

### Coverage Target
- **Minimum:** 85%
- **Critical paths:** 95%+

### Test Structure
```
tests/
├── unit/
│   ├── test_project_manager.py
│   ├── test_deployment_manager.py
│   └── test_config_manager.py
├── integration/
│   ├── test_ecos_gateway.py
│   └── test_fluence_workflow.py
└── fixtures/
    ├── sample_kiva.yaml
    └── mock_templates/
```

### Running Tests
```bash
# All tests
pytest

# Unit tests only
pytest tests/unit/

# Integration tests (requires FLUENCE CLI)
pytest tests/integration/ -m integration

# With coverage
pytest --cov=kiva_cli --cov-report=term-missing
```

## φ-CPS Validation

All commits must validate φ-CPS drift:

```python
# Before commit
phi_baseline = 4.413
phi_post = calculate_phi_cps(changes)
delta = phi_post - phi_baseline

if delta > 0.05:
    raise ValueError(f"φ-CPS drift too high: {delta:.3f}")
```

## Pull Request Process

1. **Create branch**: `feature/your-feature-name`
2. **Implement changes** with tests
3. **Run validation**:
   ```bash
   black kiva_cli/
   flake8 kiva_cli/
   mypy kiva_cli/
   pytest --cov=kiva_cli
   ```
4. **Commit** with Intent-Hash
5. **Push** and create PR
6. **CI/CD** must pass (GitHub Actions)

## Branch Strategy

- `main`: Stable production code
- `develop`: Integration branch
- `feature/*`: New features
- `fix/*`: Bug fixes
- `docs/*`: Documentation updates

## Code Review Checklist

- [ ] Tests pass (unit + integration)
- [ ] Coverage ≥ 85%
- [ ] Black + flake8 + mypy clean
- [ ] Documentation updated
- [ ] φ-CPS drift < 5%
- [ ] Backward compatibility maintained
- [ ] Examples updated (if applicable)

## Issue Reporting

Use GitHub Issues with labels:

- `bug`: Code defects
- `feature`: New functionality
- `docs`: Documentation improvements
- `performance`: Optimization needs
- `question`: Clarifications

## Contact

- **Maintainer:** gerivdb
- **Ecosystem:** ECOS Ecosystem-1
- **Chat:** [Discord/Slack link]
