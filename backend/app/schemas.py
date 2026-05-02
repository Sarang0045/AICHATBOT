from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """Data expected from the user when they send a chat message."""

    user_id: str | None = Field(default=None, examples=["google:123"])
    session_id: str | None = Field(default=None, examples=["session_abc"])
    message: str = Field(..., min_length=1, examples=["Hello, where is my order?"])


class ChatResponse(BaseModel):
    """Data returned by the chatbot after processing a message."""

    reply: str
    intent: str
    session_id: str
    user_id: str
    confidence: float | None = None
    intent_source: str
    sentiment: str | None = None
    language: str | None = None
    rag_used: bool = False
    rag_source: str | None = None
    rag_sources: list[str] = Field(default_factory=list)
    rag_confidence: float | None = None
    generation_source: str = "template"


class Message(BaseModel):
    """One saved message in a conversation."""

    role: str
    text: str
    intent: str | None = None
    timestamp: str


class HistoryResponse(BaseModel):
    """Conversation history returned for one session."""

    session_id: str
    messages: list[Message]


class MemoryStatusResponse(BaseModel):
    """Shows which memory storage backend the app is using."""

    storage_type: str
    using_database: bool
    note: str


class AuthResponse(BaseModel):
    """Identity returned after Google login/signup or guest session creation."""

    user_id: str
    session_id: str
    email: str | None = None
    name: str | None = None
    picture: str | None = None
    auth_provider: str


class TrainResponse(BaseModel):
    """Response returned after training the ML model."""

    message: str
    total_examples: int | None = None
    accuracy: float | None = None
    model_path: str | None = None
    classification_report: dict | None = None
