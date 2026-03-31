# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Adelaide Weather Forecasting System — a production weather forecasting platform using FAISS-based analog pattern matching. Python 3.11 FastAPI backend, Next.js 14 TypeScript frontend, containerized with Docker and deployed to AWS EKS via Helm/Terraform.

## Common Commands

### Backend (Python)

```bash
# Run all tests with coverage
python -m pytest api/ --cov=api -v

# Run core tests
python -m pytest tests/ -v

# Run a single test file
python -m pytest api/test_main.py -v

# Run tests by marker (unit, integration, security, performance, slow)
python -m pytest -m unit
python -m pytest -m "not slow"

# Lint
flake8 api/ core/
black --check api/ core/
isort --check-only api/ core/

# Format
black api/ core/
isort api/ core/

# Type checking
mypy api/ core/
```

### Frontend (`frontend/`)

```bash
cd frontend
npm run dev              # Dev server
npm run build            # Production build (runs type-check first)
npm run lint:strict      # ESLint with zero warnings allowed
npm run type-check:strict
npm run test             # Jest
npm run test:coverage    # Jest with coverage
npm run test:pact        # Contract tests
npm run ci:all           # Full pipeline: lint -> typecheck -> test -> build -> audit
```

### Docker

```bash
docker-compose up -d                        # Core stack: API + UI + Nginx
docker-compose --profile monitoring up -d   # With Prometheus + Grafana
docker-compose -f docker-compose.lite.yml up -d  # Minimal: API + UI only
```

### Health Checks

```bash
curl http://localhost:8000/health           # API health
curl http://localhost:8000/health/faiss      # FAISS index health
curl http://localhost:8000/metrics           # Prometheus metrics
```

## Architecture

### Three-Layer Stack

- **`api/`** — FastAPI backend. Entry point is `api/main.py` (large file, ~50KB). Middleware stack: GZip, Security (input sanitization), CORS, Rate Limiting (slowapi), Request Logging. Auth is Bearer token via `API_TOKEN` env var.
- **`core/`** — Forecasting engine. `analog_forecaster.py` runs real-time ensemble forecasting with uncertainty quantification. `model_loader.py` loads the CNN encoder (FiLM conditioning + ASPP). `device_manager.py` auto-detects GPU/CPU (env vars: `FAISS_GPU_ENABLED`, `FAISS_FORCE_CPU`).
- **`frontend/`** — Next.js 14, React 18, TypeScript 5.3, TailwindCSS, Recharts for charts, TanStack Query + SWR for data fetching, Radix UI components.

### FAISS Pipeline

1. CNN encoder produces 256-dim L2-normalized embeddings from weather patterns
2. Per-horizon FAISS indices (6h, 12h, 24h, 48h) stored as binary files in `indices/`
3. Query: real-time pattern -> cosine similarity search -> K=100 nearest neighbors
4. Softmax weighting (temperature=0.2) -> weighted mean forecast + empirical quantiles (q10, q50, q90)
5. Service layer: `api/services/analog_search.py` wraps FAISS with async, connection pooling (size=2), 5s timeout, and health monitoring

### API Services (`api/services/`)

- `analog_search.py` — Async FAISS wrapper with pooling/retry
- `faiss_health_monitoring.py` — Real-time query metrics, Prometheus integration
- `enhanced_analog_search.py` — Extended search with filtering

### Variable System

`api/variables.py` defines canonical `VARIABLE_ORDER` and `VARIABLE_SPECS` — the single source of truth for variable names, storage units (K, m/s, Pa) vs display units, and valid ranges. API and UI must stay consistent through this.

### Observability

Structured logging via `structlog` with separate loggers: `structured_logger`, `security_logger`, `forecast_logger`, `performance_logger`. Prometheus metrics on all critical paths. Custom weather exporter in `monitoring/`.

## Code Quality Configuration

- **Black**: line-length 88, Python 3.11 target
- **isort**: profile "black", known first-party: `core`, `api`
- **flake8**: max-line-length 88, ignores E203/W503/E501 for Black compatibility
- **mypy**: strict mode (`disallow_untyped_defs`, `strict_equality`, etc.)
- **pytest**: test paths are `api/tests` and `tests/`, markers: `unit`, `integration`, `security`, `performance`, `slow`. Coverage target >= 90% for API.
- **Frontend ESLint**: strict mode, zero warnings in CI

## Infrastructure

- **Docker Compose**: 5 variants (default, dev, staging, production, lite/minimal)
- **Kubernetes**: `k8s/` has base + Kustomize overlays per environment
- **Helm**: `helm/adelaide-weather-forecast/` with per-env values
- **Terraform**: `terraform/environments/` for AWS EKS provisioning
- **CI/CD**: 13 GitHub Actions workflows in `.github/workflows/`. Primary: `comprehensive-ci-cd.yml`. Production uses blue-green deployment with manual approval gates and 30-min auto-rollback.

## Key Environment Variables

| Variable | Purpose |
|----------|---------|
| `API_TOKEN` | Bearer token for API auth |
| `ADELAIDE_WEATHER_MASTER_KEY` | Master encryption key |
| `ENVIRONMENT` | `development`, `staging`, or `production` |
| `FAISS_GPU_ENABLED` / `FAISS_FORCE_CPU` | GPU/CPU selection for FAISS |
| `CORS_ORIGINS` | Allowed CORS origins |
| `RATE_LIMIT_PER_MINUTE` | API rate limit |
| `COMPRESSION_MIN_SIZE` | GZip threshold in bytes |

## Deployment

```bash
./deploy.sh development                    # Dev deploy
./deploy.sh staging --monitoring --validate # Staging with validation
./deploy.sh production --monitoring --backup --health-check  # Production
```

Production deploys via GitHub Actions with blue-green strategy, requiring manual approval. Rollback: `gh workflow run rollback-automation.yml -f environment=production -f rollback_target=previous`.

## Repair Project (Active)

### Issue Register

The verified issue register is at `docs/ISSUE-REGISTER.md`. All agents should reference this for issue IDs, file locations, and descriptions. 34 confirmed issues from the 2026-03-31 audit.

### Repair Agents

Specialist agents are defined in `.claude/agents/`. Use them for domain-specific work:

- `backend-fixer` — Python/FastAPI bugs (async, imports, error handling, logging, memory leaks)
- `ml-engineer` — PyTorch/CNN issues (tensor shapes, model loading, architecture)
- `meteorologist` — Atmospheric science correctness (humidity, pressure, analog quality)
- `security-auditor` — OWASP, CORS, SSL, input validation, secrets
- `infra-reviewer` — Docker, CI/CD, deps, monitoring, Helm
- `test-writer` — Regression tests for all fixes

### Repair Workflow

1. **Wave 1 (Critical):** backend-fixer (C1, C2) + ml-engineer (C3, C4) in parallel
2. **Wave 2 (High):** backend-fixer (H1, H4) + security-auditor (H2, H3) + meteorologist (H5, H6) in parallel
3. **Wave 3 (Medium + Low):** All agents in parallel by domain
4. **Wave 4 (Infrastructure):** infra-reviewer in passes
5. **Wave 5 (Tests):** test-writer for regression coverage

### Commit Convention

```
fix(critical): C1 — add await to forecast_with_uncertainty calls
fix(security): H2,H3 — enable SSL, fix CORS in nginx
fix(science): H5 — replace flat humidity multiplier with Bolton formula
fix(infra): pin dependencies, fix redis scrape config
test: add regression tests for C1-C4, H1-H6
```

### Key Files for Repairs

- `api/main.py` — FastAPI application, most backend issues live here
- `api/forecast_adapter.py` — Weather variable conversions (H5, H6, M7)
- `api/security_middleware.py` — Security headers and input validation
- `api/enhanced_token_manager.py` — Token management (M1)
- `api/services/faiss_health_monitoring.py` — FAISS monitoring (M3)
- `core/model_loader.py` — PyTorch model loading and architecture (C3, C4)
- `core/real_time_embedder.py` — Tensor construction for CNN input (C3, M5, L1)
- `core/analog_forecaster.py` — Analog search and weighting (M8, L5)
- `nginx/nginx.conf` — Reverse proxy config (H2, H3, M6)
