import pytest
from datetime import datetime, timedelta, timezone
from app.integrations.climate.mock import MockClimateProvider
from app.integrations.climate.fortyguard import FortyGuardProvider

@pytest.mark.asyncio
async def test_mock_provider_us_location():
    provider = MockClimateProvider()
    assert provider.is_location_supported(33.4484, -112.0740) is True  # Phoenix, US

    start_dt = datetime.now(timezone.utc)
    end_dt = start_dt + timedelta(hours=5)

    res = await provider.get_temperature_intelligence(33.4484, -112.0740, start_dt, end_dt)
    assert res["supported"] is True
    assert "summary" in res
    assert res["summary"]["avg_temperature_c"] > 0
    assert len(res["hourly_timeline"]) > 0

@pytest.mark.asyncio
async def test_unsupported_nigerian_location():
    provider = MockClimateProvider()
    # Lagos, Nigeria: Lat ~ 6.5244, Lon ~ 3.3792
    assert provider.is_location_supported(6.5244, 3.3792) is False

    start_dt = datetime.now(timezone.utc)
    end_dt = start_dt + timedelta(hours=5)

    res = await provider.get_temperature_intelligence(6.5244, 3.3792, start_dt, end_dt)
    assert res["supported"] is False
    assert res["message"] == "Hyperlocal climate intelligence is currently unavailable for this location."

@pytest.mark.asyncio
async def test_fortyguard_location_check():
    provider = FortyGuardProvider()
    assert provider.is_location_supported(33.4484, -112.0740) is True
    assert provider.is_location_supported(9.0765, 7.3986) is False  # Abuja, Nigeria

@pytest.mark.asyncio
async def test_mock_provider_ltm_endpoints():
    provider = MockClimateProvider()
    now = datetime.now(timezone.utc)

    seg = await provider.get_street_view_segmentation(33.4484, -112.0740, now)
    assert seg["supported"] is True
    assert "canopy_cover_pct" in seg
    assert "pavement_thermal_radiation_c" in seg

    env = await provider.get_environmental_parameters(33.4484, -112.0740, now)
    assert env["supported"] is True
    assert "wbgt_c" in env
    assert "uhi_intensity_c" in env

