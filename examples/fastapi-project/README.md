# KIVA Example: FastAPI REST API

## Initialize Project

```bash
kiva project my-api --template fastapi
cd my-api
```

## Generated Structure

```
my-api/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI app entry
│   ├── api/
│   │   ├── __init__.py
│   │   └── routes.py        # API endpoints
│   ├── models/
│   │   ├── __init__.py
│   │   └── user.py          # Pydantic models
│   ├── services/
│   │   ├── __init__.py
│   │   └── user_service.py  # Business logic
│   └── core/
│       ├── __init__.py
│       ├── config.py        # Settings
│       └── database.py      # DB connection
├── tests/
│   ├── __init__.py
│   ├── test_api.py
│   └── test_services.py
├── kiva.yaml
├── requirements.txt
├── .env.example
└── README.md
```

## Configuration (kiva.yaml)

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
    dev: recreate
    staging: rolling
    production: blue-green
  
  health_checks:
    enabled: true
    path: /health
    timeout: 30s
    interval: 10s
```

## Run Locally

```bash
# Install dependencies
pip install -r requirements.txt

# Run development server
uvicorn app.main:app --reload --port 8000

# Access API
curl http://localhost:8000/docs  # Swagger UI
```

## Deploy

```bash
# Staging deployment (dry-run)
kiva deploy . --env staging --dry-run

# Staging deployment (execute)
kiva deploy . --env staging

# Production deployment (blue-green)
kiva deploy . --env production --strategy blue-green
```

## Test

```bash
# Run tests
pytest

# With coverage
pytest --cov=app --cov-report=html
```
