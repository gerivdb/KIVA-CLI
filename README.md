# KIVA-CLI 🚀

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![ECOS H0](https://img.shields.io/badge/ECOS-H0%20Autonomous-green.svg)](https://github.com/gerivdb/KIVA-CLI)
[![φ-CPS](https://img.shields.io/badge/φ--CPS-4.327-brightgreen.svg)](./ECOS_ROOT.json)

**Project & Deployment Orchestrator** with H0 Autonomous Mode, Base-3/4 validation, φ-CPS tracking, and Global WAL Manager.

## Overview

KIVA-CLI is an advanced orchestration tool for:
- 🏗️ **Multi-framework project scaffolding** (FastAPI, React, Go, Python libraries)
- 🚢 **Automated deployments** (Docker, Kubernetes, LXC)
- ✅ **Base-3 ternary semantic validation** (UNKNOWN/VALID/INVALID)
- 🔄 **Base-4 lifecycle management** (GENESIS→ACTIVE→DEPRECATED→ARCHIVED)
- 📊 **φ-CPS drift tracking** with automatic rollback detection
- 🔗 **IntentHash L0-L1-L2 chain** verification
- 📝 **Global WAL (Write-Ahead Log)** event persistence
- 🎯 **NO-HITL mode** (No Human In The Loop) for autonomous operations

## Quick Start

### Installation

```bash
# Clone repository
git clone https://github.com/gerivdb/KIVA-CLI.git
cd KIVA-CLI

# Install dependencies
pip install -r requirements.txt

# Install CLI (development mode)
pip install -e .

# Verify installation
ecos --version
```

### Basic Usage

```bash
# Scaffold new FastAPI project
ecos project scaffold my-api --framework fastapi

# Deploy to Docker
ecos project deploy my-api --target docker

# Check project status
ecos project status my-api

# Transition lifecycle
ecos project lifecycle my-api ACTIVE

# Check φ-CPS drift
ecos wal drift
```

## Core Features

### 1. Project Scaffolding

Create production-ready projects from templates:

```bash
# FastAPI microservice
ecos project scaffold api-service --framework fastapi

# React frontend
ecos project scaffold web-app --framework react

# Go service
ecos project scaffold go-api --framework go

# Python library
ecos project scaffold my-lib --framework python-lib
```

**Supported Frameworks:**
- FastAPI (REST API + async support)
- React (TypeScript + Vite)
- Go (Gin/Echo framework)
- Python Library (setuptools + poetry)

### 2. Deployment Automation

Deploy to multiple targets:

```bash
# Docker container
ecos project deploy my-api --target docker

# Kubernetes cluster
ecos project deploy my-api --target kubernetes

# LXC container
ecos project deploy my-api --target lxc
```

**Deployment Strategies:**
- Rolling updates
- Blue-green deployments
- Canary releases

### 3. Base-3 Ternary Validation

Semantic validation with three states:

| State | Symbol | Description |
|-------|--------|-------------|
| **UNKNOWN** | ⚠️ | Not yet validated |
| **VALID** | ✅ | All checks passed |
| **INVALID** | ❌ | Semantic errors detected |

```bash
# Check project validation
ecos project status my-api
```

### 4. Base-4 Lifecycle Management

Manage project lifecycle with four states:

```
GENESIS → ACTIVE → DEPRECATED → ARCHIVED
   🌱        ✅          ⚠️          📦
```

```bash
# Transition to ACTIVE (production-ready)
ecos project lifecycle my-api ACTIVE

# Mark as DEPRECATED (maintenance-only)
ecos project lifecycle my-api DEPRECATED

# Archive project (terminal state)
ecos project lifecycle my-api ARCHIVED
```

**Valid Transitions:**
- GENESIS → ACTIVE | ARCHIVED
- ACTIVE → DEPRECATED | ARCHIVED
- DEPRECATED → ACTIVE | ARCHIVED
- ARCHIVED → (terminal, no transitions)

### 5. Global WAL Manager

Cross-repository event tracking with IntentHash chain:

```bash
# Append event manually
ecos wal append --operation DEPLOY_SUCCESS \
                --repo my-api \
                --phi-delta 0.012

# Query recent events
ecos wal query --repo KIVA-CLI --limit 10

# Check φ-CPS drift
ecos wal drift

# Verify IntentHash chain
ecos wal chain 0x9A4E7C2F1D8B3605

# Create rollback point
ecos wal rollback --reason "Before major deployment"

# Export audit trail
ecos wal export audit.json
```

**WAL Features:**
- ✅ Event persistence (SQLite)
- ✅ IntentHash¹¹ L0-L1-L2 chain validation
- ✅ φ-CPS cumulative drift tracking
- ✅ Automatic rollback detection (drift > 5%)
- ✅ Complete audit trail (JSON/CSV)
- ✅ Multi-dimensional event filtering

### 6. φ-CPS Drift Tracking

Automatic semantic coherence monitoring:

```bash
# Current drift status
ecos wal drift

# Output:
# 📈 φ-CPS DRIFT METRICS
# Baseline: 4.269
# Current: 4.327
# Drift: 1.36% (✅ within 5% threshold)
```

**Drift Thresholds:**
- ✅ < 3%: Healthy
- ⚠️ 3-5%: Monitor
- 🛑 > 5%: Auto-rollback triggered

## CLI Commands

### Project Management

| Command | Description | Example |
|---------|-------------|----------|
| `ecos project scaffold` | Create new project | `ecos project scaffold my-api --framework fastapi` |
| `ecos project deploy` | Deploy to target | `ecos project deploy my-api --target docker` |
| `ecos project status` | Show project status | `ecos project status my-api` |
| `ecos project list` | List all projects | `ecos project list --framework fastapi` |
| `ecos project lifecycle` | Transition lifecycle | `ecos project lifecycle my-api ACTIVE` |

### Global WAL Management

| Command | Description | Example |
|---------|-------------|----------|
| `ecos wal append` | Append event | `ecos wal append -o DEPLOY -r my-api --phi-delta 0.012` |
| `ecos wal query` | Query events | `ecos wal query --repo KIVA-CLI --limit 10` |
| `ecos wal drift` | Check φ-CPS drift | `ecos wal drift` |
| `ecos wal chain` | Verify IntentHash | `ecos wal chain 0x9A4E7C2F1D8B3605` |
| `ecos wal rollback` | Create rollback | `ecos wal rollback --reason "Pre-deploy"` |
| `ecos wal export` | Export audit trail | `ecos wal export audit.json` |

### Legacy Commands

| Command | Description |
|---------|-------------|
| `ecos deploy` | Deploy project (legacy) |
| `ecos config` | Validate config |
| `ecos secrets` | Manage secrets |
| `ecos health` | Health checks |
| `ecos monitoring` | Monitoring dashboard |

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    KIVA CLI (Entry Point)                   │
│  ┌──────────────────────────────────────────────────┐      │
│  │  Command Groups                                   │      │
│  │  - project (ProjectManager)                      │      │
│  │  - wal (GlobalWALManager)                        │      │
│  │  - deploy, health, secrets, monitoring           │      │
│  └──────────────────────────────────────────────────┘      │
└──────────────────────┬──────────────────────────────────────┘
                       │
         ┌─────────────┴─────────────┐
         ▼                           ▼
┌─────────────────────┐    ┌─────────────────────┐
│  ProjectManager     │    │  GlobalWALManager   │
│  ┌───────────────┐  │    │  ┌───────────────┐  │
│  │ Scaffolding   │  │    │  │ Event Append  │  │
│  │ Deployment    │  │    │  │ Chain Verify  │  │
│  │ Validation    │  │    │  │ Drift Track   │  │
│  │ Lifecycle     │  │    │  │ Rollback Mgmt │  │
│  └───────────────┘  │    │  │ Audit Export  │  │
└─────────────────────┘    │  └───────────────┘  │
                           └─────────────────────┘
                                     │
                                     ▼
                          ┌──────────────────────┐
                          │  SQLite Database     │
                          │  - wal_events        │
                          │  - rollback_points   │
                          └──────────────────────┘
```

## Directory Structure

```
KIVA-CLI/
├── kiva_cli/
│   ├── commands/           # CLI command groups
│   │   ├── project_commands.py  # Project management
│   │   ├── wal_commands.py      # Global WAL CLI
│   │   ├── scaffold.py
│   │   ├── secrets.py
│   │   └── ...
│   ├── core/              # Core managers
│   │   ├── project_manager.py
│   │   ├── deployment_manager.py
│   │   └── config_manager.py
│   └── kiva.py            # Main CLI entry
├── tools/
│   └── core/
│       ├── global_wal_manager.py  # Global WAL Manager
│       └── ...
├── tests/
│   ├── test_project_manager.py
│   ├── test_global_wal_manager.py
│   ├── test_wal_commands.py
│   └── ...
├── docs/
│   ├── project_manager_cli.md
│   ├── global_wal_manager.md
│   └── ...
├── ECOS_ROOT.json         # Ecosystem manifest
├── README.md
├── requirements.txt
└── setup.py
```

## Testing

```bash
# Run all tests
pytest tests/ -v

# Specific test suites
pytest tests/test_project_manager.py -v
pytest tests/test_global_wal_manager.py -v
pytest tests/test_wal_commands.py -v

# With coverage
pytest tests/ --cov=kiva_cli --cov-report=html
```

## Roadmap

### Phase 1: Core Infrastructure ✅
- [x] ProjectManager (scaffolding, deployment, lifecycle)
- [x] Base-3 ternary validation
- [x] Base-4 lifecycle states
- [x] φ-CPS per-operation tracking
- [x] IntentHash L0-L1 verification
- [x] Project registry (SQLite)
- [x] CLI integration
- [x] Comprehensive tests

### Phase 2: Global WAL Manager ✅
- [x] Cross-repo event persistence
- [x] IntentHash¹¹ L0-L1-L2 chain
- [x] φ-CPS cumulative drift tracking
- [x] Automatic rollback detection
- [x] Audit trail export (JSON/CSV)
- [x] WAL CLI commands
- [x] Complete documentation

### Phase 3: Advanced Features (Q2 2026)
- [ ] Multi-repo orchestration
- [ ] Distributed WAL synchronization
- [ ] Real-time drift monitoring dashboard
- [ ] AI-powered rollback suggestions
- [ ] Cloud deployment targets (AWS, Azure, GCP)
- [ ] CI/CD pipeline generation
- [ ] Performance benchmarking suite

### Phase 4: Ecosystem Integration (Q3 2026)
- [ ] ECOYSTEM connector
- [ ] FLUENCE workflow integration
- [ ] BRAIN knowledge synchronization
- [ ] DevTools automation bridge
- [ ] Cross-ecosystem φ-CPS harmonization

## Contributing

Contributions welcome! See [CONTRIBUTING.md](./CONTRIBUTING.md) for guidelines.

### Development Setup

```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Run linter
flake8 kiva_cli/ tools/

# Run type checker
mypy kiva_cli/ tools/

# Format code
black kiva_cli/ tools/ tests/
```

## License

MIT License - see [LICENSE](./LICENSE) for details.

## Links

- **Repository**: [github.com/gerivdb/KIVA-CLI](https://github.com/gerivdb/KIVA-CLI)
- **Documentation**: [docs/](./docs/)
- **ECOS Manifest**: [ECOS_ROOT.json](./ECOS_ROOT.json)
- **Issues**: [github.com/gerivdb/KIVA-CLI/issues](https://github.com/gerivdb/KIVA-CLI/issues)

## Acknowledgments

Part of the **ECOS H0 Autonomous Mode** ecosystem with Base-3/4 validation and φ-CPS tracking.

---

**φ-CPS Current**: 4.327 | **Drift**: 1.36% ✅ | **Status**: ACTIVE | **Validation**: VALID
