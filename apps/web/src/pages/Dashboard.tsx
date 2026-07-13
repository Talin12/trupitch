import { useEffect, useMemo, useState } from "react";
import axios from "axios";
import { useNavigate } from "react-router-dom";
import {
  ChevronDown,
  ChevronUp,
  ExternalLink,
  Plus,
  RefreshCw,
  SlidersHorizontal,
  Trophy,
} from "lucide-react";
import { API_BASE, type Submission } from "../types";

const STATUS_STYLES: Record<Submission["status"], string> = {
  evaluated: "bg-emerald-50 text-emerald-700 ring-emerald-600/20",
  evaluating: "bg-amber-50 text-amber-700 ring-amber-600/20",
  pending: "bg-slate-100 text-slate-600 ring-slate-500/20",
  disqualified: "bg-red-50 text-red-700 ring-red-600/20",
};

function StatusPill({ status }: { status: Submission["status"] }) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ring-1 ring-inset ${STATUS_STYLES[status]}`}
    >
      {status}
    </span>
  );
}

function ScoreBadge({ score }: { score: number | null }) {
  if (score === null) {
    return <span className="text-2xl font-semibold text-slate-300">—</span>;
  }
  const tone =
    score >= 70
      ? "text-emerald-600"
      : score >= 40
        ? "text-amber-600"
        : "text-red-600";
  return (
    <span className={`text-2xl font-semibold tabular-nums ${tone}`}>
      {Math.round(score)}
    </span>
  );
}

function SubmissionCard({ submission }: { submission: Submission }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <h3 className="truncate text-base font-semibold text-slate-900">
              {submission.team_name}
            </h3>
            <StatusPill status={submission.status} />
          </div>
          <a
            href={submission.github_url}
            target="_blank"
            rel="noreferrer"
            className="mt-1 inline-flex items-center gap-1 text-sm text-slate-500 hover:text-slate-900"
          >
            <span className="truncate">
              {submission.github_url.replace("https://", "")}
            </span>
            <ExternalLink className="h-3.5 w-3.5 shrink-0" />
          </a>
        </div>
        <div className="text-right">
          <ScoreBadge score={submission.final_score} />
          <div className="text-xs text-slate-400">score</div>
        </div>
      </div>

      {submission.notes && (
        <div className="mt-3 border-t border-slate-100 pt-3">
          <button
            onClick={() => setExpanded((v) => !v)}
            className="inline-flex items-center gap-1 text-xs font-medium text-slate-500 hover:text-slate-900"
          >
            {expanded ? (
              <ChevronUp className="h-3.5 w-3.5" />
            ) : (
              <ChevronDown className="h-3.5 w-3.5" />
            )}
            AI evaluation notes
          </button>
          {expanded && (
            <p className="mt-2 whitespace-pre-wrap text-sm leading-relaxed text-slate-600">
              {submission.notes}
            </p>
          )}
        </div>
      )}
    </div>
  );
}

interface LiveUpdate {
  submission_id: number;
  status: Submission["status"];
  final_score: number | null;
  notes: string | null;
}

export default function Dashboard() {
  const navigate = useNavigate();
  const [submissions, setSubmissions] = useState<Submission[]>([]);
  const [threshold, setThreshold] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [live, setLive] = useState(false);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await axios.get<Submission[]>(
        `${API_BASE}/api/campaigns/1/submissions`,
      );
      setSubmissions(res.data);
    } catch {
      setError("Could not load submissions. Is the API running on port 8000?");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  useEffect(() => {
    const ws = new WebSocket("ws://localhost:8000/api/campaigns/1/ws");

    ws.onopen = () => setLive(true);
    ws.onclose = () => setLive(false);
    ws.onerror = () => setLive(false);

    ws.onmessage = (event) => {
      let update: LiveUpdate;
      try {
        update = JSON.parse(event.data);
      } catch {
        return;
      }
      // Patch the matching row in place — no re-fetch, no flicker.
      setSubmissions((prev) =>
        prev.map((s) =>
          s.id === update.submission_id
            ? {
                ...s,
                status: update.status ?? s.status,
                final_score: update.final_score ?? s.final_score,
                notes: update.notes ?? s.notes,
              }
            : s,
        ),
      );
    };

    return () => ws.close();
  }, []);

  const visible = useMemo(
    () =>
      threshold === 0
        ? submissions
        : submissions.filter((s) => (s.final_score ?? -1) >= threshold),
    [submissions, threshold],
  );

  return (
    <div className="min-h-screen bg-slate-50">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-4xl items-center justify-between px-6 py-4">
          <div className="flex items-center gap-2">
            <Trophy className="h-5 w-5 text-indigo-600" />
            <h1 className="text-lg font-semibold text-slate-900">
              TruPitch — Organizer Dashboard
            </h1>
            <span
              className={`ml-2 inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-xs font-medium ${
                live
                  ? "bg-emerald-50 text-emerald-700"
                  : "bg-slate-100 text-slate-500"
              }`}
            >
              <span
                className={`h-1.5 w-1.5 rounded-full ${
                  live ? "animate-pulse bg-emerald-500" : "bg-slate-400"
                }`}
              />
              {live ? "Live" : "Offline"}
            </span>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={load}
              className="inline-flex items-center gap-1.5 rounded-md border border-slate-300 bg-white px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50"
            >
              <RefreshCw
                className={`h-4 w-4 ${loading ? "animate-spin" : ""}`}
              />
              Refresh
            </button>
            <button
              onClick={() => navigate("/admin/campaigns/new")}
              className="inline-flex items-center gap-1.5 rounded-md bg-indigo-600 px-3 py-1.5 text-sm font-semibold text-white hover:bg-indigo-500"
            >
              <Plus className="h-4 w-4" />
              Create Campaign
            </button>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-4xl px-6 py-8">
        <div className="mb-6 rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
          <div className="flex items-center justify-between">
            <label
              htmlFor="threshold"
              className="inline-flex items-center gap-2 text-sm font-medium text-slate-700"
            >
              <SlidersHorizontal className="h-4 w-4 text-indigo-600" />
              Triage threshold
            </label>
            <span className="text-sm tabular-nums text-slate-500">
              score ≥ <span className="font-semibold text-slate-900">{threshold}</span>
            </span>
          </div>
          <input
            id="threshold"
            type="range"
            min={0}
            max={100}
            value={threshold}
            onChange={(e) => setThreshold(Number(e.target.value))}
            className="mt-3 w-full accent-indigo-600"
          />
          <p className="mt-1 text-xs text-slate-400">
            {threshold === 0
              ? "Showing all submissions."
              : `Showing ${visible.length} of ${submissions.length} submissions.`}
          </p>
        </div>

        {error && (
          <div className="mb-6 rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700">
            {error}
          </div>
        )}

        {loading && submissions.length === 0 ? (
          <p className="text-sm text-slate-500">Loading submissions…</p>
        ) : visible.length === 0 && !error ? (
          <p className="text-sm text-slate-500">
            No submissions match the current threshold.
          </p>
        ) : (
          <div className="space-y-3">
            {visible.map((s) => (
              <SubmissionCard key={s.id} submission={s} />
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
