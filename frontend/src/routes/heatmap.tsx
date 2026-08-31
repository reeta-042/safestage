import { useEffect, useMemo, useState } from "react";
import { createFileRoute, useSearch } from "@tanstack/react-router";
import { useMutation } from "@tanstack/react-query";
import { Copy, Flame, Map as MapIcon, MapPinned, Printer, Thermometer, TrendingUp } from "lucide-react";
import { AppShell } from "@/components/AppShell";
import { EventSelect } from "@/components/EventSelect";
import { RiskBadge } from "@/components/RiskBadge";
import { EmptyState, ErrorState, LoadingState, UnsupportedNotice } from "@/components/states";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { api, type HeatmapResponse, type HeatRiskZone } from "@/lib/api";
import { useSelectedEvent } from "@/lib/useSelectedEvent";

function cToF(value: number) {
  return (value * 9) / 5 + 32;
}

function riskColor(level: string) {
  switch ((level || "Low").toLowerCase()) {
    case "extreme":
      return { fill: "rgba(239, 68, 68, 0.52)", stroke: "#ef4444" };
    case "high":
      return { fill: "rgba(249, 115, 22, 0.5)", stroke: "#f97316" };
    case "moderate":
      return { fill: "rgba(250, 204, 21, 0.48)", stroke: "#facc15" };
    default:
      return { fill: "rgba(34, 197, 94, 0.42)", stroke: "#22c55e" };
  }
}

function toPolygonPoints(geometry: unknown): string {
  if (!geometry || typeof geometry !== "object" || !("coordinates" in geometry)) return "";
  const coordinates = (geometry as { coordinates?: unknown }).coordinates;
  if (!Array.isArray(coordinates)) return "";
  const ring = Array.isArray(coordinates[0]) ? coordinates[0] : coordinates;
  if (!Array.isArray(ring)) return "";

  const points = ring
    .filter((pair): pair is number[] => Array.isArray(pair) && pair.length >= 2)
    .map(([lon, lat]) => [((lon + 180) / 360) * 1000, ((90 - lat) / 180) * 1000] as const)
    .map(([x, y]) => `${x},${y}`)
    .join(" ");

  return points;
}

function normalizeZones(data: HeatmapResponse | undefined): HeatRiskZone[] {
  const fromApi = Array.isArray(data?.zones) ? data.zones : [];
  if (fromApi.length) return fromApi;

  const geojson = data?.geojson as { features?: Array<{ properties?: Record<string, unknown>; geometry?: { coordinates?: unknown } }> } | undefined;
  const features = geojson?.features ?? [];

  return features.flatMap((feature, index) => {
    const props = feature?.properties ?? {};
    const geometry = feature?.geometry;
    const temp = Number(
      props.average_temperature ??
      props.avg_temperature ??
      props.temperature_c ??
      props.temp_c ??
      props.temp ??
      props.value ??
      34,
    );

    const zone: HeatRiskZone = {
      zone_id: String(props.zone_id ?? `zone-${index + 1}`),
      name: String(props.name ?? props.zone_name ?? `Sector ${index + 1}`),
      risk_level: temp >= 38 ? "Extreme" : temp >= 34 ? "High" : temp >= 30 ? "Moderate" : "Low",
      avg_temp_c: Number.isFinite(temp) ? temp : 34,
      advice: String(props.advice ?? "Monitor and add shade, hydration, and crowd-flow controls."),
      coordinates: geometry?.coordinates,
    };

    return [zone];
  });
}

export const Route = createFileRoute("/heatmap")({
  validateSearch: (search: Record<string, unknown>) => ({
    event_id: typeof search["event_id"] === "string" ? (search["event_id"] as string) : undefined,
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
  const [unit, setUnit] = useState<"C" | "F">("C");
  const [overlayEnabled, setOverlayEnabled] = useState(true);
  const [gridEnabled, setGridEnabled] = useState(true);
  const [activeZoneId, setActiveZoneId] = useState<string | null>(null);

  useEffect(() => {
    if (search.event_id && search.event_id !== eventId) select(search.event_id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [search.event_id]);

  const heatmap = useMutation<HeatmapResponse, unknown, Parameters<typeof api.heatmap>[0]>({
    mutationFn: api.heatmap,
  });

  const data = heatmap.data;
  const zones = useMemo(() => normalizeZones(data), [data]);
  const activeZone = zones.find((zone) => zone.zone_id === activeZoneId) ?? zones[0] ?? null;

  const stats = useMemo(() => {
    if (!zones.length) return null;

    const temps = zones.map((zone) => zone.avg_temp_c ?? 0);
    const peak = zones.reduce((max, zone) => (zone.avg_temp_c ?? 0) > (max.avg_temp_c ?? 0) ? zone : max, zones[0]);
    const avg = temps.reduce((sum, value) => sum + value, 0) / temps.length;
    const highRisk = zones.filter((zone) => (zone.risk_level ?? "Low").toLowerCase() !== "low").length;
    const spread = Math.max(...temps) - Math.min(...temps);

    return {
      peak,
      average: avg,
      highRisk,
      spread,
    };
  }, [zones]);

  const shareSummary = async () => {
    if (!data) return;
    const text = [
      "SafeStage Heat Risk Summary",
      `Latitude: ${data.latitude ?? "—"}`,
      `Longitude: ${data.longitude ?? "—"}`,
      `Provider: ${data.provider ?? "—"}`,
      ...zones.map((zone) => `${zone.name}: ${zone.risk_level} (${zone.avg_temp_c}°${unit})`),
    ].join("\n");

    try {
      await navigator.clipboard.writeText(text);
      window.alert("Heat risk summary copied to clipboard.");
    } catch {
      window.alert("Copy failed in this browser. You can still print the page for stakeholders.");
    }
  };

  return (
    <AppShell>
      <h1 className="text-2xl font-semibold tracking-tight">Hyperlocal heat map</h1>
      <p className="text-sm text-muted-foreground">
        Explore thermal risk across the venue with sector overlays, operational advice, and shareable stakeholder summaries.
      </p>

      <Tabs defaultValue="event" className="mt-6">
        <TabsList>
          <TabsTrigger value="event">By event</TabsTrigger>
          <TabsTrigger value="coords">By coordinates</TabsTrigger>
        </TabsList>

        <TabsContent value="event" className="mt-4 space-y-4">
          <EventSelect value={activeId} onChange={select} />
          <Button
            onClick={() => activeId && heatmap.mutate(timestamp ? { event_id: activeId, timestamp } : { event_id: activeId })}
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
          <LoadingState label="Loading thermal overlay…" />
        ) : heatmap.isError ? (
          <ErrorState error={heatmap.error} />
        ) : !data ? (
          <EmptyState title="No heat map loaded" description="Load a heat map to inspect thermal conditions for the venue." />
        ) : !data.supported ? (
          <UnsupportedNotice message={data.message} />
        ) : (
          <Card className="shadow-soft">
            <CardHeader className="pb-3">
              <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
                <CardTitle className="text-base">Thermal overlay</CardTitle>
                <div className="flex flex-wrap gap-2 text-xs">
                  <Button variant={overlayEnabled ? "default" : "outline"} size="sm" onClick={() => setOverlayEnabled((v) => !v)}>
                    Thermal Overlay
                  </Button>
                  <Button variant={gridEnabled ? "default" : "outline"} size="sm" onClick={() => setGridEnabled((v) => !v)}>
                    Tile Grids
                  </Button>
                  <Button variant="outline" size="sm" onClick={() => setUnit((v) => (v === "C" ? "F" : "C"))}>
                    {unit === "C" ? "°C" : "°F"}
                  </Button>
                  <Button variant="outline" size="sm" onClick={shareSummary}>
                    <Copy className="size-3.5" /> Export & Share
                  </Button>
                  <Button variant="outline" size="sm" onClick={() => window.print()}>
                    <Printer className="size-3.5" /> Print
                  </Button>
                </div>
              </div>
            </CardHeader>
            <CardContent className="space-y-5">
              <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                <div className="rounded-xl border bg-muted/30 p-3">
                  <div className="flex items-center gap-2 text-xs text-muted-foreground"><Flame className="size-3.5" /> Peak thermal sector</div>
                  <div className="mt-2 text-lg font-semibold">{stats?.peak?.name ?? "—"}</div>
                  <div className="text-sm text-muted-foreground">{stats ? `${stats.peak.avg_temp_c ?? 0}°${unit}` : "—"}</div>
                </div>
                <div className="rounded-xl border bg-muted/30 p-3">
                  <div className="flex items-center gap-2 text-xs text-muted-foreground"><Thermometer className="size-3.5" /> Average temp</div>
                  <div className="mt-2 text-lg font-semibold">{stats ? `${(unit === "C" ? stats.average : cToF(stats.average)).toFixed(1)}°${unit}` : "—"}</div>
                </div>
                <div className="rounded-xl border bg-muted/30 p-3">
                  <div className="flex items-center gap-2 text-xs text-muted-foreground"><TrendingUp className="size-3.5" /> High risk zones</div>
                  <div className="mt-2 text-lg font-semibold">{stats?.highRisk ?? 0}</div>
                </div>
                <div className="rounded-xl border bg-muted/30 p-3">
                  <div className="flex items-center gap-2 text-xs text-muted-foreground"><MapPinned className="size-3.5" /> Thermal spread</div>
                  <div className="mt-2 text-lg font-semibold">{stats ? `${(unit === "C" ? stats.spread : cToF(stats.spread)).toFixed(1)}°${unit}` : "—"}</div>
                </div>
              </div>

              <div className="grid gap-4 xl:grid-cols-[1.7fr_0.9fr]">
                <div className="overflow-hidden rounded-xl border bg-slate-950/5">
                  <svg viewBox="0 0 1000 1000" className="h-[430px] w-full bg-[radial-gradient(circle_at_center,_rgba(14,165,233,0.13),_transparent_60%)]">
                    {gridEnabled && Array.from({ length: 10 }).map((_, idx) => (
                      <g key={`grid-${idx}`}>
                        <line x1={idx * 100} y1={0} x2={idx * 100} y2={1000} stroke="rgba(148,163,184,0.2)" strokeWidth="1" />
                        <line x1={0} y1={idx * 100} x2={1000} y2={idx * 100} stroke="rgba(148,163,184,0.2)" strokeWidth="1" />
                      </g>
                    ))}

                    {overlayEnabled && zones.map((zone) => {
                      const points = toPolygonPoints(zone.coordinates as unknown);
                      if (!points) return null;
                      const color = riskColor(zone.risk_level ?? "Low");
                      const isActive = activeZone?.zone_id === zone.zone_id;
                      return (
                        <polygon
                          key={zone.zone_id}
                          points={points}
                          fill={color.fill}
                          stroke={color.stroke}
                          strokeWidth={isActive ? 4 : 2}
                          opacity={isActive ? 1 : 0.8}
                          onMouseEnter={() => setActiveZoneId(zone.zone_id)}
                          onClick={() => setActiveZoneId(zone.zone_id)}
                          className="cursor-pointer transition-all"
                        />
                      );
                    })}

                    <circle cx={500} cy={500} r={16} fill="#8b5cf6" opacity={0.9} />
                    <circle cx={500} cy={500} r={34} fill="transparent" stroke="#8b5cf6" strokeOpacity={0.5} strokeWidth={2} />
                    <text x={520} y={485} fill="#7c3aed" fontSize="18" fontWeight="700">Venue pin</text>
                  </svg>
                </div>

                <div className="space-y-3">
                  <div className="rounded-xl border bg-muted/30 p-4">
                    <div className="text-xs uppercase tracking-wide text-muted-foreground">Focused sector</div>
                    <div className="mt-2 text-xl font-semibold">{activeZone?.name ?? "No sector selected"}</div>
                    <div className="mt-2 flex items-center gap-2">
                      <RiskBadge level={activeZone?.risk_level ?? "Low"} />
                    </div>
                    <div className="mt-3 text-sm text-muted-foreground">
                      {activeZone ? `${(unit === "C" ? activeZone.avg_temp_c : cToF(activeZone.avg_temp_c)).toFixed(1)}°${unit}` : "—"}
                    </div>
                    <p className="mt-3 text-sm">{activeZone?.advice ?? "No operational guidance available."}</p>
                  </div>

                  <div className="rounded-xl border bg-muted/30 p-4">
                    <div className="text-xs uppercase tracking-wide text-muted-foreground">Legend</div>
                    <div className="mt-3 space-y-2 text-sm">
                      {[
                        { label: "Extreme", color: riskColor("Extreme").fill },
                        { label: "High", color: riskColor("High").fill },
                        { label: "Moderate", color: riskColor("Moderate").fill },
                        { label: "Low", color: riskColor("Low").fill },
                      ].map((entry) => (
                        <div key={entry.label} className="flex items-center gap-2">
                          <span className="h-3 w-6 rounded-sm" style={{ backgroundColor: entry.color }} />
                          <span>{entry.label}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </div>

              <Tabs defaultValue="zones" className="mt-4">
                <TabsList>
                  <TabsTrigger value="zones">Zone breakdown</TabsTrigger>
                  <TabsTrigger value="raw">Raw GeoJSON</TabsTrigger>
                </TabsList>

                <TabsContent value="zones" className="mt-4">
                  <div className="overflow-x-auto rounded-xl border">
                    <table className="min-w-full text-left text-sm">
                      <thead className="bg-muted/40">
                        <tr>
                          <th className="px-3 py-2">Zone</th>
                          <th className="px-3 py-2">Risk</th>
                          <th className="px-3 py-2">Temp</th>
                          <th className="px-3 py-2">Action</th>
                        </tr>
                      </thead>
                      <tbody>
                        {zones.map((zone) => (
                          <tr key={zone.zone_id} className="border-t">
                            <td className="px-3 py-2 font-medium">{zone.name}</td>
                            <td className="px-3 py-2"><RiskBadge level={zone.risk_level ?? "Low"} /></td>
                            <td className="px-3 py-2">{(unit === "C" ? zone.avg_temp_c : cToF(zone.avg_temp_c)).toFixed(1)}°{unit}</td>
                            <td className="px-3 py-2 text-muted-foreground">{zone.advice}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </TabsContent>

                <TabsContent value="raw" className="mt-4">
                  <pre className="max-h-[300px] overflow-auto rounded-xl border bg-muted/20 p-3 text-xs">{JSON.stringify(data.geojson ?? {}, null, 2)}</pre>
                </TabsContent>
              </Tabs>
            </CardContent>
          </Card>
        )}
      </div>
    </AppShell>
  );
}

export default HeatmapPage;
