from __future__ import annotations

import asyncio
import argparse
from collections.abc import Callable
import signal
import sys
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from app.adapters import CLIAdapter
from app.config import ConfigLoader
from app.dedup import MessageDedupStore
from app.errors import ApplicationStateError, BootstrapError
from app.http import HealthService
from app.logging import configure_logging
from app.plugins.echo import EchoPlugin
from app.plugins.help import HelpPlugin
from app.plugins.null import NullPlugin
from app.plugins.ping import PingPlugin
from app.rate_limit import RateLimiter
from app.router import Router
from app.runtime import AppContext
from app.session import SessionManager
from app.storage import create_storage


class Application:
    def __init__(self, context: AppContext, health_service: HealthService) -> None:
        self.context = context
        self._health_service = health_service

    async def start(self) -> None:
        if self.context.runtime.status == "running":
            raise ApplicationStateError("Application is already running")

        host, port = await self._health_service.start()

        if self.context.services.has("onebot_adapter"):
            await self.context.services.get("onebot_adapter").start()

        self.context.runtime.mark_started(host=host, port=port)
        self.context.logger.info("application started")

    async def stop(self) -> None:
        if self.context.runtime.status not in {"running", "created"}:
            raise ApplicationStateError("Application is not in a stoppable state")

        if self.context.services.has("onebot_adapter"):
            await self.context.services.get("onebot_adapter").stop()

        await self._health_service.stop()

        if self.context.storage is not None:
            await self.context.storage.close()

        self.context.runtime.mark_stopped()
        self.context.logger.info("application stopped")


def build_application(
    config_path: str | Path | None = None,
    environ: dict[str, str] | None = None,
    health_runner_factory: Callable[..., Any] | None = None,
) -> Application:
    config = ConfigLoader.load(config_path=config_path, environ=environ)
    logger = configure_logging(config.log_level)
    context = AppContext(config=config, logger=logger)

    # Storage first — Router depends on dedup from storage
    _init_storage(context)

    context.router = Router(context.plugins, dedup=context.dedup)
    _register_core_plugins(context)

    # OneBot adapter (runs if enabled in config)
    if config.onebot.enabled:
        from app.adapters.onebot import OneBotAdapter

        onebot = OneBotAdapter(
            router=context.router,
            webhook_host=config.onebot.webhook_host,
            webhook_port=config.onebot.webhook_port,
            webhook_path=config.onebot.webhook_path,
            api_base=config.onebot.api_base,
        )
        context.services.register("onebot_adapter", onebot)

    health_service = HealthService(context, runner_factory=health_runner_factory)
    context.services.register("health_service", health_service)
    return Application(context=context, health_service=health_service)


def _init_storage(context: AppContext) -> None:
    storage = create_storage(context.config.storage)
    context.storage = storage
    context.session_manager = SessionManager(storage)
    context.rate_limiter = RateLimiter(storage)
    context.dedup = MessageDedupStore(storage)


def _register_core_plugins(context: AppContext) -> None:
    echo = EchoPlugin()
    ping = PingPlugin()
    help_ = HelpPlugin(context.plugins)

    for plugin in (echo, ping, help_):
        context.router.register(plugin)

    _register_genshin_plugins(context)

    # NullPlugin must be registered last — its match() always returns True
    context.router.register(NullPlugin())


def _register_genshin_plugins(context: AppContext) -> None:
    from app.plugins.genshin import register as register_genshin

    provider = register_genshin(
        router=context.router,
        storage=context.storage,
        hoyolab_config=context.config.hoyolab,
    )
    if provider is not None:
        context.services.register("hoyolab_provider", provider)


async def async_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Start the QQ AI bot runtime skeleton.")
    parser.add_argument("--config", default=None, help="Path to JSON config file.")
    parser.add_argument(
        "--cli", action="store_true", help="Start CLI adapter for interactive input."
    )
    args = parser.parse_args(argv)

    try:
        application = build_application(config_path=args.config)
        await application.start()
    except BootstrapError as exc:
        print(f"bootstrap failed: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:  # pragma: no cover - final safety net
        print(f"unexpected startup failure: {exc}", file=sys.stderr)
        return 1

    stop_event = asyncio.Event()

    if args.cli:
        cli = CLIAdapter(application.context.router)
        cli_task = asyncio.create_task(cli.run())

        def _on_cli_done(task: asyncio.Task[None]) -> None:
            exc = task.exception()
            if exc:
                print(f"CLI adapter error: {exc}", file=sys.stderr)
            stop_event.set()

        cli_task.add_done_callback(_on_cli_done)

    def _handle_signal(_signum: int, _frame: object) -> None:
        stop_event.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, stop_event.set)
        except NotImplementedError:
            signal.signal(sig, _handle_signal)

    try:
        await stop_event.wait()
    finally:
        await application.stop()
        if args.cli and cli_task and not cli_task.done():
            cli_task.cancel()
            try:
                await cli_task
            except asyncio.CancelledError:
                pass

    return 0


def main(argv: list[str] | None = None) -> int:
    return asyncio.run(async_main(argv))
