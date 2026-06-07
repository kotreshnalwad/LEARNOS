from pydantic import BaseModel, EmailStr, HttpUrl, Field, field_validator, model_validator
from typing import Optional, List, Any, Dict
from datetime import datetime
from enum import Enum


# ─── Enums ────────────────────────────────────────────────────────────────────

class SkillLevel(str, Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"


class ResourceType(str, Enum):
    VIDEO = "video"
    COURSE = "course"
    DOCUMENTATION = "documentation"
    BOOK = "book"
    PAPER = "paper"
    BLOG = "blog"
    GITHUB = "github"
    PODCAST = "podcast"


class LessonStatus(str, Enum):
    LOCKED = "locked"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


class RoadmapStatus(str, Enum):
    GENERATING = "generating"
    ACTIVE = "active"
    COMPLETED = "completed"
    ARCHIVED = "archived"


# ─── Base ─────────────────────────────────────────────────────────────────────

class TimestampMixin(BaseModel):
    created_at: datetime
    updated_at: Optional[datetime] = None


# ─── User Schemas ─────────────────────────────────────────────────────────────

class UserCreate(BaseModel):
    clerk_id: str
    email: EmailStr
    name: str
    avatar_url: Optional[str] = None


class UserUpdate(BaseModel):
    name: Optional[str] = None
    avatar_url: Optional[str] = None


class UserResponse(BaseModel):
    id: str
    clerk_id: str
    email: str
    name: str
    avatar_url: Optional[str] = None
    xp_points: int
    streak_days: int
    last_active_at: Optional[datetime] = None
    created_at: datetime

    model_config = {"from_attributes": True}


# ─── Topic Schemas ────────────────────────────────────────────────────────────

class TopicSearchRequest(BaseModel):
    query: str = Field(..., min_length=2, max_length=200)
    level: SkillLevel = SkillLevel.BEGINNER

    @field_validator("query")
    @classmethod
    def clean_query(cls, v: str) -> str:
        return v.strip()


class TopicResponse(BaseModel):
    id: str
    title: str
    slug: str
    description: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[List[str]] = None
    search_count: int

    model_config = {"from_attributes": True}


class TrendingTopicsResponse(BaseModel):
    topics: List[TopicResponse]


# ─── Resource Schemas ─────────────────────────────────────────────────────────

class ResourceResponse(BaseModel):
    id: str
    resource_type: ResourceType
    title: str
    url: str
    description: Optional[str] = None
    author: Optional[str] = None
    platform: Optional[str] = None
    duration_minutes: Optional[int] = None
    is_free: bool
    is_primary: bool
    composite_score: float
    thumbnail_url: Optional[str] = None

    model_config = {"from_attributes": True}


# ─── Lesson Schemas ───────────────────────────────────────────────────────────

class QuestionResponse(BaseModel):
    id: str
    question: str
    question_type: str
    options: Optional[List[str]] = None
    order: int

    model_config = {"from_attributes": True}


class QuizResponse(BaseModel):
    id: str
    passing_score: int
    time_limit_minutes: Optional[int] = None
    questions: List[QuestionResponse] = []

    model_config = {"from_attributes": True}


class ProjectResponse(BaseModel):
    id: str
    title: str
    description: str
    requirements: Optional[List[str]] = None
    deliverables: Optional[List[str]] = None
    hints: Optional[List[str]] = None
    difficulty: SkillLevel
    xp_reward: int

    model_config = {"from_attributes": True}


class LessonResponse(BaseModel):
    id: str
    title: str
    summary: Optional[str] = None
    objectives: Optional[List[str]] = None
    key_concepts: Optional[List[str]] = None
    difficulty: SkillLevel
    estimated_minutes: int
    order: int
    xp_reward: int
    resources: List[ResourceResponse] = []
    quiz: Optional[QuizResponse] = None
    project: Optional[ProjectResponse] = None

    model_config = {"from_attributes": True}


class LessonWithProgress(LessonResponse):
    status: LessonStatus = LessonStatus.LOCKED
    mastery_score: float = 0.0
    time_spent_seconds: int = 0


# ─── Module Schemas ───────────────────────────────────────────────────────────

class ModuleResponse(BaseModel):
    id: str
    title: str
    description: Optional[str] = None
    order: int
    is_unlocked: bool
    estimated_hours: Optional[int] = None
    completion_percentage: float
    lessons: List[LessonResponse] = []

    model_config = {"from_attributes": True}


class ModuleWithProgress(ModuleResponse):
    lessons: List[LessonWithProgress] = []


# ─── Roadmap Schemas ──────────────────────────────────────────────────────────

class RoadmapCreateRequest(BaseModel):
    topic_id: Optional[str] = None
    topic_query: Optional[str] = None
    level: SkillLevel = SkillLevel.BEGINNER

    @model_validator(mode="after")
    def validate_topic(self) -> 'RoadmapCreateRequest':
        if self.topic_id is None and self.topic_query is None:
            raise ValueError("Either topic_id or topic_query must be provided")
        return self



class RoadmapSummary(BaseModel):
    id: str
    title: str
    level: SkillLevel
    status: RoadmapStatus
    completion_percentage: float
    estimated_hours: Optional[int] = None
    topic: TopicResponse
    created_at: datetime

    model_config = {"from_attributes": True}


class RoadmapDetailResponse(RoadmapSummary):
    description: Optional[str] = None
    modules: List[ModuleWithProgress] = []
    last_updated_at: datetime


# ─── Progress Schemas ─────────────────────────────────────────────────────────

class ProgressUpdateRequest(BaseModel):
    lesson_id: str
    status: LessonStatus
    time_spent_seconds: Optional[int] = None
    notes: Optional[str] = None


class ProgressResponse(BaseModel):
    id: str
    lesson_id: str
    status: LessonStatus
    mastery_score: float
    time_spent_seconds: int
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class DashboardStats(BaseModel):
    total_lessons_completed: int
    total_hours_learned: float
    current_streak: int
    xp_points: int
    roadmaps_in_progress: int
    average_mastery_score: float
    badges_earned: int


# ─── Quiz Schemas ─────────────────────────────────────────────────────────────

class QuizSubmitRequest(BaseModel):
    quiz_id: str
    answers: Dict[str, str]  # question_id -> answer
    time_taken_seconds: Optional[int] = None


class QuizResultResponse(BaseModel):
    attempt_id: str
    score: float
    passed: bool
    passing_score: int
    xp_earned: int
    feedback: Dict[str, Any] = {}


# ─── Tutor Schemas ────────────────────────────────────────────────────────────

class TutorMessage(BaseModel):
    role: str  # "user" | "assistant"
    content: str
    timestamp: Optional[datetime] = None


class TutorChatRequest(BaseModel):
    lesson_id: str
    message: str = Field(..., min_length=1, max_length=2000)
    conversation_history: List[TutorMessage] = []


class TutorChatResponse(BaseModel):
    message: str
    suggestions: List[str] = []
    related_resources: List[ResourceResponse] = []


# ─── Roadmap Generation Stream ────────────────────────────────────────────────

class GenerationStatus(BaseModel):
    roadmap_id: str
    status: str
    progress: int  # 0–100
    current_step: str
    message: str


# ─── Recommendations ──────────────────────────────────────────────────────────

class RecommendationResponse(BaseModel):
    lesson_id: str
    old_resource_id: str
    new_resource: ResourceResponse
    reason: str
