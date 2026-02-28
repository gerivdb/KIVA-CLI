# KIVA-CLI

**Project & Application Orchestration CLI**

Autonomous orchestrator for project initialization, deployment management, and cross-repo coordination with ECOS ecosystem integration.

[![CI](https://github.com/gerivdb/KIVA-CLI/actions/workflows/ci.yml/badge.svg)](https://github.com/gerivdb/KIVA-CLI/actions/workflows/ci.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## ✨ Features

- **Project Initialization**: Scaffold projects from templates (FastAPI, React, Go, Rust)
- **Deployment Management**: Deploy, rollback, and manage environments
- **Base-3 State Logic**: PENDING/SUCCESS/FAILED with fuzzy confidence
- **φ-CPS Validation**: Global coherence tracking across operations
- **ECOS Gateway Integration**: Delegates to specialized CLIs (ECOS, BRAIN, FLUENCE)
- **IntentHash¹¹**: Cryptographic integrity for all operations

## 🚀 Quick Start

### Installation

```bash
# Clone repository
git clone https://github.com/gerivdb/KIVA-CLI.git
cd KIVA-CLI

# Install in editable mode
pip install -e .

# Verify installation
kiva --version
```

### Basic Usage

```bash
# List available templates
kiva project templates

# Initialize new FastAPI project
kiva project init --name my-api --template fastapi

# List projects in workspace
kiva project list

# Deploy to staging
kiva deploy --project-path ./my-api --environment staging --target k8s-cluster-1

# List deployments
kiva deployment list --environment staging

# Rollback deployment
kiva rollback --deployment-id abc12345
```

## 🏗️ Architecture

### Base-3 State Machine

All operations return one of three states:

- **PENDING** (0): Operation queued or in progress
- **SUCCESS** (1): Operation completed successfully
- **FAILED** (2): Operation encountered error

### φ-CPS Validation

Global coherence tracking ensures ecosystem consistency:

- **Baseline**: φ = 4.092
- **Alert Threshold**: Δφ > 0.05 (5% drift)
- **Auto-Rollback**: Triggered on threshold breach
- **Formula**: φ_post = φ_pre + Σ(semantic_weight × confidence)

### Components

- **ProjectManager**: Project lifecycle (init, list, validate)
- **DeploymentManager**: Deployment operations (deploy, rollback, list)
- **TemplateRegistry**: Manages project templates (FastAPI, React, Go, Rust)
- **ConfigValidator**: Base-3 validation (UNKNOWN/VALID/INVALID)
- **ECOS Gateway**: Delegates to specialized CLIs via subprocess

## 📚 Documentation

- [Architecture Overview](docs/architecture.md)
- [API Reference](docs/api.md)
- [Contributing Guide](CONTRIBUTING.md)
- [Changelog](CHANGELOG.md)

## 🧪 Development

### Setup

```bash
# Install development dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run tests with coverage
pytest --cov=kiva_cli --cov-report=html

# Lint code
ruff check .
black --check .

# Format code
black .
ruff check --fix .
```

### Testing

- **Unit Tests**: `tests/unit/` - Fast, no I/O
- **Integration Tests**: `tests/integration/` - Filesystem, subprocess
- **Coverage Target**: >80%

## 🔧 Project Templates

### FastAPI
- Python 3.12 + FastAPI + SQLAlchemy
- Alembic migrations + Pydantic validation
- Docker + pytest + uvicorn

### React
- TypeScript + Vite + TailwindCSS
- React 18 + Vitest + ESLint
- Docker multi-stage build

### Go Service
- Go 1.21 + Gin + GORM
- PostgreSQL driver + Docker
- Alpine-based production image

### Rust Service
- Rust 1.75 + Actix-Web + SQLx
- Tokio async runtime + Serde
- Alpine-based production image

## 🌐 ECOS Ecosystem Integration

KIVA-CLI integrates with ECOS ecosystem via Gateway pattern:

```bash
# ECOS Gateway delegates operations
ecos-cli gateway delegate --source kiva-cli --action project_init

# Global WAL tracking
ecos-cli wal append --source kiva-cli --event deployment_execute

# φ-CPS validation
ecos-cli validate phi-cps --delta 0.012
```

## 📄 License

MIT License - see [LICENSE](LICENSE)

## 👥 Authors

ECOS Ecosystem - H0 Autonomous Mode

## 🔗 Links

- [GitHub Repository](https://github.com/gerivdb/KIVA-CLI)
- [ECOS-CLI](https://github.com/gerivdb/DevTools)
- [ECOYSTEM](https://github.com/gerivdb/ECOYSTEM)
- [BRAIN](https://github.com/gerivdb/BRAIN)
