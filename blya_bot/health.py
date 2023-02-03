import asyncio
from contextlib import contextmanager, asynccontextmanager
from typing import Callable

import structlog
from aiohttp import web

from .web_utils import BackgroundAppRunner

logger = structlog.getLogger(__name__)


def handler(callback: Callable):
    async def wrap(request):
        is_ok = False

        try:
            if asyncio.iscoroutinefunction(callback):
                is_ok = await callback()
            else:
                is_ok = callback()
        except Exception as e:
            logger.error(e)
            return web.json_response({"ok": False, "message": e}, status=422)

        if is_ok:
            return web.json_response({"ok": True}, status=200)
        else:
            return web.json_response({"ok": False}, status=422)

    return wrap


def add_health_check_probe(app: web.Application, probe_fn, path="/health/live"):
    app.add_routes([web.get(path, handler(probe_fn))])


@contextmanager
def health_check_server(probe_fn, host: str, port: int, path: str, loop=None):
    app = web.Application()
    add_health_check_probe(app, probe_fn, path=path)
    runner = BackgroundAppRunner(app, loop=loop)
    logger.info("Starting health check server...")
    runner.start_http_server(host=host, port=port)
    try:
        yield
    finally:
        logger.info("Stopping health check server...")
        runner.stop_http_server()


@asynccontextmanager
async def async_health_check_server(probe_fn, host: str, port: int, path: str, loop=None):
    app = web.Application()
    add_health_check_probe(app, probe_fn, path=path)
    runner = BackgroundAppRunner(app, loop=loop)
    logger.info("Starting health check server...")
    await runner.async_start_http_server(host=host, port=port)
    try:
        yield
    finally:
        logger.info("Stopping health check server...")
        await runner.async_stop_http_server()
