from __future__ import annotations

from app.event_model import NormalizedEvent
from app.plugin import BotPlugin, PluginContext, PluginHelp, PluginResult


class EchoPlugin(BotPlugin):
    _PREFIX = "/echo "

    def match(self, event: NormalizedEvent) -> bool:
        return event.text.startswith(self._PREFIX)

    async def handle(self, ctx: PluginContext) -> PluginResult:
        return PluginResult(text=ctx.event.text.removeprefix(self._PREFIX))

    def help(self) -> PluginHelp:
        return PluginHelp(
            command="/echo",
            description="回显消息内容",
            usage="/echo <text>",
        )
