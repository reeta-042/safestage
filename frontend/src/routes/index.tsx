import { createFileRoute, Link } from "@tanstack/react-router";
import { ShieldCheck, Thermometer, Map, Sparkles, GitCompare, FileText } from "lucide-react";
import { Logo } from "@/components/AppShell";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "SafeStage — Plan safer. Decide smarter." },
      {
        name: "description",
        content:
          "AI-powered climate-safety planning for outdoor events: readiness scores, heat risk maps, what-if simulations and readiness reports.",
      },
      { property: "og:title", content: "SafeStage — Plan safer. Decide smarter." },
      {
        property: "og:description",
        content: "AI-powered climate-safety planning for outdoor events.",
      },
    ],
  }),
  component: Landing,
});

const FEATURES = [
  { icon: ShieldCheck, title: "Readiness score", text: "A single, explainable score for how safe your event date and venue are." },
  { icon: Thermometer, title: "Heat risk insight", text: "Temperature summaries and peak-exposure windows for your schedule." },
  { icon: Map, title: "Heat map zones", text: "Venue heat-risk zones with practical, zone-level advice." },
  { icon: Sparkles, title: "AI planning assistant", text: "Ask questions about your event and get grounded guidance." },
  { icon: GitCompare, title: "What-if simulation", text: "Compare two scenarios side-by-side before you commit." },
  { icon: FileText, title: "Readiness report", text: "Download a shareable climate readiness PDF for stakeholders." },
];

function Landing() {
  return (
    <div className="min-h-screen bg-background">
      <header className="mx-auto flex max-w-6xl items-center justify-between px-4 py-5 sm:px-6">
        <Logo />
        <Button asChild size="sm">
          <Link to="/dashboard">Open dashboard</Link>
        </Button>
      </header>

      <section className="mx-auto max-w-6xl px-4 pb-16 pt-10 text-center sm:px-6 sm:pt-20">
        <span className="inline-flex rounded-full border border-border bg-accent px-3 py-1 text-xs font-medium text-accent-foreground">
          AI-powered climate safety for outdoor events
        </span>
        <h1 className="mx-auto mt-6 max-w-3xl text-4xl font-semibold tracking-tight sm:text-6xl">
          SafeStage
        </h1>
        <p className="mt-4 text-xl font-medium text-primary">Plan safer. Decide smarter.</p>
        <p className="mx-auto mt-4 max-w-2xl text-base text-muted-foreground">
          Score your event's climate readiness, map heat risk across your venue, simulate alternative
          plans and export a report your team can act on.
        </p>
        <div className="mt-8 flex flex-wrap justify-center gap-3">
          <Button asChild size="lg">
            <Link to="/events/new">Create an event</Link>
          </Button>
          <Button asChild size="lg" variant="outline">
            <Link to="/dashboard">View dashboard</Link>
          </Button>
        </div>
      </section>

      <section className="mx-auto max-w-6xl px-4 pb-24 sm:px-6">
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {FEATURES.map((f) => (
            <Card key={f.title} className="shadow-soft">
              <CardContent className="p-6">
                <span className="grid size-10 place-items-center rounded-xl bg-accent text-accent-foreground">
                  <f.icon className="size-5" />
                </span>
                <h2 className="mt-4 text-base font-semibold">{f.title}</h2>
                <p className="mt-1 text-sm text-muted-foreground">{f.text}</p>
              </CardContent>
            </Card>
          ))}
        </div>
      </section>

      <footer className="border-t border-border py-6 text-center text-xs text-muted-foreground">
        SafeStage — Plan safer. Decide smarter.
      </footer>
    </div>
  );
}
