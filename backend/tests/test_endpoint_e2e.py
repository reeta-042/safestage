from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def _create_event():
    start = datetime.now(timezone.utc) + timedelta(days=10)
    response = client.post("/events", json={
        "name": "Endpoint Journey Festival",
        "event_type": "festival",
        "venue_name": "Phoenix Park",
        "address": "Phoenix, Arizona",
        "latitude": 33.4484,
        "longitude": -112.0740,
        "attendance": 2500,
        "start_datetime": start.isoformat(),
        "end_datetime": (start + timedelta(hours=5)).isoformat()
    })
    assert response.status_code == 201
    return response.json()


def test_event_analysis_heatmap_simulation_chat_report_journey():
    event = _create_event()
    event_id = event["id"]

    analysis = client.post("/analyze", json={"event_id": event_id})
    assert analysis.status_code == 200
    assert analysis.json()["event_id"] == event_id

    heatmap = client.get("/heatmap", params={"event_id": event_id})
    assert heatmap.status_code == 200
    assert heatmap.json()["geojson"]["type"] == "FeatureCollection"

    coordinate_heatmap = client.get("/heatmap", params={
        "latitude": 33.4484,
        "longitude": -112.0740
    })
    assert coordinate_heatmap.status_code == 200

    simulation = client.post("/simulate", json={
        "event_id": event_id,
        "scenario_a": "Keep the event at 2 PM with standard shade and two water stations.",
        "scenario_b": "Move the event to 6 PM with five cooling stations and a family shade zone."
    })
    assert simulation.status_code == 200
    simulation_data = simulation.json()
    assert simulation_data["scenario_a"]
    assert simulation_data["scenario_b"]
    assert simulation_data["recommended"] == "scenario_b"

    chat = client.post("/chat", json={
        "event_id": event_id,
        "message": "Help me plan cooling and hydration for families at this event."
    })
    assert chat.status_code == 200
    assert chat.json()["reply"]

    report = client.get("/report", params={"event_id": event_id})
    assert report.status_code == 200
    assert report.headers["content-type"] == "application/pdf"
    assert len(report.content) > 1000


def test_simulation_rejects_missing_scenario_inputs():
    response = client.post("/simulate", json={
        "event_id": "does-not-matter",
        "scenario_a": "Only one scenario provided."
    })
    assert response.status_code == 422