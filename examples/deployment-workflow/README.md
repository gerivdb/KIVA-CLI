# KIVA Example: Multi-Environment Deployment Workflow

## Scenario

Deploy FastAPI application across 3 environments (dev → staging → production) with different strategies.

## Setup

```bash
# Initialize project
kiva project payment-api --template fastapi
cd payment-api

# Configure kiva.yaml
cat > kiva.yaml << EOF
project:
  name: payment-api
  version: 1.0.0
  template: fastapi

deployment:
  environments:
    - dev
    - staging
    - production
  
  strategies:
    dev: recreate
    staging: rolling
    production: blue-green
  
  health_checks:
    enabled: true
    path: /health
    timeout: 30s
    interval: 10s
    retries: 3
EOF
```

## Deployment Pipeline

### 1. Development Environment

```bash
# Deploy to dev (recreate strategy)
kiva deploy . --env dev

# Verification
curl https://dev.payment-api.example.com/health
```

### 2. Staging Environment

```bash
# Dry-run first (validate configuration)
kiva deploy . --env staging --dry-run

# Deploy with rolling strategy (zero-downtime)
kiva deploy . --env staging --strategy rolling

# Monitor deployment
kiva status payment-api --env staging

# Verification
curl https://staging.payment-api.example.com/health
```

### 3. Production Environment

```bash
# Dry-run with blue-green strategy
kiva deploy . --env production --dry-run --strategy blue-green

# Production deployment (blue-green)
kiva deploy . --env production --strategy blue-green

# Traffic is switched only after health checks pass

# Verification
curl https://payment-api.example.com/health
curl https://payment-api.example.com/metrics
```

## Rollback Scenarios

### Scenario A: Rollback Staging (Automatic)

```bash
# Deploy fails health checks → automatic rollback
kiva deploy . --env staging
# Output: Health check failed, rolling back to version 0.9.0
```

### Scenario B: Manual Rollback Production

```bash
# Issue detected after production deployment
kiva rollback payment-api --env production

# Rollback to specific version
kiva rollback payment-api --env production --version 0.9.0
```

## CI/CD Integration

```yaml
# .github/workflows/deploy.yml
name: Deploy Pipeline

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Install KIVA CLI
        run: |
          pip install kiva-cli
      
      - name: Deploy to Staging
        run: |
          kiva deploy . --env staging --strategy rolling
      
      - name: Integration Tests
        run: |
          pytest tests/integration/
      
      - name: Deploy to Production
        if: success()
        run: |
          kiva deploy . --env production --strategy blue-green
      
      - name: Rollback on Failure
        if: failure()
        run: |
          kiva rollback payment-api --env production
```

## Monitoring

```bash
# Check deployment status
kiva status payment-api --env production

# View deployment history
kiva history payment-api --env production --limit 10

# Health check
kiva health payment-api --env production
```
