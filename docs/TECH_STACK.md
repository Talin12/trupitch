# TruPitch — Official Tech Stack

| Layer | Technology | Notes |
|---|---|---|
| Frontend | **React + TypeScript** | Vite as bundler/dev server, Tailwind CSS for styling, React Router for navigation. Lives in `apps/web/`. |
| Backend API | **FastAPI** (Python) | Async request handling, Pydantic v2 validation, auto OpenAPI docs, native WebSocket support. Lives in `apps/api/`. |
| Background Tasks | **Celery** (Python) | Consumes jobs from Redis; runs the 3-stage evaluation pipeline (heuristics, code structure, LLM scoring). Lives in `apps/worker/`. |
| Primary Database | **PostgreSQL** | Source of truth for organizers, campaigns, rules, hackers, submissions. Accessed via SQLAlchemy 2.0 (async) + asyncpg. Schema managed by Alembic. |
| Message Broker & Pub/Sub | **Redis** | Celery job queue *and* the real-time channel (`campaign_{id}_updates`) bridging worker progress to the dashboard over WebSocket. |
| Authentication | **GitHub OAuth 2.0 + JWT** | Hackers authenticate via GitHub; sessions are stateless JWTs (`PyJWT`, HS256) validated per-request. No organizer auth yet. |
| LLM Scoring | **Any OpenAI-compatible endpoint** | `openai` Python SDK pointed at a configurable `LLM_BASE_URL`. Currently configured against **Hugging Face Inference Providers** (free tier, e.g. `Qwen/Qwen2.5-7B-Instruct`); OpenAI itself, or any other OpenAI-compatible host, works by changing `.env` only. |

## Supporting tooling

- **Docker Compose** — local orchestration of postgres, redis, web, api, and worker (`docker-compose.yml` at repo root, Dockerfiles in `infrastructure/`).
- **uvicorn** — ASGI server for FastAPI.
- **Alembic** — async-aware migrations targeting `Base.metadata`; every schema change is a committed migration under `apps/api/alembic/versions/`.
- **httpx** — async HTTP client used for GitHub API calls (worker and API) and OAuth token/user exchange.
- **lucide-react** — icon set for the frontend.
- **python-dotenv** — loads the repo-root `.env` for the worker process (the API loads it via `pydantic-settings`).

## Conventions

- Python services pin dependencies in per-app `requirements.txt`; a single shared `.venv` at the repo root is used for local development of both `apps/api` and `apps/worker`.
- The frontend proxies `/api/*` to the FastAPI service in development (see `apps/web/vite.config.ts`).
- Status values (`CampaignStatus`, `SubmissionStatus`) are defined as enums in `core/constants.py` (API) and mirrored in `apps/worker/constants.py` — never compare against raw strings.
- All secrets and environment-dependent config live in `.env` (see `.env.example` for the full list); nothing is hardcoded in application logic. `JWT_SECRET` has no insecure default — a missing value fails startup rather than silently signing with a known key.
- New technology choices should be recorded here before adoption.
