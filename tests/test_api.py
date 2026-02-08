import asyncio
import json
import multiprocessing
import os
import tempfile
import time
from multiprocessing import Process
from multiprocessing.sharedctypes import Synchronized
from pathlib import Path
from unittest.mock import patch

from attackapi.async_api import AdCtfApiAsync
from tests.utils import BaseTestCase, AsyncThread, AsyncProcess


class ApiTestCase(BaseTestCase):
    def setUp(self) -> None:
        from attackapi.async_api.api import _api_response_cache
        _api_response_cache._cache.clear()
        self.tempdir = tempfile.TemporaryDirectory()
        self.api = AdCtfApiAsync("http://localhost/attack.json", self.tempdir.name)

    def tearDown(self) -> None:
        self.tempdir.cleanup()

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
            from attackapi.async_api.api import _api_response_cache
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

    def test_concurrent_threads(self) -> None:
        with self.patch_request(self._res / "saarctf2025.json") as mock:
            threads = [AsyncThread(self.api.attack_info()) for _ in range(16)]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join(timeout=1)
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


async def process_inner(path: Path, counter: Synchronized[int]) -> None:
    api = AdCtfApiAsync("http://localhost/attack.json", path)
    with BaseTestCase.patch_request(BaseTestCase._res / "saarctf2025.json") as mock:
        await api.attack_info()
        with counter:
            counter.value += mock.call_count


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
    from attackapi.async_api.api import _atomic_write
    for _ in range(100):
        _atomic_write(p, json.dumps({"ts": time.time()}).encode("utf-8"))
        time.sleep(0.01)
        _slow_atomic_write(p, json.dumps({"ts": time.time()}).encode("utf-8"))
        time.sleep(0.01)
