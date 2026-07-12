# TruPitch — Architecture

## Overview

TruPitch is an async, queue-driven system. The API accepts work instantly; evaluation happens in the background.

```
┌──────────┐     ┌─────────────┐     ┌────────────┐
│ Frontend │────▶│ API Gateway │────▶│  Postgres  │
│ (React)  │     │  (FastAPI)  │     │    (DB)    │
└──────────┘     └──────┬──────┘     └─────▲──────┘
                        │ enqueue          │ persist scores
                        ▼                  │
                 ┌────────────┐     ┌──────┴──────┐
                 │   Redis    │────▶│ Worker Node │──▶ GitHub API
                 │  (Broker)  │     │  (Python)   │──▶ LLM API
                 └────────────┘     └─────────────┘
```

## Request Flow

1. **Frontend (React)** — Hackers submit repo links/pitches; Admins manage rubrics and view shortlists. Talks to the API over HTTPS/JSON.
2. **API Gateway (FastAPI)** — Validates requests (Pydantic schemas), writes the submission to Postgres with status `pending`, and enqueues an evaluation job onto Redis. Returns immediately — no evaluation happens in the request path.
3. **Postgres (Primary Database)** — Source of truth for events, rubrics, submissions, and evaluation results. Async access via SQLAlchemy + asyncpg.
4. **Redis (Message Broker)** — Job queue between API and workers. Decouples submission ingestion from slow evaluation work; absorbs bursts at submission deadlines.
5. **Worker Node (Python)** — Pulls jobs from Redis and runs the 3-stage pipeline:
   - Stage 1: hard heuristic checks (GitHub API status calls).
   - Stage 2: code structure / dependency analysis (repo contents via GitHub API).
   - Stage 3: LLM qualitative scoring against the rubric.

   Each stage persists its result to Postgres and updates submission status (`pending → evaluating → evaluated | disqualified`). Failing a hard gate short-circuits the remaining stages.

## Why This Shape

- **Async by necessity**: GitHub API and LLM calls take seconds to minutes and are rate-limited. Blocking HTTP requests on them is a non-starter.
- **Independent scaling**: submission spikes (deadline rushes) scale the API; evaluation backlogs scale workers — independently.
- **Resilience**: a failed evaluation job can be retried from the queue without losing the submission.

## Repo Mapping

| Component | Location |
|---|---|
| Frontend | `apps/web/` |
| API Gateway | `apps/api/` |
| Worker | `apps/worker/` |
| Postgres / Redis | `docker-compose.yml` services |
| Docker builds | `infrastructure/` |
