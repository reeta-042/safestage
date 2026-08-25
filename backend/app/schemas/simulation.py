"""
Simulation schemas — clean and focused comparison between Scenario A and Scenario B.
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any


class ScenarioHistoryMessage(BaseModel):
    role: str = Field(..., description="Message author: user or assistant")
    content: str = Field(..., min_length=1, description="Previous planning message")


class SimulateRequest(BaseModel):
    """
    Clean scenario simulation request comparing Scenario A vs Scenario B.
    """
    event_id: str = Field(..., description="Event ID to simulate scenarios for")
    scenario_a: str = Field(..., min_length=3, description="Scenario A description (e.g. 'Current afternoon schedule with 2 water stations')")
    scenario_b: str = Field(..., min_length=3, description="Scenario B description (e.g. 'Move event to 6 PM with 5 misting stations')")
    history: Optional[List[ScenarioHistoryMessage]] = Field(default_factory=list)


class ScenarioResult(BaseModel):
    name: str
    readiness_score: float
    heat_risk_level: str
    avg_temp_c: float
    max_temp_c: float
    peak_heat_exposure_hours: float
    risk_factors: List[str]
    mitigations: List[str]


class SimulateResponse(BaseModel):
    event_id: str
    supported: bool
    message: str
    scenario_a: ScenarioResult
    scenario_b: ScenarioResult
    recommended: str  # "scenario_a" or "scenario_b"
    score_difference: float = 0.0
    reason: str
    tactical_action_plan: List[str] = Field(default_factory=list)
    ai_simulation_insights: Optional[str] = None
