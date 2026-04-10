from __future__ import annotations

from typing import Sequence

from openai import OpenAI

from zoom_live_assistant.config import Settings
from zoom_live_assistant.models import TranscriptEvent


class LLMClient:
    def __init__(self, settings: Settings):
        self._settings = settings
        self._client = OpenAI(api_key=settings.openai_api_key)

    def answer_question(self, question: str, context: Sequence[TranscriptEvent]) -> str:
        context_lines = [
            f"[{event.timestamp.isoformat()}] {event.speaker}: {event.text}" for event in context
        ]
        context_block = "\n".join(context_lines[-self._settings.max_context_messages :])

        user_prompt = (
            "You are helping the meeting host answer a customer in real time.\n"
            "Use the transcript context below, then answer the latest customer question.\n"
            "Keep it concise (max 5 bullet points) and practical.\n\n"
            f"Transcript context:\n{context_block or '(no prior context)'}\n\n"
            f"Latest question:\n{question}\n"
        )

        response = self._client.responses.create(
            model=self._settings.openai_model,
            input=[
                {"role": "system", "content": self._settings.system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        text = getattr(response, "output_text", None)
        if text:
            return text.strip()

        # Backward-compatible extraction in case output_text is unavailable.
        fragments: list[str] = []
        for item in getattr(response, "output", []):
            for content in getattr(item, "content", []):
                if getattr(content, "type", "") == "output_text":
                    fragments.append(getattr(content, "text", ""))
        return "\n".join(part.strip() for part in fragments if part.strip())

