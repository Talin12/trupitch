# TruPitch

Automated hackathon submission filtering and judging platform.

## Layout

- `apps/web/` — React + TypeScript frontend (Vite)
- `apps/api/` — FastAPI backend
- `apps/worker/` — Python background worker (evaluation pipeline)
- `docs/` — project context, PRD, architecture, tech stack
- `infrastructure/` — Dockerfiles and deployment configs

## Quick start

```sh
docker compose up --build
```

- Web: http://localhost:5173
- API: http://localhost:8000 (docs at /docs)

See `docs/CONTEXT.md` for what TruPitch does and `docs/ARCHITECTURE.md` for how the pieces fit together.
