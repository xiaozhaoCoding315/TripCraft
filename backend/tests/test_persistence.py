"""
Tests for PostgreSQL persistence service
"""

import asyncio
import pytest
from app.core.config import Settings
from app.models.travel import AgentProgressEvent, MemoryItem, TravelPlanRequest
from app.services.persistence import PersistenceService
from app.agents.workflow import TravelPlannerWorkflow


def test_persistence_saves_plan_events_and_memory():
    async def _test():
        settings = Settings(dashscope_api_key=None, amap_api_key=None)
        store = PersistenceService(settings)
        await store.initialize(settings)

        request = TravelPlanRequest(destination="杭州", start_date="2026-07-01", days=1, interests=["西湖"])
        plan, events = await TravelPlannerWorkflow(settings=settings).plan(request)
        await store.save_plan(plan, request, events)
        await store.upsert_memory([MemoryItem(key="pace.preference", value="慢节奏", category="pace", source="request")])

        loaded = await store.get_plan(plan.plan_id)
        assert loaded is not None
        assert loaded["plan"].plan_id == plan.plan_id
        assert loaded["events"]
        assert (await store.list_plans())[0].plan_id == plan.plan_id
        assert (await store.list_memory())[0].key == "pace.preference"
        assert await store.delete_memory("pace.preference") is True

    asyncio.run(_test())


def test_append_events():
    async def _test():
        settings = Settings(dashscope_api_key=None, amap_api_key=None)
        store = PersistenceService(settings)
        await store.initialize(settings)
        request = TravelPlanRequest(destination="杭州", start_date="2026-07-01", days=1)
        plan, _ = await TravelPlannerWorkflow(settings=settings).plan(request)
        await store.save_plan(plan, request, [])
        await store.append_events(plan.plan_id, [AgentProgressEvent(agent="orchestrator", status="success", message="ok")])
        assert (await store.get_events(plan.plan_id))[0].message == "ok"

    asyncio.run(_test())
