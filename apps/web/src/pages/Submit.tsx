import { useState } from "react";
import axios, { AxiosError } from "axios";
import { CheckCircle2, Rocket } from "lucide-react";
import { API_BASE, type Submission } from "../types";

export default function Submit() {
  const [teamName, setTeamName] = useState("");
  const [githubUrl, setGithubUrl] = useState("");
  const [pitchText, setPitchText] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [submittedId, setSubmittedId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      const res = await axios.post<Submission>(
        `${API_BASE}/api/campaigns/1/submit`,
        { team_name: teamName, github_url: githubUrl, pitch_text: pitchText },
      );
      setSubmittedId(res.data.id);
      setTeamName("");
      setGithubUrl("");
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

        <form
          onSubmit={handleSubmit}
          className="space-y-4 rounded-lg border border-slate-200 bg-white p-6 shadow-sm"
        >
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
              className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-900 placeholder:text-slate-400 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
            />
          </div>

          <div>
            <label
              htmlFor="repo"
              className="mb-1 block text-sm font-medium text-slate-700"
            >
              GitHub repository URL
            </label>
            <input
              id="repo"
              type="url"
              required
              value={githubUrl}
              onChange={(e) => setGithubUrl(e.target.value)}
              placeholder="https://github.com/you/your-project"
              className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-900 placeholder:text-slate-400 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
            />
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
              className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-900 placeholder:text-slate-400 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
            />
          </div>

          <button
            type="submit"
            disabled={submitting}
            className="w-full rounded-md bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-500 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {submitting ? "Submitting…" : "Submit project"}
          </button>
        </form>

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
