from __future__ import annotations

from app.chat_log import ChatLogEntry, ChatLogStore
from app.dedup import MessageDedupStore
from app.event_model import MessageSender, NormalizedEvent
from app.plugin import BotPlugin, PluginContext, PluginResult, PluginRegistry


class Router:
    def __init__(
        self,
        registry: PluginRegistry,
        dedup: MessageDedupStore | None = None,
        chat_log: ChatLogStore | None = None,
    ) -> None:
        self._registry = registry
        self._dedup = dedup
        self._chat_log = chat_log

    def register(self, plugin: BotPlugin) -> None:
        self._registry.register(plugin)

    async def dispatch(
        self,
        event: NormalizedEvent,
        sender: MessageSender,
    ) -> PluginResult:
        if self._chat_log:
            await self._chat_log.record(ChatLogEntry(
                chat_id=event.chat_id,
                user_id=event.user_id,
                text=event.text,
                message_id=event.message_id,
                timestamp=event.timestamp,
                scene=event.scene.value,
                platform=event.platform,
            ))

        if self._dedup:
            if await self._dedup.is_duplicate(event.message_id):
                return PluginResult()
            await self._dedup.mark_seen(event.message_id)

        for plugin in self._registry.get_all():
            if plugin.match(event):
                ctx = PluginContext(event=event, sender=sender)
                return await plugin.handle(ctx)
        return PluginResult(text="未知命令。输入 /help 查看可用命令。")
