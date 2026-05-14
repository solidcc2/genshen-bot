from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Protocol


class Scene(str, Enum):
    PRIVATE = "private"
    GROUP = "group"
    GUILD = "guild"
    CHANNEL = "channel"


@dataclass(frozen=True)
class Mention:
    user_id: str
    display_name: str = ""


@dataclass(frozen=True)
class NormalizedEvent:
    platform: str
    adapter: str
    scene: Scene
    chat_id: str
    user_id: str
    message_id: str
    text: str
    mentions: tuple[Mention, ...] = ()
    reply_to: str | None = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(frozen=True)
class ReplyTarget:
    scene: Scene
    chat_id: str
    user_id: str | None = None


class MessageSender(Protocol):
    async def send_text(self, target: ReplyTarget, text: str) -> str: ...
    async def send_reply(
        self, event: NormalizedEvent, text: str
    ) -> str: ...
