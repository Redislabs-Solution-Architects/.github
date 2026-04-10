from zoom_live_assistant.question_detector import is_question, newest_question


def test_is_question_marks_explicit_question():
    assert is_question("Can you explain your pricing tiers?")


def test_is_question_ignores_short_text():
    assert not is_question("Why?", min_len=10)


def test_newest_question_returns_latest_detected():
    texts = [
        "Hello everyone",
        "This is the architecture overview",
        "How do you handle failover in Redis Enterprise?",
        "Great, thanks",
    ]
    assert newest_question(texts) == "How do you handle failover in Redis Enterprise?"
