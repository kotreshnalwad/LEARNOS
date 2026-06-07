"""
Recommendation Agent: Monitors existing roadmaps for stale resources
and replaces them with fresher, higher-quality alternatives.
Runs as a scheduled background job (Celery or APScheduler).
"""
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone, timedelta
import asyncio
import structlog
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from sqlalchemy.orm import selectinload

from app.agents.search_agent import SearchAgent
from app.agents.ranking_agent import RankingAgent, ScoredResource
from app.models.models import Resource, Lesson, Roadmap, RoadmapStatus
from app.schemas.schemas import ResourceType

logger = structlog.get_logger()

# Resources older than this threshold trigger a refresh check
STALENESS_THRESHOLD_DAYS = 90
# Minimum score improvement required to swap a resource
MIN_SCORE_IMPROVEMENT = 0.15


class RecommendationAgent:
    """
    Scans roadmaps for outdated resources and replaces them
    with fresher alternatives discovered via live web search.
    """

    def __init__(self):
        self.search_agent = SearchAgent()
        self.ranking_agent = RankingAgent()

    async def refresh_stale_roadmaps(self, db: AsyncSession, max_roadmaps: int = 10) -> Dict[str, Any]:
        """
        Entry point for scheduled job.
        Finds roadmaps with old resources and refreshes them.
        """
        cutoff = datetime.now(timezone.utc) - timedelta(days=STALENESS_THRESHOLD_DAYS)

        result = await db.execute(
            select(Roadmap)
            .where(
                Roadmap.status == RoadmapStatus.ACTIVE,
                Roadmap.last_updated_at < cutoff,
            )
            .order_by(Roadmap.last_updated_at.asc())
            .limit(max_roadmaps)
            .options(
                selectinload(Roadmap.topic),
                selectinload(Roadmap.modules).selectinload(
                    __import__('app.models.models', fromlist=['Module']).Module.lessons
                ).selectinload(
                    __import__('app.models.models', fromlist=['Lesson']).Lesson.resources
                ),
            )
        )
        roadmaps = result.scalars().all()

        stats = {"roadmaps_checked": 0, "resources_replaced": 0, "errors": 0}

        for roadmap in roadmaps:
            try:
                replaced = await self._refresh_roadmap(db, roadmap)
                stats["roadmaps_checked"] += 1
                stats["resources_replaced"] += replaced

                # Update last_updated_at
                await db.execute(
                    update(Roadmap)
                    .where(Roadmap.id == roadmap.id)
                    .values(last_updated_at=datetime.now(timezone.utc))
                )
                await db.flush()

            except Exception as e:
                logger.error("Roadmap refresh failed", roadmap_id=roadmap.id, error=str(e))
                stats["errors"] += 1

        logger.info("Recommendation cycle complete", **stats)
        return stats

    async def _refresh_roadmap(self, db: AsyncSession, roadmap: Roadmap) -> int:
        """Refresh resources for a single roadmap. Returns count of replaced resources."""
        topic = roadmap.topic.title
        level = roadmap.level.value
        replaced = 0

        logger.info("Refreshing roadmap", roadmap_id=roadmap.id, topic=topic)

        # Search for fresh resources on this topic
        raw_resources = await self.search_agent.search_all(topic, level)
        fresh_resources = self.ranking_agent.rank(raw_resources, max_per_type=5, max_total=30)

        # Build lookup: (resource_type, normalized_platform) -> best fresh resource
        fresh_by_type: Dict[ResourceType, List[ScoredResource]] = {}
        for r in fresh_resources:
            fresh_by_type.setdefault(r.resource_type, []).append(r)

        # Collect all existing resources across modules/lessons
        for module in roadmap.modules:
            for lesson in module.lessons:
                for resource in lesson.resources:
                    better = self._find_better_resource(resource, fresh_by_type)
                    if better:
                        await self._replace_resource(db, resource, better)
                        replaced += 1

        return replaced

    def _find_better_resource(
        self,
        existing: Resource,
        fresh_by_type: Dict[ResourceType, List[ScoredResource]],
    ) -> Optional[ScoredResource]:
        """
        Find a fresh resource that's meaningfully better than the existing one.
        """
        candidates = fresh_by_type.get(existing.resource_type, [])

        for candidate in candidates:
            # Skip if it's the same URL
            if self._same_url(candidate.url, existing.url):
                continue

            # Only replace if score improvement is significant
            score_delta = candidate.composite_score - existing.composite_score
            if score_delta >= MIN_SCORE_IMPROVEMENT:
                logger.info(
                    "Better resource found",
                    existing_url=existing.url[:60],
                    new_url=candidate.url[:60],
                    improvement=round(score_delta, 3),
                )
                return candidate

        return None

    def _same_url(self, url1: str, url2: str) -> bool:
        """Check if two URLs resolve to the same resource."""
        def normalize(u: str) -> str:
            import re
            u = u.lower().rstrip("/")
            u = re.sub(r"https?://(?:www\.)?", "", u)
            u = re.sub(r"\?.*$", "", u)
            return u
        return normalize(url1) == normalize(url2)

    async def _replace_resource(
        self, db: AsyncSession, existing: Resource, replacement: ScoredResource
    ) -> None:
        """Swap an existing resource with a fresher one in-place."""
        await db.execute(
            update(Resource)
            .where(Resource.id == existing.id)
            .values(
                title=replacement.title,
                url=replacement.url,
                description=replacement.description,
                author=replacement.author,
                platform=replacement.platform,
                duration_minutes=replacement.duration_minutes,
                is_free=replacement.is_free,
                thumbnail_url=replacement.thumbnail_url,
                authority_score=replacement.authority_score,
                popularity_score=replacement.popularity_score,
                freshness_score=replacement.freshness_score,
                completeness_score=replacement.completeness_score,
                community_score=replacement.community_score,
                composite_score=replacement.composite_score,
                resource_metadata=replacement.metadata,
            )
        )

    async def recommend_for_lesson(
        self, db: AsyncSession, lesson_id: str, topic: str, level: str
    ) -> List[Dict[str, Any]]:
        """
        On-demand: return top 5 fresh resources for a specific lesson.
        Used by the lesson page "Find better resources" feature.
        """
        result = await db.execute(
            select(Lesson).where(Lesson.id == lesson_id).options(selectinload(Lesson.resources))
        )
        lesson = result.scalar_one_or_none()
        if not lesson:
            return []

        existing_urls = {r.url for r in lesson.resources}
        raw = await self.search_agent.search_all(f"{topic} {lesson.title}", level)
        scored = self.ranking_agent.rank(raw, max_per_type=3, max_total=10)

        recommendations = []
        for r in scored:
            if r.url not in existing_urls:
                recommendations.append({
                    "resource_type": r.resource_type.value,
                    "title": r.title,
                    "url": r.url,
                    "description": r.description,
                    "platform": r.platform,
                    "duration_minutes": r.duration_minutes,
                    "is_free": r.is_free,
                    "composite_score": round(r.composite_score, 3),
                    "thumbnail_url": r.thumbnail_url,
                })
            if len(recommendations) >= 5:
                break

        return recommendations
