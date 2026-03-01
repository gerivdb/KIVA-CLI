# KIVA-CLI

**ECOS-CLI Unified Command-Line Interface**  
Project automation, workflow orchestration, and entity lifecycle management for the ECOS ecosystem.

[![Version](https://img.shields.io/badge/version-0.3.0-blue.svg)](https://github.com/gerivdb/KIVA-CLI)  
[![φ-CPS](https://img.shields.io/badge/φ--CPS-4.398-green.svg)](docs/global_wal_manager.md)  
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)  
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

---

## 🚀 Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Scaffold a new FastAPI project
ecos project scaffold my-api --framework fastapi

# Register an entity (citizen)
ecos citizen register --name my-api --type SERVICE --repo KIVA-CLI

# Deploy to Docker
ecos project deploy my-api --target docker

# Check φ-CPS drift
ecos wal drift

# List all citizens
ecos citizen list
```

---

## 📋 Features

### ✅ **ProjectManager** - Project Scaffolding

- **Multi-framework templates**: FastAPI, Go, React, Node.js, Django, Python CLI
- **Docker support**: Dockerfile + Docker Compose auto-generation
- **Dependency management**: Automatic `pip`, `npm`, `go mod` installation
- **Project registry**: SQLite-based tracking with φ-CPS scoring
- **CLI commands**: `scaffold`, `list`, `export`, `deploy`

### ✅ **GlobalWALManager** - Event Tracking

- **Cross-repo persistence**: SQLite database for all ecosystem-1 repos
- **IntentHash¹¹ chain**: L0-L1-L2 cryptographic continuity validation
- **φ-CPS drift monitoring**: Automatic threshold alerts (5% default)
- **Rollback points**: Auto-create snapshots on drift exceeding threshold
- **Audit trail**: Complete event history with JSON/CSV export
- **CLI commands**: `append`, `query`, `drift`, `chain`, `rollback`, `export`

### ✅ **CitizenManager** - Entity Lifecycle

- **L0-L5 hierarchy**: Entity maturity from genesis to critical production or legacy
- **Base-3 validation**: UNKNOWN / VALID / INVALID ternary states
- **Base-4 lifecycle**: GENESIS / ACTIVE / DEPRECATED / ARCHIVED
- **Entity types**: PROJECT, SERVICE, COMPONENT, TOOL, LIBRARY, FRAMEWORK, WORKFLOW, AGENT
- **Promotion/demotion**: Automatic φ-CPS adjustments on level changes
- **Cross-repo sync**: Scan 16 ecosystem-1 repos and auto-register entities
- **CLI commands**: `register`, `promote`, `demote`, `list`, `export`, `validate`, `sync`

---

## 🏗️ Architecture

```
┌────────────────────────────────────────────────────────────┐
│                       KIVA-CLI                             │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  ┌─────────────────┐   ┌───────────────────┐             │
│  │ ProjectManager  │   │ CitizenManager    │             │
│  │ (Scaffolding)   │   │ (L0-L5 Entities)  │             │
│  └────────┬────────┘   └────────┬──────────┘             │
│           │                     │                          │
│           └──────────┬──────────┘                          │
│                      ▼                                     │
│           ┌──────────────────────┐                        │
│           │  GlobalWALManager    │                        │
│           │  (Event Tracking)    │                        │
│           └──────────────────────┘                        │
│                      │                                     │
│           ┌──────────┴──────────┐                         │
│           ▼                     ▼                         │
│  ┌─────────────────┐   ┌──────────────────┐              │
│  │  projects.db    │   │  citizens.db     │              │
│  │  (SQLite)       │   │  (SQLite)        │              │
│  └─────────────────┘   └──────────────────┘              │
│           │                     │                          │
│           └──────────┬──────────┘                          │
│                      ▼                                     │
│           ┌──────────────────────┐                        │
│           │  global_wal.db       │                        │
│           │  (SQLite)            │                        │
│           └──────────────────────┘                        │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

---

## 📚 CLI Commands

### **Project Commands**

| Command | Description | Example |
|---------|-------------|----------|
| `ecos project scaffold` | Create new project from template | `ecos project scaffold my-api --framework fastapi` |
| `ecos project list` | List all projects | `ecos project list --framework fastapi` |
| `ecos project export` | Export project registry | `ecos project export projects.json` |
| `ecos project deploy` | Deploy project to Docker | `ecos project deploy my-api --target docker` |

### **WAL Commands**

| Command | Description | Example |
|---------|-------------|----------|
| `ecos wal append` | Append event to WAL | `ecos wal append --operation DEPLOY --repo my-api --phi-delta 0.015` |
| `ecos wal query` | Query WAL events | `ecos wal query --repo KIVA-CLI --limit 20` |
| `ecos wal drift` | Check φ-CPS drift | `ecos wal drift` |
| `ecos wal chain` | Verify IntentHash chain | `ecos wal chain 0x9A4E7C2F1D8B3605` |
| `ecos wal rollback` | Create rollback point | `ecos wal rollback --reason "Pre-deploy snapshot"` |
| `ecos wal export` | Export audit trail | `ecos wal export audit.json` |

### **Citizen Commands**

| Command | Description | Example |
|---------|-------------|----------|
| `ecos citizen register` | Register new entity | `ecos citizen register --name my-api --type SERVICE --repo KIVA-CLI` |
| `ecos citizen promote` | Promote entity level | `ecos citizen promote ctz_abc123 --level L2_OPERATIONAL` |
| `ecos citizen demote` | Demote or archive entity | `ecos citizen demote ctz_abc123 --level L5_LEGACY --reason "Deprecated"` |
| `ecos citizen list` | List citizens with filters | `ecos citizen list --repo KIVA-CLI --level L3_PRODUCTION` |
| `ecos citizen export` | Export citizen registry | `ecos citizen export citizens.json` |
| `ecos citizen validate` | Update validation state | `ecos citizen validate ctz_abc123 --state VALID` |
| `ecos citizen sync` | Cross-repo synchronization | `ecos citizen sync --repos KIVA-CLI,BRAIN,FLUENCE` |

---

## 🔄 Workflows

### **Complete Project Lifecycle**

```bash
# 1. Create rollback point
ecos wal rollback --reason "PRE_PROJECT_CREATION"

# 2. Scaffold project
ecos project scaffold my-api --framework fastapi

# 3. Register as citizen (entity)
ecos citizen register --name my-api --type SERVICE --repo KIVA-CLI --level L0_GENESIS

# 4. Deploy to Docker
ecos project deploy my-api --target docker

# 5. Promote after successful deployment
ecos citizen promote <citizen_id> --level L2_OPERATIONAL

# 6. Validate deployment
ecos citizen validate <citizen_id> --state VALID

# 7. Check drift
ecos wal drift

# 8. Export audit trail
ecos wal export deploy-audit-$(date +%Y%m%d).json
```

### **Cross-Repo Synchronization**

```bash
# 1. Dry-run to preview changes
ecos citizen sync --dry-run

# 2. Execute sync across all 16 repos
ecos citizen sync

# 3. Review registered entities
ecos citizen list --format json > registry_snapshot.json

# 4. Export for backup
ecos citizen export citizens_backup_$(date +%Y%m%d).json
```

### **Entity Promotion Path**

```bash
# Register new service at L0
CITIZEN_ID=$(ecos citizen register --name prod-api --type SERVICE --repo FLUENCE | grep -oP 'ctz_[a-f0-9]+')

# Promote L0 → L1 (validation passed)
ecos citizen promote $CITIZEN_ID --level L1_VALIDATED

# Deploy to staging
ecos project deploy prod-api --target docker

# Promote L1 → L2 (operational)
ecos citizen promote $CITIZEN_ID --level L2_OPERATIONAL

# After 30 days stable: Promote L2 → L3 (production)
ecos citizen promote $CITIZEN_ID --level L3_PRODUCTION

# Mark as mission-critical: Promote L3 → L4
ecos citizen promote $CITIZEN_ID --level L4_CRITICAL
```

---

## 📊 Entity Levels (L0-L5)

```
┌─────────────────────────────────────────────────────────┐
│                 Entity Lifecycle                        │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  L0: GENESIS        → Unvalidated, just created        │
│      (φ-CPS: 0.005)                                     │
│           │                                             │
│           ▼ +0.008                                      │
│  L1: VALIDATED      → Basic validation passed           │
│      (φ-CPS: 0.010)                                     │
│           │                                             │
│           ▼ +0.010                                      │
│  L2: OPERATIONAL    → Deployed and functional           │
│      (φ-CPS: 0.015)                                     │
│           │                                             │
│           ▼ +0.012                                      │
│  L3: PRODUCTION     → Stable production use             │
│      (φ-CPS: 0.020)                                     │
│           │                                             │
│           ▼ +0.015                                      │
│  L4: CRITICAL       → Mission-critical entity           │
│      (φ-CPS: 0.030)                                     │
│           │                                             │
│           ▼ (demote/archive)                            │
│  L5: LEGACY         → Archived/deprecated               │
│      (φ-CPS: 0.002)                                     │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## 📁 Project Structure

```
KIVA-CLI/
├── docs/
│   ├── global_wal_manager.md      # WAL Manager complete reference
│   └── citizen_manager.md         # CitizenManager complete reference
├── kiva_cli/
│   ├── commands/
│   │   ├── project_commands.py    # Project CLI commands
│   │   ├── wal_commands.py        # WAL CLI commands
│   │   └── citizen_commands.py    # Citizen CLI commands
│   └── kiva.py                    # Main CLI entry point
├── scripts/
│   ├── batch_issue_processor.py   # Batch issue processing
│   └── cross_repo_sync.py         # Cross-repo citizen sync
├── tests/
│   ├── test_project_manager.py    # ProjectManager tests
│   ├── test_global_wal_manager.py # WAL Manager tests
│   ├── test_wal_commands.py       # WAL CLI tests
│   ├── test_citizen_manager.py    # CitizenManager tests
│   └── test_citizen_commands.py   # Citizen CLI tests
├── tools/
│   └── core/
│       ├── project_manager.py     # ProjectManager implementation
│       ├── global_wal_manager.py  # GlobalWALManager implementation
│       └── citizen_manager.py     # CitizenManager implementation
├── ECOS_ROOT.json                 # Manifest (φ-CPS: 4.398)
├── README.md                      # This file
└── requirements.txt               # Python dependencies
```

---

## 🧪 Testing

```bash
# Run all tests
pytest tests/ -v

# Run specific test suite
pytest tests/test_citizen_manager.py -v
pytest tests/test_global_wal_manager.py -v

# Run with coverage
pytest tests/ --cov=tools --cov=kiva_cli --cov-report=html

# View coverage report
open htmlcov/index.html
```

---

## 📖 Documentation

- **[Global WAL Manager Reference](docs/global_wal_manager.md)** - Complete WAL Manager guide
- **[Citizen Manager Reference](docs/citizen_manager.md)** - Complete CitizenManager guide
- **[ECOS_ROOT.json](ECOS_ROOT.json)** - Project manifest with φ-CPS metrics

---

## 🗺️ Roadmap

### ✅ Phase 1 - ProjectManager (Completed)
- Multi-framework scaffolding (6 templates)
- Docker support (Dockerfile + Compose)
- SQLite project registry
- CLI commands (scaffold/list/export/deploy)

### ✅ Phase 2 - GlobalWALManager (Completed)
- Cross-repo event persistence
- IntentHash¹¹ L0-L1-L2 chain validation
- φ-CPS drift tracking (5% threshold)
- Automatic rollback points
- CLI integration (6 WAL commands)

### ✅ Phase 3 - CitizenManager (Completed)
- L0-L5 entity hierarchy
- Base-3 ternary validation (UNKNOWN/VALID/INVALID)
- Base-4 lifecycle states (GENESIS/ACTIVE/DEPRECATED/ARCHIVED)
- Entity promotion/demotion with φ-CPS tracking
- Cross-repo synchronization (16 ecosystem-1 repos)
- CLI integration (7 Citizen commands)

### 🔄 Phase 4 - Advanced Managers (In Progress)
- **DaemonManager**: Background task orchestration
- **SkillManager**: Reusable script/capability registry
- **PipelineManager**: Multi-step workflow automation
- **Advanced analytics**: φ-CPS trend visualization (Plotly)
- **CI/CD integration**: GitHub Actions workflows
- **Distributed WAL**: Multi-node event replication
- **Web UI**: Dashboard for entity/project monitoring

---

## 🤝 Contributing

Contributions welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/my-feature`)
3. Commit with `[ECOS-AUTO]` prefix (`git commit -m "[ECOS-AUTO] Add feature"`)
4. Push to branch (`git push origin feature/my-feature`)
5. Open a Pull Request

---

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.

---

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/gerivdb/KIVA-CLI/issues)
- **Discussions**: [GitHub Discussions](https://github.com/gerivdb/KIVA-CLI/discussions)
- **Maintainer**: [@gerivdb](https://github.com/gerivdb)

---

**KIVA-CLI** | **φ-CPS: 4.398** | **Version: 0.3.0** | **ECOS Ecosystem-1**
