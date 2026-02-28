# Integration Tests for Cross-Repo Sync

## Overview

Complete integration test suite for KIVA-CLI cross-repository synchronization, ensuring reliability and correctness of all sync operations.

## Test Structure

### Test Categories

#### 1. Sync Operations (`test_sync_operations`)
Tests core synchronization functionality:
- ECOS_ROOT.json sync between repositories
- WAL database synchronization
- Metrics synchronization
- Documentation synchronization
- Configuration synchronization

#### 2. Error Handling (`test_error_handling`)
Tests error scenarios and recovery:
- Network failure recovery with retries
- GitHub API rate limit handling
- Conflict resolution strategies
- Automatic rollback on failures
- Partial sync recovery

#### 3. Validation (`test_validation`)
Tests validation mechanisms:
- φ-CPS drift validation
- IntentHash chain integrity
- Base-3 ternary validation
- Manifest schema validation
- WAL database integrity checks

#### 4. Performance (`test_performance`)
Tests performance requirements:
- Batch operations performance (< 10s for 50 files)
- Large file handling (< 30s for 10MB)
- Concurrent sync operations
- Memory usage limits (< 100MB)
- Sync duration timeouts

## Running Tests

### Run All Integration Tests
```bash
pytest tests/integration/test_cross_repo_sync_integration.py -v
```

### Run Specific Category
```bash
# Sync operations only
pytest tests/integration/test_cross_repo_sync_integration.py::TestSyncOperations -v

# Error handling only
pytest tests/integration/test_cross_repo_sync_integration.py::TestErrorHandling -v

# Validation only
pytest tests/integration/test_cross_repo_sync_integration.py::TestValidation -v

# Performance only
pytest tests/integration/test_cross_repo_sync_integration.py::TestPerformance -v
```

### Run with Coverage
```bash
pytest tests/integration/test_cross_repo_sync_integration.py \
  --cov=kiva_cli \
  --cov-report=html \
  --cov-report=term-missing
```

### Run in Parallel
```bash
pytest tests/integration/test_cross_repo_sync_integration.py -n auto
```

### Run with Performance Profiling
```bash
pytest tests/integration/test_cross_repo_sync_integration.py \
  --benchmark-only \
  --benchmark-autosave
```

## Test Configuration

### pytest.ini
- **Coverage target**: 80% minimum
- **Timeout**: 300 seconds per test
- **Parallel execution**: Enabled with `-n auto`
- **Test discovery**: `test_*.py` pattern

### Environment Variables
```bash
# GitHub API token for real API tests
export GITHUB_TOKEN="your_token_here"

# Enable verbose logging
export KIVA_CLI_LOG_LEVEL="DEBUG"

# Test database path
export TEST_WAL_DB_PATH="/tmp/test_wal.db"
```

## Test Fixtures

### Common Fixtures
- `temp_dir`: Temporary directory for test files
- `mock_github_client`: Mocked GitHub API client
- `sample_ecos_root`: Sample ECOS_ROOT.json data
- `wal_database`: Test WAL database

## Expected Results

### Coverage Requirements
- **Overall**: ≥ 80%
- **Sync operations**: ≥ 90%
- **Error handling**: ≥ 85%
- **Validation**: ≥ 95%

### Performance Benchmarks
| Operation | Target | Acceptable |
|-----------|--------|------------|
| **Batch sync (50 files)** | < 5s | < 10s |
| **Large file (10MB)** | < 15s | < 30s |
| **Concurrent sync (20 ops)** | < 3s | < 5s |
| **Memory usage** | < 50MB | < 100MB |

## CI/CD Integration

### GitHub Actions
Automated test execution on:
- **Push to main/develop**: Full test suite
- **Pull requests**: Full test suite + coverage report
- **Daily schedule**: 3 AM UTC
- **Manual dispatch**: On demand

### Test Report Artifacts
- `test-results.xml`: JUnit XML format
- `coverage.xml`: Coverage report
- `htmlcov/`: HTML coverage report

## Troubleshooting

### Test Failures

#### Network-related Failures
```bash
# Increase timeout
pytest --timeout=600

# Skip slow tests
pytest -m "not slow"
```

#### Coverage Failures
```bash
# Check coverage report
coverage report --show-missing

# Generate HTML report
coverage html
open htmlcov/index.html
```

#### Performance Failures
```bash
# Run performance tests only
pytest -m performance --benchmark-only

# Skip performance tests
pytest -m "not performance"
```

## Best Practices

1. **Isolation**: Each test is independent and isolated
2. **Mocking**: External APIs are mocked by default
3. **Cleanup**: Temporary resources are cleaned up automatically
4. **Fixtures**: Reusable test fixtures for common setups
5. **Assertions**: Clear, descriptive assertion messages
6. **Coverage**: Aim for 100% coverage of critical paths

## φ-CPS Impact

Expected φ-CPS delta: **+0.002**

Rationale:
- Test coverage: +0.001 (improves reliability)
- Error handling: +0.0005 (reduces failure risk)
- Performance validation: +0.0005 (ensures scalability)

## Next Steps

1. ✅ Implement test suite
2. ✅ Create pytest configuration
3. ✅ Add GitHub Actions workflow
4. ⏳ Run initial test execution
5. ⏳ Fix any failing tests
6. ⏳ Achieve 80% coverage target
7. ⏳ Document test results
