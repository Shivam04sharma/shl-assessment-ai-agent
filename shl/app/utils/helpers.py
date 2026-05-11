import re
from typing import List
from app.models.schemas import Message


def count_turns(messages: List[Message]) -> int:
    return len(messages)


def get_last_user_message(messages: List[Message]) -> str:
    for msg in reversed(messages):
        if msg.role == "user":
            return msg.content
    return ""


def clean_json_response(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^```(?:json)?\n?", "", text)
    text = re.sub(r"\n?```$", "", text)
    return text.strip()


def truncate_text(text: str, max_chars: int = 500) -> str:
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "..."
