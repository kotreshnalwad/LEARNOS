"""
Curriculum Agent: Uses Claude (claude-3-5-sonnet) to generate a complete,
structured learning roadmap with modules, lessons, quizzes, and projects
based on ranked resources.
"""
from typing import List, Dict, Any, Optional, AsyncIterator
import json
import asyncio
import anthropic
import structlog

from app.core.config import get_settings
from app.agents.ranking_agent import ScoredResource
from app.schemas.schemas import SkillLevel

logger = structlog.get_logger()
settings = get_settings()


class CurriculumAgent:
    """
    Orchestrates Claude to design a complete curriculum from ranked resources.
    Produces: modules → lessons → quizzes → projects → milestones.
    """

    def __init__(self):
        self.client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
        self.model = "claude-sonnet-4-20250514"

    async def generate_roadmap(
        self,
        topic: str,
        level: SkillLevel,
        resources: List[ScoredResource],
        stream_callback: Optional[callable] = None,
    ) -> Dict[str, Any]:
        """
        Generate complete roadmap structure.
        Returns a structured dict matching the DB schema.
        """
        logger.info("Generating curriculum", topic=topic, level=level)

        # Step 1: Analyze topic and build dependency graph
        topic_analysis = await self._analyze_topic(topic, level)

        # Step 2: Generate curriculum structure
        curriculum = await self._generate_curriculum_structure(
            topic, level, topic_analysis, resources, stream_callback
        )

        # Step 3: Generate quizzes for each lesson
        curriculum = await self._enrich_with_quizzes(curriculum, topic)

        # Step 4: Generate projects for key lessons
        curriculum = await self._add_projects(curriculum, topic)

        logger.info("Curriculum generation complete", modules=len(curriculum.get("modules", [])))
        return curriculum

    async def _analyze_topic(self, topic: str, level: SkillLevel) -> Dict[str, Any]:
        """Analyze topic complexity, prerequisites, and learning path."""
        prompt = f"""Analyze the topic "{topic}" for a {level.value} level learner.
Return a JSON object with:
{{
  "complexity": "low|medium|high|very_high",
  "estimated_weeks": <integer>,
  "prerequisites": ["list", "of", "prerequisites"],
  "key_concepts": ["core", "concepts", "to", "master"],
  "learning_objectives": ["what", "learner", "will", "achieve"],
  "domain": "technology|science|business|creative|language|other"
}}
Return ONLY the JSON object, no markdown, no explanation."""

        message = await self.client.messages.create(
            model=self.model,
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}],
        )
        try:
            content = message.content[0].text.strip()
            content = content.replace("```json", "").replace("```", "").strip()
            return json.loads(content)
        except Exception as e:
            logger.warning("Topic analysis parse failed", error=str(e))
            return {
                "complexity": "medium",
                "estimated_weeks": 8,
                "prerequisites": [],
                "key_concepts": [],
                "learning_objectives": [],
                "domain": "other",
            }

    async def _generate_curriculum_structure(
        self,
        topic: str,
        level: SkillLevel,
        analysis: Dict[str, Any],
        resources: List[ScoredResource],
        stream_callback: Optional[callable],
    ) -> Dict[str, Any]:
        """Generate complete module/lesson structure with resource assignments."""

        resource_summary = self._format_resources_for_prompt(resources)
        key_concepts = ", ".join(analysis.get("key_concepts", [])[:10])
        objectives = "\n".join(f"- {o}" for o in analysis.get("learning_objectives", [])[:6])
        prerequisites = ", ".join(analysis.get("prerequisites", [])[:5]) or "None"

        prompt = f"""You are an expert curriculum designer. Create a complete learning roadmap for:

TOPIC: {topic}
LEVEL: {level.value}
PREREQUISITES: {prerequisites}
KEY CONCEPTS TO COVER: {key_concepts}
LEARNING OBJECTIVES:
{objectives}
ESTIMATED DURATION: {analysis.get('estimated_weeks', 8)} weeks

AVAILABLE RESOURCES (assign these to lessons):
{resource_summary}

Generate a JSON curriculum with this EXACT structure:
{{
  "title": "Complete {topic} Roadmap — {level.value.title()} Level",
  "description": "<2-3 sentence overview of what the learner will achieve>",
  "estimated_hours": <total hours as integer>,
  "modules": [
    {{
      "title": "<module title>",
      "description": "<what this module covers>",
      "order": 1,
      "estimated_hours": <integer>,
      "lessons": [
        {{
          "title": "<lesson title>",
          "summary": "<2-3 sentence lesson summary explaining what will be learned>",
          "objectives": ["<specific objective 1>", "<specific objective 2>", "<specific objective 3>"],
          "key_concepts": ["<concept 1>", "<concept 2>"],
          "difficulty": "{level.value}",
          "estimated_minutes": <15-90>,
          "order": 1,
          "xp_reward": <50-200>,
          "resource_indices": [<indices from the resource list above, 0-based>]
        }}
      ]
    }}
  ]
}}

RULES:
- Create 4-8 modules with clear progression (foundations → intermediate → advanced)
- Each module should have 3-8 lessons
- Assign 2-5 resources per lesson using resource_indices (can reuse resources across lessons)
- First module MUST be unlocked, others locked until prior module completed
- xp_reward should reflect lesson difficulty (easy=50, medium=100, hard=150, project=200)
- Lessons should build on each other logically
- Return ONLY valid JSON, no markdown, no comments"""

        if stream_callback:
            await stream_callback({"step": "curriculum", "progress": 30, "message": "Designing learning path..."})

        message = await self.client.messages.create(
            model=self.model,
            max_tokens=8000,
            messages=[{"role": "user", "content": prompt}],
        )

        content = message.content[0].text.strip()
        content = content.replace("```json", "").replace("```", "").strip()

        try:
            curriculum = json.loads(content)
        except json.JSONDecodeError as e:
            logger.error("Curriculum JSON parse failed", error=str(e), content=content[:500])
            curriculum = self._fallback_curriculum(topic, level)

        # Resolve resource_indices to actual resource data
        curriculum = self._resolve_resources(curriculum, resources)

        if stream_callback:
            await stream_callback({"step": "curriculum", "progress": 55, "message": "Curriculum structure created..."})

        return curriculum

    def _format_resources_for_prompt(self, resources: List[ScoredResource]) -> str:
        """Format resources for LLM prompt with index references."""
        lines = []
        for i, r in enumerate(resources[:25]):  # cap at 25 for token budget
            lines.append(
                f"[{i}] TYPE={r.resource_type.value} | PLATFORM={r.platform} | "
                f"SCORE={r.composite_score:.2f} | TITLE={r.title[:80]}"
            )
        return "\n".join(lines)

    def _resolve_resources(
        self, curriculum: Dict[str, Any], resources: List[ScoredResource]
    ) -> Dict[str, Any]:
        """Replace resource_indices with actual resource objects."""
        for module in curriculum.get("modules", []):
            for lesson in module.get("lessons", []):
                indices = lesson.pop("resource_indices", [])
                lesson_resources = []
                for idx in indices:
                    if isinstance(idx, int) and 0 <= idx < len(resources):
                        r = resources[idx]
                        lesson_resources.append({
                            "resource_type": r.resource_type.value,
                            "title": r.title,
                            "url": r.url,
                            "description": r.description,
                            "author": r.author,
                            "platform": r.platform,
                            "duration_minutes": r.duration_minutes,
                            "is_free": r.is_free,
                            "is_primary": r.is_primary and idx == indices[0],
                            "thumbnail_url": r.thumbnail_url,
                            "authority_score": r.authority_score,
                            "popularity_score": r.popularity_score,
                            "freshness_score": r.freshness_score,
                            "completeness_score": r.completeness_score,
                            "community_score": r.community_score,
                            "composite_score": r.composite_score,
                            "metadata": r.metadata,
                        })
                lesson["resources"] = lesson_resources
        return curriculum

    async def _enrich_with_quizzes(
        self, curriculum: Dict[str, Any], topic: str
    ) -> Dict[str, Any]:
        """Generate quizzes for each lesson in parallel."""
        tasks = []
        lesson_refs = []

        for module in curriculum.get("modules", []):
            for lesson in module.get("lessons", []):
                tasks.append(self._generate_quiz(lesson["title"], topic, lesson.get("key_concepts", [])))
                lesson_refs.append(lesson)

        # Generate in batches of 5 to avoid rate limits
        batch_size = 5
        for i in range(0, len(tasks), batch_size):
            batch_results = await asyncio.gather(*tasks[i:i + batch_size], return_exceptions=True)
            for j, result in enumerate(batch_results):
                idx = i + j
                if not isinstance(result, Exception):
                    lesson_refs[idx]["quiz"] = result
                else:
                    lesson_refs[idx]["quiz"] = self._default_quiz(lesson_refs[idx]["title"])

        return curriculum

    async def _generate_quiz(
        self, lesson_title: str, topic: str, concepts: List[str]
    ) -> Dict[str, Any]:
        """Generate a quiz with 5 multiple-choice questions."""
        concepts_str = ", ".join(concepts[:5]) if concepts else lesson_title
        prompt = f"""Generate a quiz for a lesson on "{lesson_title}" (part of learning {topic}).
Concepts tested: {concepts_str}

Return JSON:
{{
  "passing_score": 70,
  "questions": [
    {{
      "question": "<clear question text>",
      "question_type": "multiple_choice",
      "options": ["Option A", "Option B", "Option C", "Option D"],
      "correct_answer": "Option A",
      "explanation": "<why this is correct>",
      "order": 1
    }}
  ]
}}

Generate exactly 5 questions. Vary difficulty. Return ONLY JSON."""

        message = await self.client.messages.create(
            model=self.model,
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}],
        )
        content = message.content[0].text.strip().replace("```json", "").replace("```", "").strip()
        return json.loads(content)

    def _default_quiz(self, lesson_title: str) -> Dict[str, Any]:
        return {
            "passing_score": 70,
            "questions": [
                {
                    "question": f"What is the main concept covered in '{lesson_title}'?",
                    "question_type": "multiple_choice",
                    "options": ["Option A", "Option B", "Option C", "Option D"],
                    "correct_answer": "Option A",
                    "explanation": "Review the lesson material for the correct answer.",
                    "order": 1,
                }
            ],
        }

    async def _add_projects(
        self, curriculum: Dict[str, Any], topic: str
    ) -> Dict[str, Any]:
        """Add hands-on projects to the final lesson of each module."""
        for module in curriculum.get("modules", []):
            lessons = module.get("lessons", [])
            if not lessons:
                continue
            # Add project to last lesson of each module
            last_lesson = lessons[-1]
            try:
                project = await self._generate_project(last_lesson["title"], topic)
                last_lesson["project"] = project
            except Exception as e:
                logger.warning("Project generation failed", lesson=last_lesson["title"], error=str(e))

        return curriculum

    async def _generate_project(self, lesson_title: str, topic: str) -> Dict[str, Any]:
        """Generate a hands-on project for a lesson."""
        prompt = f"""Create a hands-on project for the lesson "{lesson_title}" in {topic}.

Return JSON:
{{
  "title": "<project title>",
  "description": "<what the learner will build, 2-3 sentences>",
  "requirements": ["<requirement 1>", "<requirement 2>", "<requirement 3>"],
  "deliverables": ["<what to submit 1>", "<what to submit 2>"],
  "hints": ["<helpful hint 1>", "<helpful hint 2>"],
  "xp_reward": <150-300>
}}

Return ONLY JSON."""

        message = await self.client.messages.create(
            model=self.model,
            max_tokens=800,
            messages=[{"role": "user", "content": prompt}],
        )
        content = message.content[0].text.strip().replace("```json", "").replace("```", "").strip()
        return json.loads(content)

    def _fallback_curriculum(self, topic: str, level: SkillLevel) -> Dict[str, Any]:
        """Emergency fallback curriculum if generation fails."""
        return {
            "title": f"Learning {topic} — {level.value.title()}",
            "description": f"A structured path to master {topic}.",
            "estimated_hours": 40,
            "modules": [
                {
                    "title": f"{topic} Fundamentals",
                    "description": f"Core concepts of {topic}",
                    "order": 1,
                    "estimated_hours": 10,
                    "lessons": [
                        {
                            "title": f"Introduction to {topic}",
                            "summary": f"Get started with {topic} from scratch.",
                            "objectives": [f"Understand what {topic} is", f"Set up your {topic} environment"],
                            "key_concepts": [topic],
                            "difficulty": level.value,
                            "estimated_minutes": 30,
                            "order": 1,
                            "xp_reward": 50,
                            "resources": [],
                        }
                    ],
                }
            ],
        }
