# DAG-3 — Triadic Graph Engine for gerivdb Ecosystem

## Overview

DAG-3 is a triadic graph engine that provides two core validation mechanisms for merge requests:

1. **ACM (Atomic Cycle Model)** - Detects atomic cycles in dependency graphs
2. **ADMR (Adjunction-driven Merge Request)** - Validates merge requests based on structural adjunctions

## Components

### ACM Detector (`acm_detector.py`)

Detects cycles in dependency graphs using NetworkX.

**Usage:**
```bash
python scripts/acm_detect.py --repo-path /path/to/repo
python scripts/acm_detect.py --validate-merge feature-branch main
```

**Features:**
- Scans Python files for import dependencies
- Detects simple cycles in the dependency graph
- Assesses cycle severity (LOW/MEDIUM/HIGH)
- Calculates φ-CPS impact

### ADMR Validator (`admr_validator.py`)

Validates merge requests based on multiple constraint types.

**Usage:**
```bash
python scripts/admr_validate.py --source feature-branch --target main
```

**Constraint Types:**
- **CYCLE** - Dependency cycle constraints
- **DEPENDENCY** - External dependency additions
- **INTERFACE** - Public API changes
- **ARCHITECTURE** - Core architecture modifications
- **SECURITY** - Security vulnerability detection
- **PERFORMANCE** - Performance impact analysis

### DAG3 Manager (`dag3_manager.py`)

Orchestrates ACM and ADMR validation.

**Usage:**
```bash
python scripts/dag3_validate.py --source feature-branch --target main
python scripts/dag3_validate.py --pre-check --source feature-branch --target main
```

## Integration with KIVA-CLI Merge Workflow

### New 5-Step Merge Sequence:

1. **DAG-3 Validation** (NEW) - ACM + ADMR before merge
2. CI local (kiva cicd run)
3. Atomic merge (gh pr merge)
4. WAL append + drift check
5. Citizen promotion

### CLI Usage:

```bash
# Standard merge with DAG-3 validation
kiva merge pr REPO PR_NUMBER source-branch

# Skip DAG-3 validation (HITL only)
kiva merge pr REPO PR_NUMBER source-branch --skip-dag3

# Hotfix mode (CI bypassed, DAG-3 still runs)
kiva merge pr REPO PR_NUMBER source-branch --hotfix
```

## Intent Hashes

- ACM Detector: `0xACM_DETECTOR_20260718`
- ADMR Validator: `0xADMR_VALIDATOR_20260718`
- DAG3 Manager: `0xDAG3_MANAGER_20260718`
- Merge Integration: `0xKIVA_MERGE_SOVEREIGN_phi4559`

## KEEL Gates Integration

DAG-3 integrates with KEEL gates:
- **R6** - Cycle constraints (via ACM)
- **R9** - Dependency constraints (via ADMR)
- **R10** - HITL approval gate (via ADMR)

## φ-CPS Impact

The φ-CPS (Phi Cognitive Performance Score) impact is calculated based on:
- Number of cycles detected
- Severity of violations
- Type of constraints violated

Impact ranges from 0.0 (no impact) to 1.0 (critical impact).