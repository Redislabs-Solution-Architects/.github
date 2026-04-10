from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime

from dotenv import load_dotenv

from zoom_live_assistant.assistant import LiveAssistant
from zoom_live_assistant.config import get_settings
from zoom_live_assistant.models import TranscriptEvent


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Read transcript lines from stdin and print live answer suggestions."
    )
    parser.add_argument(
        "--speaker",
        default="customer",
        help="Default speaker name when plain text lines are provided.",
    )
    parser.add_argument(
        "--jsonl",
        action="store_true",
        help=(
            "Expect JSON lines with keys: speaker, text, optional timestamp, optional source. "
            "Without this flag, each input line is treated as transcript text."
        ),
    )
    return parser.parse_args()


def main() -> None:
    load_dotenv()
    args = parse_args()
    settings = get_settings()
    assistant = LiveAssistant(settings=settings)

    for raw in sys.stdin:
        line = raw.strip()
        if not line:
            continue

        if args.jsonl:
            payload = json.loads(line)
            event = TranscriptEvent(
                speaker=payload.get("speaker", args.speaker),
                text=payload["text"],
                timestamp=datetime.fromisoformat(payload["timestamp"])
                if payload.get("timestamp")
                else datetime.utcnow(),
                source=payload.get("source", "manual"),
            )
        else:
            event = TranscriptEvent(speaker=args.speaker, text=line, source="manual")

        answer = assistant.ingest_event(event)
        if answer:
            print("=== QUESTION DETECTED ===")
            print(answer.question)
            print("=== SUGGESTED ANSWER ===")
            print(answer.answer)
            print()


if __name__ == "__main__":
    main()
