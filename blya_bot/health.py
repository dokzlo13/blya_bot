import asyncio
import logging
from typing import Callable

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


def add_health_check_probe(app: web.Application, probe_fn, path="/health/live"):
    app.add_routes([web.get(path, handler(probe_fn))])
