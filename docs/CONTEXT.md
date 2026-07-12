# TruPitch — Project Context

## What it is

TruPitch is a B2B SaaS platform that automates the filtering and judging of hackathon submissions. Hackathon organizers today drown in hundreds of submissions, many of which are incomplete, broken, or off-theme. TruPitch turns that raw firehose into a ranked, filtered shortlist.

## How it works

1. **Hackers submit** their project: a GitHub repository link plus a written/recorded pitch.
2. **Organizers configure** a rubric for their event: scoring criteria, weights, and pass/fail thresholds.
3. **An async evaluation engine** processes each submission through a pipeline that combines:
   - **Hard heuristics** — deterministic checks (repo exists, is public, builds, has recent commits, etc.).
   - **Code structure analysis** — dependency and project-layout inspection to gauge substance and originality.
   - **LLM qualitative scoring** — a language model scores the pitch and code against the organizer's rubric.
4. **Organizers receive** a filtered, scored shortlist instead of the raw submission pile, letting human judges focus their time on the projects that matter.

## Why async

Evaluation involves slow external calls (GitHub API, LLM inference). Submissions are accepted instantly by the API and queued; workers process them in the background and persist scores as they complete.

## Current status

Freshly scaffolded monorepo. No application logic implemented yet. See `PRD.md` for requirements, `ARCHITECTURE.md` for system design, and `TECH_STACK.md` for technology choices.
