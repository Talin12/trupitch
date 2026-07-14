# TruPitch — Architecture

## Overview

TruPitch is an async, queue-driven system with a real-time feedback loop. The API accepts work instantly; evaluation happens in the background; progress streams back to the browser over WebSocket rather than polling.

```
┌──────────┐  HTTP/JSON   ┌─────────────┐   commit    ┌────────────┐
│ Frontend │─────────────▶│ API Gateway │────────────▶│  Postgres  │
│ (React)  │◀─────────────│  (FastAPI)  │◀────────────│    (DB)    │
└────┬─────┘   WebSocket   └──────┬──────┘   query     └─────▲──────┘
     │                            │ enqueue                  │ persist
     │        subscribe           ▼                           │
     │      campaign_*_updates ┌────────────┐          ┌──────┴──────┐
     └─────────────────────────│   Redis    │─────────▶│ Worker Node │──▶ GitHub API
                               │ Broker+PubSub│  publish │  (Celery)   │──▶ LLM API
                               └────────────┘          └─────────────┘
```

## Request Flow (ingestion)

1. **Frontend (React)** — Hackers browse open events, authenticate via GitHub OAuth, and submit a repo + pitch. Organizers manage campaigns and watch the leaderboard. Talks to the API over HTTPS/JSON, plus a persistent WebSocket per viewed campaign.
2. **API Gateway (FastAPI)** — Validates requests (Pydantic schemas), verifies the authenticated hacker via JWT and their GitHub push access to the repo, writes the submission to Postgres with status `pending`, and enqueues an evaluation job onto Redis via Celery's `send_task` (the API never imports worker code — tasks are addressed by name only). Returns `202 Accepted` immediately.
3. **Postgres (Primary Database)** — Source of truth for organizers, campaigns, rules, hackers, and submissions. Async access via SQLAlchemy 2.0 + asyncpg, schema evolution via Alembic.
4. **Redis** — Two roles: Celery broker/result backend (job queue between API and worker), and Pub/Sub bus (`campaign_{id}_updates` channels) for pushing live evaluation progress to connected dashboards.
5. **Worker Node (Celery)** — Pulls jobs from Redis and runs the 3-stage pipeline (heuristics → code structure → LLM scoring). Each stage transition commits to Postgres *and* publishes a JSON event to the campaign's Pub/Sub channel.

## Real-Time Flow (live dashboard)

1. The Dashboard opens `GET /api/campaigns/{id}/ws`, a FastAPI WebSocket route.
2. The API subscribes to `campaign_{id}_updates` on Redis and relays every message straight to the connected client as JSON — no polling.
3. The worker publishes at each transition: `evaluating`, `disqualified` (+ reason), `evaluated` (+ score + notes).
4. The React client patches the matching row in place (`setSubmissions(prev => prev.map(...))`) — no re-fetch, no flicker. Switching the selected campaign closes the old socket and opens a new one for the new channel.

## Identity Flow (GitHub OAuth)

1. `GET /api/auth/github/login?next=<path>` redirects to GitHub's consent screen with a signed, short-lived `state` token (CSRF protection) that carries the SPA path to return to.
2. `GET /api/auth/github/callback` verifies `state`, exchanges the `code` server-to-server for a GitHub access token, upserts a `Hacker` row (github_id, username, token), and issues a session JWT.
3. The SPA receives `?token=...` on redirect, stores it in `localStorage`, and sends it as `Authorization: Bearer` on `/api/hacker/repos` and submission requests.
4. `GET /api/hacker/repos` uses the hacker's stored GitHub token server-side to list their real repositories — the frontend never sees or handles the GitHub token directly.
5. On submit, the API re-verifies (server-side) that the hacker has push access to the specific repo being submitted, independent of what the UI offered.

## Why This Shape

- **Async by necessity**: GitHub API and LLM calls take seconds and are rate-limited. Blocking HTTP requests on them is a non-starter.
- **Independent scaling**: submission spikes (deadline rushes) scale the API; evaluation backlogs scale workers — independently.
- **Resilience**: transient failures (GitHub rate limits, LLM timeouts, DB hiccups) raise a `RetryableError` and Celery retries with exponential backoff; permanent conditions (bad LLM key, exhausted credits, malformed input) resolve immediately instead of retrying forever.
- **No polling**: Pub/Sub + WebSocket means the organizer dashboard reflects worker progress within milliseconds, not on a refresh cycle.
- **Provider-agnostic LLM**: Stage 3 talks to any OpenAI-compatible chat completions endpoint, so switching between OpenAI, Hugging Face Inference Providers, or a local model is a config change, not a code change.

## Repo Mapping

| Component | Location |
|---|---|
| Frontend | `apps/web/` (`pages/Home.tsx`, `pages/EventPage.tsx`, `pages/Dashboard.tsx`, `pages/CampaignBuilder.tsx`) |
| API Gateway | `apps/api/` (`routers/campaigns.py`, `routers/submissions.py`, `routers/auth.py`, `routers/hacker.py`) |
| Worker | `apps/worker/` (`tasks.py`, `pipeline/`, `clients/`) |
| Postgres / Redis | `docker-compose.yml` services |
| Docker builds | `infrastructure/` |
| DB migrations | `apps/api/alembic/versions/` |
