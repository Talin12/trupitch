import { useState } from "react";
import axios, { AxiosError } from "axios";
import { useNavigate } from "react-router-dom";
import {
  ArrowLeft,
  CalendarClock,
  ClipboardList,
  Plus,
  Settings2,
  Trash2,
} from "lucide-react";
import { API_BASE } from "../types";

interface RuleDraft {
  description: string;
  weight: number;
}

const INPUT_CLASS =
  "w-full rounded-md border border-white/10 bg-zinc-950 px-3 py-2 text-sm text-zinc-50 " +
  "placeholder:text-zinc-500 focus:border-teal-500 focus:outline-none " +
  "focus:ring-1 focus:ring-teal-500";

const LABEL_CLASS = "mb-1 block text-sm font-medium text-zinc-300";

function Toggle({
  checked,
  onChange,
  label,
  description,
}: {
  checked: boolean;
  onChange: (value: boolean) => void;
  label: string;
  description: string;
}) {
  return (
    <div className="flex items-center justify-between gap-4">
      <div>
        <p className="text-sm font-medium text-zinc-300">{label}</p>
        <p className="text-xs text-zinc-500">{description}</p>
      </div>
      <button
        type="button"
        role="switch"
        aria-checked={checked}
        onClick={() => onChange(!checked)}
        className={`relative inline-flex h-6 w-11 shrink-0 items-center rounded-full transition-colors focus:outline-none focus:ring-1 focus:ring-teal-500 focus:ring-offset-2 focus:ring-offset-zinc-900 ${
          checked ? "bg-teal-600" : "bg-zinc-700"
        }`}
      >
        <span
          className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
            checked ? "translate-x-6" : "translate-x-1"
          }`}
        />
      </button>
    </div>
  );
}

export default function CampaignBuilder() {
  const navigate = useNavigate();
  const [name, setName] = useState("");
  const [startDate, setStartDate] = useState("");
  const [deadline, setDeadline] = useState("");
  const [maxTeamSize, setMaxTeamSize] = useState(4);
  const [maxSubmissionsPerTeam, setMaxSubmissionsPerTeam] = useState(1);
  const [allowLateSubmissions, setAllowLateSubmissions] = useState(false);
  const [rules, setRules] = useState<RuleDraft[]>([
    { description: "Uses AI meaningfully, not as a gimmick", weight: 1.0 },
  ]);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const addRule = () =>
    setRules((prev) => [...prev, { description: "", weight: 1.0 }]);

  const removeRule = (index: number) =>
    setRules((prev) => prev.filter((_, i) => i !== index));

  const updateRule = (index: number, patch: Partial<RuleDraft>) =>
    setRules((prev) =>
      prev.map((rule, i) => (i === index ? { ...rule, ...patch } : rule)),
    );

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    const cleanRules = rules.filter((r) => r.description.trim().length > 0);
    if (!name.trim() || !deadline || cleanRules.length === 0) {
      setError(
        "A campaign needs a name, a deadline, and at least one rubric rule.",
      );
      return;
    }

    setSubmitting(true);
    try {
      await axios.post(`${API_BASE}/api/campaigns`, {
        name: name.trim(),
        start_date: startDate ? new Date(startDate).toISOString() : null,
        deadline: new Date(deadline).toISOString(),
        status: "open",
        max_team_size: maxTeamSize,
        max_submissions_per_team: maxSubmissionsPerTeam,
        allow_late_submissions: allowLateSubmissions,
        rules: cleanRules,
      });
      navigate("/admin");
    } catch (err) {
      const ax = err as AxiosError<{ detail?: unknown }>;
      const detail = ax.response?.data?.detail;
      setError(
        typeof detail === "string"
          ? detail
          : "Could not create the campaign. Check the API is running on port 8000.",
      );
      setSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-zinc-950">
      <header className="border-b border-white/10 bg-zinc-950">
        <div className="mx-auto flex max-w-5xl items-center gap-3 px-6 py-4">
          <button
            onClick={() => navigate("/admin")}
            className="inline-flex items-center gap-1 text-sm text-zinc-500 hover:text-zinc-50"
          >
            <ArrowLeft className="h-4 w-4" />
            Dashboard
          </button>
          <span className="text-zinc-700">/</span>
          <h1 className="text-lg font-semibold text-zinc-50">New Campaign</h1>
        </div>
      </header>

      <main className="mx-auto max-w-5xl px-6 py-8">
        {error && (
          <div className="mb-6 rounded-md border border-red-500/20 bg-red-500/10 p-3 text-sm text-red-400">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-6">
          <div className="grid gap-6 lg:grid-cols-2">
            <section className="rounded-lg border border-white/10 bg-zinc-900 p-6">
              <div className="mb-4 flex items-center gap-2">
                <Settings2 className="h-4 w-4 text-teal-400" />
                <h2 className="text-sm font-semibold uppercase tracking-wide text-zinc-400">
                  Standard Configuration
                </h2>
              </div>

              <div className="space-y-4">
                <div>
                  <label htmlFor="name" className={LABEL_CLASS}>
                    Campaign name
                  </label>
                  <input
                    id="name"
                    type="text"
                    required
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    placeholder="Spring AI Hackathon 2026"
                    className={INPUT_CLASS}
                  />
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label htmlFor="startDate" className={LABEL_CLASS}>
                      Start date
                    </label>
                    <input
                      id="startDate"
                      type="datetime-local"
                      value={startDate}
                      onChange={(e) => setStartDate(e.target.value)}
                      className={INPUT_CLASS}
                    />
                  </div>
                  <div>
                    <label htmlFor="deadline" className={LABEL_CLASS}>
                      Deadline
                    </label>
                    <input
                      id="deadline"
                      type="datetime-local"
                      required
                      value={deadline}
                      onChange={(e) => setDeadline(e.target.value)}
                      className={INPUT_CLASS}
                    />
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label htmlFor="teamSize" className={LABEL_CLASS}>
                      Max team size
                    </label>
                    <input
                      id="teamSize"
                      type="number"
                      min={1}
                      required
                      value={maxTeamSize}
                      onChange={(e) => setMaxTeamSize(Number(e.target.value))}
                      className={INPUT_CLASS}
                    />
                  </div>
                  <div>
                    <label htmlFor="subsPerTeam" className={LABEL_CLASS}>
                      Submissions / team
                    </label>
                    <input
                      id="subsPerTeam"
                      type="number"
                      min={1}
                      required
                      value={maxSubmissionsPerTeam}
                      onChange={(e) =>
                        setMaxSubmissionsPerTeam(Number(e.target.value))
                      }
                      className={INPUT_CLASS}
                    />
                  </div>
                </div>

                <div className="rounded-md border border-white/10 bg-zinc-950 px-4 py-3">
                  <Toggle
                    checked={allowLateSubmissions}
                    onChange={setAllowLateSubmissions}
                    label="Allow late submissions"
                    description="Accept submissions after the deadline has passed"
                  />
                </div>
              </div>
            </section>

            <section className="rounded-lg border border-white/10 bg-zinc-900 p-6">
              <div className="mb-1 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <ClipboardList className="h-4 w-4 text-teal-400" />
                  <h2 className="text-sm font-semibold uppercase tracking-wide text-zinc-400">
                    Evaluation Rubric
                  </h2>
                </div>
                <button
                  type="button"
                  onClick={addRule}
                  className="inline-flex items-center gap-1 rounded-md border border-white/10 bg-zinc-950 px-2.5 py-1.5 text-xs font-medium text-zinc-300 hover:bg-zinc-800"
                >
                  <Plus className="h-3.5 w-3.5" />
                  Add Rule
                </button>
              </div>
              <p className="mb-4 text-xs text-zinc-500">
                The AI judge weighs each rule by its weight when scoring
                submissions.
              </p>

              <div className="space-y-2">
                {rules.map((rule, index) => (
                  <div
                    key={index}
                    className="flex items-center gap-2 rounded-md border border-white/5 bg-zinc-950/60 p-2"
                  >
                    <input
                      type="text"
                      value={rule.description}
                      onChange={(e) =>
                        updateRule(index, { description: e.target.value })
                      }
                      placeholder="e.g. Working end-to-end demo in the repo"
                      className={`${INPUT_CLASS} border-transparent bg-transparent px-2 py-1.5`}
                    />
                    <input
                      type="number"
                      step="0.1"
                      min="0.1"
                      value={rule.weight}
                      onChange={(e) =>
                        updateRule(index, { weight: Number(e.target.value) })
                      }
                      aria-label="Rule weight"
                      className={`${INPUT_CLASS} w-16 shrink-0 px-2 py-1.5 text-center`}
                    />
                    <button
                      type="button"
                      onClick={() => removeRule(index)}
                      disabled={rules.length === 1}
                      aria-label="Remove rule"
                      className="shrink-0 rounded-md p-1.5 text-zinc-600 hover:bg-red-500/10 hover:text-red-400 disabled:cursor-not-allowed disabled:opacity-40"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                ))}
              </div>
            </section>
          </div>

          <div className="flex items-center justify-between gap-3 rounded-lg border border-white/10 bg-zinc-900 px-6 py-4">
            <p className="flex items-center gap-1.5 text-xs text-zinc-500">
              <CalendarClock className="h-3.5 w-3.5" />
              Campaign opens immediately for submissions once created.
            </p>
            <div className="flex gap-3">
              <button
                type="button"
                onClick={() => navigate("/admin")}
                className="rounded-md border border-white/10 bg-zinc-950 px-4 py-2 text-sm font-medium text-zinc-300 hover:bg-zinc-800"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={submitting}
                className="rounded-md bg-teal-600 px-4 py-2 text-sm font-semibold text-white hover:bg-teal-500 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {submitting ? "Creating…" : "Create Campaign"}
              </button>
            </div>
          </div>
        </form>
      </main>
    </div>
  );
}
