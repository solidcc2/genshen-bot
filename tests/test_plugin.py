import pytest

from app.event_model import NormalizedEvent
from app.plugin import (
    BotPlugin,
    PluginContext,
    PluginHelp,
    PluginRegistry,
    PluginResult,
)
from conftest import FakeSender, make_event


class _EchoPlugin(BotPlugin):
    def match(self, event: NormalizedEvent) -> bool:
        return event.text.startswith("echo ")

    async def handle(self, ctx: PluginContext) -> PluginResult:
        return PluginResult(text=ctx.event.text.removeprefix("echo "))


class _NoopPlugin(BotPlugin):
    def match(self, event: NormalizedEvent) -> bool:
        return False

    async def handle(self, ctx: PluginContext) -> PluginResult:
        return PluginResult(text="should not be called")


class TestBotPlugin:
    @pytest.mark.anyio
    async def test_match_and_handle(self) -> None:
        plugin = _EchoPlugin()
        event = make_event("echo hello")
        assert plugin.match(event)

        result = await plugin.handle(PluginContext(event=event, sender=FakeSender()))
        assert result.text == "hello"

    def test_help_defaults_to_none(self) -> None:
        plugin = _EchoPlugin()
        assert plugin.help() is None


class TestPluginResult:
    def test_defaults(self) -> None:
        result = PluginResult()
        assert result.text is None
        assert result.reactions is None
        assert result.data is None

    def test_with_text(self) -> None:
        result = PluginResult(text="hello")
        assert result.text == "hello"


class TestPluginHelp:
    def test_minimal(self) -> None:
        help_info = PluginHelp(command="/test", description="a test plugin")
        assert help_info.command == "/test"
        assert help_info.usage is None

    def test_full(self) -> None:
        help_info = PluginHelp(command="/test", description="test", usage="test <arg>")
        assert help_info.usage == "test <arg>"


class TestPluginRegistry:
    def test_register_and_get_all(self) -> None:
        registry = PluginRegistry()
        p1 = _EchoPlugin()
        p2 = _NoopPlugin()

        registry.register(p1)
        registry.register(p2)

        all_plugins = registry.get_all()
        assert len(all_plugins) == 2
        assert p1 in all_plugins
        assert p2 in all_plugins

    def test_prevent_duplicate_register(self) -> None:
        registry = PluginRegistry()
        plugin = _EchoPlugin()
        registry.register(plugin)

        import app.errors
        with pytest.raises(app.errors.PluginError, match="already registered"):
            registry.register(plugin)

    def test_get_help_entries_empty(self) -> None:
        registry = PluginRegistry()
        assert registry.get_help_entries() == []

    def test_get_help_entries(self) -> None:
        class _HelpfulPlugin(BotPlugin):
            def match(self, event: NormalizedEvent) -> bool:
                return False

            async def handle(self, ctx: PluginContext) -> PluginResult:
                return PluginResult()

            def help(self) -> PluginHelp:
                return PluginHelp(command="/test", description="test plugin")

        registry = PluginRegistry()
        registry.register(_HelpfulPlugin())
        entries = registry.get_help_entries()
        assert len(entries) == 1
        assert entries[0].command == "/test"
