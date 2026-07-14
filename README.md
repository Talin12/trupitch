# TruPitch

Automated hackathon submission filtering and judging platform. Hackers authenticate with GitHub and submit a repo + pitch; an async Celery pipeline verifies the repo, analyzes its code structure, and scores it against the organizer's rubric with an LLM; organizers watch a live, filterable leaderboard.

## Layout

- `apps/web/` — React + TypeScript frontend (Vite + Tailwind + React Router)
- `apps/api/` — FastAPI backend (REST + WebSocket)
- `apps/worker/` — Celery background worker (3-stage evaluation pipeline)
- `docs/` — project context, PRD, architecture, tech stack, founding vision
- `infrastructure/` — Dockerfiles and deployment configs

## Setup

1. Copy the environment template and fill in secrets:
   ```sh
   cp .env.example .env
   ```
   Required: `JWT_SECRET` (e.g. `openssl rand -hex 32`), a GitHub OAuth app's `GITHUB_CLIENT_ID`/`GITHUB_CLIENT_SECRET` (callback URL: `http://localhost:8000/api/auth/github/callback`), and an LLM provider — either `OPENAI_API_KEY`, or `LLM_BASE_URL` + `LLM_API_KEY` for an OpenAI-compatible provider like Hugging Face (defaults are pre-filled for HF). Without a working LLM key, Stage 3 falls back to a labeled deterministic mock so the pipeline still completes.

2. Start Postgres and Redis:
   ```sh
   docker compose up -d postgres redis
   ```

3. Create a Python virtualenv shared by the API and worker, and install both:
   ```sh
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r apps/api/requirements.txt -r apps/worker/requirements.txt
   ```

4. Run migrations:
   ```sh
   cd apps/api && alembic upgrade head
   ```

5. Install and run the frontend:
   ```sh
   cd apps/web && npm install
   ```

## Run (local dev, one process per terminal)

```sh
# API
cd apps/api && source ../../.venv/bin/activate && uvicorn main:app --reload

# Worker
cd apps/worker && celery -A tasks worker --loglevel=info

# Frontend
cd apps/web && npm run dev
```

- Frontend: http://localhost:5173 (event list → event page → GitHub sign-in → submit)
- Organizer dashboard: http://localhost:5173/admin
- API docs: http://localhost:8000/docs

Or bring up everything via Docker Compose (`docker compose up --build`), though local dev with the steps above gives faster iteration and hot reload.

See `docs/CONTEXT.md` for what TruPitch does, `docs/ARCHITECTURE.md` for how the pieces fit together, `docs/PRD.md` for requirements, `docs/TECH_STACK.md` for technology choices, and `docs/IDEA.md` for the founding vision.
