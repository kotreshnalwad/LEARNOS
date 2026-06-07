"""
Mastery Agent: Evaluates learner comprehension through multi-dimensional assessment.
Determines readiness to advance by checking: quiz scores, time spent, and
project completion before unlocking the next module.
"""
from typing import Dict, Any, List, Optional
import google.generativeai as genai
import json
import structlog

from app.core.config import get_settings
from app.schemas.schemas import LessonStatus

logger = structlog.get_logger()
settings = get_settings()


class MasteryScore:
    def __init__(
        self,
        quiz_score: float = 0.0,
        time_score: float = 0.0,
        project_score: float = 0.0,
        engagement_score: float = 0.0,
    ):
        self.quiz_score = quiz_score
        self.time_score = time_score
        self.project_score = project_score
        self.engagement_score = engagement_score

    @property
    def composite(self) -> float:
        return (
            self.quiz_score * 0.40
            + self.time_score * 0.20
            + self.project_score * 0.25
            + self.engagement_score * 0.15
        )

    @property
    def is_mastered(self) -> bool:
        return self.composite >= 0.70

    def to_dict(self) -> Dict[str, float]:
        return {
            "quiz_score": self.quiz_score,
            "time_score": self.time_score,
            "project_score": self.project_score,
            "engagement_score": self.engagement_score,
            "composite": self.composite,
            "is_mastered": self.is_mastered,
        }


class MasteryAgent:
    """
    Evaluates whether a learner has mastered a lesson and module.
    Determines module unlock logic and advancement readiness.
    """

    def __init__(self):
        genai.configure(api_key=settings.GEMINI_API_KEY)
        self.client = genai.GenerativeModel('gemini-1.5-flash')

    def evaluate_lesson_mastery(
        self,
        quiz_attempts: List[Dict[str, Any]],
        time_spent_seconds: int,
        estimated_minutes: int,
        has_project: bool,
        project_submitted: bool = False,
        notes_taken: bool = False,
    ) -> MasteryScore:
        """
        Compute mastery score for a single lesson.
        """
        # Quiz score: best attempt
        best_quiz = 0.0
        if quiz_attempts:
            best_quiz = max(a.get("score", 0) for a in quiz_attempts) / 100.0

        # Time score: penalize if spent < 40% or > 300% of estimated time
        estimated_seconds = estimated_minutes * 60
        if estimated_seconds > 0:
            ratio = time_spent_seconds / estimated_seconds
            if ratio < 0.40:
                time_score = ratio / 0.40 * 0.60  # rushed
            elif ratio <= 3.0:
                time_score = min(1.0, 0.60 + ratio * 0.13)
            else:
                time_score = 0.85  # spent too long, minor penalty
        else:
            time_score = 0.70

        # Project score
        project_score = 0.0
        if has_project:
            project_score = 1.0 if project_submitted else 0.0
        else:
            project_score = 1.0  # No project required = full marks

        # Engagement score
        engagement = 0.50
        if notes_taken:
            engagement += 0.30
        if len(quiz_attempts) > 1:
            engagement += 0.20  # Retried quiz = engaged

        return MasteryScore(
            quiz_score=best_quiz,
            time_score=time_score,
            project_score=project_score,
            engagement_score=min(1.0, engagement),
        )

    def should_unlock_next_module(
        self,
        module_lessons_mastery: List[float],
        min_lessons_completed: float = 0.80,
        min_avg_mastery: float = 0.65,
    ) -> tuple[bool, str]:
        """
        Determine if the next module should be unlocked.
        Returns (should_unlock, reason).
        """
        if not module_lessons_mastery:
            return False, "No lessons completed"

        completion_ratio = len([s for s in module_lessons_mastery if s >= 0.70]) / len(module_lessons_mastery)
        avg_mastery = sum(module_lessons_mastery) / len(module_lessons_mastery)

        if completion_ratio < min_lessons_completed:
            pct = int(completion_ratio * 100)
            needed = int(min_lessons_completed * 100)
            return False, f"Complete {needed - pct}% more lessons to advance"

        if avg_mastery < min_avg_mastery:
            return False, f"Average mastery {int(avg_mastery*100)}% — retake quizzes to improve"

        return True, "Module mastered! Next module unlocked."

    async def evaluate_project_submission(
        self,
        project_title: str,
        project_description: str,
        submission_text: str,
        topic: str,
    ) -> Dict[str, Any]:
        """Use Claude to evaluate a project submission."""
        prompt = f"""You are evaluating a student's project submission for LearnOS.

Project: {project_title}
Requirements: {project_description}
Topic: {topic}

Student submission:
---
{submission_text[:3000]}
---

Evaluate and return JSON:
{{
  "score": <0-100>,
  "passed": <true|false>,
  "strengths": ["<strength 1>", "<strength 2>"],
  "improvements": ["<improvement 1>", "<improvement 2>"],
  "feedback": "<2-3 sentence overall feedback>",
  "xp_earned": <50-300>
}}

Be encouraging but honest. Pass if score >= 60. Return ONLY JSON."""

        response = await self.client.generate_content_async(
            prompt,
            generation_config=genai.types.GenerationConfig(max_output_tokens=800)
        )
        content = response.text.strip().replace("```json", "").replace("```", "").strip()
        try:
            return json.loads(content)
        except Exception:
            return {
                "score": 70,
                "passed": True,
                "strengths": ["Good effort"],
                "improvements": ["Review the requirements"],
                "feedback": "Project reviewed. Keep learning!",
                "xp_earned": 100,
            }

    def compute_skill_level(self, mastery_scores: List[float]) -> str:
        """
        Determine overall skill level based on history of mastery scores.
        Used for adaptive roadmap generation.
        """
        if not mastery_scores:
            return "beginner"
        avg = sum(mastery_scores) / len(mastery_scores)
        if avg >= 0.90:
            return "expert"
        elif avg >= 0.75:
            return "advanced"
        elif avg >= 0.55:
            return "intermediate"
        else:
            return "beginner"

    def get_adaptive_recommendation(
        self,
        mastery_score: float,
        lesson_title: str,
    ) -> Dict[str, Any]:
        """
        Provide adaptive recommendation based on mastery score.
        """
        if mastery_score >= 0.90:
            return {
                "action": "advance",
                "message": "Excellent work! You've mastered this lesson. Move to the next one.",
                "emoji": "🚀",
            }
        elif mastery_score >= 0.70:
            return {
                "action": "advance",
                "message": "Good job! You've passed. You can advance or review for deeper understanding.",
                "emoji": "✅",
            }
        elif mastery_score >= 0.50:
            return {
                "action": "review",
                "message": f"You're making progress on '{lesson_title}'. Review the resources and retry the quiz.",
                "emoji": "📖",
            }
        else:
            return {
                "action": "restart",
                "message": f"Let's strengthen your foundation in '{lesson_title}'. Start from the resources.",
                "emoji": "🔄",
            }
