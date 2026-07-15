// Public landing page ("/"): a hero section plus a grid of currently
// open hackathon events. This is the hacker's entry point into the
// app — clicking an event card goes to EventPage.tsx, where
// authentication and the actual submission form live.

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

// One clickable card per open campaign, showing just enough to decide
// whether to click in: name, deadline, and rubric size. The full rubric
// (each rule's text and weight) only appears on EventPage.
function EventCard({ campaign }: { campaign: Campaign }) {
  return (
    <Link
      to={`/events/${campaign.id}`}
      className="group flex flex-col rounded-lg border border-white/10 bg-zinc-900 p-5 transition hover:border-teal-500/50"
    >
      <div className="flex items-start justify-between gap-3">
        <h3 className="text-base font-semibold text-zinc-50">
          {campaign.name}
        </h3>
        {/* Static "open" badge is safe here because this component only
            ever renders campaigns already filtered to status === "open"
            (see the campaigns.filter call below). */}
        <span className="inline-flex shrink-0 items-center rounded-full bg-emerald-500/10 px-2.5 py-0.5 text-xs font-medium text-emerald-400 ring-1 ring-inset ring-emerald-500/20">
          open
        </span>
      </div>
      <div className="mt-3 space-y-1.5 text-sm text-zinc-400">
        <p className="flex items-center gap-1.5">
          <CalendarClock className="h-4 w-4 text-zinc-500" />
          Closes {formatDeadline(campaign.deadline)}
        </p>
        <p className="flex items-center gap-1.5">
          <ClipboardList className="h-4 w-4 text-zinc-500" />
          {campaign.rules.length} judging{" "}
          {campaign.rules.length === 1 ? "criterion" : "criteria"}
        </p>
      </div>
      <span className="mt-4 inline-flex items-center gap-1 text-sm font-medium text-teal-400 transition-all group-hover:gap-2">
        View event & submit
        <ArrowRight className="h-4 w-4" />
      </span>
    </Link>
  );
}

export default function Home() {
  // campaigns is already filtered to status === "open" before it's
  // stored — nothing downstream needs to re-check status.
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [loaded, setLoaded] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // One-shot fetch on mount: this page doesn't need live updates (no
  // WebSocket here), since new campaigns opening is a rare, organizer-
  // driven event rather than something that changes second-to-second.
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
    <div className="min-h-screen bg-zinc-950">
      <TopNav />

      <section className="border-b border-white/10">
        <div className="mx-auto max-w-5xl px-6 py-16 text-center">
          <h1 className="text-3xl font-bold tracking-tight text-zinc-50 sm:text-4xl">
            Hackathon submissions, evaluated fairly.
          </h1>
          <p className="mx-auto mt-3 max-w-2xl text-base text-zinc-400">
            TruPitch verifies your GitHub repository, analyzes your code
            structure, and scores your pitch against the organizer's rubric —
            automatically and transparently.
          </p>
          <p className="mt-6 inline-flex items-center gap-2 rounded-full border border-white/10 bg-zinc-900 px-4 py-1.5 text-sm text-zinc-400">
            <ShieldCheck className="h-4 w-4 text-teal-400" />
            Identity verified through GitHub — no fake submissions
          </p>
        </div>
      </section>

      <main className="mx-auto max-w-5xl px-6 py-10">
        <h2 className="mb-4 text-sm font-semibold uppercase tracking-wide text-zinc-400">
          Open events
        </h2>

        {error && (
          <div className="mb-6 rounded-md border border-red-500/20 bg-red-500/10 p-3 text-sm text-red-400">
            {error}
          </div>
        )}

        {/* Three distinct states: still loading, loaded-but-empty, and
            loaded-with-results — kept as an if/else-if chain so only one
            of "Loading…", the empty state, or the grid ever renders. */}
        {!loaded ? (
          <p className="text-sm text-zinc-500">Loading events…</p>
        ) : campaigns.length === 0 && !error ? (
          <div className="rounded-lg border border-dashed border-white/10 bg-zinc-900 p-12 text-center">
            <CalendarClock className="mx-auto h-8 w-8 text-zinc-700" />
            <h3 className="mt-3 text-base font-semibold text-zinc-50">
              No events are open right now
            </h3>
            <p className="mt-1 text-sm text-zinc-500">
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
