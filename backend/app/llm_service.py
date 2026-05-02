import json
import logging
from pathlib import Path
import ssl
import urllib.error
import urllib.request

from app.config import settings
from app.rag_service import RagResult


def _load_system_prompt() -> str:
    try:
        return settings.llm_system_prompt_path.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        return (
            "You are a concise support chatbot. Answer only from supplied context "
            "when context is present, and ask for missing order details when needed."
        )


def _history_text(history: list[dict], limit: int = 6) -> str:
    recent = history[-limit:]
    lines: list[str] = []
    for message in recent:
        role = str(message.get("role", "unknown"))
        text = str(message.get("text", ""))
        if text:
            lines.append(f"{role}: {text}")

    return "\n".join(lines)


logger = logging.getLogger(__name__)


def _build_ssl_context() -> ssl.SSLContext | None:
    """Build an explicit SSL context to avoid local trust-store issues."""
    try:
        import certifi  # type: ignore

        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        bundled_ca = Path(__file__).resolve().parents[1] / "cacert.pem"
        if bundled_ca.exists():
            logger.info("Using bundled CA bundle: %s", bundled_ca)
            return ssl.create_default_context(cafile=str(bundled_ca))

        logger.warning(
            "certifi not installed and no bundled CA found; using system certificate store",
        )
        return None


def _openai_chat_completion(messages: list[dict[str, str]]) -> str:
    if not settings.llm_api_key:
        raise RuntimeError("LLM API key is missing")

    payload = {
        "model": settings.llm_model,
        "messages": messages,
        "temperature": settings.llm_temperature,
        "max_tokens": settings.llm_max_tokens,
    }
    request = urllib.request.Request(
        f"{settings.llm_base_url}/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {settings.llm_api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    ssl_context = _build_ssl_context()

    try:
        with urllib.request.urlopen(
            request,
            timeout=settings.llm_timeout_seconds,
            context=ssl_context,
        ) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace") if exc.fp else ""
        logger.warning("LLM HTTP error %s: %s", exc.code, body)
        raise RuntimeError(f"LLM HTTP {exc.code}: {body}") from exc
    except (OSError, urllib.error.URLError, json.JSONDecodeError) as exc:
        logger.warning("LLM request failed: %s", exc)
        raise RuntimeError(f"LLM request failed: {exc}") from exc

    choices = data.get("choices", [])
    if not choices:
        raise RuntimeError("LLM returned no choices")

    content = choices[0].get("message", {}).get("content")
    if not isinstance(content, str):
        raise RuntimeError("LLM returned non-text content")

    answer = content.strip()
    if not answer:
        raise RuntimeError("LLM returned empty content")

    return answer


def generate_grounded_reply(
    message: str,
    intent: str,
    history: list[dict],
    rag_result: RagResult | None,
) -> str | None:
    if not settings.llm_enabled:
        return None

    provider = settings.llm_provider.strip().lower()
    if provider not in {"openai", "openai-compatible", "compatible"}:
        return None

    context = rag_result.context_text() if rag_result else "No retrieved context."
    messages = [
        {"role": "system", "content": _load_system_prompt()},
        {
            "role": "user",
            "content": (
                f"Intent: {intent}\n"
                f"Recent conversation:\n{_history_text(history)}\n\n"
                f"Retrieved knowledge:\n{context}\n\n"
                f"User message: {message}\n\n"
                "Reply in a helpful, short, grounded way. If the context does not "
                "contain the answer, say what detail is needed instead of inventing."
            ),
        },
    ]

    return _openai_chat_completion(messages)
