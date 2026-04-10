from __future__ import annotations

import hashlib
import hmac
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel

from zoom_live_assistant.models import TranscriptEvent


class ZoomValidationResponse(BaseModel):
    plainToken: str
    encryptedToken: str


def build_zoom_validation_response(plain_token: str, webhook_secret: str) -> ZoomValidationResponse:
    encrypted_token = hmac.new(
        webhook_secret.encode("utf-8"),
        plain_token.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return ZoomValidationResponse(plainToken=plain_token, encryptedToken=encrypted_token)


def verify_zoom_signature(
    raw_body: bytes,
    request_timestamp: str | None,
    zoom_signature: str | None,
    webhook_secret: str,
) -> bool:
    if not request_timestamp or not zoom_signature or not webhook_secret:
        return False
    # The signature format is documented by Zoom: v0=HMAC_SHA256("v0:{ts}:{raw_body}")
    message = b"v0:" + request_timestamp.encode("utf-8") + b":" + raw_body
    expected = "v0=" + hmac.new(
        webhook_secret.encode("utf-8"),
        message,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, zoom_signature)


def _parse_timestamp(value: Any) -> datetime:
    if isinstance(value, str) and value:
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            pass
    if isinstance(value, (int, float)):
        # Zoom sometimes emits milliseconds timestamps.
        ts = value / 1000 if value > 10_000_000_000 else value
        return datetime.fromtimestamp(ts, tz=UTC)
    return datetime.now(UTC)


def extract_transcript_events(body: dict[str, Any]) -> list[TranscriptEvent]:
    payload = body.get("payload", {})
    obj = payload.get("object", {})
    content = payload.get("content", {})
    events: list[TranscriptEvent] = []

    # RTMS-style transcript chunks (common in real-time streams)
    for segment in content.get("transcript_segments", []) or []:
        text = (
            segment.get("text")
            or segment.get("transcript")
            or segment.get("utterance")
            or ""
        ).strip()
        if not text:
            continue
        speaker = (
            segment.get("user_name")
            or segment.get("speaker_name")
            or segment.get("speaker")
            or "customer"
        )
        events.append(
            TranscriptEvent(
                speaker=speaker,
                text=text,
                timestamp=_parse_timestamp(
                    segment.get("timestamp")
                    or segment.get("ts")
                    or body.get("event_ts")
                ),
                source="zoom",
            )
        )

    # RTMS callback style where transcript text may exist directly in content.
    direct_text = (
        content.get("text")
        or content.get("transcript")
        or content.get("utterance")
        or ""
    ).strip()
    if direct_text:
        direct_speaker = (
            content.get("user_name")
            or content.get("speaker_name")
            or content.get("speaker")
            or "customer"
        )
        events.append(
            TranscriptEvent(
                speaker=direct_speaker,
                text=direct_text,
                timestamp=_parse_timestamp(content.get("timestamp") or body.get("event_ts")),
                source="zoom",
            )
        )

    # Alternate webhook payload style with nested object transcription arrays.
    for segment in obj.get("transcript", []) or obj.get("transcript_entries", []) or []:
        text = (segment.get("text") or "").strip()
        if not text:
            continue
        events.append(
            TranscriptEvent(
                speaker=segment.get("speaker") or "customer",
                text=text,
                timestamp=_parse_timestamp(segment.get("timestamp") or body.get("event_ts")),
                source="zoom",
            )
        )

    # Fallback object-level text style.
    obj_text = (obj.get("text") or obj.get("transcript") or "").strip()
    if obj_text:
        events.append(
            TranscriptEvent(
                speaker=obj.get("participant_name") or obj.get("speaker") or "customer",
                text=obj_text,
                timestamp=_parse_timestamp(obj.get("timestamp") or body.get("event_ts")),
                source="zoom",
            )
        )

    return events
