# SafeStage Backend — FortyGuard Hackathon '26

SafeStage is an AI-powered climate operations platform that transforms FortyGuard's hyperlocal temperature intelligence into actionable planning decisions for outdoor event organizers.

> **SafeStage solves a decision problem, not just a weather visualization problem.**

---

## 🚀 Key Features

1. **Smart Date & Time Recommendation**: Evaluates candidate dates/times (e.g. Friday vs Saturday 2 PM vs Saturday 5 PM) to recommend the thermally safest window.
2. **SafeStage Event Readiness Score**: A deterministic 0–100 decision score calculated from peak temperature, heat index, FortyGuard LTM WBGT, UHI intensity, and crowd density.
3. **Interactive Spatial Heat Map**: Returns map-compatible GeoJSON thermal micro-zones powered by FortyGuard's native map capabilities.
4. **Venue Layout Optimization**: Computes optimal placement for main stage, misting/cooling stations, medical tents, and hydration points based on FortyGuard LTM street view segmentation (canopy cover, albedo, pavement radiation).
5. **Scenario Simulation (`POST /simulate`)**: Accepts two natural-language scenario descriptions, sends both through the Gemini Flash scenario engine with event context and optional history, and returns a structured comparison with a tactical plan.
6. **Gemini AI Operations Copilot (`POST /chat`)**: Interactive AI planning assistant powered by Gemini Flash using the Google GenAI SDK (`google-genai`). Chat is displayed in the frontend and is not included in the PDF.
7. **Climate Readiness Report (`GET /report`)**: Downloadable executive PDF summary report powered by ReportLab.
8. **FortyGuard LTM Integration & Mock Mode**: Seamlessly switches between FortyGuard API (`CLIMATE_PROVIDER=fortyguard`) and offline development mock mode (`CLIMATE_PROVIDER=mock`).
9. **Location-Aware Availability**: Explicitly handles location coverage while providing FortyGuard native spatial map visualization.

---

## 📐 Architecture Overview

```text
                    SafeStage Frontend (React / Leaflet)
                                  │
                                  ▼
                            FastAPI Backend
                                  │
        ┌─────────────────────────┼─────────────────────────┐
        ▼                         ▼                         ▼
  Event Service            Gemini Flash Service     Map Provider Service
        │                    (Google GenAI SDK)      (FortyGuard Native Map)
        ▼                         │                         │
SQLite DB (safestage.db)          ▼                         ▼
                           Climate Service         FortyGuard LTM Endpoints
                                  │
                                  ▼
                        FortyGuard API Provider
                      (Mock Mode / Premium LTMs)
```

---

## 📁 Directory Structure

```text
backend/
├── app/
│   ├── main.py                   # FastAPI Application Entry & Health Check
│   ├── api/
│   │   └── routes/
│   │       ├── events.py          # POST /events, GET /events/{id}
│   │       ├── analyze.py         # POST /analyze (Core scoring engine with FortyGuard LTMs)
│   │       ├── heatmap.py         # GET /heatmap (FortyGuard native spatial GeoJSON grid)
│   │       ├── simulate.py        # POST /simulate (What-If engine)
│   │       ├── chat.py            # POST /chat (Gemini Flash copilot assistant)
│   │       └── report.py          # GET /report (PDF report generator)
│   ├── core/
│   │   └── config.py              # Pydantic environment configuration
│   ├── database/
│   │   ├── connection.py          # SQLite SQLAlchemy session & DB engine
│   │   ├── models.py              # Users, Events, HeatAnalysis, Recommendations, Reports
│   │   └── migrations/            # Alembic database migration scripts
│   ├── schemas/                   # Pydantic input/output validation models
│   ├── services/
│   │   ├── event_service.py       # Event CRUD operations
│   │   ├── climate_service.py     # Provider factory & normalization
│   │   ├── recommendation_service.py # Deterministic readiness score & date/layout engines
│   │   ├── simulation_service.py  # Deterministic scenario comparator
│   │   ├── ai_service.py          # Gemini Flash copilot and scenario engine
│   │   └── report_service.py      # PDF report generator
│   └── integrations/
│       ├── climate/
│       │   ├── base.py            # ClimateProvider Abstract Class
│       │   ├── mock.py            # Mock climate provider with LTM data
│       │   └── fortyguard.py      # FortyGuard API adapter (all 4 LTM endpoints)
│       └── maps/
│           ├── base.py            # BaseMapProvider Abstract Class
│           ├── fortyguard_map.py  # FortyGuard Native Map Provider
│           ├── osm.py             # OSM Fallback Provider
│           └── factory.py         # MapService Factory
├── tests/                         # Pytest automated test suite
├── .env.example                   # Environment variable template
├── .env                           # Local environment configuration
├── requirements.txt               # Dependencies
├── alembic.ini                    # Database migration config
└── README.md                      # Documentation
```

---

## 🛠️ Quickstart & Local Setup

### 1. Set up Python environment

```bash
cd backend
python -m venv venv
# On Windows:
venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure `.env`

Copy `.env.example` to `.env`:

```env
DATABASE_URL=sqlite:///./safestage.db
CLIMATE_PROVIDER=mock
FORTYGUARD_API_KEY=9fbb74d80169b93e3e77824b15194384
FORTYGUARD_BASE_URL=https://api.fortyguard.com
AI_API_KEY=your_google_ai_key
AI_MODEL=gemini-2.5-flash
AI_BASE_URL=https://generativelanguage.googleapis.com/v1beta
MAP_PROVIDER=fortyguard
```

### 4. Run database migrations (optional)

```bash
alembic upgrade head
```

### 5. Start development server

```bash
uvicorn app.main:app --reload --port 8000
```

The interactive API documentation is live at:
- **Swagger UI**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **ReDoc**: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

---

## 🧪 Running Automated Tests

Run `pytest` to execute all API, recommendation engine, provider, simulation, and PDF generation tests:

```bash
python -m pytest -v
```

---

## 📡 API Endpoint Reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Health check & current climate provider mode |
| `POST` | `/events` | Create outdoor event (stored in SQLite) |
| `GET` | `/events/{event_id}` | Retrieve event details |
| `POST` | `/analyze` | Execute heat risk analysis, score & recommendations with FortyGuard LTMs |
| `GET` | `/heatmap` | FortyGuard native spatial GeoJSON thermal grid |
| `POST` | `/simulate` | Compare two natural-language scenarios |
| `POST` | `/chat` | Gemini Flash planning copilot assistant |
| `GET` | `/report` | Generate and download Climate Readiness PDF report |

---

## 🌐 FortyGuard Large Temperature Models (LTMs) Integration Details

FortyGuard Enterprise Temperature API endpoints implemented in `app/integrations/climate/fortyguard.py`:

- **Authentication**: Header `api-key: YOUR_FORTYGUARD_KEY`
- **Endpoints Used**:
  - `POST /heat-intelligence` (`/v1/heat_intelligence`): Multi-dimensional temperature analysis
  - `POST /create-heatmap` (`/v1/heatmap`): Spatial GeoJSON thermal grid with `polygon_aoi`
  - `POST /street-view-segmentation` (`/v1/street-view-segmentation`): Urban canopy, surface albedo, shade index, vegetation density, pavement thermal radiation
  - `POST /environmental-parameters` (`/v1/environmental-parameters`): Wet Bulb Globe Temperature (WBGT), Land Surface Temperature (LST), Urban Heat Island (UHI) intensity, relative humidity, wind speed
  - `GET /v1/status/{activity_id}`: Asynchronous task status polling

## Complete API Property Reference

### `POST /events`

Required JSON properties are `name` (event name), `event_type` (for example `concert` or `festival`), `venue_name`, `address`, `latitude`, `longitude`, `attendance`, `start_datetime`, and `end_datetime`. Datetimes use ISO 8601 format and the start must be earlier than the end. `user_id` is optional; when supplied, the demo creates an organizer record if that ID does not exist.

### `GET /events` and `GET /events/{event_id}`

The list endpoint accepts `skip` (default `0`) and `limit` (default `2`, maximum `2` for the demo). A returned event contains `id`, `user_id`, `name`, `event_type`, `venue_name`, `address`, `latitude`, `longitude`, `attendance`, `start_datetime`, `end_datetime`, `created_at`, and `updated_at`.

### `POST /analyze`

Request JSON: `event_id`.

The response properties are `event_id`, `supported`, `message`, `provider`, `readiness_score`, `readiness_score_label`, `heat_risk_summary`, `temperature_summary`, `smart_date_recommendations`, `best_date_option`, `venue_layout_recommendations`, `heat_risk_zones`, `recommendations`, `ai_explanation`, and `analyzed_at`.

`temperature_summary` provides average, maximum, and heat-index temperatures, `wbgt_c`, `uhi_intensity_c`, `canopy_cover_pct`, and score `deductions`. Date options provide `date`, `time`, `score`, `heat_risk`, `avg_temp_c`, `max_temp_c`, and `reasoning`. Venue items provide `element`, `recommended_location`, optional `coordinates`, and `rationale`. Recommendations provide `id`, `type`, `title`, `recommendation`, `reasoning`, and `confidence`.

Each heat-risk zone provides `zone_id`, `name`, `risk_level`, `avg_temp_c`, polygon `coordinates`, and planner-oriented `advice`. Zones are relative areas inside the venue map. `Extreme` zones are unsuitable for queues, seating, children activities, or long dwell times. `High` zones should be short circulation or service areas after shade, hydration, and monitoring are added. `Moderate` zones support managed activity with nearby water and shade. `Low` zones are preferred for seating, family areas, medical recovery, and longer dwell times.

### `GET /heatmap`

Provide either `event_id`, or both `latitude` and `longitude`. Optional `timestamp` selects the heatmap frame. The response provides `supported`, `message`, optional `event_id`, `latitude`, `longitude`, `timestamp`, `provider`, `geojson`, and `zones`. `geojson` is a GeoJSON FeatureCollection suitable for map rendering.

### `POST /simulate`

Required JSON properties are `event_id`, `scenario_a`, and `scenario_b`. Both scenarios are natural-language strings, for example: `"Keep the event at 2 PM with standard shade."` and `"Move it to 6 PM with five cooling stations."` Optional `history` contains `{ "role": "user|assistant", "content": "..." }` messages.

The response always contains both `scenario_a` and `scenario_b`. Each result has `name`, `readiness_score`, `heat_risk_level`, `avg_temp_c`, `max_temp_c`, `peak_heat_exposure_hours`, `risk_factors`, and `mitigations`. The comparison also returns `recommended`, `score_difference`, `reason`, `tactical_action_plan`, and `ai_simulation_insights`.

### `POST /chat`

Required JSON properties are `event_id` and `message`. Optional `history` contains `{role, content}` messages. The response contains `event_id`, `reply`, and `context_used`. Chat is a frontend interaction and is not included in the PDF.

### `GET /report`

Required query property: `event_id`. The endpoint returns a PDF generated from the latest saved analysis. It includes the Gemini explanation, readiness score and deductions, climate metrics, all smart date options, venue layout, operational recommendations, and heat-risk zones. It does not make another Gemini request.

### `GET /health`

The response contains `status`, `project`, `version`, `climate_provider`, `fortyguard_base_url`, and `fortyguard_key_configured`.

## Gemini Request Behavior

The default model is `gemini-2.5-flash`. `/analyze` makes one Gemini explanation request, `/simulate` makes one comparison request, and `/chat` makes one request per user message. `/report`, `/events`, and `/heatmap` do not call Gemini. If Gemini is unavailable, deterministic SafeStage fallbacks keep analysis and simulation usable for demos.
