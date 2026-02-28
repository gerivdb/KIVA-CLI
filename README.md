# KIVA-CLI - Project & Deployment Orchestrator

**Version:** 1.0.0  
**Status:** Active  
**Part of:** ECOS Ecosystem-1 (16 repos)

## Overview

KIVA-CLI is a specialized command-line tool for project scaffolding and deployment orchestration within the ECOS ecosystem. It provides template-based project initialization (FastAPI, React, Go, Rust, etc.) and deployment workflows integrated with FLUENCE pipeline engine.

## Features

- 🚀 **Project Scaffolding**: Initialize projects from ecosystem templates
- 🔄 **Deployment Management**: Rolling, blue-green, canary strategies
- ✅ **Configuration Validation**: JSON Schema-based config validation
- ↩️ **Rollback Support**: Version-tracked deployment rollbacks
- 🔗 **ECOS Integration**: Seamless integration via ECOS CLI Gateway
- 📊 **FLUENCE Workflows**: Native FLUENCE pipeline orchestration

## Installation

```bash
# Clone repository
git clone https://github.com/gerivdb/KIVA-CLI.git
cd KIVA-CLI

# Install dependencies
pip install -r requirements.txt

# Install CLI (development mode)
pip install -e .

# Verify installation
kiva --version
```

## Quick Start

### 1. Initialize Project

```bash
# FastAPI project
kiva project my-api --template fastapi

# React TypeScript app
kiva project my-app --template react

# Go microservice
kiva project my-service --template go --path ./services/
```

### 2. Deploy to Environment

```bash
# Dry-run deployment (no actual changes)
kiva deploy ./my-api --env staging --dry-run

# Deploy to staging (rolling strategy)
kiva deploy ./my-api --env staging --strategy rolling

# Deploy to production (blue-green strategy)
kiva deploy ./my-api --env production --strategy blue-green
```

### 3. Validate Configuration

```bash
# Validate kiva.yaml
kiva config ./my-api/kiva.yaml

# Validate with custom schema
kiva config ./my-api/kiva.yaml --schema custom-schema
```

### 4. Rollback Deployment

```bash
# Rollback to previous version
kiva rollback my-api --env production

# Rollback to specific version
kiva rollback my-api --env production --version 1.2.3
```

## Configuration

KIVA uses `kiva.yaml` for project configuration:

```yaml
project:
  name: my-api
  version: 1.0.0
  template: fastapi
  
deployment:
  environments:
    - dev
    - staging
    - production
  
  strategies:
    staging: rolling
    production: blue-green
  
  health_checks:
    enabled: true
    path: /health
    timeout: 30s
```

## Templates

Available templates in ECOYSTEM/templates/:

| Template | Description | Stack |
|----------|-------------|-------|
| **fastapi** | REST API with FastAPI | Python 3.11+, FastAPI, Pydantic |
| **react** | React TypeScript app | React 18, TypeScript, Vite |
| **go** | Go microservice | Go 1.21+, net/http, gorilla/mux |
| **rust** | Rust service | Rust 1.75+, Actix-web |
| **nextjs** | Next.js full-stack | Next.js 14, React, TypeScript |
| **django** | Django REST API | Python 3.11+, Django 4.2, DRF |

## Integration with ECOS CLI

KIVA-CLI commands are accessible via ECOS CLI through the gateway:

```bash
# Direct KIVA call
kiva project my-app --template react

# Via ECOS CLI (delegated to KIVA)
ecos project my-app --template react

# Both execute identically
```

## Deployment Strategies

### Rolling Deployment
- Gradual instance replacement
- Zero-downtime updates
- Automatic rollback on failure

### Blue-Green Deployment
- Parallel environment preparation
- Instant traffic switch
- Easy rollback (traffic reversal)

### Canary Deployment
- Phased traffic migration (10% → 50% → 100%)
- Real-time monitoring integration
- Automated rollback on anomalies

## Architecture

```
KIVA-CLI/
├── kiva_cli/
│   ├── core/
│   │   ├── project_manager.py      # Template scaffolding
│   │   ├── deployment_manager.py   # FLUENCE integration
│   │   └── config_manager.py       # JSON Schema validation
│   ├── kiva.py                     # CLI entry point
│   └── __init__.py
├── tests/                          # Unit & integration tests
├── examples/                       # Usage examples
├── requirements.txt
└── README.md
```

## φ-CPS Integration

KIVA operations contribute to global φ-CPS (Coherence-Productivity Score):

- **Project Init:** +0.001 per successful scaffold
- **Deployment:** +0.002 per successful production deploy
- **Rollback:** -0.001 (temporary degradation)
- **Config Validation:** +0.0005 per valid config

φ-CPS threshold: Δφ > 0.05 triggers automatic rollback.

## Examples

See [examples/](examples/) directory:

1. **fastapi-project/** - Complete FastAPI REST API
2. **react-app/** - React TypeScript SPA
3. **deployment-workflow/** - Multi-environment pipeline
4. **rollback-scenario/** - Production rollback simulation
5. **config-validation/** - kiva.yaml validation examples

## Testing

```bash
# Run all tests
pytest

# With coverage report
pytest --cov=kiva_cli --cov-report=html

# Specific test file
pytest tests/test_project_manager.py -v

# Integration tests only
pytest tests/integration/ -m integration
```

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

MIT License - Part of ECOS Ecosystem-1

## Links

- **GitHub:** https://github.com/gerivdb/KIVA-CLI
- **ECOYSTEM:** https://github.com/gerivdb/ECOYSTEM
- **FLUENCE:** https://github.com/gerivdb/FLUENCE
- **Documentation:** https://github.com/gerivdb/BRAIN-DOCS
