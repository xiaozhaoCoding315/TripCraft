import pytest

from app.agents.workflow import TravelPlannerWorkflow
from app.core.config import Settings
from app.models.travel import TravelPlanRequest, TravelerProfile


@pytest.mark.asyncio
async def test_workflow_generates_plan_without_external_keys():
    settings = Settings(dashscope_api_key=None, amap_api_key=None, max_critic_rounds=3)
    workflow = TravelPlannerWorkflow(settings=settings)
    request = TravelPlanRequest(
        destination="杭州",
        start_date="2026-07-01",
        days=2,
        budget=5000,
        departure_city="上海",
        travelers=TravelerProfile(adults=2, seniors=1, mobility_notes="腿脚不便"),
        interests=["西湖", "博物馆"],
    )
    plan, events = await workflow.plan(request)

    assert plan.destination == "杭州"
    assert len(plan.days) == 2
    assert plan.revisions
    assert events
    assert all(day.pace == "relaxed" for day in plan.days)
