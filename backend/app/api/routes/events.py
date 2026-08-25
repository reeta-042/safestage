"""
Events route — create, retrieve, list events.
Geocodes venue addresses automatically when lat/lon are not provided.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import List

from app.database.connection import get_db
from app.schemas.events import EventCreate, EventResponse
from app.services.event_service import EventService
from app.core.errors import LocationResolutionError, raise_safestage_error

router = APIRouter(prefix="/events", tags=["Events"])


@router.post("", response_model=EventResponse, status_code=status.HTTP_201_CREATED, summary="Create an outdoor event")
async def create_event(event_in: EventCreate, db: Session = Depends(get_db)):
    """
    Create an outdoor event for climate risk analysis and venue planning.
    If latitude/longitude are not provided, the venue_name + address will be geocoded automatically.
    """
    if event_in.start_datetime >= event_in.end_datetime:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="start_datetime must be strictly before end_datetime"
        )

    # Geocode if coordinates not provided
    if event_in.latitude is None or event_in.longitude is None:
        try:
            lat, lon, resolved_address = await EventService.geocode_venue(
                venue_name=event_in.venue_name,
                address=event_in.address
            )
            event_in.latitude = lat
            event_in.longitude = lon
            # Update address with the resolved normalized address if more specific
            if resolved_address:
                event_in.address = resolved_address
        except LocationResolutionError as e:
            raise_safestage_error(e)

    event = EventService.create_event(db, event_in)
    return event


@router.get("/{event_id}", response_model=EventResponse, summary="Get event details")
def get_event(event_id: str, db: Session = Depends(get_db)):
    """
    Retrieve event details by ID.
    """
    event = EventService.get_event(db, event_id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Event with id '{event_id}' not found"
        )
    return event


@router.get("", response_model=List[EventResponse], summary="List all events")
def list_events(skip: int = 0, limit: int = Query(20, ge=1, le=100), db: Session = Depends(get_db)):
    """
    List events stored in the database.
    """
    return EventService.list_events(db, skip=skip, limit=limit)
