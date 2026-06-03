from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from sqlalchemy.orm import selectinload
from datetime import datetime, timezone
import structlog

from app.db.database import get_db
from app.core.auth import get_current_user
from app.models.models import (
    Lesson, Progress, Quiz, Question, QuizAttempt, User,
    LessonStatus, Module, Roadmap
)
from app.schemas.schemas import (
    ProgressUpdateRequest, ProgressResponse,
    QuizSubmitRequest, QuizResultResponse,
    TutorChatRequest, TutorChatResponse,
)
from app.agents.tutor_agent import TutorAgent
from app.agents.mastery_agent import MasteryAgent

logger = structlog.get_logger()


# ─── Progress Routes ──────────────────────────────────────────────────────────

progress_router = APIRouter(prefix="/api/progress", tags=["progress"])
mastery_agent = MasteryAgent()


@progress_router.post("", response_model=ProgressResponse)
async def update_progress(
    request: ProgressUpdateRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Update lesson progress and trigger mastery/unlock logic."""
    # Get or create progress record
    result = await db.execute(
        select(Progress).where(
            Progress.user_id == user.id,
            Progress.lesson_id == request.lesson_id,
        )
    )
    progress = result.scalar_one_or_none()

    if not progress:
        progress = Progress(
            user_id=user.id,
            lesson_id=request.lesson_id,
            status=request.status,
            started_at=datetime.now(timezone.utc) if request.status == LessonStatus.IN_PROGRESS else None,
        )
        db.add(progress)
    else:
        progress.status = request.status

    if request.time_spent_seconds:
        progress.time_spent_seconds += request.time_spent_seconds
    if request.notes:
        progress.notes = request.notes
    if request.status == LessonStatus.COMPLETED:
        progress.completed_at = datetime.now(timezone.utc)

    await db.flush()

    # Award XP if completing
    if request.status == LessonStatus.COMPLETED:
        lesson_result = await db.execute(select(Lesson).where(Lesson.id == request.lesson_id))
        lesson = lesson_result.scalar_one_or_none()
        if lesson:
            user.xp_points += lesson.xp_reward
            await _check_and_unlock_next(db, user.id, lesson)

    return progress


async def _check_and_unlock_next(db: AsyncSession, user_id: str, completed_lesson: Lesson):
    """Check if next module should be unlocked after lesson completion."""
    module_result = await db.execute(
        select(Module)
        .where(Module.id == completed_lesson.module_id)
        .options(selectinload(Module.lessons), selectinload(Module.roadmap))
    )
    module = module_result.scalar_one_or_none()
    if not module:
        return

    # Get mastery scores for all lessons in module
    lesson_ids = [l.id for l in module.lessons]
    progress_result = await db.execute(
        select(Progress).where(
            Progress.user_id == user_id,
            Progress.lesson_id.in_(lesson_ids),
        )
    )
    progress_records = {p.lesson_id: p for p in progress_result.scalars().all()}
    mastery_scores = [progress_records.get(lid, Progress()).mastery_score or 0 for lid in lesson_ids]

    should_unlock, reason = mastery_agent.should_unlock_next_module(mastery_scores)

    if should_unlock:
        # Unlock next module
        next_module_result = await db.execute(
            select(Module)
            .where(
                Module.roadmap_id == module.roadmap_id,
                Module.order == module.order + 1,
            )
        )
        next_module = next_module_result.scalar_one_or_none()
        if next_module and not next_module.is_unlocked:
            next_module.is_unlocked = True
            logger.info("Module unlocked", module_id=next_module.id, user_id=user_id)

        # Update roadmap completion
        all_modules_result = await db.execute(
            select(Module).where(Module.roadmap_id == module.roadmap_id)
        )
        all_modules = all_modules_result.scalars().all()
        unlocked_count = sum(1 for m in all_modules if m.is_unlocked)
        completion = unlocked_count / len(all_modules) if all_modules else 0

        await db.execute(
            update(Roadmap)
            .where(Roadmap.id == module.roadmap_id)
            .values(completion_percentage=completion * 100)
        )


# ─── Quiz Routes ──────────────────────────────────────────────────────────────

quiz_router = APIRouter(prefix="/api/quizzes", tags=["quizzes"])


@quiz_router.get("/{quiz_id}")
async def get_quiz(
    quiz_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get quiz questions (without answers)."""
    result = await db.execute(
        select(Quiz)
        .where(Quiz.id == quiz_id)
        .options(selectinload(Quiz.questions))
    )
    quiz = result.scalar_one_or_none()
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")

    # Return questions without correct_answer
    return {
        "id": quiz.id,
        "passing_score": quiz.passing_score,
        "time_limit_minutes": quiz.time_limit_minutes,
        "questions": [
            {
                "id": q.id,
                "question": q.question,
                "question_type": q.question_type,
                "options": q.options,
                "order": q.order,
            }
            for q in sorted(quiz.questions, key=lambda x: x.order)
        ],
    }


@quiz_router.post("/submit", response_model=QuizResultResponse)
async def submit_quiz(
    request: QuizSubmitRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Grade quiz submission and update mastery."""
    result = await db.execute(
        select(Quiz)
        .where(Quiz.id == request.quiz_id)
        .options(selectinload(Quiz.questions), selectinload(Quiz.lesson))
    )
    quiz = result.scalar_one_or_none()
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")

    # Grade answers
    correct = 0
    feedback = {}
    for question in quiz.questions:
        user_answer = request.answers.get(question.id, "")
        is_correct = user_answer.strip().lower() == question.correct_answer.strip().lower()
        if is_correct:
            correct += 1
        feedback[question.id] = {
            "correct": is_correct,
            "your_answer": user_answer,
            "correct_answer": question.correct_answer,
            "explanation": question.explanation,
        }

    total = len(quiz.questions)
    score = (correct / total * 100) if total > 0 else 0
    passed = score >= quiz.passing_score

    # Save attempt
    attempt = QuizAttempt(
        quiz_id=quiz.id,
        user_id=user.id,
        score=score,
        passed=passed,
        answers=request.answers,
        time_taken_seconds=request.time_taken_seconds,
    )
    db.add(attempt)
    await db.flush()

    # Update lesson mastery score
    progress_result = await db.execute(
        select(Progress).where(
            Progress.user_id == user.id,
            Progress.lesson_id == quiz.lesson_id,
        )
    )
    progress = progress_result.scalar_one_or_none()
    if progress:
        progress.mastery_score = max(progress.mastery_score, score / 100)

    # Award XP
    xp_earned = int((score / 100) * 75) if passed else 10
    user.xp_points += xp_earned

    return QuizResultResponse(
        attempt_id=attempt.id,
        score=score,
        passed=passed,
        passing_score=quiz.passing_score,
        xp_earned=xp_earned,
        feedback=feedback,
    )


# ─── Tutor Routes ─────────────────────────────────────────────────────────────

tutor_router = APIRouter(prefix="/api/tutor", tags=["tutor"])
tutor_agent = TutorAgent()


@tutor_router.post("/chat")
async def chat_with_tutor(
    request: TutorChatRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Stream tutor response via SSE."""
    # Get lesson context
    lesson_result = await db.execute(
        select(Lesson)
        .where(Lesson.id == request.lesson_id)
        .options(selectinload(Lesson.module).selectinload(Module.roadmap).selectinload(Roadmap.topic))
    )
    lesson = lesson_result.scalar_one_or_none()

    lesson_context = {}
    if lesson:
        lesson_context = {
            "title": lesson.title,
            "topic": lesson.module.roadmap.topic.title if lesson.module and lesson.module.roadmap else "",
            "level": lesson.difficulty.value,
            "key_concepts": lesson.key_concepts or [],
            "objectives": lesson.objectives or [],
        }

    async def generate():
        async for chunk in tutor_agent.chat_stream(
            message=request.message,
            lesson_context=lesson_context,
            conversation_history=request.conversation_history,
        ):
            import json
            yield f"data: {json.dumps({'chunk': chunk})}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@tutor_router.post("/suggestions")
async def get_suggestions(
    request: TutorChatRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get follow-up question suggestions."""
    lesson_result = await db.execute(select(Lesson).where(Lesson.id == request.lesson_id))
    lesson = lesson_result.scalar_one_or_none()
    lesson_title = lesson.title if lesson else "this lesson"

    suggestions = await tutor_agent.get_suggestions(request.message, lesson_title)
    return {"suggestions": suggestions}
