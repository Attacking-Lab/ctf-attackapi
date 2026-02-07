import asyncio
import tempfile
from pathlib import Path
from typing import Any, Union

from ad_ctf_apis import AttackInfo
from ad_ctf_apis.async_api import AdCtfApiAsync


class AdCtfApiSync:
    def __init__(self, url: str = "", tmp_directory: Union[str, Path] = tempfile.gettempdir(), **kwargs: Any) -> None:
        self._api = AdCtfApiAsync(url, tmp_directory, **kwargs)

    def attack_info(self) -> AttackInfo:
        return asyncio.run(self._api.attack_info())
