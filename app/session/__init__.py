from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

_logger = logging.getLogger(__name__)

from app.storage import StorageProvider


def _parse_timestamp(value: str | datetime) -> datetime:
    if isinstance(value, str):
        return datetime.fromisoformat(value)
    return value


@dataclass
class Session:
    chat_id: str
    state: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


_NS_SESSION = "session"


class SessionManager:
    def __init__(self, storage: StorageProvider) -> None:
        self._storage = storage

    async def get_or_create(self, chat_id: str) -> Session:
        data = await self._storage.get(_NS_SESSION, chat_id)
        if data is not None:
            return Session(
                chat_id=chat_id,
                state=data.get("state", {}),
                created_at=_parse_timestamp(data.get("created_at", "1970-01-01T00:00:00+00:00")),
                updated_at=_parse_timestamp(data.get("updated_at", "1970-01-01T00:00:00+00:00")),
            )
        return Session(chat_id=chat_id)

    async def save(self, session: Session) -> None:
        session.updated_at = datetime.now(timezone.utc)
        data = {
            "state": session.state,
            "created_at": session.created_at.isoformat(),
            "updated_at": session.updated_at.isoformat(),
        }
        await self._storage.set(_NS_SESSION, session.chat_id, data)

    async def set_state(self, chat_id: str, key: str, value: Any) -> None:
        session = await self.get_or_create(chat_id)
        session.state[key] = value
        await self.save(session)

    async def get_state(self, chat_id: str, key: str) -> Any | None:
        session = await self.get_or_create(chat_id)
        return session.state.get(key)
