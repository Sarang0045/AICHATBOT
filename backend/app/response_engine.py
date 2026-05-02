from app.intent_detector import clean_text

BASE_RESPONSES = {
    "greeting": "Hello! How can I help you today?",
    "goodbye": "Goodbye! Have a great day.",
    "order_status": "I can help you track your order. Please share your order ID.",
    "refund_request": "I can help with refunds. Please share your order ID and the reason for the refund.",
    "thanks": "You're welcome!",
    "help": "I am here to help. You can ask about order tracking, refunds, or general support.",
    "unknown": "I am not fully sure I understood. Could you explain that in a little more detail?",
}

def find_last_user_intent(history: list[dict]) -> str | None:
    for message in reversed(history):
        if message["role"] == "user" and message.get("intent"):
            return message["intent"]
        
    return None

def looks_like_order_id(message: str) -> bool:
    cleaned = clean_text(message)
    words = cleaned.split()
    if any(word.startswith("ord") for word in words):
        return True
    return any(word.isdigit() and len(word) >= 4 for word in words)

def create_reply(
    intent: str,
    message: str,
    history: list[dict],
    rag_result=None,
) -> str:
    previous_intent = find_last_user_intent(history)

    if rag_result is not None and rag_result.chunks:
        source = rag_result.primary_source or "the knowledge base"
        return f"According to {source}, {rag_result.chunks[0].content}"

    if previous_intent == "order_status" and looks_like_order_id(message):
        return f"Thanks. I found your order reference in '{message}'. Your order is being checked now."

    if previous_intent == "refund_request" and looks_like_order_id(message):
        return f"Thanks. I found your order reference in '{message}'. I will start the refund review process."

    return BASE_RESPONSES.get(intent, BASE_RESPONSES["unknown"])
