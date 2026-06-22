# KIVA-CLI — User Guide

> **Version**: 1.0 | **Date**: 2026-06-14

## Overview

KIVA-CLI is the local CI/CD orchestration tool for the VERSES ecosystem. It runs declarative pipelines defined in `.kiva/pipelines/*.yaml`.

## Critical Rule: Working Directory

**KIVA always looks for `.kiva/pipelines/` in the current working directory.**

```powershell
# CORRECT: Run from KIVA-CLI directory
cd D:\DO\WEB\TOOLS\L1-INFRA\KIVA-CLI
kiva pipeline run verses-ci

# WRONG: Running from another directory
cd D:\DO\WEB\TOOLS\L0-CANON\ONTOLOGY
kiva pipeline run verses-ci  # Will FAIL: "No pipelines found"
```

**Why?** KIVA uses `Path(".kiva/pipelines")` relative to `os.getcwd()`. It does NOT use the module's installation path.

**Workaround**: Set an alias in your PowerShell profile:
```powershell
function kiva { Set-Location "D:\DO\WEB\TOOLS\L1-INFRA\KIVA-CLI"; python -m kiva_cli.kiva @args }
```

## Commands

```bash
# List all pipelines
kiva pipeline list

# Show pipeline details
kiva pipeline show verses-ci

# Validate pipeline YAML
kiva pipeline validate verses-ci

# Run a pipeline
kiva pipeline run verses-ci

# Run with verbose output
kiva pipeline run verses-ci --verbose
```

## Available Pipelines

| Pipeline | Steps | Purpose |
|----------|-------|---------|
| `verses-ci` | 7 | Hub structure + registry validation |
| `verses-spoke-ci` | 8 | Spoke validation against domain schemas |
| `verses-sync-ci` | 5 | Sync manager unit tests + performance |
| `verses-marketplace-ci` | 4 | Marketplace API tests |
| `verses-migration-ci` | 5 | Migration script + validation |
| `build` | 8 | Build, lint, test, package (demo) |

## Pipeline YAML Format

```yaml
name: my-pipeline
version: "1.0"
description: "What this pipeline does"
intent_hash: 0x...

on_failure: abort  # or "warn" to continue on failure
max_workers: 1     # parallel workers

steps:
  - name: step-name
    description: "What this step does"
    command: "python -c \"...\""
    depends_on: [previous-step]
    on_failure: abort
    retry: 0
```

## Tips

1. **Always run from KIVA-CLI directory** (see Critical Rule above)
2. **Use absolute paths** in commands — relative paths depend on cwd
3. **Set `max_workers: 1`** for sequential pipelines
4. **Use `on_failure: warn`** for non-critical checks (e.g., coverage)

---
*IntentHash: 0xKIVA_GUIDE_20260614*
