# KIVA CLI ⚡

[![CI](https://github.com/gerivdb/KIVA-CLI/actions/workflows/ci.yml/badge.svg)](https://github.com/gerivdb/KIVA-CLI/actions/workflows/ci.yml)
[![Lint](https://github.com/gerivdb/KIVA-CLI/actions/workflows/lint.yml/badge.svg)](https://github.com/gerivdb/KIVA-CLI/actions/workflows/lint.yml)
[![codecov](https://codecov.io/gh/gerivdb/KIVA-CLI/branch/main/graph/badge.svg)](https://codecov.io/gh/gerivdb/KIVA-CLI)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Ecosystem-1](https://img.shields.io/badge/ecosystem-1-green.svg)](https://github.com/gerivdb/ECOYSTEM)

**Projects & Applications Orchestrator for Ecosystem-1**

KIVA CLI est l'orchestrateur autonome de gestion des projets et applications dans l'écosystème ECOS. Il fournit des commandes pour scaffolding, déploiement, configuration et monitoring avec intégration native au Gateway ECOS CLI.

---

## 🚀 Quick Start

### Installation

```bash
# Via pip (recommandé)
pip install kiva-cli

# Depuis les sources
git clone https://github.com/gerivdb/KIVA-CLI.git
cd KIVA-CLI
pip install -e ".[dev]"
```

### Premières Commandes

```bash
# Initialiser un projet FastAPI
kiva project init --template=fastapi --name=my-api

# Scaffolder un composant React
kiva project scaffold --type=component --name=Button --typescript

# Déployer en staging
kiva deploy staging api --env=preprod

# Valider configuration
kiva config validate kiva.yaml
```

---

## 🎯 Features

### 📁 Project Management

- **Templates Support**: FastAPI, React, Go, Rust, Next.js
- **Scaffolding**: Components, services, models, tests
- **Dependency Management**: Automatic detection + updates
- **Configuration**: YAML/JSON validation with schemas

### 🚀 Deployment

- **Multi-Environment**: dev, staging, production
- **Strategies**: rolling, blue-green, canary
- **Rollback**: One-command version rollback
- **Health Checks**: Automated post-deployment validation

### 🔗 Ecosystem Integration

- **ECOS CLI Gateway**: Seamless delegation from `ecos` command
- **BRAIN CLI**: Pattern detection and ML suggestions
- **FLUENCE CLI**: Workflow execution coordination
- **Global WAL**: Event tracking with φ-CPS validation

---

## 📚 Documentation

- [Installation Guide](docs/installation.md)
- [Command Reference](docs/commands.md)
- [Templates](docs/templates.md)
- [Configuration](docs/configuration.md)
- [API Integration](docs/api.md)
- [Contributing](CONTRIBUTING.md)

---

## 🛠️ Architecture

```
KIVA CLI
│
├── Commands Layer
│   ├── project (init, scaffold, list)
│   ├── deploy (staging, production, rollback)
│   └── config (validate, generate, migrate)
│
├── Core Managers
│   ├── ProjectManager (lifecycle, templates)
│   ├── DeploymentManager (strategies, health)
│   └── ConfigManager (validation, schemas)
│
└── Integrations
    ├── ECOS CLI (subprocess delegation)
    ├── BRAIN CLI (pattern detection)
    └── FLUENCE CLI (workflow execution)
```

---

## 🧪 Examples

### Create FastAPI Project

```bash
kiva project init --template=fastapi --name=my-api
cd my-api
kiva config validate pyproject.toml
python -m uvicorn main:app --reload
```

### Deploy with Monitoring

```bash
# Deploy to staging
kiva deploy staging api --strategy=rolling

# Check health
kiva deploy status api-staging

# Rollback if needed
kiva deploy rollback api-v1.2.0 --to-version=v1.1.0
```

### Integration with ECOS

```bash
# Via ECOS Gateway (deprecated but supported)
ecos project init --template=react --name=my-app
# ⚠️ Auto-delegates to: kiva project init ...

# Direct KIVA usage (recommended)
kiva project init --template=react --name=my-app
```

---

## 📊 Project Status

**Version**: 0.1.0-alpha  
**Phase**: 1A - Initial Extraction  
**φ-CPS Impact**: +0.008 (4.299 → 4.307 target)  
**Coverage**: Target 80%+  

### Roadmap

- [x] Repository setup + CI/CD
- [ ] Extract project commands from ECOYSTEM
- [ ] Implement core managers (Project, Deploy, Config)
- [ ] Integration tests with ECOS CLI
- [ ] Documentation complete
- [ ] Beta release 0.1.0

---

## 🤝 Contributing

Contributions welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

### Development Setup

```bash
git clone https://github.com/gerivdb/KIVA-CLI.git
cd KIVA-CLI
pip install -e ".[dev]"
pytest  # Run tests
ruff check kiva_cli  # Lint
black kiva_cli  # Format
```

---

## 📝 License

MIT License - see [LICENSE](LICENSE) for details.

---

## 🔗 Links

- [ECOYSTEM](https://github.com/gerivdb/ECOYSTEM) - Root infrastructure
- [ECOS CLI](https://github.com/gerivdb/ECOS-CLI) - CLI Gateway
- [BRAIN](https://github.com/gerivdb/BRAIN) - AI orchestration
- [FLUENCE](https://github.com/gerivdb/FLUENCE) - Workflow engine
- [PRD #421](https://github.com/gerivdb/ECOYSTEM/issues/421) - CLI Modular Distribution Strategy

---

**Made with ♥️ for Ecosystem-1 | H0 Autonomous Mode | IntentHash¹¹ Validated**
