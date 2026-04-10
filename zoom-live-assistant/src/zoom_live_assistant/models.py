from datetime import UTC, datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


class TranscriptEvent(BaseModel):
    speaker: str = Field(..., description="Speaker name or identifier")
    text: str = Field(..., min_length=1, description="Transcribed utterance")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    source: Literal["zoom", "manual", "api"] = "api"


class AssistantAnswer(BaseModel):
    question: str
    answer: str
    speaker: Optional[str] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))

