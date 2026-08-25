from app.core.config import settings
from app.integrations.maps.base import BaseMapProvider
from app.integrations.maps.fortyguard_map import FortyGuardMapProvider
from app.integrations.maps.osm import OSMMapProvider

class MapService:

    @staticmethod
    def get_provider() -> BaseMapProvider:
        if settings.MAP_PROVIDER.lower() == "osm":
            return OSMMapProvider()
        return FortyGuardMapProvider()
