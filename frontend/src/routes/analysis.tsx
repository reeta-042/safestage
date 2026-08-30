import { useEffect, useState } from "react";
import { createFileRoute, useSearch } from "@tanstack/react-router";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Download, Play } from "lucide-react";
import { toast } from "sonner";
import { AppShell } from "@/components/AppShell";
import { EventSelect } from "@/components/EventSelect";
import { DataCard, DataValue, isEmptyValue } from "@/components/DataView";
import { ReadinessScore, RiskBadge } from "@/components/RiskBadge";
import { EmptyState, ErrorState, LoadingState, UnsupportedNotice } from "@/components/states";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { api, type AnalyzeResponse } from "@/lib/api";
import { useSelectedEvent } from "@/lib/useSelectedEvent";

export const Route = createFileRoute("/analysis")({
  validateSearch: (search: Record<string, unknown>) => ({
    event_id: typeof search['event_id'] === "string" ? (search['event_id'] as string) : undefined,
  }),
  head: () => ({
    meta: [
      { title: "Event Analysis — SafeStage" },
      { name: "description", content: "Climate readiness score, heat risk, smart dates and AI explanation for your event." },
      { property: "og:title", content: "Event Analysis — SafeStage" },
      { property: "og:description", content: "Readiness score, heat risk and AI guidance for your outdoor event." },
    ],
  }),
  component: AnalysisPage,
});

function AnalysisPage() {
  const search = useSearch({ from: "/analysis" });
  const { eventId, select } = useSelectedEvent();
  const [downloading, setDownloading] = useState(false);
  const activeId = search.event_id ?? eventId;

  useEffect(() => {
    if (search.event_id && search.event_id !== eventId) select(search.event_id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [search.event_id]);

  const eventQuery = useQuery({
    queryKey: ["event", activeId],
    queryFn: () => api.getEvent(activeId),
    enabled: Boolean(activeId),
    retry: false,
  });

  const analysis = useMutation<AnalyzeResponse, unknown, string>({
    mutationFn: (id: string) => api.analyze(id),
  });

  const data = analysis.data;

  const download = async () => {
    if (!activeId) return;
    setDownloading(true);
    try {
      await api.downloadReport(activeId);
      toast.success("Report downloaded");
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Report download failed");
    } finally {
      setDownloading(false);
    }
  };

  return (
    <AppShell>
      <h1 className="text-2xl font-semibold tracking-tight">Event analysis</h1>
      <p className="text-sm text-muted-foreground">
        Runs <code>POST /analyze</code> for the selected event.
      </p>

      <div className="mt-6 flex flex-wrap items-end gap-4">
        <EventSelect value={activeId} onChange={select} />
        <Button onClick={() => activeId && analysis.mutate(activeId)} disabled={!activeId || analysis.isPending}>
          <Play className="size-4" />
          {analysis.isPending ? "Analyzing…" : "Run analysis"}
        </Button>
        <Button variant="outline" onClick={() => void download()} disabled={!activeId || downloading}>
          <Download className="size-4" />
          {downloading ? "Preparing…" : "Download Climate Readiness Report"}
        </Button>
      </div>

      {eventQuery.data ? (
        <Card className="mt-6 shadow-soft">
          <CardContent className="grid gap-2 p-5 text-sm sm:grid-cols-2">
            <p className="font-medium">{eventQuery.data.name}</p>
            <p className="text-muted-foreground">{eventQuery.data.event_type}</p>
            <p className="text-muted-foreground">
              {eventQuery.data.venue_name} — {eventQuery.data.address}
            </p>
            <p className="text-muted-foreground">
              {new Date(eventQuery.data.start_datetime).toLocaleString()} →{" "}
              {new Date(eventQuery.data.end_datetime).toLocaleString()}
            </p>
          </CardContent>
        </Card>
      ) : null}

      <div className="mt-6 space-y-4">
        {!activeId ? (
          <EmptyState title="Select an event" description="Choose an event above to run a climate readiness analysis." />
        ) : analysis.isPending ? (
          <LoadingState label="Analyzing event climate readiness…" />
        ) : analysis.isError ? (
          <ErrorState error={analysis.error} onRetry={() => analysis.mutate(activeId)} />
        ) : !data ? (
          <EmptyState title="No analysis yet" description="Run the analysis to see backend results. Nothing is shown until the backend responds." />
        ) : !data.supported ? (
          <UnsupportedNotice message={data.message} />
        ) : (
          <AnalysisResult data={data} />
        )}
      </div>
    </AppShell>
  );
}

function AnalysisResult({ data }: { data: AnalyzeResponse }) {
  return (
    <div className="space-y-4">
      <Card className="shadow-soft">
        <CardContent className="flex flex-wrap items-center justify-between gap-6 p-6">
          <ReadinessScore score={data.readiness_score ?? null} label={data.readiness_score_label ?? null} />
          <div className="text-right text-xs text-muted-foreground">
            {data.provider ? <p>Provider: {data.provider}</p> : null}
            {data.analyzed_at ? <p>Analyzed {new Date(data.analyzed_at).toLocaleString()}</p> : null}
          </div>
        </CardContent>
      </Card>

      {data.message ? (
        <Card className="shadow-soft">
          <CardContent className="p-5 text-sm text-muted-foreground">{data.message}</CardContent>
        </Card>
      ) : null}

      <div className="grid gap-4 lg:grid-cols-2">
        <DataCard title="Heat risk summary" value={data.heat_risk_summary} />
        <DataCard title="Temperature summary" value={data.temperature_summary} />
        <DataCard title="Smart date recommendations" value={data.smart_date_recommendations} />
        <DataCard title="Best date option" value={data.best_date_option} />
        <DataCard title="Venue layout recommendations" value={data.venue_layout_recommendations} />
        <DataCard title="Recommendations" value={data.recommendations} />
      </div>

      <Card className="shadow-soft">
        <CardHeader className="pb-3">
          <CardTitle className="text-base">Heat risk zones</CardTitle>
        </CardHeader>
        <CardContent>
          {isEmptyValue(data.heat_risk_zones) ? (
            <p className="text-sm text-muted-foreground">No zones returned for this event.</p>
          ) : (
            <ul className="grid gap-3 md:grid-cols-2">
              {(data.heat_risk_zones ?? []).map((zone) => (
                <li key={zone.zone_id} className="rounded-xl border border-border p-4">
                  <div className="flex items-center justify-between gap-2">
                    <p className="font-medium">{zone.name}</p>
                    <RiskBadge level={zone.risk_level} />
                  </div>
                  <p className="mt-1 text-xs text-muted-foreground">Avg temp: {zone.avg_temp_c}°C</p>
                  <p className="mt-2 text-sm">{zone.advice}</p>
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>

      <DataCard title="AI explanation">
        <DataValue value={data.ai_explanation} />
      </DataCard>
    </div>
  );
}
