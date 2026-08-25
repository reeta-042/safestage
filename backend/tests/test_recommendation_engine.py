from datetime import datetime, timedelta, timezone
from app.services.recommendation_service import RecommendationService

def test_readiness_score_calculation():
    start_dt = datetime.now(timezone.utc).replace(hour=14, minute=0)
    end_dt = start_dt + timedelta(hours=6)

    # Moderate temp
    score1, label1, details1 = RecommendationService.calculate_readiness_score(
        avg_temp=28.0,
        max_temp=30.0,
        max_heat_index=31.0,
        attendance=1000,
        start_datetime=start_dt,
        end_datetime=end_dt
    )
    assert 70.0 <= score1 <= 100.0

    # Extreme heat
    score2, label2, details2 = RecommendationService.calculate_readiness_score(
        avg_temp=38.0,
        max_temp=42.0,
        max_heat_index=44.0,
        attendance=10000,
        start_datetime=start_dt,
        end_datetime=end_dt
    )
    assert score2 < score1
    assert score2 < 50.0

def test_smart_date_recommendations():
    start_dt = datetime.now(timezone.utc).replace(hour=14, minute=0)
    end_dt = start_dt + timedelta(hours=6)
    climate_summary = {"avg_temperature_c": 34.0, "max_temperature_c": 37.0}

    options, best = RecommendationService.generate_smart_date_recommendations(
        base_start=start_dt,
        base_end=end_dt,
        climate_summary=climate_summary
    )

    assert len(options) > 0
    assert best.score >= options[-1].score
    assert "Evening" in best.date or best.score > 80.0

def test_venue_layout_recommendations():
    dict_zones = [
        {"zone_id": "z1", "name": "East Canopy", "risk_level": "Low", "avg_temp_c": 28.0, "coordinates": [[0,0]], "advice": "Cool"},
        {"zone_id": "z2", "name": "West Asphalt", "risk_level": "Extreme", "avg_temp_c": 40.0, "coordinates": [[0,0]], "advice": "Hot"}
    ]
    layout = RecommendationService.generate_venue_layout_recommendations(
        latitude=33.4484,
        longitude=-112.0740,
        zones=dict_zones,
        segmentation={"canopy_cover_pct": 40.0, "surface_albedo": 0.2}
    )
    assert len(layout) == 4
    assert any(item.element == "Main Stage" for item in layout)
    assert any(item.element == "Misting & Cooling Stations" for item in layout)

