"""
/simulate — SafeStage What-If Scenario Simulation endpoint.

Compares Scenario A vs Scenario B using event context and FortyGuard intelligence.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.database.models import HeatAnalysis
from app.schemas.simulation import SimulateRequest, SimulateResponse
from app.services.event_service import EventService
from app.services.climate_service import ClimateService
from app.services.simulation_service import SimulationService
from app.core.errors import AIServiceError, AIOutputError, FortyGuardError, raise_safestage_error

router = APIRouter(prefix="/simulate", tags=["Scenario Simulation"])


@router.post("", response_model=SimulateResponse, summary="Simulate & compare What-If operational scenarios")
async def simulate_scenarios(req: SimulateRequest, db: Session = Depends(get_db)):
    """
    Compare Scenario A vs Scenario B for an event using FortyGuard climate intelligence and AI.
    """
    event = EventService.get_event(db, req.event_id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Event '{req.event_id}' not found"
        )

    # Check location support
    provider = ClimateService.get_provider()
    is_supported = provider.is_location_supported(event.latitude, event.longitude)

    # Build context from actual event data
    latest_analysis = (
        db.query(HeatAnalysis)
        .filter(HeatAnalysis.event_id == event.id)
        .order_by(HeatAnalysis.analyzed_at.desc())
        .first()
    )

    context = {
        "event_id": event.id,
        "event_name": event.name,
        "venue_name": event.venue_name,
        "address": event.address,
        "attendance": event.attendance,
        "start_datetime": event.start_datetime.isoformat(),
        "end_datetime": event.end_datetime.isoformat(),
        "latitude": event.latitude,
        "longitude": event.longitude,
    }

    if latest_analysis:
        context["readiness_score"] = latest_analysis.readiness_score
        if latest_analysis.heat_risk:
            context["heat_risk_level"] = latest_analysis.heat_risk.get("heat_risk_level")
        if latest_analysis.temperature_data:
            context["temperature_summary"] = latest_analysis.temperature_data.get("summary", {})

    try:
        return await SimulationService.run_simulation(
            event_id=event.id,
            event_name=event.name,
            event_lat=event.latitude,
            event_lon=event.longitude,
            attendance=event.attendance,
            start_datetime=event.start_datetime,
            end_datetime=event.end_datetime,
            scenario_a=req.scenario_a,
            scenario_b=req.scenario_b,
            venue_name=event.venue_name,
            address=event.address,
            history=[msg.model_dump() for msg in req.history] if req.history else [],
            is_supported=is_supported,
            context=context
        )
    except (AIServiceError, AIOutputError) as e:
        raise_safestage_error(e)
    except FortyGuardError as e:
        raise_safestage_error(e)
