import MessageBubble from "./MessageBubble.jsx";

function getGreeting() {
  const hour = new Date().getHours();
  if (hour < 12) return "Good morning";
  if (hour < 18) return "Good afternoon";
  return "Good evening";
}

function ChatWindow({ messages, isSending }) {
  if (messages.length === 0) {
    return (
      <div className="empty-state">
        <h3>{getGreeting()}</h3>
      </div>
    );
  }

  return (
    <div className="chat-window">
      {messages.map((message, index) => (
        <MessageBubble key={`${message.timestamp}-${index}`} message={message} />
      ))}
      {isSending && (
        <div className="typing-indicator" aria-live="polite">
          <div className="dot" />
          <div className="dot" />
          <div className="dot" />
        </div>
      )}
    </div>
  );
}

export default ChatWindow;
