# TruPitch — Product Requirements Document (Condensed)

## Problem

Hackathon organizers receive far more submissions than human judges can meaningfully review. A large fraction are disqualifiable on objective grounds (broken links, empty repos, boilerplate forks), and the rest need consistent scoring against event-specific criteria.

## Personas

### Admin (Organizer)

Hackathon organizers and judging leads.

- Creates a **campaign** (event): name, deadline, status, and a **rubric** — a weighted list of judging criteria.
- Switches between multiple concurrent campaigns via a dropdown on the dashboard.
- Watches a **live leaderboard**: submissions ranked by score, updating in real time (WebSocket) as the worker finishes evaluating each one.
- Uses a **triage threshold slider** (0–100) to filter the leaderboard down to submissions scoring above a cutoff.
- Reads each submission's AI-generated notes: the Stage 2 tech summary and the Stage 3 scoring rationale.
- *Not yet implemented*: organizer authentication (campaign creation and the dashboard are currently open), manual override of a score/status.

### Hacker (Participant)

Hackathon participants submitting projects.

- Browses **open events** on the public homepage without needing to sign in first.
- Authenticates via **GitHub OAuth** before submitting (required — there is no anonymous submission path).
- Picks one of their **own GitHub repositories** from a dropdown (populated from the GitHub API using their OAuth token) rather than typing a URL.
- Submits a team name, the selected repo, and a pitch.
- Receives an immediate submission ID as confirmation that the project is queued.
- Does not see internal scores unless the organizer chooses to share them.

## The 3-Stage Evaluation Pipeline

Every submission flows through three stages in one Celery task. Failing a hard gate short-circuits later (more expensive) stages.

### Stage 1 — Hard Heuristics

- Verifies the submitted GitHub repository actually exists and resolves (via the GitHub API).
- Fail → submission status becomes `disqualified` with the reason recorded; no further stages run.

### Stage 2 — Code Structure

- Fetches the repository's language breakdown and full file tree from GitHub.
- Detects dependency manifests present (package.json, requirements.txt, pyproject.toml, go.mod, Cargo.toml, and others).
- Produces a plain-text tech summary (e.g. "Languages: Python, TypeScript. Files: 73. Dependency manifests: package.json, requirements.txt.") that feeds into Stage 3.

### Stage 3 — LLM Qualitative Scoring

- The organizer's rubric (each rule's description + weight), the Stage 2 tech summary, and the hacker's pitch are sent to an LLM.
- The LLM returns a score (0–100) and a short written rationale.
- Runs against any OpenAI-compatible provider; degrades to a labeled deterministic mock if the LLM is unavailable (no key, no credits, provider error) so submissions never get stuck mid-pipeline.

Final state: `status = evaluated`, `final_score` set, `notes` = tech summary + LLM rationale. Every state transition (`evaluating` → `disqualified`/`evaluated`) is pushed live to the organizer dashboard.

## Core Output

A per-campaign **leaderboard**: submissions ranked by score (nulls/unscored last), filterable by threshold, with every score traceable to its AI-generated rationale.

## Identity & Repo Verification

Submissions require GitHub OAuth. Beyond the UI only offering the hacker's own repos, the API independently re-verifies via GitHub that the authenticated hacker has **push access** to the submitted repository before accepting it (403 otherwise).

## Non-Goals (for now)

- Organizer authentication / role-based access control.
- Live demo/video evaluation.
- Plagiarism or fork/boilerplate detection beyond dependency-manifest presence.
- In-platform judging UI for human judges (organizers work from the leaderboard directly).
- Per-criterion score breakdown persistence (only the final weighted score + rationale is stored today).
