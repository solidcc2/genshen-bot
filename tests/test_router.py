import pytest

from app.event_model import NormalizedEvent, Scene
from app.plugin import BotPlugin, PluginContext, PluginResult
from app.router import Router
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
        router = Router()
        router.register(_AlphaPlugin())
        router.register(_BetaPlugin())

        event = make_event("alpha beta")
        result = await router.dispatch(event, FakeSender())

        assert result is not None
        assert result.text == "alpha handled"

    @pytest.mark.anyio
    async def test_dispatch_returns_none_on_no_match(self) -> None:
        router = Router()
        router.register(_AlphaPlugin())

        event = make_event("gamma")
        result = await router.dispatch(event, FakeSender())
        assert result is None

    @pytest.mark.anyio
    async def test_dispatch_respects_order(self) -> None:
        router = Router()

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
    async def test_empty_router(self) -> None:
        router = Router()
        event = make_event("anything")
        result = await router.dispatch(event, FakeSender())
        assert result is None
