import { useEffect, useState } from "react";
import { createFileRoute, useSearch } from "@tanstack/react-router";
import { useMutation } from "@tanstack/react-query";
import { GitCompare } from "lucide-react";
import { AppShell } from "@/components/AppShell";
import { EventSelect } from "@/components/EventSelect";
import { DataCard, DataValue } from "@/components/DataView";
import { RiskBadge } from "@/components/RiskBadge";
import { EmptyState, ErrorState, LoadingState, UnsupportedNotice } from "@/components/states";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { api, type ScenarioResult, type SimulateResponse } from "@/lib/api";
import { useSelectedEvent } from "@/lib/useSelectedEvent";

export const Route = createFileRoute("/simulate")({
  validateSearch: (search: Record<string, unknown>) => ({
    event_id: typeof search['event_id'] === "string" ? (search['event_id'] as string) : undefined,
  }),
  head: () => ({
    meta: [
      { title: "What-If Simulation — SafeStage" },
      { name: "description", content: "Compare two event scenarios side-by-side on readiness, heat risk and mitigations." },
      { property: "og:title", content: "What-If Simulation — SafeStage" },
      { property: "og:description", content: "Compare two plans before you commit." },
    ],
  }),
  component: SimulatePage,
});

function SimulatePage() {
  const search = useSearch({ from: "/simulate" });
  const { eventId, select } = useSelectedEvent();
  const activeId = search.event_id ?? eventId;
  const [scenarioA, setScenarioA] = useState("");
  const [scenarioB, setScenarioB] = useState("");

  useEffect(() => {
    if (search.event_id && search.event_id !== eventId) select(search.event_id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [search.event_id]);

  const sim = useMutation<SimulateResponse, unknown, void>({
    mutationFn: () =>
      api.simulate({ event_id: activeId, scenario_a: scenarioA, scenario_b: scenarioB, history: [] }),
  });
  const data = sim.data;

  return (
    <AppShell>
      <h1 className="text-2xl font-semibold tracking-tight">What-if simulation</h1>
      <p className="text-sm text-muted-foreground">
        Sends <code>POST /simulate</code> with two scenarios for the selected event.
      </p>

      <div className="mt-6 space-y-4">
        <EventSelect value={activeId} onChange={select} />
        <div className="grid gap-4 lg:grid-cols-2">
          <div className="grid gap-2">
            <Label htmlFor="a">Scenario A</Label>
            <Textarea id="a" rows={3} value={scenarioA} onChange={(e) => setScenarioA(e.target.value)} className="bg-card" />
          </div>
          <div className="grid gap-2">
            <Label htmlFor="b">Scenario B</Label>
            <Textarea id="b" rows={3} value={scenarioB} onChange={(e) => setScenarioB(e.target.value)} className="bg-card" />
          </div>
        </div>
        <Button
          onClick={() => sim.mutate()}
          disabled={!activeId || !scenarioA.trim() || !scenarioB.trim() || sim.isPending}
        >
          <GitCompare className="size-4" /> {sim.isPending ? "Simulating…" : "Run simulation"}
        </Button>
      </div>

      <div className="mt-6 space-y-4">
        {sim.isPending ? (
          <LoadingState label="Running scenario comparison…" />
        ) : sim.isError ? (
          <ErrorState error={sim.error} onRetry={() => sim.mutate()} />
        ) : !data ? (
          <EmptyState title="No simulation yet" description="Describe two scenarios and run the simulation." />
        ) : !data.supported ? (
          <UnsupportedNotice message={data.message} />
        ) : (
          <>
            <Card className="shadow-soft">
              <CardContent className="grid gap-2 p-5 text-sm sm:grid-cols-3">
                <div>
                  <p className="text-xs uppercase tracking-wide text-muted-foreground">Recommended</p>
                  <p className="font-medium">{data.recommended ?? "—"}</p>
                </div>
                <div>
                  <p className="text-xs uppercase tracking-wide text-muted-foreground">Score difference</p>
                  <p className="font-medium tabular-nums">{data.score_difference ?? "—"}</p>
                </div>
                <div className="sm:col-span-3">
                  <p className="text-xs uppercase tracking-wide text-muted-foreground">Reason</p>
                  <p>{data.reason ?? "—"}</p>
                </div>
              </CardContent>
            </Card>

            <div className="grid gap-4 lg:grid-cols-2">
              <ScenarioCard scenario={data.scenario_a} fallback="Scenario A" />
              <ScenarioCard scenario={data.scenario_b} fallback="Scenario B" />
            </div>

            <DataCard title="Tactical action plan" value={data.tactical_action_plan} />
            <DataCard title="AI simulation insights" value={data.ai_simulation_insights} />
          </>
        )}
      </div>
    </AppShell>
  );
}

function ScenarioCard({ scenario, fallback }: { scenario?: ScenarioResult | null | undefined; fallback: string }) {
  if (!scenario) {
    return (
      <Card className="shadow-soft">
        <CardHeader className="pb-3">
          <CardTitle className="text-base">{fallback}</CardTitle>
        </CardHeader>
        <CardContent className="text-sm text-muted-foreground">No result returned.</CardContent>
      </Card>
    );
  }
  return (
    <Card className="shadow-soft">
      <CardHeader className="flex-row items-center justify-between gap-2 pb-3">
        <CardTitle className="text-base">{scenario.name}</CardTitle>
        <RiskBadge level={scenario.heat_risk_level} />
      </CardHeader>
      <CardContent className="space-y-4 text-sm">
        <div className="grid grid-cols-2 gap-3">
          <Metric label="Readiness score" value={scenario.readiness_score} />
          <Metric label="Peak heat exposure (h)" value={scenario.peak_heat_exposure_hours} />
          <Metric label="Avg temp (°C)" value={scenario.avg_temp_c} />
          <Metric label="Max temp (°C)" value={scenario.max_temp_c} />
        </div>
        <div>
          <p className="mb-1 text-xs font-medium uppercase tracking-wide text-muted-foreground">Risk factors</p>
          <DataValue value={scenario.risk_factors} />
        </div>
        <div>
          <p className="mb-1 text-xs font-medium uppercase tracking-wide text-muted-foreground">Mitigations</p>
          <DataValue value={scenario.mitigations} />
        </div>
      </CardContent>
    </Card>
  );
}

function Metric({ label, value }: { label: string; value?: number | null | undefined }) {
  return (
    <div className="rounded-lg border border-border p-3">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="text-lg font-semibold tabular-nums">{value ?? "—"}</p>
    </div>
  );
}
