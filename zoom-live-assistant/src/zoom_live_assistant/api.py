from __future__ import annotations

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn

from zoom_live_assistant.assistant import LiveAssistant
from zoom_live_assistant.config import get_settings
from zoom_live_assistant.models import AssistantAnswer, TranscriptEvent

settings = get_settings()
assistant = LiveAssistant(settings)
app = FastAPI(
    title="Zoom Live Assistant API",
    description="Accepts transcript events and returns suggested live answers when a question is detected.",
)


class IngestResponse(BaseModel):
    accepted: bool = True
    answer: AssistantAnswer | None = None
    context_size: int


class ZoomTranscriptEvent(BaseModel):
    speaker: str = "customer"
    text: str
    timestamp: str | None = None


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/ingest", response_model=IngestResponse)
def ingest(event: TranscriptEvent) -> IngestResponse:
    try:
        answer = assistant.ingest_event(event)
        return IngestResponse(answer=answer, context_size=assistant.context_size())
    except Exception as exc:  # pragma: no cover
        raise HTTPException(status_code=500, detail=f"Failed to ingest event: {exc}") from exc


@app.post("/zoom/transcript", response_model=IngestResponse)
def ingest_zoom_transcript(event: ZoomTranscriptEvent) -> IngestResponse:
    normalized = TranscriptEvent(speaker=event.speaker, text=event.text, source="zoom")
    return ingest(normalized)


def run() -> None:
    uvicorn.run(
        "zoom_live_assistant.api:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=False,
    )
