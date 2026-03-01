# KIVA-CLI - Project & Deployment Orchestrator

🚀 **Advanced Project Lifecycle Management | ECOS H0 Mode Integration**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![ECOS H0](https://img.shields.io/badge/ECOS-H0_Mode-green.svg)](docs/ecos_h0_spec.md)
[![φ-CPS](https://img.shields.io/badge/φ--CPS-4.261-orange.svg)](ECOS_ROOT.json)

---

## Overview

KIVA-CLI is the **orchestrator hub** for ecosystem-1, providing:

- 🏗️ **Multi-framework project scaffolding** (FastAPI, React, Go, Python libs, Docker Compose, LXC)
- 🚀 **Automated deployment** to Docker, Kubernetes, LXC containers
- ✅ **Base-3 ternary validation** (UNKNOWN / VALID / INVALID semantic states)
- 🔄 **Base-4 lifecycle management** (GENESIS / ACTIVE / DEPRECATED / ARCHIVED)
- 📈 **φ-CPS drift tracking** with auto-rollback on threshold breach
- 🔗 **IntentHash L0-L1 chain verification** for semantic continuity
- 💡 **Global WAL Manager** for cross-repo event tracing
- 🔍 **Batch issue processing** and GitHub automation

---

## Quick Start

### Installation

```bash
# Clone repository
git clone https://github.com/gerivdb/KIVA-CLI.git
cd KIVA-CLI

# Install with ProjectManager support
pip install -e .

# Verify installation
ecos --version
ecos project --help
```

### Basic Usage

```bash
# 1. Scaffold FastAPI microservice
ecos project scaffold my-api --framework fastapi

# 2. Deploy to Docker
ecos project deploy my-api --target docker

# 3. Check status
ecos project status my-api

# 4. Transition to ACTIVE lifecycle
ecos project lifecycle my-api ACTIVE

# 5. List all projects
ecos project list
```

---

## Core Features

### 🏗️ Multi-Framework Scaffolding

Supported frameworks:
- **FastAPI**: Python microservices with async support
- **React**: Frontend applications with TypeScript/Redux
- **Go**: High-performance Go microservices
- **Python Lib**: Reusable Python library packages
- **Docker Compose**: Multi-service orchestration
- **LXC Containers**: System container configurations

```bash
ecos project scaffold webapp --framework react \
  --deps typescript --deps redux
```

### 🚀 Automated Deployment

Deploy to multiple targets:
- **Docker**: Containerization with Dockerfile generation
- **Kubernetes**: K8s manifests (Deployment + Service + Ingress)
- **LXC**: System container deployment with resource quotas

```bash
ecos project deploy my-api --target kubernetes --dry-run
```

### ✅ Base-3 Ternary Validation

Semantic validation with 3 states:
- **UNKNOWN** ❓: Not yet validated
- **VALID** ✅: All checks passed
- **INVALID** ❌: Semantic errors detected

```bash
ecos validate --project my-api --audit comprehensive
```

### 🔄 Base-4 Lifecycle Management

Project lifecycle states:
- **GENESIS** 🌱: Initial scaffolded state
- **ACTIVE** ✅: Production-ready
- **DEPRECATED** ⚠️: Legacy, maintenance-only
- **ARCHIVED** 📦: Terminal state

```bash
ecos project lifecycle old-service DEPRECATED
```

### 📈 φ-CPS Drift Tracking

Automatic drift detection with rollback:
- **Threshold**: Δφ > 0.05 (5% drift)
- **Auto-rollback**: Triggered on threshold breach
- **Per-operation tracking**: Scaffold (+0.018), Deploy (+0.012), Lifecycle (+0.005)

```bash
ecos phi check-drift
ecos phi prepare-reset  # If drift > 5%
```

### 🔗 IntentHash Verification

L0-L1 chain continuity tracking:
- **Format**: `0x<16-char HEX>`
- **Verification**: Chain continuity validation
- **Logging**: Global WAL database persistence

```bash
ecos intenthash verify --project my-api
```

---

## CLI Commands

### Project Management

| Command | Description |
|---------|-------------|
| `ecos project scaffold` | Create new project from template |
| `ecos project deploy` | Deploy to Docker/K8s/LXC |
| `ecos project status` | Show comprehensive project status |
| `ecos project list` | List all registered projects |
| `ecos project lifecycle` | Transition lifecycle state |

### Validation & Metrics

| Command | Description |
|---------|-------------|
| `ecos validate` | Semantic validation (base-3 ternary) |
| `ecos phi check-drift` | Check φ-CPS drift against threshold |
| `ecos phi prepare-reset` | Prepare baseline reset |
| `ecos intenthash verify` | Verify IntentHash chain |

### Legacy Commands

| Command | Description |
|---------|-------------|
| `ecos scaffold` | Legacy scaffold interface |
| `ecos deploy` | Legacy deploy interface |
| `ecos monitoring` | Monitoring dashboard |
| `ecos rollback` | Deployment rollback |

See [docs/project_manager_cli.md](docs/project_manager_cli.md) for complete reference.

---

## Architecture

### ECOS H0 Mode Integration

```
┌─────────────────────────────┐
│  KIVA-CLI Orchestrator      │
│  (ECOS H0 Mode)             │
└─────────┬───────────────────┘
         │
    ┌────┼────┐
    │         │
┌───┴───┐  ┌─┴──────────────┐
│ Tools │  │ ProjectManager │
│ /core │  │   (NEW H0)     │
└───┬───┘  └──────┬───────┘
    │            │
    │            ├─── Base-3 Validation
    │            ├─── Base-4 Lifecycle
    │            ├─── φ-CPS Tracking
    │            └─── IntentHash L0-L1
    │
    ├─── Global WAL Manager
    ├─── CitizenManager (L0-L5)
    ├─── SkillManager
    ├─── DaemonManager
    ├─── PipelineManager
    └─── FrameworkManager
```

### Directory Structure

```
KIVA-CLI/
├── kiva_cli/
│   ├── commands/
│   │   ├── project_commands.py  # NEW: ProjectManager CLI
│   │   ├── scaffold.py
│   │   ├── secrets.py
│   │   └── ...
│   ├── core/
│   ├── managers/
│   └── kiva.py              # Main CLI entry point
├── tools/
│   ├── core/
│   │   ├── project_manager.py   # NEW: H0 ProjectManager
│   │   ├── global_wal_manager.py
│   │   └── ...
│   └── blo/
├── tests/
│   ├── test_project_manager.py      # NEW: Core tests
│   ├── test_project_commands.py     # NEW: CLI tests
│   └── ...
├── docs/
│   ├── project_manager_cli.md       # NEW: CLI reference
│   └── ...
├── ECOS_ROOT.json                       # Ecosystem manifest
├── README.md
└── setup.py
```

---

## Testing

```bash
# Run all tests
pytest tests/ -v

# Test ProjectManager core
pytest tests/test_project_manager.py -v

# Test CLI commands
pytest tests/test_project_commands.py -v

# Test with coverage
pytest tests/ --cov=kiva_cli --cov-report=html
```

---

## Configuration

### Workspace Setup

```bash
# Set custom workspace
export KIVA_WORKSPACE=~/my-projects

# Or use --workspace flag
ecos project scaffold my-api --framework fastapi \
  --workspace ~/my-projects
```

### ECOS_ROOT.json

Ecosystem-1 manifest with 16 repositories:
- **φ-CPS baseline**: 4.261
- **Open issues**: 0
- **Total commits**: 33
- **Capabilities**: 50+ (including ProjectManager)

---

## Roadmap

### Phase 1: H0 Core ✅ COMPLETED
- [x] Base-3 ternary validation
- [x] Base-4 lifecycle management
- [x] φ-CPS drift tracking
- [x] IntentHash L0-L1 verification
- [x] ProjectManager CLI integration

### Phase 2: Advanced Deployments (Q2 2026)
- [ ] AWS ECS/Fargate deployment
- [ ] Azure Container Instances
- [ ] Google Cloud Run
- [ ] Terraform infrastructure generation

### Phase 3: CI/CD Integration (Q3 2026)
- [ ] GitHub Actions workflow generation
- [ ] GitLab CI/CD pipelines
- [ ] Jenkins integration
- [ ] Automated rollback on φ-CPS breach

### Phase 4: Multi-Repo Orchestration (Q4 2026)
- [ ] Cross-repo dependency resolution
- [ ] Monorepo support
- [ ] Distributed φ-CPS tracking
- [ ] Global IntentHash chain validation

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

### Quick Contribution

```bash
# Fork and clone
git clone https://github.com/YOUR_USERNAME/KIVA-CLI.git

# Create feature branch
git checkout -b feature/new-framework-support

# Make changes and test
pytest tests/ -v

# Commit with ECOS convention
git commit -m "[ECOS-AUTO] feat: Add Rust framework support"

# Push and create PR
git push origin feature/new-framework-support
```

---

## License

MIT License - See [LICENSE](LICENSE) for details.

---

## Links

- **Repository**: [github.com/gerivdb/KIVA-CLI](https://github.com/gerivdb/KIVA-CLI)
- **Documentation**: [docs/](docs/)
- **ECOS Specification**: [docs/ecos_h0_spec.md](docs/ecos_h0_spec.md)
- **Issue Tracker**: [GitHub Issues](https://github.com/gerivdb/KIVA-CLI/issues)

---

**Last Updated:** 2026-03-01  
**ECOS Version:** H0 (Base-3/4 ternary + lifecycle)  
**φ-CPS Current:** 4.261 (+0.022 since baseline reset)  
**IntentHash (latest):** 0x7E3A9F2D48B6C105
