from datetime import datetime, timedelta, timezone
import pytest
from app.services.simulation_service import SimulationService

@pytest.mark.asyncio
async def test_run_simulation():
    now = datetime.now(timezone.utc)
    sc_a = "Friday afternoon at 2 PM with one cooling station and 10% shade."
    sc_b = "Saturday evening at 5 PM with four cooling stations and 40% shade."

    res = await SimulationService.run_simulation(
        event_id="test_event",
        event_name="Phoenix Summer Beats",
        event_lat=33.4484,
        event_lon=-112.0740,
        attendance=5000,
        start_datetime=now,
        end_datetime=now + timedelta(hours=4),
        scenario_a=sc_a,
        scenario_b=sc_b,
        is_supported=True
    )

    assert res.supported is True
    assert res.recommended in ["scenario_a", "scenario_b"]
    assert res.scenario_a is not None
    assert res.scenario_b is not None
    assert res.score_difference >= 0
    assert len(res.tactical_action_plan) > 0

@pytest.mark.asyncio
async def test_run_simulation_natural_language():
    now = datetime.now(timezone.utc)
    res = await SimulationService.run_simulation(
        event_id="test_event",
        event_name="Family Summer Fest",
        event_lat=33.4484,
        event_lon=-112.0740,
        attendance=4000,
        start_datetime=now,
        end_datetime=now + timedelta(hours=4),
        scenario_a="Keep the event at 2 PM with standard shade.",
        scenario_b="Move the event to 6 PM with five cooling misting stations.",
        query="Compare the two plans for 2,000 children.",
        history=[{"role": "user", "content": "How do we protect kids from 42C heat?"}],
        is_supported=True
    )

    assert res.supported is True
    assert res.scenario_a is not None
    assert res.scenario_b is not None
    assert len(res.tactical_action_plan) > 0
