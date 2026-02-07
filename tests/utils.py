import asyncio
import multiprocessing
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Generator, Coroutine, Callable, Any
from unittest import IsolatedAsyncioTestCase
from unittest.mock import Mock, patch, MagicMock


class AsyncThread(threading.Thread):
    def __init__(self, f: Coroutine) -> None:
        super().__init__(daemon=True)
        self.f = f

    def run(self) -> None:
        asyncio.run(self.f)


class AsyncProcess(multiprocessing.Process):
    def __init__(self, f: Callable, *args: Any) -> None:
        super().__init__(daemon=True)
        self.f = f
        self.args = args

    def run(self) -> None:
        asyncio.run(self.f(*self.args))


async def make_async(x: bytes) -> bytes:
    return x


class BaseTestCase(IsolatedAsyncioTestCase):
    _res: Path = Path(__file__).parent / "res"

    @staticmethod
    @contextmanager
    def patch_request(f: Path) -> Generator[Mock]:
        with patch("aiohttp.client.ClientSession.get") as mock:
            mock2 = MagicMock()
            mock.return_value = mock2
            mock2.__aenter__.return_value = mock2
            mock2.raise_for_status.return_value = None
            mock2.read.side_effect = lambda *args, **kwargs: make_async(f.read_bytes())
            yield mock
