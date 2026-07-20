"""
Tests for travel planning workflow
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.agents.workflow import TravelPlannerWorkflow
from app.models.travel import TravelPlanRequest, TravelerProfile
from app.core.config import Settings


class TestTravelPlannerWorkflow:
    """Test travel planner workflow initialization and structure"""

    @pytest.fixture
    def settings(self):
        return Settings(
            dashscope_api_key=None,  # Disable LLM for tests
            qdrant_url="http://localhost:6333",
            amap_api_key=None,
        )

    @pytest.fixture
    def workflow(self, settings):
        return TravelPlannerWorkflow(settings=settings)

    def test_workflow_initialization(self, workflow):
        """Workflow should initialize with correct agents"""
        assert workflow.amap is not None
        assert workflow.rag is not None
        assert workflow.llm is not None
        assert workflow.graph is not None

    def test_workflow_has_graph_nodes(self, workflow):
        """Workflow graph should have all required nodes"""
        graph = workflow.graph
        # The compiled graph should have nodes
        assert graph is not None

    def test_safe_date_valid(self, workflow):
        """Should parse valid date string"""
        result = workflow._safe_date("2024-01-15")
        assert result is not None
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 15

    def test_safe_date_invalid(self, workflow):
        """Should return None for invalid date"""
        result = workflow._safe_date("invalid-date")
        assert result is None

    def test_summarize_weather_with_data(self, workflow):
        """Should summarize weather data correctly"""
        weather = {
            "city": "杭州",
            "casts": [
                {
                    "dayweather": "晴",
                    "nighttemp": "10",
                    "daytemp": "20",
                }
            ],
        }
        summary = workflow._summarize_weather(weather)
        assert "杭州" in summary
        assert "晴" in summary

    def test_summarize_weather_empty(self, workflow):
        """Should handle empty weather data"""
        summary = workflow._summarize_weather({"casts": []})
        assert "未获取" in summary


class TestTravelPlanRequest:
    """Test travel plan request model"""

    def test_create_basic_request(self):
        """Should create a basic travel plan request"""
        request = TravelPlanRequest(
            destination="杭州",
            start_date="2024-03-15",
            days=3,
            budget=5000,
        )
        assert request.destination == "杭州"
        assert request.days == 3
        assert request.budget == 5000

    def test_request_with_travelers(self):
        """Should create request with traveler info"""
        travelers = TravelerProfile(
            adults=2,
            children=1,
            seniors=0,
            mobility_notes="腿脚不便",
        )
        request = TravelPlanRequest(
            destination="北京",
            start_date="2024-04-01",
            days=5,
            travelers=travelers,
        )
        assert request.travelers.adults == 2
        assert request.travelers.children == 1
        assert "腿脚不便" in request.travelers.mobility_notes

    def test_request_with_interests(self):
        """Should create request with interests"""
        request = TravelPlanRequest(
            destination="成都",
            start_date="2024-05-01",
            days=3,
            interests=["美食", "大熊猫", "文化"],
        )
        assert len(request.interests) == 3
        assert "美食" in request.interests


class TestReviewPlan:
    """Test critic agent review logic"""

    @pytest.fixture
    def workflow(self):
        return TravelPlannerWorkflow()

    def test_review_seniors_too_many_attractions(self, workflow):
        """Should flag too many attractions for seniors"""
        from app.models.travel import TravelPlan, DayPlan, ItineraryItem

        plan = TravelPlan(
            destination="杭州",
            version=1,
            days=[
                DayPlan(
                    day=1,
                    title="Day 1",
                    items=[
                        ItineraryItem(time="09:00", type="attraction", title="景点1", description="desc"),
                        ItineraryItem(time="11:00", type="attraction", title="景点2", description="desc"),
                        ItineraryItem(time="13:00", type="attraction", title="景点3", description="desc"),
                    ],
                )
            ],
        )
        request = TravelPlanRequest(
            destination="杭州",
            start_date="2024-03-15",
            days=1,
            travelers=TravelerProfile(adults=1, seniors=1),
        )

        comments = workflow._review_plan(plan, request)
        # Should have warning about too many attractions for seniors
        assert any("老人" in c.message or "景点数量" in c.message for c in comments)

    def test_review_budget_overrun(self, workflow):
        """Should flag budget overrun"""
        from app.models.travel import TravelPlan, DayPlan, ItineraryItem

        plan = TravelPlan(
            destination="杭州",
            version=1,
            days=[
                DayPlan(
                    day=1,
                    title="Day 1",
                    items=[
                        ItineraryItem(
                            time="09:00",
                            type="hotel",
                            title="豪华酒店",
                            description="五星级豪华酒店",
                            cost=5000
                        ),
                    ],
                    estimated_cost=5000,
                )
            ],
            total_estimated_cost=5000,
        )
        request = TravelPlanRequest(
            destination="杭州",
            start_date="2024-03-15",
            days=1,
            budget=3000,
        )

        comments = workflow._review_plan(plan, request)
        # Check that budget warning is present (message contains "预算" or "超过")
        budget_comments = [c for c in comments if "预算" in c.message or "超过" in c.message]
        assert len(budget_comments) > 0, f"Expected budget warning but got: {[c.message for c in comments]}"


class TestAttractionAgentRacing:
    """Test attraction agent racing (FIRST_COMPLETED) strategy"""

    @pytest.fixture
    def settings(self):
        return Settings(
            dashscope_api_key=None,
            qdrant_url="http://localhost:6333",
            amap_api_key=None,
        )

    @pytest.fixture
    def workflow(self, settings):
        return TravelPlannerWorkflow(settings=settings)

    @pytest.mark.asyncio
    async def test_racing_returns_results(self, workflow):
        """Attraction agent should return results even in degraded mode"""
        request = TravelPlanRequest(
            destination="杭州",
            start_date="2026-07-01",
            days=2,
            interests=["西湖", "美食"],
        )
        initial = {
            "request": request,
            "context": {"memory": []},
            "events": [],
            "revision_round": 0,
            "critique": {},
        }
        result = await workflow._attraction_agent(initial)
        assert "attractions" in result["context"]
        assert "rag_notes" in result["context"]
        assert isinstance(result["context"]["attractions"], list)
        assert isinstance(result["context"]["rag_notes"], list)

    @pytest.mark.asyncio
    async def test_racing_handles_exception_gracefully(self, settings):
        """Racing strategy should degrade gracefully if one path raises"""
        workflow = TravelPlannerWorkflow(settings=settings)
        # Mock _safe_search_attractions to raise
        async def failing_search(city, query):
            raise RuntimeError("API down")
        workflow._safe_search_attractions = failing_search

        request = TravelPlanRequest(
            destination="杭州",
            start_date="2026-07-01",
            days=1,
        )
        initial = {
            "request": request,
            "context": {"memory": []},
            "events": [],
            "revision_round": 0,
            "critique": {},
        }
        result = await workflow._attraction_agent(initial)
        # Should still have fallback data
        assert "attractions" in result["context"]
        assert len(result["context"]["attractions"]) > 0  # fallback POIs
