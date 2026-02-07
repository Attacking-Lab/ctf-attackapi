import tempfile
from typing import Optional

from ad_ctf_apis import AttackInfo
from ad_ctf_apis.async_api import AdCtfApiAsync
from ad_ctf_apis.sync_api import AdCtfApiSync

_sync_api: Optional[AdCtfApiSync] = None
_async_api: Optional[AdCtfApiAsync] = None


def configure(url: str = "", tmp_directory: str = tempfile.gettempdir(), **kwargs) -> None:
    global _sync_api, _async_api
    _sync_api = AdCtfApiSync(url, tmp_directory, **kwargs)
    _async_api = AdCtfApiAsync(url, tmp_directory, **kwargs)


def attack_info() -> AttackInfo:
    global _sync_api
    if _sync_api is None:
        _sync_api = AdCtfApiSync()
    return _sync_api.attack_info()


async def attack_info_async() -> AttackInfo:
    global _async_api
    if _async_api is None:
        _async_api = AdCtfApiAsync()
    return await _async_api.attack_info()
