import { createFileRoute, Link } from "@tanstack/react-router";
import { CalendarPlus, Activity, Sparkles, Map, GitCompare } from "lucide-react";
import { AppShell } from "@/components/AppShell";
import { useEventsQuery } from "@/components/EventSelect";
import { EmptyState, ErrorState, LoadingState } from "@/components/states";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { setStoredEventId } from "@/lib/useSelectedEvent";

export const Route = createFileRoute("/dashboard")({
  head: () => ({
    meta: [
      { title: "Dashboard — SafeStage" },
      { name: "description", content: "Recent outdoor events, readiness status and quick actions in SafeStage." },
      { property: "og:title", content: "Dashboard — SafeStage" },
      { property: "og:description", content: "Recent events, readiness status and quick actions." },
    ],
  }),
  component: Dashboard,
});

const QUICK = [
  { to: "/events/new", label: "Create event", icon: CalendarPlus },
  { to: "/analysis", label: "Analyze event", icon: Activity },
  { to: "/assistant", label: "AI assistant", icon: Sparkles },
  { to: "/heatmap", label: "Heat map", icon: Map },
  { to: "/simulate", label: "What-if simulation", icon: GitCompare },
] as const;

function Dashboard() {
  const { data, isPending, isError, error, refetch } = useEventsQuery();
  const events = [...(data ?? [])].sort((a, b) =>
    (b.created_at ?? b.start_datetime ?? "").localeCompare(a.created_at ?? a.start_datetime ?? ""),
  );

  return (
    <AppShell>
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Dashboard</h1>
          <p className="text-sm text-muted-foreground">Plan safer. Decide smarter.</p>
        </div>
        <Button asChild>
          <Link to="/events/new">
            <CalendarPlus className="size-4" /> New event
          </Link>
        </Button>
      </div>

      <div className="mt-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
        {QUICK.map((q) => (
          <Link
            key={q.to}
            to={q.to}
            className="flex items-center gap-3 rounded-xl border border-border bg-card p-4 shadow-soft transition-colors hover:bg-accent"
          >
            <span className="grid size-9 place-items-center rounded-lg bg-accent text-accent-foreground">
              <q.icon className="size-4" />
            </span>
            <span className="text-sm font-medium">{q.label}</span>
          </Link>
        ))}
      </div>

      <Card className="mt-8 shadow-soft">
        <CardHeader>
          <CardTitle className="text-base">Recent events</CardTitle>
        </CardHeader>
        <CardContent>
          {isPending ? (
            <LoadingState label="Loading events…" />
          ) : isError ? (
            <ErrorState error={error} onRetry={() => void refetch()} />
          ) : events.length === 0 ? (
            <EmptyState
              title="No events yet"
              description="Create your first outdoor event to run a climate readiness analysis."
              action={
                <Button asChild size="sm">
                  <Link to="/events/new">Create event</Link>
                </Button>
              }
            />
          ) : (
            <ul className="divide-y divide-border">
              {events.map((ev) => (
                <li key={ev.id} className="flex flex-wrap items-center gap-3 py-4">
                  <div className="min-w-0 flex-1">
                    <p className="truncate font-medium">{ev.name}</p>
                    <p className="truncate text-xs text-muted-foreground">
                      {ev.event_type} · {ev.venue_name} · {ev.attendance.toLocaleString()} attendees
                    </p>
                    <p className="truncate text-xs text-muted-foreground">
                      {new Date(ev.start_datetime).toLocaleString()} → {new Date(ev.end_datetime).toLocaleString()}
                    </p>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <Button asChild size="sm" onClick={() => setStoredEventId(ev.id)}>
                      <Link to="/analysis" search={{ event_id: ev.id }}>
                        Analyze
                      </Link>
                    </Button>
                    <Button asChild size="sm" variant="outline" onClick={() => setStoredEventId(ev.id)}>
                      <Link to="/heatmap" search={{ event_id: ev.id }}>
                        Heat map
                      </Link>
                    </Button>
                    <Button asChild size="sm" variant="outline" onClick={() => setStoredEventId(ev.id)}>
                      <Link to="/assistant" search={{ event_id: ev.id }}>
                        Assistant
                      </Link>
                    </Button>
                  </div>
                </li>
              ))}
            </ul>
          )}
          <p className="mt-4 text-xs text-muted-foreground">
            Readiness score and heat-risk status are shown on the Analysis page once the backend returns
            an analysis for an event.
          </p>
        </CardContent>
      </Card>
    </AppShell>
  );
}
