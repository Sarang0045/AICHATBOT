import { Bot, User } from "lucide-react";

function formatConfidence(confidence) {
  if (confidence === null || confidence === undefined) {
    return null;
  }

  return `${Math.round(confidence * 100)}%`;
}

function MessageBubble({ message }) {
  const isUser = message.role === "user";
  const confidence = formatConfidence(message.confidence);
  const ragConfidence = formatConfidence(message.rag_confidence);
  const ragSources = message.rag_sources?.length
    ? message.rag_sources.join(", ")
    : message.rag_source;

  return (
    <div className={`message-row ${isUser ? "user-row" : "bot-row"}`}>
      <div className="avatar">{isUser ? <User size={16} /> : <Bot size={16} />}</div>
      <div className={`message-bubble ${isUser ? "user-bubble" : "bot-bubble"}`}>
        <p>{message.text}</p>

        {!isUser && message.intent && (
          <div className="message-meta">
            <span>{message.intent}</span>
            {message.intent_source && <span>{message.intent_source}</span>}
            {confidence && <span>{confidence}</span>}
            {message.sentiment && <span>{message.sentiment}</span>}
            {message.language && <span>{message.language}</span>}
            {message.generation_source && <span>{message.generation_source}</span>}
            {message.rag_used && <span>RAG: {ragSources}</span>}
            {ragConfidence && <span>RAG {ragConfidence}</span>}
          </div>
        )}
      </div>
    </div>
  );
}

export default MessageBubble;
