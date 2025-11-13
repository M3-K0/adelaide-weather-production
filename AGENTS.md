# Repository Guidelines

## Project Structure & Module Organization
- `api/` – FastAPI service (entry `api/main.py`), middleware, models, Dockerfiles.
- `core/` – forecasting, FAISS, validation, and system utilities.
- `frontend/` – Next.js + TypeScript UI (Jest, ESLint, Prettier, Tailwind).
- `tests/` – Python integration/security tests; `tests/e2e` Playwright config; perf/load under `tests/performance` and `tests/load`.
- `nginx/`, `monitoring/`, `ops/`, `terraform/` – infra, monitoring, and deployment assets.
- Common data/artifacts live under `indices/`, `models/`, `embeddings/`, `outcomes/` (read-only in dev containers).

## Build, Test, and Development Commands
Backend (Python 3.11):
- Create env: `python -m venv .venv && source .venv/bin/activate`
- Install: `pip install -r api/requirements.txt`
- Run API: `python -m uvicorn api.main:app --reload --port 8000`
- Tests: `pytest -q` (markers: `unit`, `integration`, `security`)
- Type/lint: `mypy . && flake8 && black --check . && isort --check-only .`
- Security: `bandit -r api core -c .bandit`

Frontend (Node 18+):
- From `frontend/`: `npm ci`, `npm run dev`, `npm test`, `npm run ci:all`

Full stack (Docker):
- `docker-compose up -d` then visit `http://localhost` (API at `:8000`, UI at `:3000`).

## Coding Style & Naming Conventions
Python:
- Format with Black (line length 88), import order via isort, lint with flake8 (E203/W503 ignored), strict mypy.
- Naming: modules/functions `snake_case`, classes `PascalCase`, constants `UPPER_SNAKE`.
- Tests: `test_*.py` or `*_test.py` alongside `api/` or under `tests/`.

TypeScript/React:
- ESLint + Prettier; components `PascalCase` in `frontend/components/`; route files under `frontend/app/` follow Next.js conventions.

## Testing Guidelines
- Unit/integration: `pytest -m "not slow"` or `pytest -m integration`.
- Coverage: target ≥90% (API enforces `--cov-fail-under=90`).
- Frontend unit: `cd frontend && npm test` (Jest + JSDOM).
- E2E: `npx playwright test -c tests/e2e/playwright.config.ts` (starts UI and API automatically).
- Performance/load: see `tests/performance/` and `tests/load/` scripts.

## Commit & Pull Request Guidelines
- Commits: imperative, present tense, concise (<72 chars), optional Conventional Commits (e.g., `feat(api): add health metrics`).
- PRs: clear description, linked issues, screenshots for UI changes, and notes on perf/security impact.
- Required before merge: `pytest -q`, `mypy`, `flake8`, `black --check .`, `isort --check-only .`, and `cd frontend && npm run ci:all`.

## Security & Configuration Tips
- Never commit secrets. Use `.env.*.sample` as templates; set `API_TOKEN` securely (see `api/token_rotation_cli.py`).
- Set `CORS_ORIGINS` when running locally with the UI; prefer Docker Compose for parity.
- Keep large data folders (`indices/`, `models/`) out of commits; mount read-only in containers.

