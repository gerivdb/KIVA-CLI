# Changelog

All notable changes to KIVA-CLI will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added — KIVA-010 S4 (close)
- `on_failure: notify` — new policy in Step/Pipeline: emits `PIPELINE_ALERT` WAL event `{step, error, retry_attempts}` (distinct from PIPELINE_RUN) and continues like `warn`. Enables future `kiva nexus drift check` (AC-K10-7).
- Loader + type system extended to accept `"notify"` (with validation).
- Exhaustive retry tests: timeout-as-failure + retry, notify emission verification, parallel/sequential total_retries_used, success on Nth attempt (AC-K10-8).
- Test surface: `test_pipeline_retry.py` now 8/8 (was 6); broader pipeline/parallel/retry matrix: 92 passed.

### Planned
- Multi-repo orchestration via ECOS Gateway
- Template hot-reload from external repos
- Deployment health monitoring dashboard
- Rollback history visualization

## [0.1.0-alpha] - 2026-02-28

### Added
- **ProjectManager**: Initialize, list, validate projects
- **DeploymentManager**: Deploy, rollback, list deployments
- **TemplateRegistry**: FastAPI, React, Go, Rust templates
- **ConfigValidator**: Base-3 validation (UNKNOWN/VALID/INVALID)
- **CLI Entrypoint**: `kiva` command with subcommands
- **Test Suite**: 20 tests (8 unit + 12 integration)
- **CI/CD Pipeline**: GitHub Actions (lint + test + coverage)
- **Documentation**: README, CONTRIBUTING, API reference
- **ECOS Integration**: Gateway delegation via subprocess

### Architecture
- Base-3 state machine: PENDING/SUCCESS/FAILED
- φ-CPS validation with auto-rollback (threshold: 0.05)
- IntentHash¹¹ for cryptographic integrity
- H0 autonomous mode (NO-HITL)

### Technical Details
- **Language**: Python 3.11+
- **Dependencies**: Stdlib only (no external deps)
- **Installation**: `pip install -e .`
- **Testing**: pytest + pytest-cov + pytest-mock
- **Linting**: Black + Ruff

### Commits
- `c374928`: feat(core): Implement ProjectManager + DeploymentManager
- `2d367c1`: feat(cli): Add executable wrapper + integration tests
- `[current]`: docs(complete): Add README + CI/CD + .clinerules

### IntentHash Tracking
- Phase 1A Complete: `0xH1_KIVA_P1A_COMPLETE_ALL_TASKS_DONE`
- Project Init: `0xH1_KIVA_P1A_T3T4_MANAGERS_COMPLETE`
- Tests Added: `0xH1_KIVA_P1A_T5T6_EXECUTABLE_TESTS_COMPLETE`

### φ-CPS Contribution
- Total Phase 1A: +0.025
- ProjectManager: +0.012
- DeploymentManager: +0.006
- Documentation: +0.007

## [0.0.0] - 2026-02-28

### Initial Commit
- Repository structure
- Basic CLI skeleton
- H0 autonomous mode activation

---

**Legend**:
- ✨ Added: New features
- 🐛 Fixed: Bug fixes
- ♻️ Changed: Breaking changes
- 🗑️ Deprecated: Soon-to-be removed
- 🚫 Removed: Deleted features
- 🔒 Security: Security patches
