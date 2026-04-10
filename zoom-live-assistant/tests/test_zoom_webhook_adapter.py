import hashlib
import hmac
import json

from zoom_live_assistant.zoom_webhook_adapter import (
    build_zoom_validation_response,
    extract_transcript_events,
    verify_zoom_signature,
)


def test_build_zoom_validation_response():
    response = build_zoom_validation_response("plain-token", "secret")
    expected = hmac.new(b"secret", b"plain-token", hashlib.sha256).hexdigest()
    assert response.plainToken == "plain-token"
    assert response.encryptedToken == expected


def test_verify_zoom_signature_matches_raw_body():
    body = {"event": "meeting.transcript_received", "payload": {"content": {"text": "hello"}}}
    raw = json.dumps(body, separators=(",", ":")).encode("utf-8")
    ts = "1739923528"
    digest = hmac.new(b"secret", b"v0:" + ts.encode("utf-8") + b":" + raw, hashlib.sha256).hexdigest()
    signature = f"v0={digest}"
    assert verify_zoom_signature(raw, ts, signature, "secret")


def test_extract_transcript_events_from_rtms_segments():
    payload = {
        "event": "meeting.transcript_received",
        "event_ts": 1739923528123,
        "payload": {
            "content": {
                "transcript_segments": [
                    {"user_name": "Alice", "text": "Can you explain your DR story?"},
                    {"user_name": "Bob", "text": "Sure, absolutely."},
                ]
            }
        },
    }
    events = extract_transcript_events(payload)
    assert len(events) == 2
    assert events[0].speaker == "Alice"
    assert events[0].text == "Can you explain your DR story?"
    assert events[0].source == "zoom"

