import asyncio
import multiprocessing
import os
import tempfile
import unittest

import aiologic
from filelock import FileLock

from attackapi.async_api.filelock import acquire_filelock
from .utils import BaseTestCase, AsyncThread, AsyncProcess


class LocksTestCase(BaseTestCase):
    def test_async_multithreaded(self) -> None:
        """Two different loops in two different threads compete on one async_api lock"""
        lock = aiologic.Lock()
        events = []

        async def t1() -> None:
            async with lock:
                events.append(1)
                await asyncio.sleep(0.1)
                events.append(2)

        async def t2() -> None:
            await asyncio.sleep(0.05)
            async with lock:
                events.append(3)

        threads = [AsyncThread(t1()), AsyncThread(t2())]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=1)

        self.assertEqual(events, [1, 2, 3])

    def test_async_filelock_multithreaded(self) -> None:
        """Two different loops in two different threads compete on one async_api filelock"""
        with tempfile.TemporaryDirectory() as tmpdir:
            lock = FileLock(tmpdir + "/lockfile")
            events = []

            async def t1() -> None:
                async with acquire_filelock(lock, timeout=1):
                    events.append(1)
                    await asyncio.sleep(0.1)
                    events.append(2)

            async def t2() -> None:
                await asyncio.sleep(0.05)
                async with acquire_filelock(lock, timeout=1):
                    events.append(3)

            threads = [AsyncThread(t1()), AsyncThread(t2())]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join(timeout=1)

        self.assertEqual(events, [1, 2, 3])

    @staticmethod
    async def _filetest_t1(tmpdir: str, events: list) -> None:
        lock = FileLock(tmpdir + "/lockfile")
        async with acquire_filelock(lock, timeout=1):
            events.append(1)
            await asyncio.sleep(0.2)
            events.append(2)

    @staticmethod
    async def _filetest_t2(tmpdir: str, events: list) -> None:
        lock = FileLock(tmpdir + "/lockfile")
        await asyncio.sleep(0.1)
        async with acquire_filelock(lock, timeout=1):
            events.append(3)

    @staticmethod
    async def _filetest_t3(tmpdir: str, events: list) -> None:
        """Provoke timeout"""
        lock = FileLock(tmpdir + "/lockfile")
        await asyncio.sleep(0.1)
        try:
            async with acquire_filelock(lock, timeout=0.01, interval=0.001):
                events.append(3)
        except TimeoutError:
            return
        raise Exception("Did not hit timeout")

    @staticmethod
    async def _filetest_t4(tmpdir: str, events: list) -> None:
        """Take lock and crash"""
        lock = FileLock(tmpdir + "/lockfile")
        await acquire_filelock(lock, timeout=0.01, interval=0.001).__aenter__()
        os._exit(0)

    def test_async_filelock_processes(self) -> None:
        """Two different loops in two different threads compete on one async_api filelock"""
        with tempfile.TemporaryDirectory() as tmpdir:
            events = multiprocessing.Manager().list()

            processes = [
                AsyncProcess(self._filetest_t1, tmpdir, events),
                AsyncProcess(self._filetest_t2, tmpdir, events)
            ]
            for process in processes:
                process.start()
            for process in processes:
                process.join(timeout=1)
            for process in processes:
                self.assertEqual(0, process.exitcode)

        self.assertEqual(list(events), [1, 2, 3])

    def test_async_filelock_processes_timeout(self) -> None:
        """Two different loops in two different threads compete on one async_api filelock"""
        with tempfile.TemporaryDirectory() as tmpdir:
            events = multiprocessing.Manager().list()

            processes = [AsyncProcess(self._filetest_t1, tmpdir, events),
                         AsyncProcess(self._filetest_t3, tmpdir, events)]
            for process in processes:
                process.start()
            for process in processes:
                process.join(timeout=1)
            for process in processes:
                self.assertEqual(0, process.exitcode)

        self.assertEqual(list(events), [1, 2])

    def test_async_filelock_processes_no_deadlock_after_crash(self) -> None:
        """Two different loops in two different threads compete on one async_api filelock"""
        with tempfile.TemporaryDirectory() as tmpdir:
            events = multiprocessing.Manager().list()

            processes = [AsyncProcess(self._filetest_t4, tmpdir, events),
                         AsyncProcess(self._filetest_t2, tmpdir, events)]
            for process in processes:
                process.start()
            for process in processes:
                process.join(timeout=1)
            for process in processes:
                self.assertEqual(0, process.exitcode)

        self.assertEqual(list(events), [3])

    # TODO run cross-platform


if __name__ == '__main__':
    unittest.main()
