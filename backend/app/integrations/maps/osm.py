import logging
import httpx
from datetime import datetime
from typing import Dict, Any, Optional, List
from app.integrations.maps.base import BaseMapProvider

logger = logging.getLogger(__name__)

class OSMMapProvider(BaseMapProvider):
    """
    OpenStreetMap Fallback Provider for geocoding and location search when FortyGuard
    native spatial capabilities require fallback address resolution.
    """
    NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
    REVERSE_URL = "https://nominatim.openstreetmap.org/reverse"

    def provider_name(self) -> str:
        return "osm"

    async def get_map_visualization(
        self,
        latitude: float,
        longitude: float,
        timestamp: datetime,
        radius_meters: int = 500
    ) -> Dict[str, Any]:
        return {
            "provider": "osm",
            "supported": True,
            "latitude": latitude,
            "longitude": longitude,
            "timestamp": timestamp.isoformat(),
            "geojson": {},
            "visualization_type": "standard_osm_layer"
        }

    async def geocode(self, query: str) -> List[Dict[str, Any]]:
        headers = {"User-Agent": "SafeStage-ClimateApp/1.0"}
        params = {
            "q": query,
            "format": "json",
            "addressdetails": 1,
            "limit": 5
        }
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(self.NOMINATIM_URL, params=params, headers=headers)
                if resp.status_code == 200:
                    results = resp.json()
                    output = []
                    for r in results:
                        output.append({
                            "display_name": r.get("display_name"),
                            "latitude": float(r.get("lat")),
                            "longitude": float(r.get("lon")),
                            "type": r.get("type"),
                            "address": r.get("address", {})
                        })
                    return output
        except Exception as exc:
            logger.error(f"OSM geocoding error: {exc}")
        return []

    async def reverse_geocode(self, latitude: float, longitude: float) -> Optional[Dict[str, Any]]:
        headers = {"User-Agent": "SafeStage-ClimateApp/1.0"}
        params = {
            "lat": latitude,
            "lon": longitude,
            "format": "json"
        }
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(self.REVERSE_URL, params=params, headers=headers)
                if resp.status_code == 200:
                    return resp.json()
        except Exception as exc:
            logger.error(f"OSM reverse geocoding error: {exc}")
        return None

# Backward compatibility alias
OSMMapService = OSMMapProvider

