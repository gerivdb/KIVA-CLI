# FrameworkManager Documentation

## Overview

FrameworkManager handles project scaffolding from production-ready templates for multiple frameworks:

- **FastAPI** - Python backend with PostgreSQL, Alembic migrations, Pydantic
- **React** - TypeScript frontend with Vite, TailwindCSS, React Router
- **Go Services** - Microservices with Gin, GORM, Wire dependency injection

## Installation

```bash
# Install KIVA-CLI
pip install -e .

# Verify installation
kiva scaffold list
```

## Quick Start

### FastAPI Backend

```bash
# Create new FastAPI project
kiva scaffold fastapi my-api \
  --description "User management service" \
  --features "auth,db,docs,celery" \
  --output ./services/

# Navigate and run
cd services/my-api
pip install -r requirements.txt
uvicorn app.main:app --reload

# Access docs
open http://localhost:8000/docs
```

### React Frontend

```bash
# Create new React app
kiva scaffold react my-app \
  --description "Admin dashboard" \
  --features "routing,state-management,auth" \
  --output ./apps/

# Navigate and run
cd apps/my-app
npm install
npm run dev

# Access app
open http://localhost:5173
```

### Go Microservice

```bash
# Create new Go service
kiva scaffold go-service payment-svc \
  --description "Payment processing service" \
  --features "api,db,grpc" \
  --output ./services/

# Navigate and run
cd services/payment-svc
go mod download
make run

# Test health endpoint
curl http://localhost:8080/health
```

## Project Structures

### FastAPI Structure

```
my-api/
├── app/
│   ├── __init__.py
│   ├── main.py              # Application entry point
│   ├── api/
│   │   └── v1/
│   │       ├── __init__.py
│   │       └── endpoints/   # API route handlers
│   ├── core/
│   │   ├── config.py        # Settings management
│   │   └── security.py      # Auth utilities
│   ├── db/
│   │   ├── base.py          # SQLAlchemy Base
│   │   └── session.py       # DB session factory
│   ├── models/              # SQLAlchemy models
│   └── schemas/             # Pydantic schemas
├── alembic/
│   └── versions/            # Database migrations
├── tests/
│   ├── api/                 # API tests
│   └── unit/                # Unit tests
├── .github/
│   └── workflows/
│       └── ci.yml           # GitHub Actions CI
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── pyproject.toml
└── README.md
```

**Key Features**:
- OpenAPI/Swagger documentation auto-generated
- CORS middleware pre-configured
- PostgreSQL with SQLAlchemy ORM
- Alembic migrations ready
- Pytest test structure
- Docker & Docker Compose ready
- GitHub Actions CI/CD

### React Structure

```
my-app/
├── src/
│   ├── components/          # Reusable components
│   ├── pages/               # Route pages
│   ├── hooks/               # Custom React hooks
│   ├── services/            # API clients
│   ├── types/               # TypeScript types
│   ├── App.tsx              # Main app component
│   └── main.tsx             # Entry point
├── public/                  # Static assets
├── package.json
├── tsconfig.json            # TypeScript config
├── vite.config.ts           # Vite config
├── tailwind.config.js       # TailwindCSS config
└── README.md
```

**Key Features**:
- TypeScript strict mode
- Vite for fast HMR
- TailwindCSS utility-first CSS
- React Router v6
- Axios HTTP client
- Vitest for testing
- ESLint configured

### Go Service Structure

```
my-service/
├── cmd/
│   └── server/
│       └── main.go          # Entry point
├── internal/
│   ├── api/                 # HTTP handlers
│   ├── models/              # Domain models
│   └── repository/          # Data access layer
├── pkg/                     # Public packages
├── Dockerfile
├── go.mod
├── go.sum
├── Makefile
└── README.md
```

**Key Features**:
- Gin web framework
- GORM for database
- Standard project layout
- Multi-stage Docker build
- Makefile for common tasks
- Health check endpoint

## Configuration

### Template Config Object

```python
from kiva_cli.managers.framework_manager import TemplateConfig

config = TemplateConfig(
    name="my-project",
    framework="fastapi",  # fastapi | react | go-service
    description="Project description",
    target_path=Path("./output/my-project"),
    features=["auth", "db", "docs"],
    metadata={
        "version": "0.1.0",
        "author": "Your Name",
        "license": "MIT"
    }
)
```

### Available Features

#### FastAPI Features
- `auth` - JWT authentication setup
- `db` - PostgreSQL + SQLAlchemy + Alembic
- `docs` - Enhanced OpenAPI documentation
- `celery` - Background task queue
- `redis` - Redis cache integration

#### React Features
- `routing` - React Router setup
- `state-management` - Redux/Zustand integration
- `auth` - Authentication flow
- `forms` - React Hook Form
- `ui-library` - Material-UI or Ant Design

#### Go Features
- `api` - REST API endpoints
- `db` - GORM database integration
- `grpc` - gRPC server setup
- `auth` - JWT middleware
- `swagger` - Swagger documentation

## Programmatic Usage

```python
from pathlib import Path
from kiva_cli.managers.framework_manager import (
    FrameworkManager,
    TemplateConfig
)

# Initialize manager
manager = FrameworkManager()

# Create FastAPI project
fastapi_config = TemplateConfig(
    name="user-service",
    framework="fastapi",
    description="User management microservice",
    target_path=Path("./services/user-service"),
    features=["auth", "db", "docs"],
    metadata={"version": "1.0.0"}
)

project_path = manager.scaffold_project(fastapi_config)
print(f"Project created at: {project_path}")

# Create React app
react_config = TemplateConfig(
    name="admin-dashboard",
    framework="react",
    description="Admin dashboard application",
    target_path=Path("./apps/admin-dashboard"),
    features=["routing", "auth"],
    metadata={"version": "1.0.0"}
)

app_path = manager.scaffold_project(react_config)
print(f"App created at: {app_path}")
```

## CI/CD Integration

### FastAPI CI Workflow

Generated `.github/workflows/ci.yml`:

```yaml
name: CI
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: postgres
    
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: pip install -r requirements.txt
      
      - name: Run tests
        run: pytest tests/ -v
```

## Docker Deployment

### FastAPI

```bash
# Build and run with Docker Compose
cd my-api
docker-compose up -d

# Check logs
docker-compose logs -f api

# Run migrations
docker-compose exec api alembic upgrade head
```

### React

```bash
# Build production image
cd my-app
docker build -t my-app:latest .

# Run container
docker run -p 80:80 my-app:latest
```

### Go Service

```bash
# Build
cd my-service
docker build -t my-service:latest .

# Run
docker run -p 8080:8080 my-service:latest
```

## Testing

### FastAPI Tests

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=app --cov-report=html

# Run specific test file
pytest tests/api/test_users.py -v
```

### React Tests

```bash
# Run tests
npm test

# Run with coverage
npm run test:coverage

# Run in watch mode
npm run test:watch
```

### Go Tests

```bash
# Run tests
go test -v ./...

# Run with coverage
go test -v -coverprofile=coverage.out ./...
go tool cover -html=coverage.out
```

## Environment Variables

### FastAPI `.env`

```env
PROJECT_NAME=my-api
VERSION=0.1.0

# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/dbname

# Security
SECRET_KEY=your-secret-key-here
ACCESS_TOKEN_EXPIRE_MINUTES=30

# CORS
BACKEND_CORS_ORIGINS=["http://localhost:3000","http://localhost:5173"]
```

### React `.env`

```env
VITE_API_BASE_URL=http://localhost:8000
VITE_APP_NAME=My App
VITE_ENABLE_ANALYTICS=false
```

### Go `.env`

```env
PORT=8080
DATABASE_URL=postgres://user:pass@localhost:5432/dbname
JWT_SECRET=your-jwt-secret
ENVIRONMENT=development
```

## Troubleshooting

### FastAPI Issues

**Issue**: Alembic migrations fail
```bash
# Reset database
docker-compose down -v
docker-compose up -d db
alembic upgrade head
```

**Issue**: Import errors
```bash
# Reinstall dependencies
pip install --upgrade -r requirements.txt
```

### React Issues

**Issue**: Module not found
```bash
# Clear cache and reinstall
rm -rf node_modules package-lock.json
npm install
```

**Issue**: Vite port already in use
```bash
# Use different port
npm run dev -- --port 5174
```

### Go Issues

**Issue**: Module dependencies
```bash
# Tidy modules
go mod tidy
go mod download
```

**Issue**: Build fails
```bash
# Clean and rebuild
go clean
go build -v ./cmd/server
```

## Advanced Usage

### Custom Templates

```python
from pathlib import Path
from kiva_cli.managers.framework_manager import FrameworkManager

class CustomFrameworkManager(FrameworkManager):
    """Extended manager with custom templates"""
    
    def scaffold_django(self, config):
        """Custom Django scaffolder"""
        # Implementation
        pass

manager = CustomFrameworkManager()
```

### Template Customization

Override default templates by placing custom files in `~/.kiva/templates/`:

```
~/.kiva/templates/
├── fastapi/
│   ├── app/
│   └── custom_config.py
├── react/
│   └── src/
└── go-service/
    └── cmd/
```

## Integration with ECOYSTEM

FrameworkManager integrates with ECOYSTEM tools:

```python
# Auto-register in ECOS_ROOT.json
from kiva_cli.core.ecos_integration import register_project

project_path = manager.scaffold_project(config)
register_project(
    project_path=project_path,
    ecosystem_root=Path.home() / "ecos",
    phi_delta=0.012
)
```

## References

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [React Documentation](https://react.dev/)
- [Go Documentation](https://go.dev/doc/)
- [KIVA-CLI GitHub](https://github.com/gerivdb/KIVA-CLI)
- [ECOYSTEM Integration Guide](https://github.com/gerivdb/ECOYSTEM/blob/main/docs/INTEGRATION.md)

## Generated by KIVA-CLI

Date: 2026-02-28  
Version: 1.0.0  
IntentHash: 0x6C9D4E2F8A7B3E1C
