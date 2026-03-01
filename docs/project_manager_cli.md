# ProjectManager CLI - Complete Reference

🚀 **Advanced Project Lifecycle Management for KIVA-CLI**

Integrated with ECOS H0 mode: Base-3 ternary validation + Base-4 lifecycle + φ-CPS tracking

---

## Overview

The ProjectManager CLI provides comprehensive project lifecycle orchestration:

- 🏗️ **Multi-framework scaffolding**: FastAPI, React, Go, Python libs, Docker Compose, LXC containers
- 🚀 **Deployment automation**: Docker, Kubernetes (K8s), LXC system containers
- ✅ **Base-3 ternary validation**: UNKNOWN / VALID / INVALID semantic states
- 🔄 **Base-4 lifecycle management**: GENESIS / ACTIVE / DEPRECATED / ARCHIVED
- 📈 **φ-CPS drift tracking**: Per-operation φ-CPS delta calculation
- 🔗 **IntentHash verification**: L0-L1 chain continuity tracking

---

## Installation

```bash
# Clone KIVA-CLI
git clone https://github.com/gerivdb/KIVA-CLI.git
cd KIVA-CLI

# Install with ProjectManager support
pip install -e .

# Verify installation
ecos project --help
```

---

## Commands

### 1. `ecos project scaffold` - Create New Project

🏗️ Scaffold new project from framework template.

**Syntax:**
```bash
ecos project scaffold <NAME> --framework <FRAMEWORK> [OPTIONS]
```

**Arguments:**
- `NAME`: Project name (lowercase, hyphen-separated recommended)

**Options:**
- `--framework`, `--fw`: **(REQUIRED)** Framework type
  - `fastapi` → Python FastAPI microservice
  - `react` → React frontend application
  - `go_service` → Go microservice
  - `python_lib` → Python library package
  - `docker_compose` → Docker Compose multi-service
  - `lxc_container` → LXC container configuration
- `--deps`: Additional dependencies (repeatable)
- `--workspace`: Workspace root directory

**Examples:**
```bash
# FastAPI microservice
ecos project scaffold my-api --framework fastapi

# React app with TypeScript + Redux
ecos project scaffold webapp --framework react \
  --deps typescript --deps redux

# Go microservice in custom workspace
ecos project scaffold svc --framework go_service \
  --workspace ~/projects

# Python library
ecos project scaffold mylib --framework python_lib \
  --deps pytest --deps black
```

**Output:**
```
🏗️  Scaffolding project 'my-api' [framework=fastapi]
────────────────────────────────────────────────────────────

✅ Project scaffolded successfully!

📊 PROJECT METADATA:
   📁 Location: /workspace/my-api
   🔗 IntentHash: 0x7E3A9F2D48B6C105
   📈 φ-CPS delta: +0.0180
   ✅ Validation: VALID
   🔄 Lifecycle: GENESIS

🎯 NEXT STEPS:
   cd /workspace/my-api
   pip install -r requirements.txt
   uvicorn main:app --reload

   Deploy with: ecos project deploy my-api --target docker
```

---

### 2. `ecos project deploy` - Deploy to Environment

🚀 Deploy project to target environment.

**Syntax:**
```bash
ecos project deploy <NAME> [OPTIONS]
```

**Arguments:**
- `NAME`: Project name (must exist in registry)

**Options:**
- `--target`, `-t`: Deployment target (default: `docker`)
  - `docker` → Containerize and build Docker image
  - `kubernetes` → Deploy to Kubernetes cluster (generates K8s manifests)
  - `lxc` → Deploy as LXC system container
- `--dry-run`: Validate deployment without executing
- `--workspace`: Workspace root directory

**Examples:**
```bash
# Deploy to Docker
ecos project deploy my-api --target docker

# Dry-run Kubernetes deployment
ecos project deploy webapp --target kubernetes --dry-run

# Deploy to LXC container
ecos project deploy legacy-svc --target lxc
```

**Output:**
```
🚀 Deploying 'my-api' to 'docker'
────────────────────────────────────────────────────────────

✅ Deployment successful!

📊 DEPLOYMENT METADATA:
   🎯 Target: docker
   🔗 IntentHash: 0x5D8F7B4A3E9C201A
   📈 φ-CPS delta: +0.0120
   ✅ Validation: VALID

📦 ARTIFACTS:
   • my-api:latest
   • Dockerfile
   • .dockerignore

🎉 Deployment completed successfully!

   Run container: docker run my-api:latest
```

---

### 3. `ecos project status` - Show Project Status

📊 Show comprehensive project status and metrics.

**Syntax:**
```bash
ecos project status <NAME> [OPTIONS]
```

**Arguments:**
- `NAME`: Project name

**Options:**
- `--workspace`: Workspace root directory

**Examples:**
```bash
# Show status
ecos project status my-api

# Status with custom workspace
ecos project status webapp --workspace ~/dev
```

**Output:**
```
📊 PROJECT STATUS: my-api
══════════════════════════════════════════════════════════════════════

🔧 CONFIGURATION:
   Framework: fastapi
   Lifecycle: ACTIVE
   Validation: ✅ VALID

📈 METRICS:
   IntentHash: 0x7E3A9F2D48B6C105
   φ-CPS cumulative Δ: +0.0300

🚀 DEPLOYMENTS:
   1. docker
   2. kubernetes

📅 HISTORY:
   Created: 2026-03-01T00:15:00Z
   Updated: 2026-03-01T01:30:00Z
```

---

### 4. `ecos project list` - List All Projects

📋 List all registered projects with optional filters.

**Syntax:**
```bash
ecos project list [OPTIONS]
```

**Options:**
- `--framework`, `--fw`: Filter by framework type
- `--lifecycle`, `--state`: Filter by lifecycle state
- `--workspace`: Workspace root directory

**Examples:**
```bash
# List all projects
ecos project list

# Filter by FastAPI framework
ecos project list --framework fastapi

# Filter by ACTIVE lifecycle
ecos project list --lifecycle ACTIVE

# Combined filters
ecos project list --framework go_service --lifecycle DEPRECATED
```

**Output:**
```
📋 REGISTERED PROJECTS (3) [framework=fastapi]
════════════════════════════════════════════════════════════════════════════════

1. ✅ my-api
   Framework: fastapi
   State: ACTIVE | Validation: ✅ VALID
   φ-CPS Δ: +0.0300
   Deployed: docker, kubernetes

2. 🌱 test-api
   Framework: fastapi
   State: GENESIS | Validation: ✅ VALID
   φ-CPS Δ: +0.0180

3. ⚠️  legacy-api
   Framework: fastapi
   State: DEPRECATED | Validation: ❌ INVALID
   φ-CPS Δ: +0.0250
   Deployed: docker
```

---

### 5. `ecos project lifecycle` - Manage Lifecycle State

🔄 Transition project to new lifecycle state (base-4).

**Syntax:**
```bash
ecos project lifecycle <NAME> <NEW_STATE> [OPTIONS]
```

**Arguments:**
- `NAME`: Project name
- `NEW_STATE`: Target lifecycle state
  - `GENESIS` → Initial state
  - `ACTIVE` → Production-ready
  - `DEPRECATED` → Legacy, maintenance-only
  - `ARCHIVED` → Terminal state (no transitions allowed)

**Options:**
- `--workspace`: Workspace root directory

**Valid Transitions:**
- GENESIS → ACTIVE | ARCHIVED
- ACTIVE → DEPRECATED | ARCHIVED
- DEPRECATED → ACTIVE | ARCHIVED
- ARCHIVED → *(terminal, no transitions)*

**Examples:**
```bash
# Transition to ACTIVE
ecos project lifecycle my-api ACTIVE

# Mark as DEPRECATED
ecos project lifecycle old-service DEPRECATED

# Archive legacy app
ecos project lifecycle legacy-app ARCHIVED
```

**Output:**
```
🔄 Transitioning 'my-api' to ACTIVE
────────────────────────────────────────────────────────────

✅ Lifecycle transitioned successfully!

📈 UPDATED METRICS:
   φ-CPS cumulative Δ: +0.0320
   Lifecycle: ACTIVE
```

---

## Base-3 Ternary Validation

**Semantic validation states:**

| State | Symbol | Meaning |
|-------|--------|--------|
| **UNKNOWN** | ❓ | Not yet validated or insufficient data |
| **VALID** | ✅ | Semantically correct, passes all checks |
| **INVALID** | ❌ | Semantic errors detected |

**Validation triggers:**
- Scaffold: Initial validation after project creation
- Deploy: Pre-deployment validation
- Manual: `ecos validate` command

**Example validation flow:**
```bash
# New project starts UNKNOWN
ecos project scaffold new-api --framework fastapi
# ↳ Validation: UNKNOWN (GENESIS state)

# First deployment triggers validation
ecos project deploy new-api --target docker
# ↳ Validation: VALID (all checks passed)

# Lifecycle transition requires VALID state
ecos project lifecycle new-api ACTIVE
# ↳ Only possible if validation = VALID
```

---

## Base-4 Lifecycle Management

**Lifecycle states:**

| State | Icon | Description | Transitions |
|-------|------|-------------|-------------|
| **GENESIS** | 🌱 | Initial scaffolded state | → ACTIVE, ARCHIVED |
| **ACTIVE** | ✅ | Production-ready | → DEPRECATED, ARCHIVED |
| **DEPRECATED** | ⚠️ | Legacy, maintenance-only | → ACTIVE, ARCHIVED |
| **ARCHIVED** | 📦 | Terminal state | *(no transitions)* |

**Lifecycle progression:**
```
GENESIS → ACTIVE → DEPRECATED → ARCHIVED
   │       │            │
   └───────┴────────────┴────────────────→ ARCHIVED
```

---

## φ-CPS Drift Tracking

**Per-operation φ-CPS delta:**

| Operation | Typical Δφ-CPS |
|-----------|----------------|
| Scaffold | +0.018 |
| Deploy | +0.012 |
| Lifecycle transition | +0.005 |
| Validation | +0.002 |

**Cumulative tracking:**
```bash
# Initial scaffold
ecos project scaffold my-api --framework fastapi
# φ-CPS Δ: +0.0180

# First deployment
ecos project deploy my-api --target docker
# φ-CPS cumulative Δ: +0.0300

# Lifecycle transition
ecos project lifecycle my-api ACTIVE
# φ-CPS cumulative Δ: +0.0350

# Check drift
ecos phi check-drift
# If Δ > 0.05 (5%) → Auto-rollback triggered
```

---

## IntentHash L0-L1 Verification

**IntentHash format:** `0x<16-char HEX>`

**Example:**
```
0x7E3A9F2D48B6C105
```

**Verification:**
```bash
# Verify IntentHash chain continuity
ecos intenthash verify --project my-api

# Output:
# ✅ IntentHash chain VALID
#    L0: 0x7E3A9F2D48B6C105 (scaffold)
#    L1: 0x5D8F7B4A3E9C201A (deploy)
#    Chain continuity: VERIFIED
```

---

## Integration with ECOS Workflow

**Full H0 workflow:**

```bash
# 1. Scaffold project
ecos project scaffold my-service --framework fastapi

# 2. Develop code (manually)
cd my-service/
vim main.py

# 3. Validate semantically
ecos validate --project my-service

# 4. Deploy to Docker
ecos project deploy my-service --target docker

# 5. Transition to ACTIVE
ecos project lifecycle my-service ACTIVE

# 6. Check φ-CPS drift
ecos phi check-drift

# 7. Push to GitHub (if integrated)
ecos github push --project my-service \
  --message "[ECOS-AUTO] Initial release"

# 8. Update ECOS_ROOT.json
ecos phi prepare-reset  # If drift > 5%
```

---

## Troubleshooting

### Common Errors

#### 1. **Project not found**
```
❌ Project 'xyz' not found in registry
```
**Solution:**
```bash
ecos project list  # Check available projects
```

#### 2. **Invalid lifecycle transition**
```
❌ Invalid transition: ARCHIVED → ACTIVE
```
**Solution:** ARCHIVED is terminal state, no transitions allowed.

#### 3. **Validation failed**
```
❌ Validation state: INVALID
```
**Solution:**
```bash
ecos project status <name>  # Check details
ecos validate --project <name> --audit comprehensive
```

#### 4. **φ-CPS drift exceeded**
```
⚠️  φ-CPS drift: +0.067 (> 0.05 threshold)
```
**Solution:**
```bash
ecos phi prepare-reset  # Prepare baseline reset
ecos phi execute-reset  # Execute after approval
```

---

## See Also

- **ECOS Validation**: `docs/ecos_validation.md`
- **Lifecycle Management**: `docs/lifecycle_management.md`
- **φ-CPS Tracking**: `docs/phi_cps_tracking.md`
- **IntentHash Specification**: `docs/intenthash_spec.md`

---

**Last Updated:** 2026-03-01  
**ECOS Version:** H0 (Base-3/4 ternary + lifecycle)  
**φ-CPS Baseline:** 4.261
