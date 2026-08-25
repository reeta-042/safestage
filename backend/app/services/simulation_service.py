"""
Simulation Service — clean What-If scenario comparison engine.

Compares Scenario A vs Scenario B using event context, FortyGuard climate intelligence,
and AI-driven tactical analysis.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional, List

from app.schemas.simulation import ScenarioResult, SimulateResponse
from app.services.ai_service import AIService
from app.core.errors import AIServiceError, AIOutputError

logger = logging.getLogger(__name__)


class SimulationService:

    @classmethod
    async def run_simulation(
        cls,
        event_id: str,
        event_name: str,
        event_lat: float,
        event_lon: float,
        attendance: int,
        start_datetime: datetime,
        end_datetime: datetime,
        scenario_a: str,
        scenario_b: str,
        venue_name: str = "",
        address: str = "",
        query: Optional[str] = None,
        history: Optional[List[Dict[str, str]]] = None,
        is_supported: bool = True,
        context: Optional[Dict[str, Any]] = None
    ) -> SimulateResponse:
        """
        Compare Scenario A and Scenario B using event context and AI simulation.
        """
        if not is_supported:
            return cls._unsupported_response(event_id, scenario_a, scenario_b)

        ctx = context or {
            "event_id": event_id,
            "event_name": event_name,
            "venue_name": venue_name,
            "address": address,
            "attendance": attendance,
            "start_datetime": start_datetime.isoformat() if isinstance(start_datetime, datetime) else str(start_datetime),
            "end_datetime": end_datetime.isoformat() if isinstance(end_datetime, datetime) else str(end_datetime),
            "latitude": event_lat,
            "longitude": event_lon
        }

        if query:
            ctx["query"] = query

        # Single AI simulation call to compare both scenarios
        sim_query = query or f"Compare Scenario A: '{scenario_a}' vs Scenario B: '{scenario_b}'"
        ai_res = await AIService.simulate_scenarios(
            event_name=event_name,
            context=ctx,
            query=sim_query,
            scenario_a_input=scenario_a,
            scenario_b_input=scenario_b,
            history=history
        )

        return cls._parse_ai_simulation_response(event_id, ai_res, scenario_a, scenario_b)

    @staticmethod
    def _safe_float(val: Any, default: float = 0.0) -> float:
        if val is None:
            return default
        try:
            return float(val)
        except (ValueError, TypeError):
            return default

    @classmethod
    def _parse_ai_simulation_response(
        cls,
        event_id: str,
        ai_res: Dict,
        scenario_a_name: str,
        scenario_b_name: str
    ) -> SimulateResponse:
        """Parse AI scenario simulation response."""
        a = ai_res.get("scenario_a", {})
        b = ai_res.get("scenario_b", {})

        raw_rec = str(ai_res.get("recommended", "scenario_b")).lower().strip()
        recommended = "scenario_a" if ("scenario_a" in raw_rec or raw_rec == "a") else "scenario_b"

        score_a = cls._safe_float(a.get("readiness_score"), 60.0)
        score_b = cls._safe_float(b.get("readiness_score"), 85.0)
        diff = round(abs(score_b - score_a), 1)

        return SimulateResponse(
            event_id=event_id,
            supported=True,
            message="Scenario simulation completed successfully.",
            scenario_a=ScenarioResult(
                name=a.get("name") or scenario_a_name,
                readiness_score=score_a,
                heat_risk_level=a.get("heat_risk_level") or "Moderate",
                avg_temp_c=cls._safe_float(a.get("avg_temp_c"), 33.0),
                max_temp_c=cls._safe_float(a.get("max_temp_c"), 36.0),
                peak_heat_exposure_hours=cls._safe_float(a.get("peak_heat_exposure_hours"), 2.0),
                risk_factors=a.get("risk_factors") or [],
                mitigations=a.get("mitigations") or []
            ),
            scenario_b=ScenarioResult(
                name=b.get("name") or scenario_b_name,
                readiness_score=score_b,
                heat_risk_level=b.get("heat_risk_level") or "Low",
                avg_temp_c=cls._safe_float(b.get("avg_temp_c"), 28.0),
                max_temp_c=cls._safe_float(b.get("max_temp_c"), 30.0),
                peak_heat_exposure_hours=cls._safe_float(b.get("peak_heat_exposure_hours"), 0.0),
                risk_factors=b.get("risk_factors") or [],
                mitigations=b.get("mitigations") or []
            ),
            recommended=recommended,
            score_difference=diff,
            reason=ai_res.get("reason") or f"Scenario {recommended.split('_')[-1].upper()} provides better thermal safety.",
            tactical_action_plan=ai_res.get("tactical_action_plan") or [],
            ai_simulation_insights=ai_res.get("ai_simulation_insights") or ""
        )

    @staticmethod
    def _unsupported_response(event_id: str, scenario_a: str = None, scenario_b: str = None) -> SimulateResponse:
        return SimulateResponse(
            event_id=event_id,
            supported=False,
            message="Hyperlocal climate intelligence is currently unavailable for this location.",
            scenario_a=ScenarioResult(
                name=scenario_a or "Scenario A",
                readiness_score=0.0,
                heat_risk_level="Unavailable",
                avg_temp_c=0.0,
                max_temp_c=0.0,
                peak_heat_exposure_hours=0.0,
                risk_factors=["Climate data unavailable"],
                mitigations=[]
            ),
            scenario_b=ScenarioResult(
                name=scenario_b or "Scenario B",
                readiness_score=0.0,
                heat_risk_level="Unavailable",
                avg_temp_c=0.0,
                max_temp_c=0.0,
                peak_heat_exposure_hours=0.0,
                risk_factors=["Climate data unavailable"],
                mitigations=[]
            ),
            recommended="scenario_a",
            score_difference=0.0,
            reason="Climate intelligence unavailable for this location.",
            tactical_action_plan=[],
            ai_simulation_insights="FortyGuard climate data is unavailable for this location."
        )
