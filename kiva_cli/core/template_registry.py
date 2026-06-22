"""Template registry for project scaffolding.

Supports FastAPI, React, Go, Rust with customizable parameters.
Templates include: structure, dependencies, CI/CD, Docker, tests.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field


@dataclass
class Template:
    """Project template definition."""
    
    name: str
    language: str
    framework: Optional[str]
    description: str
    files: Dict[str, str] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)
    dev_dependencies: List[str] = field(default_factory=list)
    scripts: Dict[str, str] = field(default_factory=dict)
    env_vars: List[str] = field(default_factory=list)
    docker_support: bool = True
    ci_cd_support: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize template to dictionary."""
        return {
            "name": self.name,
            "language": self.language,
            "framework": self.framework,
            "description": self.description,
            "dependencies": self.dependencies,
            "dev_dependencies": self.dev_dependencies,
            "scripts": self.scripts,
            "env_vars": self.env_vars,
            "docker_support": self.docker_support,
            "ci_cd_support": self.ci_cd_support,
        }


class TemplateRegistry:
    """Central registry for project templates."""
    
    def __init__(self):
        self.templates: Dict[str, Template] = {}
        self._register_builtin_templates()
    
    def _register_builtin_templates(self) -> None:
        """Register built-in templates (FastAPI, React, Go, Rust)."""
        
        # FastAPI Template
        self.register(
            Template(
                name="fastapi",
                language="python",
                framework="FastAPI",
                description="FastAPI REST API with SQLAlchemy, Alembic, pytest",
                files={
                    "main.py": 'from fastapi import FastAPI\n\napp = FastAPI()\n\n@app.get("/")\ndef read_root():\n    return {"status": "ok"}',
                    "requirements.txt": "fastapi==0.110.0\nuvicorn[standard]==0.27.1\nsqlalchemy==2.0.27\nalembic==1.13.1\npydantic==2.6.1\npydantic-settings==2.1.0\npytest==8.0.0\nhttpx==0.26.0",
                    "Dockerfile": "FROM python:3.12-slim\nWORKDIR /app\nCOPY requirements.txt .\nRUN pip install --no-cache-dir -r requirements.txt\nCOPY . .\nEXPOSE 8000\nCMD [\"uvicorn\", \"main:app\", \"--host\", \"0.0.0.0\", \"--port\", \"8000\"]",
                    ".env.example": "DATABASE_URL=postgresql://user:pass@localhost:5432/db\nSECRET_KEY=change-me\nENVIRONMENT=development",
                },
                dependencies=["fastapi", "uvicorn", "sqlalchemy", "alembic", "pydantic"],
                dev_dependencies=["pytest", "httpx", "black", "ruff"],
                scripts={
                    "dev": "uvicorn main:app --reload",
                    "test": "pytest tests/ -v",
                    "lint": "ruff check . && black --check .",
                    "format": "black . && ruff check --fix .",
                },
                env_vars=["DATABASE_URL", "SECRET_KEY", "ENVIRONMENT"],
            )
        )
        
        # React Template
        self.register(
            Template(
                name="react",
                language="typescript",
                framework="React",
                description="React + TypeScript + Vite + TailwindCSS",
                files={
                    "package.json": json.dumps({
                        "name": "react-app",
                        "version": "0.1.0",
                        "type": "module",
                        "scripts": {
                            "dev": "vite",
                            "build": "tsc && vite build",
                            "preview": "vite preview",
                            "test": "vitest",
                            "lint": "eslint . --ext ts,tsx",
                        },
                        "dependencies": {
                            "react": "^18.2.0",
                            "react-dom": "^18.2.0",
                        },
                        "devDependencies": {
                            "@types/react": "^18.2.56",
                            "@types/react-dom": "^18.2.19",
                            "@vitejs/plugin-react": "^4.2.1",
                            "typescript": "^5.3.3",
                            "vite": "^5.1.0",
                            "vitest": "^1.2.2",
                            "tailwindcss": "^3.4.1",
                        },
                    }, indent=2),
                    "index.html": '<!DOCTYPE html>\n<html lang="en">\n<head>\n  <meta charset="UTF-8" />\n  <meta name="viewport" content="width=device-width, initial-scale=1.0" />\n  <title>React App</title>\n</head>\n<body>\n  <div id="root"></div>\n  <script type="module" src="/src/main.tsx"></script>\n</body>\n</html>',
                    "Dockerfile": "FROM node:20-alpine AS build\nWORKDIR /app\nCOPY package*.json ./\nRUN npm ci\nCOPY . .\nRUN npm run build\n\nFROM nginx:alpine\nCOPY --from=build /app/dist /usr/share/nginx/html\nEXPOSE 80\nCMD [\"nginx\", \"-g\", \"daemon off;\"]",
                },
                dependencies=["react", "react-dom"],
                dev_dependencies=["vite", "typescript", "tailwindcss", "vitest"],
                scripts={
                    "dev": "vite",
                    "build": "tsc && vite build",
                    "test": "vitest",
                    "lint": "eslint .",
                },
            )
        )
        
        # Go Service Template
        self.register(
            Template(
                name="go-service",
                language="go",
                framework="Gin",
                description="Go microservice with Gin, GORM, Docker",
                files={
                    "main.go": 'package main\n\nimport "github.com/gin-gonic/gin"\n\nfunc main() {\n\tr := gin.Default()\n\tr.GET("/", func(c *gin.Context) {\n\t\tc.JSON(200, gin.H{"status": "ok"})\n\t})\n\tr.Run(":8080")\n}',
                    "go.mod": "module example.com/service\n\ngo 1.21\n\nrequire (\n\tgithub.com/gin-gonic/gin v1.9.1\n\tgorm.io/gorm v1.25.7\n\tgorm.io/driver/postgres v1.5.6\n)",
                    "Dockerfile": "FROM golang:1.21-alpine AS build\nWORKDIR /app\nCOPY go.* ./\nRUN go mod download\nCOPY . .\nRUN go build -o service main.go\n\nFROM alpine:latest\nRUN apk --no-cache add ca-certificates\nWORKDIR /root/\nCOPY --from=build /app/service .\nEXPOSE 8080\nCMD [\"./service\"]",
                    ".env.example": "DATABASE_URL=postgresql://user:pass@localhost:5432/db\nPORT=8080\nENVIRONMENT=development",
                },
                dependencies=["github.com/gin-gonic/gin", "gorm.io/gorm"],
                scripts={
                    "dev": "go run main.go",
                    "build": "go build -o service main.go",
                    "test": "go test ./... -v",
                },
                env_vars=["DATABASE_URL", "PORT", "ENVIRONMENT"],
            )
        )
        
        # Rust Service Template
        self.register(
            Template(
                name="rust-service",
                language="rust",
                framework="Actix-Web",
                description="Rust async service with Actix-Web, SQLx, Tokio",
                files={
                    "Cargo.toml": '[package]\nname = "rust-service"\nversion = "0.1.0"\nedition = "2021"\n\n[dependencies]\nactix-web = "4.5"\ntokio = { version = "1", features = ["full"] }\nserde = { version = "1.0", features = ["derive"] }\nsqlx = { version = "0.7", features = ["postgres", "runtime-tokio"] }\ndotenv = "0.15"',
                    "src/main.rs": 'use actix_web::{get, web, App, HttpServer, Responder};\n\n#[get("/")]\nasync fn index() -> impl Responder {\n    web::Json(serde_json::json!({"status": "ok"}))\n}\n\n#[actix_web::main]\nasync fn main() -> std::io::Result<()> {\n    HttpServer::new(|| App::new().service(index))\n        .bind(("0.0.0.0", 8080))?\n        .run()\n        .await\n}',
                    "Dockerfile": "FROM rust:1.75-alpine AS build\nWORKDIR /app\nCOPY Cargo.* ./\nCOPY src ./src\nRUN cargo build --release\n\nFROM alpine:latest\nRUN apk --no-cache add ca-certificates\nWORKDIR /root/\nCOPY --from=build /app/target/release/rust-service .\nEXPOSE 8080\nCMD [\"./rust-service\"]",
                },
                dependencies=["actix-web", "tokio", "serde", "sqlx"],
                scripts={
                    "dev": "cargo run",
                    "build": "cargo build --release",
                    "test": "cargo test",
                },
            )
        )
    
    def register(self, template: Template) -> None:
        """Register a new template."""
        self.templates[template.name] = template
    
    def get(self, name: str) -> Optional[Template]:
        """Get template by name."""
        return self.templates.get(name)
    
    def list_templates(self) -> List[str]:
        """List all available template names."""
        return list(self.templates.keys())
    
    def get_all(self) -> Dict[str, Template]:
        """Get all registered templates."""
        return self.templates.copy()
