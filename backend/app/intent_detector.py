import re

from app.config import settings


def clean_text(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def detect_intent(message: str) -> tuple[str, float | None, str]:
    # Import here to avoid circular imports with model_service.clean_text.
    from app.model_service import predict_intent_with_model

    intent, confidence = predict_intent_with_model(message)

    if (
        intent is not None
        and confidence is not None
        and confidence >= settings.intent_model_confidence_threshold
    ):
        return intent, confidence, "ml_model"
    return "unknown", confidence, "ml_model"
