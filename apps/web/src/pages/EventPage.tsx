// The hacker-facing event page: shows one campaign's details and
// rubric, gates the submission form behind GitHub OAuth, and — once a
// submission is made — shows its live evaluation progress in place of
// a static "submitted" message. This is the most complex page in the
// app; see the section comments below for how it's organized.

import { useEffect, useState } from "react";
import axios, { AxiosError } from "axios";
import { Link, useParams } from "react-router-dom";
import {
  ArrowLeft,
  CalendarClock,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  Circle,
  ClipboardList,
  Loader2,
  XCircle,
} from "lucide-react";
import TopNav from "../components/TopNav";
import { captureTokenFromUrl, clearToken, getToken } from "../lib/auth";
import {
  API_BASE,
  type Campaign,
  type EvaluationStage,
  type LiveUpdate,
  type Submission,
} from "../types";

// lucide-react dropped brand icons in a later major version, so the
// GitHub mark is inlined as a plain SVG instead of an import.
function GithubMark({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 16 16" fill="currentColor" className={className} aria-hidden>
      <path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27s1.36.09 2 .27c1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.01 8.01 0 0 0 16 8c0-4.42-3.58-8-8-8Z" />
    </svg>
  );
}

// Shared Tailwind classes for every text/select/textarea input on this
// page, so the dark-mode styling only needs to be defined once.
const INPUT_CLASS =
  "w-full rounded-md border border-white/10 bg-zinc-900 px-3 py-2 text-sm text-zinc-50 " +
  "placeholder:text-zinc-500 focus:border-teal-500 focus:outline-none " +
  "focus:ring-1 focus:ring-teal-500";

// The 3 pipeline stages, in order, with the label shown in the
// stepper. `key` must match the `stage` values the worker publishes
// (see apps/worker/tasks.py's publish_update calls).
const STAGE_STEPS: { key: EvaluationStage; label: string }[] = [
  { key: "verifying_repo", label: "Verifying repository" },
  { key: "analyzing_code", label: "Analyzing code structure" },
  { key: "ai_scoring", label: "Scoring with AI" },
];

interface Repo {
  name: string;
  url: string;
}

function formatDeadline(iso: string): string {
  return new Date(iso).toLocaleString(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  });
}

// Renders the 3 stages as a vertical checklist: a filled checkmark for
// stages already passed, a spinner for the one currently running, and
// a hollow circle for stages not yet reached. `currentIndex` is -1
// while still "pending" (no stage reported yet), which renders every
// step as not-yet-reached.
function StageStepper({ currentIndex }: { currentIndex: number }) {
  return (
    <ol className="mt-4 space-y-2">
      {STAGE_STEPS.map((step, i) => {
        const state = i < currentIndex ? "done" : i === currentIndex ? "active" : "todo";
        return (
          <li key={step.key} className="flex items-center gap-2.5 text-sm">
            {state === "done" && (
              <CheckCircle2 className="h-4 w-4 shrink-0 text-emerald-400" />
            )}
            {state === "active" && (
              <Loader2 className="h-4 w-4 shrink-0 animate-spin text-teal-400" />
            )}
            {state === "todo" && (
              <Circle className="h-4 w-4 shrink-0 text-zinc-700" />
            )}
            <span
              className={
                state === "todo"
                  ? "text-zinc-600"
                  : state === "active"
                    ? "font-medium text-zinc-50"
                    : "text-zinc-400"
              }
            >
              {step.label}
            </span>
          </li>
        );
      })}
    </ol>
  );
}

// The live status card shown after a hacker submits. Its appearance
// branches entirely on `status`:
//   "disqualified" -> red card with the Stage 1 failure reason
//   "evaluated"    -> green card with the score + collapsible AI notes
//   otherwise      -> a live progress bar + stepper, since "pending"
//                     and "evaluating" both mean "still working on it"
// `status`/`stage`/`score`/`notes` are all driven by WebSocket messages
// received in EventPage's own effect below — this component itself
// holds no network logic, just the expand/collapse toggle for notes.
function SubmissionTracker({
  submissionId,
  status,
  stage,
  score,
  notes,
}: {
  submissionId: number;
  status: Submission["status"] | null;
  stage: EvaluationStage | null;
  score: number | null;
  notes: string | null;
}) {
  const [expanded, setExpanded] = useState(false);

  if (status === "disqualified") {
    return (
      <div className="mt-6 rounded-lg border border-red-500/20 bg-red-500/5 p-5">
        <div className="flex items-center gap-2">
          <XCircle className="h-5 w-5 shrink-0 text-red-400" />
          <h3 className="text-sm font-semibold text-red-300">
            Submission #{submissionId} was disqualified
          </h3>
        </div>
        {notes && <p className="mt-2 text-sm text-red-400/90">{notes}</p>}
      </div>
    );
  }

  if (status === "evaluated") {
    // Same score-banding convention used on the organizer Dashboard:
    // >=70 good, >=40 middling, below that poor.
    const tone =
      score === null
        ? "text-zinc-500"
        : score >= 70
          ? "text-emerald-400"
          : score >= 40
            ? "text-amber-400"
            : "text-red-400";
    return (
      <div className="mt-6 rounded-lg border border-emerald-500/20 bg-zinc-900 p-5">
        <div className="flex items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="h-5 w-5 shrink-0 text-emerald-400" />
            <h3 className="text-sm font-semibold text-zinc-50">
              Submission #{submissionId} evaluated
            </h3>
          </div>
          <span className={`text-2xl font-bold tabular-nums ${tone}`}>
            {score !== null ? Math.round(score) : "—"}
          </span>
        </div>
        {notes && (
          <div className="mt-3 border-t border-white/10 pt-3">
            <button
              onClick={() => setExpanded((v) => !v)}
              className="inline-flex items-center gap-1 text-xs font-medium text-zinc-400 hover:text-zinc-50"
            >
              {expanded ? (
                <ChevronUp className="h-3.5 w-3.5" />
              ) : (
                <ChevronDown className="h-3.5 w-3.5" />
              )}
              AI evaluation notes
            </button>
            {expanded && (
              <p className="mt-2 whitespace-pre-wrap text-sm leading-relaxed text-zinc-400">
                {notes}
              </p>
            )}
          </div>
        )}
        <Link
          to="/admin"
          className="mt-3 inline-block text-xs font-medium text-teal-400 hover:underline"
        >
          View live leaderboard →
        </Link>
      </div>
    );
  }

  // pending or evaluating: live stepper so it never looks stuck.
  // -1 (no stage yet, i.e. still "pending") renders every step as
  // not-yet-reached; the progress bar still shows a small sliver (8%)
  // rather than 0% so it doesn't look empty/broken while queued.
  const currentIndex = stage
    ? STAGE_STEPS.findIndex((s) => s.key === stage)
    : -1;
  const progressPct =
    currentIndex < 0 ? 8 : Math.round(((currentIndex + 1) / STAGE_STEPS.length) * 100);

  return (
    <div className="mt-6 rounded-lg border border-white/10 bg-zinc-900 p-5">
      <div className="flex items-center justify-between gap-3">
        <h3 className="text-sm font-semibold text-zinc-50">
          Submission #{submissionId} is being evaluated
        </h3>
        <span className="inline-flex shrink-0 items-center gap-1.5 rounded-full bg-teal-500/10 px-2 py-0.5 text-xs font-medium text-teal-400">
          <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-teal-400" />
          Live
        </span>
      </div>

      <div className="mt-3 h-1.5 w-full overflow-hidden rounded-full bg-zinc-800">
        <div
          className="h-full rounded-full bg-teal-500 transition-all duration-700 ease-out"
          style={{ width: `${progressPct}%` }}
        />
      </div>

      <StageStepper currentIndex={currentIndex} />

      <p className="mt-3 text-xs text-zinc-500">
        This runs in the background — usually under a minute. Feel free to
        browse other events; this will keep evaluating.
      </p>
    </div>
  );
}

export default function EventPage() {
  // :id from the route ("/events/:id") — the campaign this whole page
  // is about; every API call below is scoped to this id.
  const { id } = useParams<{ id: string }>();

  // --- Campaign data ---
  const [campaign, setCampaign] = useState<Campaign | null>(null);
  const [notFound, setNotFound] = useState(false);

  // --- Auth state ---
  // Lazily initialized: on first render, check the URL for a token
  // freshly delivered by the OAuth callback redirect; if there isn't
  // one, fall back to whatever's already in localStorage from a prior
  // visit. Either way this only runs once (the `() => ...` form).
  const [token, setToken] = useState<string | null>(
    () => captureTokenFromUrl() ?? getToken(),
  );
  const [repos, setRepos] = useState<Repo[]>([]);
  const [reposLoading, setReposLoading] = useState(false);

  // --- Submission form fields ---
  const [teamName, setTeamName] = useState("");
  const [githubUrl, setGithubUrl] = useState("");
  const [pitchText, setPitchText] = useState("");
  const [submitting, setSubmitting] = useState(false);

  // --- Live tracking of the submission just made ---
  // submittedId is null until the form is successfully submitted; the
  // other four mirror whatever the latest WebSocket message (or the
  // initial POST response) said about that one submission.
  const [submittedId, setSubmittedId] = useState<number | null>(null);
  const [liveStatus, setLiveStatus] = useState<Submission["status"] | null>(null);
  const [liveStage, setLiveStage] = useState<EvaluationStage | null>(null);
  const [liveScore, setLiveScore] = useState<number | null>(null);
  const [liveNotes, setLiveNotes] = useState<string | null>(null);

  const [error, setError] = useState<string | null>(null);

  // Fetch the campaign itself once, whenever the :id route param
  // changes (e.g. navigating between two different event pages).
  useEffect(() => {
    axios
      .get<Campaign>(`${API_BASE}/api/campaigns/${id}`)
      .then((res) => setCampaign(res.data))
      .catch((err: AxiosError) => {
        if (err.response?.status === 404) setNotFound(true);
        else setError("Could not load this event. Is the API running?");
      });
  }, [id]);

  // Once we have a token (either from initial load or right after
  // signing in), fetch the hacker's own GitHub repos to populate the
  // dropdown. Re-runs whenever `token` changes (login, or a 401 forcing
  // a sign-out below, which sets token back to null and skips this).
  useEffect(() => {
    if (!token) return;
    setReposLoading(true);
    axios
      .get<Repo[]>(`${API_BASE}/api/hacker/repos`, {
        headers: { Authorization: `Bearer ${token}` },
      })
      .then((res) => {
        setRepos(res.data);
        if (res.data.length > 0) setGithubUrl(res.data[0].url);
      })
      .catch((err: AxiosError) => {
        if (err.response?.status === 401) {
          // Stored GitHub token expired/revoked server-side; drop back
          // to the "please sign in" gate rather than showing a broken
          // empty dropdown.
          clearToken();
          setToken(null);
        } else {
          setError("Could not load your GitHub repositories.");
        }
      })
      .finally(() => setReposLoading(false));
  }, [token]);

  // Live progress for the submission just made: reuses the same
  // campaign Pub/Sub channel the organizer dashboard listens on, so the
  // hacker sees pipeline progress instead of a form that looks stuck.
  useEffect(() => {
    if (submittedId === null) return;
    const ws = new WebSocket(`ws://localhost:8000/api/campaigns/${id}/ws`);

    ws.onmessage = (event) => {
      let update: LiveUpdate;
      try {
        update = JSON.parse(event.data);
      } catch {
        return;
      }
      // This campaign's channel carries updates for *every* submission
      // to it, not just this hacker's — ignore anything that isn't the
      // one we just submitted.
      if (update.submission_id !== submittedId) return;
      setLiveStatus(update.status);
      setLiveStage(update.stage ?? null);
      setLiveScore(update.final_score);
      setLiveNotes(update.notes);
    };

    // Close the socket if submittedId changes again (a second
    // submission) or the component unmounts (navigating away).
    return () => ws.close();
  }, [submittedId, id]);

  const signOut = () => {
    clearToken();
    setToken(null);
    setRepos([]);
    setGithubUrl("");
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      const res = await axios.post<Submission>(
        `${API_BASE}/api/campaigns/${id}/submit`,
        { team_name: teamName, github_url: githubUrl, pitch_text: pitchText },
        { headers: { Authorization: `Bearer ${token}` } },
      );
      // Seed the live-tracking state from the 202 response itself
      // (status will be "pending"); the WebSocket effect above then
      // takes over as the worker actually starts processing it.
      setSubmittedId(res.data.id);
      setLiveStatus(res.data.status);
      setLiveStage(null);
      setLiveScore(res.data.final_score);
      setLiveNotes(res.data.notes);
      // Clear the form so the hacker could submit another project;
      // githubUrl is deliberately left as-is (still a valid repo choice).
      setTeamName("");
      setPitchText("");
    } catch (err) {
      // Surface the API's own error message (e.g. "Campaign is not
      // accepting submissions", "You must have push access to ...")
      // rather than a generic failure, whenever the backend supplied one.
      const ax = err as AxiosError<{ detail?: unknown }>;
      const detail = ax.response?.data?.detail;
      setError(
        typeof detail === "string"
          ? detail
          : "Submission failed. Check your inputs and that the API is running.",
      );
    } finally {
      setSubmitting(false);
    }
  };

  // Early return: a nonexistent/removed campaign gets its own minimal
  // page instead of falling through to the full event layout below.
  if (notFound) {
    return (
      <div className="min-h-screen bg-zinc-950">
        <TopNav />
        <main className="mx-auto max-w-2xl px-6 py-16 text-center">
          <h1 className="text-xl font-semibold text-zinc-50">
            Event not found
          </h1>
          <p className="mt-2 text-sm text-zinc-500">
            This event may have been removed.
          </p>
          <Link
            to="/"
            className="mt-6 inline-flex items-center gap-1.5 text-sm font-medium text-teal-400 hover:underline"
          >
            <ArrowLeft className="h-4 w-4" />
            Back to all events
          </Link>
        </main>
      </div>
    );
  }

  const isOpen = campaign?.status === "open";

  return (
    <div className="min-h-screen bg-zinc-950">
      <TopNav />

      <main className="mx-auto max-w-2xl px-6 py-8">
        <Link
          to="/"
          className="inline-flex items-center gap-1 text-sm text-zinc-500 hover:text-zinc-50"
        >
          <ArrowLeft className="h-4 w-4" />
          All events
        </Link>

        {/* Everything below only renders once the campaign has loaded;
            until then just show a loading line under the back-link. */}
        {!campaign ? (
          <p className="mt-6 text-sm text-zinc-500">Loading event…</p>
        ) : (
          <>
            {/* Campaign details card: name, status, deadline, entry
                limits, and (if any exist) the full judging rubric —
                shown before any auth gate so a hacker can decide
                whether to bother signing in at all. */}
            <div className="mt-4 rounded-lg border border-white/10 bg-zinc-900 p-6">
              <div className="flex items-start justify-between gap-3">
                <h1 className="text-xl font-bold text-zinc-50">
                  {campaign.name}
                </h1>
                <span
                  className={`inline-flex shrink-0 items-center rounded-full px-2.5 py-0.5 text-xs font-medium ring-1 ring-inset ${
                    isOpen
                      ? "bg-emerald-500/10 text-emerald-400 ring-emerald-500/20"
                      : "bg-zinc-800 text-zinc-400 ring-white/10"
                  }`}
                >
                  {campaign.status}
                </span>
              </div>
              <p className="mt-2 flex items-center gap-1.5 text-sm text-zinc-400">
                <CalendarClock className="h-4 w-4 text-zinc-500" />
                Submissions close {formatDeadline(campaign.deadline)}
              </p>
              <p className="mt-1 text-xs text-zinc-500">
                Max team size {campaign.max_team_size} · Up to{" "}
                {campaign.max_submissions_per_team} submission
                {campaign.max_submissions_per_team === 1 ? "" : "s"} per team
              </p>

              {campaign.rules.length > 0 && (
                <div className="mt-4 border-t border-white/10 pt-4">
                  <h2 className="flex items-center gap-1.5 text-sm font-semibold text-zinc-300">
                    <ClipboardList className="h-4 w-4 text-teal-400" />
                    How you'll be judged
                  </h2>
                  <ul className="mt-2 space-y-1.5">
                    {campaign.rules.map((r) => (
                      <li
                        key={r.id}
                        className="flex items-baseline justify-between gap-3 text-sm text-zinc-400"
                      >
                        <span>{r.description}</span>
                        <span className="shrink-0 text-xs tabular-nums text-zinc-600">
                          ×{r.weight}
                        </span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>

            {/* Appears only after a successful submit; disappears again
                if the hacker never submits (submittedId stays null). */}
            {submittedId !== null && (
              <SubmissionTracker
                submissionId={submittedId}
                status={liveStatus}
                stage={liveStage}
                score={liveScore}
                notes={liveNotes}
              />
            )}

            {error && (
              <div className="mt-6 rounded-md border border-red-500/20 bg-red-500/10 p-3 text-sm text-red-400">
                {error}
              </div>
            )}

            {/* Three mutually exclusive states below the details card:
                  1. campaign closed -> just a notice, no form at all
                  2. campaign open but not signed in -> GitHub auth gate
                  3. campaign open and signed in -> the actual form */}
            {!isOpen ? (
              <div className="mt-6 rounded-md border border-amber-500/20 bg-amber-500/10 p-3 text-sm text-amber-400">
                This event is not accepting submissions right now.
              </div>
            ) : !token ? (
              <div className="mt-6 rounded-lg border border-white/10 bg-zinc-900 p-10 text-center">
                <GithubMark className="mx-auto h-10 w-10 text-zinc-50" />
                <h2 className="mt-4 text-lg font-semibold text-zinc-50">
                  Verify your identity to submit
                </h2>
                <p className="mx-auto mt-1 max-w-sm text-sm text-zinc-500">
                  TruPitch verifies submissions against your real GitHub
                  repositories. Sign in to pick the repo you are submitting.
                </p>
                {/* `next` carries this exact event page's path through
                    the OAuth flow, so the callback redirect lands back
                    here rather than on the homepage — see
                    apps/api/routers/auth.py's github_login/_safe_next. */}
                <a
                  href={`${API_BASE}/api/auth/github/login?next=/events/${id}`}
                  className="mt-6 inline-flex items-center gap-2 rounded-md bg-zinc-50 px-6 py-3 text-sm font-semibold text-zinc-950 hover:bg-zinc-200"
                >
                  <GithubMark className="h-4 w-4" />
                  Authenticate with GitHub
                </a>
              </div>
            ) : (
              <>
                <form
                  onSubmit={handleSubmit}
                  className="mt-6 space-y-4 rounded-lg border border-white/10 bg-zinc-900 p-6"
                >
                  <h2 className="text-sm font-semibold uppercase tracking-wide text-zinc-400">
                    Your submission
                  </h2>

                  <div>
                    <label
                      htmlFor="team"
                      className="mb-1 block text-sm font-medium text-zinc-300"
                    >
                      Team name
                    </label>
                    <input
                      id="team"
                      type="text"
                      required
                      value={teamName}
                      onChange={(e) => setTeamName(e.target.value)}
                      placeholder="The Null Pointers"
                      className={INPUT_CLASS}
                    />
                  </div>

                  <div>
                    <label
                      htmlFor="repo"
                      className="mb-1 block text-sm font-medium text-zinc-300"
                    >
                      GitHub repository
                    </label>
                    {/* A <select> of the hacker's own repos, not a free-
                        text URL field — the dropdown only ever lists
                        repos GitHub says belong to this account, and
                        the API independently re-verifies push access
                        server-side on submit (defense in depth). */}
                    <select
                      id="repo"
                      required
                      value={githubUrl}
                      onChange={(e) => setGithubUrl(e.target.value)}
                      disabled={reposLoading || repos.length === 0}
                      className={`${INPUT_CLASS} disabled:cursor-not-allowed disabled:opacity-60`}
                    >
                      {reposLoading ? (
                        <option value="">Loading your repositories…</option>
                      ) : repos.length === 0 ? (
                        <option value="">No repositories found</option>
                      ) : (
                        repos.map((r) => (
                          <option key={r.url} value={r.url}>
                            {r.name}
                          </option>
                        ))
                      )}
                    </select>
                  </div>

                  <div>
                    <label
                      htmlFor="pitch"
                      className="mb-1 block text-sm font-medium text-zinc-300"
                    >
                      Pitch
                    </label>
                    <textarea
                      id="pitch"
                      required
                      rows={5}
                      value={pitchText}
                      onChange={(e) => setPitchText(e.target.value)}
                      placeholder="What did you build, and why does it matter?"
                      className={INPUT_CLASS}
                    />
                  </div>

                  <button
                    type="submit"
                    disabled={submitting || !githubUrl}
                    className="w-full rounded-md bg-teal-600 px-4 py-2 text-sm font-semibold text-white hover:bg-teal-500 disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    {submitting ? "Submitting…" : "Submit project"}
                  </button>
                </form>

                <p className="mt-3 text-center text-xs text-zinc-500">
                  Signed in with GitHub.{" "}
                  <button
                    onClick={signOut}
                    className="text-teal-400 hover:underline"
                  >
                    Sign out
                  </button>
                </p>
              </>
            )}
          </>
        )}
      </main>
    </div>
  );
}
