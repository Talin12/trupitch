# TruPitch: The Manifesto and Master Idea Document

## 1. The Core Thesis
TruPitch is a B2B SaaS platform engineered to solve the most critical, yet universally ignored, bottleneck in the global hackathon ecosystem: **submission triage and evaluation at scale.** 

The current landscape of hackathon tooling is heavily skewed toward pre-event logistics—ticketing, team formation, and venue management. However, the actual culmination of the event, where hundreds of exhausted developers submit hastily assembled codebases at 2:00 AM, remains a chaotic, manual, and deeply flawed process. TruPitch acts as an automated, asynchronous filtration layer that mathematically and qualitatively evaluates codebase integrity and pitch relevance. It allows organizers to bypass the noise, eliminate non-functional submissions instantly, and dedicate human judging hours exclusively to the top percentile of projects.

## 2. The Anatomy of the Problem

To build TruPitch, we must deeply understand the pain points of the three primary actors in a hackathon ecosystem: Organizers, Judges, and Hackers.

### 2.1 The Organizer's Nightmare (The Crisis of Scale)
Hackathons are designed to scale infinitely in the ideation phase but bottleneck violently in the evaluation phase. 
* **The Midnight Surge:** In a 500-person hackathon, approximately 100-120 teams will submit projects within a 15-minute window right before the deadline.
* **The Garbage Ratio:** Historically, 30% to 40% of these submissions are "dead on arrival." They contain broken deployment URLs, empty GitHub repositories, or are simply clones of popular web development tutorials (e.g., a standard Next.js boilerplate) with no unique business logic.
* **The Logistics Trap:** Organizers currently use spreadsheets to assign these 120 projects to 10 judges. This means each judge is responsible for 12 projects, with only 5 minutes to review each. 

### 2.2 The Judge's Fatigue
Judges are usually industry professionals, sponsors, or senior engineers. Their time is expensive and their patience is limited.
* **Cognitive Overload:** A judge clicking a Devpost or Google Form link expects to see innovation. Instead, they spend their first 3 minutes trying to figure out how to bypass a broken CORS error on a deployed frontend, leaving them 2 minutes to evaluate the actual business idea.
* **Subjective Drift:** By the 9th project, a judge's grading criteria inevitably drifts. They are tired, biased by previous exceptional or terrible projects, and no longer adhering strictly to the sponsor's rubric.

### 2.3 The Hacker's Dilemma
Hackers often possess intermediate to advanced technical skills, building robust backend architectures and complex database schemas over a 48-hour sprint.
* **The Presentation Gap:** The tragedy of the hacker is that a brilliantly architected asynchronous microservice backend cannot be easily demonstrated in a 2-minute pitch. 
* **Misalignment with Rubrics:** Teams frequently fail to map their technical achievements to the specific criteria the sponsors care about (e.g., "Business Viability" or "Best use of AI API"). They pitch *how* they built it, rather than *why* it matters.

---

## 3. The TruPitch Paradigm Shift

TruPitch transforms evaluation from a manual human chore into an automated, deterministic pipeline. We shift the ecosystem from a "judge-everything" model to an "evaluate-all, judge-the-best" model.

| Feature | Traditional Hackathon Workflow | The TruPitch Workflow |
| :--- | :--- | :--- |
| **Submission Medium** | Google Forms / Basic Devpost Links | Authenticated Developer Portal (GitHub OAuth) |
| **Initial Review** | Human judge opens every link | Automated Engine runs Heuristic Checks |
| **Codebase Insight** | Judge guesses based on a 2-min pitch | Engine parses AST, dependencies, and commit history |
| **Rubric Alignment** | Subjective, based on judge's memory | Deterministic, scored via LLM against exact criteria |
| **Final Output** | A messy, debated spreadsheet | A dynamic, slider-based Top X% Leaderboard |

---

## 4. Deep Dive: The Three-Stage Evaluation Engine

The core IP of TruPitch is its asynchronous evaluation engine. When a hacker clicks "Submit," the payload does not go to a judge; it enters a queued state machine.

### Stage 1: The Hard Heuristics (The Reaper)
Before invoking expensive AI models, TruPitch performs brute-force verification. If a project fails these checks, it is flagged and deprioritized instantly.
* **Repository Health:** Is the repository public? Was it created before the hackathon started? Does it have more than 3 commits? Are the commits spread out, or was the entire 10,000-line codebase pushed in a single commit 5 minutes before the deadline?
* **Deployment Liveness:** The engine pings the provided frontend and backend URLs. If they return `404 Not Found` or `502 Bad Gateway`, the project's "Deployment Score" drops to zero.

### Stage 2: Code Structure & Complexity Profiling
The engine pulls the repository architecture.
* **Dependency Mapping:** It parses `package.json`, `requirements.txt`, or `pom.xml`. If the sponsor prize is for "Best use of Postgres," the engine verifies if standard Postgres drivers (like `psycopg2` or `pg`) actually exist in the codebase.
* **Boilerplate Detection:** It compares the directory structure against known boilerplate templates to ensure the team actually wrote custom logic.

### Stage 3: LLM Qualitative Matrix (The Virtual Judge)
Projects that survive Stage 1 and 2 are injected into an advanced LLM pipeline. The organizer's exact judging rubric is dynamically formatted into a strict system prompt. The LLM evaluates the hacker's submitted pitch script and `README.md` against this rubric.

**The Formal Scoring Equation:**
The final score is determined by a weighted mathematical model:

$$ S_{final} = \sum_{i=1}^{n} \left( w_i \cdot \mathcal{E}(R_i, P) \right) \times \prod_{j=1}^{m} H_j $$

Where:
* $S_{final}$ = The total computed project score.
* $w_i$ = The weight assigned to rubric criterion $i$ (e.g., 0.4 for Tech, 0.6 for Business).
* $\mathcal{E}$ = The LLM evaluation function generating a score for criterion $R_i$ based on project payload $P$.
* $H_j$ = A boolean heuristic multiplier (0 or 1). If a fatal heuristic fails (e.g., no code submitted), the entire score zeroes out.

---

## 5. The Two-Sided Platform Ecosystem

### 5.1 The Organizer OS (Admin Command Center)
This is not a consumer app; this is an enterprise-grade dashboard.
* **Campaign Builder:** Organizers create custom URLs for their events.
* **Rule Engine UI:** A no-code interface where organizers weight their rubrics (e.g., slider for "Technical Complexity" vs "Design").
* **The Triage Leaderboard:** The moment the deadline hits, the organizer sees a live dashboard updating as the background workers process submissions. They use a global slider to set the "Human Review Threshold" (e.g., "Only show me projects scoring > 75/100").

### 5.2 The Hacker Portal
* **GitHub Native:** No more copying and pasting messy links. Hackers authenticate via OAuth, select their repo from a dropdown, and grant read access.
* **Pitch Formatter:** A dedicated text editor that forces hackers to break their pitch into structured components (The Problem, The Architecture, The Business Value), ensuring the LLM (and eventual human judges) can parse their ideas clearly.

---

## 6. The "Why" & Market Value Proposition

Why build this? Because hackathon organizers have budgets, and they currently spend those budgets on pizza, t-shirts, and tooling that fails them at the most critical moment.

* **University E-Cells:** Need to manage 1000+ student hackathons without exhausting their faculty judges.
* **Corporate DevRel Teams (e.g., Vercel, Supabase):** Host global, async virtual hackathons where manually checking 5,000 GitHub repos is mathematically impossible. TruPitch allows them to automatically verify if participants actually used their specific SDKs before awarding prizes.

---

## 7. The North Star Principles (Immutable Laws of TruPitch)

1. **Zero UI Blocking:** The platform must never make an organizer or hacker wait for an LLM response on the main thread. Every heavy action must be asynchronous. If the UI freezes at 2:00 AM on submission day, the product is dead.
2. **Absolute Data Integrity:** TruPitch does not hallucinate code. If a repository is empty, the LLM must not be allowed to invent features based on a good pitch text. The heuristic engine overrides the generative engine.
3. **B2B Aesthetics:** The UI must look like a professional developer tool (akin to Vercel, Linear, or Stripe), not a playful consumer social app. It must command trust.

---

## 8. Roadmap to Monopoly

* **V1 (The MVP):** Core ingestion, GitHub OAuth, background heuristic pinging, basic LLM rubric scoring, and the Organizer Leaderboard.
* **V2 (The Feedback Loop):** Automated post-event emails to all rejected teams containing the LLM-generated technical critique, so every hacker gets feedback even if they didn't win.
* **V3 (The Ecosystem):** Integrating directly with Devpost or MLH (Major League Hacking) as a certified middleware evaluation plugin.