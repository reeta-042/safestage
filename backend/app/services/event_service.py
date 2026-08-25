"""
Event Service — CRUD operations + geocoding integration.
"""

import logging
from typing import Optional, List, Tuple

from sqlalchemy.orm import Session

from app.database.models import Event, User
from app.schemas.events import EventCreate
from app.core.errors import LocationResolutionError
from app.integrations.maps.osm import OSMMapProvider

logger = logging.getLogger(__name__)


class EventService:

    @staticmethod
    def create_event(db: Session, event_in: EventCreate) -> Event:
        if event_in.user_id:
            user = db.query(User).filter(User.id == event_in.user_id).first()
            if not user:
                user = User(
                    id=event_in.user_id,
                    name="Event Organizer",
                    email=f"{event_in.user_id}@safestage.io"
                )
                db.add(user)
                db.flush()

        db_event = Event(
            name=event_in.name,
            event_type=event_in.event_type,
            venue_name=event_in.venue_name,
            address=event_in.address,
            latitude=event_in.latitude,
            longitude=event_in.longitude,
            attendance=event_in.attendance,
            start_datetime=event_in.start_datetime,
            end_datetime=event_in.end_datetime,
            user_id=event_in.user_id
        )
        db.add(db_event)
        db.commit()
        db.refresh(db_event)
        return db_event

    @staticmethod
    def get_event(db: Session, event_id: str) -> Optional[Event]:
        return db.query(Event).filter(Event.id == event_id).first()

    @staticmethod
    def list_events(db: Session, skip: int = 0, limit: int = 100) -> List[Event]:
        return db.query(Event).offset(skip).limit(limit).all()

    @staticmethod
    async def geocode_venue(venue_name: str, address: str) -> Tuple[float, float, Optional[str]]:
        """
        Resolve a venue name + address to (latitude, longitude, normalized_address).
        Uses OSM Nominatim for geocoding.
        Raises LocationResolutionError if geocoding fails.
        """
        geocoder = OSMMapProvider()

        # Try venue_name + address combined first, then address alone
        queries = [
            f"{venue_name}, {address}",
            address,
            venue_name
        ]

        for query in queries:
            try:
                results = await geocoder.geocode(query)
                if results:
                    best = results[0]
                    lat = best.get("latitude")
                    lon = best.get("longitude")
                    display_name = best.get("display_name")

                    if lat is not None and lon is not None:
                        logger.info(f"Geocoded '{query}' → ({lat}, {lon})")
                        return lat, lon, display_name
            except Exception as exc:
                logger.warning(f"Geocoding attempt failed for '{query}': {exc}")
                continue

        raise LocationResolutionError(
            message=f"Could not resolve location for venue '{venue_name}' at '{address}'.",
            detail="Try providing a more specific address or manually enter latitude/longitude."
        )
