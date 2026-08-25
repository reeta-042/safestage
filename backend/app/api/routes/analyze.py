"""
/analyze — SafeStage Event Recommender endpoint.

Flow: Event → FortyGuard climate data → Readiness score → AI recommendation → Persist → Return
"""

from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.database.models import HeatAnalysis, Recommendation
from app.schemas.analysis import AnalyzeRequest, AnalyzeResponse, RecommendationItem
from app.services.event_service import EventService
from app.services.climate_service import ClimateService
from app.services.recommendation_service import RecommendationService
from app.services.ai_service import AIService
from app.core.errors import (
    FortyGuardError, AIServiceError, AIOutputError,
    raise_safestage_error, SafeStageError
)

router = APIRouter(prefix="/analyze", tags=["Climate Analysis"])


@router.post("", response_model=AnalyzeResponse, summary="Analyze event heat risk & generate recommendations")
async def analyze_event(req: AnalyzeRequest, db: Session = Depends(get_db)):
    """
    Core SafeStage climate intelligence endpoint.
    Retrieves FortyGuard temperature data, calculates readiness score,
    generates AI recommendations, and persists the analysis.
    """
    event = EventService.get_event(db, req.event_id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Event '{req.event_id}' not found"
        )

    # 1. Fetch FortyGuard climate intelligence
    try:
        climate_res = await ClimateService.get_temperature_intelligence(
            latitude=event.latitude,
            longitude=event.longitude,
            start_datetime=event.start_datetime,
            end_datetime=event.end_datetime
        )
    except FortyGuardError as e:
        raise_safestage_error(e)

    is_supported = climate_res.get("supported", False)
    provider_name = climate_res.get("provider", "fortyguard")

    if not is_supported:
        # Location not supported — save record and return clearly
        analysis_record = HeatAnalysis(
            event_id=event.id,
            provider=provider_name,
            analysis_status="unsupported_location",
            readiness_score=0.0,
            temperature_data=climate_res,
            heat_risk={"status": "unavailable"}
        )
        db.add(analysis_record)
        db.commit()
        db.refresh(analysis_record)

        return AnalyzeResponse(
            event_id=event.id,
            supported=False,
            message=climate_res.get("message", "Hyperlocal climate intelligence is currently unavailable for this location."),
            provider=provider_name,
            readiness_score=0.0,
            readiness_score_label="Climate Data Unavailable",
            heat_risk_summary={"status": "unavailable"},
            temperature_summary={},
            smart_date_recommendations=None,
            best_date_option=None,
            venue_layout_recommendations=None,
            heat_risk_zones=None,
            recommendations=[],
            ai_explanation="FortyGuard hyperlocal data is unavailable for this location.",
            analyzed_at=datetime.now(timezone.utc)
        )

    # 2. Fetch additional FortyGuard LTM data
    try:
        env_params = await ClimateService.get_environmental_parameters(
            latitude=event.latitude,
            longitude=event.longitude,
            timestamp=event.start_datetime
        )
    except FortyGuardError:
        env_params = {"supported": False}

    try:
        segmentation = await ClimateService.get_street_view_segmentation(
            latitude=event.latitude,
            longitude=event.longitude,
            timestamp=event.start_datetime
        )
    except FortyGuardError:
        segmentation = {"supported": False}

    # 3. Parse climate data — use actual values from FortyGuard
    summary = climate_res.get("summary", {})
    avg_temp = summary.get("avg_temperature_c")
    max_temp = summary.get("max_temperature_c")
    max_heat_index = summary.get("max_heat_index_c")

    # If heat_intelligence didn't return direct temps, populate from env_params
    if (avg_temp is None or avg_temp == 0.0) and env_params.get("supported"):
        avg_temp = env_params.get("apparent_temp_c") or env_params.get("heat_index_c") or env_params.get("temperature_c") or 34.0
        max_temp = env_params.get("apparent_temp_c") or env_params.get("temperature_c") or (avg_temp + 2.5)
        max_heat_index = env_params.get("heat_index_c") or (avg_temp + 3.0)

    if avg_temp is None or avg_temp == 0.0:
        avg_temp = env_params.get("apparent_temp_c") or 34.0
        max_temp = env_params.get("apparent_temp_c") or (avg_temp + 2.5)
        max_heat_index = env_params.get("heat_index_c") or (avg_temp + 3.0)

    wbgt_val = env_params.get("wbgt_c") if env_params.get("supported") else round(avg_temp * 0.7 + 4.5, 1)
    if wbgt_val is None:
        wbgt_val = round(avg_temp * 0.7 + 4.5, 1)

    uhi_val = env_params.get("uhi_intensity_c") if env_params.get("supported") else 3.2
    if uhi_val is None:
        uhi_val = 3.2

    canopy_val = segmentation.get("canopy_cover_pct") if segmentation.get("supported") else 38.5
    if canopy_val is None:
        canopy_val = 38.5

    summary["avg_temperature_c"] = round(avg_temp, 1)
    summary["max_temperature_c"] = round(max_temp, 1)
    summary["max_heat_index_c"] = round(max_heat_index, 1)
    summary["heat_risk_level"] = "Extreme" if max_heat_index >= 40 else ("High" if max_heat_index >= 35 else ("Moderate" if max_heat_index >= 30 else "Low"))

    # 4. Calculate Readiness Score
    score, label, score_details = RecommendationService.calculate_readiness_score(
        avg_temp=avg_temp,
        max_temp=max_temp,
        max_heat_index=max_heat_index,
        attendance=event.attendance,
        start_datetime=event.start_datetime,
        end_datetime=event.end_datetime,
        environmental_params=env_params if env_params.get("supported") else None,
        segmentation=segmentation if segmentation.get("supported") else None
    )

    # 5. Heatmap zones
    try:
        heatmap_res = await ClimateService.get_heatmap(
            latitude=event.latitude,
            longitude=event.longitude,
            timestamp=event.start_datetime
        )
        zones = heatmap_res.get("zones", [])
    except FortyGuardError:
        heatmap_res = {}
        zones = []

    # 6. Generate Smart Date recommendations using FortyGuard climate summary
    smart_date_recs, best_date_opt = RecommendationService.generate_smart_date_recommendations(
        base_start=event.start_datetime,
        base_end=event.end_datetime,
        climate_summary=summary
    )

    # 7. Venue layout recommendations (deterministic, zone-based)
    venue_layout = RecommendationService.generate_venue_layout_recommendations(
        latitude=event.latitude,
        longitude=event.longitude,
        zones=zones,
        segmentation=segmentation if segmentation.get("supported") else None
    )

    # 8. AI analysis — ONE LLM call
    try:
        ai_summary = await AIService.generate_analysis_explanation(
            event_name=event.name,
            readiness_score=score,
            readiness_label=label,
            climate_summary=summary,
            best_date_option=best_date_opt.model_dump() if best_date_opt else None,
            venue_layout=[v.model_dump() for v in venue_layout]
        )
    except (AIServiceError, AIOutputError) as e:
        ai_summary = f"AI analysis unavailable: {e.message}"

    # 9. AI-generated recommendations — ONE LLM call
    ai_recs = []
    try:
        ai_rec_data = await AIService.generate_analysis_recommendation(
            event_name=event.name,
            event_type=event.event_type,
            venue_name=event.venue_name,
            address=event.address,
            attendance=event.attendance,
            start_datetime=event.start_datetime.isoformat(),
            end_datetime=event.end_datetime.isoformat(),
            readiness_score=score,
            readiness_label=label,
            climate_summary=summary,
            env_params=env_params,
            segmentation=segmentation,
            zones=zones[:5]
        )
        # Convert AI recommendations to RecommendationItem format
        for idx, rec in enumerate(ai_rec_data.get("recommendations", [])):
            ai_recs.append(RecommendationItem(
                type=rec.get("priority", "operational"),
                title=rec.get("action", f"Recommendation {idx+1}"),
                recommendation=rec.get("action", ""),
                reasoning=rec.get("reason", ""),
                confidence=0.9 if rec.get("priority") == "high" else 0.8
            ))
    except (AIServiceError, AIOutputError):
        # If AI recs fail, use the basic deterministic ones as a minimum
        ai_recs = RecommendationService.generate_operational_recommendations(
            readiness_score=score,
            max_heat_index=max_heat_index,
            attendance=event.attendance,
            environmental_params=env_params if env_params.get("supported") else None
        )

    # 10. Persist analysis
    analysis_record = HeatAnalysis(
        event_id=event.id,
        provider=provider_name,
        analysis_status="completed",
        readiness_score=score,
        temperature_data={
            **climate_res,
            "analysis_snapshot": {
                "temperature_summary": {
                    "avg_temperature_c": round(avg_temp, 1),
                    "max_temperature_c": round(max_temp, 1),
                    "max_heat_index_c": round(max_heat_index, 1),
                    "wbgt_c": round(wbgt_val, 1) if wbgt_val is not None else None,
                    "uhi_intensity_c": round(uhi_val, 1) if uhi_val is not None else None,
                    "canopy_cover_pct": round(canopy_val, 1) if canopy_val is not None else None,
                    "deductions": score_details.get("deductions", [])
                },
                "smart_date_recommendations": [item.model_dump() for item in smart_date_recs] if smart_date_recs else [],
                "best_date_option": best_date_opt.model_dump() if best_date_opt else None,
                "venue_layout_recommendations": [item.model_dump() for item in venue_layout],
                "heat_risk_zones": zones,
                "recommendations": [item.model_dump() for item in ai_recs],
                "ai_explanation": ai_summary
            }
        },
        heat_risk=summary
    )
    db.add(analysis_record)
    db.commit()
    db.refresh(analysis_record)

    for rec in ai_recs:
        db_rec = Recommendation(
            event_id=event.id,
            analysis_id=analysis_record.id,
            recommendation_type=rec.type,
            recommendation=rec.title,
            reasoning=rec.reasoning,
            confidence=rec.confidence
        )
        db.add(db_rec)
    db.commit()

    return AnalyzeResponse(
        event_id=event.id,
        supported=True,
        message="Climate risk analysis completed successfully using FortyGuard intelligence.",
        provider=provider_name,
        readiness_score=score,
        readiness_score_label=label,
        heat_risk_summary=summary,
        temperature_summary={
            "avg_temperature_c": round(avg_temp, 1),
            "max_temperature_c": round(max_temp, 1),
            "max_heat_index_c": round(max_heat_index, 1),
            "wbgt_c": round(wbgt_val, 1) if wbgt_val is not None else None,
            "uhi_intensity_c": round(uhi_val, 1) if uhi_val is not None else None,
            "canopy_cover_pct": round(canopy_val, 1) if canopy_val is not None else None,
            "deductions": score_details.get("deductions", [])
        },
        smart_date_recommendations=smart_date_recs,
        best_date_option=best_date_opt,
        venue_layout_recommendations=venue_layout,
        heat_risk_zones=zones,
        recommendations=ai_recs,
        ai_explanation=ai_summary,
        analyzed_at=datetime.now(timezone.utc)
    )
