"""
Tests for seed data service
"""

import pytest

from app.services.seed_data import DESTINATION_SEED_DATA, SeedDataService


class TestSeedData:
    """Test seed data content and structure"""

    def test_destinations_exist(self):
        """Should have at least 5 destinations"""
        assert len(DESTINATION_SEED_DATA) >= 5

    def test_hangzhou_has_data(self):
        """Hangzhou should have attractions and notes"""
        assert "杭州" in DESTINATION_SEED_DATA
        data = DESTINATION_SEED_DATA["杭州"]
        assert len(data["attractions"]) > 0
        assert len(data["travel_notes"]) > 0

    def test_beijing_has_data(self):
        """Beijing should have attractions and notes"""
        assert "北京" in DESTINATION_SEED_DATA
        data = DESTINATION_SEED_DATA["北京"]
        assert len(data["attractions"]) > 0

    def test_attraction_structure(self):
        """Attractions should have required fields"""
        for destination, data in DESTINATION_SEED_DATA.items():
            for attraction in data["attractions"]:
                assert "name" in attraction
                assert "type" in attraction
                assert "description" in attraction
                assert "tips" in attraction

    def test_travel_note_structure(self):
        """Travel notes should have required fields"""
        for destination, data in DESTINATION_SEED_DATA.items():
            for note in data["travel_notes"]:
                assert "title" in note
                assert "content" in note

    def test_all_popular_destinations_covered(self):
        """Should cover all popular Chinese destinations"""
        expected = ["杭州", "北京", "上海", "成都", "西安"]
        for dest in expected:
            assert dest in DESTINATION_SEED_DATA, f"Missing data for {dest}"


class TestSeedDataService:
    """Test seed data service logic"""

    def test_service_initialization(self):
        """Service should initialize correctly"""
        from app.core.config import Settings
        settings = Settings(dashscope_api_key=None, qdrant_url="http://localhost:6333")
        service = SeedDataService(settings)
        assert service.settings == settings
        assert service._seeded is False

    def test_service_skips_if_already_seeded(self):
        """Service should skip seeding if already done"""
        from app.core.config import Settings
        settings = Settings(dashscope_api_key=None, qdrant_url="http://localhost:6333")
        service = SeedDataService(settings)
        service._seeded = True
        # Should not raise any errors
        import asyncio
        asyncio.run(service.seed_if_empty())
