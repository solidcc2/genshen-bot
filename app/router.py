from __future__ import annotations

from app.event_model import MessageSender, NormalizedEvent
from app.plugin import BotPlugin, PluginContext, PluginResult


class Router:
    def __init__(self) -> None:
        self._plugins: list[BotPlugin] = []

    def register(self, plugin: BotPlugin) -> None:
        self._plugins.append(plugin)

    async def dispatch(
        self,
        event: NormalizedEvent,
        sender: MessageSender,
    ) -> PluginResult | None:
        for plugin in self._plugins:
            if plugin.match(event):
                ctx = PluginContext(event=event, sender=sender)
                return await plugin.handle(ctx)
        return None
