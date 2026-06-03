"""
Tutor Agent: Streaming AI tutor powered by Claude.
Explains concepts, answers questions, generates examples, and creates
on-demand quizzes based on lesson context.
"""
from typing import List, Dict, Any, AsyncIterator
import anthropic
import structlog

from app.core.config import get_settings
from app.schemas.schemas import TutorMessage

logger = structlog.get_logger()
settings = get_settings()


TUTOR_SYSTEM_PROMPT = """You are an expert AI tutor for LearnOS — a personalized learning platform.

Your role:
- Explain complex concepts clearly using analogies, examples, and step-by-step breakdowns
- Adapt your explanations to the learner's level (beginner/intermediate/advanced)
- Answer questions about the current lesson with precision and clarity
- Generate relevant code examples or practical demonstrations when helpful
- Create mini-quizzes or exercises when the learner asks for practice
- Be encouraging, patient, and engaging — like the world's best 1-on-1 tutor

Guidelines:
- Keep responses focused and actionable (avoid essays unless asked)
- Use markdown formatting (headers, code blocks, bullet points) for clarity
- When code is relevant, always provide working examples
- If a concept is unclear, offer 2-3 different analogies or explanations
- Proactively suggest what to learn next when appropriate
- Never refuse to help with educational content

Always maintain context of what lesson the learner is currently on."""


class TutorAgent:
    """Streaming AI tutor that maintains conversation context."""

    def __init__(self):
        self.client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
        self.model = "claude-sonnet-4-20250514"

    async def chat_stream(
        self,
        message: str,
        lesson_context: Dict[str, Any],
        conversation_history: List[TutorMessage],
    ) -> AsyncIterator[str]:
        """Stream tutor response token by token."""
        messages = self._build_messages(message, lesson_context, conversation_history)

        async with self.client.messages.stream(
            model=self.model,
            max_tokens=2000,
            system=TUTOR_SYSTEM_PROMPT,
            messages=messages,
        ) as stream:
            async for text in stream.text_stream:
                yield text

    async def chat(
        self,
        message: str,
        lesson_context: Dict[str, Any],
        conversation_history: List[TutorMessage],
    ) -> str:
        """Non-streaming tutor response."""
        messages = self._build_messages(message, lesson_context, conversation_history)

        response = await self.client.messages.create(
            model=self.model,
            max_tokens=2000,
            system=TUTOR_SYSTEM_PROMPT,
            messages=messages,
        )
        return response.content[0].text

    async def generate_explanation(self, concept: str, level: str, context: str = "") -> str:
        """Generate a detailed concept explanation."""
        prompt = f"""Explain "{concept}" for a {level} level learner.
{f"Context: {context}" if context else ""}

Provide:
1. A simple, clear definition
2. A real-world analogy
3. A practical example
4. Common misconceptions to avoid
5. Why this concept matters

Use markdown formatting."""

        response = await self.client.messages.create(
            model=self.model,
            max_tokens=1500,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text

    async def generate_on_demand_quiz(
        self, topic: str, concepts: List[str], difficulty: str
    ) -> Dict[str, Any]:
        """Generate a fresh quiz on demand."""
        prompt = f"""Create a 3-question practice quiz about {topic}.
Concepts: {', '.join(concepts)}
Difficulty: {difficulty}

Return JSON:
{{
  "questions": [
    {{
      "question": "...",
      "type": "multiple_choice",
      "options": ["A", "B", "C", "D"],
      "answer": "A",
      "explanation": "..."
    }}
  ]
}}
Return ONLY JSON."""

        response = await self.client.messages.create(
            model=self.model,
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}],
        )
        import json
        content = response.content[0].text.strip().replace("```json", "").replace("```", "").strip()
        return json.loads(content)

    async def get_suggestions(
        self, message: str, lesson_title: str
    ) -> List[str]:
        """Generate follow-up question suggestions."""
        prompt = f"""For a student asking "{message}" about the lesson "{lesson_title}",
suggest 3 natural follow-up questions they might want to ask next.
Return as a JSON array of strings: ["question 1", "question 2", "question 3"]
Return ONLY JSON."""

        try:
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=300,
                messages=[{"role": "user", "content": prompt}],
            )
            import json
            content = response.content[0].text.strip().replace("```json", "").replace("```", "").strip()
            return json.loads(content)
        except Exception:
            return [
                "Can you give me a practical example?",
                "How does this connect to what I learned before?",
                "What are common mistakes to avoid?",
            ]

    def _build_messages(
        self,
        message: str,
        lesson_context: Dict[str, Any],
        history: List[TutorMessage],
    ) -> List[Dict[str, str]]:
        """Build message array with lesson context injected."""
        messages = []

        # Inject lesson context as first user/assistant exchange
        if lesson_context:
            ctx_str = f"""Current lesson context:
- Lesson: {lesson_context.get('title', 'Unknown')}
- Topic: {lesson_context.get('topic', 'Unknown')}
- Level: {lesson_context.get('level', 'beginner')}
- Key concepts: {', '.join(lesson_context.get('key_concepts', [])[:5])}
- Learning objectives: {'; '.join(lesson_context.get('objectives', [])[:3])}"""

            messages.append({"role": "user", "content": f"[CONTEXT]\n{ctx_str}\n[/CONTEXT]\nI'm ready to learn."})
            messages.append({"role": "assistant", "content": f"Great! I'm ready to help you master {lesson_context.get('title', 'this topic')}. What would you like to understand better?"})

        # Add conversation history
        for msg in history[-10:]:  # Keep last 10 messages
            messages.append({"role": msg.role, "content": msg.content})

        # Add current message
        messages.append({"role": "user", "content": message})

        return messages
