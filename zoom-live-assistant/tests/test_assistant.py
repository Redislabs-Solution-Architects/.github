from zoom_live_assistant.assistant import LiveAssistant
from zoom_live_assistant.config import Settings
from zoom_live_assistant.models import TranscriptEvent


class StubLLM:
    def __init__(self):
        self.calls = 0

    def answer_question(self, question: str, context):
        self.calls += 1
        return f"Answer for: {question}"


def _settings() -> Settings:
    return Settings(
        OPENAI_API_KEY="test-key",
        MIN_QUESTION_LENGTH=5,
    )


def test_assistant_answers_new_question_and_dedupes():
    llm = StubLLM()
    assistant = LiveAssistant(settings=_settings(), llm_client=llm)

    first = assistant.ingest_event(
        TranscriptEvent(speaker="customer", text="Can you share your SLA details?")
    )
    second = assistant.ingest_event(
        TranscriptEvent(speaker="customer", text="Can you share your SLA details?")
    )

    assert first is not None
    assert "SLA details" in first.answer
    assert second is None
    assert llm.calls == 1
