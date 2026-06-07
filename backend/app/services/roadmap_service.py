"""
Roadmap Service: Orchestrates the full roadmap generation pipeline.
Search → Rank → Curriculum → Persist → Stream status to client.
"""
from typing import Optional, AsyncIterator, Dict, Any
import asyncio
import json
import re
import structlog
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from sqlalchemy.orm import selectinload

from app.agents.search_agent import SearchAgent
from app.agents.ranking_agent import RankingAgent
from app.agents.curriculum_agent import CurriculumAgent
from app.models.models import (
    Topic, Roadmap, Module, Lesson, Resource, Quiz, Question, Project, User,
    RoadmapStatus, SkillLevel as ModelSkillLevel
)
from app.schemas.schemas import SkillLevel
from app.core.cache import cache_set, cache_get, cache_key

logger = structlog.get_logger()


class RoadmapService:

    def __init__(self):
        self.search_agent = SearchAgent()
        self.ranking_agent = RankingAgent()
        self.curriculum_agent = CurriculumAgent()

    async def create_roadmap_stream(
        self,
        db: AsyncSession,
        user: User,
        topic_query: str,
        level: SkillLevel,
    ) -> AsyncIterator[str]:
        """
        Full pipeline with SSE streaming status updates.
        Yields JSON-encoded GenerationStatus events.
        """
        roadmap_id = None
        try:
            # Step 1: Resolve or create topic
            yield self._sse("init", 5, "Analyzing your topic...")
            topic = await self._get_or_create_topic(db, topic_query)

            # Step 2: Create roadmap record (generating state)
            roadmap = Roadmap(
                user_id=user.id,
                topic_id=topic.id,
                title=f"Learning {topic.title} — {level.value.title()}",
                level=ModelSkillLevel(level.value),
                status=RoadmapStatus.GENERATING,
            )
            db.add(roadmap)
            await db.flush()
            roadmap_id = roadmap.id
            yield self._sse("created", 10, "Roadmap created, searching the web...", roadmap_id)

            # Step 3: Search for resources
            yield self._sse("searching", 20, "Scanning courses, videos, docs, and papers...", roadmap_id)
            raw_resources = await self.search_agent.search_all(topic.title, level.value)
            yield self._sse("searched", 35, f"Found {len(raw_resources)} resources. Evaluating quality...", roadmap_id)

            # Step 4: Rank resources
            scored_resources = self.ranking_agent.rank(raw_resources, max_per_type=4, max_total=25)
            yield self._sse("ranked", 45, f"Selected {len(scored_resources)} high-quality resources. Building curriculum...", roadmap_id)

            # Step 5: Generate curriculum with Claude
            async def status_callback(status: Dict[str, Any]):
                progress = status.get("progress", 50)
                message = status.get("message", "Generating...")
                yield self._sse("generating", progress, message, roadmap_id)

            curriculum = await self.curriculum_agent.generate_roadmap(
                topic=topic.title,
                level=level,
                resources=scored_resources,
                stream_callback=None,
            )
            yield self._sse("curriculum", 70, "Curriculum designed. Creating quizzes and projects...", roadmap_id)

            # Step 6: Persist to database
            yield self._sse("saving", 85, "Saving your personalized roadmap...", roadmap_id)
            await self._persist_curriculum(db, roadmap, curriculum)
            yield self._sse("complete", 100, "Your learning path is ready!", roadmap_id)

        except Exception as e:
            logger.error("Roadmap generation failed", error=str(e), exc_info=True)
            if roadmap_id:
                await db.execute(
                    update(Roadmap)
                    .where(Roadmap.id == roadmap_id)
                    .values(status=RoadmapStatus.ARCHIVED)
                )
            yield self._sse("error", 0, f"Generation failed: {str(e)}", roadmap_id)

    def _sse(self, step: str, progress: int, message: str, roadmap_id: str = "") -> str:
        data = json.dumps({
            "roadmap_id": roadmap_id,
            "status": step,
            "progress": progress,
            "current_step": step,
            "message": message,
        })
        return f"data: {data}\n\n"

    async def _get_or_create_topic(self, db: AsyncSession, query: str) -> Topic:
        """Find existing topic or create a new one."""
        normalized = query.strip().title()
        slug = re.sub(r"[^a-z0-9-]", "-", normalized.lower())
        slug = re.sub(r"-+", "-", slug).strip("-")

        result = await db.execute(select(Topic).where(Topic.slug == slug))
        topic = result.scalar_one_or_none()

        if not topic:
            topic = Topic(
                title=normalized,
                slug=slug,
                description=f"Learn {normalized} from scratch to mastery.",
                search_count=1,
            )
            db.add(topic)
            await db.flush()
        else:
            topic.search_count += 1

        return topic

    async def _persist_curriculum(
        self, db: AsyncSession, roadmap: Roadmap, curriculum: Dict[str, Any]
    ) -> None:
        """Persist full curriculum structure to PostgreSQL."""
        roadmap.title = curriculum.get("title", roadmap.title)
        roadmap.description = curriculum.get("description")
        roadmap.estimated_hours = curriculum.get("estimated_hours")
        roadmap.status = RoadmapStatus.ACTIVE

        for module_idx, module_data in enumerate(curriculum.get("modules", [])):
            module = Module(
                roadmap_id=roadmap.id,
                title=module_data["title"],
                description=module_data.get("description"),
                order=module_data.get("order", module_idx + 1),
                estimated_hours=module_data.get("estimated_hours"),
                is_unlocked=(module_idx == 0),  # First module unlocked
            )
            db.add(module)
            await db.flush()

            for lesson_idx, lesson_data in enumerate(module_data.get("lessons", [])):
                lesson = Lesson(
                    module_id=module.id,
                    title=lesson_data["title"],
                    summary=lesson_data.get("summary"),
                    objectives=lesson_data.get("objectives"),
                    key_concepts=lesson_data.get("key_concepts"),
                    difficulty=ModelSkillLevel(lesson_data.get("difficulty", roadmap.level.value)),
                    estimated_minutes=lesson_data.get("estimated_minutes", 30),
                    order=lesson_data.get("order", lesson_idx + 1),
                    xp_reward=lesson_data.get("xp_reward", 50),
                )
                db.add(lesson)
                await db.flush()

                # Persist resources
                for res_data in lesson_data.get("resources", []):
                    resource = Resource(
                        lesson_id=lesson.id,
                        resource_type=res_data["resource_type"],
                        title=res_data["title"],
                        url=res_data["url"],
                        description=res_data.get("description"),
                        author=res_data.get("author"),
                        platform=res_data.get("platform"),
                        duration_minutes=res_data.get("duration_minutes"),
                        is_free=res_data.get("is_free", True),
                        is_primary=res_data.get("is_primary", False),
                        thumbnail_url=res_data.get("thumbnail_url"),
                        authority_score=res_data.get("authority_score", 0),
                        popularity_score=res_data.get("popularity_score", 0),
                        freshness_score=res_data.get("freshness_score", 0),
                        completeness_score=res_data.get("completeness_score", 0),
                        community_score=res_data.get("community_score", 0),
                        composite_score=res_data.get("composite_score", 0),
                        resource_metadata=res_data.get("metadata", {}),
                    )
                    db.add(resource)

                # Persist quiz
                quiz_data = lesson_data.get("quiz")
                if quiz_data:
                    quiz = Quiz(
                        lesson_id=lesson.id,
                        passing_score=quiz_data.get("passing_score", 70),
                        time_limit_minutes=quiz_data.get("time_limit_minutes"),
                    )
                    db.add(quiz)
                    await db.flush()

                    for q_idx, q_data in enumerate(quiz_data.get("questions", [])):
                        question = Question(
                            quiz_id=quiz.id,
                            question=q_data["question"],
                            question_type=q_data.get("question_type", "multiple_choice"),
                            options=q_data.get("options"),
                            correct_answer=q_data["correct_answer"],
                            explanation=q_data.get("explanation"),
                            order=q_data.get("order", q_idx + 1),
                        )
                        db.add(question)

                # Persist project
                project_data = lesson_data.get("project")
                if project_data:
                    project = Project(
                        lesson_id=lesson.id,
                        title=project_data["title"],
                        description=project_data["description"],
                        requirements=project_data.get("requirements"),
                        deliverables=project_data.get("deliverables"),
                        hints=project_data.get("hints"),
                        xp_reward=project_data.get("xp_reward", 200),
                    )
                    db.add(project)

        await db.flush()
        logger.info("Curriculum persisted", roadmap_id=roadmap.id)

    async def get_roadmap_with_progress(
        self, db: AsyncSession, roadmap_id: str, user_id: str
    ) -> Optional[Roadmap]:
        """Load roadmap with all nested relationships."""
        cache_k = cache_key("roadmap", roadmap_id, user_id)
        cached = await cache_get(cache_k)
        if cached:
            return cached  # Return cached dict directly for serialization

        result = await db.execute(
            select(Roadmap)
            .where(Roadmap.id == roadmap_id, Roadmap.user_id == user_id)
            .options(
                selectinload(Roadmap.topic),
                selectinload(Roadmap.modules).selectinload(Module.lessons).selectinload(
                    Lesson.resources
                ),
                selectinload(Roadmap.modules).selectinload(Module.lessons).selectinload(
                    Lesson.quiz
                ).selectinload(Quiz.questions),
                selectinload(Roadmap.modules).selectinload(Module.lessons).selectinload(
                    Lesson.project
                ),
            )
        )
        return result.scalar_one_or_none()
