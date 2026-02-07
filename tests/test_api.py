import asyncio
import json
import multiprocessing
import os
import tempfile
import time
from contextlib import contextmanager
from multiprocessing import Process
from multiprocessing.sharedctypes import Synchronized
from pathlib import Path
from typing import Generator
from unittest.mock import Mock, patch, MagicMock

from ad_ctf_apis.async_api import AdCtfApiAsync
from tests.test_locks import AsyncProcess
from tests.utils import BaseTestCase


async def process_inner(path: Path, counter: Synchronized[int]) -> None:
    api = AdCtfApiAsync("http://localhost/attack.json", path)
    with ApiTestCase.patch_request(ApiTestCase._res / "saarctf2025.json") as mock:
        await api.attack_info()
        with counter:
            counter.value += mock.call_count


async def make_async(x: bytes) -> bytes:
    return x


class ApiTestCase(BaseTestCase):
    def setUp(self) -> None:
        from ad_ctf_apis.async_api.api import _api_response_cache
        _api_response_cache._cache.clear()
        self.tempdir = tempfile.TemporaryDirectory()
        self.api = AdCtfApiAsync("http://localhost/attack.json", self.tempdir.name)

    def tearDown(self) -> None:
        self.tempdir.cleanup()

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

    async def test_fetch(self) -> None:
        with self.patch_request(self._res / "saarctf2025.json") as mock:
            info = await self.api.attack_info()
            mock.assert_called_once()
        self.assertIn("UttermostIntelligentSpot6463", info.flag_id_flat("Licenser", "nop"))

    async def test_memory_cache(self) -> None:
        with self.patch_request(self._res / "saarctf2025.json") as mock:
            info = await self.api.attack_info()
            self.api = AdCtfApiAsync("http://localhost/attack.json", self.tempdir.name)
            info = await self.api.attack_info()
            mock.assert_called_once()
        self.assertIn("UttermostIntelligentSpot6463", info.flag_id_flat("Licenser", "nop"))

    async def test_file_cache(self) -> None:
        with self.patch_request(self._res / "saarctf2025.json") as mock:
            info = await self.api.attack_info()

            # clear caches
            from ad_ctf_apis.async_api.api import _api_response_cache
            _api_response_cache._cache.clear()
            self.api = AdCtfApiAsync("http://localhost/attack.json", self.tempdir.name)

            info = await self.api.attack_info()
            mock.assert_called_once()
        self.assertIn("UttermostIntelligentSpot6463", info.flag_id_flat("Licenser", "nop"))

    async def test_caches_expired(self) -> None:
        with self.patch_request(self._res / "saarctf2025.json") as mock:
            info = await self.api.attack_info()
            with patch("time.time", return_value=time.time() + 120):
                info = await self.api.attack_info()
            self.assertEqual(2, mock.call_count)
        self.assertIn("UttermostIntelligentSpot6463", info.flag_id_flat("Licenser", "nop"))

    async def test_simple_concurrency(self) -> None:
        async def task() -> None:
            info = await self.api.attack_info()
            self.assertIn("UttermostIntelligentSpot6463", info.flag_id_flat("Licenser", "nop"))

        with self.patch_request(self._res / "saarctf2025.json") as mock:
            await asyncio.gather(task(), task(), task(), task(), task(), task(), task(), task())
            mock.assert_called_once()

    def test_concurrent_processes(self) -> None:
        counter = multiprocessing.Value("i", 0)
        processes = [AsyncProcess(process_inner, self.tempdir.name, counter) for _ in range(16)]
        for process in processes:
            process.start()
        for process in processes:
            process.join(timeout=1)
        for process in processes:
            self.assertEqual(0, process.exitcode)
        self.assertEqual(1, counter.value)

    def test_concurrent_read_write(self) -> None:
        p = Path(self.tempdir.name) / "test.json"
        p.write_text("{}")
        processes = [
            Process(target=process_reader, args=(p,)),
            Process(target=process_reader, args=(p,)),
            Process(target=process_writer, args=(p,))
        ]
        for process in processes:
            process.start()
        for process in processes:
            process.join(timeout=3)
        for process in processes:
            self.assertEqual(0, process.exitcode)


def _slow_atomic_write(p: Path, raw: bytes) -> None:
    tmpfile = p.with_suffix(f".json.tmp")
    with tmpfile.open("wb") as f:
        time.sleep(0.01)
        f.write(raw)
        f.flush()
        os.fsync(f.fileno())
    tmpfile.replace(p)


def process_reader(p: Path) -> None:
    deadline = time.monotonic() + 2
    while time.monotonic() < deadline:
        json.loads(p.read_bytes())
        time.sleep(0.001)


def process_writer(p: Path) -> None:
    from ad_ctf_apis.async_api.api import _atomic_write
    for _ in range(100):
        _atomic_write(p, json.dumps({"ts": time.time()}).encode("utf-8"))
        time.sleep(0.01)
        _slow_atomic_write(p, json.dumps({"ts": time.time()}).encode("utf-8"))
        time.sleep(0.01)
