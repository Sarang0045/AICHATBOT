# AI Chatbot Project

A full-stack support chatbot with intelligent intent detection, sentiment analysis, and optional LLM integration.

## 📋 Project Overview

This is a React + FastAPI chatbot that can:

- Detect user intent (ML model + keyword fallback)
- Analyze sentiment and language
- Retrieve answers from a knowledge base (RAG)
- Generate grounded responses using OpenAI-compatible LLM APIs
- Store conversation history in memory or MongoDB
- Support guest and Google authentication
- Retrain intent models from CSV data

## ✨ Main Features

- **Smart Chat UI** - Typing indicator, voice input, metadata badges
- **Intent Detection** - ML model with confidence scoring, keyword rules fallback
- **RAG System** - TF-IDF + keyword overlap + MMR retrieval from knowledge base
- **Sentiment & Language** - Real-time analysis with UI labels
- **LLM Integration** - Optional grounded response generation
- **Authentication** - Guest auth and Google OAuth
- **Conversation Memory** - In-memory or MongoDB storage with history retrieval
- **Model Training** - Retrain intent classifier from intents.csv

## 🏗️ Project Structure

```
AICHATBOT/
├── frontend/                  # React + Vite
│   ├── src/
│   │   ├── App.jsx           # Main app, session management
│   │   ├── components/       # Chat UI components
│   │   ├── api/              # Backend API calls
│   │   └── style/            # CSS styling
│   ├── package.json
│   └── vite.config.js
│
├── backend/                   # FastAPI
│   ├── app/
│   │   ├── main.py          # Routes: /chat, /auth, /train, /memory
│   │   ├── intent_detector.py
│   │   ├── sentiment_service.py
│   │   ├── language_service.py
│   │   ├── rag_service.py
│   │   ├── llm_service.py
│   │   ├── response_engine.py
│   │   ├── memory.py
│   │   ├── model_service.py
│   │   └── requirements.txt
│   ├── data/                 # Knowledge base & rules
│   │   ├── knowledge_base.json
│   │   ├── intent_rules.json
│   │   ├── sentiment_lexicon.json
│   │   ├── language_hints.json
│   │   └── llm_system_prompt.txt
│   └── models/
│       └── intent_model.joblib
│
├── intents.csv              # Intent training data
├── SETUP.md                 # Installation instructions
└── readme.md                # This file
```

## 🚀 Quick Start

### Prerequisites

- **Python 3.12** (backend - required for compatible FastAPI dependencies)
- Node.js 16+ (frontend)
- MongoDB (optional, for persistent conversation storage)
- OpenAI API key (optional, for LLM response generation)

### Backend Setup

```bash
# Use Python 3.12 for this project
python3.12 -m venv .venv312
source .venv312/bin/activate
.venv312/bin/python -m pip install -r backend/app/requirements.txt

cd backend
../.venv312/bin/uvicorn app.main:app --reload --port 8000
```

Backend runs at `http://127.0.0.1:8000`

Render deployment should also use Python 3.12 via a `.python-version` file at the service root. If the backend is configured as the Render root directory, keep `backend/.python-version` in place.

### Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

Frontend runs at `http://localhost:5173` (default Vite port)

## 📡 API Routes

### Chat

- **POST** `/chat` - Send message and get reply
  - Request: `{ user_id, session_id, user_message }`
  - Response: `{ reply, intent, confidence, sentiment, language, rag_sources, generation_source }`

### Authentication

- **POST** `/auth/guest` - Create guest session
  - Response: `{ user_id, session_id }`
- **POST** `/auth/google` - Verify Google token
  - Request: `{ token }`
  - Response: `{ user_id, session_id, email, name }`

### Memory & History

- **GET** `/memory/status` - Check storage backend (memory/mongodb)
- **GET** `/history/{user_id}/{session_id}` - Retrieve chat history

### Training

- **POST** `/train` - Retrain intent model from intents.csv
  - Response: `{ accuracy, model_version }`

## 🔄 Chat Flow (End-to-End)

1. **User Input** (`ChatInput.jsx`)
   - User types message and submits

2. **Frontend** (`App.jsx` → `chatApi.js`)
   - Sends POST to `/chat` with user_id, session_id, message

3. **Backend Processing** (`main.py`)
   - Gets recent chat history
   - Detects intent (ML model or keyword rules)
   - Analyzes sentiment
   - Detects language
   - Retrieves knowledge base context (RAG)
   - Optional: Generates LLM response
   - Falls back: Uses templates + RAG if no LLM
   - Saves conversation to memory

4. **Frontend Render** (`ChatWindow.jsx` → `MessageBubble.jsx`)
   - Displays message with metadata badges
   - Shows intent, confidence, sentiment, language, sources

## 🧠 Knowledge Base & Configuration

All data files are in `backend/data/`:

| File                            | Purpose                             |
| ------------------------------- | ----------------------------------- |
| `knowledge_base.json`           | FAQ/answer pairs for RAG retrieval  |
| `intent_rules.json`             | Keyword-based intent fallback rules |
| `sentiment_lexicon.json`        | Words mapped to sentiment scores    |
| `language_hints.json`           | Keywords for language detection     |
| `llm_system_prompt.txt`         | System prompt for LLM requests      |
| `../intents.csv`                | Training data for ML intent model   |
| `../models/intent_model.joblib` | Trained scikit-learn model          |

## 🔐 Environment Variables

### Backend `.env` (optional - sensible defaults included)

````env
# MongoDB Configuration (optional - without it, uses in-memory storage)
MONGO_URL=mongodb://localhost:27017
MONGO_DATABASE=chatbot_db
MONGO_COLLECTION=conversations

# Intent Detection Model
INTENT_MODEL_CONFIDENCE_THRESHOLD=0.58

# RAG Configuration
RAG_TOP_K=3
RAG🧪 Testing & Validation

```bash
# Check backend code
.venv312/bin/python -m compileall backend/app

# Build frontend
cd frontend && npm run build
````

### Test Messages to Try

- `hello` - Basic greeting
- `what is your refund policy?` - Knowledge base retrieval
- `how long does delivery take?` - RAG + template response
- `I am angry about my order` - Sentiment analysis
- `नमस्ते` - Multi-language support

## 🔗 Google OAuth Setup (Optional)

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project and enable Google+ API
3. Create OAuth 2.0 Client ID (Web application type)
4. Add Authorized JavaScript origins:
   - `http://localhost:5173`
   - `http://127.0.0.1:5173`
5. Add Authorized redirect URIs (same as above)
6. Copy the Client ID to `.env` files:
   - Backend: `GOOGLE_CLIENT_ID`
   - Frontend: `VITE_GOOGLE_CLIENT_ID`

## 📦 Deployment Options

### Recommended: Vercel + Railway

**Frontend (Vercel)**

```bash
cd frontend
vercel deploy
```

**Backend (Railway)**

- Connect GitHub repo to Railway
- Set `VITE_API_URL` environment variable in Vercel
- Set backend env vars (OpenAI key, MongoDB, etc.) in Railway

### Alternative Platforms

- **All-in-one**: PythonAnywhere (backend) + Netlify (frontend)
- **Docker**: Fly.io, Railway, Render
- **Production**: AWS (CloudFront + S3 for frontend, App Runner for backend) if not configured)
  VITE_GOOGLE_CLIENT_ID=your_google_client_id

````

**Note:** Without MongoDB, conversations are stored in memory (lost on restart). Without LLM API, responses still work via local ML, RAG, and templates.

## 📦 Deployment Options

### Recommended: Vercel + Railway

**Frontend (Vercel)**

```bash
cd frontend
vercel deploy
````

**Backend (Railway)**

- Connect GitHub repo to Railway
- Set `VITE_API_URL` environment variable in Vercel
- Set backend env vars (OpenAI key, MongoDB, etc.) in Railway

### Alternative Platforms

- **All-in-one**: PythonAnywhere (backend) + Netlify (frontend)
- **Docker**: Fly.io, Railway, Render
- **Production**: AWS (CloudFront + S3 for frontend, App Runner for backend)

See [SETUP.md](SETUP.md) for detailed deployment instructions.

## 🧪 Testing & Development

### Run Backend Tests

```bash
cd backend
pytest
```

### Retrain Intent Model

```bash
# POST to /train endpoint
curl -X POST http://127.0.0.1:8000/train
```

### Check Memory Status

```bash
curl http://127.0.0.1:8000/memory/status
```

## 📝 Project Stack

| Layer    | Technology                            |
| -------- | ------------------------------------- |
| Frontend | React, Vite, Lucide Icons             |
| Backend  | FastAPI, Python                       |
| ML       | scikit-learn (intent), TF-IDF (RAG)   |
| Storage  | MongoDB (optional), In-memory default |
| Auth     | Google OAuth, Session tokens          |
| LLM      | OpenAI-compatible API (optional)      |

## 🤝 Contributing

1. Clone the repo
2. Create a feature branch
3. Make changes to frontend or backend
4. Test locally
5. Submit pull request

## 📄 License

MIT License

## 📧 Support

For issues or questions, please open a GitHub issue.

---

**Last Updated:** May 2, 2026

# AICHATBOT

# AICHATBOT

# CHATBOTAI
