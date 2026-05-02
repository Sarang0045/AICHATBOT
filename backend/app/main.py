import json
from pathlib import Path
import ssl
import urllib.error
import urllib.parse
import urllib.request
from uuid import uuid4

from fastapi import Body, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.intent_detector import detect_intent
from app.language_service import detect_language, language_name
from app.llm_service import generate_grounded_reply
from app.memory import memory
from app.model_service import train_intent_model
from app.rag_service import retrieve_knowledge
from app.response_engine import create_reply
from app.sentiment_service import analyze_sentiment
from app.schemas import (
    AuthResponse,
    ChatRequest,
    ChatResponse,
    HistoryResponse,
    MemoryStatusResponse,
    TrainResponse,
)

app = FastAPI(
    title="AI Chatbot With Context Memory",
    description="Chatbot backend with ML intent classification, RAG, and memory.",
    version="3.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
        "http://127.0.0.1:5175",
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:5175",
        "https://aichatbot-nine-pi.vercel.app",
        "https://aichatbot-git-main-sarang-choudharys-projects.vercel.app",
        "https://aichatbot-d7vbo9fyp-sarang-choudharys-projects.vercel.app"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Validation on startup
if not settings.google_client_id:
    print("⚠️  WARNING: GOOGLE_CLIENT_ID not configured. Google Sign-In will not work.")
else:
    print(f"✅ Google OAuth configured: {settings.google_client_id[:30]}...")


@app.get("/")
def root() -> dict:
    return {
        "message": "AI Chatbot backend is running.",
        "docs": "Open http://127.0.0.1:8000/docs",
    }


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "memory": memory.storage_type}


@app.get("/memory/status", response_model=MemoryStatusResponse)
def memory_status() -> MemoryStatusResponse:
    using_database = memory.storage_type == "mongodb"

    note = (
        "Conversation history is stored permanently in MongoDB."
        if using_database
        else "Conversation history is temporary. Set MONGO_URL to use MongoDB."
    )

    return MemoryStatusResponse(
        storage_type=memory.storage_type,
        using_database=using_database,
        note=note,
    )


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    user_id = request.user_id or "guest"
    session_id = request.session_id or f"session_{uuid4().hex}"
    recent_history = memory.get_recent_messages(session_id=session_id, user_id=user_id)
    intent, confidence, intent_source = detect_intent(request.message)
    sentiment = analyze_sentiment(request.message)
    language = language_name(detect_language(request.message))

    rag_result = retrieve_knowledge(request.message)
    rag_used = rag_result is not None
    rag_source = rag_result.primary_source if rag_result else None
    rag_sources = rag_result.source_titles if rag_result else []
    rag_confidence = rag_result.best_score if rag_result else None

    try:
        llm_reply = generate_grounded_reply(
            message=request.message,
            intent=intent,
            history=recent_history,
            rag_result=rag_result,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    if settings.llm_enabled:
        if not llm_reply:
            raise HTTPException(
                status_code=502,
                detail="LLM returned no reply",
            )
        reply = llm_reply
        generation_source = "llm"
    else:
        reply = create_reply(
            intent,
            request.message,
            recent_history,
            rag_result=rag_result,
        )
        generation_source = "rag_template" if rag_used else "template"

    memory.add_message(
        session_id=session_id,
        role="user",
        text=request.message,
        intent=intent,
        user_id=user_id,
    )
    memory.add_message(
        session_id=session_id,
        role="bot",
        text=reply,
        intent=None,
        user_id=user_id,
    )

    return ChatResponse(
        reply=reply,
        intent=intent,
        session_id=session_id,
        user_id=user_id,
        confidence=confidence,
        intent_source=intent_source,
        sentiment=sentiment,
        language=language,
        rag_used=rag_used,
        rag_source=rag_source,
        rag_sources=rag_sources,
        rag_confidence=rag_confidence,
        generation_source=generation_source,
    )


@app.get("/history/{user_id}/{session_id}", response_model=HistoryResponse)
def user_history(user_id: str, session_id: str) -> HistoryResponse:
    return HistoryResponse(
        session_id=session_id,
        messages=memory.get_history(session_id=session_id, user_id=user_id),
    )


@app.post("/train", response_model=TrainResponse)
def train() -> TrainResponse:
    result = train_intent_model()
    return TrainResponse(**result)


@app.post("/auth/guest", response_model=AuthResponse)
def guest_auth() -> AuthResponse:
    return AuthResponse(
        user_id=f"guest:{uuid4().hex}",
        session_id=f"session_{uuid4().hex}",
        auth_provider="guest",
    )


def _verify_google_token(token: str) -> dict:
    """Verify Google ID token using Google's tokeninfo endpoint"""
    print(f"🔍 Verifying Google token (length: {len(token)})")

    query = urllib.parse.urlencode({"id_token": token})
    request = urllib.request.Request(
        f"https://oauth2.googleapis.com/tokeninfo?{query}",
        method="GET",
    )

    # Use certifi's CA bundle to avoid local trust-store issues on some macOS setups.
    ssl_context = None
    try:
        import certifi  # type: ignore

        ssl_context = ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        bundled_ca = Path(__file__).resolve().parents[1] / "cacert.pem"
        if bundled_ca.exists():
            ssl_context = ssl.create_default_context(cafile=str(bundled_ca))
            print(f"ℹ️ Using bundled CA bundle: {bundled_ca}")
        else:
            print("⚠️ certifi not installed and no bundled CA found; falling back to system certificate store")

    try:
        with urllib.request.urlopen(request, timeout=8, context=ssl_context) as response:
            info = json.loads(response.read().decode("utf-8"))
            print(f"✅ Token verified. Info keys: {list(info.keys())}")
            return info
    except urllib.error.HTTPError as exc:
        print(f"❌ HTTP Error {exc.code}: {exc.read().decode('utf-8')}")
        raise HTTPException(
            status_code=401,
            detail=f"Google token verification failed (HTTP {exc.code})",
        ) from exc
    except (OSError, urllib.error.URLError) as exc:
        print(f"❌ Network error: {exc}")
        raise HTTPException(
            status_code=401,
            detail="Google token verification failed: network error",
        ) from exc
    except json.JSONDecodeError as exc:
        print(f"❌ JSON decode error: {exc}")
        raise HTTPException(
            status_code=401,
            detail="Google token verification failed: invalid response",
        ) from exc


@app.post("/auth/google", response_model=AuthResponse)
def google_auth(payload: dict = Body(...)) -> AuthResponse:
    """Google OAuth endpoint - expects {"id_token": "..."} in request body"""
    print(f"📨 /auth/google called. Payload keys: {list(payload.keys())}")
    
    # Get token from either id_token or credential field
    id_token = payload.get("id_token") or payload.get("credential")
    if not id_token:
        print(f"❌ No token found in payload")
        raise HTTPException(
            status_code=400,
            detail="Missing id_token or credential in request body",
        )

    print(f"🔐 Token received (length: {len(str(id_token))})")

    # Verify token with Google
    try:
        info = _verify_google_token(str(id_token))
    except HTTPException as exc:
        print(f"❌ Token verification failed: {exc.detail}")
        raise

    # Extract fields
    sub = info.get("sub")
    email = info.get("email")
    email_verified = info.get("email_verified")
    audience = info.get("aud")
    name = info.get("name")
    picture = info.get("picture")

    print(f"📋 Token info - sub: {sub}, email: {email}, verified: {email_verified}, aud: {audience}")

    # Validate email is verified
    if str(email_verified).lower() != "true":
        print(f"❌ Email not verified: {email_verified}")
        raise HTTPException(
            status_code=401,
            detail="Google account email is not verified",
        )

    # Validate required fields
    if not sub or not email:
        print(f"❌ Missing required fields: sub={sub}, email={email}")
        raise HTTPException(
            status_code=401,
            detail="Google account missing required information",
        )

    # Validate audience matches (if configured)
    if settings.google_client_id:
        print(f"🔒 Checking audience: token has '{audience}', backend expects '{settings.google_client_id}'")
        if audience != settings.google_client_id:
            print(f"❌ AUDIENCE MISMATCH!")
            raise HTTPException(
                status_code=401,
                detail=f"Token audience mismatch. Expected {settings.google_client_id}, got {audience}",
            )
    else:
        print(f"⚠️  GOOGLE_CLIENT_ID not configured - skipping audience validation")

    print(f"✅ Google auth successful for {email}")

    return AuthResponse(
        user_id=f"google:{sub}",
        email=str(email),
        name=name,
        picture=picture,
        session_id=f"session_{uuid4().hex}",
        auth_provider="google",
    )
