import pytest
from app.services.ai_service import AIService
from app.core.config import settings
from app.core.errors import AIServiceError

@pytest.mark.asyncio
async def test_ai_explanation_with_missing_key_raises_error(monkeypatch):
    """Verifies that missing AI key raises AIServiceError and never falls back to fake text."""
    monkeypatch.setattr(settings, "AI_API_KEY", None)
    summary = {"max_temperature_c": 36.5, "max_heat_index_c": 39.0, "heat_risk_level": "High"}
    best_date = {"date": "Friday, Aug 15", "time": "18:00 - 22:00", "score": 88.0}
    venue_layout = [{"element": "Main Stage", "recommended_location": "North shaded lawn"}]

    with pytest.raises(AIServiceError) as exc_info:
        await AIService.generate_analysis_explanation(
            event_name="Riverfront Festival",
            readiness_score=72.0,
            readiness_label="High Heat Risk",
            climate_summary=summary,
            best_date_option=best_date,
            venue_layout=venue_layout
        )
    assert exc_info.value.code == "AI_SERVICE_UNAVAILABLE"


@pytest.mark.asyncio
async def test_ai_chat_with_missing_key_raises_error(monkeypatch):
    """Verifies that missing AI key raises AIServiceError for chat instead of using keyword matching."""
    monkeypatch.setattr(settings, "AI_API_KEY", None)
    context = {
        "readiness_score": 78.0,
        "heat_risk_level": "Moderate",
        "supported": True,
        "attendance": 3200,
        "venue_name": "Harbor Park",
        "address": "Austin, Texas",
        "temperature_summary": {"max_heat_index_c": 41.5}
    }
    with pytest.raises(AIServiceError) as exc_info:
        await AIService.chat_copilot(
            event_name="Sunset Run",
            user_message="Which time is safest for my event?",
            context=context
        )
    assert exc_info.value.code == "AI_SERVICE_UNAVAILABLE"


@pytest.mark.asyncio
async def test_ai_simulation_with_missing_key_raises_error(monkeypatch):
    """Verifies that missing AI key raises AIServiceError for simulation instead of returning fake scenarios."""
    monkeypatch.setattr(settings, "AI_API_KEY", None)
    context = {
        "event_name": "Summer Concert",
        "readiness_score": 50.0,
        "temperature_summary": {"max_heat_index_c": 42.0}
    }
    with pytest.raises(AIServiceError) as exc_info:
        await AIService.simulate_scenarios(
            event_name="Summer Concert",
            context=context,
            query="What if we move to 6 PM?",
            scenario_a_input="Saturday noon",
            scenario_b_input="Saturday 6 PM"
        )
    assert exc_info.value.code == "AI_SERVICE_UNAVAILABLE"


@pytest.mark.asyncio
async def test_ai_explanation_with_live_llm():
    if not settings.AI_API_KEY:
        pytest.skip("AI_API_KEY not configured")

    summary = {"max_temperature_c": 36.5, "max_heat_index_c": 39.0, "heat_risk_level": "High"}
    best_date = {"date": "Saturday, Aug 15", "time": "17:00 - 21:00", "score": 88.0}
    venue_layout = [{"element": "Main Stage", "recommended_location": "East Canopy Zone"}]

    explanation = await AIService.generate_analysis_explanation(
        event_name="Phoenix Festival",
        readiness_score=72.0,
        readiness_label="High Heat Risk",
        climate_summary=summary,
        best_date_option=best_date,
        venue_layout=venue_layout
    )

    assert len(explanation) > 0
    assert "Phoenix Festival" in explanation or "72" in explanation or "Heat" in explanation


@pytest.mark.asyncio
async def test_ai_chat_with_live_llm():
    if not settings.AI_API_KEY:
        pytest.skip("AI_API_KEY not configured")

    context = {
        "has_analysis": True,
        "readiness_score": 75.0,
        "heat_risk_level": "Moderate",
        "venue_name": "Chase Field",
        "address": "Phoenix, Arizona",
        "attendance": 5000,
        "temperature_summary": {"avg_temperature_c": 34.0, "max_heat_index_c": 38.0}
    }
    reply = await AIService.chat_copilot(
        event_name="Summer Concert",
        user_message="Where should we place the misting stations and medical tents?",
        context=context
    )
    assert len(reply) > 0
