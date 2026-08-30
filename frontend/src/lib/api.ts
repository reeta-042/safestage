/**
 * Centralized SafeStage API client.
 * Base URL is configurable via VITE_API_BASE_URL (defaults to http://localhost:8000).
 * Endpoint names, request fields and response fields mirror the FastAPI backend exactly.
 */

export const API_BASE_URL: string =
  (import.meta.env['VITE_API_BASE_URL'] as string | undefined)?.replace(/\/$/, "") ??
  "http://localhost:8000";

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_BASE_URL}${path}`, {
      ...init,
      headers: {
        "Content-Type": "application/json",
        ...(init?.headers ?? {}),
      },
    });
  } catch {
    throw new ApiError(
      `Cannot reach the SafeStage backend at ${API_BASE_URL}. Check that it is running and reachable.`,
      0,
    );
  }
  if (!res.ok) {
    let detail = `${res.status} ${res.statusText}`;
    try {
      const body = (await res.json()) as { detail?: unknown };
      if (body?.detail) detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
    } catch {
      /* ignore body parse errors */
    }
    throw new ApiError(detail, res.status);
  }
  return (await res.json()) as T;
}

/* ---------------- Types (mirror backend field names) ---------------- */

export interface EventCreate {
  name: string;
  event_type: string;
  venue_name: string;
  address: string;
  latitude: number;
  longitude: number;
  attendance: number;
  start_datetime: string;
  end_datetime: string;
  user_id: string | null;
}

export interface EventRecord {
  id: string;
  user_id: string | null;
  name: string;
  event_type: string;
  venue_name: string;
  address: string;
  latitude: number;
  longitude: number;
  attendance: number;
  start_datetime: string;
  end_datetime: string;
  created_at?: string;
  updated_at?: string;
}

export interface HeatRiskZone {
  zone_id: string;
  name: string;
  risk_level: string;
  avg_temp_c: number;
  coordinates?: unknown;
  advice: string;
}

export interface AnalyzeResponse {
  event_id: string;
  supported: boolean;
  message?: string | null;
  provider?: string | null;
  readiness_score?: number | null;
  readiness_score_label?: string | null;
  heat_risk_summary?: unknown;
  temperature_summary?: unknown;
  smart_date_recommendations?: unknown;
  best_date_option?: unknown;
  venue_layout_recommendations?: unknown;
  heat_risk_zones?: HeatRiskZone[] | null;
  recommendations?: unknown;
  ai_explanation?: string | null;
  analyzed_at?: string | null;
}

export interface ScenarioResult {
  name: string;
  readiness_score?: number | null;
  heat_risk_level?: string | null;
  avg_temp_c?: number | null;
  max_temp_c?: number | null;
  peak_heat_exposure_hours?: number | null;
  risk_factors?: unknown;
  mitigations?: unknown;
}

export interface ChatMessage {
  role: "user" | "assistant" | "system";
  content: string;
}

export interface SimulateResponse {
  event_id: string;
  supported: boolean;
  message?: string | null;
  scenario_a?: ScenarioResult | null;
  scenario_b?: ScenarioResult | null;
  recommended?: string | null;
  score_difference?: number | null;
  reason?: string | null;
  tactical_action_plan?: unknown;
  ai_simulation_insights?: unknown;
}

export interface HeatmapResponse {
  supported: boolean;
  message?: string | null;
  event_id?: string | null;
  latitude?: number | null;
  longitude?: number | null;
  timestamp?: string | null;
  provider?: string | null;
  geojson?: unknown;
  zones?: HeatRiskZone[] | null;
}

export interface ChatResponse {
  event_id: string;
  reply: string;
  context_used?: Record<string, unknown>;
}

/* ---------------- Endpoints ---------------- */

export const api = {
  health: () => request<unknown>("/health"),

  listEvents: () => request<EventRecord[]>("/events"),

  getEvent: (eventId: string) => request<EventRecord>(`/events/${eventId}`),

  createEvent: (payload: EventCreate) =>
    request<EventRecord>("/events", { method: "POST", body: JSON.stringify(payload) }),

  analyze: (event_id: string) =>
    request<AnalyzeResponse>("/analyze", { method: "POST", body: JSON.stringify({ event_id }) }),

  simulate: (payload: {
    event_id: string;
    scenario_a: string;
    scenario_b: string;
    history: ChatMessage[];
  }) => request<SimulateResponse>("/simulate", { method: "POST", body: JSON.stringify(payload) }),

  heatmap: (params: { event_id?: string; latitude?: number; longitude?: number; timestamp?: string }) => {
    const qs = new URLSearchParams();
    if (params.event_id) qs.set("event_id", params.event_id);
    if (params.latitude !== undefined) qs.set("latitude", String(params.latitude));
    if (params.longitude !== undefined) qs.set("longitude", String(params.longitude));
    if (params.timestamp) qs.set("timestamp", params.timestamp);
    return request<HeatmapResponse>(`/heatmap?${qs.toString()}`);
  },

  chat: (payload: { event_id: string; message: string; history: ChatMessage[] }) =>
    request<ChatResponse>("/chat", { method: "POST", body: JSON.stringify(payload) }),

  reportUrl: (event_id: string) => `${API_BASE_URL}/report?event_id=${encodeURIComponent(event_id)}`,

  downloadReport: async (event_id: string) => {
    const res = await fetch(api.reportUrl(event_id));
    if (!res.ok) throw new ApiError(`Report failed: ${res.status} ${res.statusText}`, res.status);
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `safestage-readiness-${event_id}.pdf`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  },
};
