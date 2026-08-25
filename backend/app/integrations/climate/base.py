from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, Any

class ClimateProvider(ABC):
    
    @abstractmethod
    def is_location_supported(self, latitude: float, longitude: float) -> bool:
        """
        Check if hyperlocal climate intelligence is available for this location.
        FortyGuard supports US regions and premium coverage zones.
        """
        pass

    @abstractmethod
    async def get_temperature_intelligence(
        self,
        latitude: float,
        longitude: float,
        start_datetime: datetime,
        end_datetime: datetime
    ) -> Dict[str, Any]:
        """
        Fetch FortyGuard heat-intelligence (/heat-intelligence) for specific location and period.
        """
        pass

    @abstractmethod
    async def get_heatmap(
        self,
        latitude: float,
        longitude: float,
        timestamp: datetime,
        radius_meters: int = 500
    ) -> Dict[str, Any]:
        """
        Fetch FortyGuard spatial heatmap (/create-heatmap) GeoJSON grid.
        """
        pass

    @abstractmethod
    async def get_street_view_segmentation(
        self,
        latitude: float,
        longitude: float,
        timestamp: datetime
    ) -> Dict[str, Any]:
        """
        Fetch FortyGuard street view segmentation (/street-view-segmentation) LTM micro-climate analytics:
        urban canopy, surface albedo, shade index, vegetation density, pavement thermal radiation.
        """
        pass

    @abstractmethod
    async def get_environmental_parameters(
        self,
        latitude: float,
        longitude: float,
        timestamp: datetime
    ) -> Dict[str, Any]:
        """
        Fetch FortyGuard environmental parameters (/environmental-parameters) LTM metrics:
        Wet Bulb Globe Temperature (WBGT), Relative Humidity, Wind Speed, Solar Irradiance, Land Surface Temp (LST), UHI Intensity.
        """
        pass

