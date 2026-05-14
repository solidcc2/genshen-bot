from __future__ import annotations

from app.event_model import NormalizedEvent
from app.plugin import BotPlugin, PluginContext, PluginHelp, PluginResult, PluginRegistry


class HelpPlugin(BotPlugin):
    _TRIGGERS = frozenset({"/help"})

    def __init__(self, registry: PluginRegistry) -> None:
        self._registry = registry

    def match(self, event: NormalizedEvent) -> bool:
        return event.text.strip() in self._TRIGGERS

    async def handle(self, ctx: PluginContext) -> PluginResult:
        entries = self._registry.get_help_entries()
        if not entries:
            return PluginResult(text="没有已注册的插件。")

        lines = ["可用命令："]
        for entry in entries:
            usage = f"  {entry.usage}" if entry.usage else ""
            lines.append(f"  {entry.command} — {entry.description}{usage}")
        return PluginResult(text="\n".join(lines))

    def help(self) -> PluginHelp:
        return PluginHelp(
            command="/help",
            description="显示可用命令列表",
            usage="/help",
        )
