from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime
from typing import Optional

class EventCreate(BaseModel):
    name: str = Field(..., json_schema_extra={"example": "Summer Concert"})
    event_type: str = Field(..., json_schema_extra={"example": "concert"})
    venue_name: str = Field(..., json_schema_extra={"example": "Chase Field"})
    address: str = Field(..., json_schema_extra={"example": "Phoenix, Arizona"})
    latitude: float = Field(..., json_schema_extra={"example": 33.4484})
    longitude: float = Field(..., json_schema_extra={"example": -112.0740})
    attendance: int = Field(..., json_schema_extra={"example": 5000})
    start_datetime: datetime = Field(..., json_schema_extra={"example": "2026-08-15T14:00:00"})
    end_datetime: datetime = Field(..., json_schema_extra={"example": "2026-08-15T20:00:00"})
    user_id: Optional[str] = None

class EventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: Optional[str] = None
    name: str
    event_type: str
    venue_name: str
    address: str
    latitude: float
    longitude: float
    attendance: int
    start_datetime: datetime
    end_datetime: datetime
    created_at: datetime
    updated_at: datetime
