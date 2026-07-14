import { useEffect, useState } from "react";
import axios from "axios";
import { Link } from "react-router-dom";
import { ArrowRight, CalendarClock, ClipboardList, ShieldCheck } from "lucide-react";
import TopNav from "../components/TopNav";
import { API_BASE, type Campaign } from "../types";

function formatDeadline(iso: string): string {
  return new Date(iso).toLocaleString(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  });
}

function EventCard({ campaign }: { campaign: Campaign }) {
  return (
    <Link
      to={`/events/${campaign.id}`}
      className="group flex flex-col rounded-lg border border-slate-200 bg-white p-5 shadow-sm transition hover:border-teal-400 hover:shadow"
    >
      <div className="flex items-start justify-between gap-3">
        <h3 className="text-base font-semibold text-slate-900">
          {campaign.name}
        </h3>
        <span className="inline-flex shrink-0 items-center rounded-full bg-emerald-50 px-2.5 py-0.5 text-xs font-medium text-emerald-700 ring-1 ring-inset ring-emerald-600/20">
          open
        </span>
      </div>
      <div className="mt-3 space-y-1.5 text-sm text-slate-500">
        <p className="flex items-center gap-1.5">
          <CalendarClock className="h-4 w-4 text-slate-400" />
          Closes {formatDeadline(campaign.deadline)}
        </p>
        <p className="flex items-center gap-1.5">
          <ClipboardList className="h-4 w-4 text-slate-400" />
          {campaign.rules.length} judging{" "}
          {campaign.rules.length === 1 ? "criterion" : "criteria"}
        </p>
      </div>
      <span className="mt-4 inline-flex items-center gap-1 text-sm font-medium text-teal-600 group-hover:gap-2 transition-all">
        View event & submit
        <ArrowRight className="h-4 w-4" />
      </span>
    </Link>
  );
}

export default function Home() {
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [loaded, setLoaded] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    axios
      .get<Campaign[]>(`${API_BASE}/api/campaigns`)
      .then((res) => setCampaigns(res.data.filter((c) => c.status === "open")))
      .catch(() =>
        setError("Could not load events. Is the API running on port 8000?"),
      )
      .finally(() => setLoaded(true));
  }, []);

  return (
    <div className="min-h-screen bg-slate-50">
      <TopNav />

      <section className="border-b border-slate-200 bg-white">
        <div className="mx-auto max-w-5xl px-6 py-16 text-center">
          <h1 className="text-3xl font-bold tracking-tight text-slate-900 sm:text-4xl">
            Hackathon submissions, evaluated fairly.
          </h1>
          <p className="mx-auto mt-3 max-w-2xl text-base text-slate-500">
            TruPitch verifies your GitHub repository, analyzes your code
            structure, and scores your pitch against the organizer's rubric —
            automatically and transparently.
          </p>
          <p className="mt-6 inline-flex items-center gap-2 rounded-full bg-slate-100 px-4 py-1.5 text-sm text-slate-600">
            <ShieldCheck className="h-4 w-4 text-teal-600" />
            Identity verified through GitHub — no fake submissions
          </p>
        </div>
      </section>

      <main className="mx-auto max-w-5xl px-6 py-10">
        <h2 className="mb-4 text-sm font-semibold uppercase tracking-wide text-slate-700">
          Open events
        </h2>

        {error && (
          <div className="mb-6 rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700">
            {error}
          </div>
        )}

        {!loaded ? (
          <p className="text-sm text-slate-500">Loading events…</p>
        ) : campaigns.length === 0 && !error ? (
          <div className="rounded-lg border border-dashed border-slate-300 bg-white p-12 text-center">
            <CalendarClock className="mx-auto h-8 w-8 text-slate-300" />
            <h3 className="mt-3 text-base font-semibold text-slate-900">
              No events are open right now
            </h3>
            <p className="mt-1 text-sm text-slate-500">
              Check back soon — organizers open new hackathons regularly.
            </p>
          </div>
        ) : (
          <div className="grid gap-4 sm:grid-cols-2">
            {campaigns.map((c) => (
              <EventCard key={c.id} campaign={c} />
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
