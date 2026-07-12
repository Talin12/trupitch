# TruPitch — Product Requirements Document (Condensed)

## Problem

Hackathon organizers receive far more submissions than human judges can meaningfully review. A large fraction are disqualifiable on objective grounds (broken links, empty repos, boilerplate forks), and the rest need consistent scoring against event-specific criteria.

## Personas

### Admin (Organizer)

Hackathon organizers and judging leads.

- Creates an event and defines its **rubric**: criteria, weights, and descriptions.
- Sets **thresholds**: minimum scores and hard disqualification rules.
- Reviews the generated **shortlist**: ranked submissions with per-stage scores and rationale.
- Can override automated decisions (reinstate or disqualify manually).

### Hacker (Participant)

Hackathon participants submitting projects.

- Submits a **GitHub repository link** and a **pitch** (text description of the project).
- Receives confirmation of submission and, optionally, status updates (received → evaluating → evaluated).
- Does not see internal scores unless the organizer chooses to share them.

## The 3-Stage Evaluation Pipeline

Every submission flows through three stages. Failing a hard gate short-circuits later (more expensive) stages.

### Stage 1 — Hard Heuristics (status checks)

Cheap, deterministic disqualification gates:

- Repository URL resolves and is accessible (public or authorized).
- Repository is non-empty and has commit activity within the event window.
- Pitch is present and meets minimum length.

Output: pass/fail with reasons. Fail = disqualified, no further processing.

### Stage 2 — Code Structure (dependencies)

Static inspection of the repository:

- Dependency manifest analysis (package.json, requirements.txt, etc.) — what was actually built vs. imported.
- Project layout and file composition (source vs. boilerplate/generated code).
- Signals of fork/template reuse without meaningful additions.

Output: structural score + extracted metadata fed into Stage 3.

### Stage 3 — LLM Qualitative Scoring

An LLM scores the submission against the organizer's rubric:

- Inputs: pitch text, repository metadata/excerpts from Stage 2, rubric criteria and weights.
- Outputs: per-criterion scores with short written rationale, plus an overall weighted score.

## Core Output

A per-event **shortlist**: submissions ranked by overall score, with disqualified entries filtered out and every score traceable to its stage and rationale.

## Non-Goals (for now)

- Live demo/video evaluation.
- Plagiarism detection beyond fork/template heuristics.
- In-platform judging UI for human judges (organizers export/review the shortlist).
