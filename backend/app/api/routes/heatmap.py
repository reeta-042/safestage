"""
/heatmap — FortyGuard spatial heat risk GeoJSON endpoint.

Returns actual FortyGuard-derived heatmap data. No fabricated zones.
"""

from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.schemas.analysis import HeatmapResponse
from app.services.event_service import EventService
from app.services.climate_service import ClimateService
from app.core.errors import FortyGuardError, raise_safestage_error

router = APIRouter(prefix="/heatmap", tags=["Hyperlocal Heatmap"])


@router.get("", response_model=HeatmapResponse, summary="Get spatial heat risk GeoJSON grid")
async def get_heatmap(
    event_id: Optional[str] = Query(None, description="Optional Event ID to fetch location from"),
    latitude: Optional[float] = Query(None, description="Latitude"),
    longitude: Optional[float] = Query(None, description="Longitude"),
    timestamp: Optional[datetime] = Query(None, description="ISO Timestamp for heat map frame"),
    db: Session = Depends(get_db)
):
    """
    Retrieves high-resolution spatial temperature GeoJSON grid using FortyGuard.
    Can be queried either by event_id or explicit latitude/longitude coordinates.
    """
    if latitude is not None and longitude is not None:
        lat = latitude
        lon = longitude
        ts = timestamp or datetime.now(timezone.utc)
        effective_event_id = None
    elif event_id:
        event = EventService.get_event(db, event_id)
        if not event:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Event '{event_id}' not found"
            )
        lat = event.latitude
        lon = event.longitude
        ts = timestamp or event.start_datetime
        effective_event_id = event.id
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Must provide either both 'latitude' and 'longitude' or a valid 'event_id'."
        )

    try:
        res = await ClimateService.get_heatmap(
            latitude=lat,
            longitude=lon,
            timestamp=ts
        )
    except FortyGuardError as e:
        raise_safestage_error(e)

    if not res.get("supported", False):
        return HeatmapResponse(
            supported=False,
            message=res.get("message", "Hyperlocal climate intelligence is currently unavailable for this location."),
            event_id=effective_event_id,
            latitude=lat,
            longitude=lon,
            timestamp=ts.isoformat(),
            provider=res.get("provider", "fortyguard"),
            geojson={"type": "FeatureCollection", "features": []},
            zones=[]
        )

    return HeatmapResponse(
        supported=True,
        message="FortyGuard spatial heat map retrieved successfully.",
        event_id=effective_event_id,
        latitude=lat,
        longitude=lon,
        timestamp=ts.isoformat(),
        provider=res.get("provider", "fortyguard"),
        geojson=res.get("geojson", {"type": "FeatureCollection", "features": []}),
        zones=res.get("zones", [])
    )
