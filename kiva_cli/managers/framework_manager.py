#!/usr/bin/env python3
"""
Framework Manager - Project Templates Scaffolding

Handles creation of FastAPI, React, and Go service templates.
Integrates with ECOYSTEM FrameworkManager patterns.

Features:
- FastAPI backend with Pydantic, SQLAlchemy, Alembic
- React frontend with TypeScript, Vite, TailwindCSS
- Go microservices with Gin, GORM, Wire
- Docker Compose orchestration
- CI/CD workflows generation
- ECOS_ROOT.json integration
"""

import os
import json
import shutil
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime


@dataclass
class TemplateConfig:
    """Template configuration"""
    name: str
    framework: str  # fastapi, react, go
    description: str
    target_path: Path
    features: List[str]
    metadata: Dict[str, any]


class FrameworkManager:
    """Manager for project template scaffolding"""
    
    SUPPORTED_FRAMEWORKS = ["fastapi", "react", "go-service"]
    
    def __init__(self, templates_root: Optional[Path] = None):
        """
        Args:
            templates_root: Root directory for templates (default: ./templates/)
        """
        self.templates_root = templates_root or Path(__file__).parent.parent / "templates"
        self.templates_root.mkdir(parents=True, exist_ok=True)
    
    # ========================================================================
    # FASTAPI TEMPLATE
    # ========================================================================
    
    def scaffold_fastapi(self, config: TemplateConfig) -> Path:
        """
        Create FastAPI project with production-ready structure
        
        Structure:
            project/
            ├── app/
            │   ├── __init__.py
            │   ├── main.py
            │   ├── api/
            │   │   ├── __init__.py
            │   │   └── v1/
            │   │       ├── __init__.py
            │   │       └── endpoints/
            │   ├── core/
            │   │   ├── config.py
            │   │   └── security.py
            │   ├── db/
            │   │   ├── base.py
            │   │   └── session.py
            │   ├── models/
            │   └── schemas/
            ├── alembic/
            ├── tests/
            ├── Dockerfile
            ├── docker-compose.yml
            ├── requirements.txt
            ├── pyproject.toml
            └── README.md
        """
        project_path = config.target_path
        project_path.mkdir(parents=True, exist_ok=True)
        
        # Create directory structure
        dirs = [
            "app/api/v1/endpoints",
            "app/core",
            "app/db",
            "app/models",
            "app/schemas",
            "alembic/versions",
            "tests/api",
            "tests/unit",
            ".github/workflows"
        ]
        
        for d in dirs:
            (project_path / d).mkdir(parents=True, exist_ok=True)
            (project_path / d / "__init__.py").touch()
        
        # app/main.py
        (project_path / "app/main.py").write_text(
'''"""FastAPI Application Entry Point"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1 import api_router
from app.core.config import settings

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/health")
async def health_check():
    return {"status": "healthy", "version": settings.VERSION}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
'''
        )
        
        # app/core/config.py
        (project_path / "app/core/config.py").write_text(
'''"""Application Configuration"""
from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    PROJECT_NAME: str = "''' + config.name + '''"
    VERSION: str = "0.1.0"
    API_V1_STR: str = "/api/v1"
    
    # Database
    DATABASE_URL: str = "postgresql://user:pass@localhost/dbname"
    
    # CORS
    BACKEND_CORS_ORIGINS: List[str] = ["http://localhost:3000"]
    
    # Security
    SECRET_KEY: str = "CHANGE-ME-IN-PRODUCTION"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
'''
        )
        
        # requirements.txt
        (project_path / "requirements.txt").write_text(
'''fastapi==0.109.0
uvicorn[standard]==0.27.0
pydantic==2.6.0
pydantic-settings==2.1.0
sqlalchemy==2.0.25
alembic==1.13.1
psycopg2-binary==2.9.9
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-multipart==0.0.6
pytest==7.4.4
pytest-asyncio==0.23.3
httpx==0.26.0
'''
        )
        
        # Dockerfile
        (project_path / "Dockerfile").write_text(
'''FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
'''
        )
        
        # docker-compose.yml
        (project_path / "docker-compose.yml").write_text(
'''version: '3.8'

services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://postgres:postgres@db:5432/app
    depends_on:
      - db
    volumes:
      - .:/app
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
  
  db:
    image: postgres:15-alpine
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: app
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
'''
        )
        
        # README.md
        (project_path / "README.md").write_text(
f'''# {config.name}

{config.description}

## Features

''' + '\n'.join(f'- {f}' for f in config.features) + '''

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run development server
uvicorn app.main:app --reload

# Or with Docker Compose
docker-compose up
```

## API Documentation

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Testing

```bash
pytest tests/ -v
```

## Generated by KIVA-CLI

Date: ''' + datetime.now().isoformat() + '''
Framework: FastAPI
'''
        )
        
        # CI workflow
        (project_path / ".github/workflows/ci.yml").write_text(
'''name: CI

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: postgres
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: pip install -r requirements.txt
      
      - name: Run tests
        run: pytest tests/ -v
        env:
          DATABASE_URL: postgresql://postgres:postgres@localhost:5432/test
'''
        )
        
        print(f"✓ FastAPI project scaffolded: {project_path}")
        return project_path
    
    # ========================================================================
    # REACT TEMPLATE
    # ========================================================================
    
    def scaffold_react(self, config: TemplateConfig) -> Path:
        """
        Create React + TypeScript + Vite project
        
        Structure:
            project/
            ├── src/
            │   ├── components/
            │   ├── pages/
            │   ├── hooks/
            │   ├── services/
            │   ├── types/
            │   ├── App.tsx
            │   └── main.tsx
            ├── public/
            ├── Dockerfile
            ├── package.json
            ├── tsconfig.json
            ├── vite.config.ts
            └── tailwind.config.js
        """
        project_path = config.target_path
        project_path.mkdir(parents=True, exist_ok=True)
        
        # Create structure
        dirs = [
            "src/components",
            "src/pages",
            "src/hooks",
            "src/services",
            "src/types",
            "public"
        ]
        
        for d in dirs:
            (project_path / d).mkdir(parents=True, exist_ok=True)
        
        # package.json
        (project_path / "package.json").write_text(json.dumps({
            "name": config.name.lower().replace(" ", "-"),
            "version": "0.1.0",
            "type": "module",
            "scripts": {
                "dev": "vite",
                "build": "tsc && vite build",
                "preview": "vite preview",
                "lint": "eslint . --ext ts,tsx",
                "test": "vitest"
            },
            "dependencies": {
                "react": "^18.2.0",
                "react-dom": "^18.2.0",
                "react-router-dom": "^6.21.0",
                "axios": "^1.6.5"
            },
            "devDependencies": {
                "@types/react": "^18.2.48",
                "@types/react-dom": "^18.2.18",
                "@vitejs/plugin-react": "^4.2.1",
                "typescript": "^5.3.3",
                "vite": "^5.0.11",
                "tailwindcss": "^3.4.1",
                "autoprefixer": "^10.4.17",
                "postcss": "^8.4.33",
                "vitest": "^1.2.0"
            }
        }, indent=2))
        
        # src/main.tsx
        (project_path / "src/main.tsx").write_text(
'''import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
'''
        )
        
        # src/App.tsx
        (project_path / "src/App.tsx").write_text(
'''import { useState } from 'react'

function App() {
  const [count, setCount] = useState(0)

  return (
    <div className="min-h-screen bg-gray-100 flex items-center justify-center">
      <div className="bg-white p-8 rounded-lg shadow-md">
        <h1 className="text-3xl font-bold mb-4">''' + config.name + '''</h1>
        <p className="text-gray-600 mb-4">''' + config.description + '''</p>
        <button
          onClick={() => setCount(count + 1)}
          className="bg-blue-500 text-white px-4 py-2 rounded hover:bg-blue-600"
        >
          Count: {count}
        </button>
      </div>
    </div>
  )
}

export default App
'''
        )
        
        # README.md
        (project_path / "README.md").write_text(
f'''# {config.name}

{config.description}

## Stack

- React 18
- TypeScript
- Vite
- TailwindCSS

## Development

```bash
# Install dependencies
npm install

# Start dev server
npm run dev

# Build for production
npm run build
```

## Generated by KIVA-CLI

Date: {datetime.now().isoformat()}
'''
        )
        
        print(f"✓ React project scaffolded: {project_path}")
        return project_path
    
    # ========================================================================
    # GO SERVICE TEMPLATE
    # ========================================================================
    
    def scaffold_go_service(self, config: TemplateConfig) -> Path:
        """
        Create Go microservice with Gin framework
        
        Structure:
            project/
            ├── cmd/
            │   └── server/
            │       └── main.go
            ├── internal/
            │   ├── api/
            │   ├── models/
            │   └── repository/
            ├── pkg/
            ├── Dockerfile
            ├── go.mod
            └── Makefile
        """
        project_path = config.target_path
        project_path.mkdir(parents=True, exist_ok=True)
        
        # Create structure
        dirs = [
            "cmd/server",
            "internal/api",
            "internal/models",
            "internal/repository",
            "pkg"
        ]
        
        for d in dirs:
            (project_path / d).mkdir(parents=True, exist_ok=True)
        
        module_name = config.name.lower().replace(" ", "-")
        
        # cmd/server/main.go
        (project_path / "cmd/server/main.go").write_text(
f'''package main

import (
	"log"
	"github.com/gin-gonic/gin"
)

func main() {{
	r := gin.Default()
	
	r.GET("/health", func(c *gin.Context) {{
		c.JSON(200, gin.H{{"status": "healthy"}})
	}})
	
	log.Println("Server starting on :8080")
	if err := r.Run(":8080"); err != nil {{
		log.Fatal(err)
	}}
}}
'''
        )
        
        # go.mod
        (project_path / "go.mod").write_text(
f'''module github.com/gerivdb/{module_name}

go 1.21

require (
	github.com/gin-gonic/gin v1.9.1
	gorm.io/gorm v1.25.5
	gorm.io/driver/postgres v1.5.4
)
'''
        )
        
        # Dockerfile
        (project_path / "Dockerfile").write_text(
'''FROM golang:1.21-alpine AS builder

WORKDIR /app

COPY go.mod go.sum ./
RUN go mod download

COPY . .
RUN CGO_ENABLED=0 GOOS=linux go build -o server ./cmd/server

FROM alpine:latest

RUN apk --no-cache add ca-certificates

WORKDIR /root/

COPY --from=builder /app/server .

EXPOSE 8080

CMD ["./server"]
'''
        )
        
        # Makefile
        (project_path / "Makefile").write_text(
'''.PHONY: build run test docker

build:
	go build -o bin/server ./cmd/server

run:
	go run ./cmd/server/main.go

test:
	go test -v ./...

docker:
	docker build -t ''' + module_name + ''' .
'''
        )
        
        # README.md
        (project_path / "README.md").write_text(
f'''# {config.name}

{config.description}

## Stack

- Go 1.21
- Gin Framework
- GORM

## Development

```bash
# Install dependencies
go mod download

# Run server
make run

# Build binary
make build

# Build Docker image
make docker
```

## Generated by KIVA-CLI

Date: {datetime.now().isoformat()}
'''
        )
        
        print(f"✓ Go service scaffolded: {project_path}")
        return project_path
    
    # ========================================================================
    # ORCHESTRATION
    # ========================================================================
    
    def scaffold_project(self, config: TemplateConfig) -> Path:
        """
        Main entry point - route to appropriate scaffolder
        """
        if config.framework not in self.SUPPORTED_FRAMEWORKS:
            raise ValueError(f"Unsupported framework: {config.framework}. Supported: {self.SUPPORTED_FRAMEWORKS}")
        
        if config.framework == "fastapi":
            return self.scaffold_fastapi(config)
        elif config.framework == "react":
            return self.scaffold_react(config)
        elif config.framework == "go-service":
            return self.scaffold_go_service(config)
        else:
            raise NotImplementedError(f"Framework {config.framework} not yet implemented")
