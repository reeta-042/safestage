import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from app.integrations.maps.base import BaseMapProvider
from app.services.climate_service import ClimateService
from app.integrations.maps.osm import OSMMapProvider

logger = logging.getLogger(__name__)

class FortyGuardMapProvider(BaseMapProvider):
    """
    FortyGuard Native Map & Visualization Provider.
    Prioritizes FortyGuard's native spatial heatmaps and micro-climate visualization capabilities.
    Delegates address geocoding to secondary fallback when string query resolution is needed.
    """

    def provider_name(self) -> str:
        return "fortyguard"

    async def get_map_visualization(
        self,
        latitude: float,
        longitude: float,
        timestamp: datetime,
        radius_meters: int = 500
    ) -> Dict[str, Any]:
        """
        Fetches FortyGuard native heatmap visualization.
        """
        heatmap_res = await ClimateService.get_heatmap(
            latitude=latitude,
            longitude=longitude,
            timestamp=timestamp,
            radius_meters=radius_meters
        )
        return {
            "provider": "fortyguard",
            "supported": heatmap_res.get("supported", True),
            "latitude": latitude,
            "longitude": longitude,
            "timestamp": timestamp.isoformat(),
            "geojson": heatmap_res.get("geojson", {}),
            "zones": heatmap_res.get("zones", []),
            "visualization_type": "fortyguard_hyperlocal_thermal_grid"
        }

    async def geocode(self, query: str) -> List[Dict[str, Any]]:
        # Fallback to secondary provider for query text resolution
        return await OSMMapProvider().geocode(query)

    async def reverse_geocode(self, latitude: float, longitude: float) -> Optional[Dict[str, Any]]:
        return await OSMMapProvider().reverse_geocode(latitude, longitude)
