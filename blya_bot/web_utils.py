import asyncio
import structlog

from aiohttp import web

logger = structlog.getLogger(__name__)


class BackgroundAppRunner:
    def __init__(self, app: web.Application, loop: asyncio.AbstractEventLoop | None = None):
        self.app = app
        self.loop = loop if loop is not None else asyncio.get_event_loop()

    def start_http_server(self, host, port):
        self.loop.run_until_complete(self._start_http_server(host, port))

    def stop_http_server(self):
        self.loop.run_until_complete(self._stop_http_server())

    async def _start_http_server(self, host, port):
        runner = web.AppRunner(self.app)

        await runner.setup()

        site = web.TCPSite(runner, host, port)
        await site.start()

        logger.warning(f"Web app started at {host}:{port}")
        self._runner = runner  # type: ignore

    async def _stop_http_server(self) -> None:
        if self._runner is not None:
            logger.warning("Web app stopped")
            await self._runner.cleanup()
