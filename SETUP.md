# AI Chatbot Setup

Small support chatbot with a React frontend and FastAPI backend. It uses local ML for intent detection, a small knowledge base for RAG, optional LLM generation, Google login, and guest sessions.

## Backend

Use Python 3.12 for this project. The default `python3` on this machine may be newer than some pinned FastAPI dependencies.

```bash
python3.12 -m venv .venv312
.venv312/bin/python -m pip install -r backend/app/requirements.txt
cd backend
../.venv312/bin/uvicorn app.main:app --reload --port 8000
```

Optional backend `.env` values:

```env
MONGO_URL=mongodb://localhost:27017
MONGO_DATABASE=chatbot_db
MONGO_COLLECTION=conversations

GOOGLE_CLIENT_ID=your_google_client_id

LLM_PROVIDER=openai
OPENAI_API_KEY=your_api_key
LLM_MODEL=gpt-4o-mini
```

Without MongoDB, chats use temporary in-memory storage. Without an LLM key, replies still work through local ML, RAG, and templates.

## Frontend

```bash
cd frontend
npm install
npm run dev
```

Optional frontend `.env` values:

```env
VITE_API_URL=http://127.0.0.1:8000
VITE_GOOGLE_CLIENT_ID=your_google_client_id
```

If Google is not configured, use **Continue as Guest**.

## Useful Checks

```bash
.venv312/bin/python -m compileall backend/app
cd frontend && npm run build
```

Try these messages:

- `hello`
- `what is your refund policy?`
- `how long does delivery take?`
- `I am angry about my order`
- `नमस्ते`
