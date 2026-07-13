import { useState } from "react";
import axios, { AxiosError } from "axios";
import { useNavigate } from "react-router-dom";
import { ArrowLeft, CalendarClock, ClipboardList, Plus, Trash2 } from "lucide-react";
import { API_BASE } from "../types";

interface RuleDraft {
  description: string;
  weight: number;
}

const INPUT_CLASS =
  "w-full rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-900 " +
  "placeholder:text-slate-400 focus:border-indigo-500 focus:outline-none " +
  "focus:ring-1 focus:ring-indigo-500";

export default function CampaignBuilder() {
  const navigate = useNavigate();
  const [name, setName] = useState("");
  const [deadline, setDeadline] = useState("");
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
      // organizer_id omitted: the API resolves the configured default
      // organizer until organizer auth exists.
      await axios.post(`${API_BASE}/api/campaigns`, {
        name: name.trim(),
        // datetime-local is timezone-naive; send an explicit UTC instant
        deadline: new Date(deadline).toISOString(),
        status: "open",
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
    <div className="min-h-screen bg-slate-50">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-3xl items-center gap-3 px-6 py-4">
          <button
            onClick={() => navigate("/admin")}
            className="inline-flex items-center gap-1 text-sm text-slate-500 hover:text-slate-900"
          >
            <ArrowLeft className="h-4 w-4" />
            Dashboard
          </button>
          <span className="text-slate-300">/</span>
          <h1 className="text-lg font-semibold text-slate-900">New Campaign</h1>
        </div>
      </header>

      <main className="mx-auto max-w-3xl px-6 py-8">
        {error && (
          <div className="mb-6 rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-6">
          <section className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
            <div className="mb-4 flex items-center gap-2">
              <CalendarClock className="h-4 w-4 text-indigo-600" />
              <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-700">
                General Info
              </h2>
            </div>

            <div className="space-y-4">
              <div>
                <label
                  htmlFor="name"
                  className="mb-1 block text-sm font-medium text-slate-700"
                >
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

              <div>
                <label
                  htmlFor="deadline"
                  className="mb-1 block text-sm font-medium text-slate-700"
                >
                  Submission deadline
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
          </section>

          <section className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
            <div className="mb-1 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <ClipboardList className="h-4 w-4 text-indigo-600" />
                <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-700">
                  Evaluation Rubric
                </h2>
              </div>
              <button
                type="button"
                onClick={addRule}
                className="inline-flex items-center gap-1 rounded-md border border-slate-300 bg-white px-2.5 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50"
              >
                <Plus className="h-3.5 w-3.5" />
                Add Rule
              </button>
            </div>
            <p className="mb-4 text-xs text-slate-400">
              The AI judge weighs each rule by its weight when scoring
              submissions.
            </p>

            <div className="space-y-3">
              {rules.map((rule, index) => (
                <div key={index} className="flex items-start gap-2">
                  <input
                    type="text"
                    value={rule.description}
                    onChange={(e) =>
                      updateRule(index, { description: e.target.value })
                    }
                    placeholder="e.g. Working end-to-end demo in the repo"
                    className={INPUT_CLASS}
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
                    className={`${INPUT_CLASS} w-24 shrink-0`}
                  />
                  <button
                    type="button"
                    onClick={() => removeRule(index)}
                    disabled={rules.length === 1}
                    aria-label="Remove rule"
                    className="mt-1 shrink-0 rounded-md p-1.5 text-slate-400 hover:bg-red-50 hover:text-red-600 disabled:cursor-not-allowed disabled:opacity-40"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
              ))}
            </div>
          </section>

          <div className="flex justify-end gap-3">
            <button
              type="button"
              onClick={() => navigate("/admin")}
              className="rounded-md border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={submitting}
              className="rounded-md bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-500 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {submitting ? "Creating…" : "Create Campaign"}
            </button>
          </div>
        </form>
      </main>
    </div>
  );
}
