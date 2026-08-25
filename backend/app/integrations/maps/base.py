from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, Any, List, Optional

class BaseMapProvider(ABC):
    """
    Abstract Base Class for SafeStage Mapping & Visualization Layer.
    Ensures modularity so FortyGuard native maps can be prioritized while allowing
    additional geographic providers to be plugged in if needed.
    """

    @abstractmethod
    def provider_name(self) -> str:
        pass

    @abstractmethod
    async def get_map_visualization(
        self,
        latitude: float,
        longitude: float,
        timestamp: datetime,
        radius_meters: int = 500
    ) -> Dict[str, Any]:
        """
        Retrieves map visualization payload (GeoJSON micro-zones, thermal layers).
        """
        pass

    @abstractmethod
    async def geocode(self, query: str) -> List[Dict[str, Any]]:
        """
        Geocodes venue/address into lat/lon coordinates.
        """
        pass

    @abstractmethod
    async def reverse_geocode(self, latitude: float, longitude: float) -> Optional[Dict[str, Any]]:
        """
        Reverse geocodes lat/lon into location metadata.
        """
        pass
