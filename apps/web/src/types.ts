// Shared TypeScript types for API responses, plus the API's base URL.
// These mirror (by hand — there's no shared codegen) the Pydantic
// schemas in apps/api/schemas/*.py; if a field is added/renamed on the
// backend, it needs to be updated here too.

export interface Rule {
  id: number;
  description: string;
  weight: number;
}

// Mirrors apps/api/schemas/campaign.py's CampaignResponse.
export interface Campaign {
  id: number;
  name: string;
  start_date: string | null;
  deadline: string;
  status: string;
  max_team_size: number;
  max_submissions_per_team: number;
  allow_late_submissions: boolean;
  rules: Rule[];
}

// Mirrors apps/api/schemas/submission.py's SubmissionResponse.
export interface Submission {
  id: number;
  campaign_id: number;
  team_name: string;
  github_url: string;
  pitch_text: string;
  status: "pending" | "evaluating" | "evaluated" | "disqualified";
  final_score: number | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

/** Pipeline stage hint carried by live WebSocket events (not persisted). */
export type EvaluationStage = "verifying_repo" | "analyzing_code" | "ai_scoring";

// Shape of the JSON messages pushed over the campaign WebSocket
// (see apps/api/routers/campaigns.py's campaign_updates_ws and
// apps/worker/tasks.py's publish_update) — this is a *partial* update,
// not a full Submission, so consumers merge it into existing state
// rather than replacing a row outright.
export interface LiveUpdate {
  submission_id: number;
  status: Submission["status"];
  final_score: number | null;
  notes: string | null;
  stage?: EvaluationStage | null;
}

// Hardcoded to the local FastAPI dev server; there's no build-time env
// var for this yet, so pointing the frontend at a deployed API means
// changing this one line.
export const API_BASE = "http://localhost:8000";
