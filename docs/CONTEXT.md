# TruPitch — Project Context

## What it is

TruPitch is a B2B SaaS platform that automates the filtering and judging of hackathon submissions. Hackathon organizers today drown in hundreds of submissions, many of which are incomplete, broken, or off-theme. TruPitch turns that raw firehose into a ranked, filtered shortlist.

## How it works

1. **Hackers browse open events** on the public site, authenticate with **GitHub OAuth**, and submit a project: one of their own repositories (verified, not typed in) plus a pitch.
2. **Organizers configure campaigns**: name, deadline, and a weighted judging rubric (a list of criteria with weights).
3. **An async evaluation engine** processes each submission through a 3-stage pipeline:
   - **Hard heuristics** — does the repo exist and resolve on GitHub.
   - **Code structure analysis** — languages used and dependency manifests present (package.json, requirements.txt, etc.).
   - **LLM qualitative scoring** — a language model scores the pitch and tech stack against the organizer's weighted rubric, returning a score (0–100) and a written rationale.
4. **Organizers watch a live leaderboard**: submissions ranked by score, updating in real time over WebSocket as the worker finishes each one, with a triage slider to filter by minimum score.

## Why async

Evaluation involves slow external calls (GitHub API, LLM inference). Submissions are accepted instantly by the API and queued on Redis; a Celery worker processes them in the background and persists results as they complete. Progress is pushed to the organizer dashboard live via Redis Pub/Sub + WebSocket, so there's no polling.

## Identity & trust

Hackers authenticate via GitHub OAuth before submitting — no anonymous or spoofed submissions. The API independently verifies (server-side, not just in the UI) that the authenticated hacker actually has push access to the repository they're submitting.

## Multi-tenancy

The platform supports multiple concurrent campaigns ("events"). Hackers pick an event on the homepage before submitting; organizers switch between campaigns on the dashboard, each with its own leaderboard and live update channel.

## LLM provider

Stage 3 scoring runs against any OpenAI-compatible chat completions endpoint (`LLM_BASE_URL` / `LLM_API_KEY` / `LLM_MODEL`), currently configured against Hugging Face's free Inference Providers router. If no usable LLM key/credits are available, the worker falls back to a deterministic mock scorer (clearly labeled in the notes) so the pipeline always completes rather than hanging.

## Current status

Core platform is functional end-to-end: campaign creation, GitHub-authenticated submission, the full 3-stage pipeline, and a live organizer dashboard. Organizer-side authentication does not exist yet — campaign creation and the dashboard are currently open endpoints. See `PRD.md` for requirements, `ARCHITECTURE.md` for system design, and `TECH_STACK.md` for technology choices.
