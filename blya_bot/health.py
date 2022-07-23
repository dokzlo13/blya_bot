import asyncio
import logging
from typing import Callable, Optional

from aiohttp import web


def handler(callback: Callable):
    async def wrap(request):
        is_ok = False

        try:
            if asyncio.iscoroutinefunction(callback):
                is_ok = await callback()
            else:
                is_ok = callback()
        except Exception as e:
            logging.error(e)
            return web.json_response({"ok": False, "message": e}, status=422)

        if is_ok:
            return web.json_response({"ok": True}, status=200)
        else:
            return web.json_response({"ok": False}, status=422)

    return wrap


class HealthCheckApp:
    def __init__(self, live_func: Callable, port: int, ready_func: Optional[Callable] = None):
        self.live_func = live_func
        self.ready_func: Callable = ready_func if ready_func is not None else (lambda: True)  # type: ignore
        self.port = port

        self._app = web.Application()
        self._runner = None

    async def start_http_server(self) -> web.AppRunner:

        self._app.add_routes(
            [web.get("/health/live", handler(self.live_func)), web.get("/health/ready", handler(self.ready_func))]
        )
        runner = web.AppRunner(self._app)

        await runner.setup()

        site = web.TCPSite(runner, "", self.port)
        await site.start()

        logging.warning("Starting health check server at 0.0.0.0:{}".format(self.port))
        self._runner = runner  # type: ignore
        return runner

    async def stop_http_server(self) -> None:
        if self._runner is not None:
            logging.warning("Stopping health check server at 0.0.0.0:{}".format(self.port))
            await self._runner.cleanup()
