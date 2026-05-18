from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from app.event_model import NormalizedEvent, Scene
from app.plugin import BotPlugin, PluginContext, PluginHelp, PluginResult

if TYPE_CHECKING:
    from app.chat_log import ChatLogStore

_logger = logging.getLogger(__name__)

KEEP_HELP = "保留最近 N 条记录（可选），如 /chatlog-clear keep=100"


class ChatLogClearPlugin(BotPlugin):
    command = ""

    def __init__(self, chat_log: ChatLogStore) -> None:
        self._chat_log = chat_log

    def match(self, event: NormalizedEvent) -> bool:
        text = event.text.strip()
        return text == "/chatlog-clear" or text.startswith("/chatlog-clear ")

    def help(self) -> PluginHelp | None:
        return PluginHelp(
            command="chatlog-clear [keep=N]",
            description="清空当前群的聊天环境记录，" + KEEP_HELP,
            category="通用",
        )

    async def handle(self, ctx: PluginContext) -> PluginResult:
        text = ctx.event.text.strip()
        keep = self._parse_keep(text)
        if keep is not None:
            count = await self._chat_log.count(ctx.event.chat_id)
            await self._chat_log.trim(ctx.event.chat_id, keep)
            deleted = max(0, count - keep)
            return PluginResult(text=f"已清理，保留最近 {keep} 条记录，删除了 {deleted} 条。")
        await self._chat_log.clear(ctx.event.chat_id)
        return PluginResult(text="聊天环境记录已清空。")

    @staticmethod
    def _parse_keep(text: str) -> int | None:
        if "keep=" not in text:
            return None
        try:
            value = text.split("keep=", 1)[1].strip().split()[0]
            return max(1, int(value))
        except (ValueError, IndexError):
            return None
