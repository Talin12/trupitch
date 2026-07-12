# TruPitch — Official Tech Stack

| Layer | Technology | Notes |
|---|---|---|
| Frontend | **React + TypeScript** | Vite as bundler/dev server. Lives in `apps/web/`. |
| Backend API | **FastAPI** (Python) | Async request handling, Pydantic validation, auto OpenAPI docs. Lives in `apps/api/`. |
| Background Tasks | **Python Worker** | Consumes jobs from Redis; runs the 3-stage evaluation pipeline (heuristics, code structure, LLM scoring). Lives in `apps/worker/`. |
| Primary Database | **PostgreSQL** | Source of truth for events, rubrics, submissions, scores. Accessed via SQLAlchemy + asyncpg. |
| Message Broker | **Redis** | Job queue decoupling the API from evaluation workers. |

## Supporting tooling

- **Docker Compose** — local orchestration of all five services (`docker-compose.yml` at repo root, Dockerfiles in `infrastructure/`).
- **uvicorn** — ASGI server for FastAPI.

## Conventions

- Python services pin dependencies in per-app `requirements.txt`.
- The frontend proxies `/api/*` to the FastAPI service in development (see `apps/web/vite.config.ts`).
- New technology choices should be recorded here before adoption.
