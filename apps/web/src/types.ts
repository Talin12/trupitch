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

export const API_BASE = "http://localhost:8000";
