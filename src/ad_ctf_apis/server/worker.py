import asyncio

from aiohttp import GunicornWebWorker
from gunicorn.workers import base  # type: ignore


class MyGunicornWebWorker(GunicornWebWorker):
    """
    Hot-patches an issue in aiohttp.
    https://github.com/aio-libs/aiohttp/issues/11701
    """

    def init_process(self) -> None:
        try:
            super().init_process()
        except RuntimeError:
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            base.Worker.init_process(self)
