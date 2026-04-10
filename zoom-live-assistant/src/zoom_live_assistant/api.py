from __future__ import annotations

import json
from collections import deque
from typing import Deque

from fastapi import FastAPI, Header, HTTPException, Request, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
import uvicorn

from zoom_live_assistant.assistant import LiveAssistant
from zoom_live_assistant.config import get_settings
from zoom_live_assistant.models import AssistantAnswer, TranscriptEvent
from zoom_live_assistant.zoom_webhook_adapter import (
    build_zoom_validation_response,
    extract_transcript_events,
    verify_zoom_signature,
)

settings = get_settings()
assistant = LiveAssistant(settings)
recent_answers: Deque[AssistantAnswer] = deque(maxlen=100)
connected_clients: set[WebSocket] = set()
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


class ZoomWebhookEnvelope(BaseModel):
    event: str
    payload: dict
    event_ts: int | None = None


class ZoomWebhookResponse(BaseModel):
    accepted: bool = True
    validation: dict | None = None
    ingested_events: int = 0
    answers: list[AssistantAnswer] = []
    message: str | None = None


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/ingest", response_model=IngestResponse)
async def ingest(event: TranscriptEvent) -> IngestResponse:
    try:
        answer = assistant.ingest_event(event)
        if answer:
            await _store_answer(answer)
        return IngestResponse(answer=answer, context_size=assistant.context_size())
    except Exception as exc:  # pragma: no cover
        raise HTTPException(status_code=500, detail=f"Failed to ingest event: {exc}") from exc


@app.post("/zoom/transcript", response_model=IngestResponse)
async def ingest_zoom_transcript(event: ZoomTranscriptEvent) -> IngestResponse:
    normalized = TranscriptEvent(speaker=event.speaker, text=event.text, source="zoom")
    return await ingest(normalized)


@app.post("/zoom/webhook", response_model=ZoomWebhookResponse)
async def zoom_webhook(
    request: Request,
    x_zm_request_timestamp: str | None = Header(default=None),
    x_zm_signature: str | None = Header(default=None),
) -> ZoomWebhookResponse:
    raw = await request.body()
    try:
        body = json.loads(raw.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid JSON payload: {exc}") from exc

    envelope = ZoomWebhookEnvelope.model_validate(body)
    if envelope.event == "endpoint.url_validation":
        plain_token = envelope.payload.get("plainToken", "")
        if not settings.zoom_webhook_secret:
            raise HTTPException(
                status_code=500,
                detail="ZOOM_WEBHOOK_SECRET must be configured for endpoint.url_validation.",
            )
        validation = build_zoom_validation_response(
            plain_token=plain_token, webhook_secret=settings.zoom_webhook_secret
        )
        return ZoomWebhookResponse(validation=validation.model_dump(), message="url validated")

    if settings.verify_zoom_signatures:
        if not settings.zoom_webhook_secret:
            raise HTTPException(
                status_code=500,
                detail="ZOOM_WEBHOOK_SECRET must be configured when VERIFY_ZOOM_SIGNATURES is true.",
            )
        if not verify_zoom_signature(
            raw_body=raw,
            request_timestamp=x_zm_request_timestamp,
            zoom_signature=x_zm_signature,
            webhook_secret=settings.zoom_webhook_secret,
        ):
            raise HTTPException(status_code=401, detail="Invalid Zoom webhook signature.")

    events = extract_transcript_events(body)
    answers: list[AssistantAnswer] = []
    for event in events:
        answer = assistant.ingest_event(event)
        if answer:
            answers.append(answer)
            await _store_answer(answer)
    return ZoomWebhookResponse(ingested_events=len(events), answers=answers)


@app.websocket("/ws/answers")
async def answers_ws(websocket: WebSocket) -> None:
    await websocket.accept()
    connected_clients.add(websocket)
    try:
        for answer in recent_answers:
            await websocket.send_json(answer.model_dump(mode="json"))
        while True:
            # Keep alive; clients do not need to send data.
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        connected_clients.discard(websocket)


async def _store_answer(answer: AssistantAnswer) -> None:
    recent_answers.append(answer)
    payload = answer.model_dump(mode="json")
    stale_clients: list[WebSocket] = []
    for client in list(connected_clients):
        try:
            # Best effort push to live overlays.
            await client.send_json(payload)
        except Exception:
            stale_clients.append(client)
    for stale in stale_clients:
        connected_clients.discard(stale)


def run() -> None:
    uvicorn.run(
        "zoom_live_assistant.api:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=False,
    )
