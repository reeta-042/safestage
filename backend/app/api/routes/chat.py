"""
/chat — SafeStage Event Planning Assistant endpoint.

The AI receives actual event context + FortyGuard data + conversation history.
No keyword matching. No hardcoded responses.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.database.models import HeatAnalysis
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.event_service import EventService
from app.services.ai_service import AIService
from app.services.climate_service import ClimateService
from app.core.errors import AIServiceError, raise_safestage_error

router = APIRouter(prefix="/chat", tags=["AI Copilot Chat"])


@router.post("", response_model=ChatResponse, summary="Chat with SafeStage AI Event Planning Assistant")
async def chat_copilot(req: ChatRequest, db: Session = Depends(get_db)):
    """
    Interactive natural language AI assistant for event organizers.
    Uses actual event context and FortyGuard climate data — never keyword matching.
    """
    event = EventService.get_event(db, req.event_id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Event '{req.event_id}' not found"
        )

    # Fetch latest analysis if available
    latest_analysis = (
        db.query(HeatAnalysis)
        .filter(HeatAnalysis.event_id == event.id)
        .order_by(HeatAnalysis.analyzed_at.desc())
        .first()
    )

    context = {
        "event_id": event.id,
        "event_name": event.name,
        "event_type": event.event_type,
        "venue_name": event.venue_name,
        "address": event.address,
        "attendance": event.attendance,
        "start_datetime": event.start_datetime.isoformat(),
        "end_datetime": event.end_datetime.isoformat(),
        "latitude": event.latitude,
        "longitude": event.longitude,
        "has_analysis": latest_analysis is not None,
    }

    if latest_analysis:
        context["readiness_score"] = latest_analysis.readiness_score
        context["analysis_status"] = latest_analysis.analysis_status

        if latest_analysis.heat_risk:
            context["heat_risk_level"] = latest_analysis.heat_risk.get("heat_risk_level")
            context["heat_risk_summary"] = latest_analysis.heat_risk

        if latest_analysis.temperature_data:
            context["temperature_summary"] = latest_analysis.temperature_data.get("summary", {})
            snapshot = latest_analysis.temperature_data.get("analysis_snapshot", {})
            if snapshot:
                context["ai_explanation"] = snapshot.get("ai_explanation")
                context["recommendations"] = snapshot.get("recommendations", [])
    else:
        try:
            climate_res = await ClimateService.get_temperature_intelligence(
                latitude=event.latitude,
                longitude=event.longitude,
                start_datetime=event.start_datetime,
                end_datetime=event.end_datetime,
            )
            if climate_res.get("supported"):
                context["has_analysis"] = True
                context["temperature_summary"] = climate_res.get("summary", {})
                context["heat_risk_level"] = climate_res.get("summary", {}).get("heat_risk_level")
                context["heat_risk_summary"] = climate_res.get("summary", {})
        except Exception:
            context["has_analysis"] = False

    history_list = [{"role": h.role, "content": h.content} for h in req.history] if req.history else []

    # ONE LLM call — raises AIServiceError on failure
    try:
        reply = await AIService.chat_copilot(
            event_name=event.name,
            user_message=req.message,
            context=context,
            history=history_list
        )
    except AIServiceError as e:
        raise_safestage_error(e)

    return ChatResponse(
        event_id=event.id,
        reply=reply,
        context_used=context
    )
