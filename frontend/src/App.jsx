import { useEffect, useMemo, useState } from "react";
import { Menu, Plus } from "lucide-react";

import { authGoogle, getChatHistory, sendChatMessage, trainModel } from "./api/chatApi";
import ChatInput from "./components/ChatInput.jsx";
import ChatWindow from "./components/ChatWindow.jsx";

function createSessionId() {
  return `session_${Date.now()}`;
}

function loadSavedIdentity() {
  const saved = localStorage.getItem("chatbot_identity");
  if (!saved) return null;

  try {
    return JSON.parse(saved);
  } catch {
    localStorage.removeItem("chatbot_identity");
    return null;
  }
}

function getSessionsStorageKey(userId) {
  return `chat_sessions_${userId || "guest"}`;
}

function loadSavedSessions(userId) {
  const key = getSessionsStorageKey(userId);
  const raw = localStorage.getItem(key);
  if (!raw) return [];

  try {
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    localStorage.removeItem(key);
    return [];
  }
}

function makeSessionTitle(text) {
  const trimmed = text.trim();
  if (!trimmed) return "New chat";
  return trimmed.length > 42 ? `${trimmed.slice(0, 42)}...` : trimmed;
}

function App() {
  const [identity, setIdentity] = useState(loadSavedIdentity);
  const [sessionId, setSessionId] = useState(
    () => identity?.session_id || createSessionId()
  );
  const [messages, setMessages] = useState([]);
  const [isSending, setIsSending] = useState(false);
  const [isTraining, setIsTraining] = useState(false);
  const [error, setError] = useState("");
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);

  const userId = identity?.user_id || "";
  const displayName = identity?.name || identity?.email || "";
  const canChat = Boolean(identity);

  const sessionsKey = useMemo(
    () => getSessionsStorageKey(identity?.user_id),
    [identity?.user_id]
  );
  const [sessions, setSessions] = useState([]);

  function saveIdentity(nextIdentity) {
    setIdentity(nextIdentity);
    setSessionId(nextIdentity.session_id);
    localStorage.setItem("chatbot_identity", JSON.stringify(nextIdentity));

    const storedSessions = loadSavedSessions(nextIdentity.user_id);
    const nextSessions = ensureSession(storedSessions, nextIdentity.session_id);
    setSessions(nextSessions);
    localStorage.setItem(
      getSessionsStorageKey(nextIdentity.user_id),
      JSON.stringify(nextSessions)
    );
  }

  function ensureSession(list, targetSessionId) {
    if (list.some((session) => session.id === targetSessionId)) return list;
    const freshSession = {
      id: targetSessionId,
      title: "New chat",
      lastMessage: "",
      updatedAt: Date.now(),
    };
    return [freshSession, ...list];
  }

  function persistSessions(nextSessions) {
    setSessions(nextSessions);
    if (identity) {
      localStorage.setItem(sessionsKey, JSON.stringify(nextSessions));
    }
  }

  function signOut() {
    localStorage.removeItem("chatbot_identity");
    setIdentity(null);
    setSessionId(createSessionId());
    setMessages([]);
    setSessions([]);
    setError("");
    window.google?.accounts?.id?.disableAutoSelect?.();
  }

  async function loadHistory(targetSessionId = sessionId) {
    if (!canChat) return;

    try {
      setError("");
      const data = await getChatHistory(userId, targetSessionId);
      setMessages(data.messages || []);
    } catch {
      setError("Could not load chat history.");
    }
  }

  async function handleSend(text) {
    const trimmedText = text.trim();
    if (!trimmedText) return;
    if (!canChat) {
      setError("Please sign in with Google to start chatting.");
      return;
    }

    const userMessage = {
      role: "user",
      text: trimmedText,
      timestamp: new Date().toISOString(),
    };

    setMessages((current) => [...current, userMessage]);
    setIsSending(true);
    setError("");

    if (identity) {
      const title = makeSessionTitle(text);
      const updatedSessions = updateSessionsForMessage(
        sessions,
        sessionId,
        title,
        text
      );
      persistSessions(updatedSessions);
    }

    try {
      const data = await sendChatMessage({
        user_id: userId,
        session_id: sessionId,
        message: trimmedText,
      });

      const botMessage = {
        role: "bot",
        text: data.reply,
        intent: data.intent,
        confidence: data.confidence,
        intent_source: data.intent_source,
        sentiment: data.sentiment,
        language: data.language,
        rag_used: data.rag_used,
        rag_source: data.rag_source,
        rag_sources: data.rag_sources,
        rag_confidence: data.rag_confidence,
        generation_source: data.generation_source,
        timestamp: new Date().toISOString(),
      };

      setMessages((current) => [...current, botMessage]);
      if (data.session_id && data.session_id !== sessionId) {
        setSessionId(data.session_id);
      }
    } catch {
      setError("Message failed. Check that FastAPI is running.");
    } finally {
      setIsSending(false);
    }
  }

  async function handleTrain() {
    setIsTraining(true);
    setError("");

    try {
      await trainModel();
    } catch {
      setError("Training failed. Check backend dependencies and logs.");
    } finally {
      setIsTraining(false);
    }
  }

  function startNewSession() {
    if (!identity) {
      setError("Please sign in with Google to start chatting.");
      return;
    }
    const nextSessionId = createSessionId();
    setSessionId(nextSessionId);
    const updatedSessions = ensureSession(sessions, nextSessionId);
    persistSessions(updatedSessions);
    setMessages([]);
    setError("");
  }

  function updateSessionsForMessage(list, targetSessionId, title, lastMessage) {
    const now = Date.now();
    const nextList = list.map((session) =>
      session.id === targetSessionId
        ? {
            ...session,
            title: session.title === "New chat" ? title : session.title,
            lastMessage,
            updatedAt: now,
          }
        : session
    );

    if (!nextList.some((session) => session.id === targetSessionId)) {
      nextList.unshift({
        id: targetSessionId,
        title,
        lastMessage,
        updatedAt: now,
      });
    }

    return nextList.sort((a, b) => b.updatedAt - a.updatedAt);
  }

  async function handleSelectSession(targetSessionId) {
    if (!canChat) return;
    if (targetSessionId === sessionId) return;

    setSessionId(targetSessionId);
    setMessages([]);
    await loadHistory(targetSessionId);
  }

  useEffect(() => {
    const trainedFlag = "intent_model_trained";
    if (localStorage.getItem(trainedFlag)) return;

    handleTrain().finally(() => {
      localStorage.setItem(trainedFlag, "true");
    });
  }, []);

  useEffect(() => {
    if (!identity) {
      setSessions([]);
      return;
    }
    const storedSessions = loadSavedSessions(identity.user_id);
    const nextSessions = ensureSession(storedSessions, sessionId);
    setSessions(nextSessions);
  }, [identity, sessionId]);

  useEffect(() => {
    const clientId = import.meta.env.VITE_GOOGLE_CLIENT_ID;
    if (!clientId || identity) {
      const container = document.getElementById("google-signin");
      if (container) container.innerHTML = "";
      return undefined;
    }

    let cancelled = false;

    const tryInit = () => {
      if (cancelled) return;

      if (!window.google?.accounts?.id) {
        setTimeout(tryInit, 200);
        return;
      }

      window.google.accounts.id.initialize({
        client_id: clientId,
        callback: async (response) => {
          try {
            console.log("📤 Sending Google token to backend...");
            const data = await authGoogle(response.credential);
            console.log("✅ Google auth success:", data);
            saveIdentity(data);
            setMessages([]);
            setError("");
          } catch (err) {
            console.error("❌ Google sign-in failed:", err);
            setError(`Google auth failed: ${err.message || "Check backend console"}`);
          }
        },
        error_callback: (error) => {
          console.error("❌ Google Sign-In error callback:", error);
          setError("Google Sign-In failed: " + (error.type || "Unknown error"));
        },
      });

      const container = document.getElementById("google-signin");
      if (container) {
        container.innerHTML = "";
        window.google.accounts.id.renderButton(container, {
          theme: "filled_black",
          size: "large",
          shape: "pill",
          text: "signin_with",
          width: 220,
        });
      }
    };

    tryInit();
    return () => {
      cancelled = true;
    };
  }, [identity]);

  return (
    <main className="app-shell">
      <div className={`app-body ${isSidebarOpen ? "" : "sidebar-collapsed"}`.trim()}>
        {!isSidebarOpen && (
          <button
            className="ghost-button sidebar-toggle"
            type="button"
            aria-label="Expand sidebar"
            onClick={() => setIsSidebarOpen(true)}
          >
            <Menu size={18} />
          </button>
        )}
        <aside className="chat-sidebar">
          <div className="sidebar-header">
            <div className="header-brand">
              <button
                className="brand-mark"
                type="button"
                aria-label={isSidebarOpen ? "Collapse sidebar" : "Expand sidebar"}
                onClick={() => setIsSidebarOpen((open) => !open)}
              >
                <Menu size={18} />
              </button>
              <div>
                <h1>Emo</h1>
                <p>Search, reason, respond</p>
              </div>
            </div>
            {displayName && <p className="sidebar-user">{displayName}</p>}
          </div>

          <button
            className="new-chat-button"
            type="button"
            onClick={startNewSession}
            disabled={!canChat}
          >
            <Plus size={16} />
            New chat
          </button>

          <div className="session-list">
            {sessions.length === 0 && (
              <p className="session-empty">No chats yet</p>
            )}
            {sessions.map((session) => (
              <button
                key={session.id}
                type="button"
                className={`session-item ${session.id === sessionId ? "active" : ""}`}
                onClick={() => handleSelectSession(session.id)}
              >
                <span className="session-title">{session.title}</span>
                {session.lastMessage && (
                  <span className="session-preview">{session.lastMessage}</span>
                )}
              </button>
            ))}
          </div>
        </aside>

        <div className="chat-main">
          <header className="app-header">
            <div className="header-spacer" />
            <div className="header-actions header-auth">
              {!identity && <div id="google-signin" className="google-slot" />}
              {identity && (
                <button className="ghost-button" type="button" onClick={signOut}>
                  Sign out
                </button>
              )}
            </div>
          </header>

          <section className="chat-panel">
            <div className="chat-hero">
              <h2>Emo ✨</h2>
              <p>How can I help you today?</p>
            </div>

            <ChatWindow messages={messages} isSending={isSending} />

            <div className="chat-input-panel">
              {!canChat && (
                <p className="hint-text">Sign in with Google to start chatting.</p>
              )}
              {error && <p className="error-text">{error}</p>}
              <ChatInput onSend={handleSend} disabled={!canChat || isSending} />
            </div>
          </section>
        </div>
      </div>
    </main>
  );
}

export default App;
