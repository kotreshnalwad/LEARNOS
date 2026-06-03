"""Initial schema

Revision ID: 001_initial
Revises:
Create Date: 2024-01-01 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\"")

    op.create_table(
        "users",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("clerk_id", sa.String(128), unique=True, nullable=False),
        sa.Column("email", sa.String(255), unique=True, nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("avatar_url", sa.Text, nullable=True),
        sa.Column("xp_points", sa.Integer, default=0),
        sa.Column("streak_days", sa.Integer, default=0),
        sa.Column("last_active_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_users_clerk_id", "users", ["clerk_id"])
    op.create_index("ix_users_email", "users", ["email"])

    op.create_table(
        "topics",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("title", sa.String(255), unique=True, nullable=False),
        sa.Column("slug", sa.String(255), unique=True, nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("category", sa.String(100), nullable=True),
        sa.Column("tags", sa.JSON, nullable=True),
        sa.Column("search_count", sa.Integer, default=0),
        sa.Column("is_trending", sa.Boolean, default=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    skill_level = sa.Enum("beginner", "intermediate", "advanced", "expert", name="skilllevel")
    roadmap_status = sa.Enum("generating", "active", "completed", "archived", name="roadmapstatus")
    lesson_status = sa.Enum("locked", "in_progress", "completed", name="lessonstatus")
    resource_type = sa.Enum("video", "course", "documentation", "book", "paper", "blog", "github", "podcast", name="resourcetype")

    skill_level.create(op.get_bind())
    roadmap_status.create(op.get_bind())
    lesson_status.create(op.get_bind())
    resource_type.create(op.get_bind())

    op.create_table(
        "roadmaps",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("topic_id", sa.String(36), sa.ForeignKey("topics.id"), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("level", skill_level, nullable=False),
        sa.Column("status", roadmap_status, nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("estimated_hours", sa.Integer, nullable=True),
        sa.Column("completion_percentage", sa.Float, default=0.0),
        sa.Column("generation_metadata", sa.JSON, nullable=True),
        sa.Column("last_updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_roadmaps_user_id", "roadmaps", ["user_id"])

    op.create_table(
        "modules",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("roadmap_id", sa.String(36), sa.ForeignKey("roadmaps.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("order", sa.Integer, nullable=False),
        sa.Column("is_unlocked", sa.Boolean, default=False),
        sa.Column("estimated_hours", sa.Integer, nullable=True),
        sa.Column("completion_percentage", sa.Float, default=0.0),
        sa.Column("prerequisites", sa.JSON, nullable=True),
    )

    op.create_table(
        "lessons",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("module_id", sa.String(36), sa.ForeignKey("modules.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("summary", sa.Text, nullable=True),
        sa.Column("objectives", sa.JSON, nullable=True),
        sa.Column("key_concepts", sa.JSON, nullable=True),
        sa.Column("difficulty", skill_level, nullable=False),
        sa.Column("estimated_minutes", sa.Integer, default=30),
        sa.Column("order", sa.Integer, nullable=False),
        sa.Column("xp_reward", sa.Integer, default=50),
    )

    op.create_table(
        "resources",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("lesson_id", sa.String(36), sa.ForeignKey("lessons.id", ondelete="CASCADE"), nullable=False),
        sa.Column("resource_type", resource_type, nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("url", sa.Text, nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("author", sa.String(255), nullable=True),
        sa.Column("platform", sa.String(100), nullable=True),
        sa.Column("duration_minutes", sa.Integer, nullable=True),
        sa.Column("is_free", sa.Boolean, default=True),
        sa.Column("is_primary", sa.Boolean, default=False),
        sa.Column("authority_score", sa.Float, default=0),
        sa.Column("popularity_score", sa.Float, default=0),
        sa.Column("freshness_score", sa.Float, default=0),
        sa.Column("completeness_score", sa.Float, default=0),
        sa.Column("community_score", sa.Float, default=0),
        sa.Column("composite_score", sa.Float, default=0),
        sa.Column("thumbnail_url", sa.Text, nullable=True),
        sa.Column("metadata", sa.JSON, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "projects",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("lesson_id", sa.String(36), sa.ForeignKey("lessons.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("requirements", sa.JSON, nullable=True),
        sa.Column("deliverables", sa.JSON, nullable=True),
        sa.Column("hints", sa.JSON, nullable=True),
        sa.Column("difficulty", skill_level, nullable=False),
        sa.Column("xp_reward", sa.Integer, default=200),
    )

    op.create_table(
        "quizzes",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("lesson_id", sa.String(36), sa.ForeignKey("lessons.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("passing_score", sa.Integer, default=70),
        sa.Column("time_limit_minutes", sa.Integer, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "questions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("quiz_id", sa.String(36), sa.ForeignKey("quizzes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("question", sa.Text, nullable=False),
        sa.Column("question_type", sa.String(50), default="multiple_choice"),
        sa.Column("options", sa.JSON, nullable=True),
        sa.Column("correct_answer", sa.Text, nullable=False),
        sa.Column("explanation", sa.Text, nullable=True),
        sa.Column("order", sa.Integer, default=0),
    )

    op.create_table(
        "quiz_attempts",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("quiz_id", sa.String(36), sa.ForeignKey("quizzes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("score", sa.Float, nullable=False),
        sa.Column("passed", sa.Boolean, nullable=False),
        sa.Column("answers", sa.JSON, nullable=True),
        sa.Column("time_taken_seconds", sa.Integer, nullable=True),
        sa.Column("attempted_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "progress",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("lesson_id", sa.String(36), sa.ForeignKey("lessons.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", lesson_status, nullable=False),
        sa.Column("mastery_score", sa.Float, default=0.0),
        sa.Column("time_spent_seconds", sa.Integer, default=0),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("user_id", "lesson_id", name="uq_progress_user_lesson"),
    )

    op.create_table(
        "badges",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(100), unique=True, nullable=False),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("icon", sa.String(10), nullable=False),
        sa.Column("xp_reward", sa.Integer, default=100),
        sa.Column("criteria", sa.JSON, nullable=True),
    )

    op.create_table(
        "user_badges",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("badge_id", sa.String(36), sa.ForeignKey("badges.id"), nullable=False),
        sa.Column("earned_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("user_id", "badge_id", name="uq_user_badge"),
    )


def downgrade() -> None:
    for table in ["user_badges", "badges", "progress", "quiz_attempts", "questions",
                  "quizzes", "projects", "resources", "lessons", "modules",
                  "roadmaps", "topics", "users"]:
        op.drop_table(table)

    for enum_name in ["skilllevel", "roadmapstatus", "lessonstatus", "resourcetype"]:
        op.execute(f"DROP TYPE IF EXISTS {enum_name}")
