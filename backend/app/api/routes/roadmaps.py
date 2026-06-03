from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from typing import List
import structlog

from app.db.database import get_db
from app.core.auth import get_current_user
from app.models.models import Roadmap, Module, Lesson, Progress, User, RoadmapStatus, LessonStatus
from app.schemas.schemas import (
    RoadmapCreateRequest, RoadmapSummary, RoadmapDetailResponse,
    ProgressUpdateRequest, ProgressResponse, DashboardStats, SkillLevel
)
from app.services.roadmap_service import RoadmapService
from app.core.cache import cache_key, cache_delete_pattern

logger = structlog.get_logger()
router = APIRouter(prefix="/api/roadmaps", tags=["roadmaps"])
roadmap_service = RoadmapService()


@router.post("/generate")
async def generate_roadmap(
    request: RoadmapCreateRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Stream roadmap generation via Server-Sent Events.
    Client connects and receives progress updates.
    """
    query = request.topic_query or ""
    level = request.level

    return StreamingResponse(
        roadmap_service.create_roadmap_stream(db, user, query, level),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("", response_model=List[RoadmapSummary])
async def list_roadmaps(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """List all roadmaps for the current user."""
    result = await db.execute(
        select(Roadmap)
        .where(Roadmap.user_id == user.id)
        .where(Roadmap.status != RoadmapStatus.ARCHIVED)
        .options(selectinload(Roadmap.topic))
        .order_by(Roadmap.created_at.desc())
    )
    roadmaps = result.scalars().all()
    return roadmaps


@router.get("/{roadmap_id}", response_model=RoadmapDetailResponse)
async def get_roadmap(
    roadmap_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get full roadmap with modules, lessons, and user progress."""
    roadmap = await roadmap_service.get_roadmap_with_progress(db, roadmap_id, user.id)
    if not roadmap:
        raise HTTPException(status_code=404, detail="Roadmap not found")

    # Inject progress data into lessons
    lesson_ids = [
        lesson.id
        for module in roadmap.modules
        for lesson in module.lessons
    ]
    if lesson_ids:
        progress_result = await db.execute(
            select(Progress).where(
                Progress.user_id == user.id,
                Progress.lesson_id.in_(lesson_ids)
            )
        )
        progress_map = {p.lesson_id: p for p in progress_result.scalars().all()}

        for module in roadmap.modules:
            for lesson in module.lessons:
                p = progress_map.get(lesson.id)
                lesson._status = p.status if p else LessonStatus.LOCKED
                lesson._mastery_score = p.mastery_score if p else 0.0
                lesson._time_spent_seconds = p.time_spent_seconds if p else 0

    return roadmap


@router.delete("/{roadmap_id}", status_code=204)
async def delete_roadmap(
    roadmap_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Roadmap).where(Roadmap.id == roadmap_id, Roadmap.user_id == user.id)
    )
    roadmap = result.scalar_one_or_none()
    if not roadmap:
        raise HTTPException(status_code=404, detail="Roadmap not found")

    roadmap.status = RoadmapStatus.ARCHIVED
    await cache_delete_pattern(f"roadmap:{roadmap_id}:*")


@router.get("/dashboard/stats", response_model=DashboardStats)
async def get_dashboard_stats(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Aggregate stats for the dashboard."""
    # Completed lessons
    completed_result = await db.execute(
        select(func.count(Progress.id)).where(
            Progress.user_id == user.id,
            Progress.status == LessonStatus.COMPLETED,
        )
    )
    completed_count = completed_result.scalar() or 0

    # Total time
    time_result = await db.execute(
        select(func.sum(Progress.time_spent_seconds)).where(
            Progress.user_id == user.id
        )
    )
    total_seconds = time_result.scalar() or 0
    total_hours = round(total_seconds / 3600, 1)

    # Active roadmaps
    roadmap_result = await db.execute(
        select(func.count(Roadmap.id)).where(
            Roadmap.user_id == user.id,
            Roadmap.status == RoadmapStatus.ACTIVE,
        )
    )
    active_roadmaps = roadmap_result.scalar() or 0

    # Avg mastery
    mastery_result = await db.execute(
        select(func.avg(Progress.mastery_score)).where(
            Progress.user_id == user.id,
            Progress.mastery_score > 0,
        )
    )
    avg_mastery = float(mastery_result.scalar() or 0)

    # Badge count
    from app.models.models import UserBadge
    badge_result = await db.execute(
        select(func.count(UserBadge.id)).where(UserBadge.user_id == user.id)
    )
    badge_count = badge_result.scalar() or 0

    return DashboardStats(
        total_lessons_completed=completed_count,
        total_hours_learned=total_hours,
        current_streak=user.streak_days,
        xp_points=user.xp_points,
        roadmaps_in_progress=active_roadmaps,
        average_mastery_score=round(avg_mastery, 2),
        badges_earned=badge_count,
    )
