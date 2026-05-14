from __future__ import annotations

from app.event_model import NormalizedEvent
from app.plugin import BotPlugin, PluginContext, PluginHelp, PluginResult


class PingPlugin(BotPlugin):
    _TRIGGERS = frozenset({"/ping"})

    def match(self, event: NormalizedEvent) -> bool:
        return event.text.strip() in self._TRIGGERS

    async def handle(self, ctx: PluginContext) -> PluginResult:
        return PluginResult(text="Pong!")

    def help(self) -> PluginHelp:
        return PluginHelp(
            command="/ping",
            description="连通性检查",
            usage="/ping",
        )
