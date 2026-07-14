export interface Rule {
  id: number;
  description: string;
  weight: number;
}

export interface Campaign {
  id: number;
  name: string;
  deadline: string;
  status: string;
  rules: Rule[];
}

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

export interface LiveUpdate {
  submission_id: number;
  status: Submission["status"];
  final_score: number | null;
  notes: string | null;
  stage?: EvaluationStage | null;
}

export const API_BASE = "http://localhost:8000";
