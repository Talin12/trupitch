// The organizer-facing leaderboard ("/admin"): a sidebar for picking
// which campaign to view, plus a dense data table of that campaign's
// submissions that updates live over WebSocket as the worker evaluates
// each one — no polling, no manual refresh needed to see progress.

import { useEffect, useMemo, useState } from "react";
import axios from "axios";
import { useNavigate } from "react-router-dom";
import {
  ExternalLink,
  Loader2,
  Plus,
  RefreshCw,
  SlidersHorizontal,
  Trophy,
} from "lucide-react";
import {
  API_BASE,
  type Campaign,
  type EvaluationStage,
  type LiveUpdate,
  type Submission,
} from "../types";

// Small colored dot shown next to each row's status text — deliberately
// tiny/subtle rather than a big colored pill, to keep the table dense.
const STATUS_DOT: Record<Submission["status"], string> = {
  evaluated: "bg-emerald-400",
  evaluating: "bg-amber-400",
  pending: "bg-zinc-500",
  disqualified: "bg-red-400",
};

// The 4 toggleable filter chips shown above the table, in display order.
const STATUS_FILTERS: { key: Submission["status"]; label: string }[] = [
  { key: "pending", label: "Pending" },
  { key: "evaluating", label: "Evaluating" },
  { key: "evaluated", label: "Evaluated" },
  { key: "disqualified", label: "Disqualified" },
];

// Human-readable label for the live sub-stage shown while a row's
// status is "evaluating" (see EvaluationStage in types.ts).
const STAGE_LABELS: Record<EvaluationStage, string> = {
  verifying_repo: "verifying repo",
  analyzing_code: "analyzing code",
  ai_scoring: "AI scoring",
};

// Score-band coloring: >=70 good, >=40 middling, below that poor —
// shared with EventPage's SubmissionTracker for a consistent read of
// "what does this score mean" across the whole app.
function scoreTone(score: number): string {
  if (score >= 70) return "text-emerald-400";
  if (score >= 40) return "text-amber-400";
  return "text-red-400";
}

function formatTimestamp(iso: string): string {
  return new Date(iso).toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

// One row in the leaderboard table, plus (when clicked) a second
// expanded row underneath showing the AI's full notes. `stage` is the
// live sub-stage hint for rows currently "evaluating" — passed down
// from Dashboard's liveStages map since the worker's WebSocket
// messages are keyed by submission id, not attached to the Submission
// object itself.
function SubmissionRow({
  submission,
  stage,
}: {
  submission: Submission;
  stage: EvaluationStage | null;
}) {
  const [expanded, setExpanded] = useState(false);
  const isEvaluating = submission.status === "evaluating";
  const hasDetail = Boolean(submission.notes);

  // Stage 3 stores "<tech summary> | <rationale>"; disqualification
  // notes are just the reason with no separator.
  const [techSummary, rationale] = submission.notes?.includes(" | ")
    ? submission.notes.split(" | ")
    : [null, submission.notes];

  return (
    <>
      <tr
        onClick={() => hasDetail && setExpanded((v) => !v)}
        className={`border-b border-white/5 text-sm ${hasDetail ? "cursor-pointer" : ""} ${
          isEvaluating ? "animate-pulse" : ""
        } hover:bg-white/[0.03]`}
      >
        <td className="px-4 py-3 font-medium text-zinc-50">
          {submission.team_name}
        </td>
        <td className="px-4 py-3">
          <a
            href={submission.github_url}
            target="_blank"
            rel="noreferrer"
            // Stop the click from also toggling the row's expand/collapse.
            onClick={(e) => e.stopPropagation()}
            className="inline-flex items-center gap-1 text-zinc-400 hover:text-teal-400"
          >
            <span className="max-w-[220px] truncate">
              {submission.github_url.replace("https://github.com/", "")}
            </span>
            <ExternalLink className="h-3.5 w-3.5 shrink-0" />
          </a>
        </td>
        <td className="px-4 py-3 text-zinc-500">
          {formatTimestamp(submission.updated_at)}
        </td>
        <td className="px-4 py-3">
          <span className="inline-flex items-center gap-1.5">
            <span
              className={`h-2 w-2 shrink-0 rounded-full ${STATUS_DOT[submission.status]}`}
            />
            <span className="text-zinc-400">
              {submission.status === "evaluating" && stage
                ? STAGE_LABELS[stage]
                : submission.status}
            </span>
          </span>
        </td>
        <td className="px-4 py-3 text-right tabular-nums">
          {isEvaluating ? (
            <Loader2 className="ml-auto h-4 w-4 animate-spin text-teal-400" />
          ) : submission.final_score !== null ? (
            <span className={`font-semibold ${scoreTone(submission.final_score)}`}>
              {Math.round(submission.final_score)}
            </span>
          ) : (
            <span className="text-zinc-700">—</span>
          )}
        </td>
      </tr>
      {/* Second <tr> for the expanded detail panel — valid as a sibling
          of the row above inside the same <tbody> (see the render below). */}
      {expanded && hasDetail && (
        <tr className="border-b border-white/5 bg-zinc-900/60">
          <td colSpan={5} className="px-4 py-4">
            <div className="grid gap-4 sm:grid-cols-2">
              {techSummary && (
                <div>
                  <h4 className="mb-1 text-xs font-semibold uppercase tracking-wide text-zinc-500">
                    Code structure
                  </h4>
                  <p className="text-sm text-zinc-300">{techSummary}</p>
                </div>
              )}
              <div>
                <h4 className="mb-1 text-xs font-semibold uppercase tracking-wide text-zinc-500">
                  {submission.status === "disqualified"
                    ? "Disqualification reason"
                    : "AI rationale"}
                </h4>
                <p className="text-sm text-zinc-300">{rationale}</p>
              </div>
            </div>
          </td>
        </tr>
      )}
    </>
  );
}

export default function Dashboard() {
  const navigate = useNavigate();

  // --- Campaign switcher ---
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [campaignsLoaded, setCampaignsLoaded] = useState(false);
  const [selectedCampaignId, setSelectedCampaignId] = useState<number | null>(
    null,
  );

  // --- Submissions for the selected campaign ---
  const [submissions, setSubmissions] = useState<Submission[]>([]);
  // Keyed by submission id rather than stored on Submission itself,
  // since `stage` is an ephemeral WebSocket-only hint, not part of the
  // REST API's Submission shape.
  const [liveStages, setLiveStages] = useState<
    Record<number, EvaluationStage | null>
  >({});

  // --- Filters ---
  const [threshold, setThreshold] = useState(0);
  const [statusFilter, setStatusFilter] = useState<Set<Submission["status"]>>(
    new Set(),
  );

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  // Reflects whether the WebSocket below is currently connected — shown
  // as the Live/Offline indicator at the bottom of the sidebar.
  const [live, setLive] = useState(false);

  const toggleStatusFilter = (status: Submission["status"]) => {
    setStatusFilter((prev) => {
      const next = new Set(prev);
      if (next.has(status)) next.delete(status);
      else next.add(status);
      return next;
    });
  };

  // Fetch the campaign list once on mount and default to the first one
  // (newest, since the API returns them id-descending) — see
  // apps/api/routers/campaigns.py's list_campaigns.
  useEffect(() => {
    axios
      .get<Campaign[]>(`${API_BASE}/api/campaigns`)
      .then((res) => {
        setCampaigns(res.data);
        if (res.data.length > 0) {
          setSelectedCampaignId(res.data[0].id);
        } else {
          setLoading(false);
        }
      })
      .catch(() => {
        setError("Could not load campaigns. Is the API running on port 8000?");
        setLoading(false);
      })
      .finally(() => setCampaignsLoaded(true));
  }, []);

  // Also exposed as the Refresh button's onClick, for a manual re-fetch
  // on top of the automatic live updates.
  const load = async () => {
    if (selectedCampaignId === null) return;
    setLoading(true);
    setError(null);
    try {
      const res = await axios.get<Submission[]>(
        `${API_BASE}/api/campaigns/${selectedCampaignId}/submissions`,
      );
      setSubmissions(res.data);
    } catch {
      setError("Could not load submissions. Is the API running on port 8000?");
    } finally {
      setLoading(false);
    }
  };

  // Re-fetch the full submission list whenever the selected campaign
  // changes (including the very first time it's set, above). Clearing
  // `submissions` first avoids showing the *previous* campaign's rows
  // while the new campaign's data is still loading.
  useEffect(() => {
    if (selectedCampaignId === null) return;
    setSubmissions([]);
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedCampaignId]);

  // Live updates: one WebSocket per selected campaign, reconnected
  // whenever selectedCampaignId changes. This is the same
  // `campaign_{id}_updates` channel EventPage.tsx listens to for a
  // single submission — here every message for the whole campaign is
  // relevant, since this table shows every submission at once.
  useEffect(() => {
    if (selectedCampaignId === null) return;

    const ws = new WebSocket(
      `ws://localhost:8000/api/campaigns/${selectedCampaignId}/ws`,
    );

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
      setLiveStages((prev) => ({
        ...prev,
        [update.submission_id]: update.stage ?? null,
      }));
    };

    // Close the old socket before opening a new one for a different
    // campaign, or on unmount.
    return () => ws.close();
  }, [selectedCampaignId]);

  // Per-status counts shown as the little number badge on each filter
  // chip — recomputed only when the submission list actually changes.
  const statusCounts = useMemo(() => {
    const counts: Record<Submission["status"], number> = {
      pending: 0,
      evaluating: 0,
      evaluated: 0,
      disqualified: 0,
    };
    for (const s of submissions) counts[s.status] += 1;
    return counts;
  }, [submissions]);

  // The rows actually rendered: both filters (status chips and score
  // threshold) apply together — a submission must pass both to show.
  const visible = useMemo(
    () =>
      submissions.filter((s) => {
        if (statusFilter.size > 0 && !statusFilter.has(s.status)) return false;
        if (threshold > 0 && (s.final_score ?? -1) < threshold) return false;
        return true;
      }),
    [submissions, threshold, statusFilter],
  );

  const hasActiveFilter = threshold > 0 || statusFilter.size > 0;
  const noCampaigns = campaignsLoaded && campaigns.length === 0;

  return (
    <div className="flex min-h-screen bg-zinc-950 text-zinc-50">
      {/* Sidebar: brand, campaign switcher, nav, connection status. */}
      <aside className="flex w-60 shrink-0 flex-col border-r border-white/10 bg-zinc-900">
        <div className="flex items-center gap-2 border-b border-white/10 px-5 py-4">
          <Trophy className="h-5 w-5 text-teal-400" />
          <span className="text-base font-semibold">TruPitch</span>
        </div>

        <div className="px-4 py-4">
          <label
            htmlFor="campaign-select"
            className="mb-1.5 block text-xs font-medium uppercase tracking-wide text-zinc-500"
          >
            Campaign
          </label>
          {campaigns.length > 0 ? (
            <select
              id="campaign-select"
              value={selectedCampaignId ?? ""}
              onChange={(e) => setSelectedCampaignId(Number(e.target.value))}
              className="w-full rounded-md border border-white/10 bg-zinc-950 px-2.5 py-2 text-sm text-zinc-50 focus:border-teal-500 focus:outline-none focus:ring-1 focus:ring-teal-500"
            >
              {campaigns.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </select>
          ) : (
            <p className="text-xs text-zinc-600">No campaigns</p>
          )}
        </div>

        <nav className="flex-1 space-y-1 px-3">
          <button
            onClick={() => navigate("/admin/campaigns/new")}
            className="flex w-full items-center gap-2 rounded-md px-2.5 py-2 text-sm font-medium text-zinc-300 hover:bg-white/5 hover:text-zinc-50"
          >
            <Plus className="h-4 w-4" />
            New Campaign
          </button>
        </nav>

        {/* Reflects the WebSocket connection state set in the effect
            above — green+pulsing when connected, grey when not. */}
        <div className="border-t border-white/10 px-4 py-3">
          <span
            className={`inline-flex items-center gap-1.5 text-xs font-medium ${
              live ? "text-emerald-400" : "text-zinc-600"
            }`}
          >
            <span
              className={`h-1.5 w-1.5 rounded-full ${
                live ? "animate-pulse bg-emerald-400" : "bg-zinc-600"
              }`}
            />
            {live ? "Live" : "Offline"}
          </span>
        </div>
      </aside>

      <main className="flex-1 overflow-x-auto">
        {noCampaigns ? (
          // Onboarding empty state: no campaigns exist anywhere yet.
          <div className="flex h-full items-center justify-center p-12">
            <div className="text-center">
              <Trophy className="mx-auto h-8 w-8 text-zinc-700" />
              <h2 className="mt-3 text-base font-semibold text-zinc-50">
                No campaigns yet
              </h2>
              <p className="mt-1 text-sm text-zinc-500">
                Create your first hackathon campaign to start receiving and
                triaging submissions.
              </p>
              <button
                onClick={() => navigate("/admin/campaigns/new")}
                className="mt-4 inline-flex items-center gap-1.5 rounded-md bg-teal-600 px-4 py-2 text-sm font-semibold text-white hover:bg-teal-500"
              >
                <Plus className="h-4 w-4" />
                Create Campaign
              </button>
            </div>
          </div>
        ) : (
          <>
            {/* Toolbar: status filter chips + Refresh on top, score
                threshold slider below — both act on the same `visible`
                list computed above. */}
            <div className="border-b border-white/10 px-6 py-4">
              <div className="flex flex-wrap items-center justify-between gap-4">
                <div className="flex flex-wrap items-center gap-1.5">
                  {STATUS_FILTERS.map((f) => {
                    const active = statusFilter.has(f.key);
                    return (
                      <button
                        key={f.key}
                        type="button"
                        onClick={() => toggleStatusFilter(f.key)}
                        className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-medium transition-colors ${
                          active
                            ? "border-teal-500/40 bg-teal-500/10 text-teal-300"
                            : "border-white/10 bg-zinc-900 text-zinc-400 hover:border-white/20 hover:text-zinc-200"
                        }`}
                      >
                        <span
                          className={`h-1.5 w-1.5 rounded-full ${STATUS_DOT[f.key]}`}
                        />
                        {f.label}
                        <span className="tabular-nums text-zinc-500">
                          {statusCounts[f.key]}
                        </span>
                      </button>
                    );
                  })}
                  {statusFilter.size > 0 && (
                    <button
                      type="button"
                      onClick={() => setStatusFilter(new Set())}
                      className="text-xs text-zinc-500 underline hover:text-zinc-300"
                    >
                      Clear
                    </button>
                  )}
                </div>
                <button
                  onClick={load}
                  className="inline-flex shrink-0 items-center gap-1.5 rounded-md border border-white/10 px-3 py-1.5 text-sm font-medium text-zinc-300 hover:bg-white/5"
                >
                  <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} />
                  Refresh
                </button>
              </div>

              <div className="mt-3 flex flex-wrap items-center gap-3">
                <SlidersHorizontal className="h-4 w-4 shrink-0 text-teal-400" />
                <input
                  type="range"
                  min={0}
                  max={100}
                  value={threshold}
                  onChange={(e) => setThreshold(Number(e.target.value))}
                  className="w-48 accent-teal-500"
                />
                <span className="shrink-0 text-xs tabular-nums text-zinc-500">
                  score ≥{" "}
                  <span className="font-semibold text-zinc-200">
                    {threshold}
                  </span>
                </span>
                <span className="shrink-0 text-xs text-zinc-600">
                  {hasActiveFilter
                    ? `${visible.length} of ${submissions.length}`
                    : `${submissions.length} total`}
                </span>
              </div>
            </div>

            {error && (
              <div className="mx-6 mt-4 rounded-md border border-red-500/20 bg-red-500/10 p-3 text-sm text-red-400">
                {error}
              </div>
            )}

            {/* Three states: initial load, filtered-to-empty (or truly
                empty), and the actual table. */}
            {loading && submissions.length === 0 ? (
              <p className="px-6 py-8 text-sm text-zinc-500">
                Loading submissions…
              </p>
            ) : visible.length === 0 && !error ? (
              <p className="px-6 py-8 text-sm text-zinc-500">
                {submissions.length === 0
                  ? "No submissions in this campaign yet."
                  : "No submissions match the current filters."}
              </p>
            ) : (
              <table className="w-full border-collapse">
                <thead>
                  <tr className="border-b border-white/10 text-left text-xs uppercase tracking-wide text-zinc-500">
                    <th className="px-4 py-2 font-medium">Team</th>
                    <th className="px-4 py-2 font-medium">Repository</th>
                    <th className="px-4 py-2 font-medium">Updated</th>
                    <th className="px-4 py-2 font-medium">Status</th>
                    <th className="px-4 py-2 text-right font-medium">Score</th>
                  </tr>
                </thead>
                <tbody>
                  {visible.map((s) => (
                    <SubmissionRow
                      key={s.id}
                      submission={s}
                      stage={liveStages[s.id] ?? null}
                    />
                  ))}
                </tbody>
              </table>
            )}
          </>
        )}
      </main>
    </div>
  );
}
