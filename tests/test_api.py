import asyncio
import json
import multiprocessing
import os
import sys
import tempfile
import time
from contextlib import contextmanager
from multiprocessing import Process
from multiprocessing.sharedctypes import Synchronized
from multiprocessing.synchronize import Event
from pathlib import Path
from typing import Generator
from unittest.mock import patch

from filelock import FileLock

from attackapi.async_api import AdCtfApiAsync
from attackapi.async_api.api import FileCache, GenericAdCtfApiAsync, GlobalCache
from .utils import BaseTestCase, AsyncThread, AsyncProcess


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
        self.assertIn("UttermostIntelligentSpot6463", info.flag_ids("Licenser", "nop"))

    async def test_memory_cache(self) -> None:
        with self.patch_request(self._res / "saarctf2025.json") as mock:
            info = await self.api.attack_info()
            self.api = AdCtfApiAsync("http://localhost/attack.json", self.tempdir.name)
            info = await self.api.attack_info()
            mock.assert_called_once()
        self.assertIn("UttermostIntelligentSpot6463", info.flag_ids("Licenser", "nop"))

    async def test_file_cache(self) -> None:
        with self.patch_request(self._res / "saarctf2025.json") as mock:
            info = await self.api.attack_info()

            # clear caches
            from attackapi.async_api.api import _api_response_cache
            _api_response_cache._cache.clear()
            self.api = AdCtfApiAsync("http://localhost/attack.json", self.tempdir.name)

            info = await self.api.attack_info()
            mock.assert_called_once()
        self.assertIn("UttermostIntelligentSpot6463", info.flag_ids("Licenser", "nop"))

    async def test_caches_expired(self) -> None:
        with self.patch_request(self._res / "saarctf2025.json") as mock:
            info = await self.api.attack_info()
            with patch("time.time", return_value=time.time() + 120):
                info = await self.api.attack_info()
            self.assertEqual(2, mock.call_count)
        self.assertIn("UttermostIntelligentSpot6463", info.flag_ids("Licenser", "nop"))

    async def test_simple_concurrency(self) -> None:
        async def task() -> None:
            info = await self.api.attack_info()
            self.assertIn("UttermostIntelligentSpot6463", info.flag_ids("Licenser", "nop"))

        with self.patch_request(self._res / "saarctf2025.json") as mock:
            await asyncio.gather(task(), task(), task(), task(), task(), task(), task(), task())
            mock.assert_called_once()

    def test_concurrent_threads(self) -> None:
        with self.patch_request(self._res / "saarctf2025.json") as mock:
            threads = [AsyncThread(self.api.attack_info()) for _ in range(16)]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join(timeout=2)
            mock.assert_called_once()

    def test_concurrent_processes(self) -> None:
        counter = multiprocessing.Value("i", 0)
        processes = [AsyncProcess(process_inner, self.tempdir.name, counter) for _ in range(16)]
        for process in processes:
            process.start()
        for process in processes:
            process.join(timeout=3)
        for process in processes:
            self.assertEqual(0, process.exitcode)
        self.assertEqual(1, counter.value)

    def test_concurrent_read_write(self) -> None:
        p = Path(self.tempdir.name) / "test.json"
        p.write_text("{}")
        stop = multiprocessing.Event()
        readers = [
            Process(target=process_reader, args=(p, stop)),
            Process(target=process_reader, args=(p, stop)),
            Process(target=process_reader_slow, args=(p, stop))
        ]
        writer = Process(target=process_writer, args=(p,))
        processes = readers + [writer]
        for process in processes:
            process.start()
        try:
            writer.join(timeout=120)
            stop.set()
            for process in readers:
                process.join(timeout=30)
            for process in processes:
                self.assertEqual(0, process.exitcode)
        finally:
            # a survivor keeps writing into tempdir, and tearDown's rmtree would race it
            for process in processes:
                if process.is_alive():
                    process.terminate()
                process.join()


class GenericApiTestCase(BaseTestCase):
    """The generic client is used for any cached game endpoint, not only attack.json."""

    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.cache: GlobalCache = GlobalCache()

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def _api(self, **kwargs: object) -> GenericAdCtfApiAsync[dict]:
        return GenericAdCtfApiAsync(
            lambda raw: json.loads(raw),  # a plain callable, no GenericDecoder subclass
            "http://localhost/scoreboard_current.json",
            self.tempdir.name,
            memory_cache=self.cache,
            **kwargs  # type: ignore[arg-type]
        )

    async def test_callable_decoder(self) -> None:
        with self.patch_request(self._res / "saarctf2025.json") as mock:
            data = await self._api().retrieve()
            mock.assert_called_once()
        self.assertEqual(237, data["current_tick"])

    async def test_injected_memory_cache_is_not_shared(self) -> None:
        # the process-wide cache is keyed by URL alone, so tests that want isolation inject their own
        other = tempfile.TemporaryDirectory()
        self.addCleanup(other.cleanup)
        with self.patch_request(self._res / "saarctf2025.json") as mock:
            await self._api().retrieve()
            await GenericAdCtfApiAsync(
                json.loads, "http://localhost/scoreboard_current.json", other.name,
                memory_cache=GlobalCache()
            ).retrieve()
            self.assertEqual(2, mock.call_count)

    async def test_progress_wraps_remote_fetch_only(self) -> None:
        events = []

        @contextmanager
        def progress(url: str) -> Generator[None, None, None]:
            events.append(("start", url))
            try:
                yield
            finally:
                events.append(("stop", url))

        with self.patch_request(self._res / "saarctf2025.json"):
            api = self._api(progress=progress)
            await api.retrieve()
            await api.retrieve()  # cached, no progress

        url = "http://localhost/scoreboard_current.json"
        self.assertEqual([("start", url), ("stop", url)], events)


async def process_inner(path: Path, counter: Synchronized) -> None:
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


@contextmanager
def _lock_on_windows(p: Path) -> Generator[None, None, None]:
    if sys.platform == "win32":
        with FileLock(p):
            yield
    else:
        yield


def process_reader(p: Path, stop: Event) -> None:
    cache = FileCache(p, p.with_suffix(".json.lock"))
    deadline = time.monotonic() + 120  # backstop only; the writer is what ends this
    while not stop.is_set() and time.monotonic() < deadline:
        with _lock_on_windows(cache._lock):
            json.loads(cache.get() or b'')
        time.sleep(0.001)


def process_reader_slow(p: Path, stop: Event) -> None:
    cache = FileCache(p, p.with_suffix(".json.lock"))
    deadline = time.monotonic() + 120  # backstop only; the writer is what ends this
    while not stop.is_set() and time.monotonic() < deadline:
        with _lock_on_windows(cache._lock):
            with p.open("rb") as f:
                time.sleep(0.015)
                json.loads(f.read())
        time.sleep(0.001)


def process_writer(p: Path) -> None:
    cache = FileCache(p, p.with_suffix(".json.lock"))
    for _ in range(100):
        with FileLock(cache._lock):
            cache.set(json.dumps({"ts": time.time()}).encode("utf-8"))
        time.sleep(0.01)
        with FileLock(cache._lock):
            _slow_atomic_write(p, json.dumps({"ts": time.time()}).encode("utf-8"))
        time.sleep(0.01)
