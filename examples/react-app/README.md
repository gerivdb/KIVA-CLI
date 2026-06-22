# KIVA Example: React TypeScript App

## Initialize Project

```bash
kiva project my-react-app --template react
cd my-react-app
```

## Generated Structure

```
my-react-app/
├── src/
│   ├── App.tsx
│   ├── main.tsx
│   ├── components/
│   │   └── HelloWorld.tsx
│   ├── hooks/
│   │   └── useCounter.ts
│   ├── styles/
│   │   └── App.css
│   └── types/
│       └── index.ts
├── public/
│   └── index.html
├── tests/
│   └── App.test.tsx
├── kiva.yaml
├── package.json
├── tsconfig.json
├── vite.config.ts
└── README.md
```

## Configuration (kiva.yaml)

```yaml
project:
  name: my-react-app
  version: 1.0.0
  template: react

deployment:
  environments:
    - dev
    - staging
    - production
  
  strategies:
    dev: recreate
    staging: rolling
    production: blue-green
  
  build:
    command: npm run build
    output_dir: dist
  
  health_checks:
    enabled: true
    path: /
    timeout: 10s
```

## Run Locally

```bash
# Install dependencies
npm install

# Development server
npm run dev

# Access app
open http://localhost:5173
```

## Build & Deploy

```bash
# Build for production
npm run build

# Deploy to staging
kiva deploy . --env staging

# Deploy to production (blue-green)
kiva deploy . --env production --strategy blue-green
```

## Test

```bash
# Run tests
npm test

# Coverage
npm run test:coverage
```

## Add Component

```bash
# Scaffold new component
kiva scaffold component UserProfile --project .

# Generates:
# src/components/UserProfile.tsx
# tests/UserProfile.test.tsx
```
