"""
LearnOS AI — Test Suite
Tests for agents, API routes, and services.
Run: pytest tests/ -v
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from typing import List


# ─── Test: Ranking Agent ──────────────────────────────────────────────────────

class TestRankingAgent:
    def setup_method(self):
        from app.agents.ranking_agent import RankingAgent
        from app.agents.search_agent import RawResource
        from app.schemas.schemas import ResourceType
        self.agent = RankingAgent()
        self.ResourceType = ResourceType
        self.RawResource = RawResource

    def _make_resource(self, url="https://example.com", rtype=None, platform="YouTube"):
        return self.RawResource(
            title="Test Resource",
            url=url,
            resource_type=rtype or self.ResourceType.VIDEO,
            description="A test resource",
            platform=platform,
            is_free=True,
        )

    def test_deduplicates_same_url(self):
        r1 = self._make_resource("https://youtube.com/watch?v=abc")
        r2 = self._make_resource("https://youtube.com/watch?v=abc")
        result = self.agent.rank([r1, r2])
        assert len(result) == 1

    def test_deduplicates_trailing_slash(self):
        r1 = self._make_resource("https://example.com/course/")
        r2 = self._make_resource("https://example.com/course")
        result = self.agent.rank([r1, r2])
        assert len(result) == 1

    def test_composite_score_range(self):
        resources = [self._make_resource(f"https://example.com/{i}") for i in range(5)]
        result = self.agent.rank(resources)
        for r in result:
            assert 0.0 <= r.composite_score <= 1.0

    def test_high_authority_platform_scores_high(self):
        from app.agents.ranking_agent import ScoredResource
        mdn = self._make_resource("https://developer.mozilla.org/guide", platform="MDN")
        blog = self._make_resource("https://random-blog.com/post", platform="Unknown")
        scored = [self.agent._score_resource(r) for r in [mdn, blog]]
        assert scored[0].authority_score > scored[1].authority_score

    def test_marks_primary_resources(self):
        resources = [
            self._make_resource(f"https://example{i}.com", rtype=self.ResourceType.VIDEO)
            for i in range(3)
        ]
        result = self.agent.rank(resources)
        primary_count = sum(1 for r in result if r.is_primary)
        assert primary_count >= 1

    def test_max_total_cap(self):
        resources = [self._make_resource(f"https://unique{i}.com") for i in range(30)]
        result = self.agent.rank(resources, max_total=10)
        assert len(result) <= 10

    def test_freshness_score_recent_is_high(self):
        from app.agents.search_agent import RawResource
        recent = self._make_resource()
        recent.published_date = "2024-10-01"
        old = self._make_resource("https://old.com")
        old.published_date = "2018-01-01"
        recent_scored = self.agent._score_resource(recent)
        old_scored = self.agent._score_resource(old)
        assert recent_scored.freshness_score > old_scored.freshness_score


# ─── Test: Mastery Agent ──────────────────────────────────────────────────────

class TestMasteryAgent:
    def setup_method(self):
        from app.agents.mastery_agent import MasteryAgent
        self.agent = MasteryAgent()

    def test_high_quiz_score_gives_high_mastery(self):
        result = self.agent.evaluate_lesson_mastery(
            quiz_attempts=[{"score": 95}],
            time_spent_seconds=1800,
            estimated_minutes=30,
            has_project=False,
        )
        assert result.composite >= 0.70
        assert result.is_mastered

    def test_failed_quiz_gives_low_mastery(self):
        result = self.agent.evaluate_lesson_mastery(
            quiz_attempts=[{"score": 30}],
            time_spent_seconds=300,
            estimated_minutes=30,
            has_project=False,
        )
        assert result.quiz_score < 0.50

    def test_no_attempts_gives_zero_quiz_score(self):
        result = self.agent.evaluate_lesson_mastery(
            quiz_attempts=[],
            time_spent_seconds=1800,
            estimated_minutes=30,
            has_project=False,
        )
        assert result.quiz_score == 0.0

    def test_module_unlock_requires_80_percent_completion(self):
        # 4/5 lessons mastered (80%)
        scores = [0.85, 0.90, 0.75, 0.80, 0.30]
        should_unlock, reason = self.agent.should_unlock_next_module(scores)
        assert should_unlock

    def test_module_stays_locked_if_too_few_completed(self):
        # Only 2/5 (40%) mastered
        scores = [0.85, 0.90, 0.20, 0.10, 0.05]
        should_unlock, reason = self.agent.should_unlock_next_module(scores)
        assert not should_unlock

    def test_skill_level_expert(self):
        scores = [0.95, 0.92, 0.98, 0.91, 0.94]
        level = self.agent.compute_skill_level(scores)
        assert level == "expert"

    def test_skill_level_beginner_on_low_scores(self):
        scores = [0.30, 0.25, 0.40]
        level = self.agent.compute_skill_level(scores)
        assert level == "beginner"

    def test_adaptive_recommendation_advance(self):
        rec = self.agent.get_adaptive_recommendation(0.95, "Intro to ML")
        assert rec["action"] == "advance"

    def test_adaptive_recommendation_restart(self):
        rec = self.agent.get_adaptive_recommendation(0.30, "Intro to ML")
        assert rec["action"] == "restart"


# ─── Test: API Health ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_health_endpoint():
    from fastapi.testclient import TestClient
    with patch("app.core.cache.get_redis") as mock_redis:
        mock_r = AsyncMock()
        mock_r.ping = AsyncMock()
        mock_redis.return_value = mock_r

        from app.main import app
        client = TestClient(app)
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"


# ─── Test: Schemas ────────────────────────────────────────────────────────────

class TestSchemas:
    def test_topic_search_strips_whitespace(self):
        from app.schemas.schemas import TopicSearchRequest
        req = TopicSearchRequest(query="  Python  ")
        assert req.query == "Python"

    def test_topic_search_rejects_empty(self):
        from app.schemas.schemas import TopicSearchRequest
        import pydantic
        with pytest.raises(pydantic.ValidationError):
            TopicSearchRequest(query="")

    def test_roadmap_create_requires_topic(self):
        from app.schemas.schemas import RoadmapCreateRequest
        import pydantic
        with pytest.raises((pydantic.ValidationError, ValueError)):
            RoadmapCreateRequest()  # neither topic_id nor topic_query


# ─── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()
