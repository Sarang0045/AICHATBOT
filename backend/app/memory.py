from datetime import datetime, timezone
from typing import Protocol

from app.config import settings


ConversationStore = dict[str, list[dict]]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def make_message(role: str, text: str, intent: str | None = None) -> dict:
    return {
        "role": role,
        "text": text,
        "intent": intent,
        "timestamp": utc_now(),
    }


class ConversationMemory(Protocol):
    storage_type: str

    def add_message(
        self,
        session_id: str,
        role: str,
        text: str,
        intent: str | None = None,
        user_id: str | None = None,
    ) -> dict:
        ...

    def get_history(
        self,
        session_id: str,
        user_id: str | None = None,
    ) -> list[dict]:
        ...

    def get_recent_messages(
        self,
        session_id: str,
        limit: int = 6,
        user_id: str | None = None,
    ) -> list[dict]:
        ...

    def clear_session(
        self,
        session_id: str,
        user_id: str | None = None,
    ) -> None:
        ...


class InMemoryConversationMemory:
    storage_type = "in_memory"

    def __init__(self) -> None:
        self._conversations: ConversationStore = {}

    def _key(self, session_id: str, user_id: str | None = None) -> str:
        if user_id:
            return f"{user_id}:{session_id}"

        return session_id

    def add_message(
        self,
        session_id: str,
        role: str,
        text: str,
        intent: str | None = None,
        user_id: str | None = None,
    ) -> dict:
        message = make_message(role=role, text=text, intent=intent)
        key = self._key(session_id=session_id, user_id=user_id)

        if key not in self._conversations:
            self._conversations[key] = []

        self._conversations[key].append(message)
        return message

    def get_history(
        self,
        session_id: str,
        user_id: str | None = None,
    ) -> list[dict]:
        key = self._key(session_id=session_id, user_id=user_id)
        return self._conversations.get(key, [])

    def get_recent_messages(
        self,
        session_id: str,
        limit: int = 6,
        user_id: str | None = None,
    ) -> list[dict]:
        return self.get_history(session_id=session_id, user_id=user_id)[-limit:]

    def clear_session(
        self,
        session_id: str,
        user_id: str | None = None,
    ) -> None:
        key = self._key(session_id=session_id, user_id=user_id)
        self._conversations.pop(key, None)


class MongoConversationMemory:
    storage_type = "mongodb"

    def __init__(self, mongo_url: str) -> None:
        from pymongo import MongoClient
        self.client = MongoClient(mongo_url, serverSelectionTimeoutMS=2000)
        self.db = self.client[settings.mongo_database]
        self.collection = self.db[settings.mongo_collection]
        self.collection.create_index(
            [("user_id", 1), ("session_id", 1)],
            unique=True,
        )

    def _query(
        self,
        session_id: str,
        user_id: str | None = None,
    ) -> dict:
        query = {"session_id": session_id}

        if user_id:
            query["user_id"] = user_id

        return query

    def add_message(
        self,
        session_id: str,
        role: str,
        text: str,
        intent: str | None = None,
        user_id: str | None = None,
    ) -> dict:
        message = make_message(role=role, text=text, intent=intent)
        safe_user_id = user_id or "anonymous"
        self.collection.update_one(
            {"user_id": safe_user_id, "session_id": session_id},
            {
                "$setOnInsert": {
                    "user_id": safe_user_id,
                    "session_id": session_id,
                    "created_at": utc_now(),
                },
                "$set": {
                    "updated_at": utc_now(),
                },
                "$push": {
                    "messages": message,
                },
            },
            upsert=True,
        )

        return message

    def get_history(
        self,
        session_id: str,
        user_id: str | None = None,
    ) -> list[dict]:
        conversation = self.collection.find_one(self._query(session_id, user_id))

        if not conversation:
            return []

        return conversation.get("messages", [])

    def get_recent_messages(
        self,
        session_id: str,
        limit: int = 6,
        user_id: str | None = None,
    ) -> list[dict]:
        return self.get_history(session_id=session_id, user_id=user_id)[-limit:]

    def clear_session(
        self,
        session_id: str,
        user_id: str | None = None,
    ) -> None:
        self.collection.delete_one(self._query(session_id, user_id))


def create_memory() -> ConversationMemory:
    if settings.mongo_url:
        try:
            return MongoConversationMemory(settings.mongo_url)
        except Exception as exc:
            print(f"MongoDB memory unavailable, using in-memory storage: {exc}")

    return InMemoryConversationMemory()


memory = create_memory()
