from __future__ import annotations

from collections import deque
from typing import Deque, Optional

from zoom_live_assistant.config import Settings
from zoom_live_assistant.llm_client import LLMClient
from zoom_live_assistant.models import AssistantAnswer, TranscriptEvent
from zoom_live_assistant.question_detector import is_question


class LiveAssistant:
    def __init__(self, settings: Settings, llm_client: Optional[LLMClient] = None):
        self._settings = settings
        self._llm = llm_client or LLMClient(settings)
        self._events: Deque[TranscriptEvent] = deque(maxlen=max(200, settings.max_context_messages))
        self._last_answered_question: Optional[str] = None

    def ingest_event(self, event: TranscriptEvent) -> Optional[AssistantAnswer]:
        self._events.append(event)
        text = event.text.strip()
        if not is_question(text, min_len=self._settings.min_question_length):
            return None

        # Avoid repeating answers if transcript stream re-sends identical lines.
        normalized_question = " ".join(text.split()).lower()
        if normalized_question == self._last_answered_question:
            return None

        answer = self._llm.answer_question(question=text, context=list(self._events))
        self._last_answered_question = normalized_question
        return AssistantAnswer(question=text, answer=answer, speaker=event.speaker)

    def context_size(self) -> int:
        return len(self._events)

