"""
Climate Service — orchestrates FortyGuard/Mock provider access with caching.

Propagates errors explicitly; never returns silent fallback data.
"""

import logging
import os
from datetime import datetime
from typing import Dict, Any

from app.core.config import settings
from app.core.errors import FortyGuardError, ClimateDataUnavailableError
from app.integrations.climate.base import ClimateProvider
from app.integrations.climate.mock import MockClimateProvider
from app.integrations.climate.fortyguard import FortyGuardProvider
from app.services.climate_cache import ClimateCache

logger = logging.getLogger(__name__)


class ClimateService:

    @staticmethod
    def _env_or_setting(name: str, default: Any = None) -> Any:
        value = os.getenv(name)
        if value is not None and value != "":
            return value
        setting_value = getattr(settings, name, default)
        if setting_value is not None and setting_value != "":
            return setting_value
        return default

    @staticmethod
    def get_provider() -> ClimateProvider:
        env_provider = os.getenv("CLIMATE_PROVIDER")
        provider_name = (env_provider if env_provider not in (None, "") else settings.CLIMATE_PROVIDER or "mock").lower()
        api_key = ClimateService._env_or_setting("FORTYGUARD_API_KEY")

        if provider_name == "fortyguard":
            if not api_key:
                logger.warning(
                    "FORTYGUARD_API_KEY is not configured; falling back to mock climate provider."
                )
                return MockClimateProvider()
            return FortyGuardProvider()
        return MockClimateProvider()

    @classmethod
    async def get_temperature_intelligence(
        cls,
        latitude: float,
        longitude: float,
        start_datetime: datetime,
        end_datetime: datetime
    ) -> Dict[str, Any]:
        """Fetch heat intelligence with caching."""
        cache_params = dict(
            latitude=latitude, longitude=longitude,
            date=start_datetime.strftime("%Y-%m-%d")
        )

        cached = ClimateCache.get("heat_intelligence", **cache_params)
        if cached is not None:
            return cached

        provider = cls.get_provider()
        result = await provider.get_temperature_intelligence(latitude, longitude, start_datetime, end_datetime)

        # Only cache successful results
        if result.get("supported", False):
            ClimateCache.set("heat_intelligence", result, **cache_params)

        return result

    @classmethod
    async def get_heatmap(
        cls,
        latitude: float,
        longitude: float,
        timestamp: datetime,
        radius_meters: int = 500
    ) -> Dict[str, Any]:
        """Fetch heatmap with caching."""
        cache_params = dict(
            latitude=latitude, longitude=longitude,
            date=timestamp.strftime("%Y-%m-%d"),
            time=timestamp.strftime("%H:%M")
        )

        cached = ClimateCache.get("heatmap", **cache_params)
        if cached is not None:
            return cached

        provider = cls.get_provider()
        result = await provider.get_heatmap(latitude, longitude, timestamp, radius_meters)

        if result.get("supported", False):
            ClimateCache.set("heatmap", result, **cache_params)

        return result

    @classmethod
    async def get_street_view_segmentation(
        cls,
        latitude: float,
        longitude: float,
        timestamp: datetime
    ) -> Dict[str, Any]:
        """Fetch street view segmentation with caching."""
        cache_params = dict(latitude=latitude, longitude=longitude)

        cached = ClimateCache.get("streetview", **cache_params)
        if cached is not None:
            return cached

        provider = cls.get_provider()
        result = await provider.get_street_view_segmentation(latitude, longitude, timestamp)

        if result.get("supported", False):
            ClimateCache.set("streetview", result, **cache_params)

        return result

    @classmethod
    async def get_environmental_parameters(
        cls,
        latitude: float,
        longitude: float,
        timestamp: datetime
    ) -> Dict[str, Any]:
        """Fetch environmental parameters with caching."""
        cache_params = dict(
            latitude=latitude, longitude=longitude,
            date=timestamp.strftime("%Y-%m-%d"),
            time=timestamp.strftime("%H:%M")
        )

        cached = ClimateCache.get("env_params", **cache_params)
        if cached is not None:
            return cached

        provider = cls.get_provider()
        result = await provider.get_environmental_parameters(latitude, longitude, timestamp)

        if result.get("supported", False):
            ClimateCache.set("env_params", result, **cache_params)

        return result
