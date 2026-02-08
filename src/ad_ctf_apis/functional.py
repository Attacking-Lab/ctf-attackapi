import tempfile
from typing import Optional, Any

from ad_ctf_apis import AttackInfo
from ad_ctf_apis.async_api import AdCtfApiAsync
from ad_ctf_apis.sync_api import AdCtfApiSync

_sync_api: Optional[AdCtfApiSync] = None
_async_api: Optional[AdCtfApiAsync] = None


def configure(url: str = "", tmp_directory: str = tempfile.gettempdir(), **kwargs: Any) -> None:
    """
    Configure the caching API. Only URL is required.

    :param url: URL of your game's API (defaults to environment variable CTF_API)
    :param tmp_directory: where to store cache files
    :param lifetime: How long to cache data for (in seconds)
    :param timeout: How long to wait for API calls (in seconds)
    :return:
    """
    global _sync_api, _async_api
    _sync_api = AdCtfApiSync(url, tmp_directory, **kwargs)
    _async_api = AdCtfApiAsync(url, tmp_directory, **kwargs)


def attack_info() -> AttackInfo:
    """
    Get the current attack info. Either from cache, from disk, or from game API.
    This method might fail with aiohttp exceptions.
    """
    global _sync_api
    if _sync_api is None:
        _sync_api = AdCtfApiSync()
    return _sync_api.attack_info()


async def attack_info_async() -> AttackInfo:
    """
    Get the current attack info. Either from cache, from disk, or from game API.
    This method might fail with aiohttp exceptions.
    """
    global _async_api
    if _async_api is None:
        _async_api = AdCtfApiAsync()
    return await _async_api.attack_info()
