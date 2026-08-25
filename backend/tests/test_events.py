from datetime import datetime, timedelta, timezone
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "online"
    assert "climate_provider" in data

def test_create_and_get_event():
    start_dt = (datetime.now(timezone.utc) + timedelta(days=10)).isoformat()
    end_dt = (datetime.now(timezone.utc) + timedelta(days=10, hours=6)).isoformat()

    payload = {
        "name": "Phoenix Summer Concert",
        "event_type": "concert",
        "venue_name": "Phoenix Outdoor Arena",
        "address": "Phoenix, Arizona",
        "latitude": 33.4484,
        "longitude": -112.0740,
        "attendance": 5000,
        "start_datetime": start_dt,
        "end_datetime": end_dt
    }

    # 1. Create event
    response = client.post("/events", json=payload)
    assert response.status_code == 201
    event_data = response.json()
    assert "id" in event_data
    assert event_data["name"] == payload["name"]
    event_id = event_data["id"]

    # 2. Get event
    get_resp = client.get(f"/events/{event_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == event_id

def test_create_event_with_user_id():
    start_dt = (datetime.now(timezone.utc) + timedelta(days=10)).isoformat()
    end_dt = (datetime.now(timezone.utc) + timedelta(days=10, hours=6)).isoformat()

    payload = {
        "user_id": "organizer_demo_123",
        "name": "Summer Kids Carnival",
        "event_type": "festival",
        "venue_name": "Riverside Park",
        "address": "Phoenix, Arizona",
        "latitude": 33.4484,
        "longitude": -112.0740,
        "attendance": 2500,
        "start_datetime": start_dt,
        "end_datetime": end_dt
    }

    create_resp = client.post("/events", json=payload)
    assert create_resp.status_code == 201
    data = create_resp.json()
    assert data["user_id"] == "organizer_demo_123"

    event_id = data["id"]
    get_resp = client.get(f"/events/{event_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["user_id"] == "organizer_demo_123"


def test_invalid_event_dates():
    start_dt = (datetime.now(timezone.utc) + timedelta(days=10)).isoformat()
    end_dt = (datetime.now(timezone.utc) + timedelta(days=9)).isoformat()  # Start after end

    payload = {
        "name": "Invalid Event",
        "event_type": "festival",
        "venue_name": "Test Venue",
        "address": "Phoenix, Arizona",
        "latitude": 33.4484,
        "longitude": -112.0740,
        "attendance": 1000,
        "start_datetime": start_dt,
        "end_datetime": end_dt
    }

    response = client.post("/events", json=payload)
    assert response.status_code == 400
    assert "start_datetime must be strictly before end_datetime" in response.json()["detail"]

def test_analyze_event_endpoint():
    start_dt = (datetime.now(timezone.utc) + timedelta(days=5)).isoformat()
    end_dt = (datetime.now(timezone.utc) + timedelta(days=5, hours=4)).isoformat()

    create_resp = client.post("/events", json={
        "name": "Desert Beats",
        "event_type": "festival",
        "venue_name": "Desert Park",
        "address": "Phoenix, AZ",
        "latitude": 33.4484,
        "longitude": -112.0740,
        "attendance": 3000,
        "start_datetime": start_dt,
        "end_datetime": end_dt
    })
    assert create_resp.status_code == 201
    event_id = create_resp.json()["id"]

    analyze_resp = client.post("/analyze", json={"event_id": event_id})
    assert analyze_resp.status_code == 200
    data = analyze_resp.json()
    assert data["event_id"] == event_id
    assert "readiness_score" in data
    assert "venue_layout_recommendations" in data
    assert len(data["venue_layout_recommendations"]) > 0

