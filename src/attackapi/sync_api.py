import asyncio
import tempfile
from pathlib import Path
from typing import Any, Union

from attackapi import AttackInfo
from attackapi.async_api import AdCtfApiAsync


class AdCtfApiSync:
    def __init__(self, url: str = "", tmp_directory: Union[str, Path] = tempfile.gettempdir(), **kwargs: Any) -> None:
        """
        Create a new API client for synchronous use.

        :param url: URL of your game's API (defaults to environment variable CTF_API)
        :param tmp_directory: where to store cache files
        :param lifetime: How long to cache data for (in seconds)
        :param timeout: How long to wait for API calls (in seconds)
        :param decoder: A custom decoder for API responses, if the default one doesn't work for your game
        :param aiohttp_arguments: Optional arguments to pass to aiohttp.ClientSession
        """
        self._api = AdCtfApiAsync(url, tmp_directory, **kwargs)

    def attack_info(self) -> AttackInfo:
        """
        Get the current attack info. Either from cache, from disk, or from game API.
        This method might fail with aiohttp exceptions.
        """
        return asyncio.run(self._api.attack_info())
