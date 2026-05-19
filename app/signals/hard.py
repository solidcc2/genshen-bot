from __future__ import annotations

from typing import Any

from app.event_model import Mention, NormalizedEvent
from app.signals import Signal, SignalVerdict


class AtMention(Signal):
    """PASS if the event mentions the bot via @ or text @name."""

    name = "at_mention"

    def __init__(self, config: dict[str, Any], bot_user_id: str, bot_name: str = "") -> None:
        super().__init__(config)
        self._bot_user_id = bot_user_id
        self._bot_name = bot_name

    def evaluate(self, event: NormalizedEvent) -> SignalVerdict:
        for m in event.mentions:
            if m.user_id == self._bot_user_id:
                return SignalVerdict(bypass=True, reason="at_mention")

        if self._bot_name and self._bot_name in event.text:
            return SignalVerdict(bypass=True, reason="text_mention")

        return SignalVerdict(reason="no_mention")


class ReplyToBot(Signal):
    """PASS if the event is a reply to a message sent by the bot."""

    name = "reply_to_bot"

    def __init__(self, config: dict[str, Any], bot_user_id: str) -> None:
        super().__init__(config)
        self._bot_user_id = bot_user_id

    def evaluate(self, event: NormalizedEvent) -> SignalVerdict:
        if event.reply_to == self._bot_user_id:
            return SignalVerdict(bypass=True, reason="reply_to_bot")

        return SignalVerdict(reason="not_reply_to_bot")
