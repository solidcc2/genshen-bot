import pytest

from app.config import StorageConfig
from app.dedup import MessageDedupStore
from app.event_model import NormalizedEvent, Scene
from app.plugin import BotPlugin, PluginContext, PluginResult, PluginRegistry
from app.router import Router
from app.storage import create_storage
from conftest import FakeSender, make_event


class _AlphaPlugin(BotPlugin):
    def match(self, event: NormalizedEvent) -> bool:
        return "alpha" in event.text

    async def handle(self, ctx: PluginContext) -> PluginResult:
        return PluginResult(text="alpha handled")


class _BetaPlugin(BotPlugin):
    def match(self, event: NormalizedEvent) -> bool:
        return "beta" in event.text

    async def handle(self, ctx: PluginContext) -> PluginResult:
        return PluginResult(text="beta handled")


class TestRouter:
    @pytest.mark.anyio
    async def test_dispatch_hits_first_match(self) -> None:
        router = Router(PluginRegistry())
        router.register(_AlphaPlugin())
        router.register(_BetaPlugin())

        event = make_event("alpha beta")
        result = await router.dispatch(event, FakeSender())

        assert result is not None
        assert result.text == "alpha handled"

    @pytest.mark.anyio
    async def test_dispatch_returns_fallback_on_no_match(self) -> None:
        router = Router(PluginRegistry())
        router.register(_AlphaPlugin())

        event = make_event("gamma")
        result = await router.dispatch(event, FakeSender())
        assert result.text == "未知命令。输入 /help 查看可用命令。"

    @pytest.mark.anyio
    async def test_dispatch_respects_order(self) -> None:
        router = Router(PluginRegistry())

        class _CatchAll(BotPlugin):
            def match(self, event: NormalizedEvent) -> bool:
                return True

            async def handle(self, ctx: PluginContext) -> PluginResult:
                return PluginResult(text="catch all")

        router.register(_CatchAll())
        router.register(_AlphaPlugin())

        event = make_event("alpha")
        result = await router.dispatch(event, FakeSender())

        assert result is not None
        assert result.text == "catch all"

    @pytest.mark.anyio
    async def test_empty_router_returns_fallback(self) -> None:
        router = Router(PluginRegistry())
        event = make_event("anything")
        result = await router.dispatch(event, FakeSender())
        assert result.text == "未知命令。输入 /help 查看可用命令。"


class TestRouterDedup:
    @pytest.mark.anyio
    async def test_dedup_skips_duplicate_message(self) -> None:
        storage = create_storage(StorageConfig(backend="memory"))
        dedup = MessageDedupStore(storage)
        router = Router(PluginRegistry(), dedup=dedup)

        plugin = _AlphaPlugin()
        router.register(plugin)

        event = NormalizedEvent(
            platform="test",
            adapter="test",
            scene=Scene.PRIVATE,
            chat_id="chat_001",
            user_id="user_001",
            message_id="dup_001",
            text="alpha",
        )
        result1 = await router.dispatch(event, FakeSender())
        assert result1.text == "alpha handled"

        result2 = await router.dispatch(event, FakeSender())
        assert result2.text is None  # dedup returns empty PluginResult()

    @pytest.mark.anyio
    async def test_dedup_allows_different_messages(self) -> None:
        storage = create_storage(StorageConfig(backend="memory"))
        dedup = MessageDedupStore(storage)
        router = Router(PluginRegistry(), dedup=dedup)
        router.register(_AlphaPlugin())

        event1 = NormalizedEvent(
            platform="test", adapter="test", scene=Scene.PRIVATE,
            chat_id="chat_001", user_id="user_001",
            message_id="msg_001", text="alpha",
        )
        result1 = await router.dispatch(event1, FakeSender())
        assert result1.text == "alpha handled"

        event2 = NormalizedEvent(
            platform="test", adapter="test", scene=Scene.PRIVATE,
            chat_id="chat_001", user_id="user_001",
            message_id="msg_002", text="alpha",
        )
        result2 = await router.dispatch(event2, FakeSender())
        assert result2.text == "alpha handled"
