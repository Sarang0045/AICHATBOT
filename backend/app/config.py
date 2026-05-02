import os
from pathlib import Path

from dotenv import load_dotenv


BACKEND_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = BACKEND_DIR / ".env"

load_dotenv(ENV_FILE)


class Settings:
    mongo_url: str | None = os.getenv("MONGO_URL")
    mongo_database: str = os.getenv("MONGO_DATABASE", "chatbot_db")
    mongo_collection: str = os.getenv("MONGO_COLLECTION", "conversations")
    intent_model_confidence_threshold: float = float(
        os.getenv("INTENT_MODEL_CONFIDENCE_THRESHOLD", "0.58")
    )
    rag_top_k: int = int(os.getenv("RAG_TOP_K", "3"))
    rag_score_threshold: float = float(os.getenv("RAG_SCORE_THRESHOLD", "0.12"))
    rag_mmr_lambda: float = float(os.getenv("RAG_MMR_LAMBDA", "0.72"))
    llm_enabled: bool = os.getenv("LLM_ENABLED", "true").lower() == "true"
    llm_provider: str = os.getenv("LLM_PROVIDER", "openai-compatible")
    llm_api_key: str | None = os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY")
    llm_base_url: str = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    llm_model: str = os.getenv("LLM_MODEL", "gpt-4o-mini")
    llm_temperature: float = float(os.getenv("LLM_TEMPERATURE", "0.2"))
    llm_max_tokens: int = int(os.getenv("LLM_MAX_TOKENS", "220"))
    llm_timeout_seconds: int = int(os.getenv("LLM_TIMEOUT_SECONDS", "12"))
    google_client_id: str | None = os.getenv("GOOGLE_CLIENT_ID")

    language_hints_path: Path = BACKEND_DIR / "data" / "language_hints.json"
    sentiment_lexicon_path: Path = BACKEND_DIR / "data" / "sentiment_lexicon.json"
    llm_system_prompt_path: Path = BACKEND_DIR / "data" / "llm_system_prompt.txt"


settings = Settings()
