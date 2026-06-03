from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func
from sqlalchemy.orm import selectinload
from datetime import datetime, timezone
import structlog

from app.db.database import get_db
from app.core.auth import get_current_user
from app.models.models import User, Topic, Roadmap, RoadmapStatus, UserBadge, Badge
from app.schemas.schemas import UserUpdate, UserResponse, TrendingTopicsResponse, TopicResponse
from app.agents.recommendation_agent import RecommendationAgent

logger = structlog.get_logger()

# ─── Users ────────────────────────────────────────────────────────────────────

users_router = APIRouter(prefix="/api/users", tags=["users"])


@users_router.get("/me", response_model=UserResponse)
async def get_me(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get authenticated user profile."""
    # Update last_active_at
    user.last_active_at = datetime.now(timezone.utc)
    return user


@users_router.patch("/me", response_model=UserResponse)
async def update_me(
    data: UserUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if data.name is not None:
        user.name = data.name
    if data.avatar_url is not None:
        user.avatar_url = data.avatar_url
    await db.flush()
    return user


@users_router.get("/me/badges")
async def get_my_badges(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(UserBadge)
        .where(UserBadge.user_id == user.id)
        .options(selectinload(UserBadge.badge))
        .order_by(UserBadge.earned_at.desc())
    )
    badges = result.scalars().all()
    return [
        {
            "id": ub.badge.id,
            "name": ub.badge.name,
            "description": ub.badge.description,
            "icon": ub.badge.icon,
            "xp_reward": ub.badge.xp_reward,
            "earned_at": ub.earned_at,
        }
        for ub in badges
    ]


@users_router.get("/me/streak")
async def get_streak(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get streak info and check/update if needed."""
    now = datetime.now(timezone.utc)
    last = user.last_active_at

    if last:
        days_since = (now.date() - last.date()).days
        if days_since == 1:
            user.streak_days += 1
        elif days_since > 1:
            user.streak_days = 1  # Reset
    else:
        user.streak_days = 1

    user.last_active_at = now
    await db.flush()

    return {"streak_days": user.streak_days, "xp_points": user.xp_points}


# ─── Topics ───────────────────────────────────────────────────────────────────

topics_router = APIRouter(prefix="/api/topics", tags=["topics"])


@topics_router.get("/trending", response_model=TrendingTopicsResponse)
async def get_trending_topics(
    db: AsyncSession = Depends(get_db),
    limit: int = 12,
):
    """Return most-searched topics for the landing page chips."""
    result = await db.execute(
        select(Topic)
        .order_by(Topic.search_count.desc())
        .limit(limit)
    )
    topics = result.scalars().all()

    # Seed defaults if DB is empty
    if not topics:
        defaults = [
            "Machine Learning", "Python", "React", "Cybersecurity",
            "Digital Marketing", "RAG Systems", "UI/UX Design", "Blockchain",
            "Finance", "Data Science", "Cloud Computing", "DevOps",
        ]
        topics = [
            Topic(title=t, slug=t.lower().replace(" ", "-"), search_count=100 - i)
            for i, t in enumerate(defaults)
        ]
        for t in topics:
            db.add(t)
        await db.flush()

    return TrendingTopicsResponse(topics=[
        TopicResponse(
            id=t.id, title=t.title, slug=t.slug,
            description=t.description, category=t.category,
            tags=t.tags, search_count=t.search_count,
        )
        for t in topics
    ])


@topics_router.get("/search")
async def search_topics(
    q: str,
    db: AsyncSession = Depends(get_db),
    limit: int = 8,
):
    """Autocomplete topic search."""
    result = await db.execute(
        select(Topic)
        .where(Topic.title.ilike(f"%{q}%"))
        .order_by(Topic.search_count.desc())
        .limit(limit)
    )
    topics = result.scalars().all()
    return [{"id": t.id, "title": t.title, "slug": t.slug} for t in topics]


# ─── Recommendations ──────────────────────────────────────────────────────────

recommendations_router = APIRouter(prefix="/api/recommendations", tags=["recommendations"])
recommendation_agent = RecommendationAgent()


@recommendations_router.get("/lesson/{lesson_id}")
async def get_lesson_recommendations(
    lesson_id: str,
    topic: str,
    level: str = "beginner",
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get fresh resource recommendations for a specific lesson."""
    recommendations = await recommendation_agent.recommend_for_lesson(
        db, lesson_id, topic, level
    )
    return {"recommendations": recommendations}


@recommendations_router.post("/refresh/{roadmap_id}")
async def refresh_roadmap_resources(
    roadmap_id: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Trigger a resource refresh for a specific roadmap."""
    result = await db.execute(
        select(Roadmap)
        .where(Roadmap.id == roadmap_id, Roadmap.user_id == user.id)
        .options(selectinload(Roadmap.topic))
    )
    roadmap = result.scalar_one_or_none()
    if not roadmap:
        raise HTTPException(status_code=404, detail="Roadmap not found")

    # Run in background
    async def run_refresh():
        async with get_db() as refresh_db:
            await recommendation_agent._refresh_roadmap(refresh_db, roadmap)

    background_tasks.add_task(run_refresh)
    return {"message": "Resource refresh started", "roadmap_id": roadmap_id}


# Webhook route for Clerk user events
webhook_router = APIRouter(prefix="/api/webhooks", tags=["webhooks"])


@webhook_router.post("/clerk")
async def clerk_webhook(
    db: AsyncSession = Depends(get_db),
):
    """Handle Clerk user.created / user.updated / user.deleted events."""
    # Implementation would use svix to verify and process events
    return {"received": True}
