import json

from app.config import settings
from app.intent_detector import clean_text


_sentiment_lexicon: dict[str, set[str]] | None = None


def load_sentiment_lexicon() -> dict[str, set[str]]:
    global _sentiment_lexicon

    if _sentiment_lexicon is not None:
        return _sentiment_lexicon

    try:
        with settings.sentiment_lexicon_path.open("r", encoding="utf-8") as file:
            raw_lexicon = json.load(file)
    except FileNotFoundError:
        raw_lexicon = {}

    _sentiment_lexicon = {
        label: {clean_text(str(word)) for word in words}
        for label, words in raw_lexicon.items()
        if isinstance(words, list)
    }
    return _sentiment_lexicon

def analyze_sentiment(message: str) -> str:
    lexicon = load_sentiment_lexicon()
    words = clean_text(message).split()
    positive_count = sum(1 for word in words if word in lexicon.get("positive", set()))
    negative_count = sum(1 for word in words if word in lexicon.get("negative", set()))

    if positive_count > negative_count:
        return "positive"

    if negative_count > positive_count:
        return "negative"

    return "neutral"
