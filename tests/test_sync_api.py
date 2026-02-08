import multiprocessing
import tempfile
from multiprocessing import Process
from multiprocessing.sharedctypes import Synchronized
from pathlib import Path
from threading import Thread

from attackapi.sync_api import AdCtfApiSync
from tests.utils import BaseTestCase


class SyncApiTestCase(BaseTestCase):
    def setUp(self) -> None:
        from attackapi.async_api.api import _api_response_cache
        _api_response_cache._cache.clear()
        self.tempdir = tempfile.TemporaryDirectory()
        self.api = AdCtfApiSync("http://localhost/attack.json", self.tempdir.name)

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def test_fetch(self) -> None:
        with self.patch_request(self._res / "saarctf2025.json") as mock:
            info = self.api.attack_info()
            mock.assert_called_once()
        self.assertIn("UttermostIntelligentSpot6463", info.flag_id_flat("Licenser", "nop"))

    def test_threadpool(self) -> None:
        with BaseTestCase.patch_request(BaseTestCase._res / "saarctf2025.json") as mock:
            threads = [Thread(target=lambda: self.api.attack_info()) for _ in range(16)]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join(timeout=1)
            mock.assert_called_once()

    def test_concurrent_processes(self) -> None:
        counter = multiprocessing.Value("i", 0)
        processes = [Process(target=process_inner, args=(self.tempdir.name, counter)) for _ in range(16)]
        for process in processes:
            process.start()
        for process in processes:
            process.join(timeout=1)
        for process in processes:
            self.assertEqual(0, process.exitcode)
        self.assertEqual(1, counter.value)


def process_inner(path: Path, counter: Synchronized[int]) -> None:
    api = AdCtfApiSync("http://localhost/attack.json", path)
    with BaseTestCase.patch_request(BaseTestCase._res / "saarctf2025.json") as mock:
        api.attack_info()
        with counter:
            counter.value += mock.call_count
