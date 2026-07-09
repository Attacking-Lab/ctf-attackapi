import hashlib
import os
import sys
import tempfile
import time
from importlib.metadata import version
from pathlib import Path
from typing import Optional, Union, Generic, TypeVar, AsyncContextManager

import aiologic
from aiohttp import ClientSession, ClientTimeout
from filelock import FileLock

from attackapi.async_api.decoders import Decoder
from attackapi.async_api.filelock import acquire_filelock
from attackapi.models import AttackInfo

T = TypeVar("T")


class GlobalCache(Generic[T]):
    """In-memory cache for API responses. Shared between threads/loops, not shared between processes."""

    def __init__(self) -> None:
        # take the lock before modifying the cache.
        # thanks to GIL this is not necessary for thread safety, but it avoids multiple concurrent loads
        self.lock = aiologic.Lock()
        self._cache: dict[str, tuple[float, T]] = {}

    def age(self, key: str) -> Optional[float]:
        if key in self._cache:
            return time.time() - self._cache[key][0]
        return None

    def get(self, key: str) -> T:
        return self._cache[key][1]

    def set(self, key: str, value: T) -> None:
        self._cache[key] = (time.time(), value)


_api_response_cache: GlobalCache[AttackInfo] = GlobalCache()


class FileCache:
    def __init__(self, path: Path, lock: Path) -> None:
        self._path = path
        self._lock = lock

    def age(self) -> Optional[float]:
        try:
            return time.time() - self._path.stat().st_mtime
        except FileNotFoundError:
            return None

    def get(self) -> Optional[bytes]:
        """
        On Linux: not necessary to have the lock()
        On Windows: Must only be called while the lock() is taken
        """
        try:
            return self._path.read_bytes()
        except FileNotFoundError:
            pass
        return None

    def set(self, value: bytes) -> None:
        """Must only be called while the lock() is taken"""
        _atomic_write(self._path, value)

    def lock(self) -> AsyncContextManager[None]:
        return acquire_filelock(FileLock(self._lock))


def _atomic_write(p: Path, raw: bytes) -> None:
    tmpfile = p.with_suffix(f".json.tmp")
    with tmpfile.open("wb") as f:
        f.write(raw)
        f.flush()
        os.fsync(f.fileno())
    tmpfile.replace(p)


class AdCtfApiAsync:
    """
    Async API to retrieve AD team / flag information with as much caching as possible.
    """

    def __init__(self, url: str = "", tmp_directory: Union[str, Path] = tempfile.gettempdir(), *,
                 lifetime: float = 30.0, timeout: float = 10.0, decoder: Optional[Decoder] = None,
                 aiohttp_arguments: Optional[dict] = None) -> None:
        """
        Create a new API client.

        :param url: URL of your game's API (defaults to environment variable CTF_API)
        :param tmp_directory: where to store cache files
        :param lifetime: How long to cache data for (in seconds)
        :param timeout: How long to wait for API calls (in seconds)
        :param decoder: A custom decoder for API responses, if the default one doesn't work for your game
        :param aiohttp_arguments: Optional arguments to pass to aiohttp.ClientSession
        """
        if not url:
            if "CTF_API" not in os.environ:
                raise Exception("Please call configure() or set CTF_API environment variable!")
            url = os.environ["CTF_API"]
        if timeout < 1:
            raise ValueError("Timeout must be at least 1 second")
        if lifetime < timeout:
            raise ValueError("Lifetime must be at least as long as timeout")

        self._url = url
        self._lifetime = lifetime
        self._timeout = timeout
        self._decoder = decoder or Decoder()
        self._aiohttp_arguments = aiohttp_arguments or {
            "headers": {"User-Agent": "python/attackapi " + version("ctf-attackapi")}
        }
        self._cache_key = hashlib.sha256(url.encode()).hexdigest()[:12]
        self._file_cache = FileCache(
            Path(tmp_directory) / f"ctf-{self._cache_key}.json",
            Path(tmp_directory) / f"ctf-{self._cache_key}.json.lock"
        )

    async def attack_info(self) -> AttackInfo:
        """
        Get the current attack info. Either from cache, from disk, or from game API.
        This method might fail with aiohttp exceptions.
        """
        # Step 1: check in-process cache
        info = self._check_memory_cache()
        if info is not None:
            return info
        # not found? lock it to avoid concurrent loads
        async with _api_response_cache.lock:
            # check again to avoid race conditions
            info = self._check_memory_cache()
            if info is not None:
                return info
            # not found => load from file or API
            info = await self._attack_info_from_file()
            _api_response_cache.set(self._cache_key, info)
            return info

    def _check_memory_cache(self) -> Optional[AttackInfo]:
        if (age := _api_response_cache.age(self._cache_key)) is not None and age <= self._lifetime:
            return _api_response_cache.get(self._cache_key)
        return None

    def _check_file_cache(self) -> Optional[AttackInfo]:
        if (age := self._file_cache.age()) is not None and age <= self._lifetime:
            raw = self._file_cache.get()
            if raw is not None:
                return self._decoder.parse(raw)
        return None

    async def _attack_info_from_file(self) -> AttackInfo:
        # Step 2: try to load from file
        # this does not work on Windows, because concurrent read + replacing files is not possible.
        # for better performance please use Linux
        if sys.platform != "win32":
            info = self._check_file_cache()
            if info is not None:
                return info
        # not found? lock it to avoid concurrent API requests
        async with self._file_cache.lock():
            # recheck to avoid race conditions
            info = self._check_file_cache()
            if info is not None:
                return info
            # not found => load from API
            raw = await self._attack_info_from_remote()
            info = self._decoder.parse(raw)
            # and save to file (atomic)
            self._file_cache.set(raw)
            return info

    async def _attack_info_from_remote(self) -> bytes:
        async with ClientSession(**self._aiohttp_arguments) as session:
            async with session.get(self._url, timeout=ClientTimeout(total=self._timeout)) as response:
                response.raise_for_status()
                return await response.read()
