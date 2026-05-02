import { useState } from "react";
import { Mic, SendHorizonal } from "lucide-react";

function ChatInput({ onSend, disabled }) {
  const [text, setText] = useState("");
  const [isListening, setIsListening] = useState(false);

  function submitMessage(event) {
    event.preventDefault();

    if (!text.trim()) return;

    onSend(text);
    setText("");
  }

  function startVoiceInput() {
    const SpeechRecognition =
      window.SpeechRecognition || window.webkitSpeechRecognition;

    if (!SpeechRecognition) {
      alert("Voice input is not supported in this browser.");
      return;
    }

    const recognition = new SpeechRecognition();
    recognition.lang = "en-US";
    recognition.interimResults = false;
    recognition.maxAlternatives = 1;

    recognition.onstart = () => {
      setIsListening(true);
    };

    recognition.onresult = (event) => {
      const transcript = event.results[0][0].transcript;
      setText(transcript);
    };

    recognition.onerror = () => {
      setIsListening(false);
    };

    recognition.onend = () => {
      setIsListening(false);
    };

    recognition.start();
  }

  return (
    <form className="chat-input-row" onSubmit={submitMessage}>
      <button
        aria-label="Start voice input"
        className={`voice-button ${isListening ? "listening" : ""}`}
        type="button"
        onClick={startVoiceInput}
        disabled={disabled}
      >
        <Mic size={20} />
      </button>
      <input
        className="chat-input"
        value={text}
        onChange={(event) => setText(event.target.value)}
        placeholder="What do you want to know?"
        disabled={disabled}
      />
      <button className="send-button" type="submit" disabled={disabled}>
        <SendHorizonal size={20} />
      </button>
    </form>
  );
}

export default ChatInput;
