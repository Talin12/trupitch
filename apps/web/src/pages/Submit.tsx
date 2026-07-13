import { useEffect, useState } from "react";
import axios, { AxiosError } from "axios";
import { CheckCircle2, Rocket } from "lucide-react";
import { API_BASE, type Campaign, type Submission } from "../types";

function GithubMark({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 16 16" fill="currentColor" className={className} aria-hidden>
      <path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27s1.36.09 2 .27c1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.01 8.01 0 0 0 16 8c0-4.42-3.58-8-8-8Z" />
    </svg>
  );
}

const TOKEN_KEY = "trupitch_token";

const INPUT_CLASS =
  "w-full rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-900 " +
  "placeholder:text-slate-400 focus:border-indigo-500 focus:outline-none " +
  "focus:ring-1 focus:ring-indigo-500";

interface Repo {
  name: string;
  url: string;
}

export default function Submit() {
  const [token, setToken] = useState<string | null>(() =>
    localStorage.getItem(TOKEN_KEY),
  );
  const [repos, setRepos] = useState<Repo[]>([]);
  const [reposLoading, setReposLoading] = useState(false);
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [campaignsLoaded, setCampaignsLoaded] = useState(false);
  const [selectedCampaignId, setSelectedCampaignId] = useState<number | null>(
    null,
  );
  const [teamName, setTeamName] = useState("");
  const [githubUrl, setGithubUrl] = useState("");
  const [pitchText, setPitchText] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [submittedId, setSubmittedId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Capture ?token=... arriving from the OAuth callback, then clean the URL.
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const incoming = params.get("token");
    if (incoming) {
      localStorage.setItem(TOKEN_KEY, incoming);
      setToken(incoming);
      window.history.replaceState({}, "", window.location.pathname);
    }
  }, []);

  useEffect(() => {
    axios
      .get<Campaign[]>(`${API_BASE}/api/campaigns`)
      .then((res) => {
        const open = res.data.filter((c) => c.status === "open");
        setCampaigns(open);
        if (open.length > 0) setSelectedCampaignId(open[0].id);
      })
      .catch(() =>
        setError("Could not load hackathons. Is the API running on port 8000?"),
      )
      .finally(() => setCampaignsLoaded(true));
  }, []);

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
          // Session or GitHub token expired: back to the auth gate.
          localStorage.removeItem(TOKEN_KEY);
          setToken(null);
        } else {
          setError("Could not load your GitHub repositories.");
        }
      })
      .finally(() => setReposLoading(false));
  }, [token]);

  const signOut = () => {
    localStorage.removeItem(TOKEN_KEY);
    setToken(null);
    setRepos([]);
    setGithubUrl("");
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (selectedCampaignId === null) return;
    setSubmitting(true);
    setError(null);
    try {
      const res = await axios.post<Submission>(
        `${API_BASE}/api/campaigns/${selectedCampaignId}/submit`,
        { team_name: teamName, github_url: githubUrl, pitch_text: pitchText },
        { headers: { Authorization: `Bearer ${token}` } },
      );
      setSubmittedId(res.data.id);
      setTeamName("");
      setPitchText("");
    } catch (err) {
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

  const noneOpen = campaignsLoaded && campaigns.length === 0;

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-50 px-4">
      <div className="w-full max-w-lg">
        <div className="mb-6 text-center">
          <div className="mb-2 inline-flex items-center gap-2">
            <Rocket className="h-6 w-6 text-indigo-600" />
            <h1 className="text-2xl font-bold text-slate-900">TruPitch</h1>
          </div>
          <p className="text-sm text-slate-500">
            Submit your hackathon project for automated evaluation.
          </p>
        </div>

        {submittedId !== null && (
          <div className="mb-4 flex items-start gap-2 rounded-md border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-800">
            <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0" />
            <span>
              Submission <strong>#{submittedId}</strong> received and queued for
              evaluation. Save this ID to check your status.
            </span>
          </div>
        )}

        {error && (
          <div className="mb-4 rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700">
            {error}
          </div>
        )}

        {!token ? (
          <div className="rounded-lg border border-slate-200 bg-white p-10 text-center shadow-sm">
            <GithubMark className="mx-auto h-10 w-10 text-slate-900" />
            <h2 className="mt-4 text-lg font-semibold text-slate-900">
              Verify your identity
            </h2>
            <p className="mx-auto mt-1 max-w-sm text-sm text-slate-500">
              TruPitch verifies submissions against your real GitHub
              repositories. Sign in to pick the repo you are submitting.
            </p>
            <a
              href={`${API_BASE}/api/auth/github/login`}
              className="mt-6 inline-flex items-center gap-2 rounded-md bg-slate-900 px-6 py-3 text-sm font-semibold text-white hover:bg-slate-700"
            >
              <GithubMark className="h-4 w-4" />
              Authenticate with GitHub
            </a>
          </div>
        ) : (
          <>
            {noneOpen && (
              <div className="mb-4 rounded-md border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800">
                No hackathons are currently open for submissions. Check back
                soon!
              </div>
            )}

            <form
              onSubmit={handleSubmit}
              className="space-y-4 rounded-lg border border-slate-200 bg-white p-6 shadow-sm"
            >
              <div>
                <label
                  htmlFor="campaign"
                  className="mb-1 block text-sm font-medium text-slate-700"
                >
                  Select hackathon
                </label>
                <select
                  id="campaign"
                  required
                  value={selectedCampaignId ?? ""}
                  onChange={(e) =>
                    setSelectedCampaignId(Number(e.target.value))
                  }
                  disabled={campaigns.length === 0}
                  className={`${INPUT_CLASS} disabled:cursor-not-allowed disabled:bg-slate-50 disabled:text-slate-400`}
                >
                  {campaigns.length === 0 ? (
                    <option value="">No open hackathons</option>
                  ) : (
                    campaigns.map((c) => (
                      <option key={c.id} value={c.id}>
                        {c.name}
                      </option>
                    ))
                  )}
                </select>
              </div>

              <div>
                <label
                  htmlFor="team"
                  className="mb-1 block text-sm font-medium text-slate-700"
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
                  className="mb-1 block text-sm font-medium text-slate-700"
                >
                  GitHub repository
                </label>
                <select
                  id="repo"
                  required
                  value={githubUrl}
                  onChange={(e) => setGithubUrl(e.target.value)}
                  disabled={reposLoading || repos.length === 0}
                  className={`${INPUT_CLASS} disabled:cursor-not-allowed disabled:bg-slate-50 disabled:text-slate-400`}
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
                  className="mb-1 block text-sm font-medium text-slate-700"
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
                disabled={
                  submitting || selectedCampaignId === null || !githubUrl
                }
                className="w-full rounded-md bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-500 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {submitting
                  ? "Submitting…"
                  : selectedCampaignId === null
                    ? "No open hackathons"
                    : "Submit project"}
              </button>
            </form>

            <p className="mt-3 text-center text-xs text-slate-400">
              Signed in with GitHub.{" "}
              <button
                onClick={signOut}
                className="text-indigo-600 hover:underline"
              >
                Sign out
              </button>
            </p>
          </>
        )}

        <p className="mt-4 text-center text-xs text-slate-400">
          Organizer?{" "}
          <a href="/admin" className="text-indigo-600 hover:underline">
            Open the dashboard
          </a>
        </p>
      </div>
    </div>
  );
}
