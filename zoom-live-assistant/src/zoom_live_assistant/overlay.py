from __future__ import annotations

import argparse
import json
import queue
import threading
import tkinter as tk
from tkinter import ttk

import websocket


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Desktop overlay for live answer suggestions."
    )
    parser.add_argument(
        "--ws-url",
        default="ws://127.0.0.1:8080/ws/answers",
        help="WebSocket URL served by zoom-live-assistant-api",
    )
    parser.add_argument(
        "--title",
        default="Live Call Assistant",
        help="Window title text.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    incoming: "queue.Queue[dict]" = queue.Queue()
    status = {"connected": False, "error": ""}

    def on_open(_: websocket.WebSocketApp) -> None:
        status["connected"] = True
        status["error"] = ""

    def on_message(_: websocket.WebSocketApp, message: str) -> None:
        try:
            payload = json.loads(message)
            if isinstance(payload, dict):
                incoming.put(payload)
        except json.JSONDecodeError:
            pass

    def on_close(_: websocket.WebSocketApp, __, ___) -> None:
        status["connected"] = False

    def on_error(_: websocket.WebSocketApp, error: Exception) -> None:
        status["connected"] = False
        status["error"] = str(error)

    ws_app = websocket.WebSocketApp(
        args.ws_url,
        on_open=on_open,
        on_message=on_message,
        on_close=on_close,
        on_error=on_error,
    )
    ws_thread = threading.Thread(
        target=lambda: ws_app.run_forever(ping_interval=20, ping_timeout=10),
        daemon=True,
    )
    ws_thread.start()

    root = tk.Tk()
    root.title(args.title)
    root.geometry("640x360")
    root.attributes("-topmost", True)

    container = ttk.Frame(root, padding=12)
    container.pack(fill=tk.BOTH, expand=True)

    connection_var = tk.StringVar(value=f"Connecting to {args.ws_url}...")
    question_var = tk.StringVar(value="Question: (waiting)")

    ttk.Label(container, textvariable=connection_var).pack(anchor="w")
    ttk.Label(container, textvariable=question_var, wraplength=600).pack(
        anchor="w", pady=(8, 8)
    )
    answer_box = tk.Text(container, height=12, wrap=tk.WORD)
    answer_box.pack(fill=tk.BOTH, expand=True)
    answer_box.insert("1.0", "Waiting for suggested answers...")
    answer_box.config(state=tk.DISABLED)

    def set_answer(text: str) -> None:
        answer_box.config(state=tk.NORMAL)
        answer_box.delete("1.0", tk.END)
        answer_box.insert("1.0", text)
        answer_box.config(state=tk.DISABLED)

    def tick() -> None:
        if status["connected"]:
            connection_var.set(f"Connected: {args.ws_url}")
        elif status["error"]:
            connection_var.set(f"Disconnected: {status['error']}")
        else:
            connection_var.set(f"Disconnected: {args.ws_url}")

        while not incoming.empty():
            payload = incoming.get()
            question = payload.get("question", "")
            answer = payload.get("answer", "")
            speaker = payload.get("speaker", "customer")
            question_var.set(f"Question ({speaker}): {question or '(n/a)'}")
            set_answer(answer or "(empty answer)")
        root.after(200, tick)

    def on_close_window() -> None:
        try:
            ws_app.close()
        finally:
            root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_close_window)
    root.after(200, tick)
    root.mainloop()


if __name__ == "__main__":
    main()
