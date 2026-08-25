import pytest
from datetime import datetime, timezone
from app.integrations.maps.factory import MapService
from app.integrations.maps.fortyguard_map import FortyGuardMapProvider
from app.integrations.maps.osm import OSMMapProvider

@pytest.mark.asyncio
async def test_map_service_provider_selection():
    provider = MapService.get_provider()
    assert isinstance(provider, FortyGuardMapProvider)
    assert provider.provider_name() == "fortyguard"

@pytest.mark.asyncio
async def test_fortyguard_map_visualization():
    provider = FortyGuardMapProvider()
    now = datetime.now(timezone.utc)
    res = await provider.get_map_visualization(33.4484, -112.0740, now)
    assert res["provider"] == "fortyguard"
    assert "geojson" in res
    assert res["visualization_type"] == "fortyguard_hyperlocal_thermal_grid"

@pytest.mark.asyncio
async def test_osm_fallback_provider():
    provider = OSMMapProvider()
    assert provider.provider_name() == "osm"
    now = datetime.now(timezone.utc)
    res = await provider.get_map_visualization(33.4484, -112.0740, now)
    assert res["provider"] == "osm"
