# Repository Guidelines

## Project Structure & Module Organization
- Root app lives in `pyramid-rag/`.
- Backend (FastAPI): `pyramid-rag/backend/app`
  - API endpoints: `api/endpoints/*.py`, services: `services/`, tasks: `workers/`, data models: `models.py`, schemas: `schemas.py`.
- Frontend (Vite + React + TS): `pyramid-rag/frontend`
  - Source: `src/` (components, pages, contexts), static assets: `public/`.
- Infra: `pyramid-rag/docker` (nginx, prometheus), `docker-compose*.yml`.
- Tests: Python tests across `pyramid-rag/test_*.py` and `pyramid-rag/backend/test_*.py`.

## Build, Test, and Development Commands
- Backend (local): `cd pyramid-rag/backend && pip install -r requirements.txt && uvicorn app.main:app --reload --port 8000`
- Frontend (local): `cd pyramid-rag/frontend && npm install && npm run dev`
- Full stack (Docker): `cd pyramid-rag && docker compose up --build`
- Backend tests: `cd pyramid-rag && pytest -q` • Coverage: `pytest --cov=backend/app --cov-report=term-missing`
- Frontend tests: `cd pyramid-rag/frontend && npm test` or `npm run test:coverage`

## Coding Style & Naming Conventions
- Python: 4-space indent; format with `black`, lint with `flake8`, type-check with `mypy`.
  - Modules/files `snake_case.py`; classes `PascalCase`; functions/vars `snake_case`.
- TypeScript/React: 2-space indent; format with `npm run format` (Prettier); lint with `npm run lint` (ESLint).
  - Components/pages use `PascalCase` filenames (e.g., `LoadingSpinner.tsx`); hooks `useX.ts`.

## Testing Guidelines
- Python: name tests `test_*.py`; keep unit tests fast and deterministic; mark tests that require services. Validate API status codes and response shapes.
- Frontend: Vitest; colocate as `*.test.ts(x)` near sources; prefer testing user-visible behavior.

## Commit & Pull Request Guidelines
- Use Conventional Commits, e.g.: `feat: add search endpoint`, `fix(frontend): guard null session`.
- PRs include: clear description, linked issue, test updates/coverage, and screenshots/GIFs for UI changes. Keep diffs focused; avoid drive-by refactors.

## Security & Configuration Tips
- Never commit secrets. Backend reads `.env` from `pyramid-rag/backend`; frontend uses `VITE_API_URL` (see `docker-compose.yml`).
- Change default DB passwords and disable `--reload` in production. Limit public ports and review nginx config under `pyramid-rag/docker/nginx`.

