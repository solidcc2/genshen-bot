import pytest

from app.plugin import PluginContext, PluginRegistry
from app.plugins.echo import EchoPlugin
from app.plugins.help import HelpPlugin
from app.plugins.ping import PingPlugin
from conftest import FakeSender, make_event


class TestEchoPlugin:
    @pytest.mark.anyio
    async def test_echo_content(self) -> None:
        plugin = EchoPlugin()
        event = make_event("/echo hello world")
        assert plugin.match(event)

        result = await plugin.handle(PluginContext(event=event, sender=FakeSender()))
        assert result.text == "hello world"

    @pytest.mark.anyio
    async def test_echo_empty_content(self) -> None:
        plugin = EchoPlugin()
        event = make_event("/echo ")
        assert plugin.match(event)

        result = await plugin.handle(PluginContext(event=event, sender=FakeSender()))
        assert result.text == ""

    def test_not_match_without_prefix(self) -> None:
        plugin = EchoPlugin()
        assert not plugin.match(make_event("say hello"))

    def test_not_match_missing_slash(self) -> None:
        plugin = EchoPlugin()
        assert not plugin.match(make_event("echo hello"))

    def test_not_match_ambiguous_command(self) -> None:
        plugin = EchoPlugin()
        assert not plugin.match(make_event("/echos"))

    def test_help(self) -> None:
        plugin = EchoPlugin()
        help_info = plugin.help()
        assert help_info is not None
        assert help_info.command == "/echo"
        assert "回显" in help_info.description


class TestPingPlugin:
    @pytest.mark.anyio
    async def test_ping(self) -> None:
        plugin = PingPlugin()
        event = make_event("/ping")
        assert plugin.match(event)

        result = await plugin.handle(PluginContext(event=event, sender=FakeSender()))
        assert result.text == "Pong!"

    def test_not_match_missing_slash(self) -> None:
        plugin = PingPlugin()
        assert not plugin.match(make_event("ping"))

    def test_not_match_ambiguous_command(self) -> None:
        plugin = PingPlugin()
        assert not plugin.match(make_event("/pingabc"))

    def test_help(self) -> None:
        plugin = PingPlugin()
        help_info = plugin.help()
        assert help_info is not None
        assert help_info.command == "/ping"


class TestHelpPlugin:
    @pytest.mark.anyio
    async def test_help_with_plugins(self) -> None:
        registry = PluginRegistry()
        registry.register(EchoPlugin())
        plugin = HelpPlugin(registry)

        event = make_event("/help")
        assert plugin.match(event)

        result = await plugin.handle(PluginContext(event=event, sender=FakeSender()))
        assert result.text is not None
        assert "/echo" in result.text
        assert "/ping" not in result.text  # ping not registered

    @pytest.mark.anyio
    async def test_help_empty_registry(self) -> None:
        registry = PluginRegistry()
        plugin = HelpPlugin(registry)

        event = make_event("/help")
        assert plugin.match(event)

        result = await plugin.handle(PluginContext(event=event, sender=FakeSender()))
        assert "没有已注册的插件" in (result.text or "")

    def test_match(self) -> None:
        registry = PluginRegistry()
        plugin = HelpPlugin(registry)
        assert plugin.match(make_event("/help"))
        assert not plugin.match(make_event("help"))
        assert not plugin.match(make_event("/helps"))

    def test_help(self) -> None:
        registry = PluginRegistry()
        plugin = HelpPlugin(registry)
        help_info = plugin.help()
        assert help_info is not None
        assert help_info.command == "/help"
