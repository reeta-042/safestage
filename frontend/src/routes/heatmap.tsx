import { useEffect, useState } from "react";
import { createFileRoute, useSearch } from "@tanstack/react-router";
import { useMutation } from "@tanstack/react-query";
import { Map as MapIcon } from "lucide-react";
import { AppShell } from "@/components/AppShell";
import { EventSelect } from "@/components/EventSelect";
import { RiskBadge } from "@/components/RiskBadge";
import { EmptyState, ErrorState, LoadingState, UnsupportedNotice } from "@/components/states";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { api, type HeatmapResponse } from "@/lib/api";
import { useSelectedEvent } from "@/lib/useSelectedEvent";

function getPolygonPoints(geojson: unknown): Array<{ points: string; avgTemp: number; risk: string }> {
  if (!geojson || typeof geojson !== "object" || !("features" in geojson)) return [];

  const features = (geojson as { features?: Array<{ geometry?: { coordinates?: unknown[] }; properties?: Record<string, unknown> }> }).features ?? [];

  return features.flatMap((feature, index) => {
    if (!feature?.geometry || typeof feature.geometry !== "object") return [];

    const rawCoords = feature.geometry.coordinates as unknown[] | undefined;
    if (!rawCoords || !rawCoords.length) return [];

    const coords = Array.isArray(rawCoords[0]) ? rawCoords[0] : rawCoords;
    const points = coords
      .filter((pair): pair is number[] => Array.isArray(pair) && pair.length >= 2)
      .map(([lon, lat]) => `${((lon + 180) / 360) * 1000},${((90 - lat) / 180) * 1000}`)
      .join(" ");

    if (!points) return [];

    const avgTemp = Number(
      feature.properties?.average_temperature ??
      feature.properties?.avg_temperature ??
      feature.properties?.temperature_c ??
      34
    );

    return [{
      points,
      avgTemp: Number.isFinite(avgTemp) ? avgTemp : 34,
      risk: avgTemp >= 38 ? "High" : avgTemp >= 34 ? "Moderate" : "Low",
    }];
  });
}

export const Route = createFileRoute("/heatmap")({
  validateSearch: (search: Record<string, unknown>) => ({
    event_id: typeof search['event_id'] === "string" ? (search['event_id'] as string) : undefined,
  }),
  head: () => ({
    meta: [
      { title: "Heat Map — SafeStage" },
      { name: "description", content: "Heat-risk zones and GeoJSON returned by the SafeStage heat map service." },
      { property: "og:title", content: "Heat Map — SafeStage" },
      { property: "og:description", content: "Explore heat-risk zones for your event venue." },
    ],
  }),
  component: HeatmapPage,
});

function HeatmapPage() {
  const search = useSearch({ from: "/heatmap" });
  const { eventId, select } = useSelectedEvent();
  const activeId = search.event_id ?? eventId;
  const [latitude, setLatitude] = useState("");
  const [longitude, setLongitude] = useState("");
  const [timestamp, setTimestamp] = useState("");

  useEffect(() => {
    if (search.event_id && search.event_id !== eventId) select(search.event_id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [search.event_id]);

  const heatmap = useMutation<HeatmapResponse, unknown, Parameters<typeof api.heatmap>[0]>({
    mutationFn: api.heatmap,
  });
  const data = heatmap.data;

  return (
    <AppShell>
      <h1 className="text-2xl font-semibold tracking-tight">Heat map</h1>
      <p className="text-sm text-muted-foreground">
        Calls <code>GET /heatmap</code> with either an event ID or coordinates.
      </p>

      <Tabs defaultValue="event" className="mt-6">
        <TabsList>
          <TabsTrigger value="event">By event</TabsTrigger>
          <TabsTrigger value="coords">By coordinates</TabsTrigger>
        </TabsList>

        <TabsContent value="event" className="mt-4 space-y-4">
          <EventSelect value={activeId} onChange={select} />
          <Button
            onClick={() =>
              activeId &&
              heatmap.mutate(timestamp ? { event_id: activeId, timestamp } : { event_id: activeId })
            }
            disabled={!activeId || heatmap.isPending}
          >
            <MapIcon className="size-4" /> Load heat map
          </Button>
        </TabsContent>

        <TabsContent value="coords" className="mt-4 space-y-4">
          <div className="grid gap-4 sm:max-w-lg sm:grid-cols-2">
            <div className="grid gap-2">
              <Label htmlFor="lat">Latitude</Label>
              <Input id="lat" type="number" step="any" value={latitude} onChange={(e) => setLatitude(e.target.value)} />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="lon">Longitude</Label>
              <Input id="lon" type="number" step="any" value={longitude} onChange={(e) => setLongitude(e.target.value)} />
            </div>
          </div>
          <Button
            onClick={() =>
              heatmap.mutate(
                timestamp
                  ? { latitude: Number(latitude), longitude: Number(longitude), timestamp }
                  : { latitude: Number(latitude), longitude: Number(longitude) },
              )
            }
            disabled={latitude === "" || longitude === "" || heatmap.isPending}
          >
            <MapIcon className="size-4" /> Load heat map
          </Button>
        </TabsContent>
      </Tabs>

      <div className="mt-4 grid gap-2 sm:max-w-xs">
        <Label htmlFor="ts">Timestamp (optional)</Label>
        <Input id="ts" type="datetime-local" value={timestamp} onChange={(e) => setTimestamp(e.target.value)} />
      </div>

      <div className="mt-6 space-y-4">
        {heatmap.isPending ? (
          <LoadingState label="Loading heat-risk zones…" />
        ) : heatmap.isError ? (
          <ErrorState error={heatmap.error} />
        ) : !data ? (
          <EmptyState title="No heat map loaded" description="Load a heat map to see the zones returned by the backend." />
        ) : !data.supported ? (
          <UnsupportedNotice message={data.message} />
        ) : (
          <>
            <Card className="shadow-soft">
              <CardContent className="grid gap-1 p-5 text-sm text-muted-foreground sm:grid-cols-2">
                <p>Latitude: {data.latitude ?? "—"}</p>
                <p>Longitude: {data.longitude ?? "—"}</p>
                <p>Timestamp: {data.timestamp ?? "—"}</p>
                <p>Provider: {data.provider ?? "—"}</p>
              </CardContent>
            </Card>

            <Card className="shadow-soft">
              <CardHeader className="pb-3">
                <CardTitle className="text-base">Heat map preview</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="overflow-hidden rounded-xl border border-border bg-muted/40">
                  {(() => {
                    const polygons = getPolygonPoints(data.geojson);
                    if (!polygons.length) {
                      return (
                        <div className="flex min-h-52 items-center justify-center p-6 text-sm text-muted-foreground">
                          No spatial heatmap polygons were returned for this request.
                        </div>
                      );
                    }

                    return (
                      <svg viewBox="0 0 1000 1000" className="h-80 w-full bg-[radial-gradient(circle_at_center,_rgba(168,85,247,0.08),_transparent_60%)]">
                        <rect width="1000" height="1000" fill="transparent" />
                        {polygons.map((polygon, idx) => (
                          <polygon
                            key={`${polygon.points}-${idx}`}
                            points={polygon.points}
                            fill={polygon.avgTemp >= 38 ? "rgba(239,68,68,0.45)" : polygon.avgTemp >= 34 ? "rgba(251,191,36,0.45)" : "rgba(34,197,94,0.35)"}
                            stroke={polygon.avgTemp >= 38 ? "#ef4444" : polygon.avgTemp >= 34 ? "#f59e0b" : "#22c55e"}
                            strokeWidth="2"
                          />
                        ))}
                        <circle cx="500" cy="500" r="8" fill="#7c3aed" opacity="0.9" />
                      </svg>
                    );
                  })()}
                </div>
                <div className="grid gap-3 md:grid-cols-2">
                  {data.zones?.length ? data.zones.map((zone) => (
                    <div key={zone.zone_id} className="rounded-xl border border-border bg-card p-4">
                      <div className="flex items-center justify-between gap-2">
                        <p className="font-medium">{zone.name}</p>
                        <RiskBadge level={zone.risk_level} />
                      </div>
                      <p className="mt-2 text-sm text-muted-foreground">Avg temp: {zone.avg_temp_c}°C</p>
                      <p className="mt-2 text-sm">{zone.advice}</p>
                    </div>
                  )) : <p className="text-sm text-muted-foreground">The backend returned no zones.</p>}
                </div>
              </CardContent>
            </Card>

            <Card className="shadow-soft">
              <CardHeader className="pb-3">
                <CardTitle className="text-base">GeoJSON</CardTitle>
              </CardHeader>
              <CardContent>
                {data.geojson ? (
                  <pre className="max-h-96 overflow-auto rounded-lg bg-muted p-4 text-xs">
                    {JSON.stringify(data.geojson, null, 2)}
                  </pre>
                ) : (
                  <p className="text-sm text-muted-foreground">No GeoJSON returned.</p>
                )}
              </CardContent>
            </Card>
          </>
        )}
      </div>
    </AppShell>
  );
}
