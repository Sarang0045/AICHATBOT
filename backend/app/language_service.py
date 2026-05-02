import json

from app.config import settings
from app.intent_detector import clean_text


_language_hints: dict | None = None


def load_language_hints() -> dict:
    global _language_hints

    if _language_hints is not None:
        return _language_hints

    try:
        with settings.language_hints_path.open("r", encoding="utf-8") as file:
            raw_hints = json.load(file)
    except FileNotFoundError:
        raw_hints = {"en": {"name": "English", "hints": [], "unicode_ranges": []}}

    _language_hints = raw_hints
    return _language_hints


def _has_unicode_range(message: str, ranges: list[list[str]]) -> bool:
    for start_hex, end_hex in ranges:
        start = int(start_hex, 16)
        end = int(end_hex, 16)
        if any(start <= ord(character) <= end for character in message):
            return True

    return False


def detect_language(message: str) -> str:
    language_hints = load_language_hints()
    words = set(clean_text(message).split())
    for language_code, config in language_hints.items():
        unicode_ranges = config.get("unicode_ranges", [])
        if unicode_ranges and _has_unicode_range(message, unicode_ranges):
            return language_code
    for language_code, config in language_hints.items():
        hints = {clean_text(str(word)) for word in config.get("hints", [])}
        if words & hints:
            return language_code
    return "en" if "en" in language_hints else next(iter(language_hints), "en")


def language_name(language_code: str) -> str:
    language_hints = load_language_hints()
    language_config = language_hints.get(language_code, {})
    return language_config.get("name", language_code)
