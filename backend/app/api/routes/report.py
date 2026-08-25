"""
/report — Climate Readiness PDF Report endpoint.

Generates PDF report using actual event and analysis state.
No hardcoded climate data fallbacks.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
import os

from app.database.connection import get_db
from app.database.models import Report, HeatAnalysis, Recommendation
from app.services.event_service import EventService
from app.services.report_service import ReportService
from app.services.climate_service import ClimateService
from app.core.errors import raise_safestage_error, SafeStageError, ErrorCode

router = APIRouter(prefix="/report", tags=["Reports"])


@router.get("", summary="Download Climate Readiness PDF Report")
async def get_report(event_id: str = Query(..., description="Event ID"), db: Session = Depends(get_db)):
    """
    Generate and download the SafeStage Climate Readiness PDF report for an event.
    Requires that an event exists and uses its real analysis data.
    """
    event = EventService.get_event(db, event_id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Event '{event_id}' not found"
        )

    # Fetch latest heat analysis record if available
    latest_analysis = (
        db.query(HeatAnalysis)
        .filter(HeatAnalysis.event_id == event.id)
        .order_by(HeatAnalysis.analyzed_at.desc())
        .first()
    )

    provider = ClimateService.get_provider()
    supported = provider.is_location_supported(event.latitude, event.longitude)

    if latest_analysis and latest_analysis.temperature_data:
        snapshot = (latest_analysis.temperature_data or {}).get("analysis_snapshot", {})
        saved_recommendations = [
            {
                "title": r.recommendation,
                "recommendation": r.recommendation,
                "reasoning": r.reasoning
            }
            for r in db.query(Recommendation).filter(Recommendation.analysis_id == latest_analysis.id).all()
        ]

        temp_summary = snapshot.get("temperature_summary") or latest_analysis.temperature_data.get("summary", {})

        analysis_data = {
            "supported": supported,
            "provider": latest_analysis.provider,
            "readiness_score": latest_analysis.readiness_score,
            "readiness_score_label": "SafeStage Event Readiness Score",
            "best_date_option": snapshot.get("best_date_option"),
            "venue_layout_recommendations": snapshot.get("venue_layout_recommendations", []),
            "ai_explanation": snapshot.get("ai_explanation", "SafeStage operations analysis completed."),
            "temperature_summary": temp_summary,
            "smart_date_recommendations": snapshot.get("smart_date_recommendations", []),
            "heat_risk_zones": snapshot.get("heat_risk_zones", []),
            "recommendations": snapshot.get("recommendations") or saved_recommendations
        }
    else:
        # No analysis completed yet — report reflects actual state without fake climate figures
        analysis_data = {
            "supported": supported,
            "provider": "Pending Analysis",
            "readiness_score": 0.0,
            "readiness_score_label": "No Live Climate Analysis Available",
            "best_date_option": None,
            "venue_layout_recommendations": [],
            "ai_explanation": (
                f"No climate analysis has been run for {event.name} yet. "
                f"Run /analyze to generate FortyGuard hyperlocal temperature intelligence and operational recommendations."
            ),
            "temperature_summary": {
                "avg_temperature_c": None,
                "max_temperature_c": None,
                "max_heat_index_c": None,
                "deductions": ["Analysis required to compute readiness score."]
            },
            "smart_date_recommendations": [],
            "heat_risk_zones": [],
            "recommendations": []
        }

    event_dict = {
        "id": event.id,
        "name": event.name,
        "venue_name": event.venue_name,
        "address": event.address,
        "attendance": event.attendance
    }

    pdf_path = ReportService.generate_pdf_report(event_dict, analysis_data)

    # Record report generation in DB
    report_record = Report(event_id=event.id, report_path=pdf_path)
    db.add(report_record)
    db.commit()

    return FileResponse(
        path=pdf_path,
        filename=os.path.basename(pdf_path),
        media_type="application/pdf"
    )
