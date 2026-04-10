# Zoom Live Assistant

A starter tool for real-time call assistance:

1. Ingest transcript events from Zoom (or any source).
2. Detect when a customer asks a question.
3. Send recent transcript context + question to ChatGPT.
4. Return a concise suggested answer you can read to the customer.

## Important note about Zoom integration

This repo includes the core runtime assistant and API/CLI interfaces.  
Direct Zoom call audio capture/transcription depends on your Zoom account type and selected integration method (Zoom Apps/SDK/webhooks or external audio capture + ASR).  
Use this service as the central "brain" that receives transcript lines and returns answers.

## Quick start

### 1) Install

```bash
cd /workspace/zoom-live-assistant
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

### 2) Configure environment

Create `.env`:

```env
OPENAI_API_KEY=your_openai_api_key
OPENAI_MODEL=gpt-4o-mini
MIN_QUESTION_LENGTH=12
MAX_CONTEXT_MESSAGES=30
API_HOST=0.0.0.0
API_PORT=8080
ZOOM_WEBHOOK_SECRET=your_zoom_webhook_secret
VERIFY_ZOOM_SIGNATURES=true
```

### 3) Run API mode

```bash
zoom-live-assistant-api
```

Ingest transcript line:

```bash
curl -X POST "http://localhost:8080/ingest" \
  -H "Content-Type: application/json" \
  -d '{
    "speaker":"customer",
    "text":"Can you explain how your pricing scales with usage?",
    "source":"zoom"
  }'
```

Or send a Zoom webhook envelope:

```bash
curl -X POST "http://localhost:8080/zoom/webhook" \
  -H "Content-Type: application/json" \
  -d '{
    "event":"meeting.transcript_received",
    "event_ts":1739923528123,
    "payload":{
      "content":{
        "transcript_segments":[
          {"user_name":"customer","text":"Can you explain your pricing model?"}
        ]
      }
    }
  }'
```

If a question is detected, response includes:

```json
{
  "accepted": true,
  "answer": {
    "question": "...",
    "answer": "...suggested response...",
    "speaker": "customer",
    "timestamp": "..."
  },
  "context_size": 14
}
```

### 4) Run CLI mode (stdin)

Plain text mode:

```bash
printf "Hello team\nCan you describe your SLA commitments?\n" | zoom-live-assistant-cli
```

JSONL mode:

```bash
printf '{"speaker":"customer","text":"How fast can we migrate?"}\n' | zoom-live-assistant-cli --jsonl
```

## How to connect this to Zoom in practice

Common production pattern:

- Zoom transcript source -> your "bridge" service
- Bridge sends each transcript line to `POST /ingest`
- On non-null `answer`, display in desktop overlay or private chat panel

Concrete Zoom webhook path supported in this project:

- Set Zoom Event Notification endpoint to: `https://<your-domain>/zoom/webhook`
- Supports Zoom challenge event `endpoint.url_validation`
- Supports signature verification via `x-zm-signature` and `x-zm-request-timestamp`
- Parses transcript payload variants from:
  - `payload.content.transcript_segments[]`
  - `payload.content.text` / `payload.content.transcript`
  - `payload.object.transcript[]` / `payload.object.transcript_entries[]`
  - `payload.object.text`

### Desktop overlay UI

Run the overlay window (always on top) to see answers instantly:

```bash
zoom-live-assistant-overlay --ws-url ws://127.0.0.1:8080/ws/answers
```

How it works:

- API publishes each generated answer to websocket endpoint `ws://.../ws/answers`
- Overlay subscribes and updates question + suggested answer in near-real-time
- Use this while you are on a call; keep human-in-the-loop and read/adjust responses

You can build the bridge with:

- Zoom meeting transcript webhooks/events (if available in your plan)
- Zoom SDK app capturing transcript events
- Audio capture pipeline + speech-to-text (Whisper/Deepgram/Azure) then forwarding text here

## Safety guidance

- Keep a human in the loop; do not auto-send answers to customers.
- Log all suggestions for QA and compliance.
- Add domain constraints into `ASSISTANT_SYSTEM_PROMPT`.
- Mask sensitive data before sending transcripts to external APIs where required.

## Tests

```bash
pytest
```
