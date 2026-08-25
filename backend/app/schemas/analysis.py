from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List, Dict, Any

class AnalyzeRequest(BaseModel):
    event_id: str

class RecommendationItem(BaseModel):
    id: Optional[str] = None
    type: str  # date_time, venue_layout, operational, safety
    title: str
    recommendation: str
    reasoning: str
    confidence: float = 0.9

class SmartDateOption(BaseModel):
    date: str
    time: str
    score: float
    heat_risk: str
    avg_temp_c: float
    max_temp_c: float
    reasoning: List[str]

class VenueLayoutItem(BaseModel):
    element: str  # stage, cooling_station, medical_tent, shade_water
    recommended_location: str
    coordinates: Optional[Dict[str, float]] = None
    rationale: str

class HeatRiskZone(BaseModel):
    zone_id: str
    name: str
    risk_level: str  # Low, Moderate, High, Extreme
    avg_temp_c: float
    coordinates: List[List[float]]
    advice: str

class AnalyzeResponse(BaseModel):
    event_id: str
    supported: bool
    message: str
    provider: str
    readiness_score: float
    readiness_score_label: str
    heat_risk_summary: Dict[str, Any]
    temperature_summary: Dict[str, Any]
    smart_date_recommendations: Optional[List[SmartDateOption]] = None
    best_date_option: Optional[SmartDateOption] = None
    venue_layout_recommendations: Optional[List[VenueLayoutItem]] = None
    heat_risk_zones: Optional[List[HeatRiskZone]] = None
    recommendations: List[RecommendationItem]
    ai_explanation: str
    analyzed_at: datetime

class HeatmapResponse(BaseModel):
    supported: bool
    message: str
    event_id: Optional[str] = None
    latitude: float
    longitude: float
    timestamp: str
    provider: str
    geojson: Dict[str, Any]
    zones: List[HeatRiskZone]
